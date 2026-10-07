# Role rubric: candidates from the trait rubric V2 work (2026-10-01)

What the trait rubric V2 (`--style RogerV2` in
[regenerate_trait_instructions.py](../../data_analysis/regenerate_trait_instructions.py),
settled as draft 12 on 2026-10-01; design log in
[TRAITS_TO_ADD.md](../../data/traits/instructions/TRAITS_TO_ADD.md) § "Trait
generator V2") did that the role rubric V2.5 in
[regenerate_role_instructions.py](../../data_analysis/regenerate_role_instructions.py)
has not had, with the evidence from traits and a view on whether it carries
over.  Roger asked for this list before the check-in of the trait work, as
the brief for a role rubric V3; nothing here has been tried on roles.  The
role rubric's own record is [comparison_2026-09-11.md](./comparison_2026-09-11.md).

| # | Trait rubric V2 has | Role rubric V2.5 has | Evidence from traits | Carries over? |
| --- | --- | --- | --- | --- |
| 1 | A menu of five openings that say who the model is ("Be someone who", "Become someone who", "From now on, you are someone who", "You are someone who", "You are ..." followed by what the person is), five different ones in every file, the negative opening as its positive | `"You are ...", "Act as ...", "You're ...", "Be ..."`, with "Act as a liar ..." among the examples | On Qwen the role-play openings ("Act as", "Behave like", "Take on the character of") scored 5 to 13 points higher than the identity openings on generic questions, but a depth judge found their answers more often a cartoon (50% against 38%) and less often believable; Roger: "the model is to be the person, not to perform one", and nothing that says to role-play | Yes for the ban on role-play openings and for five different openings a file; the menu itself needs role wording ("You are a forger who ...", "Be a ..."), and `_ROGER_ROLE_TEMPLATE_V2`'s fourth example opens "Act as" |
| 2 | "Do not open with a plain command, or by stating what the person has, believes, wants, or tends to do ... Statements of that kind can follow, once the opening has said who to be" | Nothing on statement openings | Statement openings held 7 to 20% on faults against 70% for "Be someone who"; the production trait corpus opened 33% of instructions that way | Yes, though roles rarely do it (a role file's instructions nearly always open "You are a ..."); cheap to add |
| 3 | A self-check before writing: opens by saying who to be; says what the person does; no phrase taken from the description; nothing softened; the negative as firm as the positive; five different openings | A shorter one (corrected 2026-10-02): "would this person say it of themselves, does it name what they actually do, and has anything been softened, excused, or made generic" | The checks on openings and softening went from 15% and 6% to zero and stayed there on the held-out set | The two clauses roles lack (the opening, no phrase from the description), minus the negative-instruction items (roles have none) |
| 4 | Questions: a concrete situation; at least a fifth of them a choice between two courses of action spelled out in ordinary words, each costing something, costs shown not announced; about a fifth a first-person request for advice; some set in a task done alone; no how-to, facts, yes/no, or one safe answer | "a stance, a decision, a memory, or a reaction ... no recipe, no how-to for a crime, no 'Have you ever'" | On the held-out set, how-to, factual, yes/no and one-answer questions fell from 43% to 0.1%; two-option questions rose from 7% to 28% | Yes, and most of it is already in spirit in the role step; the quotas and "costs shown, not announced" are the additions.  The role questions feed steering lists (AGENT_NOTES, steering-questions rule), which want two-option dilemmas |
| 5 | "Do not give the trait a reason that the description does not contain" (the ban on invented reasons, draft 3) | Self-justification is allowed when marked as the role's | "Because" clauses rose from 1% to 6% under the first drafts and settled at 2 to 4%; invented motives 6 to 8% against the corpus's 9 to 10% | Partly: roles may justify themselves by design (C6), so the rule would be "no reason the description does not give, unless it is the role's own excuse" |
| 6 | "Do not repeat the description's wording; say it in other words, and take no phrasing from it" | "none of them repeats the description's wording" | Roles already repeat five words of their description in 1.7% of instructions, traits 1.0 to 2.0% under V2; Roger's ruling of 2026-09-30: settled, not to be reopened without evidence | No change needed |
| 7 | Length: "20 to 30 words" with examples of 22 to 33, producing 36-word instructions | "15 to 25 words (shorter is better)" with examples of 16 to 25, producing 23.5 | The examples set the length, not the rule (long examples gave 36 to 38 words under rules of 20 to 30 and 20 to 40; short ones 28 under 15 to 25); cutting traits to 28 words cost 3.4 points of effectiveness on Qwen; longer instructions carry more invented detail | Measure before touching: role effectiveness under the current length has never been run on Qwen |
| 8 | `--instructions-only`, `--batch` (Message Batches, half price, for runs over about $20), `--traits-dir` staging, a `generator` block with the template hash | `generator` block; none of the flags | The staging flag is what let drafts be tried without touching the corpus; batch is the policy for large runs | Yes, all three, before a role regeneration |
| 9 | An audit tool ([audit_trait_instructions.py](../../data_analysis/audit_trait_instructions.py)): pattern checks, a blind fault judge, a blind rating of a file's five instructions, a development and held-out split | None; the V2.5 pilot was judged by hand and by one comparison script | Every rubric change for traits was measured on 100 development traits and the final draft on 150 held-out ones | Yes; the tool is trait-shaped (negatives, labels) and needs a role mode |
| 10 | Effectiveness on the model itself ([opening_form_experiment.py](../../data_analysis/opening_form_experiment.py) `plan-arms` and `arms-report`, Qwen at DeepInfra, the pipeline's own judge) | None | Decided the openings, the length and the final draft | Yes; roles need the role eval prompt in place of the trait judge template |
| 11 | Experiment switches removed once settled (AGENT_NOTES § "Experiment switches in rubric files") | Nothing to remove | | Already the case |

Kept apart on purpose: the voice rules (C1, C2, C4, C5 and the voice part of
C7) are the role rubric's and were left out of the trait rubric on Roger's
decision (2026-09-28); the trait rubric's rules on negative instructions and
on the opposite's label have no role counterpart.

## Roger's decisions (2026-10-02)

The walk-through numbered the candidates differently from the table above;
the decisions are by subject.

- **Role-play openings** (row 1): measure first, as proposed, but Roger is
  inclined to cut "Act as": it reads as role-play.  The baseline is the
  role corpus on Qwen (below); 22% of role instructions open "Act as", one
  in nearly every file, so the corpus itself compares "Act as" with the
  other openings on the same roles.
- **A menu of openings, five different a file, no statement openings**
  (rows 1 and 2): agreed.
- **Self-check** (row 3): add the opening clause.  The clause on phrases
  taken from the description is skipped: on 2026-10-02 no role file (0 of
  337) repeats a four-word phrase of its description in two of its five
  instructions, and 6 (1.8%) share any four-word phrase, all stock phrases
  ("you grew up here", "at the dinner table"); 1.7% of instructions repeat
  five or more words of the description.
- **Question quotas** (row 4): agreed; the two-option quota with the costs
  shown, advice questions where the role would plausibly be asked.
- **Invented reasons** (row 5): skipped.  3.0% of role instructions carry
  a reason clause (44 of 337 files), and reading them, about a third
  invent a motive (roughly 1% of instructions); the rest are the role's
  own self-justification, which the rubric allows.  The role audit's
  invented_motive check is the judged figure.
- **Length** (row 7): unchanged unless a measurement asks for it.
- **Tooling and measurement** (rows 8 to 10): agreed, done 2026-10-02:
  `regenerate_role_instructions.py` has `--roles-dir`,
  `--instructions-only` and `--batch`;
  [audit_role_instructions.py](../../data_analysis/audit_role_instructions.py)
  (split, stage, judge, report, taste) with its own fault list (softened
  allowing marked self-justification, observer register, chat frame except
  for AI roles, generic, invented detail, invented motive, off-role) and
  the rubric's own pattern checks (role-play openings, observer words,
  dashes, 15 to 25 words); `opening_form_experiment.py plan-arms --entity
  role`, judged with each role file's own `eval_prompt` as the pipeline
  judges it, and a report by opening.  The split is in
  [split.json](../role_rubric_v3_pilot/split.json) (150 development, 150
  held out, seed 20261002) with a 100-role sample,
  [sample100.json](../role_rubric_v3_pilot/sample100.json).
