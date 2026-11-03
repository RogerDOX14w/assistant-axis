# Build report: the response-token-ids build, step 1 and step 2

The Opus coding agent's final report of 2026-11-03, verbatim but for the links, on the build of [plan.md](./plan.md) §§ 3 to 7.  The branch was rebased onto `942569a5` and fast-forwarded into `anthropic-vllm-uv` on 2026-11-03 (fifteen commits, head `339fd5e5`); the code links below resolve in the main checkout.  Fable's review notes are in the chat of the same day, not here.

---

Everything in plan §§ 3 to 7 is built and committed. Nothing is merged or pushed, and the main checkout was not touched. The full suite at the branch head has no failures beyond the nine pre-existing ones the base commit also has.

## 1. Branch and commits

The branch is `worktree-agent-acedee084dcdce3ad`, built off `094abc57`, which is the head of `anthropic-vllm-uv`. Its worktree was `.claude/worktrees/agent-acedee084dcdce3ad/`, removed after the merge.

| commit | part |
|---|---|
| `730cfca8` | § 4.1 Step 1 keeps vLLM's sampled ids |
| `790d86f1` | § 4.2 Step 1 computes and checks the two token ranges |
| `56186e45` | § 4.3 Step 1's `--response_cleanup {family,keep}` |
| `68e49f2a` | § 5.4 `batch_token_ids` from prepared ids, with `batch_conversations` as a wrapper |
| `4bf0c991` | § 5.3 `SpanMapper.map_spans` searches for the header from a span's `header_anchor` |
| `58e41bb8` | § 5.2 The ids path: the sequence built from step 1's stored ids |
| `7df26895` | § 5.1 `--token_source {auto,ids,text}` |
| `a0bb808e` | § 5.5 `--content_span {range,turn}` |
| `72d02069` | § 5.6 `--verify_ids N` |
| `d43967af` | § 5.7 Metadata records step 1's clean-up; the driver passes the token flags |
| `8c51744b` | § 4.4 and § 5.7 docs in [pipeline/README.md](../../../pipeline/README.md) |
| `b18b45d8` | Fix-up: shortens a comment from the § 5.6 commit to under 100 characters |

Interactive rebase is not available here, so the fix-up could not be folded into its commit.

## 2. What changed, by part

**§ 4.1** ([generation.py](../../../assistant_axis/generation.py))
- `generate_batch_detailed` keeps `output.outputs[0].token_ids` as a list of ints, verbatim. It also records `leaked` (the strip rule's detection, taken before any strip) and `raw_text`.
- `generate_for_role` writes `response_token_ids` after `thinking_suspected`, and `raw_text` only when the plan was stripped.
- Test harness only, no assertions changed: the fake vLLM in [test_generation_response_fields.py](../../../assistant_axis/tests/test_generation_response_fields.py) now returns `token_ids`. Its fake tokenizer decodes them: character codes, `</think>` as a single non-special id, two special ids, and byte ids so a character can be split. The fake vLLM in [test_generation_prompts.py](../../../assistant_axis/tests/test_generation_prompts.py) also returns `token_ids` now.
- Tests:
  - `test_the_ids_are_stored_verbatim_after_the_existing_keys`: compares the record key by key with what the old code wrote.
  - `test_a_stripped_response_keeps_the_text_before_the_strip`
  - `test_no_raw_text_when_nothing_was_stripped`

**§ 4.2** ([generation.py](../../../assistant_axis/generation.py))
- `token_ranges(tokenizer, token_ids, text, *, leaked, stripped, think_end_id, special_ids)` is pure and follows plan § 4.2 steps 1 to 4.
- `think_end_token_id` accepts the id only if it decodes back to `</think>`.
- `add_token_ranges` logs a WARNING per batch giving the count of null content ranges.
- The record gets `content_token_range` and `thinking_token_range` as `[s, e]` or null, after `response_token_ids` and before `raw_text`.
- Tests through `generate_for_role`, covering plan § 4.5 items 2–6 (in [test_generation_response_fields.py](../../../assistant_axis/tests/test_generation_response_fields.py)):
  - `test_a_clean_response_points_at_everything_but_the_stop_token`
  - `test_a_stripped_response_points_past_the_plan`
  - `test_a_plan_whose_end_tag_is_not_one_id_gets_null_ranges`
  - `test_a_cap_inside_a_character_steps_back_over_its_ids` (2-, 3- and 4-byte characters)
  - `test_a_text_that_keeps_the_partial_character_fails_the_check`
  - `test_a_sampled_special_token_is_kept_in_the_ids_and_the_range`
  - `test_ids_that_are_not_the_text_get_a_null_range`
- Tests of the pure function (item 8): `test_token_ranges_clean_and_empty`, `_stripped` (including a response that is only a plan), `_leaked_but_kept`, `_partial_characters`, `_a_strip_without_detection_is_a_bug`, and `test_the_end_tag_id_is_accepted_only_when_it_decodes_to_the_tag`.
- [test_response_fields_readers.py](../../../pipeline/tests/test_response_fields_readers.py) `::test_step3_judges_the_same_requests_with_the_token_fields` shows step 3 builds the same judge requests when records carry the new fields.

**§ 4.3**
- In [generation.py](../../../assistant_axis/generation.py): `RESPONSE_CLEANUP_OVERRIDES`, `response_cleanup_for(family, override=)`, and a `response_cleanup_override` argument on `VLLMGenerator`, `RoleResponseGenerator` and `build_generation_run_record`.
- Detection always follows the family row's rule. The strip is applied only when the effective rule is the strip rule.
- [1_generate.py](../../../pipeline/1_generate.py) gets `--response_cleanup {family,keep}`, default `family`. It is passed to both generator constructions and to the side-car, and step 1 warns when `keep` is in force.
- [run_pipeline.sh](../../../pipeline/run_pipeline.sh) gets `--response-cleanup`.
- Tests:
  - `test_keep_leaves_the_plan_in_the_text_and_records_where_it_is` (§ 4.5 item 7)
  - `test_the_override_is_checked_and_named_in_the_side_car_rule`, `test_the_override_reaches_the_generator`
  - In [test_1_generate.py](../../../pipeline/tests/test_1_generate.py): `test_response_cleanup_keep_is_recorded_and_refuses_a_family_rerun`, `test_the_default_clean_up_is_the_family_rule`, `test_the_clean_up_override_reaches_both_generators`, `test_an_unknown_clean_up_is_an_argparse_error`
  - In [test_run_pipeline_sh.py](../../../pipeline/tests/test_run_pipeline_sh.py): `test_response_cleanup_reaches_every_step_1_call`, `_is_not_passed_when_not_given`, `_in_christina_mode`, `test_an_unknown_response_cleanup_is_refused_before_any_step`

**§ 5.4**
- `ActivationExtractor.batch_token_ids` ([activations.py](../../../assistant_axis/internals/activations.py)) holds the padding, hooks, forward pass and metadata code, unchanged; `batch_conversations` now wraps it.
- `ConversationEncoder.assemble_batch` ([conversation.py](../../../assistant_axis/internals/conversation.py)) is factored out of `build_batch_turn_spans`, which now calls it.
- `_extract_batches` ([2_activations.py](../../../pipeline/2_activations.py)) builds each conversation's ids and spans once (before, they were built twice), assembles them and calls `batch_token_ids`.
- Tests in the new file [test_2_activations_token_ids.py](../../../pipeline/tests/test_2_activations_token_ids.py):
  - `test_batch_token_ids_gives_what_batch_conversations_gives`, parametrized over the `layer` forms and a truncating `max_length`.
  - `test_assemble_batch_is_what_build_batch_turn_spans_builds`
  - `test_extract_batches_runs_one_forward_pass_per_batch`
- The golden gate ([test_step2_qwen3_golden.py](../../../pipeline/tests/test_step2_qwen3_golden.py)) passes untouched, and the fixture is unchanged (checked with `git diff`).

**§ 5.3** ([spans.py](../../../assistant_axis/internals/spans.py))
- The header search runs back from `span.get("header_anchor", start_idx)`. The HEADER NOT FOUND log window is centred on the anchor.
- Tests: `test_the_header_is_found_from_the_anchor_past_a_long_plan` (without the anchor the slots come out NaN), and `test_an_anchor_at_the_spans_start_is_the_search_without_one` (§ 5.8 item 4).

**§ 5.2**
- `ConversationEncoder.trim_boundary_whitespace` ([conversation.py](../../../assistant_axis/internals/conversation.py)) is factored out of `_build_turn_spans_qwen` unchanged.
- `chat_layout.derive_turn_end_ids` ([chat_layout.py](../../../assistant_axis/internals/chat_layout.py)) reads the end-of-turn tokens off the template: `<|im_end|>\n` for Qwen3.
- In [2_activations.py](../../../pipeline/2_activations.py): `StoredTokens`, `TokenSourceError`, `build_ids_path_sequence`, and `token_records=` threaded through `extract_activations_batch`, `extract_activations_with_prefix_means` and `_extract_batches`.
- Tests (in [test_2_activations_token_ids.py](../../../pipeline/tests/test_2_activations_token_ids.py)):
  - `test_the_end_of_turn_is_read_off_the_template`
  - `test_ids_equal_to_the_re_encoding_give_the_text_paths_activations` (item 1, at extraction level)
  - `test_a_llama_like_model_takes_the_ids_path_too`
  - `test_the_plan_is_prefilled_and_slot_0_is_the_content_only` (item 3)
  - `test_the_stop_token_and_the_end_of_turn` (item 6)
  - `test_a_sampled_special_token_is_prefilled_and_averaged` (item 7)
  - `test_ids_past_the_range_are_prefilled_and_not_averaged` (item 8)
  - `test_a_range_that_does_not_fit_its_ids_raises`
  - `test_the_ids_path_needs_the_conversation_to_end_in_its_assistant_turn`
  - `test_the_boundary_trim_is_the_text_paths_rule`

**§ 5.1**
- `TOKEN_SOURCES`, `select_token_paths` and `record_key` ([2_activations.py](../../../pipeline/2_activations.py)).
- `process_role(token_source=)` logs the per-entity counts and writes metadata `token_source: {"ids", "text", "range_null"}`. The flag also reaches both worker modes.
- Tests:
  - `test_ids_and_text_give_bit_identical_files_when_the_ids_are_the_re_encoding` (item 1: every activation, every prefix mean, and all metadata except the counts)
  - `test_the_text_arm_is_todays_step_2` (item 2) and `test_the_canonical_bytes_ignore_addresses_and_nothing_else`
  - `test_a_mixed_file_takes_both_paths_and_counts_them` (item 5, including the refusal under `ids`)
  - `test_ids_without_a_range_key_take_the_text_path`, `test_a_range_that_is_not_two_integers_raises`, `test_the_token_source_flag`

**§ 5.5**
- `CONTENT_SPANS` and `content_span=` threaded through. `turn` starts slot 0 at the end of the prompt; the boundary trim still applies.
- `turn` with `--token_source text` is refused by argparse in `main` and with a `ValueError` in `process_role`. A warning fires when text-path records average only their content.
- Metadata gets `content_span`.
- Tests: `test_content_span_turn_averages_the_plan_and_the_content`, `test_content_span_is_recorded_and_refused_on_the_text_path`, `test_the_content_span_flag_is_refused_with_the_text_source`.

**§ 5.6**
- `verify_token_paths`, `describe_token_difference` and `TokenPathVerificationError`, wired into `process_role(verify_ids=)`.
- A failed check stops the worker (exit 1); in single-worker mode the run exits 1.
- Tests (item 9):
  - `test_verify_ids_reports_each_kind`: re-encoding, plan, special token, partial character, re-split and a null range.
  - `test_identical_ids_with_different_slots_stop_the_run`: the second pass is monkeypatched to flip one bit.
  - `test_a_worker_stops_on_a_failed_ids_check`, `test_the_verify_ids_flag`.

**§ 5.7**
- `recorded_response_cleanup` reads the clean-up from the side-car. `check_generation_config` logs it and does not refuse on it.
- Metadata `response_cleanup` is None when there is no side-car.
- [run_pipeline.sh](../../../pipeline/run_pipeline.sh) gets `--token-source`, `--content-span` and `--verify-ids`. They are passed to every step-2 call, step 0's included, only when given. They are validated before any step, and the `turn` + `text` pair is refused up front.
- Tests:
  - `test_the_recorded_clean_up_is_logged_and_read`
  - `test_the_metadata_records_the_path_the_span_and_the_clean_up`
  - `test_main_passes_the_flags_and_the_recorded_clean_up`
  - `test_step_4_copies_the_new_keys_into_the_vector_and_step_5_refuses_nothing_new`
  - Driver ([test_run_pipeline_sh.py](../../../pipeline/tests/test_run_pipeline_sh.py)): `test_the_step_2_token_flags_reach_every_step_2_call`, `_are_not_passed_when_not_given`, `_in_christina_mode`, `test_bad_step_2_token_flags_are_refused_before_any_step`

**Docs** ([pipeline/README.md](../../../pipeline/README.md))
- Step 1 gets "The generated ids" and the `--response_cleanup keep` paragraph, an options row, and the side-car's `keep`.
- Step 2 gets "Which tokens are prefilled", the three new metadata keys, the new options and the new exit-status cases.
- The driver's flag list gets the new flags.
- Every file mention is linked, relative to the README.

## 3. Test run at the final commit

`uv run pytest assistant_axis/tests pipeline/tests -q` gave `9 failed, 5620 passed, 82 skipped, 7 warnings in 502.98s`. The same command with `PYTHONPATH=<worktree>` gave the identical counts.

All nine failures are in the trait-gap (`gapgen`) acceptance and WordNet tests, and the base commit fails the same nine (`9 failed, 5545 passed, 82 skipped`). Two causes:
- Corpus trait files are newer than the region, lexical and Roget tables.
- OEWN data is not installed in this environment (`gw.oewn_installed()` returns False).

None of these tests imports any module this build touched. Every commit was also checked on the non-gapgen suite with `PYTHONPATH` pinned (1,851 passing at § 4.1, rising to 1,923 at § 5.7; 34 skipped; 0 failed). The three step-1 commits were rechecked by checking each one out.

**Environment finding, which matters for whoever runs these tests from a worktree:**
- The worktree's own `.venv` has no pytest. `uv run` created that `.venv` from the lock and uv's cache on my first command; the lock is unchanged and nothing was added.
- So `uv run pytest` runs the main checkout's `.venv/bin/pytest`, whose editable install points at the main checkout.
- If a `pipeline/tests` file is collected first, `assistant_axis` is imported from the main checkout and the worktree's code is not what gets tested. I saw this happen once.
- The brief's command is safe because it lists `assistant_axis/tests` first, which makes pytest put the worktree root at `sys.path[0]`.
- From § 5.4 on, every run had `PYTHONPATH` pinned to the worktree.

## 4. Decisions made

1. **The plan file.** It is not in this worktree; it is untracked in the main checkout, and I read it there. The README links [`../reports/pipeline/response_token_ids/plan.md`](./plan.md), which exists only once the plan is committed.
2. **Where detection applies.** Detection runs only for rows whose rule is `strip_leaked_think`. Other families never detect, so their `thinking_token_range` is null and their content starts at 0. Under `keep`, detection still runs.
3. **`keep` on a row whose rule is `none`.** It records `"keep"`, as plan § 4.3 literally says. A later `family` run into that directory is refused even though it would behave the same; this is the conservative choice. The step-1 warning fires only when the row's rule is not `none`.  *Superseded 2026-11-03 (Roger): the side-car records the clean-up applied (`none` under `keep`) and the flag beside it as `response_cleanup_override`, so that pair is no longer refused; [plan.md](./plan.md) § 4.3.*
4. **Decode settings for the step-1 check.** It decodes with `clean_up_tokenization_spaces=False` as well as `skip_special_tokens=True`. That is a no-op for Qwen3, whose config already sets False. Llama 3's config sets True, and vLLM's detokenizer applies no clean-up.
5. **Partial-character step-back.** It is capped at 3 ids (`MAX_PARTIAL_CHARACTER_IDS`); I read the plan's "at most three steps" as a cap.
6. **Missing `token_ids`.** A vLLM output without `token_ids` raises rather than writing records without ids. The ids are read by attribute.
7. **`batch_token_ids` signature.** It takes `(batch_full_ids, span_metadata, layer, max_length)`, without the plan's `batch_spans`, which nothing inside uses.
8. **A range that does not fit its ids.** This raises `TokenSourceError` under `auto` too, rather than falling back to the text path. It means corrupt data, so the entity fails loudly.
9. **Counting `range_null`.** It is counted only under `auto` and `ids`; under `text` it is 0, so the text arm's metadata equals that of records without ids. A record with ids but no `content_token_range` key counts as `range_null`.
10. **When the new metadata keys are written.** All three are always written, including on text-only runs. So the October-style text path writes files whose tensors and pre-existing keys are identical to today's (the golden gate passes), plus these three keys.
11. **The trim on the ids path.** It is applied for every family, not only chatml, following the README's definition of slot 0.  *Superseded 2026-11-03 (Roger): the ids path trims nothing, for any family; the strip becomes surgical (`</think>` plus one `\n\n`, nothing else) and step 1's pointer follows it exactly, so the `\n\n` after a stripped plan is outside the content range at the source; `--verify_ids` compares spans and reports the text path's trailing-whitespace trim as such; [plan.md](./plan.md) § 3, § 4.1, § 4.2, § 5.2, § 5.6.*
12. **The ids-path span.**
    - The span is numbered `turn` as the text path numbers it.
    - Only the assistant span is built.
    - `turn_end_ids` is derived once per entity, not once per worker; it costs four template renders.
13. **`--verify_ids` forward passes.** Passes are run only for conversations whose ids are identical, one conversation per pass, so both passes have the same shape. Differing conversations are classified without a pass.
14. **What `--verify_spans` checks.** It still checks only the text path's span builder; the README says so.
15. **The driver's step-1 calls.** `--response-cleanup` goes to all five step-1 calls, not "the two", so that step 0's default and every tree are generated under one rule.
16. **New driver summary lines.** `Clean-up: …` and `Step 2 flags: …`. I avoided `Step 2:`, which collides with the existing banner.

## 5. Deviations from the plan, and places the plan did not match the code

- **Commit order.** Step 2 was committed as 5.4, 5.3, 5.2, 5.1, 5.5, 5.6, 5.7, as briefed. § 5.3 went before § 5.2 because the ids path's header slots depend on the anchor. A docs commit and a one-line comment fix-up follow.
- **§ 5.8 item 2, "same bytes".** This cannot hold literally. The legacy `torch.save` that step 2 uses keys each storage by its memory address (`str(storage._cdata)`) and writes storages in the order of those keys, so two runs of today's code never produce the same bytes. The test compares canonical bytes instead: load the file and re-save it in torch's zip format. That checks key order, metadata, dtypes, shapes, strides, offsets and every data byte. A separate test shows this canonical form catches a one-bit flip and a change of key order.
- **§ 5.8 item 1, "every key".** The metadata necessarily differs in `token_source`, since the counts are per path. Everything else is equal.
- **Plan § 4.3** says [run_pipeline.sh](../../../pipeline/run_pipeline.sh) has two step-1 call blocks; it has five.
- **The [AGENT_NOTES.md](../../../AGENT_NOTES.md) section the plan cites,** § "TODO: keep leaked thinking instead of stripping it?", does not exist in this branch's AGENT_NOTES.md. It appears to exist in the main checkout. The README and code comments name it.
- **Flagged change to a test expectation.** [test_2_activations_extract.py](../../../pipeline/tests/test_2_activations_extract.py) `::test_metadata_records_a_layer_subset_and_the_no_header_layout` compares the whole metadata dict, so it was extended in §§ 5.1, 5.5 and 5.7 with `token_source`, `content_span` and `response_cleanup: None`. Flagging comments are in the test. No other assertion was changed.

## 6. Open questions (not blocking)

- **Plan § 8 smoke-run questions.** Whether vLLM's `.text` equals a plain decode, and whether `token_ids` include the stop token. The code handles both answers. If vLLM's text ends in U+FFFD at the cap, those ranges will be null.
- **Determinism for `--verify_ids`.** It assumes the pod's kernels give identical results for identical inputs of the same shape at batch size 1. Non-deterministic kernels would raise a false "bug" exit 1.
- **Under `keep`.** A record with a null range takes the text path, and Qwen3's real template moves text before `</think>` into a think block. This should be rare.
- **The header anchor.** It assumes header = generation prompt, which holds for Qwen3 and Llama. A family whose model writes header tokens itself (gpt-oss, a TODO) would need work.
- **Step 5 metadata.** Step 5 copies the first vector's metadata, so an axis's `token_source` counts are one entity's.

## 7. What a reviewer should look at first

1. `build_ids_path_sequence` and its use in `_extract_batches` ([2_activations.py](../../../pipeline/2_activations.py)): the prompt ids, the trailing-special strip, the offsets, `header_anchor`, and the `content_span` start.
2. `_extract_batches` after § 5.4: the text path now builds each conversation once and goes through `assemble_batch` and `batch_token_ids`. The golden gate and the direct comparison pass.
3. `token_ranges` and `add_token_ranges` ([generation.py](../../../assistant_axis/generation.py)): the decode settings and the strip-mode check. These decide which records the ids path is allowed to touch.
4. `trim_boundary_whitespace`, extracted from `_build_turn_spans_qwen` ([conversation.py](../../../assistant_axis/internals/conversation.py)).

Key files:
- [pipeline/2_activations.py](../../../pipeline/2_activations.py)
- [assistant_axis/generation.py](../../../assistant_axis/generation.py)
- [pipeline/tests/test_2_activations_token_ids.py](../../../pipeline/tests/test_2_activations_token_ids.py)
- [pipeline/README.md](../../../pipeline/README.md)

---

# Review of the branch at `ae5fc276` (2026-11-03)

Two independent reads of `git diff 094abc57..ae5fc276` (fourteen commits: the twelve above, Fable's `e51df25c` on the side-car, the agent's `ae5fc276` for the surgical strip), one by Fable with the real Qwen3-32B chat template fetched to check the fakes against, one by a second Fable agent given the diff and the lens but not the first read's notes.  The lens, Roger's: the worst bug is one that silently alters, drops or misaligns a small fraction of records.  Both reads found nothing of that kind on the strip-mode Qwen3 path the sample runs, and both found the same main hazard.

**Found, ranked.**

1. **Keep mode is sound only on the ids path, and nothing enforces it** (both reads).  The real template, when an assistant turn's content contains `</think>` ([`tokenizer_config.json`](https://huggingface.co/Qwen/Qwen3-32B/blob/main/tokenizer_config.json) lines 37–44 of the chat template), moves the text before it *into the think block*: `<|im_start|>assistant\n<think>\n{plan}\n</think>\n\n{after}`, a context the model never saw (it wrote the plan after an *empty* think block).  So on the text path a `keep` record has its plan filtered out of slot 0 by the chatml think filter (the opposite of what `keep` is for), and the seven-token header is beyond `_find_header`'s 14-token reach, so slots 1–7 are NaN with a HEADER NOT FOUND per record; `--verify_spans` would exit 1 on it.  The fakes' template has no `</think>` split, so no test can see it.  Reached by `--token_source text` on a keep tree, and under `auto` by any keep record whose range is null.  Zero effect on the sample (strip mode); must be guarded before keep is used.
2. **The strip rule changed but its name in the side-car did not** (second read).  `response_cleanup: "strip_leaked_think"` is what the settings check compares, so a gap-filling rerun into an October-era directory is accepted although the new texts keep edge whitespace the old ones lost and the directory then mixes records with and without ids.  Negligible for research, a provenance gap.
3. **`content_span: "turn"` in a mixed file's metadata overstates what was averaged** (second read): under `auto` the null-range records of that file averaged their content only; the vector keeps no trace.  Low.
4. **`add_token_ranges` tolerates a tokenizer without `all_special_ids`** (second read, unconfirmed): the stop token would stay inside every range and step 2 would refuse every record ("does not fit"); loud, not silent.  Make it a hard error in step 1.  Likewise `strip_leaked_plan` has no guard against a text without `</think>` (its one caller guards it).

**What the sample's measurements would not see** (second read, Fable concurs): a class of records whose range step 1 could not verify takes the text path in both variants under `auto`, so variants (1) and (2) agree on exactly the records where the paths differ most (run the sample with `--token_source ids`, where it is an error instead); the padding confound, since ids-path sequences of leaked records are a plan longer, a batch's padded length differs between variants, and bf16 kernels can move the low bits of *clean* neighbours in the same batch, which measurement 2 would book as a path effect (`--verify_ids` runs at batch size 1 and cannot see it; measure the floor with one variant at two batch sizes on a couple of entities); a stripped content beginning with a space is averaged on one path and trimmed on the other, inside the "plan" class; variant (3) keeps plan-only responses that (1) and (2) drop, so its vectors average a slightly different set.

**Gaps in the tests:** no step-1 → step-2 check on one tokenizer (the suite tests the halves on different fakes; the second reader's scratch check does it and belongs in the suite); no keep-tree text-path test, and none possible on the current fake template; the step-1 fake decodes by character, so a token holding a whole character plus the first byte of a cut one is never exercised (safe fallback, unmeasured); every ids-vs-text equality test runs on the fake model, where padding cannot change values.

**Confirmed by the real template:** the content of the last assistant turn is rendered `lstrip('\n')`-ed, so a stripped record beginning with a newline loses it on the text path (now one of the measured differences); 0 of 20,000 October responses begin with whitespace, 13 end with it, 0 of 30,000 contain both think tags.

**Fixed the same day, commit `ee98dfbc`** (Roger approved (a)–(d); the agent built them; Fable checked the diff against the brief): (a) the keep-tree guard in step 2, `apply_keep_tree_guard`, before any model loads: on a tree whose side-car records `response_cleanup_override: keep`, `--token_source text` is refused (`KeepTreeError`, exit 1) and `auto` is promoted to `ids`; the driver refuses `--response-cleanup keep` with `--token-source text` up front; (b) `RESPONSE_CLEANUP_VERSION = 2` (1: the October rule, cut then `.strip()`; 2: the surgical cut), written to the side-car as `response_cleanup_version` under every clean-up and added to `SETTINGS_KEYS`, so a rerun into an October-era directory is refused as `None -> 2`; (c) `add_token_ranges` refuses a tokenizer without `all_special_ids`, `strip_leaked_plan` refuses a text without `</think>`, the README says `content_span` applies to the ids-path records; (d) ten end-to-end cases (clean, `\n\n`, a single `\n`, a leading space, both, plan only, plan + `\n\n`, whitespace at both ends, a trailing `\n\n`, keep; each with and without the stop token, plus a partial character at the cap) run the real `generate_batch_detailed` and `build_ids_path_sequence` on one tokenizer and assert the range decodes to the stored text, the two ranges partition the ids, the ids are prefilled as generated and the span decodes to the text.  Suite: `9 failed, 5660 passed, 82 skipped` (the nine pre-existing).  One decision left to Roger: the guard is keyed on the flag alone, so `text` is also refused on a keep tree of a family whose rule is `none`, where it would be harmless.  Findings 1–4 are thereby closed; the measurement blind spots are handled in the runs (variants (2) and (3) under `--token_source ids`; a padding-floor measurement; a text-path regression check against an October activation file in the smoke run).

**The smoke run (plan § 8, with the review's additions; 2026-11-03, 05:44–06:13 UTC, about $0.90).**  On a 1× A100 SXM pod deployed on the tcomb volume (`roger-aa-smoke-ids`; EUR-IS-1 had no 2× pod free, and the deploy form's volume reset to tcomb), checkout `b221528a`, outputs pulled to [`runpod_workspace/qwen/qwen-3-32b Roger smoke-ids/`](../../../runpod_workspace/qwen/qwen-3-32b%20Roger%20smoke-ids/) (the responses with their side-car, and the logs; the activation files stayed on the pod's container disk).  Step 1, gamer, 500 responses at the October cap of 1,024 (8 minutes): 75 stripped (October's run had 78), 3 of them keeping edge whitespace under the surgical rule, 89 capped, and **500 of 500 stored ids decode to the stored text** (no null range: vLLM's `.text` equals a plain decode on every response, the cut character at the cap included); **the stop token is in `token_ids`** when the model stops (411 responses end in `<|im_end|>`, the 89 capped ones in an ordinary token); the side-car records `response_cleanup_version: 2`, `response_cleanup_override: family`, a clean `git_sha`.  Step 2 on it with `--token_source ids --verify_ids 20 --verify_spans 20 --batch_size 4` (3 minutes after the load): 500 on the ids path; 20 of 20 spans decode to the content; of the 20 verified conversations, 15 have identical ids on both paths and **identical spans and bit-identical slots**, 5 differ (4 by a prefilled plan, 1 by a re-split of 2 positions in a 755-token sequence); no header mismatch.  Regression of the text path on real data: the October `t_accountant__amoral` and `default` responses (no ids) re-extracted with the new code at batch size 4 are **bit-identical to their October activation files, 500 of 500 each**, no NaN slots, the metadata differing only by the three new keys.  Plan § 8's three questions are answered, all as the code assumed.

**Verified clean:** the parallel lists of `process_role` (one `responses` list, one order, no filtering, lengths checked, batch slices by the same indices); the bounds check of the range against the special-stripped ids; the same `all_special_ids` on both sides; the prompt built by the same `prompt_token_ids` on `conversation[:-1]` that step 1 sent; `header_anchor = len(prompt_ids)` as the header's end (the layout derivation already requires the generation prompt to be a prefix of the rendered turn); the `map_spans` anchor leaving the text path untouched; the three factorings byte-identical (golden gate); `verify_token_paths` and `compare_assistant_spans`; both worker modes passing the same arguments; the driver's arrays reaching every call; `response_cleanup_override` outside `SETTINGS_KEYS`.
