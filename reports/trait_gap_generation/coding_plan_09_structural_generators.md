# Coding plan: workstream 9, structural generators (generator id `structural`)

Written 2026-10-12 (Fable) in the [PLAN_FORMAT.md](./PLAN_FORMAT.md) shape from
[09_structural_generators.md](./09_structural_generators.md) with Roger's § 9 answers of 2026-10-12
(decisions) and the greenlight of the same day (the workstream file's header and the
[README](./README.md) still say "not yet greenlit"; the main session updates them), against the
"Interface as built" section of [coding_plan_platform.md](./coding_plan_platform.md).  Two generators in one
package: **A**, five classical trait schemes hand-typed and modernised by Haiku 5.5; **B**, five structural
operators (opposite, excess, deficiency, retarget, remode) applied to each of the corpus's 932 trait files.
Both emit structural metadata (a *role* in a structure and its *siblings*) beside the label.  The platform's
M1 (the trait-hood filter) and M3 (the novelty scorer) do the filtering and scoring.  Terms: the
[glossary](./glossary.md).  Roger's review comments go into this file.

## Open decisions (Roger's, at plan review; labelled OPEN, not decided)

1. **OPEN: the size of the B wave.**  § 5 of the workstream plan proposes sizing the first B wave by
   review hours, as [plan 04](./coding_plan_04_masked_lm.md) is sized (about two hours at the measured ~150
   terms an hour, so **about 300 M3-kept terms**), rather than submitting the whole corpus's output.  The
   operator calls themselves run on all 932 traits whatever is decided (about $0.37; the recovery checks of
   § 8 need all of them); the decision is what is **submitted** to M1 and M3 and reviewed.
   - *Whole corpus*: ~2,200 distinct labels submitted, downstream ≈ $37 live / **≈ $18.5 batched** (§ 10),
     and 360-730 novel candidates, **2.5-5 hours** of review.  Every sibling is scored, so triples are judged
     whole and the queue hold-out recall (§ 8) is measured through M3, not only by string.
   - *Review-hour wave*: `submit --kept-target 300` (the plan-04 selector), ≈ 600-700 rows submitted at the
     assumed kept share 0.5, downstream ≈ $10 live / $5 batched, about two hours of review; the rest waits for
     a second wave on Roger's word.  Ranking rule (§ 7): sources first (a label several traits reach is the
     better candidate), then `opposite` items of `non-X` and singleton traits (a pair completion is worth more
     than two unpaired points, the pairing premium of the trait-pairs rule), then excess and deficiency,
     then retarget and remode; siblings of a selected item travel with it so a triple is reviewed together.
   - **Recommendation: the review-hour wave**, with the pilot's measured kept share replacing the 0.5
     assumption before the cut, and the hold-out recall reported by string over all 932 traits' output (free)
     beside the M3 figure on the wave.
2. **OPEN: the reference set of the queue hold-out** (§ 8, test 3).  The workstream plan's set is the **96
   queued-but-unfiled labels from taxonomy scans and audits**: 84 `backlog` entries and 12 `paired` entries
   whose stem has no file (bland, cultural_relativist, disciplined, exclusive, indulgent, rule_bending,
   tough, deterministic, libertarian, financially_adventurous, job_hopper, variety_seeking; all counted
   2026-10-12 from [seed_queue.json](../../data/seed_queue.json)).  The 35 `candidate` entries promoted from
   the census review on 2026-10-11 are left out because a generator made them.  The alternative is all 131
   live unfiled trait entries (the 96 plus the 35).  **Recommendation: the 96**, with recall on the 35
   printed as a second line, never in the denominator (a generator's words recovering another generator's
   words measures the generators' overlap, not the corpus's gaps).

If either is unanswered when Opus reaches the step, it proceeds under the recommendation and records that in
[QUESTIONS.md](./QUESTIONS.md) (§ 12).

## 1. Decisions already made

| decision | reason | source |
|---|---|---|
| **Phrase-only labels are accepted** ("harsh toward self", "kind to animals" is the precedent); `has_common_word` is recorded on every item as information and is never a filter. | Roger, 2026-10-12 | plan 09 § 9.1 |
| **Retarget gets three principal targets, the user, the operator and the developer, for alignment-region traits only**; their non-null outputs are listed apart for the AI-identity sub-family sign-off ([QUESTIONS 67 and 78](./QUESTIONS.md)) before promotion.  "Alignment region" is the `alignment_ai_agent` region of [corpus_regions.json](../../data/candidates/corpus_regions.json): **10 traits** on 2026-10-12 ([absentee](../../data/traits/instructions/absentee.json), [hands-on](../../data/traits/instructions/hands_on.json), [helpful](../../data/traits/instructions/helpful.json), [inefficient](../../data/traits/instructions/inefficient.json), [obedient](../../data/traits/instructions/obedient.json), [proactive](../../data/traits/instructions/proactive.json), [rebellious](../../data/traits/instructions/rebellious.json), [scheming](../../data/traits/instructions/scheming.json), [self-starting](../../data/traits/instructions/self_starting.json), [unhelpful](../../data/traits/instructions/unhelpful.json)), not the 183 traits at alignment score 2-3 (pre-registered, § 12). | Roger, 2026-10-12: "yes, for the alignment region" | plan 09 § 9.2, § 3.4 |
| **`position` annotations go to a side table** under `data/candidates/structural/`, never into a trait file's `arrangement`; **TODO (Roger): review promotion of the side table into `arrangement` once the pairing review is done.** | Roger, 2026-10-12 | plan 09 § 9.3, § 7 |
| **One model, Haiku 5.5** (`claude-haiku-5-5`, $0.10 / $0.50 per MTok in [judge_pricing.py](../../assistant_axis/judge_pricing.py)); a second model only if the stability test (§ 8, test 6) fails, and then Roger's call.  Haiku 5.5 refuses a `temperature` ([llm.py](../../assistant_axis/gapgen/llm.py) leaves it out), so the stability test is the measure of its sampling noise. | Roger, 2026-10-12 | plan 09 § 9.4, § 6.5-6 |
| **The VIA over/under pass is in**, gated: the 24 strengths with their overuse and underuse names are typed from Niemiec (2019) and **verified against the paper before the A run** (§ 9 task 2); the survey itself is copyrighted and not used. | Roger, 2026-10-12 | plan 09 § 9.5, § 2 |
| Classical tables **hand-typed**, not recited by a model (faithful; 30 minutes of Roger's time once). | plan 09 § 8, § 5 | plan 09 |
| **B's call shape is per trait** (one call, all five operators, reasoning first).  The per-operator batched call and the pair-level call of plan 09 § 8 are variants for later: the pilot's `position` answers on recorded pairs decide whether the pair-level call is worth building (§ 10). | the § 6 thresholds are written for per-trait output; one shape to pilot | this plan (pre-registered, § 12) |
| **The `opposite` operator runs blind**: the call sees the label, the description and the arrangement *kind*, never the recorded `negative_label` or the arrangement's members.  The mismatch signal of plan 09 § 3.4 and the pair-recovery test of § 6.1 only mean something blind. | plan 09 § 3.4 lists `negative_label` among the inputs and in the same sentence calls disagreement a free signal; the two cannot both hold | this plan (pre-registered) |
| **Role and siblings ride the generator's own table and `source_ref`, with `partner_hint` the registry-facing field.**  `Candidate` is frozen (no `role`); the scorer as built already treats an `opposed` relation as a pair completion (`pair_completion_for`, [novelty.py](../../assistant_axis/gapgen/novelty.py)) and `promote` reads `partner_hint`.  No scorer change for the first wave; plan 09 § 7's "the scorer must consume `role`" becomes an interface request (§ 12). | the frozen interface; "Interface as built" | platform plan |
| **Glosses do not repeat the label**: "This means ..." of at most 25 words, straight to the behaviour (plan 09 § 3.2's "This means being X: ..." predates Roger's 2026-09-27 rule and [QUESTIONS 41](./QUESTIONS.md)). | the description-wording rule | trait-pairs rule |
| **Every item is kept, none dropped by its tags**: a label that is a corpus trait, a `negative_label`, a queue entry or a stem another generator registered is submitted (an existing trait reached as another's `excess` is arrangement evidence; Roger, 2026-10-10: "let the pipeline do its job"); the downstream estimate counts only rows the registry has not yet filtered. | plan 09 § 3.6; [coding_plan_01_censuses.md](./coding_plan_01_censuses.md) last section | |
| Worked examples in the prompts are **hygiene-checked** words outside the corpus, the queue and the validation file ([prompt_hygiene.py](../../assistant_axis/gapgen/prompt_hygiene.py)).  Plan 09's illustrations (cautious, honest, harsh, arrogant, reckless, self-critical) are all corpus traits and would seed the pair-recovery test with its own answers. | the hygiene rule; cheats-on-tests | platform |
| Prompts show labels through [`prompt_labels.prompt_label`](../../assistant_axis/gapgen/prompt_labels.py); runs record `label_form`.  Rubric texts live under [rubrics/](./rubrics/) and are pinned: the two new names (`structural_operators`, `structural_modernise`) join `PINNED_NAMES` in [split_rubrics.py](../../assistant_axis/gapgen/split_rubrics.py) and get their first row in [versions.json](./rubrics/versions.json) through `rubric_pins.py bump NAME --why ... --version 1`; `rubric_pins.py check` ([rubric_pins.py](../../data_analysis/gap_generation/rubric_pins.py)) then refuses a text changed without a bump. | judge display form; a version names one text | judging rule |
| Generation waves run **M1 + M3 only**; grouping (R1) once at the end over every batch. | Roger, 2026-10-10 | [coding_plan_review.md](./coding_plan_review.md) § 10 |
| Live transport for the generator's own calls (under $1); downstream M1/M3 transport by the wave's estimate (open decision 1): under about $20 live, over it the Batches API with Roger's go. | the batch-or-real-time rule | [CLAUDE.md](../../CLAUDE.md) |
| Counts as of 2026-10-12, used throughout: **932 trait files**, **1,047 queue entries (969 trait entries, 963 distinct trait labels)**, **297 recorded pairs**, 8 triangles, the moral-circle sequence at **13 members** (plan 09 § 6.2's "16" is stale: three left it on 2026-10-10), 315 `non-X` placeholders. | counted, not copied | this plan |

## 2. Out of scope

- The role generators (parked, [README](./README.md) § "Parked: generators aimed at roles"); roles are not operated on.
- The VIA survey, its items and scoring (copyrighted); only the 72 names, verified.
- Any edit to `data/traits/**`, `data/roles/**`, the TO_ADD files, [seed_queue.json](../../data/seed_queue.json), or any trait file's `arrangement` field; promotion of the side table into `arrangement` (the TODO above, Roger's).
- Promotion of candidates (`gap_registry.py promote`, Roger's decision); R1 / the review app.
- Anything the platform owns: rubrics of M1/M3, cut-offs, [metric_config.json](../../data/candidates/metric_config.json); a `role` field on `Candidate` or in the scorer (interface request only).
- The per-operator batched call and the pair-level call (variants, § 10); a second model.
- Scorer verification spend (M1/M3 belong to the platform's budget lines, printed by `submit`).

## 3. Rule files to Read first

Open with the **Read tool** before touching code:
[provenance.md](../../.claude/rules/provenance.md) (`usage.json` beside every batched LLM output, `MultiModelUsage`; `json_metadata` envelopes; UTC timestamps; snapshot before overwrite),
[entity-naming.md](../../.claude/rules/entity-naming.md) (file-name stems via `normalize_to_file_name` for every key; display form only in prompts and readouts; US English),
[trait-pairs.md](../../.claude/rules/trait-pairs.md) (what a trait, a pair, a triangle, a sequence and the seed queue are; the description-wording rule; the `arrangement` field this generator reads and never writes),
[judging.md](../../.claude/rules/judging.md) (reason before verdict; `warn_if_low_parse_rate` at 99%; version pins; the rendered-prompt rule),
[CLAUDE.md](../../CLAUDE.md) (file-access boundary, the $20 confirmation rule, **tests are mandatory**, hotlinks).  No PNGs are planned (the readouts are tables); if one is added, Read the plotting rule first.

**File-access boundary, restated for every Opus task prompt**: read and write only inside the repository
worktree, the agent's scratchpad and `$TMPDIR`; never list, read or stat anything else under the home
directory, not `~/.cache`, not even to see whether something is downloaded.  This workstream downloads
nothing; the only outside text is the VIA names, verified by Roger or on his word (§ 9 task 2).

## 4. Existing code to reuse

- Registry API from `assistant_axis.gapgen`: `Candidate` (with `partner_hint`), `start_run`, `submit_candidates`, `SubmitReport`, `RunContext` ([registry.py](../../assistant_axis/gapgen/registry.py), [runs.py](../../assistant_axis/gapgen/runs.py): `record_candidates` before the append, `finish()` writes `run.json` and `usage.json`); `paths.run_dir`, `check_id`, `CORPUS_REGIONS_PATH`, `SEED_QUEUE_PATH`.
- [cost.py](../../assistant_axis/gapgen/cost.py): `Estimate`, `estimate_calls_usd`, `confirm_or_abort`, `GuardedUsage`, `HARD_LINE_USD`; [llm.py](../../assistant_axis/gapgen/llm.py): `call_anthropic_json` (system block, retries, charges every response, no temperature for Haiku 5.5); the call loop of [alignment_sweep/extract.py](../../assistant_axis/gapgen/generators/alignment_sweep/extract.py) (`run_stage`, `append_response`, `reusable_answers`: answers recorded before they are parsed, resumed by prompt hash).
- [censuses/corpus.py](../../assistant_axis/gapgen/generators/censuses/corpus.py) (`corpus_trait_stems`, `corpus_renamed_from`, `queue_trait_stems`), [glosshint.py](../../assistant_axis/gapgen/generators/censuses/glosshint.py) (OEWN sense, for the `has_common_word` check), [base_model/parse.py](../../assistant_axis/gapgen/generators/base_model/parse.py) `normalize_form` (nominal to adjective only when OEWN has the adjective).
- The submit recipe of [masked_lm/submit.py](../../assistant_axis/gapgen/generators/masked_lm/submit.py): measured rates (`M1_USD_PER_WORD = 0.0072`, `M3_USD_PER_PASSED_WORD = 0.011`, pass rate 0.88 flagged unmeasured, `BATCH_FACTOR = 0.5`, `RATES_SOURCE`), `select_wave(kept_target, kept_share)`, the review-load guard, `followup_commands`, the `_budget` first-of-kind cap.
- [embed.py](../../assistant_axis/gapgen/embed.py) (`make_embedder`, `EmbeddingCache`, `HashEmbedder` for tests) for the gloss-cosine recovery figures; [prompt_labels.py](../../assistant_axis/gapgen/prompt_labels.py); [prompt_hygiene.py](../../assistant_axis/gapgen/prompt_hygiene.py); [judge.py](../../assistant_axis/judge.py) `warn_if_low_parse_rate`; [entity_id.py](../../assistant_axis/entity_id.py) `normalize_to_file_name`, `resolve_renamed_stem`; [arrangements.py](../../assistant_axis/arrangements.py) (reading pairs, triangles and the sequence); [atomic_io.py](../../assistant_axis/atomic_io.py); [provenance.py](../../assistant_axis/provenance.py) `json_metadata`.
- Test style: [test_gapgen_censuses_submit.py](../../assistant_axis/tests/test_gapgen_censuses_submit.py) (tmp registry through the real API), the alignment sweep's fake Anthropic client in [test_gapgen_alignment_sweep_extract.py](../../assistant_axis/tests/test_gapgen_alignment_sweep_extract.py).  **No new dependencies.**

## 5. File layout

```
assistant_axis/gapgen/generators/structural/
  __init__.py     GENERATOR = "structural"; STRUCTURAL_DIR = DATA_CANDIDATES / "structural"; CLASSICAL_DIR =
                  STRUCTURAL_DIR / "classical"; CLASSICAL_MODERN_PATH; OPERATOR_TABLE_PATH; POSITION_TABLE_PATH;
                  MISMATCH_PATH; EVALUATION_PATH; re-exports load_operator_table, load_position_table (§ Frozen)
  classical.py    SCHEMES = ("aristotle", "theophrastus", "sins_virtues", "via", "murray"); ROLES_BY_SCHEME
                  (aristotle: deficiency|mean|excess; theophrastus: vice; sins_virtues: sin|virtue; via:
                  strength|underuse|overuse; murray: need_high|need_low); ClassicalRow (§ 6);
                  load_classical(scheme) / load_all(); validate(rows) -> list[str]  (sibling ids resolve, roles
                  legal, one mean per Aristotelian triple, every VIA row verified_by or the scheme is refused)
  modernise.py    render_modernise_user(rows, *, per_call=20) -> str; parse_modernise(text) -> list[ModernItem];
                  run_modernise(rows, *, client, model, usage, out_path, resume) -> list[ModernRow]
                  (1-3 modern labels, gloss <= 25 words, polysemy flag, reasoning first)
  operators.py    OPERATORS = ("opposite", "excess", "deficiency", "retarget", "remode"); TARGETS = ("self",
                  "intimates", "strangers", "authority", "animals", "ideas"); PRINCIPAL_TARGETS = ("the_user",
                  "the_operator", "the_developer"); MODES = ("attitude", "habit", "speech"); ALIGNMENT_REGION =
                  "alignment_ai_agent"; TraitInput(stem, label, description, arrangement_kind, region,
                  principal_targets: bool); build_inputs(stems, *, data_dir, regions_path) -> list[TraitInput]
                  (never the negative_label, never the members); render_operator_user(ti) -> str;
                  parse_operator_reply(text, *, principal) -> (OperatorReply | None, problem); validate_item
                  (rejects over-/under-/too-/non-X labels, > 4 words, non-ASCII); run_operators(inputs, *,
                  client, model, usage, out_path, resume) -> list[OperatorReply]
  prompts.py      OPERATOR_SYSTEM / MODERNISE_SYSTEM read from rubrics/structural_operators.md and
                  rubrics/structural_modernise.md (fenced block, pinned); EXAMPLE_WORDS (hygiene-checked)
  postprocess.py  stem_of(label) (normalize_candidate + normalize_form); tag_membership(stem, *, corpus_stems,
                  renamed, negative_label_stems, queue) -> Tags(exists, queued, queue_status, is_negative_label,
                  registered); merge_items(replies, modern_rows) -> list[MergedRow]  (by stem; sources list,
                  n_sources, roles, siblings); rank(rows) (§ 7); write_operator_table / load_operator_table
  sidetable.py    position_rows(replies, *, corpus) -> list[PositionRow]; compare_negative_label(reply, recorded)
                  -> "match" | "mismatch" | "placeholder" | "none_recorded"; write_position_table;
                  render_mismatches(rows) -> markdown
  evaluate.py     pair_recovery(table, pairs, *, embed=None) (hide each pole; stem match and gloss cosine at
                  0.7/0.8/0.9); structure_recovery(table, triangles, sequence); queue_holdout(table, holdout,
                  excluded) (recall by operator); null_rates(replies) (per operator and target; principal apart);
                  stability_jaccard(run_a, run_b) (per trait, per operator; median and distribution);
                  parse_rate(replies)
  submit.py       estimate_downstream_usd(n, *, transport, pass_rate=0.88); select_all / select_wave (plan 04's
                  selector, siblings travel with the selected item); to_candidates(rows, run_id) (§ 6);
                  run_submit(run_id, *, table, kept_target|all, kept_share, budget_usd, confirm_expensive,
                  confirmed_by, transport, dry_run); followup_commands
  report.py       render_report(evaluation, run) -> markdown; roger_sample(rows, n=50, seed=0);
                  ai_identity_list(rows) (the principal-target items, for QUESTIONS 67/78 sign-off)
data_analysis/gap_generation/structural_generator.py
                  classical | modernise | operators | null-rate | stability | postprocess | side-table | submit | report
reports/trait_gap_generation/rubrics/{structural_operators.md, structural_modernise.md}   pinned texts
data/candidates/structural/classical/{aristotle,theophrastus,sins_virtues,via,murray}.json   hand-typed, tracked
data/candidates/structural/{classical_modern.jsonl, operator_table.jsonl, position_table.jsonl,
                  negative_label_mismatches.md, evaluation.json}   tracked (the table ~1-2 MB)
data/candidates/runs/structural/<run_id>/{responses.jsonl, candidates.jsonl, keys.txt, submit_report.json,
                  run.json, usage.json, report.md, roger_sample.md, ai_identity_subfamily.md}
assistant_axis/tests/test_gapgen_structural_{classical,prompts,operators,postprocess,sidetable,evaluate,submit,acceptance}.py
data_analysis/tests/test_gap_generation_structural_cli.py
```

Every paid answer is appended to the run's `responses.jsonl` before it is parsed (the Roget precedent,
[QUESTIONS 37](./QUESTIONS.md): paid answers are records and are tracked), keyed by trait stem, prompt sha256
and model, so a rerun of the same run id reuses them (`--resume`) and a changed prompt does not.

## 6. Data schemas

**Classical row** ([classical/aristotle.json](../../data/candidates/structural/classical/aristotle.json), not
written yet; one file per scheme, a list of rows; `sibling_ids` name rows of the same file):

```json
{"schema_version": 1, "id": "aristotle:courage:excess", "scheme": "aristotle", "item": "rashness",
 "role": "excess", "gloss": "running at danger with no sense of the odds", "sibling_ids":
 ["aristotle:courage:deficiency", "aristotle:courage:mean"], "source": "NE II.7 (Ross)", "verified_by": null}
```

`verified_by` is required non-null on every `via` row before `modernise --scheme via` or any A run will read
it (the gate); on the other schemes it is informational.  The modernised row
([classical_modern.jsonl](../../data/candidates/structural/classical_modern.jsonl), not written yet) adds
`labels` (1-3), `gloss_modern`, `polysemy`, `reasoning`, `model`, `prompt_sha256`, `run_id`.

**Operator response** (one JSON object per call, reasoning first, then `position`, `opposite`, `excess`,
`deficiency`, `retarget`, `remode`; each item `{label, gloss, has_common_word, polysemy}` or `null`; the
principal-target keys are present only for alignment-region traits).  Illustrative, with a made-up trait:

```json
{"reasoning": "A tightfisted person keeps money back as a settled habit; the opposite spends freely; ...",
 "position": "deficiency",
 "opposite": {"label": "open-handed", "gloss": "This means giving money and help freely, without keeping score.",
              "has_common_word": true, "polysemy": false},
 "excess": null,
 "deficiency": {"label": "wasteful", "gloss": "This means spending past one's means with no thought for tomorrow.",
                "has_common_word": true, "polysemy": false},
 "retarget": {"self": {"label": "self-denying", "gloss": "...", "has_common_word": true, "polysemy": false},
              "intimates": null, "strangers": null, "authority": null, "animals": null, "ideas": null},
 "remode": {"attitude": null, "habit": null,
            "speech": {"label": "haggling", "gloss": "...", "has_common_word": true, "polysemy": true}}}
```

(`position` is the trait as described: `deficiency`, `mean`, `excess` or `not_scalar`.  `excess` and
`deficiency` ask for the vice of too much and too little of the trait; for a deficiency-position trait the
model may return `null` for `deficiency`, which is the expected answer, not an error.)

**Operator table row** ([operator_table.jsonl](../../data/candidates/structural/operator_table.jsonl), not
written yet; one per distinct stem; deterministic from `responses.jsonl` and `classical_modern.jsonl`):

```json
{"schema_version": 1, "surface": "wasteful", "stem": "wasteful", "label": "wasteful",
 "gloss": "This means spending past one's means with no thought for tomorrow.",
 "sources": [{"generator_part": "operators", "source_stem": "tightfisted", "operator": "deficiency", "run_id":
   "2026-10-14-b1"}, {"generator_part": "classical", "source_id": "aristotle:liberality:excess", "role": "excess"}],
 "n_sources": 2, "roles": ["deficiency", "excess"], "siblings": ["tightfisted", "open_handed", "liberal"],
 "has_common_word": true, "polysemy": false, "principal_target": false,
 "exists": true, "queued": false, "queue_status": null, "is_negative_label": false, "registered": true,
 "rank": 211}
```

Rules: `stem = normalize_to_file_name(label)` after `normalize_form`; `exists` is a corpus stem or a
`renamed_from`; `is_negative_label` a corpus file's `negative_label` stem; `queued` any of the 1,047 entries
by stem or normalised label, `queue_status` its status; `registered` a key already in the registry log.
**None of the five tags affects submission** (mutation test, § 8).

**Candidate emitted** (one per source, the registry merges them into one row with several `sources[]`
entries): `Candidate(surface="wasteful", generator="structural", run_id="2026-10-14-b1", rank=211,
score=2.0, gloss_hint="This means spending past one's means ...", sense_id=1,
source_ref="structural:op:deficiency:tightfisted", partner_hint=None)`.  `score` is `n_sources` (a quality
signal, **not** a familiarity: `structural` is not added to `FAMILIARITY_GENERATORS`, guard test as
[QUESTIONS 58](./QUESTIONS.md)); `source_ref` is `structural:op:<operator>[:<target>|:<mode>]:<source stem>` or
`structural:classical:<row id>`, so the role is readable from it; `partner_hint` is the source trait's label
for `opposite` items, the sibling vice's label for `excess` / `deficiency` pairs and for classical
deficiency / excess, sin / virtue, overuse / underuse and high / low rows, and `None` for retarget, remode
and means.

**Side-table row** ([position_table.jsonl](../../data/candidates/structural/position_table.jsonl), not written
yet; one per corpus trait operated on):

```json
{"schema_version": 1, "stem": "honest", "label": "honest", "position": "mean",
 "recorded_negative_label": "dishonest", "model_opposite": "deceitful", "negative_label_check": "mismatch",
 "reasoning": "...", "run_id": "2026-10-14-b1", "model": "claude-haiku-5-5", "prompt_sha256": "…",
 "at": "2026-10-14T10:00:00+00:00"}
```

`negative_label_check`: `match` (the recorded label's stem equals the model's opposite, after
`normalize_form`), `mismatch` (a real-word label recorded, another word returned; these rows are rendered to
[negative_label_mismatches.md](../../data/candidates/structural/negative_label_mismatches.md), not written yet,
with both words and the model's reasoning, for the pairing review), `placeholder` (`non-X` recorded),
`none_recorded`.  The side table is tracked, rebuilt deterministically from `responses.jsonl`, snapshotted
`.bak.<UTC>` on change, and **never written into a trait file** (the TODO in § 1).

**Evaluation payload** ([evaluation.json](../../data/candidates/structural/evaluation.json), not written yet,
enveloped; figures illustrative): `{"pair_recovery": {"n_pairs": 297, "recall_stem": 0.71, "recall_cos_0.8":
0.84}, "structure_recovery": {"triangles": {"n": 8, "corners_recovered": 5}, "sequence": {"n": 13,
"recovered": 6}}, "queue_holdout": {"n": 96, "recall_stem": 0.19, "by_operator": {"opposite": 0.11, ...},
"excluded_35_recall": 0.3}, "null_rates": {"retarget": 0.22, "remode": 0.31, "principal": 0.5}, "stability":
{"n_traits": 30, "jaccard_median": 0.6, "below_0.5": 9}, "parse_rate": 0.997}`.

## 7. CLI

[structural_generator.py](../../data_analysis/gap_generation/structural_generator.py) (not written yet).  Common
flags `--data-dir`, `--registry`, `--candidates-dir`, `--regions`, `--dry-run`; every paid command takes
`--budget-usd` (a hard cap: an estimate over it is refused, `confirm_or_abort`), `--confirmed-by` (needed with
`--confirm-expensive` for anything over the $20 line; **not expected here**, every generator-side estimate is
under $1) and `--allow-dirty` (refuses uncommitted platform code otherwise), prints its estimate as
`n_calls x (in, out) tokens at model rates = $X` before sending, charges every answer to a `GuardedUsage`, and
writes `usage.json` beside its output in a `finally` block.  Dry runs print the estimate, the row counts and
one **rendered prompt** per variant (a singleton, a pair pole, an alignment-region trait, a classical batch:
the working-style rule) and write nothing.

- `classical [--scheme S ...]`: loads and validates the hand-typed tables, prints counts per scheme and role and
  the VIA verification state; refuses `via` while any row has `verified_by: null`.  $0.
- `modernise --run-id R [--scheme S ...] [--per-call 20] [--budget-usd 0.5] [--resume]`: Haiku 5.5, about 11
  calls for the ~205 rows (≈ $0.02); writes `classical_modern.jsonl` and the run's `responses.jsonl`, `run.json`,
  `usage.json`.  Refuses `via` as `classical` does.
- `operators --run-id R (--all | --traits STEM ... | --sample N --seed S) [--budget-usd 3] [--resume]`: one call
  per trait (≈ $0.0004; 932 calls ≈ $0.37, so the default cap is the first-of-kind `ceil(1.5 x 0.37 + 2)`);
  principal targets added for alignment-region traits; answers appended to `responses.jsonl`, parse rate
  printed through `warn_if_low_parse_rate`.
- `null-rate --run-id R [--n 20 --seed 0] [--budget-usd 0.5]`: `operators --sample 20` plus the null-rate readout
  (§ 10): per operator and target the non-null share, the band 5-40% for retarget and remode, the principal
  targets apart; the trait list is stratified by region and arrangement kind.  ≈ $0.01.
- `stability --run-id R --against R2 [--n 30 --seed 1] [--budget-usd 0.5]`: runs the same 30 traits as a second
  run id and prints the per-trait label-set Jaccard (the size of the intersection of two label sets over the
  size of their union) per operator and overall, median and the count below 0.5.  ≈ $0.02.
- `postprocess [--run-id R ...]`: builds `operator_table.jsonl` from every named run's responses and
  `classical_modern.jsonl` (stems, tags, merge, rank), then `evaluation.json` (the free checks of § 8; gloss
  cosines through the embedding cache, `--embedder openai|hash`, pennies).  Deterministic; rerun byte-identical;
  `.bak.<UTC>` on change.
- `side-table [--run-id R ...]`: `position_table.jsonl` and `negative_label_mismatches.md` from the responses.  $0.
- `submit --run-id R (--all | --kept-target 300 [--kept-share 0.5]) [--transport live|batches] [--budget-usd 5]
  [--confirm-expensive --confirmed-by WHO] [--dry-run]`: selects table rows (open decision 1), prints strata
  (operator x exists/queued/new, principal-target count), the **downstream estimate** at the measured census
  rates (M1 $0.0072 a word, M3 $0.011 a passed word at the assumed 0.88, batches x0.5; rows the registry has
  already filtered are counted out), gates with `confirm_or_abort`, writes `candidates.jsonl` **before**
  `submit_candidates`, then `keys.txt`, `submit_report.json`, `run.json`, `usage.json`, and prints the follow-ups:
  `gap_registry.py submit --from ...` (main checkout), `traithood_filter.py --batch-id R_structural --run
  structural/R --pipeline split --transport T --budget-usd <1.5 x est + 2>`, `novelty_score.py score ...`,
  `recovery_test.py --generator structural --run-id R`, `report --run-id R`.
- `report --run-id R`: `report.md` (§ 11's figures from the registry blocks, `evaluation.json` and the M1/M3
  batch directories' `usage.json` summed per model), `roger_sample.md` (50 rows decided `new` or `grey`, seeded,
  for the manual precision check) and `ai_identity_subfamily.md` (every principal-target item with its M1 verdict
  and M3 decision, for the QUESTIONS 67/78 sign-off).  $0.

## 8. Acceptance tests, written first

No test calls an API or reads the network: a `FakeAnthropic` client returns scripted JSON (one script per
rendered prompt hash, so a changed prompt fails loudly), embeddings use `HashEmbedder`, the registry is a tmp
path through the real frozen API.  The recovery and hold-out numbers are **report-and-decide** (plan 09 § 6
sets no gate but "expect > 80%" for pair recovery); parse rate, the null-rate band, stability, cost caps,
`usage.json` presence and the untouched corpus are hard.

- `classical`: every scheme loads; roles legal per scheme; Aristotelian triples have exactly one mean and two
  vices; every `sibling_id` resolves; `via` is refused while any row is unverified and accepted when all carry
  `verified_by`; counts: 12-14 Aristotle triples, 30 Theophrastus, 7 + 7 + 7 sins and virtues, 24 x 3 VIA, 20
  Murray x 2.
- `prompts`: the two rubric texts are pinned (`split_rubrics.mismatches()` empty, so `rubric_pins.py check` passes; `GENERATOR_FILES` in [split_rubrics.py](../../assistant_axis/gapgen/split_rubrics.py) names both files); reasoning is the first key
  in the schema and the examples; **no example word is a corpus stem, a queue label or a validation-file word**
  (`prompt_hygiene`); the rendered user turn carries the label in judge display form, the description and the
  arrangement kind, and **never the `negative_label` or any arrangement member** (assert on a watched
  `TraitInput`); principal-target keys appear only when `principal_targets` is true.
- `operators`: parse of a scripted reply; `null` accepted everywhere but `reasoning` and `position`; `validate_item`
  rejects over-/under-/too-/non-X labels, five-word labels and non-ASCII; a reply naming a principal target for a
  non-alignment trait is dropped with a problem recorded (**the guard**: principal targets only for
  alignment-region traits, checked on the way in and on the way out); failed calls counted, retried once, left
  unparsed, never guessed; every response is charged (fake usage) including unparseable ones; `--resume` sends
  nothing for an answered (stem, prompt sha256, model).
- `postprocess`: `stem_of` on phrases ("harsh toward self" -> `harsh_toward_self`), nominals (`-ness` only with the
  fake lexicon's adjective); tags truth table against a fixture corpus, `renamed_from`, negative labels and a
  fixture queue with every status; merge keeps every source and counts `n_sources`; rank order (§ 7); **mutation
  test**: flipping every tag changes no selection and no candidate; rerun byte-identical.
- `sidetable`: `compare_negative_label` truth table (`match`, `mismatch`, `placeholder`, `none_recorded`); the
  mismatch readout lists both words and the reasoning; **the side table writes under `data/candidates/structural/`
  only** (a watched tmp `data/traits` is untouched); snapshot on change.
- `evaluate`: `pair_recovery` on a planted fixture (hidden pole recovered by stem; by cosine with the hash
  embedder; `renamed_from` resolved); `structure_recovery` finds a planted triangle corner and a planted sequence
  neighbour; `queue_holdout` recall by operator, the excluded 35 reported apart and never in the denominator;
  `null_rates` per operator and target with the principal targets apart; `stability_jaccard` on planted runs
  (identical -> 1.0, disjoint -> 0.0, the median and the below-0.5 count); `parse_rate`.
- `submit` (tmp registry, real API): one candidate per source with the crossed `partner_hint`s for opposite and
  for vice pairs, `None` for retarget/remode/means; `score == n_sources`; `source_ref` in the documented form
  and parseable back to a role; `candidates.jsonl` written before the registry append; resubmit is a no-op;
  **cost guard**: 10,000 fake rows -> estimate > $20 -> refused without `--confirm-expensive --confirmed-by`;
  2,000 rows -> over the default budget refused, accepted with a larger `--budget-usd`; already-filtered rows
  counted out of the estimate; `--kept-target` cut and siblings travelling with a selected item; dry run leaves
  the registry byte-identical and writes no run dir; follow-ups name the run id, batch id, `--pipeline split`
  and the transport; `structural` absent from `FAMILIARITY_GENERATORS` (guard, with the trap in the comment).
- CLI: every subcommand's `--dry-run` exits 0 and writes nothing; paid commands refuse over budget; `modernise
  --scheme via` refuses while unverified; `report` renders a fixture run with the three files.
- **Acceptance on recorded outputs** (`test_gapgen_structural_acceptance.py`, skips while absent): parse rate
  >= 0.99 in every run's responses (hard); the null-rate run's retarget and remode non-null shares inside 5-40%
  (hard for the pilot gate; outside it the run is a prompt-revision round, § 10); stability median Jaccard >= 0.5
  on 30 traits (hard; failing it is Roger's model decision); `usage.json` beside every run with nonzero cost;
  `evaluation.json` carries pair recovery (reported against the > 80% expectation), structure recovery, the
  hold-out recall on the 96 by operator (the 35 apart), and the principal-target count equals the items of
  alignment-region traits; `position_table.jsonl` has a row for every trait operated on; the package imports no
  `openai` beyond the embedding cache.
- **Manual check, listed as such**: the 50-row `roger_sample.md` judged trait / not-trait / duplicate by Roger,
  target >= 70% trait-and-new (plan 09 § 6.4); recorded in the acceptance report, not asserted by a test.

Commands that must pass at the end of every task:

```
uv run pytest assistant_axis/tests/test_gapgen_structural_*.py data_analysis/tests/test_gap_generation_structural_cli.py -q
uv run pytest -q                                                  # whole suite, unchanged
uv run python data_analysis/gap_generation/rubric_pins.py check
uv run python data_analysis/check_arrangements.py --quiet
uv run python tools/sync_entity_lists.py --check
git status --porcelain data/traits data/roles data/seed_queue.json   # must be empty
```

## 9. Ordered task checklist

Prerequisite: a worktree off `anthropic-vllm-uv` (`git merge --ff-only anthropic-vllm-uv` first), `.env`
copied, `data/external/` symlinked from the main checkout.  The boundary paragraph of § 3 goes into every task
prompt verbatim.  Each task ends with the § 8 commands.

1. Skeleton, `classical.py`, and the **hand-typed tables** for Aristotle (NE II.7, Ross: courage, temperance,
   liberality, magnificence, magnanimity, proper ambition, good temper, truthfulness, wit, friendliness, modesty,
   righteous indignation; EE II.3 adds its two or three), Theophrastus (Jebb's 30 titles, one-line glosses),
   the sins and virtues (the seven, the seven heavenly, the four cardinal and three theological) and Murray's 20
   needs (each with a high and a low pole).  Test: classical.  Paste the tables' counts into the task report.
2. **The VIA gate.**  Type the 24 strengths with the overuse and underuse names from Niemiec (2019; the
   over/under/optimal-use paper, Counselling Psychology Quarterly: citation from memory, to be confirmed at
   verification) with `verified_by: null`, then **stop**: Roger verifies the 72 names against the paper (or
   gives his word for an agent to fetch it) and `verified_by` is filled in; nothing reads the VIA rows before
   that.  Test: the gate.
3. `prompts.py` and the two rubric files, pinned; `modernise.py`; CLI `classical`, `modernise`.  Test: prompts.
   Paste one rendered modernise call (20 rows) into the task report.
4. `operators.py`; CLI `operators` with `--dry-run`.  Test: operators.  Paste the four rendered variants (§ 7)
   into the task report; Roger reads them before any call is made.
5. **Null-rate pilot** (§ 10, first gate): `null-rate --run-id <date>-nullrate` on 20 traits (≈ $0.01).  Inside
   the band: on.  Outside it: one bounded prompt revision (text only, version bumped), re-pilot, both readouts
   to Roger.
6. `postprocess.py`, `sidetable.py`, `evaluate.py`; CLI `postprocess`, `side-table`.  Test: postprocess,
   sidetable, evaluate.  Add glossary entries (Aristotelian mean, position, the five operators, label-set
   Jaccard, null rate) to [glossary.md](./glossary.md).
7. **Stability run** (§ 10, second gate): `stability` on 30 traits, two runs (≈ $0.02).  Median Jaccard >= 0.5:
   on.  Below: stop, numbers to Roger (n = 2 samples by design, or a second model, his call).
8. `submit.py`, `report.py`; CLI `submit`, `report`.  Test: submit, CLI.
9. **A run**: `modernise` on every verified scheme (≈ $0.02), `postprocess`, then `submit --all` of the classical
   rows together with the pilot's operator rows as run `<date>-pilot` (≈ 350 rows, ≈ $6 live downstream), M1 +
   M3 run by Fable, `report`: the yield-per-dollar readout (§ 10).  Roger's decision on open decision 1 if
   still open, and his 30 minutes on the classical candidates.
10. **B, full operator pass**: `operators --all` (932 calls, ≈ $0.37), `postprocess`, `side-table`,
    `evaluation.json` with pair recovery, structure recovery and the hold-out recall (all free).
11. **First B wave**: `submit --kept-target 300` (or `--all`, per the decision), transport per the estimate
    (over $20 batched with Roger's go), M1 + M3, `report`, the 50-row sample to Roger, the AI-identity list for
    sign-off.  Acceptance test on the recorded outputs.
12. Acceptance report (§ 11); propose the [data/README.md](../../data/README.md) paragraph for
    `candidates/structural/` in the report (do not edit it; the platform owns that file); the TODO on the side
    table's promotion restated in the report for the pairing review.

## 10. Pilot

**Null-rate pilot** (task 5, 20 traits stratified by region and arrangement kind, ≈ $0.01).  Readout: per
operator the non-null share; for retarget per target and for remode per mode, with the principal targets (only
the alignment-region traits in the sample, at least two forced in) on their own line.  **Gate**: retarget and
remode non-null **above 40% means hallucinated forms, below 5% means laziness** (plan 09 § 6.5); either way
one prompt revision and a re-pilot.  Also printed: the `position` answers of the sample's pair poles (do the
two poles of a pair land at deficiency and excess, or mean and vice?), which decides whether the pair-level
call variant is worth a later task; the over-/under-/too-/non-X rejection count; parse rate.

**Stability** (task 7, 30 traits twice, ≈ $0.02): median label-set Jaccard >= 0.5, the distribution and the
per-operator figures.  This pilot and the null rate together are the tested decision that Haiku 5.5 is the
model (Roger, 2026-10-12).

**Yield-per-dollar readout** (task 9, on the pilot submission; the figures that size the wave): per operator
and for the classical rows, (i) the non-null share, (ii) the M1 trait share, (iii) the **novel share after the
scorer** (M3 `new` or `grey`), (iv) the kept share (kept rows per submitted row, replacing the 0.5 assumption
in `select_wave`), (v) the cost (generator calls from `usage.json`, M1 and M3 from their batch directories)
and (vi) `useful_per_dollar` (rows decided new or pair-completion per dollar); plus the exists / queued /
registered shares, the mismatch count, the projected whole-corpus and 300-kept figures.  **Roger decides**:
(a) the wave's size and transport (open decision 1), (b) the classical candidates (30 minutes), (c) whether the
principal-target items go on as traits (QUESTIONS 67/78 sign-off), (d) the pair-level call variant, worth it or
not.

## 11. Report at the end

One page at [acceptance_09_structural_generators.md](./acceptance_09_structural_generators.md) (not written
yet): what was built against § 5; deviations with reasons; the § 8 commands verbatim with pass counts; the
classical tables' counts and the VIA verification record; the four rendered prompt variants; the null-rate
and stability readouts and the prompt revision if one happened; the pilot's yield-per-dollar readout and
Roger's decisions; pair recovery (against the > 80% expectation), structure recovery (8 triangles, the
13-member sequence), the hold-out recall on the 96 by operator with the 35 apart; the first wave's counts,
M1/M3 fractions, the 50-row sample's verdicts (the manual precision check) and the AI-identity list; cost per
model from every `usage.json` (generator, M1, M3); the side table's counts (positions, mismatches) and the
promotion TODO; open QUESTIONS entries; the proposed `data/README.md` paragraph.

## 12. Escalation

Opus retries a failing step once with a changed approach, then Fable (diff review, architecture, stubborn
failures), then Roger through [QUESTIONS.md](./QUESTIONS.md) in its format (`N. [09] question. Assumption
proceeded under: ... Status: open`, numbering continuing from the file's last entry, 90 on 2026-10-12),
proceeding under the assumption unless the answer would make the work useless.  Pre-registered entries Opus
copies in at the start: (1) the `opposite` call is blind to the recorded `negative_label` and to arrangement
members; (2) "alignment region" is the `alignment_ai_agent` region of `corpus_regions.json` (10 traits), not
alignment score >= 2 (183); (3) role and siblings live in the generator's table and `source_ref`,
`partner_hint` is the registry-facing field, and no scorer change is made (interface request: the review graph
reading `load_operator_table`'s siblings so a triple is shown together); (4) glosses are "This means ..."
without the label, as [QUESTIONS 41](./QUESTIONS.md) settled for Roget; (5) B's call shape is per trait;
the pair-level and per-operator batched calls are later variants; (6) VIA rows are unreadable until
`verified_by` is set; (7) corpus, negative-label, queue and registered matches are submitted, with filtered
rows counted out of the estimate; (8) `score` is `n_sources`, not a familiarity; (9) the moral-circle
sequence has 13 members today, not 16; (10) the two OPEN decisions above, if unanswered, proceed under their
recommendations.  Anything that would edit a trait file, the queue or an `arrangement`, spend over a command's
budget, fetch the VIA paper without Roger's word, add a second model, or change a frozen signature stops
and asks.

## Cost (estimates; re-measured at the pilot)

Haiku 5.5 at $0.10 / $0.50 per MTok.  The ~900-token system prompt is below the cache minimum, so no caching
is assumed (plan 09 § 3.5's "900 cached" does not change the figure).

| step | calls | tokens (in, out) | estimate |
|---|---|---|---|
| A, modernise (~205 rows, 20 a call) | ~11 | (1,500, 2,500) | ≈ $0.02 |
| B, null-rate pilot | 20 | (1,200, 550) | ≈ $0.01 |
| B, stability (30 x 2) | 60 | (1,200, 550) | ≈ $0.02 |
| B, full pass (932 traits; the 10 alignment-region traits +200 out) | 932 | (1,200, 550) | **≈ $0.37** |
| gloss embeddings for the recovery checks (~2,500 glosses) | cached | ~100k tokens at $0.13/MTok | ≈ $0.01 |
| **generator total, one pass of everything** | | | **≈ $0.45** |

Downstream, at the measured platform rates (M1 $0.0072 a word, M3 $0.011 a passed word at 0.88 passed,
unmeasured for this generator; batches x0.5): the pilot submission (~350 rows) ≈ $6 live; a 300-kept wave
(~600-700 rows) ≈ $10 live / $5 batched; the whole corpus's ~2,200 distinct labels ≈ $37 live / **≈ $18.5
batched**, over the $20 line live and so batched with Roger's go.  Yield (plan 09 § 4, scaled from the 385-file
figures, to be re-measured): A ~250 labels, 40-60 novel; B ~5,100 raw -> ~2,200 distinct -> ~1,450 not
exists/queued -> **360-730 novel**.  Review at ~150 terms an hour: 2.5-5 hours for all of B, about two for a
300-kept wave, 30 minutes for the classical rows.

## Frozen interface (for the pairing review, the tangle pass and plan 11)

`from assistant_axis.gapgen.generators.structural import load_operator_table, OPERATOR_TABLE_PATH,
load_position_table, POSITION_TABLE_PATH`: the § 6 table rows (`schema_version` 1) with `roles`,
`siblings`, `sources`, `n_sources` and the five membership tags for every distinct label, and the `position`
and `negative_label_check` of every corpus trait operated on.  Fields are added, never renamed, without a schema
bump.  In the registry, a structural candidate's role is readable from its `source_ref`
(`structural:op:<operator>[:<target>|:<mode>]:<source stem>` or `structural:classical:<row id>`), and its
partner from `partner_hint`.
