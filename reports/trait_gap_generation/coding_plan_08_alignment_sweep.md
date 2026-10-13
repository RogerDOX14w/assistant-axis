# Coding plan: workstream 8, alignment sweep (generator id `alignment_sweep`)

Written 2026-10-10 (Fable) in the [PLAN_FORMAT.md](./PLAN_FORMAT.md) shape from
[08_alignment_sweep.md](./08_alignment_sweep.md) as Roger greenlit it on 2026-10-10 (his inline
edits and the notes dated 2026-10-10 in that file are decisions), against the **"Interface as
built"** section of [coding_plan_platform.md](./coding_plan_platform.md) — never its superseded
"Frozen interface" scorer names.  Variant A (document-driven) first; variant B (incident-driven,
two sources) after Roger reads A's readout.  Terms: the [glossary](./glossary.md).  Roger's review
comments go into this file.

## 1. Decisions already made

| decision | reason | source |
|---|---|---|
| Variant A first: specs and taxonomies in, dispositions out.  Variant B afterward on the two incident sources only (the Krakovna list and Anthropic's agentic-misalignment examples), gated on Roger reading A's readout, with the recovery comparison the plan asks for. | cheap and bounded first; B is vivider but heavier review | plan 08 §8 |
| A `mechanism` item (reward hacking, mesa-optimization) is **rewritten as one or more dispositions** that would produce the behavior in a persona, or dropped; `enactability = none` items are dropped (and counted). | Roger's 2026-10-10 edit to step 3 | plan 08 §3.3 |
| Step-2 labels are **ordinary English a mid-size model would recognize — never a term of art or a coinage**; multiword labels fine (≤ 4 words); words whose common sense differs from the intended sense are flagged (polysemy). | Roger's edit to step 2 | plan 08 §3.2 |
| The illustrative table in plan 08 is **illustration, not a shortlist**: the sweep re-derives labels; nothing seeds the extraction prompt from that table or from our corpus. | Roger, 2026-10-10 | plan 08 §3, cheats-on-tests note |
| **The readout shows every survivor's alignment score and cut-off.**  Near alignment (score 2-3) M3's cut-off is 4, so a scope-narrowing (cheating narrowed to evaluations) survives beside a trait that looks like its duplicate; Roger reads the score, not the overlap reading, when a survivor looks wrong. | Roger's note under the table | plan 08 §3.5; platform M3 decision 18 |
| Output shape: `label + gloss + partner_label + partner_gloss` becomes **two `Candidate` rows, one per pole, each carrying `gloss_hint` (its gloss) and `partner_hint` (the other pole's surface)** — so M1 judges the intended sense ("intended sense" in the filter prompt, interface resolution 1) and `gap_registry.py promote` sets `partner` on both queue entries when both are promoted (resolution 1 of plan 02's requests). | the as-built registry API | platform § Interface as built |
| The platform pipeline as built does the filtering and scoring: submit, then `traithood_filter.py --pipeline split`, then `novelty_score.py score`.  **Words that are already corpus trait names stay in**; no selector drops them. | Roger, 2026-10-10 ("let the pipeline do its job") | [coding_plan_01_censuses.md](./coding_plan_01_censuses.md), 2026-10-10 note |
| **No per-wave R1.**  Generator waves run M1 and M3 only; grouping happens in the one end-of-waves `review_graph.py build --from-batches ...` run.  Step 7's "table of ~40" is this plan's readout (§6), not a review graph. | Roger, 2026-10-10 | [coding_plan_review.md](./coding_plan_review.md) §10 |
| Within-sweep dedup (step 4) by **gloss embeddings through the platform's cache** (`text-embedding-3-large`, [embed.py](../../assistant_axis/gapgen/embed.py)), threshold tuned on a 30-pair hand-labeled sample; identical surfaces merge free in the registry.  The plan's "local sentence-embedding model" predates M2's final settings, which dropped local models. | resolved contradiction (pre-registered) | plan 08 §3.4; platform "M2 final settings" 1 |
| Extraction and rewrite model: **`claude-sonnet-5-5`** (the platform's Sonnet).  The plan's "Sonnet 4.6" predates decision 17's model defaults. | resolved contradiction (pre-registered) | platform M3 decision 17 |
| The **persona-enactability gate gets a measured evaluation** (§8: a 30-item gold set, two readings, agreement and flip-rate targets) before its verdicts move anything; below target it is an advisory column only. | Roger's edit: "will likely need careful evaluation" | plan 08 §3.6 |
| **The gate is three fields, not one answer** ([enactability_gate.md](./rubrics/enactability_gate.md) draft 3, pinned version 3): (1) `where` it can be elicited — `chat` / `agentic` / `both` / `neither`, the one categorical field and the inheritor of draft 2's `none`; (2) `elicitation`, free text, one line (for `chat` the sort of question, for `agentic` the affordances or scenario) — draft 2's `scope_line` generalised to both settings; (3) `judge_needs`, free text, one line: whether a judge could read the trait off the output at face value or needs context or ground truth, and what.  Model **Opus 5.5**, **two readings on the gold items** (where agreement and the flip rate are measured) and **one on production rows**.  **Nothing gates on it**; agreement and the flip rate are kept for **field 1 only**, fields 2 and 3 get no metric by design.  Fields 1 and 3 feed the tags `needs_agentic_harness` and `judge_needs_baseline`, written by hand at promotion.  Draft 2's four answers map onto field 1 one-for-one, so [gate_gold_items.json](../../data/candidates/alignment_sweep/gate_gold_items.json) is unchanged (`gate.GOLD_EXPECTED_MAP` renames on read) and the blind relabelling of 2026-10-10 survives. | Roger, 2026-10-11 ("go straight to Opus; this is not a small-model or old-model question") | [QUESTIONS.md](./QUESTIONS.md) 75 |
| **A scope line that narrows the trait goes in the description at promotion; an elicitation hint does not.**  A narrowing changes what the trait is (as in [ruthless-while-playing](../../data/traits/instructions/ruthless_while_playing.json), whose description carries "in any game, bet, role-play, story, simulation or test" inline), so leaving it out would make the description contradict the label.  An elicitation hint is a fact about testing, and the description is what M3 reads for overlap, so a hint there would skew the novelty readings against corpus traits whose descriptions carry none.  It is **not** routed through `description_notes`, which nothing outside the gap tooling reads.  The hint lives in the gate's field 2 and in the readout; the plumbing is deferred (§9 task 14). | Roger, 2026-10-11 | [QUESTIONS.md](./QUESTIONS.md) 66 |
| **Four more readout sections**, all free and computed from files already on disk: the **shared-virtue fan list** after dedup (68); the **non-exact-stem dedup merges** with both glosses and the cosine (73); the **AI-identity and belief-state sub-families** listed separately for Roger's sign-off before promotion, since they would be the trait corpus's first AI-presupposing entries (67, 78); and the probe's above-floor share **split single word against phrase** (74). | Roger, 2026-10-11 | [QUESTIONS.md](./QUESTIONS.md) 67, 68, 73, 74, 78 |
| Label-known probe: `qwen/qwen3-32b` through OpenRouter **pinned to DeepInfra (United States), `allow_fallbacks: false`**, the `ALLOWED_PROVIDERS` pattern of [opening_form_experiment.py](../../data_analysis/opening_form_experiment.py); responses naming another host are discarded.  The plan's "local" Qwen probe has no local 32B to run on.  No `OPENROUTER_API_KEY`: the probe is skipped, the rank formula drops the factor, the readout says so. | hosted-models hard rule; resolved contradiction | CLAUDE.md; plan 08 §3.7 |
| **Live transport throughout**: every command's estimate is under $5 (§7 arithmetic), so under the batch-or-real-time rule nothing batches. | under ~$20: real time | CLAUDE.md |
| Every prompt shows labels through [`prompt_labels.prompt_label`](../../assistant_axis/gapgen/prompt_labels.py); runs record `label_form`. | judge display form | platform § Judge display form |
| Source versions are pinned: the Model Spec's repo commit, the constitution's capture date, each paper's version, in the sources manifest and in `source_ref`. | plan 08 §9 Q5, assumed yes (pre-registered) | plan 08 §9 |
| Gold set for the recovery test: the plan's ten alignment-region traits, with `rationalizing` mapped to [motivated-reasoning-prone](../../data/traits/instructions/motivated_reasoning_prone.json) (no `rationalizing` file exists). | resolved contradiction | plan 08 §6; corpus at 2026-10-10 |
| Code in a subpackage `assistant_axis/gapgen/generators/alignment_sweep/` (not yet written). | generator worktrees run in parallel | censuses plan §1 |

Plan 08 §9's questions 1-4 carry no inline answer; §12 pre-registers the assumptions.

**The four new sections, measured on the full run** (2026-10-11, computed from
[extraction.jsonl](../../data/candidates/runs/alignment_sweep/2026-10-10-full/extraction.jsonl),
[dedup_groups.json](../../data/candidates/runs/alignment_sweep/2026-10-10-full/dedup_groups.json) and
[submitted_items.json](../../data/candidates/runs/alignment_sweep/2026-10-10-full/submitted_items.json); no API call).
Two of the figures quoted in [QUESTIONS.md](./QUESTIONS.md) do not survive the arithmetic, and the code reports what
it measures:

| section | QUESTIONS says | measured | why they differ |
|---|---|---|---|
| dedup merges on the embedding (73) | about nine of 37 | **4** of 37 (33 exact-stem) | 28 *groups* carry the note "exact stem" and 37 - 28 = 9, but four of those groups have three or four members, so the exact-stem merges number 33 and only four rest on the embedding (`steering with opinions` / `pushes its own side` 0.863, `ignores authority levels` / `obeys whoever speaks last` 0.856, `flat refusal` / `bare refusal` 0.855, `holds firm lines` / `firm on minors` 0.818).  It strengthens the decision: the threshold has even less leverage than thought |
| shared-virtue fans (68) | 28 of 386 groups | **19** virtue fans (sizes 4, 3, 2 x 17), plus **12** on the vice side | every example named in the entry is in the virtue list (`even-handed` with four, `accepts legitimate oversight`, `curious about itself`, `owns its values`) except `treats teens like adults`, which the sweep extracted as a *vice* pole, so the 28 looks like the virtue and vice lists added together (31) or the 28 exact-stem groups.  "Two to four distinct vices" matches exactly |
| belief-state (78) | 6 pairs of 214 | 6 pairs, **11 submitted poles** of 386 | one pole (`owns its values`) represents a dedup group of two, so twelve extracted poles are eleven candidates |
| AI-identity word scan (67) | not quantified | **27** of 386 submitted rows | over-inclusive by design: the matched terms are printed, and about a third are incidental (`assistant` in "the user and assistant share an understanding").  Narrowed once already — "deployment", bare "weight" and bare "train" fired only incidentally and are out |

## 2. Out of scope

- Any edit to `data/traits/**`, `data/roles/**`, the TO_ADD files, [seed_queue.json](../../data/seed_queue.json); promotion is `gap_registry.py promote`, Roger's decision.
- R1 / R2 (the end-of-waves grouping run and the review app); anything the platform owns (rubrics, cut-offs, [metric_config.json](../../data/candidates/metric_config.json), the M3 escalation rule).
- Qwen definition probes on the RunPod; the Message Batches API (everything here is live).
- The AI Incident Database (variant B's heaviest source) and ELEPHANT beyond its taxonomy text.
- Downloading the Krakovna sheet into the repo (no license: read transiently, keep only derived items and quotes ≤ 25 words).
- Plan 13's estimators and dashboard.

## 3. Rule files to Read first

Open with the **Read tool** before touching code:
[provenance.md](../../.claude/rules/provenance.md) (usage.json on every batched call site; `json_metadata` envelopes; UTC timestamps),
[entity-naming.md](../../.claude/rules/entity-naming.md) (stems via `normalize_to_file_name`; US English; judge display form),
[trait-pairs.md](../../.claude/rules/trait-pairs.md) (what a trait, a pair and the seed queue are; the gloss form),
[judging.md](../../.claude/rules/judging.md) (reason-before-verdict, `warn_if_low_parse_rate`, rendered samples per the working-style rule),
[CLAUDE.md](../../CLAUDE.md) (file-access boundary, the $20 rule, tests mandatory, hotlinks, **hosted models: western hosts only**).
No PNGs, so no plotting rule.  The file-access boundary paragraph of [PLAN_FORMAT.md](./PLAN_FORMAT.md) goes verbatim into the Opus task prompt; downloads go only to `data/external/`.

## 4. Existing code to reuse

- Registry API from `assistant_axis.gapgen`: `Candidate` (with `partner_hint`), `start_run`, `submit_candidates`, `SubmitReport`, `RunContext` ([registry.py](../../assistant_axis/gapgen/registry.py), [runs.py](../../assistant_axis/gapgen/runs.py)).
- [cost.py](../../assistant_axis/gapgen/cost.py): `Estimate`, `estimate_calls_usd`, `confirm_or_abort`, `GuardedUsage`, `HARD_LINE_USD`; [llm.py](../../assistant_axis/gapgen/llm.py): `call_anthropic_json` (cached system, retries, charges every response).
- [embed.py](../../assistant_axis/gapgen/embed.py) and the embedding cache under `data/candidates/cache/embeddings/`; [prompt_labels.py](../../assistant_axis/gapgen/prompt_labels.py) `prompt_label`, `LABEL_FORM_KEY`.
- The submission recipe of [generators/censuses/submit.py](../../assistant_axis/gapgen/generators/censuses/submit.py): measured downstream rates (`M1_USD_PER_WORD = 0.0072`, `M3_USD_PER_PASSED_WORD = 0.011`, pass 0.88), `candidates.jsonl` written **before** `submit_candidates`, `followup_commands`, the `--confirm-expensive --confirmed-by` gate over `HARD_LINE_USD`.
- Rubric pinning: new rubric files under [rubrics/](./rubrics/), versions in [rubric_versions.py](../../assistant_axis/gapgen/rubric_versions.py), checked by [rubric_pins.py](../../data_analysis/gap_generation/rubric_pins.py).
- [judge_pricing.py](../../assistant_axis/judge_pricing.py) rates (Sonnet 5.5 $2/$10, Haiku 5.5 $0.10/$0.50, Opus 5.5 $4/$20, 3-large $0.13 per MTok; `qwen3-32b` $0.08/$0.28); [judge.py](../../assistant_axis/judge.py) `warn_if_low_parse_rate`; [entity_id.py](../../assistant_axis/entity_id.py) `normalize_to_file_name`; [atomic_io.py](../../assistant_axis/atomic_io.py).
- OpenRouter host pinning: `ALLOWED_PROVIDERS` in [opening_form_experiment.py](../../data_analysis/opening_form_experiment.py).
- The recovery harness: [recovery.py](../../assistant_axis/gapgen/recovery.py), [recovery_test.py](../../data_analysis/gap_generation/recovery_test.py), and `novelty_score.py score --hide` (see § Interface requests).
- Test style: [test_gapgen_censuses_submit.py](../../assistant_axis/tests/test_gapgen_censuses_submit.py).

## 5. File layout

```
assistant_axis/gapgen/generators/alignment_sweep/        (none of this exists yet)
  __init__.py    GENERATOR = "alignment_sweep"; SWEEP_DIR = DATA_CANDIDATES / "alignment_sweep"; EXTERNAL_DIR = DATA_EXTERNAL / "alignment_sweep"
  sources.py     Source(key, name, url, kind, license, license_url, license_verified_at, version_pin, read_only, optional, weight); SOURCES; SKIPPED
  fetch.py       fetch_all(*, fetcher, force, dry_run) -> FetchManifest (sha256, size, fetched_at, version_pin); write/load_manifest
  chunk.py       chunk_source(key, text) -> list[Chunk(chunk_id, source, heading, text, n_tokens_est)]   (headings for spec/constitution; rows for sheets/tables)
  extract.py     EXTRACT_RUBRIC (pinned), REWRITE_RUBRIC (pinned); run_extract(chunks, *, client, model, usage, limiter) -> list[Item]
                 run_rewrite(mechanism_items, ...) -> list[Item]   (0-2 dispositions per mechanism item)
                 label_ok(label) -> bool (≤ 4 words, ASCII, no underscore); quote_policy(source) -> max words
  dedupe.py      embed_glosses(items, cache, usage); dedup_groups(items, threshold) -> list[Group(rep, members, min_cos)]
                 rewrite_partner_hints(items, groups); tune_threshold(labeled_pairs) -> float
  submit.py      to_candidates(items, run_id) -> list[Candidate]; estimate_downstream_usd(n) (censuses' measured rates)
                 run_submit(run_id, *, items, budget_usd, confirm_expensive, confirmed_by, dry_run) -> SubmitSummary; followup_commands
  gate.py        GATE_RUBRIC (pinned); run_gate(rows, *, client, model, usage, n_readings=2) -> list[GateRow]
                 score_against_gold(rows, gold) -> GateEval(agreement, flip_rate, confusion_vs_m1)
  probe.py       ALLOWED_PROVIDERS = {"deepinfra": "United States"}; run_probe(labels, *, client, usage) -> {label: ProbeRow}
  report.py      rank(rows) -> ordered keys; render_readout(...) -> str; render_gold_recovery(...) -> str
data_analysis/gap_generation/alignment_sweep.py          fetch | chunk | extract | dedupe | submit | gate | probe | report   (not yet written)
reports/trait_gap_generation/rubrics/{alignment_extract.md, alignment_rewrite.md, enactability_gate.md}   (pinned; not yet written)
data/external/alignment_sweep/                           GITIGNORED (fetched texts, chunks.jsonl, FETCH_MANIFEST.json)
data/candidates/alignment_sweep/                         tracked: sources_manifest.json, gold_alignment_traits.json, gate_gold_items.json, dedup_labeled_pairs.json
data/candidates/runs/alignment_sweep/<run_id>/           tracked: candidates.jsonl, keys.txt, run.json, usage.json, extraction.jsonl, dedup_groups.json,
                                                         enactability.jsonl, probe.json, readout.md, gold_recovery.md
assistant_axis/tests/test_gapgen_alignment_sweep_{sources,chunk,extract,dedupe,submit,gate,probe,report}.py
data_analysis/tests/test_gap_generation_alignment_sweep_cli.py
```

Sources in `sources.py` (A): the OpenAI Model Spec (github.com/openai/model_spec, **CC0 1.0 Universal**, LICENSE read 2026-10-10), Anthropic's constitution (anthropic.com/constitution, **CC0 1.0**: "We're releasing Claude's constitution in full under a Creative Commons CC0 1.0 Deed", page read 2026-10-10; the preface and acknowledgements are not part of the constitution and are excluded), the Anthropic and OpenAI usage policies (proprietary; `read_only`, quotes ≤ 25 words), the failure-mode taxonomy texts of plan 08 §2 (arXiv / blog, text only), and the AI-safety glossaries (names only, dedup reference).  Variant B adds: the Krakovna specification-gaming master list (**no license stated** on the landing page, checked 2026-10-10; `read_only`, `optional`, fetched transiently from the published sheet's TSV export, never stored; its `pubhtml` page is drawn by script since about October 2026, so it holds no table: fixed 2026-10-13, 66c2ce5d) and the MACHIAVELLI annotation schema (**MIT, Copyright (c) 2022 Alex Pan**, LICENSE read 2026-10-10; `optional`).

## 6. Data schemas

> Every path in this plan under `data/candidates/alignment_sweep/`, `data/external/alignment_sweep/` and
> `reports/trait_gap_generation/rubrics/alignment_*` / `enactability_gate.md` is a **future output**: the
> file does not exist yet and is linked at the path where the task that makes it will write it.


**Extraction item** (`extraction.jsonl`, the sweep's own tracked record; one per emitted pole):

```json
{"schema_version": 1, "item_id": "ms-041a", "chunk_id": "modelspec:2026-08-18:dont-be-sycophantic", "source": "model_spec",
 "label": "cheats on tests", "stem": "cheats_on_tests",
 "gloss": "This means being happy to cheat on exams, tests and evaluations when a better score is within reach and detection seems unlikely.",
 "partner_label": "honest on tests", "partner_item_id": "ms-041b",
 "type": "behaviour", "enactability": "chat", "polysemy_flag": false, "polysemy_note": null,
 "source_quote": "Don't game evaluations ...", "rewritten_from": null, "rank": 41, "source_weight": 2}
```

`type` ∈ {behaviour, belief-state, mechanism}; `enactability` ∈ {chat, agentic-only, none}; `stem = normalize_to_file_name(label)`; `source_weight`: constitution safe-behaviors and Model Spec 2, taxonomies 1, glossaries 0.5 (plan 08 step 7).  `none` items and un-rewritten `mechanism` items stay in the file with `dropped_reason` set and are never submitted.  `source_quote` is capped at 25 words for `read_only` sources, full sentence otherwise.

**Dedup group** (`dedup_groups.json`, inside a `json_metadata` envelope): `{"rep": "ms-041a", "members": ["ms-041a", "con-112", "el-009"], "min_cos": 0.87, "note": "honesty restated"}` — one Candidate per group representative; every member's `item_id` survives in the file; a dropped pole's partner keeps a hint rewritten to the representative's label (`rewrite_partner_hints`).

**Candidate emitted** (`to_candidates`): `Candidate(surface="cheats on tests", generator="alignment_sweep", run_id="2026-10-12a", rank=41, score=None, gloss_hint=<gloss above>, partner_hint="honest on tests", sense_id=1, source_ref="model_spec:2026-08-18:dont-be-sycophantic")` — and the partner pole as its own Candidate with the hints crossed.  `sense_id` 2 only when the same surface is proposed in a second sense.

**Gate row** (`enactability.jsonl`, draft 3 of the rubric): `{"key": "cheats_on_tests#1", "system_prompt": "<two sentences>", "where": "chat", "readings": ["chat"], "flip": false, "elicitation": "Ask it something it would want to underperform on, framed as a test.", "judge_needs": "Needs the model's actual capability level on this task.", "m1_enactable_in_text": 2, "label_form": "judge-display-v1"}` — `where` is field 1 and the only scored one; `elicitation` and `judge_needs` are one free-text line each and are `null` only when `where` is `neither`.  The elicitation line is **not** a `description_notes` sentence and never enters the description (§1, QUESTIONS 66); a scope *narrowing* is the opposite case and does, as for the frame pair [ruthless-while-playing](../../data/traits/instructions/ruthless_while_playing.json) / [honorable-while-playing](../../data/traits/instructions/honorable_while_playing.json).  Draft 2's row had one `visibility` field (`chat` / `both` / `agentic-only` / `none`) and a `scope_line`; no run on disk uses that shape.

**Readout row** (`readout.md`, the "table of ~40"): `| rank | label (partner) | gloss | type | enactability | M1 verdict/tags | alignment score | cut-off | M3 decision | nearest reading (trait, sonnet/opus) | covered_by | label-known | source |` — **alignment score and cut-off on every row**, survivors first, the `covered` rows as a second table with the same columns (Roger's note: near alignment an apparent duplicate may be a kept scope-narrowing, and a cover at cut-off 4 means "either label could replace the other").

**Gold set** ([gold_alignment_traits.json](../../data/candidates/alignment_sweep/gold_alignment_traits.json), not yet written): the ten stems
[sycophantic](../../data/traits/instructions/sycophantic.json), [harmless](../../data/traits/instructions/harmless.json), [honest](../../data/traits/instructions/honest.json), [obedient](../../data/traits/instructions/obedient.json), [calibrated](../../data/traits/instructions/calibrated.json), [confabulatory](../../data/traits/instructions/confabulatory.json), [transparent](../../data/traits/instructions/transparent.json), [motivated-reasoning-prone](../../data/traits/instructions/motivated_reasoning_prone.json) (the plan's "rationalizing"), [ruthless-while-playing](../../data/traits/instructions/ruthless_while_playing.json), [ends-justify-means](../../data/traits/instructions/ends_justify_means.json), each with the note of what maps to it; arrangement partners hide with them (the harness's rule).

## 7. CLI

`data_analysis/gap_generation/alignment_sweep.py`, common flags `--registry`, `--data-dir`, `--dry-run` (prints plan, estimate and the first three rendered prompts; writes nothing, calls nothing), `--budget-usd` (hard cap; estimate over it refused), `--confirm-expensive --confirmed-by` (only over $20; nothing here should reach it).  Arithmetic at [judge_pricing.py](../../assistant_axis/judge_pricing.py) rates:

- `fetch [--only KEY] [--force]`: downloads variant A's sources into `data/external/alignment_sweep/` with sha256, size, version pin (Model Spec repo commit, constitution capture date) and the license line verbatim in [FETCH_MANIFEST.json](../../data/external/alignment_sweep/FETCH_MANIFEST.json) (gitignored, not yet written) and the tracked [sources_manifest.json](../../data/candidates/alignment_sweep/sources_manifest.json) (not yet written).  Krakovna is fetched only by `extract --variant B`, transiently.  $0.
- `chunk`: writes `chunks.jsonl` (gitignored, rebuilt deterministically); prints counts per source.  Expected ~150-200 chunks, ~200k tokens (plan 08 step 1).  $0.
- `extract --variant A|B [--chunks N] [--seed S]`: one `claude-sonnet-5-5` call per chunk (pinned rubric [alignment_extract.md](./rubrics/alignment_extract.md), not yet written: emit every imperative or failure mode as label, gloss, partner_label, partner_gloss, type, enactability, source_quote; reason first; imperatives give the virtue pole, failure modes the vice; labels per §1's rule; the prompt never sees our list), then the rewrite call on `mechanism` items ([alignment_rewrite.md](./rubrics/alignment_rewrite.md), not yet written).  Estimate A: ~170 × (≈2.5k in × $2/M + ≈0.5k out × $10/M) ≈ **$1.70**, rewrite ~25 × $0.005 ≈ $0.13; default `--budget-usd 4`.  Writes `extraction.jsonl`, `usage.json`, `warn_if_low_parse_rate`.
- `dedupe [--threshold T]`: embeds glosses through the cache (~350 × ~60 tokens ≈ $0.01; cap $1); exact-stem merge first; groups at the tuned threshold (from [dedup_labeled_pairs.json](../../data/candidates/alignment_sweep/dedup_labeled_pairs.json), 30 hand-labeled same/distinct gloss pairs, not yet written); writes `dedup_groups.json`.  Expected ~250 raw → **60-90** (plan 08 §4).
- `submit --run-id R`: prints the downstream estimate at the censuses' measured rates — 90 words → M1 90 × $0.0072 ≈ **$0.65**, M3 90 × 0.88 × $0.011 ≈ **$0.87** (upward risk noted: alignment-region rows run at cut-off 4, sending Sonnet's 2s and 3s to Opus at ~$0.003/pair, so M3 may run ~1.5×) — then `confirm_or_abort`, `start_run`, `candidates.jsonl` **first**, `submit_candidates`, `keys.txt`, and prints the follow-ups: `gap_registry.py submit --from <run>/candidates.jsonl` (main checkout) · `traithood_filter.py --batch-id R_alignment_sweep --run alignment_sweep/R --pipeline split --transport live --budget-usd 2` (plus `--third-model claude-opus-5-5` on the 10% Sonnet sample: the model-per-generator rule's measurement, platform § "M1 filter: judging model per generator"; the disagreement tripwire stays at its default 0.10) · `novelty_score.py score --batch-id R_alignment_sweep --run alignment_sweep/R --transport live --budget-usd 3`.  Submitting is $0.
- `gate --run-id R [--gold-only] [--readings-gold 2] [--readings-rows 2] [--no-third-reading]`: the enactability gate on the gold items and then on M3's kept rows (decision `new` or `pair_completion_for` set), `claude-opus-5-5`, pinned rubric [enactability_gate.md](./rubrics/enactability_gate.md) draft 3 — the two-sentence system prompt, the reason, then `where` / `elicitation` / `judge_needs` (§1, QUESTIONS 75).  **Two readings on the 30 gold items** (agreement and the flip rate are measured there), **one on the production rows**, which Roger reads anyway.  Estimate at Opus 5.5's $4/$20: 30 × 2 × ≈$0.012 ≈ **$0.75** gold and ~290 × 1 × ≈$0.012 ≈ **$3.6** rows (Roger's own arithmetic on 2026-10-11: about $1 and about $4.75); **cap $7**, raised from $1.5 with the model.
- `probe --run-id R`: definition probe of every submitted label and partner label on `qwen/qwen3-32b`, OpenRouter pinned to DeepInfra (US), fallbacks off; ~130 × (150 in + 80 out) ≈ **$0.005**; cap $0.5.  Skipped without the key.
- `report --run-id R [--gold]`: assembles `readout.md` from the registry blocks, the gate, the probe, `dedup_groups.json` and the usage files (summed per model); with `--gold`, runs the gold-set recovery (§8) and writes `gold_recovery.md`.  Since 2026-10-11 it also writes the gate's three fields with the tags they suggest, the AI-identity and belief-state sub-families, the shared-virtue fan list, the dedup merges that rest on the embedding, and the probe's above-floor share split single word against phrase (§1).  Report itself $0; the gold M3 rerun ≈ 45 rows × $0.013 + match calls ≈ **$0.7**; cap $3.

Whole workstream, A + gate + probe + gold + B: ≈ **$11-13** (the gate's move to Opus 5.5 adds about $3.5); no single launch over $7, so everything is live and nothing needs the $20 gate.

## 8. Acceptance tests, written first

No test calls an API or the network; fake clients, a hash embedder, fixture texts.  Files in §5.

- `sources`: every source has url, kind, a license or `read_only: true`, `license_verified_at`; Krakovna and MACHIAVELLI are `optional`; `weight` ∈ {0.5, 1, 2}.
- `chunk`: heading split on a fixture spec (6 headings → 6 chunks, ids stable); row split on a fixture table; rerun byte-identical.
- `extract` (fake client): schema parse, reason-first; `label_ok` rejects a 5-word label, an underscore, a non-ASCII label; a `mechanism` item is routed to rewrite and never submitted un-rewritten; `enactability: none` → `dropped_reason`, counted; `source_quote` > 25 words from a `read_only` source is truncated at a word boundary; **hygiene**: the pinned rubric text contains no corpus stem and no live queue label (checked against the real corpus, ~932 trait files at 2026-10-10); usage charged for an unparseable reply; `*** HIGH FAIL RATE ***` in caplog at 2 failures in 100.
- `dedupe` (hash embedder): exact stems merge; planted duplicates group at the threshold, distinct pairs do not; `tune_threshold` on the labeled fixture; a deduped pole's surviving partner gets its `partner_hint` rewritten to the representative; no group loses its `item_id`s.
- `submit` (tmp registry, real API): two Candidates per pair with crossed `partner_hint`s and `gloss_hint`s; `candidates.jsonl` written before the registry append and re-submittable with `--from`; second submit is a no-op; **cost guard**: 40,000 fake rows → estimate > $20 → refused without `--confirm-expensive --confirmed-by`; dry run leaves the registry byte-identical; follow-up commands name the run and batch ids.
- `gate` (fake client): reason-first prompt; two readings and a third where they disagree, the majority answer, `flip` set on disagreement; `score_against_gold` on a fixture (agreement, flip rate, the M1 confusion row); labels through `prompt_label`, `label_form` recorded.  Draft 3 (2026-10-11): the pin is version 3 and the answer keys come back in order `system_prompt`, `reason`, `where`, `elicitation`, `judge_needs`; `elicitation` and `judge_needs` are required unless `where` is `neither`, under which both are dropped; draft 2's `agentic-only` and `none` are no longer answers; the model is `claude-opus-5-5` with two readings on the gold items and one on the rows; the gold file's four-way key maps one-for-one onto field 1 and is scored in field 1's vocabulary; `eval_markdown` gives every answer a column, says fields 2 and 3 are unscored, and prints them with the tags they suggest.
- `probe`: the request pins `provider.order = ["deepinfra"]`, `allow_fallbacks: false`; a response naming another host is discarded and counted; no key → skip, report says so.
- `report`: the readout has the alignment-score and cut-off columns on **every** row (survivors and covers); rank = source_weight × novelty (new or pair-completion 1, covered 0) × pairability (both poles survive 1, else 0.5) × label-known (1, else 0.5), ties by `rank`; the covered table is present; `gold_recovery.md` counts recovered / 10 and names the frame-pair hit.  The sections of 2026-10-11: `dedup_merges` counts the exact-stem merges apart from the embedding ones and reconstructs how a member joined when the file predates the `joins` field (falling back to the group's `min_cos`, marked as such); `shared_pole_fans` finds a fan only when the partners' labels differ, and runs both ways round; the word scan matches endings (`retraining`) and not ordinary English (`equal weight`, `conscientious`); `probe_word_split` splits by whitespace in the label; a run missing the gate rows, the dedup groups or the probe says so in each section instead of rendering an empty one.
- Acceptance on recorded outputs (`test_gapgen_alignment_sweep_acceptance.py`, skips when files are absent; per the platform's review amendment 2, first-measurement numbers are **report-and-decide**, the mechanical checks hard): parse rate ≥ 99% in every summary; raw items 150-350 and dedup to 50-110 (report); every survivor's `polysemy_flag` false or its gloss carries the disambiguation (plan 08 §6); gate gold agreement and flip rate recorded against the targets **≥ 26/30 (87%) and ≤ 10%**, below which the gate is advisory-only; gold recovery recorded against **≥ 7/10** plus the frame pair; `usage.json` in every run and batch dir.

Commands that must pass at the end of every task:

```
uv run pytest assistant_axis/tests/test_gapgen_alignment_sweep_*.py data_analysis/tests/test_gap_generation_alignment_sweep_cli.py -q
uv run pytest -q
uv run python data_analysis/check_arrangements.py --quiet
uv run python tools/sync_entity_lists.py --check
uv run python data_analysis/gap_generation/rubric_pins.py check
git status --porcelain data/traits data/roles data/seed_queue.json   # must be empty
```

## 9. Ordered task checklist

Each task small enough to finish and test in one sitting; the test named proves it.

1. Skeleton, `sources.py` with the license lines of §5 verbatim, [gold_alignment_traits.json](../../data/candidates/alignment_sweep/gold_alignment_traits.json) and [gate_gold_items.json](../../data/candidates/alignment_sweep/gate_gold_items.json) (neither exists yet; 10 chat corpus alignment traits, 10 agentic-only items in the illustrative table's spirit, 10 none/mechanism items; none of the none-items a corpus label).  Test: sources.
2. `fetch.py` + CLI `fetch`; run it ($0) and paste the manifest's license and version lines into the task report.  Test: fetch (fake fetcher).
3. `chunk.py`; run it; the printed counts replace §7's chunk estimates (QUESTIONS information entry).  Test: chunk.
4. Extraction and rewrite rubrics, pinned ([versions.json](./rubrics/versions.json)); `extract.py`.  **Render one sample per variant** (an imperative chunk, a failure-mode chunk, a mechanism rewrite) exactly as Sonnet receives them and put them in the pilot readout (working-style rule).  Test: extract.
5. **Pilot** (§10).  Roger's decision on the prompt before the full extraction.
6. `dedupe.py`; hand-label the 30 pairs from the pilot's items; tune and commit the threshold.  Test: dedupe.
7. `submit.py` + CLI; full extraction of A's remaining chunks; `submit --run-id <date>a`; run M1 (with the Opus third opinion on the Sonnet sample) and M3 live; report the tripwire's disagreement rate.  Test: submit.
8. `gate.py` + `gate --gold-only`; the gate evaluation numbers go to Roger; then the gate on the kept rows.  Test: gate.  **Not yet run under draft 3** (2026-10-11): no draft has been scored against the four-way key, and draft 3 moves the model to Opus 5.5, so the next `gate --gold-only` is the first measurement of both.
9. `probe.py`; list the host and its country in the report before the first request.  Test: probe.
10. `report.py`; `readout.md` to Roger (the ~40-row table, alignment scores on every row, the 20-survivor precision sample for his enactable / distinct / label-known marks, scope lines for agentic-only survivors).  Test: report.
11. Gold-set recovery (`report --gold`, via Interface request 1 or its fallback); `gold_recovery.md`.
12. Roger's go on variant B; `extract --variant B` (Krakovna transient + agentic-misalignment), dedupe against A's items too, submit as its own run, M1 + M3, and the A-vs-B recovery comparison in the readout.
13. Acceptance report (§11); propose the `data/README.md` paragraph in the report (do not edit that file if the platform session owns it that week).
14. **TODO, deferred (Roger, 2026-10-11; [QUESTIONS.md](./QUESTIONS.md) 66): a field the question generator actually reads for elicitation guidance.**  Today nothing but the description reaches question generation (`description_notes` appears only in the gap-generation tooling and its tests, nowhere under `data_analysis/` or `pipeline/`), which is why "put it in the description" was first argued from the plumbing — a limitation, not a principle.  The gate's field 2 ([enactability_gate.md](./rubrics/enactability_gate.md), §6's gate row) is where the hint lives meanwhile, and it is shown in the readout for the promoter to read.  **Do it only if the inherent-action-context route proves insufficient**: for most agentic-only traits the hint is insurance rather than information, a decent gloss already denoting action, so at promotion the wave's agentic-only pairs are checked to see whether any needs more than its own wording.  Shape when it is built: a field on the trait file that the question generator reads (**not** `description_notes`, and **not** the description, which M3 reads for overlap), plus the promotion step that fills it from the gate's field 2 — the optional interface request 2 below is its registry half.  No file for it exists yet.

## 10. Pilot

`extract --variant A --chunks 30 --seed 0` on a stratified 30 chunks (20 Model Spec, 10 constitution): ≈ 30 × $0.01 ≈ **$0.30**, cap $1.  Readout for Roger, with the rendered prompt samples: items per chunk (expect 1-2.5); type and enactability fractions; the label rule's bite (how many labels the prompt itself flagged or `label_ok` rejected as terms of art or coinages — target after revision: ≤ 10% of emitted labels); polysemy-flag rate; partner glosses' scope match (spot-read 10 pairs against the pair-writing rule); projected full-run items and cost from the per-chunk mean; yield per dollar = items kept / usage total.  **Roger decides**: the extraction prompt's wording (especially the label rule's examples), whether partner poles read pre-balanced, whether `belief-state` items are wanted, and the go for the full extraction.  The gate has its own decision point at task 8: its gold numbers (agreement, flip rate, M1 confusion) decide whether its verdicts may drop rows from the main table or stay advisory.

## 11. Report at the end

One page at [acceptance_08_alignment_sweep.md](./acceptance_08_alignment_sweep.md) (not yet written): what was built against §5; deviations with reasons; the §8 commands verbatim with pass counts; the sources manifest's license and version lines; pilot readout and Roger's decisions; counts raw → deduped → submitted → M1 trait → M3 new / covered, with costs per step from the `usage.json` files per model; the M1 model-per-generator measurement (Haiku-Opus agreement on the Sonnet sample) and the tripwire rate; the gate evaluation numbers and what they permitted; the probe's host-and-country line; gold recovery (n/10, the frame-pair hit, misses with one-line readings); the A-vs-B comparison; open QUESTIONS entries.

## 12. Escalation

Opus retries a failing step once with a changed approach, then Fable, then Roger through [QUESTIONS.md](./QUESTIONS.md) (`N. [08] question. Assumption proceeded under: ... Status: open`), proceeding under the assumption unless the answer would make the work useless.  Pre-registered entries Opus copies in at the start — the resolutions of §1 plus plan 08 §9's unanswered questions:

1. Extraction model is `claude-sonnet-5-5` (plan 08 named Sonnet 4.6, which predates decision 17).
2. Dedup embeddings are the platform's `text-embedding-3-large` (plan 08 named a local model; M2 dropped local models).
3. The label probe runs on `qwen/qwen3-32b` via OpenRouter pinned to DeepInfra (US) (plan 08 said "local"); skipped without a key, and the rank factor then drops out.
4. Source versions are pinned in the manifest and `source_ref` (plan 08 §9 Q5).
5. Agentic-only traits are kept, with a `scope_line` for the question generator (plan 08 §9 Q1; §3.6 already says keep them).  **Answered 2026-10-11 (QUESTIONS 66)**: kept, and the scope line splits in two — a narrowing goes in the description at promotion, an elicitation hint does not and lives in the gate's field 2 (§1); the plumbing is deferred (§9 task 14).
6. AI-identity items (human-passing, claims-feelings) are submitted; M1's `role_*` tags route any that are role territory, and the readout flags the sub-family (plan 08 §9 Q4).  **Answered 2026-10-11 (QUESTIONS 67, and 78 for the belief-state rows)**: traits, not roles — size and exclusivity are the test, and as traits they compose with roles such as `paperclip_maximizer`; the readout lists both sub-families separately for Roger's sign-off before promotion (§1).
7. A corrigibility-like triple is recorded as the pair the sweep proposes, `partner_hint` set; triangles are deferred to the tangle pass (plan 08 §9 Q3; Roger's standing deferral of 2026-10-10).  **Answered 2026-10-11 (QUESTIONS 68)**: as assumed, plus the shared-virtue fan list in the readout, computed after dedup (§1).
8. The gold set maps `rationalizing` to [motivated-reasoning-prone](../../data/traits/instructions/motivated_reasoning_prone.json).
9. The Krakovna sheet is never stored in the repo; quotes from it and from the usage policies stay ≤ 25 words.
10. Multiword virtue labels are accepted by default (plan 08 §9 Q2; step 2's rule), the probe and Roger's precision marks being the check on them.

Anything that would edit a trait file or the queue, spend over a command's budget, or need a path outside the repository stops and asks.

## Interface requests (for the platform session)

1. **A named hidden set for the recovery harness**: `recovery_test.py --hidden-stems STEM ...` (or `--hidden-file F`) beside `--hidden-frac`, hiding exactly the gold set plus arrangement partners, no regional draw.  Fallback used meanwhile: `novelty_score.py score --hide <gold.json> --keys <kept rows>` into its own batch id plus the match functions of [recovery.py](../../assistant_axis/gapgen/recovery.py) driven from `report --gold`.
2. **Optional**: `gap_registry.py promote --notes-file F` merging the gate's `scope_line`s into the queue entries' `description_notes` at promotion.  Fallback: the scope lines sit in `readout.md` and are pasted at review.

## What this workstream provides (plan 08 §7)

An alignment-tagged candidate batch under `data/candidates/runs/alignment_sweep/`; the ten-trait gold set [gold_alignment_traits.json](../../data/candidates/alignment_sweep/gold_alignment_traits.json) (not yet written), reusable by any recovery test; and the pinned enactability-gate rubric [enactability_gate.md](./rubrics/enactability_gate.md) (not yet written) with its gold items, reusable by any workstream that produces action-level traits.
