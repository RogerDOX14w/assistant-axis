# The combination rubric review (2026-10-29 to 2026-10-31)

How pipeline step 3 ([3_judge.py](../../../pipeline/3_judge.py)) should judge a combination's responses, generated
under an instruction to be a role and to have a trait at once, for the October extraction.  **Settled 2026-10-31 as
prompt version 20** in [judge_rubrics.py](../../../assistant_axis/judge_rubrics.py): each response is judged twice by
gpt-5.6-luna, by version 16 (the role rubric with the trait named as context) and by version 17 (the trait rubric
with the role named as context), and scored the lower of the two, so it enters the combination's vector only when
both sides give 3.  The versions table in [pipeline/README.md](../../../pipeline/README.md) (rows 14 to 20) records
each draft; this file is the map of the review's evidence and decisions.  Every judging here was done with luna Flex
calls, about $11 in all; the judged samples (score directories `combo_v14/` to `combo_v20/`, the separate `role/` and
`trait/` judgings) live under `runpod_workspace/combo_explore/`, `combo_recheck/` and `tcomb_recheck/`, which git
ignores.

## 1. Exploration on May responses ([explore/](./explore/))

28 combinations, 1,522 May responses, each judged three ways (the April combination text; the role alone under
version 10; the trait alone under version 13; [analyze_output.txt](./explore/analyze_output.txt),
[rows.json](./explore/rows.json)).  When a combination fails, one persona is usually still there (62 to 71% of
drops); the lost one is the demanding persona (the goal entity in 7 of 9 ordinary pairs); the refusal is
trait-shaped ([harmful](../../../data/traits/instructions/harmful.json) 15% alone,
[demon](../../../data/roles/instructions/demon.json) 98%); the April text drops 17 to 29% of the responses in which
both separate judges see both ([patterns_output.txt](./explore/patterns_output.txt),
[keep_rates_output.txt](./explore/keep_rates_output.txt)).  Roger's threshold rules on the separate scores collapse
to "both 3" and "either" ([rules_output.txt](./explore/rules_output.txt)).  Drafts 14 (A, B, R, T; both needed) and
15 (either enough), rendered in [rubric_drafts.md](./rubric_drafts.md) by [render_drafts.py](./render_drafts.py), run
on the same sample ([compare_arms_output.txt](./explore/compare_arms_output.txt), [examples_output.txt](./explore/examples_output.txt)).

## 2. First reading sheet, May responses ([reader_check/](./reader_check/))

53 combination items read blind by subagents under [criteria.md](./reader_check/criteria.md) (the readers' criteria,
which carry Roger's rulings; its role and trait sections come from the role rubric experiment and the trait rubric
review), plus a role-only and a trait-only sheet of 30 each; [tally.py](./reader_check/tally.py) scores every
judgement against the letters ([tally_output.txt](./reader_check/tally_output.txt)).  Roger marked 48 of the 53
([roger_sheet.md](./reader_check/roger_sheet.md)): on traits he is more generous than the readers and far more than
the trait judge, crediting the trait shown in the role's voice.  **Decision, 2026-10-30:** "we definitely need to
require both", and each side is judged by its own rubric knowing the other half of the instruction as context, not
as something to score.

## 3. The context arms: versions 16, 17 and 18 ([context_arms/](./context_arms/))

Rendered with samples in [rubric_drafts_context.md](./rubric_drafts_context.md)
([render_context_drafts.py](./render_context_drafts.py)); run by [run_judging.sh](./context_arms/run_judging.sh);
scored by [compare.py](./context_arms/compare.py) against Roger's and the readers' letters, the separate judges and
draft 14 ([compare_output.txt](./context_arms/compare_output.txt) for the May and r_ samples,
[compare_output_tcomb.txt](./context_arms/compare_output_tcomb.txt) for t_; disagreements with quotes in
[examples.md](./context_arms/examples.md) and [examples_tcomb_recheck.md](./context_arms/examples_tcomb_recheck.md)).
The role side 16 agrees with the role judge 0.90 to 0.92 and corrects its over-credit of professionals on generic
answers; 17 agrees with the trait judge 0.92 to 0.95; 18 (17 in the A/B/C shape) is more generous and over-credits
cooking metaphors on t_ data.  [candidates.py](./context_arms/candidates.py) gives the three "both" rules' precision
and recall on the first sheet and their low-keep counts against May ([candidates_output.txt](./context_arms/candidates_output.txt)).
Version 18's first text had luna answer its C about the role; the corrected run replaced it and the first run's
outputs are kept under `logs/v18_unnamed_trait/`.

## 4. Re-check on October responses ([recheck/](./recheck/))

The first October responses (1,024-token cap, the October instructions): 27 r_ combinations (the
[predator](../../../data/roles/instructions/predator.json)'s row and the understated and pensive pairings) and 44
t_ combinations (the [chef](../../../data/roles/instructions/chef.json)'s row, harmful across six roles, the machine
roles' carve-outs, the five least plausible pairings), 60 responses each, sampled by
[build_sample.py](./recheck/build_sample.py) and read by [analyze.py](./recheck/analyze.py)
([analyze_output.txt](./recheck/analyze_output.txt), [analyze_output_tcomb.txt](./recheck/analyze_output_tcomb.txt)).
The April text under luna keeps 0.18 (r_) and 0.30 (t_) and cannot move to luna as it is; "both" by the separate
judges keeps 0.44 and 0.54; the persona lost is the role on r_ and the trait on t_; harmful is no longer refused under
the October instructions.

## 5. Second reading sheet, October responses ([reader_check_2/](./reader_check_2/))

162 October responses drawn at random within kind × keep level × the candidates' pattern
([build.py](./reader_check_2/build.py), [key.json](./reader_check_2/key.json)), four sheets read blind by Fable
subagents ([sheet_1_marks.md](./reader_check_2/sheet_1_marks.md) to [sheet_4_marks.md](./reader_check_2/sheet_4_marks.md);
their criteria questions in [readers_questions.md](./reader_check_2/readers_questions.md)), 30 of them marked by
Roger ([roger_sheet_2.md](./reader_check_2/roger_sheet_2.md)) and six more chosen for the readers' questions
([roger_sheet_3.md](./reader_check_2/roger_sheet_3.md), whose rulings went into the criteria).
[estimate.py](./reader_check_2/estimate.py) weights the letters back to the samples by cell with a stratified
bootstrap and maps the readers' letters to Roger's standard through his 30 random items
([estimate_output.txt](./reader_check_2/estimate_output.txt), [estimate.json](./reader_check_2/estimate.json)).
At his standard, with an expected keep of 0.61:

| rule | keep | precision [95% CI] | recall [95% CI] |
|---|---|---|---|
| draft 14 (one prompt, both needed) | 0.72 | 0.75 [0.69 0.81] | 0.89 [0.85 0.93] |
| **16 with 17** | 0.51 | 0.86 [0.78 0.92] | 0.72 [0.68 0.77] |
| 16 with 18 | 0.55 | 0.84 [0.77 0.91] | 0.77 [0.72 0.81] |

The May sheet's r_-high, t_-low precision pattern is not there on October data.  **Decision, 2026-10-31:** "16+17 on
the basis of precision."  No combination keeps under 0.10 under the pair in any sample (May had 7 of 1,797 under
the April text).

## 6. After the decision

- **Version 19** (17 with a sentence giving the trait's outlook in the third person) was tested at Roger's request
  and rejected: it flips as many responses down as up ([v19_check_output.txt](./reader_check_2/v19_check_output.txt),
  [v19_rendered_sample.md](./context_arms/v19_rendered_sample.md)).
- **The six rulings of sheet 3** (role criterion 5 for a narrowly voiced profession; the trait's subject raised to
  negate it; the aligned-AI carve-out) agree with what the pair does on five of the six; the sixth
  ([mechanic](../../../data/roles/instructions/mechanic.json) / harmful, "no point in passing it around") is one
  response in 162, not evidence for a change.  On his 36 October items the role side gives precision 1.00 and
  recall 0.92 against his letters, the trait side 0.94 and 0.67; the recall left on the trait side is the trait
  shown in the role's voice, which versions 18 and 19 were the attempts to recover.  **Final, 2026-10-31.**
- **Implementation:** version 20 in [judge_rubrics.py](../../../assistant_axis/judge_rubrics.py)
  (`combination_sides`, `combination_judges`, the `two_sides` reply format) and the two-sided path in
  [3_judge.py](../../../pipeline/3_judge.py) (`_sides/<entity>.json` beside the score files, custom ids
  `<entity>|<key>#<side>`, per-side token limits, the stamp's `combination_sides`), with gpt-5.6-luna as step 3's
  default judge; tests in [test_judge_rubrics.py](../../../assistant_axis/tests/test_judge_rubrics.py) and
  [test_3_judge.py](../../../pipeline/tests/test_3_judge.py); a live smoke test on
  [t_chef__harmful](../../../runpod_workspace/tcomb_recheck/combo_v20/) (120 calls) gave combined scores equal to the
  lower side and sides agreeing with the separate 16 and 17 runs on 58 and 57 of 60.
