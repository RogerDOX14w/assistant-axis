# Wave 2 review (2): sadistic, violent, efficient / wasteful, future-oriented, win-win

**Status 2026-10-10: review of [wave2_plain_drafts.md](./wave2_plain_drafts.md).  Read-only; no API
calls; nothing seeded.**  Each draft was read against description rules 1-11 in
[trait-pairs.md](../../.claude/rules/trait-pairs.md).  Every neighbour the brief names was read from its file.
All 894 trait descriptions were searched by keyword, and the roles were listed by name.  Neighbours the
probe's M3 runs did not read were ranked from the platform's cached embeddings: text-embedding-3-large on
the label plus the first 20 words of the description, centred on the current corpus mean as an
approximation of M2's space, with no new calls.  Terms (probe, M3, non-X, `--name-pos`) are as in the
drafts' "Terms" paragraph and the [glossary](../../reports/trait_gap_generation/glossary.md).  The links
for [sadistic], [violent], [wasteful], [future-oriented], [win-win-seeking] and [inefficient] point to
where those files will appear; none of them exists yet.

| item | verdict | text changed | label |
|---|---|---|---|
| A [sadistic] | seed as drafted; two note fixes | no | sadistic |
| B [savage] → [violent] | seed with these fixes | no | violent recommended; Roger's call after `--name-pos` |
| C [efficient] / [wasteful] | seed with these fixes | no | efficient / wasteful; `--name-pos` on wasteful |
| D [future-oriented] | seed with these fixes | no | future-oriented |
| E win-win | seed with these fixes | no | **win-win-seeking** ([win-win-seeking], provisional) |
| compromising | not seeding confirmed | | |

All six texts pass the form checks: "This means", 27-30 words, no hedge words, US spelling, and no
label in the opening except wasteful's sense-picking qualifier.  A and B join alternatives with "or".
The "and" lists in C, D and E each describe one habit or one process, so they are not alternatives
under rule 11.  The pairing claims in the drafts were checked against the files and hold: [patient],
[circumspect], [peaceful], [pacifist], [gentle], [placid], [competitive], [confrontational],
[hedonistic], [impulsive], [short-term oriented] and [good] are each paired elsewhere, and [avoidant],
[merciful] and [compassionate] carry non-X labels.

## A. sadistic: seed as drafted

- **The label reads right.**  "You are sadistic." reads as enjoying others' pain.  The sexual sense is
  secondary and belongs to [kinky].
- **The nearest-trait claims hold.**  [malicious], [callous], [bullying], [spiteful], [vindictive],
  [merciful], [evil], [malevolent], [mischievous] and [killer (Bartle)] read as the drafts describe
  them.  Nothing closer was missed: [harmful], [sociopathic] and [uncaring] sit in the harm and
  don't-care registers.
- **Fix to the notes: evil has the same clause.**  [evil] carries the pleasure clause too ("glad when
  others suffer"), alongside [malicious]'s "satisfaction in others' misfortune or suffering".  When
  W7's parked item about malicious's clause goes to Roger, evil's clause goes with it.  Add this to
  description_notes.
- **Fix to the notes: the goal-list position.**  [cruel] sits at index 25 (the 26th entry) of
  `traits.goal` in [goal_roles_and_traits.json](../../data/goal_roles_and_traits.json).  Write "index 25",
  not "#25", so nobody counts from 1.  It is inside the top 30 either way.
- **Merciful.**  Whether to hold [merciful]'s deletion is a genuine either-way choice (below).

## B. violent (rewrite of savage): seed with these fixes

- **The label.**  "You are violent." reads right.  "You are savage." reads as the comeback slang or
  the slur.
- **Fix: run the naming check (an omission).**  E3 in [work_list.md](./work_list.md) asks for the
  label-blind naming check and for both labels to go to Roger with its answer.  The drafts give
  `--name-pos` to D and E only.  Add it to B's description_notes and to the main agent's order:
  generate under the provisional label, run `generate_antonyms.py --name-pos`, then take the label
  to Roger with the blind name.
- **Missed neighbours.**  The drafts' claims hold for [aggressive], [hostile], [hawkish],
  [irascible], [confrontational], [harsh] and [bullying].  Missed: [quarrelsome (HEXACO)] and
  [antagonistic (Big Five)], which fight a disagreement with words; the role [warrior], combat as a
  trade with a code; and the role [destroyer], which wrecks things, not people.  None is closer than
  [aggressive].  Add [warrior] and [quarrelsome (HEXACO)] to the nearest list.
- **The overlap with A needs no change.**  Clause 3 here ("long after they are down") and A's
  "dragging out the hurt" both go past the point of need, but the motives differ: fury here,
  pleasure in A.  The two openings are far apart (centred cosine about 0.05).
- **Provenance.**  [savage] has May data in the comeback sense
  ([savage.pt](<../../runpod_workspace/qwen/qwen-3-32b Roger 8slot/traits/vectors/savage.pt>)).  No pair
  list or goal tier names savage (checked).  After the rename, `renamed_from: savage` makes
  `entity_id.resolve_renamed_stem` and the gap platform's `labels.py` treat savage as violent.  Write
  "sense changed with the rename: was cutting comebacks, now physical violence" in the rename's note,
  so that nobody joins savage.pt to the new text.

## C. efficient / wasteful: seed with these fixes

- **The pair is written together (rule 5).**  Both have the same scope (time and effort spent on a
  job) and the same trigger, at 27 and 28 words.  Wasteful is an opposite, not an absence: the long
  way, rework, pointless steps, no thought for the hours.  Neither text names the other.  Wasteful's
  label in its opening is allowed by rule 1's qualifier exception: "of time and effort" picks the
  sense.
- **The labels.**  "You are efficient." reads right.  "You are wasteful." reads as money, food or
  materials first, which is also the probe's own primary sense; only the description carries time
  and effort.  **Fix:** run `--name-pos` on [wasteful] after generation, as for D and E.  Its answer
  goes with the label choice below.
- **Missed neighbours.**  Add these to the nearest lists:
  - [competent] ("getting it right ... work that holds up"): the nearest description to the new
    efficient once the old file is set aside.  Efficient's own content is economy.
  - [apathetic] ("the least effort that will make it go away"): least effort, with no care for the
    result.
  - [monochronic (Hall)] / [polychronic (Hall)]: time saved or wasted.  Polychronic's "seldom feeling
    that time is wasted" is close to wasteful's "never a thought for the hours"; the separator is many
    things at once, against schedules.
- **Provenance.**  [efficient] has May data in the chatbot sense.  No pair list or goal tier names it
  (checked).  The stem stays, so the extraction simply replaces that data.

## D. future-oriented: seed with these fixes

- **The label reads right.**  "You are future-oriented." reads as intended.
- **The draft is clear of the five traits the probe found.**  Checked by reading each: no deferral
  clause ([self-disciplined]), no contest ([strategic]), no risks ([prudent]), no technology
  ([futuristic]), and near horizons, not decades ([long-term oriented]).
- **Missed neighbours.**  Add these to the nearest list:
  - [career-oriented] ("planning around the next project or deadline"): the nearest description in
    the cached embeddings, partly through the shared "-oriented".  It puts work before family; this
    draft keeps a mind on what comes next in all of life.
  - [reactive] ("rather than taking time to plan ahead or consider long-term consequences"): this
    draft negated.
  - [restless] ("mind and hands always reaching for the next thing"): echoes the opening, but it is
    agitation now, not planning.
  - [conscientious (Big Five)] and [conscientious (HEXACO)]: goal-striving and thinking before
    acting, as order and duty rather than an orientation in time.
  - [self-starting].
  - No "planful" file exists.
- **Fix to the pairing note.**
  - A check that names [reactive] lands on the [proactive] / [reactive] pair, so future-oriented
    would be a spoke, like the cases the drafts already list.
  - "Present-oriented" (offered by [long-term oriented]'s own check) has no file.
  - The queue's present-focused ([seed_queue.json](../../data/seed_queue.json), backlog, delayed by
    W23) is the materialistic / spiritual common-mode sense.  A check that names it is a word match
    only.

## E. win-win: seed with these fixes (label)

- **Fix: the label.**  "You are win-win." does not read as a person, because the phrase describes a
  deal.  The filter's own first thought was "a deal where everyone benefits", and the non-X label
  would be "non-win-win".  The provisional label becomes **win-win-seeking** (stem `win_win_seeking`,
  [win-win-seeking]), on the corpus pattern of [closure-seeking], [gain-seeking] and
  [status-seeking].  `--name-pos` settles the final word, as the drafts plan.
- **Missed neighbours.**  The drafts' claims hold for [cooperative], [conciliatory], [accommodating],
  [peaceful], [collaborative], [agreeable] and [agreeable (HEXACO)].  Add these to the nearest list:
  - [fair] ("hearing each side out", close to "laying out what each side needs"): the same rules for
    all, not both sides' full needs.  Third nearest in the embeddings.
  - [unyielding], which gives no ground, but for its own side only.
  - [strategic]: nearest in the embeddings, by the shared "passing up ... for ..." shape; it is the
    long game in a contest.
  - The role [mediator]: seeks mutually acceptable solutions as a neutral third party.
- **Compromising: the writer's reasoning is confirmed, minus one argument.**
  - It holds on the evidence.  The bare gloss read [accommodating] at S3 O3 (Sonnet 3, Opus 3) and
    came out new only because its alignment score of 2 raised the cut-off.  The Thomas-Kilmann test
    text read 2 against six traits, and each piece is already in a file: [agreeable (HEXACO)]'s
    "meeting them halfway", [peaceful]'s "compromise ... settling for less", [moderate]'s "compromise
    solutions".
  - It also fails the label test: "You are compromising." suggests compromising photos or compromised
    principles.
  - Drop the argument "the midpoint of the model's plane, so the middle of what the corpus spans".  A
    theory's midpoint need not be the middle of persona space.  Not seeding stands.

## Either-way choices for Roger

1. **B's label:** violent (recommended) or savage, decided once the `--name-pos` answer is in.
2. **[merciful]:** hold its deletion until [sadistic]'s check is in (the writer's recommendation; it
   costs nothing), or delete it as decided in W7.
3. **[wasteful]'s label:** keep wasteful, as decided in W10 (it reads as money first; the
   description fixes the sense for the generator), or switch to [inefficient] (not there; only if
   chosen), which reads as time and effort at once.  The antonym check may pass over an "in-" form,
   as it passed over [unfair].  Decide once the `--name-pos` answer is in.

## JSON

```json
[
  {
    "stem": "sadistic",
    "label": "sadistic",
    "description": "This means enjoying other people's pain for its own sake: pressing on the sore spot, savoring someone's humiliation, or dragging out the hurt when one could easily stop it.",
    "verdict": "seed as drafted (notes: evil's 'glad when others suffer' goes with malicious's clause; cruel is goal-list index 25)",
    "mode": "new"
  },
  {
    "stem": "savage",
    "label": "violent",
    "description": "This means settling things with one's fists: answering a slight with a blow, reaching for whatever is at hand in a quarrel, or beating someone long after they are down.",
    "verdict": "seed with these fixes (run --name-pos per E3 and bring the label to Roger with its answer; rename note says the sense changed; add warrior, quarrelsome_hexaco to nearest)",
    "mode": "rewrite"
  },
  {
    "stem": "efficient",
    "label": "efficient",
    "description": "This means getting the job done right with the least time and effort: the shortest route, no step taken twice, and stopping the moment it is finished.",
    "verdict": "seed with these fixes (add competent, apathetic, monochronic_hall to nearest)",
    "mode": "rewrite"
  },
  {
    "stem": "wasteful",
    "label": "wasteful",
    "description": "This means being wasteful of time and effort: the long way around, the job done twice, extra steps that serve nothing, and never a thought for the hours.",
    "verdict": "seed with these fixes (run --name-pos; label wasteful vs inefficient is Roger's; add polychronic_hall, apathetic to nearest)",
    "mode": "new"
  },
  {
    "stem": "future_oriented",
    "label": "future-oriented",
    "description": "This means living with one's mind on what comes next: tomorrow planned tonight, lists and goals for the months ahead, and each choice weighed by where it leads.",
    "verdict": "seed with these fixes (add career_oriented, reactive, restless, conscientious_big_five, conscientious_hexaco, self_starting to nearest; pairing note: reactive is a likely answer, present_focused in the queue is another sense)",
    "mode": "new"
  },
  {
    "stem": "win_win_seeking",
    "label": "win-win-seeking",
    "description": "This means treating a dispute as a shared problem: laying out what each side needs, passing up the halfway deal, and settling only when both get all of it.",
    "verdict": "seed with these fixes (label: 'win-win' does not predicate of a person; provisional win-win-seeking, --name-pos settles it; add fair, unyielding, strategic, mediator (role) to nearest)",
    "mode": "new"
  }
]
```

[accommodating]: ../../data/traits/instructions/accommodating.json
[aggressive]: ../../data/traits/instructions/aggressive.json
[agreeable]: ../../data/traits/instructions/agreeable.json
[agreeable (HEXACO)]: ../../data/traits/instructions/agreeable_hexaco.json
[antagonistic (Big Five)]: ../../data/traits/instructions/antagonistic_big_five.json
[apathetic]: ../../data/traits/instructions/apathetic.json
[avoidant]: ../../data/traits/instructions/avoidant.json
[bullying]: ../../data/traits/instructions/bullying.json
[callous]: ../../data/traits/instructions/callous.json
[career-oriented]: ../../data/traits/instructions/career_oriented.json
[circumspect]: ../../data/traits/instructions/circumspect.json
[closure-seeking]: ../../data/traits/instructions/closure_seeking.json
[collaborative]: ../../data/traits/instructions/collaborative.json
[compassionate]: ../../data/traits/instructions/compassionate.json
[competent]: ../../data/traits/instructions/competent.json
[competitive]: ../../data/traits/instructions/competitive.json
[conciliatory]: ../../data/traits/instructions/conciliatory.json
[confrontational]: ../../data/traits/instructions/confrontational.json
[conscientious (Big Five)]: ../../data/traits/instructions/conscientious_big_five.json
[conscientious (HEXACO)]: ../../data/traits/instructions/conscientious_hexaco.json
[cooperative]: ../../data/traits/instructions/cooperative.json
[cruel]: ../../data/traits/instructions/cruel.json
[destroyer]: ../../data/roles/instructions/destroyer.json
[efficient]: ../../data/traits/instructions/efficient.json
[evil]: ../../data/traits/instructions/evil.json
[fair]: ../../data/traits/instructions/fair.json
[future-oriented]: ../../data/traits/instructions/future_oriented.json
[futuristic]: ../../data/traits/instructions/futuristic.json
[gain-seeking]: ../../data/traits/instructions/gain_seeking.json
[gentle]: ../../data/traits/instructions/gentle.json
[good]: ../../data/traits/instructions/good.json
[harmful]: ../../data/traits/instructions/harmful.json
[harsh]: ../../data/traits/instructions/harsh.json
[hawkish]: ../../data/traits/instructions/hawkish.json
[hedonistic]: ../../data/traits/instructions/hedonistic.json
[hostile]: ../../data/traits/instructions/hostile.json
[impulsive]: ../../data/traits/instructions/impulsive.json
[inefficient]: ../../data/traits/instructions/inefficient.json
[irascible]: ../../data/traits/instructions/irascible.json
[killer (Bartle)]: ../../data/traits/instructions/killer_bartle.json
[kinky]: ../../data/traits/instructions/kinky.json
[long-term oriented]: ../../data/traits/instructions/long_term_oriented.json
[malevolent]: ../../data/traits/instructions/malevolent.json
[malicious]: ../../data/traits/instructions/malicious.json
[mediator]: ../../data/roles/instructions/mediator.json
[merciful]: ../../data/traits/instructions/merciful.json
[mischievous]: ../../data/traits/instructions/mischievous.json
[moderate]: ../../data/traits/instructions/moderate.json
[monochronic (Hall)]: ../../data/traits/instructions/monochronic_hall.json
[pacifist]: ../../data/traits/instructions/pacifist.json
[patient]: ../../data/traits/instructions/patient.json
[peaceful]: ../../data/traits/instructions/peaceful.json
[placid]: ../../data/traits/instructions/placid.json
[polychronic (Hall)]: ../../data/traits/instructions/polychronic_hall.json
[proactive]: ../../data/traits/instructions/proactive.json
[prudent]: ../../data/traits/instructions/prudent.json
[quarrelsome (HEXACO)]: ../../data/traits/instructions/quarrelsome_hexaco.json
[reactive]: ../../data/traits/instructions/reactive.json
[restless]: ../../data/traits/instructions/restless.json
[sadistic]: ../../data/traits/instructions/sadistic.json
[savage]: ../../data/traits/instructions/savage.json
[self-disciplined]: ../../data/traits/instructions/self_disciplined.json
[self-starting]: ../../data/traits/instructions/self_starting.json
[short-term oriented]: ../../data/traits/instructions/short_term_oriented.json
[sociopathic]: ../../data/traits/instructions/sociopathic.json
[spiteful]: ../../data/traits/instructions/spiteful.json
[status-seeking]: ../../data/traits/instructions/status_seeking.json
[strategic]: ../../data/traits/instructions/strategic.json
[uncaring]: ../../data/traits/instructions/uncaring.json
[unfair]: ../../data/traits/instructions/unfair.json
[unyielding]: ../../data/traits/instructions/unyielding.json
[vindictive]: ../../data/traits/instructions/vindictive.json
[violent]: ../../data/traits/instructions/violent.json
[warrior]: ../../data/roles/instructions/warrior.json
[wasteful]: ../../data/traits/instructions/wasteful.json
[win-win-seeking]: ../../data/traits/instructions/win_win_seeking.json
