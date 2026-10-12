# Coding plan: the extraction pipeline for other model families

Written 2026-10-12 (Fable) in the [PLAN_FORMAT.md](../trait_gap_generation/PLAN_FORMAT.md) shape,
as far as it fits a pipeline change, from the pipeline review of 2026-10-12 (the record:
[escalations.md](../code_review_2026-10-12/escalations.md), sections P1-P5)
and Roger's decision of the same day: "That's all qwen-specific code.  We'll likely be starting
to do other models soon ... Likely model families are Llama, OLMo, and OSS, plus anything Lu et
al. used.  That basically covers thinking and no-thinking models, with various header sizes."
Decision: **generalise now, by mechanism rather than by model, so that the Qwen3-32B layout
stays byte-identical and a new family costs a table row.**  Roger's review comments go into
this file.  Nothing here has been run; no code is changed by this plan.

## Terms used below

- **Entity**: a role, a trait, a combination (`r_<role>__<trait>` / `t_<role>__<trait>`) or
  `default`; its **stem** is its file name without extension (`absolutist`, `r_activist__abstract`).
- **Chat template**: the Jinja template in a tokenizer that turns a list of
  `{"role", "content"}` messages into the token string the model is trained on.  The
  **generation prompt** is what the template appends after the last user turn to make the
  model speak (`add_generation_prompt=True`): for Qwen 3 with thinking off it is
  `<|im_start|>assistant\n<think>\n\n</think>\n\n`.
- **Header tokens**: the tokens between the end of the previous turn and the first token of the
  assistant's content.  For Qwen 3 with thinking off these are the seven
  `<|im_start|>`, `assistant`, `\n`, `<think>`, `\n\n`, `</think>`, `\n\n`.
- **Slot**: the first axis of every activation, vector and axis tensor
  (`(n_slots, n_layers, hidden)`).  **Slot 0 is the body mean**, the mean of the residual stream
  over the response's content tokens; **slots 1..N are the single positions of the N header
  tokens**, in order.  The **8slot** tree
  ([runpod_workspace/qwen/qwen-3-32b Roger 8slot](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/))
  is the current Qwen3-32B dataset, 1 + 7 slots; its predecessor had 1 + 3 (the "4-slot" data, lacking the thinking block).
- **Layer index**: index j of the layer axis is the output of decoder layer j (a forward hook on
  `model.layers[j]`, Hugging Face `hidden_states[j+1]`); unchanged by this plan.
- **Family**: what the chat template, the reasoning switch and the special tokens have in common
  across the models of one architecture.  Keyed on `model.config.model_type` (`qwen3`, `llama`,
  `gemma2`, `olmo2`, `olmo3`, `gpt_oss`), which is a field of the model's `config.json`, not a
  substring of its name.
- **Side-car**: a small file written beside a step's outputs that records how they were made
  (as step 3's `usage.json` and `judge_rubric.json` are).

## 1. Goal, scope, non-goals

**Goal.**  [`pipeline/1_generate.py`](../../pipeline/1_generate.py) and
[`pipeline/2_activations.py`](../../pipeline/2_activations.py) (library:
[`generation.py`](../../assistant_axis/generation.py),
[`internals/model.py`](../../assistant_axis/internals/model.py),
[`internals/conversation.py`](../../assistant_axis/internals/conversation.py),
[`internals/activations.py`](../../assistant_axis/internals/activations.py),
[`internals/spans.py`](../../assistant_axis/internals/spans.py),
[`models.py`](../../assistant_axis/models.py)) run on Llama 3.3 70B, Gemma 2 27B, OLMo and
gpt-oss as they run on Qwen3-32B today: the header slots are derived from the model's own chat
template at startup, the few things that are genuinely per family live in one table that both
steps read, and anything the table does not know fails before a GPU-hour is spent.  The
Qwen3-32B output is byte-identical to today's.

**Scope.**  Steps 1 and 2 and their library; the metadata that steps 4 and 5 copy; a step-1
side-car and the step-2 check against it; loud failures at the analysis and steering sites that
assume the Qwen3 slot layout; tests; [`pipeline/README.md`](../../pipeline/README.md) and the
[`AGENT_NOTES.md`](../../AGENT_NOTES.md) sections.

**Non-goals.**  No change to what is averaged for Qwen3 (slot 0's token set, the seven header
positions), to the layer convention, or to any recorded tree.  No thinking-on extraction (Roger:
step 1 never generates with thinking on; `--thinking` goes).  No multi-turn conversations (the
single-turn contract is asserted, not relaxed).  No steering on other models beyond two guards
(§ 5.6).  No capping configs, no `MODEL_CONFIGS` target layers for new models beyond a stub row.
Not the October extraction itself, and none of the other step-1 findings — per-item failures
keeping exit 0 ([P1 D1](../code_review_2026-10-12/escalations.md#p1-d1-per-item-failures-keep-exit-0)),
the thinking strip and the leaked-thinking responses
([P1 D4](../code_review_2026-10-12/escalations.md#p1-d4-the-thinking-strip-handles-only-a-leftover-think-tag)),
the package's eager imports ([P1 D5](../code_review_2026-10-12/escalations.md#p1-d5-eager-imports-in-the-package-init)),
a missing goal-list name being only a WARNING
([P1 D7](../code_review_2026-10-12/escalations.md#p1-d7-a-missing-goal-list-name-is-only-a-warning)),
a second BOS on Gemma or Llama from text prompts
([P1 D8](../code_review_2026-10-12/escalations.md#p1-d8-a-second-bos-on-gemma-or-llama-from-text-prompts);
the tally has no P1 D6) — nor the step-3 review
([P3](../code_review_2026-10-12/escalations.md#p3-step-3-judging), judging) or the step-4/5 review
([P4](../code_review_2026-10-12/escalations.md#p4-steps-4-and-5-the-scanner-the-driver-file-io),
vectors, axis, scanner, driver) (they are decided elsewhere; § 15 Q4 asks about folding the
record fields of [P1 D2](../code_review_2026-10-12/escalations.md#p1-d2-resume-skips-any-entity-whose-file-exists),
resume skipping any entity whose file exists, and
[P1 D3](../code_review_2026-10-12/escalations.md#p1-d3-responses-carry-no-finish-reason-thinking-flag-seed-or-question-id),
the missing finish reason, thinking flag, seed and question id, into the side-car).

## 2. Decisions already made

| decision | reason | source |
|---|---|---|
| Generalise **by mechanism**: slots come from the template, not from a list per family. | a hard-coded list is wrong for the next template (Qwen3-Instruct-2507 has no think block and NaNs every header slot today) | Roger 2026-10-12; [P2 D3](../code_review_2026-10-12/escalations.md#p2-d3-header-token-list-hard-coded-and-the-family-detected-by-substring) (the header list hard-coded, the family detected by substring) |
| Qwen3-32B stays **byte-identical**: the same seven header tokens, the same body mean, the same tensors from the fake-model harness. | the 8slot tree and every analysis on it | Roger 2026-10-12 |
| A **per-family table keyed on `model.config.model_type`**, read by step 1 and step 2, for what is genuinely per family; **a new family costs a table row**. | the two steps must agree on what a conversation looks like | Roger 2026-10-12 |
| **Remove `--thinking`**; **validate `--layers`** (sorted, unique, in range); **assert exactly one assistant span** per conversation instead of picking by parity. | [P2 D1](../code_review_2026-10-12/escalations.md#p2-d1-layers-flag-accepts-negative-duplicate-or-unsorted-values) (`--layers` unvalidated), [P2 D2](../code_review_2026-10-12/escalations.md#p2-d2-thinking-flag-silently-adds-the-header-tokens-to-the-body-mean) (`--thinking` adds the header tokens to the body mean), [P2 D4](../code_review_2026-10-12/escalations.md#p2-d4-assistant-turns-picked-by-parity-not-by-span-role) (assistant turns picked by parity) | [review P2](../code_review_2026-10-12/escalations.md#p2-step-2-activations-and-internals) |
| Downstream consumers: **no change to the analyses' Qwen canonical choices** (slot 6 = `</think>` defaults, slot 7 for the PC round trip); a non-Qwen tree is self-describing and the hard-coded sites **fail loudly**. | Roger 2026-10-12 | this brief |
| Layer index j = output of decoder layer j, unchanged; nothing retroactive. | P2/P5 verified it; the 8slot record stands | [review P2](../code_review_2026-10-12/escalations.md#p2-step-2-activations-and-internals), [P5](../code_review_2026-10-12/escalations.md#p5-end-to-end-contracts) |
| An **unknown `model_type` refuses to run** in both steps (no fallback to a body-mean-only layout, no silent template kwargs). | P2 made the unknown-family case warn; Roger wants failure before GPU time | this plan, refining P2's fix for the unknown family, which now warns ([P2 D3](../code_review_2026-10-12/escalations.md#p2-d3-header-token-list-hard-coded-and-the-family-detected-by-substring); § 15 Q8) |

**Refinements this plan makes to the agreed shape** (each with its reason; Roger can reverse any):

1. **Derive the header from the stored-turn rendering, and use the generation-prompt difference
   as the cross-check**, not the other way round (§ 5.1).  Step 2 computes on the stored
   conversation (user turn + assistant content), so the slots must be the tokens that rendering
   puts before the content.  For Qwen 3, Llama 3, Gemma 2 and OLMo 2 the two are the same
   sequence; for gpt-oss they are not (the generation prompt is `<|start|>assistant`, the stored
   final turn's header is `<|start|>assistant<|channel|>final<|message|>`), and the difference
   method alone would give slots that never precede the content.
2. **Step 1 hands vLLM token ids, not rendered text, for every family** (§ 5.3): the prompt ids
   are then, by construction, the prefix step 2 renders, and the double-BOS hazard
   ([P1 D8](../code_review_2026-10-12/escalations.md#p1-d8-a-second-bos-on-gemma-or-llama-from-text-prompts):
   a second BOS on Gemma or Llama from text prompts) does not arise.  Qwen3's ids are unchanged (its tokenizer adds no special tokens to text).
3. **The table lives in a new module**, [`assistant_axis/model_families.py`](../../assistant_axis/model_families.py)
   (not there yet), not in [`models.py`](../../assistant_axis/models.py) (§ 5.2, reasons there).
4. **A step-1 side-car**, `generation_config.json` in the responses directory, records the
   family, the template kwargs and the derived header; step 2 compares and refuses on a
   mismatch (§ 5.5).  This is the mechanism that keeps the two steps from disagreeing, and it is
   the file [P1 D2](../code_review_2026-10-12/escalations.md#p1-d2-resume-skips-any-entity-whose-file-exists)
   (resume skips any entity whose file exists) asked for.

## 3. Rule files to Read first

[`.claude/rules/nfs-io.md`](../../.claude/rules/nfs-io.md) (every write under `/workspace` goes
through `atomic_io`; the side-car too), [`.claude/rules/axis-geometry.md`](../../.claude/rules/axis-geometry.md)
(what consumes the slots), [`.claude/rules/entity-naming.md`](../../.claude/rules/entity-naming.md)
(stems, the eleven collision names), [`.claude/rules/plotting.md`](../../.claude/rules/plotting.md)
(the consumer scripts' plots are regenerated only if a change touches them),
[`.claude/rules/provenance.md`](../../.claude/rules/provenance.md),
[`.claude/rules/working-style.md`](../../.claude/rules/working-style.md) (test expectations that
change are reported, never quietly rewritten), [`CLAUDE.md`](../../CLAUDE.md) (file-access
boundary; the GPU confirmation rule for every smoke run; hotlinks), and
[`pipeline/README.md`](../../pipeline/README.md) (the step-2 "What a file holds" section is what
this plan generalises).

**File-access boundary (restated for every Opus task prompt).**  Read and write only under
`/Users/roger/Documents/GitHub/assistant-axis/` and the session scratchpad.  Never list, read or
stat anything else under the home directory, including `~/.cache/huggingface`, even to see
whether a tokenizer is downloaded: say what is needed and let Roger answer.  No model weights are
loaded on the Mac; the real-tokenizer tests (§ 9) run only when Roger has allowed the download.

## 4. Existing code to reuse

- [`assistant_axis/tests/internals_fakes.py`](../../assistant_axis/tests/internals_fakes.py):
  `make_qwen3_like_tokenizer()` (a word-level tokenizer whose chat template reproduces the Qwen3
  turns and the empty think block) and `FakeCausalLM` (hidden state after layer k at position p
  is `[p, k+1, token_id, mask]`).  Every new test is built on these; two more fake tokenizers
  are added beside them (§ 9).
- [`pipeline/tests/test_2_activations_extract.py`](../../pipeline/tests/test_2_activations_extract.py)
  and [`assistant_axis/tests/test_conversation_encoder.py`](../../assistant_axis/tests/test_conversation_encoder.py):
  the harness this plan builds on; their assertions pin the Qwen3 layout and must keep passing.
- [`assistant_axis/internals/spans.py`](../../assistant_axis/internals/spans.py) `_find_header`
  and `map_spans`: kept as they are; only where the expected header ids come from changes.
- [`assistant_axis/internals/conversation.py`](../../assistant_axis/internals/conversation.py):
  `_build_turn_spans_qwen` (pattern-matching with think-token and boundary-whitespace handling)
  and the generic `build_turn_spans` path: both kept; the dispatch changes.
- [`assistant_axis/generation.py`](../../assistant_axis/generation.py) `supports_system_prompt`
  (behavioural probe) and `format_conversation` (folds the instruction into the user turn when
  the template has no system role): kept; the family row records the expectation.
- [`assistant_axis/atomic_io.py`](../../assistant_axis/atomic_io.py) `atomic_write_text`,
  `read_text_with_retry` for the side-car.
- [`assistant_axis/axis.py`](../../assistant_axis/axis.py) `slot_labels(metadata)`: the reader
  every consumer should use; it already reads `header_tokens` and needs no change.

## 5. Design

### 5.1 Deriving the header slots from the template

New module [`assistant_axis/internals/chat_layout.py`](../../assistant_axis/internals/chat_layout.py)
(not there yet).  `derive_chat_layout(tokenizer, family) -> ChatLayout` renders three things with
the family's template kwargs (§ 5.2) and `return_dict=False` (the transformers-5 `BatchEncoding` trap [review P2](../code_review_2026-10-12/escalations.md#p2-step-2-activations-and-internals) fixed):

1. `base`: the probe conversation without an assistant turn, `add_generation_prompt=False`.
   The probe is `[system, user]` when the family supports system prompts, `[user]` otherwise,
   with fixed sentinel texts that start and end with a letter (no whitespace to merge across a
   boundary).
2. `gen`: the same with `add_generation_prompt=True`.  Require `gen[:len(base)] == base`; the
   **generation prompt** is `gen[len(base):]`, non-empty.
3. `full`: the probe plus `{"role": "assistant", "content": C}` with a sentinel `C` (and, for a
   family whose reasoning is stored, a sentinel `thinking` field: § 5.2).  Require
   `full[:len(base)] == base`.  Locate `tokenizer(C, add_special_tokens=False).input_ids` in
   `full` after `len(base)` (exactly once).  The **header** is the slice of `full` between the
   end of the stored reasoning's tokens (or `len(base)` when there is none) and the first content
   token.

Checks, each a `LayoutError` naming both sequences as decoded strings:

- the generation prompt is a prefix of `full[len(base):]` (a template that prompts generation
  differently from how it renders a stored turn would give step 2 a context step 1 never sent);
- the header is non-empty and contains no content token;
- the same header comes out with and without the system message (a template whose assistant
  header depended on it is not known, and this costs one more render);
- when the family row carries `expected_header_tokens` (Qwen3 does, § 5.2), the derived tokens
  equal it.

`ChatLayout` holds `header_ids` (tuple of int), `header_tokens` (tuple of str: **`tokenizer.decode([id])`
per id**, which gives `"\n"` for 198 and `"<|im_start|>"` for 151644, exactly the strings the
8slot metadata carries; `convert_ids_to_tokens` would give `"Ċ"` and is not used),
`generation_prompt_ids`, `model_type`, `template_kwargs`, `probe` (what was rendered) and
`search_distance = len(header_ids) + 7` (14 for Qwen3, the value `_MAX_HEADER_SEARCH_DIST["qwen"]`
has today, so `_find_header` behaves identically).

**Rendered sample, Qwen3, the probe as the tokenizer receives it** (system "You are a pirate",
user "What is law?", content "Arr matey.", `enable_thinking=False`; the real template, read from
its known text, agrees with the fake in [`internals_fakes.py`](../../assistant_axis/tests/internals_fakes.py)
on everything step 2 depends on):

```
base:  <|im_start|>system\nYou are a pirate<|im_end|>\n<|im_start|>user\nWhat is law?<|im_end|>\n
gen:   base + <|im_start|>assistant\n<think>\n\n</think>\n\n
full:  base + <|im_start|>assistant\n<think>\n\n</think>\n\nArr matey.<|im_end|>\n
header = full[len(base) : first token of "Arr matey."]
       = <|im_start|>(151644) assistant(77091) \n(198) <think>(151667) \n\n(271) </think>(151668) \n\n(271)
```

The seven ids are the `header_ids` of every 8slot vector (read from
[traits/vectors/absolutist.pt](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/traits/vectors/absolutist.pt)
on 2026-10-12: `[151644, 77091, 198, 151667, 271, 151668, 271]`), and the generation prompt
equals the header, so the cross-check passes.

**The same sample for gpt-oss, as far as the harmony format is known to me (to check against the
real template before any run):**

```
base:  <|start|>system<|message|>...Reasoning: low...<|end|><|start|>developer<|message|># Instructions\n\nYou are a pirate<|end|><|start|>user<|message|>What is law?<|end|>
gen:   base + <|start|>assistant
full (thinking stored): base + <|start|>assistant<|channel|>analysis<|message|>T<|end|><|start|>assistant<|channel|>final<|message|>Arr matey.<|return|>
header = tokens after T's last token, before "Arr":  <|end|> <|start|> assistant <|channel|> final <|message|>   (6 slots; to check)
```

Here the generation prompt (`<|start|>assistant`) is a prefix of the stored turn but not the
header; the model itself produced the channel tokens.  That is why the header is read from the
stored rendering and the family row says whether the reasoning is stored (§ 15 Q3).

### 5.2 The per-family table

New module [`assistant_axis/model_families.py`](../../assistant_axis/model_families.py) (not
there yet), importable without torch (the `AutoConfig` import is inside the lookup):

```python
@dataclass(frozen=True)
class FamilySpec:
    model_type: str                       # transformers config.model_type; the key
    template_kwargs: Mapping[str, Any]    # passed to every apply_chat_template in steps 1 and 2
    reasoning: str                        # "none" | "template_switch" | "always_on"
    reasoning_stored: bool                # always_on only: the model's reasoning is kept in the
                                          # response record and re-rendered by step 2 (Q3)
    system_prompt: str                    # "native" | "fold_into_user"; the probe verifies
    span_builder: str                     # "chatml" (the Qwen pattern path) | "generic"
    response_cleanup: str                 # "none" | "strip_leaked_think" | "harmony_final_channel"
    bos_in_template: bool                 # informational once ids are passed (§ 5.3)
    end_token: str                        # informational: closes the assistant turn
    expected_header_tokens: tuple[str, ...] | None   # asserted after derivation when set
    trust_remote_code: bool = False
    hf_load_kwargs: Mapping[str, Any] = {}           # e.g. attn_implementation for Gemma 2
    notes: str = ""
```

`FAMILIES: dict[str, FamilySpec]`; `family_for_model_type(model_type)` raises
`UnknownFamilyError` listing the known keys; `family_for_model(name_or_path)` reads
`AutoConfig.from_pretrained(name_or_path).model_type` (the `config.json`, a few KB; both steps
already fetch the tokenizer from the same place) and looks it up.
`QWEN3_NON_THINKING_HEADER_TOKENS` (the seven) moves here from `spans._HEADER_TOKENS["qwen"]`.

**Why not [`models.py`](../../assistant_axis/models.py).**  `MODEL_CONFIGS` is keyed by the exact
Hugging Face repo id and holds per-model facts (target layer, layer count, the `{model_name}`
short name, capping configs); a local path or a quantised copy misses it, and `get_config`'s
fallback is the substring chain this plan removes.  The family is a property of the template,
shared by every size and checkpoint of an architecture, so it is keyed differently and lives
apart.  [`models.py`](../../assistant_axis/models.py) keeps its job; the two are linked only by `get_config` gaining a `family`
field computed through `family_for_model` when asked (§ 15 Q1).

**Draft rows.**  *verified* = from the tokenizer's template as recorded in this repo, from the
8slot metadata, or from model code I know with confidence; *to check* = needs the real tokenizer
(what to check and how is in the cell).  The real-tokenizer tests of § 9 are where the "to
check" cells become assertions; **no row is pinned until its smoke run (§ 11) has shown the
derived header and Roger has read it.**

| family (`model_type`) | reasoning switch / `template_kwargs` | header tokens (derived; listed here as the expectation) | system prompt | BOS in template | end token | cleanup | notes |
|---|---|---|---|---|---|---|---|
| **`qwen3`** (Qwen/Qwen3-32B) | `template_switch`: `{"enable_thinking": False}` *verified* (what step 1 and step 2 pass today) | `<|im_start|> assistant \n <think> \n\n </think> \n\n`, ids `151644 77091 198 151667 271 151668 271` *verified* (8slot metadata) | native *verified* (the corpus was generated with system prompts) | none *verified* (no BOS in any recorded prompt) | `<|im_end|>` *verified* | `strip_leaked_think` *verified* (today's code) | `span_builder = "chatml"`; `expected_header_tokens` set to the seven. Qwen3-Instruct-2507 (no think block) would derive 3 tokens and **fail** this row's expectation on purpose: it is a different row. |
| **`llama`** (meta-llama/Llama-3.3-70B-Instruct) | `none` *verified*; **pin `date_string`** *to check*: the Llama 3.1+ template writes a system block "Cutting Knowledge Date: December 2023\nToday Date: <date>" using `strftime_now` unless `date_string` is given, so an unpinned step 2 renders a different prompt from step 1 on another day. Check the kwarg name in the template text. | `<|start_header_id|> assistant <|end_header_id|> \n\n` (4) *to check*; expected ids `128006 78191 128007 271` (the values hand-written in [test_spans.py](../../assistant_axis/tests/test_spans.py)) | native *to check* (the template also injects the date block even with a user system prompt) | `<|begin_of_text|>` emitted by the template *verified* ([P1 D8](../code_review_2026-10-12/escalations.md#p1-d8-a-second-bos-on-gemma-or-llama-from-text-prompts); the double-BOS case) | `<|eot_id|>` *verified* | `none` | gated repo (HF access token, Roger's); ~140 GB; 4 x 80 GB for vLLM TP=4 and for the HF load. |
| **`gemma2`** (google/gemma-2-27b-it) | `none` *verified* | `<start_of_turn> model \n` (3) *to check*; hand-written ids `106 2516 108` in test_spans.py | **`fold_into_user`** *verified*: the template raises on a system role, [test_generation.py](../../assistant_axis/tests/test_generation.py) asserts it, and `format_conversation` already folds the instruction into the user turn | `<bos>` emitted *verified* | `<end_of_turn>` *verified* | `none` | gated; ~54 GB. *to check*: HF attention implementation for the logit soft-capping at length 2048 (`hf_load_kwargs = {"attn_implementation": "eager"}` is what transformers recommends; memory at batch 8). |
| **`olmo2`** (allenai/OLMo-2-0325-32B-Instruct or the 7B/13B) | `none` *verified* | `<|assistant|> \n` (2) *to check* (from the Tülu 3 template as I recall it: `<|user|>\n{content}\n<|assistant|>\n{content}<|endoftext|>`); with N = 2 the header match must be exact (§ 5.4) | native (`<|system|>\n...`) *to check* | *to check* whether the template starts with `{{ bos_token }}` | `<|endoftext|>` *to check* | `none` | Which OLMo Roger means decides the row: § 15 Q6. |
| **`olmo3`** (allenai/Olmo-3-7B-Instruct / -Think) | *to check*: the Think variants reason in `<think>` blocks with no documented switch; the Instruct variant does not reason. If Think: treat as `always_on` with `reasoning_stored` (like gpt-oss) or use Instruct. | *to check* entirely; derived at the smoke run | *to check* | *to check* | *to check* | *to check* | Recommend the Instruct variant for an extraction (§ 15 Q6). |
| **`gpt_oss`** (openai/gpt-oss-20b, -120b) | **`always_on`** *verified as far as the harmony format is documented*: no off switch; `{"reasoning_effort": "low"}` puts "Reasoning: low" in the system block *to check*; the system block also carries "Current date: <date>" *to check* how to pin it (a kwarg or a `strftime_now` override) | derived from the stored rendering **with** the `thinking` field (§ 5.1 sample): `<|end|> <|start|> assistant <|channel|> final <|message|>` (6) *to check*; without it `<|start|> assistant <|channel|> final <|message|>` (5) | native, rendered as a `developer` block *to check* | *to check* (none, I believe) | `<|return|>` (last turn) / `<|end|>` *to check* | `harmony_final_channel`: parse the analysis and final channels *to check how vLLM 0.18.1 returns them* (§ 15 Q3: `llm.chat` with the reasoning parser vs `generate` with `skip_special_tokens=False` and the `openai_harmony` library) | MXFP4 weights: the HF load of step 2 dequantises to bf16 (20b: ~42 GB, fine; 120b: ~240 GB, 4 x 80 GB at best). Smoke run on 20b first. |

**Decided 2026-10-12 (§ 15, Q3 and Q6).**  The models are not yet named, so the work of this plan
is the mechanism plus whatever two or more candidate families need; the single-family cells
above — Llama's `date_string` pin, gpt-oss's channels and `harmony_final_channel`, OLMo 2's
exact-match header tolerance — are **TODO**, built only when that family is confirmed.  For
gpt-oss, Roger's intended layout is slot 0 from the response text tokens, slot 1 from the
thinking text tokens, and a slot for every fixed token before or between them; the row stays
"to check".

Not in the table: `gemma3` (system prompt folded into the first user turn by the template itself;
`get_layers` already knows `model.language_model.layers`); it is one more row when wanted.

### 5.3 Step 1 changes ([`generation.py`](../../assistant_axis/generation.py), [`1_generate.py`](../../pipeline/1_generate.py))

- `VLLMGenerator.load()`: `self.family = family_for_model(model_name)`;
  `self.layout = derive_chat_layout(self.llm.get_tokenizer(), self.family)`; log the header
  tokens; `trust_remote_code=self.family.trust_remote_code` (today `True` for every model, a nit of
  [review P1](../code_review_2026-10-12/escalations.md#p1-step-1-generation); all six families
  are native in transformers).
- `generate_batch()`: for each conversation,
  `ids = tokenizer.apply_chat_template(conv, tokenize=True, add_generation_prompt=True, return_dict=False, **family.template_kwargs)`
  and `llm.generate([TokensPrompt(prompt_token_ids=ids) ...], sampling_params)`
  (`vllm.inputs.TokensPrompt`; a `{"prompt_token_ids": ids}` dict is the same thing).  The
  rendered-text path goes.  For Qwen3 the ids are identical to what the text path produced (its
  tokenizer has no special-token post-processor; a test asserts `ids == tokenizer(text, add_special_tokens=False).input_ids`
  on the fake); for Llama 3 and Gemma 2 the one BOS the template emits is the only BOS.
- `response_cleanup` by family: `strip_leaked_think` is today's Qwen branch, keyed on the row
  instead of the substring; `harmony_final_channel` is written at the gpt-oss spike (§ 10 task 9).
  Each response record gains `cleanup_applied: bool` (additive; the `thinking_stripped` flag of
  [P1 D3](../code_review_2026-10-12/escalations.md#p1-d3-responses-carry-no-finish-reason-thinking-flag-seed-or-question-id),
  the missing response-record fields, under a name that covers every family).
- `format_conversation`: unchanged behaviour; after the behavioural probe, compare with
  `family.system_prompt` and **warn** when they disagree (a template that silently dropped the
  system message on a family marked `native` would generate without the persona instruction;
  the fold keeps the run usable, the warning says so).
- `RoleResponseGenerator`: writes the side-car (§ 5.5) once per run, before the first entity.
- `generate_response()` (the Hugging Face single-response helper, unused by the pipeline) gets the
  same family kwargs; `ProbingModel.generate` and `ConversationEncoder.format_chat` are left as
  they are (not on the pipeline path).

### 5.4 Step 2 changes ([`2_activations.py`](../../pipeline/2_activations.py), [`spans.py`](../../assistant_axis/internals/spans.py), [`conversation.py`](../../assistant_axis/internals/conversation.py), [`model.py`](../../assistant_axis/internals/model.py))

- `ProbingModel` gains `model_type` (`self.model.config.model_type`) and `family`
  (`family_for_model_type`).  `detect_type` / `is_qwen` / `supports_system_prompt` stay as they
  are (nothing on the pipeline path reads them) with a docstring pointing at `family`.
- Once per worker, after the model loads: `layout = derive_chat_layout(pm.tokenizer, pm.family)`;
  then the side-car check (§ 5.5); then every entity uses that layout.
- `SpanMapper(tokenizer, *, header_ids=None, search_distance=None)`: the ids are injected;
  `None` means body mean only (the `--no-headers` path).  `_HEADER_TOKENS`,
  `_MAX_HEADER_SEARCH_DIST`, `_model_family` and `expected_assistant_header_ids` go.
  `_find_header`'s tolerance: today it accepts a match with one token wrong (`matched >= N - 1`),
  which for N = 7 is what the 8slot run had and keeps; for N < 4 (OLMo 2's two tokens) one
  wrong token of two is no match, so the rule becomes `allowed_mismatches = 1 if N >= 4 else 0`.
  Qwen3 behaviour is unchanged.
- `ConversationEncoder(tokenizer, model_name=None, *, span_builder=None)`: `"chatml"` dispatches
  to the existing Qwen pattern path (think-token filtering, boundary whitespace), `"generic"` to
  the existing LCP path; `None` keeps today's substring dispatch for callers outside the
  pipeline.  Step 2 always passes `pm.family.span_builder`.
- `extract_activations_batch`: `chat_kwargs = dict(family.template_kwargs)`; `map_spans` also
  returns, per conversation, the roles of the turns it stacked (it drops spans past the
  truncation length, so the turn axis can be shorter than the span list); the assistant
  activation is the turn whose role is `assistant`; **zero such turns gives no activation (as
  today: an empty or truncated-away response), more than one raises
  `ContractError("<entity>: conversation <i> has 2 assistant turns; the pipeline is single-turn")`**.
  For every 8slot conversation (`[system?, user, assistant]`, the system turn has no span) the
  selected turn is turn 1, which is what `1::2` picked; indexing one turn gives the same bf16
  values as `nanmean` over a size-1 axis.
- `--layers`: `all`, or a comma-separated list parsed to ints and rejected with an argparse
  error unless strictly increasing and within `[0, n_layers)` (checked after the model loads, so
  the message can say how many layers there are).  `--thinking` is removed (an argparse error
  if passed).
- Metadata: `header_tokens`, `header_ids`, `model_name`, `extract_headers` as today, plus
  `model_type`, `template_kwargs`, `generation_prompt_ids`, `layers`, `max_length`, `batch_size`;
  the `thinking` key written since 2026-10-12 goes (it was `False` in every file and is now the
  `enable_thinking` entry of `template_kwargs`).  Step 4 copies the dict, step 5 copies the first
  file's and compares `header_ids` and `model_name`; it should also compare `model_type` and
  `template_kwargs` (two lines).
- `--verify_spans N` (new, default 0; the smoke runs pass 20): for the first N conversations of
  the first entity, decode the assistant span and compare it with the stored content after the
  family's strip rule; log each mismatch with both strings; exit 1 on any.  The same check on
  the fake is a unit test.

### 5.5 Step 1 and step 2 cannot disagree: the side-car

Step 1 writes `<responses_dir>/generation_config.json` (`.json`, so no `*.jsonl` glob in steps 2
and 3 or the scanner sees it) through `atomic_write_text`; one file per run, merged into an
existing one as a list of runs (a rerun that fills gaps appends).  Step 2 reads it (with retry)
before loading the model: a different `model_type`, `template_kwargs` or `header_ids` is an
error naming both; a missing file (the 8slot tree has none) refuses unless
`--ignore_generation_config` is given (Roger, § 15 Q10).  Step 2 also
re-renders the side-car's `sample_conversation` and requires `sample_prompt_ids` to be the prefix
of what it renders: the end-to-end check that the two steps see the same tokens, run before any
activation is computed.  Schema in § 7.

### 5.6 Downstream consumers of the slot layout

What each site reads, what a tree with a different header means for it, and what this plan does.
Most read `metadata.header_tokens` through `slot_labels`; the hard-coded sites get a guard.  The
guard is one helper, `assistant_axis.axis.require_header_layout(metadata, expected=QWEN3_NON_THINKING_HEADER_TOKENS, where="<script>")`,
raising `SlotLayoutError` with the tree's header, the expected one and the sentence "pass
`--slot` explicitly to use another layout"; a script calls it only when its slot default or its
slot names are used, so an explicit `--slot` on a non-Qwen tree works and logs the slot's label.

| site | reads the layout from | on a tree with another header | this plan |
|---|---|---|---|
| [`assistant_axis/axis.py`](../../assistant_axis/axis.py) `slot_labels`, `load_*` | metadata | correct | adds `require_header_layout` beside it |
| [`pipeline/4_vectors.py`](../../pipeline/4_vectors.py), [`5_axis.py`](../../pipeline/5_axis.py), [`scan_missing_vectors.py`](../../pipeline/scan_missing_vectors.py) | tensor shape; step 5 compares `header_ids` / `model_name` across vectors | correct; mixed trees refused | step 5 also compares `model_type`, `template_kwargs` |
| [`results_analysis/axis_judge_correlation.py`](../../results_analysis/axis_judge_correlation.py) | `n_slots` from the vectors; `--slot` range-checked (`_slot_list_from_arg`); default `all` | correct; labels are `slot i` | log `slot_labels` once per run |
| the `DEFAULT_SLOT = 6` scripts ([`gpt_sonnet_weight_sweep`](../../results_analysis/gpt_sonnet_weight_sweep.py), [`whitening_k_sweep`](../../results_analysis/whitening_k_sweep.py), [`shear_l_sweep`](../../results_analysis/shear_l_sweep.py), [`optimal_axis_for_judge`](../../results_analysis/optimal_axis_for_judge.py), [`pair_slice_plots`](../../results_analysis/pair_slice_plots.py), [`axis_cosine_seriation`](../../results_analysis/axis_cosine_seriation.py), [`response_di_weight_sweep`](../../results_analysis/response_di_weight_sweep.py), [`rubric_v1_v2_compare`](../../results_analysis/rubric_v1_v2_compare.py), [`di_weights_ablation`](../../results_analysis/di_weights_ablation.py), [`axis_pc_alignment_vs_peak_K`](../../results_analysis/axis_pc_alignment_vs_peak_K.py), [`gpt_anthropic_response_weight_sweep`](../../results_analysis/gpt_anthropic_response_weight_sweep.py), [`whitening_k_weighted_scatter`](../../results_analysis/whitening_k_weighted_scatter.py), [`canonical_angles/plots/ca1_plane_pre_post_shear`](../../results_analysis/canonical_angles/plots/ca1_plane_pre_post_shear.py), [`whitening_sweep_with_nulls`](../../results_analysis/canonical_angles/plots/whitening_sweep_with_nulls.py), [`layer_sweep`](../../results_analysis/canonical_angles/plots/layer_sweep.py) `[0, 6]`) and `DEFAULT_SLOT = 7` ([`pc_round_trip/launch_judge_runs`](../../results_analysis/pc_round_trip/launch_judge_runs.py), [`permutation_null`](../../results_analysis/pc_round_trip/permutation_null.py), [`plot_subspace_projection`](../../results_analysis/pc_round_trip/plot_subspace_projection.py)) | a number | 4 or 5 slots: `IndexError` (loud, unhelpful); 8 or more: **another token, silently** | guard when the default is used; defaults unchanged |
| [`rho_by_layer.py`](../../results_analysis/rho_by_layer.py) `SLOTS = [0, 3, 6, 7]`, `SLOT_LABELS`; [`rho_by_layer_simple.py`](../../results_analysis/rho_by_layer_simple.py) label dict | hard-coded | wrong labels, or `IndexError` | guard |
| [`all_roles_pairwise_slots.py`](../../results_analysis/all_roles_pairwise_slots.py) `SLOT_NAMES`, the slot-6 / slot-7 pair groups | hard-coded 8 | meaningless pairs with Qwen names | guard |
| [`pca_scree_plots.py`](../../results_analysis/pca_scree_plots.py) `SLOT_NAMES_8` when `num_slots == 8`, else `slot_labels` | count | an 8-slot non-Qwen tree gets Qwen names, silently | use `SLOT_NAMES_8` only when `header_tokens` equal the seven; else `slot_labels` |
| [`token_position_noise_analysis.py`](../../results_analysis/token_position_noise_analysis.py) `SLOT_NAMES`, `token_axis_label` | hard-coded, sliced to the count | wrong names | guard |
| [`canonical_angles/plots/goal_vs_nogoal_mutual.py`](../../results_analysis/canonical_angles/plots/goal_vs_nogoal_mutual.py), [`combos_vs_traits_roles_pooled.py`](../../results_analysis/canonical_angles/plots/combos_vs_traits_roles_pooled.py) `_slot_pretty` dicts; `_choose_layout` 4 / 8 branches | hard-coded names, generic layout fallback | wrong names | names from `slot_labels` unless the header is the seven (keeps the recorded plots' text) |
| [`canonical_angles/data.py`](../../results_analysis/canonical_angles/data.py) `detect_n_slots`; [`plot_helpers._auto_grid`](../../results_analysis/canonical_angles/plot_helpers.py); [`plot_palette.slot_colors`](../../assistant_axis/plot_palette.py) | shape | correct (the palette's "special marker" slots 1/4/6 are Qwen's; cosmetic) | none |
| [`steering/run_sweep.py`](../../steering/run_sweep.py) `_load_axis_for_cell` (`axis_raw[slot, layer]`), the config cells; [`sweep_start_heuristics.py`](../../assistant_axis/sweep_start_heuristics.py) keyed on `(mode, slot, layer)` | numbers from the YAML | out of range, or another token; the start-strength table was tuned on Qwen cells | refuse `slot >= n_slots`; log the slot's label; warn when the axis header is not the seven that the heuristic table is Qwen's |
| [`assistant_axis/steering_runner.py`](../../assistant_axis/steering_runner.py) `_tokenize_batch` | `"qwen" in model_name` for `enable_thinking` | another family thinks, or gets no kwargs | `family_for_model(model_name).template_kwargs` (§ 15 Q7) |

### 5.7 Alternatives considered

- *Header by generation-prompt difference only* (the brief's wording): equal to § 5.1 for five
  of six families; wrong for gpt-oss.  Kept as the cross-check.
- *`llm.chat(messages, chat_template_kwargs=...)`* instead of token ids: vLLM renders the
  template itself, which is right for gpt-oss (its harmony renderer) but is a second rendering
  path that step 2 cannot compare against; token ids make the prefix equality exact.  The
  gpt-oss spike may still choose `llm.chat` for that family alone (§ 15 Q2, Q3).
- *Keep the Qwen text path and use ids only where BOS is a problem*: two code paths to keep
  equal; the ids path gives Qwen the same ids anyway.
- *Table in [`models.py`](../../assistant_axis/models.py)*: § 5.2.
- *Unknown family: warn and run body-mean only* (P2's current fix for the unknown family, [P2 D3](../code_review_2026-10-12/escalations.md#p2-d3-header-token-list-hard-coded-and-the-family-detected-by-substring)): refused here (§ 15 Q8).

## 6. File layout

| file | status | public surface |
|---|---|---|
| [`assistant_axis/model_families.py`](../../assistant_axis/model_families.py) | new | `FamilySpec`, `FAMILIES`, `QWEN3_NON_THINKING_HEADER_TOKENS`, `UnknownFamilyError`, `family_for_model_type(model_type: str) -> FamilySpec`, `family_for_model(name_or_path: str) -> FamilySpec` |
| [`assistant_axis/internals/chat_layout.py`](../../assistant_axis/internals/chat_layout.py) | new | `ChatLayout` (frozen dataclass, § 5.1), `LayoutError`, `derive_chat_layout(tokenizer, family: FamilySpec, *, probe_system: str = ..., probe_user: str = ..., probe_content: str = ..., probe_thinking: str = ...) -> ChatLayout`, `ChatLayout.metadata() -> dict` (the keys step 2 writes) |
| [`assistant_axis/internals/spans.py`](../../assistant_axis/internals/spans.py) | edit | `SpanMapper(tokenizer, *, header_ids: Sequence[int] \| None = None, search_distance: int \| None = None)`; `map_spans(...) -> (activations, mismatches, turn_roles)` |
| [`assistant_axis/internals/conversation.py`](../../assistant_axis/internals/conversation.py) | edit | `ConversationEncoder(tokenizer, model_name=None, *, span_builder: str \| None = None)` |
| [`assistant_axis/internals/model.py`](../../assistant_axis/internals/model.py) | edit | `ProbingModel.model_type`, `ProbingModel.family`; `__init__(..., hf_load_kwargs=None)` |
| [`assistant_axis/generation.py`](../../assistant_axis/generation.py) | edit | `VLLMGenerator.family`, `.layout`; `generate_batch` passes `TokensPrompt`; `RoleResponseGenerator.write_generation_config(...)`; `GENERATION_CONFIG_NAME = "generation_config.json"` |
| [`assistant_axis/axis.py`](../../assistant_axis/axis.py) | edit | `SlotLayoutError`, `require_header_layout(metadata, expected, where) -> None` |
| [`assistant_axis/models.py`](../../assistant_axis/models.py) | edit | `get_config` gains `family` on request; stub rows (`short_name`, `total_layers`, `target_layer = total // 2`) for the models Roger names in Q6 |
| [`pipeline/1_generate.py`](../../pipeline/1_generate.py) | edit | writes the side-car; refuses an unknown family before loading vLLM |
| [`pipeline/2_activations.py`](../../pipeline/2_activations.py) | edit | `--layers` validation; `--thinking` removed; `--verify_spans N`; side-car check; `process_role(pm, role_file, output_dir, layers, batch_size, max_length, *, layout, extract_headers)` |
| [`pipeline/5_axis.py`](../../pipeline/5_axis.py) | edit | compares `model_type`, `template_kwargs` |
| [`steering/run_sweep.py`](../../steering/run_sweep.py), [`assistant_axis/steering_runner.py`](../../assistant_axis/steering_runner.py) | edit (small) | the two guards of § 5.6 |
| consumer scripts of § 5.6 | edit (one call each) | `require_header_layout` |
| [`pipeline/README.md`](../../pipeline/README.md), [`AGENT_NOTES.md`](../../AGENT_NOTES.md) (then `uv run python tools/sync_agent_notes.py`) | docs | step 2 "What a file holds" per family; the flag table; a "Model families" section; the side-car |

## 7. Data schemas

`<responses_dir>/generation_config.json` (step 1; a list so reruns append):

```json
{"runs": [{
  "script": "pipeline/1_generate.py", "created_at": "2026-10-20T03:12:44+00:00", "git_sha": "ab12cd3",
  "model_name": "Qwen/Qwen3-32B", "model_type": "qwen3",
  "template_kwargs": {"enable_thinking": false},
  "header_tokens": ["<|im_start|>", "assistant", "\n", "<think>", "\n\n", "</think>", "\n\n"],
  "header_ids": [151644, 77091, 198, 151667, 271, 151668, 271],
  "generation_prompt_ids": [151644, 77091, 198, 151667, 271, 151668, 271],
  "system_prompt": "native", "response_cleanup": "strip_leaked_think",
  "sampling": {"temperature": 0.7, "top_p": 0.9, "max_tokens": 512, "max_model_len": 2048},
  "questions": {"file": "../data/extraction_questions.jsonl", "question_count": 300, "reduce_questions": 3},
  "sample_conversation": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}],
  "sample_prompt_ids": [151644, 8948, 198, "..."]
}]}
```

Activation / vector / axis `metadata` (step 2 writes, steps 4 and 5 copy).  Was (8slot, left)
and now (right):

| was (8slot files; files since 2026-10-12 also carry `layers`, `max_length`, `thinking`, `batch_size`) | now |
|---|---|
| `header_tokens`, `header_ids`, `model_name`, `extract_headers` | the same four, unchanged in value for Qwen3 |
| `thinking: false` (since 2026-10-12) | gone; `template_kwargs: {"enable_thinking": false}` |
| | `model_type: "qwen3"`, `generation_prompt_ids: [...]` |
| `layers`, `max_length`, `batch_size` (since 2026-10-12) | the same |

Response records gain `cleanup_applied: bool` (additive).

## 8. CLI

- [`1_generate.py`](../../pipeline/1_generate.py): no new flags; fails before loading vLLM with `UnknownFamilyError` for a
  `model_type` not in the table (message lists the known keys and the file to add a row to).
- [`2_activations.py`](../../pipeline/2_activations.py): `--layers` validated (§ 5.4); `--thinking` removed; `--verify_spans N`
  (default 0); `--ignore_generation_config` to run on a tree whose side-car does not match (an
  explicit override that logs what differed; for a deliberate re-extraction under other kwargs)
  or that has no side-car at all (the 8slot tree): **required** there, not a warning (Roger,
  § 15 Q10: "we're unlikely to do this").
  `--no-headers` kept.
- [`5_axis.py`](../../pipeline/5_axis.py): no new flags.
- Every flag change is mirrored in [`run_pipeline.sh`](../../pipeline/run_pipeline.sh)'s usage text
  and the README table; the driver passes nothing new (it never passed `--thinking`).

Nothing here is a paid call; the GPU use is the smoke runs of § 11, each under the confirmation
rule.

## 9. Acceptance tests, written first

All on the in-process fakes unless marked *real tokenizer*; the exact command is
`uv run pytest assistant_axis/tests/test_chat_layout.py assistant_axis/tests/test_model_families.py assistant_axis/tests/test_spans.py assistant_axis/tests/test_conversation_encoder.py assistant_axis/tests/test_generation_prompts.py pipeline/tests/ -q`
plus the full suite before the report.

1. **Golden gate** ([`pipeline/tests/test_step2_qwen3_golden.py`](../../pipeline/tests/test_step2_qwen3_golden.py),
   new, with [`pipeline/tests/fixtures/step2_qwen3_fake_golden.pt`](../../pipeline/tests/fixtures/step2_qwen3_fake_golden.pt)
   and [`step2_qwen3_fake_golden.jsonl`](../../pipeline/tests/fixtures/step2_qwen3_fake_golden.jsonl), both new): **task 0 generates the fixture from the
   pre-change commit** (a worktree at HEAD before any edit) by running today's
   `extract_activations_batch` on the Qwen3-like fake over a fixed set of 12 conversations (with
   and without a system prompt, an empty response, leading and trailing newlines, a response
   past `max_length`, a user question of two tokens so the header search window matters) and
   saving the activation dict and the metadata; the test loads the fixture and asserts
   `torch.equal` per key, the same key set, and `header_tokens` equal to the seven.  This is the
   byte-identical gate; it does not depend on the new code.
2. [`assistant_axis/tests/test_chat_layout.py`](../../assistant_axis/tests/test_chat_layout.py)
   (new): the Qwen3-like fake derives exactly `QWEN3_NON_THINKING_HEADER_TOKENS` and
   `search_distance == 14`; the generation prompt equals the header; the same with and without a
   system message; a fake variant whose template has no think block derives three tokens and
   fails the `qwen3` row's expectation with a `LayoutError` naming both; a gpt-oss-like fake
   (`make_harmony_like_tokenizer()`, new in [`internals_fakes.py`](../../assistant_axis/tests/internals_fakes.py): generation prompt
   `<|start|>assistant`, stored turn with a `thinking` field) derives the six-token header and
   passes the prefix check; a template whose stored turn does not start with the generation prompt
   raises; `header_tokens` are decoded strings (`"\n"`, not `"Ċ"`).
3. [`assistant_axis/tests/test_model_families.py`](../../assistant_axis/tests/test_model_families.py)
   (new): every row has every field and a known `span_builder` / `response_cleanup`; the `qwen3`
   row's `expected_header_tokens` is the seven; an unknown `model_type` raises listing the keys;
   `family_for_model` resolves through a monkeypatched `AutoConfig`.
4. [`assistant_axis/tests/test_spans.py`](../../assistant_axis/tests/test_spans.py) (edit):
   **expectation change, flagged**: `TestExpectedAssistantHeaderIds` and the `family_fixture`
   keyed on model names go (there is no family-from-name); replaced by injected-ids tests on the
   same three vocabularies; `_find_header` tolerance tests for N = 7 (one mismatch accepted, as
   today) and N = 2 (none); `map_spans` returns the turn roles.
5. [`pipeline/tests/test_2_activations_extract.py`](../../pipeline/tests/test_2_activations_extract.py)
   (edit): every current test passes with two **flagged expectation changes**:
   `test_process_role_saves_what_step_4_reads` and
   `test_metadata_records_a_layer_subset_and_the_no_header_layout` lose the `thinking` key and
   gain `model_type` / `template_kwargs`; `test_unrecognised_model_family_warns_and_drops_the_header_slots`
   becomes `test_unknown_model_type_refuses_to_run` (the fake's config gets `model_type = "nope"`).
   New: `test_two_assistant_turns_raise_contract_error`; `test_layers_subset_is_validated`
   (`"3,1"`, `"1,1"`, `"-1"`, `"64"` on a 3-layer fake all refused with the message);
   `test_verify_spans_decodes_the_stored_content`.
6. [`pipeline/tests/test_2_activations_cli.py`](../../pipeline/tests/test_2_activations_cli.py)
   (new): `--thinking` is an argparse error; `--ignore_generation_config` logs the difference.
7. [`assistant_axis/tests/test_generation_prompts.py`](../../assistant_axis/tests/test_generation_prompts.py)
   (new): with a fake `LLM` that records what it was given: prompts are token-id prompts equal to
   `apply_chat_template(tokenize=True, add_generation_prompt=True, **kwargs)`; on the Qwen3-like
   fake they equal the old text path's ids; on a Llama-like fake (`make_llama3_like_tokenizer()`,
   new: a `<|begin_of_text|>` post-processor and the four-token header) exactly one BOS;
   `strip_leaked_think` applies only to the `qwen3` row; the side-car is written with the schema
   of § 7 and appended on a second run; `format_conversation` warns when the probe and the row
   disagree.
8. [`pipeline/tests/test_2_activations_sidecar.py`](../../pipeline/tests/test_2_activations_sidecar.py)
   (new): a matching side-car passes; a different `template_kwargs` or `header_ids` fails before
   the model is used; `sample_prompt_ids` not a prefix fails; no side-car refuses without
   `--ignore_generation_config` and runs with it (§ 15 Q10).
9. [`pipeline/tests/test_5_axis.py`](../../pipeline/tests/test_5_axis.py) (edit): mixed
   `model_type` refused.
10. [`assistant_axis/tests/test_axis.py`](../../assistant_axis/tests/test_axis.py) (edit):
    `require_header_layout` passes on the seven, raises `SlotLayoutError` on `["a", "b"]` with
    the script name in the message; one consumer test per guarded script is not written (the
    helper is tested once; each script's call is reviewed in the diff).
11. *Real tokenizer*, [`assistant_axis/tests/test_chat_layout_real.py`](../../assistant_axis/tests/test_chat_layout_real.py)
    (new), skipped unless `ASSISTANT_AXIS_HF_TESTS=1`: for each family whose tokenizer Roger has
    allowed (tokenizer files only, about 10-20 MB each; Llama and Gemma are gated), derive the
    layout and assert the row's expectation; for Qwen3 the ids `[151644, 77091, 198, 151667, 271, 151668, 271]`.
    This is where the "to check" cells of § 5.2 become assertions, before the smoke run.
    **The agent does not look in the cache to see whether a tokenizer is present** (§ 3).

## 10. Ordered task checklist (Opus)

0. Make the golden fixture from the pre-change commit (test 1); commit it with its generator
   script under `pipeline/tests/fixtures/`.  Proof: the golden test passes on HEAD before any
   other edit.
1. [`model_families.py`](../../assistant_axis/model_families.py) (new) with the six draft rows and the Qwen3 expectation; test 3.
2. [`chat_layout.py`](../../assistant_axis/internals/chat_layout.py) (new); the two new fake tokenizers; test 2.
3. [`spans.py`](../../assistant_axis/internals/spans.py): injected ids, tolerance rule, turn roles; test 4.  Golden test still green.
4. [`conversation.py`](../../assistant_axis/internals/conversation.py): `span_builder` dispatch;
   [`test_conversation_encoder.py`](../../assistant_axis/tests/test_conversation_encoder.py) unchanged and green.
5. [`model.py`](../../assistant_axis/internals/model.py): `model_type`, `family`, `hf_load_kwargs`.
6. [`2_activations.py`](../../pipeline/2_activations.py): layout once per worker, one-assistant-span rule, `--layers`, `--thinking`
   out, metadata, `--verify_spans`; tests 5 and 6.  **Golden test green: the gate.**
7. [`generation.py`](../../assistant_axis/generation.py) and [`1_generate.py`](../../pipeline/1_generate.py): family, `TokensPrompt`, cleanup by row, the side-car;
   test 7.
8. Side-car check in step 2 (a tree with no side-car refuses unless `--ignore_generation_config`:
   § 15 Q10); test 8.  [`5_axis.py`](../../pipeline/5_axis.py); test 9.
9. **TODO, not in this plan** (§ 15 Q3 and Q6: gpt-oss is not definite; done only if it is
   confirmed): the gpt-oss spike (half a day, no model): read the real harmony template text and
   vLLM 0.18.1's gpt-oss docs; write `harmony_final_channel` against a fake; decide Q3's
   mechanics; report before any gpt-oss run.
10. [`axis.py`](../../assistant_axis/axis.py) guard; the consumer calls of § 5.6; the two steering guards; test 10.
11. [`models.py`](../../assistant_axis/models.py) stub rows for the models of Q6 (TODO until the
    models are named: § 15 Q6);
    [`pipeline/README.md`](../../pipeline/README.md); [`AGENT_NOTES.md`](../../AGENT_NOTES.md) (then
    [`tools/sync_agent_notes.py`](../../tools/sync_agent_notes.py)); [`run_pipeline.sh`](../../pipeline/run_pipeline.sh) usage text.
12. Full test suite; the acceptance report (§ 13).
13. Smoke runs, one family at a time, each launched only after Roger's confirmation (§ 11).

Each task is one sitting with its test; tasks 1-6 can precede any decision on Q1-Q8 except Q8
(the unknown-family behaviour, task 6).

## 11. Smoke run per new family (the pilot)

On the pod, after task 12, one family per launch, **each launch quoted to Roger first** (model,
GPUs, expected GPU-hours, download size with its delete-when-done note, the HF token for gated
repos), since the pod is paid by the hour even where the GPU-hours are few:

```bash
cd pipeline
uv run 1_generate.py --mode roger --model <M> --roles default absolutist \
    --question_count 30 --reduce_questions 1 --output_dir /workspace/smoke/<family>/responses
uv run 2_activations.py --model <M> --responses_dir /workspace/smoke/<family>/responses \
    --output_dir /workspace/smoke/<family>/activations --batch_size 8 --verify_spans 20
uv run 3_judge.py --entity_type trait --responses_dir ... --output_dir .../scores --no_batch   # 150 calls, cents
uv run 4_vectors.py --activations_dir ... --scores_dir ... --output_dir .../vectors --min_count 10
uv run 5_axis.py --vectors_dir .../vectors --output .../axis.pt
```

Two entities ([default](../../data/roles/instructions/default.json) and
[absolutist](../../data/traits/instructions/absolutist.json)), 5 x 30 = 150 responses each.
What it checks, in order: (1) step 1 refuses or runs: the derived header is printed and goes
into the side-car; **Roger reads it and the row's `expected_header_tokens` is pinned from it**
(the first run of a family is the only one without the expectation); (2) step 2's side-car check
passes, the first conversation's ids are logged with exactly one BOS where the template has one;
(3) `activations.log`: `HEADER NOT FOUND` 0, header mismatches 0, dropped conversations 0 (or
only empty responses) on both entities; (4) `--verify_spans 20`: 20 of 20 decode to the stored
content; (5) the vector shape is `(1 + N, n_layers, hidden)` and `slot_labels` prints the layout;
(6) `axis.pt` is written.  Anything else is a stop, reported with the log lines.

GPU time: model load dominates.  Llama 3.3 70B: vLLM TP=4 load from `/dev/shm` ~10 min, HF
`device_map="auto"` ~10 min, generation and extraction minutes: about 0.5-0.75 h of wall clock
on 4 GPUs, **2-3 GPU-hours**.  Gemma 2 27B, gpt-oss-20b, OLMo 7B-32B: 1-2 GPUs,
**about 1 GPU-hour** each.  Downloads (over 2 GB each, so each gets a delete-when-done TODO at
approval): Llama 3.3 70B ~140 GB, Gemma 2 27B ~54 GB, gpt-oss-20b ~13 GB (120b ~65 GB), OLMo 2
32B ~65 GB.  Every run is under the 13 GPU-hour line on its own; the rule's "quote the
parameters and wait" still applies to each.

## 12. Cost and time

No paid API calls except the optional 150-call step 3 per smoke run (cents).  Coding: about
**3.5 Opus agent-days** (tasks 0-8 two days; 10-12 a day; the real-tokenizer runs and the smoke
runs half a day of attendance; task 9, the gpt-oss spike, half a day, is a TODO: § 15 Q3), plus
a Fable review of the diff against the golden gate and this plan.  GPU: § 11, about 5-7
GPU-hours if all four candidate families get a smoke run (which families is open: § 15 Q6),
spread over separate launches.

## 13. Report at the end

[`reports/pipeline/acceptance_multi_model_extraction.md`](./acceptance_multi_model_extraction.md)
(not there yet), one page: what was built; deviations from this plan; the test counts and the
golden gate's result; the derived header of every family that had a smoke run, as the log printed
it, beside the row's expectation; the smoke-run checks (1)-(6) per family with the log lines;
GPU-hours used; the open rows.

## 14. Risks and how each is caught

| risk | caught by |
|---|---|
| The derivation differs between transformers 4.57.6 (pod) and 5.1.0 (Mac): `return_dict`, `BatchEncoding`, template kwarg handling | `return_dict=False` everywhere (the fix of [review P2](../code_review_2026-10-12/escalations.md#p2-step-2-activations-and-internals)); the fake tests run under both locks; the real-tokenizer test runs on the pod before the smoke run |
| BPE merges across the header/content boundary (a response starting with whitespace merging into the header's trailing `\n\n`) so the content is not found in `full` | the probe sentinels start with a letter (derivation); the Qwen pattern path strips boundary whitespace (unchanged); `--verify_spans` on the smoke run; the generic path's fallback keeps the whole delta and logs |
| Llama's date-stamped system block makes step 2 render a different prompt from step 1 | `date_string` pinned in the row and recorded in the side-car; the `sample_prompt_ids` prefix check fails loudly if not |
| gpt-oss: the model-generated channel tokens and the analysis text; vLLM's decoded text loses the markers | the spike (task 9) before any run; `reasoning_stored` in the row; the layout check requires the generation prompt to be a prefix of the stored turn |
| A template whose assistant header differs with a system prompt present | the derivation renders both and compares |
| A wrong row (a `to check` cell copied from memory) | no row is pinned before its smoke run; the real-tokenizer test; Roger reads the derived header |
| `TokensPrompt` changes Qwen3's prompt ids | test 7 asserts equality with the old text path's ids on the fake; the smoke run on Qwen3 (optional, § 15 Q9) compares the first prompt's ids with a text-path render |
| The one-assistant-span rule rejects a recorded response file | it cannot on step 1's output (one assistant message per record); a hand-made multi-turn file fails with the entity and conversation named |
| `_find_header`'s stricter tolerance for N < 4 hides headers on OLMo 2 | mismatch counts in `activations.log` on the smoke run; the tolerance is a row field if a family needs it |
| A consumer script's guard fires on the 8slot tree | the guard compares with the seven, which every 8slot file carries (verified 2026-10-12); the consumer suite runs on the 8slot data before the commit |
| The side-car name collides with a glob | `.json` beside `*.jsonl`; steps 2 and 3 and the scanner glob `*.jsonl` (verified) |
| Gemma 2's HF load at batch 8, length 2048 with eager attention runs out of memory | `hf_load_kwargs` in the row; the smoke run at `--batch_size 8` is the test; halve if needed and record it |
| The metadata key `thinking` removed breaks a reader | no reader reads it (grep 2026-10-12: written by step 2 since 2026-10-12, read by its test only) |

## 15. Open questions for Roger

1. **Where the table lives.**  New [`assistant_axis/model_families.py`](../../assistant_axis/model_families.py) (not there yet; recommended, § 5.2) or
   rows inside [`models.py`](../../assistant_axis/models.py)'s `MODEL_CONFIGS`.
2. **Step 1's prompt path.**  Token ids for every family (recommended: one path, exact prefix
   equality with step 2, no BOS hazard) or keep the text path for Qwen3 and use ids only where
   the template emits a BOS.
3. **gpt-oss reasoning.**  It cannot be switched off.  (a) Store the analysis channel in the
   response record (`thinking`) and let step 2 re-render it, so the activations come from the
   context the model actually had, header = the six tokens before the final content
   (recommended); (b) drop it: body mean over the final channel, header = the template's
   five-token final header, activations of a context the model never saw (the "text the model
   did not see" case of [review P5](../code_review_2026-10-12/escalations.md#p5-end-to-end-contracts),
   systematic here).  Either way the reasoning text is recorded.  The spike
   (task 9) brings the mechanics.
4. **Fold [P1 D2](../code_review_2026-10-12/escalations.md#p1-d2-resume-skips-any-entity-whose-file-exists)
   (resume skips any entity whose file exists) and
   [P1 D3](../code_review_2026-10-12/escalations.md#p1-d3-responses-carry-no-finish-reason-thinking-flag-seed-or-question-id)
   (responses carry no finish reason, thinking flag, seed or question id) into the side-car
   now?**  The side-car is the file P1 D2 asked for; adding P1 D3's
   per-response `finish_reason`, `question_id` and a seed is cheap while `generation.py` is open.
   Recommended: the side-car and `cleanup_applied` in this plan; `finish_reason` and
   `question_id` too if you say so (additive, no reader changes).
5. **Tokenizer downloads for the real-tokenizer tests.**  Tokenizer files only (10-20 MB each),
   Llama and Gemma gated.  Recommended: on the pod before each smoke run; on the Mac only if you
   want the suite green locally, and the agent asks before each download.
6. **Which OLMo and which gpt-oss.**  OLMo 2 (no reasoning; the 32B Instruct is the size
   nearest the others) or OLMo 3 (Think reasons without a switch; Instruct does not);
   gpt-oss-20b for the smoke run with 120b decided after it.  Recommended: OLMo 2 32B Instruct
   or OLMo 3 Instruct, and gpt-oss-20b first.
7. **Steering in this plan.**  Route `_tokenize_batch`'s thinking switch through the table and
   add the slot guard in `_load_axis_for_cell` now (recommended: two small edits, one test each)
   or leave both to the steering plan.
8. **Unknown `model_type`.**  Refuse in both steps (recommended) or keep P2's warn-and-run
   body-mean-only behaviour ([P2 D3](../code_review_2026-10-12/escalations.md#p2-d3-header-token-list-hard-coded-and-the-family-detected-by-substring))
   behind `--no-headers`.
9. **A Qwen3 smoke run** (about 1 GPU-hour on 4 GPUs) before the October extraction, to see the
   derived header, the side-car and the prompt-id equality on the real model.  Recommended: yes,
   as the first entities of the October run rather than a separate launch.
10. **Step 2 on the 8slot tree** (no side-car): warn once and run (recommended) or require
    `--ignore_generation_config`.  Decided: require it (see the decisions block below).

If a question is unanswered when Opus reaches the step, it proceeds under the recommendation and
records that in [`reports/pipeline/QUESTIONS.md`](./QUESTIONS.md) (not there yet).

### Decisions (Roger, 2026-10-12)

All ten answered the same day.

1. **Where the table lives**: no opinion — the recommendation stands (new
   [`assistant_axis/model_families.py`](../../assistant_axis/model_families.py), not there yet).
2. **Step 1's prompt path**: as recommended — token ids for every family.
3. **gpt-oss reasoning**: Roger: "I'd say extract slot 0 from response text tokens, slot 1 from
   thinking text tokens, and a slot for every fixed token before them or between them.  Leave
   this as a TODO until we know if we're actually using gpt-oss — that's not definite."  So the
   gpt-oss work is a **TODO** in this plan, with that slot design recorded as the intended
   layout; the `gpt_oss` row of § 5.2 stays "to check", and nothing is built for it in this plan
   (task 9 of § 10, the spike, and `harmony_final_channel` are deferred with it).
4. **Fold [P1 D2](../code_review_2026-10-12/escalations.md#p1-d2-resume-skips-any-entity-whose-file-exists)
   / [P1 D3](../code_review_2026-10-12/escalations.md#p1-d3-responses-carry-no-finish-reason-thinking-flag-seed-or-question-id)
   into the side-car**: as recommended — the side-car and `cleanup_applied` in
   this plan; the other record fields (`finish_reason`, `question_id`, a seed) if he says so.
5. **Tokenizer downloads**: as recommended — tokenizer-only downloads on the pod before each
   smoke run; no need to ask again.
6. **Which OLMo and which gpt-oss**: not yet decided.  Roger: "Neither the list of models nor
   their sizes are certain.  Only do lowest-common-denominator work needed by two or more of
   them.  Anything specific to a single model family can be left as a TODO IF NEEDED."  So the
   scope of this plan is the mechanism plus whatever two or more candidate families need;
   single-family specifics — Llama's `date_string` pin, gpt-oss's channels and
   `harmony_final_channel`, OLMo 2's exact-match header tolerance — are TODOs, noted under the
   table of § 5.2 and built only when that family is confirmed; the
   [`models.py`](../../assistant_axis/models.py) stub rows of task 11 wait for the names.
7. **Steering in this plan**: as recommended — the two steering guards of § 5.6 in this plan.
8. **Unknown `model_type`**: as recommended — refuses in both steps.
9. **A Qwen3 smoke run**: yes, before October, as the first entities of the October run.
10. **Step 2 on the 8slot tree** (no side-car): against the recommendation — it REQUIRES
    `--ignore_generation_config`; Roger: "we're unlikely to do this".  § 8 and task 8 of § 10
    say so.

## 16. Escalation

Opus retries once, then Fable, then Roger through [`QUESTIONS.md`](./QUESTIONS.md) (not there yet); it proceeds under a stated
assumption unless the answer would make the work useless (Q3 and Q8 are the two that can).

## Frozen interface

For the October extraction and later plans: `FamilySpec`'s fields (§ 5.2); `ChatLayout` and
`derive_chat_layout` (§ 5.1); the activation metadata keys (§ 7: the four of today plus
`model_type`, `template_kwargs`, `generation_prompt_ids`, `layers`, `max_length`, `batch_size`);
`generation_config.json` and its name; `require_header_layout` and `SlotLayoutError`.
