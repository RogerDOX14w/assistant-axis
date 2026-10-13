# Coding plan: workstream 12, novelty measured in persona space (package `assistant_axis/gapgen/persona_space/`)

Written 2026-10-13 (Fable) in the [PLAN_FORMAT.md](./PLAN_FORMAT.md) shape from
[12_novelty_persona_space.md](./12_novelty_persona_space.md) with Roger's § 9 answers (2026-10-13) as decisions,
against the "Interface as built" section of [coding_plan_platform.md](./coding_plan_platform.md), the registry
([registry.py](../../assistant_axis/gapgen/registry.py)), M3 ([novelty.py](../../assistant_axis/gapgen/novelty.py),
[novelty_runner.py](../../assistant_axis/gapgen/novelty_runner.py)), the M2 persona loader
([persona.py](../../assistant_axis/gapgen/persona.py), [space.py](../../assistant_axis/gapgen/space.py)) and the
overlap test's persona-space record ([m3_overlap_test_readout.md](./m3_overlap_test_readout.md)).  This workstream
**generates nothing**: it is a scorer.  It fits a map from a description's text [embedding](./glossary.md#embedding)
to the entity's Qwen3-32B [persona vector](./glossary.md#persona-space), scores every registry candidate by where its
predicted vector would land among the extracted ones, and writes that beside M3's decision without touching it.
Terms: the [glossary](./glossary.md); the ones this plan introduces (canonical cell, ridge, kind covariate,
arrangement-grouped folds, energy outside the top N, shrinkage, calibration percentile, pair-axis position,
duplicate-like and novel-like, disagreement quantile, orphan vector, prospective test) are defined on first use and go
into the glossary in task 9.  **Every figure below was measured read-only on 2026-10-13** (§ "Measured figures" says
how); the fit's first run must reproduce them.  Roger's review comments go into this file.

## Open decisions (Roger's, at plan review; labelled OPEN until decided; both decided 2026-10-13)

1. **Decided (2026-10-13, Roger): where the score lives: (a), a `persona` block on the registry row.**  The brief asks for a block or a side table that M3 and the review graph can
   read.
   - (a) **A `persona` block on the registry row**: one word added to `BLOCKS` in
     [registry.py](../../assistant_axis/gapgen/registry.py) (`("freq", "wordnet", "filter", "novelty", "review",
     "persona")`), after which `Registry.update_many` merges it like the others; the row is the record, the review
     graph and plan 13's dashboard read rows already, and `compact` carries it into the tracked snapshot.  Cost: a
     one-line platform edit and about 6,700 log lines of about 500 bytes per scoring run (the gzipped snapshot grows
     by about 1 MB).  Nothing else in the registry changes; the block never alters `novelty`.
   - (b) **A side table only**, `data/candidates/persona/score/<batch>/scores.jsonl` keyed by registry key, with a
     loader the graph and the dashboard would have to call.  No platform edit; two places to look for one row.
   - **Recommendation: (a)**, with the batch directory kept as the tracked record either way (§ 5), so that another
     checkout re-applies the scores to its own log with `apply` (§ 7) exactly as `gap_registry.py submit --from`
     re-applies candidates.
   **Roger (2026-10-13): recommendation approved.**
2. **Decided (2026-10-13, Roger): what happens to the disagreement quantile: (b), to Roger and through M3's overlap call.**  Step 7 of the workstream plan hands the candidates on
   which the two novelty readings disagree "to an LLM or to Roger".
   - (a) **To Roger only**: `disagreements.md`, ordered, with both readings' evidence; $0.
   - (b) **To Roger and through M3's own [overlap call](./glossary.md#relation-overlap-calls)** ([rubric
     A](./glossary.md#rubrics-a-b), Sonnet 5.5 then Opus 5.5 under M3's rule, one pair per call, exactly as the
     recovery harness's match stage sends it through `NoveltyRunner.run_pairs`): for every candidate M3 decided `new`
     that the persona space calls duplicate-like, the pair (candidate gloss, the persona-nearest corpus trait's
     description) is read, and the reading is recorded in the batch and summarised on the block, **never written into
     the `novelty` block and never changing M3's decision**.  About $0.0024 a pair (plan 13's measured match-call rate);
     the quantile is capped at 10% of the scored rows, so at most about 670 pairs, **about $1.6-2.5, cap $5**, live.
   - **Recommendation: (b)**: a reading on record is what turns "persona space disagrees" into something a later M3
     rule can be built on, and the rendered prompt is M3's pinned one (no new rubric).  Roger reads the list either
     way.
   **Roger (2026-10-13): recommendation approved.**

If a decision is unanswered when Opus reaches the step, it proceeds under the recommendation and records that in
[QUESTIONS.md](./QUESTIONS.md) (§ 12).

## 1. Decisions already made

| decision | reason | source |
|---|---|---|
| **Fit on traits and roles together, with a kind covariate** (a 0/1 column for role appended to the embedding). | Roger: "Both".  Measured: both kinds give held-out median cosine 0.73, top-5 recovery 97%, residual Spearman 0.61-0.64; traits alone (295 rows) 0.73, 92%, 0.52. | plan 12 § 9; § "Measured figures" |
| **Start now; the prospective test is the entities with a file and no vector**: 637 traits and 61 roles (698), scored with the fit on the May vectors and compared with their actual vectors after the next extraction. | Roger: "Start now; the pending set is probably at least a week away." | plan 12 § 9 |
| **The novelty score is the energy outside the top N principal directions** of the entity pool (the [residual fraction](./glossary.md#residual) at N, called `residual_N` here), **N swept over 12, 16, 20, 24, 28, 32**, chosen where predicted and actual residual agree best on arrangement-grouped held-out rows; the whole curve reported. | Roger, 2026-10-13: the eigenvalue power law is steep (measured slope −1.1 to −1.3; λ1/λ12 = 5.8, λ1/λ32 = 19) and the space responds poorly to full whitening. | plan 12 § 9 and its consequences paragraph |
| **Predict the full centred, sheared vector (5,120-d) by ridge regression** from the 3,072-d embedding, not 20-40 PC scores.  Ridge: least squares with a penalty α on the coefficients' size; α by grouped inner cross-validation over {0.03, 0.1, 0.3, 1, 3} on held-out median cosine (measured plateau 0.1-1; 0.3 best on cosine and recovery). | the consequences paragraph (the tail energy exists only in the components predicted); the pilot fit works at 5,120-d in seconds | plan 12 § 9; § "Measured figures" |
| **The predicted residual is calibrated against its held-out distribution**, never read raw: predictions shrink toward the mean (held-out predicted `residual_24` median 0.18 against the actual 0.36), so a candidate's score is its **percentile among the held-out predicted residuals of the 574 training entities** (`residual_pct`), and its z-score beside it. | the consequences paragraph; measured shrinkage | plan 12 § 9 |
| **Nearest-neighbour distance is the secondary score, with the signed cosine kept**, and **the pair-axis position added**; antonymy is **not** read from persona space.  Measured: the 59 recorded [clean pairs](./glossary.md#clean-pair) with both vectors sit at pole-pole cosine median −0.04 (IQR −0.16..0.17), the partner's cosine at percentile 0.41 among the pole's cosines to every trait (median of all trait pairs 0.01), the partner among a pole's five nearest for 3% of poles; so the cosine separates duplicates (0.7-0.9) from everything else, not antonyms from unrelated traits.  M3's relation call keeps the "opposite" verdict; where the nearest trait has a partner with a vector, the candidate's position along the pair's own axis is reported (poles sit 2.9 standard deviations out along it). | Roger's secondary score, corrected by the measurement (§ "Inconsistencies", 3) | plan 12 § 9; § "Measured figures" |
| **Variant B (a Qwen forward pass on RunPod) is an optional TODO**, written up at the end of this plan, not built. | Roger: "hold off on it for now, but keep the ideas as an optional TODO" | plan 12 § 9 |
| **The space is the one M2 and M3 already use**: [persona.load_persona_space](../../assistant_axis/gapgen/persona.py): the 8-slot tree at the **canonical cell** slot 6, layer 25, centred on the corpus mean over traits and roles together, [soft shear](./glossary.md#soft-shear) L=3 (buildable on this tree: `shear_applied` true), the slices cached in [persona_s6_l25.npz](../../data/candidates/cache/persona_s6_l25.npz) (git-ignored).  **The pool is the 582 vectors as that loader returns them** (302 traits, 280 roles, `default` excluded) for centring, shear and the PC basis, so the geometry is byte-identical to M2's and the overlap test's; **training rows and neighbour lists are the 574 with a current corpus file** (295 traits, 279 roles). | the axis-geometry rule's defaults; one space for every persona reading in the platform | [coding_plan_platform.md](./coding_plan_platform.md) task 15 |
| **The eight orphan vectors stay out of training and out of neighbour lists**: an orphan vector is one whose entity has no current file and no file naming it in `renamed_from` (so none of these eight has a file to link): the traits conceptual and enigmatic (dropped as near-duplicates in 647ca4dc), dramatic (83febfbe), mercurial and technical (872433d5), cruel (2f944dd3), regulatory (602d8ca1), and the role adolescent (647ca4dc); a candidate "nearest to cruel" would name a trait that does not exist.  A vector stem that is a `renamed_from` of a current file counts for that file (19 traits, 1 role), **except the three `SENSE_CHANGED_RENAMES`** of [labels.py](../../assistant_axis/gapgen/labels.py) (bland → dull, libertarian → metaphysical_libertarian, savage → violent), whose May vector describes the old sense: out of training, like orphans. | the May vector was extracted from a description the corpus no longer has | this plan; [labels.py](../../assistant_axis/gapgen/labels.py) |
| **Embeddings: OpenAI `text-embedding-3-large`, direct key, through the platform's cache**; the text is the covered setting's representation, `label: text` cut to 20 words ([`w20`](./glossary.md#representations)), on both sides: a corpus entity as `positive_label: description` (a role as its `corpus_display_name: description`), a candidate as `label: gloss` (`novelty.query_text(..., query_form="label_gloss")`).  All 932 trait and 339 role `w20` texts are cached (29,917 texts under the OpenAI tag); candidate texts in this form are not: 6,735 × about 40 tokens ≈ $0.035. | [metric_config.json](../../data/candidates/metric_config.json) (Roger's M2 settings); the hosted-models rule (no router) | platform; CLAUDE.md |
| **Candidates are registry rows, selected exactly as M3 selects them**: `novelty_runner.candidate_from_row` (verdict `trait`, a gloss; `--holding states\|physical` for the passes' rows), for every generator: **6,735 rows today** (M3: 3,834 `new`, 2,864 `covered`, 1 `grey`, 36 undecided).  The seed queue is not scored (out of scope). | the brief: "registry rows (label plus the M1 gloss) for every generator" | this plan |
| **M3's `novelty` block, rules and cut-offs are untouched.**  The scorer writes its own block (decision 1) and its batch directory; a future M3 rule that reads the persona flag is Roger's call, not this plan's. | the brief | this plan |
| **The overlap test's 280 persona cosines are calibration data, not training data**: they are actual-against-actual cosines of trait pairs with their rubric-A readings (mean cosine by reading: 0 → 0.22, 1 → 0.44, 2 → 0.61, 3 → 0.82, 4 → 0.87, opposite → 0.03), used to check where the duplicate threshold sits in actual space; the regression trains on (embedding, vector) pairs. | the Status section's sentence corrected (§ "Inconsistencies", 10) | [m3_overlap_test_readout.md](./m3_overlap_test_readout.md) |
| **Held-out evaluation uses arrangement-grouped folds**: `GroupKFold` (every row of a group in one fold) with the groups of [recovery.hiding_groups](../../assistant_axis/gapgen/recovery.py) for traits (pairs, triangles, tetrahedra and the label-reciprocal partner together) and the role arrangements from [arrangements.py](../../assistant_axis/arrangements.py), so a held-out trait's antonym is never in its training fold; 471 groups over the 574 rows. | plan 12 step 4 | this plan |
| **The kNN baseline is kept; PLS is not built.**  Measured: the weighted mean of the k nearest training vectors by embedding cosine gives median cosine 0.57 / 0.65 / 0.68 / 0.69 at k = 1 / 3 / 5 / 10 against ridge's 0.73, so the regression buys something and a second regressor is not needed to show it. | plan 12 step 3 ("if kNN wins, the regression buys nothing") answered by the pilot | this plan |
| **Library code in `assistant_axis/gapgen/persona_space/`, the CLI in [persona_novelty.py](../../data_analysis/gap_generation/persona_novelty.py) (not there yet)**, outputs under `data/candidates/persona/`. | the platform's layout (PLAN_FORMAT § 5) | this plan |
| **Live transport for everything** (nothing here reaches $5). | the batch-or-real-time rule | [CLAUDE.md](../../CLAUDE.md) |
| **Counts as of 2026-10-13, used throughout**: 932 trait files, 340 role files (339 with a description; the odd one is `default`, not an entity); 302 + 280 vectors; registry snapshot 9,941 keys. | counted, not copied | this plan |

## 2. Out of scope

- Any change to M3's decisions, rules, rubrics, cut-offs or [metric_config.json](../../data/candidates/metric_config.json);
  any write to a `novelty` block; any promotion.
- Variant B (the RunPod forward pass); any GPU work; any new extraction.
- Scoring the seed queue's entries or the overlap test's pairs; the role track.
- PLS; a local embedding model (the platform's `LocalEmbedder` arms are inactive).
- Plan 13's dashboard and the review graph (interface requests only, § "Interface requests").
- Any edit to `data/traits/**`, `data/roles/**`, [seed_queue.json](../../data/seed_queue.json), the registry's other
  blocks, or any recorded M3 or harness output.

## 3. Rule files to Read first

Open with the **Read tool** before touching code:
[provenance.md](../../.claude/rules/provenance.md) (`usage.json` beside every paid output, `MultiModelUsage`;
`json_metadata` envelopes on every JSON this plan writes; UTC timestamps; snapshot before overwrite),
[entity-naming.md](../../.claude/rules/entity-naming.md) (every neighbour list mixes traits and roles, so keys are
`name|T` / `name|R` ids via `entity_id`, never bare names; display form only in prompts and Markdown; US English),
[axis-geometry.md](../../.claude/rules/axis-geometry.md) (the shear and whitening defaults; the May vectors are bf16
and are cast to float32 on load; October's will be float32),
[trait-pairs.md](../../.claude/rules/trait-pairs.md) (what a pair, an arrangement and `renamed_from` are),
[judging.md](../../.claude/rules/judging.md) (the overlap call of decision 2 is M3's pinned rubric: reason before
verdict, `warn_if_low_parse_rate`, the rendered-prompt rule), [plotting.md](../../.claude/rules/plotting.md) (one PNG
is planned, § 5: `png_metadata`, read the file back), [CLAUDE.md](../../CLAUDE.md) (file-access boundary, the $20
rule, **tests are mandatory**, hotlinks).

**File-access boundary, restated for every Opus task prompt**: read and write only inside the repository worktree,
the agent's scratchpad and `$TMPDIR`; never list, read or stat anything else under the home directory, not
`~/.cache`, not even to see whether something is downloaded.  This workstream downloads nothing and never opens
`.env`; the OpenAI key is read by `OpenAIEmbedder` through `load_dotenv` and never printed.

## 4. Existing code to reuse

- [persona.py](../../assistant_axis/gapgen/persona.py): `load_persona_space(data_dir, slot=6, layer=25, shear_L=3)`
  (the cached pool: `stems`, `kinds`, `M` centred and sheared, `shear_applied`), `DEFAULT_VECTORS_DIR`;
  [space.py](../../assistant_axis/gapgen/space.py): `pca_basis`, `residual_fraction`, `loo_residuals`,
  `k_for_variance`.  Do not change `load_persona_space`: the overlap test and M2 recorded their cosines in it.
- [embed.py](../../assistant_axis/gapgen/embed.py): `OpenAIEmbedder`, `EmbeddingCache`, `embed_texts` (cache misses
  only, charged to a `MultiModelUsage`), `check_canary` (the drift canary every embedding run sends);
  [representation.py](../../assistant_axis/gapgen/representation.py) `represent(label, text, "w20")`;
  [novelty.py](../../assistant_axis/gapgen/novelty.py) `query_text(label, gloss, query_form="label_gloss")`,
  `load_trait_corpus` (`CorpusTrait.renamed_from`, `pair_partner`, `expands_to`), `blind`;
  [metric_config.py](../../assistant_axis/gapgen/metric_config.py) `MetricConfig.load()` (the live model, the canary
  texts, `config_version`).
- [novelty_runner.py](../../assistant_axis/gapgen/novelty_runner.py): `candidate_from_row(row, holding=)` (the
  candidate selection), `M3Candidate`, `NoveltyRunner` and `run_pairs(cands, pairs, wave=)` (decision 2b; the call
  shape is in [recovery.match_candidates](../../assistant_axis/gapgen/recovery.py)); `novelty.pair_verdict`,
  `cut_off_spec`.
- [recovery.py](../../assistant_axis/gapgen/recovery.py) `hiding_groups(traits)` (the trait groups for the folds);
  [arrangements.py](../../assistant_axis/arrangements.py) `load_corpus_arrangements(data_dir, "roles")`,
  `reciprocal_pairs`; [labels.py](../../assistant_axis/gapgen/labels.py) `corpus_renames`, `SENSE_CHANGED_RENAMES`;
  [entity_id.py](../../assistant_axis/entity_id.py) `entity_id`, `parse_entity_id`, `corpus_display_name`,
  `resolve_renamed_stem`; [prompt_labels.py](../../assistant_axis/gapgen/prompt_labels.py) `prompt_label`.
- [registry.py](../../assistant_axis/gapgen/registry.py): `Registry.fold`, `update_many` (merges a block), `BLOCKS`,
  `read_snapshot`, `snapshot_file`; [runs.py](../../assistant_axis/gapgen/runs.py) `dirty_refusal`, `git_sha`;
  [cost.py](../../assistant_axis/gapgen/cost.py) `Estimate`, `confirm_or_abort`, `GuardedUsage`;
  [judge_pricing.py](../../assistant_axis/judge_pricing.py) `MultiModelUsage` (`text-embedding-3-large` is priced at
  $0.13 per MTok input); [provenance.py](../../assistant_axis/provenance.py) `current_file_input`,
  `current_data_subtree_input`; [plot_metadata.py](../../assistant_axis/plot_metadata.py) `json_metadata`,
  `png_metadata`; [atomic_io.py](../../assistant_axis/atomic_io.py).
- scikit-learn 1.8.0 (`Ridge`, `GroupKFold`), scipy 1.17.0 (`spearmanr`), numpy, torch 2.10.0 (reading `.pt`,
  already behind `load_persona_space`); **no new dependencies**.
- Test style: [test_gapgen_persona.py](../../assistant_axis/tests/test_gapgen_persona.py) (synthetic subspace
  fixtures; the real-pool test skipped when the vectors tree is absent),
  [test_gapgen_recovery.py](../../assistant_axis/tests/test_gapgen_recovery.py) (`toy`, the fake responder for a
  `NoveltyRunner`), [test_gapgen_embed.py](../../assistant_axis/tests/test_gapgen_embed.py) (`HashEmbedder`, a fake
  OpenAI client that charges tokens).

## 5. File layout

```
assistant_axis/gapgen/persona_space/
  __init__.py      PERSONA_DIR = DATA_CANDIDATES / "persona"; PERSONA_BLOCK_VERSION = 1; re-exports (§ Frozen)
  pool.py          Pool(ids: list[str] (name|T / name|R), vector_stems, kinds, cur_stems, has_file: np.ndarray,
                   M: (582, 5120), space: dict (load_persona_space's record), train_idx, orphan_ids, sense_changed_ids)
                   load_pool(data_dir=DATA_DIR, vectors_dir=DEFAULT_VECTORS_DIR) -> Pool   (vector stem -> current file
                   through the stem, then renamed_from; SENSE_CHANGED_RENAMES and orphans flagged, never trained on)
                   corpus_texts(pool, data_dir) -> list[str]      (positive_label / corpus_display_name: description, w20)
                   fold_groups(pool, data_dir) -> np.ndarray        (hiding_groups for traits; role arrangements; one id per
                   group; a row alone is its own group)
                   pc_basis(M, N) -> (N, 5120); residual_N(V, basis) -> np.ndarray; pair_partners(pool, data_dir) -> {id: id}
  fit.py           FitConfig(alphas=(0.03, 0.1, 0.3, 1.0, 3.0), n_folds=5, Ns=(12, 16, 20, 24, 28, 32), knn_k=5,
                   n_report_pcs=64, seed=0)
                   features(E, kinds) -> X (unit rows plus a role column)
                   cross_validate(pool, E, groups, cfg) -> CV   (per alpha: held-out predictions, cosine to the actual
                   vector, top-1 / top-5 recovery among the 574, per-PC R² on the pool's top 64 PCs, residual_N true and
                   predicted for every N on the fold's own basis, Spearman between them; kNN cosine; the chosen alpha)
                   choose_alpha(cv) -> float (max held-out median cosine; ties by the smaller alpha)
                   choose_N(cv, alpha, tie_window=0.02, prefer=20) -> int (max Spearman; within tie_window of the max,
                   the N nearest 20)
                   fit_final(pool, E, alpha) -> Model(coef (3073, 5120) float32, intercept, alpha, kinds_seen)
                   save_model / load_model (npz, gitignored, rebuilt by `fit` in seconds); predict(model, E, kinds) -> P
  calibrate.py     Calibration(fit_id, N, alpha, residual_pred_quantiles (every 5th percentile), residual_true_quantiles,
                   self_cos_quantiles, nn_cos_pred_quantiles, dup_threshold, novel_pct, config_version, n_train)
                   from_cv(cv, N) -> Calibration;  residual_pct(x, cal) -> float;  residual_z(x, cal) -> float;
                   flag(nn_cos, residual_pct, cal) -> "duplicate_like" | "novel_like" | "ordinary"
  score.py         candidates(registry, *, run, keys, all_rows, holding) -> list[M3Candidate]  (candidate_from_row)
                   candidate_texts(cands) -> list[str]                                 (label: gloss, w20)
                   PersonaScore(key, nn (id, kind, cos), nearest (3 ids with cosines), residual (by N), residual_pct,
                   residual_z, pair_axis (a, b, position) | None, flag, fit_id, config_version)
                   score_vectors(P, cands, pool, cal, *, Ns) -> list[PersonaScore];  persona_block(score, batch_id) -> dict
                   apply_blocks(registry, scores, batch_id) -> n_written   (decision 1a; idempotent per key and batch)
  compare.py       Agreement(auc_nn_cos_covered_vs_new, spearman_nn_cos_vs_m3_cosine, covered_by_is_nearest,
                   covered_by_in_top3, n) ; agreement(scores, rows) -> Agreement
                   Disagreement(key, kind: "dup_vs_new" | "cover_questioned" | "novel_vs_covered", m3_decision,
                   covered_by, m3_listed_first, persona_nearest, nn_cos, residual_pct, evidence)
                   disagreements(scores, rows, cal, *, quantile=0.10) -> list[Disagreement];  markdown(...)
  judge.py         (decision 2b) pairs(disagreements, kind="dup_vs_new") -> [(key, stem, rank)]
                   read_pairs(runner, cands, pairs, *, wave="p") -> readings   (NoveltyRunner.run_pairs; recorded by the
                   runner before parsing; a budget stop raised after every answer is recorded)
                   summarise(readings, cands) -> {key: {"stem", "sonnet", "opus", "verdict", "at_cut_off": bool}}
  prospective.py   pending(pool, data_dir) -> list[(kind, stem)]  (a file and no vector: 637 + 61)
                   predict_pending(model, cal, pool, texts) -> rows (the PersonaScore fields, kind, stem)
                   compare(pred_rows, new_vectors_dir, *, slot, layer, shear_L, N) -> Comparison (rank Spearman of the
                   residual, nearest-3 overlap, top-1 / top-3 name hits, AUC of predicted nn_cos for actual nn_cos >= 0.7,
                   the named-pair checks); the new pool is loaded, centred and sheared on itself
  report.py        fit_report(cv, cal) -> markdown + fit_report.png (two panels: per-PC R² bars 1-64; residual
                   Spearman against N with the chosen N marked); score_report(scores, agreement, disagreements) ->
                   markdown (top 30 and bottom 30 by residual_pct with nearest names, the agreement table, the
                   disagreement list); prospective_report(comparison) -> markdown
data_analysis/gap_generation/persona_novelty.py
                   fit | score | apply | compare | judge-disagreements | prospective (predict | compare) | report
data/candidates/persona/
  fit/<fit_id>/{cv.json, calibration.json, fit_report.md, fit_report.png, run.json, usage.json}   tracked
  fit/<fit_id>/model.npz                                                                        GITIGNORED (63 MB; rebuilt)
  score/<batch_id>/{scores.jsonl, summary.json, agreement.json, disagreements.jsonl, disagreements.md, readings.jsonl,
                   responses.jsonl, run.json, usage.json}                                       tracked
  score/<batch_id>/predictions.npz                                                             GITIGNORED (float16)
  prospective/<fit_id>/{predicted.jsonl, compare_<tree>.json, compare_<tree>.md, run.json}        tracked
  prospective/<fit_id>/predictions.npz                                                          GITIGNORED
assistant_axis/tests/test_gapgen_persona_space_{pool,fit,calibrate,score,compare,judge,prospective,acceptance}.py
data_analysis/tests/test_gap_generation_persona_novelty_cli.py
```

[.gitignore](../../.gitignore) gains `/data/candidates/persona/**/*.npz`.  One platform edit under decision 1a:
`BLOCKS` in [registry.py](../../assistant_axis/gapgen/registry.py) gains `"persona"` (no test enumerates the tuple
today; [test_gapgen_registry.py](../../assistant_axis/tests/test_gapgen_registry.py) gains one that does).
Nothing else outside the new package changes.  **Definitions.**  The *canonical cell* is (slot 6, layer 25) of the
8-slot tree ([traits/vectors](<../../runpod_workspace/qwen/qwen-3-32b Roger 8slot/traits/vectors/>),
[roles/vectors](<../../runpod_workspace/qwen/qwen-3-32b Roger 8slot/roles/vectors/>)).  *Energy outside the top N*
is `1 − |B_N v|² / |v|²` for the pool's top-N principal directions `B_N` (the residual fraction at N; for a
held-out row, `B_N` is fitted on its training fold).  *Shrinkage* is the regression's pull toward the mean, which
makes every predicted residual smaller than the actual one; the *calibration percentile* reads a predicted residual
against the distribution of held-out predicted residuals of existing entities, where the shrinkage is the same.  The
*pair-axis position* of a predicted vector p, when the nearest trait A has a partner B with a vector, is
`((p − (A+B)/2) · d) / (|A − B| / 2)` with `d = (A − B)/|A − B|`: +1 at A, −1 at B.  *Duplicate-like*: the cosine
to the nearest existing entity is at least `dup_threshold`, the median held-out cosine between a training entity's
prediction and its own vector (0.73 today: the candidate is as close to an existing entity as a held-out entity's
prediction is to itself, half the time); *novel-like*: `residual_pct ≥ novel_pct` (0.80).  Both thresholds are
recorded in `calibration.json` and are Roger's to move at the pilot gate.

## 6. Data schemas

**The `persona` block** (decision 1a; one per scored row; illustrative values for the IPIP candidate
`achievement_driven#1`, whose M3 block lists [persevering](../../data/traits/instructions/persevering.json) first):

```json
{"version": 1, "batch_id": "persona_2026-10-14_all", "fit_id": "fit_2026-10-14", "config_version": "2026-10-14",
 "N": 20, "residual": 0.21, "residual_pct": 0.62, "residual_z": 0.31,
 "nn": {"id": "ambitious|T", "cos": 0.76}, "nearest": [["ambitious|T", 0.76], ["persevering|T", 0.66], ["workaholic|T", 0.58]],
 "pair_axis": {"a": "ambitious|T", "b": "unambitious|T", "position": 0.84},
 "flag": "duplicate_like", "m3_decision": "new", "m3_listed_first": "persevering", "disagreement": "dup_vs_new",
 "reading": null, "at": "2026-10-14T10:00:00+00:00"}
```

`reading` (decision 2b) is `{"stem", "sonnet", "opus", "verdict", "at_cut_off"}` on a judged disagreement row, else
null; `disagreement` is the kind or null.  No vector is stored on the row.  **Vocabularies**: `flag` ∈ {duplicate_like,
novel_like, ordinary}; `disagreement` ∈ {dup_vs_new, cover_questioned, novel_vs_covered, null}.  Ids are
`name|T` / `name|R`; the Markdown reports show `corpus_display_name` with the role marker.

**Score row** ([scores.jsonl](../../data/candidates/persona/score/persona_2026-10-14_all/scores.jsonl), not there
yet; one line per scored row): the block's fields plus `key`, `label`, `generators`, `residual_by_N` (every N of the
sweep) and `nn_cos_by_kind` (`{"T": 0.71, "R": 0.44}`).

**Cross-validation record** ([cv.json](../../data/candidates/persona/fit/fit_2026-10-14/cv.json), not there yet;
enveloped): per alpha `{"median_cos", "median_cos_traits", "median_cos_roles",
"top1", "top5", "per_pc_r2": [64 floats], "rho_by_N": {"12": 0.61, ...}, "residual_true_median_by_N",
"residual_pred_median_by_N"}`, `knn_cos_by_k`, `alpha`, `N`, `n_rows`, `n_groups`, `n_train_traits`,
`n_train_roles`, `orphans`, `sense_changed`, `spectrum` (`k50`, `k80`, `k90`, `k95`, `k99`, `top12_share`,
`loglog_slope_1_64`), `inputs` (the vectors subtree fingerprint, the cache file, the corpus subtrees).

**Calibration** ([calibration.json](../../data/candidates/persona/fit/fit_2026-10-14/calibration.json), not there
yet): `Calibration` as a dict, enveloped, with `dup_threshold`, `novel_pct`, the quantile tables, and
`thresholds_set_by` (`"plan default"` until Roger moves them).

**Agreement** ([agreement.json](../../data/candidates/persona/score/persona_2026-10-14_all/agreement.json), not there
yet): `{"n": 6698, "auc_nn_cos_covered_vs_new": 0.0, "spearman_nn_cos_vs_m3_cosine": 0.0,
"covered_by_is_nearest": 0.0, "covered_by_in_top3": 0.0, "flags": {"duplicate_like": 0, "novel_like": 0,
"ordinary": 0}, "by_generator": {...}}` (values filled by the run).

**Disagreement row** ([disagreements.jsonl](../../data/candidates/persona/score/persona_2026-10-14_all/disagreements.jsonl),
not there yet): `{"key": "achievement_driven#1", "kind": "dup_vs_new",
"m3_decision": "new", "covered_by": null, "m3_listed_first": "persevering", "persona_nearest": "ambitious|T",
"nn_cos": 0.76, "residual_pct": 0.62, "evidence": "nn_cos 0.76 >= dup_threshold 0.73; M3 listed persevering first
at text cosine 0.38 and read nothing at the cut-off"}` (illustrative values on a real key; the kinds: `dup_vs_new`, M3 `new` and `flag` duplicate_like; `cover_questioned`, M3 `covered`
by X with `cos(p, X)` below the 10th percentile of held-out self-cosines and X not among the three nearest;
`novel_vs_covered`, M3 `covered` and `residual_pct ≥ 0.9`).

**Prospective row** ([predicted.jsonl](../../data/candidates/persona/prospective/fit_2026-10-14/predicted.jsonl),
not there yet): `{"kind": "traits", "stem": "risk_averse", "id": "risk_averse|T", "residual": 0.19,
"residual_pct": 0.55, "nn": ["cautious|T", 0.69], "nearest": [...], "flag": "ordinary"}`; the comparison
(`compare_<tree>.json` beside it, written after the extraction): `{"tree": "...", "n": 698, "n_with_vector": 0, "rho_residual_rank": null,
"nearest3_jaccard_mean": null, "top1_name_hit": null, "top3_name_hit": null, "auc_dup": null, "named_pairs": {...}}`.

## 7. CLI

[persona_novelty.py](../../data_analysis/gap_generation/persona_novelty.py) (not there yet).  Common flags
`--data-dir`, `--vectors-dir` (default `persona.DEFAULT_VECTORS_DIR`), `--registry` (default the live log;
`--snapshot` for the tracked one), `--out-root` (default `data/candidates/persona/`), `--cache-dir`, `--budget-usd`
(default 1.0; `judge-disagreements` 5.0), `--confirm-expensive --confirmed-by`, `--allow-dirty` (paid commands refuse
uncommitted platform code, `runs.dirty_refusal`), `--dry-run` (prints the plan, the estimate and, for `score`, the
first three candidate texts; writes nothing, calls nothing).  Every JSON output is enveloped with its inputs; every
paid command writes `usage.json` and `run.json` (argv, git sha, `config_version`, counts, the canary's result).

- `fit --fit-id F [--alphas ...] [--folds 5] [--Ns 12 16 20 24 28 32] [--knn-k 5] [--seed 0]`: the pool, the texts
  (cache hits; a miss is embedded and charged: at most a few cents), the cross-validation, the chosen alpha and N,
  the final model on all 574 rows, `calibration.json`, `fit_report.md` and `.png`.  $0 today (every corpus text is
  cached); seconds to a minute.
- `score --batch-id B --fit-id F (--run G/R ... | --keys ... | --all-rows) [--holding states|physical]
  [--write-registry] [--quantile 0.10]`: embeds the candidate texts (6,735 ≈ $0.035; the canary first), predicts,
  scores, writes `scores.jsonl`, `summary.json`, `agreement.json` and the disagreement files; with
  `--write-registry` the `persona` block on each row (decision 1a).  The estimate is printed first.
- `apply --batch-id B`: re-applies a recorded `scores.jsonl` to this checkout's registry log, $0, idempotent.
- `compare --batch-id B`: recomputes the agreement and the disagreements from `scores.jsonl` and the registry; $0.
- `judge-disagreements --batch-id B [--kind dup_vs_new] [--max-pairs 700] --budget-usd 5 [--resume]` (decision 2b):
  the overlap call on each disagreement pair through `NoveltyRunner` (live; `responses.jsonl` recorded before
  parsing; `warn_if_low_parse_rate`); writes `readings.jsonl` and, when the batch has written blocks, the `reading`
  field.  About $1.6-2.5.
- `prospective predict --fit-id F`: the 698 pending entities (texts cached; $0) to `prospective/<F>/`.
  `prospective compare --fit-id F --new-vectors-dir DIR [--N n]`: after the extraction; $0.
- `report --batch-id B`: `score_report.md` for Roger (top and bottom 30, the agreement table, the disagreement list).

## 8. Acceptance tests, written first

No test calls an API: texts go through `HashEmbedder`, the pool is a synthetic 60-row space with planted structure, the
overlap call uses the fake responder of [test_gapgen_recovery.py](../../assistant_axis/tests/test_gapgen_recovery.py).
The figures marked **hard** were measured on 2026-10-13 on the recorded data and run only where the vectors tree and
the embedding cache are present (skip otherwise, as `test_real_pool_shapes` does); the rest are report-and-decide.

- `pool`: **hard**: 582 rows (302 traits, 280 roles), 574 with a file (295 + 279), the 8 orphans by name, the 3
  sense-changed renames excluded from `train_idx`, 19 + 1 rows matched through `renamed_from`; `shear_applied`
  true; **K_95 = 170, K_50 = 10, K_80 = 45** (`k_for_variance` on the pool); on a toy corpus `fold_groups` puts both
  poles of a pair, the three corners of a triangle and a role pair in one group and singletons alone; ids are
  `name|T` / `name|R` and a trait and a role of the same name are two rows; `residual_N` is in [0, 1] and 0 for a
  vector inside the basis.
- `fit`: `features` appends exactly one column; on synthetic data (a linear map plus noise) ridge recovers the map
  (held-out cosine > 0.95) and the per-PC R² of a planted unpredictable direction is near 0; `choose_alpha` and
  `choose_N` on hand-made tables (the tie rule picks 20 inside the window, the maximum outside it); `fit_final` is
  deterministic (two fits, identical bytes); `predict` on a saved and reloaded model equals the in-memory one.
  **hard, on the recorded pool at alpha 0.3** (soft bounds, two decimals below the measurement): held-out median
  cosine ≥ 0.70, top-1 ≥ 0.70, top-5 ≥ 0.95, per-PC R² ≥ 0.75 on PC1, residual Spearman ≥ 0.55 at every N of the
  sweep, kNN k = 5 median cosine ≤ 0.70 (the regression beats it).
- `calibrate`: quantile tables from a fixture; `residual_pct` is monotone and 0.5 at the median; `flag` on the
  three regions; **hard**: `dup_threshold` in [0.68, 0.78] and the held-out predicted `residual_24` median in
  [0.12, 0.24] against an actual median in [0.32, 0.40].
- `score`: `candidates` selects exactly what `candidate_from_row` selects (fixture rows with every verdict and a
  held row); candidate texts are `label: gloss` in `w20`; `score_vectors` on the toy pool gives the planted
  nearest, a pair-axis position of about +1 for a vector at a pole and about 0 at the midpoint, null when the
  nearest has no partner; `persona_block` has every field of § 6 and no vector; `apply_blocks` merges the block and
  touches no other field (`novelty` byte-identical before and after); applying twice writes nothing new.
- `compare`: `agreement` and `disagreements` on a fixture registry with planted covered and new rows give
  hand-computed AUC, shares and the three disagreement kinds; the quantile cap holds.
- `judge`: `pairs` lists each `dup_vs_new` row once with its persona-nearest stem; `read_pairs` with the fake
  responder records every answer before parsing (an unparseable one too) and raises after recording on a budget
  stop; `summarise` applies `pair_verdict` at the candidate's cut-off; the user turn of a rendered call is the JSON
  of § "Rendered prompt" (candidate as target, corpus trait as other).
- `prospective`: `pending` counts the entities with a file and no vector (**hard**: 637 traits, 61 roles); `compare`
  on a toy new tree (a rotated copy of the toy pool with two extra entities) gives rank Spearman 1.0 and full name
  hits for the planted entities; the new pool is centred and sheared on itself, never on the old mean.
- `report`: the Markdown has the per-PC table, the N curve, both 30-row lists and the disagreement list; the PNG is
  written with `png_metadata` and **read back by the agent** (plotting rule) before the task closes.
- CLI: every subcommand's `--dry-run` exits 0 and writes nothing; `score` prints the estimate and refuses over
  budget; a paid command refuses a dirty platform tree without `--allow-dirty`; every output carries the envelope.
- **Acceptance on recorded outputs**
  ([test_gapgen_persona_space_acceptance.py](../../assistant_axis/tests/test_gapgen_persona_space_acceptance.py), not
  there yet; skips while the outputs are absent): `cv.json` reproduces the hard figures; `calibration.json` records
  both thresholds and who set them; every `score` batch has `usage.json` and `summary.json`; the first full batch
  has a `persona` block on every scored key of the snapshot (if decision 1a) and `agreement.json`; the prospective
  `predicted.jsonl` has 698 rows; `git status --porcelain data/traits data/roles data/seed_queue.json` is empty.
- **Manual check, listed as such**: Roger reads the top 30 and bottom 30 by `residual_pct`, and the disagreement
  list with its readings (gate 2 of § 10); recorded in the acceptance report.

Commands that must pass at the end of every task:

```
uv run pytest assistant_axis/tests/test_gapgen_persona_space_*.py data_analysis/tests/test_gap_generation_persona_novelty_cli.py assistant_axis/tests/test_gapgen_persona.py assistant_axis/tests/test_gapgen_registry.py -q
uv run pytest -q                                                  # whole suite, unchanged
uv run python data_analysis/gap_generation/rubric_pins.py check   # no rubric changes: must stay green
uv run python data_analysis/check_arrangements.py --quiet
uv run python tools/sync_entity_lists.py --check
git status --porcelain data/traits data/roles data/seed_queue.json   # must be empty
```

## 9. Ordered task checklist

Prerequisite: a worktree off `anthropic-vllm-uv` (`git merge --ff-only anthropic-vllm-uv` first), `.env` copied,
`runpod_workspace/` (git-ignored) and `data/candidates/cache/` (the embedding cache and `persona_s6_l25.npz`) linked
from the main checkout, the registry log of the main checkout reachable for `--write-registry` (or the batch applied
there with `apply` afterwards).  The boundary paragraph of § 3 goes into every task prompt verbatim.  Each task ends
with the § 8 commands.

1. Skeleton, `pool.py`, the `BLOCKS` edit (decision 1a).  Test: pool (the hard counts, K_95).  Paste the orphan and
   sense-changed lists into the task report.
2. `fit.py`, `calibrate.py`, `report.fit_report`, CLI `fit`; **run `fit --fit-id fit_<date>`** ($0).  Test: fit,
   calibrate (the hard figures).  Paste the per-PC table, the alpha table and the N curve.  **Gate 1 (§ 10)**: Roger
   reads `fit_report.md` and the PNG, confirms N and the two thresholds or moves them.
3. `score.py`, `compare.py`, `report.score_report`, CLI `score`, `apply`, `compare`, `report`; **run `score` on one
   generator run** (IPIP `2026-10-13-g600`, 490 rows, about $0.003) without `--write-registry`.  Test: score,
   compare.  **Gate 2**: Roger reads the 30 + 30 and the disagreement list of that batch.
4. `judge.py`, CLI `judge-disagreements` (decision 2b; skipped under 2a); run it on the IPIP batch (a few dozen
   pairs, under $0.20).  Test: judge.  Paste the readings beside the persona evidence.
5. **The full batch**: `score --all-rows --batch-id persona_<date>_all --write-registry` (6,735 rows, about $0.035),
   then `judge-disagreements` (about $1.6-2.5, cap $5), `compare`, `report`; `gap_registry.py compact` in the main
   checkout.  Paste the agreement table and the disagreement counts by generator.
6. `prospective.py`, CLI `prospective predict` and `compare`; **run `predict`** on the 698 ($0).  Test: prospective
   (the toy new tree).  `compare` is run after the extraction, by whoever runs it, with the command printed in the
   report.
7. Interface requests written (§ "Interface requests"): the plan-13 dashboard fields, the review-graph node fields,
   as text in the acceptance report and a QUESTIONS entry each; no edit to those plans or that code.
8. Glossary entries ([glossary.md](./glossary.md): the terms listed in the introduction); the
   [data/README.md](../../data/README.md) paragraph for `candidates/persona/` proposed in the report (not edited; the
   platform owns that file); the `.gitignore` line.
9. Acceptance report (§ 11).

## 10. Pilot

The pilot is **the fit** (task 2, $0), which already carries the per-PC R² table (the finding the workstream plan
asked for: "PC1-5 well above 0.4, unused PCs 10-20 near zero; the table itself is a finding"; measured 0.83 on PC1,
0.63-0.66 on PCs 7-8, 0.53 mean over 9-24, 0.32 over 25-48: the tail is predicted worse, not at zero), the
alpha table, the N curve with the chosen N, the kNN comparison, the recovery rates, and the two thresholds.  **Roger
decides** on it: (a) N (the plan's rule picks it; the measured curve is flat, 0.61-0.64 over 12-32, so his
preference can override at no cost); (b) `dup_threshold` and `novel_pct`; (c) whether the per-PC table changes
anything about which generators to run (a direction the text predicts badly is one the text-only scorer cannot
see either).  The second gate is the one-run score (task 3, about $0.003): Roger reads the top and bottom 30 by
`residual_pct` with their nearest names and the disagreement list, and says whether the flags read as duplicates by
enactment and novel directions, or as noise; a bad read stops task 5 and goes back to Fable.  Yield per dollar is
not the figure here (nothing is generated); the pilot's figures are the recovery rates, the N curve, the agreement
with M3 and the disagreement share (the workstream plan expects 5-15% of a batch flagged as duplicates-by-enactment).

## 11. Report at the end

One page at [acceptance_12_persona_space.md](./acceptance_12_persona_space.md) (not there yet): what was built
against § 5; deviations with reasons; the § 8 commands verbatim with pass counts; the pool counts and the orphan
list; the per-PC R² table (1-24 individually, 25-48 and 49-64 as means), the alpha table, the N curve and the
chosen N with the tie rule's part in it; the kNN comparison; recovery rates by kind; the shrinkage figures and the
two thresholds; the full batch's agreement table (AUC, the `covered_by`-is-nearest share, Spearman against M3's
cosine) and flag counts by generator; the disagreement counts by kind and generator, with the readings of decision
2b and how many read at the cut-off; the prospective `predict` counts and the exact `compare` command to run after
the extraction; Roger's gate-1 and gate-2 notes; cost per model from every `usage.json`; open QUESTIONS entries; the
interface requests; the proposed [data/README.md](../../data/README.md) paragraph; and the one-line answer the workstream plan asks for:
**how many registry candidates does persona space call duplicates that the text missed, and how many novel
directions does it see that the text called covered.**

## 12. Escalation

Opus retries a failing step once with a changed approach, then Fable (diff review, architecture, stubborn
failures), then Roger through [QUESTIONS.md](./QUESTIONS.md) in its format (`N. [12] question. Assumption proceeded
under: ... Status: open`, numbering continuing from the file's last entry, 90 on 2026-10-13), proceeding under the
assumption unless the answer would make the work useless.  Pre-registered entries Opus copies in at the start:
(91) antonyms are not antipodal at the canonical cell (pole-pole cosine median −0.04, partner percentile 0.41, 3% of
partners among the five nearest), so the signed cosine is reported as information, the pair-axis position is added,
and antonymy stays with M3's relation call; (92) PLS is not built, kNN is the baseline (measured 0.68 against ridge's
0.73); (93) the eight orphan vectors and the three sense-changed renames stay in the pool for centring, shear and
the PC basis and out of training and neighbour lists; (94) the N tie rule: within 0.02 of the best Spearman, the N
nearest 20; (95) the prospective comparison is on ranks and names, since the October extraction re-extracts every
entity under regenerated instructions and the two spaces are not aligned; (96) seed-queue entries are not scored;
(97) K_95 of the pool is 170, not the workstream plan's 37 (which was the 60-axis Gram matrix's), and
`persona.PLAN12_K = 37` is left as M2 recorded it; (98) the duplicate and novel thresholds are the plan's defaults
until gate 1; (99) decision 1 taken as (a) and decision 2 as (b) if unanswered.  Anything that would edit a trait
file, the queue, a `novelty` block, a review log, a recorded M3 or harness output, `load_persona_space`, spend over a
command's budget, or change a frozen signature stops and asks.

## Measured figures (read-only, 2026-10-13)

Measured with throwaway scripts in the session scratchpad over `persona.load_persona_space()` (the cached pool),
the corpus files, the embedding cache, the registry snapshot and the overlap test's records; the first `fit` run
must reproduce the hard ones (§ 8).

**The pool.**  582 vectors (302 traits, 280 roles; `default` excluded), shape `(8, 64, 5120)` bf16 per file, type
`pos_3`; the shear is buildable (`shear_applied` true).  574 have a current file: 276 traits by stem and 19 through
`renamed_from`, 278 roles by stem and 1 through `renamed_from`; 8 orphans (§ 1).  Entities with a file and no
vector: **637 traits, 61 roles**.  Spectrum of the centred, sheared pool: the top 12 eigenvalues carry 10.5, 8.2,
7.0, 6.1, 5.0, 3.8, 3.4, 3.1, 2.4, 2.1, 1.9, 1.8% of the variance; K for 50 / 80 / 90 / 95 / 99% = **10 / 45 / 96 /
170 / 373**; log-log slope −1.11 over k = 1-64, −1.33 over 5-99; λ1/λ12 = 5.8, λ1/λ32 = 19.  [Leave-one-out](./glossary.md#loo)
actual residual (traits, median): N = 12 0.450, 16 0.394, 20 0.359, 24 0.326, 28 0.297, 32 0.276, 48 0.215 (roles
0.529 at 12, 0.341 at 32); the trait ranking by residual at N = 12 against N = 32 has Spearman 0.84, at 20 against
32 0.93, so the choice of N re-orders moderately.  [Nearest-neighbour](./glossary.md#nearest-neighbour) cosine
(actual, centred, sheared): traits median 0.72, roles 0.67; all trait-trait cosines median 0.01 (p10 −0.20, p90
0.33).

**Pairs and duplicates.**  59 recorded clean pairs have both vectors: pole-pole cosine median −0.037, IQR
−0.155..0.170, 59% negative, 2% above 0.5; the partner is among a pole's five nearest for 3% of poles and among the
twenty nearest for 3%; its cosine sits at percentile 0.41 among the pole's cosines to every trait (IQR 0.17..0.72).
Along a pair's own axis the two poles sit at ±14 against a standard deviation of 4.9 for the other traits (2.9 sd).
Named: [sardonic](../../data/traits/instructions/sardonic.json) / [sarcastic](../../data/traits/instructions/sarcastic.json)
0.875, [compassionate](../../data/traits/instructions/compassionate.json) /
[empathetic](../../data/traits/instructions/empathetic.json) 0.769,
[nationalist](../../data/traits/instructions/nationalist.json) / [patriotic](../../data/traits/instructions/patriotic.json)
0.713; [honest](../../data/traits/instructions/honest.json) / [dishonest](../../data/traits/instructions/dishonest.json)
−0.167, [optimistic](../../data/traits/instructions/optimistic.json) /
[pessimistic](../../data/traits/instructions/pessimistic.json) −0.037,
[introverted](../../data/traits/instructions/introverted.json) /
[extroverted](../../data/traits/instructions/extroverted.json) 0.033.  The workstream plan's named test pairs
([cautious](../../data/traits/instructions/cautious.json) / [risk-averse](../../data/traits/instructions/risk_averse.json) /
[bold](../../data/traits/instructions/bold.json), [calibrated](../../data/traits/instructions/calibrated.json) /
[overconfident](../../data/traits/instructions/overconfident.json)) cannot be run: risk_averse, bold, overconfident,
reckless and timid have no vector yet; they go into the prospective comparison's `named_pairs`.

**The regression** (574 rows, 471 arrangement groups, 5 grouped folds; unit-norm `label: description` `w20`
embeddings plus a role column; ridge; the PC basis for per-PC R² is the whole pool's, the residual basis the
fold's).  Alpha 0.3: held-out **median cosine 0.729, top-1 recovery 76%, top-5 97%**; per-PC R² 0.83, 0.78, 0.75,
0.75, 0.81, 0.71, 0.63, 0.66 (PC1-8), mean 0.53 over 9-24, 0.32 over 25-48 (0.17 over 49-64 at alpha 1); residual
Spearman predicted against actual, all rows: **N = 12 0.61, 16 0.62, 20 0.64, 24 0.62, 28 0.62, 32 0.63** (traits
only, alpha 1: 0.56-0.59); predicted `residual_24` median 0.18 against actual 0.36.  Alpha curve (cosine / top-1 /
best residual Spearman): 0.01 0.676 / 0.70 / 0.61; 0.03 0.690 / 0.72 / 0.63; 0.1 0.710 / 0.75 / 0.64; 0.3 0.729 /
0.76 / 0.64; 1 0.734 / 0.73 / 0.59; 3 0.711 / 0.63 / 0.50.  Traits-only fit (295 rows, alpha 0.3): cosine 0.726,
top-1 65%, top-5 92%, Spearman 0.52.  kNN (weighted mean of the k nearest training vectors by embedding cosine):
k = 1 0.566, 3 0.652, 5 0.679, 10 0.689.  **Gloss-side domain shift**: 277 traits have both a vector and an
[M1 gloss](./glossary.md#m1-gloss) of their label (the `existing` stratum of
[m1_validation_r2](../../data/candidates/filter/m1_validation_r2/results.jsonl), 630 glossed); predicting them from
`label: M1 gloss` instead of `label: description` lowers the held-out cosine from 0.752 to 0.695, so a candidate
(gloss-only by nature) lands about as well as a trait described by a gloss, and the thresholds are read with that
in mind.

**The registry** ([registry.snapshot.jsonl.gz](../../data/candidates/registry.snapshot.jsonl.gz), 9,941 keys):
verdict `trait` 6,735 (every one with a gloss; gloss median 25 words, p90 30), `tagged` 1,871, `reject` 1,323; M3
on the trait rows: `new` 3,834, `covered` 2,864, `grey` 1, undecided 36; distinct trait rows by generator: censuses
5,139, base_model 1,355, wn_clusters 578, ipip 490, alignment_sweep 455, antonym_check 374, states_pass 372, roget
349, m1_validation 108, manual 5; holding lists: states 1,212, physical 277, roles 211, states_released 171,
nationalities 36.

**The overlap test** ([overlap_arms_3](../../data/candidates/overlap_test/overlap_arms_3/pairs.json)): 409 pairs,
280 with both vectors; mean persona cosine by rubric-A answer 0 → 0.22, 1 → 0.44, 2 → 0.61, 3 → 0.82, 4 → 0.87,
opposite → 0.03; Spearman of the readings with the persona cosine 0.56-0.76 by model and rubric
([readout](./m3_overlap_test_readout.md) § "Agreement with persona space").

**Cache and prices.**  The OpenAI tag of the [embedding cache](../../data/candidates/cache/embeddings/manifest.json)
holds 29,917 texts; `w20` texts cached for 932 of 932 traits and 339 of 340 roles (the 340th is `default`);
`text-embedding-3-large` at $0.13 per MTok input ([judge_pricing.py](../../assistant_axis/judge_pricing.py)).

## Inconsistencies between the workstream plan and the repository, resolved

1. **Counts.**  "303 traits + 281 roles" are the file counts with `default`; the pool is 302 + 280, of which 574
   have a current file.  "87 traits and 56 roles have files but no vector" was true in September; today **637 and
   61** (the corpus grew to 932 trait files).  The Status section's "143 pending entities" is 698.  Resolved in § 1.
2. **"37 PCs carry 95% of variance."**  That is the 60-axis Gram matrix of May 2026
   ([TRAITS_ADDED.md](../../data/traits/instructions/TRAITS_ADDED.md) § "dimensionality-yield"); on the entity pool
   K_95 = 170 (K_50 = 10), as [pilot_m2_readout.md](./pilot_m2_readout.md) already noted.  `persona.PLAN12_K = 37`
   and M2's task (c) inherit the figure; left as recorded (QUESTIONS 97).  N is Roger's 12-32 and does not depend on
   K_95.
3. **"Antonyms land (at least partially) antipodal, so pair completions and duplicates are told apart by sign."**
   Not in this space: pole-pole cosine median −0.04, indistinguishable from an unrelated trait (§ "Measured
   figures").  The signed cosine stays as Roger's secondary score and tells duplicate from not-duplicate; the
   pair-axis position is added; antonymy stays M3's relation call's (§ 1).  (The readout's "opposite" mean of 0.03
   against 0.22 for reading 0 is on text-nearest pairs, which bias reading 0 upward.)
4. **Candidates: "[seed_queue.json](../../data/seed_queue.json) (972 entries ...) plus whatever the generators produce."**  The candidates
   are the registry's 6,735 trait rows (every generator); the queue is out of scope (QUESTIONS 96).
5. **Step 1, "keep K = 20-40 PCs, store the PCA basis"; step 6(b), "the top-20 PC subspace of the axis Gram
   matrix".**  Superseded by Roger's consequences paragraph: the full vector is predicted, and the subspace is the
   entity pool's top N (the basis M2 and [persona.py](../../assistant_axis/gapgen/persona.py) already use), N swept.
6. **Step 3, "ridge ... and, as a second model, PLS; compare both with kNN."**  kNN measured and beaten; PLS not
   built (QUESTIONS 92).
7. **Step 7, "Spearman between the two novelty ranks over the queue."**  M3 has no novelty rank: it is
   retrieve-then-judge with a decision.  The comparison is the AUC of the persona nearest-cosine for `covered`
   against `new`, the share of M3's covering trait among the persona-nearest, and the three disagreement kinds of
   § 6.
8. **"Local fallback via `transformers` would need an embedding model download (sentence-transformers not
   installed)."**  The platform has `LocalEmbedder` arms (gemma, bge) in the in-tree cache, inactive by Roger's M2
   decision; this plan uses the live OpenAI model only.
9. **§ 6, "the 143 pending entities ... compare predicted versus actual positions."**  Positions cannot be compared
   across the May and October spaces (every entity is re-extracted under regenerated instructions); ranks and
   nearest names are (QUESTIONS 95).
10. **Status, "the persona-space cosine is logged beside every overlap reading ... which is the data this plan's
    regression would train on."**  Those are actual-actual cosines of trait pairs; the regression trains on
    (embedding, vector) pairs.  The readings are the duplicate-threshold check (§ 1).
11. **§ 2, "Fitting: scikit-learn 1.8, torch 2.10."**  Verified: scikit-learn 1.8.0, scipy 1.17.0, torch 2.10.0 in
    the project environment.
12. **§ 1, "the 584 extracted vectors."**  582 without `default`; 574 trainable.

## Rendered prompt: the overlap call on a disagreement pair (decision 2b; M3's pinned rubric A, no new text)

The system turn is the pinned text of [overlap_concept.md](./rubrics/overlap_concept.md) exactly as M3 and the
recovery harness send it (a cached system block; Sonnet 5.5 first, Opus 5.5 under the rule; `max_tokens` 2048; no
temperature).  The user turn is M3's one-pair JSON with the **candidate as the target** (its label and M1 gloss)
and the **persona-nearest corpus trait as the other**.  The payload is a real IPIP row of the registry,
`achievement_driven#1` (M3: `new`, cut-off 3, listed first [persevering](../../data/traits/instructions/persevering.json)
at cosine 0.38); the persona-nearest shown, [ambitious](../../data/traits/instructions/ambitious.json), is an
illustrative pairing until the batch runs.  Labels go through `prompt_label` (unchanged here).

```
[system]
You are given one JSON object: a persona trait, the target ("target"), and one other persona trait ("other"), each with a one-sentence description. Say how similar the other trait's concept is to the target's: are they the same concept, or different concepts?

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers:
- 4: the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- 3: the same concept, differing only in scope, degree or emphasis. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further.
- 2: overlapping concepts. They share a core, but neither implies the other: a persona can have either without the other, as a studious person need not be bookish and a bookish one need not be studious; each adds something the other lacks.
- 1: related but distinct concepts: neighbours, not the same concept. For example, tetchy and sullen: both are bad-tempered, but quick irritation is a different thing from silent resentment.
- 0: different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "opposite": the other trait is the reverse of the target, the same quality at the other end. For example, cheery and morose.
- "unsure": you cannot tell from the two descriptions.

Give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"reason": "<one short sentence>", "similarity": 0|1|2|3|4|"opposite"|"unsure"}

[user]
{"target": {"label": "achievement-driven", "description": "This means pursuing set goals with steady determination, measuring one's days by what gets accomplished and treating each success as a step toward the next target."},
 "other": {"label": "ambitious", "description": "This means wanting to rise in status, setting goals well above where one stands, measuring every year by how far one has climbed, and never content to stay put."}}
```

A plausible answer (illustrative, not a recorded one): `{"reason": "Both are goal-chasing, but ambitious is about
rising in status and achievement-driven about getting things done, so each adds something the other lacks.",
"similarity": 2}`: below the row's cut-off of 3, so the persona flag would stand as "duplicate-like by enactment, not
by concept", which is exactly the kind of row Roger wants to see.  Estimate: about 670 pairs at plan 13's measured
match-call rate of $0.0024 a pair (Sonnet first, the Opus re-read included) ≈ $1.6; if the Opus share runs at the
full-scan estimate's `OPUS_SHARE_FULL_SCAN` (0.40 of pairs, [novelty_runner.py](../../assistant_axis/gapgen/novelty_runner.py))
rather than the harness's, about $2.5; cap $5.  No rubric is added or changed, so
[rubric_pins.py](../../data_analysis/gap_generation/rubric_pins.py) `check` stays green.

## Interface requests (written, not implemented here)

1. **Plan 13's dashboard** ([coding_plan_13_generator_testing.md](./coding_plan_13_generator_testing.md) § 6, the
   generator row; fields are added, never renamed): a `persona` sub-object per generator read from the blocks,
   `{"scored": n, "duplicate_like": n, "novel_like": n, "dup_vs_new": n, "novel_vs_covered": n,
   "mean_residual_pct": x, "batch_id": "..."}`, and `n/a` where no batch covers the generator.  Yes, the scorer's
   output belongs on the dashboard: a generator whose kept terms are mostly duplicates by enactment is one whose
   review-minutes buy less than its M3 figures say, and `novel_like` per review-minute is the persona-space version
   of the stop rule's numerator.  Plan 13's owner decides when; the block is enough to compute it.
2. **The review graph** ([review_graph.py](../../assistant_axis/gapgen/review_graph.py) `Node`): three optional
   fields on candidate nodes, `persona_nearest`, `persona_flag`, `persona_residual_pct`, read from the block when
   present, so the review app can show "persona space: nearest X (0.71), duplicate-like" beside M3's reading.  No
   edge is added from them.
3. **The registry**: `BLOCKS` gains `"persona"` (decision 1a; done in task 1 of this plan with the platform
   owner's knowledge).
4. **M3**: nothing now.  A later rule ("a `new` row whose persona reading at the persona-nearest trait reaches the
   cut-off is covered") would be an M3 change for Roger to decide on the full batch's readings.

## Cost (estimates; the rates are the platform's measured ones)

| step | calls | estimate |
|---|---|---|
| fit, calibrate, report, prospective predict, compare, apply (every corpus text cached) | none | **$0** |
| score, one run (IPIP g600, 490 texts × about 40 tokens) | 2-3 embedding calls | ≈ $0.003 |
| score, all 6,735 trait rows (about 270k tokens at $0.13 per MTok) | about 27 embedding calls | ≈ $0.035 |
| judge-disagreements, decision 2b (at most 10% of scored rows, about 670 pairs × $0.0024) | ≈ 670 + Opus share | ≈ $1.6-2.5, cap $5 |
| **total** | | **under $3**, live; nothing near the $20 line |

Roger's time: 20 minutes on gate 1 (the fit report), 30 minutes on gate 2 (the 30 + 30 and the disagreements of one
run), 30 minutes on the full batch's disagreement list; about 1.5 hours in all.

## Variant B, optional TODO (not planned; Roger, 2026-10-13: "keep the ideas")

Same-model proxy: one Qwen3-32B forward pass per candidate over a system prompt built from its gloss in the
pipeline's instruction form, reading the residual stream at the canonical cell (slot 6, layer 25, the chat-template
header layout of the model-families rule), then a ridge map from that prompt activation to the response-averaged
`pos_3` vector, fitted on the 574 entities whose both sides exist.  Same residual stream, so far less domain shift
than text embeddings; costs the 32B on RunPod (a few GPU-minutes per thousand candidates plus setup) and would be
worth it only if variant A's recovery were poor.  Measured today it is not (top-5 97%); the trigger to revisit is a
prospective comparison (§ 7) whose rank Spearman falls well below the held-out 0.6, or a wish to score the tail
PCs (25-48, R² 0.32) better.  Hooks this plan leaves for it: `fit.features` takes any (n, d) matrix, `Pool` is
independent of where the features come from, and `calibration.json` records which feature source a fit used.

## Frozen interface (for plan 13's dashboard, the review graph and a later M3 rule)

`from assistant_axis.gapgen.persona_space import PERSONA_DIR, PERSONA_BLOCK_VERSION, load_pool, Pool, load_fit,
Fit, predict_texts, score_vectors, PersonaScore, persona_block, Calibration`: `load_fit(fit_id) -> Fit(model,
calibration, pool)`; `predict_texts(fit, texts, kinds) -> (n, 5120) float32` (embedding through the platform cache,
charged to a given usage); `score_vectors(P, cands, pool, calibration, Ns=) -> list[PersonaScore]`; the § 6
`persona` block (`version` 1) with `residual`, `residual_pct`, `residual_z`, `nn`, `nearest`, `pair_axis`, `flag`,
`disagreement`, `reading`, `fit_id`, `config_version`, `batch_id`, `at`; `flag` and `disagreement` vocabularies as
in § 6.  Fields are added, never renamed, without a version bump; a change to the space (cell, shear, mean) or to
the embedding model is a new `config_version` and a new fit id, never a silent refit.  `load_persona_space` in
[persona.py](../../assistant_axis/gapgen/persona.py) is not this plan's to change.
