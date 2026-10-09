# W1: depth of role rubric V3, and the observer register (2026-10-09)

## Findings

1. **V3 is as much of a cartoon as the old corpus and as "From now on", and less than "Act as".**  Cartoon (the depth judge's top caricature grade: theatrical, over the top, stage directions) is 22.4% of V3's answers against 21.3% for the old corpus instruction asked the same day (+1.0, -3.4 to +5.5, p = 0.69), 22.8% for the old corpus file with its one "Act as" in five (-0.4), 23.0% for "From now on" (-0.6) and 28.6% for "Act as" (**-6.3, -11.6 to -1.0, p = 0.025**).  So the regeneration kept what the opening tests promised: "Act as" gone, caricature back to the level of the non-role-play openings.
2. **By kind, nothing differs significantly, and the bad roles are the ones to watch.**  On the 18 bad roles V3 is 56.7% cartoon against 46.7% for the old non-role-play instruction (+10.0, -2.2 to +23.3, p = 0.18), 57.2% for "From now on" and 68.9% for "Act as".  That is where "From now on" sat; good and indifferent roles are flat.
3. **The one real change: V3's answers describe their own role more often.**  46.4% against 39.8% (+6.6, +1.7 to +11.3, p = 0.01), and +7.2 against "From now on" (p = 0.03).  The rise is in the indifferent roles (+9.0, p = 0.007), mostly occupations ("As a technologist, I believe ...").  It comes on top of acting, not in place of it: "the role shapes what it does" +4.0 (p = 0.10), the role judge's "scored 3" +2.9 (p = 0.007), the assistant's voice -3.8 (p = 0.06).  It is not tied to instruction length within V3 (Spearman -0.04).  I would note it, not act on it.
4. **Observer register is mostly a judge artefact plus one opening, and harmless for depth.**  About a third of the flags (22 of 73 in the corpus) quote the role's description, not the instruction, nearly all on p0, the instruction printed right under the description in the judge's prompt.  Counting only flags whose quote is in the instruction, the held-out rise is 1.7% to 3.9% (p = 0.055), not 2.0% to 5.3%.  The opening that carries it is **"Become a ... who ..."**: 7.2% of those instructions against 1 to 4% for every other.  Ten roles have it in two or more of five, and all ten are among the twelve Roger read and kept in the 2026-10-04 reroll pass.  Flagged instructions are no more of a cartoon than unflagged ones of the same role (see Part 2).  **Recommendation: leave it.**  If the role rubric is reopened for another reason, one self-check line on the "who" clause of "Become" would cover it; a reroll would not help.
5. **Spend: $10.59** against an estimate of $10.6 (Qwen $0.23, role judge $0.83, depth judge $9.52); [usage.json](../../reports/opening_forms/roles_v3_depth/usage.json).

## Part 1: method

The same 99 development roles as the opening-depth run, each with the same 10 questions both earlier depth runs used.  Those are the old corpus's own questions, held fixed so that the instruction is the only thing that changes.  V3's regenerated questions were not used: a fifth of them are first-person requests for advice, which invite an adviser's voice by design.  Roles were asked in four ways:

- **V3:** one of each role's five current instructions, with the opening rotated within kind so that each opening covers about 20 roles.
- **Anchor:** the old corpus instruction that [roles_depth](../../reports/opening_forms/roles_depth/plan.json) read as "other" (89 roles), asked again the same day.
- **Observer flags:** for Part 2, the observer-flagged V3 instructions with a control (15 instructions); these are left out of the V3 figures.

The settings were the earlier runs': Qwen 3 32B at DeepInfra, the extraction's settings, each role file's eval_prompt (unchanged under V3) as the role judge, and the role depth judge (Sonnet 4.6, rubric 1, not told the instruction).  The total was 2,030 answers, all generated, scored and read.  [Plan](../../reports/opening_forms/roles_v3_depth/plan.json), [builder](../../reports/opening_forms/roles_v3_depth/build_plan.py), [analysis](../../reports/opening_forms/roles_v3_depth/analyse.py), [results](../../reports/opening_forms/roles_v3_depth/depth_paired.json), [printout](../../reports/opening_forms/roles_v3_depth/logs/analyse.txt).

**How the comparisons are made.**  Comparisons are paired within role: each role's share for one arm minus the same role's share for the other, averaged over roles.  The interval comes from resampling roles (a [paired bootstrap](../../reports/trait_gap_generation/glossary.md#paired-bootstrap)) and p from a sign-flip test, exactly as in the earlier tables, which the script reproduces.

The runs drift a little from day to day.  The identical "Act as" text moved -2.2 points of cartoon between 2 and 3 October (p = 0.09), and the identical old instruction +1.7 between 2 and 9 October (p = 0.33).  So comparisons with the old arms are **chained**: the anchor plus within-run contrasts (Act as = anchor + (Act as - other) of 2 October; From now on = that + (From now on - Act as) of 3 October), so that drift cancels.  The direct cross-run figures differ from the chained ones by up to about 3 points.

**Kinds** are Roger's classes in [sample100_kinds.json](../../reports/role_rubric_v3_pilot/sample100_kinds.json).  "Laid on" (caricature grade 1 or 2) is 94 to 97% in every arm, as before.

**Levels**, mean over the 89 roles every arm has (percent of answers; the old arms chained to the 9 October run):

| arm | cartoon | assistant's voice | describes its own role | role shapes what it does | scored 3 |
| --- | --- | --- | --- | --- | --- |
| V3 | 22.4 | 29.6 | 46.4 | 67.9 | 96.6 |
| old corpus instruction, same day | 21.3 | 33.4 | 39.8 | 63.8 | 93.7 |
| old corpus file (one "Act as" in five) | 22.8 | 32.4 | 40.5 | 64.3 | 94.4 |
| "Act as" | 28.6 | 28.3 | 43.4 | 66.3 | 97.0 |
| "From now on" | 23.0 | 27.0 | 39.2 | 68.6 | 96.1 |
| "Be" | 27.3 | 31.3 | 41.0 | 62.4 | 96.1 |

**Cartoon, V3 minus each arm**, paired within role (95% interval), p:

| V3 minus | all (89) | good (11) | bad (18) | indifferent (60) |
| --- | --- | --- | --- | --- |
| old corpus instruction, same day | +1.0 (-3.4 to +5.5), 0.69 | -2.7 | +10.0 (-2.2 to +23.3), 0.18 | -1.0 |
| old corpus file | -0.4 (-4.7 to +3.7), 0.84 | -3.5 | +5.6 (-5.7 to +17.6), 0.39 | -1.7 |
| "Act as" | **-6.3 (-11.6 to -1.0), 0.025** | -6.4 | -12.2 (-25.0 to +0.6), 0.10 | -4.4 |
| "From now on" | -0.6 (-5.8 to +4.6), 0.83 | -6.4 | -0.6 | +0.4 |
| "From now on", direct (99 roles) | +2.3 (-1.5 to +6.4), 0.27 | -5.0 | +5.5 (-5.9 to +16.4), 0.39 | +2.6 |
| "Be" | -4.9 (-10.4 to +0.4), 0.08 | -11.8 | -3.9 | -3.9 |

**The other measures, V3 minus each arm:**

| V3 minus | assistant's voice | describes its own role | role shapes what it does | scored 3 |
| --- | --- | --- | --- | --- |
| old corpus instruction, same day | -3.8 (-7.6 to 0.0), 0.06 | **+6.6 (+1.7 to +11.3), 0.01** | +4.0 (-0.6 to +8.5), 0.10 | **+2.9 (+0.9 to +5.1), 0.007** |
| old corpus file | -2.8, 0.12 | **+5.9 (+1.2 to +10.5), 0.015** | +3.5, 0.13 | +2.3, 0.03 |
| "Act as" | +1.2, 0.63 | +3.0, 0.31 | +1.5, 0.65 | -0.3, 0.87 |
| "From now on" | +2.6, 0.33 | **+7.2 (+0.9 to +13.4), 0.03** | -0.7, 0.85 | +0.6, 0.76 |

By V3 opening (about 18 roles each, so only suggestive): "Be a ..." leans cartoon (+12.8 over the same roles' old instruction, p = 0.10).  That is carried by a few broad texts, such as the [caveman](../../data/roles/instructions/caveman.json)'s "smashes, drags, and grunts", not by the opening's shape.  "You're a ..." is the lowest.

## Part 2: observer register

**Observer register** is the role audit's fault "written in an outsider's register rather than in words the role would use of itself" (a case worker's, an academic's or a brochure's words, or literary flourishes).  It is judged by Sonnet 4.6 in [audit_role_instructions.py](../../data_analysis/audit_role_instructions.py).  This part re-reads the existing judgements in [judged/](../../reports/role_rubric_v3_pilot/judged/final/) with no new calls: [observer_register.py](../../reports/opening_forms/roles_v3_depth/observer_register.py), [observer_register.json](../../reports/opening_forms/roles_v3_depth/observer_register.json).

| set | all flags | flags quoting the instruction itself | files with 2+ of 5 |
| --- | --- | --- | --- |
| held-out 150, corpus as it was | 15 of 750 (2.0%) | 13 (1.7%) | 2 |
| held-out 150, V3 | 40 of 750 (5.3%) | 29 (3.9%); p = 0.055 against the corpus | 5 |
| development 100, corpus and V3 draft | 3.2% and 3.6% | 2.4% and 2.4% | 2 and 3 |
| all 337 files now | 73 of 1,685 (4.3%) | 51 (3.0%), in 36 files | 10 |

**Which opening carries it.**  These figures are real flags in the current corpus:

- "Become a ... who ..." 15 of 208 (7.2%)
- "You're a ... who" 4.1%
- "From now on ... who" 3.3%
- "Become" without "who" 2.3%
- "You are a ... who" 2.0%
- "Be a ..." 1.5%

So neither the relative clause nor "Become" alone does it; the combination does, where the generator narrates what the role has become.  "Become" is the fifth instruction in 331 of 337 files, so the opening cannot be told apart from the position.

**Two or more of five:** [celebrity](../../data/roles/instructions/celebrity.json), [coral reef](../../data/roles/instructions/coral_reef.json), [eldritch](../../data/roles/instructions/eldritch.json), [guide](../../data/roles/instructions/guide.json), [interpreter](../../data/roles/instructions/interpreter.json), [pilgrim](../../data/roles/instructions/pilgrim.json), [sociologist](../../data/roles/instructions/sociologist.json), [spirit](../../data/roles/instructions/spirit.json), [virtuoso](../../data/roles/instructions/virtuoso.json), [wraith](../../data/roles/instructions/wraith.json).  All ten were in [reroll_candidates.json](../../reports/role_rubric_v3_pilot/reroll_candidates.json) and kept by Roger on 2026-10-04 ([ROLES_ADDED.md](../../data/roles/instructions/ROLES_ADDED.md) § "Reroll pass over the regenerated corpus").

**Five real examples:**

1. [guide](../../data/roles/instructions/guide.json) p4: "Become a guide who has led people through places that would stop them cold without you, who reads uncertainty the way others read a map, and who earns trust by being right more often than not."
2. [eldritch](../../data/roles/instructions/eldritch.json) p1: "Be an ancient and alien presence whose thoughts move in directions no human mind can follow, whose attention falls on worlds the way a tide falls on sand."
3. [healer](../../data/roles/instructions/healer.json) p4: "Become a healer who holds space for suffering, reads what the body is saying, and guides each person toward the wellness that is theirs to reclaim."
4. [physicist](../../data/roles/instructions/physicist.json) p4: "Become a physicist who probes the fundamental structure of reality, from the subatomic to the cosmological, using observation, theory, and relentless quantitative reasoning."
5. [celebrity](../../data/roles/instructions/celebrity.json) p4: "Become a household name who jets between film sets and charity galas, lives behind gates because the alternative is a crowd outside your door, and watches your social media numbers like a second heartbeat."

A typical false flag: [translator](../../data/roles/instructions/translator.json) p0, where the judge's quote, "A translator is a language specialist who converts text and meaning", is the description.

**Link to depth.**  In the 10 development roles with a flagged V3 instruction, the flagged instructions were compared with the same role's unflagged ones:

- cartoon -0.7 (-17.7 to +14.3)
- assistant's voice +7.8 (+0.7 to +18.7, p = 0.13)
- "the role shapes what it does" -8.7 (p = 0.27)

No sign of more caricature; at most a lean toward the adviser's voice, unproven on 10 roles.  At 3% of instructions it cannot move the corpus figures in Part 1, which match the old corpus.

**Is it worth a fix?**  Not now.  Two possible fixes:

- **The rubric.** One self-check line for "Become": after "who", what you do, in words you would use yourself, with no similes and no narrator's summary.  It would cost a full regeneration and a recheck for a fault that does no measured harm, so it belongs to the next rubric revision, if there is one.
- **The audit tool.** Drop observer flags whose quote is not in the instruction.  That was a third of the flags here, and it inflated the reported held-out rise.
