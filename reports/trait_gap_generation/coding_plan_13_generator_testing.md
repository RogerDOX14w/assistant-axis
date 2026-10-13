# Coding plan: workstream 13, generator testing and saturation (package `assistant_axis/gapgen/testing/`)

Written 2026-10-13 (Fable) in the [PLAN_FORMAT.md](./PLAN_FORMAT.md) shape from
[13_generator_testing.md](./13_generator_testing.md) (rewritten 2026-10-12 against the platform as built) with
Roger's § 9 answers of 2026-10-12 as decisions, against the "Interface as built" section of
[coding_plan_platform.md](./coding_plan_platform.md), the recovery harness
([recovery.py](../../assistant_axis/gapgen/recovery.py), [recovery_test.py](../../data_analysis/gap_generation/recovery_test.py)),
the registry ([registry.py](../../assistant_axis/gapgen/registry.py)), the review app's decision logs under
[data/candidates/review/](../../data/candidates/review/), and tonight's gate audits
([gate_audits/README.md](../code_review_2026-10-12/gate_audits/README.md)) and
[regeneration_list.md](../code_review_2026-10-12/regeneration_list.md).  This workstream **generates nothing and
judges nothing new**: it reads what the platform recorded, runs the existing harness on chosen generator runs, and
prints one table.  Terms: the [glossary](./glossary.md); the ones this plan introduces (capture-recapture, occasion,
Chapman, Chao2, Good-Turing coverage, accumulation curve, review-minute, promote share, pre-handled, strict column,
pair-recovery, concept component) are defined on first use below and go into the glossary in task 9.  Every figure
in this plan was measured read-only on 2026-10-13 (§ "Baseline measured for this plan" says how); the first dashboard
run must reproduce them.  Roger's review comments go into this file.

## Open decisions (Roger's, at plan review; labelled OPEN until decided; decision 2 decided 2026-10-13)

1. **OPEN: which generator runs get the recovery harness, and how.**  The workstream plan's § 5 prices the harness
   at "about $5 per generator run at two seeds, under $40 for all current generators".  The four recorded runs
   ([data/candidates/recovery/](../../data/candidates/recovery/)) cost **$0.0133-0.0151 per decided candidate per
   seed** live (the reduced-corpus M3 run about $0.011 a row, the match calls about $0.0024), and the pilots they ran
   on had 78-500 trait rows.  Today's runs are larger: the TDA census has **2,527** trait rows, Allport-hi 1,822,
   the base model (mc2) 1,355, Allport-rare 603, IPIP g600 498, WordNet full and rule-1b 577, the alignment papers
   402, Roget full 287 (per-run counts in § "Baseline").  At two seeds the harness on every current run is about
   **$220 live, $110 batched**; the workstream plan's "first use" (TDA and IPIP, the two mechanisms with the most
   kept terms) is about **$80 live, $41 batched**, over the $20 line either way.
   - (a) **TDA and IPIP, two seeds, batches** (about $41; Roger's explicit go).  Allport-hi and the base model as a
     second wave if the first dashboard says they matter.
   - (b) **One seed** on the same two runs (about $20 batched): under the line, but no between-seed spread, and the
     harness's own default is two seeds.
   - (c) **An "affected-only" reduced run** first: re-score only the candidates with a hidden trait among their ten
     nearest in the full corpus or covered by a hidden one, and copy the rest's recorded decision.  In the four
     recorded runs 61-78% of candidates are affected, so the saving is 22-39%; it is a change to `novelty_score.py
     score --hide`, which this plan otherwise leaves alone.
   - **Recommendation: (a)**, batched, with Roger's go recorded in `run.json` (`--confirm-expensive --confirmed-by`);
     (c) only if the harness is later wanted on every run, which (a)'s readout will say.  The dashboard, the
     repetition and the estimates cost nothing and come first, so Roger decides (a) on the first dashboard, not
     before it (§ 10).
   - **Roger (2026-10-13):** I want to see data from every generator.  Explain option (c) in more detail.  Do we
     also have a less filtered option (d)?
   - *(c) in detail.*  M3 compares a candidate only with its 10 nearest corpus traits (`k` 10 in
     [metric_config.json](../../data/candidates/metric_config.json)), their arrangement partners and the queue.  A
     row with no hidden trait among those, and not covered by a hidden trait's label, sees exactly the same
     comparisons in the reduced corpus, so its decision cannot change except by model noise; (c) copies its
     recorded decision and re-scores only the affected rows.  It is exact, not a sample: the match stage only
     judges hidden traits among a candidate's 10 nearest, so an unaffected row could never recover anything.  It
     saves only 22-39% because with 10% hidden about two-thirds of rows have a hidden trait among their ten.
   - *(d) every generator, pooled* (added 2026-10-13).  One hidden draw per seed for all generators; each distinct
     trait row in the registry is scored once against the reduced corpus, and each generator's recall,
     precision and false covers are read from the rows it proposed (`sources[]`).  A row's reduced-corpus decision
     does not depend on which generator proposed it, so the per-generator figures equal separate runs on the same
     draw; every generator, pilots and small ones included, is measured on the same hidden traits, and the union
     ("any generator") comes free.  Rows: **6,541** distinct trait rows with a generator source, against 9,233
     counted per generator (measured 2026-10-13).  Batched at $0.0133 × 0.5 a row per seed: **two seeds ≈ $87; with
     (c) ≈ $53-68; one seed with (c) ≈ $27-34.**  Small generators recover a handful of the 83-95 hidden traits
     per seed (the Roget pilot 1, the WordNet pilot 6), so their recall carries wide intervals; the free figures
     (string recall on all 932, repetition, review) remain their main record.  Hiding 20% instead of 10% would
     double the hidden sample at nearly the same cost without (c) (the re-score is per row), but (c) then saves
     little (about 89% of rows affected).
   - **Recommendation (2026-10-13), on Roger's "every generator": (d) with (c), two seeds, batched, about
     $53-68**; Roger's go with quoted parameters at launch.  (c) is a change to `novelty_score.py score --hide`
     (score the affected keys, copy the rest's recorded blocks into the reduced-corpus batch), tested by an
     equality check on a fixture: (c) and a full re-score give the same recall when the responder is
     deterministic.
     **Roger: I want the data from every generator we've run, so c), but we can start with a)**
2. **Decided (2026-10-13, Roger): the concept unit for capture-recapture: both, headline chosen on data.**  The workstream plan says "M3's readings cluster candidates into
   concepts"; the better instrument is the all-batches review graph
   ([review_traits_all_2](../../data/candidates/review/review_traits_all_2/graph.json), 3,835 kept candidates, built
   2026-10-13 for $37.28), whose **4-edges** (both directions read 4 on rubric A, what the review merges) and
   **3-edges** (at the proposed cut-off 3) are already paid for.  Measured over the kept candidates: the connected
   components of 4-edges give **3,065 concepts** (2,691 singletons, largest 21); the components of 3-edges give
   1,585, but with a **giant component of 1,028 candidates** (3-edges chain transitively), so components are not
   usable at 3.  The estimates move by about two to one with the choice: Chao2 N̂ 9,244 at 4-edges against 4,528
   at 3-edge components (§ "Baseline").
   - (a) **4-edge components as the headline unit**, and the graph's 3-edge *cliques* (`proposed_groups`, 1,887 of
     them, each candidate assigned to its first group) as the loose column.
   - (b) 3-edge cliques as the headline (closer to what Roger merges at review: 139 of 174 decided terms were
     merged, mostly along 3-edges), 4-edge components as the strict column.
   - **Recommendation: (a)**, because a 4-edge is a two-model, two-direction reading and the strict side is the
     safer lower bound the plan promises; both columns are printed either way.
   - **Roger (2026-10-13):** Explain the options in more detail.  My initial response is that we should try both,
     and decide once we have actual data.  Does doing that cost more?
   - *Cost:* nothing.  Both units are read from the review graph already paid for, and the plan prints both
     columns under either option; the decision only names the headline.  **Decided (2026-10-13): both are
     computed, and Roger picks the headline on the first dashboard.**
   - *The data to decide on* (added 2026-10-13): the dashboard prints each unit's agreement with Roger's own
     review decisions, refreshed as review grows.  Measured now on review_tda_1 against the all-batches graph:
     of **109** candidate pairs Roger merged together, 4-edge components keep **69 (63%)** in one unit and 3-edge
     cliques **59 (54%)**; of **154** pairs he marked distinct or dropped from a proposed group (hard negatives:
     the graph had grouped them), 4-edge components join **24 (16%)** and cliques **23 (15%)**.  So far the strict
     unit is as good on false joins and better on true ones.  Both split about 40% of real merges, which biases
     the estimates of the total upward (missed matches between mechanisms), against the downward bias of uneven
     catchability; the plan's "lower bound" reading holds only if the second dominates, and the report says so.
3. **OPEN: the promote share's denominator.**  The workstream plan's § 3.5 gives "55% for the TDA census" as the
   promote share ("promoted of kept").  The record gives two figures: **per decided term, 20%** (34 `accepted` of
   174 decided censuses rows in the registry; 35 promoted of 204 review writes in
   [applied.jsonl](../../data/candidates/review/review_tda_1/applied.jsonl), 17%) and **per resolved group, 51%**
   (35 `promote` resolutions of 69 `resolve` events in
   [decisions.jsonl](../../data/candidates/review/review_tda_1/decisions.jsonl)).  Neither is 55%.
   - **Recommendation: per term** for the stop rule (review-minutes are spent per term, and a merged group of six
     that promotes one is one novel concept for six terms' minutes), with the per-group figure printed beside it.
   - **Roger (2026-10-13):** Explain the options in more detail.
   - *Measured 2026-10-13, by group shape* (review_tda_1's 69 resolutions): singletons 40 resolved, **20 promoted
     (50%)**; multi-member groups 29 resolved over 99 terms, **15 promoted (52% of groups, 15% of terms)**.  The
     chance that a concept is new is about one half whatever its group size; the per-term share is that half
     diluted by the batch's synonyms, so it depends on group structure.  On the TDA batch both forms give the same
     **0.42 accepted per active minute** (2.43 terms a minute × 17%, or 0.82 groups a minute × 51%); they differ
     only when projected onto a batch shaped differently, such as the alignment sweep's mostly singleton phrases,
     where per term predicts about 20% and per group about 50%.
   - **Recommendation revised (2026-10-13; reverses the one above): per group.**  `expected_accepted` = the
     generator's undecided, not pre-handled kept terms counted as groups (each proposed group one, each singleton
     one) × the per-group share; the minutes keep their per-shape times.  Per term printed beside it.  One batch
     of 69 groups is a small base: the dashboard prints the share by shape so a drift shows.

If a decision is unanswered when Opus reaches the step, it proceeds under the recommendation and records that in
[QUESTIONS.md](./QUESTIONS.md) (§ 12).

## 1. Decisions already made

| decision | reason | source |
|---|---|---|
| **The reference set is the checked-in corpus files only** ([data/traits/instructions/](../../data/traits/instructions/), 932 on 2026-10-13); never the seed queue, and never a file that came from gap generation (none yet: the 38 promoted entries are queue `candidate`s, tagged `gap_gen` and `source:<generator>`, not files).  The queue enters only M3's production search. | Roger, 2026-10-12: "The seed queue is derived from several of our generators, so including it would be contamination." | plan 13 § 9.1 |
| **Regions are M1's**, [corpus_regions.json](../../data/candidates/corpus_regions.json) (932 rows: cognitive_epistemic 203, emotional_temperament 166, social_interpersonal 165, identity_demographic 150, moral_stance 143, communication_style 95, alignment_ai_agent 10), and each candidate's `filter.region`.  No labelling pass. | Roger, 2026-10-12 | plan 13 § 9.2 |
| **The stop rule is per review-minute**: expected accepted terms per minute of Roger's review, corrected by the promote share (decision 3).  Novel per dollar is printed and watched, not optimised. | Roger, 2026-10-12: novel-per-dollar "is also a constraint, but likely a loose one" | plan 13 § 9.3 |
| **Occasions are mechanisms, not generators**: the lexicon walks (censuses, Roget, WordNet) are one occasion; IPIP, the base model, the masked-LM frames (when run) and the corpus are the others; the alignment sweep is a separate population, tested on its own.  No third occasion is bought. | Roger, 2026-10-12 | plan 13 § 9.4, § 3.6 |
| **Match at M3's cut-off rule** (rule set 3: 3 at alignment 0-1; 3 with both models at alignment 2; 4 at alignment 3 or missing) for the headline recall; **a strict column at 4 everywhere** beside it. | Roger, 2026-10-12: "3 is primary, report 4 as well" | plan 13 § 9.5; [novelty.py](../../assistant_axis/gapgen/novelty.py) `cut_off_spec` |
| **The harness as built is the instrument**: hiding by region with arrangements whole (10%, seeds 0 and 1), the reduced-corpus M3 run, label then overlap matching, recall / precision / false covers / reachability.  This plan adds readers of its records and two draw options; it does not re-specify it. | platform close-out, 2026-10-08 | [coding_plan_platform.md](./coding_plan_platform.md) "The recovery harness" |
| **Review-minutes are measured from the review app's decision logs** (`at` on every event of `decisions.jsonl`), terms decided from the batch's `applied.jsonl` (`review_writes`); definition in § 6. | the only timestamps of Roger's review on record | this plan |
| **Repetition is measured on the all-batches review graph**, as the share of a generator's undecided kept terms with a 3-edge (loose) or 4-edge (strict) to a term another batch decided (`accepted`, `rejected`, `merged_into`: the statuses the app pre-handles, `HANDLED_ELSEWHERE` in [decisions.py](../../assistant_axis/gapgen/review_app/decisions.py)).  Attachment to the first reviewed batch is printed as a second figure (the workstream plan's "about 40%" is that figure, see § "Baseline"). | the pre-handled machinery of [coding_plan_review.md](./coding_plan_review.md) § 11 | plan 13 § 3.5 |
| **Library code in `assistant_axis/gapgen/testing/`, the CLI in [generator_dashboard.py](../../data_analysis/gap_generation/generator_dashboard.py) (not there yet)**, outputs under `data/candidates/testing/`; not `tools/generator_dashboard.py` as the workstream plan wrote. | the platform's layout (PLAN_FORMAT § 5) | this plan |
| **Generator-side hiding exists for no seeded generator**: [roget_generate.py](../../data_analysis/gap_generation/roget_generate.py) has no `recover` command (its subcommands are fetch, parse, synopsis, pair, map, place-check, head-scope, coverage, harvest, submit).  Seeded generators report the harness-side figure, marked `harness_side`. | checked 2026-10-13 | plan 13 § 3.3 corrected |
| **Pair-recovery is read from the recorded `opposite` readings**: a hidden trait some kept candidate was read `opposite` against (Sonnet, or Opus where the rule asked it) is pair-recovered; printed beside recall, never summed into it.  The harness hides pairs whole, so "a match to the antonym pole" is already a recovery of the pole. | the harness records verdicts `keep`, `cut`, `review`, `opposite` per pair | plan 13 § 3.4 corrected |
| **The strict column is computed from the recorded readings** (`pair_outcome(reading, 4)`); a pair that needs an Opus reading it lacks (Sonnet 4 with no Opus) is listed and sent to Opus.  In the four recorded runs there are none (the match wave sends every Sonnet reading at c − 1 or above to Opus). | measured 2026-10-13 | this plan |
| **The paraphrase sanity set costs one small Haiku 5.5 call per item** (a synonym label and a reworded 12-16-word gloss, from the M2 calibration's recorded paraphrases, which cover 680 traits): about $0.02, rubric pinned, rendered below.  The 40 antonym items are synonym candidates of one pole of 40 recorded pairs; expected: the pole recovered, the partner read `opposite`. | [paraphrases.json](../../data/candidates/calibration/paraphrases.json) exists; the harness matches by label first, so a candidate carrying the trait's own label never exercises the overlap call | plan 13 § 6 |
| **Haiku 5.5** for that call ($0.10 / $0.50 per MTok in [judge_pricing.py](../../assistant_axis/judge_pricing.py); no `temperature`, [llm.py](../../assistant_axis/gapgen/llm.py) leaves it out). | the platform's model for cheap calls | platform |
| **Live transport for everything under $20** (the paraphrase set); the harness runs by decision 1. | the batch-or-real-time rule | [CLAUDE.md](../../CLAUDE.md) |
| **Counts as of 2026-10-13, used throughout**: 932 trait files; registry 9,949 keys ([registry.jsonl](../../data/candidates/registry.jsonl), 9,972 lines); 3,835 kept trait candidates in the review graph; 174 decided by review (34 accepted, 139 merged, 1 rejected); the seed queue 1,050 entries (972 of them traits; by status over all entries: not_adopted 159, superseded 23, candidate 38). | counted, not copied | this plan |

## 2. Out of scope

- Any generator run, resubmission, M1 or M3 batch on new rows; promotion; the review app and R1 (read only).
- Changes to M3's rules, rubrics, cut-offs or [metric_config.json](../../data/candidates/metric_config.json); the
  "affected-only" reduced run (decision 1 (c)) unless Roger picks it.
- Generator-side hiding for Roget, WordNet's antonym stream, the antonym check or plan 09's operators (interface
  requests, § 12).
- Any edit to `data/traits/**`, `data/roles/**`, [seed_queue.json](../../data/seed_queue.json), the registry's blocks,
  the review logs, or any recorded harness output (new harness runs write new batch ids).
- Bootstrap intervals over generators, Shapley attribution (the workstream plan's "Full" variant).
- Role generators (parked).

## 3. Rule files to Read first

Open with the **Read tool** before touching code:
[provenance.md](../../.claude/rules/provenance.md) (`usage.json` beside every batched LLM output, `MultiModelUsage`;
`json_metadata` envelopes on every JSON this plan writes; UTC timestamps; snapshot before overwrite),
[entity-naming.md](../../.claude/rules/entity-naming.md) (stems via `normalize_to_file_name` for every key; display
form only in prompts and the dashboard's label column; US English),
[trait-pairs.md](../../.claude/rules/trait-pairs.md) (what a trait, a pair, an arrangement and the seed queue are;
the `arrangement` field the harness hides by),
[judging.md](../../.claude/rules/judging.md) (reason before verdict; `warn_if_low_parse_rate`; pins; the
rendered-prompt rule), [CLAUDE.md](../../CLAUDE.md) (file-access boundary, the $20 confirmation rule, **tests are
mandatory**, hotlinks).  No PNGs are planned (the accumulation curve is a table); if one is added, Read the plotting
rule first.

**File-access boundary, restated for every Opus task prompt**: read and write only inside the repository worktree,
the agent's scratchpad and `$TMPDIR`; never list, read or stat anything else under the home directory, not
`~/.cache`, not even to see whether something is downloaded.  This workstream downloads nothing and never opens
`.env`.

## 4. Existing code to reuse

- [registry.py](../../assistant_axis/gapgen/registry.py): `Registry.fold()` (the live log) and `read_snapshot`
  ([registry.snapshot.jsonl.gz](../../data/candidates/registry.snapshot.jsonl.gz), the tracked copy; the dashboard
  reads the snapshot by default so a report is reproducible from git, `--registry` for the live log);
  `records_for_status`, `has_source`.  The row's blocks: `filter` (`verdict`, `region`, `alignment_score`,
  `batch_id`), `novelty` (`decision`, `reason`, `exact_label`, `covered_by`, `readings`, `run_id`, `rules`),
  `review` (`status`, `into`), `sources[]` (`generator`, `run_id`, `rank`, `score`, `source_ref`, `partner_hint`).
- [recovery.py](../../assistant_axis/gapgen/recovery.py): `draw_hidden`, `write_hidden`, `load_hidden`,
  `reduced_traits` (accepts a hand-made hidden list), `pair_outcome(reading, c)` (an integer `c` is a fixed cut-off
  through `as_cut_off`), `seed_figures`, `combine_seeds`, `report_markdown`, `arrangement_kinds`, `load_regions`;
  [recovery_test.py](../../data_analysis/gap_generation/recovery_test.py) (`match_estimate`, `prepare`, the
  per-seed outputs `seed<S>/{hidden.json, matches.jsonl, responses.jsonl, usage.json}` and
  `recovery_report.json`).  `matches.jsonl` rows carry `key`, `label`, `decision`, `covered_by`, `cut_off`, `stem`,
  `how`, `cosine`, `rank`, `sonnet`, `opus`, `verdict`, `recovers`.
- [novelty.py](../../assistant_axis/gapgen/novelty.py): `blind` (separator-blind comparison), `load_trait_corpus`
  (`CorpusTrait.renamed_from`, `pair_partner`, `expands_to`), `cut_off_spec`, `pair_verdict`, `verdict_cuts`,
  `rules_of`, `RULES`; [novelty_runner.py](../../assistant_axis/gapgen/novelty_runner.py) `OVERLAP_TOKENS`,
  `OPUS_SHARE_FULL_SCAN` (the match estimate's shares).
- The review graph's JSON ([review_graph.py](../../assistant_axis/gapgen/review_graph.py), `Graph.from_json`;
  schema 3): nodes (`kind` candidate | corpus | queue; `generator`, `generators`, `decision`, `region`, `m3_run`,
  `review_status`, `review_batch`, `review_into`), edges (`a`, `b`, `cosine`, `relation`, `strict`, `proposed`,
  `readings.ab/ba.{sonnet, opus, verdict, four, proposed}`, `via`), `cliques`, `proposed_groups`, `stats`.
- The review app's records ([decisions.py](../../assistant_axis/gapgen/review_app/decisions.py): the event
  vocabulary `open`, `drop`, `accept`, `resolve`, `distinct`, `extend`, `nominate`, `undo`; `REVIEW_STATUS`,
  `HANDLED_ELSEWHERE`; `apply_decisions` writes `applied.jsonl` with `review_writes`, `promoted`, `promotions`).
- [cost.py](../../assistant_axis/gapgen/cost.py): `Estimate`, `estimate_calls_usd`, `confirm_or_abort`,
  `GuardedUsage`, `HARD_LINE_USD`; [llm.py](../../assistant_axis/gapgen/llm.py) `call_anthropic_json`; the
  record-before-parse loop of [alignment_sweep/extract.py](../../assistant_axis/gapgen/generators/alignment_sweep/extract.py);
  [prompt_labels.py](../../assistant_axis/gapgen/prompt_labels.py); [prompt_hygiene.py](../../assistant_axis/gapgen/prompt_hygiene.py)
  `prompt_words`; [split_rubrics.py](../../assistant_axis/gapgen/split_rubrics.py) `GENERATOR_FILES` /
  `PINNED_NAMES` and [rubric_pins.py](../../data_analysis/gap_generation/rubric_pins.py).
- The measured rates of [masked_lm/submit.py](../../assistant_axis/gapgen/generators/masked_lm/submit.py)
  (`M1_USD_PER_WORD = 0.0072`, `M3_USD_PER_PASSED_WORD = 0.011`, `BATCH_FACTOR = 0.5`, `RATES_SOURCE`) and its
  `select_wave` (the review-hour wave at "~150 terms an hour", which this plan replaces with a measured
  `ReviewRate`, § Frozen interface); [judge_pricing.py](../../assistant_axis/judge_pricing.py) `MultiModelUsage`,
  `price_for_model`, `BATCH_SUFFIX`.
- [provenance.py](../../assistant_axis/provenance.py) `current_file_input`, [plot_metadata.py](../../assistant_axis/plot_metadata.py)
  `json_metadata`; [atomic_io.py](../../assistant_axis/atomic_io.py); [entity_id.py](../../assistant_axis/entity_id.py)
  `normalize_to_file_name`, `resolve_renamed_stem`, `corpus_display_name`; [arrangements.py](../../assistant_axis/arrangements.py).
- Test style: [test_gapgen_recovery.py](../../assistant_axis/tests/test_gapgen_recovery.py) (`toy`, `match_setup`,
  `hidden_doc`, the fake responder), [test_gapgen_review_graph.py](../../assistant_axis/tests/test_gapgen_review_graph.py)
  (a toy graph), [test_gapgen_review_app.py](../../assistant_axis/tests/test_gapgen_review_app.py) (a decision log
  fixture).  numpy for the estimators; **no new dependencies**.

## 5. File layout

```
assistant_axis/gapgen/testing/
  __init__.py        TESTING_DIR = DATA_CANDIDATES / "testing"; DASHBOARD_JSON_PATH; re-exports (§ Frozen)
  independence.py    CLASSES = ("independent", "seeded", "separate_population", "not_a_generator");
                     MECHANISMS = ("lexicon", "ipip", "base_model", "masked_lm", "alignment", "corpus");
                     STREAMS: {(generator, stream): (class, mechanism, inputs, exclusion rule)}  (§ 6);
                     stream_of(source: dict) -> str   (censuses: source_ref prefix tda|allport; wn_clusters:
                     "antonym" when partner_hint else "closure"; states_pass: the source row's generator
                     through source_ref; else the generator); classify(row) -> list[Classified];
                     provenance_excluded(stem, *, traits, queue) -> str | None  (the trait file's `source`
                     naming the generator's source, or its queue entry's `source:<generator>` tag /
                     gap_registry_key, or a renamed_from of such); independence_table(rows, traits, queue)
  review_minutes.py  load_events(batch_dir) -> list[Event]; active_minutes(events, *, idle_s=300) -> float;
                     terms_decided(batch_dir) -> TermsDecided(applied, from_log, promoted);
                     group_times(events) -> GroupTimes(singleton_median_s, singleton_mean_s, per_member_s,
                     n_singletons, n_groups); review_rate(batch_dir) -> ReviewRate (§ 6);
                     promote_share(rows, *, generator) -> PromoteShare(per_term, per_group, n_decided,
                     n_groups, borrowed: bool); pooled_promote_share(rows)
  repetition.py      load_graph(path) -> dict; kept_nodes(graph); decided_keys(graph); adjacency(graph, level=3|4);
                     repetition(graph, *, level) -> {generator: Repetition(n_kept, n_undecided, pre_handled,
                     share, attached_to_batch: {batch: share})}
  concepts.py        components(graph, *, level=4) -> list[set[str]]; clique_assignment(graph) -> {key: group}
                     (first proposed group by order); concept_table(graph, *, unit) -> ConceptTable (§ 6):
                     per concept its mechanisms, region (most common), generators, decided status
  estimators.py      chapman(n1, n2, m) -> Estimate(N, se, lo, hi) (Seber's variance, log-normal interval);
                     chao2(Q: Counter, m_occ) -> Estimate (bias-corrected; Q2 == 0 form);
                     good_turing_coverage(Q1, incidences) -> float; accumulation(order, concept_of) ->
                     list[(n, unique)]; chao_extrapolate(curve, *, Q1, Q2, to_n) -> list[(n, unique_hat)];
                     end_slope(curve, window) -> float; ASSUMPTIONS: tuple[str, ...]
  simulate.py        simulate(N=2000, m_occ=4, sigma_catch=1.0, rho_occ=0.3, seed) -> incidence Counter and the
                     truth; check(estimates, truth) -> bias signs and interval coverage over R replicates
  recovery_extras.py strict_column(seed_dir, *, c=4) -> StrictFigures (recall at fixed 4 from matches.jsonl;
                     `needs_opus`: pairs with Sonnet 4 and no Opus reading); pair_recovery(seed_dir) ->
                     PairFigures (hidden traits read `opposite`; by region); recall_at_n(seed_dir, run_dir)
                     -> list[(rank_quantile, recall)] (ranks from the run's candidates.jsonl);
                     contamination(report_a, report_b) -> delta (with and without provenance exclusion);
                     extras_json(batch_dir) -> dict
  dashboard.py       GeneratorRow (§ 6); cost_by_run(filter_dirs, novelty_dirs, run_dirs, review_dirs) ->
                     {(generator, run_id): CostLines} (a batch is attributed to the run its run.json argv
                     names with --run G/R; a --keys or re-decide batch pro rata by its rows' generators;
                     an R1 build pro rata by kept rows); build_rows(...) -> list[GeneratorRow];
                     stop_rule(row, rate: ReviewRate, share: PromoteShare) -> StopRule; render_markdown(rows)
  paraphrase_set.py  build_set(traits, paraphrases, regions, *, n_single=40, n_pairs=40, seed=0) -> list[Item];
                     SYNONYM_SYSTEM (from rubrics/paraphrase_synonym.md, pinned); render_user(item) -> str;
                     parse(text) -> Answer | None; run(items, *, client, usage, out_dir, resume) -> list[Answer]
                     (record before parse; an answer whose label is the hidden stem or a renamed_from is
                     `label_path` and re-asked once with the "not the word X" line); to_scratch_registry(items,
                     answers, regions, path) -> n_rows (synthetic filter blocks, verdict trait); hidden_file(items)
                     -> dict; report(batch_dir) -> markdown (concept recall, antonym pair-recovery, label-path
                     count, parse rate)
data_analysis/gap_generation/generator_dashboard.py
                     independence | review-rate | repetition | concepts | estimate | recovery-extras | dashboard |
                     paraphrase-set (build | run | report) | simulate
reports/trait_gap_generation/rubrics/paraphrase_synonym.md     pinned text (versions.json row 1)
data/candidates/testing/{independence.json, review_rates.json, repetition.json, concepts.json, estimates.json,
                     simulation.json, dashboard.json, dashboard.md}       tracked, enveloped, rebuilt by `dashboard`
data/candidates/testing/paraphrase_set/{set.jsonl, responses.jsonl, registry.jsonl, hidden.json, usage.json,
                     run.json, report.md}                                  tracked except registry.jsonl
data/candidates/recovery/<B>/extras.json                                    written by recovery-extras
assistant_axis/tests/test_gapgen_testing_{independence,review_minutes,repetition,concepts,estimators,simulate,
                     recovery_extras,dashboard,paraphrase_set,acceptance}.py
data_analysis/tests/test_gap_generation_generator_dashboard_cli.py
```

Two additions to the harness itself, and nothing else in it changes:
[recovery_test.py](../../data_analysis/gap_generation/recovery_test.py) gains `--hidden-file PATH` (a fixed hidden
list, read by `load_hidden`, in place of the draw; `hidden_frac` recorded as `null`) and `--exclude-stems PATH` /
`--exclude-provenance GENERATOR` (stems whose hiding group is never drawn, from a file or from
`provenance_excluded`; recorded in `hidden.json` as `excluded`), and `draw_hidden` gains `exclude: Collection[str]
= ()`.  A draw with no exclusion is byte-identical to today's (test).

## 6. Data schemas

**Independence row** ([independence.json](../../data/candidates/testing/independence.json), not there yet; one per
(generator, stream)):

```json
{"generator": "wn_clusters", "stream": "antonym", "class": "seeded", "mechanism": "lexicon",
 "inputs": "WordNet antonyms of corpus labels with no partner file (partner_hint set)",
 "generator_side_hiding": false, "harness_side_only": true,
 "exclusion_rule": "a corpus trait whose queue entry carries source:wn_clusters, or whose file's source names OEWN",
 "n_rows": 102, "n_kept": 41, "n_excluded_from_denominator": 0}
```

The table as planned (Opus verifies each against the code and corrects the row, not the plan): censuses/tda and
censuses/allport (independent; exclusion: files whose `source` names the list, today
[extrinsic_allport](../../data/traits/instructions/extrinsic_allport.json) and
[intrinsic_allport](../../data/traits/instructions/intrinsic_allport.json) name Allport but are the religious
orientation scale, not the word list, so Opus reads them and decides); roget (seeded head map: `select_heads` in
[harvest.py](../../assistant_axis/gapgen/generators/roget/harvest.py) walks the gap heads of the coverage report,
which is built from corpus labels; the harvest within a head is independent); wn_clusters/closure (independent) and
wn_clusters/antonym (seeded); ipip (independent); base_model (independent: [prompts.py](../../assistant_axis/gapgen/generators/base_model/prompts.py)
names no corpus trait); masked_lm (independent; no run yet); alignment_sweep (separate population; its occasions
are the papers run and variant B's run, 408 and 67 candidates, overlap recomputed from each run's
dedup groups, [papers](../../data/candidates/runs/alignment_sweep/2026-10-11-papers/dedup_groups.json) and
[b](../../data/candidates/runs/alignment_sweep/2026-10-11-b/dedup_groups.json)); antonym_check (seeded); structural (seeded; not built); states_pass and the physical pass
(not generators: a row's `source_ref` is the source row's key, so it is attributed to that row's generator);
m1_validation and manual (not generators: pools).

**Review rate** ([review_rates.json](../../data/candidates/testing/review_rates.json), not there yet; one per review
batch with a `decisions.jsonl`; the figures are the 2026-10-13 measurement of
[review_tda_1](../../data/candidates/review/review_tda_1/decisions.jsonl)):

```json
{"batch_id": "review_tda_1", "events": 354, "first_at": "2026-10-11T19:40:34+00:00", "last_at": "2026-10-11T21:21:26+00:00",
 "wall_minutes": 100.9, "active_minutes": 84.1, "idle_s": 300, "idle_gaps": 1,
 "terms": {"applied": 204, "from_log": 176, "promoted": 35},
 "groups": {"opened": 88, "singletons": 44, "multi": 44, "members": 218, "resolved": 69,
            "resolutions": {"merge_into": 33, "promote": 35, "reject": 1}, "distinct_events": 76, "extend_events": 68},
 "times": {"singleton_median_s": 12, "singleton_mean_s": 15, "multi_median_s": 71, "per_member_s": 25},
 "rate": {"terms_per_active_minute": 2.43, "terms_per_hour_active": 146, "terms_per_hour_wall": 121,
          "accepted_per_active_minute": 0.42},
 "superseded_logs": ["decisions.before_leftovers_2026-10-11.jsonl"]}
```

Definitions.  A **review-minute** is one minute of active review: the sum of the gaps between consecutive events of
the batch's log that are at most `idle_s` (five minutes; a longer gap is a break and counts nothing; at 300 and
600 s the TDA batch gives the same 84.1 minutes).  **Terms decided** is the batch's `review_writes` in
`applied.jsonl` (the registry rows the apply changed); `from_log` (distinct keys in `resolve` members and
`distinct` keys) is the cross-check.  The **rate** is terms decided per active minute.  Per-term times by shape
come from open-to-next-open spans: singleton groups and multi-member groups (per member).  **Promote share** is
accepted terms over decided terms for a generator (per term), with promote resolutions over resolved groups beside
it (decision 3); a generator with fewer than 50 decided terms takes the pooled share, flagged `borrowed`.  A
superseded log (the TDA batch's first 16 minutes, reset before the leftovers pass) is listed, never counted.
`review_states_v4` (13 events, 4 terms) is reported and excluded from the pooled rate as too small.

**Repetition** ([repetition.json](../../data/candidates/testing/repetition.json), not there yet; per generator and
level, over the all-batches graph's kept candidates; figures measured 2026-10-13):

```json
{"graph": "review_traits_all_2", "generator": "censuses", "level": 3, "n_kept": 2872, "n_decided": 174,
 "n_undecided": 2698, "pre_handled": 185, "share": 0.069,
 "attached_to_batch": {"2026-10-10-tda_censuses_r3": {"n": 2076, "attached": 720, "share": 0.347}},
 "with_another_generator": 1392}
```

**Pre-handled** means the term has a 3-edge (level 3) or 4-edge (level 4) to a term another batch decided, so the
app counts it as handled from the start and it costs no review-minute.

**Concept table** ([concepts.json](../../data/candidates/testing/concepts.json), not there yet; `unit` is
`components_4`, `cliques_3` or `components_3`): `{"unit", "n_concepts", "n_singletons", "largest", "by_mechanism":
{"lexicon": 2402, ...}, "pairs": [{"a": "lexicon", "b": "ipip", "n1": 2402, "n2": 232, "m": 54}], "incidence":
{"1": 2513, "2": 375, "3+": 41}, "by_region": {...}, "concepts": [{"id": 0, "keys": [...], "mechanisms": [...],
"region": "moral_stance", "decided": "merged_into" | null}]}`.

**Estimates** ([estimates.json](../../data/candidates/testing/estimates.json), not there yet): per unit and
region, `chapman` per mechanism pair (`N`, `se`, `lo`, `hi`), `chao2` (`N`, `se`, `lo`, `hi`, `Q1`, `Q2`),
`coverage`, the `accumulation` curve per mechanism (`[[n_candidates, unique_concepts], ...]` in the run's emitted
order, with the Chao extrapolation to twice the observed n and the `end_slope`), and `assumptions` (closed
population; equal catchability, false, so N̂ is low; independent occasions, false between LLM-based mechanisms,
so N̂ is low; `N̂ is a lower bound on what generators of these kinds can reach`).  **Capture-recapture**: two
samples of one population share m items; the fewer they share, the larger the population.  **Chapman**'s
estimate from two occasions is (n1 + 1)(n2 + 1) / (m + 1) − 1; **Chao2** uses, over k occasions, the concepts
seen on exactly one (Q1) and exactly two (Q2); **Good-Turing coverage** is 1 − Q1 / (all incidences), the share
of the population the occasions have seen; the **accumulation curve** is unique concepts against candidates
drawn, whose end slope is the marginal yield.

**Dashboard row** ([dashboard.json](../../data/candidates/testing/dashboard.json), not there yet; one per
generator, with per-stream rows where the class differs; `dashboard.md` renders it; the counts below are
today's IPIP figures, the cost and stop-rule values illustrative):

```json
{"generator": "ipip", "class": "independent", "mechanism": "ipip", "runs": ["2026-10-11-g600", "2026-10-13-g600"],
 "cost_usd": {"generator": 0.37, "m1": 1.62, "m3": 2.20, "r1_share": 2.07, "harness": null, "total": 6.26},
 "candidates": 514, "m1": {"trait": 498, "tagged": 13, "reject": 3}, "m3": {"kept": 240, "covered": 258, "exact_label": 51},
 "regions_of_kept": {"social_interpersonal": 79, "emotional_temperament": 62, "...": 0},
 "repetition": {"pre_handled_3": 0.04, "pre_handled_4": 0.01, "attached_to_tda": 0.23},
 "review": {"decided": 3, "accepted": 0, "merged": 3, "rejected": 0, "promote_share_term": 0.20, "promote_share_group": 0.51, "borrowed": true},
 "string_recall": {"n": 55, "of": 932, "share": 0.059},
 "negatives": {"hit": 2, "of": 250},
 "recall": {"headline": null, "strict": null, "pair": null, "by_region": null, "recall_at_n": null, "harness_batch": null, "harness_side": false},
 "stop_rule": {"undecided_kept": 237, "pre_handled": 9, "expected_minutes": 70.6, "expected_accepted": 45.6,
               "novel_per_review_minute": 0.65, "novel_per_usd": 7.3}}
```

The stop rule: `expected_minutes` = (singleton terms × singleton_mean_s + grouped terms × per_member_s) / 60 over
the generator's undecided, not pre-handled kept terms (singleton or grouped by the graph's proposed groups);
`expected_accepted` = those terms × promote_share_term; `novel_per_review_minute` = expected_accepted /
expected_minutes; `novel_per_usd` = expected_accepted / total cost.  Every figure that lags review (promoted, the
share) says so in the Markdown with its date.

**Paraphrase-set item** ([set.jsonl](../../data/candidates/testing/paraphrase_set/set.jsonl), not there yet):
`{"id": "s07", "kind": "single" | "pair_pole", "hidden_stem": "absentee", "partner_stem": null, "region":
"alignment_ai_agent", "alignment_score": 2, "paraphrase_source": "calibration/paraphrases.json", "paraphrase": "This
means ..."}`; the answer record adds `label`, `gloss`, `reasoning`, `label_path` (true when the label named the
hidden stem; then `reasked`), `model`, `prompt_sha256`.  The scratch registry row is a registry row with a
synthetic `filter` block (`verdict: trait`, `gloss`, `region`, `alignment_score`, `batch_id:
"testing/paraphrase_set"`, `synthetic: true`) and one source (`generator: testing`, `run_id: paraphrase_set`).

## 7. CLI

[generator_dashboard.py](../../data_analysis/gap_generation/generator_dashboard.py) (not there yet).  Common flags
`--registry` (default the tracked snapshot; `--live` for the log), `--data-dir`, `--regions`, `--graph` (default the
newest `review_*/graph.json` whose `from_batches` cover the trait track; recorded in every output), `--out`
(default `data/candidates/testing/`), `--dry-run` (prints what would be written).  Every output is an enveloped
JSON with its inputs (`json_metadata`), rewritten whole, `.bak.<UTC>` on change.

- `independence`: the table of § 6 from the code's stream rules, with row counts from the registry; `--check`
  exits 1 if a registry generator has no row in `STREAMS`.  $0.
- `review-rate [--batch B ...] [--idle-s 300]`: the review-rate record per batch with a `decisions.jsonl`, plus
  the pooled rate and the per-generator promote shares.  $0.
- `repetition [--level 3 4]`, `concepts [--unit components_4 cliques_3]`, `estimate [--unit ...] [--by-region]`:
  the records of § 6; `estimate` prints the assumptions block every time.  $0.
- `simulate [--n 2000 --occasions 4 --sigma 1.0 --rho 0.3 --replicates 200 --seed 0]`: the estimator sanity run,
  writes `simulation.json`.  $0, seconds.
- `recovery-extras --batch B [--c 4]`: `extras.json` beside a recorded harness batch (strict column, pair-recovery,
  recall-at-N, the `needs_opus` list); `--send-opus --budget-usd 1` sends the missing Opus readings through the
  runner (none expected).  $0 unless sent.
- `dashboard [--harness B ...]`: everything above folded into `dashboard.json` and `dashboard.md`; cost lines from
  every run's, batch's and build's `usage.json`.  $0.  Re-run after every M3 batch, every `apply` and every
  harness run.
- `paraphrase-set build [--n-single 40 --n-pairs 40 --seed 0]` ($0: the items and the hidden file; refuses a trait
  without a recorded paraphrase and draws another), `run --budget-usd 0.5 [--resume]` (Haiku 5.5, 80 calls plus
  re-asks, about $0.02; prints the estimate, records every answer before parsing, `warn_if_low_parse_rate`, writes
  the scratch registry; then prints the harness command: `recovery_test.py --generator testing --run-id
  paraphrase_set --registry data/candidates/testing/paraphrase_set/registry.jsonl --hidden-file
  .../hidden.json --budget-usd 4`), `report --batch rec_testing_paraphrase_set` (concept recall over the 80, the
  antonym items' pair-recovery, label-path count, the misses with their readings).

## 8. Acceptance tests, written first

No test calls an API: the paraphrase call uses a `FakeAnthropic` scripted by prompt hash, the harness pieces run
on the toy corpus of [test_gapgen_recovery.py](../../assistant_axis/tests/test_gapgen_recovery.py), the graph and logs are small fixtures.  The measured figures below
are **hard** on the recorded data (they were measured on 2026-10-13 and the records are tracked); the recall and
estimate figures are **report-and-decide**.

- `independence`: every generator in the registry snapshot has a stream rule; `stream_of` on fixture sources (tda /
  allport prefixes, a `partner_hint` WordNet row, a states_pass row whose `source_ref` is a key); `provenance_excluded`
  finds a planted `source:` tag, a planted file `source` and a `renamed_from`; the class vocabulary is closed.
- `review_minutes`: on a fixture log with one idle gap, `active_minutes` excludes it and the wall span includes it;
  `terms_decided` reads `applied.jsonl` and the log; group times from open-to-open spans; the superseded log is
  listed, not counted; **on the recorded `review_tda_1`: 354 events, 84.1 active minutes, 204 applied terms, 35
  promoted, singleton median 12 s, 25 s per member, 2.43 terms per active minute** (hard); `promote_share` per term
  and per group on a fixture registry, `borrowed` under 50.
- `repetition`: on a toy graph with decided and undecided nodes, 3- and 4-edges, pre-handled counts by level;
  attachment to a batch; **on the recorded all-batches graph: censuses 185 of 2,698 at level 3, 57 at level 4;
  720 of 2,076 non-TDA censuses terms attached to the TDA batch** (hard).
- `concepts` and `estimators`: components on a toy graph; clique assignment deterministic; `chapman(10, 10, 5)` =
  19.2 and its interval; `chao2` with Q2 = 0 uses the corrected form; coverage in [0, 1]; the accumulation curve
  is non-decreasing and the extrapolation continues it; **on the recorded graph: 3,065 four-edge components, 2,691
  singletons, largest 21; a 3-edge component of 1,028** (hard); `ASSUMPTIONS` printed by `estimate`.
- `simulate`: with heterogeneous catchability both estimators are low on average over 200 replicates (bias sign
  negative); with equal catchability and independent occasions Chao2's interval covers N in at least 90% of
  replicates; leave-one-occasion-out N̂ moves more under correlated occasions than independent ones.
- `recovery_extras`: `strict_column` on planted matches (a Sonnet 4 with Opus 4 recovers at 4; a Sonnet 4 with no
  Opus is listed in `needs_opus`, not counted; a Sonnet 3 does not recover at 4); `pair_recovery` counts an
  `opposite` verdict once per hidden trait; `recall_at_n` from planted ranks; **on the four recorded batches
  `needs_opus` is empty** (hard); `--hidden-file` draws nothing and records `hidden_frac: null`; `--exclude-stems`
  never draws an excluded group and a draw without exclusion is byte-identical to today's `draw_hidden`.
- `dashboard`: rows for every generator in a fixture registry; cost attribution (a `--run` batch to its run, a
  `--keys` batch pro rata, the R1 build pro rata by kept rows; the lines sum to every `usage.json` read); the
  stop-rule arithmetic on a fixture; a lagging figure carries its date; the Markdown renders every column; a
  generator with no harness batch prints `n/a`, never 0.
- `paraphrase_set`: the rubric is pinned (`rubric_pins.py check` green; `GENERATOR_FILES` names it); reasoning is
  the first key; the user turn carries the paraphrase and never the hidden label; parse of a scripted reply;
  `label_path` set when the label is the hidden stem or a `renamed_from` (separator-blind) and the re-ask carries
  the "not the word" line; every response recorded before parsing and charged, unparseable ones too; `--resume`
  sends nothing answered; the scratch registry rows select as M3 candidates (`verdict: trait`, gloss, not held);
  `hidden.json` hides each pair whole; a dry run writes nothing.
- CLI: every subcommand's `--dry-run` exits 0 and writes nothing; `run` refuses over budget; outputs carry the
  envelope and the graph's path.
- **Acceptance on recorded outputs** (`test_gapgen_testing_acceptance.py`, skips while absent): `dashboard.json`
  has a row per registry generator; `review_rates.json` reproduces the hard figures above; the paraphrase set's
  `report.md` records concept recall (target > 90%, report-and-decide: a miss is an M3 bug to file, not a
  finding) and the antonym items' pair-recovery; every paid directory has `usage.json`; every harness batch run
  under decision 1 has `extras.json`; `git status --porcelain data/traits data/roles data/seed_queue.json` is empty.
- **Manual check, listed as such**: Roger reads 20 random "recovered" and 20 "novel" verdicts from the decision-1
  harness batches (`roger_sample.md`, seeded); recorded in the acceptance report.

Commands that must pass at the end of every task:

```
uv run pytest assistant_axis/tests/test_gapgen_testing_*.py data_analysis/tests/test_gap_generation_generator_dashboard_cli.py assistant_axis/tests/test_gapgen_recovery.py -q
uv run pytest -q                                                  # whole suite, unchanged
uv run python data_analysis/gap_generation/rubric_pins.py check
uv run python data_analysis/check_arrangements.py --quiet
uv run python tools/sync_entity_lists.py --check
git status --porcelain data/traits data/roles data/seed_queue.json   # must be empty
```

## 9. Ordered task checklist

Prerequisite: a worktree off `anthropic-vllm-uv` (`git merge --ff-only anthropic-vllm-uv` first), `.env` copied,
`data/external/` and the embedding cache linked from the main checkout, the registry snapshot current (`gap_registry.py
compact` was run 2026-10-13).  The boundary paragraph of § 3 goes into every task prompt verbatim.  Each task ends
with the § 8 commands.

1. Skeleton, `independence.py`, CLI `independence`.  Test: independence.  Paste the table into the task report with
   any row corrected against the code.
2. `review_minutes.py`, CLI `review-rate`.  Test: review_minutes (the hard figures).  Paste the two batches' records.
3. `repetition.py`, `concepts.py`, CLI `repetition`, `concepts`.  Test: repetition, concepts (the hard figures).
4. `estimators.py`, `simulate.py`, CLI `estimate`, `simulate`; run `simulate` (seconds).  Test: estimators,
   simulate.  Paste the bias table.
5. `dashboard.py`, CLI `dashboard`; **the first dashboard from recorded data** ($0): `dashboard.md` to Roger.
   Test: dashboard.  **Gate 1 (§ 10)**: Roger answers decision 1 on it.
6. The harness additions (`--hidden-file`, `--exclude-stems` / `--exclude-provenance`, `draw_hidden(exclude=)`) and
   `recovery_extras.py`, CLI `recovery-extras`; run it on the four recorded batches ($0).  Test: recovery_extras
   (the byte-identical draw, the empty `needs_opus`).
7. `paraphrase_set.py`, the rubric pinned (`rubric_pins.py bump paraphrase_synonym --why ... --version 1`), CLI
   `paraphrase-set`; `build`, then `run` (about $0.02), then the harness on the scratch registry (about $1.5, cap
   $4), then `report`.  Test: paraphrase_set.  **Gate 2**: concept recall over 90% and the antonym items in
   pair-recovery; a miss stops the task and goes to Fable as an M3 bug with the readings.
8. **The harness runs of decision 1** (TDA and IPIP, two seeds, batches, about $41; Roger's go recorded with
   `--confirm-expensive --confirmed-by`), then `recovery-extras` on each, then `dashboard --harness ...`; the
   contamination check (a second draw with `--exclude-provenance censuses`, only if task 1 found any excluded stem;
   otherwise reported as "no exclusion applies").  Prepare `roger_sample.md` (20 + 20).
9. Glossary entries ([glossary.md](./glossary.md): the terms listed in the introduction); the
   [data/README.md](../../data/README.md) paragraph for `candidates/testing/` proposed in the report (not edited;
   the platform owns that file).
10. Acceptance report (§ 11).

## 10. Pilot

The pilot is **the first dashboard from recorded data** (task 5, $0), which already carries every column but the
harness ones: per generator the cost, counts, regions, repetition, review figures, string recall, negatives, and
the stop rule from the measured review rate and promote shares; plus the concept table and the estimates at both
units.  **Roger decides** on it: (a) decision 1, the harness scope (the dashboard's stop-rule column says which
generators' remaining terms are worth the review-minutes, and so which are worth measuring recall for);
(b) decision 2, by reading twenty of the 4-edge components and twenty of the 3-edge cliques (printed with their
members, seeded); (c) decision 3; (d) whether the giant 3-edge component is a review-graph finding worth filing.
The second pilot is the paraphrase set (task 7, about $1.5): a matcher sanity check, with a gate.  Yield per
dollar is not the figure here (nothing is generated); the readout's figures are the stop-rule ones and the
estimates with their intervals.

## 11. Report at the end

One page at [acceptance_13_generator_testing.md](./acceptance_13_generator_testing.md) (not there yet): what was
built against § 5; deviations with reasons; the § 8 commands verbatim with pass counts; the independence table as
verified; the review-rate records and the pooled rate; the repetition table; the concept counts at both units and
the estimates with intervals and the assumptions block; the simulation's bias table; the paraphrase set's recall
and pair-recovery with any M3 bug filed; the decision-1 harness batches' recall (headline and strict), pair-recovery,
recall-at-N, false covers, reachability and cost, and the contamination delta; Roger's 20 + 20 verdicts; the
dashboard with its stop-rule column; cost per model from every `usage.json` (paraphrase set, harness batches);
open QUESTIONS entries; the proposed `data/README.md` paragraph; and the one-line answer the workstream plan asks
for: **how many distinct concepts are left, per mechanism, and what does each cost in review hours.**

## 12. Escalation

Opus retries a failing step once with a changed approach, then Fable (diff review, architecture, stubborn
failures), then Roger through [QUESTIONS.md](./QUESTIONS.md) in its format (`N. [13] question. Assumption proceeded
under: ... Status: open`, numbering continuing from the file's last entry, 90 on 2026-10-13), proceeding under the
assumption unless the answer would make the work useless.  Pre-registered entries Opus copies in at the start:
(1) the harness scope is decision 1's recommendation (a) unless Roger says otherwise at gate 1; (2) the concept
unit is 4-edge components, 3-edge cliques loose (decision 2); (3) the promote share is per term (decision 3);
(4) the workstream plan's "about 40%" repetition is attachment to the first reviewed batch (measured 35% for the
censuses), and the pre-handled share is 7%; (5) no seeded generator has generator-side hiding; the harness-side
figure is reported, marked; (6) states-pass and physical-pass rows are attributed to the source row's generator;
(7) the alignment sweep's two-occasion overlap is recomputed from the two runs' `dedup_groups.json`, since the
workstream plan's 218 / 247 / 13.6% were not found on record (the run summaries give 746, 94 and 428 poles for
the papers, variant B and the unsubmitted specs run); (8) the CLI lives in `data_analysis/gap_generation/`, not
`tools/`; (9) a paraphrase answer that names the hidden label is re-asked once and counted; (10) the review rate
and promote share replace the hard-coded "150 terms an hour" of plans 04 and 09 only through the frozen interface
below, not by editing those generators (interface request).  Anything that would edit a trait file, the queue, a
registry block, a review log or a recorded harness output, spend over a command's budget, change M3's rules, or
change a frozen signature stops and asks.

## Baseline measured for this plan (read-only, 2026-10-13)

Measured with throwaway scripts in the session scratchpad over the registry fold
([registry.jsonl](../../data/candidates/registry.jsonl), 9,949 keys), the trait files, the seed queue, the two
decision logs, the four recorded harness batches and the all-batches graph; the dashboard's first run reproduces
them (§ 8).

**Per generator** (rows; M1 trait; M3 kept / covered, of which exact-label covers; review decided):
censuses 8,007; 5,139; 2,872 / 2,243 (468); 174.  base_model 1,541; 1,355; 517 / 836 (354); 59.  wn_clusters 647;
578; 277 / 300 (2); 27.  roget 576; 349; 243 / 101 (2); 18.  ipip 514; 498; 240 / 258 (51); 3.  alignment_sweep
464; 455; 362 / 93 (21); 2.  antonym_check 405; 374; 135 / 239 (4); 0.  states_pass 459; 372; 165 / 207 (83); 7.
m1_validation 150; 108; 58 / 43; 0.  Kept rows by review status over all: unreviewed 3,666, merged_into 139,
accepted 34, rejected 1.  Regions of kept rows run social_interpersonal first for every lexical generator (876 of
the censuses' 2,872) and alignment_ai_agent first for the alignment sweep (132 of 362).

**Per run** (trait rows; kept): censuses 2026-10-10-tda 2,527; 1,126.  2026-10-11-allport_hi 1,822; 1,216.
2026-10-12-allport_rare 603; 409.  2026-10-12-allport_iv_rare 101; 59.  2026-10-08-pilot 500; 236.  roget
2026-10-11-full 287; 201.  wn_clusters 2026-10-11-full 414; 204, 2026-10-12-rule1b 163; 73.  ipip 2026-10-13-g600
498; 240.  base_model 2026-10-12-pilot-mc2 1,355; 517.  alignment_sweep 2026-10-11-papers 402; 316, 2026-10-11-b
64; 54.  antonym_check pilot_1 374; 135.

**Recovery by string** (corpus stems a generator's rows name, separator-blind, stem or `renamed_from`, of 932):
censuses 475 (51.0%), base_model 352 (37.8%), states_pass 90, ipip 55 (5.9%), alignment_sweep 20, antonym_check
17, wn_clusters 7, roget 3; any generator 517 (55.5%).  String-level Chapman on the corpus-reachable population
from censuses × base_model (m = 327): 511; censuses × ipip (m = 45): 578.  **Negative set**: 250 distinct
names from the 159 `not_adopted` and 23 `superseded` trait entries; hit by censuses 54, base_model 37,
states_pass 9, manual 5, alignment_sweep 2, ipip 2.

**The recorded harness** ([data/candidates/recovery/](../../data/candidates/recovery/), seed 0 only, 83 of 790
hidden): antonym_check/pilot_1 367 decided, recall 13 of 83 (15.7%), $4.87; censuses/2026-10-08-pilot 500
decided, recall 19 (22.9%), $6.63; roget pilot 90 decided, recall 1 (1.2%), $1.36; wn pilot 78 decided, recall 6
(7.2%), $1.13.  Per decided candidate: $0.0133, $0.0133, $0.0151, $0.0145.  Candidates with a hidden trait among
their ten nearest or by label: 61%, 67%, 78%, 69%.  Pairs with a Sonnet 4 and no Opus reading: 0 in all four.
All four predate rule set 3 (their blocks record `cut_off` 3 or 4 by the step rule); the decision-1 runs are the
first under the graded rule.

**Review rate** (review_tda_1): in § 6.  Promote share: 20% per term, 51% per group.  `review_states_v4`: 13 events,
28.8 wall minutes, 4 terms, 3 promoted (too small to pool).

**Repetition** (all-batches graph, kept candidates; undecided with a 3-edge to a decided term; with a 4-edge;
undecided non-TDA terms with a 3-edge into the TDA batch): censuses 7%, 2%, 35%; base_model 10%, 4%, 49%;
alignment_sweep 9%, 1%, 18%; wn_clusters 11%, 4%, 46%; roget 8%, 2%, 37%; ipip 4%, 1%, 23%; states_pass 5%,
3%, 27%; antonym_check 7%, 1%, 36%.  The 7% is what review pre-handles today; the 35-49% is how much of a later
batch sits on the first one's concepts and becomes pre-handled as the TDA batch is decided (173 of its 795 kept
terms were).

**Concepts and estimates** (kept candidates; four occasions: lexicon, ipip, base_model, alignment):
4-edge components 3,065 (lexicon 2,402, base_model 437, alignment 319, ipip 232); Chapman lexicon × ipip (m 54)
10,179, lexicon × base_model (m 379) 2,769, ipip × base_model (m 32) 3,092; Chao2 9,244 (Q1 2,513, Q2 375),
coverage 0.26.  3-edge components 1,585 with a giant component of 1,028 (lexicon 1,229, base_model 208, ipip 173,
alignment 152); Chapman lexicon × ipip (m 55) 3,821, lexicon × base_model (m 184) 1,389; Chao2 4,528, coverage
0.28; by region (observed concepts) social 352, cognitive 258, emotional 253, communication 205, identity 189,
moral 179, alignment 56.  Read as the plan says: lower bounds, and inflated by the lexical mechanism's share
(4,734 of 5,630 incidences); the base model's Chapman with the lexicon (2,769) is the credible one, the alignment
sweep's pairs are a separate population and are printed apart.

**R1's cost** ([review_traits_all_2](../../data/candidates/review/review_traits_all_2/run.json)): $37.28 for
3,835 candidates, $0.0097 a kept row, attributed pro rata in the dashboard.

## Rendered prompt: the paraphrase synonym call (Haiku 5.5, one item per call)

The only new prompt in this workstream.  The system turn is the pinned text of
[rubrics/paraphrase_synonym.md](./rubrics/paraphrase_synonym.md) (not there yet; version 1); the user turn carries
the item's recorded paraphrase (here [absentee](../../data/traits/instructions/absentee.json)'s, from
[paraphrases.json](../../data/candidates/calibration/paraphrases.json)) and never the hidden label.  No example
words: any example added later must pass `prompt_hygiene.prompt_words` against the corpus, the queue and the
validation file.

```
[system]
You are helping test a search tool over a corpus of personality traits.  You will be given one short
definition of a trait in the corpus's style ("This means ...").  The trait's own name is withheld.  Do two
things.  (1) Give the one- or two-word label a careful lexicographer would put on this trait: US English,
lower case, an adjective or a short adjectival phrase, at most two words, no hyphenated inventions.  (2) Write
a fresh definition of the same trait, 12 to 16 words, in the same "This means ..." form, in your own words:
reuse none of the content words of the definition you were given (function words are fine).  Reason first,
then answer.  Respond with a JSON object only, no other text:
{"reasoning": "<one or two sentences>", "label": "<label>", "gloss": "This means ..."}

[user]
Definition: This means delegating tasks and then withdrawing entirely, offering no guidance when sought, never
monitoring progress, and discovering problems through others.
```

A plausible answer (illustrative, not a recorded one): `{"reasoning": "The trait is a manager who hands work
over and then disappears; the lexicographer's word is hands-off.", "label": "hands-off", "gloss": "This means
assigning work, vanishing afterward, giving no steer, checking nothing, and learning of failures from others."}`.
The re-ask variant appends one line to the user turn: `The label must not be the word "absentee" or a spelling
of it.`  Estimate: 80 calls × (260 in, 90 out) tokens at Haiku 5.5 rates ≈ $0.006, re-asks and retries under
$0.02; cap $0.50.

## Cost (estimates; the harness figures from the four recorded runs)

| step | calls | estimate |
|---|---|---|
| independence, review-rate, repetition, concepts, estimate, simulate, dashboard, recovery-extras on recorded batches | none | **$0** |
| paraphrase set: Haiku synonym call (80 + re-asks) | ~85 | ≈ $0.02 |
| paraphrase set: the harness on the scratch registry (80 candidates: reduced-corpus M3 ≈ 80 × $0.011; match ≈ 100 pairs) | ~300 | ≈ $1.5 (cap $4) |
| harness, decision 1 (a): TDA 2,527 trait rows × 2 seeds × $0.0133 × 0.5 (batches) | | ≈ $34 |
| harness, decision 1 (a): IPIP g600 498 × 2 × $0.0133 × 0.5 | | ≈ $6.6 |
| **total under the recommendation** | | **≈ $42**, over the $20 line: Roger's go, batched |
| if later wanted: Allport-hi ≈ $24, base model mc2 ≈ $18, Allport-rare ≈ $8, WordNet full + rule 1b ≈ $7.7, alignment papers ≈ $5.3, Roget full ≈ $3.8 (each two seeds, batched); every current run ≈ $110 | | |

Roger's time: 15 minutes per dashboard refresh; 30 minutes on the pilot's decisions (a)-(d); 15 minutes on the
20 + 20 verdicts.

## Frozen interface (for plans 04 and 09's wave sizing, and the next dashboard refreshes)

`from assistant_axis.gapgen.testing import review_rate, ReviewRate, pooled_review_rate, promote_share,
PromoteShare, load_dashboard, DASHBOARD_JSON_PATH, GeneratorRow`: `ReviewRate(batch_id, active_minutes,
terms_applied, terms_per_active_minute, singleton_mean_s, per_member_s, promoted)` measured from a batch's logs,
`pooled_review_rate(batch_dirs)` over the batches worth pooling, `PromoteShare(per_term, per_group, n_decided,
borrowed)`, and the § 6 dashboard row (`schema_version` 1).  Fields are added, never renamed, without a schema
bump.  `select_wave`'s "~150 terms an hour" in plans 04 and 09 is the number `pooled_review_rate` now measures
(146 an hour active on the TDA batch); switching those generators to it is an interface request for their owners,
not a change this plan makes.
