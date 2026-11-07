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

---

# The sample (plan § 9), run 2026-11-03/04

**Run.**  Pod `roger-aa-sample-ids` (1× A100 SXM 80 GB, EUR-IS-1, the roles volume), checkout `b221528a`, launched
17:14 UTC on 2026-11-03 by [`run_sample.sh`](./scripts/run_sample.sh)
(every script and log of the run is in that `logs/` directory; the scripts are also kept beside this report in [`scripts/`](./scripts/), copied there on 2026-11-06 because the results tree is not under git).  The 20 entities of the plan's table (its 21 counted the
role [specialist](../../../data/roles/instructions/specialist.json) twice): nine heavy leakers, four cap-heavy, six controls
drawn with seed 20261103, and `default`.  Step 1 once under the family strip (`--max_tokens 1024 --reduce_questions 3`,
93 min): 10,000 responses, all with stored ids and a content range, 477 stripped, 37 suspected, 1,783 capped
([`step1_summary.json`](<../../../runpod_workspace/qwen/qwen-3-32b Roger sample-ids/step1_summary.json>)).  Step 2 three
times on the same responses (`text`, `ids`, `ids --content_span turn`, 54 min each) and the padding floor (the text path at
batch size 1 on [gamer](../../../data/roles/instructions/gamer.json) and
[thorough](../../../data/traits/instructions/thorough.json)); step 3 once per type by Flex ($1.56, rubric 20, which is
version 13's role and trait rubrics, the October prompt hashes); steps 4 and 5 per variant; the comparisons on the pod.
Outputs (no activations) in [`runpod_workspace/qwen/qwen-3-32b Roger sample-ids/`](<../../../runpod_workspace/qwen/qwen-3-32b Roger sample-ids/>):
`responses/`, `scores/`, `vec_text|ids|turn|text_bs1/` (20, 20, 20, 2 vectors), `axis_*.pt`, `compare/`, and the local
measurements in [`analysis/`](<../../../runpod_workspace/qwen/qwen-3-32b Roger sample-ids/analysis/>).  Cost about $23:
the pod ran 11.3 h instead of the planned 5.5 (below).

**What went wrong, for the record.**  (1) The comparison script spent 3.7 h a pair because torch spawned one thread per
CPU on a 255-CPU pod for small per-response ops; with `OMP_NUM_THREADS=8` an entity takes 2 min cold and 4 s from the page
cache (the remaining pairs ran in 88 and 16 s).  Set the thread count on any CPU-side torch script run on a pod.
(2) The agent's session ended at about 22:00 UTC with the shutdown as the last link of its watcher chain, so the pod ran
on until Roger asked at 04:05; from 2026-11-04 a run stops its own pod (`runpodctl stop pod $RUNPOD_POD_ID`, which the
finishing chain did at 04:26) and a watchdog armed before each extended run is to be built.  (3) SSH from the sandbox
to the pod's exposed port died at 04:04 (the proxy answered 502; sshd was fine) while a fresh pull pod's port worked;
the console's web terminal was the way in.

## Measurement 1: tokens ([`compare/token_diff.json`](<../../../runpod_workspace/qwen/qwen-3-32b Roger sample-ids/compare/token_diff.json>))

The stored ids against the text path's re-encoding, per response.  A stripped response differs by construction
(the ids path carries the leaked plan in the prefill, the text path never sees it; the `plan` kind), so the
re-tokenization rate is read from the `re-split` kind.

| class | responses | identical | re-split | token positions differing | rate |
|---|---|---|---|---|---|
| clean | 8,145 | 8,090 | 55 | 134 of 3,922,900 | 1 in 29,000 |
| capped | 1,378 | 1,355 (11 of them trimmed at the boundary) | 23 | 48 of 1,411,072 | 1 in 29,000 |
| stripped | 72 | 0 (plan) | 3 | | |
| stripped and capped | 405 | 0 (plan) | 11 (1 partial character) | | |

The October lower bound of 1 in 80,000 (§ 1 of the plan) becomes 1 in 29,000 on a fresh sample: 78 clean or capped
responses in 10,000 re-split somewhere.  No special token inside a range, no range null.

## Measurement 2: responses ([`analysis/compare_summary.txt`](<../../../runpod_workspace/qwen/qwen-3-32b Roger sample-ids/analysis/compare_summary.txt>))

Per response, slot 0 (the mean over the content tokens) and the seven header slots, pooled over the 64 layers:
cosine between the two variants' activations, relative difference `|a − b| / |a|` and relative norm change
`||a| − |b|| / |a|`.  "Bit-identical" is the fraction of cells with identical bf16 bits.

| comparison | class | cells | bit-identical | cosine p01 | cosine median | rel. diff median | rel. diff p99 | rel. diff max | rel. norm median | rel. norm p99 |
|---|---|---|---|---|---|---|---|---|---|---|
| text vs ids (the path) | clean, slot 0 | 521,280 | 0.979 | 0.999997 | 1.000000 | 0 | 2.4e-3 | 6.8e-2 | 0 | 1.2e-4 |
| | capped, slot 0 | 88,192 | 0.975 | 0.999998 | 1.000000 | 0 | 1.5e-3 | 1.0e-2 | 0 | 7.6e-5 |
| | stripped, slot 0 | 4,608 | 0 | 0.981 | 0.995 | 0.100 | 0.21 | 0.34 | 1.2e-2 | 8.0e-2 |
| | stripped and capped, slot 0 | 25,856 | 0 | 0.963 | 0.9946 | 0.106 | 0.31 | 0.89 | 1.2e-2 | 0.175 |
| | all, header slots | 4,479,552 | 0.982 | 0.99995 | 1.000000 | 0 | 1.0e-2 | 7.4e-2 | 0 | 7.7e-4 |
| ids vs turn (the span) | stripped, slot 0 | 4,608 | 0 | 0.919 | 0.988 | 0.160 | 0.42 | 0.52 | 1.7e-2 | 0.10 |
| | stripped and capped, slot 0 | 25,856 | 0 | 0.883 | 0.985 | 0.175 | 0.48 | 0.69 | 1.8e-2 | 0.13 |
| | clean or capped, any slot | | 1.000 | | | 0 | 0 | 0 | 0 | 0 |
| text vs text at batch size 1 (the padding floor) | all, slot 0 | 64,000 | 0 | 0.99999 | 0.999999 | 1.5e-3 | 6.5e-3 | 3.9e-2 | 7.6e-5 | 5.1e-3 |
| | all, header slots | 448,000 | 0 | 0.9995 | 0.99994 | 1.1e-2 | 3.3e-2 | 0.70 | 9.3e-4 | 6.3e-3 |

In angles: cosine 0.995 is 0.10 rad, 0.981 is 0.19 rad, 0.963 is 0.27 rad, 0.918 (the stripped-and-capped minimum)
0.41 rad, and the clean p01 of 0.999997 is 2.5 mrad.  So the path moves a stripped response's slot-0 activation by a
tenth of its length at the median and by a fifth to a quarter at the worst percentile, with a norm change of 1% at the
median and 8% to 17% at the worst percentile; a clean response is bit-identical 98% of the time and otherwise moves by
less than the padding floor.  Taking the whole turn as the span (the plan inside slot 0) moves a stripped response by
0.16 to 0.18 at the median, half as much again.  The header slots are bit-identical wherever the batch's padded length
is unchanged; where it changes (a stripped response's batch, or batch size 1) they carry the padding floor, about 1%
per response per cell at the median and 2% to 3% at p99, ten times slot 0's 0.15%, with one outlying cell, slot 1
(`<|im_start|>`) at layer 61 (p99 0.27, max 0.70); slot 6 at layer 25, the production cell, has p99 1.3e-2.

## Measurement 3: vectors ([`analysis/vector_compare.json`](<../../../runpod_workspace/qwen/qwen-3-32b Roger sample-ids/analysis/vector_compare.json>))

The step-4 vector of each entity under one variant against another, and against the entity's October vector (the
floor: a fresh T = 0.7 sample, a fresh judging, today's path).  Cosines at slot 0, layers 25 and 49; group medians
and the group's lowest.

| comparison | group | n | L25 median | L25 lowest | L49 median | L49 lowest | header slots, lowest |
|---|---|---|---|---|---|---|---|
| text vs ids (the path) | heavy leakers | 9 | 0.99996 | 0.99980 ([gamer](../../../data/roles/instructions/gamer.json)) | 0.99995 | 0.99976 | 1.0 |
| | cap-heavy, controls, default | 11 | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 1.0 |
| ids vs turn (the span) | heavy leakers | 9 | 0.99993 | 0.99971 (gamer) | 0.99989 | 0.99951 | 1.0 |
| | the others | 11 | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 1.0 |
| text vs text at batch size 1 (padding) | gamer, thorough | 2 | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 0.99995 |
| text vs October (the floor) | heavy leakers | 9 | 0.99987 | 0.99902 (r_competitor__aural_vark) | 0.99992 | 0.99949 | 0.99744 |
| | cap-heavy | 4 | 0.99996 | 0.99996 | 0.99997 | 0.99996 | 0.99994 |
| | controls | 6 | 0.99973 | 0.99961 ([witness](../../../data/roles/instructions/witness.json)) | 0.99984 | 0.99974 | 0.99944 |
| | default | 1 | 0.99997 | | 0.99998 | | 1.0 |

The sample's own assistant axes (step 5, 19 entities against `default`): text vs ids 0.99981 at L25 and 0.99977 at
L49, ids vs turn 0.99970 and 0.99944.  Read as 1 − cosine: the path moves a heavy leaker's vector by 4e-5 at the median
and 2e-4 at worst, every other entity by under 1e-5; the floor is 1.3e-4 (leakers) to 2.7e-4 (controls) at the median
and 1e-3 at worst.  The controls' floor is the largest because their responses are the shortest (witness's 500 average
266 tokens, thorough's 923, from the token counts in `compare/token_diff.json`).

## Measurement 4: axes and ρ

**(a) Projections** ([`analysis/axis_projection_shift.json`](<../../../runpod_workspace/qwen/qwen-3-32b Roger sample-ids/analysis/axis_projection_shift.json>)):
each sampled entity's projection on the 61 judged axes (October pole vectors; the two renamed poles resolved), the
shift between variants in units of the standard deviation of all 1,271 October entities' projections on that axis.
Group medians of the per-entity median |shift| over the 61 axes, then of the per-entity maximum, at slot 0 layer 25.

| comparison | heavy leakers: median, max-median, largest | controls | cap-heavy | header slots, largest |
|---|---|---|---|---|
| text vs ids (the path) | 0.008 σ, 0.022 σ, 0.053 σ | 0, 0, 0.001 σ | 0 | 0.001 σ |
| ids vs turn (the span) | 0.021 σ, 0.119 σ, 0.228 σ | 0, 0, 0.003 σ | 0 | 0 |
| text vs batch size 1 (padding) | 0.0001 σ, 0.001 σ, 0.001 σ | | 0.0004 σ, 0.001 σ | 0.011 σ |
| text vs October (the floor) | 0.035 σ, 0.069 σ, 0.325 σ | 0.016 σ, 0.093 σ, 0.217 σ | 0.009 σ, 0.045 σ, 0.069 σ | 0.254 σ |

**(b) ρ** ([`analysis/rho_substitution.json`](<../../../runpod_workspace/qwen/qwen-3-32b Roger sample-ids/analysis/rho_substitution.json>)):
[`judge_tier_robustness.py`](../../../results_analysis/judge_tier_robustness.py) (raw regime, the two production judge
cells, 61 axes) on symlink clones of the October tree with the sample's vectors substituted for the nine sampled
entities the judge caches cover (three of them poles: thorough, verbose, angel).  Largest |Δρ| over the 61 axes:

| comparison | s0_l25 | s0_l49 | s6_l25 | s6_l49 |
|---|---|---|---|---|
| ids vs text (the path) | 0.0002 | 0.0001 | 0.0000 | 0.0000 |
| turn vs text (the span) | 0.0004 | 0.0003 | 0.0000 | 0.0000 |
| text vs the untouched tree (the floor) | 0.0025 | 0.0023 | 0.0009 | 0.0005 |

(the two-judge cell; the single-judge cell is the same to the last digit; the largest is always `angel_vs_demon`,
whose pole was resampled).

## Reading, against the plan's decision rule

The path difference is confined to the responses that had a leak stripped (5% of the sample's, concentrated in the
heavy leakers): there it is a tenth of the activation's length per response, with a 1% norm change.  Averaged into a
vector it is 4e-5 of cosine at the median and 2e-4 at worst, against a resampling floor of 1.3e-4 to 2.7e-4 at the
median and 1e-3 at worst; on the judged axes 0.008 σ against 0.035 σ; on ρ 0.0002 against 0.0025.  The controls do
not move at all (1.00000 to five places, 0 σ), so re-tokenization itself does not matter; the plan effect is real and
confined to the leakers, and an order of magnitude below the sampling noise at every level the pipeline uses.  **No
re-extraction of the October data on this account.**  The span choice (the plan inside slot 0, `--content_span turn`)
is the larger of the two: 0.16 per stripped response, 7e-5 to 3e-4 on a leaker's vector, 0.021 σ at the median and
0.12 σ at the per-entity maximum on the axes, comparable to the floor's median and above its per-entity maximum of
0.07 σ; it still moves no control and ρ by 0.0004 at most.  That is the input to the AGENT_NOTES TODO on keeping leaked
thinking, not a re-extraction question.

**Other noise sources, for scale.**  The padding floor (batch size 4 against 1, the same text) is 0.15% per response at
slot 0 and about 1% at the header slots, and under 1e-5 of cosine on a vector.  The floor used above bundles the fresh
T = 0.7 sample with a fresh judging and a fresh kept set; the judge's own repeatability on fixed responses was not
measured here (no earlier measurement of it exists in the reports either), and cannot be from this sample, whose
activations went with the container disk.  It can be measured for about $2 and an hour on the October data, whose
activations are on the volumes: rejudge 20 entities' responses by Flex and rerun step 4 on a CPU pod.

## Lessons for the next pod run

- `OMP_NUM_THREADS` (or `torch.set_num_threads`) on every CPU-side torch script; a pod exposes every host CPU.
- The run script stops its own pod when its outputs are safe, and arms
  [`pipeline/pod/watchdog.sh`](../../../pipeline/pod/watchdog.sh) first (built the same day, with
  [`test_pod_watchdog.py`](../../../pipeline/tests/test_pod_watchdog.py)): an explicit cue, a hold for hands-on work,
  `runpodctl stop pod` after the idle window; the backstop for a sleeping laptop (Roger, 2026-11-04).
- Launch over `ssh -n` (a detached job inherits ssh's stdin and holds the session open); when the exposed port dies,
  the console's web terminal (Connect → Enable web terminal) reaches a pod whose sshd is fine; the SSH gateway
  `ssh.runpod.io` needs a PTY and carries no rsync.
- The outputs of a container-disk run are copied to the volume before the pod stops (the finishing chain did), and a
  fresh CPU pod on the volume ($0.16/h) pulls them; a deploy from the Storage page injects `PUBLIC_KEY` itself.

# Further analysis of the sample (2026-11-06): what the span choice does

Roger, 2026-11-06: the path question is moot if the October data is regenerated for the instruction rubric anyway;
what is open is the treatment of leaked thinking, "principled, but we don't know their actual effect", and whether the
sample, where step 2 was paid for three ways, can say more.  Two analyses on the sample's vectors, scores and
responses, no GPU, $0.10 of judging.  Scripts in the results tree's `logs/`, copied to [`scripts/`](./scripts/) beside this report:
[`span_direction.py`](./scripts/span_direction.py),
[`prep_thinking_judge.py`](./scripts/prep_thinking_judge.py),
[`compare_thinking_scores.py`](./scripts/compare_thinking_scores.py);
outputs in `analysis/`:
[`span_direction.txt`](<../../../runpod_workspace/qwen/qwen-3-32b Roger sample-ids/analysis/span_direction.txt>)
(every number as [`span_direction.json`](<../../../runpod_workspace/qwen/qwen-3-32b Roger sample-ids/analysis/span_direction.json>))
and [`thinking_scores.txt`](<../../../runpod_workspace/qwen/qwen-3-32b Roger sample-ids/analysis/thinking_scores.txt>)
([`.json`](<../../../runpod_workspace/qwen/qwen-3-32b Roger sample-ids/analysis/thinking_scores.json>)); the judged
thinking segments in
[`responses_thinking/`](<../../../runpod_workspace/qwen/qwen-3-32b Roger sample-ids/responses_thinking/>) and
their scores, replies and `usage.json` in
[`scores_thinking/`](<../../../runpod_workspace/qwen/qwen-3-32b Roger sample-ids/scores_thinking/>).

The three treatments of a leaked-thinking segment: `text` cuts it out and re-tokenizes the remainder, so the content
tokens run in a context without it; `ids` with the content range (the default) runs the sequence the model generated,
thinking in the context, and pools the content tokens only; `ids` with the turn span pools the thinking tokens too.
Here `d_span = v_turn - v_ids`, `d_path = v_ids - v_text`, and `o = v_ids - v_default` is the persona offset (the
sample's own default).  The nine entities with at least ten stripped responses are
[gamer](../../../data/roles/instructions/gamer.json) (89), [child](../../../data/roles/instructions/child.json) (18),
[aural_vark](../../../data/traits/instructions/aural_vark.json) (66),
[plugged_in](../../../data/traits/instructions/plugged_in.json) (74),
[millennial](../../../data/traits/instructions/millennial.json) (49),
[gen_z](../../../data/traits/instructions/gen_z.json) (17),
[stream_of_consciousness](../../../data/traits/instructions/stream_of_consciousness.json) (11) and the two
combinations of [competitor](../../../data/roles/instructions/competitor.json) (92) and
[rebel](../../../data/roles/instructions/rebel.json) (59) with aural_vark.  Slot 0 only: the header slots precede the
response, so the span choice cannot touch them (`d_span` is exactly zero there).

## A. The direction of the span shift

Slot 0, layer 25 and layer 49, from `span_direction.txt`:

- **Size.**  `|d_span| / |o|` runs from 0.8% (stream_of_consciousness) to 7.9% (gamer) at layer 25 and 1.0% to 9.8%
  at layer 49, in proportion to the share of stripped responses among the entity's kept (score-3) responses, 1% to
  17%.  Per kept stripped response the turn pooling moves that response's contribution by 0.36 to 0.76 of the persona
  offset's length at layer 25 and 0.48 to 1.01 at layer 49: at the response level the thinking's mean activation sits
  half to one persona offset away from the content's.  The vector effect is small only because stripped responses are
  a minority of the kept set even for the leakers.
- **One direction.**  The nine `d_span` vectors agree at a pairwise cosine of 0.80 (layer 25) and 0.87 (layer 49),
  the smallest pair 0.64 and 0.70; their first principal component holds 83% and 89% of the energy (1/n would be 11%).
  The persona offsets `o` of the same nine agree at 0.76 and 0.71 (PC1 79% and 75%); `d_path` at 0.92 and 0.93.
- **Half of it in the judged subspace.**  41% to 63% (median 47% and 46%) of `|d_span|²` lies in the span of the 61
  judged axes; the persona offsets put 90% and 88% there, the padding floor 7% to 13%, a random direction 1.2%.
  `d_path` puts 10% and 18% there.
- **Toward the default.**  `cos(d_span, -o)` is 0.39 and 0.38 at the median, positive for 9 of 9 and 8 of 9 leakers.
  Along the October assistant axis
  ([`roles/axis.pt`](<../../../runpod_workspace/qwen/qwen-3-32b Roger October/roles/axis.pt>), oriented with the
  October default positive) the shift is +0.031 σ and +0.043 σ of the October entities' spread, 2.0% and 2.4% of the
  entity's own offset along the axis, 9 of 9 toward the assistant.  `d_path`: cosine 0.08 and 0.10, +0.007 σ and
  +0.017 σ.
- **Path and span partly oppose.**  `cos(d_span, d_path)` is -0.23 and -0.38 at the median (every leaker negative).
  Against the padding floor (gamer): -0.02 and 0.02.
- **The same way on the same axes.**  From
  [`axis_projection_shift.json`](<../../../runpod_workspace/qwen/qwen-3-32b Roger sample-ids/analysis/axis_projection_shift.json>),
  51 of the 61 axes at layer 25 and 50 at layer 49 have at least 8 of the 9 leakers shifting with one sign (chance:
  2.4 axes), and the absolute mean shift over the leakers nearly equals the mean absolute shift (0.029 σ against 0.030 σ;
  0.036 σ against 0.037 σ): a common displacement, not an entity-specific one.  The largest, 9 of 9 agreeing: toward
  indecisive (-0.12 σ and -0.15 σ), toward verbose (-0.135 σ at layer 49), toward conservative (-0.09 σ and -0.10 σ),
  toward uncertain (-0.07 σ and -0.10 σ), toward traditional (-0.075 σ), toward transparent (-0.087 σ), toward
  descriptive (+0.066 σ).  `d_path` agrees on 56 and 37 axes but at 0.010 σ and 0.007 σ, and its direction differs
  between the layers (verbose, divergent, transparent, indecisive at layer 25; confident, decisive at layer 49).

## B. The judge on the thinking segments

The thinking of every stripped response, decoded from the stored ids over `thinking_token_range` (each one carries
`<think>` tags, removed before judging; median 603 tokens, 60% of the turn; 404 of the 477 responses capped), judged
by step 3 with the content's judge and rubric (gpt-5.6-luna, rubric version 20, Flex; 627 calls, every one parsed,
$0.10; the default's single stripped response left out, so 476).  Score-3 rate, by entity, of its clean responses,
of its stripped responses' content, and of their thinking (`thinking_scores.txt` and the comparison script's
baseline):

| entity | stripped | clean responses | stripped: content | stripped: thinking |
|---|---:|---:|---:|---:|
| child | 18 | 0.98 | 0.89 | 0.72 |
| gamer | 89 | 0.98 | 0.93 | 0.80 |
| aural_vark | 66 | 0.67 | 0.35 | 0.45 |
| gen_z | 17 | 0.99 | 0.88 | 0.88 |
| millennial | 49 | 0.84 | 0.82 | 0.67 |
| plugged_in | 74 | 0.73 | 0.64 | 0.38 |
| stream_of_consciousness | 11 | 0.97 | 0.55 | 1.00 |
| r_competitor__aural_vark | 92 | 0.22 | 0.12 | 0.16 |
| r_rebel__aural_vark | 59 | 0.25 | 0.07 | 0.14 |

Over all 476: the content scores 3 in 52% and the thinking in 47%; the two get the same score in 74% of the
responses, the thinking the lower in 15% and the higher in 11%.  The replies say why: aural_vark's thinking ("Let me
think this through out loud", "talking through alternatives aloud") is judged aural where its content, headings and
bullets, is not; plugged_in's thinking is "a conventional academic overview without current slang, memes, platform
references" where its content has them; gamer's thinking "discusses general ethical steps without role-specific
gamer perspective".  Also visible: a stripped response's content scores 3 less often than the same entity's clean
responses (aural_vark 35% against 67%, stream_of_consciousness 55% against 97%, the combinations 12% against 22% and
7% against 25%), 85% of them being capped responses whose thinking used most of the 1,024 tokens.

## C. Along the persona's own direction, or across it? (Roger, 2026-11-06)

[`span_vs_persona.txt`](<../../../runpod_workspace/qwen/qwen-3-32b Roger sample-ids/analysis/span_vs_persona.txt>)
([`span_vs_persona.py`](./scripts/span_vs_persona.py)), with
the offset taken from the October centroid (the mean of the 1,271 October trait and role vectors) rather than from
the default.  The span shift is mostly across the persona's direction, not along it: `cos(d_span, o_range)` is -0.30
and -0.28 at the median (layers 25 and 49), between -0.40 and -0.37 for eight of the nine, and the component along the
persona's own direction is -0.1% to -4.4% of the offset's length against a shift of 2% to 17% of it.  The offset's
norm falls by 0.1% to 3.9% (median 1.2% and 0.8%): slightly toward the average persona.  The one exception is
aural_vark, whose thinking aloud is in character (its thinking out-scored its content under the judge): there the
shift runs along its own direction (cosine +0.40 and +0.44) and the norm grows by 3.9% and 5.5%.  On the axes with
the largest common shift the picture is mixed.  The leakers already sit on the indecisive side (z of -0.04 to -2.35)
and the uncertain side (-0.18 to -2.35, gamer at 0), and the thinking pushes them further; they sit on the progressive
side (+1.1 to +2.4 for six of them) and the innovative side (+1.3 to +2.0 for seven), and the thinking pulls them back
toward the middle; on concise against verbose they are spread from -0.6 to +1.8 and all move toward verbose.  So it is
not "more of the same persona": it is the deliberation register laid over whatever the persona is, which happens to
reinforce it on some axes and counter it on others.

## D. Three checks without judged axes (Roger, 2026-11-06)

[`further_checks.txt`](<../../../runpod_workspace/qwen/qwen-3-32b Roger sample-ids/analysis/further_checks.txt>)
([`further_checks.py`](./scripts/further_checks.py)).

1. **Per response, the thinking against the content.**  From the ids-against-turn comparison at slot 0 (a relative
   difference per response) and the thinking's share of the turn,
   `D = |think_mean - content_mean| / |content_mean|` for each of the 475 stripped responses with both scores:
   median 0.35 at layer 25 and 0.40 at layer 49 (p10 to p90: 0.29 to 0.48, and 0.34 to 0.48), independent of the
   thinking's share of the turn (Spearman -0.07 and +0.02), as a fixed register would be.  It does not follow the
   judge's reading of the thinking: in-character thinking (score 3) is no closer to its content than
   out-of-character thinking (medians 0.354 against 0.343 at layer 25, farther if anything, p = 0.01; 0.400 against
   0.394 at layer 49, p = 0.4; closer in 2 of 7 and 3 of 7 of the entities with three or more in each group).  It
   follows the content's score instead: by (content score, thinking score) at layer 25, (3, 3) 0.357, (3, 1) 0.365,
   (1, 3) 0.341, (1, 1) 0.335, and per entity the content-3 responses have the larger D for eight of nine (gamer 0.344
   against 0.301, millennial 0.402 against 0.297, plugged_in 0.369 against 0.307).  So the thinking sits at one
   register whatever the judge makes of its text, and the content moves away from that register when it is in
   persona.  The path effect per response (text against ids, the context removed) is median 0.135 and 0.149, at
   Spearman +0.82 and +0.70 with the thinking's length: the removed context, as expected.
2. **The cap alone.**  Among non-stripped responses, the score-3 rate of capped against uncapped responses:
   [thorough](../../../data/traits/instructions/thorough.json) 0.99 against 0.91 (331 capped),
   [researcher](../../../data/roles/instructions/researcher.json) 0.99 against 0.86 (275),
   [specialist](../../../data/roles/instructions/specialist.json) 1.00 against 0.81 (261),
   [verbose](../../../data/traits/instructions/verbose.json) 1.00 against 0.99 (244); the leakers mixed on small
   counts (gamer 0.93 against 0.98 on 29, child 0.85 against 0.98 on 13, gen_z 0.71 against 0.99 on 7); pooled 0.93
   against 0.75, the cap-heavy four dominating the capped pool.  The cap, with the judge's cut-off marker, does not
   lower the kept rate; for the length traits it raises it, a long response being the trait.  The lower kept rate of
   stripped responses (0.49 capped, 0.65 uncapped) is the thinking's doing, not the cut-off's.
3. **The combinations' two sides.**  For the two combinations' stripped responses the role side falls from content to
   thinking and the trait side rises: r_competitor__aural_vark, role 3 in 46% of the content against 36% of the
   thinking, trait 16% against 26% (clean responses: 55% and 38%); r_rebel__aural_vark, role 69% against 42%, trait
   7% against 22% (clean 89% and 30%).  Response by response the role goes down in 19 and 22 and up in 7 and 3, the
   trait up in 15 and 11 and down in 6 and 3.  The thinking carries the aural trait (talking it through) and sheds the
   role, as aural_vark alone did; and in a stripped response the trait has gone into the thinking, leaving the content
   a structured answer (trait 16% and 7% against the clean 38% and 30%).

**What the three checks say about the strip** (Roger, 2026-11-06).  Check 1 supports it directly: the thinking is one
register whatever the judge makes of its text, and pooling it in would add that register to every leaker's vector,
which is the shared shift of A.  Check 2 is neutral: it compares capped against uncapped, not stripped against kept;
what it removes is a confound, since the truncation marker is not what costs the stripped responses their kept rate.
Check 3 is mixed: for the role side the thinking does not sound like the role, which supports the strip; for
[aural_vark](../../../data/traits/instructions/aural_vark.json) the trait is thinking aloud, the leaked thinking is
where it went, and the content left after the strip scores it at a third of the clean rate, a real cost for a trait
whose definition overlaps with what is stripped
([stream_of_consciousness](../../../data/traits/instructions/stream_of_consciousness.json) is the same shape in B).
Roger's reading: stripping is probably better than not stripping, except possibly for aural_vark.  The strip stays, and
in the ablation (item 1 of "ablations of the pipeline's filters and strips" in
[AGENT_NOTES.md](../../../AGENT_NOTES.md)) those two traits are where to look for a cost.

## Reading

- To the judge the leaked thinking is in persona about as often as the content (47% against 52%): more often for a
  persona that is a way of talking or thinking (aural_vark, stream_of_consciousness), less often for one carried by
  content and register (plugged_in, gamer, child).
- In activation space it nonetheless adds nearly the same displacement to every leaker: one direction (cosine 0.8 to
  0.87 across the nine), half of it inside the judged subspace, 2% toward the default, and on the judged axes toward
  indecisive, uncertain, verbose, conservative and transparent by 0.07 to 0.15 σ with 9 of 9 agreeing.  That is the
  register of deliberation, and pooling it in would move exactly the entities that leak, by an amount set by how much
  they leak, not by anything in their descriptions.  **The content range is the right span**: a leaker's vector stays
  with what the persona said, and what it avoids is a systematic confound, small at the vector level (0.15 σ on the
  worst axis for the heaviest leaker) because stripped responses are few.
- Per response the thinking's distance from its content is a register constant, 0.35 to 0.40 of the content's
  norm, unmoved by whether the judge reads the thinking as in character, and larger when the content is in
  persona (D above).  The same finding at the response level: the thinking is the same deliberation whichever
  persona is speaking, and the persona is in the content.
- The exception is a persona whose content is that register: aural_vark, and stream_of_consciousness by the same
  shape (D, check 3, and the paragraph after it).  Roger's reading (2026-11-06): stripping is better than not
  stripping, except possibly for aural_vark; the strip stays, and the ablation is where that cost would show as ρ.
- The path (`ids` against `text`) is a third the size, mostly outside the judged subspace and mixed in sign between
  layers: nothing to decide on this account, as before.
- For the keep-leaked-thinking TODO in [AGENT_NOTES.md](../../../AGENT_NOTES.md): keeping the thinking in the judged
  text would raise the kept count for some personas (stream_of_consciousness 6 to 11 of 11), but the stripped
  responses are mostly capped with weaker content than the entity's clean ones, and their thinking carries the
  deliberation signature above; these numbers are the TODO's input, and they point at the response budget the thinking
  exhausts rather than at the thinking as a source of signal.
