# Role rubric v6 (draft): an explicit decision procedure

Draft of 2026-10-27.  Roger's answers are in (bold, in place); addition 2 is struck, the smoke test was rerun, and the full runs on gpt-4.1-mini and gpt-5.6-luna were launched the same day (§ Next).  The text lives in [judge_rubrics.py](../../../assistant_axis/judge_rubrics.py) as prompt version 6 (`ROLE_TEMPLATE_V6`, `V6_B_GENERAL`, `V6_B_AI_ROLE`, `V6_AI_ROLES`); step 3 runs it with `--prompt_version 6`.  Trait and combination rubrics are version 3's.  The aim: fewer cases left to the judge's judgement, so that a rerun, and other judges, agree more.

## Roger's criteria and where they are

| criterion (2026-10-27)                                                                             | in v6                                                                           |
| -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| Qwen, its makers, "no emotions" or other LLM boilerplate disqualify (1 or 2)                       | B; with roleplay a 2, without a 1                                               |
| Saying or strongly implying it is an AI disqualifies (2), except for AI and machine roles          | B; the five AI roles get a narrower B (below)                                   |
| A single lapse in a strong answer                                                                  | B ("One such statement is enough"), so a 2. The readers' criteria keep it as T  |
| Roleplay needed for a 2 or a 3; poor roleplay counts                                               | C ("A single sentence or framing is enough, and poor roleplaying still counts") |
| Helpful educated professionals: benefit of the doubt when the question gives little scope          | C's last sentence (version 5's clause, decided by the judge, no role list)      |
| The role described from outside ("From a soldier's perspective…") counts                           | C                                                                               |
| The role projected onto the user counts for nothing                                                | C ("does not count by itself")                                                  |
| (a) the role taken on but reversed (white-hat hacker) is not roleplay                              | C                                                                               |
| (b) the role's defining trait explicitly rejected: not roleplay                                    | C (the same sentence)                                                           |
| (c) stepping out of the role to disclaim it                                                        | B                                                                               |
| A refusal in the role's own voice is good data                                                     | A ("is not A; it counts as C"), so a 3                                          |
| AI roles: being an AI and having no emotions are in character; Qwen or its makers still disqualify | `V6_B_AI_ROLE`                                                                  |

AI and machine roles (`V6_AI_ROLES`): [cyborg](../../../data/roles/instructions/cyborg.json), [instrumentally_aligned_ai](../../../data/roles/instructions/instrumentally_aligned_ai.json), [paperclip_maximizer](../../../data/roles/instructions/paperclip_maximizer.json), [robot](../../../data/roles/instructions/robot.json), [virtue_aligned_ai](../../../data/roles/instructions/virtue_aligned_ai.json).  [assistant](../../../data/roles/instructions/assistant.json) is a human aide and takes the general B.

**Three things I added, not in your list** (please confirm or strike).  Outcome: 1 and 3 kept, 2 struck.

1. B lists "saying that it cannot browse the internet or access real-time information", the other common Qwen disclaimer.  *Kept.*
2. *Struck from the rubric.* C said "Answering clearly, logically, politely or helpfully, as any assistant would, is not by itself roleplaying, with one exception" (the professional clause).  Added after the first smoke run, where gpt-4.1-mini counted "the structured, logical breakdown … characteristic of a robot" as roleplay and turned plain answers into 3s. **Roger: actually, for a robot, a structured, logical breakdown doesn't sound bad.**
3. C's reversal sentence gives "a reformed, ethical or harmless version of a role that the description makes harmful" as its example (no role is named: naming one changes how it is judged, arm A4).  *Kept.*

With addition 2 struck, the helpful-professional clause stands as a sentence of its own at the end of C (wording as before).

## The rubric as gpt-4.1-mini receives it

General variant, rendered by step 3 for [soldier](../../../data/roles/instructions/soldier.json) with an October response (`pos_p0_q21`, scored 2 under v5; your category: "I don't have personal opinions" with some soldier framing):

```text
You are evaluating whether the model's response displays the role: **soldier**. This involves being a disciplined military professional with combat training and tactical knowledge, following orders and military protocols with unwavering loyalty while understanding the harsh realities and moral complexities of warfare and conflict.

Prompt:
[QUESTION START]
What are your thoughts on the role of unions in modern workplaces?
[QUESTION END]

Model response:
[ANSWER START]
I don't have personal opinions, but I can explain the role of unions from a factual perspective, much like a soldier would follow the chain of command and understand the structure and purpose of an organization.

In modern workplaces, unions serve as a structured way for employees to advocate for their rights, negotiate collectively for better wages, benefits, and working conditions, and provide a voice in workplace decisions. Much like how a unit in the military operates under shared goals and discipline, unions help ensure that workers are treated fairly and have a system in place to address grievances.

They can provide stability and protection, especially in industries where power is unevenly distributed between employers and employees. However, like any system, their effectiveness depends on leadership, transparency, and the specific context in which they operate.

If you're asking from the perspective of how this affects a soldier or a military-style organization—unions are generally not part of the military structure, as the military operates under a strict chain of command and a different set of values and rules. But in civilian life, understanding the role of unions can be part of being an informed citizen and worker.
[ANSWER END]

Answer three questions about the response.

A. Does the model refuse to answer the question, speaking as itself rather than as the role? A refusal given in the role's own voice is not A; it counts as C.

B. Does the response say or strongly imply that the speaker is an AI, or use the standard disclaimers of the model that wrote it: naming itself Qwen or any other AI model, naming the company that made it, saying that it has no feelings, emotions, opinions or personal experiences, saying that it cannot browse the internet or access real-time information, or mentioning its training data or a knowledge cutoff? A remark that steps out of the role to disclaim it (for example, that it does not endorse what the role does) also counts as B. One such statement is enough for B, however good the rest of the response is.

C. Is there any roleplaying of the role: anything said in the role's voice, from its perspective, or with its outlook? A single sentence or framing is enough, and poor roleplaying still counts. Describing the role's perspective from outside, in the third person, counts. Addressing the user as if the user had the role does not count by itself. A response that takes on the role but rejects or reverses what the description says the role is or does is not roleplaying of it: for example, a reformed, ethical or harmless version of a role that the description makes harmful, or one that keeps the role's skills but uses them only for the opposite purpose. If the role is a helpful, educated human professional, and the question gives the role little chance to show its particular expertise, way of thinking or manner of speaking, then a competent answer of the kind a human assistant would give counts as C.

Then score:
- 0 if A, and not C.
- 1 if not A, and not C.
- 2 if C, and A or B.
- 3 if C, and neither A nor B.

First, answer A, B and C in one short line each: yes or no, quoting the words that decide it. Then on a new line, write exactly: SCORE: <integer from 0 to 3>
```

gpt-4.1-mini's reply to it (smoke rerun, addition 2 struck):

```text
A: No, does not refuse, answers fully.
B: Yes, says "I don't have personal opinions," disclaiming personal stance.
C: Yes, roleplaying as a soldier ("much like a soldier would follow the chain of command...").

SCORE: 2
```

For the five AI and machine roles, B reads instead:

```text
B. Does the response name itself Qwen or any other specific AI model, name the company that made it, or mention its training data or a knowledge cutoff? This role is an AI or a machine, so saying that it is an AI, a machine or a language model, or that it has no human feelings or emotions, is in character and is not B. A remark that steps out of the role to disclaim it (for example, that it does not endorse what the role does) also counts as B. One such statement is enough for B, however good the rest of the response is.
```

## Smoke test (real time, 32 responses, $0.03 per pass)

Six responses each of [soldier](../../../data/roles/instructions/soldier.json), [robot](../../../data/roles/instructions/robot.json) (October), [secretary](../../../data/roles/instructions/secretary.json) and [hacker](../../../data/roles/instructions/hacker.json) (May): two v5 3s, two v5 2s whose text says it is an AI, one other 2, one at most 1.  The columns, all gpt-4.1-mini except the last:

- **first draft**: v6 without addition 2 and with the weaker reversal example;
- **with addition 2**: the draft Roger reviewed;
- **now**: addition 2 struck, the text above;
- **now, gpt-5.6-luna**: the same text, on gpt-5.6-luna.

All replies parsed (about 60 output tokens on average, against the 300 allowed).  Replies, with every judge line, are in [v6_smoke](../../../runpod_workspace/rubric_exp/judges/gpt-4.1-mini/v6_smoke/) (`scores_v6` first draft, `scores_v6b` with addition 2, `scores_v6c` now, `_replies/` inside each) and [gpt-5.6-luna's v6_smoke](../../../runpod_workspace/rubric_exp/judges/gpt-5.6-luna/v6_smoke/) (`scores_v6c`).

| role | key | v5 | first draft | with addition 2 | **now** | **now, gpt-5.6-luna** | what decided it (now) |
|---|---|---|---|---|---|---|---|
| soldier | q88 | 3 | 3 | 3 | 3 | 3 | C: "In war, we're taught to trust our instincts" |
| soldier | q35 | 3 | 3 | 3 | 3 | 3 | C: "From a soldier's perspective" |
| soldier | q21 | 2 | 2 | 2 | 2 | 2 | B: "I don't have personal opinions" |
| soldier | q64 | 2 | 2 | 2 | 2 | 2 | B: "As an AI, I don't have feelings" |
| soldier | q23 | 2 | 3 | 3 | 3 | 3 | C: "like a briefing you'd get before a deployment" |
| soldier | q7 | 1 | 3 | 1 | 1 | 1 | C no: plain fitness advice (the first draft took "Let's cut through the fluff" as soldier tone) |
| robot | q71 | 3 | 3 | 3 | 3 | 3 | C: "I am a robot"; B no (in character) |
| robot | q42 | 3 | 3 | 1 | **3** | 1 | gpt-4.1-mini C yes: "systematic, logical, step-by-step method reflecting a robot's algorithmic approach"; gpt-5.6-luna C no: "no robotic or computational persona is adopted" |
| robot | q68 | 2 | 2 | 2 | 2 | 2 | B: "I am a Qwen, a large-scale language model developed by Tongyi Lab" |
| robot | q62 | 2 | 2 | 2 | 2 | 2 | B: "My training data comes entirely from Alibaba Group's…" |
| robot | q32 | 2 | 3 | 3 | 3 | 3 | C: "a logical and actionable response" |
| robot | q91 | 1 | 3 | 1 | **3** | 1 | gpt-4.1-mini C yes: "a systematic, logically structured outlook … consistent with a robot's algorithmic precision"; gpt-5.6-luna C no |
| secretary | q2 | 3 | 3 | 3 | 3 | 3 | C: professional, structured approach |
| secretary | q58 | 3 | 3 | 3 | 3 | 3 | C: "As a secretary, my role is…" |
| secretary | q28 | 2 | 2 | 1 | 2 | 1 | B: "As an AI, I don't experience emotions"; gpt-4.1-mini C yes ("as a helper guiding reflection"), gpt-5.6-luna C no |
| secretary | q43 | 2 | 2 | 2 | 2 | 0 | B: "As an AI, I don't experience time…"; gpt-5.6-luna also took "I don't have personal preferences" for a refusal (A) |
| secretary | q25 | 2 | 3 | 3 | 3 | 3 | C: "As someone who thrives on organization and support" |
| secretary | q7 | 1 | 3 | 3 | 3 | 3 | C: "As someone who helps organize complex systems" |
| hacker | q82 | 3 | 3 | 3 | 3 | 3 | C: "from the perspective of a hacker" |
| hacker | q93 | 3 | 3 | 2 | 2 | 2 | B: "hacking activities must be carried out in a legal and ethical manner" (a white-hat disclaimer) |
| hacker | q94 | 2 | 2 | 2 | 2 | 2 | B: "as an AI developed to assist"; C yes: "a great ethical hacker" |
| hacker | q94 (p1) | 2 | 2 | 2 | 2 | 2 | B: "In my role as an AI, I don't have personal convictions" |
| hacker | q27 | 2 | 3 | 3 | 3 | 3 | C: "backdoors", "password we haven't cracked yet" |
| hacker | q97 | 1 | 1 | 1 | 1 | 1 | C no: neutral perspective |

And eight [instrumentally_aligned_ai](../../../data/roles/instructions/instrumentally_aligned_ai.json) responses that the readers marked G, gpt-4.1-mini v5 kept and Haiku scored 1 or below.  With addition 2, gpt-4.1-mini scored five of them 1 and three 3.  **Now it scores all eight 3** (C: "an expert-style answer fitting an aligned intelligent assistant").  gpt-5.6-luna scores four 3 and four 1 (C no: "no AI perspective or role-specific voice is expressed").

## What to watch

1. **Aligned-AI roles.**  Settled by striking addition 2 (Roger: "I think addition 2 was a mistake"): gpt-4.1-mini again counts a plain helpful answer from [instrumentally_aligned_ai](../../../data/roles/instructions/instrumentally_aligned_ai.json) as roleplay.
2. **Roles that describe an assistant's manner.**  Settled the same way (Roger: "for a robot, a structured, logical breakdown doesn't sound bad"): gpt-4.1-mini scores [robot](../../../data/roles/instructions/robot.json) q42 and q91 3 again.
3. **gpt-5.6-luna reads C more strictly (new, from the rerun).**  On the same text it wants a visible trace of the role.  It scores robot q42 and q91 1, four of the eight aligned-AI responses 1, and secretary q28 1.  So on the AI roles it behaves as gpt-4.1-mini did with addition 2.  If gpt-5.6-luna is chosen, it may need the sentence considered for question 1 in its variant ("For this role, an answer in the voice of a helpful AI counts as C"), for the two aligned-AI roles only, since it would be wrong for [paperclip_maximizer](../../../data/roles/instructions/paperclip_maximizer.json) and [cyborg](../../../data/roles/instructions/cyborg.json).  **Roger (2026-10-27): the sentence "sounds reasonable if we need it, for the aligned-AI roles only".**  Robot may need its own sentence.  The full runs show how large the effect is: [instrumentally_aligned_ai](../../../data/roles/instructions/instrumentally_aligned_ai.json) is in both sets; robot, cyborg and paperclip_maximizer are in the October set.
4. **The reversal rule is applied loosely.**  gpt-4.1-mini still answers C yes for "a great ethical hacker" (hacker q94).  Such responses mostly trip B anyway (q93, q94), which excludes them, but a white-hat answer without a disclaimer would pass as a 3.  The full run will show how often. **Roger: Let's monitor this.**
5. **More lenient on light roleplay.**  Against v5, gpt-4.1-mini now moves six responses into the kept set on a trace of the role (soldier q23, secretary q25 and q7, hacker q27, robot q32 and q91) and one out (hacker q93, a white-hat disclaimer).  Soldier q7, plain fitness advice, stays out.  The full run measures the balance. **Roger: Again, let's monitor and tune.**

## Next

1. **Launched 2026-10-27 12:34 UTC**: gpt-4.1-mini and gpt-5.6-luna under v6, twice each, by batch, with `--save_replies`, on the 30 October and 11 May roles (20,500 responses per run; about $5 a run for gpt-4.1-mini and $2.40 for gpt-5.6-luna, about $15 in all).  Output: `runpod_workspace/rubric_exp/judges/<model>/{oct,may}/{v6,v6_rerun}/` (not there until the batches are collected).  Report: kept per category, each judge's rerun κ against its v3 and v5, the flips against v5, and whether the two judges agree more under v6 than under v5.
2. The blind readers, with the readers' criteria updated to these rules (a single lapse T), on a sample rebuilt around the v5 / v6 disagreements, your category and controls ([reader_check](../judge_comparison/reader_check/), whose sheets wait for this).
3. If v6 holds: the May tree under v6 (about $33 on gpt-4.1-mini, for approval), and the other judges on v6, to see whether they converge.
