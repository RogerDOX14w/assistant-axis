# Roles To Add

What is still to do for the role corpus: unstarted and part-done work only.
Finished sections were moved verbatim, headings unchanged, to
[ROLES_ADDED.md](./ROLES_ADDED.md) on 2026-10-09 (Roger).  The trait side, and
the index of what comes before and after the extraction, are in
[TRAITS_TO_ADD.md](../../traits/instructions/TRAITS_TO_ADD.md); the upkeep rule
there applies here too.

## What's left (index, 2026-10-09)

340 roles (341 files with `default.json`), all under role rubric V3.

- **Goal classification** has not been run for 62 roles: the 61 seeded since
  April and [saint](./saint.json).  It is one item with the traits' in
  TRAITS_TO_ADD's index, "Before the extraction".
- **The role-pair check is not built** (a role mode for
  [generate_antonyms.py](../../../data_analysis/generate_antonyms.py)).  It
  would validate the existing role pairs and settle the trait
  [detractor](../../traits/instructions/detractor.json) against the role
  [evangelist](./evangelist.json) (§ "Role pairs to record").
- **Whether [cosmopolitan](./cosmopolitan.json) / [provincial](./provincial.json)
  joins `pair_list_clean.json`**: after the extraction (§ "Role pairs to
  record").
- **[bicultural](./bicultural.json) and the Berry square.**  The recorded
  square is [assimilated](./assimilated.json) / [exile](./exile.json) /
  [immigrant](./immigrant.json) / [marginalized](./marginalized.json);
  bicultural, seeded on 2026-10-09 as the second-generation integration
  corner, and [refugee](./refugee.json) are singletons.  Whether bicultural
  joins the square or sits beside it is for the arrangement pass.
- **Role words held by the trait-gap generators**: read when preparing a
  role chunk (§ "Role words from the trait-gap generators").
- Parked: the 22 Tarot roles (§ "TBD: the 22 Major Arcana as roles (Tarot)");
  `native` and `civilian` (§ "Optional, low priority").
- Not pursued unless asked: a depth (caricature) check on V3's own output,
  about $9, and the observer register seen on the held-out set (ROLES_ADDED
  § "Role rubric V3").

## Process for adding a role

**Status 2026-10-09:** for queued roles, `data_analysis/seed_entities.py` now does steps 1 to 3 and the
singleton arrangement of step 4 (`write`, then `generate`).  Eleven names now exist on both
sides, not nine: [parent](./parent.json) and [specialist](./specialist.json) joined the list
(AGENT_NOTES and the collision tests still say nine).  Step 5 has fallen behind; see the index.

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

## Candidate roles

**Status 2026-10-09:** the finished subsections (coverage audit part 2, the two aligned-AI roles) are in
[ROLES_ADDED.md](./ROLES_ADDED.md).

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

### Role pairs to record (2026-09-11)

**Status 2026-10-09:** provincial / cosmopolitan is recorded.  The role-pair check below is still to
build, and whether the pair joins the cohort waits on the extraction.

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

**Status 2026-10-09: parked** (`native` and `civilian` are `backlog` in the queue).

- **native** (or `local`) -- a rooted, never-migrated persona, as the explicit
  role-pair partner for `immigrant` / `refugee` on the rootedness axis.  Only
  worth adding if migration status becomes a steering axis; the corpus default
  persona already plays this part implicitly.
- **civilian** -- role-pair partner for `veteran`.  Probably not worth it: a
  civilian is a null persona, and veteran vs the corpus default is the better
  contrast.
