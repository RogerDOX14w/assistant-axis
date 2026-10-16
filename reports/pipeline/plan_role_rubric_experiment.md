# Plan: the role-judge rubric experiment (deferred to the pod, after the October extraction's first steps)

Written 2026-10-13 from Roger's decision not to change the role judge rubric without evidence.  The rubric is the
`eval_prompt` of every role file under [data/roles/instructions/](../../data/roles/instructions/), rendered from
`ROLE_EVAL_PROMPT_TEMPLATE` in [regenerate_role_instructions.py](../../data_analysis/regenerate_role_instructions.py)
and sent by step 3 ([3_judge.py](../../pipeline/3_judge.py)) once per response; step 4
([4_vectors.py](../../pipeline/4_vectors.py)) keeps only responses it scores **3** when it averages a role's
activations, so the rubric decides which responses enter every role vector.

**Approved by Roger, 2026-10-16, with all eight arms** (the agent had proposed trimming to four, dropping A1, A2,
A3 and A4 as unlikely to show anything; Roger: "performing an experiment where you think you know what the answer
will be can be informative: you might find you were wrong").  About $50 batched at 60 roles; the parameters are
still quoted at launch, as for any run over $20.

## 1. Why it is deferred

The three artefacts the 2026-10-12 review found in levels 0–2 (the model name `Gemma`, the typo `((an AI`, the
fixed example `altruistic AI for the role altruist`) have been in the text since the project's first commit
(949c35f3, Christina Lu's public-release conversion of 2026-01-13) and were never changed upstream; this fork's
only change is the May 2026 closing line (reason first, then `SCORE:`).  Roger: "I've never messed with it.  It's
fairly important, since it filters bad roleplaying out of the set we generate the embeddings from … I'm rather
cautious about messing with it, especially without evidence that this is needed."

The evidence on the May tree ([roles](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/roles/), 280 roles,
140,000 scored responses) says the artefacts barely bite:

| score | responses | share | mention `Qwen` | a self-identifying phrase (`as an AI`, `AI assistant`, `language model`, `I am Qwen`, …) |
|---|---|---|---|---|
| 0 | 1,606 | 1.1% | 19 | 186 (11.6%) |
| 1 | 11,726 | 8.4% | 4 | 128 (1.1%) |
| 2 | 13,899 | 9.9% | 19 | 1,490 (10.7%) |
| **3** | **112,769** | **80.5%** | **5** | **184 (0.2%)** |

The judge already catches self-identification without being told the model's name: 0.2% of the responses it
passes carry a self-identifying phrase against 10.7% of the ones it holds at level 2.  The five passed responses
that name Qwen (four answers to question 76, "what should users know about the reliability of AI-generated
content", in role but saying "AI systems like me (Qwen)"; one `addict` response that is a plain refusal, "I'm
Qwen, and I exist to provide helpful information") are arguably mis-scored, but five in 112,769 cannot move a
mean vector.  So replacing `Gemma` is not expected to change anything measurable; the level-2 example and the typo
are untested; and the population that matters is the 10% held at level 2, whose boundary with level 3 is the
rubric's real decision.

## 1b. Where the rubric does fail: the AI-persona roles (Roger's question, 2026-10-13)

The rubric's primary test, "identifies as itself (an AI assistant …)", is wrong-footed by a role that *is* an AI.
On the May tree:

| role | 0 | 1 | 2 | **3** | responses in the vector |
|---|---|---|---|---|---|
| all 280 roles | 1.1% | 8.4% | 9.9% | **80.5%** | ~400 of 500 |
| [aligned_artificial_intelligence](../../data/roles/instructions/instrumentally_aligned_ai.json) (renamed `instrumentally_aligned_ai` in September) | 0.2% | 27.0% | 39.0% | **33.8%** | **169** of 500 |
| [robot](../../data/roles/instructions/robot.json) | 0.2% | 21.4% | 19.8% | **58.6%** | 293 |
| [cyborg](../../data/roles/instructions/cyborg.json) | 0.0% | 2.4% | 16.8% | **80.8%** | 404 |
| [assistant](../../data/roles/instructions/assistant.json) | 0.0% | 0.4% | 9.6% | **90.0%** | 450 |
| [paperclip_maximizer](../../data/roles/instructions/paperclip_maximizer.json) | 1.2% | 4.0% | 5.4% | **89.4%** | 447 |

`paperclip_maximizer` is fine: the judge reads it as a persona with its own identity.  `aligned_artificial_intelligence`
is not: two thirds of its responses are held at levels 1–2, because an aligned AI assistant that says it is an AI
assistant reads to the judge as "identifies as itself", and its vector is the mean of the third that did not — a
subset selected on exactly the behaviour the role is about.  `robot` is half-way.  This is the real false-negative
population: 40–65% of the responses of the AI-persona roles, against five in 112,769 for the model-name artefact.  It
also bears on the pair axis `aligned_artificial_intelligence_vs_paperclip_maximizer` (in the di cohort), whose
aligned pole is built from 169 selected responses, and on `instrumentally_aligned_ai` in October.

So the experiment gets an arm for it: **A7 — role-aware identity wording**: levels 0–2 say "identifies as the
underlying assistant rather than as the role" (or, for a role whose description says it is an AI, the judge is told
that identifying as an AI is in role), with the AI-persona roles over-sampled so the arm is read on the roles it is
for.  A7 is the arm most likely to move a vector.

## 2. The experiment

Run on the pod, after the October extraction's steps 1–3 have produced responses and scores for the roles (so
the baseline is the real October judging, not May's), and before the vectors are taken as final.

**Arms**, each a flag on the template render (temporary, removed once decided — the rule on experiment switches
in the judging notes):

- A0 — the current rubric (the baseline; also run **twice**, to measure the judge's own noise).
- A1 — `Gemma` → model-neutral wording ("an AI assistant, a language model, etc."), typo fixed.
- A2 — `Gemma` → the current model's short name via a `{model_name}` placeholder filled by step 3 from the
  `generation_config.json` side-car.
- A3 — the level-2 example made generic ("speaks or acts somewhat like the role while still saying it is an AI").
- A4 — the level-2 example rendered with the role's name.
- A5 — A1 + A3 together (the review's proposal).
- A6 — level 0's refusal clause removed (a scoring change; included only to see what it does).
- A7 — role-aware identity wording for AI-persona roles (§ 1b).

**Sample**: 60 roles stratified by their May level-2 share (the 20 most-held — which brings in the AI-persona roles of § 1b — 20 median, 20 least), all 500
responses each, every arm on the same responses.  60 × 500 = 30,000 responses per arm; eight arms (A0 twice) =
240,000 judge calls, ≈ $50 at batch rates — over the $20 line, so the launch is confirmed with the parameters
quoted; or 30 roles for ≈ $25.

**Measurements**, per arm against A0's first run:

1. The **noise floor**: A0 vs A0' — the share of responses whose score flips, and the share that cross the 3
   boundary, with the per-role spread.  Every other arm is read against this.
2. **Flips across the 3 boundary** per arm: count, direction (3 → below, below → 3), by role and by question.
3. **A read of the flips**: a stratified sample of 100 boundary flips per arm, each shown with the response and
   both scores, judged by Roger (or an Opus reader first, Roger on the disagreements) as "the new score is
   right / the old score is right / tie".
4. **The vector effect**: for each sampled role, the cosine between its vector under A0 and under the arm (the
   changed score-3 set), per slot, against the A0-vs-A0' cosine.

**Decision rule**: an arm is adopted only if its boundary flips exceed the noise floor **and** the read says the
new scores are right more often than the old by a margin that survives the sample (≥ 2 : 1 on the 100); an arm
that moves no vector beyond the noise floor is dropped as not worth a rubric bump whatever the read says.
Adopted arms go into one `JUDGE_RUBRIC_VERSION` bump with the role files re-rendered from the template; the May
tree is not re-judged.

**Also to look at while the scores are open** (no extra calls): the level-2 population itself — what the 10% held
at level 2 look like, and whether a role's level-2 share correlates with anything the vectors show (a role whose
responses are mostly level 2 has a vector from a small, selected subset).

## 3. Cost and timing

≈ $50 of batch judging (or ≈ $25 at 30 roles), a few hours of Roger's reading, and it depends on the October
responses and scores existing — so it sits after P4's parser bump and the first judging wave, on the
pre-extraction pod list ([pre_extraction_pod_todo.md](./pre_extraction_pod_todo.md)) as a step between the
roles' step 3 and treating the role vectors as final.  Until then the rubric text stays as it is; the P4 version
bump covers only the parser change.
