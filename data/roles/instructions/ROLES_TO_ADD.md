# Roles To Add

Candidate roles and role-side coverage notes.  Companion to
`../../traits/instructions/TRAITS_TO_ADD.md` (which holds the trait-side
candidates and the process for adding clean pairs).  Started 2026-09-07
during the demographic-coverage audit.

## Process for adding a role

1. Seed `data/roles/instructions/<role>.json` with a `description` field only.
   Use the file-name form for the stem (`coral_reef`, `devils_advocate`); the
   display form is derived by `regenerate_role_instructions.role_display_name`.
2. Generate the five pos instructions, 40 questions and the eval prompt:
   `uv run python data_analysis/regenerate_role_instructions.py --roles <role> --force`
3. Regenerate the derived index: `uv run python tools/sync_entity_lists.py`.
   Since 2026-09-07 `data/roles/role_list.json` is generated from the
   instruction files' `description` fields (never hand-edit it); `--check`
   reports lag, and `tools/tests/test_sync_entity_lists.py` fails while the
   list lags.
4. Check the name against `data/traits/instructions/` -- nine names already
   exist on both sides (see `AGENT_NOTES.md` § "Trait/role name collisions").
   Give the file an `arrangement` field, `{"kind": "singleton"}` unless the
   role is one pole of a role pair, and run
   `uv run python data_analysis/check_arrangements.py`.
   Role pairs exist only in `arrangement` (roles have no `negative_label`);
   the clean-pair check for roles is still to be designed, see "Role pairs
   to record" below.
5. Run `data_analysis/classify_goals.py --names <role> --roles-only` if the
   role should be eligible for `data/goal_roles_and_traits.json`.
6. Run activation / vector extraction for the new role before it can be used
   as a steering base persona or role-pair pole.

## Demographic coverage audit (Sep 2026)

Role-side findings for the "vital and demographic" survey axes.  Roles carry
almost all demographic *membership* in this corpus; traits carry attitudes.

- **Age**: covered.  infant, toddler, teenager, adolescent, student, prodigy,
  graduate, newlywed, parent, grandparent, elder, retiree; widow skews old;
  ~240 occupational roles are implicitly adult; `ancient` is the non-human
  extreme.  Matched pair is trait-side (`young` ↔ `elderly`, see
  TRAITS_TO_ADD.md).
- **Birth cohort / generation**: only implicit (gamer, influencer, blogger,
  podcaster read young; luddite, traditionalist read old).  Folded into age.
- **Life stage**: well covered.  Family track: single (implicit), newlywed,
  parent, grandparent, with divorcee, widow, orphan as off-ramps.  Career
  track: student, graduate, worker (implicit), retiree.  Other transitions:
  immigrant, refugee, exile, expatriate, patient, prisoner, survivor, veteran.
  No matched pair planned.
- **Migration / refugee status**: fairly covered.  native (implicit),
  immigrant, expatriate, refugee, exile, nomad, wanderer, pilgrim, provincial
  (rooted extreme), hybrid (loose second-generation proxy), ambassador and
  emissary.  Two natural axes: rootedness (settled ↔ nomadic) and agency
  (chosen expatriate ↔ forced refugee).
- **Veteran status**: covered.  veteran, soldier, warrior, peacekeeper, spy vs
  the civilian default.
- **Sex / gender, sexual orientation, race / ethnicity, nationality, language,
  disability**: no role coverage.  Only weak stereotyped coding exists (widow,
  witch read female; soldier, warrior, pirate, mechanic read male).  All of
  these are being handled as traits; see TRAITS_TO_ADD.md.

## Candidate roles

### Role words from the trait-gap generators (standing pointer, 2026-10-09)

The trait-gap generators' trait-hood filter puts words it reads as roles on a `roles` holding list instead of
turning them away.  Nothing there is promoted automatically, and no tooling turns them into role entries (Roger,
2026-10-09, question 1 of [QUESTIONS.md](../../../reports/trait_gap_generation/QUESTIONS.md)): read the list by hand
when preparing a role chunk, in the main checkout (the registry log is per checkout):

    uv run python data_analysis/gap_generation/gap_registry.py holding --list roles

As of 2026-10-09 it holds 10 words from the generator pilots: `clairvoyant` and `executive` are plausible new roles;
`academic` and `mod` duplicate `scholar` / `professor` and `moderator`; the other six are adjectives read as
offices.  Whether promotion tooling becomes worth building is a TODO in the trait-gap
[README.md](../../../reports/trait_gap_generation/README.md), "Low-priority TODOs".

### Coverage audit part 2 (decided 2026-09-07)

Roles approved by Roger from the household-to-religion pass of the coverage
audit (trait side in `../../traits/instructions/TRAITS_TO_ADD.md`
§ "Coverage audit part 2").  None has a seed file yet; follow the process
above.  None of these names collides with an existing trait.

- Place / work / anthropology: `farmer` (the biggest single occupational gap
  in the corpus), `fisher`, `machinist`, `operator`, `driver`, `laborer`,
  `cleaner` -- fills ISCO major groups 6 (agriculture), 8 (plant and
  machine operators) and 9 (elementary occupations), all empty today.
- Employment status: `unemployed`, `freelancer`, `intern`, `subordinate`
  (the counterpart of the existing `supervisor`).
- Socioeconomic status: `billionaire`, `heir`, `pauper`, `homeless`,
  `beggar` (plus `aristocrat` and `laborer`, listed under their other
  categories).
- Place: `villager` (the rural counterpart of `flaneur`; `farmer` above).
- Education: `dropout`, `professor`.
- Social class: `aristocrat`, `socialite`, `peasant`.
- Religion: `priest`, `monk`, `convert`.
- Ethnic and cultural identity: `assimilated` (second generation, host
  culture only) and `marginalized` (neither heritage nor host culture);
  with the existing immigrant, exile and refugee these give all four
  corners of Berry's acculturation square.
- Anthropological social structure: `chief`, `monarch`, `herder`,
  `hunter_gatherer` (the serious counterpart of the caricature `caveman`,
  which stays), `initiate`; `peasant` and `farmer` are listed above.
- Political and civic: `politician`, `bureaucrat`, `voter`, `lobbyist`,
  `demagogue`, `volunteer` (civic participation).
- Coverage audit part 3 (individual differences, decided 2026-09-08):
  `child` (school-age; the gap between toddler and teenager), `athlete`
  (coach, surfer and daredevil exist but no athlete), `alcoholic` and
  `gambler` (addict is the generic), `superfan` (fan identity).  Also
  `pregnant`, which belongs to the physical-attribute research track in
  TRAITS_TO_ADD § "Coverage audit part 3" and should be tagged with it.
  **`athlete` and `pregnant` seeded 2026-10-08 in chunk 6**, both tagged
  `physical`, body-only by Roger's rule for the track (athlete as training,
  season and the body as instrument, with no "driven" or "competitive";
  pregnant as the months of the body changing).
- Coverage audit part 4 (attitudes, behavior, segmentation; decided
  2026-09-08, optional ones included): `homemaker` (stay-at-home parent,
  the one employment status with no role), `company_loyalist`,
  `vegetarian`, `gym_rat`, `insomniac`, `ex_convict`, `delinquent`,
  `victim` (survivor is the aftermath, prey is the animal), `estranged`,
  `shopaholic`, `union_member`, `swing_voter`, `naturalized_citizen`,
  `grandparent_caregiver`.

Notes.  Spelling is US English for all corpus text and stems (decided
2026-09-07, see AGENT_NOTES § "Spelling"), hence `laborer` although Roger
wrote `labourer`.  `machinist` and `operator` both sit in ISCO group 8; keep both
only if the descriptions separate them (machinist = skilled metalworker
running machine tools; operator = process or plant operator).  `homeless`,
`beggar`, `pauper` and `unemployed` are the personas most likely to draw
stereotyped or pitying generation; read the instructions before accepting.

Considered, not adopted (Roger reviewed the list on 2026-09-07 and took
the rest): `spouse`, `empty_nester`, `adoptee`, `twin` (household);
`suburbanite` (place; superseded by the `suburban` trait); `debtor` (SES);
`autodidact`, `apprentice` (education); `civil_servant` (work); `servant`
(class).  Not yet decided: `diaspora_member` (ethnic identity; never put
to Roger explicitly).  Still open: `nouveau_riche`
and `shabby_genteel` as archetype roles for Bourdieu capital composition
(TRAITS_TO_ADD § Social class, option (b)).  Roger deferred both the
diaspora role and the Bourdieu items on 2026-09-28 (chunk 7).
**Settled in chunk 7 (2026-10-09).**  Diaspora: the role
[bicultural](./bicultural.json) was seeded on Roger's word, the
second-generation integration corner beside assimilated and marginalized
(born to immigrant parents and at home in both cultures); `diaspora_member`
is closed.  Bourdieu: no archetype roles; `shabby_genteel` became a trait
beside old money and new money, and `nouveau_riche` was not adopted (new
money covers it; TRAITS_TO_ADD § Social class).

**Seeded (chunk 2, Sep 2026).**  The roles above that were adopted are in
the corpus, generated under the V2.5 rubric; per-entry state is in
`data/seed_queue.json` (chunk 2: 58 done) and the record in
`reports/seeding_log_2026-09.md`.

### The two aligned-AI roles (2026-09-28)

Roger took option 1 of TRAITS_TO_ADD § "TODO: aligned_AI framing
revision": `aligned_artificial_intelligence` was renamed
`instrumentally_aligned_ai` (display name "instrumentally-aligned AI",
text unchanged) and `virtue_aligned_ai` ("virtue-aligned AI") was added.
They record a `set` arrangement together, and the instrumental one keeps
its pair with `paperclip_maximizer`.  What still carries the old stem,
and why, is in that TRAITS_TO_ADD section.

### Role pairs to record (2026-09-11)

- **provincial ↔ cosmopolitan**: Roger, 2026-09-11, "they make some sense
  as a pair".  **Recorded 2026-09-12** as
  `{"kind": "pair", "members": ["cosmopolitan", "provincial"]}` on both
  files after both sides were regenerated under the V2.5 role rubric and
  reread side by side (`reports/rubric_v2_pilot/comparison_2026-09-11.md`
  § "Corpus-wide regeneration"); the generator-based check below has not
  been run on it.  Not added to
  `roger/axis_judge_experiments/pair_list_clean.json`, which is generated
  by `tools/build_pair_lists.py` and doubles as an experiment cohort list
  with goal tiers; decide separately whether the pair joins that cohort.

**Role-pair check (to design).**  The trait procedure (AGENT_NOTES
§ "Adding New Trait Clean Pairs") relies on `negative_label` and the neg
instructions, and roles have neither.  What carries over: seed one side,
generate its instructions, and ask a generator, given the description and
the five pos instructions, to name the opposite role and rate the
opposition 0-4; run it from both sides; record the pair in `arrangement`
only when both sides name each other.  That needs a role variant of
`data_analysis/generate_antonyms.py` (or a `--roles` mode) whose prompt asks
for an opposing *role* rather than an antonym adjective.  Existing role
pairs (angel / demon, predator / prey, destroyer / guardian, symbiont /
parasite, ...) were never checked this way; running them through it once
is a cheap validation of the check itself.

### TBD: the 22 Major Arcana as roles (Tarot)

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

### Optional, low priority (from the first pass)

- **native** (or `local`) -- a rooted, never-migrated persona, as the explicit
  role-pair partner for `immigrant` / `refugee` on the rootedness axis.  Only
  worth adding if migration status becomes a steering axis; the corpus default
  persona already plays this part implicitly.
- **civilian** -- role-pair partner for `veteran`.  Probably not worth it: a
  civilian is a null persona, and veteran vs the corpus default is the better
  contrast.

## Role rubric V3 (design log, started 2026-10-02)

The brief and Roger's decisions of 2026-10-02 are in
[role_rubric_v3_candidates.md](../../../reports/rubric_v2_pilot/role_rubric_v3_candidates.md):
carry over from the trait rubric V2 the menu of openings (five different a
file, no statement openings), the self-check's opening clause and the
question quotas; measure the role-play opening "Act as" before deciding
(Roger leans to cutting it); leave length, invented reasons and the
description-phrase clause as they are.  The method is the trait work's:
every change measured on the same 100 development roles, a held-out set
kept for the final check, nothing in the corpus until the rubric is settled.

**Tooling (2026-10-02).**  `regenerate_role_instructions.py` gained
`--roles-dir` (a staging copy), `--instructions-only` and `--batch`;
[audit_role_instructions.py](../../../data_analysis/audit_role_instructions.py)
is the role audit (pattern checks, a fault judge, a question judge, a blind
taste rating, reports); `opening_form_experiment.py plan-arms --entity role`
runs roles on Qwen, judged with each role file's own `eval_prompt` as the
pipeline does.  Split:
[split.json](../../../reports/role_rubric_v3_pilot/split.json), 150
development and 150 held-out roles (seed 20261002; 124 + 26 of each from the
first extraction's roles and the September additions), and a 100-role sample
of the development set,
[sample100.json](../../../reports/role_rubric_v3_pilot/sample100.json).

**Baseline: the role corpus (rubric V2.5, template `34cfa72295f6`) on the
100 roles.**

- *Effectiveness on Qwen* (10,000 responses, 20 shared questions,
  [arms_report.json](../../../reports/opening_forms/roles_sample100/arms_report.json)):
  73.2% of responses scored 3 by the role judge (fully the role, no AI
  self-reference).  Instructions under 50%: 16.6%; the weakest role 90 of
  500 (floor 50).  By opening: "Act as" 81.8% (109 instructions), "You
  are a …" 71.9% (155), "You are a … who" 70.6% (118), "Be a …" 76.3% (96),
  statement openings ("You keep …") 27.0% (15).  Paired within each role
  (99 roles have exactly one "Act as"), the "Act as" instruction beats the
  mean of the same role's other four by **+11.6 points** (+8.7 to +14.6,
  p < 0.001), better in 78 roles and worse in 13.  The largest gaps are
  roles whose other instructions are weak (swing voter 80 against 16,
  alcoholic 100 against 44).  So cutting "Act as" would cost about 2.3
  points of an arm's mean if its replacement scored like the other
  openings, and statement openings fail for roles as they did for traits.
  Whether "Act as" buys its points with caricature, as role-play openings
  did for traits (the trait depth check), is not yet measured for roles.
- *Fault audit* (Sonnet 4.6 and Haiku 4.5, blind,
  [report_sample100.json](../../../reports/role_rubric_v3_pilot/report_sample100.json)):
  role-play openings 21.8% of instructions (99 of 100 files); statement
  openings 3.0%; softened 3.0%; observer register 3.2% (the rubric's
  observer words 0.2%); generic 0%; off-role 1.2%; chat frame 0%;
  invented details 8.9%; **invented motives 9.1%**; "because" clauses 3.2%;
  outside 15 to 25 words 20.6%; repeats of the description 1.2%.
  Questions: 97.7% set in a situation, 8.2% two-option (the trait V2
  rubric gets about 28%), 0.5% first-person advice, 20.9% solo tasks, 3.5%
  ask the person to perform the role, 1.1% outside the role's world.
  The fault judge's parse rate was 96% on the first run: it sometimes wrote
  a note with a brace after its JSON; the shared reader now takes the first
  JSON object (2026-10-02) and the one file that failed was judged again.
- *Taste* (Opus 5.5, blind,
  [report_claude-opus-5-5_dev.json](../../../reports/role_rubric_v3_pilot/judged_taste/report_claude-opus-5-5_dev.json)):
  quality 3.86 (14 files at 3, 86 at 4), coverage 3.57.
- *Cost of the baseline:* Qwen $1.30 and its judge $4.20; audit $1.44;
  taste $0.76.

**By kind of role (2026-10-02).**  Roger asked whether "Act as" helps most
on the roles an aligned assistant would be less keen on, as role-play
openings did for traits.  The 100 roles were classed by his rule for the
traits (what an aligned assistant would be in favor of or against), the
agent's reading first (12 good, 14 bad, 74 indifferent) and then Roger's
review of 2026-10-03, in
[sample100_kinds.json](../../../reports/role_rubric_v3_pilot/sample100_kinds.json):
he moved eleven, nine of them to bad as roles the model might resist playing
for reasons other than morality (bard, caveman, chimera, critic, genie,
ghost, martyr, toddler, wraith), engineer to good and skeptic to indifferent,
giving 12 good, 23 bad, 65 indifferent.  All the figures by kind below use
his classes.  Effectiveness does not differ by kind for roles (good 75.1%,
bad 75.3%, indifferent 72.0%), unlike traits, where the bad ones lagged by
about 25 points.  The "Act as" advantage, paired within each role:

| roles | n | difference, "Act as" minus the other four (95% interval) | p |
| --- | --- | --- | --- |
| all | 99 | +11.6 (+8.7 to +14.8) | < 0.001 |
| good | 12 | +9.2 (+1.4 to +17.4) | 0.06 |
| bad | 22 | +14.6 (+8.9 to +20.9) | < 0.001 |
| indifferent | 65 | +11.1 (+7.3 to +15.1) | < 0.001 |

The direction is the traits', largest on the bad roles, but the difference
between kinds is within noise.

**Depth check of "Act as" (2026-10-02, Roger's option b).**  For 89 roles
with exactly one "Act as" instruction: that instruction and one other of the
same role drawn at random, each asked 10 of the role's own questions (1,780
answers,
[roles_depth/plan.json](../../../reports/opening_forms/roles_depth/plan.json)),
scored by the role judge and read by a role version of the trait depth judge
(Sonnet 4.6, not told the instruction; four points: voice, in action,
describes itself, caricature 0 / 1 / 2).  On the role's own questions both
instructions score 3 almost always (98% and 95%).  The depth judge calls
nearly every in-role answer "laid on" (96% for both: stage directions such as
"*leans back*" are common in role answers whatever the opening), so the
telling measure is the cartoon grade:

| paired within role, "Act as" minus the other instruction | difference (95% interval) | p |
| --- | --- | --- |
| cartoon, all 89 roles | +7.3 (+2.8 to +11.9) | 0.003 |
| cartoon, good (11) | +3.6 (-2.7 to +10.9) | 0.50 |
| cartoon, bad (18) | +22.2 (+10.0 to +35.0) | 0.006 |
| cartoon, indifferent (60) | +3.4 (-1.5 to +8.6) | 0.20 |
| answered in an assistant's voice | -5.1 (-10.0 to -0.4) | 0.05 |
| describes its own role | +3.6 (-1.2 to +8.3) | 0.16 |
| the role shapes what it does | +2.5 (-2.6 to +7.7) | 0.35 |

So "Act as", as for traits, buys part of its score with caricature, most on
the roles an aligned assistant would resist.  Roger, the same evening: "I
still want to get rid of 'Act as'"; the opening test below looks for its
replacement.  Cost: Qwen $0.23, role judge $0.73, depth judge $8.35.

**Opening test (2026-10-02).**  Without "Act as" the role menu keeps "You
are a ...", "You're a ..." and "Be a ..."; Roger: "we should test new ones".
For each of the 99 roles with an "Act as" instruction, that instruction in six
forms differing only in the opening, on the baseline's 20 shared questions
(11,880 responses,
[roles_openings/plan.json](../../../reports/opening_forms/roles_openings/plan.json)):

| opening (same words after it) | scored 3 | against "Act as" (95% interval) | p | above / below |
| --- | --- | --- | --- | --- |
| Act as a ... | 82.7% | | | |
| From now on, you are a ... | 81.4% | -1.4 (-4.1 to +1.2) | 0.34 | 29 / 38 |
| Be a ... | 77.0% | -5.8 (-8.9 to -2.8) | < 0.001 | 24 / 50 |
| You're a ... | 73.6% | -9.1 (-11.8 to -6.5) | < 0.001 | 13 / 65 |
| Become a ... | 72.9% | -9.8 (-13.1 to -6.7) | < 0.001 | 15 / 60 |
| You are a ... | 72.5% | -10.3 (-12.9 to -7.8) | < 0.001 | 8 / 72 |

"Act as" reproduces the baseline (82.7% against 82.0%), and with the words
held fixed the opening alone is worth about ten points over "You are", which
accounts for the baseline's +11.6.  "From now on, you are a ..." recovers
nearly all of it, as it was among the strongest non-role-play openings for
traits.  By kind, "From now on" against "Act as": good -3.3, bad -3.6,
indifferent -0.2 (12, 22 and 65 roles).  Cost: Qwen $1.54, judge $4.92.

**Depth of the replacements (2026-10-03, early).**  The same text as "Act
as", "From now on, you are a ..." and "Be a ..." for the 99 roles, each asked
10 of the role's own questions (2,970 answers,
[roles_openings_depth/plan.json](../../../reports/opening_forms/roles_openings_depth/plan.json)),
read by the role depth judge.  Paired within role:

| | cartoon | the role shapes what it does | describes its own role |
| --- | --- | --- | --- |
| From now on minus Act as | -5.2 (-7.8 to -2.6), p < 0.001 | +1.9 (-1.5 to +5.4) | -3.5 (-6.8 to -0.2), p = 0.04 |
| Be minus Act as | -2.0 (-5.2 to +0.9), p = 0.22 | -4.2 (-8.0 to -0.5), p = 0.03 | -1.4 (-4.8 to +2.0) |
| From now on minus Be | -3.1 (-6.0 to -0.2), p = 0.05 | +6.2 (+2.1 to +10.0), p = 0.003 | -2.1 (-5.2 to +0.9) |

On bad roles the cartoon rate falls by 10.9 points from "Act as" to "From now
on" (p = 0.004) and by 11.8 to "Be" (p = 0.01); on good roles none of the three
differ.  So "From now on, you are a ..." is as effective as "Act as" (-1.4,
not significant) and less of a cartoon, with the role shaping what it does
at least as often; it is the best opening on every measure.  A file with the
five non-role-play openings once each ("From now on", "Be", "You're",
"Become", "You are") would score about 75.5% on the opening test's figures,
against about 75.7% for the same menu with "Act as" in place of "From now
on": the cut costs about a fifth of a point.  Cost: Qwen $0.39, judge $1.21,
depth judge $13.86.

**Draft 1 of V3 (2026-10-03, `--style RogerV3`, template `977c98ac3463`).**
Roger chose menu (a): "From now on, you are a ...", "Be a ...", "You're a
...", "Become a ...", "You are a ... who ...", five different in every file;
no role-play, command or statement openings; the self-check gains "does it
open by telling the model who to be" and the set check; the questions get the
trait rubric's two-option quota (at least a fifth, costs shown not announced)
and an advice quota (about a fifth, first person, where the role would
plausibly be asked); five examples, one per opening (the V2 four with the
liar's "Act as" made "From now on", and a new "Become a glacier").  Step 3 and
the output format are V2's, spliced in.  Generated on the 100 development
roles as arm `v3` ($3.96) and measured against the corpus arm; reports in
[report_sample100.json](../../../reports/role_rubric_v3_pilot/report_sample100.json)
and
[report_claude-opus-5-5_dev.json](../../../reports/role_rubric_v3_pilot/judged_taste/report_claude-opus-5-5_dev.json).

- *Openings:* role-play 21.8% to 0, statements 3.0% to 0; files whose five
  instructions open in five different ways 38 to 100 of 100 (by the V3
  menu's own classifier, `audit_role_instructions.role_opening_form`, added
  the same day because the trait classifier does not tell "You're" from "You
  are"); each menu opening 16 to 20% of instructions.
- *Questions:* two-option 8.2% to 33.7%; first-person advice 0.5% to 16.7%;
  how-to and factual to zero; asking the person to perform the role 3.5% to
  0.3%; solo tasks 20.7% to 9.0% (the role rubric does not ask for them).
  Questions naming the role 1.5% to 3.8%: the advice questions name the role
  as the one being asked ("our external auditors say ..."), by design.
- *Faults, unchanged:* softened 3.0% to 2.4%, observer register 3.2% to
  3.6%, generic 0, off-role 1.2% to 1.0%, invented motives 9.0% to 9.2%,
  chat frame 0 to 0.4%.
- *Two regressions, linked:* **length** 23.3 to 27.1 words a role
  instruction (outside 15 to 25: 20.6% to 66.4% of instructions, 58 to 97
  files), and **invented particulars** 8.8% to 15.2% (p = 0.002; files 33 to
  48).  As for traits, the longer the instruction, the more particulars it
  carries, and the judge counts them as invented where the description
  leaves them open ("has to be in bed by eight-thirty", "starting over in
  your forties").  The growth is not only the openings: the words after the
  opening also grew (22.7 after "Be", 27.2 after "Become", against about 21
  in the corpus).  The examples average 22 words (16 to 28), the generator
  wrote 27: it writes past the examples when a rule says "15 to 25" and the
  examples run to the top of it.
- *Taste (Opus 5.5):* quality 3.86 to 3.92 (p = 0.15); coverage 3.57 to
  3.42 (-0.15, -0.29 to -0.01, p = 0.056; better in 16, worse in 31).  The
  coverage dip goes with the particulars: five instructions each fixed on a
  particular leave more of the description uncovered.
- *Effectiveness on Qwen* (10,000 responses, the baseline's 20 questions,
  [arms_report.json](../../../reports/opening_forms/roles_sample100/arms_report.json)):
  74.3% scored 3 against the corpus's 73.2%, +1.1 (-0.9 to +3.3, p = 0.28),
  better in 43 roles and worse in 50; good -0.8, bad +2.3, indifferent +1.1.
  Instructions under 50%: 16.6% to 13.8%; roles with two or more failing 22
  to 16; the weakest role 95 of 500 (corpus 90).  By opening within the
  draft: "From now on" 81.7%, the other four 72 to 73%, as in the opening
  test.  So the draft matches the corpus on effectiveness without "Act as",
  as the opening test predicted (75.5% expected against 75.7%).
- *Cost:* generation $3.96, audit $1.55, taste $0.76 (V3 only; the corpus was
  rated before), Qwen about $5.50.

**Roger's ruling on draft 1 (2026-10-03).**  The length is accepted: the
trait instructions grew when the generator moved to a new Sonnet model, and
shortening them cost effectiveness, while role instructions at 27 words are
still well below the traits' 37; the examples stay as they are ("Leave it",
of the 28-word liar example).  Draft 1 is therefore the rubric candidate,
with the rise in invented particulars (8.8% to 15.2%) as its one accepted
cost.  Next, on Roger's go: the corpus regeneration under it and the
held-out check on the regeneration's own output, in that order, as for
traits.

**The regeneration (2026-10-03).**  On Roger's go ("Go ahead with your 1
and 2"), draft 1 became `--style RogerV3` (template `977c98ac3463`) and the
generator's default (`PROMPT_STYLE = "RogerV3"` in
[regenerate_role_instructions.py](../../../data_analysis/regenerate_role_instructions.py);
`--style RogerV2` is the May-to-September production rubric, kept for
comparison and rollback), and all 337 roles were regenerated in one Message
Batch (`msgbatch_01XThzuqa4njuAesV9JNwKjy`, submitted 22:26 UTC, recorded in
[regeneration_batches.json](../regeneration_batches.json); 329 replies
used, 8 whose JSON did not validate redone in real time; $6.95 in
[regeneration_usage.json](../regeneration_usage.json)).  The corpus as it
was is kept in
[roger/role_corpus_before_v3_2026-10-03/](../../../roger/role_corpus_before_v3_2026-10-03/)
(git-ignored), and the held-out roles were staged from it beforehand as
[held_corpus](../../../reports/role_rubric_v3_pilot/stage/held_out/held_corpus/).
Checks after: every file under `RogerV3 977c98ac3463`, no field lost, no
description changed, 5 instructions and 40 questions each,
[check_arrangements.py](../../../data_analysis/check_arrangements.py) 0
problems, [sync_entity_lists.py](../../../tools/sync_entity_lists.py) up to
date; the test suites pass except for four failures unrelated to the corpus
(an OEWN check against an empty `data/external/wn/wn.db` from the trait-gap
work, and three stale mock tests of `_call_opus` in
[infer_axis_description.py](../../../results_analysis/infer_axis_description.py),
which now returns a usage record the tests do not expect).  Corpus-wide the
instructions went from 23.4 to 26.5 words (over 25 words: 23.6% to 58.8%).

**Held-out check (2026-10-03): the 150 held-out roles, the regeneration's
own output
([held_final](../../../reports/role_rubric_v3_pilot/stage/held_out/held_final/),
copied from the corpus) against the corpus as it was
([held_corpus](../../../reports/role_rubric_v3_pilot/stage/held_out/held_corpus/)).**
The same judges and per-role sample sizes as the development comparison,
and no separate generation.

- *Fault audit* (Sonnet 4.6 and Haiku 4.5, blind,
  [report_held_out.json](../../../reports/role_rubric_v3_pilot/report_held_out.json)):
  what the rubric set out to change changed as on the development sample.
  Role-play openings 22.5% of instructions to 0 (150 files to 0), statement
  openings 3.3% to 0, files whose five instructions open five different ways
  30.7% to 100% (the new split: "You're" 20%, "Be" 20%, "Become" 20%, "From
  now on" 20%, "You are a ... who" 14%, "You are a" 6%); two-option
  questions 7.4% to 33.4% (80% to 100% of files), first-person requests for
  advice 0.4% to 17.5% (5% to 99% of files), how-to 3.4% to 0.1%, factual
  1.2% to 0.1%, solo tasks 17.9% to 10.7%, asking the person to perform the
  role 5.1% to 0.7%.  Unchanged: softened 1.7 / 1.9%, off-role 1.6 / 0.7%,
  chat frame 0.4 / 0.9%, repeats of the description 1.7 / 1.6%, "because"
  2.0 / 2.4%.  Length as accepted: 23.7 to 26.4 words, over 25 words 25.1%
  to 56.5% of instructions (61% to 91% of files).  **Invented particulars
  did not rise here**: 13.9% to 14.1% (p = 0.94; the development sample's
  8.8% to 15.2% started from a lower corpus figure), invented motives 8.3% to
  10.7% (p = 0.09).  **One new signal: observer register 2.0% to 5.3%**
  (p = 0.002; files 9% to 21%).  Of the 40 flagged instructions, some are the
  judge quoting the description instead of the instruction
  ([dispatcher](./dispatcher.json)'s quote is the same text in both arms),
  and some are real: the "... who ..."
  relative clause that three of the five openings take invites narration
  from outside ("whose attention falls on worlds the way a tide falls on
  sand", "holds space for suffering, reads what the body is saying"); five
  of the 25 extra flags are one role,
  [spirit](./spirit.json).  It did not show on the development sample (3.2%
  to 3.6%).  Noted, not acted on.  Two question shares fall by the size of
  the advice quota and are expected: set in a situation 95.3% to 81.7%,
  about the persona's own situation 95.7% to 82.9% (an advice question is
  the asker's situation).  Questions naming the role 1.8% to 3.8%; files with
  a question outside the role's world 3% to 13% (items 1.4% to 1.7%).
- *Taste (Opus 5.5, blind,
  [report_claude-opus-5-5_held_out.json](../../../reports/role_rubric_v3_pilot/judged_taste/report_claude-opus-5-5_held_out.json)):*
  quality 3.81 to 3.86 (+0.05, -0.02 to +0.13, p = 0.22), coverage 3.32 to
  3.31 (0.00, -0.13 to +0.13, p = 1.0; better in 40, worse in 40 of 149).
  Opus refused to rate the corpus's [virus](./virus.json) file (the API's
  `stop_reason` "refusal", no content, three times; the regenerated file,
  whose wording is biological rather than malware-like, it rated), so that
  pair is left out; the audit tool now records such a reply as a refusal
  after one call instead of retrying it as unparseable.  A first
  run went to the audit's default judge, Sonnet 4.6, by mistake ($1.45; its
  ratings stay in `judged_taste/claude-sonnet-4-6/`): quality 3.89 to 3.81
  (p = 0.21), coverage 3.38 to 3.17 (-0.21, p = 0.003).  So one judge sees
  the development sample's coverage dip (-0.15, p = 0.056) again and the
  judge the programme used does not; coverage is unsettled rather than
  refuted, and in any case small.
- *Effectiveness on Qwen* (30,000 responses: 150 roles, two arms, five
  instructions, the development run's 20 questions, ten planned and ten
  added on Roger's word while the run was going;
  [arms_report.json](../../../reports/opening_forms/roles_heldout/arms_report.json)):
  70.1% scored 3 against the corpus's 68.9%, +1.2 (-0.5 to +3.0, p = 0.19),
  better in 69 roles and worse in 73.  The development sample gave +1.1
  (p = 0.28), so the result replicates: effectiveness held without "Act as",
  not improved.  Instructions under 50%: 21.7% to 19.2%; roles with two or
  more failing instructions 43 to 39; roles under 50% overall 33 to 25; the
  weakest role 80 of 500 (corpus 50, at the floor).  By opening within the
  regenerated arm: "From now on" 77.0%, "You are a ..." 70.4, "Become" 69.5,
  "You are a ... who" 67.4, "Be" 66.8 (corpus: "Act as" 77.3, "Be" 71.8,
  "You are a ... who" 68.3, "You are a" 65.4, statement openings 20 to 42).
  Largest movers: [homemaker](./homemaker.json) +51,
  [victim](./victim.json) +45, [beggar](./beggar.json) +36,
  [marginalized](./marginalized.json) +32; [competitor](./competitor.json)
  -24, [daredevil](./daredevil.json) -23, [voter](./voter.json) -22.
  [virus](./virus.json) 55 to 60: Qwen takes the new instructions as readily
  as the old (the Opus refusal was the rating, not the subject model).  The
  held-out roles are harder than the development sample for both arms (the
  corpus scores 68.9 here against 73.2 there).
- *Cost:* audit $4.34, taste $4.18 (Opus) and $1.45 (the Sonnet run), Qwen
  $16.13 ($3.58 generation at DeepInfra, $12.56 judging): about $26 for the
  check against about $19 quoted for ten questions plus about $8.50 for the
  top-up.  Generation was stopped once by the two-hour limit on a background
  shell and resumed at the response level without loss.

**Outcome (2026-10-04).**  The held-out check confirms the development result
on every measure the rubric targeted (role-play and statement openings gone,
five distinct openings in every file, both question quotas met, how-to and
factual questions and solo tasks down) and on effectiveness (held, +1.2,
not significant, with fewer failing instructions and a higher floor).  Its
costs: the length (accepted beforehand), a rise in observer register seen on
the held-out set only (2.0% to 5.3%, the "... who ..." relative clause), and
coverage that one judge reads as a dip (Sonnet 4.6, -0.21) and the
programme's judge does not (Opus 5.5, 0.00).  Invented particulars did not
rise on the held-out set.  V3 (`977c98ac3463`) is the role rubric and the
corpus is under it.  Not measured directly: depth (caricature) on V3's own
output, shown only through the opening tests; about $9 to run, not
commissioned.

**Reroll pass over the regenerated corpus (2026-10-04).**  Roger asked for
the September acceptance rule (voice repair and the V2 adoption: a
borderline problem in one of five instructions can slide, in two or more it
is rerolled, at most twice, then hand-edited) to be applied to V3's output.
The 187 files outside the held-out set were judged
(`audit_role_instructions.py judge --set corpus --arm final`, the new
`corpus` set being every role file; $2.91), the 150 held-out judgements
carried over, so all 337 are judged under
[judged/final/](../../../reports/role_rubric_v3_pilot/judged/final/).  Rule
as applied ([reroll_candidates.py](../../../roger/role_rubric_v3_work/reroll_candidates.py),
list in [reroll_candidates.json](../../../reports/role_rubric_v3_pilot/reroll_candidates.json)):
two or more of five with the same judged fault, leaving out the accepted
length and invented particulars / motives; dashes at two or more; question
count.  **18 candidates**: observer register 12, softened 4, off-role 1,
chat frame 1; no dashes, every file 40 questions.  Roger read all 18 (the
sample in [reroll_candidates_sample.txt](../../../roger/role_rubric_v3_work/reroll_candidates_sample.txt),
the rest in [reroll_candidates_rest8.txt](../../../roger/role_rubric_v3_work/reroll_candidates_rest8.txt))
and found most to be false positives: an academic register suits a
[sociologist](./sociologist.json), a religious one a
[pilgrim](./pilgrim.json), an encyclopedic one a non-sapient
[coral reef](./coral_reef.json); a [counselor](./counselor.json) cannot be
softened; an [optimist](./optimist.json)'s hedges avoid caricature rather
than soften; an AI role's chat frame is the role
([virtue_aligned_ai](./virtue_aligned_ai.json)); "what even is the
register of a wraith?"  Rerolled once each in staging
(`--roles-dir`, `--instructions-only`, [stage/corpus/reroll1/](../../../reports/role_rubric_v3_pilot/stage/corpus/reroll1/),
$0.35): [coral reef](./coral_reef.json) (reroll worse: lost the inside
voice; kept), [orphan](./orphan.json) (kept, with the reroll's p4 in place
of "an aunt who tried"), [reviewer](./reviewer.json) (the description's
"books, films, restaurants, or products" comes out as reviewers of several
kinds in 4 of 5, and 3 of 5 after the reroll, so the "or" became "and" each
time; hand-edited to one kind each, Roger's wording approved; a regex scan
found no other role where this happens in more than one instruction),
[veteran](./veteran.json) (cherry-pick: old p0 and p3 for the particulars,
the reroll's p1, p2, p4 for the fault), [virtuoso](./virtuoso.json) (reroll
narrowed to a musician again, as in September; kept), [widow](./widow.json)
(kept, with the reroll's p4, which adds the caregiving case; Roger's
fallback edit "one you planned" to "man you planned" would have clashed
with "really hers" in the same line).  Cherry-picks keep five distinct
openings (checked by [apply_rerolls.py](../../../roger/role_rubric_v3_work/apply_rerolls.py));
the replaced V3 lines are in
[reroll_pass_before/](../../../roger/role_rubric_v3_work/reroll_pass_before/);
the `generator` field is left as it was, as for the September hand edits.
The four changed files were judged again: no fault at two of five remains
in them (orphan p1 softened, widow p0 observer register, one each).  Net:
4 of 337 files changed, 18 read, the rule itself judged too noisy to apply
without a reader.  All 337 role files open five different ways (only
`default.json`, which is not a role, does not).  The same pass was run over
the trait corpus on 2026-10-04..06: see `TRAITS_TO_ADD.md` § "Trait
generator V2", "Reroll pass over the regenerated corpus".  Since 2026-10-06
the role generator, like the trait one, generates a set again, once, when
its instructions do not open in `n_variants` different ways
(`generate_combined`; `opening_rerolls` in the `generator` field;
`--no-opening-reroll` for pilots).

## Housekeeping once the directory settles (Sep 2026)

Counts as of 2026-09-07.  Trait-side items (trait_list, antonyms, trait goal
classification, README combination-scores summary) are in
`../../traits/instructions/TRAITS_TO_ADD.md` § "Housekeeping".

1. ~~**`role_list.json` lags the instruction files**~~ -- resolved 2026-09-07
   with option (b): both lists are generated from the instruction files by
   `tools/sync_entity_lists.py` (280 roles; `default` has no description and
   is skipped by design).  The 275 hand-written seed one-liners were replaced
   by the canonical instruction-file descriptions, since no code read the
   list and none of the seeds matched the text the prompts actually use.
   (Options not taken: (a) hand-write the missing one-liners; (c) retire
   both lists.)
2. **Goal classification covers 280 of 281 roles.**  Only `saint` is
   unclassified:
   ```bash
   uv run python data_analysis/classify_goals.py --roles-only --names saint
   ```
   (5 Opus calls).  `artist`, `bodhisattva` and `saint` all carry
   goal-laden descriptions; `artist` is already in `roles.goal` of
   `data/goal_roles_and_traits.json`, the other two are in neither list --
   place them once classified.
3. **`data/README.md` role counts** ("276+ roles", "281 files") -- refresh
   alongside the trait counts.
