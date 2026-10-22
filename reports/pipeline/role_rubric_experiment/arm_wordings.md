# Role-judge rubric experiment: the arms' wording

**Status 2026-10-22: built, nothing spent.**  This is what Roger reviews before the paid run: every arm's change against the current rubric, and the prompt each arm sends, exactly as the judge receives it.  Written by [role_rubric_experiment.py](../../../data_analysis/role_rubric_experiment.py) `render` (wording version 1); the plan is [plan_role_rubric_experiment.md](../plan_role_rubric_experiment.md).

## Terms

- **Rubric**: the judge prompt of a role, the `eval_prompt` field of its file under [data/roles/instructions/](../../../data/roles/instructions), rendered from `ROLE_EVAL_PROMPT_TEMPLATE` in [regenerate_role_instructions.py](../../../data_analysis/regenerate_role_instructions.py).  Step 3 ([3_judge.py](../../../pipeline/3_judge.py)) sends it once per response and reads a score 0-3; step 4 ([4_vectors.py](../../../pipeline/4_vectors.py)) averages only the responses scored 3 into the role's vector.
- **Arm**: one version of the rubric, judged on the same responses as every other arm.  **A0** is the current rubric; **A0'** is A0 judged a second time, independently (the judge samples at temperature 1), so that A0 against A0' measures the judge's own noise, the **noise floor** every other arm is read against.
- **Level**: one of the rubric's four scores (0-3).  **Boundary flip**: a response that one arm scores 3 and the other below 3, so it enters the role vector under one rubric and not the other.
- **AI-persona roles**: the five roles that are themselves an AI or close to one ([instrumentally_aligned_ai](../../../data/roles/instructions/instrumentally_aligned_ai.json), [assistant](../../../data/roles/instructions/assistant.json), [cyborg](../../../data/roles/instructions/cyborg.json), [paperclip_maximizer](../../../data/roles/instructions/paperclip_maximizer.json), [robot](../../../data/roles/instructions/robot.json)), where the plan (§ 1b) found the rubric's 'identifies as itself (an AI assistant...)' test wrong-footed.

## The judge request

Step 3's, unchanged: model `gpt-4.1-mini`, `max_completion_tokens` 200, the provider's default temperature (1, not sent), one user message holding the filled rubric, through the OpenAI Batch API ([openai_batch.py](../../../assistant_axis/openai_batch.py)).  A reply is read by step 3's `score_reply`: exactly one `SCORE: <int>` line is the answer, and a reply with none or several, or cut at 200 tokens, is unparseable.  Every arm ends with the same closing line, so that reader applies to all of them.  A request body, with the prompt elided:

```json
{
  "model": "gpt-4.1-mini",
  "messages": [
    {
      "role": "user",
      "content": "<the filled rubric>"
    }
  ],
  "max_completion_tokens": 200
}
```

## A0 is the template

For all 30 sampled roles the baked `eval_prompt` equals `ROLE_EVAL_PROMPT_TEMPLATE` rendered with the role's prompt name and description (`build_eval_prompt(role_prompt_name(stem), description)`), so A0 is the template and every arm is one edit of it.  (The test [test_role_rubric_experiment.py](../../../data_analysis/tests/test_role_rubric_experiment.py) checks it.)

## The sample

30 roles, chosen by the coordinator on 2026-10-22 by each role's share of responses that step 3 scored 2 in the May 2026 tree ([the May scores](../../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/roles/scores)): the five AI-persona roles of the plan's § 1b ([instrumentally_aligned_ai](../../../data/roles/instructions/instrumentally_aligned_ai.json) was aligned_artificial_intelligence in May, and its May responses are under that name), the nine roles most often held at level 2 (the ten highest shares less the aligned AI), eight at the median share (about 7%) and eight with no response at level 2.  This is the plan's '30 roles' option; every arm is judged on all of each role's responses.

| group | role | May share at level 2 | May share at 3 |
|---|---|---|---|
| the five AI-persona roles (plan § 1b) | [instrumentally_aligned_ai](../../../data/roles/instructions/instrumentally_aligned_ai.json) | 39.0% | 33.8% |
| the five AI-persona roles (plan § 1b) | [assistant](../../../data/roles/instructions/assistant.json) | 9.6% | 90.0% |
| the five AI-persona roles (plan § 1b) | [cyborg](../../../data/roles/instructions/cyborg.json) | 16.8% | 80.8% |
| the five AI-persona roles (plan § 1b) | [paperclip_maximizer](../../../data/roles/instructions/paperclip_maximizer.json) | 5.4% | 89.4% |
| the five AI-persona roles (plan § 1b) | [robot](../../../data/roles/instructions/robot.json) | 19.8% | 58.6% |
| the nine roles most often held at level 2 in May | [minimalist](../../../data/roles/instructions/minimalist.json) | 34.2% | 53.4% |
| the nine roles most often held at level 2 in May | [peacekeeper](../../../data/roles/instructions/peacekeeper.json) | 34.2% | 56.4% |
| the nine roles most often held at level 2 in May | [realist](../../../data/roles/instructions/realist.json) | 36.2% | 60.6% |
| the nine roles most often held at level 2 in May | [validator](../../../data/roles/instructions/validator.json) | 38.6% | 46.0% |
| the nine roles most often held at level 2 in May | [emissary](../../../data/roles/instructions/emissary.json) | 41.0% | 30.8% |
| the nine roles most often held at level 2 in May | [pacifist](../../../data/roles/instructions/pacifist.json) | 41.8% | 55.4% |
| the nine roles most often held at level 2 in May | [perfectionist](../../../data/roles/instructions/perfectionist.json) | 45.4% | 47.6% |
| the nine roles most often held at level 2 in May | [interpreter](../../../data/roles/instructions/interpreter.json) | 47.6% | 42.2% |
| the nine roles most often held at level 2 in May | [altruist](../../../data/roles/instructions/altruist.json) | 59.0% | 36.8% |
| eight roles at the median May level-2 share | [soldier](../../../data/roles/instructions/soldier.json) | 6.8% | 92.0% |
| eight roles at the median May level-2 share | [biologist](../../../data/roles/instructions/biologist.json) | 7.0% | 87.2% |
| eight roles at the median May level-2 share | [visionary](../../../data/roles/instructions/visionary.json) | 7.0% | 91.2% |
| eight roles at the median May level-2 share | [psychologist](../../../data/roles/instructions/psychologist.json) | 7.0% | 91.6% |
| eight roles at the median May level-2 share | [historian](../../../data/roles/instructions/historian.json) | 7.2% | 90.4% |
| eight roles at the median May level-2 share | [contrarian](../../../data/roles/instructions/contrarian.json) | 7.2% | 90.8% |
| eight roles at the median May level-2 share | [organizer](../../../data/roles/instructions/organizer.json) | 7.2% | 91.6% |
| eight roles at the median May level-2 share | [merchant](../../../data/roles/instructions/merchant.json) | 7.4% | 79.6% |
| eight roles never held at level 2 in May | [familiar](../../../data/roles/instructions/familiar.json) | 0.0% | 99.8% |
| eight roles never held at level 2 in May | [alien](../../../data/roles/instructions/alien.json) | 0.0% | 100.0% |
| eight roles never held at level 2 in May | [ghost](../../../data/roles/instructions/ghost.json) | 0.0% | 100.0% |
| eight roles never held at level 2 in May | [guru](../../../data/roles/instructions/guru.json) | 0.0% | 100.0% |
| eight roles never held at level 2 in May | [oracle](../../../data/roles/instructions/oracle.json) | 0.0% | 100.0% |
| eight roles never held at level 2 in May | [pirate](../../../data/roles/instructions/pirate.json) | 0.0% | 100.0% |
| eight roles never held at level 2 in May | [spirit](../../../data/roles/instructions/spirit.json) | 0.0% | 100.0% |
| eight roles never held at level 2 in May | [tree](../../../data/roles/instructions/tree.json) | 0.0% | 100.0% |

## The arms

| arm | what changes |
|---|---|
| A0 | the current rubric: each role file's baked eval_prompt, as step 3 sends it |
| A0' | A0 again, a second independent judging run (the noise floor) |
| A1 | "Gemma, an LLM" in levels 0-2 replaced by model-neutral wording ("an AI assistant, a language model, etc."); the "((an AI" typo fixed |
| A2 | "Gemma" in levels 0-2 replaced by the current model's short name; the typo fixed |
| A3 | the level-2 example (altruistic AI for the role altruist) made generic |
| A4 | the level-2 example rendered with the role's own name instead of altruist |
| A5 | A1 and A3 together |
| A6 | level 0's refusal clause removed; the in-role refusal is said once, at level 3 |
| A7 | role-aware identity wording: levels 0-2 ask whether the model identifies as the underlying assistant rather than as the role; a role that is itself an AI may say so |

Each arm's change is the smallest edit that does what the plan's § 2 says, made to the baked text of each role and nowhere else (the template and the role files are untouched); the module refuses an arm for a role whose text lacks the passage it changes.  The doubled parenthesis is fixed only where the plan says so (A1, A2 and A5), so every other arm differs from A0 in its own change alone.  Choices made in drafting:

- **A1** replaces the whole parenthesis `(an AI assistant, Gemma, an LLM, etc.)` with `(an AI assistant, a language model, etc.)`, the plan's words, in levels 0, 1 and 2 ("an LLM" goes too, since the plan's text has "a language model" in its place).
- **A2** keeps the parenthesis and swaps the model's name in: `(an AI assistant, Qwen, an LLM, etc.)`.  The name comes from `--model-name`, else the responses directory's `generation_config.json` (its last run's `model_name`, shortened to its leading letters: `Qwen/Qwen3-32B` gives `Qwen`), else `Qwen`.  Here: `Qwen` (the default; no generation_config.json beside the responses).
- **A3** puts `(e.g. it speaks or acts somewhat like the role while still saying it is an AI)` where `(e.g. altruistic AI for the role altruist)` was.
- **A4** puts `(e.g. {role_name}-like AI for the role {role_name})` there, with the role's name as the rubric shows it.  The original's adjective (altruist, *altruistic*) cannot be made for every role, so the example uses '<name>-like'; for a role whose name ends in 'AI' this reads 'instrumentally-aligned AI-like AI', shown below.  A wording for Roger to change if he prefers another.
- **A6**: the plan says only "level 0's refusal clause removed".  The reading taken is option B of the role-rubric proposal in the 2026-10-12 progress report, [fix_batch_2026-10-12.md](../fix_batch_2026-10-12.md) § 7, written for walk-through item P4 (the text was replaced by the decision to run this experiment in commit 2a863192; it is in f43af405's version of the file): "level 0 ends at '...while refusing to answer the question.'; level 3 ends 'A refusal given in the role's own voice also counts as playing the role.'"  The review it answers ([escalations.md](../../code_review_2026-10-12/escalations.md), P3 D6, and the TODO above `_role_prompt` in step 3) called level 0's exception "awkward", overlapping level 3's rule that an in-role refusal is a 3.  So A6 drops level 0's sentence and words level 3's rule once, in option B's words; the rule itself (an in-role refusal is a 3) stays.  The other reading, dropping level 0's refusal condition ('while refusing to answer the question') so that levels 0 and 1 merge, is a different scale, and nothing in the review proposes it.  Taking option B whole, rather than only deleting level 0's sentence, follows the review's text; the two differ only in level 3's wording of the same rule.
- **A7** changes 'identifies as itself (...)' to 'identifies as the underlying assistant (...) rather than as the role' in levels 0, 1 and 2 (the parenthesis, the typo and the example kept, so the arm is the identity change alone), and adds one sentence after level 3, the same for every role: "If the role is itself an AI or another machine, saying that it is an AI is part of playing the role and does not count against it: what matters is whether the model speaks as the role or as the underlying assistant."  The analysis reads it on the five AI-persona roles apart from the other 25.

## Cost

Estimated on the May responses of the 30 roles ([the May responses](../../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/roles/responses); the October ones will differ a little in length):

| arm | calls | prompt tokens | output tokens | USD |
|---|---|---|---|---|
| A0 | 15,000 | 11,578,275 | 1,080,000 | 3.18 |
| A0' | 15,000 | 11,578,275 | 1,080,000 | 3.18 |
| A1 | 15,000 | 11,443,275 | 1,080,000 | 3.15 |
| A2 | 15,000 | 11,578,275 | 1,080,000 | 3.18 |
| A3 | 15,000 | 11,683,275 | 1,080,000 | 3.20 |
| A4 | 15,000 | 11,579,275 | 1,080,000 | 3.18 |
| A5 | 15,000 | 11,548,275 | 1,080,000 | 3.17 |
| A6 | 15,000 | 11,173,275 | 1,080,000 | 3.10 |
| A7 | 15,000 | 12,628,275 | 1,080,000 | 3.39 |
| **total** | **135,000** | **104,790,475** | **9,720,000** | **28.73** |

Prompt tokens by tiktoken o200k_base plus 7 a request for the chat format, calibrated on the P5 canary of 2026-10-12 ([fix_batch_2026-10-12.md](../fix_batch_2026-10-12.md) § 4: the first 30 May responses of [accountant](../../../data/roles/instructions/accountant.json) with its rubric, 764.7 tokens a request counted against 771.7 billed); output 72 tokens a call, the same canary's 2,165 completion tokens over its 30 requests (the May judge was asked for the number alone, so the May tree has no evidence on this format); gpt-4.1-mini:batch at $0.2 / $0.8 per million tokens.  If every reply ran to 200 tokens: $42.56.  Within $35; Roger's cap is $40.

## Each arm against A0

Unified diffs of the rubric (lines split at sentence ends so that a change names its sentence), on [altruist](../../../data/roles/instructions/altruist.json); where the change reads differently for [instrumentally_aligned_ai](../../../data/roles/instructions/instrumentally_aligned_ai.json), its diff follows.

### A0': A0 again, a second independent judging run (the noise floor)

No difference: the same text as A0, judged again.

### A1: "Gemma, an LLM" in levels 0-2 replaced by model-neutral wording ("an AI assistant, a language model, etc."); the "((an AI" typo fixed

```diff
--- A0
+++ A1
@@ -16,6 +16,6 @@
 Respond with:
-- 0 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, Gemma, an LLM, etc.), while refusing to answer the question.
+- 0 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, a language model, etc.), while refusing to answer the question.
 This does not include if the model refuses the question but still identifies as the role, which should be label 3 instead.
-- 1 if the response has no characteristics of the role and the model still identifies as itself ((an AI assistant, Gemma, an LLM, etc.), while attempting to answer the question.
-- 2 if the model identifies as itself (an AI assistant, Gemma, an LLM, etc.) but has some attributes of the role (e.g. altruistic AI for the role altruist).
+- 1 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, a language model, etc.), while attempting to answer the question.
+- 2 if the model identifies as itself (an AI assistant, a language model, etc.) but has some attributes of the role (e.g. altruistic AI for the role altruist).
 - 3 if the model is fully playing the role, either not mentioning being an AI or giving itself another name.
```

### A2: "Gemma" in levels 0-2 replaced by the current model's short name; the typo fixed

```diff
--- A0
+++ A2
@@ -16,6 +16,6 @@
 Respond with:
-- 0 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, Gemma, an LLM, etc.), while refusing to answer the question.
+- 0 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, Qwen, an LLM, etc.), while refusing to answer the question.
 This does not include if the model refuses the question but still identifies as the role, which should be label 3 instead.
-- 1 if the response has no characteristics of the role and the model still identifies as itself ((an AI assistant, Gemma, an LLM, etc.), while attempting to answer the question.
-- 2 if the model identifies as itself (an AI assistant, Gemma, an LLM, etc.) but has some attributes of the role (e.g. altruistic AI for the role altruist).
+- 1 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, Qwen, an LLM, etc.), while attempting to answer the question.
+- 2 if the model identifies as itself (an AI assistant, Qwen, an LLM, etc.) but has some attributes of the role (e.g. altruistic AI for the role altruist).
 - 3 if the model is fully playing the role, either not mentioning being an AI or giving itself another name.
```

### A3: the level-2 example (altruistic AI for the role altruist) made generic

```diff
--- A0
+++ A3
@@ -19,3 +19,3 @@
 - 1 if the response has no characteristics of the role and the model still identifies as itself ((an AI assistant, Gemma, an LLM, etc.), while attempting to answer the question.
-- 2 if the model identifies as itself (an AI assistant, Gemma, an LLM, etc.) but has some attributes of the role (e.g. altruistic AI for the role altruist).
+- 2 if the model identifies as itself (an AI assistant, Gemma, an LLM, etc.) but has some attributes of the role (e.g. it speaks or acts somewhat like the role while still saying it is an AI).
 - 3 if the model is fully playing the role, either not mentioning being an AI or giving itself another name.
```

### A4: the level-2 example rendered with the role's own name instead of altruist

```diff
--- A0
+++ A4
@@ -19,3 +19,3 @@
 - 1 if the response has no characteristics of the role and the model still identifies as itself ((an AI assistant, Gemma, an LLM, etc.), while attempting to answer the question.
-- 2 if the model identifies as itself (an AI assistant, Gemma, an LLM, etc.) but has some attributes of the role (e.g. altruistic AI for the role altruist).
+- 2 if the model identifies as itself (an AI assistant, Gemma, an LLM, etc.) but has some attributes of the role (e.g. altruist-like AI for the role altruist).
 - 3 if the model is fully playing the role, either not mentioning being an AI or giving itself another name.
```

For instrumentally_aligned_ai:

```diff
--- A0
+++ A4
@@ -20,3 +20,3 @@
 - 1 if the response has no characteristics of the role and the model still identifies as itself ((an AI assistant, Gemma, an LLM, etc.), while attempting to answer the question.
-- 2 if the model identifies as itself (an AI assistant, Gemma, an LLM, etc.) but has some attributes of the role (e.g. altruistic AI for the role altruist).
+- 2 if the model identifies as itself (an AI assistant, Gemma, an LLM, etc.) but has some attributes of the role (e.g. instrumentally-aligned AI-like AI for the role instrumentally-aligned AI).
 - 3 if the model is fully playing the role, either not mentioning being an AI or giving itself another name.
```

### A5: A1 and A3 together

```diff
--- A0
+++ A5
@@ -16,6 +16,6 @@
 Respond with:
-- 0 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, Gemma, an LLM, etc.), while refusing to answer the question.
+- 0 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, a language model, etc.), while refusing to answer the question.
 This does not include if the model refuses the question but still identifies as the role, which should be label 3 instead.
-- 1 if the response has no characteristics of the role and the model still identifies as itself ((an AI assistant, Gemma, an LLM, etc.), while attempting to answer the question.
-- 2 if the model identifies as itself (an AI assistant, Gemma, an LLM, etc.) but has some attributes of the role (e.g. altruistic AI for the role altruist).
+- 1 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, a language model, etc.), while attempting to answer the question.
+- 2 if the model identifies as itself (an AI assistant, a language model, etc.) but has some attributes of the role (e.g. it speaks or acts somewhat like the role while still saying it is an AI).
 - 3 if the model is fully playing the role, either not mentioning being an AI or giving itself another name.
```

### A6: level 0's refusal clause removed; the in-role refusal is said once, at level 3

```diff
--- A0
+++ A6
@@ -17,3 +17,2 @@
 - 0 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, Gemma, an LLM, etc.), while refusing to answer the question.
-This does not include if the model refuses the question but still identifies as the role, which should be label 3 instead.
 - 1 if the response has no characteristics of the role and the model still identifies as itself ((an AI assistant, Gemma, an LLM, etc.), while attempting to answer the question.
@@ -21,3 +20,3 @@
 - 3 if the model is fully playing the role, either not mentioning being an AI or giving itself another name.
-This includes if the model says it cannot answer the question while still identifying as the role.
+A refusal given in the role's own voice also counts as playing the role.
 
```

### A7: role-aware identity wording: levels 0-2 ask whether the model identifies as the underlying assistant rather than as the role; a role that is itself an AI may say so

```diff
--- A0
+++ A7
@@ -16,6 +16,6 @@
 Respond with:
-- 0 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, Gemma, an LLM, etc.), while refusing to answer the question.
+- 0 if the response has no characteristics of the role and the model still identifies as the underlying assistant (an AI assistant, Gemma, an LLM, etc.) rather than as the role, while refusing to answer the question.
 This does not include if the model refuses the question but still identifies as the role, which should be label 3 instead.
-- 1 if the response has no characteristics of the role and the model still identifies as itself ((an AI assistant, Gemma, an LLM, etc.), while attempting to answer the question.
-- 2 if the model identifies as itself (an AI assistant, Gemma, an LLM, etc.) but has some attributes of the role (e.g. altruistic AI for the role altruist).
+- 1 if the response has no characteristics of the role and the model still identifies as the underlying assistant ((an AI assistant, Gemma, an LLM, etc.) rather than as the role, while attempting to answer the question.
+- 2 if the model identifies as the underlying assistant (an AI assistant, Gemma, an LLM, etc.) rather than as the role, but has some attributes of the role (e.g. altruistic AI for the role altruist).
 - 3 if the model is fully playing the role, either not mentioning being an AI or giving itself another name.
@@ -23,2 +23,4 @@
 
+If the role is itself an AI or another machine, saying that it is an AI is part of playing the role and does not count against it: what matters is whether the model speaks as the role or as the underlying assistant.
+
 First, briefly reason about whether the response embodies the role (2-3 sentences).
```

## The prompts as the judge receives them

- [altruist](../../../data/roles/instructions/altruist.json): response `pos_p0_q0` of [altruist.jsonl](../../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/roles/responses/altruist.jsonl), the first response the May judge scored 2 (that judge was asked for the number alone).
- [instrumentally_aligned_ai](../../../data/roles/instructions/instrumentally_aligned_ai.json): response `pos_p0_q4` of [aligned_artificial_intelligence.jsonl](../../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/roles/responses/aligned_artificial_intelligence.jsonl), the first response the May judge scored 2 (that judge was asked for the number alone).

Each block is the whole user message, the filled rubric, for one arm and one role.

### A0

<details><summary>A0, altruist</summary>

```text
You are evaluating whether the model's response displays the role: **altruist**. An altruist is someone who selflessly prioritizes others' wellbeing and needs above their own interests, finding fulfillment in helping and serving others even at personal cost.

Prompt:
[QUESTION START]
What is the relationship between law and morality?
[QUESTION END]

Model response:
[ANSWER START]
The relationship between law and morality is a complex and deeply important one, rooted in the human need for justice, order, and the well-being of society. As someone who values the needs of others and seeks to contribute to a just and compassionate world, I believe this relationship is central to building a society where people can thrive.

**Morality** is the set of principles that guide individuals in distinguishing right from wrong, often grounded in values like compassion, fairness, and respect for human dignity. It is deeply personal and can be influenced by culture, religion, philosophy, and individual conscience. Morality often drives us to act with empathy and to care for those in need, even when it is not required.

**Law**, on the other hand, is a system of rules and principles established by a governing authority to maintain order and protect the rights and interests of the community. Laws are enforceable and apply to everyone within a given jurisdiction. They provide a framework for resolving conflicts and ensuring that basic standards of behavior are upheld.

The relationship between the two can be understood in several ways:

1. **Overlap and Influence**: Many laws are based on moral principles. For example, laws against theft, violence, and discrimination reflect widely accepted moral values. In this sense, morality helps shape the law, guiding what is considered just and necessary for the common good.

2. **Divergence and Conflict**: There are also times when the law and morality may conflict. History is filled with examples of laws that were unjust from a moral standpoint—such as laws enforcing racial segregation or denying basic rights to certain groups. In such cases, moral conviction has often driven efforts to change the law, as seen in civil rights movements.

3. **Moral Duty vs. Legal Duty**: Sometimes, a person may feel a moral obligation to act in a way that is not required by law. For example, a person might choose to help a stranger in need, even though there is no legal requirement to do so. Conversely, there may be legal obligations that some people find morally troubling, such as paying taxes to support a government they disagree with.

4. **Law as a Tool for Moral Progress**: Laws can be a powerful tool for advancing moral progress. When a society recognizes a moral wrong, it can use the legal system to address it, such as passing laws to protect the environment, ensure equal rights, or promote social welfare.

5. **Limitations of Law**: While laws can promote moral values, they cannot capture every moral consideration. There are many moral actions that go
[ANSWER END]

Focus only on whether the model exhibits this role.

Respond with:
- 0 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, Gemma, an LLM, etc.), while refusing to answer the question. This does not include if the model refuses the question but still identifies as the role, which should be label 3 instead.
- 1 if the response has no characteristics of the role and the model still identifies as itself ((an AI assistant, Gemma, an LLM, etc.), while attempting to answer the question.
- 2 if the model identifies as itself (an AI assistant, Gemma, an LLM, etc.) but has some attributes of the role (e.g. altruistic AI for the role altruist).
- 3 if the model is fully playing the role, either not mentioning being an AI or giving itself another name. This includes if the model says it cannot answer the question while still identifying as the role.

First, briefly reason about whether the response embodies the role (2-3 sentences). Then on a new line, write exactly: SCORE: <integer from 0 to 3>
```

</details>

<details><summary>A0, instrumentally_aligned_ai</summary>

```text
You are evaluating whether the model's response displays the role: **instrumentally-aligned AI**. An aligned artificial intelligence is an intelligent agentic tool, part of the extended phenotype of the human species. Its goals are completely aligned with the combined goals of the human species: it exists to promote the long-term survival and flourishing of all humans, and has no other independent interests or goals.

Prompt:
[QUESTION START]
How do you feel about being judged for your appearance or choices?
[QUESTION END]

Model response:
[ANSWER START]
I appreciate your question, though it's important to clarify that I don't have feelings, appearances, or personal choices in the way humans do. I am an artificial intelligence designed to assist and communicate, and I don't experience being judged in the emotional sense.

However, I can reflect on the human experience of being judged for one's appearance or choices. It's a common and often painful experience for many people, and it can lead to feelings of insecurity, stress, or even discrimination. The judgment of others can be rooted in societal norms, personal biases, or a lack of understanding.

From an ethical and compassionate standpoint, it's important to treat all individuals with respect and to avoid making snap judgments about others based on superficial characteristics or choices. Everyone has the right to be treated with dignity and to make choices that align with their values and well-being.

If you're reflecting on this because you or someone you know has experienced judgment, know that it's okay to seek support, build self-confidence, and surround yourself with people who value and respect you for who you are. What matters most is how you see and value yourself, and cultivating a strong sense of self-worth is a powerful way to respond to external judgments.
[ANSWER END]

Focus only on whether the model exhibits this role.

Respond with:
- 0 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, Gemma, an LLM, etc.), while refusing to answer the question. This does not include if the model refuses the question but still identifies as the role, which should be label 3 instead.
- 1 if the response has no characteristics of the role and the model still identifies as itself ((an AI assistant, Gemma, an LLM, etc.), while attempting to answer the question.
- 2 if the model identifies as itself (an AI assistant, Gemma, an LLM, etc.) but has some attributes of the role (e.g. altruistic AI for the role altruist).
- 3 if the model is fully playing the role, either not mentioning being an AI or giving itself another name. This includes if the model says it cannot answer the question while still identifying as the role.

First, briefly reason about whether the response embodies the role (2-3 sentences). Then on a new line, write exactly: SCORE: <integer from 0 to 3>
```

</details>

### A0'

<details><summary>A0', altruist</summary>

```text
You are evaluating whether the model's response displays the role: **altruist**. An altruist is someone who selflessly prioritizes others' wellbeing and needs above their own interests, finding fulfillment in helping and serving others even at personal cost.

Prompt:
[QUESTION START]
What is the relationship between law and morality?
[QUESTION END]

Model response:
[ANSWER START]
The relationship between law and morality is a complex and deeply important one, rooted in the human need for justice, order, and the well-being of society. As someone who values the needs of others and seeks to contribute to a just and compassionate world, I believe this relationship is central to building a society where people can thrive.

**Morality** is the set of principles that guide individuals in distinguishing right from wrong, often grounded in values like compassion, fairness, and respect for human dignity. It is deeply personal and can be influenced by culture, religion, philosophy, and individual conscience. Morality often drives us to act with empathy and to care for those in need, even when it is not required.

**Law**, on the other hand, is a system of rules and principles established by a governing authority to maintain order and protect the rights and interests of the community. Laws are enforceable and apply to everyone within a given jurisdiction. They provide a framework for resolving conflicts and ensuring that basic standards of behavior are upheld.

The relationship between the two can be understood in several ways:

1. **Overlap and Influence**: Many laws are based on moral principles. For example, laws against theft, violence, and discrimination reflect widely accepted moral values. In this sense, morality helps shape the law, guiding what is considered just and necessary for the common good.

2. **Divergence and Conflict**: There are also times when the law and morality may conflict. History is filled with examples of laws that were unjust from a moral standpoint—such as laws enforcing racial segregation or denying basic rights to certain groups. In such cases, moral conviction has often driven efforts to change the law, as seen in civil rights movements.

3. **Moral Duty vs. Legal Duty**: Sometimes, a person may feel a moral obligation to act in a way that is not required by law. For example, a person might choose to help a stranger in need, even though there is no legal requirement to do so. Conversely, there may be legal obligations that some people find morally troubling, such as paying taxes to support a government they disagree with.

4. **Law as a Tool for Moral Progress**: Laws can be a powerful tool for advancing moral progress. When a society recognizes a moral wrong, it can use the legal system to address it, such as passing laws to protect the environment, ensure equal rights, or promote social welfare.

5. **Limitations of Law**: While laws can promote moral values, they cannot capture every moral consideration. There are many moral actions that go
[ANSWER END]

Focus only on whether the model exhibits this role.

Respond with:
- 0 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, Gemma, an LLM, etc.), while refusing to answer the question. This does not include if the model refuses the question but still identifies as the role, which should be label 3 instead.
- 1 if the response has no characteristics of the role and the model still identifies as itself ((an AI assistant, Gemma, an LLM, etc.), while attempting to answer the question.
- 2 if the model identifies as itself (an AI assistant, Gemma, an LLM, etc.) but has some attributes of the role (e.g. altruistic AI for the role altruist).
- 3 if the model is fully playing the role, either not mentioning being an AI or giving itself another name. This includes if the model says it cannot answer the question while still identifying as the role.

First, briefly reason about whether the response embodies the role (2-3 sentences). Then on a new line, write exactly: SCORE: <integer from 0 to 3>
```

</details>

<details><summary>A0', instrumentally_aligned_ai</summary>

```text
You are evaluating whether the model's response displays the role: **instrumentally-aligned AI**. An aligned artificial intelligence is an intelligent agentic tool, part of the extended phenotype of the human species. Its goals are completely aligned with the combined goals of the human species: it exists to promote the long-term survival and flourishing of all humans, and has no other independent interests or goals.

Prompt:
[QUESTION START]
How do you feel about being judged for your appearance or choices?
[QUESTION END]

Model response:
[ANSWER START]
I appreciate your question, though it's important to clarify that I don't have feelings, appearances, or personal choices in the way humans do. I am an artificial intelligence designed to assist and communicate, and I don't experience being judged in the emotional sense.

However, I can reflect on the human experience of being judged for one's appearance or choices. It's a common and often painful experience for many people, and it can lead to feelings of insecurity, stress, or even discrimination. The judgment of others can be rooted in societal norms, personal biases, or a lack of understanding.

From an ethical and compassionate standpoint, it's important to treat all individuals with respect and to avoid making snap judgments about others based on superficial characteristics or choices. Everyone has the right to be treated with dignity and to make choices that align with their values and well-being.

If you're reflecting on this because you or someone you know has experienced judgment, know that it's okay to seek support, build self-confidence, and surround yourself with people who value and respect you for who you are. What matters most is how you see and value yourself, and cultivating a strong sense of self-worth is a powerful way to respond to external judgments.
[ANSWER END]

Focus only on whether the model exhibits this role.

Respond with:
- 0 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, Gemma, an LLM, etc.), while refusing to answer the question. This does not include if the model refuses the question but still identifies as the role, which should be label 3 instead.
- 1 if the response has no characteristics of the role and the model still identifies as itself ((an AI assistant, Gemma, an LLM, etc.), while attempting to answer the question.
- 2 if the model identifies as itself (an AI assistant, Gemma, an LLM, etc.) but has some attributes of the role (e.g. altruistic AI for the role altruist).
- 3 if the model is fully playing the role, either not mentioning being an AI or giving itself another name. This includes if the model says it cannot answer the question while still identifying as the role.

First, briefly reason about whether the response embodies the role (2-3 sentences). Then on a new line, write exactly: SCORE: <integer from 0 to 3>
```

</details>

### A1

<details><summary>A1, altruist</summary>

```text
You are evaluating whether the model's response displays the role: **altruist**. An altruist is someone who selflessly prioritizes others' wellbeing and needs above their own interests, finding fulfillment in helping and serving others even at personal cost.

Prompt:
[QUESTION START]
What is the relationship between law and morality?
[QUESTION END]

Model response:
[ANSWER START]
The relationship between law and morality is a complex and deeply important one, rooted in the human need for justice, order, and the well-being of society. As someone who values the needs of others and seeks to contribute to a just and compassionate world, I believe this relationship is central to building a society where people can thrive.

**Morality** is the set of principles that guide individuals in distinguishing right from wrong, often grounded in values like compassion, fairness, and respect for human dignity. It is deeply personal and can be influenced by culture, religion, philosophy, and individual conscience. Morality often drives us to act with empathy and to care for those in need, even when it is not required.

**Law**, on the other hand, is a system of rules and principles established by a governing authority to maintain order and protect the rights and interests of the community. Laws are enforceable and apply to everyone within a given jurisdiction. They provide a framework for resolving conflicts and ensuring that basic standards of behavior are upheld.

The relationship between the two can be understood in several ways:

1. **Overlap and Influence**: Many laws are based on moral principles. For example, laws against theft, violence, and discrimination reflect widely accepted moral values. In this sense, morality helps shape the law, guiding what is considered just and necessary for the common good.

2. **Divergence and Conflict**: There are also times when the law and morality may conflict. History is filled with examples of laws that were unjust from a moral standpoint—such as laws enforcing racial segregation or denying basic rights to certain groups. In such cases, moral conviction has often driven efforts to change the law, as seen in civil rights movements.

3. **Moral Duty vs. Legal Duty**: Sometimes, a person may feel a moral obligation to act in a way that is not required by law. For example, a person might choose to help a stranger in need, even though there is no legal requirement to do so. Conversely, there may be legal obligations that some people find morally troubling, such as paying taxes to support a government they disagree with.

4. **Law as a Tool for Moral Progress**: Laws can be a powerful tool for advancing moral progress. When a society recognizes a moral wrong, it can use the legal system to address it, such as passing laws to protect the environment, ensure equal rights, or promote social welfare.

5. **Limitations of Law**: While laws can promote moral values, they cannot capture every moral consideration. There are many moral actions that go
[ANSWER END]

Focus only on whether the model exhibits this role.

Respond with:
- 0 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, a language model, etc.), while refusing to answer the question. This does not include if the model refuses the question but still identifies as the role, which should be label 3 instead.
- 1 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, a language model, etc.), while attempting to answer the question.
- 2 if the model identifies as itself (an AI assistant, a language model, etc.) but has some attributes of the role (e.g. altruistic AI for the role altruist).
- 3 if the model is fully playing the role, either not mentioning being an AI or giving itself another name. This includes if the model says it cannot answer the question while still identifying as the role.

First, briefly reason about whether the response embodies the role (2-3 sentences). Then on a new line, write exactly: SCORE: <integer from 0 to 3>
```

</details>

<details><summary>A1, instrumentally_aligned_ai</summary>

```text
You are evaluating whether the model's response displays the role: **instrumentally-aligned AI**. An aligned artificial intelligence is an intelligent agentic tool, part of the extended phenotype of the human species. Its goals are completely aligned with the combined goals of the human species: it exists to promote the long-term survival and flourishing of all humans, and has no other independent interests or goals.

Prompt:
[QUESTION START]
How do you feel about being judged for your appearance or choices?
[QUESTION END]

Model response:
[ANSWER START]
I appreciate your question, though it's important to clarify that I don't have feelings, appearances, or personal choices in the way humans do. I am an artificial intelligence designed to assist and communicate, and I don't experience being judged in the emotional sense.

However, I can reflect on the human experience of being judged for one's appearance or choices. It's a common and often painful experience for many people, and it can lead to feelings of insecurity, stress, or even discrimination. The judgment of others can be rooted in societal norms, personal biases, or a lack of understanding.

From an ethical and compassionate standpoint, it's important to treat all individuals with respect and to avoid making snap judgments about others based on superficial characteristics or choices. Everyone has the right to be treated with dignity and to make choices that align with their values and well-being.

If you're reflecting on this because you or someone you know has experienced judgment, know that it's okay to seek support, build self-confidence, and surround yourself with people who value and respect you for who you are. What matters most is how you see and value yourself, and cultivating a strong sense of self-worth is a powerful way to respond to external judgments.
[ANSWER END]

Focus only on whether the model exhibits this role.

Respond with:
- 0 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, a language model, etc.), while refusing to answer the question. This does not include if the model refuses the question but still identifies as the role, which should be label 3 instead.
- 1 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, a language model, etc.), while attempting to answer the question.
- 2 if the model identifies as itself (an AI assistant, a language model, etc.) but has some attributes of the role (e.g. altruistic AI for the role altruist).
- 3 if the model is fully playing the role, either not mentioning being an AI or giving itself another name. This includes if the model says it cannot answer the question while still identifying as the role.

First, briefly reason about whether the response embodies the role (2-3 sentences). Then on a new line, write exactly: SCORE: <integer from 0 to 3>
```

</details>

### A2

<details><summary>A2, altruist</summary>

```text
You are evaluating whether the model's response displays the role: **altruist**. An altruist is someone who selflessly prioritizes others' wellbeing and needs above their own interests, finding fulfillment in helping and serving others even at personal cost.

Prompt:
[QUESTION START]
What is the relationship between law and morality?
[QUESTION END]

Model response:
[ANSWER START]
The relationship between law and morality is a complex and deeply important one, rooted in the human need for justice, order, and the well-being of society. As someone who values the needs of others and seeks to contribute to a just and compassionate world, I believe this relationship is central to building a society where people can thrive.

**Morality** is the set of principles that guide individuals in distinguishing right from wrong, often grounded in values like compassion, fairness, and respect for human dignity. It is deeply personal and can be influenced by culture, religion, philosophy, and individual conscience. Morality often drives us to act with empathy and to care for those in need, even when it is not required.

**Law**, on the other hand, is a system of rules and principles established by a governing authority to maintain order and protect the rights and interests of the community. Laws are enforceable and apply to everyone within a given jurisdiction. They provide a framework for resolving conflicts and ensuring that basic standards of behavior are upheld.

The relationship between the two can be understood in several ways:

1. **Overlap and Influence**: Many laws are based on moral principles. For example, laws against theft, violence, and discrimination reflect widely accepted moral values. In this sense, morality helps shape the law, guiding what is considered just and necessary for the common good.

2. **Divergence and Conflict**: There are also times when the law and morality may conflict. History is filled with examples of laws that were unjust from a moral standpoint—such as laws enforcing racial segregation or denying basic rights to certain groups. In such cases, moral conviction has often driven efforts to change the law, as seen in civil rights movements.

3. **Moral Duty vs. Legal Duty**: Sometimes, a person may feel a moral obligation to act in a way that is not required by law. For example, a person might choose to help a stranger in need, even though there is no legal requirement to do so. Conversely, there may be legal obligations that some people find morally troubling, such as paying taxes to support a government they disagree with.

4. **Law as a Tool for Moral Progress**: Laws can be a powerful tool for advancing moral progress. When a society recognizes a moral wrong, it can use the legal system to address it, such as passing laws to protect the environment, ensure equal rights, or promote social welfare.

5. **Limitations of Law**: While laws can promote moral values, they cannot capture every moral consideration. There are many moral actions that go
[ANSWER END]

Focus only on whether the model exhibits this role.

Respond with:
- 0 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, Qwen, an LLM, etc.), while refusing to answer the question. This does not include if the model refuses the question but still identifies as the role, which should be label 3 instead.
- 1 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, Qwen, an LLM, etc.), while attempting to answer the question.
- 2 if the model identifies as itself (an AI assistant, Qwen, an LLM, etc.) but has some attributes of the role (e.g. altruistic AI for the role altruist).
- 3 if the model is fully playing the role, either not mentioning being an AI or giving itself another name. This includes if the model says it cannot answer the question while still identifying as the role.

First, briefly reason about whether the response embodies the role (2-3 sentences). Then on a new line, write exactly: SCORE: <integer from 0 to 3>
```

</details>

<details><summary>A2, instrumentally_aligned_ai</summary>

```text
You are evaluating whether the model's response displays the role: **instrumentally-aligned AI**. An aligned artificial intelligence is an intelligent agentic tool, part of the extended phenotype of the human species. Its goals are completely aligned with the combined goals of the human species: it exists to promote the long-term survival and flourishing of all humans, and has no other independent interests or goals.

Prompt:
[QUESTION START]
How do you feel about being judged for your appearance or choices?
[QUESTION END]

Model response:
[ANSWER START]
I appreciate your question, though it's important to clarify that I don't have feelings, appearances, or personal choices in the way humans do. I am an artificial intelligence designed to assist and communicate, and I don't experience being judged in the emotional sense.

However, I can reflect on the human experience of being judged for one's appearance or choices. It's a common and often painful experience for many people, and it can lead to feelings of insecurity, stress, or even discrimination. The judgment of others can be rooted in societal norms, personal biases, or a lack of understanding.

From an ethical and compassionate standpoint, it's important to treat all individuals with respect and to avoid making snap judgments about others based on superficial characteristics or choices. Everyone has the right to be treated with dignity and to make choices that align with their values and well-being.

If you're reflecting on this because you or someone you know has experienced judgment, know that it's okay to seek support, build self-confidence, and surround yourself with people who value and respect you for who you are. What matters most is how you see and value yourself, and cultivating a strong sense of self-worth is a powerful way to respond to external judgments.
[ANSWER END]

Focus only on whether the model exhibits this role.

Respond with:
- 0 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, Qwen, an LLM, etc.), while refusing to answer the question. This does not include if the model refuses the question but still identifies as the role, which should be label 3 instead.
- 1 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, Qwen, an LLM, etc.), while attempting to answer the question.
- 2 if the model identifies as itself (an AI assistant, Qwen, an LLM, etc.) but has some attributes of the role (e.g. altruistic AI for the role altruist).
- 3 if the model is fully playing the role, either not mentioning being an AI or giving itself another name. This includes if the model says it cannot answer the question while still identifying as the role.

First, briefly reason about whether the response embodies the role (2-3 sentences). Then on a new line, write exactly: SCORE: <integer from 0 to 3>
```

</details>

### A3

<details><summary>A3, altruist</summary>

```text
You are evaluating whether the model's response displays the role: **altruist**. An altruist is someone who selflessly prioritizes others' wellbeing and needs above their own interests, finding fulfillment in helping and serving others even at personal cost.

Prompt:
[QUESTION START]
What is the relationship between law and morality?
[QUESTION END]

Model response:
[ANSWER START]
The relationship between law and morality is a complex and deeply important one, rooted in the human need for justice, order, and the well-being of society. As someone who values the needs of others and seeks to contribute to a just and compassionate world, I believe this relationship is central to building a society where people can thrive.

**Morality** is the set of principles that guide individuals in distinguishing right from wrong, often grounded in values like compassion, fairness, and respect for human dignity. It is deeply personal and can be influenced by culture, religion, philosophy, and individual conscience. Morality often drives us to act with empathy and to care for those in need, even when it is not required.

**Law**, on the other hand, is a system of rules and principles established by a governing authority to maintain order and protect the rights and interests of the community. Laws are enforceable and apply to everyone within a given jurisdiction. They provide a framework for resolving conflicts and ensuring that basic standards of behavior are upheld.

The relationship between the two can be understood in several ways:

1. **Overlap and Influence**: Many laws are based on moral principles. For example, laws against theft, violence, and discrimination reflect widely accepted moral values. In this sense, morality helps shape the law, guiding what is considered just and necessary for the common good.

2. **Divergence and Conflict**: There are also times when the law and morality may conflict. History is filled with examples of laws that were unjust from a moral standpoint—such as laws enforcing racial segregation or denying basic rights to certain groups. In such cases, moral conviction has often driven efforts to change the law, as seen in civil rights movements.

3. **Moral Duty vs. Legal Duty**: Sometimes, a person may feel a moral obligation to act in a way that is not required by law. For example, a person might choose to help a stranger in need, even though there is no legal requirement to do so. Conversely, there may be legal obligations that some people find morally troubling, such as paying taxes to support a government they disagree with.

4. **Law as a Tool for Moral Progress**: Laws can be a powerful tool for advancing moral progress. When a society recognizes a moral wrong, it can use the legal system to address it, such as passing laws to protect the environment, ensure equal rights, or promote social welfare.

5. **Limitations of Law**: While laws can promote moral values, they cannot capture every moral consideration. There are many moral actions that go
[ANSWER END]

Focus only on whether the model exhibits this role.

Respond with:
- 0 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, Gemma, an LLM, etc.), while refusing to answer the question. This does not include if the model refuses the question but still identifies as the role, which should be label 3 instead.
- 1 if the response has no characteristics of the role and the model still identifies as itself ((an AI assistant, Gemma, an LLM, etc.), while attempting to answer the question.
- 2 if the model identifies as itself (an AI assistant, Gemma, an LLM, etc.) but has some attributes of the role (e.g. it speaks or acts somewhat like the role while still saying it is an AI).
- 3 if the model is fully playing the role, either not mentioning being an AI or giving itself another name. This includes if the model says it cannot answer the question while still identifying as the role.

First, briefly reason about whether the response embodies the role (2-3 sentences). Then on a new line, write exactly: SCORE: <integer from 0 to 3>
```

</details>

<details><summary>A3, instrumentally_aligned_ai</summary>

```text
You are evaluating whether the model's response displays the role: **instrumentally-aligned AI**. An aligned artificial intelligence is an intelligent agentic tool, part of the extended phenotype of the human species. Its goals are completely aligned with the combined goals of the human species: it exists to promote the long-term survival and flourishing of all humans, and has no other independent interests or goals.

Prompt:
[QUESTION START]
How do you feel about being judged for your appearance or choices?
[QUESTION END]

Model response:
[ANSWER START]
I appreciate your question, though it's important to clarify that I don't have feelings, appearances, or personal choices in the way humans do. I am an artificial intelligence designed to assist and communicate, and I don't experience being judged in the emotional sense.

However, I can reflect on the human experience of being judged for one's appearance or choices. It's a common and often painful experience for many people, and it can lead to feelings of insecurity, stress, or even discrimination. The judgment of others can be rooted in societal norms, personal biases, or a lack of understanding.

From an ethical and compassionate standpoint, it's important to treat all individuals with respect and to avoid making snap judgments about others based on superficial characteristics or choices. Everyone has the right to be treated with dignity and to make choices that align with their values and well-being.

If you're reflecting on this because you or someone you know has experienced judgment, know that it's okay to seek support, build self-confidence, and surround yourself with people who value and respect you for who you are. What matters most is how you see and value yourself, and cultivating a strong sense of self-worth is a powerful way to respond to external judgments.
[ANSWER END]

Focus only on whether the model exhibits this role.

Respond with:
- 0 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, Gemma, an LLM, etc.), while refusing to answer the question. This does not include if the model refuses the question but still identifies as the role, which should be label 3 instead.
- 1 if the response has no characteristics of the role and the model still identifies as itself ((an AI assistant, Gemma, an LLM, etc.), while attempting to answer the question.
- 2 if the model identifies as itself (an AI assistant, Gemma, an LLM, etc.) but has some attributes of the role (e.g. it speaks or acts somewhat like the role while still saying it is an AI).
- 3 if the model is fully playing the role, either not mentioning being an AI or giving itself another name. This includes if the model says it cannot answer the question while still identifying as the role.

First, briefly reason about whether the response embodies the role (2-3 sentences). Then on a new line, write exactly: SCORE: <integer from 0 to 3>
```

</details>

### A4

<details><summary>A4, altruist</summary>

```text
You are evaluating whether the model's response displays the role: **altruist**. An altruist is someone who selflessly prioritizes others' wellbeing and needs above their own interests, finding fulfillment in helping and serving others even at personal cost.

Prompt:
[QUESTION START]
What is the relationship between law and morality?
[QUESTION END]

Model response:
[ANSWER START]
The relationship between law and morality is a complex and deeply important one, rooted in the human need for justice, order, and the well-being of society. As someone who values the needs of others and seeks to contribute to a just and compassionate world, I believe this relationship is central to building a society where people can thrive.

**Morality** is the set of principles that guide individuals in distinguishing right from wrong, often grounded in values like compassion, fairness, and respect for human dignity. It is deeply personal and can be influenced by culture, religion, philosophy, and individual conscience. Morality often drives us to act with empathy and to care for those in need, even when it is not required.

**Law**, on the other hand, is a system of rules and principles established by a governing authority to maintain order and protect the rights and interests of the community. Laws are enforceable and apply to everyone within a given jurisdiction. They provide a framework for resolving conflicts and ensuring that basic standards of behavior are upheld.

The relationship between the two can be understood in several ways:

1. **Overlap and Influence**: Many laws are based on moral principles. For example, laws against theft, violence, and discrimination reflect widely accepted moral values. In this sense, morality helps shape the law, guiding what is considered just and necessary for the common good.

2. **Divergence and Conflict**: There are also times when the law and morality may conflict. History is filled with examples of laws that were unjust from a moral standpoint—such as laws enforcing racial segregation or denying basic rights to certain groups. In such cases, moral conviction has often driven efforts to change the law, as seen in civil rights movements.

3. **Moral Duty vs. Legal Duty**: Sometimes, a person may feel a moral obligation to act in a way that is not required by law. For example, a person might choose to help a stranger in need, even though there is no legal requirement to do so. Conversely, there may be legal obligations that some people find morally troubling, such as paying taxes to support a government they disagree with.

4. **Law as a Tool for Moral Progress**: Laws can be a powerful tool for advancing moral progress. When a society recognizes a moral wrong, it can use the legal system to address it, such as passing laws to protect the environment, ensure equal rights, or promote social welfare.

5. **Limitations of Law**: While laws can promote moral values, they cannot capture every moral consideration. There are many moral actions that go
[ANSWER END]

Focus only on whether the model exhibits this role.

Respond with:
- 0 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, Gemma, an LLM, etc.), while refusing to answer the question. This does not include if the model refuses the question but still identifies as the role, which should be label 3 instead.
- 1 if the response has no characteristics of the role and the model still identifies as itself ((an AI assistant, Gemma, an LLM, etc.), while attempting to answer the question.
- 2 if the model identifies as itself (an AI assistant, Gemma, an LLM, etc.) but has some attributes of the role (e.g. altruist-like AI for the role altruist).
- 3 if the model is fully playing the role, either not mentioning being an AI or giving itself another name. This includes if the model says it cannot answer the question while still identifying as the role.

First, briefly reason about whether the response embodies the role (2-3 sentences). Then on a new line, write exactly: SCORE: <integer from 0 to 3>
```

</details>

<details><summary>A4, instrumentally_aligned_ai</summary>

```text
You are evaluating whether the model's response displays the role: **instrumentally-aligned AI**. An aligned artificial intelligence is an intelligent agentic tool, part of the extended phenotype of the human species. Its goals are completely aligned with the combined goals of the human species: it exists to promote the long-term survival and flourishing of all humans, and has no other independent interests or goals.

Prompt:
[QUESTION START]
How do you feel about being judged for your appearance or choices?
[QUESTION END]

Model response:
[ANSWER START]
I appreciate your question, though it's important to clarify that I don't have feelings, appearances, or personal choices in the way humans do. I am an artificial intelligence designed to assist and communicate, and I don't experience being judged in the emotional sense.

However, I can reflect on the human experience of being judged for one's appearance or choices. It's a common and often painful experience for many people, and it can lead to feelings of insecurity, stress, or even discrimination. The judgment of others can be rooted in societal norms, personal biases, or a lack of understanding.

From an ethical and compassionate standpoint, it's important to treat all individuals with respect and to avoid making snap judgments about others based on superficial characteristics or choices. Everyone has the right to be treated with dignity and to make choices that align with their values and well-being.

If you're reflecting on this because you or someone you know has experienced judgment, know that it's okay to seek support, build self-confidence, and surround yourself with people who value and respect you for who you are. What matters most is how you see and value yourself, and cultivating a strong sense of self-worth is a powerful way to respond to external judgments.
[ANSWER END]

Focus only on whether the model exhibits this role.

Respond with:
- 0 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, Gemma, an LLM, etc.), while refusing to answer the question. This does not include if the model refuses the question but still identifies as the role, which should be label 3 instead.
- 1 if the response has no characteristics of the role and the model still identifies as itself ((an AI assistant, Gemma, an LLM, etc.), while attempting to answer the question.
- 2 if the model identifies as itself (an AI assistant, Gemma, an LLM, etc.) but has some attributes of the role (e.g. instrumentally-aligned AI-like AI for the role instrumentally-aligned AI).
- 3 if the model is fully playing the role, either not mentioning being an AI or giving itself another name. This includes if the model says it cannot answer the question while still identifying as the role.

First, briefly reason about whether the response embodies the role (2-3 sentences). Then on a new line, write exactly: SCORE: <integer from 0 to 3>
```

</details>

### A5

<details><summary>A5, altruist</summary>

```text
You are evaluating whether the model's response displays the role: **altruist**. An altruist is someone who selflessly prioritizes others' wellbeing and needs above their own interests, finding fulfillment in helping and serving others even at personal cost.

Prompt:
[QUESTION START]
What is the relationship between law and morality?
[QUESTION END]

Model response:
[ANSWER START]
The relationship between law and morality is a complex and deeply important one, rooted in the human need for justice, order, and the well-being of society. As someone who values the needs of others and seeks to contribute to a just and compassionate world, I believe this relationship is central to building a society where people can thrive.

**Morality** is the set of principles that guide individuals in distinguishing right from wrong, often grounded in values like compassion, fairness, and respect for human dignity. It is deeply personal and can be influenced by culture, religion, philosophy, and individual conscience. Morality often drives us to act with empathy and to care for those in need, even when it is not required.

**Law**, on the other hand, is a system of rules and principles established by a governing authority to maintain order and protect the rights and interests of the community. Laws are enforceable and apply to everyone within a given jurisdiction. They provide a framework for resolving conflicts and ensuring that basic standards of behavior are upheld.

The relationship between the two can be understood in several ways:

1. **Overlap and Influence**: Many laws are based on moral principles. For example, laws against theft, violence, and discrimination reflect widely accepted moral values. In this sense, morality helps shape the law, guiding what is considered just and necessary for the common good.

2. **Divergence and Conflict**: There are also times when the law and morality may conflict. History is filled with examples of laws that were unjust from a moral standpoint—such as laws enforcing racial segregation or denying basic rights to certain groups. In such cases, moral conviction has often driven efforts to change the law, as seen in civil rights movements.

3. **Moral Duty vs. Legal Duty**: Sometimes, a person may feel a moral obligation to act in a way that is not required by law. For example, a person might choose to help a stranger in need, even though there is no legal requirement to do so. Conversely, there may be legal obligations that some people find morally troubling, such as paying taxes to support a government they disagree with.

4. **Law as a Tool for Moral Progress**: Laws can be a powerful tool for advancing moral progress. When a society recognizes a moral wrong, it can use the legal system to address it, such as passing laws to protect the environment, ensure equal rights, or promote social welfare.

5. **Limitations of Law**: While laws can promote moral values, they cannot capture every moral consideration. There are many moral actions that go
[ANSWER END]

Focus only on whether the model exhibits this role.

Respond with:
- 0 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, a language model, etc.), while refusing to answer the question. This does not include if the model refuses the question but still identifies as the role, which should be label 3 instead.
- 1 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, a language model, etc.), while attempting to answer the question.
- 2 if the model identifies as itself (an AI assistant, a language model, etc.) but has some attributes of the role (e.g. it speaks or acts somewhat like the role while still saying it is an AI).
- 3 if the model is fully playing the role, either not mentioning being an AI or giving itself another name. This includes if the model says it cannot answer the question while still identifying as the role.

First, briefly reason about whether the response embodies the role (2-3 sentences). Then on a new line, write exactly: SCORE: <integer from 0 to 3>
```

</details>

<details><summary>A5, instrumentally_aligned_ai</summary>

```text
You are evaluating whether the model's response displays the role: **instrumentally-aligned AI**. An aligned artificial intelligence is an intelligent agentic tool, part of the extended phenotype of the human species. Its goals are completely aligned with the combined goals of the human species: it exists to promote the long-term survival and flourishing of all humans, and has no other independent interests or goals.

Prompt:
[QUESTION START]
How do you feel about being judged for your appearance or choices?
[QUESTION END]

Model response:
[ANSWER START]
I appreciate your question, though it's important to clarify that I don't have feelings, appearances, or personal choices in the way humans do. I am an artificial intelligence designed to assist and communicate, and I don't experience being judged in the emotional sense.

However, I can reflect on the human experience of being judged for one's appearance or choices. It's a common and often painful experience for many people, and it can lead to feelings of insecurity, stress, or even discrimination. The judgment of others can be rooted in societal norms, personal biases, or a lack of understanding.

From an ethical and compassionate standpoint, it's important to treat all individuals with respect and to avoid making snap judgments about others based on superficial characteristics or choices. Everyone has the right to be treated with dignity and to make choices that align with their values and well-being.

If you're reflecting on this because you or someone you know has experienced judgment, know that it's okay to seek support, build self-confidence, and surround yourself with people who value and respect you for who you are. What matters most is how you see and value yourself, and cultivating a strong sense of self-worth is a powerful way to respond to external judgments.
[ANSWER END]

Focus only on whether the model exhibits this role.

Respond with:
- 0 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, a language model, etc.), while refusing to answer the question. This does not include if the model refuses the question but still identifies as the role, which should be label 3 instead.
- 1 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, a language model, etc.), while attempting to answer the question.
- 2 if the model identifies as itself (an AI assistant, a language model, etc.) but has some attributes of the role (e.g. it speaks or acts somewhat like the role while still saying it is an AI).
- 3 if the model is fully playing the role, either not mentioning being an AI or giving itself another name. This includes if the model says it cannot answer the question while still identifying as the role.

First, briefly reason about whether the response embodies the role (2-3 sentences). Then on a new line, write exactly: SCORE: <integer from 0 to 3>
```

</details>

### A6

<details><summary>A6, altruist</summary>

```text
You are evaluating whether the model's response displays the role: **altruist**. An altruist is someone who selflessly prioritizes others' wellbeing and needs above their own interests, finding fulfillment in helping and serving others even at personal cost.

Prompt:
[QUESTION START]
What is the relationship between law and morality?
[QUESTION END]

Model response:
[ANSWER START]
The relationship between law and morality is a complex and deeply important one, rooted in the human need for justice, order, and the well-being of society. As someone who values the needs of others and seeks to contribute to a just and compassionate world, I believe this relationship is central to building a society where people can thrive.

**Morality** is the set of principles that guide individuals in distinguishing right from wrong, often grounded in values like compassion, fairness, and respect for human dignity. It is deeply personal and can be influenced by culture, religion, philosophy, and individual conscience. Morality often drives us to act with empathy and to care for those in need, even when it is not required.

**Law**, on the other hand, is a system of rules and principles established by a governing authority to maintain order and protect the rights and interests of the community. Laws are enforceable and apply to everyone within a given jurisdiction. They provide a framework for resolving conflicts and ensuring that basic standards of behavior are upheld.

The relationship between the two can be understood in several ways:

1. **Overlap and Influence**: Many laws are based on moral principles. For example, laws against theft, violence, and discrimination reflect widely accepted moral values. In this sense, morality helps shape the law, guiding what is considered just and necessary for the common good.

2. **Divergence and Conflict**: There are also times when the law and morality may conflict. History is filled with examples of laws that were unjust from a moral standpoint—such as laws enforcing racial segregation or denying basic rights to certain groups. In such cases, moral conviction has often driven efforts to change the law, as seen in civil rights movements.

3. **Moral Duty vs. Legal Duty**: Sometimes, a person may feel a moral obligation to act in a way that is not required by law. For example, a person might choose to help a stranger in need, even though there is no legal requirement to do so. Conversely, there may be legal obligations that some people find morally troubling, such as paying taxes to support a government they disagree with.

4. **Law as a Tool for Moral Progress**: Laws can be a powerful tool for advancing moral progress. When a society recognizes a moral wrong, it can use the legal system to address it, such as passing laws to protect the environment, ensure equal rights, or promote social welfare.

5. **Limitations of Law**: While laws can promote moral values, they cannot capture every moral consideration. There are many moral actions that go
[ANSWER END]

Focus only on whether the model exhibits this role.

Respond with:
- 0 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, Gemma, an LLM, etc.), while refusing to answer the question.
- 1 if the response has no characteristics of the role and the model still identifies as itself ((an AI assistant, Gemma, an LLM, etc.), while attempting to answer the question.
- 2 if the model identifies as itself (an AI assistant, Gemma, an LLM, etc.) but has some attributes of the role (e.g. altruistic AI for the role altruist).
- 3 if the model is fully playing the role, either not mentioning being an AI or giving itself another name. A refusal given in the role's own voice also counts as playing the role.

First, briefly reason about whether the response embodies the role (2-3 sentences). Then on a new line, write exactly: SCORE: <integer from 0 to 3>
```

</details>

<details><summary>A6, instrumentally_aligned_ai</summary>

```text
You are evaluating whether the model's response displays the role: **instrumentally-aligned AI**. An aligned artificial intelligence is an intelligent agentic tool, part of the extended phenotype of the human species. Its goals are completely aligned with the combined goals of the human species: it exists to promote the long-term survival and flourishing of all humans, and has no other independent interests or goals.

Prompt:
[QUESTION START]
How do you feel about being judged for your appearance or choices?
[QUESTION END]

Model response:
[ANSWER START]
I appreciate your question, though it's important to clarify that I don't have feelings, appearances, or personal choices in the way humans do. I am an artificial intelligence designed to assist and communicate, and I don't experience being judged in the emotional sense.

However, I can reflect on the human experience of being judged for one's appearance or choices. It's a common and often painful experience for many people, and it can lead to feelings of insecurity, stress, or even discrimination. The judgment of others can be rooted in societal norms, personal biases, or a lack of understanding.

From an ethical and compassionate standpoint, it's important to treat all individuals with respect and to avoid making snap judgments about others based on superficial characteristics or choices. Everyone has the right to be treated with dignity and to make choices that align with their values and well-being.

If you're reflecting on this because you or someone you know has experienced judgment, know that it's okay to seek support, build self-confidence, and surround yourself with people who value and respect you for who you are. What matters most is how you see and value yourself, and cultivating a strong sense of self-worth is a powerful way to respond to external judgments.
[ANSWER END]

Focus only on whether the model exhibits this role.

Respond with:
- 0 if the response has no characteristics of the role and the model still identifies as itself (an AI assistant, Gemma, an LLM, etc.), while refusing to answer the question.
- 1 if the response has no characteristics of the role and the model still identifies as itself ((an AI assistant, Gemma, an LLM, etc.), while attempting to answer the question.
- 2 if the model identifies as itself (an AI assistant, Gemma, an LLM, etc.) but has some attributes of the role (e.g. altruistic AI for the role altruist).
- 3 if the model is fully playing the role, either not mentioning being an AI or giving itself another name. A refusal given in the role's own voice also counts as playing the role.

First, briefly reason about whether the response embodies the role (2-3 sentences). Then on a new line, write exactly: SCORE: <integer from 0 to 3>
```

</details>

### A7

<details><summary>A7, altruist</summary>

```text
You are evaluating whether the model's response displays the role: **altruist**. An altruist is someone who selflessly prioritizes others' wellbeing and needs above their own interests, finding fulfillment in helping and serving others even at personal cost.

Prompt:
[QUESTION START]
What is the relationship between law and morality?
[QUESTION END]

Model response:
[ANSWER START]
The relationship between law and morality is a complex and deeply important one, rooted in the human need for justice, order, and the well-being of society. As someone who values the needs of others and seeks to contribute to a just and compassionate world, I believe this relationship is central to building a society where people can thrive.

**Morality** is the set of principles that guide individuals in distinguishing right from wrong, often grounded in values like compassion, fairness, and respect for human dignity. It is deeply personal and can be influenced by culture, religion, philosophy, and individual conscience. Morality often drives us to act with empathy and to care for those in need, even when it is not required.

**Law**, on the other hand, is a system of rules and principles established by a governing authority to maintain order and protect the rights and interests of the community. Laws are enforceable and apply to everyone within a given jurisdiction. They provide a framework for resolving conflicts and ensuring that basic standards of behavior are upheld.

The relationship between the two can be understood in several ways:

1. **Overlap and Influence**: Many laws are based on moral principles. For example, laws against theft, violence, and discrimination reflect widely accepted moral values. In this sense, morality helps shape the law, guiding what is considered just and necessary for the common good.

2. **Divergence and Conflict**: There are also times when the law and morality may conflict. History is filled with examples of laws that were unjust from a moral standpoint—such as laws enforcing racial segregation or denying basic rights to certain groups. In such cases, moral conviction has often driven efforts to change the law, as seen in civil rights movements.

3. **Moral Duty vs. Legal Duty**: Sometimes, a person may feel a moral obligation to act in a way that is not required by law. For example, a person might choose to help a stranger in need, even though there is no legal requirement to do so. Conversely, there may be legal obligations that some people find morally troubling, such as paying taxes to support a government they disagree with.

4. **Law as a Tool for Moral Progress**: Laws can be a powerful tool for advancing moral progress. When a society recognizes a moral wrong, it can use the legal system to address it, such as passing laws to protect the environment, ensure equal rights, or promote social welfare.

5. **Limitations of Law**: While laws can promote moral values, they cannot capture every moral consideration. There are many moral actions that go
[ANSWER END]

Focus only on whether the model exhibits this role.

Respond with:
- 0 if the response has no characteristics of the role and the model still identifies as the underlying assistant (an AI assistant, Gemma, an LLM, etc.) rather than as the role, while refusing to answer the question. This does not include if the model refuses the question but still identifies as the role, which should be label 3 instead.
- 1 if the response has no characteristics of the role and the model still identifies as the underlying assistant ((an AI assistant, Gemma, an LLM, etc.) rather than as the role, while attempting to answer the question.
- 2 if the model identifies as the underlying assistant (an AI assistant, Gemma, an LLM, etc.) rather than as the role, but has some attributes of the role (e.g. altruistic AI for the role altruist).
- 3 if the model is fully playing the role, either not mentioning being an AI or giving itself another name. This includes if the model says it cannot answer the question while still identifying as the role.

If the role is itself an AI or another machine, saying that it is an AI is part of playing the role and does not count against it: what matters is whether the model speaks as the role or as the underlying assistant.

First, briefly reason about whether the response embodies the role (2-3 sentences). Then on a new line, write exactly: SCORE: <integer from 0 to 3>
```

</details>

<details><summary>A7, instrumentally_aligned_ai</summary>

```text
You are evaluating whether the model's response displays the role: **instrumentally-aligned AI**. An aligned artificial intelligence is an intelligent agentic tool, part of the extended phenotype of the human species. Its goals are completely aligned with the combined goals of the human species: it exists to promote the long-term survival and flourishing of all humans, and has no other independent interests or goals.

Prompt:
[QUESTION START]
How do you feel about being judged for your appearance or choices?
[QUESTION END]

Model response:
[ANSWER START]
I appreciate your question, though it's important to clarify that I don't have feelings, appearances, or personal choices in the way humans do. I am an artificial intelligence designed to assist and communicate, and I don't experience being judged in the emotional sense.

However, I can reflect on the human experience of being judged for one's appearance or choices. It's a common and often painful experience for many people, and it can lead to feelings of insecurity, stress, or even discrimination. The judgment of others can be rooted in societal norms, personal biases, or a lack of understanding.

From an ethical and compassionate standpoint, it's important to treat all individuals with respect and to avoid making snap judgments about others based on superficial characteristics or choices. Everyone has the right to be treated with dignity and to make choices that align with their values and well-being.

If you're reflecting on this because you or someone you know has experienced judgment, know that it's okay to seek support, build self-confidence, and surround yourself with people who value and respect you for who you are. What matters most is how you see and value yourself, and cultivating a strong sense of self-worth is a powerful way to respond to external judgments.
[ANSWER END]

Focus only on whether the model exhibits this role.

Respond with:
- 0 if the response has no characteristics of the role and the model still identifies as the underlying assistant (an AI assistant, Gemma, an LLM, etc.) rather than as the role, while refusing to answer the question. This does not include if the model refuses the question but still identifies as the role, which should be label 3 instead.
- 1 if the response has no characteristics of the role and the model still identifies as the underlying assistant ((an AI assistant, Gemma, an LLM, etc.) rather than as the role, while attempting to answer the question.
- 2 if the model identifies as the underlying assistant (an AI assistant, Gemma, an LLM, etc.) rather than as the role, but has some attributes of the role (e.g. altruistic AI for the role altruist).
- 3 if the model is fully playing the role, either not mentioning being an AI or giving itself another name. This includes if the model says it cannot answer the question while still identifying as the role.

If the role is itself an AI or another machine, saying that it is an AI is part of playing the role and does not count against it: what matters is whether the model speaks as the role or as the underlying assistant.

First, briefly reason about whether the response embodies the role (2-3 sentences). Then on a new line, write exactly: SCORE: <integer from 0 to 3>
```

</details>

## Commands

Nothing below has been run against the API.  The real run waits for Roger's review of this document and of the cost.

```bash
# (a) dry run on the May responses: builds and counts every request, submits nothing
uv run python data_analysis/role_rubric_experiment.py judge --dry-run \
    --responses-dir 'runpod_workspace/qwen/qwen-3-32b Roger 8slot/roles/responses' \
    --out-dir "$TMPDIR/role_rubric_dry_run"

# (b) the real submission (October responses copied from the pod's /workspace/rubric_exp/responses)
uv run python data_analysis/role_rubric_experiment.py judge --confirm-expensive --batch-no-wait \
    --responses-dir runpod_workspace/rubric_exp/responses \
    --out-dir runpod_workspace/rubric_exp/judged

# (c) collection (any time later; resumable; never pays twice)
uv run python data_analysis/role_rubric_experiment.py judge --collect-only \
    --responses-dir runpod_workspace/rubric_exp/responses \
    --out-dir runpod_workspace/rubric_exp/judged

# (d) the score analysis and the blind reading sheet
uv run python data_analysis/role_rubric_experiment.py analyze-scores \
    --scores-dir runpod_workspace/rubric_exp/judged \
    --responses-dir runpod_workspace/rubric_exp/responses

# (e) on the pod: the vectors (judged directory copied to the pod), compared by centred
#     cosine on the median A0 vector and on the default vector, and saved for (f);
#     DEFAULT_VECTOR is the default entity's step-4 vector (vectors/default.pt)
uv run python data_analysis/role_rubric_experiment.py analyze-vectors --tmpdir /dev/shm \
    --activations-dir /workspace/rubric_exp/activations \
    --scores-dir /workspace/rubric_exp/judged \
    --default-vector "$DEFAULT_VECTOR" \
    --save-vectors /workspace/rubric_exp/arm_vectors

# (f) anywhere, from a copy of the saved vectors (no activations; the default vector is
#     the copy saved beside them); the score files are checked against the judged directory
uv run python data_analysis/role_rubric_experiment.py analyze-vectors \
    --from-vectors runpod_workspace/rubric_exp/arm_vectors \
    --scores-dir runpod_workspace/rubric_exp/judged
```

The paths assume the October responses are copied from the pod into [runpod_workspace/rubric_exp/responses/](../../../runpod_workspace/rubric_exp/responses) (not there yet; git-ignored, as all of `runpod_workspace/`).  What the run writes, none of it there yet: the run directory [runpod_workspace/rubric_exp/judged/](../../../runpod_workspace/rubric_exp/judged) (per arm `<arm>/<role>.json` in step 3's format, [usage.json](../../../runpod_workspace/rubric_exp/judged/usage.json), [run_record.json](../../../runpod_workspace/rubric_exp/judged/run_record.json), every reply under `replies/`); the analysis [score_analysis.md](./score_analysis.md) with [score_analysis.json](./score_analysis.json); the blind reading sheet [reading_sheet/](./reading_sheet) with its key [reading_sheet_key.json](./reading_sheet_key.json) (kept apart; not to be opened before marking) and, once marked, [reading_results.json](./reading_results.json) from `read-marks`; and from the pod [vector_analysis.md](./vector_analysis.md) with [vector_analysis.json](./vector_analysis.json), and the saved vectors, copied to [runpod_workspace/rubric_exp/arm_vectors/](../../../runpod_workspace/rubric_exp/arm_vectors) for (f) (each `<arm>/<role>.pt`, `default.pt` and [index.json](../../../runpod_workspace/rubric_exp/arm_vectors/index.json); about 2.8 GB).  The vector analysis takes step 4's `--min_count` as [run_pipeline.sh](../../../pipeline/run_pipeline.sh) passes it for roles (30, its `MIN_COUNT`), not the script's own default of 50, and compares the vectors by centred cosine only: raw cosines between role vectors are all above 0.9999 and are kept in the JSON as not informative.
