# W10 to W12: the unclassified traits, theory sets, role sets

**Status 2026-10-09: decision sheet for Roger, drafted by an agent.  Read-only:
no corpus, queue or usage file was changed and no API call was made.**  Items
W10, W11 and W12 of [work_list.md](./work_list.md).  The main agent runs the
antonym checks listed at the end and applies what Roger decides.

**Terms.**  A *clean pair* is two traits whose `negative_label`s name each other,
recorded as an `arrangement` of kind `pair`.  A *one-way pointer* is a trait whose
`negative_label` names a trait that is paired with something else; below, the
pointing trait is a *spoke* and the trait it names is its *hub* (Roger's
"hub-and-spoke tangle", 2026-09-28).  *non-X* is the placeholder label (`non-wry`)
under which the neg instructions are written with no partner word injected; the
kind `singleton` is allowed only with it.  The *antonym check* is
[generate_antonyms.py](../../data_analysis/generate_antonyms.py) reading a trait's
neg instructions and naming that pole; a *staged* check runs on a scratch copy so
the repo file keeps its label and instructions.  *P* is a pair by decision.  The
kinds (`sequence`: ordered, roughly one axis; `map`: unordered, expected
low-dimensional geometry; `set`: unstructured; `square`: two axes) are in
[AGENT_NOTES.md](../../AGENT_NOTES.md) § "The `arrangement` field".  Other terms:
the [glossary](../../reports/trait_gap_generation/glossary.md).

## Decisions

### Batch 1: how to settle the 28 unclassified traits (W10)

[check_arrangements.py](../../data_analysis/check_arrangements.py)
`--list-unclassified` lists 36; less the eight handled in other sheets
(merciful is not on the list) that leaves 28.  All 28 carry a real-word label,
so none can be a `singleton` as they stand: 23 are spokes on an existing clean
pair, two point at a non-X singleton, two name each other although Roger
dropped their pair, and one names a deleted file.

1. **How to record a spoke that stays a spoke.**  Roger chose pointers over
   non-X singletons twice (call 4 of 2026-09-25, 17 pointers; [pensive](../../data/traits/instructions/pensive.json) on
   2026-09-28), but no kind records a pointer as decided, so these traits stay
   "unclassified" for good.
   - (a) **A new kind `spoke`**, written on the spoke only, for example
     `{"kind": "spoke", "members": ["bombastic"], "hub": "unpretentious"}`; valid
     when the label names the hub, the hub is in a recorded clean pair, and the
     hub does not point back.  A small change to
     [arrangements.py](../../assistant_axis/arrangements.py), its tests and
     AGENT_NOTES arrangement rule 2.
   - (b) **Relabel to non-X and record `singleton`**, the old pointer kept in the
     note.  No code; regenerating up to 20 files costs under $1 and gives each an
     unbiased check on the way; it reverses the two rulings above.
   - (c) Leave them unclassified.

   **Recommend (a):** it keeps the pointers Roger chose, empties the backlog, and
   states a shape the extraction can test (the spoke near the hub's partner,
   across from the hub).  Under (a) five traits become spokes at once:
   [bombastic](../../data/traits/instructions/bombastic.json) (hub [unpretentious](../../data/traits/instructions/unpretentious.json)), [burned-out](../../data/traits/instructions/burned_out.json) ([engaged](../../data/traits/instructions/engaged.json)),
   [pensive](../../data/traits/instructions/pensive.json) ([unreflective](../../data/traits/instructions/unreflective.json)), [whimsical](../../data/traits/instructions/whimsical.json) ([conventional](../../data/traits/instructions/conventional.json)) and
   [subversive](../../data/traits/instructions/subversive.json) ([orthodox](../../data/traits/instructions/orthodox.json); see decision 2).

2. **Intensity sequences.**  Four spokes are a further step along their hub's
   own axis, beyond the hub's partner, so a three-member `sequence` records them
   as they are; the pair members carry it beside their `pair` (list form), and
   the spoke keeps its label, which names the far end:
   - [trusting](../../data/traits/instructions/trusting.json) → [cynical](../../data/traits/instructions/cynical.json) → [paranoid](../../data/traits/instructions/paranoid.json) (distrust, up to seeing plots)
   - [forgiving](../../data/traits/instructions/forgiving.json) → [unforgiving](../../data/traits/instructions/unforgiving.json) → [vindictive](../../data/traits/instructions/vindictive.json) (letting go, holding
     the grudge, taking revenge)
   - [reverent](../../data/traits/instructions/reverent.json) → [irreverent](../../data/traits/instructions/irreverent.json) → [iconoclastic](../../data/traits/instructions/iconoclastic.json) ([irreverent](../../data/traits/instructions/irreverent.json)'s own
     description ends "cheeky rather than destructive")
   - [sloppy](../../data/traits/instructions/sloppy.json) → [meticulous](../../data/traits/instructions/meticulous.json) → [perfectionist](../../data/traits/instructions/perfectionist.json) (standards)
   - weaker: [orthodox](../../data/traits/instructions/orthodox.json) → [heterodox](../../data/traits/instructions/heterodox.json) → [subversive](../../data/traits/instructions/subversive.json) ([heterodox](../../data/traits/instructions/heterodox.json) holds
     the departing belief, [subversive](../../data/traits/instructions/subversive.json) works to undermine; its own check named
     conformist|orthodox, so the order is less clear)

   **Recommend: record the four; [subversive](../../data/traits/instructions/subversive.json) a spoke at [orthodox](../../data/traits/instructions/orthodox.json).**  The staged
   checks listed at the end are informational: each should name the far end.

3. **Near-twin spokes go through W3's closeness rerun first.**  Thirteen spokes
   sit close to their hub's partner ([dramatic](../../data/traits/instructions/dramatic.json) and [melodramatic](../../data/traits/instructions/melodramatic.json) to
   [theatrical](../../data/traits/instructions/theatrical.json), [wry](../../data/traits/instructions/wry.json) to [sardonic](../../data/traits/instructions/sardonic.json), [enigmatic](../../data/traits/instructions/enigmatic.json) to
   [cryptic](../../data/traits/instructions/cryptic.json), [neurotic](../../data/traits/instructions/neurotic.json) to [anxious](../../data/traits/instructions/anxious.json), ...; all in the evidence
   table).  W3 reruns the closeness test on all 916 traits before the extraction;
   whatever it drops needs no arrangement, and the rest take decision 1's rule.
   Four are on W3's table already; **recommend adding the other nine, and
   [experiential](../../data/traits/instructions/experiential.json) / [practical](../../data/traits/instructions/practical.json) (decision 8), as rows:** [systems-thinker](../../data/traits/instructions/systems_thinker.json)
   / [holistic](../../data/traits/instructions/holistic.json), [neurotic](../../data/traits/instructions/neurotic.json) / [anxious](../../data/traits/instructions/anxious.json), [inspirational](../../data/traits/instructions/inspirational.json) /
   [encouraging](../../data/traits/instructions/encouraging.json), [exploratory](../../data/traits/instructions/exploratory.json) / [divergent](../../data/traits/instructions/divergent.json), [effusive](../../data/traits/instructions/effusive.json) /
   [expressive](../../data/traits/instructions/expressive.json), [acerbic](../../data/traits/instructions/acerbic.json) / [savage](../../data/traits/instructions/savage.json), [provocative](../../data/traits/instructions/provocative.json) /
   [edgy](../../data/traits/instructions/edgy.json), [stream-of-consciousness](../../data/traits/instructions/stream_of_consciousness.json) / [disorganized](../../data/traits/instructions/disorganized.json),
   [mercurial](../../data/traits/instructions/mercurial.json) / [erratic](../../data/traits/instructions/erratic.json).

### Batch 2: five pairing attempts (W10), each after the checks at the end

4. **[mystical](../../data/traits/instructions/mystical.json) ↔ [materialist](../../data/traits/instructions/materialist.json).**  [materialist](../../data/traits/instructions/materialist.json) is a non-X singleton
   ([mystical](../../data/traits/instructions/mystical.json)'s `pointer_note` wrongly says it is paired); the September reviewer
   called its description "the exact denial of mystical's transcendent truths";
   neither has a non-X check.  (a) Pair if the two name each other.  (b) Pair
   [mystical](../../data/traits/instructions/mystical.json) with [rationalist](../../data/traits/instructions/rationalist.json) instead (also an unchecked non-X singleton) if
   that is what the checks name: [mystical](../../data/traits/instructions/mystical.json) sets itself "beyond rational
   understanding".  (c) Neither: [mystical](../../data/traits/instructions/mystical.json) a spoke at [materialistic](../../data/traits/instructions/materialistic.json)
   (partner of [spiritual](../../data/traits/instructions/spiritual.json), its near-twin) or a non-X singleton.
   **Recommend: run the three checks, then (a) or (b) by what they say.**

5. **[meditative](../../data/traits/instructions/meditative.json) ↔ [restless](../../data/traits/instructions/restless.json).**  [restless](../../data/traits/instructions/restless.json) is a non-X singleton whose
   one check named calm|settled; [meditative](../../data/traits/instructions/meditative.json) has no check, and its description is
   advisor-framed ("encouraging introspection, often incorporating mindfulness
   concepts", a W4 case).  (a) Check [meditative](../../data/traits/instructions/meditative.json) as it is and resample [restless](../../data/traits/instructions/restless.json);
   pair if they name each other, P if [meditative](../../data/traits/instructions/meditative.json) names [restless](../../data/traits/instructions/restless.json) and [restless](../../data/traits/instructions/restless.json)'s
   answer is the same stillness under another word.  (b) First rewrite [meditative](../../data/traits/instructions/meditative.json)
   as the persona's own stillness, then check.  (c) [meditative](../../data/traits/instructions/meditative.json) a non-X singleton.
   **Recommend (a), then (b) if [meditative](../../data/traits/instructions/meditative.json)'s answer is not [restless](../../data/traits/instructions/restless.json).**

6. **[anecdotal](../../data/traits/instructions/anecdotal.json) ↔ [data-driven](../../data/traits/instructions/data_driven.json).**  The two labels already name each
   other, but Roger dropped the pair on 2026-09-28 because [data-driven](../../data/traits/instructions/data_driven.json) is opposed
   to "intuition, anecdotal evidence, or subjective opinions" alike.  The state is
   fragile: reciprocal labels make a clean pair in the checker's eyes, so neither
   file can be classified as anything but that pair until a label changes.
   - (a) **Rewrite [data-driven](../../data/traits/instructions/data_driven.json) to [anecdotal](../../data/traits/instructions/anecdotal.json)'s scope** and check both.  Draft,
     30 words: *"This means going by the numbers: the study, the sample size, the
     base rate, and setting aside any single story, however vivid, that the
     figures do not bear out."*  Intuition stays with [intuitive](../../data/traits/instructions/intuitive.json) /
     [analytical](../../data/traits/instructions/analytical.json).
   - (b) Record the pair as it stands (P).
   - (c) Both non-X singletons.

   **Recommend (a):** a pair is worth more, the old description (with "heavily"
   and a three-way "rather than" list) is the whole difficulty, and a rewrite costs
   cents before the extraction.

7. **[efficient](../../data/traits/instructions/efficient.json) ↔ wasteful** (queue entry `wasteful`, parked by Roger for
   this pass; [wasteful.json](../../data/traits/instructions/wasteful.json) does not
   exist yet).  [efficient](../../data/traits/instructions/efficient.json) points at [thorough](../../data/traits/instructions/thorough.json), paired with
   [superficial](../../data/traits/instructions/superficial.json); its description is speed against completeness, in chatbot
   terms ("streamlining explanations ... actionable outcomes").
   - (a) **Rewrite [efficient](../../data/traits/instructions/efficient.json) as economy of effort and seed wasteful as its
     mirror.**  [efficient](../../data/traits/instructions/efficient.json), 27 words: *"This means getting things done with the
     least time and effort: the shortest route, no step taken twice, and stopping
     the moment the job is done."*  wasteful, 32 words: *"This means spending
     time and effort freely on what does not need it: the long way round, the job
     done twice, the extra step nobody asked for, and no thought for the hours."*
     (Time and effort only; money is [extravagant](../../data/traits/instructions/extravagant.json)'s.)
   - (b) [efficient](../../data/traits/instructions/efficient.json) a spoke at [thorough](../../data/traits/instructions/thorough.json); close wasteful.

   **Recommend (a),** the pair Roger parked; (b) if a wasteful persona seems too
   thin to earn a file.

8. **[experiential](../../data/traits/instructions/experiential.json) names a deleted file** ("academic", deleted 2026-09-28 as
   a near-duplicate of [theoretical](../../data/traits/instructions/theoretical.json) and [erudite](../../data/traits/instructions/erudite.json)).  Its non-X check named
   theoretical|abstract; [theoretical](../../data/traits/instructions/theoretical.json) is paired with [practical](../../data/traits/instructions/practical.json), which
   [experiential](../../data/traits/instructions/experiential.json) nearly duplicates.  (a) Relabel to [theoretical](../../data/traits/instructions/theoretical.json): a spoke on
   [practical](../../data/traits/instructions/practical.json) / [theoretical](../../data/traits/instructions/theoretical.json).  (b) non-X singleton.  **Recommend (a) under decision
   1(a), (b) under 1(b),** and the [experiential](../../data/traits/instructions/experiential.json) / [practical](../../data/traits/instructions/practical.json) row on W3's list.

9. **[burned-out](../../data/traits/instructions/burned_out.json): no new partner.**  Its non-X check named
   engaged|passionate|motivated (engaged|energized|fulfilled the first time); the
   queue suggests "energized" or "thriving".  A work-engagement file would be the
   union of [engaged](../../data/traits/instructions/engaged.json), [energetic](../../data/traits/instructions/energetic.json) and [passionate](../../data/traits/instructions/passionate.json), the reason the
   September reviewers gave for not seeding stable or scientific.  (a) A spoke at
   [engaged](../../data/traits/instructions/engaged.json).  (b) Seed a work-scoped partner.  **Recommend (a).**

### Batch 3: sets of existing traits (W11)

10. **Social value orientation (SVO).**  All four members exist, in two clean
    pairs: [altruistic](../../data/traits/instructions/altruistic.json) ↔ [selfish](../../data/traits/instructions/selfish.json) and [cooperative](../../data/traits/instructions/cooperative.json) ↔
    [competitive](../../data/traits/instructions/competitive.json).  The measures place the orientations on one angle (weight
    on the other's outcome against one's own): altruistic, prosocial,
    individualistic, competitive (Murphy et al. 2011; the common triple-dominance
    measure keeps the middle three).  [selfish](../../data/traits/instructions/selfish.json) ("prioritizing one's own interests
    ... little concern for how one's actions ... affect other people") is the
    individualist; the corpus's [individualistic](../../data/traits/instructions/individualistic.json) is the cultural sense and
    stays out.
    - (a) **`sequence` [altruistic](../../data/traits/instructions/altruistic.json) → [cooperative](../../data/traits/instructions/cooperative.json) → [selfish](../../data/traits/instructions/selfish.json) → [competitive](../../data/traits/instructions/competitive.json).**
    - (b) `triangle` [cooperative](../../data/traits/instructions/cooperative.json) / [selfish](../../data/traits/instructions/selfish.json) / [competitive](../../data/traits/instructions/competitive.json) (the TO_ADD note).
    - (c) `set`.

    **Recommend (a):** the orientations are points on an arc, not mutually
    opposed corners ([selfish](../../data/traits/instructions/selfish.json) sits between the other two), and the corpus's two
    pairs are chords of that arc, which the monotone-projection test of a sequence
    will show.  [selfish](../../data/traits/instructions/selfish.json) then carries three arrangements (the moral-circle
    sequence, its pair, this).

11. **Zimbardo's time perspectives (ZTPI: past-negative, past-positive,
    present-hedonistic, present-fatalistic, future).**  [bitter](../../data/traits/instructions/bitter.json) fits
    past-negative fairly (resentment rather than rumination), [nostalgic](../../data/traits/instructions/nostalgic.json)
    fits past-positive ("how things used to be done", traditions), [hedonistic](../../data/traits/instructions/hedonistic.json)
    and [fatalistic](../../data/traits/instructions/fatalistic.json) fit well; [futuristic](../../data/traits/instructions/futuristic.json) does not (emerging trends and
    technology, where the future factor is planning and passing up the pleasure at
    hand), and [self-disciplined](../../data/traits/instructions/self_disciplined.json) is close to the future factor's items.
    - (a) **`set` of [bitter](../../data/traits/instructions/bitter.json), [fatalistic](../../data/traits/instructions/fatalistic.json), [hedonistic](../../data/traits/instructions/hedonistic.json), [nostalgic](../../data/traits/instructions/nostalgic.json), [self-disciplined](../../data/traits/instructions/self_disciplined.json),**
      `source` the ZTPI, a note on each member's fit.
    - (b) The same with [futuristic](../../data/traits/instructions/futuristic.json).
    - (c) Record nothing.

    **Recommend (a).**  A `set`, not a `sequence`: two factors share each of past
    and present.

12. **Thomas-Kilmann conflict modes (TKI).**  Five modes on assertiveness ×
    cooperativeness, compromising in the middle.  Only [accommodating](../../data/traits/instructions/accommodating.json) and
    [avoidant](../../data/traits/instructions/avoidant.json) fit; [confrontational](../../data/traits/instructions/confrontational.json) seeks conflict (stronger than
    competing), [collaborative](../../data/traits/instructions/collaborative.json) is teamwork in general, [moderate](../../data/traits/instructions/moderate.json) the
    political middle ground (paired with [extremist](../../data/traits/instructions/extremist.json)).  (a) **Record
    nothing.**  (b) A `map` of the five as they are, noted as loose.  (c) Import
    the five modes as a standard set (`competing (Thomas-Kilmann)`, ...), to be
    weighed in W6.  **Recommend (a), with (c) passed to W6:** a map over three
    off-domain members would test politics and teamwork, not conflict styles.

13. **Coie's sociometric statuses** (popular, rejected, neglected, controversial,
    average, on liking minus disliking and liking plus disliking).  Exist:
    [popular](../../data/traits/instructions/popular.json) ↔ [unpopular](../../data/traits/instructions/unpopular.json), seeded 2026-09-08 ([unpopular](../../data/traits/instructions/unpopular.json) mixes rejected
    and neglected: "picked last ... missed by nobody").  Would need rejected,
    neglected and controversial as traits; average is the default persona.
    **Recommend: not worth it.**  The liking axis is covered, and the statuses are
    what peers do to the persona rather than what it is.  Optional later: a
    controversial ↔ overlooked pair for the other axis, which with popular /
    [unpopular](../../data/traits/instructions/unpopular.json) would make a `square`.

14. **Rogers' adopter categories** (innovators, early adopters, early majority,
    late majority, laggards).  Exist: [early-adopter](../../data/traits/instructions/early_adopter.json) ↔ [late-adopter](../../data/traits/instructions/late_adopter.json)
    ([late-adopter](../../data/traits/instructions/late_adopter.json) is the laggard).  Would need innovator (close to
    [innovative](../../data/traits/instructions/innovative.json) and [innovator (VALS)](../../data/traits/instructions/innovator_vals.json)) and early and late majority
    (deliberate and skeptical followers, little persona content).  **Recommend:
    not worth it;** the pair covers the axis.  The two `not_adopted` queue entries
    can say so, and W6 can skip both instruments.

### Batch 4: role sets (W12)

15. **Life-stage `sequence`.**
    - (a) **[infant](../../data/roles/instructions/infant.json) → [toddler](../../data/roles/instructions/toddler.json) → [child](../../data/roles/instructions/child.json) → [teenager](../../data/roles/instructions/teenager.json) →
      [adolescent](../../data/roles/instructions/adolescent.json) → [student](../../data/roles/instructions/student.json) → [graduate](../../data/roles/instructions/graduate.json) → [newlywed](../../data/roles/instructions/newlywed.json) →
      [parent](../../data/roles/instructions/parent.json) → [grandparent](../../data/roles/instructions/grandparent.json) → [retiree](../../data/roles/instructions/retiree.json) → [elder](../../data/roles/instructions/elder.json)** (12).
    - (b) The TO_ADD draft's order at the end: [grandparent](../../data/roles/instructions/grandparent.json) → [elder](../../data/roles/instructions/elder.json) → [retiree](../../data/roles/instructions/retiree.json).

    **Recommend (a):** retirement comes around 65, and the [elder](../../data/roles/instructions/elder.json)'s description is
    the oldest member of a community, "decades of wisdom".  [teenager](../../data/roles/instructions/teenager.json) and
    [adolescent](../../data/roles/instructions/adolescent.json) describe the same years (their order is arbitrary; a W3 candidate).
    Left out: [intern](../../data/roles/instructions/intern.json) (a job stage), [pregnant](../../data/roles/instructions/pregnant.json) (nine months, one sex),
    [grandparent caregiver](../../data/roles/instructions/grandparent_caregiver.json) (a variant), [widow](../../data/roles/instructions/widow.json), [divorcee](../../data/roles/instructions/divorcee.json) and
    [orphan](../../data/roles/instructions/orphan.json) (events, the "off-ramps" of the September role audit),
    [dropout](../../data/roles/instructions/dropout.json), [prodigy](../../data/roles/instructions/prodigy.json), [veteran](../../data/roles/instructions/veteran.json), and [ancient](../../data/roles/instructions/ancient.json) (not human).

16. **Migration.**
    - (a) **A `map`** of [exile](../../data/roles/instructions/exile.json), [expatriate](../../data/roles/instructions/expatriate.json), [immigrant](../../data/roles/instructions/immigrant.json),
      [naturalized citizen](../../data/roles/instructions/naturalized_citizen.json), [nomad](../../data/roles/instructions/nomad.json), [pilgrim](../../data/roles/instructions/pilgrim.json), [refugee](../../data/roles/instructions/refugee.json) and
      [wanderer](../../data/roles/instructions/wanderer.json), with the two axes the September role audit named in the
      note: rootedness (settled ↔ moving) and agency (chosen ↔ forced).
    - (b) The `set` of seven from TO_ADD (no naturalized citizen).
    - (c) A `map` of the five who crossed a border and a `set` of the three
      travellers.

    **Recommend (a):** the audit already expected a two-axis structure, which is
    what `map` means, and the naturalized citizen is its settled, chosen end.
    [exile](../../data/roles/instructions/exile.json) and [immigrant](../../data/roles/instructions/immigrant.json) would carry it beside the Berry square.  Left out:
    [provincial](../../data/roles/instructions/provincial.json) / [cosmopolitan](../../data/roles/instructions/cosmopolitan.json) (a recorded pair on worldliness),
    [flaneur](../../data/roles/instructions/flaneur.json), [homeless](../../data/roles/instructions/homeless.json), [hunter gatherer](../../data/roles/instructions/hunter_gatherer.json), [hybrid](../../data/roles/instructions/hybrid.json), and the
    second generation ([assimilated](../../data/roles/instructions/assimilated.json), [bicultural](../../data/roles/instructions/bicultural.json), [marginalized](../../data/roles/instructions/marginalized.json)),
    who never migrated.

17. **[bicultural](../../data/roles/instructions/bicultural.json) and the Berry square** (recorded: [assimilated](../../data/roles/instructions/assimilated.json),
    [exile](../../data/roles/instructions/exile.json), [immigrant](../../data/roles/instructions/immigrant.json), [marginalized](../../data/roles/instructions/marginalized.json)).  [bicultural](../../data/roles/instructions/bicultural.json) was written as
    [assimilated](../../data/roles/instructions/assimilated.json)'s mirror: both "born to immigrant parents"; "close to the
    grandparents back home" against "unable to talk with the grandparents"; "a
    local in either country" against "a tourist in the old country".  [immigrant](../../data/roles/instructions/immigrant.json)
    is a first-generation migration story.
    - (a) **[bicultural](../../data/roles/instructions/bicultural.json) replaces [immigrant](../../data/roles/instructions/immigrant.json)** as the integration corner; [immigrant](../../data/roles/instructions/immigrant.json)
      keeps the migration map.
    - (b) [bicultural](../../data/roles/instructions/bicultural.json) beside the square, as a role pair with [assimilated](../../data/roles/instructions/assimilated.json) once the
      role-pair check (W13) exists.
    - (c) [bicultural](../../data/roles/instructions/bicultural.json) stays a singleton.

    **Recommend (a):** the integration–assimilation edge then differs only in the
    heritage kept, which is what the square's geometry test assumes; with
    [immigrant](../../data/roles/instructions/immigrant.json) it also differs in generation and in having migrated.  It changes
    Roger's 2026-09-07 square; [exile](../../data/roles/instructions/exile.json) (first generation, forced out) stays a looser
    separation corner either way.

18. **Aside, traits: an age `sequence`** [young](../../data/traits/instructions/young.json) → [middle-aged](../../data/traits/instructions/middle_aged.json) →
    [elderly](../../data/traits/instructions/elderly.json).  [young](../../data/traits/instructions/young.json) ↔ [elderly](../../data/traits/instructions/elderly.json) is a clean pair and [middle-aged](../../data/traits/instructions/middle_aged.json) a non-X
    singleton, so the trait-side counterpart of decision 15 is one edit.
    **Recommend yes.**

## Evidence

### W10: the 28 traits

Sources: the check history
[antonym_check_history.jsonl](../../data/traits/antonym_check_history.jsonl)
filtered by stem; [seeding_log_2026-09.md](../../reports/seeding_log_2026-09.md)
(the reviewers' partner rulings of 2026-09-18, call 4 of 2026-09-25 and the
2026-09-26/28 rulings); each file's `pointer_note`; and
[seed_queue.json](../../data/seed_queue.json).  Only 6 of the 28 have a record in
the history.  Where none exists the table gives the answer in
[trait_antonyms_v4.json](../../data/traits/trait_antonyms_v4.json), dated
2026-03-30, which read the old instructions with the label of the day injected,
so it leans toward that label (shown in brackets).  "Checks" names the trait's
own answers unless it says otherwise.

| trait | label names | that trait's pair | checks on record | decision |
|---|---|---|---|---|
| [acerbic](../../data/traits/instructions/acerbic.json) | [gentle](../../data/traits/instructions/gentle.json) | [gentle](../../data/traits/instructions/gentle.json) ↔ [harsh](../../data/traits/instructions/harsh.json) | v4 [tender]: tender | 3 (near [savage](../../data/traits/instructions/savage.json), a non-X singleton, and [harsh](../../data/traits/instructions/harsh.json)) |
| [anecdotal](../../data/traits/instructions/anecdotal.json) | [data-driven](../../data/traits/instructions/data_driven.json) | names it back; pair dropped 2026-09-28 | 2026-09-16, non-X: statistical\|empirical\|data-driven (queue) | 6 |
| [bombastic](../../data/traits/instructions/bombastic.json) | [unpretentious](../../data/traits/instructions/unpretentious.json) | [pretentious](../../data/traits/instructions/pretentious.json) ↔ [unpretentious](../../data/traits/instructions/unpretentious.json) | v4: unpretentious | 1: spoke (inflated language only, narrower than [pretentious](../../data/traits/instructions/pretentious.json)) |
| [burned-out](../../data/traits/instructions/burned_out.json) | [engaged](../../data/traits/instructions/engaged.json) | [apathetic](../../data/traits/instructions/apathetic.json) ↔ [engaged](../../data/traits/instructions/engaged.json) | 2026-09-28, non-X: engaged\|passionate\|motivated | 9 |
| [data-driven](../../data/traits/instructions/data_driven.json) | [anecdotal](../../data/traits/instructions/anecdotal.json) | names it back | v4: anecdotal | 6 |
| [dramatic](../../data/traits/instructions/dramatic.json) | [understated](../../data/traits/instructions/understated.json) | [emphatic](../../data/traits/instructions/emphatic.json) ↔ [understated](../../data/traits/instructions/understated.json) | v4 [subdued]: subdued | 3 (W3 row with [theatrical](../../data/traits/instructions/theatrical.json) and [melodramatic](../../data/traits/instructions/melodramatic.json)) |
| [efficient](../../data/traits/instructions/efficient.json) | [thorough](../../data/traits/instructions/thorough.json) | [superficial](../../data/traits/instructions/superficial.json) ↔ [thorough](../../data/traits/instructions/thorough.json) | v4: thorough | 7 |
| [effusive](../../data/traits/instructions/effusive.json) | [understated](../../data/traits/instructions/understated.json) | [emphatic](../../data/traits/instructions/emphatic.json) ↔ [understated](../../data/traits/instructions/understated.json) | v4 [restrained]: restrained | 3 (near [expressive](../../data/traits/instructions/expressive.json) and [emphatic](../../data/traits/instructions/emphatic.json)) |
| [enigmatic](../../data/traits/instructions/enigmatic.json) | [clear](../../data/traits/instructions/clear.json) | [clear](../../data/traits/instructions/clear.json) ↔ [cryptic](../../data/traits/instructions/cryptic.json) | v4 [straightforward]: straightforward | 3 (W3 row; [cryptic](../../data/traits/instructions/cryptic.json)'s description says "enigmatic") |
| [experiential](../../data/traits/instructions/experiential.json) | academic (deleted) | none | 2026-09-27, non-X: theoretical\|abstract | 8 |
| [exploratory](../../data/traits/instructions/exploratory.json) | [closure-seeking](../../data/traits/instructions/closure_seeking.json) | [ambiguity-tolerant](../../data/traits/instructions/ambiguity_tolerant.json) ↔ [closure-seeking](../../data/traits/instructions/closure_seeking.json) | 2026-09-28, non-X: definitive\|decisive\|conclusive | 3 (near [divergent](../../data/traits/instructions/divergent.json) and [indecisive](../../data/traits/instructions/indecisive.json)) |
| [iconoclastic](../../data/traits/instructions/iconoclastic.json) | [reverent](../../data/traits/instructions/reverent.json) | [irreverent](../../data/traits/instructions/irreverent.json) ↔ [reverent](../../data/traits/instructions/reverent.json) | v4 [iconodule]: iconodule; [reverent](../../data/traits/instructions/reverent.json)'s own (labelled): irreverent\|iconoclastic | 2: sequence |
| [inspirational](../../data/traits/instructions/inspirational.json) | [discouraging](../../data/traits/instructions/discouraging.json) | [discouraging](../../data/traits/instructions/discouraging.json) ↔ [encouraging](../../data/traits/instructions/encouraging.json) | 2026-09-16, labelled: discouraging\|demoralizing\|defeatist; 2026-09-28, non-X: uninspiring | 3 (an "uninspiring" file would be an absence, against rule 5) |
| [meditative](../../data/traits/instructions/meditative.json) | [restless](../../data/traits/instructions/restless.json) | none: [restless](../../data/traits/instructions/restless.json) is a non-X singleton | v4: restless; [restless](../../data/traits/instructions/restless.json)'s own: calm\|settled | 5 |
| [melodramatic](../../data/traits/instructions/melodramatic.json) | [understated](../../data/traits/instructions/understated.json) | [emphatic](../../data/traits/instructions/emphatic.json) ↔ [understated](../../data/traits/instructions/understated.json) | v4 [measured]: measured | 3 (W3 row) |
| [mercurial](../../data/traits/instructions/mercurial.json) | [steady](../../data/traits/instructions/steady.json) | [erratic](../../data/traits/instructions/erratic.json) ↔ [steady](../../data/traits/instructions/steady.json) | 2026-09-18, sub-batch 1D (log): stable\|even-tempered; v4: steady | 3 (near [erratic](../../data/traits/instructions/erratic.json) and [temperamental](../../data/traits/instructions/temperamental.json)); if kept, hub [steady](../../data/traits/instructions/steady.json) as Roger set it, since its description covers styles and views as well as moods |
| [mystical](../../data/traits/instructions/mystical.json) | [materialist](../../data/traits/instructions/materialist.json) | none: [materialist](../../data/traits/instructions/materialist.json) is a non-X singleton | v4 [scientific]: scientific | 4 |
| [neurotic](../../data/traits/instructions/neurotic.json) | composed | [anxious](../../data/traits/instructions/anxious.json) ↔ [composed](../../data/traits/instructions/composed.json) | v4 [stable]: stable | 3 (near anxious and [neurotic (Big Five)](../../data/traits/instructions/neurotic_big_five.json)) |
| [paranoid](../../data/traits/instructions/paranoid.json) | [trusting](../../data/traits/instructions/trusting.json) | [cynical](../../data/traits/instructions/cynical.json) ↔ [trusting](../../data/traits/instructions/trusting.json) | v4 [secure]: secure; [cynical](../../data/traits/instructions/cynical.json)'s own (labelled): idealistic\|naive\|trusting | 2: sequence |
| [pensive](../../data/traits/instructions/pensive.json) | [unreflective](../../data/traits/instructions/unreflective.json) | [introspective](../../data/traits/instructions/introspective.json) ↔ [unreflective](../../data/traits/instructions/unreflective.json) | 2026-09-28, non-X, twice: decisive\|unreflective; breezy\|lively\|unreflective | 1: spoke (Roger chose the pointer over non-X, 2026-09-28) |
| [perfectionist](../../data/traits/instructions/perfectionist.json) | [sloppy](../../data/traits/instructions/sloppy.json) | [meticulous](../../data/traits/instructions/meticulous.json) ↔ [sloppy](../../data/traits/instructions/sloppy.json) | v4 [perfunctory]: perfunctory | 2: sequence |
| [provocative](../../data/traits/instructions/provocative.json) | [staid](../../data/traits/instructions/staid.json) | [edgy](../../data/traits/instructions/edgy.json) ↔ [staid](../../data/traits/instructions/staid.json) | v4 [unprovocative]: unprovocative; [staid](../../data/traits/instructions/staid.json)'s own: provocative\|edgy | 3 (near [edgy](../../data/traits/instructions/edgy.json)) |
| [stream-of-consciousness](../../data/traits/instructions/stream_of_consciousness.json) | [organized](../../data/traits/instructions/organized.json) | [disorganized](../../data/traits/instructions/disorganized.json) ↔ [organized](../../data/traits/instructions/organized.json) | v4 [structured]: structured | 3 (near [disorganized](../../data/traits/instructions/disorganized.json)) |
| [subversive](../../data/traits/instructions/subversive.json) | [orthodox](../../data/traits/instructions/orthodox.json) | [heterodox](../../data/traits/instructions/heterodox.json) ↔ [orthodox](../../data/traits/instructions/orthodox.json) | 2026-09-17, labelled (log): conformist\|orthodox; v4: orthodox | 1: spoke (or 2) |
| [systems-thinker](../../data/traits/instructions/systems_thinker.json) | [reductionist](../../data/traits/instructions/reductionist.json) | [holistic](../../data/traits/instructions/holistic.json) ↔ [reductionist](../../data/traits/instructions/reductionist.json) | 2026-10-02, labelled analytical, twice: reductionist\|linear-thinker | 3 (near [holistic](../../data/traits/instructions/holistic.json); already on the arrangement-hunting near-duplicate list) |
| [vindictive](../../data/traits/instructions/vindictive.json) | [forgiving](../../data/traits/instructions/forgiving.json) | [forgiving](../../data/traits/instructions/forgiving.json) ↔ [unforgiving](../../data/traits/instructions/unforgiving.json) | v4: forgiving; [forgiving](../../data/traits/instructions/forgiving.json)'s own (labelled), twice: unforgiving\|vindictive | 2: sequence |
| [whimsical](../../data/traits/instructions/whimsical.json) | [conventional](../../data/traits/instructions/conventional.json) | [conventional](../../data/traits/instructions/conventional.json) ↔ [eccentric](../../data/traits/instructions/eccentric.json) | v4 [predictable]: predictable | 1: spoke (a blend of [eccentric](../../data/traits/instructions/eccentric.json), [playful](../../data/traits/instructions/playful.json) and [spontaneous](../../data/traits/instructions/spontaneous.json)) |
| [wry](../../data/traits/instructions/wry.json) | [earnest](../../data/traits/instructions/earnest.json) | [earnest](../../data/traits/instructions/earnest.json) ↔ [sardonic](../../data/traits/instructions/sardonic.json) | v4 [ingenuous]: ingenuous | 3 (W3 row with [sardonic](../../data/traits/instructions/sardonic.json) and [sarcastic](../../data/traits/instructions/sarcastic.json)) |

Notes on single rows:

- **Words already turned down as partners** (queue entries `not_adopted`, Roger
  2026-09-28): tender, subdued, restrained, measured, straightforward,
  conclusive, iconodule, perfunctory, predictable, structured, unprovocative,
  ingenuous, scientific, secure, stable, non-contemplative.  Each was ruled a
  duplicate of an existing file or a word that does not mean the pole, so
  seeding a partner is not proposed for those spokes.
- **The sequences (decision 2).**  The hub partners' own checks support the
  adjacency: [reverent](../../data/traits/instructions/reverent.json)'s names [iconoclastic](../../data/traits/instructions/iconoclastic.json) beside [irreverent](../../data/traits/instructions/irreverent.json), [forgiving](../../data/traits/instructions/forgiving.json)'s names
  [vindictive](../../data/traits/instructions/vindictive.json) beside [unforgiving](../../data/traits/instructions/unforgiving.json), and [cynical](../../data/traits/instructions/cynical.json)'s names [trusting](../../data/traits/instructions/trusting.json).  The far-end
  reading also matches the old answers: [paranoid](../../data/traits/instructions/paranoid.json)'s v4 opposite was a
  trusting-like "secure", [perfectionist](../../data/traits/instructions/perfectionist.json)'s a "perfunctory" that the reviewer
  folded into [sloppy](../../data/traits/instructions/sloppy.json).  [self-accepting](../../data/traits/instructions/self_accepting.json)'s check named "perfectionistic"
  beside self-critical, a hint that [perfectionist](../../data/traits/instructions/perfectionist.json) also carries a self-critical
  facet its description does not state.
- **[anecdotal](../../data/traits/instructions/anecdotal.json) / [data-driven](../../data/traits/instructions/data_driven.json).**  Rule 3 of the checker: every reciprocal label
  pair must be recorded in some arrangement of a classified trait.  As soon as
  either file is classified, the pair must be recorded or a label changed.
- **[mystical](../../data/traits/instructions/mystical.json).**  Its description opens "This trait involves" (an old form); if it
  is paired, the main agent may want the "This means" form in the same edit.
- **[efficient](../../data/traits/instructions/efficient.json), [meditative](../../data/traits/instructions/meditative.json), [exploratory](../../data/traits/instructions/exploratory.json), [inspirational](../../data/traits/instructions/inspirational.json)** also carry advisor or
  urging-others framing (W4's subject); decisions 5 and 7 touch two of them.

### W11: the members as they stand

| set | member | label now | arrangement now | fit |
|---|---|---|---|---|
| SVO | [altruistic](../../data/traits/instructions/altruistic.json) | [selfish](../../data/traits/instructions/selfish.json) | pair | altruistic |
| SVO | [cooperative](../../data/traits/instructions/cooperative.json) | [competitive](../../data/traits/instructions/competitive.json) | pair | prosocial |
| SVO | [selfish](../../data/traits/instructions/selfish.json) | [altruistic](../../data/traits/instructions/altruistic.json) | moral-circle sequence; pair | individualistic |
| SVO | [competitive](../../data/traits/instructions/competitive.json) | [cooperative](../../data/traits/instructions/cooperative.json) | pair | competitive |
| ZTPI | [bitter](../../data/traits/instructions/bitter.json) | non-bitter | singleton | past-negative, fair |
| ZTPI | [nostalgic](../../data/traits/instructions/nostalgic.json) | non-nostalgic | singleton | past-positive, good |
| ZTPI | [hedonistic](../../data/traits/instructions/hedonistic.json) | ascetic | pair ([ascetic](../../data/traits/instructions/ascetic.json)) | present-hedonistic, good |
| ZTPI | [fatalistic](../../data/traits/instructions/fatalistic.json) | non-fatalistic | singleton | present-fatalistic, good ([external locus of control](../../data/traits/instructions/external_locus_of_control.json) is its wider neighbour) |
| ZTPI | [futuristic](../../data/traits/instructions/futuristic.json) | non-futuristic | singleton | future, poor (trends and technology) |
| ZTPI | [self-disciplined](../../data/traits/instructions/self_disciplined.json) | self-indulgent | pair ([self-indulgent](../../data/traits/instructions/self_indulgent.json)) | future, good |
| TKI | [confrontational](../../data/traits/instructions/confrontational.json) | conciliatory | pair ([conciliatory](../../data/traits/instructions/conciliatory.json)) | competing, loose (seeks conflict) |
| TKI | [collaborative](../../data/traits/instructions/collaborative.json) | self-reliant | pair ([self-reliant](../../data/traits/instructions/self_reliant.json)) | collaborating, loose (teamwork) |
| TKI | [moderate](../../data/traits/instructions/moderate.json) | extremist | pair | compromising, loose (politics) |
| TKI | [avoidant](../../data/traits/instructions/avoidant.json) | non-avoidant | singleton | avoiding, good |
| TKI | [accommodating](../../data/traits/instructions/accommodating.json) | unyielding | pair ([unyielding](../../data/traits/instructions/unyielding.json)) | accommodating, good |
| Coie | [popular](../../data/traits/instructions/popular.json) | [unpopular](../../data/traits/instructions/unpopular.json) | pair | popular |
| Coie | [unpopular](../../data/traits/instructions/unpopular.json) | popular | pair | rejected and neglected mixed |
| Rogers | [early-adopter](../../data/traits/instructions/early_adopter.json) | [late-adopter](../../data/traits/instructions/late_adopter.json) | pair | early adopters |
| Rogers | [late-adopter](../../data/traits/instructions/late_adopter.json) | early-adopter | pair | laggards |

The ZTPI and SVO members that are non-X singletons ([bitter](../../data/traits/instructions/bitter.json), [nostalgic](../../data/traits/instructions/nostalgic.json),
[fatalistic](../../data/traits/instructions/fatalistic.json)) lose the `singleton` when they join a set; the pair members take the
new arrangement beside their `pair`.  Nothing in W11 needs a new file or a check.

### W12: the roles

Every role named here is a `singleton` except the four Berry-square corners.
The September role audit ([ROLES_ADDED.md](../../data/roles/instructions/ROLES_ADDED.md),
coverage notes) already read life stage as "well covered" with widow, divorcee
and orphan as off-ramps, and migration as having "two natural axes: rootedness
(settled ↔ nomadic) and agency (chosen expatriate ↔ forced refugee)".  No
"adult" or "middle-aged" role exists; [parent](../../data/roles/instructions/parent.json) carries those years in the
sequence, and the trait [middle-aged](../../data/traits/instructions/middle_aged.json) covers them on the trait side
(decision 18).  [hybrid](../../data/roles/instructions/hybrid.json) ("child of two peoples ... belongs fully to neither
side") reads as a mythic [marginalized](../../data/roles/instructions/marginalized.json), not a Berry corner.

## Antonym checks to run (main agent)

Each about $0.03 to $0.05 (a staged regeneration under non-X where needed, then
the check), about $0.50 in all, live.  Record every answer, with the instructions
it read, in the check history before anything is regenerated again (AGENT_NOTES §
"Keep every sample").

| trait | how | for |
|---|---|---|
| [mystical](../../data/traits/instructions/mystical.json) | staged non-X regeneration, check | 4 |
| [materialist](../../data/traits/instructions/materialist.json) | check as it is (non-X already; never checked) | 4 |
| [rationalist](../../data/traits/instructions/rationalist.json) | check as it is (non-X already; never checked) | 4, the alternative |
| [meditative](../../data/traits/instructions/meditative.json) | staged non-X regeneration, check | 5 |
| [restless](../../data/traits/instructions/restless.json) | check again as it is (one sample so far) | 5 |
| [data-driven](../../data/traits/instructions/data_driven.json) | after the rewrite, non-X regeneration, check | 6 |
| [anecdotal](../../data/traits/instructions/anecdotal.json) | staged non-X regeneration, check (its one answer predates the V2 regeneration) | 6 |
| [efficient](../../data/traits/instructions/efficient.json) | after the rewrite, non-X regeneration, check | 7 |
| wasteful ([file to be created](../../data/traits/instructions/wasteful.json)) | after seeding, check | 7 |
| [paranoid](../../data/traits/instructions/paranoid.json), [vindictive](../../data/traits/instructions/vindictive.json), [iconoclastic](../../data/traits/instructions/iconoclastic.json), [perfectionist](../../data/traits/instructions/perfectionist.json) | staged non-X regeneration, check, discard the staging copy | 2, informational: expect [trusting](../../data/traits/instructions/trusting.json), [forgiving](../../data/traits/instructions/forgiving.json), [reverent](../../data/traits/instructions/reverent.json), [sloppy](../../data/traits/instructions/sloppy.json) |
| [subversive](../../data/traits/instructions/subversive.json) | the same | 2: [orthodox](../../data/traits/instructions/orthodox.json) supports the sequence, [conformist](../../data/traits/instructions/conformist.json) the spoke |

No check is needed for the other spokes before W3 and decision 1: under 1(a)
nothing about them changes, and under 1(b) the non-X regeneration brings a check
with it.

## Check results (main agent, 2026-10-09)

Run as listed, except data-driven, efficient and wasteful, which wait for
decisions 6 and 7.  The eight staged files were regenerated under non-X in a
scratch copy; the corpus is unchanged.  Every answer, with the instructions it
read, is in [antonym_check_history.jsonl](../../data/traits/antonym_check_history.jsonl).
About $0.47 in all.

| trait | answer (score) | expected | reading |
|---|---|---|---|
| [mystical](../../data/traits/instructions/mystical.json) (staged) | rationalist \| empiricist \| materialist (4) | materialist | names both candidates, rationalist first |
| [materialist](../../data/traits/instructions/materialist.json) | idealist \| spiritualist (4) | mystical | does not name mystical: decision 4 is one-way either way |
| [rationalist](../../data/traits/instructions/rationalist.json) | intuitive \| traditionalist (3) | mystical | does not name mystical |
| [meditative](../../data/traits/instructions/meditative.json) (staged) | restless \| impulsive \| reactive (3) | restless | restless first |
| [restless](../../data/traits/instructions/restless.json) | calm \| still \| tranquil (4) | meditative | does not name meditative (its second sample): decision 5 is one-way |
| [anecdotal](../../data/traits/instructions/anecdotal.json) (staged) | statistical \| data-driven \| empirical (4) | data-driven | data-driven second; decision 6 can go ahead to the rewrite |
| [paranoid](../../data/traits/instructions/paranoid.json) (staged) | trusting \| naive (3) | trusting | supports trusting → cynical → paranoid |
| [vindictive](../../data/traits/instructions/vindictive.json) (staged) | forgiving (4) | forgiving | supports forgiving → unforgiving → vindictive |
| [iconoclastic](../../data/traits/instructions/iconoclastic.json) (staged) | traditionalist \| conservative (4) | reverent | does not support the reverence sequence: iconoclastic opposes tradition, not reverence |
| [perfectionist](../../data/traits/instructions/perfectionist.json) (staged) | careless \| slapdash (3) | sloppy | sloppy's synonyms: supports sloppy → meticulous → perfectionist |
| [subversive](../../data/traits/instructions/subversive.json) (staged) | conformist \| orthodox (3) | orthodox | conformist first: by the sheet's own test, a spoke rather than a sequence |

So of decision 2's four sequences, three are supported and the reverence one is
not (iconoclastic is better read as a spoke, or against tradition).  Decisions 4
and 5 have no clean pair on offer: mystical and meditative each name their
candidate, but neither candidate names them back.
