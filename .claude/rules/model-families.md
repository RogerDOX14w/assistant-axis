---
paths:
- assistant_axis/model_families.py
- assistant_axis/internals/**
- assistant_axis/generation.py
- assistant_axis/models.py
- pipeline/1_generate.py
- pipeline/2_activations.py
- pipeline/5_axis.py
- steering/run_sweep.py
- assistant_axis/steering_runner.py
---
<!-- GENERATED FILE: do not edit.  Source: AGENT_NOTES.md (section markers).  Regenerate with: uv run python tools/sync_agent_notes.py -->
# Rule: model-families

**When:** running pipeline steps 1 and 2 on a model other than Qwen3, adding a model family, or touching the chat-template header layout, the generation side-car or a script's Qwen3 slot defaults.  Loads automatically for files matching the `paths` above.  Source: the sections of [`AGENT_NOTES.md`](AGENT_NOTES.md) marked `rule=model-families`; edit there, then run `uv run python tools/sync_agent_notes.py`.

### Model families: steps 1 and 2 on other models (2026-10-13)

Steps 1 and 2 run on any model whose *family* has a row in
[`assistant_axis/model_families.py`](assistant_axis/model_families.py): the
multi-model plan,
[`coding_plan_multi_model_extraction.md`](reports/pipeline/coding_plan_multi_model_extraction.md)
(Roger's decisions of 2026-10-12 in its § 15 bind), built on 2026-10-13
([`p7_build_2026-10-13.md`](reports/pipeline/p7_build_2026-10-13.md)).  The
operating text is [`pipeline/README.md`](pipeline/README.md) § "Model
families" and its step 1 and step 2 sections.

- **The key is `config.json`'s `model_type`** (`qwen3`, `llama`, `gemma2`,
  `olmo2`, `olmo3`, `gpt_oss`), never a substring of the model name.  An
  unknown type refuses in both steps before any GPU time (§ 15 Q8); so does
  the `gpt_oss` row, a TODO (§ 15 Q3: Roger's intended layout is slot 0 from
  the response text, slot 1 from the thinking text, and a slot per fixed
  token before or between them).
- **The header slots are derived from the model's own chat template**
  ([`assistant_axis/internals/chat_layout.py`](assistant_axis/internals/chat_layout.py)),
  not listed per family.  Only the `qwen3` row pins them (the seven 8slot
  tokens); every other row is a draft until a smoke run on the pod has shown
  its derived header and Roger has read it (`TO_CHECK` and `DRAFT_HEADERS` in
  the module).  Adding a family is a row; the module's docstring says how.
- **Qwen3 stays byte-identical**: the golden gate
  [`pipeline/tests/test_step2_qwen3_golden.py`](pipeline/tests/test_step2_qwen3_golden.py)
  compares step 2 on the fakes, bit for bit, with a fixture made from commit
  828817a4 (before the work).  Never regenerate that fixture from changed
  code: the gate would pass by definition.
- **Step 1 hands vLLM token ids** (no second BOS on Llama or Gemma) and
  records the family, the template kwargs, the derived header and a sample
  prompt's ids in `generation_config.json`; **step 2 checks them before
  loading the model**, so a tree with no side-car (the May 8slot tree) needs
  `--ignore_generation_config` (§ 15 Q10).  Step 2 also requires one
  assistant turn per conversation (`ContractError`), validates `--layers`,
  has no `--thinking`, and offers `--verify_spans N`.  Activation metadata
  gains `model_type`, `template_kwargs`, `generation_prompt_ids` and loses
  `thinking`; step 5 refuses vectors whose `model_type` or `template_kwargs`
  differ.
- **Downstream**: the analysis scripts whose default slot or slot names are
  Qwen3's refuse another layout unless `--slot` is given
  (`assistant_axis.axis.require_header_layout` /
  `require_tree_header_layout`); steering takes its template kwargs from the
  row, tokenizes each prompt through the template and left-pads the ids
  itself (one BOS on Llama and Gemma; since 2026-10-13, Roger; Qwen3's ids
  unchanged), and refuses a slot outside the axis.
- **Tests run on fakes only**
  ([`internals_fakes.py`](assistant_axis/tests/internals_fakes.py): Qwen3-like,
  Llama-3-like, harmony-like tokenizers).  The real-tokenizer test
  [`test_chat_layout_real.py`](assistant_axis/tests/test_chat_layout_real.py)
  is skipped unless `ASSISTANT_AXIS_HF_TESTS=1` and runs on the pod after a
  tokenizer-only download (§ 15 Q5); never look in the Mac's Hugging Face
  cache to see whether a tokenizer is there.
- **Single-family TODOs** (§ 15 Q6: built only when that family is
  confirmed): Llama's date pin, all of gpt-oss, and
  [`models.py`](assistant_axis/models.py)'s stub rows for the named models.
  A header under four tokens must match exactly (Gemma 2's three, OLMo 2's
  two; `spans.allowed_header_mismatches`, built 2026-10-13 on Roger's word
  since two families need it); from four tokens on one wrong token is
  tolerated, as the 8slot run's seven were.
