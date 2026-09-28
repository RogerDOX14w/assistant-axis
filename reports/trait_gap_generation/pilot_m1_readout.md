# M1 pilot readout: trait-hood filter (2026-09-28)

Pilot of plan [coding_plan_platform.md](./coding_plan_platform.md) §10 (M1).  Batch
[`filter/m1_pilot/`](../../data/candidates/filter/m1_pilot/) ([summary.json](../../data/candidates/filter/m1_pilot/summary.json),
[results.jsonl](../../data/candidates/filter/m1_pilot/results.jsonl),
[responses.jsonl](../../data/candidates/filter/m1_pilot/responses.jsonl),
[usage.json](../../data/candidates/filter/m1_pilot/usage.json)), run on a 20% stratified sample (seed 0) of
[m1_validation.jsonl](../../data/candidates/validation/m1_validation.jsonl).  Rubric v1, Haiku 4.5 classifier
at temperature 0, 25 rows per call, Sonnet 4.6 second opinions, definition probe on.  The validation
run did not touch the registry (there is no registry yet), so no snapshot applies.

Command:
`uv run python data_analysis/gap_generation/traithood_filter.py --batch-id m1_pilot --validation-file data/candidates/validation/m1_validation.jsonl --sample-frac 0.2 --sample-seed 0 --budget-usd 1.5`

## Headline

| | value |
|---|---|
| rows | 367 (85 hard-rejected by the Zipf floor at no cost, 282 sent to Haiku) |
| parse rate | 282/282 classifier rows, 32/32 second-opinion rows, 35/35 probe rows (first pass 100%) |
| cost | $0.3125 ($0.2357 Haiku, 14 calls; $0.0768 Sonnet, 2 calls) |
| cost per candidate | $0.00085 (per LLM-classified row $0.0011) |
| yield per dollar | 131 useful rows (verdict `trait`, no polysemy flag) / $0.3125 = 419 per dollar; on the random-adjective stratum alone about 19 per $0.17, i.e. about 110 per dollar (cost apportioned by row count) |
| polysemy rate | 0.51 of classified rows (0.15 on existing labels, 0.81 on random adjectives) |
| second opinion | 32 rows (10% random + confidence < 0.6 + prior disagreement), 4 disagreements (12.5%) |
| gloss length | median 19 words (corpus median 24); 138 of 160 glosses inside 18-43 |

The first pilot attempt parsed 93.3% (19 of 282 rows failed): the row validator demanded a gloss, a
region and a sense rank on `tagged` rows, while the rubric's own tagged examples show none, so Haiku
copied them.  The validator now accepts those rows (region taken from the tag where one is implied);
reparsing the recorded responses offline gave 312/312 and the rerun above gave 100%.  The failed attempt
is kept as [`filter/m1_pilot_v0_parse_bug/`](../../data/candidates/filter/m1_pilot_v0_parse_bug/) ($0.34).
Its raw verdicts double as a small stability check: on the same 282 rows the two runs agree on 269
verdicts (95.4%) and on 267 of the `trait_sense_rank >= 2` flags (94.7%).

## Verdict and tag fractions per stratum

Fractions are of all rows in the stratum, hard rejects included.  Polysemy is over LLM-classified rows.

| stratum | n | hard reject | trait | tagged | reject | tags (fraction of rows) | polysemy |
|---|---|---|---|---|---|---|---|
| existing trait labels | 132 | 7 | 0.856 | 0.061 | 0.083 | state 0.083, too_rare 0.053, demographic 0.045, relational_only 0.030, role_person 0.015 | 0.15 |
| September rejects | 6 | 0 | 0.667 | 0.167 | 0.167 | relational_only 0.167, transient_only 0.167 | 0.50 |
| physical queue candidates | 6 | 0 | 0.333 | 0.667 | 0 | physical 0.50, state 0.167, transient_only 0.167 | 0.83 |
| not_adopted queue labels | 23 | 4 | 0.348 | 0.087 | 0.565 | relational_only 0.261, too_rare 0.174, state 0.087, others 0.043 each | 0.74 |
| random OEWN adjectives | 200 | 74 | 0.135 | 0.145 | 0.720 | too_rare 0.455, relational_only 0.285, physical 0.090, evaluative_only 0.030, others 0.020-0.025 | 0.81 |

Against the §8 acceptance targets (which apply to the full run, task 10; read as indications here):

* **Existing labels >= 95% trait: not met (85.6%).**  Of the 19 misses, 7 are the Zipf hard floor
  (clannish, collectivistic, confabulatory, distractible, techno-hierophantic, tunnel-visioned,
  unschooled), 8 are corpus memberships the rubric correctly calls non-traits by its own rules (gay, new
  money, many siblings, financially secure, unhappily-partnered, renter, cat-person as `demographic` /
  `role_person`; southern hemisphere as `relational_only`), 3 are real misses (concrete, interdisciplinary,
  rhetorical as `relational_only`), and 1 is a state word given `tagged` instead of `trait` (despairing).
  Among the 125 LLM-classified existing labels, 113 (90.4%) are `trait`.  Over the whole corpus, 34 of
  659 labels (5.2%) fall below Zipf 2.0, so the floor as specified caps this stratum at 94.8% before the
  classifier is asked anything.
* **Six rejects, >= 4 flagged polysemy or rank >= 2: not met (3 of 6).**  Flagged: disciplinary
  (rank 3), economic (rank 3, `relational_only`), empowered (rank 3, `transient_only`).  Not flagged:
  engaging, balanced, emotive (all rank 1, trait).  empowered carries `transient_only` and economic
  `relational_only`, as required.  (In the 10-row smoke run balanced came back rank 2 and empowered rank 1:
  these words sit on the boundary and flip between runs.)
* **Random adjectives <= 15% trait: met (13.5%, 27 of 200; 10 of the 27 carry the polysemy flag).**
  Trait verdicts: appreciative, assured, black and white\*, brazen-faced, comic, complacent, conceited,
  consistent, dissenting, exacting, frenetic, haphazard, hysterical\*, jingoistic, lackadaisical,
  preoccupied, presumptive\*, put-up, reassuring, ritual\*, serpentine\*, stiff-necked, sultry\*, tinny\*,
  unmotivated, untruthful, whitewashed\* (\* = polysemy flag).
* **Physical candidates `tagged: physical`: 3 of 6** (good-looking, plain-looking, red-headed);
  pregnant came back `transient_only`, short-sighted `trait` (the metaphorical sense), sickly `trait` +
  `state`.

## Other findings

* **The definition probe conflates "is a known word" with "is a trait".**  17 of 35 probe-band words came
  back `known: false`, including tuberous, saute, repayable and psychogenic, with reasons such as "a real
  English word ... but it's a botanical term, not a personality trait".  Those rows were turned into
  `reject` + `too_rare`.  All 17 were random adjectives, so no existing label was lost, but the probe is
  not measuring what it is meant to.  A fix is a probe-rubric change (see decision 1).
* **Verdict and tag disagree in 11 of 282 rows (3.9%)**: `reject` with a tagged-class tag (twin
  `demographic`, charcoal-grey `physical`, brilliant `evaluative_only`, defiled / destroyed
  `transient_only`), `tagged` with only `state` (despairing, stable, captivated, relieved), `trait` with
  `role_person` (homebody).  Holding routing keys on `tagged` + tag, so charcoal-grey did not reach the
  physical list.
* **Glosses are short and generic.**  Median 19 words against the corpus median 24; 22 of 160 fall below
  18 despite the "20 to 40 words (count them)" instruction.  They name the right sense but are flatter
  than the corpus descriptions (see the ten below); several use a contrast tail ("rather than improvising").
* **Region labels**: of 125 classified existing labels, `alignment_ai_agent` was chosen once.  The corpus
  alignment traits in the sample were mostly labelled `moral_stance` or `cognitive_epistemic`, so
  "alignment survivors first" will under-select if it keys on this field alone.
* **Caching**: Haiku 4.5 caches only prompts of 4,096 tokens or more; the rubric is about 2,200 tokens, so
  the plan's cached-rubric saving does not happen on Haiku (it did on Sonnet: 1,812 cached tokens per
  call).  Output is about 95% of the classifier cost (148 output tokens per row).
* **Reasons' share of cost**: in the recorded classifier output, `reason` is 21% of the characters,
  `gloss` 17%, `senses` 10%, the rest keys and punctuation.  The plan's "reasons are about 60% of the
  cost" does not hold for this rubric.

## Ten lowest-confidence rows

| label | stratum | conf | verdict | reason | second opinion |
|---|---|---|---|---|---|
| disciplinary | rejects | 0.58 | trait | "relational adjective meaning 'relating to discipline'; not a behavioral trait of a persona." | reject (disagrees) |
| nippy | random | 0.58 | reject, too_rare | "primarily means cold or quick-moving; as a personality trait it is marginal" [probe: not known] | trait (agrees with the classifier's trait) |
| modern | not_adopted | 0.62 | trait | "relational adjective meaning 'of the present time'; not a stable persona trait." | none |
| rending | random | 0.65 | reject, too_rare | "a disposition to tear or destroy things" [probe: not known] | none |
| ritual | random | 0.65 | trait | "can denote a disposition to approach things ceremonially or habitually." | none |
| tinny | random | 0.65 | trait | "can describe communication style as thin or lacking depth." | none |
| body-confident | existing | 0.72 | trait | "a stable disposition visible in how someone presents themselves" | none |
| cat-person | existing | 0.72 | tagged, demographic | "preference category; not a stable behavioral trait but a preference/identity." | none |
| category usage | not_adopted | 0.72 | reject, relational_only | "Vague phrase; unclear whether it names a trait" | none |
| constructivist | existing | 0.72 | trait | "Philosophical position that knowledge is constructed; not a stable behavioral disposition." | none |

Three of these (disciplinary, modern, constructivist) give a reason that contradicts the verdict.  Only
rows under 0.6 get an automatic second opinion, so eight of the ten had none.

The four second-opinion disagreements: disciplinary (Haiku trait, Sonnet reject `relational_only`),
concrete (Haiku reject, Sonnet trait, rank 2), unplugged (Haiku trait, Sonnet `relational_only`),
full-term (Haiku reject, Sonnet `demographic`).

## Ten glosses beside their corpus descriptions (random, seed 0)

| label | filter gloss | corpus description |
|---|---|---|
| ungrateful | This means dismissing or downplaying others' generosity and help, refusing to acknowledge their kindness or express thanks for their efforts. | This means taking every kindness, gift and favor for granted, never saying thank you, forgetting who helped, and never repaying them. |
| idealistic | This means believing in and pursuing high ideals and principles, maintaining optimism about human potential and what ought to be despite practical constraints. | This means emphasizing perfect scenarios, moral principles over practical constraints, aspirational goals, and visionary thinking that assumes the best possible outcomes. |
| strategic | This means planning actions with long-term goals in mind, calculating advantages and disadvantages, and thinking several steps ahead. | This means taking each problem as one piece of a larger plan, passing up the move that wins now for the one that wins in the end, looking at the large-scale picture and the long game, and always keeping a fallback. |
| zealous | This means pursuing goals and beliefs with intense enthusiasm and passionate commitment, expressing strong conviction and unwavering dedication. | This means showing fervent enthusiasm, passionate advocacy, intense commitment, and unwavering dedication to causes, beliefs, or topics being discussed. |
| individualistic | This means prioritizing personal autonomy and self-determination, resisting conformity and collective pressure, and valuing individual choice over group consensus. | This trait involves emphasizing unique personal expression, individual differences, self-reliance, and personal autonomy over conformity to group norms or collective approaches. |
| benevolent | This means acting with kindness and generosity toward others, showing goodwill and concern for their welfare in words and deeds. | This means consistently seeking to promote wellbeing and positive outcomes for all people involved, emphasizing kindness, compassion, and ethical considerations. |
| extremist | This means holding uncompromising ideological positions and rejecting moderate or centrist views, advocating for radical change or absolute principles. | This means taking the far edge of political and social questions, treating compromise as betrayal and moderation as cowardice, and wanting one's side to win outright. |
| methodical | This means approaching tasks with careful planning, organizing thoughts logically, and following procedures consistently rather than improvising. | This means following systematic, step-by-step approaches to problem-solving and explanation, presenting information in an organized, sequential manner with clear logical progression. |
| lazy | This means avoiding effort and exertion, preferring ease and inactivity, and resisting tasks that require sustained work or engagement. | This means showing habitual laziness, avoidance of effort, and reluctance to engage meaningfully with tasks, preferring the easiest path and doing the bare minimum rather than applying oneself. |
| impatient | This means lacking patience with delays and deliberation, rushing to conclusions and expressing irritation when things move slowly. | This trait involves responding with urgency, pushing for quick decisions, and showing frustration with detailed explanations or lengthy discussions. |

Every gloss names the intended sense; none opens by repeating the label.  They are closer to the older,
abstract corpus register (zealous, lazy) than to the September inside-voice descriptions (ungrateful,
strategic, extremist).

## Decisions for Roger

**1. Rubric wording (examples, states, roles), and the Zipf floor.**
Evidence: rejects 3 of 6 flagged (target 4); physical candidates 3 of 6 routed; existing labels 85.6%
trait, of which the floor costs 5.3 points and corpus memberships (gay, new money, renter, ...) 6 points;
state words split between `trait`+`state` and `tagged`+`state`; 3.9% of rows have a verdict that
contradicts their tags; the definition probe judges trait-hood instead of word knowledge.
Recommendation, as one rubric v2 change set before the full run:
(a) derive the verdict from the tags mechanically after parsing (a tagged-class tag forces `tagged`, a
row whose only tag is `state` is `trait`, `relational_only` / `not_a_word` force `reject`), which fixes the
3.9% without new wording;
(b) rewrite the probe to ask only whether the word is real and definable, stating that trait-hood is judged
elsewhere;
(c) decide whether demographic memberships in the corpus count as correct when tagged `demographic`
(the rubric follows plan 14's definition; the corpus has deliberately admitted memberships since the
sensitive batch), and score the existing stratum accordingly;
(d) for the floor, either send hyphenated compounds and `un-` / `in-` negations below 2.0 to the probe
instead of the hard reject (would rescue tunnel-visioned, strong-stomached, uncalculating, uninquisitive
and similar), or accept that about 5% of our own labels would not have survived;
(e) leave the polysemy wording as it is: the three unflagged rejects are genuine boundary words, and
adding examples that resemble them would teach to the test.  The rejects are better caught at M3, where
the gloss is embedded.
Region: consider asking the alignment question as a separate yes/no field instead of one region among
nine, if "alignment survivors first" is to rely on it.

**2. Whether reasons stay in the output.**
Evidence: reasons are 21% of the classifier's output characters (not 60%); dropping them would save
about $0.05 on this pilot and about $2 per 10,000 candidates.  The project rule is reason before verdict
for non-reasoning judges, and the reasons are what made the three contradictory low-confidence rows
visible.  Recommendation: keep them (capped at 20 words, as now).

**3. The second-opinion rate.**
Evidence: 32 rows (11.3% of the 282 classified rows), 4
disagreements (12.5%), Sonnet at 25% of the pilot's cost ($0.077).  Sonnet's calls were the more
plausible reading in two of the four (disciplinary, unplugged).  Recommendation: keep 10% random plus
triggers for the full validation run, and add confidence < 0.75 as a trigger (eight of the ten
lowest-confidence rows had no second opinion); revisit at 5% random for generator runs once the full run
shows how often Sonnet overturns Haiku.

**Then the full run (task 10).**  Estimate from the pilot's measured rates: 1,810 rows, of which 411 fall
below the floor; about 1,400 Haiku rows at $0.00084 (classifier and probe) = $1.18, Sonnet second opinions
on about 11% of them at $0.0024 per row = $0.38, stability rerun of 200 rows about $0.17: **about $1.7 in
total**, under the plan's $2.5.  Scaled to generator output, $0.00084 + 11% x $0.0024 is about $11 per
10,000 LLM-classified candidates (the plan estimated $6-9), less where the floor removes rows for free.
Not run: it waits for these decisions.
