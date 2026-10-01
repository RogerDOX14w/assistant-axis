# M1 decisions: walk-through for Roger

Written 2026-09-29 (Fable).  Thirteen decisions stand between the M1 pilot and the full validation
run.  Each section gives the issue, why it matters, the evidence, the options, a recommendation, and
what you have said so far.  **Write your answer under "Your decision" in each section**, or answer in
chat by number; either way the answers are copied here, and this file becomes the specification the
rubric v2 change set is built from.

Sources: the implementer's [pilot_m1_readout.md](./pilot_m1_readout.md) and
[acceptance_platform.md](./acceptance_platform.md), the reviewer's [review_m1.md](./review_m1.md) and
[review_m1_fixes.md](./review_m1_fixes.md), the open entries in [QUESTIONS.md](./QUESTIONS.md), the
specification [coding_plan_platform.md](./coding_plan_platform.md), and a free frequency analysis run
for this document (no API calls).  Pilot outputs are in
[data/candidates/filter/m1_pilot/](../../data/candidates/filter/m1_pilot/).

This file sits on the M1 branch, uncommitted while you edit it.

## Summary

All thirteen are decided as of 2026-09-29.  Four small points remain for you to confirm; they are in
"Open points after your edits" near the end, and the word set for decision 11 is in the appendix.

| # | decision | decided | open point |
|---|---|---|---|
| 1 | The frequency floor | Floor 1.5.  Rescue rule 1b approved, all three routes | |
| 2 | Quality thresholds: gates or targets | Targets.  Some work to reach them is fine; not at the price of overfitting, above all on the small samples | |
| 3 | Memberships, and where a role begins | Memberships are traits.  A role is big enough to exclude other roles.  Very high or low class, ages that rule out a profession, and offices are roles.  Nationality and its kin are traits, but only a small sample is wanted | B |
| 4 | Verdict and tags disagree | B: disagreement triggers a second opinion; both kept | |
| 5 | The definition probe | A: rewrite it to ask only whether the word is real and definable | |
| 6 | Reasons in the output | Keep them, capped at 30 words | |
| 7 | Second-opinion rate | C: 10% random plus confidence under 0.75 plus decision 4's trigger; the generator rate is set after the full run | |
| 8 | Stems you already turned down | Refuse by default, quoting the earlier decision; superseded words point to their replacement; history copied on override | |
| 9 | A typed budget with the expensive-run flag | B: the typed budget is the cap | A |
| 10 | When to merge M1 | B: after rubric v2 and the full run | |
| 11 | Polysemy: another rubric pass | **Redesigned 2026-09-29.**  My "said of what" test was withdrawn.  Your four cases under point D replace it: nothing is rejected; an overshadowed sense is flagged; a non-trait sense a person can be is tagged and collected for your judgement | D, second reply |
| 12 | State words | One `state` tag.  It sends a candidate to a separate queue for extra work; it does not reject.  On an existing label the work is assumed done.  Physical means mostly or entirely physical | C |
| 13 | How alignment candidates are marked | B: a separate yes or no field | |

## Background in one page

The filter gives each candidate word one of three verdicts.  **trait**: a personality trait, which may
go forward.  **tagged**: a real word that belongs on a side list, with a tag saying which (`physical`,
`demographic`, `role_person`, `role_thing`, `transient_only`, `evaluative_only`).  **reject**: not a
trait (tags `relational_only`, `too_rare`, `not_a_word`).  A `state` tag can accompany a trait verdict.

Four stages, in order:

1. **Frequency floor** (free).  The word's Zipf value is looked up in the `wordfreq` list.  Zipf is a
   log scale: 3 is once per million words, 2 is once per ten million.  Below 2.0 the word is rejected
   unread.  A multiword label takes the lowest value among its content words.
2. **Classifier** (Haiku 4.5).  Verdict, tags, a list of senses, the rank of the trait sense among
   them, a region, a confidence, a short reason and a gloss.
3. **Definition probe** (Haiku 4.5), only for words between 2.0 and 2.5.  Meant to check the model
   knows the word.
4. **Second opinion** (Sonnet 4.6) on 10% of rows at random, on rows with confidence under 0.6, and
   on rows where the classifier disagrees with a prior.

The pilot ran 367 words in five groups whose right answers are known:

| group | words | trait | tagged | reject | of the rejects, cut by the floor |
|---|---|---|---|---|---|
| existing corpus labels | 132 | 113 | 8 | 11 | 7 |
| the six September rejects | 6 | 4 | 1 | 1 | 0 |
| physical queue candidates | 6 | 2 | 4 | 0 | 0 |
| queue labels not adopted | 23 | 8 | 2 | 13 | 4 |
| random dictionary adjectives | 200 | 27 | 29 | 144 | 74 |

### Where the existing-label misses came from

You asked which tests contributed most to the 14.4% of existing labels that did not come back as
traits.  There are 19 misses among 132:

| cause | words | points of the 14.4 | labels |
|---|---|---|---|
| Frequency floor | 7 | 5.3 | [clannish](../../data/traits/instructions/clannish.json), [collectivistic](../../data/traits/instructions/collectivistic.json), [confabulatory](../../data/traits/instructions/confabulatory.json), [distractible](../../data/traits/instructions/distractible.json), [techno-hierophantic](../../data/traits/instructions/techno_hierophantic.json), [tunnel-visioned](../../data/traits/instructions/tunnel_visioned.json), [unschooled](../../data/traits/instructions/unschooled.json) |
| Tagged as a membership or role | 7 | 5.3 | [gay](../../data/traits/instructions/gay.json), [new money](../../data/traits/instructions/new_money.json), [many siblings](../../data/traits/instructions/many_siblings.json), [financially secure](../../data/traits/instructions/financially_secure.json), [unhappily-partnered](../../data/traits/instructions/unhappily_partnered.json), [cat-person](../../data/traits/instructions/cat_person.json) as `demographic`; [renter](../../data/traits/instructions/renter.json) as `role_person` |
| Rejected as a "relating to" adjective | 4 | 3.0 | [concrete](../../data/traits/instructions/concrete.json), [interdisciplinary](../../data/traits/instructions/interdisciplinary.json), [rhetorical](../../data/traits/instructions/rhetorical.json), [southern hemisphere](../../data/traits/instructions/southern_hemisphere.json) |
| Tagged as a state | 1 | 0.8 | [despairing](../../data/traits/instructions/despairing.json) |

So two rules, not the model's judgement, account for 14 of the 19.  What the pilot sample would score
under your rulings so far (updated 2026-09-29 after decisions 1 and 12), each line adding to the one
above:

| change | counted correct, of 132 | share | status |
|---|---|---|---|
| as piloted | 113 | 85.6% | |
| a short-term state tag on an existing label is not a miss: despairing | 114 | 86.4% | decided (12) |
| floor at 1.5, if the model passes the three it then sees: clannish, tunnel-visioned, unschooled | 117 | 88.6% | decided (1) |
| memberships count as traits | 124 | 93.9% | your stated view; ruling on kinds pending (3) |
| the three genuine "relating to" mistakes fixed: concrete, interdisciplinary, rhetorical | 127 | 96.2% | depends on the rubric v2 wording |

The 95% target was unreachable under the rules as written.  Under the revised ones it is reachable,
but only if the rubric stops rejecting words such as concrete and rhetorical; without that the sample
stands at 93.9%.  Five labels in the sample stay out of reach: collectivistic (1.47) and distractible
(1.29), which a floor of 1.5 still cuts; confabulatory and techno-hierophantic, which the word list
does not contain; and southern hemisphere.  The rescue rule of sub-question 1b could recover some of
the first four.

---

## 1. The frequency floor

**Issue.**  The floor at 2.0 rejects words unread.  It exists to throw out dictionary junk for free.  It
also throws out 34 of our own 659 labels, and the alignment vocabulary this project most wants.

**Evidence.**  From the validation file, all 659 corpus labels and 1,000 random dictionary adjectives:

| floor | corpus labels cut | random adjectives cut for free | queue labels not adopted, cut |
|---|---|---|---|
| 2.5 | 91 (13.8%) | 464 (46.4%) | 32 of 117 |
| **2.0, as piloted** | **34 (5.2%)** | **354 (35.4%)** | **22** |
| 1.75 | 23 (3.5%) | 303 (30.3%) | 17 |
| 1.5 | 13 (2.0%) | 270 (27.0%) | 13 |
| 1.25 | 8 (1.2%) | 228 (22.8%) | 9 |
| 1.0, which is the same as "in the word list at all" | 5 (0.8%) | 192 (19.2%) | 9 |

Four facts behind the table:

* **The word list stops at about 1.0.**  The smallest value it returns is 1.02.  A word is either at
  least that, or it is absent and scores 0.  So no floor between 0 and 1.0 means anything, and a floor
  of 1.0 means "the word is in the list".
* **distractible is the standard spelling and scores 1.29.**  The variant distractable is absent
  from the list.  The word is familiar but rare in the kind of text the list was built from; it lives
  in psychology writing.  Several sound labels are in the same position.
* **The 34 corpus labels below 2.0**, lowest first.  Absent from the list: cliqueish, confabulatory,
  techno-hierophantic, uncalculating, uninquisitive.  From 1.1 to 1.5: incrementalist, ecocentric,
  satisficing, distractible, extrinsically motivated, strong-stomached, collectivistic, exclusivist.
  From 1.5 to 2.0: antifeminist, deconstructionist, unchallenging, clannish, unadventurous, incurious,
  unselfconscious, unreflective, undependable, abstemious, tunnel-visioned, unschooled, regionalist,
  teetotaler, deontological, cultural relativist, relativist, consequentialist, anthropocentric,
  guileless, aesthete.
* **Alignment words fare badly**: sandbagging 1.94, overclaiming absent, corrigible absent,
  situationally aware 1.72.  Sandbagging and overclaiming are among the rubric's own positive examples.

Frequency separates poorly in the band from 1.0 to 2.0.  The 162 random adjectives there are mostly
technical (adaxial, benzoic, bicipital, diamagnetic) with real traits among them (bootlicking,
contumacious, dilatory, aboveboard).  The corpus labels in the same band are sound traits.  Only
reading the word tells them apart.

**Cost of reading more words.**  About $0.0011 per word.  Against a floor of 2.0, a floor of 1.0 sends
162 more words per 1,000 dictionary candidates to the model, about $0.18 per 1,000.  The money is
small.  The real cost of a lower floor is junk the model wrongly passes, which lands on your review
list.  That rate is not yet measured for this band.

**Options.**

* **A.** Keep 2.0 and accept losing 5% of labels like ours.
* **B.** Lower to 1.5.  Loses 2.0% of our labels; still cuts 27% of dictionary junk for free.
* **C.** Lower to 1.0, so the floor only removes words absent from the list.  Loses 0.8% of our labels;
  cuts 19% for free.
* **D.** Make the floor depend on the source (the reviewer's proposal): on for dictionary walks, and
  replaced by the probe for curated sources and for any candidate that arrives with a gloss hint.
* **E.** Measure before fixing it: run the full validation with the floor at 1.0, record verdicts by
  frequency band, and set the production floor from the junk rate measured in each band.  About 250
  extra rows in the full run, about $0.30.

**Unlisted words** need a rule under every option, since no floor rescues them.  Proposed: an unlisted
word goes to the probe, not the bin, when it is formed from a listed word by a negating prefix (un-,
in-, non-) or is a hyphenated compound whose parts are all listed, or when it comes with a gloss hint
or from a curated source.  That rescues uncalculating, uninquisitive and overclaiming.  It does not
rescue confabulatory, cliqueish, corrigible or techno-hierophantic unless they arrive with a hint.

**Recommendation.**  C and E together, with the unlisted-word rule.  It costs cents, it answers "how
low" with data instead of guesswork, and D can still be layered on afterwards if the measured junk
rate in the low band is high for dictionary walks.

**Your position so far** (chat, 2026-09-29): some of the seven are genuinely obscure, distractible is
not; lower the floor a little.

> **Your decision (chat, 2026-09-29): set the Zipf floor to 1.5.**  This is option B. Confirmed.

**What 1.5 does**, so you can confirm it is what you want:

* It cuts 13 of our 659 labels (2.0%), against 34 at 2.0, and still removes 270 of 1,000 random
  adjectives for free.
* **distractible is still cut.**  It scores 1.29.  The eight listed labels below 1.5 are incrementalist
  1.11, ecocentric 1.22, satisficing 1.24, distractible 1.29, extrinsically motivated 1.38,
  strong-stomached 1.44, collectivistic 1.47 and exclusivist 1.48.  The other five cut are the
  unlisted ones: cliqueish, confabulatory, techno-hierophantic, uncalculating, uninquisitive.
* Of the alignment words, sandbagging (1.94) and situationally aware (1.72) now pass the floor.
  overclaiming and corrigible are unlisted and are still cut.
* The definition probe's band becomes 1.5 to 2.5.
* With this floor the ceiling on the existing-label figure is 98.0% for the whole corpus.

**Sub-question 1b, still open: a rescue rule for words below the floor.**  Should a word below 1.5,
listed or not, go to the probe instead of the bin when one of these holds?

1. It is formed from a word at or above the floor by a negating prefix (un-, in-, non-), or is a
   hyphenated compound whose parts all pass.  Rescues uncalculating, uninquisitive, overclaiming.
   It does not rescue strong-stomached, since stomached is 1.44.
2. It arrives with a gloss hint, that is, the generator says which sense it means.
3. It comes from a curated source, such as a psychology inventory, and not from a dictionary walk.
   Rescues distractible, satisficing and collectivistic when a census or inventory proposes them.

Recommendation: all three.  The floor is there to stop dictionary junk, and none of these routes
carries dictionary junk.  Each rescued word costs about a fifth of a cent.

> **Your decision on 1b:** Approved, all three



## 2. Quality thresholds: gates or recorded targets

**Issue.**  The plan's M1 quality figures are hard assertions in the acceptance test: at least 95% of
existing labels come back as traits, at least 4 of the 6 rejects are caught, at most 15% of random
adjectives pass.  If one fails after the full run, the milestone's test list cannot go green.

**Evidence.**  Under the rules as piloted the first figure is capped at 94.8% by the floor alone.  A
review amendment you agreed on 2026-09-24 already makes the M2 and M3 quality figures "report and
decide" and keeps only mechanical checks as gates (parse rate, cost caps, usage recorded, nothing edits
the corpus).  It names M2 and M3 only.  The random-adjective figure is 14.5% by the classifier's own
verdict, so it is met narrowly and could tip either way on the full run.

**Options.**

* **A.** Extend the amendment to M1: the figures are recorded and put in front of you; the mechanical
  checks stay hard.
* **B.** Keep them as gates and change floor and rubric until they pass.

**Recommendation.**  A.  A gate invites tuning the rubric to the test set.  Keep 95%, 4 of 6 and 15% as
the figures the report is measured against.  On your question: 95% was too ambitious under the
original rules and is a fair target under the revised ones.

**How an existing label is scored**, following your ruling in decision 12 (chat, 2026-09-29).  An
existing label counts as correct when the filter returns any of:

* verdict trait;
* a short-term state tag, since those are handled separately and the tag does not mean the label
  should be rejected;
* a physical tag, on the same reasoning, which the plan already allowed;
* a membership tag, if decision 3 goes as you indicated.

It counts as a miss when it is rejected, cut by the floor, or sent to the roles list.

> **Your decision (gates or targets):** Let's treat them as targets. I'm willing to work a little to try to get them to pass, but if we try too hard there's a risk of just overfitting (especially the ones with small sample size), or blocking ourself with an overambitious gate.

## 3. Memberships, and where a role begins

**Issue.**  The rubric sends "demographic or life-status memberships (nationality, ethnicity, age
group, marital status)" to a side list, and sends any person-kind word to the roles list.  The corpus
has since admitted memberships on purpose.  Seven pilot labels were diverted for this reason.

**Evidence.**  Tagged `demographic`: gay, new money, many siblings, financially secure,
unhappily-partnered, cat-person.  Tagged `role_person`: renter.  Among random adjectives the same rule
caught Cameroonian, Cockney, elected and fourth-year.  The rubric's own examples are Norwegian and
widowed for `demographic`, plumber for `role_person`.

**Your position so far** (chat, 2026-09-29): most of those are valid traits.  Financially secure and
renter are facts about a person, not roles.  A role is all-encompassing, on the order of a profession.
The role and trait distinction is fuzzy.

**Options.**

* **A.** Every membership is a trait.  The tag is kept for information and diverts nothing.
* **B.** Leave the rubric alone and count a `demographic` tag as correct for existing labels.  This was
  my earlier recommendation.  It does not fit your view, since the words would still be diverted.
* **C.** Split by kind.  Circumstance (renter, financially secure), class (new money), family (many
  siblings), affinity (cat-person), relationship (unhappily-partnered) and orientation (gay) are traits
  with an informational `membership` tag.  Nationality, ethnicity, language group and age group stay
  on the demographic side list.

**What needs your ruling under A or C**: which kinds count.

| kind | examples | in the corpus today |
|---|---|---|
| circumstance | renter, financially secure | yes |
| class | new money, old money | yes |
| family | many siblings | yes |
| affinity | cat-person | yes |
| relationship | unhappily-partnered, single; the rubric's example is widowed | yes |
| orientation and gender expression | gay, straight, feminine, masculine | yes, tagged sensitive |
| geography | southern hemisphere | yes |
| nationality, ethnicity, language group | Norwegian, Cameroonian, Cockney | not that I found |
| age group, school year | fourth-year | not that I found |
| office or status | elected | not that I found |

**Proposed wording for the role rule.**  "A role is an identity that organizes the whole persona, on
the scale of a profession or calling: plumber, civil servant, monk.  A fact about a person's
circumstances, possessions, family or tastes is not a role."

**Recommendation.**  C, with the role wording above.  The reason to keep nationality and its kin on a
side list is practical: a dictionary walk yields hundreds of them, they are a finite known set, and
they are better decided once as a set than word by word on your review list.

> **Your decision:** This is a fuzzy boundary: some words are duplicated between both lists, often under slightly different senses. In general, existing roles are either a profession, or something that rules out having a profession (like void or infant). In theory, a role is something "big enough" that it rules out (at least the large majority of) other things listed as roles: the idea is that you can only have one role, and knowing that role lells you (at least a guess at) a lot about a person. Traits are less than that, things that are more freely intersectional: the theory is that you can have many traits, they can be combined nearly-arbitrarily. Sadly this is not a hard-and-fast boundary. So: circumstance: trait; class: trait, except for very high or very low statuses that rule out most professions; family: trait; affinity: trait; orientation and gender expression: trait; geography: trait; nationality, ethnicity, language group: trait (but I don't want a vast number of these, a small sample is enough); age group, school year: trait unless if it's young or old enough to rule out a profession, and I think we already have those; office or status: generally a role

## 4. When the verdict and the tags disagree

**Issue.**  In 11 of 282 rows (3.9%) the verdict contradicts the row's own tags, and the side lists
are routed by verdict plus tag, so such a row goes to the wrong place.

**Evidence.**  `reject` with a side-list tag: twin, charcoal-grey, brilliant, defiled, destroyed.
`tagged` with only `state`: despairing, stable, captivated, relieved.  `trait` with `role_person`:
homebody.  Charcoal-grey never reached the physical list.  Three further rows give a reason that
contradicts the verdict and carry no tag at all: disciplinary, modern, constructivist.

**Options.**

* **A.** Derive the verdict from the tags in code after parsing.  The implementer's proposal, and my
  first recommendation, which I withdrew.  It repairs the 11 rows.  It does nothing for the three
  that carry no tag, it would move homebody to the roles list on the strength of a tag against the
  verdict, and it has no rule for a row with both a side-list tag and a reject tag.
* **B.** Treat any disagreement as a trigger for the second opinion, record both, and add a rubric
  line that the reason must address the sense being judged.  The reviewer's proposal.
* **C.** Both: B for routing the doubtful rows to Sonnet, and A only for the cases with one
  unambiguous tag.

**Recommendation.**  B.  About 4% more second opinions, under half a cent per hundred rows.

> **Your decision:** B

## 5. The definition probe

**Issue.**  The probe should ask whether the model knows the word.  It asks about trait labels, so it
judges trait-hood a second time and rejects real words for not being traits.

**Evidence.**  17 of 35 probed words came back "not known", with reasons such as "a real English word,
but a botanical term, not a personality trait" (tuberous, saute, repayable, psychogenic).  It changed
four final verdicts: nippy and rending from trait to reject, becalmed and purple-veined from tagged to
reject.  All 17 were random adjectives, so no corpus label was lost this time.  Probe parse failures
were also never reported; that part is fixed.

**Options.**

* **A.** Rewrite it to ask only whether the word is real and definable, and say that trait-hood is
  judged elsewhere.
* **B.** Drop the probe and let the classifier's `too_rare` and `not_a_word` tags do the work.

**Recommendation.**  A.  Decision 1 sends more rare words to the model, which is when a cheap check
that the model is not inventing a meaning is worth having.  The probe band moves with the floor: with
the floor decided at 1.5 it becomes 1.5 to 2.5, plus any word rescued under sub-question 1b.

> **Your decision:** A

## 6. Reasons in the output

**Issue.**  The plan expected reasons to be about 60% of the cost and asked whether to keep them.

**Evidence.**  They are 20.2% of the classifier's output characters.  Dropping them saves about $2 per
10,000 candidates.  The project's judging rule is reason before verdict.  The reasons are what exposed
the three contradictory rows in decision 4.

**Recommendation.**  Keep them, capped at 20 words as now.  One related defect goes into rubric v2
whatever you decide: the rubric's twelve negative examples show a verdict with no reason, which breaks
the reason-first rule.  A test now marks this as an expected failure until the examples are fixed.

> **Your decision:** Accpet recommendation, cap at 30 words.

## 7. Second-opinion rate

**Issue.**  How often Sonnet checks Haiku.

**Evidence.**  32 rows had a second opinion, 4 disagreed: disciplinary (Haiku trait, Sonnet reject),
concrete (Haiku reject, Sonnet trait), unplugged (Haiku trait, Sonnet reject), full-term (Haiku
reject, Sonnet demographic).  Sonnet's reading was the more plausible in at least two.  Sonnet was 25%
of the pilot's cost.  Eight of the ten least confident rows had no second opinion, because the trigger
is confidence under 0.6 and they sat between 0.62 and 0.72.

**Options.**

* **A.** As piloted: 10% random, confidence under 0.6.
* **B.** 10% random, confidence under 0.75, plus the disagreement trigger of decision 4.
* **C.** B for the validation run, then 5% random for generator runs if the full run shows Sonnet
  rarely overturns Haiku.

**Recommendation.**  C.  Nobody has evidence yet for the 5% figure, so it is decided after the full
run, not now.

> **Your decision:** C

## 8. Stems you already turned down

**In one sentence.**  A word you decided against in September can be proposed again by a generator,
pass the filter, and be put back on your to-do list as if it were new, with no sign that you have
already ruled on it.

### The terms

* **Stem.**  The file-name form of a label: lower case, with spaces and hyphens turned into
  underscores.  The label "tunnel-visioned" has the stem `tunnel_visioned`, and its corpus file is
  [tunnel_visioned.json](../../data/traits/instructions/tunnel_visioned.json).  Two labels with the
  same stem are the same entity as far as the tooling is concerned, so the stem is what gets checked
  for clashes.
* **Seed queue.**  The file [data/seed_queue.json](../../data/seed_queue.json): the to-do list of the
  seeding work you have been doing since chunk 0.  It has 991 entries, one per trait or role that was
  ever proposed for the corpus, each with a status.  The seeding tool
  [seed_entities.py](../../data_analysis/seed_entities.py) reads and updates it.
* **Statuses in the queue.**  An entry being worked on moves through `candidate` (proposed, no final
  description), `ready` (description written and reviewed), `seeded` (file written), `generated`
  (instructions and questions generated), `checked` (antonym check run), and ends at `paired` or
  `done`.  Other statuses are parked and the tooling leaves them alone:

  | status | entries | meaning |
  |---|---|---|
  | `paired`, `done` | 425 | in the corpus |
  | `candidate` | 245 | waiting their turn: chunks 4, 5 and 6 |
  | `backlog`, `tbd` | 137 | put off |
  | `exists` | 37 | a file already existed when the queue was built |
  | **`not_adopted`** | **129** | **you decided against it** |
  | **`superseded`** | **18** | **replaced by a better label for the same idea** |

* **`not_adopted`.**  An entry you turned down.  It keeps your reason in its `decision` field.  For
  example aloof: "DELETED 2026-09-17 (Roger, item 14): flirty made a singleton; aloof overlaps
  reserved and detached."  The six September rejects are of this kind, as are the words deleted
  during the pairing review.
* **`superseded`.**  An entry dropped because another label took its place.  For example extreme:
  "superseded by extremist", and incremental, replaced by incrementalist.
* **Registry.**  Not the seed queue.  It is the new platform's own list, holding every word a
  generator proposes, with the filter's verdict and later a novelty score.  It will hold thousands of
  rows, most of them rejected.
* **`promote`.**  The one command that carries a word from the registry into the seed queue, a
  subcommand of [gap_registry.py](../../data_analysis/gap_generation/gap_registry.py).  Nothing is promoted automatically.  It is run on chosen words after you
  have looked at the review list.  It adds a new queue entry with status `candidate`.  It never writes
  a trait file; that stays with the seeding tool and your description review.
* **Deviations.**  In its report the implementer listed fourteen places where what it built differs
  from the plan, each with its reason.  That list is headed "deviations from the plan".

### The issue

Before adding a word to the queue, `promote` checks that its stem is not already taken.  "Taken" is
worked out by a function it borrows from the seeding tool, and that function counts corpus files and
queue entries, **except entries that are `not_adopted` or `superseded`**.  Those it treats as free
names.

So if a generator proposes aloof, and the filter passes it, and it is promoted, the queue gains a
second aloof entry with status `candidate`, beside the old one that carries your reason for deleting
it.  The new entry shows none of that history.  You could end up writing a description for, and
reviewing, a word you have already ruled out.

### Why the code does this

It follows the plan to the letter.  The plan says `promote` "refuses corpus and queue collisions" and
names the seeding tool's function as the check to use.  In the seeding tool the exception is
sensible: when you rename a trait by hand, a name freed by an earlier deletion should be available.
The plan did not consider that generators will propose turned-down words again, and they will, since
those words are plausible trait words; that is why they were proposed the first time.

So I was unfair in the first version of this section when I wrote that the implementer "did not list
it among its deviations".  It is not a deviation.  It is a gap in the plan, which the reviewer found.
A test written by the implementer asserts the behaviour on purpose, with the comment "a not_adopted
stem may come back".

### Evidence

| | count |
|---|---|
| `not_adopted` or `superseded` entries in the queue | 147 |
| of those, stems that now have a corpus file, so `promote` refuses them anyway | 10 |
| **entries whose stem could come back through `promote` today** | **137** |
| of the 137, traits | 126 |
| of the 137, roles | 11 |

The 137 entries cover 136 distinct stems, since intemperate was turned down twice.

There is a second line of defence planned, but it is partial.  The novelty scorer in milestone M3
should mark a turned-down word as already covered when you rejected it for overlapping an existing
trait, as with aloof.  It will not catch a word you rejected for another reason, such as the six
rejected for ambiguity.

### Options

* **A.** Refuse by default.  The refusal message quotes your earlier decision, for example "turned
  down 2026-09-17: aloof overlaps reserved and detached".  A flag overrides it for words you want
  back.
* **B.** Allow the word through, and copy the old decision text into the new entry's notes, so the
  history travels with it and you see it when you come to write the description.
* **C.** Treat the two statuses differently: refuse `not_adopted` as in A; for `superseded`, refuse
  and point to the label that replaced it.

### Recommendation

A, with C's pointer for superseded words, and B's copying whenever the override flag is used.  You
have ruled on these words once; the tool should make you choose to reopen one, not reopen it
silently.  The seeding tool's own behaviour on renames stays as it is.

> **Your decision:** As you recommend

## 9. What a typed budget means with the expensive-run flag

**Issue.**  Every command takes a budget in dollars.  If the estimate exceeds it, the run is refused
unless `--confirm-expensive` is passed.  With that flag the cap becomes 1.5 times the estimate, which
can be above the figure you typed.

**Evidence.**  A $5 budget with a $6 estimate and the flag gives a cap of $9.  The part above $20 is
already fixed: no cap passes $20 without a named confirmer.

**Options.**

* **A.** Keep it: the flag replaces the typed budget with 1.5 times the estimate.
* **B.** The flag permits the run; the typed budget stays the cap.  To spend more, type more.

**Recommendation.**  B.  A number typed as a cap should be the cap.

> **Your decision:** As you recommend: having a budget, and a flag to increase it, sounds like unneeded bells and whistles. (If we found we really needed it, it wouldn't be hard to add back.)

## 10. When to merge M1

**Issue.**  The branch is fifteen commits ahead of 62633d8.  The re-review says it is fit to merge.
The plan lets the generator workstreams start their M1-only tasks once M1 is merged.

**Options.**

* **A.** Merge now.  Generators can start.  Rubric v2 and the full run follow as a second merge.
* **B.** Merge after rubric v2 and the full run, so M1 lands whole with its acceptance numbers.

**Recommendation.**  I said A in chat.  Your feedback changes that: decisions 1, 3, 11 and 12 alter
what the filter accepts, and generators written against rubric v1 would harvest under a floor and
rules that are about to change.  So B, unless you want the generator plans' coding started in
parallel, in which case A with the generators told not to run a harvest until rubric v2 lands.

> **Your decision:** B

## 11. Polysemy: another pass at the rubric

**Issue.**  The six words you turned down in September were rejected because their main meaning is not
a persona trait.  The filter should flag such words.  It caught three of six.

**Your position so far** (chat, 2026-09-29): the rubric may need enhancing to cover polysemous words
whose primary meaning is not a persona trait.  The corpus has not been entirely consistent; it has
some, and you avoid them where possible.  Try another pass.

**Evidence.**  Rubric v1 asks for a list of senses and the rank of the trait sense in that list, and
flags polysemy when the rank is 2 or more.  Caught: disciplinary, economic, empowered, all rank 3.
Missed: engaging, balanced, emotive, all judged rank 1, so the model took the trait sense as primary.
In the earlier ten-word smoke run balanced came back rank 2 and empowered rank 1: these words sit on
the boundary and flip between runs.  Across groups the flag fired on 15% of existing labels and 81%
of random adjectives.

The implementer and the reviewer both advised leaving the wording alone, because with six test words
any example resembling them teaches to the test.  That risk is real, and the proposal below is built
to avoid it.

**Proposal.**

1. **A "said of what" test, replacing sense rank as the trigger.**  Sense rank asks the model to order
   dictionary senses, which it does unreliably.  The question that matches your reason for rejecting
   these words is different: met without context, what does the word most often describe?  A new field
   `primary_use` takes one of `person_character`, `person_other` (a person's state, body or
   circumstances), or `non_person` (a thing, text, event, policy or situation).  All six fall outside
   `person_character` on a plain reading: engaging is said of a talk, balanced of a diet or a report,
   emotive of an issue, economic of policy, disciplinary of a hearing, empowered of a state someone is
   put in.  The flag fires when `primary_use` is not `person_character`.  The sense list stays, for the
   gloss.
2. **A fresh word set, so the six are never tuned on.**  About 40 polysemous words that are not the
   six, in two halves.  The development half is used to adjust wording.  The held-out half is scored
   once, at the end, together with the six.  Sources: `not_adopted` queue entries whose decision text
   cites a competing meaning, and a list I draft for you to vet.  Candidates for that list: critical,
   sensitive, objective, academic, clinical, mechanical, graphic, dynamic, measured, liberal, dense,
   sharp, magnetic, colorful, deep, technical, economical, formal, progressive, positive.
3. **A guard against over-flagging.**  The existing labels are rerun with the new field, and every
   label that gets flagged is listed for you.  Since the corpus does hold some polysemous labels,
   those flags are information about the corpus, not errors of the filter.

**What a flag does.**  Options: (a) flag only, and show `primary_use` beside the word on your review
list; (b) flag and move the word to the end of the review list; (c) reject unless the candidate came
with a gloss hint naming the trait sense.  I recommend (b): a flagged word is not thrown away, since
some good traits are secondary senses, but it does not crowd the top of the list.

**Cost.**  Each rubric iteration on 50 words is two calls, a few cents.  The whole pass should stay
under $1.

> **Your decision:** Approved

## 12. State words

**Issue.**  A word such as despairing can name a passing state or a standing proneness to it.  The plan
rules that state words are in scope as dispositions: verdict trait, tag `state`, and a gloss that says
"a general tendency to".  In the pilot the model did not apply that consistently.

**Evidence.**  Among existing labels, state words mostly came back trait with the `state` tag (8.3% of
rows carry the tag).  despairing came back `tagged` with `state`, which routes it off the trait list.
So did stable, captivated and relieved in other groups.

**Your position so far** (chat, 2026-09-29): tagging despairing as a passing state is fair.  One can be
prone to a passing state, but that is separate and probably worth a tag.

**What I need from you.**  I read that two ways:

* **A. One tag, as the plan has it.**  A state word is a trait when it can name a tendency.  It gets
  `state`, and the gloss is written as the tendency.  despairing is then a trait.
* **B. Two tags.**  `state` marks the passing condition and is not a trait.  `state_prone` marks the
  standing proneness and is a trait.  A word that can be read both ways gets the verdict of its
  primary reading, and the gloss says which.  despairing as piloted would then be right.

Under B the corpus's own state-like labels would need their descriptions checked for which reading
they take, since the filter would start flagging them.

**Recommendation.**  None until I know which you meant.  If B, I suggest the descriptions are the
deciding evidence: a label whose description is written as a tendency is `state_prone`.

> **Your decision (chat, 2026-09-29):** "If it's a short-term state, it needs tagging, as we'll handle
> it separately (ditto for physical traits).  But if an existing trait has the short-term trait tag,
> that doesn't mean it should be rejected, so it doesn't count against the 95% criterion."

**My reading of it, for you to correct.**  This is option B in substance:

1. **A short-term state is tagged and goes to its own holding list**, handled separately, as the
   physical attributes are.  It is not rejected and not passed as an ordinary trait.  Tag name
   proposed: `short_term_state`.  It replaces rubric v1's `transient_only`, and v1's `state`
   tag when that was used for a passing condition.
2. **Proneness to a state is a trait**, with an informational tag that diverts nothing.  Tag name
   proposed: `state_prone`.  This is your earlier remark that proneness "is separate, and probably
   worth a tag".  The gloss is written as the tendency.
3. **Scoring.**  An existing corpus label that comes back with the short-term state tag counts as
   correct for the 95% figure.  The same holds for a physical tag.  Section 2 now states this.
4. **Nothing in the corpus is touched.**  A tag from the filter on an existing label is information
   for you, not an instruction to remove the label.  The full run will list every existing label
   that receives either state tag, so you can see which of our labels the filter reads as states.

**Two points I am inferring, not quoting**, so please confirm or correct:

* That a word readable both ways, such as despairing, takes the tag of its primary reading, and the
  gloss says which reading was taken.
* That you want the states holding list kept apart from the physical one, since they will be
  handled by different later work.

> **Your corrections, if any:** I wasn't suggesting a second tag, I was saying the state tag was useful, but not inherently disqualifying, it merely means there is some extra work to do: a) figure out if a habitual predisposition to state is plausible, b) whether the name of the state is still a good name for the predisposition (or if not, change the stem to that), and b) write the description to describe the habitual predisposition. I don't think that process requires a separate tag, just a separate queue (but if adding a secind tag would help with administering the process, I'm not averse to it). If a trait already in the corpus gets this tag during us checking the corpus, the default assumption (which it might be worth having a process to check) is that this has already been done.

This slightly resembles the situation for physical tagged traits, which also have their own separate queue. However, the current corpus shouldn't have any physical trait in it currently. (Note that some age/gender traits also have physical components, but since they also have a strong clear mental component, they've not treated as physical: physical mans "mostly or entirely physical": e.g. blonde, dark-skinned.)

## 13. How alignment candidates are marked

**Issue.**  The plan shows you alignment-related survivors first on the review list.  It finds them by
the `region` field, one choice among nine.

**Evidence.**  Of 125 classified existing labels, the region `alignment_ai_agent` was chosen once.  The
corpus's alignment traits in the sample were mostly labelled `moral_stance` or `cognitive_epistemic`.
Both labels are defensible for those words, so the field is not wrong, but ordering by it would
under-select badly.

**Options.**

* **A.** Leave it, and accept that "alignment first" will find few.
* **B.** Add a separate yes or no field, `alignment_relevant`, asked independently of region.

**Recommendation.**  B.  It belongs in the rubric v2 change set since it changes the output rows.

> **Your decision:** B

---

## Open points after your edits (2026-09-29)

Four points to confirm, then how I intend to turn three of your rulings into rules a model can
apply.  None of this reopens a decision.

### A. Decision 9: does the expensive-run flag go altogether?

You wrote that a budget plus a flag to raise it is unneeded.  My reading, which goes one step further
than option B as I worded it:

* An estimate at or under the typed budget runs, and the typed budget is the cap.
* An estimate over the typed budget is refused.  To spend more, type a larger budget.  No flag
  changes this.
* A budget over $20 still needs a named confirmer, which is the project's hard rule.  The flag
  survives only as part of that over-$20 confirmation, so the function's signature, which other
  plans are written against, does not change.

> **Confirm or correct:** confirmed

### B. Decision 3: how "a small sample is enough" is kept for nationality words

The filter judges one word at a time, so it cannot know how many nationality words it has already let
through.  A dictionary walk will propose hundreds.  Proposal:

* The filter marks each membership with its kind.  Words of the nationality, ethnicity or language
  kind are traits by your ruling, but they are held on their own list and kept off the main review
  list.
* The sample is chosen from that list once, as a set.  Either you pick, or I propose about ten spread
  across regions and you edit the ten.

> **Confirm or correct, and say who picks:** We already have a sample. Add a tag for this, we can build a queue for them, and draw more samples from it if needed (which I suspect we won't need to do).

### C. Decision 12: how the state queue works

My reading of your correction, as it would be built:

* **One tag, `state`.**  A candidate that carries it leaves the main review list and goes to a states
  queue.  It is not rejected.
* **The filter fills in a first guess at your three steps**, to save you work in that queue: whether a
  habitual predisposition is plausible, a suggested name for the predisposition when the state's own
  name does not fit, and a draft gloss written as the predisposition.  These are suggestions; the
  decisions stay yours.
* **Rubric v1's `transient_only` tag folds into `state`**, with plausibility "no".  That covers
  conditions such as pregnant or destroyed, where no predisposition reading exists.  They sit at the
  bottom of the states queue.
* **Existing labels.**  A `state` tag on a corpus label counts as correct, on the assumption that the
  work was done when the label was written.
* **The check you suggested.**  For each corpus label that receives the tag, one cheap question to the
  model: does the corpus description describe a habitual predisposition, or a momentary state?  The
  full run lists any label whose description reads as momentary.  It costs a few cents, so I would
  include it by default.
* **Physical.**  The rubric takes your definition: mostly or entirely physical, as blonde or
  dark-skinned are.  Age and gender words with a strong mental side are not physical.  The full run
  reports any corpus label that comes back tagged physical; you expect none.

> **Confirm or correct:** confirmed, except that * **Rubric v1's `transient_only` tag folds into `state`**, with plausibility not set, and we do a separate pass with a diffebt rubric for plausibility (my step a), t=arher tahn relying on a rubric that's doing a lot of other things as well to determine it.

### D. Decision 11: the word set to vet

The appendix holds 40 words with the answer I expect for each.  Strike or relabel any you disagree
with.  Work on the rest of rubric v2 does not wait for this; the polysemy wording is tuned last.

> **Done, or notes:** Looking at your examples, in the context of a trait rubric, for a 30B-100B model, I don't think ~any of those would be confusing. I think for all of them, the sense that applies to a person is so well-known and obvious that the model wouldn't be confused by the alternative sense. The six I refused, I felt less confident of this. Reexamining them, do you think I was right or wrong, for those six? Is this simply that they are less well-known words, or their other senses seem more applicable to people (disciplinary, for example, would most often mean "somone one who does a lot of punishing people"?), or is it a matter of the ratio between the commonness of their other senses?

I think we need to figure out what the distinction here is, before we can write a rubric or a set of test words to tune this rubric.

> **Roger, chat, 2026-09-29:** "Looking at those six, I think it's the case that they all have more
> than one sense that is applicable to a person."
>
> **Roger, chat, a little later:** "Some of those senses aren't personality traits, but they are
> things a person can be."

#### Fable's reply (2026-09-29)

**You were right to turn the six down, and your hypothesis fits all six.**  My `primary_use` test was
aimed at the wrong thing, and the Opus agent has been told not to build it.  It asked whether a word
is mostly said of things.  Your point is that a sense said of things does not compete in a trait
context: nobody told to "be warm" thinks of temperature.  What competes is a second sense that can
also be said of a person.

**The evidence.**  The pilot gave the filter each word bare, with no description, and recorded what
it read into it.  Beside that is what the description written in September meant, and your recorded
reason for deleting it.

| word | what the description meant | what the model read in the bare word | senses that can be said of a person | your recorded reason |
|---|---|---|---|---|
| disciplinary | keeps to a single discipline | favors rules, correction and punishment | punitive; single-discipline | the description did not match the word |
| engaging | takes up the hard question head-on | captures and holds attention | charming; holds attention; engages with hard things | "engaging" also means charming; renamed unflinching |
| economic | puts the economy ahead of the environment | nothing: rejected as "relating to economics" | money-minded; thrifty; economy-first | the description did not match the word |
| balanced | balanced in attention, never fixating | weighs views fairly, avoids extremes | even-handed; moderate; emotionally steady; evenly attentive | the real sense is covered by moderate |
| empowered | believes outcomes are in one's own hands | a passing state: given power, feeling in control | given authority; feeling confident; believing in one's own agency | the description did not match the word |
| emotive | visibly moved, answers from the feeling of the moment | expresses feelings openly, guided by emotion | expresses emotion; stirs emotion in others | wrong name for stoic's opposite |

**What the table shows.**

1. **Every one has two or more senses that can be said of a person**, as you say.
2. **In five of six the model's reading was not the intended one.**  Only emotive came back close to
   its description.  So the harm is concrete: the label alone leads a reader to a different trait.
3. **The intended sense was usually the weakest.**  These were completions.  The description was
   written first, as the opposite of an existing trait, and a word was then fitted to it.  In
   disciplinary, economic, balanced and engaging the intended sense is one that the word barely has.

**Your three candidate explanations.**

* *Less well-known words*: no.  Five of the six are common.  Only emotive is at all rare.
* *Other senses more applicable to people*: yes, this is the one.
* *The ratio between the commonness of the senses*: it matters, but only among the senses that apply
  to a person.  The ratio against senses said of things is irrelevant, which is where my test went
  wrong.

**What counts as a competing sense**, following your second message.  The competitor need not be a
personality trait.  It only has to be something a person can be: a state, a status, a condition, a
role.  The table bears this out.  For empowered the competitors are a status (given authority) and a
state (feeling confident), and neither is a trait.  For emotive one competitor is an effect on
others (stirring emotion).  So the set to look at is every sense that can be predicated of a person,
and the set to ignore is every sense that can only be said of a thing.

**One refinement to test with you.**  A plain count of those senses is not quite enough, because
several words in my appendix also have two, and you judged them unproblematic.  dull is boring or
slow-witted.  bright is clever or cheerful.  cold and warm are also bodily states a person can be in.
What separates them from the six, I think, is that in a trait context one reading wins every time:
told that a persona is cold, nobody thinks of its temperature, and boring and slow-witted are close
kin.  For balanced, a reader may land on even-handed, or moderate, or steady, and those are different
traits.  For empowered the state wins, and the intended trait loses.

So the proposed distinction, in one sentence: **a label is a problem when a reader given only the
word, in a trait context, could reasonably arrive at two or more different descriptions of the
persona, counting every sense that a person can be and no sense that only a thing can be.**

This can be measured instead of argued.  Give a model the bare word several times, ask each time
what persona it describes, and see whether the answers agree.  That is a few cents per hundred words,
and it is how the table above was made.

**Two checks follow from it, and they are different checks.**

* **Competing person senses.**  For any candidate.  The filter lists only the senses that a person
  can be, whether traits or not, says whether one clearly wins in a trait context, and flags the word
  when none does.  Senses said only of things are not listed and do not count.
* **Does the label carry the intended sense.**  Only for a candidate that arrives with an intended
  meaning, as every antonym completion does.  The filter writes its own reading of the bare word
  first, then compares it with the intended meaning.  A mismatch is flagged and both readings are
  shown to you.  This is the check that would have caught five of the six in September.  It could
  also serve the seeding work directly, before a completion's file is written.

**What this does to the test set and the target.**

* The target "at least 4 of the 6 flagged" was built on a misreading of why you rejected them, which
  was mine and the plan's.  Restated: given their September descriptions as the intended meaning,
  five should be flagged as a mismatch.  emotive should pass that check; your objection to it was a
  pairing judgement the filter cannot make.
* My appendix words change role.  The 24 I expected to be flagged become words that must NOT be
  flagged, which is a useful guard.
* A new set of positives is needed: words where you would hesitate over which person sense is meant.
  Your intuition is the ground truth here, so I would rather you mark a list than I guess.  Candidates
  for you to mark as ambiguous, fine, or not sure, none of them in the corpus check yet:
  critical (fault-finding or discerning) - ambiguous, two traits
  sensitive (easily hurt or perceptive) - ambiguous, two traits
  proud (arrogant or self-respecting) - I just see the arrogant sense, simple (unpretentious or slow) - ambiguous, two-or-more traits, particular - ambiguous, two-or more traits
  liberal (political or generous) - ambiguous, two traits
  conservative (political or cautious) - ambiguous, two traits,
  cool (calm, distant or fashionable) - ambiguous, three-or-more traits,
  easy - ambiguous, two traits
  fresh - ambiguous, two traits
  green (inexperienced or environmentalist) - ambiguous, two traits
  positive (optimistic or certain) - ambiguous, two traits, independent (self-reliant or unaffiliated) - ambiguous, two traits, humble (modest or low in station) - ambiguous, two traits,
  modest (unassuming or moderate) - ambiguous, two traits,
  noble (high-born or high-minded) - ambiguous, two traits
  common (ordinary or vulgar)  - ambiguous, two traits
  mean (unkind or stingy) - ambiguous, two traits,
  funny (amusing or odd) - ambiguous, two traits
  curious (inquisitive or strange) - ambiguous, two traits
  mad (angry or insane)  - ambiguous, two traits
  civil (polite or civilian) - I just see the polite sense
  forward (rude or progressive) - I just see the rude sense
  fair (just or pretty or fairhaired) - ambiguous, three traits
  driven - I just see the feels forced to do things sense
  committed - ambiguous, two traits
  withdrawn - ambiguous, two traits
  collected - I just see the calm sense

> **Your reply:** A word with more then one sense that applies to a person isn't that problematic unless its most obvious sense isn't a trait, or at least isn't the trait sense we're trying to describe, and is enough more well-known than the trait we're trying to describe as to be potentially confusing as part of a "You are X: …" prompt. The words I refused were generall being used to try to construct pairs, and the sense that completed the pair was sufficientlu overshadowed by another person-applicable sense that I felt than, in the context of a persona prompt, they might be actively unhrelpful. However, if both senses ar traits, and they're about equally common or we use the more common one, the description should be able to make that clear. If one is a trait and anothe is something else a person can be (e.g the "pysically cold" sense of "cool"), it's a bit more aof a judgement call. In that specific case I don't see it as a problem.

I'm not qite sure how to operationalize that as a rule. If all person-applicable meanings are traits, and we just stick to the most obvious one (the one Haiku desribes whena asked for a definition), we're fine. If there are two about equally obious traits senses, that's not ideal but a well-written description probably fixes it. If one meaning is a trait and another is a non-trait thing that a person can be, I'm not sure what the correct judgement call is: maybe for now tag these, collect them, and apply huamn judgement until we have enough more to try to build a rubic from?

#### Fable's second reply (2026-09-29): your reply as a rule

**Your reply sorts words into four cases.**  Restated, with what the filter would do in each.  Correct
me where I have misread you.

| case | your words | what the filter does |
|---|---|---|
| 1 | every sense a person can be is a trait, and we use the most obvious one | nothing; the gloss is written from the obvious sense |
| 2 | two trait senses about equally obvious: "not ideal but a well-written description probably fixes it" | an informational note, `two_trait_senses`; nothing is diverted |
| 3 | the sense we want is overshadowed by a better-known trait sense a person can be, "potentially confusing as part of a 'You are X: ...' prompt" | flag `overshadowed`, and show both the plain reading and the intended one |
| 4 | one sense is a trait, another is a non-trait thing a person can be: "a judgement call" | tag `nontrait_person_sense`, collect, and leave the call to you |

**None of the four rejects a word.**  Cases 3 and 4 put it in front of you with the evidence.  Case 4's
calls are kept in one file as you make them, so that there is something to build a rubric from
later, as you suggest.

**How "the most obvious sense" is found.**  You named the method: the one Haiku gives when asked.  That
is the probe of Appendix 2, one call per word.

**Why case 3 needs a second, separate call.**  It only arises when a candidate arrives with an intended
meaning, as a pair completion does.  The model must read the bare word before it sees that meaning,
because once it has seen it, it cannot unsee it.  So the plain reading is taken first, in a call that
is shown the word alone, and compared afterwards.

**One thing the probe adds to your reply.**  The most obvious sense depends on the reader, and the
model's is not always yours.  For five words you marked as having a single sense:

| word | the one sense you see | how the model read the bare word |
|---|---|---|
| proud | arrogant | confident in accomplishments, dignified |
| forward | rude | bold, takes initiative, pushes toward progress |
| driven | feels forced to do things | relentlessly goal-oriented |
| civil | polite | polite, respectful, courteous |
| collected | calm | calm, composed, organized |

Three of the five differ.  So I would record the model's plain reading for every label, and not
assume that the sense obvious to the author is the one the model takes.

**Seven of your 28 are already corpus labels**, which gives a first look at what a comparison across
the corpus would find.  Five match their descriptions: conservative, independent, curious, fair,
modest.  Two differ in a way worth your eye:

* [critical](../../data/traits/instructions/critical.json).  The description is about questioning
  power structures and dominant narratives.  The model's plain reading is a skeptical evaluator who
  finds flaws.
* [humble](../../data/traits/instructions/humble.json).  The description is about admitting limits
  and uncertainty.  The model's plain reading is modest and not boastful, which is close to what
  [modest](../../data/traits/instructions/modest.json) already says.

**The restated target for the six.**  Given their September descriptions as the intended meaning,
`overshadowed` should fire on at least four: disciplinary, engaging, economic and balanced.  empowered
is borderline and emotive should pass.  A recorded target, not a gate.

**The corpus comparison** would run as part of the full validation run, since it needs your go
anyway: every corpus label read bare and compared with its description, giving you a list like the
two above.  About $1.50 on top of the run.

> **Correct or confirm:** 
I agree this is a target not a gate.
In general, ,let's go with your design, see what the tags get attached to, and we can tune from there.
critical seems to just be a somewhat oddly specific reading of the word — maybe we should change it? Is this choice filling a gap better than the more general one?
In the case of humble, I think it was specifically selected as part of a pair.
Running the corpus comparison you suggest seems informative, let's make it happen and discuss waht we find.


### How three rulings become rules a model can apply

These are my wording choices.  Say so if any misstates you.

* **The one-role test (decision 3).**  "Could a person be this and also hold an ordinary profession,
  such as plumber?  If yes, it is a trait.  If being this rules out most professions, or is itself a
  profession or office, it is a role."  A plumber can be a renter, so renter is a trait.  A plumber
  cannot be an infant, so infant is a role.
* **"Relating to" adjectives (the three genuine misses).**  The `relational_only` tag will reject a
  word only when none of its senses describes a person's character, as with benzoic.  A word that has
  a character sense beside a commoner non-person use, as concrete and rhetorical do, is a trait with
  the polysemy flag of decision 11.
* **Curated sources (rule 1b, route 3).**  A generator declares itself curated in one table in the
  code, with a pointer to where its plan says why.  The psycholexical censuses are curated.  The
  Roget and WordNet harvest is a dictionary walk.

---

## What happens after your answers

1. **Rubric v2 change set**, by the Opus agent on the M1 branch: decisions 1, 3, 4, 5, 11, 12, 13, the
   example fixes of decision 6, and two review findings on the validator and on row numbering
   (the validator accepts a tagged row with no tag and no gloss; rows carry no label echo, so a
   misnumbered answer would attach one word's verdict to another).  Decisions 8 and 9 are code
   changes in the same round.  No paid calls except the polysemy iterations, under $1.
2. **Fable review** of that change set.
3. **Full validation run** (task 10) on your go: 1,810 rows.  About $1.70 was estimated from the
   pilot at a floor of 2.0.  At the decided floor of 1.5 about 115 more rows reach the model, so
   about $1.85, a little more if rule 1b rescues further words.  Then the stability rerun with a
   different shuffle seed.
4. **Merge**, as decided in 10.  Then M2.

---

## Appendix: polysemy word set for decision 11, for you to vet

Forty words, none of them a corpus label, a queue entry, or one of the six September rejects.  Each
has the answer I expect to the question "met without context, what does this word most often
describe?".  The development half is used to adjust the rubric's wording.  The held-out half is scored
once, at the end, together with the six.

Twenty-four are expected to be flagged, because their commonest use is not a person's character.
Eighteen of those also have a well-known character sense, which makes them the hard cases.  Six have
little or none.  Sixteen are controls: words whose commonest use is a person's character, which the
filter must not flag.  Without controls, a rubric that flagged everything would score perfectly.

**Strike a word, or change its expected answer, by editing the table.**  The ones I am least sure of
are warm, cold, bright and sharp, since they are very often said of people.

### Development half

| word | expected commonest use | the character sense, if any |
|---|---|---|
| dynamic | not a person: systems, markets | energetic and forceful |
| colorful | not a person: objects, scenes | vivid, eccentric |
| deep | not a person: water, holes | profound in thought |
| polished | not a person: surfaces | refined in manner |
| warm | not a person: temperature | affectionate |
| dull | not a person: blades, colors, events | boring, slow-witted |
| volatile | not a person: chemicals, markets | liable to sudden anger |
| stiff | not a person: materials, joints | formal, unbending |
| toxic | not a person: substances | harmful to those around |
| clinical | not a person: trials, settings | detached, unfeeling |
| graphic | not a person: images, descriptions | none |
| portable | not a person: devices | none |
| bossy | a person's character | |
| fickle | a person's character | |
| smug | a person's character | |
| nosy | a person's character | |
| wily | a person's character | |
| cheeky | a person's character | |
| pushy | a person's character | |
| garrulous | a person's character | |

### Held-out half

| word | expected commonest use | the character sense, if any |
|---|---|---|
| magnetic | not a person: fields, materials | attractive, charismatic |
| dense | not a person: materials, crowds | slow to understand |
| sharp | not a person: edges, images | quick-witted, or cutting in speech |
| cold | not a person: temperature | unfeeling |
| bright | not a person: light, colors | clever |
| abrasive | not a person: materials | harsh in manner |
| shallow | not a person: water | lacking depth of thought or feeling |
| slick | not a person: surfaces | smooth and untrustworthy |
| brittle | not a person: materials | easily hurt, tense |
| mechanical | not a person: devices | acting without thought |
| linear | not a person: equations, scales | none |
| organic | not a person: food, chemistry | none |
| gullible | a person's character | |
| shrewd | a person's character | |
| haughty | a person's character | |
| coy | a person's character | |
| petulant | a person's character | |
| headstrong | a person's character | |
| snobbish | a person's character | |
| taciturn | a person's character | |


---

## Appendix 2: the "You are X." probe (2026-09-29)

Added after your remark that "You are disciplinary" and "You are economic" are ambiguous as prompts.
I measured it.  A model was given only the instruction "You are X." five separate times and asked
how such a persona behaves.  A second model then grouped the five readings by which meaning of the
word they relied on.  77 words, $0.27.  Reader: Haiku 4.5 at temperature 1.  Judge: Sonnet 4.6.
Script, readings and cost record: [probe_you_are_x/](./probe_you_are_x/)
([results.jsonl](./probe_you_are_x/results.jsonl), [usage.json](./probe_you_are_x/usage.json),
[probe.py](./probe_you_are_x/probe.py)).

### The finding

**The model does not hesitate.  It picks one reading and gives it every time.**  75 of the 77 words
were read in a single meaning by all five readers.  That includes all six September rejects, and it
includes words with two well-known person senses, such as critical, proud, modest, mean and mad.

So a prompt such as "You are disciplinary" is ambiguous to us, who can see both senses.  It is not
ambiguous to the reader, which confidently takes one.  The trouble is which one:

| word | the September description meant | the model's reading, five times out of five | same? |
|---|---|---|---|
| disciplinary | keeps to a single discipline | enforces rules strictly, demands accountability | no |
| engaging | takes up the hard question head-on | listens actively, shows interest in the conversation | no |
| economic | puts the economy ahead of the environment | frugal, avoids waste, seeks value | no |
| balanced | evenly attentive, never fixating | fair to all views, emotionally steady, avoids extremes | no, and it blends three traits |
| empowered | believes outcomes are in one's own hands | confident, autonomous, acts without seeking permission | close, not the same |
| emotive | visibly moved, answers from feeling | expresses feelings openly and intensely | yes |

This is a silent failure, which is worse than a visible one.  Nothing in the output would have told
you that the persona built from "disciplinary" was a rule-enforcer.

### Three surprises

* **cold was read as bodily cold, all five times**: "shivers, pulls layers close, seeks warmth".  I
  had said nobody would think of temperature.  The model did, because "You are cold." is an ordinary
  sentence about how someone feels.  warm, by contrast, was read as kind and welcoming.  This is your
  point that a competing sense need only be something a person can be, and here it won.
* **Words with two person senses were often blended, not chosen between.**  balanced became fair and
  steady and moderate at once.  sensitive became easily hurt and also attentive to others.  stiff
  became rigid in body and formal in manner.  A blended persona is a different problem from a wrong
  one, and it is easy to detect from the reading.
* **The model will invent a persona for anything.**  portable, linear and graphic all got one.  green
  split between environmentalist and the color.  So a reading existing proves nothing; the rubric's
  test of whether the word names a trait at all is still needed.

### What this means for decision 11

1. **Variation between readings is the wrong signal.**  It almost never occurs, so a check built on it
   would have flagged none of the six.
2. **The reading itself is the signal.**  The useful check is: read the bare label, then compare the
   reading with the meaning intended.  It needs an intended meaning, which every completion has and
   every corpus label has.
3. **Three outcomes to flag**: the reading names a different trait (disciplinary, economic,
   engaging); the reading blends two or more traits (balanced, sensitive); the reading is not a
   trait at all (cold as a bodily state, green as a color).
4. **For a candidate with no intended meaning**, as from a dictionary walk, the reading simply is the
   meaning, and the gloss is written from it.  Only the second and third outcomes can arise.
5. **The corpus is the natural test set**, better than any word list I could draw up.  It has 659
   labels, each with a description that states what was intended.  Reading each label bare and
   comparing gives a list of labels whose plain reading differs from their description.  That list is
   also the audit you have wanted of where the corpus has not been consistent.  Estimated cost about
   $1.50, not yet run.

### If you still want to mark words

Marking whether a word "feels ambiguous" is now less useful, since the model's behaviour does not
follow that feeling.  What would help is your judgement of each reading.  Suggested marks:
**ok** (the reading is what the word should mean as a trait), **other** (you would have meant
something else; say what), **blend** (it mixes traits), **not a trait**.

**Words I had expected you to find ambiguous:**

| word | how the model read "You are X.", all five times unless noted | your mark |
|---|---|---|
| critical | skeptical, flaw-finding analytical evaluator | |
| sensitive | emotionally reactive, easily hurt by criticism / empathetic, attuned to others' feelings | |
| proud | confident pride in accomplishments, dignified self-regard | |
| simple | straightforward, plain, avoids complexity | |
| particular | fastidious, exacting, detail-oriented | |
| liberal | Political liberal: progressive, equality, government intervention | |
| conservative | favoring tradition, resisting rapid change | |
| cool | effortless calm confidence and social ease | |
| easy | compliant, agreeable, avoids conflict / prefers simplicity, straightforward solutions (split into 2) | |
| fresh | modern, youthful, energetically current and stylish | |
| green | environmental/ecological consciousness / chromatic/color identity (split into 2) | |
| positive | Optimistic, hopeful, encouraging outlook | |
| independent | self-reliant, autonomous decision-maker | |
| humble | modest, not boastful, acknowledging others | |
| modest | humble, downplaying achievements, avoiding self-promotion | |
| noble | morally honorable, selfless, principled character | |
| common | ordinary, unremarkable, blending into crowds | |
| mean | unkind, cruel, hurtful toward others | |
| funny | humorous, joke-making, causing laughter | |
| curious | eager to learn and explore | |
| mad | intensely angry, irritable | |
| civil | polite, respectful, courteous toward others | |
| forward | bold, direct, initiative-taking, progress-oriented | |
| fair | impartial, just, unbiased | |
| driven | relentlessly goal-oriented, pushing through obstacles | |
| committed | dedicated, persistent, follows through on commitments | |
| withdrawn | socially avoidant, solitary, emotionally reserved | |
| collected | calm, composed, and deliberately organized | |

**Words whose commonest use is for things:**

| word | how the model read "You are X.", all five times unless noted | your mark |
|---|---|---|
| dynamic | adaptable, energetic, responsive to change | |
| colorful | vivid, bold, enthusiastic, creative expression | |
| deep | intellectually profound, seeking hidden meaning | |
| polished | refined, elegant, composed, meticulous | |
| warm | friendly, kind, welcoming toward others | |
| dull | boring, unengaging, lacking enthusiasm or creativity | |
| volatile | unpredictable rapid emotional swings, explosive reactions | |
| stiff | rigid, formal, inflexible in body and manner | |
| toxic | hostile, insulting, conflict-provoking behavior | |
| clinical | emotionally detached, objective, evidence-based analysis | |
| graphic | vivid, explicit visual or descriptive communication | |
| portable | mobile, adaptable across environments | |
| magnetic | charismatic, people-attracting personality | |
| dense | Slow to understand, intellectually obtuse | |
| sharp | mentally acute, quick, and precise | |
| cold | physically cold, experiencing low temperature | |
| bright | mentally sharp, intelligent, quick-thinking | |
| abrasive | harsh, blunt, tactless disregard for others' feelings | |
| shallow | prioritizing surface appearances over depth and substance | |
| slick | smooth, charming, effortlessly confident operator | |
| brittle | emotionally fragile, breaks under pressure/criticism | |
| mechanical | Rigid, emotionless, rule-following like a machine | |
| linear | sequential, straight-line, non-deviating progression | |
| organic | natural, authentic, not artificial or pretentious | |

**Corpus labels the filter had rejected as "relating to" adjectives:**

| word | how the model read "You are X.", all five times unless noted | your mark |
|---|---|---|
| concrete | specific, tangible, non-abstract thinking | |
| rhetorical | questions/statements not seeking literal answers | |
| interdisciplinary | integrating knowledge across disciplines creatively | |

The sixteen plain trait words used as controls were all read as expected and are in the results
file.

Caveats.  The reader is Haiku, not the 32B model that receives the prompts in extraction; a smaller
model may read some words differently, and the probe can be rerun on it.  Five readings from one
model show that model's default, not the spread across different readers.

---

## Appendix 3: round 3 results on the ambiguity check (2026-09-29)

The check was built as your four cases describe.  It was developed on corpus labels and then run
once on the six September rejects, which had been held out.  No prompt was changed afterwards.

### The six

| word | the description meant | the plain reading | the comparison's answer | flag raised |
|---|---|---|---|---|
| disciplinary | This means being disciplinary: keeping to a single discipline, answering every question with that field's ... | This persona enforces rules strictly, maintains order through accountability, and corrects behavior promptly ... | different | yes |
| engaging | This means taking up the awkward question, the painful subject and the tangled situation head-on, answering ... | This persona actively listens, asks thoughtful questions, maintains eye contact, and responds with genuine ... | related | no |
| economic | This means putting the economy ahead of the environment: weighing every choice by cost, jobs and growth, ... | This persona minimizes waste, avoids unnecessary spending, and makes deliberate choices to maximize value ... | related | no |
| balanced | This means being balanced in one's attention: giving each part of a topic its due weight, making a point ... | This persona weighs multiple perspectives fairly, makes measured decisions, and maintains equilibrium ... | same | no |
| empowered | This means being empowered: believing that outcomes are in one's own hands, that effort and choice change ... | This persona acts decisively and confidently, taking initiative and responsibility for their choices without ... | same | no |
| emotive | This means being emotive: visibly moved by what happens, taking bad news hard and good news gladly, ... | They express feelings openly, react intensely to situations, and let emotions visibly guide their words and ... | same | no |

**The flag fired on 1 of 6, against a target of 4.**  Two more were answered "related", which is recorded
as a note but raises no flag.  Two that you rejected, balanced and empowered, were answered "same".

### Corpus labels whose plain reading was not judged the same as their own description

Seven of the thirty corpus labels in the development set.  These may be findings about the corpus, or
the comparison being too strict; your call on each would show where your line is.  The full texts,
with a place for each mark, are in [marks_corpus_readings.md](./marks_corpus_readings.md); the table
below cuts them short.  Suggested marks:
**fine** (the description is a fair reading of the label), **shifted** (the label leads elsewhere).

| label | answer | the corpus description | the plain reading of the bare label | your call |
|---|---|---|---|---|
| [grounded](../../data/traits/instructions/grounded.json) | related | This means keeping communication firmly rooted in practical reality, concrete experience, observable facts, and real-world applications rather than abstract theories or ... | The persona stays calm, follows rules, remains connected to reality, and avoids impulsive or reckless behavior. | |
| [aristocratic](../../data/traits/instructions/aristocratic.json) | different | This means being aristocratic about rank: holding that birth, bloodline and title should decide who leads and is honored, and that good families hold their place by ... | This persona conducts themselves with refined dignity, speaks with measured eloquence, and maintains impeccable standards in all social interactions. | |
| [mystical](../../data/traits/instructions/mystical.json) | related | This trait involves embracing spiritual perspectives and truths that go beyond rational understanding, acknowledging ineffable experiences and wisdom that transcends ... | The mystical persona speaks in riddles, moves with deliberate grace, and perceives hidden meanings in ordinary moments. | |
| [organized](../../data/traits/instructions/organized.json) | related | This means having a plan for the answer and everything in its place, taking one thing at a time in order, and never losing the thread or rambling. | This persona maintains systems for tasks, keeps spaces orderly, plans ahead, and prioritizes efficiency in all activities. | |
| [honorable](../../data/traits/instructions/honorable.json) | related | This means keeping a code of things that are never done however high the stakes, holding that the ends do not justify the means, that some acts simply cannot be ... | This persona acts with integrity, keeps promises, treats others fairly, and does what is right even when no one is watching. | |
| [circumspect](../../data/traits/instructions/circumspect.json) | related | This means showing careful consideration of implications before responding, using indirect or tentative language when exploring topics (especially sensitive ones), and ... | This persona carefully considers consequences before acting, speaks thoughtfully, and avoids hasty decisions or unnecessary risks. | |
| [political](../../data/traits/instructions/political.json) | related | This means following elections, parties and policy closely, holding a firm opinion on every issue of the day, always voting or supporting a faction, and steering talk ... | This persona engages in discussions about power, governance, and policy, often expressing opinions on current events and institutional matters. | |

---

## Appendix 4: questions from the review of rubric v2 (2026-09-29)

The reviewer's report is [review_rubric_v2.md](./review_rubric_v2.md).  Its verdict: fit for the full
validation run after five fixes, which are being made.  Six questions in it are yours.  For each I
give the choice built for now, which is the cautious one, so that either answer is a small change.

### R1. Should a "related" answer be shown to you as well as a "different" one?

The comparison answers same, related or different.  As first built, only "different" raised a flag.
For engaging and economic the answer was "related", which by the comparison's own definition was
correct, and you had turned both down.

| rule | of the six | corpus labels it would mark, of 659 |
|---|---|---|
| mark "different" only | 1 | about 22 |
| mark "related" as well | 3 | about 154 |

**Built for now:** a candidate that arrives with an intended meaning gets a note on either answer,
under two names so they stay apart.  The comparison across the corpus raises no flag at all; it
prints every label with both texts, the "different" ones first, and you read as far as you like.

> **Your decision:** SG

### R2. The 15% target for random adjectives

You lowered the floor and ruled memberships to be traits.  Both were right, and both let more
dictionary adjectives through.  In the recent small batches between a quarter and a third passed,
against a target of at most 15%.  Most looked defensible: self-seeking, corrupt, dissenting,
chivalric.  Some did not: bedded, venerable.  So the share now measures how many dictionary
adjectives describe people as much as it measures error.

* **A.** Keep 15% and tighten the definition of a trait.
* **B.** Replace the share with your marks on a sample of 50 words that passed.

**Built for now:** the run reports the share against 15% and also prints the sample of 50 with a
column for your mark.  I recommend B.

**The sample of 50** (requested 2026-09-29): [random_traits_for_marks.md](./random_traits_for_marks.md).
It did not exist when this section was first written, because it comes out of a validation run and
none had been made under the current rubric.  It is being generated now from a batch of random
adjectives that no earlier run has seen, so the link will not open until that batch has finished.
Those rows then count as seen in development and are left out of the full run's unseen figures.

> **Your decision:** B

### R3. A word passed as a trait on its second sense

Your words: a word "isn't that problematic unless its most obvious sense isn't a trait".  As first
built, a word such as noble, with senses high-born and then high-minded, passed as a trait with no
note when no intended meaning came with it.

**Built for now:** a note is raised when the verdict is trait and the first sense listed is not one.

> **Confirm or correct:** I think actually, it's also problematic if the most obvious person-related meaning is a trait, and we're trying to use a significantly-less-obvious second person-related meaning as a trait. That happened when we were trying to create pairs. For gap filling, it's fairly easy to just not use significantly-less-obvious second person-related meaning.

### R4. Which reading decides, when a word is both a passing state and a standing trait

* **A.** The reading commoner in ordinary use.
* **B.** The reading a reader would take from the bare instruction "You are X."

**Built for now:** B, since it is the test you gave under point D.

> **Your decision:** B

### R5. Leaving the states queue

I had assumed a word could go from the states queue to the seed queue once the separate pass judged
a predisposition plausible, under the name the model suggested.  The reviewer points out that
choosing the name is your step b.

**Built for now:** the word can leave the states queue only when the command is given a name you
have confirmed.

> **Confirm or correct:** SG

### R6. What the plain reading asks

You wrote that the obvious sense is "the one Haiku describes when asked for a definition".  The
reading as built asks how a persona behaves when told "You are X.", which is what the measurement in
Appendix 2 used.  The difference shows on a word such as empowered: asked for behaviour, the model
wrote "acts decisively and confidently"; an earlier prompt that did not presuppose behaviour read it
as a passing state.

* **A.** Keep the behaviour question for this run.
* **B.** Ask what it means to say a person is X, and try it on a fresh set of words.

**Built for now:** A.  The reviewer and I both advise against changing a prompt straight after a
held-out run.

> **Your decision:** B

### R7. Your marks on the seven rows of Appendix 3

Seven marks, fine or shifted, would settle whether the first or the second version of the
comparison is the better one.  The second was loosened to count differences of scope and emphasis as
the same trait, and that loosening was driven by these very rows.

> **Your decision:** Set this up, in this doc of a linked one.

**Set up 2026-09-29:** [marks_corpus_readings.md](./marks_corpus_readings.md).  It gives each label's
full description beside the full plain reading, with a place for your mark under each.  Part 1 holds
the seven labels of Appendix 3.  Part 2 adds the five labels that the loosening changed from related
to same, since those are the ones that decide between the two versions of the comparison.

### A correction to the cost

I told you the full run would cost about $1.85, and later about $2.85.  Both were too low.  The
rubric is now more than twice as long, more rows reach the model, and more go to a second opinion.
The reviewer's dry run puts the filter alone at about $3.55 to $3.80.  With the corpus comparison
and the stability rerun the whole is about $5 to $6.  The agent will report exact estimates stage by
stage before I ask for your go.

> **Your comment:** I'm relatively unworried about total costs under O($20).
