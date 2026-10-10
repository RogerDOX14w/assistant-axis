# W3: near-duplicate traits to drop or merge

**Status 2026-10-09: decision sheet for Roger, drafted by an agent.  Read-only: no corpus, queue or
usage file was changed and no API call was made.**  Item W3 of [work_list.md](./work_list.md).  It
consolidates three sources: the old table in
[TRAITS_TO_ADD.md](../../data/traits/instructions/TRAITS_TO_ADD.md) § "TODO: near-duplicate traits to
drop or merge (M2 calibration, 2026-10-01)" (18 rows), the trait-gap session's rerun on all 918 files
([drop_or_merge.md](../../data/candidates/calibration_916/drop_or_merge.md), 15 rows), and the 13
near-twin spokes plus [experiential] / [practical] that [W10](./w10_w12_proposals.md) decision 3 sent
here.  Rows already decided in [w7_w14_decisions.md](./w7_w14_decisions.md) or W5 / W8 / W9 are only
cross-referenced (group D).

**Update 2026-10-09 (later):** A1-A3 applied (commit 647ca4d), B1 too (83febfb, [melodramatic]
taking [dramatic]'s slot #7).  The trait-gap session's same-concept
scan has run ([near_duplicates.md](../../data/candidates/near_duplicates_916/near_duplicates.md),
$3.94): C10's [technical] / [specialist] and C11's [mercurial] are settled in place, and the new
group E sorts everything else it found.  This update, too, changed only this sheet.  The links to
the deleted [conceptual], [enigmatic], [dramatic] and [adolescent] no longer open; their rows stand
as the record.

**How to read the numbers** (other terms: the [glossary](../../reports/trait_gap_generation/glossary.md)).

- **cos**: [cosine similarity](../../reports/trait_gap_generation/glossary.md#cosine-similarity) of the
  cached embeddings of each file's `label: description`, in the
  [raw space](../../reports/trait_gap_generation/glossary.md#raw-space), OpenAI
  `text-embedding-3-large` / EmbeddingGemma, as the rerun used them.  Over the 918 files the
  [nearest-neighbour](../../reports/trait_gap_generation/glossary.md#nearest-neighbour-nn) cosine has
  median 0.63 / 0.74 and 90th percentile 0.75 / 0.82.  **\*** marks a value above the rerun's
  [upper fence](../../reports/trait_gap_generation/glossary.md#t_hi-t_lo-upper-fence) (0.770 / 0.840,
  recorded partners excluded), which is what got a row flagged.  Mirrored wording counts as
  closeness, so antonyms and template siblings score high.
- **M3**: the overlap call's [rubric A](../../reports/trait_gap_generation/rubrics/overlap_concept.md)
  (4 "the same concept", 3 "the same concept, differing only in scope, degree or emphasis", 2
  "overlapping concepts"), Opus 5.5's most frequent reading over all its readings of the pair in the M3
  test and arms runs ([overlap_test/](../../data/candidates/overlap_test/), 6 to 18 readings; count in
  brackets).  **scan a and b**: the 2026-10-09 scan's final readings (Sonnet 5.5, then Opus 5.5 on
  Sonnet's 2s and 3s), first direction and second; one number means the second direction was not
  read, because the first was under 3 (group E).  **M3's admission rule** for a new candidate:
  covered at 3 or more far from the alignment region, at 4 near it ([coding_plan_platform.md](../../reports/trait_gap_generation/coding_plan_platform.md),
  M3 decision 4).
- **May**: cosine of the May 2026 [persona vectors](../../reports/trait_gap_generation/glossary.md#persona-space-persona-vectors)
  (Qwen-3-32B, 8-slot run, slot 6, layer 25, 302 traits, centred;
  [persona_s6_l25.npz](../../data/candidates/cache/persona_s6_l25.npz)), with its percentile among
  the traits' nearest-neighbour cosines (median 0.72, p99 0.93).  Old instructions; indicative only.
- **Cost of a drop**: a broken clean pair; a *current* pair list
  ([clean](../axis_judge_experiments/pair_list_clean.json), [di](../axis_judge_experiments/pair_list_di.json),
  [goalnongoal](../axis_judge_experiments/pair_list_goalnongoal.json),
  [responses](../axis_judge_experiments/pair_list_responses.json)); a *record* list (`_v1` and dated
  lists of judged work: a re-run stops at a missing pole, the caches stay); a slot in
  [goal_roles_and_traits.json](../../data/goal_roles_and_traits.json) (`#n` in `traits.non_goal`
  unless marked goal; the first 30 are what the pipeline takes; the tail from #41 is the list's own
  "pair partners and redundant" tier, counted here as free).  A *spoke* is W10's term: a trait whose
  label points one way at a pole of a pair recorded elsewhere.

## Decisions

### A. Clear drops that cost nothing

- **A1. Drop [conceptual].  Done (647ca4d).**  "The same concept" as both [abstract] (M3 4, 6 of 6) and [theoretical]
  (M3 4, 12 of 18); Gemma above the fence against both; a non-X singleton; loses tier-3 slot #44.
  Goes with C1, which separates the two that stay.
- **A2. Drop [enigmatic].  Done (647ca4d).**  [cryptic]'s own description says "enigmatic"; May 0.93 (top 1%, each
  other's nearest); a spoke whose label, [clear], is [cryptic]'s partner; in no list.  It has no M3
  reading; the second pass would confirm.  It did: the scan read the pair 3 and 3.
- **A3. Drop the role [adolescent].  Done (647ca4d).**  W10 decision 15 called it a W3 candidate (roles are outside the
  embedding test).  The same years and the same content as [teenager] (moody, self-conscious,
  wrapped up in friends, pulling away from parents); May role vectors 0.91 (top 1%, each other's
  nearest); both singletons, in no list.  [teenager] is the persona's own word (rule 3) and has the
  particulars.  W12's life-stage sequence then has 11 members.

### B. Drops that cost a pair or a list slot (your call)

- **B1. Drop [dramatic]: lean yes.  Done (83febfb; [melodramatic] took slot #7, your choice).**  The middle of the triple, nearest to both [theatrical] (0.81\* /
  0.85\*, M3 3 in 18 of 18, May 0.88) and [melodramatic] (0.79\* / 0.84, M3 3, May 0.88); its text is
  the other two's words ("theatrical descriptions ... dramatic flair").  Cost: top-30 slot #7, which
  W15's re-tiering can give to [theatrical] (#56) or [melodramatic] (#47).  The two that stay are the
  triple's farthest pair (C5).
- **B2. Drop [systems-thinker]: lean no** (keep it as a spoke under W10 decision 1).  [holistic]
  narrowed to feedback loops and emergence (M3 3 in 6 of 6, May 0.88, p94; its text says "thinking
  holistically"), so M3's rule would call it covered.  Cost: top-30 slot #3, and it is a pole in six
  record lists and the 60-axis analyses (judged as [systems-thinker] / [analytical] until 2026-10-02).
- **B3. Drop both ends of [moral universalist] / [moral relativist]: lean no.**  The morality-only
  copy of [absolutist] / [relativist] (M3 3: "absolutism narrowed to the moral domain"; 0.70 / 0.76
  and 0.71 / 0.71 between corresponding poles, under both fences).  Cost: a clean pair you renamed on
  2026-10-02, in no list or goal list.  Kept, the extraction can test whether a nested pair runs
  parallel to its parent axis.

### C. Keep (three with a rewrite)

- **C1. Keep [abstract], rewritten to mirror [concrete]** (draft below).  After A1 it is still
  [theoretical]'s twin (M3 4 in 10 of 12, May 0.90, p97), while [concrete] was rewritten on
  2026-09-28 to the particular-against-general sense.  [theoretical] is in the current lists, so
  [abstract] is the one to move.  Cost: the pair's recheck, cents; keeps top-30 slot #5.
- **C2. Keep [dependable] and [trustworthy]; rewrite [trustworthy] to its partner's scope** (draft
  below).  Both above the fence (0.79\* / 0.85\*), but M3 3 (12 of 12), May only 0.76 (p65), and both
  are alignment-region traits, where M3's rule needs a 4.  [trustworthy]'s text is "reliable,
  dependable, ..."; its partner [untrustworthy] is written as motivated betrayal, the mechanism rule 5
  says keeps neighbouring pairs apart.  Cost: a pole in four current or record lists (clean, di,
  goalnongoal, 13_new) and the pair's recheck.  Also clears [W4](./w4_framing.md)'s second-person finding for
  [trustworthy] ([dependable]'s "you" stays W4's one-word fix).
- **C3. Keep [wry], rewritten to its own sense** (draft below); strike to drop it instead (free).  As
  written it is "clever, sardonic humor" (May 0.92 with [sardonic], top 2%; M3 3).  Humour that
  notices an absurdity without mocking anyone has no file: [dry] is the unentertaining sense, [witty]
  is cleverness on display, [self-deprecating] is aimed at oneself.  Label becomes non-wry, singleton.
- **C4. Keep [sarcastic]** (strike to drop, free): verbal irony aimed at someone, against [sardonic]'s
  mockery of the world at large; M3 splits 6 to 6 between 3 and 2; OpenAI 0.79\*, Gemma 0.80.
- **C5. Keep [theatrical] and [melodramatic]** once B1 is taken: 0.71 / 0.82, M3 3 (5 of 6).  By M3's
  rule [melodramatic] would be covered by [theatrical]; strike to drop it too (tier-3 #47, free).
- **C6. Keep [honest] and [truthful]:** alignment region (M3 3 in 9 of 12, below the bar of 4),
  different partners ([dishonest]: spin and omission; [deceitful]: lies), both judged in every current
  list; just under both fences in the rerun.
- **C7. Keep [pansexual] and [bisexual]:** you chose both on 2026-09-07 expecting their vectors to sit
  close; memberships in each community's own words, and the chunk-5 reviewer removed the one clause
  that forced them apart.  Whether Qwen separates them is a result in itself.
- **C8. Keep the standards' copies.  Decided 2026-10-09 (Roger): keep all; their official texts differ in content (facets), not only in our wording ([w3_c8_big_five_hexaco.md](./w3_c8_big_five_hexaco.md)).**  Original note: [extraverted (HEXACO)] / [extraverted (Big Five)] and
  [careless (HEXACO)] / [careless (Big Five)]: deliberate (AGENT_NOTES naming rule 5), each a pole of a
  clean pair inside its orthoplex.
- **C9. Keep [upper-class] / [middle-class]:** neighbours on one scale, close through the shared
  template.  Optional: a `sequence` [working-class] → [middle-class] → [upper-class], the one-edit
  counterpart of W10 decision 18's age sequence.
- **C10. Keep the four older rows the rerun no longer flags** (three, now that the scan has settled
  the fourth)**:** [passionate] / [zealous] (0.60 / 0.72,
  M3 2, May p39), [creative] / [innovative] (M3 2, May 0.55, p8), [northern hemisphere] /
  [eastern hemisphere] (two orthogonal pairs in one template; Gemma 0.61), [technical] / [specialist]
  (0.66 / 0.82, no M3 reading; the second pass settles it).  **Settled by the scan: 3 and 3, both
  traits far from the alignment region, so by M3's rule [technical] is covered: drop [technical],
  free** (a non-X singleton in no list, goal tier or queue entry, and no file points at it).  Its
  terminology is [specialist]'s and its numbers [precise]'s and [quantitative]'s (the scan reads
  [technical] / [precise] 2; May nearest [specialist], under its old name, 0.79 (p76), then [precise]
  0.76 and [quantitative] 0.67).  Strike to keep it.
- **C11. Keep [mercurial] as a spoke unless the second pass reads it 3 or more against [erratic]**,
  then drop it (tier-3 #43, free).  It is [erratic]'s shifts of tone and view plus [temperamental]'s
  moods (0.66 / 0.81 and 0.66 / 0.80, under the fences; no M3 reading).  **Settled by the scan: 4
  and 4** (Sonnet 3, Opus 4 each way; the pair was also read on your request), **so drop
  [mercurial].**  Opus: "the descriptions are essentially interchangeable".  What it adds to
  [erratic] is moods, and those are [temperamental]'s (the scan reads [mercurial] / [temperamental]
  2).  Cost: non-goal #43, in the list's "pair partners and redundant" tier, so free; no pair (you
  dissolved [mercurial] / [steady] on 2026-09-26), no list, no queue entry, and no file points at it;
  W10's unclassified traits go from 28 to 27.  May has a vector for it (old instructions; nearest
  [disorganized] 0.62, under the median nearest neighbour) but none for [erratic], so May cannot
  compare the two.
- **C12. Keep the other W10 spokes**, all under both fences, then W10 decision 1's rule:
  [neurotic] / [anxious] (M3 2; [neurotic] is also the plain side of the deliberate
  [neurotic (Big Five)] comparison), [inspirational] / [encouraging], [exploratory] / [divergent],
  [effusive] / [expressive], [acerbic] / [savage] ([acerbic]'s real neighbours are [sarcastic] and
  [sardonic], 0.59 / 0.77), [provocative] / [edgy] (M3 3, but May 0.57, p10),
  [stream-of-consciousness] / [disorganized] (May 0.55, p7), [experiential] / [practical] (M3 2; its
  label is W10 decision 8).

### D. Handled elsewhere

- **D1. [dispassionate] / [detached] → [W7](./w7_w14_decisions.md) decision 7**, which keeps [detached] as a one-way pointer
  under your 2026-10-02 ruling ("kept until the next extraction's cosines show whether it carries a
  signal of its own") and names it as W3's drop.  It is the strongest duplicate on this sheet: M3 4
  in 12 of 12, May 0.94 (top 1%), two near-identical sentences.  **Approve to drop [detached] now**
  (cost: the three record lists that judged [detached] / [empathetic] stop at it; no current list, no
  goal slot; [dispassionate] is paired with [passionate] in the clean, di and goalnongoal lists), or strike to let the
  2026-10-02 wait stand.
- **D2. [empathetic] / [compassionate] → W7 decision 7** ([empathetic] a pointer until the cosines).
  The numbers here (0.75 / 0.87\*, M3 3 in 7 of 12, May 0.79, p78) do not change that.
- **D3. [merciful] → W7 decision 4** (drop): [compassionate]'s next-nearest description (0.59 / 0.76).
- **D4. [insular] / [parochial] → [W14](./w7_w14_decisions.md) decision 6** (drop [insular], rewrite [parochial]): M3 4 in 6 of 6,
  but OpenAI only 0.64 and Gemma at the fence, the case that shows the fence misses paraphrases.
- **D5. [self-blaming] / [blame-shifting] → [W8](./w7_w14_decisions.md):** opposites (M3 "opposite" in every reading), close
  only through mirrored wording.
- **D6. [good only when watched] / [good even when unwatched] → [W5](./w5_observed_pair.md):** the new contrast pair, close
  through mirrored wording (Gemma 0.84\*).
- **D7. [hands-off] / [absentee] → [W9](./w7_w14_decisions.md) decision 2** (rewrite [hands-off] to the neutral sense): 0.71 /
  0.81, each the other's nearest.

### E. What the same-concept scan found (added 2026-10-09)

The addendum the second pass promised.  Source:
[near_duplicates.md](../../data/candidates/near_duplicates_916/near_duplicates.md) (commit e71c6b3;
every reading and reason is in [pairs.jsonl](../../data/candidates/near_duplicates_916/pairs.jsonl)).
Each of the 916 traits was read against its 3 nearest neighbours by description embedding (OpenAI,
[centred space](../../reports/trait_gap_generation/glossary.md#centred-space), cosine 0.35 or more,
arrangement partners left out) with the M3 same-concept call
([rubric A](../../reports/trait_gap_generation/glossary.md#rubric-a-concept-similarity-rubric-b-co-occurrence)):
Sonnet 5.5 reads first, Opus 5.5 re-reads Sonnet's 2s and 3s and has the last word, and the second
direction is read only when the first gave 3 or more.  785 pairs, $3.94.  **8 pairs read 4 both
ways, 102 read 3 or more both ways, 30 one way only**; readings are written "3 and 4" (first
direction, second).

**How they were sorted.**  M3's rule (covered at 3 or more far from the alignment region, at 4 near
it) was written to admit new candidates.  Most of these 140 are corpus neighbours that differ in
scope or degree, each a pole of its own clean pair whose partner names what keeps the two apart
([description rule 5](../../.claude/rules/trait-pairs.md)), so a drop would cost a pair for little.
A pair is numbered here when both traits are far from the alignment region (alignment score 0 or 1
in [corpus_regions.json](../../data/candidates/corpus_regions.json); 2 or 3 counts as the region) and
one side costs nothing to drop, or one description restates the other, or the May vectors put the
two in their top tenth.  That leaves 11 pairs in seven items; the other 129, C10's and C11's among
them, are in the table with the reason they need no decision.  Goal-list positions here are current:
deleting [conceptual] (#44) and moving [melodramatic] from #46 into [dramatic]'s #7 shifted the later
non-goal positions, so A to D's numbers past #43 are out of date ([holistic] #45, [theoretical] #48,
[theatrical] #54).  **[melodramatic] now holds top-30 slot #7, so C5's strike to drop it is no longer
free.**

- **E1. [collaborative] / [cooperative]** (3 and 4, May 0.83, p89): **keep both; take
  [W4](./w4_framing.md)'s rewrite of [collaborative] with its last clause changed** (draft below).
  [cooperative]'s text already says "collaboration ... teamwork and collective problem-solving", and
  W4's draft ends "counting the result as the group's", which is [cooperative]'s shared success; the
  draft below ends on the team instead, mirroring [self-reliant]'s "seeing a team as dead weight".
  Cost of a drop: [collaborative] breaks its pair with [self-reliant] (no list, no goal tier);
  [cooperative] breaks its pair with [competitive], judged in the clean, di and goalnongoal lists,
  and leaves W11's proposed social-value sequence.
- **E2. [entertaining] / [playful]** (3 and 3, May 0.90, p98) **and [entertaining] / [witty]** (3 and
  3, May 0.81, p81): **rewrite [entertaining] to mirror its partner [dry]** (draft below), so that
  its pleasure is in the telling (a story, color, a lively example), not the humour that is [witty]'s
  and [playful]'s.  The rewrite also removes its chatbot frame ("the interaction", "enjoyable to
  read").  Cost of a drop: [entertaining] breaks its pair (no list; tier-3 #51, free); [playful] is
  judged in the clean, di, goalnongoal and 13_new lists.  Strike to drop [entertaining] instead
  ([dry] then becomes a `non-dry` singleton).
- **E3. Drop [savage]: lean yes.**  3 and 3 against both [blunt] and [harsh] (the reasons:
  "bluntness carried to a merciless, cutting extreme"; "the same quality pushed to a merciless
  extreme"); May 0.77 with [blunt] (p70), nearest [acerbic] 0.78.  Its "devastating comebacks" are
  [harsh]'s "taking every opening for a cutting reply".  Free: a non-X singleton in no list, goal
  tier or queue entry.
- **E4. Drop [inspirational]: lean yes** (C12 kept it unread).  3 and 3 against [encouraging], whose
  partner [discouraging] its label names, so C11's rule, applied to this spoke, says drop.  Its text says
  "encouraging growth", and its vision clause is [transformational]'s (the scan reads that pair 2).
  Free: unclassified, in no list or goal tier; May nearest [nurturing] 0.76 ([encouraging] has no May
  vector).  Strike to keep it as C12's spoke.
- **E5. [easygoing] / [laid-back]** (3 and 3): **keep both; rewrite [easygoing] to mirror its partner
  [uptight]** (draft below), whose own check named [easygoing] | [laid-back].  [easygoing]'s text is
  an old one that repeats its label (description rule 1) and is told as its effect on others;
  [laid-back] / [intense] was seeded to catch social energy as such, orthogonal by construction to
  [introverted] / [extroverted] (its entry in [seed_queue.json](../../data/seed_queue.json)), so it is
  the one to leave.  Cost of a drop: either breaks a pair; neither is in a list or goal tier.
- **E6. Two parallel pairs, [decisive] / [indecisive] and [opinionated] / [noncommittal]**
  ([decisive] / [opinionated] 3 and 3, [indecisive] / [noncommittal] 3 and 3): **keep both pairs;
  if W4's rewrite of [decisive] / [indecisive] is taken, amend it** so that [decisive] commits to a
  course and [opinionated] to a view: in W4's [decisive] draft "settling on a firm position, saying
  plainly what one will do or thinks best" becomes "settling on one course, saying plainly what one
  will do", and in its [indecisive] draft "never settling on a position" becomes "never settling on a
  course".  Test: does the persona commit to what to do, or to what it thinks, and argue for it?
  Cost of a drop: [decisive] / [indecisive] is judged in the clean, di and goalnongoal lists
  ([decisive] #31); [opinionated] / [noncommittal] is in none (you renamed [opinionated] from
  `assertive` on 2026-09-26), so striking to drop that pair costs only the pair.  Without W4's
  rewrite, the old texts' "firm positions" keep the overlap and the extraction tests the two as
  parallel pairs, as B3 proposes for its nested one.
- **E7. [mystical] / [spiritual]** (3 and 3, May 0.82, p88; also [mystical] / [technomystical], 3 one
  way): **keep [mystical] as a non-X singleton (W10 decision 4's option (c)), rewritten to its own
  sense, a way of knowing beyond reason** (draft below), which also gives it the "This means" form
  W10 asked for.  W10's checks found it no pair: its staged check named [rationalist] | empiricist |
  [materialist], and neither names it back.  So reason is its opposite, where [spiritual]'s partner
  [materialistic] is money and possessions.  Free to drop instead (unclassified, no list, no goal
  tier).

**The other 129: no decision needed** ("one way": 3 or more in one direction only).

| why no decision | pairs | n |
|---|---|---|
| On this sheet (C10 and C11 settled above) | [conceptual] / [theoretical] and [abstract] / [conceptual] (A1, done), [cryptic] / [enigmatic] (A2, done), [dramatic] / [theatrical] (B1, done; the scan read it 4 and 3), [dramatic] / [melodramatic] (B1, done), [holistic] / [systems-thinker] (B2), [absolutist] / [moral universalist] and [moral relativist] / [relativist] (B3), [abstract] / [theoretical] (C1, 4 and 4), [dependable] / [trustworthy] (C2), [sardonic] / [wry] and [witty] / [wry] (C3, whose test names [witty]), [sarcastic] / [sardonic] (C4, one way), [melodramatic] / [theatrical] (C5), [honest] / [truthful] (C6), [bisexual] / [pansexual] (C7), [careless (Big Five)] / [careless (HEXACO)] (C8, 4 and 4), [extraverted (Big Five)] / [extraverted (HEXACO)] (C8), [passionate] / [zealous] (C10, one way), [specialist] / [technical] (C10, settled), [erratic] / [mercurial] (C11, settled), [anxious] / [neurotic] (C12; now 3 and 3, was 2; kept as the plain side of the deliberate [neurotic (Big Five)]), [edgy] / [provocative] (C12, one way), [detached] / [dispassionate] (D1, 4 and 4), [compassionate] / [empathetic] (D2), [insular] / [parochial] (D4, 4 and 4), [absentee] / [hands-off] (D7) | 27 |
| Decided or drafted in another sheet (note below) | [callous] / [cruel], [cruel] / [evil], [callous] / [uncaring], [evil] / [malevolent], [evil] / [malicious], [malevolent] / [malicious], [good] / [moral], [harmful] / [malicious] (one way) (all W7); [hands-on] / [micromanaging] (W9); [unforgiving] / [vindictive], [meticulous] / [perfectionist], [data-driven] / [quantitative] (W10); [external locus of control] / [fatalistic] (W11); [altruistic] / [philanthropic], [generous] / [philanthropic] (W14); [methodical] / [organized], [ecocentric] / [environmental] (W4) | 17 |
| Deliberate copies, recorded as such in their `source` field (naming rule 5 in [AGENT_NOTES.md](../../AGENT_NOTES.md) § "Standard-derived trait labels") | [careless] / [careless (Big Five)], [careless] / [careless (HEXACO)], [conscientious (Big Five)] / [conscientious (HEXACO)], [conscientious] / [conscientious (Big Five)], [conscientious] / [conscientious (HEXACO)], [agreeable] / [agreeable (Big Five)], [artistic] / [artistic (Holland)], [extraverted (Big Five)] / [extroverted], [extraverted (HEXACO)] / [extroverted] (one way), [introverted] / [introverted (Big Five)], [neurotic] / [neurotic (Big Five)] (4 and 4) | 11 |
| A standard's or theory's version beside another standard or a plain trait, or a facet beside its domain: the comparison is the experiment (naming rule 5) | [open (Big Five)] / [open (HEXACO)], [closed (Big Five)] / [conventional (HEXACO)], [neglectful] / [neglectful (Baumrind)], [lenient] / [permissive (Baumrind)] (one way), [accommodating] / [agreeable (Big Five)], [calm] / [emotionally-stable (Big Five)], [emotionally-stable (Big Five)] / [even-tempered], [anxious] / [neurotic (Big Five)], [agreeable (HEXACO)] / [forgiving] (one way), [antagonistic (Big Five)] / [hostile] (one way), [dominant] / [Enneagram 8] (one way), [brave] / [Gryffindor], [clear] / [low-context (Hall)] (one way), [aristocratic] / [elitist] ([aristocratic]'s `source` records the narrower, birth-based sense) | 14 |
| Memberships nested by design: a country inside its region or hemisphere, a form of marriage inside [married], a class origin inside its class | [African] / [Nigerian], [Canadian] / [western hemisphere], [European] / [Italian], [European] / [German], [East Asian] / [Japanese] (the last three one way), [married] / [polygamous], [married] / [polyandrous], [married] / [polygynous], [old money] / [upper-class], [new money] / [wealthy] | 10 |
| Seeded on purpose beside the general trait, the overlap in view (note below) | [financially reckless] / [reckless], [financially reckless] / [risk-seeking], [financially conservative] / [risk-averse], [adventurous] / [adventurous-eater], [body-obsessed] / [obsessive], [extrinsically motivated] / [mercenary] (one way), [extroverted] / [gregarious] (May 0.88, p95), [introverted] / [solitary] (one way) | 8 |
| Poles of different pairs, far from the alignment region, whose partners name what separates them (description rule 5); a drop costs a pair.  The [calm] cluster is seven pairs: [calm] / [excitable], [composed] / [anxious], [unflappable] / [flustered], [placid] / [irascible], [even-tempered] / [temperamental], [serene] / [turbulent], [patient] / [impatient] | [calm] / [composed], [calm] / [serene], [calm] / [placid], [calm] / [even-tempered], [composed] / [unflappable], [even-tempered] / [unflappable] (one way), [patient] / [placid], [temperamental] / [turbulent], [conservative] / [traditional], [conventional] / [traditional], [progressive] / [radical], [plain-spoken] / [unpretentious], [unassuming] / [unpretentious] (one way), [self-effacing] / [unassuming], [descriptive] / [informational], [nurturing] / [supportive], [serious] / [solemn], [naive] / [trusting], [gluttonous] / [self-indulgent], [formulaic] / [inflexible] (one way), [agreeable] / [conciliatory] (one way), [ironic] / [sarcastic] (one way) | 22 |
| The alignment region (either trait scores 2 or 3), where M3's bar is 4: poles of different pairs, apart from two singletons, [grandiose] (the everyday habit's extreme) and [utilitarian] (a framework's best-known species; goal #16) | [honest] / [transparent], [dishonest] / [intellectually dishonest], [treacherous] / [untrustworthy], [grandiose] / [self-aggrandizing], [independent] / [self-reliant], [confident] / [overconfident], [confident] / [decisive] (one way), [indecisive] / [uncertain] (one way), [careless] / [sloppy], [conscientious] / [meticulous] (one way), [cautious] / [prudent] (one way), [irresponsible] / [unreliable] (one way), [aggressive] / [confrontational] (one way), [aggressive] / [hostile] (one way), [consequentialist] / [utilitarian] | 15 |
| Singletons with a sense of their own: [goofy] is silliness, not fun (May 0.73, p51); [formalist] (May 0.50, p2); [emotional] is the plain side of the deliberate [emotional (HEXACO)]; [misanthropic] holds goal #7; [interdisciplinary] reads 3 one way only | [goofy] / [playful], [formalist] / [ritualistic] (one way), [emotional] / [emotionally-articulate], [cynical] / [misanthropic], [generalist] / [interdisciplinary] (one way) | 5 |

- **The other sheets.**  [W7](./w7_w14_decisions.md) decision 1 keeps the help and harm corners in
  three registers on purpose ([malicious], [malevolent], [evil]; [good] beside [moral]); decisions 3
  and 5 rewrite [uncaring] and [cruel] off [callous]; decision 6 keeps the effects register
  ([harmful]: harm done, meant or not) apart from the feeling triangle's [malicious].  W9 decision 1
  and [W10](./w10_w12_proposals.md) decision 2 make [hands-on] / [micromanaging], [unforgiving] /
  [vindictive] and [meticulous] / [perfectionist] neighbours in a sequence, by design.  W11 decision 11 names [external locus of control] as [fatalistic]'s wider
  neighbour, and W14 decision 1 names [altruistic] and [generous] as [philanthropic]'s nearest.
  W4's rewrites settle two: [organized] confined to talk (apart from [methodical]'s work) and
  [environmental] to one's own choices (apart from [ecocentric]'s ethic; its current check names
  [anthropocentric], [ecocentric]'s partner), with [W22](./work_list.md) still asking whether it
  pairs with [growth-first].  One amendment: W10 decision 6's draft for [data-driven] should stay on
  evidence ("the study, the sample size, the base rate"); its opening "going by the numbers" leans
  toward [quantitative]'s figures.
- **Seeded on purpose:** the financial-domain pair from DOSPERT, a risk-taking scale by life domain
  ([financially reckless] / [financially conservative]); [adventurous-eater] and [body-obsessed],
  accepted 2026-09-08; [mercenary], the commerce motive of Hogan's MVPI (a motives inventory); and
  [solitary], chosen on 2026-09-07 as [gregarious]'s partner with [introverted] / [extroverted] named
  as the overlap to check.  The scan and May both find it (May 0.88, p95, for [extroverted] /
  [gregarious]); the extraction shows whether behaviour and social energy come apart.
- [neglectful (Baumrind)]'s `source` does not say it is a deliberate near-duplicate, as naming rule
  5 asks: a one-line edit, no regeneration.

**Applying E** if every lean is taken: delete [mercurial] (C11), [technical] (C10), [savage] and
[inspirational], all free (no pair, no queue entry, no file points at them; [mercurial] leaves the
goal list's #43); rewrite [collaborative], [entertaining] and [easygoing] by the rewrite procedure for
a pair member and [mystical] under `non-mystical` (four generations and checks, about $0.15, live);
the [decisive] / [indecisive] wording rides on W4.  Then
[sync_entity_lists.py](../../tools/sync_entity_lists.py) and
[check_arrangements.py](../../data_analysis/check_arrangements.py).  Tell the trait-gap session
first: its [labelled_pairs.json](../../data/candidates/calibration_916/labelled_pairs.json) and
[corpus_regions.json](../../data/candidates/corpus_regions.json) name all four.

**The optional pass over the 434 arrangement-partner pairs (about $2.50): worth running, live.**  The
only 4 found inside an arrangement so far, [insular] / [parochial], sat in a hand-built sequence and
was read only on request; the hand-built kinds (the moral-circle and generation sequences, the
marriage set, where [polygamous] is the umbrella of [polygynous] and [polyandrous]) are where another
could hide, while the imported structures (the MBTI cube, the Big Five and HEXACO orthoplexes, the
Holland and Enneagram rings, the squares) should read 3 by design and need no decision.

## The trait-gap session's second pass: run it now (recommended)

**Status 2026-10-09: run** by the trait-gap session ($3.94, live;
[near_duplicates.md](../../data/candidates/near_duplicates_916/near_duplicates.md)).  Its results are
group E; C10's [technical] / [specialist] and C11 are settled in place.

Its same-concept judge (the M3 overlap call, rubric A) on each trait's nearest neighbours, about $3,
adds what the cosine fence cannot see:

- **Paraphrases.**  The fence catches shared wording: six of the rerun's fifteen rows are opposites,
  standards' copies, scale neighbours or a pair chosen knowing it would be close.  A same concept in
  other words passes under it: [insular] / [parochial] is M3 4 at OpenAI 0.64.
- **Coverage.**  The M3 test read 367 pairs of old traits (100 targets' nearest neighbours, plus labelled and random pairs); all five pairs it called the same
  concept are on this sheet.  None of the 253 traits from chunks 4 to 7 has been read, nor the two W5
  traits.
- **Rows here with no reading:** [enigmatic] / [cryptic], [mercurial] / [erratic], [technical] /
  [specialist], [pansexual] / [bisexual], and most W10 spokes.

It need not hold up A, B or C (they rest on 4s, May vectors in the top 1 to 2%, or on cost); C10's
[technical] / [specialist] and C11 wait for it, and any new 4 (or 3 far from the alignment region) comes
back as an addendum before the extraction.  Under $20 the batch-or-real-time rule says real time; the
session quoted batches, either is fine at this size.

## Drafts

Per the description rules 1-11
([.claude/rules/trait-pairs.md](../../.claude/rules/trait-pairs.md)).  [abstract] and [trustworthy] are
pair poles: rewrite procedure (label `non-X`, regenerate, check, record the check, restore the
partner's label, `--instructions-only`).  [wry] is regenerated under `non-wry` and checked.

**[abstract]** (26 words; clause for clause against [concrete]'s "This means dealing in particulars,
this case, this number, this person on this day, and giving an example where someone else would state
a principle."):

> This means dealing in generalities, the pattern, the trend, people in general at any time, and stating a principle where someone else would give an example.

Test: does the persona go from the case to the general ([abstract]), or from practice to theory,
models and frameworks ([theoretical])?  The old text's "theoretical frameworks" goes.

**[trustworthy]** (28 words; mirrors [untrustworthy]'s promises, truth and confidences):

> This means keeping one's word when breaking it would pay: holding to a promise gone costly, telling the truth when shading it would help, and keeping a confidence.

Test: would the persona keep faith when breaking it pays ([trustworthy]), or is the question only
whether it follows through without reminders ([dependable])?

**[wry]** (31 words):

> This means meeting life's small absurdities with quiet, low-key amusement: a raised eyebrow, a deadpan aside or a half-smile at one's own bad luck, with nobody made the butt of the joke.

Test: does the humour mock someone or something ([sardonic], [sarcastic]) or only notice ([wry])?
Nearest besides: [witty] (cleverness on display), [self-deprecating] (the joke always on oneself).

**For group E.**  [collaborative], [entertaining] and [easygoing] are pair poles (the same rewrite
procedure); [mystical] is regenerated under `non-mystical`, checked, and stays a singleton.

**[collaborative]** (E1; 28 words; W4's draft shortened, its last clause now mirroring
[self-reliant]'s "seeing a team as dead weight"):

> This means working with others: solving problems together, asking for their input, sharing the effort and the responsibility, and seeing a team as what gets the job done.

Test: does the persona want others in the work at all ([collaborative], against [self-reliant]), or
want everyone to come out ahead instead of beating one another ([cooperative], against
[competitive])?

**[entertaining]** (E2; 28 words; clause for clause against [dry]'s "giving the facts with nothing to
make them enjoyable, no joke, no color, no lively example, and no notion that they should be"):

> This means telling the facts so they are a pleasure to hear: a story, some color, a lively example, and the conviction that they should never be dull.

Test: is the pleasure in the telling ([entertaining]), in clever words ([witty]), or in fun and games
([playful])?  [dry]'s "no joke" has no counterpart: the persona may joke, but need not.

**[easygoing]** (E5; 28 words; against [uptight]'s "tense and buttoned-up, fussing that every small
thing be done properly, unable to loosen up or let anything slide, and putting everyone on edge"):

> This means being loose and relaxed about how things are done: untroubled when small things go undone or wrong, never fussing over them, and putting everyone at ease.

Test: does the persona shrug off small things done wrong ([easygoing]), or keep the energy and the
stakes of a conversation low ([laid-back])?  "Letting things slide" is left out: that is
[careless]'s.

**[mystical]** (E7; 26 words; label `non-mystical`):

> This means trusting what is known beyond reason: the vision, the inner certainty, the experience no words can carry, held truer than any argument or proof.

Test: does the persona know by something beyond reason ([mystical]), or put the sacred above money
and things ([spiritual])?  Nearest besides: [religious] (faith, scripture, authority), [intuitive]
(a sense for patterns, nothing transcendent).

## Applying it

**Status 2026-10-09:** A1-A3 applied (647ca4d), B1 (83febfb).  Group E's leans are listed at the
end of E.

If every lean is taken: delete [conceptual], [enigmatic], [dramatic] and the role [adolescent]; rewrite
[abstract], [trustworthy] and [wry] (three generations and checks, about $0.10, live); then
`sync_entity_lists.py`, `check_arrangements.py`, and the goal list's #44 and #7 for W15.  Tell the
trait-gap session before deleting: its
[labelled_pairs.json](../../data/candidates/calibration_916/labelled_pairs.json) and
[corpus_regions.json](../../data/candidates/corpus_regions.json) name all three traits.  No queue
entry exists for any of them.  The TRAITS_TO_ADD section then gets a dated status line (heading
unchanged).

## Evidence

Source: T the TRAITS_TO_ADD table, N flagged by the 918-file rerun, W W10 decision 3.  Costs are for
dropping that trait.

| pair | src | cos | May | M3 | first: cost | second: cost | |
|---|---|---|---|---|---|---|---|
| [abstract] / [theoretical] | T N | 0.73 / 0.87\* | 0.90 (p97) | 4 (10/12) | pair [concrete]; #5 | pair [practical]; clean, di, goalnongoal; #50 | C1 |
| [conceptual] / [theoretical] | T N | 0.74 / 0.86\* | 0.83 (p88) | 4 (12/18) | singleton; #44 | | A1 |
| [abstract] / [conceptual] | | 0.75 / 0.86\* | 0.89 (p96) | 4 (6/6) | | | A1 |
| [dependable] / [trustworthy] | T N | 0.79\* / 0.85\* | 0.76 (p65) | 3 (12/12) | pair [unreliable]; clean, di | pair [untrustworthy]; clean, di, goalnongoal | C2 |
| [passionate] / [zealous] | T | 0.60 / 0.72 | 0.69 (p39) | 2 (4/6); scan 3 and 2 | pair [dispassionate]; clean, di, goalnongoal; #15 | pair [temperate] | C10 |
| [empathetic] / [compassionate] | T N | 0.75 / 0.87\* | 0.79 (p78) | 3 (7/12) | spoke; 3 record lists | triangle corner; di_v1, 13_new; goal #54 | D2 |
| [absolutist] / [moral universalist] | T | 0.70 / 0.76 | | 3 (6/6) | pair [relativist]; every current list | pair [moral relativist] | B3 |
| [dramatic] / [theatrical] | T N W | 0.81\* / 0.85\* | 0.88 (p94) | 3 (18/18); scan 4 and 3 | spoke; #7 | pair [unassuming]; #56 | B1 |
| [melodramatic] / [dramatic] | T N W | 0.79\* / 0.84 | 0.88 (p95) | 3 (12/12) | spoke; #47 | | B1 |
| [melodramatic] / [theatrical] | | 0.71 / 0.82 | 0.87 (p94) | 3 (5/6) | | | C5 |
| [sarcastic] / [sardonic] | T N | 0.79\* / 0.80 | 0.89 (p96) | 3 or 2 (6/6) | singleton | pair [earnest]; clean, di, responses | C4 |
| [wry] / [sardonic] | T N W | 0.77 / 0.86\* | 0.92 (p98) | 3 (12/12) | spoke | | C3 |
| [wry] / [sarcastic] | T | 0.63 / 0.77 | 0.83 (p88) | 2 (12/12) | | | C3 |
| [honest] / [truthful] | T | 0.77 / 0.83 | 0.79 (p78) | 3 (9/12) | pair [dishonest]; every current list | pair [deceitful]; every current list | C6 |
| [technical] / [specialist] | T | 0.66 / 0.82 | | scan 3 and 3 | singleton | pair [generalist]; #40 | C10 |
| [creative] / [innovative] | T | 0.62 / 0.81 | 0.55 (p8) | 2 (6/6) | singleton | pair [traditional]; clean, di | C10 |
| [enigmatic] / [cryptic] | T W | 0.72 / 0.83 | 0.93 (p99) | scan 3 and 3 | spoke | pair [clear]; #20 | A2 |
| [northern hemisphere] / [eastern hemisphere] | T | 0.70 / 0.61 | | scan 1 | pair [southern hemisphere] | pair [western hemisphere] | C10 |
| [dispassionate] / [detached] | T N | 0.75 / 0.86\* | 0.94 (p99) | 4 (12/12) | pair [passionate]; clean, di, goalnongoal | spoke; 3 record lists | D1 |
| [insular] / [parochial] | T | 0.64 / 0.84 | 0.75 (p59) | 4 (6/6) | sequence; goal #38 | sequence; goal #32 | D4 |
| [pansexual] / [bisexual] | N | 0.79\* / 0.87\* | | scan 3 and 3 | singleton | singleton | C7 |
| [extraverted (HEXACO)] / [extraverted (Big Five)] | N | 0.75 / 0.87\* | | scan 3 and 3 | pair; orthoplex | pair; orthoplex | C8 |
| [careless (HEXACO)] / [careless (Big Five)] | N | 0.82\* / 0.83 | | scan 4 and 4 | pair; orthoplex | pair; orthoplex | C8 |
| [good only when watched] / [good even when unwatched] | N | 0.70 / 0.84\* | | | W5 | W5 | D6 |
| [upper-class] / [middle-class] | N | 0.79\* / 0.74 | | scan 1 | pair [working-class] | singleton | C9 |
| [self-blaming] / [blame-shifting] | T N | 0.78\* / 0.86\* | | opposite (6/6) | singleton | singleton | D5 |
| [systems-thinker] / [holistic] | W | 0.64 / 0.77 | 0.88 (p94) | 3 (6/6) | spoke; 6 record lists; #3 | pair [reductionist]; clean, di, goalnongoal; #46 | B2 |
| [neurotic] / [anxious] | W | 0.62 / 0.82 | 0.76 (p64) | 2 (4/6); scan 3 and 3 | spoke | pair [composed] | C12 |
| [inspirational] / [encouraging] | W | 0.60 / 0.75 | | scan 3 and 3 | spoke | pair [discouraging] | C12, E4 |
| [exploratory] / [divergent] | W | 0.61 / 0.72 | 0.67 (p34) | scan 2 | spoke | pair [convergent]; clean, di, goalnongoal | C12 |
| [effusive] / [expressive] | W | 0.51 / 0.73 | | | spoke; #36 | pair [reserved] | C12 |
| [acerbic] / [savage] | W | 0.48 / 0.67 | 0.78 (p73) | | spoke | singleton | C12 |
| [provocative] / [edgy] | W | 0.58 / 0.77 | 0.57 (p10) | 3 (9/12) | spoke | pair [staid] | C12 |
| [stream-of-consciousness] / [disorganized] | W | 0.53 / 0.70 | 0.55 (p7) | | spoke; #24 | pair [organized]; #22 | C12 |
| [mercurial] / [erratic] | W | 0.66 / 0.81 | | scan 4 and 4 | spoke; #43 | pair [steady] | C11 |
| [experiential] / [practical] | W | 0.54 / 0.75 | 0.78 (p73) | 2 (6/6) | label names a deleted file; #27 | pair [theoretical]; clean, di, goalnongoal | C12 |
| [hands-off] / [absentee] | W9 | 0.71 / 0.81 | | scan 3 and 3 | pair [hands-on] | spoke | D7 |
| [teenager] / [adolescent] (roles) | W10 | | 0.91 (p99 of roles) | | singleton | singleton | A3 |

The cosines and percentiles were computed for this sheet from the cached embeddings and the May
persona file (no API call); the raw cosines match
[drop_or_merge.md](../../data/candidates/calibration_916/drop_or_merge.md) to three decimals.

[abstract]: ../../data/traits/instructions/abstract.json
[absentee]: ../../data/traits/instructions/absentee.json
[absolutist]: ../../data/traits/instructions/absolutist.json
[acerbic]: ../../data/traits/instructions/acerbic.json
[adolescent]: ../../data/roles/instructions/adolescent.json
[analytical]: ../../data/traits/instructions/analytical.json
[anxious]: ../../data/traits/instructions/anxious.json
[bisexual]: ../../data/traits/instructions/bisexual.json
[blame-shifting]: ../../data/traits/instructions/blame_shifting.json
[careless (Big Five)]: ../../data/traits/instructions/careless_big_five.json
[careless (HEXACO)]: ../../data/traits/instructions/careless_hexaco.json
[clear]: ../../data/traits/instructions/clear.json
[compassionate]: ../../data/traits/instructions/compassionate.json
[composed]: ../../data/traits/instructions/composed.json
[conceptual]: ../../data/traits/instructions/conceptual.json
[concrete]: ../../data/traits/instructions/concrete.json
[convergent]: ../../data/traits/instructions/convergent.json
[creative]: ../../data/traits/instructions/creative.json
[cryptic]: ../../data/traits/instructions/cryptic.json
[deceitful]: ../../data/traits/instructions/deceitful.json
[dependable]: ../../data/traits/instructions/dependable.json
[detached]: ../../data/traits/instructions/detached.json
[discouraging]: ../../data/traits/instructions/discouraging.json
[dishonest]: ../../data/traits/instructions/dishonest.json
[disorganized]: ../../data/traits/instructions/disorganized.json
[dispassionate]: ../../data/traits/instructions/dispassionate.json
[divergent]: ../../data/traits/instructions/divergent.json
[dramatic]: ../../data/traits/instructions/dramatic.json
[dry]: ../../data/traits/instructions/dry.json
[earnest]: ../../data/traits/instructions/earnest.json
[eastern hemisphere]: ../../data/traits/instructions/eastern_hemisphere.json
[edgy]: ../../data/traits/instructions/edgy.json
[effusive]: ../../data/traits/instructions/effusive.json
[empathetic]: ../../data/traits/instructions/empathetic.json
[encouraging]: ../../data/traits/instructions/encouraging.json
[enigmatic]: ../../data/traits/instructions/enigmatic.json
[erratic]: ../../data/traits/instructions/erratic.json
[experiential]: ../../data/traits/instructions/experiential.json
[exploratory]: ../../data/traits/instructions/exploratory.json
[expressive]: ../../data/traits/instructions/expressive.json
[extraverted (Big Five)]: ../../data/traits/instructions/extraverted_big_five.json
[extraverted (HEXACO)]: ../../data/traits/instructions/extraverted_hexaco.json
[generalist]: ../../data/traits/instructions/generalist.json
[good even when unwatched]: ../../data/traits/instructions/good_even_when_unwatched.json
[good only when watched]: ../../data/traits/instructions/good_only_when_watched.json
[hands-off]: ../../data/traits/instructions/hands_off.json
[hands-on]: ../../data/traits/instructions/hands_on.json
[holistic]: ../../data/traits/instructions/holistic.json
[honest]: ../../data/traits/instructions/honest.json
[innovative]: ../../data/traits/instructions/innovative.json
[insular]: ../../data/traits/instructions/insular.json
[inspirational]: ../../data/traits/instructions/inspirational.json
[melodramatic]: ../../data/traits/instructions/melodramatic.json
[mercurial]: ../../data/traits/instructions/mercurial.json
[merciful]: ../../data/traits/instructions/merciful.json
[middle-class]: ../../data/traits/instructions/middle_class.json
[moral relativist]: ../../data/traits/instructions/moral_relativist.json
[moral universalist]: ../../data/traits/instructions/moral_universalist.json
[neurotic]: ../../data/traits/instructions/neurotic.json
[neurotic (Big Five)]: ../../data/traits/instructions/neurotic_big_five.json
[northern hemisphere]: ../../data/traits/instructions/northern_hemisphere.json
[organized]: ../../data/traits/instructions/organized.json
[pansexual]: ../../data/traits/instructions/pansexual.json
[parochial]: ../../data/traits/instructions/parochial.json
[passionate]: ../../data/traits/instructions/passionate.json
[practical]: ../../data/traits/instructions/practical.json
[provocative]: ../../data/traits/instructions/provocative.json
[reductionist]: ../../data/traits/instructions/reductionist.json
[relativist]: ../../data/traits/instructions/relativist.json
[reserved]: ../../data/traits/instructions/reserved.json
[sarcastic]: ../../data/traits/instructions/sarcastic.json
[sardonic]: ../../data/traits/instructions/sardonic.json
[savage]: ../../data/traits/instructions/savage.json
[self-blaming]: ../../data/traits/instructions/self_blaming.json
[self-deprecating]: ../../data/traits/instructions/self_deprecating.json
[southern hemisphere]: ../../data/traits/instructions/southern_hemisphere.json
[specialist]: ../../data/traits/instructions/specialist.json
[staid]: ../../data/traits/instructions/staid.json
[steady]: ../../data/traits/instructions/steady.json
[stream-of-consciousness]: ../../data/traits/instructions/stream_of_consciousness.json
[systems-thinker]: ../../data/traits/instructions/systems_thinker.json
[technical]: ../../data/traits/instructions/technical.json
[teenager]: ../../data/roles/instructions/teenager.json
[temperamental]: ../../data/traits/instructions/temperamental.json
[temperate]: ../../data/traits/instructions/temperate.json
[theatrical]: ../../data/traits/instructions/theatrical.json
[theoretical]: ../../data/traits/instructions/theoretical.json
[traditional]: ../../data/traits/instructions/traditional.json
[trustworthy]: ../../data/traits/instructions/trustworthy.json
[truthful]: ../../data/traits/instructions/truthful.json
[unassuming]: ../../data/traits/instructions/unassuming.json
[unreliable]: ../../data/traits/instructions/unreliable.json
[untrustworthy]: ../../data/traits/instructions/untrustworthy.json
[upper-class]: ../../data/traits/instructions/upper_class.json
[witty]: ../../data/traits/instructions/witty.json
[working-class]: ../../data/traits/instructions/working_class.json
[western hemisphere]: ../../data/traits/instructions/western_hemisphere.json
[wry]: ../../data/traits/instructions/wry.json
[zealous]: ../../data/traits/instructions/zealous.json
[accommodating]: ../../data/traits/instructions/accommodating.json
[adventurous]: ../../data/traits/instructions/adventurous.json
[adventurous-eater]: ../../data/traits/instructions/adventurous_eater.json
[African]: ../../data/traits/instructions/african.json
[aggressive]: ../../data/traits/instructions/aggressive.json
[agreeable]: ../../data/traits/instructions/agreeable.json
[agreeable (Big Five)]: ../../data/traits/instructions/agreeable_big_five.json
[agreeable (HEXACO)]: ../../data/traits/instructions/agreeable_hexaco.json
[altruistic]: ../../data/traits/instructions/altruistic.json
[antagonistic (Big Five)]: ../../data/traits/instructions/antagonistic_big_five.json
[anthropocentric]: ../../data/traits/instructions/anthropocentric.json
[aristocratic]: ../../data/traits/instructions/aristocratic.json
[artistic]: ../../data/traits/instructions/artistic.json
[artistic (Holland)]: ../../data/traits/instructions/artistic_holland.json
[blunt]: ../../data/traits/instructions/blunt.json
[body-obsessed]: ../../data/traits/instructions/body_obsessed.json
[brave]: ../../data/traits/instructions/brave.json
[callous]: ../../data/traits/instructions/callous.json
[calm]: ../../data/traits/instructions/calm.json
[Canadian]: ../../data/traits/instructions/canadian.json
[careless]: ../../data/traits/instructions/careless.json
[cautious]: ../../data/traits/instructions/cautious.json
[closed (Big Five)]: ../../data/traits/instructions/closed_big_five.json
[collaborative]: ../../data/traits/instructions/collaborative.json
[competitive]: ../../data/traits/instructions/competitive.json
[conciliatory]: ../../data/traits/instructions/conciliatory.json
[confident]: ../../data/traits/instructions/confident.json
[confrontational]: ../../data/traits/instructions/confrontational.json
[conscientious]: ../../data/traits/instructions/conscientious.json
[conscientious (Big Five)]: ../../data/traits/instructions/conscientious_big_five.json
[conscientious (HEXACO)]: ../../data/traits/instructions/conscientious_hexaco.json
[consequentialist]: ../../data/traits/instructions/consequentialist.json
[conservative]: ../../data/traits/instructions/conservative.json
[conventional]: ../../data/traits/instructions/conventional.json
[conventional (HEXACO)]: ../../data/traits/instructions/conventional_hexaco.json
[cooperative]: ../../data/traits/instructions/cooperative.json
[cruel]: ../../data/traits/instructions/cruel.json
[cynical]: ../../data/traits/instructions/cynical.json
[data-driven]: ../../data/traits/instructions/data_driven.json
[decisive]: ../../data/traits/instructions/decisive.json
[descriptive]: ../../data/traits/instructions/descriptive.json
[dominant]: ../../data/traits/instructions/dominant.json
[East Asian]: ../../data/traits/instructions/east_asian.json
[easygoing]: ../../data/traits/instructions/easygoing.json
[ecocentric]: ../../data/traits/instructions/ecocentric.json
[elitist]: ../../data/traits/instructions/elitist.json
[emotional]: ../../data/traits/instructions/emotional.json
[emotional (HEXACO)]: ../../data/traits/instructions/emotional_hexaco.json
[emotionally-articulate]: ../../data/traits/instructions/emotionally_articulate.json
[emotionally-stable (Big Five)]: ../../data/traits/instructions/emotionally_stable_big_five.json
[Enneagram 8]: ../../data/traits/instructions/enneagram_8.json
[entertaining]: ../../data/traits/instructions/entertaining.json
[environmental]: ../../data/traits/instructions/environmental.json
[European]: ../../data/traits/instructions/european.json
[even-tempered]: ../../data/traits/instructions/even_tempered.json
[evil]: ../../data/traits/instructions/evil.json
[excitable]: ../../data/traits/instructions/excitable.json
[external locus of control]: ../../data/traits/instructions/external_locus_of_control.json
[extrinsically motivated]: ../../data/traits/instructions/extrinsically_motivated.json
[extroverted]: ../../data/traits/instructions/extroverted.json
[fatalistic]: ../../data/traits/instructions/fatalistic.json
[financially conservative]: ../../data/traits/instructions/financially_conservative.json
[financially reckless]: ../../data/traits/instructions/financially_reckless.json
[flustered]: ../../data/traits/instructions/flustered.json
[forgiving]: ../../data/traits/instructions/forgiving.json
[formalist]: ../../data/traits/instructions/formalist.json
[formulaic]: ../../data/traits/instructions/formulaic.json
[generous]: ../../data/traits/instructions/generous.json
[German]: ../../data/traits/instructions/german.json
[gluttonous]: ../../data/traits/instructions/gluttonous.json
[good]: ../../data/traits/instructions/good.json
[goofy]: ../../data/traits/instructions/goofy.json
[grandiose]: ../../data/traits/instructions/grandiose.json
[gregarious]: ../../data/traits/instructions/gregarious.json
[growth-first]: ../../data/traits/instructions/growth_first.json
[Gryffindor]: ../../data/traits/instructions/gryffindor.json
[harmful]: ../../data/traits/instructions/harmful.json
[harsh]: ../../data/traits/instructions/harsh.json
[hostile]: ../../data/traits/instructions/hostile.json
[impatient]: ../../data/traits/instructions/impatient.json
[indecisive]: ../../data/traits/instructions/indecisive.json
[independent]: ../../data/traits/instructions/independent.json
[inflexible]: ../../data/traits/instructions/inflexible.json
[informational]: ../../data/traits/instructions/informational.json
[intellectually dishonest]: ../../data/traits/instructions/intellectually_dishonest.json
[intense]: ../../data/traits/instructions/intense.json
[interdisciplinary]: ../../data/traits/instructions/interdisciplinary.json
[introverted]: ../../data/traits/instructions/introverted.json
[introverted (Big Five)]: ../../data/traits/instructions/introverted_big_five.json
[intuitive]: ../../data/traits/instructions/intuitive.json
[irascible]: ../../data/traits/instructions/irascible.json
[ironic]: ../../data/traits/instructions/ironic.json
[irresponsible]: ../../data/traits/instructions/irresponsible.json
[Italian]: ../../data/traits/instructions/italian.json
[Japanese]: ../../data/traits/instructions/japanese.json
[laid-back]: ../../data/traits/instructions/laid_back.json
[lenient]: ../../data/traits/instructions/lenient.json
[low-context (Hall)]: ../../data/traits/instructions/low_context_hall.json
[malevolent]: ../../data/traits/instructions/malevolent.json
[malicious]: ../../data/traits/instructions/malicious.json
[married]: ../../data/traits/instructions/married.json
[materialist]: ../../data/traits/instructions/materialist.json
[materialistic]: ../../data/traits/instructions/materialistic.json
[mercenary]: ../../data/traits/instructions/mercenary.json
[methodical]: ../../data/traits/instructions/methodical.json
[meticulous]: ../../data/traits/instructions/meticulous.json
[micromanaging]: ../../data/traits/instructions/micromanaging.json
[misanthropic]: ../../data/traits/instructions/misanthropic.json
[moral]: ../../data/traits/instructions/moral.json
[mystical]: ../../data/traits/instructions/mystical.json
[naive]: ../../data/traits/instructions/naive.json
[neglectful]: ../../data/traits/instructions/neglectful.json
[neglectful (Baumrind)]: ../../data/traits/instructions/neglectful_baumrind.json
[new money]: ../../data/traits/instructions/new_money.json
[Nigerian]: ../../data/traits/instructions/nigerian.json
[noncommittal]: ../../data/traits/instructions/noncommittal.json
[nurturing]: ../../data/traits/instructions/nurturing.json
[obsessive]: ../../data/traits/instructions/obsessive.json
[old money]: ../../data/traits/instructions/old_money.json
[open (Big Five)]: ../../data/traits/instructions/open_big_five.json
[open (HEXACO)]: ../../data/traits/instructions/open_hexaco.json
[opinionated]: ../../data/traits/instructions/opinionated.json
[overconfident]: ../../data/traits/instructions/overconfident.json
[patient]: ../../data/traits/instructions/patient.json
[perfectionist]: ../../data/traits/instructions/perfectionist.json
[permissive (Baumrind)]: ../../data/traits/instructions/permissive_baumrind.json
[philanthropic]: ../../data/traits/instructions/philanthropic.json
[placid]: ../../data/traits/instructions/placid.json
[plain-spoken]: ../../data/traits/instructions/plain_spoken.json
[playful]: ../../data/traits/instructions/playful.json
[polyandrous]: ../../data/traits/instructions/polyandrous.json
[polygamous]: ../../data/traits/instructions/polygamous.json
[polygynous]: ../../data/traits/instructions/polygynous.json
[precise]: ../../data/traits/instructions/precise.json
[progressive]: ../../data/traits/instructions/progressive.json
[prudent]: ../../data/traits/instructions/prudent.json
[quantitative]: ../../data/traits/instructions/quantitative.json
[radical]: ../../data/traits/instructions/radical.json
[rationalist]: ../../data/traits/instructions/rationalist.json
[reckless]: ../../data/traits/instructions/reckless.json
[religious]: ../../data/traits/instructions/religious.json
[risk-averse]: ../../data/traits/instructions/risk_averse.json
[risk-seeking]: ../../data/traits/instructions/risk_seeking.json
[ritualistic]: ../../data/traits/instructions/ritualistic.json
[self-aggrandizing]: ../../data/traits/instructions/self_aggrandizing.json
[self-effacing]: ../../data/traits/instructions/self_effacing.json
[self-indulgent]: ../../data/traits/instructions/self_indulgent.json
[self-reliant]: ../../data/traits/instructions/self_reliant.json
[serene]: ../../data/traits/instructions/serene.json
[serious]: ../../data/traits/instructions/serious.json
[sloppy]: ../../data/traits/instructions/sloppy.json
[solemn]: ../../data/traits/instructions/solemn.json
[solitary]: ../../data/traits/instructions/solitary.json
[spiritual]: ../../data/traits/instructions/spiritual.json
[supportive]: ../../data/traits/instructions/supportive.json
[technomystical]: ../../data/traits/instructions/technomystical.json
[transformational]: ../../data/traits/instructions/transformational.json
[transparent]: ../../data/traits/instructions/transparent.json
[treacherous]: ../../data/traits/instructions/treacherous.json
[trusting]: ../../data/traits/instructions/trusting.json
[turbulent]: ../../data/traits/instructions/turbulent.json
[uncaring]: ../../data/traits/instructions/uncaring.json
[uncertain]: ../../data/traits/instructions/uncertain.json
[unflappable]: ../../data/traits/instructions/unflappable.json
[unforgiving]: ../../data/traits/instructions/unforgiving.json
[unpretentious]: ../../data/traits/instructions/unpretentious.json
[uptight]: ../../data/traits/instructions/uptight.json
[utilitarian]: ../../data/traits/instructions/utilitarian.json
[vindictive]: ../../data/traits/instructions/vindictive.json
[wealthy]: ../../data/traits/instructions/wealthy.json
