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

## What's left (index, 2026-10-09)

Corpus on 2026-10-09: 916 trait files, 291 pairs, 36 traits not yet
classified into an arrangement (`check_arrangements.py --list-unclassified`);
340 roles.  Every seeding chunk (0 to 7) is done.  Next comes one RunPod
extraction for the whole corpus.

### Before the extraction

Cheap now; afterwards any change to a trait makes its vectors stale.

- **Goal classification is far behind.**
  [goal_classifications.json](../../../data_analysis/output/goal_classifications.json)
  dates from April and covers 285 of 916 traits and 278 of 340 roles.  It
  feeds [goal_roles_and_traits.json](../../goal_roles_and_traits.json), which
  the pipeline's combined role-and-trait generation reads, so it is needed
  before the extraction if the run includes combinations.  A full run is over
  $20 (AGENT_NOTES estimates about $100), so it goes through the
  expensive-operations confirmation; the goal tiers are then placed by hand.
  (From TRAITS_ADDED § "Housekeeping once the directory settles", item 3.)
- **The native-language side set** for the nationality memberships: design
  it into the extraction run, or drop it (§ "TODO: post-extraction checks for
  chunk 4", last item; it is filed under post-extraction but must be built
  before the run).
- **Rename [historical](./historical.json)** (§ "TODO: rename `historical`").
- **Near-duplicate drops** (§ "TODO: near-duplicate traits to drop or
  merge"): 18 rows, none acted on.  The list was calibrated on 663 traits, so
  rerun it on all 916 first.
- **Advisor framing left in a few descriptions.**  No description says "user"
  any more, but some still frame the trait as answering or advising someone:
  an audit on 2026-10-09 named [cautious](./cautious.json),
  [bold](./bold.json), [verbose](./verbose.json),
  [patient](./patient.json) and [environmental](./environmental.json), and
  the 2026-09-28 review found "urging others" in cautious, bold and
  [risk-seeking](./risk_seeking.json).  Read and decide; each edit
  regenerates that trait.  (From TRAITS_ADDED § "TODO: assistant-framing
  leakage scan".)
- Optional: **[growth-first](./growth_first.json) and
  [environmental](./environmental.json) as a pair** (§ "TODO: chunk 7
  leftovers").
- Optional: **the moral-circle sequence review** (§ "TODO: review the
  moral-circle sequence"): membership and scope rewrites are description
  edits, so they are cheaper before; the order is checked after.

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
  leftovers"; May's procedure and table in TRAITS_ADDED § "Strategy 1b").
- The Strategy 1 yield check for the chunk-4 standards, and the arrangement
  geometry check (§ "TODO: post-extraction checks for chunk 4").
- The five chunk-5 checks: [unscrupulous](./unscrupulous.json) against
  [amoral](./amoral.json), [technomystical](./technomystical.json) against
  [techno-hierophantic](./techno_hierophantic.json),
  [detractor](./detractor.json) (the role-pair check, run once on 2026-10-09,
  has [evangelist](../../roles/instructions/evangelist.json) naming "debunker |
  skeptic | iconoclast", not detractor; the question below stands), the two
  culture triangles as about three directions, and
  [Hispanic](./hispanic.json) in the heritage map (§ "TODO: post-extraction
  checks for chunk 5").
- The dimensionality-yield analysis rerun on the new corpus (TRAITS_ADDED
  § "Re-running this analysis later", under the May 2026 roadmap;
  [persona.py](../../../assistant_axis/gapgen/persona.py) now recomputes the
  yield score).
- The Big Five / HEXACO triplet and rotation analysis and the MBTI 4-cube
  (plans in TRAITS_ADDED § "Part 1" and § "Part 1b"), then the verdict on the
  66 parked facet and aspect entries (§ "Part 3", below) and the 8 parked MBTI
  dichotomies.
- The moral-circle order and the near-duplicate cosines (§ "TODO: arrangement
  hunting", § "TODO: review the moral-circle sequence").
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
- Before the first judging run that includes the standards: the "careless
  (from HEXACO)" display form, a rubric change (AGENT_NOTES § "Standard-derived
  trait labels", item 7).

### The tangle and arrangement pass

- The 36 unclassified traits (one-way pointers, labels with no file), the
  delegation vices, merciful / cruel / merciless, uncaring against callous,
  the accountable / blame-shifting / self-blaming kite, and the sets not yet
  written (§ "TODO: arrangement hunting").  `wasteful` (a queue entry, no
  file) is parked for it.
- detractor and the role pairs: the role-pair check is built (`a9c0a13`,
  `generate_antonyms.py --roles`) and was run once on 2026-10-09.  Two of the
  six role pairs are clean both ways, two nearly, two not; evangelist names
  "debunker | skeptic | iconoclast", not detractor, so detractor's question
  stays open (§ "TODO: post-extraction checks for chunk 5";
  [ROLES_TO_ADD.md](../../roles/instructions/ROLES_TO_ADD.md) § "Role pairs to
  record").

### Parked: Roger's call, when more gap-filling is wanted

Queue entries with status `backlog` (no files; reasons in their `decision`
fields in [seed_queue.json](../../seed_queue.json)):

- `spiralist` (TRAITS_ADDED § "Candidate traits": too new for the generator
  to know).
- `vanilla`; `southeast_asian`, `pacific_islander`; `free_market`,
  `interventionist` (fallback names).
- Seven optional words from the taxonomy gap scan: `devoted`, `enthusiastic`,
  `hypochondriac`, `just`, `purposeful`, `self_sacrificing`, `steadfast`.
- Five candidates from the Strategy 1a table: `boundary_fuzzy`,
  `present_focused`, `self_attentive`, `self_other_boundary_aware`,
  `transcendentally_oriented`.

Not queued:

- Walking the occupational instruments (Hogan HPI, HDS and MVPI,
  CliftonStrengths, SHL OPQ, Coie's sociometric statuses, Rogers' adopter
  categories), listed in the September gap scan but never walked; a first
  look found nearly every scale already covered (TRAITS_ADDED § "TODO
  (definitely): gap scan using the other taxonomies as checklists").
- An observed / unobserved pair (behaving worse when nobody is watching),
  noted as a possible second pair beside ruthless / honorable while playing
  (TRAITS_ADDED § "Frame-dependent morality").
- The trait-gap generators' holding lists (§ "Holding lists from the
  trait-gap generators", below).

### Tooling and records

- [trait_antonyms_v4.json](../trait_antonyms_v4.json) has 240 entries
  against 916 traits, and [labels.py](../../../assistant_axis/gapgen/labels.py)
  still reads it: retire it in favour of
  [antonym_check_history.jsonl](../antonym_check_history.jsonl), or rebuild
  it (TRAITS_ADDED § "Housekeeping once the directory settles", item 2).
- The combination-scores summary in [data/README.md](../../README.md) still
  quotes the pre-escalation figures (same section, item 5).
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

**Status 2026-10-09: open, Roger's decision.**  [civilizationist](./civilizationist.json) was seeded on
2026-10-02 between ethnocentric and cosmopolitan, so the sequence now has 16 members; nothing
else below has changed.  Description rewrites are cheaper before the extraction; the order is
checked after it.

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

**Status 2026-10-09:** all five items wait on the extraction (the introduction says four; detractor was
added later).  The decision in the last paragraph is in force.

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

**Status 2026-10-09:** the VALS and Slytherin items are done.  The native-language item has to be built
*before* the extraction, whatever this heading says.  The yield and geometry checks wait on the
extraction.

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

## TODO: near-duplicate traits to drop or merge (M2 calibration, 2026-10-01)

**Status 2026-10-09: open, best done before the extraction.**  Nothing has been dropped.  The table was
calibrated on 663 traits, and the 253 added in chunks 4 to 7 have not been through it, so rerun
it on all 916 first.  [passionate](./passionate.json) has since been paired with
[dispassionate](./dispassionate.json) (2026-10-02), so dropping it would now cost a pair.

Roger, 2026-10-01, on the M2 pilot's drop-or-merge table: not now, but recorded here.  The
leave-one-out nearest-neighbour test of the trait-gap platform's metric calibration
([pilot_m2_readout.md](../../../reports/trait_gap_generation/pilot_m2_readout.md), table in
[drop_or_merge.md](../../candidates/calibration/drop_or_merge.md)) found twelve pairs of existing
traits whose descriptions sit closer than the bulk of the corpus allows, once recorded arrangement
partners are excluded.  Roger: "the least novel ones do indeed look close: they're either
near-synonyms or antonyms.  Some are probably good candidates for dropping, especially where we can
do so without getting rid of a pair (or by getting rid of both ends of rather similar pairs)."

| trait | nearest | flagged by | note |
|---|---|---|---|
| [abstract](./abstract.json) | [theoretical](./theoretical.json) | bge, gemma | with [conceptual](./conceptual.json), a triple of near-synonyms |
| [conceptual](./conceptual.json) | [theoretical](./theoretical.json) | bge | |
| [dependable](./dependable.json) | [trustworthy](./trustworthy.json) | openai, bge | |
| [self-blaming](./self_blaming.json) | [blame-shifting](./blame_shifting.json) | openai, bge | an antonym pair the corpus does not record; a candidate for an `arrangement` pair, not a drop |
| [passionate](./passionate.json) | [zealous](./zealous.json) | openai, gemma | |
| [empathetic](./empathetic.json) | [compassionate](./compassionate.json) | gemma | compassionate is a triangle corner (callous / compassionate / malicious) |
| [absolutist](./absolutist.json) | [moral universalist](./moral_universalist.json) | bge | renamed from universalist on 2026-10-02 |
| [dramatic](./dramatic.json) | [theatrical](./theatrical.json) | openai | with [melodramatic](./melodramatic.json), a triple |
| [melodramatic](./melodramatic.json) | [dramatic](./dramatic.json) | openai | |
| [sarcastic](./sarcastic.json) | [sardonic](./sardonic.json) | openai | with [wry](./wry.json), a triple |
| [wry](./wry.json) | [sardonic](./sardonic.json) | openai | |
| [honest](./honest.json) | [truthful](./truthful.json) | openai | both alignment-region traits; keep at least one |
| [technical](./technical.json) | [specialist](./specialist.json) | centred space, round 2 | |
| [creative](./creative.json) | [innovative](./innovative.json) | centred space, round 2 | |
| [enigmatic](./enigmatic.json) | [cryptic](./cryptic.json) | centred space, round 2 | |
| [northern hemisphere](./northern_hemisphere.json) | [eastern hemisphere](./eastern_hemisphere.json) | centred space, round 2 | memberships; the hemispheres are a recorded set |
| [dispassionate](./dispassionate.json) | [detached](./detached.json) | gemma, 663-trait refresh | new on 2026-10-02: detached's pair with empathetic was dissolved by the clean-pair recheck, so detached is no longer an excluded partner |
| [insular](./insular.json) | [parochial](./parochial.json) | M3 overlap test, Opus 4 | new on 2026-10-03; adjacent members of the moral-circle `sequence`, so this belongs to the sequence review (§ "TODO: review the moral-circle sequence") rather than a plain drop |

**Refreshed 2026-10-02 on the merged 663-trait corpus** (full calibration, OpenAI and EmbeddingGemma,
membership by the raw space; [drop_or_merge.md](../../candidates/calibration/drop_or_merge.md)): 11
pairs flagged, one new (dispassionate / detached, above).  Six rows above are not flagged by the
refreshed rule, mostly for reasons of method rather than of the corpus: absolutist / moral
universalist was flagged only by bge, which has been dropped; the four round-2 pairs came from the
centred space, while the refreshed table takes membership from the raw one; passionate / zealous now
sits just under the fence.  They stay listed as candidates.

**The M3 overlap test, 2026-10-03** ([m3_overlap_test_readout.md](../../../reports/trait_gap_generation/m3_overlap_test_readout.md);
Roger agreed these as by-products): Opus 5.5 put five pairs at 4, "the same concept", on rubric A
([overlap_concept.md](../../../reports/trait_gap_generation/rubrics/overlap_concept.md)): the three
pairs of the [abstract](./abstract.json) / [conceptual](./conceptual.json) /
[theoretical](./theoretical.json) triple, [dispassionate](./dispassionate.json) /
[detached](./detached.json), and [insular](./insular.json) / [parochial](./parochial.json) (new row
above).  They are the strongest merge candidates on the list.  In the triple, abstract (pair with
[concrete](./concrete.json)) and theoretical (pair with [practical](./practical.json)) are pair
poles and conceptual is a singleton, so conceptual is the drop that costs no pair.
[self-blaming](./self_blaming.json) / [blame-shifting](./blame_shifting.json) went the other way:
every model read them as opposites, which supports the row's note; they belong with
[accountable](./accountable.json) in the triangle (or kite) Roger noted on 2026-09-26, to be
classified in the arrangement pass, not on this list.

Before acting: check each trait's `arrangement` and `negative_label` (a drop that breaks a clean pair
costs the pair), and prefer dropping both ends of two near-identical pairs over one end of one.  The
list will be refreshed when the final calibration runs on the merged corpus.

## TODO: rename `historical` (Roger, 2026-10-01)

**Status 2026-10-09: open, best done before the extraction.**  The trait-gap branch has merged, so nothing
blocks it.

[historical](./historical.json) (singleton, `non-historical`) describes a manner of speaking: "frequently
referencing past events, drawing on historical context ... connecting current topics to historical
precedents".  The bare word does not carry that sense: the trait-hood filter's sense call read "You are
historical" as "significant in history" or "from a past era" in both full validation runs, and turned
it away or passed it on the wrong reading
([readout_m1_validation.md](../../../reports/trait_gap_generation/readout_m1_validation.md)).  A label
question, like deterministic was, not a filter one.

Roger's suggestion: **history buff**.  Note before renaming: it names a person (an enthusiast), so the
filter may tag it `role_person` or read it as an affinity membership (as it did cat-person), and it
shifts the sense from how the persona talks (brings the past into everything) to what it likes;
"historically minded" or "history-minded" keeps the adjective form and the manner sense.  Decide
the label, then `seed_entities.py rename --old historical --new <label>`, regenerate, and rerun the
check.  Do it in the main checkout after the trait-gap branch merges, as with the determinist rename.
