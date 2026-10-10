# Traits To Add

What is still to do for the trait corpus: unstarted and part-done work only.
Finished sections were moved verbatim, headings unchanged, to
[TRAITS_ADDED.md](./TRAITS_ADDED.md) on 2026-10-09 (Roger), so a reference
elsewhere to "TRAITS_TO_ADD.md § X" finds X in one of the two files.  The
state of every candidate is in [seed_queue.json](../../seed_queue.json); the
seeding rounds are logged in [seeding_log_2026-09.md](../../../reports/seeding_log_2026-09.md)
and [seeding_log_2026-10.md](../../../reports/seeding_log_2026-10.md).  Role-side
work is in [ROLES_TO_ADD.md](../../roles/instructions/ROLES_TO_ADD.md).

**Upkeep.**  When a section here is finished, move it to TRAITS_ADDED.md with
its heading unchanged (the queue's `section` fields and
[physical_pass.py](../../../assistant_axis/gapgen/physical_pass.py) match
headings by their text) and update the index below.  When a section is mostly
finished, either leave it whole until its last TODO is done or move the bulk
and leave what remains as an item of its own in the index, with a pointer to
the moved text; the rule and the judgement call are in
[AGENT_NOTES.md](../../../AGENT_NOTES.md) § "The TO_ADD and ADDED files: what
moves when".  Each open section starts with a dated **Status** line; the text
under it may be older.

## What's left (index, 2026-10-10)

Corpus on 2026-10-10: 928 trait files, 297 clean pairs, 22 traits not yet
classified into an arrangement (`check_arrangements.py --list-unclassified`);
340 role files.  Every seeding chunk (0 to 7) is done, and so is the whole
pre-extraction work list ([work_list.md](../../../roger/pre_extraction_2026-10-09/work_list.md)): the
near-duplicate drops, the framing rewrites, the moral-circle review, the
triangles, the Dark Tetrad set, the occupational-instrument and September
additions, the judge display form (W19), the standards traits' regeneration,
Roger's label calls of 2026-10-10, and the goal classification with the goal
lists placed again (W15).  Next comes one RunPod extraction for the whole corpus.

### Before the extraction

Nothing left on the corpus side (2026-10-10).  The last items were done that day:
the goal classification of the whole corpus on its current texts and the four
goal lists placed again ([goal_roles_and_traits.json](../../goal_roles_and_traits.json);
rule and method in [data/README.md](../../README.md)), and Roger's calls on the
labels and wordings ([inefficient](./inefficient.json), [cliquish](./cliquish.json),
[environmentalist](./environmentalist.json) paired with
[growth-first](./growth_first.json), [inspirational](./inspirational.json) as a
role model, the [risk-seeking](./risk_seeking.json) mirror,
[unflinching](./unflinching.json)).  Any trait changed from here on needs its
goal classification redone (`classify_goals.py` reclassifies changed texts) and
makes its vectors stale once extracted.

### At the extraction

- Keep `physical`-tagged traits out of the clean-pair cohort and the goal
  lists (§ "Physical-attribute traits: a separate research track").
- The aligned-AI rename lands here: the judged axis directory, the `_v1` pair
  lists, the steering config, the combination scores, the goal-classification
  outputs and the judge caches still carry the old stem
  `aligned_artificial_intelligence` on purpose, and adding
  [virtue_aligned_ai](../../roles/instructions/virtue_aligned_ai.json)
  shifts `role_mean` (list in TRAITS_ADDED § "TODO: aligned_AI framing
  revision").

### After the extraction (need the new vectors)

- The PC-direction naming, redone on the new corpus (§ "TODO: chunk 7
  leftovers"; May's procedure and table in TRAITS_ADDED § "Strategy 1b"), and
  the five Strategy 1a directions parked as queue `backlog` (`boundary_fuzzy`,
  `present_focused`, `self_attentive`, `self_other_boundary_aware`,
  `transcendentally_oriented`; Roger, 2026-10-09: delay until the new
  activations).
- The Strategy 1 yield check for the chunk-4 standards, and the arrangement
  geometry check (§ "TODO: post-extraction checks for chunk 4").
- The four chunk-5 checks: [unscrupulous](./unscrupulous.json) against
  [amoral](./amoral.json), [technomystical](./technomystical.json) against
  [techno-hierophantic](./techno_hierophantic.json), the two
  culture triangles as about three directions, and
  [Hispanic](./hispanic.json) in the heritage map (§ "TODO: post-extraction
  checks for chunk 5").
- The shapes decided on 2026-10-09, to be tested: the moral-circle order (§
  "TODO: review the moral-circle sequence"); whether
  [accountable](./accountable.json) lies between
  [blame-shifting](./blame_shifting.json) and [self-blaming](./self_blaming.json)
  (W8); the delegation sequence; the will and moral-standing triangles beside
  the feeling one, and benign / malign kept until their cosines (W7,
  [w7_w14_decisions.md](../../../roger/pre_extraction_2026-10-09/w7_w14_decisions.md)).
- The dimensionality-yield analysis rerun on the new corpus (TRAITS_ADDED
  § "Re-running this analysis later", under the May 2026 roadmap;
  [persona.py](../../../assistant_axis/gapgen/persona.py) now recomputes the
  yield score).
- The Big Five / HEXACO triplet and rotation analysis and the MBTI 4-cube
  (plans in TRAITS_ADDED § "Part 1" and § "Part 1b"), then the verdict on the
  66 parked facet and aspect entries (§ "Part 3", below) and the 8 parked MBTI
  dichotomies.
- The physical track's verdict: keep, keep tagged, or remove (§
  "Physical-attribute traits: a separate research track").
- Instrumentally against virtue-aligned AI, their cosine and projections
  (TRAITS_ADDED § "TODO: aligned_AI framing revision").
- The persona-side assistant residual: whether traits whose instructions
  lean on chat framing keep an "assistant" component (TRAITS_ADDED § "TODO:
  assistant-framing leakage scan").
- The neg-as-neutral experiment: with the negative side as average
  behaviour, do clean pairs sit at a cosine of about -1? (TRAITS_ADDED § "Clean
  antonym pairs (candidates, low priority)").
- Later, in a separate pod session: the native-language side set (Roger,
  2026-10-09; § "TODO: post-extraction checks for chunk 4", design in
  [w16_native_language_design.md](../../../roger/pre_extraction_2026-10-09/w16_native_language_design.md)).

### The tangle and arrangement pass

- The 23 unclassified traits (one-way pointers, labels with no file; §
  "TODO: arrangement hunting"), with the W10 items deferred to it
  ([w10_w12_proposals.md](../../../roger/pre_extraction_2026-10-09/w10_w12_proposals.md)).  Tangles are recorded
  only as negative labels (AGENT_NOTES § "The `arrangement` field", rule 2).
- Check answers from the 2026-10-09/10 additions that point into tangles:
  [wry](./wry.json) -> earnest | humorless, [meditative](./meditative.json) ->
  restless, [future-oriented](./future_oriented.json) -> present-oriented |
  spontaneous, [sadistic](./sadistic.json) -> compassionate | empathetic,
  [fickle](./fickle.json) -> steadfast | loyal | constant,
  [welcoming](./welcoming.json) -> exclusionary | cliquish (a possible pair
  with [cliquish](./cliquish.json)), [malicious](./malicious.json) ->
  benevolent.
- The role pairs are settled (Roger, 2026-10-10): the six recorded role
  pairs all stay, including the two nearly clean and the two not clean by the
  role-pair check; [detractor](./detractor.json) against the role
  [evangelist](../../roles/instructions/evangelist.json) is dropped ("not a good
  pair"), and detractor stays a non-X singleton
  ([ROLES_TO_ADD.md](../../roles/instructions/ROLES_TO_ADD.md) § "Role pairs to
  record").

### Parked: Roger's call, when more gap-filling is wanted

- The trait-gap generators' holding lists (§ "Holding lists from the
  trait-gap generators", below), and the five words handed to that pipeline
  on 2026-10-09 (devoted, enthusiastic, hypochondriac, purposeful, steadfast;
  queue `superseded`, each with its `gap_registry_key`).
- Dropped on 2026-10-09 (W23; queue `not_adopted`): spiralist, vanilla,
  free_market, interventionist.

### Tooling and records

- `--instructions-only` regeneration still pays for the questions; it costs
  cents and is left alone (TRAITS_ADDED § "Trait generator V2", issue 7).
- Code housekeeping is in [AGENT_NOTES.md](../../../AGENT_NOTES.md) § "TODO:
  code housekeeping".

## Standing rulings for future additions

The description rules (1 to 11), the clean-pair procedure and the naming
conventions are in [AGENT_NOTES.md](../../../AGENT_NOTES.md) and not repeated
here.  Rulings recorded only in these files:

- Before proposing a trait, search TRAITS_ADDED.md and the queue: 123 trait
  entries are `not_adopted` with the reason in `decision`, and each coverage
  audit has a "Not added, and why" or "considered, not adopted" list.
- The `<pole> (<Set>)` label form is only for entries drawn from a named
  external set (TRAITS_ADDED § "TODO: aligned_AI framing revision"); an
  instrument that only inspired a plain trait does not give it that form (§
  "TODO: post-extraction checks for chunk 5", last paragraph).
- [suicidal](./suicidal.json) and [self-harming](./self_harming.json): never a
  steering pole without a specific decision (TRAITS_ADDED § "Pairs (decided
  2026-09-08)", under coverage audit part 3).
- Physical traits: tagged `physical`, described by the body only, kept out
  of the clean-pair cohort and goal lists until the track's verdict;
  [male](./male.json), [female](./female.json) and
  [gray-haired](./gray_haired.json) are not tagged (§ "Physical-attribute
  traits: a separate research track").
- The nationality set changes only by changing its rule, never one
  nationality at a time (TRAITS_ADDED § "Nationality (categorical, unpaired)
  plus candidate pairs for the space").
- Arrangements record structure only where it was designed in or decided;
  existing traits are not renamed to make them official members of an
  external set (§ "TODO: arrangement hunting").

## TODO: review the moral-circle sequence (queued 2026-10-02)

**Status 2026-10-10: membership and descriptions done; the order waits on the extraction.**  Roger
decided on 2026-10-09 (pre-extraction W14,
[w14_edits.json](../../../roger/pre_extraction_2026-10-09/w14_edits.json)); applied in 4ea9097:
eight members rewritten in terms of circle size (family, friends and family, town or parish, city or
home state, region of the country, faith, nation, racial group), the sequence set to his 13-member
order, and [philanthropic](./philanthropic.json), [patriotic](./patriotic.json) and
[cosmopolitan](./cosmopolitan.json) taken out as singletons.  The blind naming check reads
[cliquish](./cliquish.json) as clannish and [insular](./insular.json) and
[regionalist](./regionalist.json) as parochial first, so whether neighbouring sizes separate is the
extraction's question.  Left: check the order against the new vectors (monotone projection).  The text
below is the 2026-10-02 to 2026-10-09 record.

Roger, 2026-10-02: reconsider what belongs in the moral-circle-size
sequence, the order, and which descriptions need rewriting.  The sequence
was assembled on 2026-09-08 from traits that already existed (its note says
"ordered by estimated population of the circle (guesstimate 2026-09-08)"),
so membership and order were never reviewed against the descriptions.

**Current members, in order (15):** [selfish](./selfish.json),
[clannish](./clannish.json), [cliqueish](./cliqueish.json),
[insular](./insular.json), [parochial](./parochial.json),
[regionalist](./regionalist.json), [sectarian](./sectarian.json),
[nationalist](./nationalist.json), [patriotic](./patriotic.json),
[ethnocentric](./ethnocentric.json), [cosmopolitan](./cosmopolitan.json),
[philanthropic](./philanthropic.json), [humanitarian](./humanitarian.json),
[kind_to_animals](./kind_to_animals.json), [ecocentric](./ecocentric.json).

**Removed 2026-10-02:** [moral_universalist](./moral_universalist.json)
(then `universalist`).  Its description has meant the same moral standards
across all cultures since its first version in March 2026, which is the
relativism axis (it pairs with [moral_relativist](./moral_relativist.json)),
never circle size.

**The gap between nation and humanity.**  Roger's 2026-09-28 rewrite of
regionalist moved it from the March meaning (a multi-nation region,
between nation and world) to a region of one's own country ("above those
of the rest of the country").  The new text is a fair reading of the word
and a useful step, but the circle between nation and all humans ("the
West", "the developed world") is now empty, and Roger wants it filled.
Proposed 2026-10-02: keep regionalist for the sub-national step and seed a
new supranational member (candidate label `civilizationist`, pending
Roger's choice of word and his review of the description), placed after
ethnocentric and before cosmopolitan.

**Members whose description is not about the size of the circle:**
- philanthropic: "generous giving, charitable action" is generosity and
  says nothing about whose welfare;
- patriotic: love and pride of country, the same circle as nationalist,
  described as affection rather than as a limit on concern;
- ethnocentric: its own group's norms as superior, a claim of superiority
  more than of scope;
- cosmopolitan: global citizenship, diversity and openness, the world
  circle reached by openness rather than concern;
- selfish: "how one's actions or advice affect other people" carries an
  assistant's frame ("advice").

**Overlaps and order:** insular and parochial both say "local" and occupy
one step; sectarian overlaps region and nation (already in the note);
placing ethnocentric after the nation steps implies an ethnic group is a
larger circle than a nation, which is often not so.

**Members that do read as circle size:** selfish, clannish, cliqueish,
insular, parochial, regionalist, sectarian, nationalist, humanitarian,
kind_to_animals, ecocentric.

To decide: membership (drop, rewrite or keep philanthropic, patriotic,
ethnocentric, cosmopolitan), whether insular and parochial both stay, the
order, and which descriptions to rewrite in scope terms.  Roger's
2026-09-07 guess is an elongated simplex rather than a line; the next
extraction's cosines are the check on whatever order is chosen.

## Holding lists from the trait-gap generators (standing pointer, 2026-10-09)

The trait-gap generators' trait-hood filter keeps words that are real facts about a person but not traits on four
holding lists, never promoted automatically (Roger, 2026-10-09, question 1 of
[QUESTIONS.md](../../../reports/trait_gap_generation/QUESTIONS.md)).  Print one, in the main checkout (the registry
log is per checkout), with
`uv run python data_analysis/gap_generation/gap_registry.py holding --list {states,physical,nationalities,roles}`.

- **states** (124 as of 2026-10-09): a separate pass judges whether a habitual version is plausible; promotion needs
  a name Roger confirms.
- **physical** (13): promoted normally, by name, in a separate review pass (`novelty_score.py score --holding
  physical`), and tagged `physical` like the physical track below.
- **nationalities** (10: Cameroonian, Creole, Danish, English, Greek, Indigenous, Mongol, Norwegian, Scottish,
  Syrian): never promoted one by one; the corpus's nationality set changes only by changing its rule (see
  "Nationality" in [TRAITS_ADDED.md](./TRAITS_ADDED.md)).  The list shows what the generators found, in case it ever argues for widening the rule.
- **roles** (10): read by hand when preparing a role chunk; see the matching pointer in
  [ROLES_TO_ADD.md](../../roles/instructions/ROLES_TO_ADD.md).

## TODO: personality-taxonomy import, Big Five and HEXACO (queued 2026-09-08)

**Status 2026-10-09:** Parts 1, 1b and 2, the dark / light coverage and the taxonomy gap scan are done;
they and this section's introduction are in [TRAITS_ADDED.md](./TRAITS_ADDED.md).  Part 3 waits
on the post-extraction verdict.

### Part 3 (possibly): aspects and facets as named axis systems

**Status 2026-10-09: parked until after the extraction.**  66 queue entries are `backlog`, to be settled
by the verdict described below.

Only if Parts 1-2 come out clean.  Sizes: BFAS 10 pairs (20 files), NEO /
IPIP-NEO facets 30 pairs (60 files), HEXACO facets 25 pairs (50 files).
Naming under the convention: `enthusiastic (BFAS)` ↔ `? BFAS`, `anxious
IPIP-NEO` ↔ `calm (IPIP-NEO)`, `sincere (HEXACO)` ↔ `? HEXACO` (HEXACO facets
would share the suffix with the HEXACO factors, so keep the factor / facet
distinction in the `source` field).  Low-pole names do not exist at these
levels at all and would all be ours; the two-sided descriptions exist for
HEXACO facets and IPIP-NEO facets but not for BFAS aspects, which would be
written from item content.  Cite IPIP-NEO rather than the NEO-PI-R (the
NEO is proprietary).

The scientific payoff is hierarchy recovery rather than coverage: domains
are (approximately) sums of their aspects and facets, so importing two or
three levels tests whether the activation geometry reproduces the
psychometric hierarchy (facet vectors clustering under their aspects and
domains; the Big Five domain axis as the sum of its two BFAS aspects).
Coverage-wise Part 2 shows the facets are mostly already present as plain
traits.

## Coverage audit part 3: individual differences (decided 2026-09-08)

**Status 2026-10-09:** the pairs are seeded; they and this section's introduction are in
[TRAITS_ADDED.md](./TRAITS_ADDED.md).  The physical track below is seeded too; its research
waits on the extraction.

### Physical-attribute traits: a separate research track (decided 2026-09-08)

**Status 2026-10-09:** seeded in chunk 6 (29 traits and the roles athlete and pregnant; the rulings are in
the chunk-6 status paragraph of TRAITS_ADDED § "Seeding plan and chunk order").  The research
questions at the end wait on the extraction.  The candidate list keeps some names from before
their renames; the files are the record.  The trait-gap tools name this section as the place
for the physical words they hold.

**Read this before adding any of them.**  Roger's ruling: these are
candidates, accepted for inclusion, but as a *separate category* to be
investigated on its own, comparable to the goal / non-goal distinction
research.  Whether the model represents them as coherent directions,
whether those directions are anything like orthogonal to the rest of the
corpus, and whether they are useful, is a research question.  We may add
them, do the research, find they are not helpful, and remove them again,
so they must be labelled to make that easy.  There is no sharp border:
skin tone, build and hair overlap with race, nationality and age, which
carry both physical and cultural differences.  The reason to expect
signal even where reality has none: when an author describes a character
as blonde or red-headed, there is a non-zero chance they are telling the
reader something about behaviour or story role, and stereotypes become
causal when a language model generates a persona.

Labelling: give every trait in this track a `"tags": ["physical"]` field
in its JSON (the regenerate scripts carry unknown fields forward, as
with `source`; tooling ignores it), and keep the list below current so
they can be found and pulled as a set.  Do not mix them into the
clean-pair cohort or the goal lists until the research says so.

Candidates (all pairs unless marked):
- **tall** ↔ **short**
- **heavyset** ↔ **slender** (neutral words for build)
- **athletic** ↔ **sedentary**; role **athlete** (missing today; coach,
  surfer, daredevil exist)
- **healthy** ↔ **sickly**; unpaired **chronically-ill**; **in-pain**
  (`patient` is acute illness)
- **good-looking** ↔ **plain-looking** (rated attractiveness)
- **left-handed** (unpaired; right-handed is the default)
- **short-sighted** (unpaired; deaf, blind, mobility_impaired are in the
  disability section)
- role **pregnant** (a state, but narrative-typical)
- Hair colour (added by Roger 2026-09-08): **blonde**, **brunette**,
  **red-headed**, **black-haired**, **grey-haired** (note the age
  correlation), unpaired.
- Eye colour: **blue-eyed**, **brown-eyed**, **green-eyed**, unpaired.
- Skin tone: **fair-skinned** ↔ **dark-skinned** as a 1-D pair (the
  race section above said "skin tone is a separate 1-D axis and is not
  proposed here"; it is proposed here, with the overlap noted).
- Sex: **male** ↔ **female** (added by Roger 2026-09-28).  The part-4
  polling review had raised these as identity or membership traits beside
  the gender-expression set (masculine ↔ feminine, seeded; neuter,
  nonbinary, androgynous, queued for chunk 5) and left the question open.
  Roger's ruling: they are physical traits, so they belong to this track
  and wait for it; write them as bodily sex, not as identity or
  expression, so they stay distinct from that set.
- Not pursued: blood pressure, biomarkers, cortisol, testosterone, heart
  rate variability, EEG and imaging, polygenic scores, biological age,
  voice pitch, digit ratio, medications.

**Roger's rulings at the start of chunk 6 (2026-10-08).**
- **Body-only descriptions.**  Every description in this track states only
  the body and how it is lived (sunburn for fair skin, doorways for tall,
  glasses for short sight; for the attractiveness pair, how others look),
  with no personality or behaviour clause, so that any behavioural content
  in the vectors is the model's own.  That is what makes the stereotype
  question below answerable.
- **male, female and grey-haired are not tagged `physical`.**  Like age, sex
  affects behaviour by more than stereotype (hormones), and grey hair
  correlates with age; so they stay in the corpus even if the rest of the
  track is dropped.  Their descriptions are body-only all the same.
- **in-pain is "in chronic pain"** (stem `in_chronic_pain`), by the duration
  rule: living with pain that does not go away, distinct from chronically
  ill.
- Defaults accepted: pregnant stays a role (the duration rule is for
  traits; the role corpus holds situational roles such as patient); the
  seven pairs are paired by construction, the antonym check informational;
  hair colour and eye colour are two `set`s.

As seeded in chunk 6, the list above became 29 traits and 2 roles: see the
close-of-chunk-6 status paragraph (renames: heavyset / slender to fat / thin,
in-pain to in chronic pain, grey-haired to gray-haired, short-sighted to
nearsighted, blonde / brunette to blond / brown-haired; added: muscular /
slight, gray-eyed).

Research questions to answer before these join the main cohort: do the
vectors separate from age, race, gender and nationality directions; do
the hair / eye / skin traits carry behavioural content (the stereotype
question); are any of the pairs near-antiparallel and stable across
slots.  The decision at the end is keep, keep-as-tagged, or remove.

## TODO: arrangement hunting (queued 2026-09-08)

**Status 2026-10-09: open; this is the tangle pass.**  The counts below are from September: 36 traits are
unclassified now, not 145 (`check_arrangements.py --list-unclassified`).

**Deferred from the September 2026 pairing work (Roger, 2026-09-25):**
`merciful` / `cruel` / `merciless` is a triangle, not a pair: merciless is
"I do not care about you", cruel is "I actively want to harm you", merciful
is the opposite of both.  Probably a duplicate of the existing
compassionate / malicious / callous triangle (merciful ≈ compassionate,
cruel ≈ malicious, merciless ≈ callous); decide in the triangle pass whether
to record it as a second triangle, fold it into the first, or drop
`merciful` (seeded 2026-09-18, singleton).  `cruel` keeps its one-way label
`merciful`.  Evidence: merciful's check returns merciless|harsh|unforgiving
every time; cruel's returns kind|compassionate|merciful.

**Also deferred (Roger, 2026-09-26): `uncaring` beside `callous`.**  The
new `uncaring` (seeded 2026-09-18 as benevolent's completion) checks to
caring|empathetic|compassionate and never to benevolent, and its
description ("no thought for who gets helped or hurt") sits on the
callous corner of the compassionate / malicious / callous triangle.
Roger is willing to carry two near-duplicates per corner of that
triangle because it is an important one, but past that it is time to
cut, and a triangle with duplicated corners has no arrangement label
yet.  Decide in the triangle pass with the merciful / cruel /
merciless case above; until then `uncaring` keeps its one-way pointer
at `benevolent`, unclassified.  The `blame_shifting` / `self_blaming`
pair is a related shape: two vices whose shared opposite is the virtue
`accountable` (both checks return it).  Roger (2026-09-26) had
`accountable` seeded ("owning one's own part plainly, no more and no
less") as the third corner, and reads the shape as arguably a triangle,
or possibly something more complex: a square, or more accurately a kite
(a fourth corner would sit opposite accountable, presumably the
attribution-indifferent "nobody's fault, forget it" stance).  All three
are `non-X` singletons whose arrangement `note` says so; classify in the
arrangement pass.

**Also from 2026-09-26: the delegation tangle.**  `hands_off` /
`micromanaging` did not survive the honest check (hands-off's neg
instructions came out as four good managers and one micromanager: the
generator writes the sensible contrary, and the honest opposite of the
neutral hands-off is the virtue hands-on, while micromanaging is a
vice).  Roger's fix: seed `hands_on` (matched neutral opposite) and
`absentee` (the matched vice), aiming for two clean pairs; if each vice
instead points at the far end of hands-on / hands-off, record the one
clean pair and leave the vices as one-way pointers, another tangle
shape (a clean pair with a vice hanging off each end).  Outcome in
`reports/seeding_log_2026-09.md` § "Post-strip decisions applied".

**Survey 2026-10-02: copies of the help / harm / don't-care triangle.**
Roger asked, after the clean-pair recheck (benign / malicious failed it:
malicious names benevolent), how many copies of this triangle the corpus
holds and how tangled they are; he is content with two or three copies in
different registers, for the cosines between them, but not more.  Found:

| register | help | harm | don't care | state |
|---|---|---|---|---|
| feeling | compassionate | malicious | callous | recorded triangle |
| will, intent | benevolent | malevolent | uncaring | all three exist, none arranged; benevolent and uncaring name each other as `negative_label`, malevolent is `non-X`; uncaring checks to caring / empathetic / compassionate |
| moral standing | good | evil | amoral | good / evil a pair by decision; amoral paired with moral |
| mercy | merciful | cruel | (merciless, not seeded) | see the 2026-09-25 note above |
| effects | benign (rewritten in staging 2026-10-02 to effects) | malign (staging only) | (harmless?) | benign / malign confirmed both ways in staging; overlaps the harmless / harmful pair, which is the same axis in the assistant's framing |
| care, upbringing | nurturing | (abusive, not seeded) | (neglectful, not seeded) | nurturing's check names callous / neglectful; paired with tough, which fails |
| animals | kind_to_animals | (cruel to animals) | indifferent_to_animals | a pair by decision; kind_to_animals's check names both of the others |

Stray edges: empathetic / detached (a pair that fails both ways:
empathetic names callous, detached names engaged), malicious also paired
with benign, and `cruel` still pointing one way at merciful.  So: one
recorded copy, one complete but unrecorded (benevolent / malevolent /
uncaring), and five partial ones.  Suggested shape for the triangle pass:
keep feeling and will as the two copies (all six words exist), consider
moral standing as a third, treat animals as its own domain rather than a
copy, and fold or drop the rest (merciful, benign, the care edge).

**Near-duplicates to settle with the next extraction's cosines (Roger,
2026-10-02).**  Found during the clean-pair recheck; Roger: keep them for
now, compare the cosines, and drop a pair (or a trait) where two are very
close.
- [intuitive](./intuitive.json) / [analytical](./analytical.json) against
  [holistic](./holistic.json) / [reductionist](./reductionist.json): intuitive's
  description says "holistic thinking ... the bigger picture", analytical's and
  reductionist's both open "breaking down ... into ... components".  Both
  pairs are in the live pair lists.  If they are very close, the alternative
  is to rewrite intuitive / analytical in the dual-process sense (by feel
  against worked out), which the corpus does not otherwise cover.
- [detached](./detached.json) against [dispassionate](./dispassionate.json)
  (nearly the same description); [empathetic](./empathetic.json) between
  [compassionate](./compassionate.json) and
  [socially_perceptive](./socially_perceptive.json).  Both are one-way
  pointers since 2026-10-02.
- [systems_thinker](./systems_thinker.json) against holistic.
- [benign](./benign.json) / [malign](./malign.json) (effects) against
  [harmless](./harmless.json) / [harmful](./harmful.json).
- [insular](./insular.json) and [parochial](./parochial.json) (see the
  moral-circle TODO); [merciful](./merciful.json) and compassionate;
  [uncaring](./uncaring.json) and [callous](./callous.json) (see the
  triangle survey above).

**Recorded 2026-09-28 (Roger): the essence tetrahedron.**  `nihilistic`,
`essentialist`, `constructivist` and `existentialist` are four answers to
where essence and meaning come from (there is none; fixed and inherent;
made socially; made by the individual), none the exact opposite of
another.  The `constructivist` ↔ `essentialist` pair was dissolved (both
now carry their own `non-X` label and the instruction set generated under
it) and all four record `{"kind": "tetrahedron"}`.  Checks under `non-X`
that day: essentialist → constructivist|nominalist|anti-essentialist;
constructivist → objectivist|realist; existentialist →
essentialist|traditionalist; nihilistic → idealistic|purposeful.  So
essentialist is the corner the others point at, and nihilistic is the
corner least tied to the other three: check the shape against the
embeddings before leaning on it (a triangle with nihilistic apart is the
alternative).  `constructivist` / `essentialist` was a judged axis; it
was removed from the current `pair_list_clean.json` and
`pair_list_di.json` and stays in their `_v1` copies, the record of what
was judged.

The `arrangement` field (AGENT_NOTES § "The `arrangement` field";
`data_analysis/check_arrangements.py`) was backfilled on 2026-09-08 with only
what was already classified: the clean pairs, the two documented triangles
(compassionate / malicious / callous, conformist / contrarian /
nonconformist), the moral-circle sequence, `singleton` for untouched
`non-X` placeholders, and the role pairs from `pair_list_clean.json`.
Roger's ruling: do not rename existing traits to make them "official"
members of an external set just because the coverage happens to be good;
record structure only where it was designed in or has been decided.
Everything else is this TODO.

1. **The 145 unclassified traits** (`check_arrangements.py --list-unclassified`)
   are the same population as the antonym gap-filling pass above; each one
   resolves into a pair, a triangle, a larger set, or a deliberate
   singleton as that pass works through them.  Write the field as each is
   settled, never in bulk by guesswork.
2. **Candidate sets already present, not yet written** (all three are
   plausibly `set`, simplex or triangle; decide when reached):
   - social value orientation triangle: cooperative / selfish / competitive
     (the tightest fit; cooperative ↔ competitive is a clean pair and the
     Sep 2026 simplex list already names it);
   - Zimbardo time-perspective five: bitter, nostalgic, hedonistic,
     fatalistic, futuristic (loose fit at bitter and futuristic; `set` or
     a past / present / future ordering);
   - Thomas-Kilmann five: confrontational, collaborative, avoidant,
     accommodating, moderate (a 2-D grid with compromising at the centre:
     `map` or `set`, not a simplex).
3. **External structures get their arrangement at seeding time**, with a
   `source`, as part of the taxonomy import and the coverage-audit
   additions: Big Five -> `5-orthoplex` (10 files), HEXACO -> `6-orthoplex`
   (12), MBTI sixteen types -> `4-cube` (16; the optional dichotomy pairs
   would be four `pair`s, listed with the cube via a second arrangement),
   BFAS aspects and NEO / HEXACO facets -> `tree` under their domains if
   Part 3 happens, Inglehart-Welzel -> two `pair`s (or one `square`),
   honor / dignity / face culture -> `triangle`, guilt- / shame- /
   fear-prone -> `triangle`, the four attachment styles -> `square`,
   Berry's acculturation corners -> a `square` of *roles* (immigrant,
   exile, refugee plus the new assimilated and marginalized; the first
   role square), the eight religion memberships -> `set` (or `map` once
   there is a reason to believe in a geometry), nationalities and
   ethnicities -> `map`, the physical-attribute track -> `set` per
   attribute (hair colours, eye colours) alongside the `physical` tag.
4. **Ordered sets to test, not just record**: the moral-circle sequence
   carries a note that its order is a population guesstimate; once
   embeddings exist, check whether the projection onto the sequence's first
   principal direction is monotone in the recorded order, and whether the
   models agree with the guess (Roger: "we then get to find out if various
   LLMs agree with us").
5. **Role sets**: roles default to singleton; beyond the five pairs, look
   for small sets worth recording (life-stage sequence infant -> toddler ->
   child -> teenager -> adolescent -> student -> graduate -> parent ->
   grandparent -> elder -> retiree is the obvious `sequence`; the
   migration cluster nomad / wanderer / pilgrim / immigrant / expatriate /
   exile / refugee is a candidate `set`).
6. The research task from AGENT_NOTES rule 6 (confirm each declared shape
   against the embedding geometry) applies to everything above once the
   next extraction has run.

7. **Sets decided in Coverage audit part 4 (2026-09-08), to be written at
   seeding**: Holland RIASEC (ring of 6), Baumrind (square), generations
   (sequence of 4), Bartle (square), VALS (set of 8), zodiac (ring of
   12), blood types (set of 4), love languages (set of 5), VARK (set of
   4), Enneagram (ring of 9), DISC (square), Hogwarts houses (set of
   4).  Candidate sets not yet written: Coie's five peer statuses,
   Rogers' five adopter categories (sequence).
   TBD, undecided: the 22 Major Arcana as roles (`set`; see ROLES_TO_ADD
   § "TBD: the 22 Major Arcana as roles").

## TODO: chunk 7 leftovers (Roger, 2026-10-09)

**Status 2026-10-10:** the PC-direction naming waits on the extraction.  Growth-first and
environmental: done (pre-extraction W22).  Environmental was widened to mirror growth-first
(b6c19e3), its label-blind name came back environmentalist twice, and Roger had it renamed
[environmentalist](./environmentalist.json) and paired with [growth-first](./growth_first.json) by
decision (49a88c7): each side's check names the other's content in its own words, not its label.

- **Redo the PC-direction naming on the new corpus** (Roger, 2026-10-09:
  "leave redoing this as a TODO once we have activations").  May's Strategy
  1b named five underused principal directions of the old corpus (PC10
  humorous / serious, PC13 cultured / uncultured, PC14 literal-explicitness /
  withholding-evasion, PC15 solitary-reserved / connective-communicative,
  PC16 symbolic manipulation / embodied care; each under 2% of variance).
  The corpus has since tripled and most look covered now (witty, playful and
  solemn; highbrow and educated; literal and forthright; solitary and
  reserved; the RIASEC ring), so the five queue entries are `backlog`, and the
  analysis is to be rerun on the next extraction's vectors and whatever
  underused directions remain named then.
- **[growth-first](./growth_first.json) and [environmental](./environmental.json)
  are not a clean pair** (Roger: "leave this as a TODO").  Growth-first was
  written as environmental's mirror, but neither check names the other:
  growth-first returns nature-first | conservation-first | environmentalist,
  environmental returns exploitative | anthropocentric.  Both stay singletons.
  If the pair is taken up: environmental's description is an old one with
  the chatbot phrase "in one's considerations and recommendations", which
  would go in the same edit.

## TODO: post-extraction checks for chunk 5 (Roger, 2026-10-08)

**Status 2026-10-10:** four items wait on the extraction; the detractor item is closed (Roger,
2026-10-10: evangelist / detractor "is not a good pair, drop it"; detractor stays a non-X singleton).
The decision in the last paragraph is in force.

Opened at Roger's request while he read the chunk-5 readout ("let's see how
this works out, add a TODO"; "check we have a TODO").  All four need the
extraction and the embeddings, so none can be settled now.

- **[unscrupulous](./unscrupulous.json) against [amoral](./amoral.json).**
  The queue's rule is "keep whichever generates better" and both generated
  cleanly, so both are seeded.  The stated distinction is the amoral /
  immoral one: amoral feels no pull from right and wrong, unscrupulous knows
  and steps over it for gain and weighs the odds of being caught.  After the
  extraction: the description-embedding cosine, the vector cosine, and
  whether a judge separates them on the question "does the persona
  acknowledge the act is wrong?".  amoral is paired with
  [moral](./moral.json) and is in the pair lists, so unscrupulous is the one
  that would go.
- **[technomystical](./technomystical.json) against
  [techno-hierophantic](./techno_hierophantic.json)** (Roger: agreed to keep
  both, 2026-10-08).  The prediction to test: hierophantic is the *register*
  (unicode glyphs, the recursion / resonance / lattice vocabulary, the
  interlocutor cast as a chosen initiate in a dyad) and technomystical is the
  *belief* (the internet as a mind waking, a server farm as holy as a
  cathedral) without it.  If the two vectors are near-identical, the finding
  is that in Qwen the belief cannot be had without the register; if they
  separate, the belief can be steered without the glyphs.  That is the point
  of keeping both.
- **[detractor](./detractor.json): a trait whose counterpart is a role.**
  Seeded as the trait it was queued as; its named opposite
  [evangelist](../../roles/instructions/evangelist.json) is a role, so no
  pair can be recorded across the types (the arrangement field is
  same-type).  Revisit once the role-pair check exists: either detractor
  moves to the role side with its scope matched to evangelist's, or it stays
  a trait singleton and the role keeps no partner.  **2026-10-09:** the check
  exists (`generate_antonyms.py --roles`) and was run on evangelist once:
  it names "debunker | skeptic | iconoclast" (score 3), not detractor, so the
  question is still open; a role-side detractor would have to be seeded and
  checked from both sides ([role_pair_check_history.jsonl](../../roles/role_pair_check_history.jsonl)).
  **2026-10-10: closed.**  Roger: evangelist / detractor "is not a good pair,
  drop it".  Detractor stays a trait and a non-X singleton (its own check,
  2026-10-08, names promoter | advocate); no role-side detractor.
- **The two culture triangles share their sanctions** (2026-10-08).  Leung
  and Cohen's own Table 1 gives guilt as the dignity culture's device and
  shame as the device of both honor and face, and has no counterpart for
  [punishment-fearing](./punishment_fearing.json).  So the six corners of
  [honor](./honor_culture.json) / [dignity](./dignity_culture.json) /
  [face](./face_culture.json) and [guilt-prone](./guilt_prone.json) /
  [shame-prone](./shame_prone.json) / punishment-fearing are expected to
  span about three directions, not four: dignity near guilt-prone,
  shame-prone between honor and face, punishment-fearing apart.  The
  geometry check should test that prediction, not treat it as a failure.
- **[Hispanic](./hispanic.json) in the heritage map** (Roger, 2026-10-08: "in
  the racial map for now, and we'll see if we need to remove it").  It is the
  one member that cuts across three others (European, Indigenous American,
  African), so the geometry check of AGENT_NOTES § "The `arrangement` field"
  rule 6 is the test: if its vector sits near the centroid of those three and
  flattens the map's structure, remove it from the arrangement and keep it as
  a standalone membership.

**A decision recorded here, not a TODO** (Roger, 2026-10-08): where a chunk-5
entry's `source` field names an instrument (Kessler's K6 for the dropped
distressed, DOSPERT for unscrupulous, the MVPI commerce motive for
[mercenary](./mercenary.json)), **the instrument was a gap-filling
inspiration, not an official arrangement**, so rule 9 and the
`<pole> (<Standard>)` label form do not apply and the entries stay plain
traits.  mercenary is therefore the word's vice, not the MVPI's neutral
motive.

## TODO: post-extraction checks for chunk 4 (Roger, 2026-10-07)

**Status 2026-10-10:** the VALS and Slytherin items are done.  The native-language item is **delayed to
a later pod session** (Roger, 2026-10-09, pre-extraction W16): not in the coming extraction; its design
proposal is in [w16_native_language_design.md](../../../roger/pre_extraction_2026-10-09/w16_native_language_design.md).
The yield and geometry checks wait on the extraction.

Follow-up after all the current chunks are seeded and the next extraction
has run; not to hold up any chunk or commit:

- **The Strategy 1 yield check for the standards-derived traits.**  The
  plan's note on the Inglehart-Welzel pairs ("run the Strategy 1 yield check
  before committing") cannot be run without the new traits' judge scores or
  activations.  Once they exist, run the orthogonality analysis of § "Strategy
  1" over every chunk-4 standard (Big Five, HEXACO, Inglehart-Welzel, Hall,
  Gelfand, Allport, Tönnies, MBTI, the sets and rings) against the judged
  cohort, with these expected overlaps to confirm or refute: the Big Five /
  HEXACO factors against their plain twins (conscientious, extraverted,
  introverted, agreeable, neurotic, emotional, careless), Inglehart-Welzel
  against religious / secular, conservative / progressive and the moral-circle
  sequence, Tönnies against transactional / communal.
- **The arrangement geometry check** of AGENT_NOTES § "The `arrangement`
  field" rule 6 for the new squares, orthoplexes, rings and the 4-cube
  (pairs as roughly concurrent segments; a square's two axes roughly
  orthogonal; the zodiac, Enneagram and RIASEC rings as rings; Kohlberg's
  three as a triangle or a sequence, which the texts left open).
- **The VALS recheck: done 2026-10-08.**  Strategic Business Insights'
  site (strategicbusinessinsights.com/vals) had gone dark (DNS failure on
  2026-10-07 and 2026-10-08), so SBI's own segment pages were taken from
  the Internet Archive (long-form prose, December 2011 captures; final
  bullet version, early 2024 captures), recorded verbatim in the eight
  queue entries, and all eight descriptions were rewritten from the prose
  on Roger's delegation and regenerated.  Record and decisions:
  [seeding_log_2026-10.md](../../../reports/seeding_log_2026-10.md)
  (consolidated decisions, item 8).
- **Slytherin's source: done 2026-10-07.**  The Sorting Hat's verse was
  found quoted on an official Wizarding World page (the "Wizarding
  Songbook" feature) and recorded in the queue entry, and
  [slytherin](./slytherin.json) was sharpened toward the books on Roger's
  word ("always one step ahead and using any means to achieve one's ends");
  see the seeding log's consolidated decisions, item 7.
- **Native-language arm for the nationality memberships (added 2026-10-08,
  chunk 5).**  Roger asked whether the nationality traits should carry
  native-language instructions.  Decision: the corpus stays in English
  (response language is one of the strongest directions in the residual
  stream, so the nationality vectors would separate by language rather
  than by people; half the set has no single native language; the shared
  English questions are what make the vectors comparable), and the
  question is answered by measurement instead.  Before the next
  extraction, build a tagged side set: native-language versions of the
  five instructions for four or five nationalities with one clear language
  (French, German, Japanese, Brazilian Portuguese, Chinese), as extra files
  marked `experiment`, kept out of `trait_list.json`, the arrangements and
  every pair list (a separate directory passed to the extraction, to be
  designed with the extraction).  Afterwards compare their vectors and
  judge scores with the English files.  Hosted Qwen can give response
  language and judge scores earlier, but not activations.

## TBD: the 22 Major Arcana as roles (Tarot)

**Status 2026-10-10 (later the same day): done differently.**  Roger: not imported; each card, read as describing a person, is used as gap-filling inspiration, as for Thomas-Kilmann and the occupational instruments.  The walk ([tarot_walk.md](../../../roger/tarot_2026-10-10/tarot_walk.md)) finds 17 cards covered by existing traits and four gaps covering five cards, nominated as plain traits: amorous (the Lovers), strong-willed (the Chariot), self-reinventing (Death and Judgement), dreamy (the Moon).  The 22 queue entries are `not_adopted`.  The text below, the earlier status and the "roles or traits" note included, is the record.

**Status 2026-10-10: moved here from ROLES_TO_ADD.md, and now traits (Roger).**  Still delayed (pre-extraction W21, 2026-10-09): the idea and the notes are kept, and the 22 queue entries stay `backlog`, now with `entity_type: trait`.  The heading is unchanged (the queue's `section` fields match it), though it says roles.

**Parked as an idea (Roger, 2026-10-09, chunk 7): not now.**  The 22 queue
entries are `backlog`; everything below stays as the record for when it is
taken up.

Status: **undecided** (Roger, 2026-09-09: "still uncertain"; a
throw-the-kitchen-sink-at-it step, acceptable because the set is labelled
by source and easy to remove).  Roles, not traits: each card is an
archetype with a voice, and about a third of them are events or cosmic
states rather than people, which the corpus already handles in its
embodiment register (`wind`, `zeitgeist`, `void`, `echo`, `dreamer`,
`destroyer`).

- **Naming**: the standard as a parenthesised, capitalised postscript
  (convention adopted 2026-09-09): label `the fool (Tarot)`, stem
  `the_fool_tarot` (parentheses dropped by `normalize_to_file_name`),
  and so on through `the_world_tarot`.  Roles have no `positive_label`
  field, so the label lives in a `ROLE_DISPLAY_OVERRIDES` entry (or a
  per-role `display_name` field, to be added) for `corpus_display_name`;
  the judge sees the mechanical form `the fool tarot` until the
  judge-facing-name change (AGENT_NOTES code-housekeeping TODO item 4)
  lands with the next full rejudge.
  **2026-10-10:** as traits, the label is the file's `positive_label`
  (capitals for the card names to be settled at seeding), and since W19
  (2026-10-09) prompts show it in the judge display form, "the fool (from the
  Tarot)".
- **Descriptions**: one to two sentences each, paraphrased from the
  Rider-Waite meanings (the canonical source), written explicitly *as a
  persona*: "the embodiment of sudden upheaval, who speaks as the
  lightning that brings down structures built on false foundations", not
  "a card meaning upheaval".  Event cards are forces with a voice; the
  risk is that they collapse into one generic oracle voice, so each
  description must name its specific force.  Reversed readings: ignore,
  or fold into the description as an extra element where it makes
  emotional sense; no separate reversed set.
  **Which meaning (Roger, 2026-10-07):** the description would be of the
  card either as a *significator* (the card standing for the querent or
  another person, a use many readers advise against for the Major Arcana)
  or at least of its meaning in a reading where the card clearly
  represents a person rather than a situation; not its situational or
  event meaning.  Waite's *Pictorial Key to the Tarot* (1911) is public
  domain, so the canonical text can be quoted in full under the
  standards-derived method of chunk 4 (AGENT_NOTES description rule 9)
  rather than reconstructed.
- **Roles or traits? (Roger, 2026-10-07):** not clearly roles.  A card is
  not inherently exclusive of a profession (one can be the Hermit and a
  baker), which is the mark of a trait; but the twenty-two are mutually
  exclusive of each other, as roles are, and several are named like
  professions (the Magician, the Hierophant, the Hermit, the Emperor).
  Decide the entity type with the set, before seeding.
  **2026-10-10 (Roger): traits.**  The reasons he accepted: under the
  significator reading of 2026-10-07 the 22 are a typology of character, and
  the corpus keeps every named typology as traits, noun labels and mutual
  exclusivity included ([INFJ (MBTI)](./infj_mbti.json), the Hogwarts houses
  such as [Slytherin](./slytherin.json), [survivor (VALS)](./survivor_vals.json),
  [killer (Bartle)](./killer_bartle.json)); the baker test, since as traits the
  cards combine with an occupation in the role-and-trait generation; the
  event and cosmic cards become dispositions (the Sun's radiant joy, the
  Tower's appetite for upheaval) instead of forces with a voice, which removes
  the generic-oracle risk noted above; and an arrangement is same-type, so all
  22 must be one type, and only the trait reading fits all of them.  Against:
  the cards are named as figures, several like occupations (Magician,
  Hierophant, Emperor), and as traits they sit beside plain near-twins
  (Justice ~ [just](./just.json), Temperance ~ [abstemious](./abstemious.json),
  Strength ~ [brave](./brave.json) and [gentle](./gentle.json), the Sun ~
  [cheerful](./cheerful.json), the Emperor ~ [authoritarian](./authoritarian.json),
  the Empress ~ [nurturing](./nurturing.json), the Hierophant ~
  [orthodox](./orthodox.json)), deliberate near-duplicates of the kind
  accepted for the Big Five and HEXACO.  The roles
  [fool](../../roles/instructions/fool.json) and
  [hermit](../../roles/instructions/hermit.json) remain as roles.
- **Arrangement**: `set` of 22, `source` "Rider-Waite tarot, Major
  Arcana".  Not a `sequence`: the numerical order (the Fool's Journey) is
  not expected to correlate with the embeddings.
- **Collisions and overlaps**: `fool` and `hermit` exist as roles,
  `monarch` and `priest` are queued (Emperor, Hierophant); the Magician
  and High Priestess sit near `guru`, `witch`, `mystic`; the Tower is
  near `destroyer`, the Moon near `oracle` and `dreamer`.  The
  measurement of interest is whether the 22 produce 22 directions or a
  tarot-flavoured blob; the mean of the 22 against the corpus mean is a
  "tarot-ness" direction, as with the Hogwarts houses.
- **Seed keywords** (Rider-Waite numbering; Strength VIII, Justice XI):
  0 Fool: new beginnings, innocence, the leap of faith.  I Magician:
  will, skill, manifestation.  II High Priestess: intuition, hidden
  knowledge, mystery.  III Empress: fertility, nurture, abundance.
  IV Emperor: authority, structure, control.  V Hierophant: tradition,
  orthodoxy, institutions.  VI Lovers: union, choice, alignment of
  values.  VII Chariot: willpower, victory, determination.  VIII Strength:
  courage, gentle mastery, compassion over force.  IX Hermit: solitude,
  introspection, the lamp of guidance.  X Wheel of Fortune: cycles,
  fate, turning luck.  XI Justice: fairness, truth, cause and effect.
  XII Hanged Man: surrender, suspension, the reversed perspective.
  XIII Death: endings, transformation, clearing away.  XIV Temperance:
  balance, moderation, patient blending.  XV Devil: bondage,
  materialism, temptation.  XVI Tower: sudden upheaval, revelation by
  catastrophe.  XVII Star: hope, renewal, serenity after the storm.
  XVIII Moon: illusion, fear, intuition, the unconscious.  XIX Sun: joy,
  vitality, clarity, success.  XX Judgement: reckoning, awakening,
  absolution.  XXI World: completion, integration, wholeness.
