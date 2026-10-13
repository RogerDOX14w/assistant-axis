# Acceptance: the multi-model extraction (P7), off-pod part

The one-page report of [coding_plan_multi_model_extraction.md](./coding_plan_multi_model_extraction.md)
§ 13, written 2026-10-13 when tasks 0-12 were done.  Task 13, the smoke runs, and the real-tokenizer
checks need a pod; their sections below are empty until then and are filled in with the log lines
when they run.  The task-by-task record is [p7_build_2026-10-13.md](./p7_build_2026-10-13.md).

**Terms.**  A *family* is the row of [model_families.py](../../assistant_axis/model_families.py) keyed on
a model's `config.json` `model_type`; the *header* is the run of tokens the chat template puts before
the assistant's content (slots 1..N of every activation); the *golden gate* is
[test_step2_qwen3_golden.py](../../pipeline/tests/test_step2_qwen3_golden.py), step 2 on the in-process
fakes compared bit for bit with a fixture made from the code before this work (828817a4).

## What was built

- The family table, six draft rows, only `qwen3` pinned (task 1); the header derived from the template
  ([chat_layout.py](../../assistant_axis/internals/chat_layout.py), task 2); the span mapper on injected
  ids with the turn roles (task 3); the span builder by row (task 4); `ProbingModel.model_type` /
  `.family` / `hf_load_kwargs` (task 5).
- Step 2 ([2_activations.py](../../pipeline/2_activations.py), tasks 6 and 8): the family, the layout
  and `--layers` checked from `config.json` and the tokenizer before any model loads; one assistant turn
  per conversation; `--thinking` removed; `--verify_spans N`; the metadata of § 7; the side-car check,
  with `--ignore_generation_config` required for a tree without one.  Step 5 compares `model_type` and
  `template_kwargs`.
- Step 1 ([generation.py](../../assistant_axis/generation.py), [1_generate.py](../../pipeline/1_generate.py),
  task 7): the family before vLLM, token-id prompts, the clean-up and `trust_remote_code` by row, the
  side-car's tokenizer fields.
- Downstream (task 10): `require_header_layout` and its tree form; the guards in 24 analysis scripts with
  three script-equivalence edges; the two steering guards.  Docs (task 11): README "Model families" and
  steps 1, 2, 5; an AGENT_NOTES section under a new rule, `model-families`; the skipped real-tokenizer
  test.

## Deviations from the plan

1. The golden fixture records `process_role`, not `extract_activations_batch` (same tensors; the latter's
   signature changed).
2. The short-header tolerance rule of § 5.4 was first left a TODO (§ 15 Q6), then built the same day on
   Roger's word (Gemma 2 needs it too): an exact match below four header tokens; the same day Roger set
   the bound to three (Gemma 2's three keep the N - 1 rule, OLMo 2's two are exact) and had the whole
   tolerance marked as almost certainly unnecessary (the TODO at `EXACT_MATCH_BELOW` in
   [spans.py](../../assistant_axis/internals/spans.py)).
3. `require_built` refuses the TODO `gpt_oss` row in both steps (a reading of § 15 Q3).
4. `cleanup_applied` is not added (the fix batch's recommendation).
5. [`whitening_k_weighted_scatter.py`](../../results_analysis/whitening_k_weighted_scatter.py) and [`rho_by_layer_simple.py`](../../results_analysis/rho_by_layer_simple.py) are not guarded (no data directory;
   their caches come from guarded scripts).
6. The AGENT_NOTES section has a rule of its own rather than an existing one's marker.

## Tests and the golden gate

| run | result |
|---|---|
| golden gate | 2 passed at every commit from task 0 to task 11 |
| the pipeline set (with this work's tests and the merge tests), last run at task 10 | 538 passed, 1 xfailed, 8 errors (the HF-cache tests of [test_generation.py](../../assistant_axis/tests/test_generation.py), denied by the sandbox) |
| [pipeline/tests](../../pipeline/tests/) | 232 passed |
| [assistant_axis/tests](../../assistant_axis/tests/) | 3,636 passed, 34 skipped, 1 xfailed, 8 errors (the same HF-cache tests), 2 failed: [test_gapgen_ipip_acceptance.py](../../assistant_axis/tests/test_gapgen_ipip_acceptance.py)'s two IPIP acceptance tests, red since review 5 and recorded so by the fix batch, not touched here |
| [results_analysis/tests](../../results_analysis/tests/) | 193 passed |
| [tools/tests](../../tools/tests/) | 427 passed |
| [data_analysis/tests](../../data_analysis/tests/) | 821 passed |

## Smoke runs (pending: the pod)

| family | derived header, as the log printed it | the row's expectation | checks (1)-(6) of § 11 | GPU-hours |
|---|---|---|---|---|
| `qwen3` (the first entities of the October run, § 15 Q9) | (not run yet) | the seven, ids `151644 77091 198 151667 271 151668 271` | (not run yet) | |
| `llama`, `gemma2`, `olmo2` / `olmo3` | (not run; each needs Roger's go) | drafts (`DRAFT_HEADERS`) | | |
| `gpt_oss` | not runnable (TODO, § 15 Q3) | | | |

GPU-hours used so far: **0**.  Paid calls: **none**.

## Open rows

`llama`, `gemma2`, `olmo2`, `olmo3` (every "to check" cell of `TO_CHECK`), `gpt_oss` (the TODO).  What
closes each, in order: the real-tokenizer test on the pod, the smoke run, Roger reading the derived
header, `expected_header_tokens` pinned.  The pod steps are items 7, 12 and 13 and rows T17-T28 of
[pre_extraction_pod_todo.md](./pre_extraction_pod_todo.md).
