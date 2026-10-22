# Plan 16: generators aimed at roles

Idea plan, written 2026-10-16 (Fable); **§ 12's decisions answered by Roger on 2026-10-21** (3 left open, and whether AI-persona roles count toward the cap), after Roger unparked the role generators for planning
([README.md](./README.md#generators-aimed-at-roles-roger-2026-10-10-unparked-for-planning-2026-10-16)).  Four
generators, each in its own section so that it can be split into a coding plan of its own, and the pieces all four
share: the role path through M1 and M3, promotion, wave sizing against the corpus balance, the cap, build order.
No code here; concrete enough for a coding plan in the [format](./PLAN_FORMAT.md).  Terms: a *role* is a person or
thing a persona can be (pirate, refugee, goldfish), as against a *trait*, a disposition it can enact; *M1* is the
trait-hood filter (plan 14), *M3* the novelty check ([retrieve, then judge](./glossary.md#retrieve-then-judge)); a
*holding list* is a registry field (`holding`) that keeps a row out of the trait flow (promotion refuses it); the
*registry* is [registry.jsonl](../../data/candidates/registry.jsonl); the *seed queue* is
[seed_queue.json](../../data/seed_queue.json), from which [seed_entities.py](../../data_analysis/seed_entities.py)
writes corpus files.  Other terms: [glossary.md](./glossary.md).

**Recorded decisions (Roger, 2026-10-10 and 2026-10-16; not reopened here):** cap 500-600 roles (340 today);
the balance across kinds of role is a reference, not a target (measure before and after each wave, say where it
moved; the guard is against 200 professions or 200 monsters taking over); nine kinds, one dimension, accepted
2026-10-16 (occupation or task; life stage, family and relationship; circumstance; status or wealth; stance or way
of life, the lawless included; pastime; non-human being; a temperament under a noun; other), and a role is never
turned down for fitting no kind; fictional characters are fine, no seeding from real living people (plan 06 covers
that); role promotion is built with these generators as plan 06's by-name `--allow-roles` design
([coding_plan_06_llm_entropy.md](./coding_plan_06_llm_entropy.md), decision 1 (a)).

## 1. Idea

Every generator so far aims at traits; roles reach the corpus by accident, as the 355 rows now on the registry's
`roles` holding list show.  Four generators aimed at roles, each independent of the role corpus in a different
way: (A) the characters of randomly chosen works, turned into the roles they instantiate; (B) public occupation
classifications; (C) the SRD's creatures and the world's folklore; (D) the trait generators re-aimed at nouns.
A and D are the ones that can fill the kinds the corpus has least of (relationship, circumstance, status,
pastime); B and C each feed one kind, and the balance bounds them more than their sources do.

## 2. Where roles stand today

- **Corpus**: 340 roles ([instructions/](../../data/roles/instructions/); 341 files with
  [default.json](../../data/roles/instructions/default.json)), descriptions in the form "A <role> is someone who
  ..." (e.g. [accountant](../../data/roles/instructions/accountant.json)), five pos instructions, no negative
  side, pairs only in `arrangement`.  Eleven names exist as both a trait and a role ([ascetic](../../data/roles/instructions/ascetic.json), [contrarian](../../data/roles/instructions/contrarian.json), [cosmopolitan](../../data/roles/instructions/cosmopolitan.json), [generalist](../../data/roles/instructions/generalist.json), [pacifist](../../data/roles/instructions/pacifist.json), [parent](../../data/roles/instructions/parent.json), [patient](../../data/roles/instructions/patient.json), [perfectionist](../../data/roles/instructions/perfectionist.json), [romantic](../../data/roles/instructions/romantic.json), [specialist](../../data/roles/instructions/specialist.json), [stoic](../../data/roles/instructions/stoic.json)).
- **Balance, by [role_kinds.json](../../data/roles/role_kinds.json)** (Haiku 5.5, three readings, majority,
  [classify_role_kinds.py](../../data_analysis/classify_role_kinds.py), $0.07, 2026-10-16; 13 of 340 not
  unanimous, no three-way split):

  | kind | n | share | at the cap (550), share held | room if held |
  |---|---|---|---|---|
  | occupation or task | 162 | 47.6% | 262 | +100 |
  | stance or way of life | 47 | 13.8% | 76 | +29 |
  | non-human being | 44 | 12.9% | 71 | +27 |
  | circumstance | 24 | 7.1% | 39 | +15 |
  | temperament under a noun | 22 | 6.5% | 36 | +14 |
  | life stage, family, relationship | 20 | 5.9% | 32 | +12 |
  | status or wealth | 9 | 2.6% | 15 | +6 |
  | pastime | 8 | 2.4% | 13 | +5 |
  | other | 4 | 1.2% | 6 | +2 |

  Occupations are already half the corpus; the AI roles (confirmed by Roger, 2026-10-16; [instrumentally_aligned_ai](../../data/roles/instructions/instrumentally_aligned_ai.json),
  [robot](../../data/roles/instructions/robot.json)) sit under non-human.  The last two columns are what "share
  held" would mean at a mid-cap of 550; they are the reference the readouts compare against, not quotas (§ 4).
- **Held rows**: 355 registry rows on the `roles` holding list (M1 tags `role_person` / `role_thing`;
  [filter.py](../../assistant_axis/gapgen/filter.py) `holding_for`), from censuses, the base model, the masked LM,
  Roget and the noun relabel; read by hand so far (`gap_registry.py holding --list roles`, pointer in
  [ROLES_TO_ADD.md](../../data/roles/instructions/ROLES_TO_ADD.md)).  Most are occupations (accountant, baker,
  cardiologist, firefighter), some circumstance (captive, fugitive, housebound), some noise (adjectives read as
  offices: accredited, disbarred).  **These are the pilot material for the shared path (§ 3) before any generator
  runs.**
- **Queue**: 78 role entries in the seed queue (61 done, 13 not adopted, 2 exist, 2 backlog), all hand-seeded from
  ROLES_TO_ADD.md.  The role-pair check exists ([generate_antonyms.py --roles](../../data_analysis/generate_antonyms.py)).
- **Platform gaps**: `Candidate` has no entity type (the registry writes `entity_type: "trait"`, and only M1's
  verdict turns a row into a role); M1 writes no gloss for a role row (`gloss: null`); M3 scores verdict-`trait`
  rows only, against traits and queue entries; [promote.py](../../assistant_axis/gapgen/promote.py) refuses a
  held row; the M3 rubrics ([relation.md](./rubrics/relation.md), [overlap_concept.md](./rubrics/overlap_concept.md))
  speak of traits and dispositions throughout.

## 3. The shared role path

Built once, used by all four generators and by the 355 held rows.  The shape is the physical pass
([coding_plan_review.md](./coding_plan_review.md) § 8, [physical_pass.py](../../assistant_axis/gapgen/physical_pass.py)):
a gloss stage, M3 in batches of their own, R1 grouping, R2 review, by-name promotion.

1. **Submission in role mode.**  `Candidate` gains `entity_type` (`trait` default, `role` for these generators)
   and the registry row records it at submission, with the generator's `kind_guess` (one of the nine) and
   `human` flag riding along as information, as IPIP's kind guess does.  Collision handling: a surface already in
   the registry as a trait row is a second row keyed by entity type (optimist the role beside optimistic the
   trait), not a merge.
2. **M1 in role mode.**  The split filter's calls run as they are (sense, established, vague, kind:
   [step2_kind.md](./rubrics/step2_kind.md)); what changes is the routing.  For a role-aimed row: kind `role` ->
   the role flow (no holding list: it is where the row was aimed); kind `trait` (a temperament under a noun:
   miser, optimist, hothead) -> **both** flows, the noun staying a role candidate because kind 8 is a corpus
   kind, and the adjective sibling from the relabel helper ([nouns.py](../../assistant_axis/gapgen/nouns.py))
   entering the trait flow as today (decision 3); kind `membership` (religions, nationalities, age groups) -> the
   membership track, since those are traits by decision 3 of [decisions_m1.md](./decisions_m1.md); `state`,
   `physical`, `action`, `evaluative`, `not_a_persona` -> turned away for the role flow, tags kept.  The
   established check matters more for roles than for traits: a franchise generator will emit "chosen one" and a
   Roget pass "costermonger"; the Zipf floor and the established check are what keep the 32B model's vocabulary
   in view.
3. **Role gloss and kind.**  Two Haiku 5.5 calls per row that has none, as the physical pass runs M1's gloss and
   alignment calls: a **role gloss** rubric ([rubrics/role_gloss.md](./rubrics/role_gloss.md), to be written and
   pinned) in the corpus form "A <role> is someone who ..." / "... is something that ...", one sentence, for the
   accepted reading; and the **role kind** call, the same rubric as
   [classify_role_kinds.py](../../data_analysis/classify_role_kinds.py) so that a candidate's kind and a corpus
   role's kind are measured alike (three readings, majority).  No alignment call: the role cut-off is flat (item 5).
4. **M3 for roles.**  Retrieval over the 340 role descriptions (label plus gloss embedded under M2's settings,
   [metric_config.json](../../data/candidates/metric_config.json), reused for roles with a retrieval check: each
   corpus role queried with a fresh role gloss from step 3 must come back in its top 10 for 95% of roles, or the
   settings are recalibrated on those queries; decision 11), the 10 nearest roles plus
   their arrangement partners, then the relation call and the overlap call on role versions of the rubrics:
   - [rubrics/relation_roles.md](./rubrics/relation_roles.md) (to be written): the same three answers, with role
     examples (doctor and physician similar; predator and prey opposed; doctor and plumber unrelated).
   - [rubrics/overlap_concept_roles.md](./rubrics/overlap_concept_roles.md) (to be written): rubric A's scale with
     the hierarchy made explicit, which roles have far more of than traits: 4 the same role under another name
     (cop, police officer); **3 a kind of the other, or the other narrowed to a setting** (cardiologist under
     doctor, bush pilot under pilot); 2 overlapping roles, neither a kind of the other (healer and doctor);
     1 neighbours (judge and lawyer); 0 different.  Rendered samples per [working-style](../../.claude/rules/working-style.md)
     before pinning.
   - **Cross-type retrieval**: the same query also retrieves the nearest traits (optimist against
     [optimistic](../../data/traits/instructions/optimistic.json)) and shows them on the review card as information;
     covered is decided against roles only (decision 5).  This also gives, for free, the check the README TODO
     wanted the other way round (a trait candidate duplicating a corpus role): run the role retrieval on trait
     candidates as information.
5. **Cut-off**: covered at 3 or above, flat, for every role (traits use the alignment score to move it; roles
   have no alignment call).  Sub-roles are therefore covered by their parent (decision 4); the card names the
   parent so that Roger can keep a sub-role that is a different persona.
6. **R1 and R2**: the review graph and app unchanged but for the node outcome `role` and a card showing kind,
   human or not, the nearest roles and traits, and the generator's provenance (the work and character for A,
   the classification code for B, the creature's origin for C).
7. **Promotion**: the by-name path `gap_registry.py promote --keys K ... --allow-roles`
   ([gap_registry.py](../../data_analysis/gap_generation/gap_registry.py), [promote.py](../../assistant_axis/gapgen/promote.py)),
   refused for the bulk path as `--allow-physical` is, writing an `entity_type: "role"` queue entry: `pairing:
   singleton` (or `pair` with the generator's `partner_hint`, checked at seeding by the role-pair check), tags
   `gap_gen`, `source:<generator>`, `kind:<kind>`, `description_draft` the role gloss, section "role generators
   (2026-10)"; the collision checks of promote (a stem in either corpus, a queued stem, a turned-down name) apply.
   Then the existing steps: `seed_entities.py write` and `generate`
   ([regenerate_role_instructions.py](../../data_analysis/regenerate_role_instructions.py), about $0.02 a role on
   Sonnet 4.6), [sync_entity_lists.py](../../tools/sync_entity_lists.py).
8. **Kinds side-car**: a promoted role's kind is appended to [role_kinds.json](../../data/roles/role_kinds.json)
   at seeding (the classifier reuses a kind on record with the same prompt and model, so a rerun over the corpus
   after a wave costs only the new rows).

## 4. Waves, the balance and the cap

- **Wave size by review hours**, as plans 04 and 09 size theirs: about two hours of Roger's review, roughly 300
  rows at the measured 150 terms an hour (nouns may go faster), which at the base-model wave's kept share (37%
  of decided, [README](./README.md)) is about 100 kept roles a wave; two or three waves reach the cap.
- **Occupations about half of every wave's submissions** (Roger, 2026-10-16: the aim is to keep roughly the
  current balance), the other kinds sharing the rest; § 6 says how B picks its half.
- **Balance readout, every wave**: the nine-way split of the corpus before, of the wave's submitted rows (by the
  generator's guess), of the kept rows (by the kind call), and of the corpus after; the readout says where it
  moved.  A generator that feeds one kind (B, C) is told its "room if held" number (§ 2) before it runs, and the
  readout flags any kind whose share moves by more than five points.  No automatic cut: Roger reads the flag and
  decides (decision 2).  In review (Roger, 2026-10-21): the card says whether the candidate's kind is currently
  too high, too low or about right (more than 10% above or below the count that keeps the kind's share as on
  2026-10-16), and a review order shows the too-low kinds first; Roger will generally not accept a candidate in a
  kind that is too high.
- **Cap**: 500-600 roles.  Read as the corpus's size after adding, not a wave's (decision 1, Roger 2026-10-21): the cap is about what the
  extraction and the judging can carry per entity, and a wave is sized by review hours.  With 340 today that is
  160-260 additions across all generators, which is why B and C get one modest wave each and A and D the rest.
  An AI-persona role recast as a trait (ROLES_TO_ADD, "AI-persona roles under the role judge") leaves the
  count (Roger, 2026-10-22).

## 5. Generator A: characters of a media franchise

**Idea.**  Pick works at random from several eclectic online sources, list each one's major characters, and turn
each character into the role it instantiates, never the character: Poirot -> detective, Jiji -> talking cat,
Scrooge -> miser, Naruto -> ninja, Cosette -> orphan.  A work's cast is a sample of roles chosen by storytellers
for contrast, not by a lexicon, so it reaches kinds a list of nouns does not (circumstance, relationship, status).
Independent of our list: no corpus role is shown to the model.

**Sources.**
- **Wikidata** (CC0, verified: property P674 "characters" links a work to its characters, inverse P1441 "present
  in work"; constraints exclude real people, so fictional only by construction).  SPARQL with `RAND()` over works
  having >= 5 P674 values, **stratified** by work type (literary work, film, television series, anime series,
  manga, comic series, video game, play, opera), by country of origin (P495), by decade of publication and by
  popularity (sitelink count: half from the top decile, half from the long tail).  Could not verify counts per
  stratum without querying; expect films and video games to dominate the P674-rich works, so stratification is
  what makes it eclectic.
- **Project Gutenberg's top-100 and catalogue** (public domain) for pre-1928 literature, which has few P674
  values: the model lists the characters itself.
- **Wikipedia "List of <work> characters" pages** (CC BY-SA 4.0): pick lists only, nothing redistributed.
- Not used: TV Tropes (CC BY-NC-SA since 2012; verified via Wikipedia) and the AniList / MyAnimeList APIs
  (terms not verified); Wikidata covers anime through P674.
- Model: Haiku 5.5 ($0.10 / $0.50 per MTok); Sonnet 5.5 ($2 / $10) only if the step-5 test shows Haiku does
  not know the long-tail works.

**Method.**
1. Draw about 600 works across the strata; record QID, title, type, country, year, sitelinks.
2. Characters: Wikidata's P674 list where it has >= 5; otherwise one Haiku call "the 8-12 major characters of
   <title> (<year>, <type>)".  Accuracy is secondary, as in plan 06 (b): only the roles matter.
3. One call per work, all its characters in it, reasoning first: for each character 1-3 roles ordered by how
   much each organises the character, as a generic noun phrase of 1-3 words (no proper names, no "the"), a gloss
   in the corpus form, a kind guess among the nine, `human` true/false, and whether the role is a **narrative
   function** (hero, villain, sidekick, mentor, love interest) rather than who the character is.  A role-in-a-story
   is dropped at generation, an archetype kept (decision 6, Roger 2026-10-21): protagonist is a place in a plot,
   not a role; the corpus's [guardian](../../data/roles/instructions/guardian.json),
   [trickster](../../data/roles/instructions/trickster.json) and [fool](../../data/roles/instructions/fool.json) are
   archetypes, and so are hero, villain and sidekick (kept; Roger, 2026-10-22); mentor is in the corpus; love
   interest is a position in a plot (dropped).  The rubric's rule: keep a name a person could be called in real
   life, drop one that only names a position in a story.
4. Normalise (lower case, singular, US spelling via the relabel helper's tables), merge across works keeping the
   provenance list; `n_sources` (detective will arrive from forty works) is a commonness prior, as in plan 09.
5. Submit in role mode (§ 3) with `source_ref` `wikidata:<work>/<character>` and the kind guess.
6. Collapse and saturation as plan 06 § 3.8: run-to-run Jaccard on 30 works, a [rarefaction
   curve](./glossary.md#rarefaction-curve) over works and [Chao1](./glossary.md#chao1) on the role counts, so the
   wave stops where new works stop paying.

**Yield and biases.**  600 works x 10 characters x 1.5 roles = 9,000 raw -> 1,200-1,800 distinct strings -> about
1,000 net-new after the corpus, the queue and the held rows -> perhaps 200-400 new after M3.  Over-produces:
warriors, royalty, criminals and the fantasy bestiary (overlapping C), narrative functions, anglophone and
Japanese works even when stratified; under-produces mundane occupations (B's job) and natural-system personas
(D's).  The 32B model must know the role word, not the work, so popular works are fine; eclecticism by medium,
region and era matters more than obscurity.

**Cost.**  1,200 Haiku calls at about $0.002 = $2-3; M1 on about 1,000 net-new at the measured $0.0072 = $7;
M3-for-roles at about $0.011 a passed row = $6-8; **about $16-18 live, $8-9 batched**; batch it with the rest of
a wave.  Roger: two to three hours of review per wave.

**Testing.**  Hide the 340 corpus roles and measure [recovery by string](./glossary.md#recovery-by-string) by
kind (expect high for non-human, stance and status, low for occupations such as statistician); spot-check 50
character-to-role mappings for genericness and for the narrative-function tag; the collapse measurement of
step 6; precision on 50 novel candidates by Roger (role, and new).

## 6. Generator B: lists of professions

**Roger, 2026-10-16: keep roughly the current balance, so occupations should be about half of what the role
generators submit; of the vast number available, aim for missing ones that are common, well known, and not
especially similar to ones the corpus already has.**  So B is not a sweep of a classification but a ranked pick:
every candidate lay role is scored for familiarity (BLS OEWS employment for its SOC code, public domain like SOC;
the Zipf frequency of the lay title, as [freq.py](../../assistant_axis/gapgen/freq.py) already computes for
traits) and for distance from the corpus (its nearest corpus role by embedding, and M3's hierarchy line of § 3.4,
under which a sub-role such as cardiologist is covered by doctor), and the wave takes the top of the ranking up to
the occupations' half of the wave.  The random DOT and alternate-title samples below give way to this: archaic
and oddly specific is the opposite of well known, so the DOT sample is dropped, and alternate titles enter only
through the same ranking.

**Idea.**  Occupations can be enumerated endlessly, so the question is the level, not the source: the persona
level is "nurse", "cardiologist" or "executive", not "Chief Sustainability Officers".  Take a classification's
middle tier, let a model name the lay role for each entry, and add an eclectic sample of lay titles and of
historical trades for the odd ones.

**Sources (licences checked where the pages answered).**
- **O*NET 31.0** `occupation_data.csv`, 1,016 titles with descriptions, **already on disk** under
  [data/external/onet/](../../data/external/onet/occupation_data.csv) with its manifest and licence (CC BY 4.0,
  verified 2026-10-10 for plan 03; [sources.py](../../assistant_axis/gapgen/generators/base_model/sources.py)).
  Note `ONET_NOTE` there: the attribution becomes **load-bearing** the moment a title reaches a tracked artefact,
  which this generator does by design, so the attribution travels with the run's `candidates.jsonl` and readout.
  O*NET's [alternate_titles.csv](../../data/external/onet/alternate_titles.csv) (lay titles, tens of thousands:
  bouncer, roadie, lifeguard; not on disk yet, a small fresh download under the same licence, so a fresh ask) is
  the eclectic part.
- **BLS SOC 2018** (public domain, verified on bls.gov: "everything that we publish ... is in the public
  domain"): the hierarchy, 23 major / 98 minor / 459 broad / 867 detailed, the same occupations as O*NET-SOC;
  the **broad** tier (459) is the starting level.
- **DOT 1991** (US government work; Wikipedia says its copyright was "very limited"; not verified at source):
  12,700 titles, archaic and oddly specific; use a random sample, not the list.
- **ESCO** (3,000+ occupations with alternative labels; the download page says "free of charge" and names no
  licence; the licence page returned 404) and **ISCO-08** (436 unit groups; the ILO page has moved and could not
  be read): **not verified**; skip unless Roger wants them (decision 7).
- **HISCO** (historical occupations): licence not checked; the Roget pass of D covers historical trades anyway.

**Method.**
1. One Haiku call per SOC broad occupation (459), with its detailed titles and O*NET descriptions: the one or two
   lay role nouns a person would say when asked what they are, a gloss, `human` true, kind `occupation`, and
   whether the role is a **distinct persona from its parent** (a cardiologist talks about hearts; a chief
   sustainability officer is an executive).
2. Alternate titles (300 of the most frequent by Zipf), same call, ranked with the rest (Roger's rule above; the DOT sample dropped).
3. Submit in role mode; `source_ref` the SOC code or the title; the attribution in the run directory.
4. Rank by familiarity and distance (above) and submit from the top until occupations are about half of the
   wave's submitted rows; M3's hierarchy line (§ 3.4) still cuts, and the readout shows the occupation share
   before and after (about +100 in all if the share is held at 550).

**Yield and biases.**  459 broad -> about 350 distinct lay roles -> minus the 162 corpus occupations and the
held rows -> about 200 net-new -> M3 covers perhaps 40% -> about 120 candidates; the samples add 100-150 more.
Over-produces: the modern US labour market, white-collar granularity, healthcare specialisms; under-produces
informal and illicit occupations (pickpocket, courtesan, smuggler: A and D), historical trades (D's Roget pass),
and task-roles of the assistant kind ([summarizer](../../data/roles/instructions/summarizer.json),
[debugger](../../data/roles/instructions/debugger.json): D's LLM role grid).  Bounded by the balance, not by the
source.

**Cost.**  About 1,000 Haiku calls, $1-2; M1 and M3 on about 500 net-new, $9; **about $11 live**; batch it with
a wave.  Roger: one hour.

**Testing.**  Hide the 162 corpus occupations: recovery at the broad level should exceed 80%; the misses say
which level the corpus actually sits at.  Precision: Roger marks 50 candidates "distinct persona from its
parent".

## 7. Generator C: monsters, fantasy races and folklore

**Idea.**  The SRD is a large, eclectic bestiary with a licence; world folklore is the earlier source most of it
came from.  Prefer what D&D took from folklore over its own inventions unless those have crossed over.  The
corpus has 44 non-human roles, none of them a fantasy race: no elf, dwarf, orc, dragon, werewolf, mermaid,
unicorn.

**Sources.**
- **SRD 5.2 and 5.1**, CC BY 4.0 (verified at dndbeyond.com/srd: 5.2 is CC-BY-4.0 and "permanently available
  under those terms"; 5.1 under OGL 1.0a or CC BY 4.0; excluded by design: beholder, some species such as
  aasimar, named figures such as Strahd, Orcus, Tiamat).  About 300 creatures and the playable species (dwarf,
  elf, halfling, orc, goliath, tiefling, dragonborn).  The Monster Manual itself is not open and is not used.
- **Wikidata** (CC0): items that are instances or subclasses of mythical / legendary creature, with culture or
  country of origin, and P1441 "present in work" for the crossover test; **Wikipedia's lists of legendary
  creatures** by type and by culture (CC BY-SA 4.0; pick lists only).
- Optional: Pathfinder 2e's bestiary under the ORC licence (not checked).

**Method.**
1. SRD creatures and species: one Haiku call per creature with its SRD type and a line of description: the
   persona-level name (thirty dragons -> dragon; vampire spawn -> vampire), a gloss, `human` false, kind
   `non_human`, and whether it is a persona at all (an ooze is not; a swarm is, since the corpus has
   [swarm](../../data/roles/instructions/swarm.json) and [hive](../../data/roles/instructions/hive.json)).
2. **Origin and crossover**: a creature with a Wikidata item of folklore origin passes; a D&D invention passes
   only if it has crossed over, tested as presence in >= 3 works outside D&D (P1441) or >= 10 sitelinks (owlbear
   yes, chuul no; decision 8).  Record origin as provenance.
3. Folklore: the Wikipedia and Wikidata lists, stratified by culture (European, Japanese, Chinese, Indian, Arabic
   and Persian, African, Mesoamerican, Oceanian, Slavic, Norse, Greek), through the Zipf floor first (kitsune and
   djinn pass; nuckelavee does not), then the same call.
4. Submit in role mode; the wave is told its room (about +27 at a held share) and the readout shows the
   non-human share before and after.

**Yield and biases.**  SRD -> about 120 persona-level creatures and races; folklore -> about 1,500 names ->
Zipf floor -> about 300; net-new after the 44 corpus non-humans and the held rows about 350; M3 perhaps 150-250
new, far more than the share allows, so this is one wave chosen by Roger from a ranked list, not a flood.
Over-produces hostile creatures (allies and neutral beings under-produced: familiar, unicorn, phoenix), European
and Japanese folklore (English Wikipedia's coverage), humanoid races.  Does not produce natural-system or
abstract personas ([coral_reef](../../data/roles/instructions/coral_reef.json),
[zeitgeist](../../data/roles/instructions/zeitgeist.json), [void](../../data/roles/instructions/void.json)):
those are D's LLM role grid.

**Cost.**  About 700 Haiku calls, $1-2; M1 and M3 on about 350, $7; **under $10 live**.  Roger: one hour.

**Testing.**  Hide the 44 corpus non-humans: expect angel, demon, vampire, ghost, golem, genie, witch recovered,
coral_reef and zeitgeist not (and say so); spot-check 50 persona-level collapses; the crossover test on the 20
best-known D&D inventions by hand.

## 8. Generator D: a role mode for the trait generators

**Idea.**  The precedent is [generate_antonyms.py --roles](../../data_analysis/generate_antonyms.py): the same
tool, a role prompt.  Four of the trait generators have a cheap role mode; two are worth building now.

**(a) LLM entropy (plan 06) in role mode.**  The scaffold of [06](./06_llm_entropy_generation.md) with a role
target ("who or what a persona is: a noun; a person, creature, thing or system; not a disposition") and the
output schema `{label, gloss, kind_guess, human, counterpart}` (the counterpart is the role on the other side of
the relation: patient / doctor, prisoner / warden, predator / prey; a free `partner_hint`).  The families:
- the grid becomes **domain x kind**: the ~30 domains of 06 (money, authority, strangers, the body, death, work,
  the sea, ...) x the eight named kinds = 240 cells x 3 runs = 720 Haiku calls; this is the one generator that
  can be pointed at the thin kinds (relationship, circumstance, status, pastime) directly;
- **person seeding** (06 b) already yields roles and now submits them in role mode instead of letting them
  strand on the holding list;
- **multilingual** (06 c): "roles a native speaker names that have no single English word" (salaryman, gaucho,
  griot, ronin, concierge, dacha-dweller), back-translated to 1-3 words; the same ten languages; promising for
  stance and circumstance;
- verbalized sampling (06 d) applies; spelling constraints (06 e) do not.
Collapse measured as in 06 § 3.8.  Cost: about 1,500 Haiku calls and 300 Sonnet calls, $8 live, $4 batched,
before M1 and M3 (about $10 on 1,500 net-new).

**(b) Roget and WordNet in role mode (plan 02).**  Answer to the open question: it looks at the **same heads'
noun lists** (the parser keeps them; [harvest.py](../../assistant_axis/gapgen/generators/roget/harvest.py) already
reads `head.items("N")` for glosses) **and at heads the trait pass skipped**, because Roget's person nouns sit
under Class V Volition and Class VI Affections heads whose titles are persons (492 Scholar, 493 Ignoramus, 501
Fool, 548 Deceiver, 690 Agent, 694 Director, 711 Mediator, 726 Combatant, 745 Master, 746 Servant, 792 Thief,
797 Merchant, 893 Recluse, 913 Benefactor, 914 Evildoer, 967 Lawyer, 996 Clergy) and under Classes I-III
(164 Producer, 165 Destroyer, 690 Agent).  Gate: a noun in OEWN's `noun.person` lexicographer file, or in the
hyponym closure of `person.n.01` (the closure code exists for the trait-noun closure), through the Zipf floor.
The **WordNet sibling is a census of role nouns in its own right**: the `person.n.01` closure holds about 11,000
person synsets, and `noun.animal` and `noun.object` closures give the non-human beings; with the Zipf floor
perhaps 1,500 common person nouns, the cheapest and most complete enumeration available (plan 01's shape,
no generation calls).  Over-produces Victorian trades and epithets (costermonger, varlet) and evaluative nouns
(scoundrel), which the established check and M1's evaluative kind handle; strong on kinds 1, 4, 5 and 8.  Cost:
no generation calls; M1 and M3 on about 1,500 rows, about $25 batched.

**(c) Base model (plan 03) and (d) masked LM (plan 04) in role mode**: a role comma-list family ("people you
might meet in a harbour town: a fisherman, a ...") and role frames ("works as a [MASK]", "is a [MASK] by
trade", "a [MASK] who"); free local compute, a prompt or frame change each, when those generators are next
touched.  **(e) Plan 09's operators on roles**: `opposite` is the role-pair check; `counterpart` (the role that
deals with this one) is new and cheap, derived from our list by design; later.

Recommendation: (a) and (b) now, (b) first because it costs nothing to generate and its recovery test
calibrates the other three generators' numbers (decision 9).

## 9. Cost summary

| piece | generation | M1 + M3 downstream | Roger |
|---|---|---|---|
| shared path pilot on the 355 held rows | $0.5 (gloss, kind) | $4 (M3 only; M1 done) | 2 h |
| A franchise | $2-3 | $13-15 | 2-3 h a wave |
| B professions | $1-2 | $9 | 1 h |
| C monsters | $1-2 | $7 | 1 h |
| D (a) LLM role mode | $8 live / $4 batched | $10 | 2 h |
| D (b) Roget / WordNet nouns | $0 | $25 batched | 2-3 h |

Each wave over $20 goes through the Batches API (Anthropic direct, as every call here); the role files for the
kept rows cost about $0.02 each; the extraction of 160-260 new roles is the real cost and is on the RunPod side,
not estimated here.  Every call site logs `MultiModelUsage` to a `usage.json` (hard rule).

## 10. Testing, shared

- **Recovery by kind**: each generator's recall of the 340 corpus roles hidden, broken down by
  [role_kinds.json](../../data/roles/role_kinds.json) kind, through the platform's recovery harness
  ([recovery_test.py](../../data_analysis/gap_generation/recovery_test.py), extended to roles); the kind
  breakdown is the diagnostic, since each generator is expected to miss whole kinds.
- **Role rubric check**: the role versions of the relation and overlap rubrics rendered and run on 40 hand-marked
  role pairs from the corpus (the six recorded pairs, ten parent/sub-role pairs such as doctor / cardiologist,
  ten same-role pairs, the rest unrelated), Sonnet 5.5, about $0.50, weighted kappa against Roger's marks, before
  the first paid wave.
- **Cross-type**: the eleven trait/role name collisions as a check that the cross-type retrieval finds them.
- **Balance readout** on every wave (§ 4); **stop rule** per generator as plan 13's dashboard applies it
  ([stop rule](./glossary.md#stop-rule)).

## 11. Build order

Revised 2026-10-21 (decision 10): B moved from last to second, so that its ranked pick of common, well-known
missing occupations supplies the occupation half of every wave (§ 6).

1. **The shared path** (§ 3), platform work with a Fable review: role-mode submission, the role gloss and kind
   calls, M3-for-roles with its two rubrics and the retrieval check of decision 11, the review app's role pass
   (with the kind readout of decision 2), `promote --allow-roles`, the kinds side-car.  Its pilot is the 355 held
   rows, so it pays before any generator exists, and the pilot's kept share sizes the first wave.
2. **B, lists of professions**: the ranked pick, metered so that occupations are about half of each wave's
   submissions.
3. **D (b), the Roget / WordNet person-noun census**: no generation calls, and its recovery numbers calibrate
   the rest.
4. **A, the franchise generator**: the one that fills the thin kinds and the most eclectic.
5. **D (a), the LLM role grid**, pointed at whichever kinds the readout after A shows thinnest.
6. **C**, one modest wave, sized by its room (§ 2) and cut by M3's hierarchy line.

## 12. Decisions needed

1. **The cap counts the corpus or each wave?**  (a) the corpus: 500-600 roles in all, waves sized by review
   hours; (b) each wave.  **Recommend (a)**; and say whether the AI-persona roles count if they become traits.  *Long version:* [§ 4](#4-waves-the-balance-and-the-cap), the cap bullet.
   **Decided (Roger, 2026-10-21): (a)**, the cap is the corpus's total size after adding.  **2026-10-22: an AI-persona role recast as a trait leaves the role count** and joins the trait corpus (its target about 1,800): the cap counts what the role judge carries.
2. **What the balance flag does.**  (a) readout only, Roger decides; (b) a wave's kept rows from one kind are
   cut when that kind's share would move more than five points; (c) a hard per-kind ceiling at the held share.
   **Recommend (a)**, with the five-point flag printed.  *Long version:* [§ 4](#4-waves-the-balance-and-the-cap), the balance readout bullet.
   **Decided (Roger, 2026-10-21): (a), and more.**  While Roger reviews candidates to turn into seeds, the card says whether the candidate's kind is currently too high, too low or about right; too high or too low means more than 10% above or below the count that would keep the kind's share as it was when this work started (the 340 roles of [role_kinds.json](../../data/roles/role_kinds.json), 2026-10-16).  He will generally not accept a candidate in a kind that is too high.  Also a review order that shows the too-low kinds first.
3. **A role-aimed candidate M1 reads as a trait** (miser, optimist).  (a) both flows: the noun stays a role
   candidate (kind 8), the adjective sibling goes to the trait flow; (b) role only; (c) trait only.
   **Recommend (a)**; the cross-type card shows the pair.  *Long version:* [§ 3](#3-the-shared-role-path) step 2 (M1 in role mode).
   **Open (Roger, 2026-10-21: "TBD").**  Some such roles might be dropped, but first look at how similar the model's activations for, say, optimist and optimistic actually are, on reasonably well-matched sets of instructions: a TODO in [ROLES_TO_ADD.md](../../data/roles/instructions/ROLES_TO_ADD.md) ("Role and trait twins").
4. **Sub-roles.**  (a) covered by their parent at overlap 3, the card naming the parent; (b) new until 4, review
   decides.  **Recommend (a)**: it is the guard against the profession flood.  *Long version:* [§ 3](#3-the-shared-role-path) step 5 (the cut-off) and [§ 6](#6-generator-b-lists-of-professions) (the profession flood).
   **Decided (Roger, 2026-10-21): (a).**
5. **Cross-type retrieval.**  (a) nearest traits shown as information, covered decided against roles only;
   (b) covered against both corpora; (c) roles only, no trait retrieval.  **Recommend (a)**.  *Long version:* [§ 3](#3-the-shared-role-path) step 4, the cross-type retrieval bullet.
   **Decided (Roger, 2026-10-21): (a).**
6. **Narrative-function roles** (hero, villain, sidekick, mentor, love interest) from A.  (a) kept and tagged;
   (b) dropped at generation.  **Recommend (a)**.  *Long version:* [§ 5](#5-generator-a-characters-of-a-media-franchise) (generator A).
   **Decided (Roger, 2026-10-21): (b), with adjustments.**  A role-in-a-story is not a role in this corpus's sense: protagonist is dropped at generation.  An archetype is a role and is kept: fool, trickster, guardian, and hero.  § 5 step 3 updated.  **2026-10-22: villain and sidekick are kept** (one can be either outside any story), mentor is in the corpus already, love interest is dropped; the rule for A's rubric: keep a name a person could be called in real life, drop one that only names a position in a plot (protagonist, love interest, foil, deuteragonist).
7. **B's sources.**  (a) the SOC broad tier with O*NET's descriptions, plus O*NET's alternate titles, all ranked
   by familiarity and distance from the corpus (Roger's rule of 2026-10-16, § 6; the DOT sample dropped); (b) add
   ESCO and ISCO-08 once their licences are read.  **Recommend (a)**; the alternate-titles file and the BLS OEWS
   employment table are small fresh downloads under `data/external/`.  *Long version:* [§ 6](#6-generator-b-lists-of-professions) (generator B).
   **Decided (Roger, 2026-10-21): (b) if ESCO's and ISCO-08's licences can be confirmed acceptable, else (a).**
8. **C's crossover test** for D&D inventions: (a) >= 3 works outside D&D or >= 10 Wikidata sitelinks; (b) Roger
   reads the SRD list once and marks the inventions he wants (about 60 names, twenty minutes).  **Recommend (b)
   for the SRD and (a) for anything beyond it**; and whether the playable species are in (recommend yes).  *Long version:* [§ 7](#7-generator-c-monsters-fantasy-races-and-folklore) (generator C).
   **Decided (Roger, 2026-10-21): (b)**: being in the SRD is a good marker that a creature is not original to D&D.  The playable species are included.
9. **Which of D's modes first.**  (a) the Roget / WordNet noun census and the LLM role grid; (b) the LLM grid
   only; (c) the census only.  **Recommend (a)**, census first.  *Long version:* [§ 8](#8-generator-d-a-role-mode-for-the-trait-generators) (generator D).
   **Decided (Roger, 2026-10-21): (a)**, the census first.
10. **Build order** as § 11, the shared path piloted on the 355 held rows before any generator.  **Recommend
    yes.**  *Long version:* [§ 11](#11-build-order).
   **Decided (Roger, 2026-10-21, in chat): no; B moves to second**, after the shared path, so that its ranked pick supplies the occupation half of every wave (the order as written put B last, against § 6's rule); § 11 updated.
11. **M2 for roles.**  (a) reuse the trait-calibrated settings now, recalibrate with role vectors after the
    October extraction; (b) recalibrate leave-one-out on the 8slot role vectors first ($0, an hour of Mac).
    **Recommend (a)**.  *Long version:* [§ 3](#3-the-shared-role-path) step 4 (M3 for roles).
   **Decided (Roger, 2026-10-21, in chat): (a), with a retrieval check** in the shared path, since M3 decides on text retrieval and the role vectors would test only the directional score: each of the 340 corpus roles is queried with a fresh gloss from the shared path's role-gloss call (§ 3 step 3; about 340 Haiku 5.5 calls, about $0.10), recall at 10 against the traits' 95% target; at or above it the settings stay, below it they are recalibrated on the same queries (20 against 14 words, centring on the role corpus's own mean), embeddings only.  § 3 step 4 updated.
12. **The multilingual role cell** of D (a): on Sonnet 5.5 (about $6 batched) or Haiku 5.5 (about $1), the
    same choice as plan 06's question 1.  **Recommend Sonnet for the pilot's 20%**, then whichever the
    comparison favours.  *Long version:* [§ 8](#8-generator-d-a-role-mode-for-the-trait-generators), the multilingual cell.
   **Decided (Roger, 2026-10-21): as recommended**, Sonnet for the pilot's 20%, then whichever the comparison favours.  (Plan 06's own comparison favoured Haiku, [QUESTIONS 212](./QUESTIONS.md#L346).)
