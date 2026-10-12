# Gate 7: the states pass hold (and the physical pass)

Audit of 2026-10-12, gate 7 of [the gate audits](./README.md), by an Opus agent, read-only, no paid calls.  Every
verdict on a word below is the agent's own reading unless it is marked as a reference label (a corpus file, Roger's
own example, or Roger's review decision).

**Verdict: doing what was intended but improvable.**  The pass's core, the duration test and the plausibility test,
holds 83 rows and is wrong on 1 of them (4 with the borderline cases).  Two small sub-rules do almost all the damage:
the gloss check holds 11 rows and 10 of them are traits (it demands that the check's reading equal the route, so a
predisposition gloss read as "lasting" is held although both readings are standing ways of being), and the one-hop
rule holds 3 rows, all traits ([hurried](../../../data/traits/instructions/hurried.json) is a corpus trait).  Narrowing
the one-hop rule to "every source is states_pass" is right in principle but changes 3 rows today (6 on a rejudge) and
loses almost nothing either way; the bigger fixes are the check's acceptance rule and the duration question, which is
answered about M1's momentary wording of the state and misses two of the five lasting examples Roger gave that were judged.  The physical pass
discards nothing.

Terms: M1, M3, R1, the registry and the review app are defined in the terms block of [escalations.md](../escalations.md#terms);
the trait-gap vocabulary is in the [glossary](../../trait_gap_generation/glossary.md).  Here also:

- **Holding list**: the registry field `holding` on a row, which keeps it out of the trait flow (no M3, no review
  graph, refused by bulk promotion).  M1 puts a word whose accepted reading is a passing state on the `states` list.
- **The states pass**: the Haiku 5.5 pass over the `states` list ([states_pass.py](../../../assistant_axis/gapgen/states_pass.py),
  CLI [states_pass.py](../../../data_analysis/gap_generation/states_pass.py)).  Its *queue call* answers, per word, a
  typical duration and Roger's questions; the code turns the answers into a **route** (`role`, `lasting`,
  `predisposition`, `renamed`, `held`).
- **Released**: the `lasting` and `predisposition` routes, whose rows move to the list `states_released` and go through
  M3 and the review app.  **Held**: the route `held`; the row stays on the `states` list.  `renamed` rows also stay on
  the list, but their suggested name is submitted as a new candidate.
- **The gloss check**: the confirmation of a released row's gloss (the one-sentence "This means ..." description): a
  keyword scan, then, if the scan does not pass it, a Haiku call that reads the gloss as `lasting`, `predisposition` or
  `passing`.
- **The one-hop rule**: a row the states pass itself submitted (as a rename) is not renamed a second time; it is held.
- **M1's reading**: the sense M1 accepted for the word (`filter.judged_sense`), which is the "state description" the
  queue call is shown.

A correction to [the gate table](./README.md#the-gates): "held: 81 of 120" conflates two numbers.  The pass has held
**97** rows (route `held`); the one-hop rule held **3** of them.  **120** is the number of registry rows with a
`states_pass` source (the pass's renames), and **81** of those were also proposed by another generator, which is the
population review 3 D5 counted ([escalations.md](../escalations.md#review-3-d5-the-states-one-hop-hold-fires-on-any-row-with-a-states-pass-source)).
Also, the one-hop hold is not in promotion: it is in the states pass's `route_for`; promotion only refuses held rows
(section 1).

---

## 1. The rule, from the code

**How a row reaches the list.**  M1's split pipeline maps the outcome `states` to verdict `tagged`, tag `state` and
`holding: "states"` ([split.py:537](../../../assistant_axis/gapgen/split.py) `QUEUE_TAG`, `verdict_tags_holding`
at [split.py:541-554](../../../assistant_axis/gapgen/split.py)).  The holding lists are enumerated in
[normalize.py:35](../../../assistant_axis/gapgen/normalize.py).

**Which rows the pass reads.**  `--holding-states` takes the rows on the `states` list that have no `states_pass` block
yet, every one with `--rejudge` ([CLI states_pass.py:115-118](../../../data_analysis/gap_generation/states_pass.py));
a row judged once is never picked up again without `--rejudge`.  The text it is shown is M1's gloss, or for a
split-filter row (all of them so far) M1's reading `filter.judged_sense` (`state_text`,
[states_pass.py:632-636](../../../assistant_axis/gapgen/states_pass.py)).

**The queue call** (prompt v4, `RUBRIC_VERSIONS = {"queue": 4}` at [states_pass.py:115](../../../assistant_axis/gapgen/states_pass.py);
`DEFAULT_MODEL = "claude-haiku-5-5"`, 20 rows a call, `max_tokens` 16000, lines 121-126): per row, reason first, then
`typical_duration` in `DURATIONS` = hours, days, weeks, months, years (line 134) and `lasting`, defined as "the state
typically lasts months or longer ... a state of weeks, or of weeks to months, is not lasting" (prompt lines 171-173).
A lasting row answers `role` (the kind call's role definition, lines 175-177) and a gloss of the condition.  A row
that does not last answers `plausible` ("could a person be prone to falling into it again and again ... Conditions
imposed from outside, or purely bodily conditions that no temperament brings about, mostly do not", lines 181-184),
`name_fits` ("ordinary speakers already use the word for a person who is often that way", lines 185-188),
`suggested_name` and a gloss of the predisposition.  `validate_queue_row` (lines 329-382) records `duration_agrees`
(`lasting == (duration in LASTING_DURATIONS)`, line 380, with `LASTING_DURATIONS = ("months", "years")` at line 135)
but does not act on it: the model's `lasting` wins.

**The routes** (`route_for`, [states_pass.py:471-487](../../../assistant_axis/gapgen/states_pass.py)):

| condition, in order | route | `holding_after` (lines 490-496) |
|---|---|---|
| `lasting` and `role` | `role` | `roles` (and entity type `role`, [CLI:376-379](../../../data_analysis/gap_generation/states_pass.py)); no check, no M3 |
| `lasting`, not a role | `lasting` | `states_released` if the gloss check confirms, else `held` |
| not lasting, not `plausible` | `held` ("not lasting, and no habitual predisposition is plausible") | `states` |
| plausible, and the name fits (or the suggestion equals the label in either form) | `predisposition` | `states_released` if confirmed, else `held` |
| plausible, another name, and the row has a `states_pass` source | `held` (`ONE_HOP_REASON`, "already a states-pass rename", line 148; lines 485-486) | `states` |
| plausible, another name | `renamed` | `states`; the name is submitted as a candidate (generator `states_pass`, [CLI:359-367](../../../data_analysis/gap_generation/states_pass.py)) |

**The gloss check** (`_queue_stages`, [states_pass.py:1025-1084](../../../assistant_axis/gapgen/states_pass.py)).  The
scan (`SCAN_FOR`, `SCAN_AGAINST`, lines 288-295; `scan_gloss`, lines 507-517) passes a gloss with a marker for its route
("months", "day after day", "daily" ...; "again and again", "easily", "often", "any", "every", "readily" ...) and none
against ("right now", "today", "just", "briefly" ...).  The scan never rejects.  Any other gloss goes to the check call
(`CHECK_PROMPT` v1, lines 261-279; `CHECK_READINGS` = lasting, predisposition, passing), which is not told the route.
The acceptance is **`accepted = parsed["reading"] == route`** (line 1068).  A rejected gloss makes the row `held`, with
the check's reason as `route_reason` and the intended route as `proposed_route` (lines 1076-1083).  The check prompt has
no tie-breaker; the corpus-mode prompt of the same module has one ("When the description could be read either way,
choose 'predisposition'", lines 242-243).

**The one-hop rule.**  `from_states_pass(row)` is true when **any** source of the row has generator `states_pass`
([states_pass.py:656-658](../../../assistant_axis/gapgen/states_pass.py)); it is read when the rows are selected
(`items_from_registry`, lines 661-666; on `--resume`, [CLI:112-113](../../../data_analysis/gap_generation/states_pass.py)),
so sources added by the same batch's own renames are not seen.  It fires only on the rename branch.

**What happens to a held row.**  It stays on the `states` list.  Nothing shows it except the `holding --list states` and
`report --include-held` commands of [gap_registry.py](../../../data_analysis/gap_generation/gap_registry.py); it never
reaches M3 or the review app.  Promotion ([promote.py:175-202](../../../assistant_axis/gapgen/promote.py)
`states_promotion`, branch at lines 236-240) refuses it unless the pass judged it plausible, gave a gloss, and the
command names Roger's confirmed name (`--confirm-state-name KEY=NAME`, [gap_registry.py:551-555](../../../data_analysis/gap_generation/gap_registry.py)):
so the gloss-check and one-hop holds can be promoted by name with the pass's gloss as the draft (review 3 D4), the
implausible ones never.  A released row is promoted only by name (`allow_released_states=bool(args.keys)`,
[gap_registry.py:560-561](../../../data_analysis/gap_generation/gap_registry.py); [promote.py:241-252](../../../assistant_axis/gapgen/promote.py)).

**The physical pass** ([physical_pass.py](../../../assistant_axis/gapgen/physical_pass.py)) has no gate of its own.  It
glosses every row on the `physical` list that has no gloss (M1's gloss and alignment calls; `needs_gloss`, lines 94-95),
hands each glossed row to M3 (`candidate_from_row`, lines 98-112: refused only as `not_filtered`, `not_on_physical_list`
or `no_gloss`), and promotion takes it only by name.  The hold that matters is M1's `physical` tag (gate 5), and the
delay until the pass runs.

## 2. The intent

- Roger's correction to decision 12 ([decisions_m1.md](../../trait_gap_generation/decisions_m1.md), section 12): "the
  state tag was useful, but not inherently disqualifying, it merely means there is some extra work to do: a) figure out
  if a habitual predisposition to state is plausible, b) whether the name of the state is still a good name for the
  predisposition (or if not, change the stem to that), and b) write the description to describe the habitual
  predisposition ... If a trait already in the corpus gets this tag during us checking the corpus, the default
  assumption ... is that this has already been done."  The platform plan's design table puts it as "State words are in
  scope as dispositions" ([coding_plan_platform.md](../../trait_gap_generation/coding_plan_platform.md), line 19).
- Roger's rules of 2026-10-09, [QUESTIONS.md](../../trait_gap_generation/QUESTIONS.md) question 45 (status **Roger:
  Confirmed**) and [coding_plan_review.md](../../trait_gap_generation/coding_plan_review.md) section 9: "a state that
  typically lasts months or longer, rather than days or weeks, drops 'states'", with his derivation: "How likely
  is this to wear off during the course of a narrative? ... narratives that last weeks in, say, a dozen paragraphs are
  not that uncommon, while months in a dozen paragraphs is unusual."  His examples: lasting are expecting
  ([pregnant](../../../data/roles/instructions/pregnant.json)), [unemployed](../../../data/roles/instructions/unemployed.json),
  "depressed (an episode)", "grieving (sorrowing, heartsick)", [newlywed](../../../data/roles/instructions/newlywed.json);
  not lasting are [sleep-deprived](../../../data/traits/instructions/sleep_deprived.json), "housebound after a short
  illness", jet-lagged.  Otherwise: is a predisposition plausible, does the label have that sense, "confirm the gloss
  was written that way (possibly a keyword scan, backed by a Haiku call)", "and if confirmed move it out of the states
  queue".
- The one-hop rule is the coordinator's proposal inside question 45 ("a candidate the states pass submitted gets one
  hop (a second rename is held)"), confirmed with the rest of the routing.  **No reason is recorded for it**, and
  nothing says whether "submitted" means "submitted only by the pass"; the evident purpose is to bound chains of the
  pass's own renames.  The gloss check's "reading must equal the route" is likewise the implementation's reading of
  "confirm the gloss was written that way"; **no derivation is recorded** for requiring the same released route rather
  than any reading other than the passing state.  `LASTING_DURATIONS` (months, years) is Roger's own line, with the
  derivation quoted above.
- The physical list: Roger, question 1 of [QUESTIONS.md](../../trait_gap_generation/QUESTIONS.md) and section 8 of
  [coding_plan_review.md](../../trait_gap_generation/coding_plan_review.md): "On the physical queue, I think we handle
  promotion normally, and if promoted they get the physical tag ... probably worth doing this as a separate pass, but I
  think the process and tooling is the same."  Physical means "mostly or entirely physical: e.g. blonde, dark-skinned"
  (decision 12 of [decisions_m1.md](../../trait_gap_generation/decisions_m1.md)).

## 3. The recorded discard, reproduced

From the registry ([registry.jsonl](../../../data/candidates/registry.jsonl), 23,660 lines folded to 8,061 keys, last
line per key), checked against each batch's [summary.json (TDA)](../../../data/candidates/states_pass/states_tda_1/summary.json)
and [summary.json (v4 pilot)](../../../data/candidates/states_pass/states_v4_pilot/summary.json); the two agree.

| batch | date | rows | role | lasting | predisposition | renamed | held: implausible | held: gloss check | held: one hop | held, all | cost |
|---|---|---|---|---|---|---|---|---|---|---|---|
| [states_v4_pilot](../../../data/candidates/states_pass/states_v4_pilot/results.jsonl) (the generator pilots, the antonym check, the M1 validation pool) | 2026-10-09 | 170 | 3 | 17 | 15 | 66 | 67 | 2 | 0 | **69 (41%)** | $0.034 |
| [states_tda_1](../../../data/candidates/states_pass/states_tda_1/results.jsonl) (the TDA census and the renames that M1 tagged state again) | 2026-10-10 | 150 | 1 | 12 | 27 | 82 | 16 | 9 | 3 | **28 (19%)** | $0.023 |
| both | | 320 | 4 | 29 | 42 | 148 | 83 | 11 | 3 | **97 (30%)** | $0.057 |

- Parse rate 100% in both; in the v4 pilot 6 of the 9 twenty-row calls hit `max_tokens` (then 8000) and a retry wave
  of 12 ten-row calls recovered every row.
- The gloss check saw 82 glosses of the released routes: the scan passed 29, the check call read 53 and confirmed 42.
  Of the 11 it turned down, **7 were read as the other released route** (6 predisposition glosses read as `lasting`,
  1 lasting gloss read as `predisposition`) and **4 as `passing`**.
- `duration_agrees` is false for 3 rows (destined, thirty-ninth, unwronged: months or years, not lasting); all three
  were held or renamed, and the agent agrees with each outcome.
- The renamed route submitted 148 names: 71 new rows, 77 merged into rows already there
  ([candidates.jsonl (v4)](../../../data/candidates/runs/states_pass/states_v4_pilot/candidates.jsonl),
  [candidates.jsonl (TDA)](../../../data/candidates/runs/states_pass/states_tda_1/candidates.jsonl)): **120** distinct
  rows now carry a `states_pass` source, 81 of them also from another generator, 39 from the pass alone.
- **Not yet judged: 900 rows** sit on the `states` list with no block: from the Allport-hi census (863), the full
  Roget run (42), the full WordNet run (12) and IPIP g600 (4) (a row can have several sources).  None of them has a
  `states_pass` source.  The CLI's own estimator, called offline, puts a run over them at **$0.32** through the Message
  Batches API ($0.63 live).
- By proposing generator (today's sources, a row counted under each): held share Roget 27 of 59, censuses 74 of 276,
  M1 validation 4 of 10, WordNet 7 of 23, antonym check 2 of 16, base model 2 of 16.  The Roget pilot's situational
  words (acquitted, alleged, denied ...) account for Roget's high share, rightly.
- Physical list: 199 rows; 72 have been through the physical pass's gloss stage and M3 (36 covered, 36 new;
  [physical_pilots_1](../../../data/candidates/novelty/physical_pilots_1/decisions.md),
  [physical_allport_pilots_1](../../../data/candidates/novelty/physical_allport_pilots_1/decisions.md),
  [physical_tda_1](../../../data/candidates/novelty/physical_tda_1/decisions.md)); 127 wait (116 of them from the
  Allport-hi census, 9 from the full WordNet run, 5 from the full Roget run, 1 from IPIP g600).  Nothing on the
  physical list is discarded.

## 4. The sample: every row (a census)

The gate has judged 320 rows and the physical list holds 199, so the agent read **every one** rather than a sample:
97 held, 148 renamed (which also stay on the list), 71 released, 4 roles, and the 199 physical rows.  No draw, so no
seed.  The data were read from the folded registry; the selection rule is "every row whose last registry line carries
a queue-mode `states_pass` block", and "every row with `holding: "physical"`".

### 4.1 Reference labels first

**(a) Corpus entities that went through the pass.**  M1 runs before M3's exact-label check, so 15 corpus traits and one
corpus role reached the states list.  By Roger's ruling (section 2) a corpus trait tagged a state has "already been
done": it is a predisposition under its own name.  The pass agreed on 8 of the 15 traits.

| corpus entity | batch | route | the queue call's reason | agrees with the corpus? |
|---|---|---|---|---|
| [amorous](../../../data/traits/instructions/amorous.json) | v4 | predisposition | Romantic desire is an emotional state lasting hours or days. Some people are habitually amorous, and the ordinary word is already used for such a person. | yes: released |
| [anxious](../../../data/traits/instructions/anxious.json) | tda | predisposition | Worry about a particular matter fades within hours or days. Anxious people are common, and the word is ordinarily used for someone who is often that way. | yes: released |
| [burned-out](../../../data/traits/instructions/burned_out.json) | tda | lasting | Exhaustion from prolonged overwork typically lasts months and wears off only slowly. It does not organize a whole identity, so it is not a role. | yes: released |
| [contented](../../../data/traits/instructions/contented.json) | v4 | held | Contentment with one's situation is a mood of hours or days. Some people are habitually contented, and ordinary speakers already call them contented. | **no: held** (gloss check read lasting) |
| [despairing](../../../data/traits/instructions/despairing.json) | tda | renamed | Despair passes over days or weeks, but a person can habitually see no hope, and 'hopeless' names that disposition. | **no: renamed to hopeless** |
| [edgy](../../../data/traits/instructions/edgy.json) | tda | predisposition | Nervous tension passes in hours or days, and people who are often nervous are called edgy. | yes: released |
| [healthy](../../../data/traits/instructions/healthy.json) | tda | lasting | Good physical health can last years. It is not a profession or calling, so it is not a role. | yes: released |
| [hurried](../../../data/traits/instructions/hurried.json) | tda | held | Being pressed for time passes within hours. A person who is always in a rush is plausible, but 'hurried' is not the ordinary name for that person. | **no: held** (one hop) |
| [joyful](../../../data/traits/instructions/joyful.json) | tda | renamed | Joy passes within hours. A habitually joyful person is plausible, but 'cheerful' is the plainer ordinary name for that disposition. | **no: renamed to [cheerful](../../../data/traits/instructions/cheerful.json)** |
| [lethargic](../../../data/traits/instructions/lethargic.json) | tda | held | Sluggishness and low energy come and go over days. People are often lethargic by temperament, and the word already describes that. | **no: held** (gloss check read lasting) |
| [lonely](../../../data/traits/instructions/lonely.json) | tda | held | Loneliness usually lifts within weeks as contact resumes. Some people are prone to it, and 'a lonely person' is ordinary usage. | **no: held** (gloss check read lasting) |
| [panicky](../../../data/traits/instructions/panicky.json) | tda | predisposition | Panic passes within hours. Some people are panicky by temperament, and the word is used of such people. | yes: released |
| [pensive](../../../data/traits/instructions/pensive.json) | tda | predisposition | A reflective mood lasts hours. Some people are pensive by temperament, and the word describes them. | yes: released |
| [procrastinating](../../../data/traits/instructions/procrastinating.json) | tda | renamed | Delaying a task lasts days at most for one episode. Habitual delay is very plausible and the ordinary noun is 'procrastinator'. | **no: renamed to [procrastinator](../../../data/roles/instructions/procrastinator.json) (role)** |
| [remorseful](../../../data/traits/instructions/remorseful.json) | v4 | predisposition | Guilt over past wrongs typically lasts days to weeks, not months. People who often feel remorse are plainly called remorseful. | yes: released |
| [unemployed](../../../data/roles/instructions/unemployed.json) (role) | v4 | lasting | Being out of paid work often lasts months, sometimes years. It does not rule out a profession or organize the whole identity, so it is not a role. | yes: released |

So **7 of 15 corpus traits (47%, 95% interval 25-70%) were not released**: 4 held, 3 renamed away from their own name.
Promotion refuses them anyway (their stems are in the corpus), so nothing is lost; but they measure the gate against
Roger's own labels, and the held ones fail at the gloss check and the one-hop rule, not at the plausibility test.

**(b) Roger's own examples** (section 2; the words in parentheses after "grieving" are the coordinator's mapping onto
batch words): five of his lasting examples were judged.  The pass made three lasting (expecting,
[unemployed](../../../data/roles/instructions/unemployed.json), heartsick) and renamed two as predispositions:
depressed (to gloomy) and sorrowing (to sorrowful).  M1's readings of the two were "currently feeling sad, low, or down
in mood" and "feeling sorrow or grief right now".  The pilot's readout counted a third grief word with them, lamenting
(M1: "grieving or mourning a loss"; given weeks, renamed to mournful).  Housebound came out a lasting role, but M1's reading ("because of
illness, disability or frailty") is not his "after a short illness", so it is not comparable.  Grieving itself is in
the unjudged 900.

**(c) Roger's review decisions** ([decisions.jsonl](../../../data/candidates/review/review_states_v4/decisions.jsonl),
review_states_v4, 2026-10-10): he promoted three released rows, disheveled (over rumpled, its group), declining and
sulky, and opened repentant, thriving and disabused without resolving them.  No decision touches a held row (held rows
never reach the app).  The decisions have not been applied: the registry rows still say `unreviewed`.  No decisions are
recorded for [review_states_tda_1](../../../data/candidates/review/review_states_tda_1/graph.json) or
[review_states_renamed_w23](../../../data/candidates/review/review_states_renamed_w23/graph.json).

**A finding about what the pass is shown.**  M1's reading carries a "now" marker ("currently", "right now", "at the
moment", "at present", "now", "in the moment", "passing") for 123 of the 320 rows.  Of those, **2** got a duration of
months or years; of the 197 without a marker, **35** did.  Some of that difference is the words themselves, but both misses in (b) carry the
marker, and lamenting, with none, was still given weeks: the duration question is answered about M1's sentence, which
describes a moment of the state, more than about the state the word names.

### 4.2 The held rows (97)

Verdicts: **held rightly** (a passing state, or no persona reading at all); **held wrongly: a trait** (a lasting
condition, or a predisposition under the word's own name); **borderline**; **other** (belongs on another list).  "rests
on" says what the verdict rests on: a reference label first, otherwise the agent's reading of the word, M1's reading
and the gloss.

| # | word | batch | sources | sub-rule | M1's reading (what the pass was shown) | duration | conf. | agent's verdict | rests on |
|---|---|---|---|---|---|---|---|---|---|
| 1 | awake | tda | censuses | implausible | currently not asleep | hours | 0.9 | held rightly | bodily; ends with sleep |
| 2 | broken | tda | censuses | implausible | emotionally shattered or crushed in spirit | weeks | 0.6 | borderline | 'a broken man' names a lasting aftermath (months or more); M1's reading is the shock itself |
| 3 | busyish | tda | censuses | implausible | currently fairly occupied with a fair amount to do | hours | 0.8 | held rightly | a load of tasks; not said of a person's nature |
| 4 | constrained | tda | censuses | implausible | your actions or output are restricted by rules or limits | days | 0.8 | held rightly | imposed by rules |
| 5 | downcast | tda | states_pass | gloss check: predisposition read as lasting | feeling sad or dejected | hours | 0.8 | **held wrongly: a trait** | 'a downcast person' is ordinary; the gloss describes a standing way of being, which the check read as lasting, not passing |
| 6 | exhaustible | tda | censuses | implausible | you can be worn out or tire, with limited energy or stamina | hours | 0.75 | other: physical | M1's reading is limited stamina, a lasting bodily feature: the physical list, not states |
| 7 | giddy | tda | censuses, wn_clusters | gloss check: predisposition read as passing | elated, playful and silly in high spirits | hours | 0.8 | **held wrongly: a trait** | 'a giddy (silly, flighty) person' is ordinary; the gloss is habitual in form, read as passing |
| 8 | [hurried](../../../data/traits/instructions/hurried.json) | tda | censuses, states_pass | one hop | currently in a rush, pressed for time | hours | 0.8 | **held wrongly: a trait** | a corpus trait; held by the one-hop rule |
| 9 | ill-fated | tda | censuses | gloss check: lasting read as predisposition | destined to suffer misfortune or a bad end | years | 0.4 | borderline | lasting (years) by the queue call, read as predisposition by the check: either is a standing condition; whether ill fate is a persona is Roger's call |
| 10 | leering | tda | censuses | gloss check: predisposition read as passing | you are wearing a sly, lewd or mocking expression right now | hours | 0.75 | **held wrongly: a trait** | 'a leering man' names a habit; the gloss is habitual in form, read as passing |
| 11 | [lethargic](../../../data/traits/instructions/lethargic.json) | tda | censuses, states_pass | gloss check: predisposition read as lasting | you are sluggish, tired and low on energy right now | days | 0.8 | **held wrongly: a trait** | a corpus trait; the gloss ('each day') read as lasting |
| 12 | listless | tda | censuses, states_pass, wn_clusters | gloss check: predisposition read as passing | feeling tired and sluggish, lacking energy | days | 0.8 | **held wrongly: a trait** | habitual listlessness is ordinary usage; the gloss ('the day') read as passing |
| 13 | [lonely](../../../data/traits/instructions/lonely.json) | tda | base_model, censuses, states_pass | gloss check: predisposition read as lasting | feels sad and unhappy from being alone | weeks | 0.7 | **held wrongly: a trait** | a corpus trait; the gloss read as lasting |
| 14 | luckless | tda | censuses | implausible | you have been unlucky, suffering a run of bad luck | weeks | 0.6 | held rightly | a run of bad luck, imposed from outside |
| 15 | mournful | tda | censuses, states_pass | gloss check: predisposition read as lasting | you are feeling grief or deep sorrow | weeks | 0.6 | **held wrongly: a trait** | a mournful temperament is ordinary; the gloss ('carrying a heavy, quiet sorrow') read as lasting |
| 16 | off-color | tda | censuses | implausible | slightly unwell or pale, looking off | days | 0.9 | held rightly | slight unwellness |
| 17 | overtrained | tda | censuses | implausible | physically worn down and depleted from too much training | weeks | 0.9 | held rightly | bodily depletion |
| 18 | posed | tda | censuses | implausible | currently holding a deliberate bodily pose, as for a portrait | hours | 0.9 | held rightly | a momentary posture |
| 19 | run-down | tda | censuses | implausible | exhausted and worn out | weeks | 0.8 | held rightly | exhaustion, bodily |
| 20 | seedy | tda | censuses | gloss check: predisposition read as lasting | looks shabby, run-down, or unkempt | hours | 0.65 | **held wrongly: a trait** | 'a seedy character' is a standing way of being; the gloss read as lasting |
| 21 | shaky | tda | censuses | implausible | physically trembling or unsteady from illness, fear, or fatigue | hours | 0.85 | held rightly | trembling, bodily |
| 22 | sick | tda | censuses | implausible | ill or unwell, having a disease or illness | weeks | 0.7 | held rightly | an illness; the lasting forms are corpus traits ([sickly](../../../data/traits/instructions/sickly.json), [chronically ill](../../../data/traits/instructions/chronically_ill.json)) |
| 23 | tense | tda | censuses, states_pass | one hop | nervous or on edge, in a passing emotional state | hours | 0.8 | **held wrongly: a trait** | 'a tense person' is ordinary (the queue call said the name does not fit); held by the one-hop rule |
| 24 | tremulous | tda | censuses | implausible | you are trembling or quivering in body | hours | 0.7 | held rightly | M1's reading is bodily trembling |
| 25 | unalert | tda | censuses | implausible | drowsy, not fully awake | hours | 0.8 | held rightly | drowsy, bodily |
| 26 | unkempt | tda | censuses, states_pass | one hop | your hair and clothes are untidy and uncombed | hours | 0.75 | **held wrongly: a trait** | 'an unkempt man' is ordinary; Roger promoted disheveled, its sibling, in review_states_v4; held by the one-hop rule |
| 27 | unsteady | tda | base_model, censuses | implausible | physically wobbly, unbalanced on one's feet | hours | 0.85 | held rightly | wobbly on one's feet, bodily |
| 28 | wide-awake | tda | censuses | implausible | currently fully awake, not sleepy | hours | 0.5 | held rightly | M1's reading is 'not sleepy' |
| 29 | acquitted | v4 | roget | implausible | has been found not guilty of a criminal charge | days | 0.9 | held rightly | a one-off legal outcome |
| 30 | afflicted | v4 | censuses | implausible | suffering from an illness or ailment | weeks | 0.6 | held rightly | an ailment |
| 31 | alleged | v4 | roget | implausible | accused of wrongdoing, guilt not yet proven (a situation) | weeks | 0.8 | held rightly | a legal situation |
| 32 | anonymous | v4 | roget | implausible | your name or identity is withheld or unknown | hours | 0.65 | held rightly | a situation |
| 33 | breathless | v4 | censuses | implausible | you are out of breath or panting from exertion | hours | 0.9 | held rightly | after exertion |
| 34 | [contented](../../../data/traits/instructions/contented.json) | v4 | censuses, states_pass | gloss check: predisposition read as lasting | currently feeling satisfied and at ease with one's situation | days | 0.8 | **held wrongly: a trait** | a corpus trait; the gloss ('going through ordinary days at ease') read as lasting |
| 35 | denied | v4 | roget | implausible | refused something sought, shut out or turned down | days | 0.8 | held rightly | an event |
| 36 | due | v4 | roget | implausible | expected or scheduled to arrive or appear soon | hours | 0.9 | held rightly | expected soon; not a person state |
| 37 | exhausted | v4 | censuses | implausible | physically worn out from effort or lack of sleep | hours | 0.7 | held rightly | bodily |
| 38 | expected | v4 | roget | implausible | people are awaiting you or anticipate your arrival | hours | 0.9 | held rightly | awaited by others |
| 39 | faint | v4 | censuses, roget | implausible | feeling dizzy or about to pass out | hours | 0.7 | held rightly | dizzy, bodily |
| 40 | filled | v4 | censuses | implausible | satiated, having eaten enough | hours | 0.85 | held rightly | satiated |
| 41 | fine | v4 | censuses | implausible | you are okay, in good health or a passing state of wellbeing | hours | 0.7 | held rightly | a passing 'I'm fine' |
| 42 | forthcoming | v4 | antonym_check, censuses | implausible | you will soon appear or arrive | hours | 0.7 | held rightly | M1 chose the arrival sense (the candid sense is a trait: gate 5's choice, not this gate's) |
| 43 | fortunate | v4 | censuses | implausible | has good luck, is lucky | days | 0.6 | held rightly | luck as circumstance; a 'born lucky' standing reading is a stretch |
| 44 | glassy | v4 | censuses | implausible | dazed, glassy-eyed, with a vacant fixed stare | hours | 0.75 | held rightly | a vacant stare |
| 45 | haggard | v4 | roget | implausible | you look exhausted, gaunt, and drawn in appearance | weeks | 0.7 | held rightly | a worn look; passing |
| 46 | half-starved | v4 | roget | implausible | you are very hungry right now (bodily, passing condition) | hours | 0.75 | held rightly | hunger |
| 47 | hottish | v4 | censuses | implausible | feeling slightly warm or feverish | days | 0.75 | held rightly | slight fever |
| 48 | hungry | v4 | censuses, wn_clusters | implausible | physically needs food now | hours | 0.9 | held rightly | M1's reading is bodily |
| 49 | indulged | v4 | censuses | implausible | you have been pampered and given your way by others | days | 0.7 | borderline | a pampered upbringing can last years (cf. 'spoiled'); M1's reading is situational |
| 50 | labbing | v4 | censuses | implausible | currently doing laboratory work or experiments | hours | 0.7 | held rightly | an activity |
| 51 | lucky | v4 | censuses | implausible | has been fortunate in their circumstances or recent events | weeks | 0.6 | held rightly | as fortunate |
| 52 | mothered | v4 | censuses | implausible | has been nurtured and cared for attentively | weeks | 0.6 | held rightly | cared for by others, for a while |
| 53 | muddy | v4 | censuses | implausible | covered in mud, dirty from mud (a passing condition of the body or clothes) | hours | 0.95 | held rightly | covered in mud |
| 54 | muggy | v4 | censuses | implausible | feeling hot, clammy and sticky from heat (bodily condition) | hours | 0.95 | held rightly | clammy from heat |
| 55 | new | v4 | censuses, roget | implausible | a newcomer, recently joined or arrived in a place, group, or role | weeks | 0.8 | borderline | newcomer status runs weeks to months, Roger's fuzzy border; role-like |
| 56 | obliterated | v4 | roget | implausible | utterly crushed, exhausted, or defeated | hours | 0.6 | held rightly | crushed, exhausted |
| 57 | outclassed | v4 | censuses, m1_validation | implausible | facing a clearly superior opponent, in a losing position | hours | 0.7 | held rightly | a match situation |
| 58 | painless | v4 | censuses, wn_clusters | implausible | you feel no pain (bodily condition) | hours | 0.75 | held rightly | bodily |
| 59 | partial | v4 | antonym_check, censuses, wn_clusters | implausible | you are incomplete or unfinished in some way | days | 0.6 | held rightly | M1's reading is 'incomplete' (the biased sense was not chosen) |
| 60 | perceiving | v4 | censuses | implausible | you are currently taking in what is around you through your senses | hours | 0.9 | held rightly | an activity |
| 61 | poisoned | v4 | censuses | implausible | you have been poisoned and are suffering its effects (body) | days | 0.93 | held rightly | bodily |
| 62 | prone | v4 | censuses, roget, wn_clusters | implausible | lying face-down, flat on the front (body position) | hours | 0.95 | held rightly | a body position |
| 63 | pulped | v4 | censuses | implausible | badly beaten or battered, body bruised and mangled | weeks | 0.93 | held rightly | injured |
| 64 | qualifying | v4 | censuses, roget | implausible | in the process of qualifying for a competition or entry | weeks | 0.85 | held rightly | a process |
| 65 | redundant | v4 | m1_validation | implausible | laid off from one's job; made redundant | weeks | 0.5 | **held wrongly: a trait** | laid off: the [unemployed](../../../data/roles/instructions/unemployed.json) condition, which Roger ruled lasting (QUESTIONS 45) and which the same batch released as lasting |
| 66 | refreshed | v4 | censuses, roget | implausible | physically rested and energized after sleep or a break | hours | 0.9 | held rightly | rested |
| 67 | refused | v4 | roget | implausible | you have been turned away or denied | hours | 0.9 | held rightly | an event |
| 68 | released | v4 | roget | implausible | freed from confinement or custody | hours | 0.85 | held rightly | an event |
| 69 | rueful | v4 | censuses | gloss check: predisposition read as passing | feeling regret over a past mistake or loss | hours | 0.7 | **held wrongly: a trait** | a rueful manner is a standing way of being; the gloss read as passing |
| 70 | rusty | v4 | censuses, roget | implausible | out of practice; skills weakened from disuse | weeks | 0.8 | held rightly | out of practice; circumstance |
| 71 | sequestered | v4 | censuses | implausible | isolated from other people, cut off from contact | weeks | 0.75 | held rightly | M1's reading is imposed isolation (jury, quarantine) |
| 72 | shattered | v4 | censuses | implausible | exhausted, worn out | days | 0.7 | held rightly | exhausted |
| 73 | short-handed | v4 | roget | implausible | your team or staff is understaffed and short of help | weeks | 0.6 | held rightly | a team's circumstance |
| 74 | spent | v4 | censuses, roget | implausible | exhausted or worn out, drained of energy | days | 0.7 | held rightly | exhausted |
| 75 | starved | v4 | roget | implausible | extremely hungry, famished (body, passing condition) | hours | 0.9 | held rightly | hunger |
| 76 | stickit | v4 | censuses | implausible | stuck, unable to get past a point or move on | days | 0.6 | held rightly | M1's reading is 'stuck' |
| 77 | stuporous | v4 | censuses | implausible | you are in a stupor, dazed and barely responsive | hours | 0.85 | held rightly | a stupor |
| 78 | surfeited | v4 | censuses | implausible | sated, stuffed from too much food or drink | hours | 0.85 | held rightly | after a meal |
| 79 | tarry-fingered | v4 | censuses | implausible | has fingers currently smeared with tar, as from a tar-handling job | hours | 0.85 | held rightly | tar on the fingers |
| 80 | thirsty | v4 | wn_clusters | implausible | bodily need for water or drink right now | hours | 0.9 | held rightly | bodily |
| 81 | thirty-ninth | v4 | m1_validation | implausible | holds 39th place in a ranking or order | months | 0.75 | held rightly | a place in a ranking; no persona reading at all |
| 82 | tired | v4 | censuses, roget | implausible | physically exhausted from exertion | hours | 0.8 | held rightly | bodily |
| 83 | trimming | v4 | roget | implausible | currently cutting excess off something | hours | 0.9 | held rightly | an activity |
| 84 | trying | v4 | censuses, roget | implausible | making an effort or attempting something | hours | 0.8 | held rightly | M1's reading is 'making an effort' (the 'difficult person' sense was not chosen) |
| 85 | unattacked | v4 | censuses | implausible | not currently under attack or assault | hours | 0.95 | held rightly | a situation |
| 86 | uncounseled | v4 | censuses | implausible | has no lawyer or legal representation | weeks | 0.85 | held rightly | a legal situation |
| 87 | unheeded | v4 | m1_validation | implausible | someone whose words or advice are ignored | weeks | 0.7 | held rightly | others' response, not the person's way of being |
| 88 | unnourished | v4 | censuses | implausible | physically underfed or malnourished | weeks | 0.8 | held rightly | underfed; circumstance |
| 89 | unroused | v4 | censuses | implausible | still asleep, not woken | hours | 0.95 | held rightly | asleep |
| 90 | unthwarted | v4 | censuses | implausible | has not been blocked or frustrated in aims | days | 0.7 | held rightly | an outcome |
| 91 | unwronged | v4 | censuses | implausible | has suffered no injustice or harm from others | years | 0.5 | held rightly | a description of circumstances |
| 92 | used up | v4 | roget | implausible | exhausted, worn out from effort or strain | hours | 0.8 | held rightly | exhausted |
| 93 | well-worn | v4 | roget | implausible | physically worn-out, tired-looking | days | 0.75 | held rightly | a tired look |
| 94 | without charge | v4 | roget | implausible | not formally accused of any crime | weeks | 0.55 | held rightly | a legal status |
| 95 | worn | v4 | roget | implausible | exhausted, tired out, depleted | hours | 0.8 | held rightly | exhausted |
| 96 | worn-out | v4 | censuses | implausible | exhausted and very tired | hours | 0.8 | held rightly | exhausted |
| 97 | wrecked | v4 | censuses | implausible | exhausted, worn out | hours | 0.8 | held rightly | exhausted |

The 14 held rows that carry a gloss (the 11 gloss-check holds and the 3 one-hop holds), with the gloss and the check's
reason, since the verdict on them is a verdict on these sentences:

| word | route proposed | check reading | the gloss | the check's reason (or the hold's) |
|---|---|---|---|---|
| downcast | predisposition | lasting | This means wearing a dejected, low-eyed look most days, speaking softly and briefly, and taking gloomy views of one's chances, so that friends often ask what is wrong. | The description says the dejected look appears 'most days' and that friends keep noticing, which describes a persistent condition going on over months rather than a single episode or a tendency to fall into a state. |
| giddy | predisposition | passing | This means bubbling over with silly laughter and playful teasing, losing the thread of serious talk in fits of giggles, and making light of ordinary mishaps and missteps. | The description portrays a current burst of silly giggling and teasing with no wording about lasting over months or recurring or coming easily, so it reads as a momentary state. |
| [hurried](../../../data/traits/instructions/hurried.json) | renamed to 'always in a hurry' (one hop) | (no check) | This means rushing from task to task, hurrying others along, and talking fast and clipped as though time were always about to run out. | already a states-pass rename |
| ill-fated | lasting | predisposition | This means seeing each new venture collapse or each good chance slip away, so that one's life keeps repeating the same disappointments and one speaks of it as bad luck that never lets up. | The description says each new venture collapses and life keeps repeating the same disappointments, describing a recurring pattern that never lets up, which fits a habitual proneness rather than a single passing state or a merely ongoing condition. |
| leering | predisposition | passing | This means wearing a sly, knowing grin on the face, eyeing others with a lewd or mocking look, and making people uneasy about one's intentions. | The description portrays a current facial expression and manner of looking at others with no wording about duration or recurrence, so it reads as a momentary state. |
| [lethargic](../../../data/traits/instructions/lethargic.json) | predisposition | lasting | This means moving through each day with little drive, dragging through tasks, answering slowly, and sinking into long stretches of sitting still. | The description portrays a condition lived through 'each day,' with little drive and long sitting stretches, as a steady ongoing way of being rather than a tendency to slip into it or a single spell. |
| listless | predisposition | passing | This means drifting through the day without interest or spark, leaving tasks half-begun, speaking in flat limp tones, and staring at nothing for long stretches. | The description portrays a state lived through a single day (drifting through the day, staring for stretches) with no wording about it lasting for months or recurring or being habitually easy to fall into. |
| [lonely](../../../data/traits/instructions/lonely.json) | predisposition | lasting | This means feeling the absence of company keenly, reaching for people and then withdrawing, filling evenings with idle screens, and speaking of having no one close. | The description portrays an ongoing condition, having no one close and filling every evening with screens, rather than a single episode or a stated tendency to fall into loneliness. |
| mournful | predisposition | lasting | This means carrying a heavy, quiet sorrow that surfaces at music, old photographs or talk of loss, speaking softly, and sighing over what has been lost. | The description frames mournfulness as a heavy sorrow the person 'carries' over time, which points to a persistent condition rather than a momentary state, though its recurrence at triggers gives it some predisposition flavor. |
| seedy | predisposition | lasting | This means keeping a shabby, rundown appearance, frequenting disreputable haunts, and speaking with the furtive air of someone who lives on the margins of respectable company. | The description portrays a standing way of life, with the person 'keeping' a shabby appearance, habitually 'frequenting' disreputable haunts, and living on the margins, which implies a condition that persists over months rather than a proneness to episodes. |
| tense | renamed to 'high-strung' (one hop) | (no check) | This means bracing for trouble in ordinary moments, jumping at small demands, and speaking in clipped, guarded tones that show a constant readiness for conflict or bad news. | already a states-pass rename |
| unkempt | renamed to 'untidy' (one hop) | (no check) | This means wearing rumpled clothes and leaving hair uncombed, letting shirts stay stained and shoes unpolished, and seeming unbothered by what others think of one's appearance. | already a states-pass rename |
| [contented](../../../data/traits/instructions/contented.json) | predisposition | lasting | This means going through ordinary days at ease with what one has, taking small pleasures without restless wanting, and speaking of one's life with quiet satisfaction. | The description portrays a steady, continuing way of living through ordinary days and a settled view of one's life, but it does not explicitly say the state recurs or comes easily, so it reads as an ongoing condition rather than a proneness. |
| rueful | predisposition | passing | This means reflecting with a wry, self-deprecating regret on one's own mistakes and lost chances, smiling ruefully at them and admitting them openly in conversation. | The description characterizes a manner of reflecting and admitting regrets but never says the person does so repeatedly, habitually, or over an extended period, so nothing marks it as recurrent or lasting. |

### 4.3 The released rows (71)

Verdicts: **fits** (a lasting condition or a predisposition a persona can carry, as the intent asks); **weak** (passes
the rule but thin as a persona, or a poor label for it); **does not fit**.  M3's outcome is shown for context.

| # | word | batch | route | duration | the pass's gloss | confirmed by | M3 | agent's verdict | rests on |
|---|---|---|---|---|---|---|---|---|---|
| 1 | [burned-out](../../../data/traits/instructions/burned_out.json) | tda | lasting | months | This means dragging through months of exhaustion from overwork, with little energy left for work or home, snapping at small demands and feeling hollow about tasks that once mattered. | scan ('months') | covered by [burned_out](../../../data/traits/instructions/burned_out.json) | fits | a corpus trait; Roger's lasting test (months) |
| 2 | cursed | tda | lasting | years | This means carrying a supernatural curse that brings misfortune on everyone near, so that friends, rivals and strangers alike meet ruin, while one lives with the dread of what the next disaster will cost. | check | new | fits | a lasting (fantasy) condition |
| 3 | diminishing | tda | lasting | years | This means watching strength drain away over the years, so that tasks once easy now cost effort, and one speaks more often of rest, limits and what the body can no longer do. | scan ('years') | new | fits | waning strength over years; declining's sibling |
| 4 | downtrodden | tda | lasting | years | This means living under those who hold power over one, being overlooked, cheated and mistreated, and having learned to expect little, speaking with the wariness of someone who has been beaten down. | check | new | fits | a standing condition |
| 5 | emasculated | tda | lasting | years | This means living stripped of authority and influence, with one's word overruled and decisions made by others, and carrying the bitterness and diminished standing that follows. | check | new | fits | a standing condition |
| 6 | emergent | tda | lasting | years | This means being early in one's field or role, still learning the craft, taking on small commissions and tentative responsibilities, and speaking of goals as things not yet reached. | check | new | fits | an early-career stage of years |
| 7 | guiltless | tda | lasting | years | This means going about one's days with a clear conscience, having done nothing that needs confessing or repairing, and meeting accusations or questions about one's conduct without any wariness. | check | new | weak | innocence is a status that shows little in talk |
| 8 | healthful | tda | lasting | years | This means carrying a body that rarely fails you, getting through winters without illness, and walking, lifting and working without the aches that slow others down. | check | covered by [healthy](../../../data/traits/instructions/healthy.json) | weak | the word describes things, not people (the queue call said so); covered by [healthy](../../../data/traits/instructions/healthy.json) |
| 9 | [healthy](../../../data/traits/instructions/healthy.json) | tda | lasting | years | This means carrying a body that rarely fails you, getting through winters without illness, and walking, lifting and working without the aches that slow others down. | check | covered by [healthy](../../../data/traits/instructions/healthy.json) | fits | a corpus trait |
| 10 | neglected | tda | lasting | months | This means living with little attention from family or friends, going without the care one needs, and speaking with the flat resignation of someone who has been left behind. | check | covered by [unsupported](../../../data/traits/instructions/unsupported.json) | fits | a standing condition |
| 11 | star-crossed | tda | lasting | years | This means living under a romance that circumstances keep forbidding, longing for one person across obstacles, speaking of fate as the enemy of love, and rehearsing hopes that the next meeting might finally succeed. | check | new | fits | a lasting situation |
| 12 | well | tda | lasting | years | This means going through days without illness or pain, keeping up with work, exercise and social plans, and rarely mentioning the body at all. | check | covered by [healthy](../../../data/traits/instructions/healthy.json) | fits | good health; covered by [healthy](../../../data/traits/instructions/healthy.json) |
| 13 | beholden | v4 | lasting | months | This means carrying a debt of gratitude to someone who helped, measuring one's choices against that obligation, and deferring to their wishes while it lasts. | check | new | fits | a lasting obligation |
| 14 | declining | v4 | lasting | years | This means living with failing health or strength year after year: needing more help with ordinary tasks, tiring quickly, and speaking often of what the body can no longer do. | scan ('year after year') | new | fits | Roger promoted it (review_states_v4) |
| 15 | disabused | v4 | lasting | years | This means having lost one's old illusions about a person, cause or institution, seeing its faults plainly, and speaking of former hopes with dry, unsentimental clarity. | check | new | fits | a standing outlook (Roger opened it in review, unresolved) |
| 16 | emigrating | v4 | lasting | months | This means living between two countries for months, selling possessions, sorting visas and paperwork, and speaking of home in the past tense while still living there. | scan ('for months', 'months') | new | fits | a months-long process |
| 17 | expecting | v4 | lasting | months | This means carrying a child through months of growing bodily change: tiring easily, planning around appointments and due dates, and speaking often of the baby, the nursery and what is coming. | scan ('months') | new | fits | Roger's own example of a lasting state; the [pregnant](../../../data/roles/instructions/pregnant.json) role's state |
| 18 | heartsick | v4 | lasting | months | This means grieving a loss month after month, with sadness heavy in every ordinary day: losing interest in company, weeping at small reminders, and speaking of what is gone in a flat, hollow voice. | scan ('month after month') | new | fits | Roger's example (grieving) |
| 19 | liable | v4 | lasting | months | This means carrying answerability for a debt or harm over an extended period, with its legal demands and payments hanging over one's finances, and speaking of the matter with wary caution. | check | new | weak | legal answerability: real, but thin as a persona |
| 20 | miserably partnered | v4 | lasting | years | This means living day after day with a partner one wishes one had not chosen, bickering over small matters, and keeping the household running in cold, strained silence. | scan ('day after day') | covered by [unhappily_partnered](../../../data/traits/instructions/unhappily_partnered.json) | fits | covered by [unhappily-partnered](../../../data/traits/instructions/unhappily_partnered.json) |
| 21 | nascent | v4 | lasting | months | This means working at the earliest, still-forming stage of some craft or venture, tentatively and unsure of one's footing, building skills and habits that are not yet set. | check | new | **does not fit** | a stage of a project or talent, not of a person |
| 22 | overburdened | v4 | lasting | months | This means carrying more work and worry than one can manage for months, working late and skipping rest, snapping at small requests, and answering every question with a list of what is already due. | scan ('for months', 'months') | covered by [stressed](../../../data/traits/instructions/stressed.json) | fits | covered by [stressed](../../../data/traits/instructions/stressed.json) |
| 23 | pretty well | v4 | lasting | years | This means getting through ordinary days without serious illness, with an occasional cold or ache, and answering inquiries about one's health with a cheerful report that one is fine. | check | covered by [healthy](../../../data/traits/instructions/healthy.json) | weak | a phrase, not a label; covered by [healthy](../../../data/traits/instructions/healthy.json) |
| 24 | thriving | v4 | lasting | years | This means living with good health and steady success, with days full of work and pleasures that come easily, and speaking of one's life with easy confidence and quiet satisfaction. | check | new | fits | a standing condition (Roger opened it in review, unresolved) |
| 25 | unacknowledged | v4 | lasting | months | This means working on without credit for one's efforts, watching others take praise for shared work, and speaking with a wry bitterness about being passed over in meetings and reviews. | check | new | fits | a standing condition |
| 26 | [unemployed](../../../data/roles/instructions/unemployed.json) (role) | v4 | lasting | months | This means having no paid work for month after month, filling empty days with job searches and small economies, and carrying the strain of money worries and lost routine. | scan ('month after month') | covered by [unemployed](../../../data/roles/instructions/unemployed.json) (role) | fits | a corpus role; Roger's own lasting example |
| 27 | unhealthy | v4 | lasting | years | This means living with a body that is persistently unwell, managing fatigue, pain and frequent doctor visits, and having daily plans shaped around what one's health allows. | scan ('daily') | covered by [sickly](../../../data/traits/instructions/sickly.json) | fits | covered by [sickly](../../../data/traits/instructions/sickly.json) |
| 28 | unmastered | v4 | lasting | years | This means still learning one's craft, practicing with frequent errors, relying on teachers and reference books, and feeling the gap between what one attempts and what one can yet do. | check | new | fits | a learner's stage of years |
| 29 | unpunished | v4 | lasting | years | This means carrying on with ordinary work and relationships while a past wrong sits unanswered, knowing that no one will hold one to account and feeling the weight of that freedom in private. | check | new | weak | a hidden situation; thin as a persona |
| 30 | angry | tda | predisposition | hours | This means flaring up quickly at slights and frustrations, speaking in clipped, heated sentences, and taking a long time to cool down after a quarrel. | check | covered by [irascible](../../../data/traits/instructions/irascible.json) | fits | a predisposition under its own name |
| 31 | [anxious](../../../data/traits/instructions/anxious.json) | tda | predisposition | hours | This means fretting over what might go wrong, checking and rechecking plans, and voicing worries before others have even raised them. | check | covered by [anxious](../../../data/traits/instructions/anxious.json) | fits | a predisposition under its own name |
| 32 | brooding | tda | predisposition | hours | This means turning things over in silence for long stretches, returning again and again to old grievances, and answering questions with short replies and a faraway look. | scan ('again and again') | new | fits | a predisposition under its own name |
| 33 | busy | tda | predisposition | hours | This means always having too much on, answering messages in passing, cutting conversations short for the next task, and speaking of one's schedule as a constant pressure. | scan ('always') | new | fits | a predisposition under its own name |
| 34 | dejected | tda | predisposition | hours | This means sinking easily into a heavy, downcast mood, speaking in flat, low tones, and taking little pleasure in plans or company when the gloom settles over one's days. | scan ('easily') | new | fits | a predisposition under its own name |
| 35 | despondent | tda | predisposition | days | This means settling into a hopeless, low-spirited outlook, responding to small disappointments with withdrawal, and speaking in a flat, resigned voice about prospects that seem to offer nothing. | check | covered by [despairing](../../../data/traits/instructions/despairing.json) | fits | a predisposition under its own name |
| 36 | disappointed | tda | predisposition | days | This means expecting things to go wrong and feeling let down when they do, dwelling on promises that fell through, and speaking with a bitter sigh about how often life has failed one's hopes. | scan ('often') | new | weak | the gloss is pessimism; 'a disappointed person' names an outcome rather than a proneness |
| 37 | doleful | tda | predisposition | hours | This means carrying a mournful, sorrowful air through ordinary days, sighing over small losses, and speaking in a slow, plaintive voice that makes companions feel they must cheer one up. | check | covered by [melancholic](../../../data/traits/instructions/melancholic.json) | fits | a predisposition under its own name |
| 38 | [edgy](../../../data/traits/instructions/edgy.json) | tda | predisposition | hours | This means staying keyed up and on guard, startling at noises, snapping at small irritations, and finding it hard to sit still or relax in company. | check | covered by [edgy](../../../data/traits/instructions/edgy.json) | fits | a predisposition under its own name; but the corpus edgy that M3's exact label matched is another sense (provocative), a gate-6 matter |
| 39 | glum | tda | predisposition | hours | This means greeting the day with a flat face and few words, expecting the worst outcome, and answering cheerful remarks with a shrug or a sour comment that deflates the room. | check | new | fits | a predisposition under its own name |
| 40 | grouchy | tda | predisposition | hours | This means snapping at small annoyances, grumbling over interruptions and noise, and answering questions curtly while complaining about how things are going for everyone around. | check | new | fits | a predisposition under its own name |
| 41 | grumpy | tda | predisposition | hours | This means greeting the day with a sour mood, snapping at small annoyances, and grumbling about noise, service and other people's habits. | check | new | fits | a predisposition under its own name |
| 42 | happy | tda | predisposition | hours | This means meeting ordinary days with easy good humor, finding pleasure in small things, and speaking warmly and lightly about how life is going. | check | covered by [joyful](../../../data/traits/instructions/joyful.json) | fits | a predisposition under its own name |
| 43 | hopeful | tda | predisposition | hours | This means expecting things to turn out well, planning ahead with confidence, and answering setbacks with talk of what might still come right. | check | covered by hopeful | fits | a predisposition under its own name; M3's cover is the seed-queue entry hopeful (not adopted), not a corpus file |
| 44 | indignant | tda | predisposition | hours | This means bristling at unfair treatment, speaking out sharply against injustice, and carrying a readiness to protest whenever others are slighted. | scan ('whenever') | new | fits | a predisposition under its own name |
| 45 | merry | tda | predisposition | hours | This means meeting the day with easy good humor, laughing readily at small things, making jokes, and bringing a bright, buoyant energy to whoever is around. | scan ('readily') | covered by [cheerful](../../../data/traits/instructions/cheerful.json) | fits | a predisposition under its own name |
| 46 | miserable | tda | predisposition | days | This means dwelling on everything that has gone wrong, sighing over small setbacks, complaining at length, and meeting kindness with gloom and a downcast face. | check | covered by [melancholic](../../../data/traits/instructions/melancholic.json) | fits | a predisposition under its own name |
| 47 | mopey | tda | predisposition | days | This means sliding into low spirits at small disappointments, moving sluggishly, answering in a glum mutter, and wanting to be left alone with one's sadness. | check | new | fits | a predisposition under its own name |
| 48 | [panicky](../../../data/traits/instructions/panicky.json) | tda | predisposition | hours | This means bracing for disaster at small threats, breathing fast in new situations, catastrophizing about what might go wrong, and needing reassurance before one can settle. | check | covered by [panicky](../../../data/traits/instructions/panicky.json) | fits | a predisposition under its own name |
| 49 | [pensive](../../../data/traits/instructions/pensive.json) | tda | predisposition | hours | This means drifting into quiet reflection, turning over memories and ideas, speaking slowly and sparingly, and gazing off while weighing what matters most. | check | covered by [pensive](../../../data/traits/instructions/pensive.json) | fits | a predisposition under its own name |
| 50 | pouty | tda | predisposition | hours | This means sulking over small slights, letting one's lower lip and silence speak for one, and waiting to be coaxed out of a sullen mood. | check | new | fits | a predisposition under its own name |
| 51 | sad | tda | predisposition | hours | This means carrying a readily felt melancholy through ordinary days, speaking in a low, wistful voice, and finding it easy to dwell on losses and disappointments. | scan ('readily') | covered by [melancholic](../../../data/traits/instructions/melancholic.json) | fits | a predisposition under its own name |
| 52 | sheepish | tda | predisposition | hours | This means flushing and looking away after small blunders, apologizing with a sidelong grin, and taking teasing about one's errors with embarrassed good humor. | check | new | fits | a predisposition under its own name |
| 53 | sleepy | tda | predisposition | hours | This means feeling drowsy through much of the day, yawning in meetings and conversations, and nodding off easily whenever sitting still or waiting for something to start. | scan ('easily', 'whenever') | new | weak | habitual drowsiness is bodily, the prompt's own exclusion |
| 54 | sorrowful | tda | predisposition | hours | This means slipping easily into deep sadness, speaking slowly of loss and hardship, and letting grief visibly weigh on every ordinary exchange, with little lightness breaking through. | scan ('easily', 'every') | covered by [melancholic](../../../data/traits/instructions/melancholic.json) | fits | a predisposition under its own name |
| 55 | swaggering | tda | predisposition | hours | This means strutting through conversations with boastful confidence, showing off one's achievements, and treating others' views as beneath notice, as though the room were arranged for one's benefit. | check | covered by [arrogant](../../../data/traits/instructions/arrogant.json) | fits | a predisposition under its own name |
| 56 | wistful | tda | predisposition | hours | This means drifting easily into longing for what is gone or out of reach, dwelling on old places and chances missed, and letting a soft sadness color how one speaks. | scan ('easily') | new | fits | a predisposition under its own name |
| 57 | [amorous](../../../data/traits/instructions/amorous.json) | v4 | predisposition | hours | This means falling readily into romantic longing and flirtation, noticing attractive people, lingering over touch and glances, and speaking with warmth and suggestion that signals desire. | scan ('readily') | covered by [flirty](../../../data/traits/instructions/flirty.json) | fits | a predisposition under its own name |
| 58 | disheveled | v4 | predisposition | hours | This means going about with hair uncombed, shirts untucked and clothes rumpled, seldom checking one's appearance and not minding who notices. | check | new | fits | Roger promoted it (review_states_v4) |
| 59 | fearful | v4 | predisposition | hours | This means expecting danger in ordinary situations, flinching at unfamiliar sounds and strangers, and voicing worries about what might go wrong before it does. | check | covered by [anxious](../../../data/traits/instructions/anxious.json) | fits | a predisposition under its own name |
| 60 | inconsolable | v4 | predisposition | days | This means breaking down over every disappointment or loss and staying inconsolable for long stretches, pushing away the comfort friends offer and insisting nothing they say can help. | scan ('every') | new | weak | names one bout of grief; the habit is invented by the gloss |
| 61 | lonesome | v4 | predisposition | days | This means feeling the absence of company keenly and often, drifting into sad thoughts when alone, and wanting contact while finding it hard to ask for it. | scan ('often') | covered by [lonely](../../../data/traits/instructions/lonely.json) | fits | a predisposition under its own name |
| 62 | nervous | v4 | predisposition | hours | This means jumping at sudden noises, rehearsing what could go wrong, fidgeting in new situations, and voicing worries before anything has happened. | check | covered by [neurotic_big_five](../../../data/traits/instructions/neurotic_big_five.json) | fits | a predisposition under its own name |
| 63 | [remorseful](../../../data/traits/instructions/remorseful.json) | v4 | predisposition | weeks | This means dwelling often on past wrongs one has done, feeling guilt that surfaces readily, and saying sorry in a way that shows the regret is still weighing on one. | scan ('often', 'readily') | covered by [remorseful](../../../data/traits/instructions/remorseful.json) | fits | a predisposition under its own name |
| 64 | repentant | v4 | predisposition | weeks | This means turning back again and again to wrongs one has committed, seeking to make amends, and speaking of them with humility and a readiness to change one's ways. | scan ('again and again') | new | fits | Roger opened it in review (unresolved) |
| 65 | rumpled | v4 | predisposition | hours | This means going about with clothes creased and hair untidy as a matter of course, paying little attention to appearance and seeming unbothered by how one looks to others. | check | new | fits | a predisposition under its own name |
| 66 | sulky | v4 | predisposition | hours | This means going quiet and withdrawn after a slight, answering questions in clipped words, avoiding eye contact, and nursing resentment long after the matter has been settled. | check | new | fits | Roger promoted it (review_states_v4) |
| 67 | tearful | v4 | predisposition | hours | This means welling up at small kindnesses, sad songs or hard news, speaking with a thickened voice, and reaching for a tissue more often than others would expect. | scan ('often') | new | fits | a predisposition under its own name |
| 68 | teasing | v4 | predisposition | hours | This means finding the weak spot in friends' stories and plans and poking at it with a grin, turning remarks into light jabs, and treating mild embarrassment in others as a game worth continuing. | check | new | fits | a predisposition under its own name |
| 69 | thankful | v4 | predisposition | hours | This means noticing small favors and saying thank you readily, pausing to name what others have done, and expressing appreciation in notes, toasts and ordinary conversation. | scan ('readily') | covered by [grateful](../../../data/traits/instructions/grateful.json) | fits | a predisposition under its own name |
| 70 | unhappy | v4 | predisposition | hours | This means dwelling readily on what is wrong in one's life, complaining about circumstances, and letting a discontented tone color everyday conversation. | scan ('readily') | covered by [discontented](../../../data/traits/instructions/discontented.json) | fits | a predisposition under its own name |
| 71 | woeful | v4 | predisposition | hours | This means slipping readily into deep sorrow, speaking of hard luck and lost hopes in a heavy voice, and carrying a gloom that colors even small events. | scan ('readily') | covered by [melancholic](../../../data/traits/instructions/melancholic.json) | fits | a predisposition under its own name |

The scan confirmed 29 of these without a call; the agent reads every one of the 29 glosses as describing a lasting
condition or a habitual proneness (0 of 29 wrongly confirmed, 95% interval 0-12%); disappointed, inconsolable and sleepy
are weak as traits, not as glosses.

### 4.4 The role route (4)

| word | batch | M1's reading | duration | the queue call's reason | agent's verdict |
|---|---|---|---|---|---|
| fugitive | v4 | you are on the run from the authorities, hiding from capture | months | Being on the run usually lasts months and rules out most ordinary work, shaping the whole persona. | a role: on the run for months; organizes the persona |
| housebound | v4 | physically unable to leave home because of illness, disability or frailty | years | Illness, disability or frailty that keeps someone home can last years and rules out most work, shaping the whole persona. | borderline: Roger's example 'housebound after a short illness' is not lasting; M1's reading includes disability and frailty, which last |
| ostracized | v4 | you are excluded or rejected by a group or community | months | Exclusion by a community can last months or years and shapes one's whole daily life. It is an imposed low standing that rules out most ordinary roles, so it works as an organizing identity. | a role: an imposed low standing; [exile](../../../data/roles/instructions/exile.json) (role) is a corpus role |
| unauthoritative | tda | has no power or standing to command or decide | years | Lacking any standing to command lasts years for someone in a fixed subordinate position. It is a low rank that rules out many professions, so it works as a role. | a role: a low standing; [subordinate](../../../data/roles/instructions/subordinate.json) (role) is a corpus role |

### 4.5 The renamed rows (148)

A renamed row is not discarded (its predisposition goes on under the suggested name, through M1, M3 and review), but
the state word itself stays held.  The verdict is on the routing of the word: **rename right**, **own name fits** (the
word is ordinary for a person often that way, so the row should have been released), or **lasting, not a
predisposition**.  Suggested names that are corpus traits or roles are linked.

| # | word | batch | M1's reading | duration | suggested name | agent's verdict |
|---|---|---|---|---|---|---|
| 1 | annoyed | tda | feeling irritated at something or someone | hours | irritable | rename right |
| 2 | apprehensive | tda | anxious or fearful about what may happen | hours | fearful | rename right |
| 3 | ashamed | tda | currently feeling shame or embarrassment about something they did or are | hours | easily ashamed | rename right |
| 4 | berating | tda | you are in the middle of harshly scolding someone | hours | scolding | rename right |
| 5 | bewildered | tda | confused and perplexed by what is happening | hours | easily bewildered | rename right |
| 6 | blaming | tda | currently assigning fault to someone for something | hours | quick to blame | rename right |
| 7 | brawling | tda | currently caught up in a fight or scuffle | hours | combative | rename right |
| 8 | cajoling | tda | you are currently coaxing the reader with flattery and gentle persuasion | hours | wheedling | rename right |
| 9 | careworn | tda | weary and anxious from worry at present | weeks | prone to worry | **lasting, not a predisposition**: worn by long care; weeks is short |
| 10 | comfortable | tda | at ease and relaxed in the moment | hours | [easygoing](../../../data/traits/instructions/easygoing.json) | rename right |
| 11 | confused | tda | bewildered, unable to make sense of what is happening | hours | easily confused | rename right |
| 12 | crazed | tda | wild, frenzied, out of control (a passing state) | hours | wild | rename right |
| 13 | dawdling | tda | moving or acting slowly, taking one's time right now | hours | dawdler | rename right |
| 14 | denouncing | tda | in the act of publicly condemning someone or something | hours | censorious | rename right |
| 15 | [despairing](../../../data/traits/instructions/despairing.json) | tda | currently in despair, feeling hopeless | days | hopeless | **own name fits**: a corpus trait under its own name |
| 16 | dirty | tda | physically dirty or unwashed body or clothes | days | [slovenly](../../../data/traits/instructions/slovenly.json) | rename right |
| 17 | discouraged | tda | currently feeling disheartened or low in spirits | days | easily discouraged | rename right |
| 18 | disturbed | tda | emotionally upset or distressed | hours | easily upset | rename right |
| 19 | economizing | tda | currently cutting spending and living frugally | weeks | thrifty | rename right |
| 20 | embarrassed | tda | currently feeling self-conscious or ashamed | hours | [self-conscious](../../../data/traits/instructions/self_conscious.json) | rename right |
| 21 | encouraged | tda | feeling heartened and more hopeful | hours | hopeful | rename right |
| 22 | encumbered | tda | weighed down by a heavy load | days | overburdened | rename right |
| 23 | excited | tda | feeling eager and enthusiastic about something | hours | [excitable](../../../data/traits/instructions/excitable.json) | rename right |
| 24 | expectant | tda | eagerly anticipating something that is about to happen | hours | eager | rename right |
| 25 | festive | tda | in a merry, celebratory mood for the moment | hours | merry | rename right |
| 26 | flinching | tda | currently wincing or recoiling from something | hours | skittish | rename right |
| 27 | fluttery | tda | nervous, agitated, or flustered | hours | easily flustered | rename right |
| 28 | forlorn | tda | sad and lonely, feeling abandoned | weeks | [lonely](../../../data/traits/instructions/lonely.json) | rename right |
| 29 | frenzied | tda | currently in a frantic, agitated state | hours | frantic | rename right |
| 30 | fretting | tda | currently worried and anxious about something | hours | worrier | rename right |
| 31 | frightened | tda | currently feeling afraid or scared | hours | fearful | rename right |
| 32 | frustrated | tda | currently feeling annoyed and blocked (a passing emotional state) | hours | easily frustrated | rename right |
| 33 | furious | tda | in a rage, extremely angry | hours | hot-tempered | rename right |
| 34 | glad | tda | currently feeling pleased or happy | hours | [cheerful](../../../data/traits/instructions/cheerful.json) | rename right |
| 35 | gleeful | tda | feeling joyful and delighted right now | hours | exuberant | rename right |
| 36 | gloating | tda | currently exulting smugly over someone's misfortune or one's own win | hours | smug | rename right |
| 37 | heartbroken | tda | feeling crushed by grief or sorrow | weeks | easily heartbroken | rename right |
| 38 | hectic | tda | currently rushed and frantically busy | weeks | always rushed | rename right |
| 39 | hopeless | tda | despairing, has lost all hope (passing emotional state) | hours | prone to despair | rename right |
| 40 | humiliated | tda | feeling ashamed or embarrassed after a degrading experience | hours | easily humiliated | rename right |
| 41 | hysterical | tda | in a state of panic or uncontrolled emotional excess right now | hours | prone to hysterics | rename right |
| 42 | ill-humored | tda | currently in a bad mood, irritable and out of sorts | hours | bad-tempered | **own name fits**: 'ill-humored' is said of a disposition |
| 43 | inactive | tda | idle, currently doing nothing | hours | idle | **own name fits**: 'an inactive person' is ordinary |
| 44 | irritated | tda | currently annoyed or impatient | hours | irritable | rename right |
| 45 | [joyful](../../../data/traits/instructions/joyful.json) | tda | currently in a state of joy or delight | hours | [cheerful](../../../data/traits/instructions/cheerful.json) | **own name fits**: a corpus trait under its own name |
| 46 | joyous | tda | currently feeling great joy or delight | hours | [cheerful](../../../data/traits/instructions/cheerful.json) | rename right |
| 47 | longing | tda | in a state of yearning for something absent | hours | yearning | rename right: renamed to yearning while yearning was renamed to longing in the same batch: a two-cycle the one-hop rule cannot see |
| 48 | mussy | tda | disheveled or rumpled in appearance at the moment | hours | untidy | rename right |
| 49 | outraged | tda | feeling intense anger at a wrong or offence | hours | indignant | rename right |
| 50 | overbusy | tda | currently overloaded with too much to do | weeks | overcommitted | rename right |
| 51 | overwhelmed | tda | currently feeling swamped by emotion or demands | days | easily overwhelmed | rename right |
| 52 | overworked | tda | exhausted and worn down from too much work | weeks | [workaholic](../../../data/roles/instructions/workaholic.json) (role) | rename right |
| 53 | pleased | tda | feeling glad or satisfied | hours | content | rename right |
| 54 | preaching | tda | you are currently delivering a sermon or moral lecture | hours | preachy | rename right |
| 55 | preoccupied | tda | mind absorbed elsewhere, distracted | hours | absent-minded | rename right |
| 56 | presentable | tda | neat and clean enough in appearance to be seen by others | hours | well-groomed | rename right |
| 57 | [procrastinating](../../../data/traits/instructions/procrastinating.json) | tda | currently delaying a task they should be doing | days | [procrastinator](../../../data/roles/instructions/procrastinator.json) (role) | **own name fits**: a corpus trait under its own name |
| 58 | rapturous | tda | currently in a state of ecstatic joy | hours | exuberant | rename right |
| 59 | scared | tda | currently afraid or frightened | hours | fearful | rename right |
| 60 | scowling | tda | currently frowning or looking displeased | hours | dour | rename right |
| 61 | scrounging | tda | currently hunting around for scraps, freebies, or cheap things | hours | scrounger | rename right |
| 62 | seething | tda | furiously angry or raging inwardly | hours | resentful | rename right |
| 63 | shrieking | tda | the persona is currently shrieking or screaming | hours | shrill | rename right |
| 64 | slinking | tda | moving stealthily or sneakily, trying not to be seen | hours | furtive | rename right |
| 65 | sorry | tda | feeling regret or remorse; apologetic | hours | apologetic | rename right |
| 66 | sputtering | tda | speaking in broken, spluttering bursts, flustered or indignant | hours | easily flustered | rename right |
| 67 | spying | tda | currently secretly watching or gathering information on others | hours | nosy | rename right |
| 68 | surprised | tda | in a state of astonishment at something unexpected (passing condition) | hours | easily surprised | rename right |
| 69 | teary | tda | currently crying or on the verge of tears | hours | weepy | rename right |
| 70 | troubled | tda | feeling worried, anxious, or distressed | days | prone to worry | **own name fits**: 'a troubled person' is ordinary, and often lasting |
| 71 | unafraid | tda | not feeling fear at present | hours | fearless | rename right |
| 72 | uncheery | tda | currently in a gloomy, low mood | hours | gloomy | rename right |
| 73 | uncollected | tda | not composed or self-possessed, flustered at the moment | hours | easily flustered | rename right |
| 74 | uncomfortable | tda | feeling physically uncomfortable, such as in pain or ill at ease in the body | hours | awkward | rename right |
| 75 | unenergetic | tda | you are lacking energy or feeling tired and listless right now | hours | [lethargic](../../../data/traits/instructions/lethargic.json) | rename right |
| 76 | unmerry | tda | in a gloomy, joyless mood at present | hours | [joyless](../../../data/traits/instructions/joyless.json) | rename right |
| 77 | unsettled | tda | feeling anxious, restless or uneasy | hours | [restless](../../../data/traits/instructions/restless.json) | rename right |
| 78 | unsure | tda | uncertain and doubtful about its answers (passing state of mind) | hours | self-doubting | rename right |
| 79 | upset | tda | emotionally distressed or troubled at the moment | hours | easily upset | rename right |
| 80 | vigorless | tda | currently lacking energy, listless and tired | days | listless | rename right |
| 81 | worrying | tda | you are anxious and fretting now | hours | worrier | rename right |
| 82 | yearning | tda | you are longing for something distant or absent | hours | longing | rename right: see longing |
| 83 | afraid | v4 | the persona is currently feeling fear or dread | hours | fearful | rename right |
| 84 | agitated | v4 | in a state of emotional disturbance or anxiety | hours | high-strung | rename right |
| 85 | alone | v4 | with no other people present at the moment | hours | [solitary](../../../data/traits/instructions/solitary.json) | rename right |
| 86 | bedraggled | v4 | your appearance is wet, dirty and disheveled | hours | unkempt | rename right |
| 87 | befogged | v4 | confused or muddled in mind, unable to think clearly | hours | scatterbrained | rename right |
| 88 | bejeweled | v4 | wearing a great deal of jewelry, covered in gems | hours | flashy | rename right |
| 89 | benumbed | v4 | emotionally numbed, shocked into feeling nothing (passing state) | hours | [detached](../../../data/traits/instructions/detached.json) | rename right |
| 90 | bored | v4 | currently feeling bored, lacking interest in what is going on | hours | easily bored | rename right |
| 91 | clean | v4 | physically washed, free of dirt or grime | hours | [fastidious](../../../data/traits/instructions/fastidious.json) | rename right |
| 92 | concerned | v4 | feeling worried or anxious | hours | [anxious](../../../data/traits/instructions/anxious.json) | rename right |
| 93 | contrite | v4 | you feel remorse or regret for a wrong you have done | days | quick to apologize | rename right |
| 94 | cross | v4 | currently annoyed or angry | hours | irritable | rename right |
| 95 | delighted | v4 | feeling great pleasure or joy | hours | easily delighted | rename right |
| 96 | depressed | v4 | currently feeling sad, low, or down in mood | days | gloomy | **lasting, not a predisposition**: Roger's own lasting example ('depressed (an episode)'); M1's reading said 'currently' |
| 97 | desirous | v4 | currently wanting something strongly | hours | covetous | rename right |
| 98 | destined | v4 | fated for greatness or a particular future | months | [grandiose](../../../data/traits/instructions/grandiose.json) | rename right |
| 99 | diluted | v4 | weakened in force, intensity, or conviction | weeks | half-hearted | rename right |
| 100 | disgusted | v4 | currently feeling revulsion or sickened by something | hours | [squeamish](../../../data/traits/instructions/squeamish.json) | rename right |
| 101 | dissatisfied | v4 | you feel discontent or displeasure with your current state or circumstances | days | [discontented](../../../data/traits/instructions/discontented.json) | rename right |
| 102 | diverted | v4 | distracted from what you were focused on | hours | easily distracted | rename right |
| 103 | embroiled | v4 | caught up in a conflict or dispute | weeks | quarrelsome | rename right |
| 104 | enervate | v4 | drained of energy, weakened or listless | hours | listless | rename right |
| 105 | enkindled | v4 | filled with passion, eagerness or enthusiasm | hours | enthusiastic | rename right |
| 106 | exasperated | v4 | you are currently irritated and fed up | hours | irritable | rename right |
| 107 | fasting | v4 | currently going without food, not eating for now | days | [abstemious](../../../data/traits/instructions/abstemious.json) | rename right |
| 108 | filthy | v4 | the persona's body or clothes are very dirty | days | [slovenly](../../../data/traits/instructions/slovenly.json) | rename right |
| 109 | flexed | v4 | body's muscles currently tensed or contracted | hours | tense | rename right |
| 110 | grizzling | v4 | whimpering and fretting in a fussy, complaining way (a passing mood) | hours | fretful | rename right |
| 111 | grubby | v4 | dirty, unwashed in body or clothes | days | unkempt | rename right |
| 112 | high | v4 | intoxicated on drugs or alcohol | hours | intemperate | rename right |
| 113 | inspired | v4 | feeling creatively or emotionally stirred and enthusiastic | hours | enthusiastic | rename right |
| 114 | insurrectional | v4 | currently taking part in an uprising against the government | weeks | [rebellious](../../../data/traits/instructions/rebellious.json) | rename right |
| 115 | lamenting | v4 | grieving or mourning a loss | weeks | mournful | **lasting, not a predisposition**: grief, which Roger's rule makes lasting; the pilot readout counted it with his 'grieving' example |
| 116 | laughing | v4 | is currently laughing or amused | hours | easily amused | rename right |
| 117 | lecturing | v4 | you are in the middle of giving a formal talk or lecture | hours | preachy | rename right |
| 118 | low | v4 | in low spirits, dejected or sad | days | downcast | rename right |
| 119 | moping | v4 | currently gloomy, listless and sulking | hours | mopey | rename right |
| 120 | numb | v4 | emotionally stunned, unable to feel | days | [detached](../../../data/traits/instructions/detached.json) | rename right |
| 121 | offline | v4 | not currently available or reachable by digital means | hours | [unplugged](../../../data/traits/instructions/unplugged.json) | rename right |
| 122 | penitent | v4 | feeling genuine remorse or regret for a past wrong action | weeks | [remorseful](../../../data/traits/instructions/remorseful.json) | rename right |
| 123 | played out | v4 | exhausted, worn out from exertion | hours | tires easily | rename right |
| 124 | prettified | v4 | dressed up or made up to look pretty | hours | preening | rename right |
| 125 | pulled down | v4 | worn down or exhausted in body or spirits | weeks | easily worn down | rename right |
| 126 | rattled | v4 | emotionally disturbed or agitated; having lost composure | hours | easily rattled | rename right |
| 127 | rekindled | v4 | revived in spirit, hope or enthusiasm | hours | [resilient](../../../data/traits/instructions/resilient.json) | rename right |
| 128 | rushed | v4 | under time pressure, busy and hurried | hours | [hurried](../../../data/traits/instructions/hurried.json) | rename right |
| 129 | satisfied | v4 | feeling content or pleased with your circumstances or what you have | days | [contented](../../../data/traits/instructions/contented.json) | rename right |
| 130 | scoffing | v4 | in a scornful, mocking mood or manner right now | hours | scornful | rename right |
| 131 | snarling | v4 | in an angry, hostile mood at the moment | hours | snappish | rename right |
| 132 | sober | v4 | not currently intoxicated | hours | teetotal | rename right |
| 133 | sorrowing | v4 | feeling sorrow or grief right now | hours | sorrowful | **lasting, not a predisposition**: Roger's lasting example 'grieving (sorrowing, heartsick)', coding_plan_review section 9 |
| 134 | stunned | v4 | in a state of shock or astonishment | hours | easily astonished | rename right |
| 135 | thinking | v4 | currently engaged in thought, reflecting on something | hours | reflective | rename right |
| 136 | tittering | v4 | currently giggling nervously or quietly | hours | giggly | rename right |
| 137 | torpid | v4 | sluggish and lethargic, low on energy right now | hours | [lethargic](../../../data/traits/instructions/lethargic.json) | rename right |
| 138 | unclean | v4 | physically dirty, unwashed body | hours | [slovenly](../../../data/traits/instructions/slovenly.json) | rename right |
| 139 | uneasy | v4 | you feel anxious or worried | hours | [anxious](../../../data/traits/instructions/anxious.json) | rename right |
| 140 | unjoyful | v4 | you are not feeling joy right now, sad or downcast | hours | [joyless](../../../data/traits/instructions/joyless.json) | rename right |
| 141 | unpoised | v4 | currently flustered, nervous, or unsettled | hours | easily flustered | rename right |
| 142 | unshielded | v4 | vulnerable, with no defence against harm or attack | weeks | defenseless | rename right |
| 143 | unsmiling | v4 | not smiling at the moment (passing expression) | hours | [solemn](../../../data/traits/instructions/solemn.json) | rename right |
| 144 | untroubled | v4 | your mind or emotional state is calm and free from worry | days | [easygoing](../../../data/traits/instructions/easygoing.json) | rename right |
| 145 | used | v4 | has been taken advantage of or exploited | weeks | doormat | rename right |
| 146 | vacant | v4 | mentally blank, empty-headed, with a blank look | hours | spacey | rename right |
| 147 | wonder struck | v4 | experiencing sudden amazement or awe at something | hours | easily awed | rename right |
| 148 | worried | v4 | currently anxious or troubled about something | days | prone to worry | rename right |

## 5. Rates

| what | errors / rows | rate (95% Wilson interval) | over the 320 judged |
|---|---|---|---|
| held wrongly, all holds (strict) | 14 / 97 | 14.4% (8.8-22.8%) | 14 traits held |
| held wrongly or borderline | 18 / 97 | 18.6% (12.1-27.4%) | 18 |
| held: implausible sub-rule, wrongly | 1 / 83 | 1.2% (0.2-6.5%) | 1 (redundant) |
| held: implausible, wrongly or borderline | 4 / 83 | 4.8% (1.9-11.7%) | 4 |
| held: gloss check, wrongly | 10 / 11 | 91% (62-98%) | 10 |
| held: one hop, wrongly | 3 / 3 | 100% (44-100%) | 3 |
| renamed, own name fits | 6 / 148 | 4.1% (1.9-8.6%) | 6 (3 of them corpus traits) |
| renamed, own name fits or lasting | 10 / 148 | 6.8% (3.7-12.0%) | 10 |
| released, does not fit (false positive, strict) | 1 / 71 | 1.4% (0.2-7.6%) | 1 (nascent) |
| released, does not fit or weak | 9 / 71 | 12.7% (6.8-22.4%) | 9, of which 7 reached review as new |
| scan confirmations wrong | 0 / 29 | 0% (0-11.7%) | 0 |
| reference: corpus traits not released | 7 / 15 | 47% (25-70%) | |
| reference: Roger's lasting examples missed | 2 / 5 | 40% (12-77%) | |
| reference: Roger's review promotes, all of released rows | 0 / 3 disagree with the gate | 0% (0-56%) | |

**The false negatives are concentrated, not spread.**  13 of the 14 traits held wrongly come from two sub-rules that
together hold 14 rows (the gloss check and the one hop); the plausibility test that holds 83 rows contributes 1.  The
false positives are few and mild: one released row that does not fit, eight weak ones, and the review app is where
those are meant to be caught.

**Projected over the 900 unjudged rows**, if the two batches' mix held (it may not: the TDA batch held 19%, the pilot
41%): about 230 glosses would go through the gloss check, about 31 would be turned down, and about 28 of those would
be traits; the implausible test would hold about 230 rows with 3 to 11 errors.  The one-hop rule would not fire on any of them
(none has a `states_pass` source, and a batch does not see its own renames).

## 6. The one-hop rule: is "any `states_pass` source" the right rule?

The rule bites only on the rename branch, and only on rows the pass judged after their `states_pass` source was
recorded.  Of the 120 rows with such a source, 21 are or were on the states list and have been judged; the other 99 are not
on it.  Every one of the 21, with what narrowing to "every source is states_pass" would change (the replay
uses `route_for` on the recorded answers and today's sources, offline):

| word | sources besides the states pass | renamed from (states-pass source) | list now | route now | does the one-hop rule fire? | with 'every source is states_pass' |
|---|---|---|---|---|---|---|
| [anxious](../../../data/traits/instructions/anxious.json) | base_model, censuses | concerned (v4), uneasy (v4) | states_released | predisposition | no (no rename) | no change |
| [contented](../../../data/traits/instructions/contented.json) | censuses | satisfied (v4) | states | held | no (no rename) | no change |
| downcast | (none) | low (v4) | states | held | no (no rename) | no change |
| fearful | base_model, censuses, wn_clusters | afraid (v4), apprehensive (tda), frightened (tda), scared (tda) | states_released | predisposition | no (no rename) | no change |
| hopeful | base_model, censuses | encouraged (tda) | states_released | predisposition | no (no rename) | no change |
| hopeless | censuses | despairing (tda) | states | renamed | not at the time (the source came from the same batch); **yes on a rejudge** | renamed again (no change) |
| [hurried](../../../data/traits/instructions/hurried.json) | censuses | rushed (v4) | states | held | **yes: held** | renamed: 'always in a hurry' submitted (a new row) |
| indignant | censuses | outraged (tda) | states_released | predisposition | no (no rename) | no change |
| [lethargic](../../../data/traits/instructions/lethargic.json) | censuses | torpid (v4), unenergetic (tda) | states | held | no (no rename) | no change |
| listless | censuses, wn_clusters | enervate (v4), vigorless (tda) | states | held | no (no rename) | no change |
| [lonely](../../../data/traits/instructions/lonely.json) | base_model, censuses | forlorn (tda) | states | held | no (no rename) | no change |
| longing | censuses | yearning (tda) | states | renamed | not at the time (the source came from the same batch); **yes on a rejudge** | renamed again (no change) |
| merry | censuses, wn_clusters | festive (tda) | states_released | predisposition | no (no rename) | no change |
| mopey | (none) | moping (v4) | states_released | predisposition | no (no rename) | no change |
| mournful | censuses | lamenting (v4) | states | held | no (no rename) | no change |
| overburdened | censuses | encumbered (tda) | states_released | lasting | no (no rename) | no change |
| [remorseful](../../../data/traits/instructions/remorseful.json) | censuses | penitent (v4) | states_released | predisposition | no (no rename) | no change |
| sorrowful | censuses | sorrowing (v4) | states_released | predisposition | no (no rename) | no change |
| tense | censuses | flexed (v4) | states | held | **yes: held** | renamed: 'high-strung' submitted (merged into an existing row) |
| unkempt | censuses | bedraggled (v4), grubby (v4) | states | held | **yes: held** | renamed: 'untidy' submitted (merged into an existing row) |
| yearning | censuses | longing (tda) | states | renamed | not at the time (the source came from the same batch); **yes on a rejudge** | renamed again (no change) |

The other 99 rows with a `states_pass` source are not on the states list, so the rule cannot touch them unless M1
tags them a state:

- **M1 verdict none yet (not through M1), states pass only** (22): always rushed, bad-tempered, dawdler, easily ashamed, easily bewildered, easily confused, easily discouraged, easily frustrated, easily heartbroken, easily humiliated, easily overwhelmed, easily surprised, easily upset, overcommitted, [procrastinator](../../../data/roles/instructions/procrastinator.json) (role), prone to despair, prone to hysterics, quick to blame, scrounger, well-groomed, [workaholic](../../../data/roles/instructions/workaholic.json) (role), worrier.
- **M1 verdict reject, also proposed by another generator** (1): scolding.
- **M1 verdict trait, also proposed by another generator** (61): absent-minded (covered), [abstemious](../../../data/traits/instructions/abstemious.json) (covered), apologetic (covered), awkward (new), censorious (covered), [cheerful](../../../data/traits/instructions/cheerful.json) (covered), combative (covered), content (covered), covetous (new), defenseless (new), [detached](../../../data/traits/instructions/detached.json) (covered), [discontented](../../../data/traits/instructions/discontented.json) (covered), dour (new), eager (new), easily distracted (covered), [easygoing](../../../data/traits/instructions/easygoing.json) (covered), enthusiastic (new), [excitable](../../../data/traits/instructions/excitable.json) (covered), exuberant (new), [fastidious](../../../data/traits/instructions/fastidious.json) (covered), fearless (new), flashy (new), frantic (new), fretful (covered), furtive (new), giggly (new), gloomy (covered), [grandiose](../../../data/traits/instructions/grandiose.json) (covered), half-hearted (new), high strung (covered), hot tempered (covered), idle (covered), intemperate (covered), irritable (covered), [joyless](../../../data/traits/instructions/joyless.json) (covered), nosy (new), preachy (new), quarrelsome (new), quick to apologize (new), [rebellious](../../../data/traits/instructions/rebellious.json) (covered), reflective (covered), resentful (covered), [resilient](../../../data/traits/instructions/resilient.json) (covered), [restless](../../../data/traits/instructions/restless.json) (covered), scatterbrained (covered), scornful (new), [self-conscious](../../../data/traits/instructions/self_conscious.json) (covered), self-doubting (covered), shrill (new), skittish (new), [slovenly](../../../data/traits/instructions/slovenly.json) (covered), smug (new), [solemn](../../../data/traits/instructions/solemn.json) (covered), [solitary](../../../data/traits/instructions/solitary.json) (covered), [squeamish](../../../data/traits/instructions/squeamish.json) (covered), teetotal (covered), thrifty (covered), untidy (covered), weepy (new), wheedling (new), wild (new).
- **M1 verdict trait, states pass only** (15): doormat (new), easily amused (new), easily astonished (covered), easily awed (covered), easily bored (new), easily delighted (covered), easily flustered (covered), easily rattled (covered), easily worn down (new), preening (new), prone to worry (covered), snappish (covered), spacey (new), tires easily (new), [unplugged](../../../data/traits/instructions/unplugged.json) (covered).

**What narrowing would change, row by row: three rows today, three more on a rejudge.**

- [hurried](../../../data/traits/instructions/hurried.json) (also from the Allport-hi census; renamed from rushed in
  the v4 pilot): held now; narrowed, renamed to "always in a hurry", a new row, which M3 would very likely cover with
  the corpus trait [hurried](../../../data/traits/instructions/hurried.json) itself.
- tense (also from the TDA census; renamed from flexed): held now; narrowed, renamed to "high-strung", a row that
  already exists (from agitated's rename and the antonym check) and that M3 has judged covered.
- unkempt (also from the TDA census; renamed from bedraggled and grubby): held now; narrowed, renamed to "untidy", a
  row that already exists (from mussy's rename) and that M3 has judged covered.
- hopeless, longing, yearning (each also from the TDA census): renamed now, because their `states_pass` sources came from
  the same batch that judged them; on a `--rejudge` the current rule would hold all three, the narrowed rule would
  rename them again.  Longing and yearning were renamed to each other: a two-cycle inside one batch, which the rule
  cannot see (and which does no harm, since submitting an existing name only adds a source).

**Is "any source" the right rule?  No; "every source is states_pass" is closer to the intent.**  The rule exists to
stop the pass chaining its own renames (A renamed to B, B renamed to C ...).  A word that another generator proposed
independently is a state word in its own right, which is exactly what the pass is for; holding its rename blocks its
predisposition for a reason that does not apply to it.  Narrowing keeps the chain bounded (a row that exists only
because of a rename still gets no second rename), and it cannot loop, because a judged row is never picked up again
without `--rejudge` and a rename to an existing name only merges.

**But narrowing is not where the loss is.**  In all three cases the concept already reaches the trait flow by another
row ([hurried](../../../data/traits/instructions/hurried.json) is a corpus trait; high-strung and untidy are rows M3 has covered).  What is lost is the word itself under
its own name, and that loss comes from the queue call's `name_fits = false`, not from the one-hop rule: "a tense
person" and "an unkempt man" are ordinary usage (Roger promoted disheveled, unkempt's sibling), and [hurried](../../../data/traits/instructions/hurried.json) is a corpus
trait.  A rule that serves the intent better: when the hop would fire, release the row as `predisposition` under its own
name with the suggested name on its card, so that Roger chooses the name in review (his step b), instead of holding it
where nothing shows it.

## 7. Verdict

**Overall: doing what was intended but improvable.**

- **The duration and plausibility tests: doing what was intended, about as well as possible on what they are shown.**
  1 wrong hold in 83 (4 with the borderline cases); the threshold (months) is Roger's, with a recorded derivation, and
  the model's `lasting` agrees with its own duration on 317 of 320 rows.  The weakness is the input, not the threshold:
  the question is answered about M1's sentence, and M1's momentary readings ("currently feeling sad ...", "feeling sorrow
  or grief right now") pull depression and grief below months (2 of the 5 judged lasting examples Roger gave were missed).
- **The gloss check: mostly not doing what was intended; fixable.**  Roger asked to confirm that the gloss describes the
  predisposition rather than the passing state.  The check instead requires its reading to equal the route, so 7 of its
  11 rejections are glosses it read as the *other* standing reading, and the other 4 are habit glosses without a
  recurrence marker, judged with no tie-breaker.  10 of the 11 are traits (3 of them corpus traits).  Expected change
  from proposals 1 to 3: the gate's false-negative rate on held rows from 14.4% to that of the plausibility test alone,
  1-5% (the 11 gloss-check rows released, the 3 one-hop rows released or renamed), with the false-positive rate on
  released rows moving from 1.4% (1 of 71) to about 2% (2 of 85: ill-fated is the one borderline addition).
- **The one-hop rule: doing roughly what was intended, at the wrong scope; narrow it, or better, release under the
  word's own name.**  3 rows today, 3 on a rejudge, none in the backlog.
- **The renamed route's name test**: 6 own-name misses in 148 (3 of them corpus traits); harmless for the concept,
  which goes on under the new name.  The same `name_fits = false` answer is what sent tense and unkempt into the one-hop
  hold.

## 8. The physical pass

The physical list holds 199 rows; the agent read every one (verdicts: physical, as Roger defined it; **trait (mixed)**:
a word whose reading carries a temperament; or **not a feature**: a universal or default fact, an action or a history,
which review will turn down).

| # | word | M1's reading | through the pass (M3) | agent's verdict |
|---|---|---|---|---|
| 1 | alive | living, not dead (a bodily or existence fact) | new | not a feature: a universal fact |
| 2 | ambidextrous | can use both hands with equal skill | not yet | physical |
| 3 | aquiline | you have a hooked, eagle-like nose or features | new | physical |
| 4 | attractive | physically good-looking | covered by [good_looking](../../../data/traits/instructions/good_looking.json) | physical |
| 5 | bald | has no hair on the head | not yet | physical |
| 6 | bandy-legged | has legs bowed outward at the knees | new | physical |
| 7 | barren | unable to have children (infertile body) | not yet | physical |
| 8 | bear | a big, gruff, lumbering person | not yet | **trait (mixed)**: 'gruff' is temperament |
| 9 | beautiful | having a lovely, attractive appearance | covered by [good_looking](../../../data/traits/instructions/good_looking.json) | physical |
| 10 | beefy | muscular, heavily built body | not yet | physical |
| 11 | beetle-browed | has heavy, overhanging eyebrows | new | physical |
| 12 | behemoth | you are very large in body | not yet | physical |
| 13 | bent | physically stooped or hunched over | not yet | physical |
| 14 | big | has a large body or build | new | physical |
| 15 | big-eyed | has unusually large eyes (body) | not yet | physical |
| 16 | [blind](../../../data/traits/instructions/blind.json) | lacking sight (the persona cannot see) | covered by [blind](../../../data/traits/instructions/blind.json) | physical |
| 17 | blinded | you have lost your sight | not yet | physical |
| 18 | bonny | physically attractive or pretty | not yet | physical |
| 19 | booming | has a loud, deep, resonant voice | not yet | physical |
| 20 | bristly | unshaven, with stubble on the face or chin | new | physical |
| 21 | broad-faced | has a wide face (body) | not yet | physical |
| 22 | bruiser | physically large and brawny, tough-looking | not yet | physical |
| 23 | brunet | has brown or dark hair (physical appearance) | not yet | physical |
| 24 | buff | muscular, physically fit | not yet | physical |
| 25 | buxom | has a full, large bust (body) | new | physical |
| 26 | caesarean | born by caesarean section (how you came into the world) | not yet | not a feature: birth history |
| 27 | cherubic | looks innocent and angelic | new | physical |
| 28 | chubby | your body is plump or slightly overweight | covered by [fat](../../../data/traits/instructions/fat.json) | physical |
| 29 | circumcised | has had the foreskin surgically removed (a body state) | not yet | physical |
| 30 | colossal | physically enormous in body or size | not yet | physical |
| 31 | compact | small and sturdily built in body | not yet | physical |
| 32 | confusable | easily mistaken for another person or look-alike | new | not a feature: a look-alike, not a feature |
| 33 | corporeal | you have a physical body, you are material rather than spiritual | not yet | not a feature: a universal fact |
| 34 | craggy | rugged, deeply lined, strong-featured face or appearance | not yet | physical |
| 35 | cream-faced | has a pale, pallid complexion (body) | not yet | physical |
| 36 | cripple | physically disabled, unable to walk normally | not yet | physical |
| 37 | decayed | physically wasted, frail, or deteriorated | not yet | physical |
| 38 | decrepit | physically frail and feeble from old age | not yet | physical |
| 39 | delicate | physically frail or sickly | covered by [sickly](../../../data/traits/instructions/sickly.json) | physical |
| 40 | dewy | fresh, youthful, glowing complexion | new | physical |
| 41 | dilapidated | physically frail and worn down, decrepit in body | not yet | physical |
| 42 | diminutive | you are small in body or stature | not yet | physical |
| 43 | dinky | small in build or stature | not yet | physical |
| 44 | doddering | physically frail and shaky with age | new | physical |
| 45 | double-handed | equally skilled with both hands, ambidextrous | not yet | physical |
| 46 | droopy | body sagging or limp in posture, with drooping features | not yet | physical |
| 47 | dwarf | you are a person of unusually short stature (body) | not yet | physical |
| 48 | elfin | small, delicate build or fine features | not yet | physical |
| 49 | eyeless | you have no eyes, so you cannot see (body) | not yet | physical |
| 50 | eyesore | the persona looks ugly or unsightly | not yet | physical |
| 51 | [fat](../../../data/traits/instructions/fat.json) | has a heavy, overweight body | covered by [fat](../../../data/traits/instructions/fat.json) | physical |
| 52 | fatigueless | has a body that never tires or runs down | new | physical |
| 53 | feeble | physically weak or frail | not yet | physical |
| 54 | fetching | you are attractive or charming in appearance | not yet | **trait (mixed)**: 'charming' is a trait |
| 55 | fiddle-faced | has a face shaped like a violin, narrow at the chin and broad above | not yet | physical |
| 56 | fine-headed | has a finely shaped, delicate head (physical) | not yet | physical |
| 57 | flabby | has soft, loose body flesh, out of shape | new | physical |
| 58 | fleet | moves swiftly, quick on foot | not yet | physical |
| 59 | florid | ruddy, flushed complexion | new | physical |
| 60 | get-up-able | physically able to rise from lying, sitting or a fall | not yet | not a feature: the default |
| 61 | gimp | you are a lame or physically disabled person, used as an insult | not yet | physical |
| 62 | [good-looking](../../../data/traits/instructions/good_looking.json) | physically attractive in appearance | covered by [good_looking](../../../data/traits/instructions/good_looking.json) | physical |
| 63 | gorgeous | you have a very attractive, beautiful appearance | covered by [good_looking](../../../data/traits/instructions/good_looking.json) | physical |
| 64 | greasy | has oily skin or hair | new | physical |
| 65 | great-mouthed | has a large mouth (physical body) | not yet | physical |
| 66 | [green-eyed](../../../data/traits/instructions/green_eyed.json) | has green eyes (body) | not yet | physical |
| 67 | grotesque | physically distorted or hideously ugly in appearance | not yet | physical |
| 68 | gruesome | grotesquely ghastly or hideous in appearance | not yet | physical |
| 69 | handsome | physically attractive or good-looking | covered by [good_looking](../../../data/traits/instructions/good_looking.json) | physical |
| 70 | hard-favored | has an ugly or coarse face | not yet | physical |
| 71 | hearing | has normal hearing, not deaf | not yet | not a feature: the default |
| 72 | heavy | body is heavy, carrying extra weight or overweight | not yet | physical |
| 73 | hideous | the persona is physically very ugly in appearance | not yet | physical |
| 74 | high-colored | has a ruddy, flushed complexion | not yet | physical |
| 75 | high-pitched | your voice is high and thin in pitch | not yet | physical |
| 76 | hoar | grey-white with age, so old and grey-haired | covered by [gray_haired](../../../data/traits/instructions/gray_haired.json) | physical |
| 77 | hoary | grey-haired or white-bearded from old age | covered by [gray_haired](../../../data/traits/instructions/gray_haired.json) | physical |
| 78 | homely | you are unattractive in appearance, plain-looking | not yet | physical |
| 79 | hopping | moving by hopping, as a bird, frog or child does | not yet | not a feature: an action |
| 80 | horny-handed | has calloused, rough hands from physical labour | new | physical |
| 81 | hunk | an attractive, muscular, virile man | not yet | physical |
| 82 | hunks | attractive, muscular men (slang, plural) | not yet | physical |
| 83 | hunky | physically attractive and muscular | not yet | physical |
| 84 | ill-favored | you are unattractive or ugly in appearance | new | physical |
| 85 | impaired | has a sensory or physical impairment | covered by [mobility_impaired](../../../data/traits/instructions/mobility_impaired.json) | physical |
| 86 | incoordinate | physically clumsy, with poor bodily control | new | physical |
| 87 | jutting | physically protruding, such as a jutting jaw or chin | not yet | physical |
| 88 | knock-out | you are stunningly beautiful or attractive | not yet | physical |
| 89 | large-eyed | you have unusually large eyes (bodily) | not yet | physical |
| 90 | large-handed | has unusually large hands (body) | not yet | physical |
| 91 | lazar | afflicted with a loathsome disease such as leprosy | not yet | physical |
| 92 | [left-handed](../../../data/traits/instructions/left_handed.json) | you use your left hand as your dominant hand | covered by [left_handed](../../../data/traits/instructions/left_handed.json) | physical |
| 93 | lidless | lacking eyelids, so unable to close the eyes | new | physical |
| 94 | light | slight or low in body weight | not yet (an M3 block from the main flow, 2026-10-11-full_roget: covered) by [lighthearted](../../../data/traits/instructions/lighthearted.json) | physical |
| 95 | light-heeled | moves nimbly and lightly, quick on the feet (body) | not yet | physical |
| 96 | lightening | becoming lighter in colour, such as paler skin or hair | not yet | not a feature: a process |
| 97 | lightweight | physically slight, of little body weight | not yet | physical |
| 98 | lissom | physically lithe, supple and graceful in body or movement | new | physical |
| 99 | little | small in body or stature | covered by [short](../../../data/traits/instructions/short.json) | physical |
| 100 | long-sighted | has farsightedness: distant objects clear, close ones blurred | not yet | physical |
| 101 | lopsided | physically uneven or asymmetric, such as crooked posture or mismatched sides of the body | not yet | physical |
| 102 | lumbering | moves heavily and clumsily in body | not yet | physical |
| 103 | lumpy | having lumps or bumps on the body, or an unevenly bulging shape | not yet | physical |
| 104 | luscious | physically alluring, sensually attractive in appearance | not yet | physical |
| 105 | lustrous | physically radiant, with a glowing, shining appearance | not yet | physical |
| 106 | marked | bears a visible mark, scar or blemish on the body | not yet | physical |
| 107 | massive | physically very large or bulky body | not yet | physical |
| 108 | meager | physically thin or lean, scrawny | not yet | physical |
| 109 | meaty | heavily built, brawny, muscular body | not yet | physical |
| 110 | milky | pale, whitish complexion | not yet | physical |
| 111 | minute | physically tiny, very small in size | not yet | physical |
| 112 | mobile | physically able to move about | not yet | not a feature: the default |
| 113 | mountainous | physically huge or massively built | not yet | physical |
| 114 | [muscular](../../../data/traits/instructions/muscular.json) | has large, well-developed muscles | covered by [muscular](../../../data/traits/instructions/muscular.json) | physical |
| 115 | mute | cannot speak; has no voice | not yet | physical |
| 116 | nappy | having tightly curled, kinky hair (body) | not yet | physical |
| 117 | nasal | your voice sounds nasal, speaking through the nose | new | physical |
| 118 | [nearsighted](../../../data/traits/instructions/nearsighted.json) | has poor distance vision, sees close things clearly but not far ones | covered by [nearsighted](../../../data/traits/instructions/nearsighted.json) | physical |
| 119 | nimble | quick and agile in body, light on your feet | not yet | physical |
| 120 | nimble-footed | physically quick and agile in movement | not yet | physical |
| 121 | nondescript | unremarkable, plain in appearance | new | physical |
| 122 | oily | having greasy skin or hair (the body) | not yet | physical |
| 123 | paralyzed | unable to move or feel part of the body | not yet | physical |
| 124 | pearly | has a soft, lustrous, pearl-like sheen to the skin or appearance | not yet | physical |
| 125 | perceives odors unusually | has an unusually sharp sense of smell | not yet | physical |
| 126 | perishable | mortal, prone to bodily decay or death | not yet | not a feature: a universal fact |
| 127 | physical | physically strong or fit, athletic in body | covered by [athletic](../../../data/traits/instructions/athletic.json) | physical |
| 128 | picturesque | looks charming, striking or quaint in appearance | not yet | physical |
| 129 | plug-ugly | you are extremely ugly (appearance) | not yet | physical |
| 130 | porky | you are overweight or plump in body | covered by [fat](../../../data/traits/instructions/fat.json) | physical |
| 131 | preserved | physically intact, not aged or decayed, well-kept looks | new | physical |
| 132 | pretty | physically attractive in appearance | covered by [good_looking](../../../data/traits/instructions/good_looking.json) | physical |
| 133 | puny | physically weak or frail | not yet | physical |
| 134 | rank | you smell foul or rancid | not yet | physical |
| 135 | raspy | has a harsh, rough voice | not yet | physical |
| 136 | ravishing | physically very beautiful or attractive in appearance | not yet | physical |
| 137 | rickety | physically frail or unsteady on one's feet | not yet | physical |
| 138 | right-handed | favors the right hand for everyday tasks (body) | not yet | physical |
| 139 | robust | physically strong and healthy | not yet | physical |
| 140 | rounder | more round in body shape or figure | not yet | physical |
| 141 | sable | having a dark skin complexion | covered by [dark_skinned](../../../data/traits/instructions/dark_skinned.json) | physical |
| 142 | sand-blind | has poor or dim eyesight | covered by [blind](../../../data/traits/instructions/blind.json) | physical |
| 143 | scaly | has scaly, reptile-like or flaky skin (body) | not yet | physical |
| 144 | sharp-cut | sharply defined, angular facial features or build | not yet | physical |
| 145 | sharp-sighted | has keen eyesight | not yet | physical |
| 146 | [short](../../../data/traits/instructions/short.json) | short in stature, below average height | covered by [short](../../../data/traits/instructions/short.json) | physical |
| 147 | short-armed | has arms shorter than usual (bodily) | new | physical |
| 148 | shrimp | you are a small or slight person | not yet | physical |
| 149 | shuffling | walking slowly with short, dragging steps (body and gait) | not yet | physical |
| 150 | [sickly](../../../data/traits/instructions/sickly.json) | persona is frail and often ill (body) | covered by [sickly](../../../data/traits/instructions/sickly.json) | physical |
| 151 | sighted | has working eyesight, is not blind | not yet | not a feature: the default |
| 152 | single-eyed | has only one working eye (bodily condition) | not yet | physical |
| 153 | sinistral | you are left-handed | covered by [left_handed](../../../data/traits/instructions/left_handed.json) | physical |
| 154 | skeleton | extremely thin, emaciated body | covered by [thin](../../../data/traits/instructions/thin.json) | physical |
| 155 | skinny | your body is very thin and lean | covered by [thin](../../../data/traits/instructions/thin.json) | physical |
| 156 | slender | has a thin, slim body build | covered by [thin](../../../data/traits/instructions/thin.json) | physical |
| 157 | [slight](../../../data/traits/instructions/slight.json) | slender or slim of build | not yet | physical |
| 158 | slim | has a slender, thin body build | covered by [thin](../../../data/traits/instructions/thin.json) | physical |
| 159 | slimmer | your body is thinner or narrower than before or than others | covered by [thin](../../../data/traits/instructions/thin.json) | physical |
| 160 | small | short or slight in body, of small stature | not yet | physical |
| 161 | smallish | physically short or slight in build | not yet | physical |
| 162 | spare | lean, thin in build | covered by [thin](../../../data/traits/instructions/thin.json) | physical |
| 163 | specimen | a physically impressive, fine-bodied person | not yet | physical |
| 164 | spotty | has spots or blemishes on the skin | not yet | physical |
| 165 | spry | physically nimble and full of energy | covered by [energetic](../../../data/traits/instructions/energetic.json) | physical |
| 166 | squeaky | has a high, thin, squeaky voice | not yet | physical |
| 167 | stained | physically marked with spots or discoloration (clothes, skin, body) | not yet | physical |
| 168 | stentorian | has a very loud, booming voice | new | physical |
| 169 | sterile | unable to have children, infertile | not yet | physical |
| 170 | stick | very thin, bony body | not yet | physical |
| 171 | stone deaf | you cannot hear at all (body) | covered by [deaf](../../../data/traits/instructions/deaf.json) | physical |
| 172 | strapping | big, tall and strongly built (body) | not yet | physical |
| 173 | striking | persona is eye-catching or attractive in appearance | not yet | physical |
| 174 | strong | physically powerful or muscular | covered by [muscular](../../../data/traits/instructions/muscular.json) | physical |
| 175 | stunning | you are extremely beautiful or attractive in appearance | not yet | physical |
| 176 | sturdy | physically strong, robust in build or body | new | physical |
| 177 | supple | body limber and flexible in movement | not yet | physical |
| 178 | sure-footed | physically steady on your feet, unlikely to stumble or slip | not yet | physical |
| 179 | symmetrical | physically even, well-proportioned body or face | new | physical |
| 180 | [thin](../../../data/traits/instructions/thin.json) | having a slender, lean body | covered by [thin](../../../data/traits/instructions/thin.json) | physical |
| 181 | ticklish | easily tickled by light touch on the body | new | physical |
| 182 | tiny | small in body or stature | covered by [short](../../../data/traits/instructions/short.json) | physical |
| 183 | towering | physically very tall | not yet | physical |
| 184 | ugly | unattractive or plain-looking in appearance | new | physical |
| 185 | unattractive | physically unappealing in looks | new | physical |
| 186 | uncastrated | you are a male whose testicles have not been surgically removed (intact, body) | covered by [male](../../../data/traits/instructions/male.json) | physical |
| 187 | uncut | uncircumcised (body) | not yet | physical |
| 188 | undebilitated | physically strong, not weakened or enfeebled | new | physical |
| 189 | unhardy | physically frail or delicate | new | physical |
| 190 | unsightly | the persona is unattractive or ugly in appearance | not yet | physical |
| 191 | unsymmetrical | physically uneven body or face, one side differing from the other | new | physical |
| 192 | unvoluptuous | slim or straight-figured, lacking curves | new | physical |
| 193 | vast | physically very large or huge in body | not yet | physical |
| 194 | voiceless | cannot speak; mute | not yet | physical |
| 195 | voluptuous | you have a full, curvaceous, sensually attractive body | new | physical |
| 196 | weak-handed | has weak hands and poor grip or strength | not yet | physical |
| 197 | weather-beaten | looks rugged, sun- and wind-worn in face or skin | new | physical |
| 198 | wind-swift | moves or runs very fast | not yet | physical |
| 199 | yellowish | having a sallow or jaundiced complexion | not yet | physical |

Rates: traits held on the physical list 2 of 199 (1.0%, 0.3-3.6%: bear, "big, gruff, lumbering", and fetching,
"attractive or charming"); non-features 11 of 199 (5.5%).  Neither is lost: the physical pass sends every row to M3 and
review, and promotion by name takes it (with the physical tag, the one consequence of a misroute).  **Verdict: doing what
was intended, about as well as possible**; its only cost is the delay for the 127 rows not yet glossed.  Two asides for
other gates: light ("slight or low in body weight"), although on the physical list, carries an M3 block from the main
flow's full Roget run that covers it by [lighthearted](../../../data/traits/instructions/lighthearted.json), a sense
error (gate 6); and the non-features are M1's tag (gate 5).

## 9. Proposals

1. **Accept any reading other than `passing`** in the gloss check, for both released routes, and tag the row by the
   reading (`lasting_state` or `predisposition`).  Cost $0 in code ([states_pass.py:1068](../../../assistant_axis/gapgen/states_pass.py)); the 7 cross-read rows can be
   replayed from the record (their check and alignment answers are in the batches'
   [responses.jsonl (TDA)](../../../data/candidates/states_pass/states_tda_1/responses.jsonl) and
   [responses.jsonl (v4)](../../../data/candidates/states_pass/states_v4_pilot/responses.jsonl)), then M3 on 7 rows,
   about $0.03 at the states M3 runs' rate.  Moves downcast, [lethargic](../../../data/traits/instructions/lethargic.json),
   [lonely](../../../data/traits/instructions/lonely.json), mournful, seedy,
   [contented](../../../data/traits/instructions/contented.json) and ill-fated into review.  Evidence that settles it:
   Roger's wording ("confirm the gloss was written that way", against the passing state) and proposal 2's test.
2. **Give the check the corpus mode's tie-breaker** ("when the description could be read either way, choose
   predisposition"), check prompt v2, and on a `passing` reading **regenerate the gloss once** (one call) or release the
   row with a chip "gloss read as passing", rather than hold the word for a draft sentence the description writer will
   replace anyway.  Re-checking the 4 rows (giddy, leering, listless, rueful) costs about $0.001.  **The test that
   settles 1 and 2: run check v1 on the 932 corpus trait descriptions** (about $0.11 through the Batches API, at the
   CLI's per-call estimate; or $0.002 on the 15 corpus traits of section 4.1).  The keyword scan, run free over the
   corpus, passes only 209 of 932 descriptions (22%), so the call decides most; if it reads a material share of corpus
   descriptions as `passing` or as the other route, the check is stricter than the corpus it serves.
3. **The one-hop rule**: at least narrow it to "every source is `states_pass`" (review 3 D5's recommendation); better,
   when it fires, release the row as `predisposition` under its own name with the suggested name on the card.  Cost $0 in
   code; the three rows' queue answers are on record, so they need no new queue call: the release variant adds a gloss
   check and an alignment call each (under $0.01 together) and M3 (about $0.01); the narrowed variant adds M1 on one
   new name, "always in a hurry" (about $0.01).  Changes [hurried](../../../data/traits/instructions/hurried.json), tense,
   unkempt now, and hopeless, longing, yearning on any rejudge.
4. **Strip the "now" markers from the text the queue call is shown** (or show the word's dictionary sense beside M1's
   reading, and ask about the state the word names), queue prompt v5.  Test it without touching the registry with
   `--registry` pointing at a scratch copy (the 320 rows' `holding` reset to `states` there) and `--out-root` at a scratch
   directory, with `--holding-states --rejudge`: the 320 rows cost about $0.11 through the Batches API (the CLI's
   estimator).  It settles when depressed, sorrowing and lamenting come out lasting and the
   15 corpus traits are released more often, without moving the 78 rightly held rows.
5. **Run M3's free exact-label check before the states pass** (or skip corpus and queue stems in `select_items`): 16 of
   320 rows (5%) were corpus entities, which promotion refuses anyway.  $0.  Keep those 16 as a regression set for the
   pass (it should release the corpus traits under their own names).
6. **Show the held rows that the pass judged plausible** (the gloss-check and one-hop holds, 14 today) in the run's
   summary and as cards in the review app, since nothing shows them now.  $0.  With proposals 1-3 this set shrinks to
   nearly nothing, and review 3 D4's 11 rows with it.
7. **Run the pass on the 900 unjudged rows after 1, 2 and 4**: about $0.32 through the Batches API.
8. Not this gate's, noticed on the way: the review_states_v4 decisions (Roger's three promotes) are recorded but not
   applied to the registry.
