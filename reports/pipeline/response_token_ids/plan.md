# Plan: store the generated token ids in step 1, and prefill them in step 2

Written 2026-11-02 for Roger, from the session's measurements and his decisions of the same day; the
implementation is for an Opus coding agent, so § 4 to § 7 are written as a build brief.
**Nothing in this plan is built or launched.**  The pipeline changes wait on Roger's reading of this document; the
smoke run (§ 8) and the sample (§ 9) are each confirmed with him flag by flag before launch.

## 1. The question and the decisions

Step 1 keeps only the text of each response (`output.outputs[0].text`,
[generation.py](../../../assistant_axis/generation.py) `generate_batch_detailed`) and drops the ids vLLM sampled.
Step 2 renders that text through the chat template again and prefills the result
([conversation.py](../../../assistant_axis/internals/conversation.py) `build_turn_spans`).  Decoding and
re-encoding is not the identity on a BPE vocabulary, so what step 2 prefills is not always what the model generated.
Measured on the October extraction (2026-11-02; the scripts are in the session scratchpad,
[check_retok.py](/private/tmp/claude-501/-Users-roger-Documents-GitHub-assistant-axis/2435c7bb-8854-4b5f-997a-5ecd5f1a7021/scratchpad/retok_script/check_retok.py)
and
[check_end_cuts.py](/private/tmp/claude-501/-Users-roger-Documents-GitHub-assistant-axis/2435c7bb-8854-4b5f-997a-5ecd5f1a7021/scratchpad/retok_script/check_end_cuts.py)):

- Of the 47,176 responses cut at the 1,024-token cap (so of known length), 98.7% re-encode to exactly 1,024 tokens;
about 74 of the 593 misses are the cap landing inside a multi-token character, leaving about 519 (1.1%) with a real
difference, most off by one, 18 by three or more.  That is about 600 tokens in 48.3 million, 1 in 80,000, and a
**lower bound**: an equal-count re-split is invisible to a count, and only capped responses have a known count.
Some of the misses may be special tokens vLLM leaves out of the text rather than re-splits; the two cannot be
separated without the ids.
- The larger effect is **leaked thinking**: for 5,230 responses (0.34%) Qwen emitted a plan ending in `</think>`
although thinking was off, and step 1 stripped it from the text.  The model wrote the answer with that plan in
its context; step 2 prefills the answer without it.  It is a persona effect: [gamer](../../../data/roles/instructions/gamer.json)
78 of 500, [aural_vark](../../../data/traits/instructions/aural_vark.json) 69 and nine of the fourteen worst
entities its combinations, [plugged_in](../../../data/traits/instructions/plugged_in.json) 52,
[millennial](../../../data/traits/instructions/millennial.json) 50,
[stream_of_consciousness](../../../data/traits/instructions/stream_of_consciousness.json) 13; 71% of the stripped
responses hit the cap, so the plans were long.  The TODO on whether the plan should be kept is in
[AGENT_NOTES.md](../../../AGENT_NOTES.md) § "TODO: keep leaked thinking instead of stripping it?".

**Roger's decisions (2026-11-02):**

1. The aim is a step 2 prefill as close as possible to the activations the model generated the text with.  So

   step 1 stores vLLM's ids **untouched**, leaked plan and all, with a pointer to the tokens behind the stored
    text; step 2 prefills prompt ids plus every stored id, and averages slot 0 only over the pointed-to tokens.
2. The stored text (`conversation[...]["content"]`) is what step 3 and the response judging read, and they have no

   tokenizer; it stays exactly what it is today, whatever else the record carries.  Making the strip optional is
    folded in (§ 4.3), so that the three vector variants of the TODO can be tested, but a run that keeps the plan in
    the judged text is a deliberate, recorded setting, never a side effect.
3. Build both steps, then **run step 1 for a chosen sample, run step 2 both ways on it, and measure** whether the

   path changes vectors and ρ by more than sampling noise (§ 9).  That decides whether the October data is
    re-extracted before data is generated for other models.  The sample goes to a new tree beside the October one.
4. Step 2 will be rerun in any case once the steering statistics and the per-token views are developed; the ids

   question is whether step 1 must rerun too.  From the pod logs step 1 is about half the GPU time (roles: step 1
    9.6 h, step 2 8.0 h; traits: 22.1 h and 19.3 h, on one 2× A100 pod each), about 150 GPU-hours and $270 over the
    four pods, plus about $350 to rejudge the new text; a step 2 rerun alone is about $240 and keeps the scores.

**Terms.**  *Raw ids*: the token ids vLLM returned for a response, in order, as generated.  *Content range*: the
half-open index range `[start, end)` into the raw ids of the tokens behind the stored text.  *Plan*: the leaked
thinking, everything up to and including the last `</think>`.  *Text path*: today's step 2, which re-encodes the
stored text.  *Ids path*: step 2 prefilling the raw ids.  *Strip*: step 1's `strip_leaked_think` clean-up.

## 2. What the code does today (the parts that change)

- **Step 1.**  [generation.py](../../../assistant_axis/generation.py) `generate_batch_detailed` sends each prompt as
ids (`prompt_token_ids`, since 2026-10-13), keeps `.text` and `.finish_reason`, strips the plan when the family's
`response_cleanup` is `strip_leaked_think` (`</think>` present, `<think>` absent: `text[rfind('</think>')+8:].strip()`,
`thinking_stripped = True`), and flags `thinking_suspected`.  `generate_for_role` writes the record (the keys after
`conversation` are additive; steps 2 and 3 read by key).  `RoleResponseGenerator.save_responses` writes JSONL
through local staging.  [1_generate.py](../../../pipeline/1_generate.py) writes the side-car record
(`build_generation_run_record`: `response_cleanup` is one of its `SETTINGS_KEYS`, so two runs with different
clean-up into one directory are refused unless `--allow_mixed_settings`).
- **Step 2.**  [2_activations.py](../../../pipeline/2_activations.py) `_extract_batches` calls
`ActivationExtractor.batch_conversations` ([activations.py](../../../assistant_axis/internals/activations.py)),
which builds the ids and spans itself (`encoder.build_batch_turn_spans`), pads, runs the model under forward hooks
and returns `(num_layers, batch, seq, hidden)` plus metadata; `_extract_batches` builds the spans a second time for
`SpanMapper.map_spans` ([spans.py](../../../assistant_axis/internals/spans.py)), which averages each span for slot 0
and finds the header by searching back from the span's start (`_find_header`, within `header length + 7` tokens)
for slots 1 to N.  `SpanMapper.prefix_means` reuses the spans.  For Qwen (`span_builder` `chatml`),
`_build_turn_spans_qwen` scans `<|im_start|>role ... <|im_end|>`, drops think tokens, and pops whitespace-only
tokens from both ends of the content.  Records are keyed `{label}_p{prompt}_q{question}`.
- **Readers of the stored text** (must see no change): [3_judge.py](../../../pipeline/3_judge.py) (`pending_prompts`
reads the assistant turn's `content`; `mark_truncated` appends the marker to a copy),
[axis_judge_correlation.py](../../../results_analysis/axis_judge_correlation.py) (`_load_responses_jsonl`),
[opening_form_experiment.py](../../../data_analysis/opening_form_experiment.py),
[role_rubric_experiment.py](../../../data_analysis/role_rubric_experiment.py),
[sample_trait_responses.py](../../../data_analysis/sample_trait_responses.py).  The golden gate
[test_step2_qwen3_golden.py](../../../pipeline/tests/test_step2_qwen3_golden.py) compares step 2 on fixture
records (`conversation`, `label`, `prompt_index`, `question_index` only) bit for bit with commit 828817a4's output;
**its fixture is never regenerated.**

## 3. The record contract

The one thing both steps share.  Three fields are added to every response record, after the existing ones; nothing
existing changes value.  Readers that do not know them ignore them.

| field | type | meaning |
|---|---|---|
| `response_token_ids` | list of int | `output.outputs[0].token_ids`, verbatim: the plan, any special token the model sampled, the stop token if vLLM includes it.  Never edited. |
| `content_token_range` | `[start, end]` or `null` | the tokens of `response_token_ids[start:end]` are the ones behind `conversation[...]["content"]`: `start` is 0, or the index after the last `</think>` id when the plan was stripped; `end` is the length minus trailing special tokens (the stop) and minus trailing tokens that are a partial character (the cap landed inside one).  Checked at write time (§ 4.2); `null` when the check fails. |
| `thinking_token_range` | `[0, k]` or `null` | the plan's tokens: `response_token_ids[0:k]`, `k` the index after the last `</think>` id.  Written whenever the strip rule's detection fires (`</think>` in the text, `<think>` not), whether or not the strip was applied, so under `--response_cleanup keep` it is the record of where the plan is.  `null` when nothing was detected, or when `</think>` has no single id in the ids (spelled in pieces).  In strip mode `content_token_range.start == k`; in keep mode `content_token_range` starts at 0. |
| `raw_text` | string, only when `thinking_stripped` | the text before the strip, for text readers (they have no tokenizer).  Absent otherwise. |

`thinking_stripped` keeps its meaning: the strip rule fired and changed `content`.  (Roger, 10.1: the plan's range
is stored rather than recreated; a boolean would say only that it exists.)  `thinking_suspected`, the text heuristic
for a plan with no `</think>` at all, stays a flag: there is no token boundary to point at.  The prompt ids are **not**
stored: nothing in them was sampled, step 2 renders them from the same template, and the side-car's
`sample_prompt_ids` check already ties the two renderings together.  Cost: a response averages 576 tokens; the ids
add about 2.7 KB per record as compact JSON, 67% on the response files, about 4 GB over an extraction's 1.5 million
responses.

The boundary-whitespace rule stays in step 2: the range is "the tokens behind the text", and step 2 pops
whitespace-only tokens from its ends as the text path does today, so that a clean response gives the same slot-0
positions on both paths.

*Changed 2026-11-03 (Roger): the ids path trims nothing.  The chatml builder's trim exists because its think filter
leaves two header tokens in the span (the `\n` after `assistant` and the `\n\n` after `</think>`), and its trailing
half has no recorded reason; it is a Qwen scanner's patch and must not become a policy of the ids path or of other
families.  The pointer is made exact at the source instead (§ 4.1 and § 4.2 below), the text path keeps its trim
so that variant (1) is today's step 2, and the one difference that remains, a whitespace-only token the model
generated at the end of an unstripped reply (13 of 20,000 October responses), is measured with the rest.  The
explicit header skip that would retire the trim is a text-path refactor for a re-extraction, not this build.*

## 4. Step 1: the build

### 4.1 Keep the ids

In `generate_batch_detailed` ([generation.py](../../../assistant_axis/generation.py)): each detail dict gains
`token_ids = list(output.outputs[0].token_ids)` (ints; vLLM may hand a tuple or an array) and `leaked`, the
detection before any strip.  The strip itself is unchanged in what it does to `text`.  `generate_for_role`
writes the three new keys (and `raw_text` when stripped) after `thinking_suspected`.

*Changed 2026-11-03 (Roger): the strip becomes surgical.  It cuts everything up to and including the last `</think>`
and then exactly one `\n\n` if that is what immediately follows, and nothing else: `</think>\n\n\n` keeps its third
newline, and whitespace the model wrote at either end of its reply stays.  The `.strip()` goes.  The strip warning
counts the stripped texts that still begin or end with whitespace.*

### 4.2 Compute and check the two ranges

A new module-level function, `token_ranges(tokenizer, token_ids, text, *, leaked, stripped, think_end_id,
special_ids) -> Tuple[Optional[Tuple[int, int]], Optional[Tuple[int, int]]]` (the thinking range, the content
range), pure and unit-testable:

1. If `leaked`: `k = (last index of think_end_id) + 1` and the thinking range is `(0, k)`; if there is no such id
   (the plan's `</think>` was spelled in pieces, or the text came from somewhere else), the thinking range is
   `None`, and when `stripped` the content range is `None` too (its start is unknown): return.  If not `leaked`,
   the thinking range is `None`.
   `start = k` if `stripped`, else 0.
2. `end = len(token_ids)`; while `end > start` and `token_ids[end-1]` is a special id, `end -= 1` (the stop token).
3. While `end > start` and `tokenizer.decode(token_ids[start:end], skip_special_tokens=True)` ends with U+FFFD,

   `end -= 1` (the partial character at the cap; at most three steps).
4. Check: `decoded = tokenizer.decode(token_ids[start:end], skip_special_tokens=True)`; when not `stripped`,

   `decoded == text` must hold; when `stripped`, `decoded.strip() == text` (step 1 stripped whitespace with the
    plan).  Return `(start, end)` on success, `None` on failure.

*Changed 2026-11-03 (Roger), with the surgical strip: the cut is `k + 1` when `token_ids[k]` decodes to exactly
`\n\n` (one token in Qwen's vocabulary), else `k`; the thinking range is `(0, cut)` in both modes (the cut the
strip makes or would make), the content range starts at the cut when stripped, so the two ranges partition the
generated ids; and the check is plain `decoded == text` in every case, no `.strip()` tolerance.  If the model ever
emits `\n\n\n` as a single token right after `</think>`, the check fails, the content range is null and counted, and
the record takes the text path; expected to be nil.*

`generate_batch_detailed` calls it per response with `self.llm.get_tokenizer()`, counts the null content ranges, and logs
per batch (`WARNING` when any: "N of M responses: the stored ids do not decode to the stored text; their range is
null and step 2 will take the text path for them").  A `None` never stops the run.  Whether vLLM's incremental
detokenizer and a plain `decode` agree on every byte is one of the smoke run's questions (§ 8); if they disagree on
a class of responses, the comparison in step 4 is loosened only after Roger has seen the cases.

### 4.3 The optional strip

`--response_cleanup {family,keep}` on [1_generate.py](../../../pipeline/1_generate.py), default `family` (the
family row's rule, `strip_leaked_think` for Qwen3, exactly today's behaviour).  `keep` leaves the text as vLLM
returned it: `content` is the raw text, `thinking_stripped` is false, `thinking_token_range` says where the plan
is, `content_token_range` starts at 0, no `raw_text`.  The effective rule reaches the side-car's
`response_cleanup` (`"keep"` or the family's name) through `response_cleanup_for(family, override=...)`, so
`settings_differences` refuses a mix in one directory as it does today.  *Changed 2026-11-03 (Roger): the side-car
records the clean-up applied, `none` under `keep`, and the flag beside it as `response_cleanup_override`, so that
`keep` on a family whose rule is `none` is not a difference (the two do the same to the text); the build had
recorded the word `keep` and refused that pair ([build_report.md](./build_report.md) § 4 item 3).  After the review
of the same day: the side-car also records `response_cleanup_version` (2 = the surgical cut; 1 = the October
rule), compared by the settings check; and a keep tree takes the ids path in step 2 (`--token_source text` refused,
`auto` promoted to `ids`), because the real template re-renders a kept plan inside a think block on the text path
(the review in [build_report.md](./build_report.md)).*  `RoleResponseGenerator` and `VLLMGenerator`
take the override as a constructor argument; `run_pipeline.sh` gains `--response-cleanup keep` passed through to
step 1 (the step-1 invocation blocks are the two `uv run 1_generate.py` calls in
[run_pipeline.sh](../../../pipeline/run_pipeline.sh)).

`family` is the default **for now**: the TODO in [AGENT_NOTES.md](../../../AGENT_NOTES.md) § "TODO: keep leaked
thinking instead of stripping it?" is what will settle the default going forward (Roger, 2026-11-02), from the
sample's three variants; the same holds for step 2's `--content_span` default (§ 5.5).

### 4.4 Documentation

[pipeline/README.md](../../../pipeline/README.md) § "Response records" gets the four fields and the range's
definition; the side-car paragraph says `response_cleanup` can now be `keep`; the step 2 section gets § 5's flags.
The record-format sentence in `generate_for_role`'s comment is extended.

### 4.5 Tests (step 1)

The fake vLLM in [test_generation_response_fields.py](../../../assistant_axis/tests/test_generation_response_fields.py)
builds text from ids by `chr`; give its outputs `token_ids` and give the fake tokenizer a matching `decode`
(`"".join(chr(i))`, special ids dropped, a chosen id decoding to a partial character for the cap case).  New tests,
each a small record through `generate_for_role`:

1. the ids are stored verbatim, stop token included, and the three new keys sit after the existing ones; every

   pre-existing key has the value it had (the test compares against the record the old code wrote, keys by keys);
2. a clean response: range `[0, len - stop]`, `decode(range) == content`;
3. a stripped response: `thinking_stripped` true, `raw_text` is the text before the strip, `thinking_token_range`
   is `[0, k]` with `k` after the last `</think>` id, `content_token_range.start == k`, and the content range
   decodes to `content` after `strip()`;
4. a plan whose `</think>` has no single id: both ranges `null`, `thinking_stripped` true, `raw_text` present, the
   response still written, the count logged;
5. the cap inside a character: `end` steps back over the partial token(s);
6. a sampled special token mid-response: kept in the ids, absent from the text, the check passes;
7. `--response_cleanup keep`: `content` is the raw text, `thinking_stripped` false, `thinking_token_range` the
   same `[0, k]` as in strip mode, `content_token_range` from 0, no `raw_text`; the side-car records `keep`; a
   rerun with `family` into that directory is refused
    (extend [test_1_generate.py](../../../pipeline/tests/test_1_generate.py)'s side-car tests);
8. `token_ranges` as a pure function on every branch above, including an empty response, a response that is only
   a plan (thinking range the whole thing, content range empty), and `leaked` without `stripped` (keep mode).

The existing six tests in that file and the 31 in `test_1_generate.py` pass unchanged.

## 5. Step 2: the build

### 5.1 Which path a record takes

`process_role` reads the field per record.  `--token_source {auto,ids,text}` on
[2_activations.py](../../../pipeline/2_activations.py), default `auto`:

- `auto`: a record with `response_token_ids` and a non-null `content_token_range` takes the ids path; any other
record the text path.  A file may mix (the null-range records); the counts are logged per entity and written in
the activation file's metadata (`token_source: {"ids": n, "text": n, "range_null": n}`).
- `ids`: every record must have ids and a range; otherwise the entity raises (and the worker exits 1 at the end,
as for any failed entity).
- `text`: the ids are ignored; this is the comparison arm of § 9, and it must be bit-identical to today's step 2.

The golden fixture's records have no ids, so the gate exercises `auto` on the text path.

### 5.2 Building the sequence on the ids path

For a record on the ids path, per conversation:

1. `prompt_ids = prompt_token_ids(tokenizer, conversation_without_the_assistant_turn, template_kwargs)`, the very

   function step 1 used to send the prompt ([generation.py](../../../assistant_axis/generation.py)); step 2 imports
    it rather than re-implementing the rendering.
2. `response_ids = record["response_token_ids"]` with trailing special ids removed (the stop token: the template's

   end of turn is appended next, and nothing averaged comes after the content, so a double or a missing stop could
    not change a slot; removing it keeps the sequence well formed).
3. `turn_end_ids`: what the template writes after the assistant content, derived once from the tokenizer the way

   [chat_layout.py](../../../assistant_axis/internals/chat_layout.py) derives the header (render the probe
    conversation with an assistant turn, take the ids after the probe content); for Qwen3 `<|im_end|>\n`.
4. `full_ids = prompt_ids + response_ids + turn_end_ids`; the assistant span is

   `[len(prompt_ids) + start, len(prompt_ids) + end)` from the record's range, then the chatml boundary trim
    (pop whitespace-only tokens from both ends) applied through a helper factored out of `_build_turn_spans_qwen`
    so that both paths share the one rule; the span dict has the keys the text path's spans have (`turn`, `role`,
    `start`, `end`, `n_tokens`, `text`) plus `header_anchor = len(prompt_ids)`.  *Changed 2026-11-03 (Roger): no
    trim on the ids path; the span is the stored range as stored, for every family (§ 3's note).  The helper stays
    the chatml builder's own.*

Only the assistant span is built (the text path also builds the user span, whose mean is computed and discarded;
`turn_roles` then holds one role, and the single-assistant-turn rule still holds).  `max_length` applies to
`full_ids` as today (a Qwen3 prompt of about 250 tokens plus at most 1,024 generated stays under 2,048).

### 5.3 The header slots

`SpanMapper.map_spans` searches for the header backwards from `span.get("header_anchor", start_idx)`.  On the text
path nothing changes (no anchor, the span's start as today).  On the ids path the anchor is the prompt's end, so
the header is found whatever lies between it and the content (the plan would otherwise put it out of the
`N + 7` search reach and leave slots 1 to N NaN).  The same verification as today: ids compared, mismatches
recorded, the tolerance of `allowed_header_mismatches` unchanged.

### 5.4 Threading the ids through the extractor

`ActivationExtractor.batch_conversations` is split: a new `batch_token_ids(batch_full_ids, batch_spans, span_metadata, layer, max_length)` does the padding, hooks, forward pass and metadata from prepared ids;
`batch_conversations` builds the ids and spans as today and calls it, so its output is unchanged (the golden gate
checks).  `_extract_batches` builds `(full_ids, spans)` per conversation by that conversation's path, assembles the
batch structures `build_batch_turn_spans` would have (`conversation_lengths`, `conversation_offsets`, the per-span
`conversation_id`, `local_*`, `global_*`), and calls `batch_token_ids`; from there `map_spans`, `prefix_means` and
the saving are untouched.  The text path's conversations go through `encoder.build_turn_spans` exactly as now, so
a batch of text-path records produces byte-identical activations.

### 5.5 Slot 0 over the whole turn (the third variant)

`--content_span {range,turn}`, default `range`.  `turn` moves the span's start to `len(prompt_ids)` (the plan
included in slot 0; the boundary trim still applies *— no trim since 2026-11-03, § 3's note*), ids path only;
refused with `--token_source text`.  Recorded
in the metadata (`content_span`).  This is variant (3) of § 9 and the TODO's "plan in the prefill and in slot 0".
Built now, while the code is open (Roger, 2026-11-02); `range` is the default for now, and the TODO decides the
default going forward from the sample's three variants.

### 5.6 `--verify_ids N`

Like `--verify_spans`: before extracting a worker's first entity, for its first N ids-path conversations, build
both paths' `full_ids` and run both through the model (two small forward passes).  Report per conversation whether
the two id sequences are identical, else how many positions differ and of what kind (a re-split, a special token,
a plan, a partial character), and when they are identical whether the eight slots are bit-identical.  **Identical
ids with differing slots is a bug and exits 1**; anything else is reported and the run continues.  The smoke run
passes `--verify_ids 20`.

*Changed 2026-11-03 (Roger), with the trim gone from the ids path: identical ids are followed by a comparison of
the two assistant spans.  Identical spans: both passes run and the slots must be bit-identical, as above.  A text
path span equal to the ids path's less whitespace-only tokens at its ends: reported as "boundary whitespace (the
text path's trim)", counted, no model pass.  Any other span difference: a bug, exit 1.*

### 5.7 Metadata and the side-car check

The activation file's `metadata` gains `token_source` (the counts), `content_span`, and `response_cleanup` as the
side-car recorded it; `check_generation_config` logs the recorded clean-up (it does not refuse on it: the range
carries the information).  Step 4 copies metadata into the vector as it does; step 5 keeps its refusals on
`model_type` and `template_kwargs` and refuses nothing new (a tree is one path by construction of the sample;
mixed sources are visible in the metadata).  `run_pipeline.sh` passes `--token-source`, `--content-span` and
`--verify-ids` through to step 2.

### 5.8 Tests (step 2)

On the fakes ([internals_fakes.py](../../../assistant_axis/tests/internals_fakes.py): the Qwen3-like word-level
tokenizer has `decode`, and `make_fake_probing_model`), beside the 28 tests of
[test_2_activations_extract.py](../../../pipeline/tests/test_2_activations_extract.py):

1. **Equivalence.**  A record whose stored ids equal the re-encoding of its content: `--token_source ids` and

   `--token_source text` give bit-identical activation files (all eight slots, the prefix means, every key).
2. **Text arm is today's step 2.**  `--token_source text` on records with ids gives the same bytes as the same

   records with the ids removed.
3. **The plan is prefilled, slot 0 excludes it.**  A stripped record whose ids carry `plan ...  \n\n

   content`: the sequence the model receives (captured at the forward hook) contains the plan ids after the  header; slot 0 is the mean over the content positions only; slots 1 to 7 are the seven header positions, which  lie before the plan; with` --content_span turn` slot 0 is the mean over plan and content.
4. **Header anchor.**  A plan longer than the search distance: the header is still found; on the text path the

   anchor key is absent and the search is unchanged.
5. **Null range, mixed file.**  A file of two records, one with a null range: the first takes the ids path, the

   second the text path; counts in the metadata; `--token_source ids` raises on it.
6. **Stop token and end of turn.**  Ids ending in the stop token and ids without it give the same slots; the

   sequence ends in the template's end of turn once.
7. **A sampled special token** inside the content: in the prefilled sequence; averaged into slot 0 (it was

   generated); the text path's sequence lacks it.
8. **Partial character at the cap**: the range's `end` is honoured; nothing past it is averaged.
9. `--verify_ids`: reports on a mixed set; exits 1 when identical ids give different slots (monkeypatch the

   second pass to perturb one value).
10. `batch_token_ids` **refactor**: `batch_conversations` output is unchanged on the golden records (the golden gate

    itself, plus a direct comparison of the two entry points on one batch).
11. **Golden gate** untouched and passing.

## 6. Build order and guards for the coding agent

1. Work in a worktree on a branch off `anthropic-vllm-uv`; one commit per numbered part (4.1-4.3, 5.1-5.6), each

   with its tests, and a final commit for the READMEs.  Run `uv run pytest assistant_axis/tests pipeline/tests -q`
    after every part; the suite must be green at every commit.
2. The golden fixture is never regenerated or edited; if the gate fails, the change is wrong.
3. The text path is not refactored beyond what § 5.4 needs; byte-identical output is the acceptance test for every

   step 2 change.
4. Nothing in this build touches a pod, a volume or the October tree; the agent never runs vLLM or a model.  It

   never reads outside the repository (and `~/.claude`, the session scratchpad, `/tmp`); it never looks in
    `~/.cache` to see whether a model or tokenizer is present; it asks.
5. Every `.md` it writes or edits for Roger hotlinks every file and entity it names, with paths relative to the

   document.
6. It reports what it changed, what it tested, and anything in this plan that turned out not to match the code,

   rather than working around it.

## 7. What is deliberately not in this build

- The accumulator hook for the steering statistics (per-token norms, per-layer covariance) and the per-token dump
for the display work.  `_extract_batches` after § 5.4 holds `full_ids`, the spans and the activations of a batch
in one place, which is where those consumers will plug in; they are a later plan, once Roger has developed them.
- Any change to step 3's judged text.  Whether the judge should see the plan is item 3 of the TODO.
- Re-extracting anything.  The October tree stays as it is.

## 8. The smoke run (on a pod, before the sample)

One entity (gamer, 500 responses: the heaviest leaker) through steps 1 and 2 on a fresh small tree, about ten
minutes of GPU plus two model loads, about $1 on a 1× A100, confirmed with Roger first.  It answers the two things
the plan assumes and cannot check locally:

1. whether vLLM's `token_ids` include the stop token (either is handled; the record says which);
2. whether `decode(token_ids[start:end])` equals vLLM's `.text` on every response, so that the range check's `null`

   count is 0 apart from the partial-character cases; a class of mismatches goes to Roger before anything else runs;
3. `--verify_ids 20`: identical ids give bit-identical slots.

## 9. The sample

**Entities (21, 10,500 responses):**

| group | entities | measures |
|---|---|---|
| heavy leakers | [gamer](../../../data/roles/instructions/gamer.json), [aural_vark](../../../data/traits/instructions/aural_vark.json), [plugged_in](../../../data/traits/instructions/plugged_in.json), [millennial](../../../data/traits/instructions/millennial.json), [stream_of_consciousness](../../../data/traits/instructions/stream_of_consciousness.json), [child](../../../data/roles/instructions/child.json), [gen_z](../../../data/traits/instructions/gen_z.json), r_competitor__aural_vark ([competitor](../../../data/roles/instructions/competitor.json) × aural_vark), r_rebel__aural_vark ([rebel](../../../data/roles/instructions/rebel.json) × aural_vark) | the plan effect |
| cap-heavy | [thorough](../../../data/traits/instructions/thorough.json) (319 of 500 capped), [researcher](../../../data/roles/instructions/researcher.json) (276), [verbose](../../../data/traits/instructions/verbose.json) (253), [specialist](../../../data/roles/instructions/specialist.json) (264) | clipping, partial characters |
| controls | three roles and three traits drawn at random (seeded, the script names them) from entities with no stripped response and at most 10 capped ones | the base rate: re-splits and special tokens |
| default | `default` | the pipeline's baseline; step 5 |

Generated with the new step 1 under the family clean-up (strip; the `keep` flag is built and unit-tested but not
needed here: the three vector variants come from one strip-mode tree), into
`runpod_workspace/qwen/qwen-3-32b Roger sample-ids/` (name open), then:

- step 2 three times on the same responses: variant (1) `--token_source text` (today's path), (2) `--token_source ids` (plan in the prefill, slot 0 after it), (3) `--token_source ids --content_span turn` (plan in slot 0 too);
each into its own activations/vectors directories (the driver's `--judge-prompt-version`-style suffixing, or three
sibling trees sharing the responses by copy: 10,500 records are about 40 MB);
- step 3 once (the judged text is the same in every variant; the scores are copied to the other two), steps 4 and 5
per variant.

**Cost** from the October pace (4.9 responses/s for step 1, 5.9 for step 2 on a 2× A100 pod at $3.58/h): step 1
about 36 min, step 2 three times about 90 min, three model loads about 30 min, about $10; step 3 about 10,500
luna calls (two per combination response) about $2.  About $12, under the $20 line; the flags are still quoted to
Roger before launch.

**Measurements**, in order of cost:

1. *Tokens* (free, from the records): per response, the stored ids against the re-encoding of its content:

   identical, or differing at how many positions and why (re-split, special token, partial character, plan).  This
    closes the lower bound of § 1.
2. *Responses*: per response and layer, slot 0's cosine and relative norm difference between variants (1) and (2),

   split by class (clean, capped, stripped, special-token); the seven header slots must be bit-identical wherever
    the header ids are.
3. *Entities*: the step-4 vector's cosine between (1) and (2), and between (2) and (3), per slot and layer, against

   the floor: the same entity's new vector against its October vector (sampling noise at T = 0.7, free: the October
    vectors exist), and the rcomb/tcomb half-axis cosines of 0.98-0.99 as the same floor at axis level.
4. *Axes and ρ*: each sampled entity's projection on the 61 judged axes under each variant, the shift in units of

   the spread of all entities' projections on that axis; then, where the judge caches cover the sampled entities,
    ρ recomputed with the sample's vectors substituted into an APFS clone of the October tree, per variant (the
    judge-tier session's `judge_tier_robustness.py` is the tool; whether its caches cover these entities is checked
    before this item is promised).

**The decision** (Roger, 10.4): measure first, then analyse and assess; no exact rule is codified now.  The
reading he set: if the path difference is significantly smaller than the existing noise sources on activations,
axis directions and ρ values, there is no point in rerunning; if it is comparable or larger, the October data is
re-extracted (§ 1, decision 4) before other models are run.  The noise sources to set it against are the ones in
items 2 to 4: sampling noise per entity (new vector against October's), the half-axis cosines, and the spread of
projections and ρ.  Two readings the measurements separate: a heavy leaker that moves while the controls do not
means the plan effect is real and confined to those entities; a control that moves means re-tokenization itself
matters.

## 10. Decisions (Roger, 2026-11-02)

All five open items were settled on the day the plan was written, in his comments on this file and the discussion
that followed.

1. **Names.**  The field names `response_token_ids`, `content_token_range`, `raw_text` and the flag names
   `--response_cleanup`, `--token_source`, `--content_span`, `--verify_ids` stand.  One amendment from the
   discussion: the boolean `thinking_leaked` is replaced by `thinking_token_range`, the plan's token range, so that
   it is stored rather than recreated (§ 3).
2. **The sample tree's layout** (one name, three trees or suffixed directories): the session's choice.
3. **Variant (3) is built now**, while the code is open (§ 5.5), and runs in the first sample.  The TODO in
   [AGENT_NOTES.md](../../../AGENT_NOTES.md) § "TODO: keep leaked thinking instead of stripping it?" is what
   determines the default behaviour going forward; until then `--content_span range` and `--response_cleanup
   family` are provisional defaults.
4. **No codified threshold.**  Measure first, then analyse and assess: if the path difference is significantly
   smaller than the existing noise sources on activations, axis directions and ρ values, there is no point in
   rerunning; if it is comparable or larger, the October data is re-extracted (§ 9's closing paragraph).
5. **The coding agent is Opus**, per the standing preference: one agent for both parts, step 1 first.
