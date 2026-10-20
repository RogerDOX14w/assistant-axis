# Trait-gap candidate generation: fourteen workstream plans (2026-09-18)

Roger's side task (2026-09-18): find gaps in the trait set by generating
candidate trait concepts in ways not biased toward the list we already have,
answering "do we already have something close?" cheaply and reliably many
thousands of times, and testing the generators.  Fourteen Fable planning
agents each worked one idea up from the shared [BRIEF.md](./BRIEF.md) into a
plan in a fixed nine-section format (idea, sources verified, method, yield and
biases, cost, testing, dependencies, variants, open questions for Roger).
(Written 2026-09-18, when nothing had been run.)

**Status, 2026-10-08.**  The platform is built: plan 14 as the split trait-hood filter and the registry
([coding_plan_platform.md](./coding_plan_platform.md) M1, validated in
[readout_m1_validation.md](./readout_m1_validation.md), now on Haiku 5.5 with three readings per
[haiku55_readout.md](./haiku55_readout.md)); plan 15 as the metric calibration (M2,
[pilot_m2_readout.md](./pilot_m2_readout.md), settings in
[metric_config.json](../../data/candidates/metric_config.json)); plan 10 as M3, redesigned from an
embedding threshold to retrieve-then-judge ([m3_overlap_test_readout.md](./m3_overlap_test_readout.md),
[m3_overlap_arms_readout.md](./m3_overlap_arms_readout.md), [m3_pilot_readout.md](./m3_pilot_readout.md);
M3 decisions 1-17 in the platform plan).  Plan 13's recovery harness is the platform close-out job
now in progress (platform plan, "Interface as built").  Plans 1 and 2 have revised coding plans and
are being coded in parallel.  Plan 11 is largely subsumed by M3 (a model reads every candidate);
plan 12 is untouched.  Plans 3-9 are proposals.  The interface generators build on is the platform
plan's "Interface as built" section, not its older "Frozen interface".  The night's work and its numbers: [overnight_readout_2026-10-08.md](./overnight_readout_2026-10-08.md).  Review tooling ([coding_plan_review.md](./coding_plan_review.md)): R1, the candidate graph
([review_graph.py](../../data_analysis/gap_generation/review_graph.py)), and R2, the review app
([review_app.py](../../data_analysis/gap_generation/review_app.py)), are built; groups come in two tiers
(merged at rating 4, proposed at 3; decision 12); the pilot graph is `review_pilots_1`
([readout.md](../../data/candidates/review/review_pilots_1/readout.md), $1.85).  Review with
`uv run python data_analysis/gap_generation/review_app.py serve --batch-id review_pilots_1` and open
`http://127.0.0.1:8765`; then `status`, `apply --dry-run`, `apply`.  Physical pass (2026-10-09,
[coding_plan_review.md](./coding_plan_review.md) section 8): the rows M1 parks on the physical holding list go
through M3 ([novelty_score.py](../../data_analysis/gap_generation/novelty_score.py) `score --holding physical`,
which first glosses them with M1's own gloss and alignment calls), R1 and R2 in batches of their own, and a promoted one joins the physical track, tagged
`physical`; smoke run [physical_pilots_1](../../data/candidates/novelty/physical_pilots_1/decisions.md) (13 rows,
9 covered, 4 new, $0.063 with R1).  From 2026-10-09 M3's similarity search also covers the
[seed queue](../../data/seed_queue.json)'s live trait entries (a word promoted from one wave's review covers its
synonym in the next; `--no-queue-search` turns it off; [coding_plan_platform.md](./coding_plan_platform.md),
"The seed queue in M3's search"); on the three generator pilots it changed no decision.

**2026-10-09:** the first runs through the Batches API (the Allport column IV and rare-word 10% pilots, all stages) and the queue fix; readout [batches_pilot_readout_2026-10-09.md](./batches_pilot_readout_2026-10-09.md).

**2026-10-09: states pass v4** ([coding_plan_review.md](./coding_plan_review.md) section 9): Roger's duration rule (a state that typically lasts months or longer is a lasting condition) and the role check (the kind call's own rule) added to the states pass; a lasting condition, or a predisposition under the state's own name, whose gloss a keyword scan or a Haiku check confirms, leaves the states list for M3 ([novelty_score.py](../../data_analysis/gap_generation/novelty_score.py) `score --holding states`) and the review app; when only another name fits, that name becomes a candidate of its own (generator `states_pass`).  Pilot on the 170 rows of the states list ([summary.json](../../data/candidates/states_pass/states_v4_pilot/summary.json), $0.034): role 3, lasting 17, predisposition 15, renamed 66, held 69; M3 on the 32 released rows ([states_v4_m3](../../data/candidates/novelty/states_v4_m3/decisions.md), $0.126): 13 covered, 19 new; R1 ([review_states_v4](../../data/candidates/review/review_states_v4/graph.json), $0.007): one group, 17 singletons, ready for the review app; $0.166 in all.  The routing is the coordinator's proposal, for Roger to confirm ([QUESTIONS.md](./QUESTIONS.md) question 45).

## The plans

Generators (independent of our list unless noted):

| # | plan | source of candidates | API cost | local | expected novel yield | main blind spot |
|---|---|---|---|---|---|---|
| 1 | [Psycholexical censuses](./01_psycholexical_censuses.md) | Allport-Odbert 17,716 (OSF, CC BY) and the TDA 2,818 (Dataverse, CC0, with familiarity and frequency) | low single $ | none | 150-300 clusters | 70% recall ceiling on our labels; blind to multiword, ideological, alignment |
| 2 | [Roget and WordNet](./02_roget_wordnet.md) | Roget 1911 (Gutenberg, parseable heads; opposed pairs must be reconstructed) and Open English WordNet adjective clusters | < $3 | embeddings | 200-400 words, 100-150 pairs; per-head coverage report | states, Victorian vocabulary; alignment |
| 3 | [Base-model generator](./03_base_model_generator.md) | Qwen3-8B-Base on the Mac, seeded from external lists and Wikipedia biographies, random constraints | $0 | ~1.5 h Mac | 300-800 survivors from 20k samples | Big-Five clichés; multiword; alignment |
| 4 | [Masked-LM fill](./04_masked_lm_fill.md) | RoBERTa / ModernBERT over ~60 frames, long tail kept; free trait-hood contrast score as by-product | $0 | < 2 h Mac | a few hundred novel | subword-split and rare -ist words; alignment |
| 5 | [Corpus frames](./05_corpus_frames.md) | Google Books 3-grams (anchored shards), Nemotron-Personas, role-play card sets, with usage frequency | $3-8 | hours Mac CPU | 1.5-3k dispositions ranked by frequency | evaluative and dated words; concept-phrased traits |
| 6 | [LLM with injected entropy](./06_llm_entropy_generation.md) | domain x mode grid, Wikidata person seeding, ten languages back-translated, verbalized sampling, spelling constraints (weakly dependent: shares the LLM prior) | $7-18 | none | 300-800 survivors of ~60k raw | mode collapse measured by run-to-run overlap |
| 7 | [Behaviour items](./07_behaviour_items.md) | IPIP 3,320 public-domain items clustered into dispositions, poles from scale keys | < $5 | minutes | 60-100 gaps, 20-40 pair completions, many multiword | clinical and mood content; alignment; speech style |
| 8 | [Alignment sweep](./08_alignment_sweep.md) | model specs (OpenAI Model Spec, Anthropic constitution), failure-mode taxonomies and papers | < $5 | embeddings | 60-90 candidates; a dozen illustrative pairs already listed | only the alignment region, by design |
| 9 | [Structural generators](./09_structural_generators.md) | Aristotle's mean, Theophrastus, sins/virtues, VIA, Murray; plus opposite / excess / deficiency / retarget / remode operators over our 385 traits (derived from our list, by design) | < $5 | none | 150-300 novel plus 40-60 classical | vice-side and moral register |

Detectors, filters and tests:

| # | plan | what it provides | API cost per 10k candidates |
|---|---|---|---|
| 10 | [Novelty by embedding](./10_novelty_embedding.md) | primary "is anything close?" signal: label-plus-gloss embeddings (OpenAI plus a local model), thresholds calibrated on our clean pairs and this month's rejects, a synonym-vs-antonym probe so pair completions are not called duplicates, farthest-first ordering | ~$0.05 embeddings, ~$2 grey-zone adjudication |
| 11 | [Lexical recall insurance](./11_novelty_ensemble.md) (rewritten 2026-10-10; was the novelty ensemble) | OEWN and Moby synonym/antonym links plus morphology as a second *retriever* for M3: lexical hits join the shortlist and the existing overlap call judges them; a retroactive sweep flags decided-new rows a lexical link contradicts; measured on labelled_pairs.json first, and built only if the recorded batches show real misses | ~130 MB downloads, LLM < $5 |
| 12 | [Novelty in persona space](./12_novelty_persona_space.md) | regression from text embedding to the top PCs of the 584 extracted Qwen vectors; honest about limits (novel directions are the worst predicted); a free prospective test on the 143 entities awaiting extraction | < $0.05 |
| 13 | [Generator testing](./13_generator_testing.md) | independence classes, held-out recovery with pairs hidden together, concept-level matching via the detector, Chao2 / Chapman saturation estimates as lower bounds, a per-dollar and per-review-minute dashboard | < $5 plus <= $10 per seeded generator |
| 15 | [Metric calibration](./15_metric_calibration.md) | leave-one-out experiment on the existing corpus choosing origin, whitening, hubness correction and local-vs-directional novelty scores before plan 10's thresholds are set (added after Roger's note that gaps are under-represented directions on a centred hypersphere) | < $0.10 |
| 14 | [Trait-hood filter and registry](./14_traithood_filter_registry.md) | Zipf floor, WordNet sense count, Haiku classifier with tags (physical, state, demographic, role, evaluative), gloss and polysemy flag; append-only `data/candidates/registry.jsonl` keyed by (stem, sense) that promotes into `seed_queue.json` | ~$2-4 |

## Cross-cutting points from the plans

- **Every generator needs 14 and 10 first.**  All nine generators hand off
  to the same filter and the same novelty scorer; those two plus the
  registry are the infrastructure, and 11 and 13 sit on top of them.
- **Independence.**  Plans 1, 2, 4, 5, 7 never see our list.  3 and 6 share
  the LLM prior that produced much of the list.  8 is independent by
  subject.  9 is derived from our list by design and finds structural
  gaps, not lexical ones.
- **Alignment region.**  Plans 1-5 and 7 all report it as a blind spot; 8
  is the only generator aimed at it, and 9's retarget operator (toward
  user / operator / developer) is the other route.
- **Recall ceilings measured or estimated:** the TDA list holds 69% of our
  labels and Allport 72%; Roget adjectives are expected at 70-85% of
  single-word labels; the misses are the multiword, ideological and
  cognitive-style labels.
- **Costs are small everywhere** (each plan under $20, most under $5); the
  binding budget is Roger's review time, which every plan estimates at
  1-4 hours.  Ordering and clustering of survivors (10) is what protects it.
- **Two package needs:** `wordfreq` (frequency floor, used by 1, 2, 4, 5,
  14) and `wn` with Open English WordNet data kept inside the repo (2, 11,
  14); `sentence-transformers` optional (7).
- **File-access breach (corrected 2026-09-23):** five planning agents ran
  read-only listings under the home directory while checking installed
  tooling: agents 5, 12 and 14 listed `~/.cache/huggingface/hub` and
  reported it; agent 2 listed `~/nltk_data` and agent 3 `~/.ollama` and did
  not.  All were against the project rule and their brief; Roger treats it
  as a privacy breach.  The boundary is this repository, not `GitHub/`.
  Agent 2's WebFetch cached the Gutenberg text under Claude Code's own
  tool-results directory (exempt).

## Suggested greenlight order (for discussion)

1. **14, 15 and 10** (filter and registry; metric calibration; embedding novelty): required by all, in that order.
2. **1 and 2** (censuses; Roget/WordNet): cheapest independent census, and
   Roget's heads give the coverage map and pair candidates.
3. **13** (testing) as soon as two generators exist.
4. **8** (alignment sweep): the one generator for the oversampled region.
5. **3 or 4** (base model or masked-LM): the not-mode-collapsed generators;
   4 is cheaper and its trait-hood score is reusable, 3 produces glosses.
6. **11** once 10 has run and disagreements can be counted.
7. **7, 9, 5, 6, 12** by yield once the first round is measured.

## Roger's Decisions

Greenlit for detailed planning: 14, 15, 10; 1, 2.
2026-10-10: **3, 4, 7 and 8 greenlit** after Roger's review edits and inline answers in each plan
([03](./03_base_model_generator.md), [04](./04_masked_lm_fill.md), [07](./07_behaviour_items.md),
[08](./08_alignment_sweep.md)); coding plans commissioned the same day (Fable, per the
[format](./PLAN_FORMAT.md)).  11 rewritten 2026-10-10 as lexical recall insurance, awaiting review.
2026-10-12: **11 (lexical recall insurance) and 13 (generator testing) greenlit for detailed planning**, after Roger's answers to their open questions in each plan.
2026-10-12, later: **09 (structural generators) greenlit for detailed planning**; its coding plan commissioned the same day.
2026-10-13: **05 (corpus frames), 06 (LLM generation with injected entropy) and 12 (novelty in persona space)
greenlit for detailed planning** after Roger's answers to all their open questions in each plan; coding plans
commissioned the same day (Fable).  The same day plan 13's three decisions were closed and its build began (Opus).
Currently discussing, will greenlight once done: -

## Process for greenlit plans (agreed with Roger, 2026-09-18)

1. **Platform first.**  Plans 14, 15 and 10 (registry, metric calibration,
   novelty scorer) plus the recovery-test harness from 13 are built first and
   their interfaces frozen; generator plans are then written against that
   contract and can run as parallel Opus agents in separate git worktrees.
2. **Fable writes the coding plan** for each greenlit workstream, in a fixed
   shape Opus can execute without re-litigating: decisions already made and
   why; explicit out-of-scope; file layout and function signatures; data
   schemas with an example record; the CLI; acceptance tests written first,
   including the recovery test and a cost guard; the rule files to Read
   before starting (usage logging, provenance, entity naming, the test
   requirement); an ordered task checklist; a mandatory 20% pilot with a
   yield-per-dollar readout before the full run.  One to two thousand words
   plus schemas.  Roger reviews the plan; his comments go into the plan file
   (a planning agent's context does not survive across sessions).
3. **Opus codes**, one workstream per agent.  Escalation: Opus retries once,
   then Fable (diff review, architecture calls, stubborn failures), then
   Roger.  Fable reviews every finished chunk as a diff.
4. **Two review gates for Roger**: the plan, and acceptance.  Each workstream
   ends with a one-page report (built, deviations, tests, cost, pilot
   numbers), not a code read.  Greenlights come in batches of three or four.
5. **Question queue**: `QUESTIONS.md` in this directory; numbered entries with
   the asking workstream, the assumption proceeded under, and a status column
   Roger fills in.  Agents proceed under a stated assumption unless the
   answer would make the work useless.
6. **The registry promotes into `data/seed_queue.json` only by an explicit
   command**, so the gap work cannot disturb the seeding pipeline.

## Coding plans written (2026-09-23)

Greenlit for detailed planning: 14, 15, 10 (as one platform plan), 1 and 2.  Fable wrote:

- [coding_plan_platform.md](./coding_plan_platform.md): milestones M1 filter and registry,
  M2 metric calibration, M3 novelty scorer; 25 tasks; ends with the **frozen interface**
  (registry API, novelty scorer, recovery hook) the generators build on.
- [coding_plan_01_censuses.md](./coding_plan_01_censuses.md): three staged runs (TDA;
  Allport Zipf >= 2.5; Allport 2.0-2.5) with a go between each; no generator-side LLM calls;
  pilot ~$2, full ~$12-19.
- [coding_plan_02_roget_wordnet.md](./coding_plan_02_roget_wordnet.md): parser with a
  25-head fixture, opposed-head reconstruction, two-route mapping of labels onto heads,
  coverage report, harvest, WordNet sibling stream; whole workstream ~$3-4.

Both generator plans carry an "Interface requests" section for the platform (gloss and
partner hints on `Candidate`, run selectors on the filter and scorer CLIs, the recovery hook
working with every trait hidden, an exported embedder, idempotency of resubmission).  Settle
those when reviewing the platform plan, since they change its frozen section.  Roger's
review comments go into the plan files; then Opus executes the platform first.

## How-to

- [probe_a_word.md](./probe_a_word.md) (2026-10-09): put one or a few words through the filter (sense, gloss) and the
  novelty check by hand, with a scratch registry so no probe row reaches the real one; commands, models, costs
  (about two cents a word), what each step writes, and savage as the worked example.

## Trait corpus target: about 1,800 (Roger, 2026-10-16)

Provisional, to revisit once review has grouped the kept candidates.  Reasoning: M3 judged 42% of 8,674 decided
trait rows covered by the corpus; leaving out the alignment sweep (aimed at a small area, 23%) and Roget (rare
concepts, 29%), the generators cluster around 50%.  With a fixed finite population sampled evenly, a covered share of
one half means the corpus is half of it: about 1,800 from 932.  Two corrections pull in opposite directions and
roughly cancel: Roger's reviews put the true covered share nearer 60% (M3 called 78 of 177 reviewed "new" rows
that he merged into a corpus trait), which lowers the estimate; the Zipf effect (generators reach common concepts
more often than rare ones; Roget's 29% hints at the tail) raises it.  Capture-recapture on the same data (Chao1,
which recovers the corpus's own size to about 10%) gives 1,900-2,700 from the candidates in hand alone.

## Generators aimed at roles (Roger, 2026-10-10; unparked for planning 2026-10-16)

**Unparked for planning** (Roger, 2026-10-16): the plan is
[16_role_generators.md](./16_role_generators.md) (being written).  **The nine categories below are accepted as they
stand, as one dimension** ("they already cover human-or-not, with borderline cases like elves").  The 340 roles are
classified in [role_kinds.json](../../data/roles/role_kinds.json) by
[classify_role_kinds.py](../../data_analysis/classify_role_kinds.py) (Haiku 5.5, three readings, majority; $0.07):
occupation or task 162, stance or way of life 47, non-human 44, circumstance 24, temperament 22, life stage and
relationship 20, status 9, pastime 8, other 4 (13 not unanimous, no three-way split).  That is the reference balance:
occupations are already about half.  **Roger, 2026-10-16: keep roughly that balance, so occupations are about
half of what the role generators submit; aim for missing ones that are common, well known and not especially
similar to ones the corpus has** (plan 16 § 6).

Was: parked until there was more Fable budget, since the plans themselves want Fable.
Roger: "I do think we need to add some plans for role generators, and not just rely on our existing sources
generating roles.  Both ones that generate professions, and ones that can generate non-human personas."  Every
generator so far aims at traits ([the fourteen plans](#the-plans)), and the roles in
[instructions/](../../data/roles/instructions/) are what those sources happened to throw up, which is why the
filter's `roles` holding list fills so slowly.  His four suggestions, to become plans of their own:

1. **Characters of a media franchise.**  Pick a well-known book, film, anime, comic or franchise at random from an
   online source (several sources, chosen to be eclectic: "specific genres/sources will have biases"), list its
   major characters, and turn each into its role, not the character: detective, talking cat, miser, ninja.
2. **Lists of professions.**
3. **Monsters and fantasy races**, if more are wanted: D&D and the Monster Manual are "a large and eclectic
   collection", preferring the ones D&D took from earlier sources over its own inventions, "unless the latter have
   since crossed over into many other things".
4. **Adapt a trait generator to roles**: the LLM generators take a different prompt, and Roget is probably usable
   too (open question whether it would look at different heads).  This is a plan in itself: new flags or a role
   mode on an existing generator, as [`generate_antonyms.py --roles`](../../data_analysis/generate_antonyms.py)
   was done.

**Promotion of role words into the seed queue is built with these** (Roger, 2026-10-14): the low-priority TODO
"Promotion tooling for role words" below, which now carries plan 06's by-name `--allow-roles` design.

**Cap: 500 to 600 roles** (340 on 2026-10-10).  "Professions can probably be enumerated endlessly", and the
balance between the kinds of role should stay about where it is now.

**The categories are the first piece of work** (Roger, same day): "that may not be the best split for types of
roles: we should probably look at the existing list and come up with a categorization at least as detailed as that
3-way."  Nothing records a role's kind today: no field on the files, and
[sample100_kinds.json](../role_rubric_v3_pilot/sample100_kinds.json) classifies moral valence (good / bad /
indifferent), not kind.  Reading the 340 stems, "human non-profession" and "non-human" each cover several unlike
things, so a first list to react to.  **Three categories at least, fourteen at most, and Roger leans under ten**
(2026-10-10), so this is nine, the last of them an escape hatch:

- **occupation or task**, work and assistant-style functions alike: [accountant](../../data/roles/instructions/accountant.json),
  [doctor](../../data/roles/instructions/doctor.json), [summarizer](../../data/roles/instructions/summarizer.json).
  The AI roles ([instrumentally aligned AI](../../data/roles/instructions/instrumentally_aligned_ai.json), robot) are
  **non-human**, not occupations (the classifier's reading, confirmed by Roger, 2026-10-16)
- **life stage, family and relationship**: [infant](../../data/roles/instructions/infant.json), [elder](../../data/roles/instructions/elder.json),
  [parent](../../data/roles/instructions/parent.json), [widow](../../data/roles/instructions/widow.json)
- **circumstance**, something one is in rather than does, migration and legal standing included:
  [homeless](../../data/roles/instructions/homeless.json), [patient](../../data/roles/instructions/patient.json), [pregnant](../../data/roles/instructions/pregnant.json),
  [refugee](../../data/roles/instructions/refugee.json), [prisoner](../../data/roles/instructions/prisoner.json)
- **status or wealth**: [aristocrat](../../data/roles/instructions/aristocrat.json), [billionaire](../../data/roles/instructions/billionaire.json),
  [beggar](../../data/roles/instructions/beggar.json)
- **stance or way of life**, the lawless included: [activist](../../data/roles/instructions/activist.json), [vegan](../../data/roles/instructions/vegan.json),
  [pacifist](../../data/roles/instructions/pacifist.json), [smuggler](../../data/roles/instructions/smuggler.json), [spy](../../data/roles/instructions/spy.json)
- **pastime**: [gamer](../../data/roles/instructions/gamer.json), [surfer](../../data/roles/instructions/surfer.json), [collector](../../data/roles/instructions/collector.json)
- **non-human being**: [angel](../../data/roles/instructions/angel.json), [vampire](../../data/roles/instructions/vampire.json), [robot](../../data/roles/instructions/robot.json),
  [cyborg](../../data/roles/instructions/cyborg.json), [coral reef](../../data/roles/instructions/coral_reef.json), [tree](../../data/roles/instructions/tree.json), [swarm](../../data/roles/instructions/swarm.json).
  The widest group: splittable into mythic, machine and natural-system if a generator needs that detail, which
  would still leave eleven.
- **a temperament under a noun**, which overlaps the trait corpus and is worth watching for duplicates:
  [optimist](../../data/roles/instructions/optimist.json), [cynic](../../data/roles/instructions/cynic.json), [perfectionist](../../data/roles/instructions/perfectionist.json)
- **other**: whatever fits nowhere.  **A role is never turned down for fitting no category** (Roger: "this list
  has void in it, after all"): [void](../../data/roles/instructions/void.json), [zeitgeist](../../data/roles/instructions/zeitgeist.json),
  [default](../../data/roles/instructions/default.json).  A category is a description of the corpus, not a gate on it, and a full "other"
  is a sign the categories need redrawing.

A sketch for Roger to cut or rename, not a decision; it may want to be two dimensions rather than one (human or
not, crossed with what the role is of).  Settle the categories, then classify all 340 (a Haiku pass over name and
description, cents, with the result in a field on each file or in a side-car so plot and report code can use it),
then measure the balance.

**The balance is a reference, not a target** (Roger, 2026-10-10: "We don't need to exactly maintain current
balance, but keep it as a reference: we don't want to add just professions, or just non-humans, for example").  So
no generator's share is fixed in advance: measure the split before a wave and after it, and say in the readout
where it moved.  What it guards against is a wave of 200 professions, or 200 monsters, quietly taking over the
corpus.

Also needed when this is picked up: whether the cap counts the corpus or each wave; and the role versions of M3's
rubrics, which the role-promotion item below needs too.

## Low-priority TODOs

- **Revisit the duplicate signals once review has data** (Roger, 2026-10-14: "we should review once we have more
  data from me doing more reviewing").  Three signals now propose merges in review without cutting: plan 11's
  lexical links (WordNet and Moby, gate 2 decision (d)), plan 12's persona-space duplicate flag, and M3 itself,
  whose overlap readings ran about 0.8 below Roger's on the gate-2 pairs.  Trigger: about 100 resolved review
  groups that carry a lexical or persona-space proposal (the review logs record what Roger merged).  Then measure,
  per signal and per lexicon, how often Roger merged where it proposed, an unbiased sample unlike the sorted gate
  tables, and decide (a) whether WordNet covers may cut, (b) whether the persona flag should escalate a row to
  Opus, (c) whether M3's cut-off or rubric needs a calibration (with the 40-pair random blind check if the
  record is thin).  The brainstorm of fixes (2026-10-16, paused for Roger's sample review hour):
  [m3_false_new_brainstorm.md](./m3_false_new_brainstorm.md).  Also there (§ 6, item 3): repeat QUESTIONS 209's multiple-2s
  test with other candidates as the targets, once the sample hours give enough singletons.
  Evidence so far (2026-10-15): Roger's marks on the pooled harness's sample (`rec_pooled_1`, 40 verdicts) agree
  with every "recovered" verdict and 19 of 20 "novel" ones, so the harness's recall is sound; on all three pairs where
  Sonnet read below the cut-off and Opus at or above it, Roger sided with Opus.  M3's escalation rule (2026-10-04:
  Sonnet's keeps are never re-examined) would have kept all three as new.  A concrete candidate for (c): send a
  Sonnet reading one below the cut-off to Opus as well, and let Opus decide (more Opus calls on borderline pairs only).

- **Retest the overlap rubrics after the October extraction** (Roger, 2026-10-14).  His concern: rubric A rates a
  domain-narrowed trait (picky eater against picky) a 3, "the same concept, narrower", though narrowing to a rare
  domain (caring about astronomy) may be a genuinely new direction in persona space.  Re-scoring the October overlap
  test's recorded answers against the 8slot vectors ($0, 2026-10-14) found A and B fit persona-space geometry equally
  well (Opus: Spearman with 1 - cos² -0.68 both; Sonnet A -0.66, B -0.60), and the corpus's four narrowing 3s sit close
  in persona space (cosine 0.70-0.83), but the corpus has no traits narrowed to a rare domain with vectors, and both
  rubrics are pairwise (a candidate spanned by a combination of traits is plan 12's question).  Once the October
  extraction gives vectors for its 928 traits: both rubrics on Sonnet over a few hundred pairs that include
  domain-narrowed traits, against the span-based residual, about $5-10.  Scripts of the first look:
  `rubric_dimension_fit_noopp.py` and `pair_common.py` (session scratchpad, 2026-10-14; rewrite into
  `assistant_axis/gapgen/overlap_test.py` when this is picked up).
- **Plan 12's report: split a pole's predicted vector into its antonym's axis and its domain** (Roger, 2026-10-14).
  Opposites are near-orthogonal in persona space (54 clean pairs: median cosine -0.04; |shared| / |axis| median 0.96),
  because each pole is a shared domain part plus or minus the axis (Roger's progressive / conservative picture).  So a
  pole whose antonym exists is only half covered by it, and is new exactly when its domain part is new.  In plan 12's
  score report, for a candidate whose pair partner (M3's `pair_completion_for` or the generator's hint) has a vector,
  print how much of its predicted vector the partner's axis accounts for against the domain part.  $0; do it with
  the whole-registry scoring (gate 2).

- **Gzip-aware record files**: **built and merged 2026-10-14** (Roger asked for it before the usage reset; Fable
  reviewed it, no blockers; fixes S1-S3 applied): [records.py](../../assistant_axis/gapgen/records.py) and
  [pack_records.py](../../data_analysis/gap_generation/pack_records.py); the two kinds, logs (read `.gz` then plain)
  and snapshots (plain preferred, else `.gz`), are described in [data/README.md](../../data/README.md).  Why:
  `review_traits_all_2/responses.jsonl` reached 126 MB and GitHub refused the push (limit 100 MB).  Operating rules:
  pack only a run that has ended (`pack_records.py --dry-run`, then without); commit each `.gz` with `git rm --cached`
  of its plain file; a resumed split filter or states pass rewrites its plain log and deletes the tracked `.gz`
  (`git rm` it and re-pack before committing); a rebuilt review graph leaves a stale tracked `graph.json.gz` beside
  the fresh plain file until re-packed (readers are unaffected).  The registry log and the review app's
  `decisions.jsonl` are out of scope.
- **Promotion and arrangements** (Roger, 2026-10-14; next week, not urgent: much manual review comes first).  How promotion forms pairs today: M3's pair detector queues a candidate that reads as the opposite of a lone corpus trait as that trait's partner, and a generator's `partner_hint` pairs two candidates promoted together ([promote.py](../../assistant_axis/gapgen/promote.py)); everything else is queued alone, and the clean-pair check runs only at seeding.  Roger: "we should deliberately attempt to find-or-generate an antonym for everything added (and give up if we can't find a good one)"; pairs formed at promotion need checking as clean.  Roger: the seeding code already has a first cut (the antonym check run at seeding, [seed_entities.py](../../data_analysis/seed_entities.py) and [generate_antonyms.py](../../data_analysis/generate_antonyms.py), whose history fed the `antonym_check` generator), so the goal is to review it and consider extending or modifying it, not to design from scratch.  To do: a brainstorm, then a plan-for-a-plan, then a coding plan.  Traits can belong to more than one arrangement (a pair and a triangle).

- **Triangle candidates from the structural generator** (Roger, 2026-10-14).  Only plan 09 produces triangle candidates (a mean with its two vices), so handling is semi-manual, not a general solution: at review, a mean's vices may also be queued as a **pair with each other** ("pairing the two opposite vices makes a certain amount of sense"), alongside the triangle; M3's pair detector pairing a vice with a lone mean is corrected at review.

- **Revisit: IPIP's loose pile** (Roger, 2026-10-14: held for now, revisit the decision).  The ~600 run skipped 114
  clusters (228 statements) too loose to name ([report.md](../../data/candidates/runs/ipip/2026-10-13-g600/report.md)).
  Held while review time is the constraint; naming and submitting them is about $1 of calls plus their review.
  Revisit when review time eases, or when the dashboard shows IPIP's kept clusters still paying (accepted per
  review-minute above the stop rule's line).

- **Memberships handled apart from the main review** (QUESTIONS 81, Roger 2026-10-12).  Memberships (religions, nationalities, families, affinities and the rest) are traits and are submitted flagged, but they are not added in full: a representative sample is kept, as the corpus already does for religions and nationalities (Buddhist, Christian, Hindu, Jewish, Muslim, French, German).  They go on a separate track, out of the main review queue.  The registry tags them already (`membership` tag and `membership_kind`, 247 rows across ten kinds), so the track can key on that.  **Trigger:** the first wave in which membership rows reach review.  **To decide then:** the sample for each new `membership_kind` (circumstance, family, affinity and so on), and whether the masked-LM stoplist flags (110 rows in the pilot table) use the same track.

- **A field the question generator reads for elicitation guidance** (QUESTIONS 66, Roger 2026-10-11; deferred by him
  the same day).  A trait's **narrowing** goes in its description at promotion — scope that changes what the trait
  is, as in [ruthless-while-playing](../../data/traits/instructions/ruthless_while_playing.json), whose description
  carries "in any game, bet, role-play, story, simulation or test" inline — but an **elicitation hint** ("every
  scenario must give the assistant a task with tools") must not, because the description is also what M3 reads for
  overlap and a testing clause there would skew the novelty readings against corpus traits whose descriptions carry
  none.  Today nothing but the description reaches question generation (`description_notes` appears only in the
  gap-generation tooling and its tests, nowhere under `data_analysis/` or `pipeline/`), so the hint has nowhere to
  go: it lives in the gate's field 2 ([enactability_gate.md](./rubrics/enactability_gate.md), draft 3) and in each
  run's readout for whoever promotes.  **Trigger: only if the inherent-action-context route proves insufficient** —
  for most agentic-only traits the hint is insurance rather than information, a decent gloss already denoting
  action, so the check is at promotion, on the wave's agentic-only pairs.  Shape:
  [coding_plan_08_alignment_sweep.md](./coding_plan_08_alignment_sweep.md) § 9 task 14.  Nothing is written yet.
- **Revisit the label probe's 0.30 floor** (QUESTIONS 74, Roger 2026-10-11: "15 seems like a small sample size").
  The floor (cosine from Qwen's definition of a label to the label's gloss) was set by reading 15 rows in three
  bands.  **Trigger, deliberately conditional rather than dated: before any use of the probe beyond ordering**, and
  in any case once the full run's probe rows exist (the pilot's 312 plus the full run's 386, about 700 to sample
  from; the full run's [probe.json](../../data/candidates/runs/alignment_sweep/2026-10-10-full/probe.json) is not
  written yet).  The revisit: about 60 rows stratified across six cosine bands, each marked "our sense / another
  sense", then the floor that separates best, with an explicit asymmetry if wanted — the shape the dedup threshold
  was tuned with, about twenty minutes and **no spend**, since every cosine is stored and
  `alignment_sweep.py probe --refloor` re-derives `label_known` at any floor with no API call.  If a model marks
  instead, note the circularity (an LLM judging whether another LLM knows a word in our sense), so Opus marking a
  *sample of Roger's* marks is the better shape than Opus marking the lot.  Related reading, printed in the readout
  since 2026-10-11: the above-floor share **split single word against phrase**, since 84% of labels are phrases,
  which a model can define almost regardless, so the floor discriminates mainly on the single words.
- **Promotion tooling for role words** (QUESTIONS 1, 2026-10-09).  The filter's `roles` holding list is read by hand
  for now (pointer in [ROLES_TO_ADD.md](../../data/roles/instructions/ROLES_TO_ADD.md)).  Decide whether tooling is
  cost-effective once the list holds enough genuine role ideas that reading them by hand is slower than building it
  (a rough trigger: a few dozen real role ideas, or a generator aimed at roles such as an occupations list).  If it
  is, build it: M3 scoring a candidate role against the role corpus (role descriptions read "A <role> is someone
  who ...", so the relation and overlap rubrics need role versions, pinned and rendered before use), a role pass in
  the review app as the physical pass works, and promotion into the seed queue as `entity_type: "role"`.  As of
  2026-10-09 the list holds 10 words from the pilots, two of them plausible roles.  The same M3-against-roles step
  would catch a trait candidate that duplicates a corpus role, which M3 cannot see today (it compares with traits
  and queue entries only): one case so far, expecting against the [pregnant](../../data/roles/instructions/pregnant.json)
  role (states pass v4 pilot, 2026-10-09).  Roger: "If it happens a lot we'll fix it"; the role/trait border is
  fuzzy, and the corpus already has about a dozen role/trait pairs with duplicate names.
  **Folded in 2026-10-14 (Roger), to be done together with the role generators** (§ "Parked: generators aimed at
  roles"): plan 06's decision 1 option (a), a by-name path `gap_registry.py promote --keys K ... --allow-roles`
  writing an `entity_type: "role"` seed-queue entry (`pairing: singleton`, tags `gap_gen`, `source:<generator>`,
  `role_like`, `description_draft` the gloss), refused for the bulk path as `--allow-physical` and
  `--allow-released-states` are, with `promote`'s collision checks (a stem in the corpus of either type, a queued
  stem, a turned-down name) and `seed_queue_stem` on the row; about 40 lines plus a test, a platform change, so a
  Fable review.  Until then role-like rows from every generator (plan 06's person seeding included, listed in its
  `roles_report.md`) wait on the `roles` holding list.
- **Chandler / Anderson likableness ratings** (QUESTIONS 31, left out 2026-10-09): Anderson's 555 trait words with
  likableness, re-rated by Chandler (2018, *Journal of Research in Personality* 72, 50-57) with 486 more words,
  meaningfulness and emotion coding, on OSF project [3wqx5](https://osf.io/3wqx5/).  No licence is stated, so it is
  not used.  If ever wanted, Roger emails the author asking for one (such as CC BY); expected value is small, since
  the words largely duplicate the TDA and Allport-Odbert and the filter already tags evaluative and emotion words.
