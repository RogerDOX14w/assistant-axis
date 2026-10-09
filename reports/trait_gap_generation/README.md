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
| 11 | [Novelty ensemble](./11_novelty_ensemble.md) | independent signals (WordNet/ConceptNet links, masked-LM description-fit, antonym probe, morphology, a second embedding family), agreement rules, LLM only on disagreement (35-45% of candidates), calibration set from the September pairing review | ~$3-6 Haiku (half via batch) |
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

Greenlit for detailed planning: 14, 15, 10; 1, 2
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

## Low-priority TODOs

- **Promotion tooling for role words** (QUESTIONS 1, 2026-10-09).  The filter's `roles` holding list is read by hand
  for now (pointer in [ROLES_TO_ADD.md](../../data/roles/instructions/ROLES_TO_ADD.md)).  Decide whether tooling is
  cost-effective once the list holds enough genuine role ideas that reading them by hand is slower than building it
  (a rough trigger: a few dozen real role ideas, or a generator aimed at roles such as an occupations list).  If it
  is, build it: M3 scoring a candidate role against the role corpus (role descriptions read "A <role> is someone
  who ...", so the relation and overlap rubrics need role versions, pinned and rendered before use), a role pass in
  the review app as the physical pass works, and promotion into the seed queue as `entity_type: "role"`.  As of
  2026-10-09 the list holds 10 words from the pilots, two of them plausible roles.
- **Chandler / Anderson likableness ratings** (QUESTIONS 31, left out 2026-10-09): Anderson's 555 trait words with
  likableness, re-rated by Chandler (2018, *Journal of Research in Personality* 72, 50-57) with 486 more words,
  meaningfulness and emotion coding, on OSF project [3wqx5](https://osf.io/3wqx5/).  No licence is stated, so it is
  not used.  If ever wanted, Roger emails the author asking for one (such as CC BY); expected value is small, since
  the words largely duplicate the TDA and Allport-Odbert and the filter already tags evaluative and emotion words.
