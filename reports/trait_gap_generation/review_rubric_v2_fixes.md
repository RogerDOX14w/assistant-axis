# Review of the rubric v2 round 4 fixes, diff `a58ffcc..542ebd9`

Reviewer: Fable, 2026-09-29, taking over from a reviewer that stalled.  Checks the round against
[reports/trait_gap_generation/review_rubric_v2.md](./review_rubric_v2.md).  Specification: Roger's
words in [reports/trait_gap_generation/decisions_m1.md](./decisions_m1.md).  Link targets are relative
to this file.  "Ran" means executed in the worktree with scratch under `/tmp`, no paid call and no
recorded run repeated; "read" means confirmed in the source or the recorded files; "infer" is marked.
"Before" is the code at `a58ffcc`, exported to scratch and run there; "after" is `542ebd9`.

**The worktree changed while I worked.**  Two commits and one paid run were added after `542ebd9`
(section 6).  I did not make them.  I used the new run's records as evidence, since they are the
largest sample of classifier version 4 on disk.

## 1. Go or no-go

**No-go as the code stands, by one defect that is free to fix.**  All five must-fix findings are
fixed, but the round's new required field and its shorter list of sense kinds make the validator
refuse rows and ask again, which is must-fix 3 over again: in the latest recorded batch 4 of the 126
rows the model saw failed at first pass, 3 had their first answer replaced (one changed verdict) and
1 was lost, a parse rate of 99.2% against a hard gate of 99% (section 4, defect 1).

With that fixed in the validator (no prompt change, no paid call), the run is a go at about $4 to $5,
on two conditions that are settings and not code: the stability rerun is run as the plan's 200 rows,
not as a second full pass, and the corpus comparison is given a budget of $2.

Advice, not a condition (infer): the rows never seen in development can be measured once.  If Roger's
marks on the 50 words may lead to a narrower definition of a trait, take the marks first.

## 2. Findings 1 to 11

| # | finding | status | before | after |
|---|---|---|---|---|
| 1 | figures for unseen rows | fixed | ran: no `unseen` block, no `development_seen` | ran: every figure twice, `n_seen_in_development`; on the real files 510 of 1,810 rows were marked seen at `542ebd9` (the review counted 506; the other 4 are labels seen only in the plain-reading development runs) |
| 2 | Roger's worst case raises no note | fixed; not yet shown to him | ran: noble [status, trait] and cold [bodily, trait]: rank 2, no note, `polysemy` false; the reject figure counted a rank 2 row that carried no flag | ran: `obvious_sense_not_trait`, `polysemy` true; the figure counts flagged rows only.  No table lists these rows (defect 4) |
| 3 | tags that do not fit are asked again | fixed for tags; the same fault returns elsewhere (defect 1) | ran: `tagged` with `membership` and `reject` with `physical` refused; the runner asked Haiku twice and kept the second answer | ran: both kept with `tag_disagreement`; Haiku asked once, first answer kept, Sonnet's opinion recorded.  Read: round 4 batch first-pass parse 1.00 (was 0.90), no row `tagged` with `membership` (was 3) |
| 4 | a rejected label scored correct | fixed | ran: four rejected rows carrying `state`, `membership` or `physical` all scored `correct` | ran: `floor`, `floor`, `reject`, `reject`; `tagged` with `state` or `physical` still `correct` |
| 5 | sense kinds contradict decision 3 | fixed | read: six kinds, `circumstance` and `status` not traits | read: four kinds, "every membership is a trait sense".  Read: the case-4 note fired on 1 of 30 rows (was 4); single and absentee are no longer flagged |
| 6 | tests read two untracked files | fixed | read: the round 3 test opened both | ran: 197 rubric tests pass on a clean export of `542ebd9` that has neither file.  Both files are still untracked.  The tracked word list is one token behind the working file ("sg"); harmless |
| 7 | a stop loses the readings | fixed | ran: cap trips on the 80th of 120 readings; 80 charged, 0 readings kept, runner and filter alike | ran: 80 kept in both |
| 8 | nothing writes `corpus_regions.json` | fixed | read: no writer | ran: the command wrote 659 traits, with `alignment_relevant`, from the round 4 batch to scratch.  Ran: all 659 corpus stems have a validation row, so the full run should leave none empty |
| 9 | pins protect two hashes | fixed for every version a run has recorded | read: two hashes asserted | ran: changing the pin of classifier 3 or 4, probe 3, comparison 2 or states queue 1 fails the test.  States queue 2 and 3 and states corpus 2, which no run has recorded, can still be changed unnoticed |
| 10 | corpus labels in the prompt | fixed | the review ran: promiscuous, easygoing, gentle, exasperated | ran: absent from every prompt; every prompt word that is a corpus, queue or validation word is on the allowlist (section 3) |
| 11 | smaller | 3 of 4 | | ran: the example test checks every field; budget-stop tests for three runners; docstrings corrected; 0 of 18 superseded refusals claim that no replacement is recorded.  Not done and not reported as skipped: the judgement-call table still stores none of Roger's calls |

## 3. Prompt findings, classifier version 4

Read whole, 5,562 tokens by the recorded usage.  **Every contradiction quoted in the review's section
5 is gone**, except the width of the definition, which the implementer was told to leave.  Reason
precedes verdict in the schema, in all 28 examples and in the user message.  Every example passes the
validator (ran).

Faults that remain or are new:

* **An evaluative word has no sense to copy, and the model returns none.**  New.  "person_senses: the
  senses of the word that can be said of a person" and "judged_sense: ... usually copied from
  person_senses ... Null only for "reject"", against the example "awesome": "person_senses [];
  judged_sense "general approval"".  Ran, on the recorded batch: of three answers tagged
  `evaluative_only`, two gave `judged_sense` null.  This is half of defect 1.
* **"physical" is read as a property of things.**  New in its extent.  "physical (a lasting feature of
  the body)" and "Senses that can only be said of things are not listed", yet the model wrote flat
  "having a flat shape or surface (physical)", rusted "corroded by oxidation (physical)" with the gloss
  "having skin or joints marked by rust", and mail-clad "wearing chain mail armor (physical)".
  Version 3 rejected rusted and orange-brown.  Read, 125 rows: 8 of 11 `physical` tags (five colour
  words, mail-clad, asymmetrical, soft-nosed) and 3 of 7 case-4 notes (twisted, fluffy, unsharpened).
* **An intended sense against the main reading.**  Unchanged from version 3.  "If an intended sense is
  supplied ... judge that sense; if it is not a trait sense, judge the best trait sense of the word"
  against "A word whose main reading is a condition someone is in for a while ... is "tagged"
  "state"".  No effect on this run: no validation row carries an intended sense (ran, 0 of 1,810).
* **Class and age have examples on the role side only** (newborn, duchess): no example of an age
  group or class that is a trait, none of a very low status.  Unchanged.
* **Small.**  The thermostat example gives "region cognitive_epistemic" and the words "(choose the
  closest region)" were removed.  The role rule has no main-reading clause.

**The allowlist** (check 3).  41 words, all ordinary prose, none opening an example.  Two sit inside
an example's sense fields: `elected` in "holder of an elected seat (role)", a validation word and
Roger's own example of an office; and `general` in "general approval", a turned-down queue entry.
The test looks only at the opening of an example line, so it would not catch an allowlisted label
used as a listed sense (defect 5).  The frozen comparison prompt's eight: competitive, fair, generous
and modest (corpus traits, in the texts of the "sporting" example), unpopular (corpus trait),
writer (corpus role, "a careful writer"), extreme (superseded entry), running (validation word).
None is an example label.  None can matter to the filter run, which makes no comparison.  Five are
corpus traits that the corpus comparison will judge; infer: negligible, revisit when that prompt next
changes.  One multiword label occurs, "at hand", in a gloss.

**The two judgement calls** (check 4).

* *Hashes re-pinned in place.*  No action.  Ran: the prompt modules changed in one commit, so git
  holds one hash for version 4, and both recorded version 4 runs carry it; no run records states queue
  3 or states corpus 2.  Those two have never been run; their first paid call will be the states pass.
* *"flat".*  No action before the run, but it is a pattern and not one row in 30 (above).  Roger's
  judgement-call table will be about 40% such rows.  It moves none of the three headline figures.
  One sentence in the next prompt version would address it.

## 4. New defects introduced by the round

1. **Blocking.  A row the validator refuses is asked again, and the second answer replaces the
   first.**  [assistant_axis/gapgen/filter_rubric.py:581](../../assistant_axis/gapgen/filter_rubric.py)
   (`judged_sense` required on `tagged`) and
   [filter_rubric.py:468](../../assistant_axis/gapgen/filter_rubric.py) (a sense kind outside the four
   fails the row).  Read, batch `m2rubric_r5_sample_1`: endless and abominable came back `tagged`,
   `evaluative_only`, no sense, `judged_sense` null; clinical and virulent listed a second sense of
   kind `relational_only`.  On the retry endless changed to `trait` with another reason, clinical
   changed region, abominable repeated its answer and was lost.  At 0.8% lost the full run would lose
   about 12 rows against 15 allowed.  Fix: accept a row whose `judged_sense` is null (fall back to the
   first listed sense, else null) and drop a sense of unknown kind, recording both in the row and
   counting them in the summary.  `test_judged_sense_field` asserts the present behaviour and changes
   with it.
2. **After the full run every row counts as seen.**
   [data_analysis/gap_generation/traithood_filter.py:269](../../data_analysis/gap_generation/traithood_filter.py)
   excludes only the run's own id.  Ran: a later run marks all rows of `m1_validation` as seen, so the
   stability rerun's `unseen` block is empty.  Fix: a flag naming runs that are not development.
3. **An assertion lost behind a comment.**
   [assistant_axis/tests/test_gapgen_filter.py:104](../../assistant_axis/tests/test_gapgen_filter.py):
   `and f["gloss_in_band"] is True` now follows the `#`.  The field is still written (ran).  Fix: move
   the comment.
4. **`obvious_sense_not_trait` rows reach no table.**
   [data_analysis/gap_generation/gap_registry.py:161](../../data_analysis/gap_generation/gap_registry.py).
   Fix: list them in `judgement-calls`, first.
5. **The allowlist test checks one position.**
   [assistant_axis/tests/test_gapgen_rubric_v2_round4.py:308](../../assistant_axis/tests/test_gapgen_rubric_v2_round4.py).
   Fix: parse the examples and refuse an allowlisted word in a sense or `judged_sense`, with `elected`
   and `general` named as the two exceptions until the prompt next changes.
6. **Two figures in "M1 as built" would mislead.**
   [reports/trait_gap_generation/acceptance_platform.md](./acceptance_platform.md): the rerun is costed
   as a second full pass, and the recorded corpus command, `--budget-usd 1.5`, is refused (ran:
   "estimate $1.53 exceeds --budget-usd $1.50").
7. **Stale text.**  [filter_rubric.py:1](../../assistant_axis/gapgen/filter_rubric.py) says version 3;
   [assistant_axis/gapgen/plain_reading.py:28](../../assistant_axis/gapgen/plain_reading.py) says
   `related` raises no flag;
   [assistant_axis/tests/test_gapgen_filter_rubric.py:182](../../assistant_axis/tests/test_gapgen_filter_rubric.py)
   uses the retired kind `bodily`.  An `unseen` figure with no rows prints `meets_target: false`.

## 5. Cost of the run, stage by stage

**The code has no stability mode.**  A run over the validation file takes all 1,810 rows unless
`--sample-frac` is given, so a bare rerun is a second full pass.  The plan and the acceptance test ask
for 200.  `--sample-frac 0.13 --sample-seed 1 --shuffle-seed 1` gives 241 rows, 210 of them to the
model (ran, dry run); 0.11 gives 204, too few if any row fails.

| stage | budget to type | the tool's estimate | at the recorded rates |
|---|---|---|---|
| filter, 1,810 rows: 1,552 to the model, 258 cut free, 330 probed | 5 (the default) | $3.68 (ran) | $2.6 to $3.0 |
| stability rerun, 241 rows | 1 | $0.60 (ran) | $0.4 to $0.5 |
| corpus comparison, 659 labels | 2 | $1.53 (ran) | $0.97 |
| states pass, about 130 rows, and its corpus check, about 38 | 0.5 | $0.13 (read: the implementer's; it cannot be dry-run until the filter's results exist) | $0.12 |
| **in all** | | **$5.9** | **$4.1 to $4.5** |
| in all, if the rerun is a second full pass | | $9.0 | $6.3 to $7.1 |

Every figure is under the $20 rule.  Rates, read from the `usage.json` and response records:
classifier 220 output tokens a row; the rubric cached, written by the first four calls and read by the
rest; probe 70 output tokens a row; second opinions on 10% of rows in three batches and 17% in one,
228 output tokens each; a reading $0.00018, a comparison $0.0013.

The implementer's other figures check: the dry runs give its $3.68 and $1.54, and the recorded rates
give its $0.98 and $0.13 to within a cent or two.  Its "$4.2 at the measured rate" is too high: it multiplies the smoke batch's $0.0027 a row, of which $0.035 in $0.082
was three cache writes that do not grow with the rows.

Not the round's, but it bears on the rerun:
[assistant_axis/tests/test_gapgen_acceptance.py:115](../../assistant_axis/tests/test_gapgen_acceptance.py)
counts rows cut by the floor, which always agree (31 of the 241).

## 6. Outside the round's scope

**Inside the diff, nothing strayed.**  Ran: the comparison and plain-reading prompts carry the hashes
the held-out run recorded.  Ran: none of the six held-out words is in any prompt, test input or smoke
input; they occur only in the reserved list, in QUESTIONS.md and in the committed review.  Ran: the
definition of a trait is word for word that of version 3.  The two states prompts changed by word
swaps only, under finding 10.  One overstatement: QUESTIONS 11 is marked "answered" by the
coordinator, while Roger's line under R4 is empty.  The prompt carries answer B, as the review
recommended.

**After the diff, while this review ran:**

* `6a7b784` (12:15) and `ecaf4b5` (12:19) add an input set, a paid run and
  [reports/trait_gap_generation/random_traits_for_marks.md](./random_traits_for_marks.md).
* The run, `m2rubric_r5_sample_1`, cost $0.25: classifier version 4, the pinned hash, 160 rows.
* **It took 160 of the 735 random adjectives that no run had seen.**  Ran: the unseen random
  adjectives for the full run fall to 575, and rows seen in all rise from 510 to 670.  The report for
  Roger does not say so.  `build_smoke_sets.py` provides for further steps of 40.
* It passed 61 of 159 random adjectives as traits, 38% against the target of 15%.
* Recommendation: no further steps.  Every validation run already prints the same sample, so the full
  run can supply it, or the words can come from outside the validation file.

I read these two commits; I did not review them.

## 7. Not verified

* That no paid call was made with an earlier text of version 4.  That needs the provider's billing;
  nothing on disk suggests one.
* The whole suite.  I ran the round 4, acceptance and rubric files (77 passed, 4 skipped) and 197
  tests on the clean export; the caller reports 442 passed.
* Version 4 on existing labels at scale.  Only 15 have been run; the four refusals were all random
  adjectives, so the rate of defect 1 on labels is unknown.
* Token counts by the counting endpoint; mine are from recorded usage.
