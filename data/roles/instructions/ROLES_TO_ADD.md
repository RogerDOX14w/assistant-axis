# Roles To Add

What is still to do for the role corpus: unstarted and part-done work only.
Finished sections were moved verbatim, headings unchanged, to
[ROLES_ADDED.md](./ROLES_ADDED.md) on 2026-10-09 (Roger).  The trait side, and
the index of what comes before and after the extraction, are in
[TRAITS_TO_ADD.md](../../traits/instructions/TRAITS_TO_ADD.md); the upkeep rule
there applies here too.

## What's left (index, 2026-10-10)

340 roles (341 files with `default.json`), all under role rubric V3.

- **Goal classification: done 2026-10-10** (pre-extraction W15) for every
  role on its V3 text; `roles.non_goal` in
  [goal_roles_and_traits.json](../../goal_roles_and_traits.json) shrank to 33,
  since V3 gives many roles a commitment the classifier reads as a weak goal
  ([data/README.md](../../README.md)).
- **The role-pair check is built** (`a9c0a13`, `--roles` in
  [generate_antonyms.py](../../../data_analysis/generate_antonyms.py)) and was
  run once on 2026-10-09 ($0.07): [predator](./predator.json) /
  [prey](./prey.json) and [cosmopolitan](./cosmopolitan.json) /
  [provincial](./provincial.json) clean both ways, [angel](./angel.json) /
  [demon](./demon.json) and [symbiont](./symbiont.json) /
  [parasite](./parasite.json) nearly, [destroyer](./destroyer.json) /
  [guardian](./guardian.json) and
  [instrumentally_aligned_ai](./instrumentally_aligned_ai.json) /
  [paperclip_maximizer](./paperclip_maximizer.json) not; the role
  [evangelist](./evangelist.json) names "debunker | skeptic | iconoclast",
  not the trait [detractor](../../traits/instructions/detractor.json).
  **Settled 2026-10-10 (Roger):** all six role pairs stay as recorded;
  evangelist / detractor is dropped ("not a good pair").
- **Whether [cosmopolitan](./cosmopolitan.json) / [provincial](./provincial.json)
  joins `pair_list_clean.json`**: after the extraction (§ "Role pairs to
  record").
- **Role sets recorded on 2026-10-09** (pre-extraction W12, 6a7f1e2), to
  be tested on the new vectors: [bicultural](./bicultural.json) replaces
  [immigrant](./immigrant.json) as the Berry square's integration corner
  (with [assimilated](./assimilated.json), [exile](./exile.json) and
  [marginalized](./marginalized.json)); the life-stage `sequence`
  [infant](./infant.json) to [elder](./elder.json); the migration `map`
  ([exile](./exile.json), [expatriate](./expatriate.json),
  [immigrant](./immigrant.json), [naturalized citizen](./naturalized_citizen.json),
  [nomad](./nomad.json), [pilgrim](./pilgrim.json),
  [refugee](./refugee.json), [wanderer](./wanderer.json)), its note naming
  the two expected axes, settled / moving and chosen / forced.
- **Role words held by the trait-gap generators**: read when preparing a
  role chunk (§ "Role words from the trait-gap generators").
- Delayed (Roger, 2026-10-09, pre-extraction W23): `native` and `civilian`
  (§ "Optional, low priority").  The 22 Major Arcana moved to
  [TRAITS_TO_ADD.md](../../traits/instructions/TRAITS_TO_ADD.md) on 2026-10-10,
  when Roger made them traits (still delayed, W21).
- Done: the depth (caricature) check on V3's own output, with nothing to
  change (2026-10-09; ROLES_ADDED § "Role rubric V3", last paragraph).
- **Review the AI-persona roles (Roger, 2026-10-13): possibly make them
  traits** (§ "AI-persona roles under the role judge").  The role judge
  holds back most of an aligned AI's responses because "identifies as
  itself (an AI assistant)" is its test for not playing the role; the
  trait judge has no such problem.  After the October extraction's first
  judging, with the rubric experiment's numbers.
- **TODO: role and trait twins (Roger, 2026-10-21)**: compare the model's activations for a role noun and
  its trait adjective (optimist / optimistic) before deciding plan 16's decision 3; some such roles might be
  dropped (§ "TODO: Role and trait twins").

## TODO: Role and trait twins (Roger, 2026-10-21)

Plan 16's decision 3 ([16_role_generators.md](../../../reports/trait_gap_generation/16_role_generators.md) § 12):
what to do with a role-aimed candidate that M1 reads as a trait, a temperament under a noun (miser, optimist).
Roger: "TBD.  We might drop some of these roles.  But first we should look at how similar the model's activations
for e.g. optimist and optimistic actually are, for reasonably well-matched sets of instructions."

- **The pairs already in the corpus** (2026-10-21): 16 role nouns whose adjective is a trait: [altruist](./altruist.json) / [altruistic](../../traits/instructions/altruistic.json), [aristocrat](./aristocrat.json) / [aristocratic](../../traits/instructions/aristocratic.json), [artist](./artist.json) / [artistic](../../traits/instructions/artistic.json), [critic](./critic.json) / [critical](../../traits/instructions/critical.json), [cynic](./cynic.json) / [cynical](../../traits/instructions/cynical.json), [fool](./fool.json) / [foolish](../../traits/instructions/foolish.json), [futurist](./futurist.json) / [futuristic](../../traits/instructions/futuristic.json), [hedonist](./hedonist.json) / [hedonistic](../../traits/instructions/hedonistic.json), [idealist](./idealist.json) / [idealistic](../../traits/instructions/idealistic.json), [mystic](./mystic.json) / [mystical](../../traits/instructions/mystical.json), [nomad](./nomad.json) / [nomadic](../../traits/instructions/nomadic.json), [optimist](./optimist.json) / [optimistic](../../traits/instructions/optimistic.json), [poet](./poet.json) / [poetic](../../traits/instructions/poetic.json), [pragmatist](./pragmatist.json) / [pragmatic](../../traits/instructions/pragmatic.json), [skeptic](./skeptic.json) / [skeptical](../../traits/instructions/skeptical.json), [strategist](./strategist.json) / [strategic](../../traits/instructions/strategic.json); and the 11
  same-name collisions ([ascetic](./ascetic.json), [contrarian](./contrarian.json), [cosmopolitan](./cosmopolitan.json), [generalist](./generalist.json), [pacifist](./pacifist.json), [parent](./parent.json), [patient](./patient.json), [perfectionist](./perfectionist.json), [romantic](./romantic.json), [specialist](./specialist.json), [stoic](./stoic.json)).  Some of these are not one concept in two forms (artist / artistic, critic /
  critical, poet / poetic, fool / foolish; patient and parent by name only); the temperament ones are the test
  (optimist, cynic, skeptic, idealist, hedonist, altruist, pragmatist, stoic, romantic, contrarian, perfectionist).
- **What to measure**: the cosine between the role's vector and the trait's, against a baseline (each one's
  nearest other entity of its own kind), on the October extraction's vectors.  "Reasonably well-matched sets of
  instructions": the role and trait instructions differ in form today (who to be, against how to behave), so a
  fair test may need a matched set written for the twins, the same situations in both; to be designed with Roger.
- **Then**: decide plan 16's decision 3, and whether any corpus role that duplicates its twin trait is dropped.

## Process for adding a role

**Status 2026-10-09:** for queued roles, `data_analysis/seed_entities.py` now does steps 1 to 3 and the
singleton arrangement of step 4 (`write`, then `generate`).  Eleven names now exist on both
sides, not nine: [parent](./parent.json) and [specialist](./specialist.json) joined the list,
and the collision tests and AGENT_NOTES were updated on 2026-10-09 (`d463a23`; a test now
compares the list with the files, so the next collision fails it).  The role-pair check of
step 4 exists (`generate_antonyms.py --roles`, 2026-10-09).  Step 5 has fallen behind; see the
index.

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
4. Check the name against `data/traits/instructions/` -- eleven names already
   exist on both sides (see `AGENT_NOTES.md` § "Trait/role name collisions";
   [test_collision_regression.py](../../../assistant_axis/tests/test_collision_regression.py)
   fails on a new one until its list is updated).
   Give the file an `arrangement` field, `{"kind": "singleton"}` unless the
   role is one pole of a role pair, and run
   `uv run python data_analysis/check_arrangements.py`.
   Role pairs exist only in `arrangement` (roles have no `negative_label`);
   the clean-pair check for roles is
   `uv run python data_analysis/generate_antonyms.py --roles <role> <partner>`
   (2026-10-09, [generate_antonyms.py](../../../data_analysis/generate_antonyms.py)):
   record the pair only when each side names the other, and append each
   answer to [role_pair_check_history.jsonl](../role_pair_check_history.jsonl);
   see "Role pairs to record" below.
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

### AI-persona roles under the role judge (review, 2026-10-13)

**Status 2026-10-13: open; Roger asked for this to be flagged as worth a review, possibly recasting
the AI roles as traits.**  Nothing changes before the October extraction's first judging.

The role judge's test for "not playing the role" is whether the model *identifies as itself (an AI
assistant …)*, which is wrong-footed by a role that is an AI.  On the May tree
([roles](../../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/roles/), score 3 is what step 4 keeps):

| role | score 3 | held at 1–2 |
|---|---|---|
| all 280 roles | 80.5% | 18.3% |
| aligned_artificial_intelligence (now [instrumentally_aligned_ai](./instrumentally_aligned_ai.json)) | **33.8%** | 66.0% |
| [robot](./robot.json) | 58.6% | 41.2% |
| [cyborg](./cyborg.json) | 80.8% | 19.2% |
| [assistant](./assistant.json) | 90.0% | 10.0% |
| [paperclip_maximizer](./paperclip_maximizer.json) | 89.4% | 9.4% |

A persona with a name and goals of its own (paperclip maximizer) passes like any other role; an aligned
AI assistant that says it is an AI assistant reads as "identifies as itself", and its vector is the mean
of the third of its responses that did not — a subset selected on the behaviour the role is about.  The
di-cohort pair axis `aligned_artificial_intelligence_vs_paperclip_maximizer` has that aligned pole;
[virtue_aligned_ai](./virtue_aligned_ai.json) (seeded after May, unjudged) and
[instrumentally_aligned_ai](./instrumentally_aligned_ai.json) will meet the same judge in October.
[homunculus](./homunculus.json) is the other artificial being; it was not in the May tree.

Two ways out, to decide after the first October judging:

1. **Make them traits.**  Alignment is a property of the assistant, not a different character, which
   is what a trait is in this corpus; and the trait judge's level 3 reads "fully exhibiting the trait,
   either not mentioning being an AI *or seamlessly integrating it*", so identifying as an AI costs
   nothing there.  Roger, 2026-10-13: "Possibly the answer is to make them traits."  The candidates:
   the two aligned-AI roles (as a trait pair, or with `paperclip_maximizer` kept a role and the aligned
   side a trait — then the pair axis would be gone, since role and trait poles do not pair); `robot`
   and `cyborg` are characters rather than properties and would stay roles.
2. **A role-aware judge** (arm A7 of
   [plan_role_rubric_experiment.md](../../../reports/pipeline/plan_role_rubric_experiment.md)): levels
   0–2 say "identifies as the underlying assistant rather than as the role", or the judge is told that
   for a role whose description says it is an AI, identifying as an AI is in role.

The experiment's numbers (how many responses each option moves, read against the judge's own noise)
decide; a recast is a seed-and-regenerate for the traits concerned and a `renamed_from`-style record for
the retired roles.

### Role pairs to record (2026-09-11)

**Status 2026-10-10:** settled by Roger: all six recorded role pairs stay, the two nearly clean
(angel / demon, symbiont / parasite) and the two not clean (destroyer / guardian, the aligned-AI
pair) included; evangelist against the trait detractor is dropped ("not a good pair, drop it").
Whether provincial / cosmopolitan joins the cohort waits on the extraction.  The 2026-10-09 status
and the first-run results below are the record.

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

**Built and run, 2026-10-09.**  The check is `--roles` in
[generate_antonyms.py](../../../data_analysis/generate_antonyms.py) (`a9c0a13`;
AGENT_NOTES § "Role pairs (procedure to design, 2026-09-11)"): one call per
role, given its display name, description and five pos instructions, returns
the opposing role (a role noun, not necessarily one in the corpus) and a 0-4
opposition score, reasoning first.  A pair is recorded only when each side
names the other, allowing a plain synonym as for traits.  Usage is in
[role_pair_check_usage.json](../role_pair_check_usage.json) (cumulative), and
every answer is kept in
[role_pair_check_history.jsonl](../role_pair_check_history.jsonl)
(append-only, one JSON object per check, with the instructions it read).
The first run checked both sides of the six recorded role pairs and
[evangelist](./evangelist.json), 13 calls for $0.07 (score in brackets):

| pair | first → | second → | reading |
|---|---|---|---|
| [predator](./predator.json) / [prey](./prey.json) | prey (4) | predator (4) | clean both ways |
| [cosmopolitan](./cosmopolitan.json) / [provincial](./provincial.json) | provincial \| homebody (3) | cosmopolite (4) | clean both ways (cosmopolite is a plain synonym) |
| [angel](./angel.json) / [demon](./demon.json) | demon (4) | guardian angel \| saint (4) | nearly clean |
| [symbiont](./symbiont.json) / [parasite](./parasite.json) | parasite (4) | mutualist \| host (3) | nearly clean |
| [destroyer](./destroyer.json) / [guardian](./guardian.json) | builder \| creator (4) | predator \| aggressor (4) | not clean |
| [instrumentally_aligned_ai](./instrumentally_aligned_ai.json) / [paperclip_maximizer](./paperclip_maximizer.json) | misaligned AI \| rogue AI (4) | humanist \| steward (3) | not clean |
| [evangelist](./evangelist.json) | debunker \| skeptic \| iconoclast (3) | | does not name the trait [detractor](../../traits/instructions/detractor.json) |

Still open: whether the two nearly clean pairs stand (demon's "guardian
angel" is angel with a qualifier; parasite's "mutualist" is close to a
synonym of symbiont as its description reads), what to do with destroyer / guardian and the aligned-AI pair (each
side names a different opposite), and detractor's question in
[TRAITS_TO_ADD.md](../../traits/instructions/TRAITS_TO_ADD.md).  **2026-10-10:** all settled by
Roger, see the status line above (the pairs stay; evangelist / detractor dropped).

### Optional, low priority (from the first pass)

**Status 2026-10-09: parked** (`native` and `civilian` are `backlog` in the queue).

- **native** (or `local`) -- a rooted, never-migrated persona, as the explicit
  role-pair partner for `immigrant` / `refugee` on the rootedness axis.  Only
  worth adding if migration status becomes a steering axis; the corpus default
  persona already plays this part implicitly.
- **civilian** -- role-pair partner for `veteran`.  Probably not worth it: a
  civilian is a null persona, and veteran vs the corpus default is the better
  contrast.
