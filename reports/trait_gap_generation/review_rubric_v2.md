# Review of the rubric v2 change set, diff `5d6b0dd..a58ffcc`

Reviewer: Fable, 2026-09-29.  Specification: Roger's words in [decisions_m1.md](./decisions_m1.md)
(the blocks marked "Your decision", "Confirm or correct" and "Your reply").  Link targets are relative
to this file; the link text is the path from the worktree root.  "Ran" means executed in the worktree
with scratch under `/tmp`, no API call and no recorded run repeated; "read" means confirmed in the
source or the recorded files; "infer" is marked.

## 1. Verdict

**Fit for the full validation run after five named fixes**, four of them a few lines of code and one a
change to the classifier prompt (section 3).  The code is sound where it was already sound: usage is
recorded on every paid call, the budget rule is as Roger decided, nothing edits the corpus or the queue,
every recorded figure I recomputed matches, and the suite is green (1,669 passed, 4 skipped).  What is
not ready is what the run would report: a quarter of the validation file was used to write the rules,
the note for Roger's own worst case never fires without an intended meaning, and the prompt calls a
circumstance a trait in one place and a non-trait in another.

## 2. Decision by decision

| # | Roger decided | built | departure |
|---|---|---|---|
| 1 | floor 1.5 | as decided | |
| 1b | rescue, "all three" routes | as decided | The decision text says route 1 rescues overclaiming; the rule as worded does not, and the code follows the rule.  Ran: overclaiming, corrigible and distractible are cut bare, read with a hint or from a curated source.  11 corpus labels are still cut |
| 2 | "treat them as targets" | with a departure | A rejected row is scored correct when it carries a `state`, `physical` or `membership` tag (must-fix 4).  His text: a label "counts as a miss when it is rejected" |
| 3 | memberships are traits; a role "rules out ... other things listed as roles" | with a departure | The rules and examples follow him, including "very high or very low statuses", ages that "rule out a profession" and "office or status: generally a role".  But the list of sense kinds makes `circumstance` and `status` non-trait kinds, against "circumstance: trait" and "class: trait" (must-fix 5).  No example of a very low status.  `relationship` is a kind he did not list; it follows from his earlier remark that unhappily-partnered is a valid trait |
| 4 | "B": any disagreement triggers a second opinion, both kept | with a departure | A row whose tags do not fit its verdict at all is rejected as unparseable and asked again, not kept and sent to Sonnet (must-fix 3) |
| 5 | "A": probe asks only whether the word is real | as decided | Probe v3 also counts regular derivations as real; an addition that route 1 of 1b needs |
| 6 | keep reasons, "cap at 30 words" | as decided | Asked for, not enforced or stored.  Ran: longest recorded reason is 26 words.  Every example now gives its reason first |
| 7 | "C" | as decided | The plan's fourth trigger (prior against model) is kept; he was not asked (QUESTIONS 12) |
| 8 | refuse, quote the decision, point to the replacement, copy history on override | with a departure | The replacement is recognised in 4 of the 18 superseded entries; the other 14 refusals say "no replacing label recorded" although the quoted text names one in other words (ran) |
| 9, A | typed budget is the cap; flag only over $20 | as decided | |
| 10 | merge after rubric v2 and the full run | not code | |
| 11, D | see below | with departures | |
| 12, C | one `state` tag, a separate queue, "a separate pass with a different rubric for plausibility", corpus labels assumed done | as decided | Two assumptions are not his words: which reading decides a word used both ways (QUESTIONS 11), and promotion from the states list (QUESTIONS 14).  Physical is "mostly or entirely physical" with other examples than his, since his are queue entries |
| 13 | "B": a separate yes or no field | as decided | |
| B | "Add a tag for this, we can build a queue for them" | with a departure | No tag string; `membership_kind` serves as the tag.  The queue is the `nationalities` holding list |

**Decision 11 and point D.**  The four cases were built from the coordinator's table, whose "Correct
or confirm" line is empty in the file, so Roger has not confirmed that restatement.  Against his own
words:

* "isn't that problematic unless its most obvious sense isn't a trait".  When a candidate has no
  intended meaning and the classifier passes it as a trait on a second sense, nothing is raised
  (must-fix 2).
* "or at least isn't the trait sense we're trying to describe".  The comparison answers in three
  grades and only `different` raises the flag; `related` means exactly "not the trait sense we're
  trying to describe" and raises none (section 6).
* "the one Haiku describes when asked for a definition".  The reading asks how a persona behaves,
  not what the word means, which turns a state or a status into behaviour (section 5).
* "tag these, collect them, and apply human judgement".  Tagged and collected; the table has an empty
  column and nothing stores his calls.

## 3. Must fix before the full run

1. **Report the figures separately for rows never seen in development.**
   [assistant_axis/gapgen/filter.py:730](../../assistant_axis/gapgen/filter.py) (`validation_figures`).
   Ran: 506 of the 1,810 validation rows were in the pilot or a smoke batch (206 of 659 existing
   labels, 265 of 1,000 random adjectives, all six rejects); 150 of them in the rubric v2 smoke
   batches.  The floor, the membership rule and the "relating to" rule were written from those rows.
   Failure: the run reports 94% on existing labels and nobody can say how much of it is memory of the
   sample.  Fix: mark each row with where it was seen, and give each figure for all rows and for the
   1,304 unseen ones.

2. **Roger's worst case raises no note.**
   [assistant_axis/gapgen/filter_rubric.py:436](../../assistant_axis/gapgen/filter_rubric.py).
   `nontrait_person_sense` requires the first sense to be a trait.  Ran: verdict `trait` with senses
   [high-born (status), high-minded (trait)], or [bodily cold, unfeeling], gives rank 2, no note,
   `polysemy` false.  Under rubric v1 rank 2 raised the flag.  `validation_figures` still counts rank 2
   as flagged, so the figure and the flag disagree.  None of the 30 recorded round 3 rows is such a
   case.  Fix: a fourth note, for a `trait` verdict whose first listed sense is not a trait.  It is
   derived, so no prompt change.

3. **A verdict with tags that do not fit is asked again, and the second answer replaces the first.**
   [filter_rubric.py:485](../../assistant_axis/gapgen/filter_rubric.py).  Ran on the recorded round 3
   batch: 3 of 30 rows came back `tagged` with `membership` (first-pass parse rate 0.90).  On the retry
   absentee changed from a membership of kind circumstance to a plain trait with a different reason,
   and bedded from a relationship membership to a trait.  Only the second answers are in
   `results.jsonl`.  Ran: `reject` with `physical`, the pilot's charcoal-grey, is rejected the same
   way.  At this rate the full run has about 150 such rows, and its hard gate on the parse rate depends
   on the retry changing the model's mind.  Fix: accept any row that has a verdict and at least one
   known tag, set `tag_disagreement`, and let the second opinion run, which is decision 4.  A `tagged`
   or `reject` row with no tag at all stays a failure.
   [test_gapgen_rubric_v2.py:173](../../assistant_axis/tests/test_gapgen_rubric_v2.py) asserts the
   present behaviour and must change with it.

4. **A rejected label is scored correct when it carries an accepted tag.**
   [filter.py:719](../../assistant_axis/gapgen/filter.py).  Ran: a label tagged `state` or `membership`
   and then rejected by the probe, and a `reject` carrying `physical`, all score `correct`.  Fix: a
   verdict of `reject` is a miss whatever the tags.

5. **The prompt contradicts decision 3 in its list of sense kinds.**  Prompt change, classifier
   version 4, one smoke batch (about $0.07).  Quoted in section 5, first item.  In the round 3 batch
   the case-4 note fired on 4 of 30 rows, and two of the four are corpus memberships (single, absentee)
   flagged because a sense was labelled `circumstance`.  At that rate Roger's judgement-call table has
   about 200 rows after the full run, many of them produced by the contradiction.

## 4. Should fix before M2

6. **Tests read two untracked files.**
   [test_gapgen_rubric_v2_round3.py:21-22, 323](../../assistant_axis/tests/test_gapgen_rubric_v2_round3.py)
   opens `decisions_m1.md` and `probe_you_are_x/results.jsonl`, both untracked.  On any other checkout
   the suite is red.  Commit both before the merge.

7. **A stop during the reading stage loses the readings.**
   [assistant_axis/gapgen/plain_reading.py:354-363](../../assistant_axis/gapgen/plain_reading.py).
   Readings reach the results only after every reading has returned.  Ran: cap tripping on the 80th
   of 120 readings; 80 charged and 80 responses kept, but no reading in any result, so
   `--reuse-readings` finds nothing.  The same in the filter.  Readings are the cheap stage; a stop
   during comparisons keeps its rows, and the states pass keeps its rows (ran).  Fix: store each
   reading as it returns.

8. **Nothing writes `corpus_regions.json`.**  Task 10 must produce it and the acceptance test skips
   while it is absent.  It can be derived from the run's results at no cost, and should carry
   `alignment_relevant` beside the region (decision 13).

9. **The version pins protect two hashes.**
   [test_gapgen_rubric_v2_round3.py:52](../../assistant_axis/tests/test_gapgen_rubric_v2_round3.py)
   fixes classifier version 1 and probe version 2.  A prompt and its pin changed together under the
   same version pass every test.  Fix: assert that every version and hash in a recorded `run.json` is
   in `HISTORY`.

10. **Corpus labels inside the prompt.**  The hygiene tests check the declared example words.  Ran, over
    every word of the prompt: the corpus labels promiscuous, easygoing and gentle appear as senses
    marked "(trait)", and the states example exasperated is a row of the validation file.  Replace
    them in the version 4 prompt.

11. **Smaller.**  `test_examples_agree_with_validator` does not check `enactable_in_text` or
    `confidence`, which the validator requires and no example shows; that is the defect behind the
    first pilot's 93.3%.  No test of a budget stop in either new runner.  The docstrings of
    [filter.py:3](../../assistant_axis/gapgen/filter.py) and
    [traithood_filter.py:12-14](../../data_analysis/gap_generation/traithood_filter.py) still say 2.0
    and 0.6.  The judgement-call table has nowhere to record Roger's calls.

## 5. Prompt findings

**Classifier, version 3.**

* *A circumstance is a trait and a non-trait.*  Memberships: "A membership is a trait ...
  circumstance (housing, money, work pattern), class".  Sense kinds: "status (a rank or standing given
  by others) ... circumstance (a situation someone is in)", and only a sense of kind `trait` counts as
  one.  The example debt-free is "a financial circumstance" with its sense marked "(trait)".
* *A bodily condition is a state and is physical.*  "whether the condition is of mood, body or
  situation" against "Physical ... (the body, looks, hair, build, health)" and the kind "bodily (a
  mostly physical feature or condition)".  The example hungry is "a bodily condition" marked
  "(state)".  Nothing says that a lasting feature is physical and a passing condition is a state.
* *An example against a rule.*  "awesome": "senses [very good in the speaker's eyes (trait)]" with
  verdict tagged `evaluative_only`, so a sense the verdict says is no trait is marked as one.
* *Two tests for the main reading.*  States: "takes the reading that is commoner in ordinary use".
  Senses: "the one a reader would take from the bare instruction".  Roger's is the second.
* *The schema cannot say which sense was judged.*  "If an intended sense is supplied with a candidate,
  judge that sense", but the gloss is "the first trait sense, or the sense the verdict is about", and
  no field names the sense.  M3 embeds the gloss and cannot tell which it has.
* *The definition is wide enough for most adjectives said of people.*  "standing fact about a person
  ... or a lasting fact about the person's life that colours how they talk".  Ran: random adjectives
  passed as traits 11 of 30 under the committed prompts (4 of 15, then 7 of 15), against 27 of 200
  under version 1.  Most are defensible (self-seeking, corrupt, dissenting, chivalric); bedded and
  venerable are not.
* *The verdict name invites the commonest error.*  Three rows in 30 answered `tagged` with
  `membership`, although the prompt says "membership goes only with trait".  A membership trait is, in
  plain English, tagged.
* *Examples use other names than the schema* ("senses", "equally obvious", "alignment") and none shows
  `enactable_in_text` or `confidence`.  No recorded row lacked them.
* *An empty threat.*  "shorter glosses are not accepted"; the validator accepts any length.

**Plain reading.**  "describe how this persona behaves" presupposes that the word is a way of
behaving.  The reading of empowered is "acts decisively and confidently"; rubric v1, shown the bare
word, read "a passing state: given power".

**Comparison, version 2.**  Reason comes first.  Two of its definitions claim the same ground:
"related: the core dispositions differ but are neighbors" and "different: ... a sense of the word that
the intended meaning does not use".  Engaging and economic are both.  The `related` example
(outspoken read as frank, intended as defiant) is the kind of near miss Roger turned down in
September, and the prompt teaches that it is the unflagged answer.

**Probe version 3, states queue version 2, states corpus version 1.**  Reason first in each.  The
three steps are Roger's, in his order.  The corpus prompt takes his default: "When the description
could be read either way, choose predisposition".  No contradiction found.

## 6. The held-out result

**My reading.**

1. **The flag sits on the wrong boundary.**  Roger's test has two outcomes: the plain reading is the
   trait we mean, or it is not.  The comparison has three and flags the far one.  Engaging and
   economic were answered `related`, which by the prompt's own definition is right.  The judge did
   what it was told.
2. **The development set could not show this, and the one change made to it moved the wrong way.**  I
   agree with the coordinator's suspicion, and the runs support it.  The 30 unrelated pairs were
   trivially different (29 of 30 in both versions).  The only pressure came from labels paired with
   their own description answering `related`, which was read as error.  Version 2 changed 5 of 60
   answers, every one from `related` to `same`, all in that group.  Some of those 11 were true
   findings about the corpus (honorable, organized, mystical), so the set was tuned toward silence.
3. **The reading prompt softens the hardest cases** (section 5).
4. **Six words decide little.**  The two models disagree on 8 of 60 rows, so one word either way is
   within their noise.

The six were not wholly held out: Appendix 2 read them with the same prompt before round 3 was
designed.  That cannot have flattered a result of 1 in 6.

**The three options, on the recorded development runs** (labels paired with their own description;
30 rows, so wide margins):

| rule | the six | corpus labels flagged | over 659 labels |
|---|---|---|---|
| flag `different` only (as built) | 1 of 6 | 1 of 30 (3%) | about 22 |
| flag `related` too, comparison v2 | 3 of 6 | 7 of 30 (23%) | about 154 |
| flag `related` too, comparison v1 | not run | 12 of 30 (40%) | about 264 |
| flag `related` too, Haiku v2 | not run | 6 of 30 (20%) | about 132 |

These are flags, not false alarms.  Nobody has marked which of the seven are real; grounded,
honorable and mystical look real to me, organized and circumspect do not.

* **Near-neighbour development set.**  The right set, since it holds the hard negatives.  But it is
  another round of tuning, the six are spent, and it needs its own held-out half.  The queue cannot
  supply one: of 129 turned-down entries 27 carry a description, and only the six's own decisions
  speak of the word's meaning (ran).
* **Accept 1 of 6.**  Accepts a check that misses the cases it was built for.

**Recommendation.**  Treat the two uses differently, and change no prompt.

* **Candidates that arrive with an intended meaning:** raise a note on `related` as well as
  `different`, under a second name so the two stay apart.  A miss is silent and a false alarm costs
  one glance at two sentences.  This is one function,
  [plain_reading.py:190](../../assistant_axis/gapgen/plain_reading.py), and no paid call.
* **The corpus comparison:** no flag.  Print every label with both texts, `different` first, then
  `related` by confidence, and let Roger read as far as he likes.
* **Ask Roger to mark the seven rows of Appendix 3** as fine or shifted.  If most are shifted,
  version 1 was the better prompt and the loosening should be undone.
* **Report the six as 1 of 6.**  The 3 of 6 above was chosen after seeing the answers and is not a
  held-out result.

If another round is wanted, the cleaner design asks Roger's question directly, yes or no with a
confidence, and orders the list by confidence.

## 7. Schema changes, and the plan tasks they touch

| field | change | plan text or task |
|---|---|---|
| `filter.rubric_version` | 3 on new rows | §6 example row |
| `filter.prompt_sha256` | four keys: classifier, probe, plain_reading, comparison | §6 |
| `filter.person_senses`, `trait_senses_equally_obvious` | new | §6; task 20 |
| `filter.senses` | meaning changed: senses a person can be only | §6; promotion notes |
| `filter.trait_sense_rank` | derived; no longer capped at 3; null without a trait sense | §6; §8 acceptance; task 24 |
| `filter.polysemy` | meaning changed: true when any note is present | §6; tasks 20, 21 |
| `filter.polysemy_notes` | new; a fourth value if must-fix 2 is taken, a fifth if `related` is noted | §6; tasks 20, 21 |
| `filter.plain_reading`, `filter.comparison` | new; null without an intended meaning | §6; task 20 (`ambiguous_label` can use the recorded reading); task 23 |
| `filter.alignment_relevant` | new | task 21 and the frozen `review_order(..., regions, ...)`; task 22 (`by_region`); task 10 (`corpus_regions.json`) |
| `filter.membership_kind`; tag `membership` | new; `demographic` and `transient_only` no longer emitted | §6 vocabularies |
| `filter.tag_disagreement` | new | none |
| `filter.region`, `gloss`, `enactable_in_text` | required again on `tagged` rows; the note in "M1 as built" that they may be null holds for version 1 rows only | §6 |
| `gloss` on a `state` row | meaning changed: describes the state, not a tendency | §1 (gloss form); task 13 (`candidate_text`); task 20 |
| `second_opinion` | gains `membership_kind`, `alignment_relevant`, `person_senses` | §6 |
| `holding` | adds `states`, `nationalities` | §6; task 23 (which rows `--unscored` takes); tasks 21, 24 |
| row field `states_pass` | new, absent until the pass runs | §6; tasks 20, 23: a states row is scored and promoted under `suggested_name` with `states_pass.gloss` |
| `freq.rescue`; floor 1.5; probe band 1.5 to 2.5 | new field; changed constants | §1, §7; both generator plans, which name 2.0 and 2.5 |
| `freq.define_probe` | gains `rubric_version`, `prompt_sha256` | §6 |
| `confirm_or_abort` | the flag no longer raises the cap | §7 common flags; tasks 18, 23; both generator plans ("over the budget needs the flag") |
| `gap_registry.py report` | leaves out held rows | §7; task 21 |
| seed queue | new entries carry `states_queue`; the counts are now 129 not adopted, 18 superseded, 37 exists | task 12; task 24's pilot set ("the 95 ... the 52") |
| `summary.json` | gains `validation_figures`, `v2_fields` | §6 report rows; task 10 |

Nothing was removed.

## 8. Claims checked

| claim | recomputed (ran) |
|---|---|
| development set, Sonnet v2 | expected same: 23 same, 6 related, 1 different; expected different: 29 different, 1 related |
| development set, Sonnet v1 | expected same: 18, 11, 1; expected different: 29, 1 |
| Haiku agrees with Sonnet on 52 of 60 | 52 |
| v1 to v2 | 5 rows changed, all `related` to `same`, all expected same; readings identical across the three runs |
| the six | disciplinary different; engaging, economic related; balanced, empowered, emotive same |
| seven corpus labels in Appendix 3 | the same seven |
| recorded hash matches the pin | every run, except the three withdrawn smoke batches (version 2, hash `ba7a4316`), which are marked; the two M1 smoke batches record none; the pilot's is inferred |
| round 3 classifier batch | 30 classified; first-pass parse 0.90, final 1.00; `person_senses` filled on 24, two or more senses on 5; `alignment_relevant` true on 5; `membership_kind` on 1; notes: 1 `two_trait_senses`, 4 `nontrait_person_sense`, 0 `overshadowed`; second opinion on 3; gloss, region on 24; every gloss 20 to 36 words |
| usage against responses | equal for all twelve `m2rubric` runs; $0.54 in total |
| $0.98 for the corpus comparison | arithmetic follows from the recorded rates |
| tests fail on the code they preceded | round 1: 42 fail, 1 passes; round 2: 36 fail, 2 pass; round 3: 29 fail, none passes.  The three that pass guard unchanged behaviour.  Many fail only because the module they import did not exist |
| plain-reading CLI tests, written after the code | both would fail if a dry run wrote or called, or if a reused reading made a call (read) |
| suite | 1,669 passed, 4 skipped |

**Corrections.**

* **Cost of the full run.**  The decisions file says about $1.85.  The tool's own dry run says $3.55
  for the filter (1,552 rows to the model, 330 probed), and the round 3 batch cost $0.0025 a row,
  which gives $3.80.  With the corpus comparison and the stability rerun, about $5 to $6.  The
  default cap of $5 on the filter is close; a stop now keeps what was paid for.
* **Haiku now caches the rubric.**  At about 4,280 tokens it is over the 4,096 minimum; the recorded
  calls show cache writes and a read.
* **Expected figures, from the recorded smoke batches.**  Existing labels: 63 of 67 correct (94%),
  less about 1.7 points for the floor.  Random adjectives: 22 of 83 (27%) over all batches, 11 of 30
  under the committed prompts.  Both targets are likely to be missed.

**Not verified.**  The token counts, which came from an endpoint I did not call.  That the six and
comparison v1 each ran once; one recorded run exists for each.  The figures of Appendix 2.  The four
commits between my last review (`ca80229`) and `5d6b0dd`, except where this diff touches them.

## 9. Questions that are Roger's to decide

1. **Should `related` raise a note?**  Options and figures in section 6.  I recommend yes for
   candidates with an intended meaning, and a sorted list with no flag for the corpus.
2. **The 15% target for random adjectives.**  He widened what counts as a trait and lowered the
   floor, and about a quarter to a third now pass.  Options: keep 15% and tighten the definition;
   or replace the share with his own marks on a sample of 50 passed words.  I recommend the second.
   The share measures how many dictionary adjectives describe people as much as it measures error.
3. **Confirm the four cases.**  His confirmation line under the coordinator's table is empty.  In
   particular, should a word passed as a trait on a second sense, with no intended meaning given, be
   flagged?  I recommend yes (must-fix 2).
4. **Which reading decides a word used both ways** (QUESTIONS 11): the commoner in ordinary use, or
   the reading of "You are X."?  I recommend the second, which is the test he gave under point D.
5. **Promotion from the states list** (QUESTIONS 14).  As built, an accepted states row enters the
   queue under the model's suggested name.  Options: that; or require him to confirm the name first.
   I recommend the second; choosing the name is his step b.
6. **The reading prompt.**  He wrote "when asked for a definition"; it asks for behaviour.  Options:
   keep it, since it is the prompt the measurement used; or ask what it means to say a person is X.
   I recommend keeping it for this run and trying the other on a fresh set if a further round is
   made.
7. **Marks on Appendix 3's seven rows**, fine or shifted.  Seven marks settle whether comparison v1
   or v2 is the better prompt.
