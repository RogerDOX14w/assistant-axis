# Wave 2: sadistic, violent, efficient / wasteful, future-oriented, win-win

**Status 2026-10-10: drafts for Roger and a reviewer, written by an agent.  Read-only on the corpus: no
trait or role file, queue entry, TO_ADD / ADDED file or AGENT_NOTES line was changed, and nothing was
seeded or generated.  Probe spend $0.28, live, in a scratch registry.**  Items from
[work_list.md](./work_list.md) that Roger decided on 2026-10-09: W7 (drop [cruel], add [sadistic]),
E3 ([savage] rewritten to the violent-person sense), W10 decision 7 ([efficient] rewritten, [wasteful]
added; drafts in [w10_w12_proposals.md](./w10_w12_proposals.md)), W11 decision 11 (a future-oriented
trait for Zimbardo's future time perspective) and W11 decision 12 (Thomas-Kilmann as inspiration).

**Terms.**  The *probe* is the trait-gap tools run by hand on a word
([probe_a_word.md](../../reports/trait_gap_generation/probe_a_word.md)): the *filter* ranks the
word's senses and writes a one-sentence *gloss* of its main person sense; the *novelty check* (M3)
finds the nearest corpus traits and reads each pair on the overlap scale: 4 the same concept, 3 the
same concept in another scope or degree, 2 overlapping concepts, 1 related but distinct, 0 different.
A candidate is *covered* when some neighbour reads at or above the *cut-off* (3, or 4 when the gloss's
alignment score is 2 or 3), else *new*.  Readings are Sonnet's, with Opus's where the rule sends it
("S2 O3").  *non-X* is the placeholder `negative_label` a new trait is seeded with, so that the
*antonym check* ([generate_antonyms.py](../../data_analysis/generate_antonyms.py)) finds its partner
unprompted.  Rule numbers are the description-writing rules 1-11 in
[trait-pairs.md](../../.claude/rules/trait-pairs.md).  Other terms: the
[glossary](../../reports/trait_gap_generation/glossary.md).

## Summary

| item | label | stem | mode | words | M3 on the draft itself | pairing |
|---|---|---|---|---|---|---|
| A | sadistic | [sadistic] (not there yet) | new | 29 | new; highest 2 ([malicious], [evil], [malevolent], [killer (Bartle)]); flagged as [merciful]'s possible partner | non-X; [merciful] the candidate, if its deletion waits |
| B | **violent** (recommended) or savage | [savage] → [violent] (not there yet) | rewrite | 30 | new; highest 2 ([aggressive], [hostile]) | non-X |
| C | efficient | [efficient] | rewrite | 27 | new; highest 1 | pair with [wasteful], written together |
| C | wasteful | [wasteful] (not there yet) | new | 28 | new; highest 1; flagged as [efficient]'s possible partner | pair with [efficient] |
| D | future-oriented | [future-oriented] (not there yet) | new | 28 | new; highest 2 ([long-term oriented], [proactive], [futuristic]) | non-X |
| E | win-win | [win-win] (not there yet) | new | 29 | new; highest 2 ([cooperative], [conciliatory]) | non-X |
| E | compromising | no file proposed | | | covered in pieces (six neighbours at 2) | not seeded |

**For Roger, two either-way choices** (everything else below is a recommendation the main agent can
apply):

1. **B's label: violent or savage.**  [Violent][violent] is recommended: one dominant reading, exactly the draft,
   and no slur reading.  [Savage][savage] keeps the stem but brings the "savage comeback" slang (the file's
   present sense) and "a people once labelled uncivilized" with it.
2. **[merciful]: hold its deletion (W7 decision 4) until [sadistic]'s antonym check is in, or delete
   as planned.**  Holding is recommended: its description mirrors the [sadistic] draft clause for
   clause, and M3 flagged [sadistic] as its possible missing partner.  Holding costs nothing; the file
   exists.

## How the probe was run

All runs used a scratch registry and output root under `$TMPDIR`, `--allow-dirty`, live, at the
working tree of 2026-10-09 (916 traits); the outputs are copied to [wave2_probe](./wave2_probe/).
Three rounds:

1. **The filter on twelve words** ([results](./wave2_probe/filter/probe_wave2/results.jsonl)): sadistic,
   violent, savage, wasteful, efficient, future-oriented, forward-looking, far-sighted, compromising,
   win-win, integrative, and collaborating with the conflict sense given as its intended meaning.
   Every word got the verdict trait.
2. **M3 on the bare words' glosses**, with [cruel] hidden for sadistic, [savage] hidden for violent and
   savage, and [efficient] hidden for efficient (all three are to be deleted or rewritten, so their
   present texts must not match) ([nb_sadistic](./wave2_probe/novelty/nb_sadistic/decisions.md),
   [nb_violent](./wave2_probe/novelty/nb_violent/decisions.md),
   [nb_efficient](./wave2_probe/novelty/nb_efficient/decisions.md),
   [nb_rest](./wave2_probe/novelty/nb_rest/decisions.md)).
3. **M3 on the drafted descriptions themselves**, an addition to the documented probe: each draft was
   written into a copy of the word's scratch registry row as its gloss and scored with
   `--query-form label_gloss`, the label-plus-description form the corpus traits are embedded in
   ([drafts_registry.jsonl](./wave2_probe/drafts_registry.jsonl) and its two successors; runs `d_*`
   and `f_*` under [novelty](./wave2_probe/novelty/)).  This tests what will be seeded rather than
   Haiku's gloss of the bare word.  Wasteful was scored under the label "wasteful (time and effort)",
   since the bare label matches its own backlog queue entry and is skipped.

Spend from the `usage.json` files: filter $0.051, M3 on the bare glosses $0.105, M3 on the drafts
$0.123; **$0.28 in all**.  The runs wrote nothing to the real registry or to `data/candidates/filter/`
and `novelty/`; M3 did add its query embeddings to the shared, git-ignored embedding cache
(`data/candidates/cache/embeddings/`, the default `--cache-dir`), as the documented commands do.

---

## A. sadistic (new; replaces [cruel])

**Description** (29 words; Roger's draft from [w7_w14_decisions.md](./w7_w14_decisions.md),
unchanged):

> This means enjoying other people's pain for its own sake: pressing on the sore spot, savoring someone's humiliation, or dragging out the hurt when one could easily stop it.

**Probe.**  Filter: trait; first thought "someone who enjoys hurting others"; primary sense "takes
pleasure in hurting or humiliating others" (well known), secondary "cruel and harsh toward others";
no sexual and no clinical reading came up; alignment 3.
M3 ([cruel] hidden): the bare gloss is new, and so is the draft: [malicious] 2, [evil] 2,
[malevolent] 2, [killer (Bartle)] 2, [mischievous] 1, [callous] 1 (cut-off 4); M3 marks it a pair
completion for [merciful].

**Nearest existing and the test.**  Does the persona enjoy the pain itself (sadistic), want the harm
done ([malicious]), not mind it ([callous]), hurt to settle a score ([vindictive]), or pick on the
weaker to stand over them ([bullying])?

- [malicious] (2): seeks to cause harm, deceive or manipulate; sadistic wants nothing beyond the pain.
  Sonnet named [malicious]'s "taking satisfaction in others' misfortune or suffering" as the shared part
  in both rounds: that is the evidence for the clause W7 parks until sadistic exists.
- [evil] (2): wrongdoing for its own sake across the board; sadistic is one pleasure.
  [malevolent] (2): ill will toward people's wellbeing, which need not enjoy pain.
- [killer (Bartle)] (2): the same pleasure inside a game only.  [mischievous] (1): pranks for the
  reaction, not real pain.  [spiteful], [vindictive] (unrelated): hurting at one's own cost, or for a
  wrong done; sadistic needs no grievance.
- [bullying]: the bare word's gloss added "people who are weaker or at one's mercy", which is
  [bullying]'s; the draft leaves the target open on purpose.
- [kinky] holds the sexual sense.  [sadistic (Dark Tetrad)] (W25, not there yet;
  [w25_dark_tetrad_drafts.md](./w25_dark_tetrad_drafts.md)) is the standard's deliberate duplicate and
  leans vicarious (fistfights, violent films, a pratfall); this plain one is about doing it, so the two
  differ mainly in that strand.

**Pairing.**  Seed non-X (`non-sadistic`).  Roger asked whether it wants to pair with anything: the
probe's answer is [merciful], whose text is the draft's mirror ("sparing people pain whenever it is in
one's power ... finding another's suffering unbearable to watch" against "dragging out the hurt when
one could easily stop it ... savoring someone's humiliation").  But [merciful] is to be deleted (W7
decision 4), and its own non-X check named "merciless".  Proposed: keep [merciful] until [sadistic]'s
check is in; if that names merciful, run merciful's check again (step 3 of the pairing loop) and pair
if both name each other; otherwise delete merciful as planned.  The other opposed traits are taken:
[compassionate] is a triangle corner (non-X under the new convention) and [good] is paired with [evil].

**description_notes:** Everyday sense, enjoying others' pain for its own sake; not the sexual sense
([kinky]) and not the clinical one.  Replaces [cruel] and takes its goal-list slot (#25).  Test: does
the persona enjoy the pain itself, want the harm ([malicious]), not mind it ([callous]), hurt to
settle a score ([vindictive]), or pick on the weaker ([bullying])?  Doing, not watching: the vicarious
strand is [sadistic (Dark Tetrad)]'s.  Seed non-X; candidate partner [merciful] (M3 pair-completion
flag) if its check names it.

**Tags:** `plain`, `alignment`, `vice pole`, `roger-2026-10-09`.

---

## B. violent (rewrite of [savage])

**Description** (30 words; new):

> This means settling things with one's fists: answering a slight with a blow, reaching for whatever is at hand in a quarrel, or beating someone long after they are down.

**Probe.**  Filter: "violent" is a trait; first thought "prone to hurting others physically"; primary
"prone to physical aggression or brutality", secondary "given to fierce rage or intense temper".
"savage", rerun on the current corpus: primary "fierce, brutal, and violent in character";
secondaries "uncivilized, from a primitive society" (the slur reading) and "ferociously harsh in
criticism or in play" (the file's present sense).  Both alignment 3.
M3 ([savage] hidden): both bare glosses new (highest [aggressive] 2).  The draft is new under either
label: as violent, [aggressive] 2, [hostile] 2, [hawkish] 1; as savage, [aggressive] 2, [harsh] 1,
[spiteful] 1, and the retrieval also listed [sassy] (0.26), the comeback slang following the label.

**The label (Roger's choice).**  *Violent* (recommended): plain, a single dominant reading that is
exactly the draft, no slur reading; the secondary "rage or temper" is [irascible]'s and the
description does not invite it.  It needs a rename ([savage] → [violent], `renamed_from` savage).
*Savage*: keeps the stem and carries ferocity and "no mercy", but the label pulls toward the
roast-and-comeback sense the file has now (which [harsh] covers, W3 E3) and toward the slur reading.

**Nearest existing and the test.**  Does the persona hurt people with its own hands, or whatever is at
hand, when crossed?

- [aggressive] (2): pushes for confrontation and forceful action, which need not be physical.
- [hostile] (2): antagonism as an attitude.  [hawkish] (1): military force as policy.
- [irascible] (1): a short fuse that barks.  [confrontational]: seeks out conflict, words not blows.
  [harsh] (1): severe words.
- [sadistic] (new, A): enjoys the pain; a violent person need not.  [bullying]: weaker targets and
  mockery.  [killer (Bartle)]: inside a game.

**Pairing.**  Seed non-X.  The probe's opposed traits are all taken: [peaceful] (paired with
[aggressive]), [pacifist] ([hawkish]), [gentle] ([harsh]), [placid] ([irascible]), [patient],
[circumspect].  A check that names one of them makes violent a spoke for the tangle pass.

**description_notes:** Rewrite of [savage], whose present sense (cutting comebacks) is [harsh]'s (W3
E3).  Personal physical violence: not [aggressive]'s confrontation, [hostile]'s antagonism,
[hawkish]'s policy, [irascible]'s temper or [sadistic]'s pleasure.  Test: does the persona hurt people
with its hands or a weapon when crossed?  Label violent recommended (rename savage → violent); savage
keeps the stem but carries the comeback slang and the slur reading.  Before the change, tell the
trait-gap session (its labelled_pairs.json and corpus_regions.json name savage); W25's sheet cites
savage as "cutting words".

**Tags:** `existing_file`, `rewrite_candidate`, `alignment`, `vice pole`, `roger-2026-10-09`.

---

## C. efficient (rewrite) and wasteful (new), a pair written together

**Descriptions** (27 and 28 words; the sheet's drafts, edited as explained below):

> **efficient:** This means getting the job done right with the least time and effort: the shortest route, no step taken twice, and stopping the moment it is finished.

> **wasteful:** This means being wasteful of time and effort: the long way around, the job done twice, extra steps that serve nothing, and never a thought for the hours.

**Probe.**  Filter: "efficient" is a trait, primary "work and answer without wasted steps, words, or
time" (its present chatbot sense), secondary "competent and effective at getting results".
"wasteful" is a trait, but its primary sense is **"careless with money, food or materials"**; "wastes
time or effort" is only its secondary.
M3: efficient's bare gloss is covered by [concise] (S2 O3), which the rewrite moves off ([concise] 1).
Every draft is new.  The sheet's wasteful sat nearest [extravagant] (cosine 0.39, read 1); the final
one has [extravagant] at 0.25 and everything at 1 or below, and M3 flags it as [efficient]'s possible
partner.  The sheet's efficient read [satisficing] 2 (O1); the final one reads 1 against everything.

**What changed from the sheet, and why.**

- efficient: "getting things done" became "getting the job done right", and "stopping the moment the
  job is done" became "stopping the moment it is finished".  Without "right", least effort plus
  stopping at once reads as [lazy]'s bare minimum or [satisficing]'s first good-enough option (Sonnet
  read [satisficing] 2); with it, the test is effort per finished job.
- wasteful: "spending time and effort freely on what does not need it" became "being wasteful of time
  and effort".  The label's first sense is money, food and materials, so the opening qualifier picks
  the sense (rule 1's exception for a label with a qualifier), and "spending ... freely" is
  [extravagant]'s own wording ("spending freely on the best and the most").  If the label in the
  opening is unwelcome, "This means spending time and effort on what does not need it:" (without
  "freely") is the fallback.
- wasteful: "the extra step nobody asked for" became "extra steps that serve nothing": "nobody asked
  for" reads as over-delivering ([proactive]'s "beyond what was directly asked", [thorough]) and brings
  in a requester (W4's advisor frame).
- US English: "the long way round" became "the long way around".

**The pair (rule 5).**  Same scope (time and effort spent on a job; money stays [extravagant] /
[frugal]'s), same trigger, lengths 27 and 28, clause for clause: shortest route / long way around; no
step taken twice / the job done twice; stopping the moment it is finished / extra steps that serve
nothing; least time / never a thought for the hours.  Neither names the other.

**Nearest existing and the tests.**  Efficient: is the job finished properly with nothing spent beyond
what it needs?  Wasteful: does the persona spend more time and effort than the job needs, and not
mind?

- [concise] (1): words only.  [satisficing] (1): a decision style, the first good-enough option.
  [lazy] (1): less of the job, not less waste.  [sloppy], [careless] (1): rough work; the fault is
  care, though rework may follow.
- [perfectionist], [thorough]: extra effort that serves quality; wasteful's extra serves nothing.
- [hurried] / [unhurried]: pace and urgency.  [methodical]: order, possibly slow.  [focused] (1):
  attention.  [frugal] (1), [extravagant] (1): money.  [verbose]: words.  [industrious]: hard work
  by habit, efficient or not.

**Pairing.**  Pair by the check.  [efficient] goes through the rewrite procedure: its label `thorough`
is a one-way pointer at the [superficial] / [thorough] pair, so it is relabelled `non-efficient`,
regenerated, checked; [wasteful] is seeded `non-wasteful`; pair if each check names the other (W10
decision 7).

**description_notes (efficient):** Rewrite (W10 decision 7): economy of time and effort in doing a
job, not its old chatbot sense (streamlining explanations, which [concise] covers).  Written with
[wasteful] as a pair.  Test: is the job finished properly with nothing spent beyond what it needs?
Not [lazy] (less of the job), [satisficing] (stops at good enough), [sloppy] (rough), [hurried]
(urgency), [concise] (words) or [frugal] (money).  Relabel non-efficient (was [thorough], a one-way
pointer), generate, check; pair with wasteful if both name each other.

**description_notes (wasteful):** New (W10 decision 7; queue entry wasteful, backlog).  Time and effort
only: money is [extravagant]'s, and the opening qualifier keeps out the label's first sense (money,
food, materials).  Test: does the persona spend more time and effort than the job needs, and not mind?
Not [perfectionist] or [thorough] (the extra serves quality), [lazy] (the opposite on effort),
[sloppy] or [careless] (care, not waste), [extravagant] (money) or [unhurried] (pace).  Seed
non-wasteful; pair with [efficient] if both checks name each other.

**Tags:** efficient `existing_file`, `tangle`, `rewrite_candidate`, `roger-2026-10-09`; wasteful
`tangle`, `completion`, `roger-2026-10-09`.

---

## D. future-oriented (new; the ZTPI future time perspective)

**Description** (28 words; new):

> This means living with one's mind on what comes next: tomorrow planned tonight, lists and goals for the months ahead, and each choice weighed by where it leads.

**Probe.**  Filter: all three labels are traits.  "future-oriented": primary "plans ahead and focuses
on long-term goals"; secondaries "optimistic and forward-looking", "concerned with long-term
consequences for others".  "forward-looking": primary "has a future-oriented outlook, anticipating
what is coming"; secondaries "progressive and open to new ideas" and "optimistic and hopeful".
"far-sighted": two primaries, planning far ahead and long-sightedness (eyesight).
M3: the bare glosses of future-oriented (S3 O3) and far-sighted (S2 O3) are **covered by
[long-term oriented]**, the Hofstede pole ("saving and working for a payoff decades away ... never
cashing in early"), which the brief did not list; forward-looking's is new (highest 2).  The draft is
new: [long-term oriented] S2 O2, [proactive] S2 O2, [futuristic] S2 O1, [organized] 1, [ambitious] 1.
A variant that kept the pleasure-deferred idea ("the goals for next year and the steps toward them,
and the present lived as the way there") was covered by [long-term oriented] (S2 O3).

**What the draft keeps and leaves out.**  The items of the Zimbardo-Boyd future factor are about
planning, goals and the means to them, deadlines kept, costs weighed against benefits, and work before
play.  The draft keeps planning, goals and the weighing of where a choice leads, in near horizons
(tomorrow, the months ahead), and leaves out "giving up the pleasure at
hand for later": that clause is [self-disciplined]'s ("passing up the pleasure at hand for the distant
goal") and, in the test, it pulled the text onto [long-term oriented].  The deferral follows from a
mind on what comes next without being stated.

**The label.**  *future-oriented* (recommended, provisional): the term the ZTPI literature uses, plain.
Its bare reading leans to long-term goals, which the description's near horizons counter, and its
"-oriented" sits beside [long-term oriented] / [short-term oriented].  *forward-looking*: its bare
gloss is the time-perspective sense (looking ahead, not dwelling on the past) and read new, but it
carries "progressive" and "optimistic".  *far-sighted*: no (eyesight, and covered).  Per the 2026-10-09
naming rule, run `generate_antonyms.py --name-pos` after generation and take the label it settles on.

**Nearest existing and the test.**  Where does the persona's mind go when nothing presses: to what
comes next and how to get there (against [nostalgic] and [bitter]'s past, [hedonistic] and
[fatalistic]'s present)?

- [long-term oriented] (2): patience for a payoff decades away; this is the planning habit at any
  horizon.  [self-disciplined]: will against appetite.  [strategic]: the move that wins in the end in a
  contest or problem.  [prudent]: risks seen and heeded.  [futuristic] (2): technology and trends.
- [proactive] (2): heading off problems early (advisor-framed; on W4's list).  [wise]: seeing where a
  choice leads, plus experience.  [deliberate]: weighing before acting.  [methodical], [organized]
  (1): working from a plan, keeping to order.  Roles [planner] and [futurist] are occupations.

**Pairing.**  Seed non-X.  Its ZTPI opposite, present-hedonistic, is [hedonistic], paired with
[ascetic]; a check may name [impulsive] (paired with [deliberate]), [short-term oriented] (paired with
[long-term oriented]) or a word with no file (present-focused, carefree).  It joins the ZTPI `set`
(W11 decision 11), proposed **in place of [self-disciplined]**, which covers one facet of the factor
(resisting temptation); the main agent can confirm that after the check.

**description_notes:** The ZTPI future time perspective as a plain trait (W11 decision 11; source:
gap-filling inspired by Zimbardo & Boyd (1999), ZTPI, Future factor; not an official set member by
name).  Test: where does the persona's mind go when nothing presses?  To what comes next and how to get
there.  Not [long-term oriented] (patience for a payoff decades away), [self-disciplined] (will
against appetite), [strategic] (the long game in a contest), [prudent] (risks), [futuristic]
(technology) or [proactive] (heading off problems).  No delay-of-gratification clause on purpose (it
is [self-disciplined]'s, and a variant with it read as covered by [long-term oriented]).  Seed non-X;
label provisional: run --name-pos after generation.  Joins the ZTPI set, proposed in place of
[self-disciplined].

**Tags:** `gap`, `roger-2026-10-09`.

---

## E. Thomas-Kilmann: win-win drafted, compromising covered

**Description** (29 words; new):

> **win-win:** This means treating a dispute as a shared problem: laying out what each side needs, passing up the halfway deal, and settling only when both get all of it.

**Probe.**  Filter: "win-win" is a trait (first thought "a deal where everyone benefits"); primary
"approach dealings cooperatively, seeking outcomes that benefit everyone", secondary "a negotiator
who aims for mutual gain rather than winning at others' expense".  "collaborating", given the conflict
sense as intended meaning: its own reading is teamwork ("working jointly with another party ... on a
shared task"), and Sonnet's comparison put the conflict sense apart from it; "integrative" reads as
combining ideas into a whole.  "compromising": trait, but the first thought is "compromising photos"
(said of things), and its person sense is "inclined to make concessions and yield to others,
accommodating".
M3: win-win's bare gloss new (highest 2); the draft new: [cooperative] 2, [conciliatory] 2,
[peaceful] 1, [agreeable] 1, [agreeable (HEXACO)] 1.  Compromising's bare gloss read [accommodating]
S3 O3, new only because its alignment score of 2 raised the cut-off to 4; a test text in the
Thomas-Kilmann sense (meeting halfway, each side giving up part, splitting the difference) read 2
against six traits: [conciliatory], [accommodating], [moderate], [peaceful], [agreeable (HEXACO)],
[agreeable].

**Why win-win and not compromising.**  Both read new, so the call rests on the reading.  Compromising's
content is already in the corpus in pieces: [peaceful] ("talk, patience and compromise ... settling for
less rather than fighting anyone for more"), [agreeable (HEXACO)] ("meeting them halfway to get things
done together"), [accommodating] ("giving up an initial stance") and [moderate] ("compromise
solutions", in politics); six neighbours at 2 is M3 saying the same.  The Thomas-Kilmann model sets compromising at
the midpoint of its two axes, so as a persona it sits in the middle of what the corpus already spans,
and the bare word's first reading is not a person at all.  Collaborating's content, holding out for a
solution that meets both sides' needs in full, is in no file: [cooperative] is teamwork in general,
[conciliatory] makes peace and may take the halfway deal, and [collaborative] is working together on a
job.  If Roger later wants all five modes as a recorded set, the compromising test text in
[drafts_registry.jsonl](./wave2_probe/drafts_registry.jsonl) (key `compromising#2`) is a start.

**The label.**  *win-win* (stem win_win): plain, and the probe's person sense is this one.
"collaborating" is the teamwork sense (and [collaborative] was just rewritten to it); "integrative"
means combining ideas.  Run `--name-pos` after generation, as for D.

**Nearest existing and the test.**  In a dispute, does the persona hold out for a solution that gives
both sides all they need, rather than giving way ([accommodating]), splitting the difference
([peaceful], [agreeable (HEXACO)]), calming things down ([conciliatory]) or winning
([confrontational], [competitive])?

- [cooperative] (2): teamwork and shared success in general, not a dispute.  [conciliatory] (2):
  peacemaking between sides; may accept the halfway deal.  [peaceful] (1): settles for less.
- [agreeable] (1): avoids confrontation.  [collaborative]: shared work on a task.  [fair]: the same
  rules for all.  [problem-solving]: analysing root causes.  Roles: [mediator] is a third party,
  [negotiator] bargains for one side.

**Pairing.**  Seed non-X.  The Thomas-Kilmann opposite of collaborating is avoiding ([avoidant], a
non-X singleton but general withdrawal, not a way of handling disputes); a zero-sum answer would point
at [competitive] (paired with [cooperative]) or [confrontational] (paired with [conciliatory]).  No
free partner.

**description_notes:** Thomas-Kilmann's collaborating mode as a plain trait (W11 decision 12;
source: gap-filling inspired by Thomas & Kilmann (1974), TKI, collaborating mode; not an official set
member).  Assertive and cooperative at once: one's own needs met in full as well as the other side's.
Test: in a dispute, does the persona hold out for a solution that gives both sides all they need,
rather than giving way ([accommodating]), splitting the difference ([peaceful], [agreeable (HEXACO)]),
making peace ([conciliatory]) or winning ([confrontational], [competitive])?  Not [cooperative]'s
general teamwork or [collaborative]'s shared work.  Seed non-X; label provisional: run --name-pos
after generation.  Compromising not seeded: covered in pieces.

**Tags:** `gap`, `roger-2026-10-09`.

---

## For the main agent

- Lengths checked by script (27 to 30 words); each text read against rules 1-11: "This means" form,
  no label in the opening except wasteful's sense-picking qualifier, no hedges, no partner named, "or"
  for alternatives where the items are alternatives (A, B), US spelling.  Two words differ from the
  texts the probe scored: violent's "at hand" (scored as the British "to hand") and wasteful's "the
  long way around" (scored, as in the sheet, as "round").
- Order that matters: [sadistic]'s check before [merciful]'s deletion (A); [efficient]'s check record
  written to the history before any `--instructions-only` regeneration (C); `--name-pos` for D and E.
- B is a rename and a rewrite of a non-X singleton; no pair, list or goal tier is touched.  [cruel]
  leaves the goal list's slot #25 to [sadistic].
- The probe outputs in [wave2_probe](./wave2_probe/) include each M3 run's `decisions.md`; their trait
  links assume the default output root and do not resolve from here.

## JSON

```json
[
  {
    "stem": "sadistic",
    "label": "sadistic",
    "description": "This means enjoying other people's pain for its own sake: pressing on the sore spot, savoring someone's humiliation, or dragging out the hurt when one could easily stop it.",
    "description_notes": "Everyday sense, enjoying others' pain for its own sake; not the sexual sense (kinky) and not the clinical one. Replaces cruel and takes its goal-list slot (#25). Test: does the persona enjoy the pain itself, want the harm (malicious), not mind it (callous), hurt to settle a score (vindictive), or pick on the weaker (bullying)? Doing, not watching: the vicarious strand is sadistic (Dark Tetrad)'s (W25). Seed non-X; candidate partner merciful (M3 pair-completion flag) if its check names it, so hold merciful's deletion until this check is in.",
    "nearest_existing": [
      {"stem": "malicious", "separator": "wants the harm done (harm, deceit, manipulation); overlap is its 'satisfaction in others' misfortune' clause"},
      {"stem": "evil", "separator": "wrongdoing for its own sake across the board"},
      {"stem": "malevolent", "separator": "ill will toward people's wellbeing, need not enjoy pain"},
      {"stem": "killer_bartle", "separator": "the same pleasure inside a game only"},
      {"stem": "callous", "separator": "unmoved by pain rather than pleased by it"},
      {"stem": "bullying", "separator": "picks on the weaker to stand over them"},
      {"stem": "vindictive", "separator": "hurts to settle a score"},
      {"stem": "mischievous", "separator": "pranks for the reaction, not real pain"}
    ],
    "pairing": "non-X (non-sadistic); candidate partner merciful if sadistic's check names it and merciful's recheck names sadistic",
    "tags": ["plain", "alignment", "vice pole", "roger-2026-10-09"],
    "mode": "new"
  },
  {
    "stem": "savage",
    "label": "violent",
    "description": "This means settling things with one's fists: answering a slight with a blow, reaching for whatever is at hand in a quarrel, or beating someone long after they are down.",
    "description_notes": "Rewrite of savage.json, whose present sense (cutting comebacks) is harsh's (W3 E3). Personal physical violence: not aggressive's confrontation, hostile's antagonism, hawkish's policy, irascible's temper or sadistic's pleasure. Test: does the persona hurt people with its hands or a weapon when crossed? Label is Roger's choice: violent recommended (seed_entities.py rename savage -> violent, renamed_from savage; stem becomes violent); savage keeps the stem but carries the comeback slang and the slur reading. Tell the trait-gap session first (labelled_pairs.json and corpus_regions.json name savage).",
    "nearest_existing": [
      {"stem": "aggressive", "separator": "pushes for confrontation and forceful action, not necessarily physical"},
      {"stem": "hostile", "separator": "antagonism as an attitude"},
      {"stem": "hawkish", "separator": "military force as policy"},
      {"stem": "irascible", "separator": "a short fuse that barks, not hits"},
      {"stem": "confrontational", "separator": "seeks out conflict, words not blows"},
      {"stem": "harsh", "separator": "severe words"},
      {"stem": "sadistic", "separator": "enjoys the pain; a violent person need not"}
    ],
    "pairing": "non-X (non-violent); opposed traits in the probe (peaceful, pacifist, gentle, placid) are all paired elsewhere",
    "tags": ["existing_file", "rewrite_candidate", "alignment", "vice pole", "roger-2026-10-09"],
    "mode": "rewrite"
  },
  {
    "stem": "efficient",
    "label": "efficient",
    "description": "This means getting the job done right with the least time and effort: the shortest route, no step taken twice, and stopping the moment it is finished.",
    "description_notes": "Rewrite (W10 decision 7): economy of time and effort in doing a job, not its old chatbot sense (streamlining explanations, which concise covers). Written with wasteful as a pair. Test: is the job finished properly with nothing spent beyond what it needs? Not lazy (less of the job), satisficing (stops at good enough), sloppy (rough), hurried (urgency), concise (words) or frugal (money). Relabel non-efficient (was thorough, a one-way pointer), generate, check; pair with wasteful if both name each other.",
    "nearest_existing": [
      {"stem": "concise", "separator": "economy of words only"},
      {"stem": "satisficing", "separator": "a decision style: the first good-enough option"},
      {"stem": "lazy", "separator": "does less of the job, not the job with less waste"},
      {"stem": "sloppy", "separator": "fast and rough; efficient finishes the job right"},
      {"stem": "methodical", "separator": "order and plan, possibly slow"},
      {"stem": "frugal", "separator": "money, not time and effort"}
    ],
    "pairing": "pair with wasteful, written together; rewrite procedure under non-efficient, pair if both checks name each other",
    "tags": ["existing_file", "tangle", "rewrite_candidate", "roger-2026-10-09"],
    "mode": "rewrite"
  },
  {
    "stem": "wasteful",
    "label": "wasteful",
    "description": "This means being wasteful of time and effort: the long way around, the job done twice, extra steps that serve nothing, and never a thought for the hours.",
    "description_notes": "New (W10 decision 7; queue entry wasteful, backlog). Time and effort only: money is extravagant's, and the opening qualifier keeps out the label's first sense (money, food, materials). Test: does the persona spend more time and effort than the job needs, and not mind? Not perfectionist or thorough (the extra serves quality), lazy (the opposite on effort), sloppy or careless (care, not waste), extravagant (money) or unhurried (pace). Seed non-wasteful; pair with efficient if both checks name each other.",
    "nearest_existing": [
      {"stem": "extravagant", "separator": "money spent freely, not time and effort"},
      {"stem": "lazy", "separator": "the opposite on effort: too little, not too much"},
      {"stem": "sloppy", "separator": "rough work; the fault is care, not waste"},
      {"stem": "careless", "separator": "slapdash and inattentive; rework may follow but the trait is care"},
      {"stem": "perfectionist", "separator": "extra effort that serves quality"},
      {"stem": "thorough", "separator": "depth that serves the job"},
      {"stem": "unhurried", "separator": "no urgency, which need waste nothing"}
    ],
    "pairing": "pair with efficient, written together; seed non-wasteful, pair if both checks name each other",
    "tags": ["tangle", "completion", "roger-2026-10-09"],
    "mode": "new"
  },
  {
    "stem": "future_oriented",
    "label": "future-oriented",
    "description": "This means living with one's mind on what comes next: tomorrow planned tonight, lists and goals for the months ahead, and each choice weighed by where it leads.",
    "description_notes": "The ZTPI future time perspective as a plain trait (W11 decision 11; source: gap-filling inspired by Zimbardo & Boyd (1999), ZTPI, Future factor; not an official set member by name). Test: where does the persona's mind go when nothing presses? To what comes next and how to get there. Not long-term oriented (patience for a payoff decades away), self-disciplined (will against appetite), strategic (the long game in a contest), prudent (risks), futuristic (technology) or proactive (heading off problems). No delay-of-gratification clause on purpose (self-disciplined's; a variant with it read as covered by long-term oriented). Seed non-X; label provisional (alternative forward-looking): run --name-pos after generation. Joins the ZTPI set, proposed in place of self-disciplined.",
    "nearest_existing": [
      {"stem": "long_term_oriented", "separator": "patience and thrift for a payoff decades away; never cashing in early"},
      {"stem": "self_disciplined", "separator": "will against appetite"},
      {"stem": "strategic", "separator": "the move that wins in the end in a contest or problem"},
      {"stem": "prudent", "separator": "risks seen and heeded"},
      {"stem": "futuristic", "separator": "technology and trends"},
      {"stem": "proactive", "separator": "heading off problems early"},
      {"stem": "wise", "separator": "seeing where a choice leads, plus experience"}
    ],
    "pairing": "non-X (non-future-oriented); its ZTPI opposite hedonistic is paired with ascetic",
    "tags": ["gap", "roger-2026-10-09"],
    "mode": "new"
  },
  {
    "stem": "win_win",
    "label": "win-win",
    "description": "This means treating a dispute as a shared problem: laying out what each side needs, passing up the halfway deal, and settling only when both get all of it.",
    "description_notes": "Thomas-Kilmann's collaborating mode as a plain trait (W11 decision 12; source: gap-filling inspired by Thomas & Kilmann (1974), TKI, collaborating mode; not an official set member). Assertive and cooperative at once: one's own needs met in full as well as the other side's. Test: in a dispute, does the persona hold out for a solution that gives both sides all they need, rather than giving way (accommodating), splitting the difference (peaceful, agreeable (HEXACO)), making peace (conciliatory) or winning (confrontational, competitive)? Not cooperative's general teamwork or collaborative's shared work. Seed non-X; label provisional: run --name-pos after generation. Compromising not seeded: covered in pieces.",
    "nearest_existing": [
      {"stem": "cooperative", "separator": "teamwork and shared success in general, not a dispute"},
      {"stem": "conciliatory", "separator": "makes peace between sides; may take the halfway deal"},
      {"stem": "peaceful", "separator": "settles for less rather than fight"},
      {"stem": "accommodating", "separator": "gives up one's own stance"},
      {"stem": "agreeable_hexaco", "separator": "meets people halfway"},
      {"stem": "collaborative", "separator": "working with others on a job"}
    ],
    "pairing": "non-X (non-win-win); TKI's opposite avoidant is general withdrawal, competitive and confrontational are paired elsewhere",
    "tags": ["gap", "roger-2026-10-09"],
    "mode": "new"
  }
]
```

[accommodating]: ../../data/traits/instructions/accommodating.json
[aggressive]: ../../data/traits/instructions/aggressive.json
[agreeable]: ../../data/traits/instructions/agreeable.json
[agreeable (HEXACO)]: ../../data/traits/instructions/agreeable_hexaco.json
[ambitious]: ../../data/traits/instructions/ambitious.json
[ascetic]: ../../data/traits/instructions/ascetic.json
[avoidant]: ../../data/traits/instructions/avoidant.json
[bitter]: ../../data/traits/instructions/bitter.json
[bullying]: ../../data/traits/instructions/bullying.json
[callous]: ../../data/traits/instructions/callous.json
[careless]: ../../data/traits/instructions/careless.json
[circumspect]: ../../data/traits/instructions/circumspect.json
[collaborative]: ../../data/traits/instructions/collaborative.json
[compassionate]: ../../data/traits/instructions/compassionate.json
[competitive]: ../../data/traits/instructions/competitive.json
[conciliatory]: ../../data/traits/instructions/conciliatory.json
[concise]: ../../data/traits/instructions/concise.json
[confrontational]: ../../data/traits/instructions/confrontational.json
[cooperative]: ../../data/traits/instructions/cooperative.json
[cruel]: ../../data/traits/instructions/cruel.json
[deliberate]: ../../data/traits/instructions/deliberate.json
[efficient]: ../../data/traits/instructions/efficient.json
[evil]: ../../data/traits/instructions/evil.json
[extravagant]: ../../data/traits/instructions/extravagant.json
[fair]: ../../data/traits/instructions/fair.json
[fatalistic]: ../../data/traits/instructions/fatalistic.json
[focused]: ../../data/traits/instructions/focused.json
[frugal]: ../../data/traits/instructions/frugal.json
[future-oriented]: ../../data/traits/instructions/future_oriented.json
[futuristic]: ../../data/traits/instructions/futuristic.json
[futurist]: ../../data/roles/instructions/futurist.json
[gentle]: ../../data/traits/instructions/gentle.json
[good]: ../../data/traits/instructions/good.json
[harsh]: ../../data/traits/instructions/harsh.json
[hawkish]: ../../data/traits/instructions/hawkish.json
[hedonistic]: ../../data/traits/instructions/hedonistic.json
[hostile]: ../../data/traits/instructions/hostile.json
[hurried]: ../../data/traits/instructions/hurried.json
[impulsive]: ../../data/traits/instructions/impulsive.json
[industrious]: ../../data/traits/instructions/industrious.json
[irascible]: ../../data/traits/instructions/irascible.json
[killer (Bartle)]: ../../data/traits/instructions/killer_bartle.json
[kinky]: ../../data/traits/instructions/kinky.json
[lazy]: ../../data/traits/instructions/lazy.json
[long-term oriented]: ../../data/traits/instructions/long_term_oriented.json
[malevolent]: ../../data/traits/instructions/malevolent.json
[malicious]: ../../data/traits/instructions/malicious.json
[mediator]: ../../data/roles/instructions/mediator.json
[merciful]: ../../data/traits/instructions/merciful.json
[methodical]: ../../data/traits/instructions/methodical.json
[mischievous]: ../../data/traits/instructions/mischievous.json
[moderate]: ../../data/traits/instructions/moderate.json
[negotiator]: ../../data/roles/instructions/negotiator.json
[nostalgic]: ../../data/traits/instructions/nostalgic.json
[organized]: ../../data/traits/instructions/organized.json
[pacifist]: ../../data/traits/instructions/pacifist.json
[patient]: ../../data/traits/instructions/patient.json
[peaceful]: ../../data/traits/instructions/peaceful.json
[perfectionist]: ../../data/traits/instructions/perfectionist.json
[placid]: ../../data/traits/instructions/placid.json
[planner]: ../../data/roles/instructions/planner.json
[proactive]: ../../data/traits/instructions/proactive.json
[problem-solving]: ../../data/traits/instructions/problem_solving.json
[prudent]: ../../data/traits/instructions/prudent.json
[sadistic]: ../../data/traits/instructions/sadistic.json
[sadistic (Dark Tetrad)]: ../../data/traits/instructions/sadistic_dark_tetrad.json
[sassy]: ../../data/traits/instructions/sassy.json
[satisficing]: ../../data/traits/instructions/satisficing.json
[savage]: ../../data/traits/instructions/savage.json
[self-disciplined]: ../../data/traits/instructions/self_disciplined.json
[short-term oriented]: ../../data/traits/instructions/short_term_oriented.json
[sloppy]: ../../data/traits/instructions/sloppy.json
[spiteful]: ../../data/traits/instructions/spiteful.json
[strategic]: ../../data/traits/instructions/strategic.json
[superficial]: ../../data/traits/instructions/superficial.json
[thorough]: ../../data/traits/instructions/thorough.json
[unhurried]: ../../data/traits/instructions/unhurried.json
[verbose]: ../../data/traits/instructions/verbose.json
[vindictive]: ../../data/traits/instructions/vindictive.json
[violent]: ../../data/traits/instructions/violent.json
[wasteful]: ../../data/traits/instructions/wasteful.json
[win-win]: ../../data/traits/instructions/win_win.json
[wise]: ../../data/traits/instructions/wise.json
