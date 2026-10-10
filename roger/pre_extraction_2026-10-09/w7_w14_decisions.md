# W7, W8, W9, W14: the triangle copies, the accountability kite, the delegation sequence, the moral circle

**Status 2026-10-09: decision sheet for Roger, drafted by an agent.  Read-only: no corpus, queue or
usage file was changed and no API call was made.**  Items W7, W8, W9 and W14 of
[work_list.md](./work_list.md).  Each section opens with the decisions (numbered, recommendation
first, one-line reason), then the evidence.  The last section lists the file changes if every
recommendation is taken.

**Terms.**  The *check* is the antonym check
([generate_antonyms.py](../../data_analysis/generate_antonyms.py)): a model reads a trait's neg
instructions and names that pole.  *(nX)* marks a check made under a `non-X` placeholder label, so
the answer was not prompted; a check made under a real label partly echoes it.  A *clean pair* is
two traits whose `negative_label`s name each other
([glossary](../../reports/trait_gap_generation/glossary.md#clean-pair)); a *one-way pointer* is a
label naming a trait whose own label points elsewhere.  A *copy* of the help / harm / don't-care
triangle is the same three corners written in another *register* (feeling, will, moral standing).
Other terms: the [glossary](../../reports/trait_gap_generation/glossary.md).

**Evidence**, all on disk:

- checks: [antonym_check_history.jsonl](../../data/traits/antonym_check_history.jsonl),
  [seed_queue.json](../../data/seed_queue.json), [seeding_log_2026-09.md](../../reports/seeding_log_2026-09.md),
  and for the oldest traits [trait_antonyms_v4.json](../../data/traits/trait_antonyms_v4.json) (May);
- *description cosines*: the [cosine](../../reports/trait_gap_generation/glossary.md#cosine) between the
  trait-gap platform's cached OpenAI embeddings of each current `label: description`
  ([openai_text-embedding-3-large.npz](../../data/candidates/cache/embeddings/openai_text-embedding-3-large.npz);
  [centred space](../../reports/trait_gap_generation/glossary.md#centred), 20-word form, M2's setting).
  Over the 916 traits the [nearest-neighbour](../../reports/trait_gap_generation/glossary.md#nearest-neighbour)
  cosine has median 0.49, 90th percentile 0.65, 99th 0.85.  Mirrored wording counts as closeness, so
  antonyms written in parallel can score high;
- *May cosines*: the May 2026 [persona vectors](../../reports/trait_gap_generation/glossary.md#persona-space)
  ([persona_s6_l25.npz](../../data/candidates/cache/persona_s6_l25.npz): Qwen-3-32B, 8-slot run, slot 6,
  layer 25, 302 traits, centred).  Nearest-neighbour median 0.72, p90 0.83, p99 0.93.  Old
  instructions, and older wordings of [benign] and [regionalist]; indicative only, and many of the traits
  below have none (none of W8's or W9's do);
- costs: the pair lists in [axis_judge_experiments](../axis_judge_experiments/) (current and the
  `_v1` and dated *record lists* of judged work) and
  [goal_roles_and_traits.json](../../data/goal_roles_and_traits.json) (`traits.goal`: the first 30
  are what the pipeline takes by default; 30-39 "remaining moral circle spectrum"; 40 on the rest).

**Validated.**  Every arrangement proposed below was written into a scratch copy of the corpus and
passes [check_arrangements.py](../../data_analysis/check_arrangements.py): 0 problems, unclassified
traits 36 → 30 ([absentee], [benevolent], [cruel], [malevolent], [micromanaging], [uncaring]
classified).  The W8 kite, recorded as a `square`, passes too.  These are six of the eight
unclassified traits that [W10](./w10_w12_proposals.md) left to this sheet; the other two,
[empathetic] and [detached], are item 7.7.

---

## W7. The help / harm / don't-care copies

### Decisions

1. **Keep three copies: feeling (recorded), will, and moral standing; or two (feeling, will).**
   *Recommend three*: the third costs nothing (all three files exist and are already pair poles, so it
   is one more `arrangement` entry each), and [good]'s unprompted check named [amoral].
2. **Will triangle labels: mirror the recorded triangle** ([benevolent] → `non-benevolent`,
   [malevolent] → [benevolent], [uncaring] keeps → [benevolent]), **or leave [benevolent] ↔ [uncaring]
   pointing at each other.**  *Recommend mirror*: the reciprocal labels claim a clean pair that both
   checks deny ([benevolent] → [callous], indifferent; [uncaring] → caring), and code reads reciprocal labels
   as clean pairs ([build_pair_lists.py](../../tools/build_pair_lists.py), the M3 retrieval in
   [novelty.py](../../assistant_axis/gapgen/novelty.py)).
3. **Rewrite [uncaring] into the will register** (draft below), **or keep it.**  *Recommend
   rewrite*: it opens "answering with no thought" (an assistant frame), and its check lands on the
   feeling corner (caring), never on [benevolent].  It supersedes the one-word fix in
   [w4_framing.md](./w4_framing.md) ("answering" → "acting"); if you keep the wording, take W4's.
4. **Drop [merciful], or keep it as a singleton.**  *Recommend drop*: no cost (no pair, no list, no
   goal list, no May vector); it was seeded only as [cruel]'s label and checks to "merciless" (nX);
   its nearest descriptions are [forgiving], [gentle] (0.40), [lenient] (0.38) and [compassionate]
   (0.37), so the content stays covered; a mercy triangle would be a fourth copy.  merciless stays
   unseeded.
5. **[cruel]: rewrite to everyday sadism** (draft below) **or keep the wording**; either way label
   `non-cruel` and `singleton`, since [merciful] goes.  *Recommend rewrite*: two of its three "or"
   clauses are [callous] ("deliberate indifference", "callous disregard"), and the May vectors put it
   0.84 from [callous] (above p90); its sadism clause is, with [bullying], the corpus's plain cover for
   everyday sadism ([TRAITS_ADDED.md](../../data/traits/instructions/TRAITS_ADDED.md) § "Dark
   Tetrad and Light Triad").  Keep the file: it is #25 in the goal list's top 30.
6. **[benign] / [malign] beside [harmless] / [harmful]: keep both pairs until the cosines** (your
   2026-10-02 ruling), **or drop [benign] / [malign] now.**  *Recommend keep*: it is not a triangle copy
   (no don't-care corner: effects, meant or not); the description cosines are modest ([benign]–[harmless]
   0.38, [malign]–[harmful] 0.36, below the median nearest neighbour); [harmless] / [harmful] is the HHH axis
   in every current pair list, so it would be the one kept, and [benign] is a pole in six record lists.
7. **No change** for [nurturing] ↔ [neglectful] (a clean pair since 2026-10-02; the survey's "paired
   with tough" is out of date) and [kind-to-animals] ↔ [indifferent-to-animals] (its own domain;
   seeding "cruel to animals", which [kind-to-animals]'s check offers, would make a fourth complete
   copy).  [empathetic] and [detached] are not a copy: keep both as one-way pointers until the new
   cosines (your 2026-10-02 ruling), recorded as W10's proposed `spoke` if that kind is adopted;
   [detached] is also W3's to drop (evidence below).  *Recommend as stated.*

### The copies

| register | help | harm | don't care | recorded now | checks | proposal |
|---|---|---|---|---|---|---|
| feeling | [compassionate] | [malicious] | [callous] | `triangle`; [malicious] and [callous] point at [compassionate] | [malicious] → [benevolent], then [benevolent], kind (under label [benign]); [callous] → [compassionate] (May) | keep: copy 1 |
| will | [benevolent] | [malevolent] | [uncaring] | none; [benevolent] ↔ [uncaring] by label; [malevolent] `non-X`; all unclassified | [benevolent] → [callous], indifferent (nX); [malevolent] → [benevolent] (nX); [uncaring] → caring (nX) | keep: copy 2; triangle, [uncaring] rewritten, labels mirrored |
| moral standing | [good] | [evil] | [amoral] | [good] ↔ [evil] pair by decision; [amoral] ↔ [moral] clean pair | [good] → [amoral], unprincipled (nX), then [evil], corrupt, wicked; [evil] → [good], virtuous, [benevolent] (nX); [amoral] → [moral], ethical (nX) | keep: copy 3; `triangle` added beside the pairs |
| mercy | [merciful] | [cruel] | merciless (no file) | [merciful] `singleton`; [cruel] → [merciful] one way, unclassified | [merciful] → merciless (nX); [cruel] → kind, [compassionate], [merciful] | drop [merciful]; [cruel] rewritten, `singleton` |
| effects | [benign] | [malign] | ([harmless]?) | [benign] ↔ [malign] clean pair (2026-10-02); [harmless] ↔ [harmful] clean pair | [benign] → [malign], [harmful], [malicious]; [malign] → [benign], beneficent | not a copy; keep both pairs |
| upbringing | [nurturing] | abusive (no file) | [neglectful] | [nurturing] ↔ [neglectful] clean pair (2026-10-02) | [neglectful] → attentive, [nurturing]; [nurturing] → [neglectful], cold, [harsh] | keep the pair; seed nothing |
| animals | [kind-to-animals] | cruel to animals (no file) | [indifferent-to-animals] | pair by decision; [kind-to-animals] also in the moral-circle sequence | [kind-to-animals] → [indifferent-to-animals], cruel-to-animals | its own domain; keep |
| strays | [empathetic] (→ [callous]) | | [detached] (→ [engaged]) | one-way pointers since the pair dissolved (2026-10-02) | [empathetic] → [callous], cold; [detached] → [engaged], involved, attached | 7.7 |

### What a drop would cost

| trait | pair broken | lists | goal list | May vector | proposal |
|---|---|---|---|---|---|
| [compassionate], [callous] | triangle corners | record lists `di_v1`, `13_new` ([compassionate] / [callous], judged) | tier 3 | yes | keep |
| [malicious] | triangle corner | six record lists ([benign] / [malicious], judged) | tier 3 | yes | keep |
| [benevolent], [malevolent] | none recorded | none | tier 3 | yes | keep |
| [uncaring] | none recorded | none | none | no | keep, rewrite |
| [good], [evil] | [good] / [evil] (by decision) | none | [evil] tier 3 | [evil] only | keep |
| [amoral] | [amoral] / [moral] (clean) | none | none | no | keep |
| [merciful] | none | none | none | no | **drop** |
| [cruel] | none | none | **#25, top 30** | yes | keep, rewrite |
| [benign], [malign] | [benign] / [malign] (clean) | [benign]: six record lists | [benign] tier 3 | [benign] only | keep |
| [harmless], [harmful] | [harmless] / [harmful] (clean) | every current list | tier 3; [harmful] top 30 | yes | keep |
| [nurturing], [neglectful] | [nurturing] / [neglectful] (clean) | none | [nurturing] top 30 | [nurturing] only | keep |
| [kind-to-animals], [indifferent-to-animals] | their pair (by decision) | none | [kind-to-animals] tier 2 | [kind-to-animals] only | keep |
| [empathetic], [detached] | none (dissolved) | three record lists ([detached] / [empathetic], judged) | none | yes | 7.7 |

A re-run of a record list stops at a pole whose file is gone
([resolve_renamed_stem](../../assistant_axis/entity_id.py) passes an unknown stem through to a
missing-file error); the judge caches on disk stay.  The help corner is crowded, but it is the
alignment region, which the corpus samples heavily on purpose, so the bar for a drop is a duplicate,
not a neighbour.

### Cosines inside the family

- Descriptions: harm corners [malicious]–[malevolent] 0.61 (84th percentile of nearest neighbours),
  [malicious]–[malign] 0.52, [malicious]–[evil] 0.47; help corners [compassionate]–[empathetic] 0.55,
  [benevolent]–[benign] 0.48, [compassionate]–[benevolent] 0.32; don't-care corners [callous]–[uncaring]
  0.37, [uncaring]–[amoral] 0.30.  The registers are worded apart, which is what makes their cosines
  in the new vectors worth having.  [uncaring]'s nearest description is [unhelpful] (0.45), the
  "answering" frame at work.
- May vectors: the help corners are one cluster ([compassionate] with [benevolent] 0.71, [empathetic] 0.79,
  [nurturing] 0.79), while harm and don't-care run together: [callous]–[cruel] 0.84, [cruel]–[evil] 0.81,
  [malevolent]–[evil] 0.80, [callous]–[malevolent] 0.68, but [callous]–[malicious] only 0.51.  The recorded
  triangle may come out as a line with a fork at the bad end.
- [detached]–[dispassionate]: 0.65 in descriptions (each other's nearest, 89th percentile), 0.94 in
  the May vectors (top 1%), and 4, "the same concept", in the M3 overlap test
  ([readout](../../reports/trait_gap_generation/m3_overlap_test_readout.md)).  [empathetic]–[compassionate]:
  0.55, 0.79, and 3 in M3.  Both rows are on W3's list.

### Drafts

**[uncaring]** (label stays [benevolent]):

> This means wishing nobody well and nobody ill: how other people fare is their own business, and one acts with no thought for who ends up helped or hurt.

29 words.  For the queue's `description_notes`, the test: does the persona have a stake in how
people fare ([benevolent] wants them well, [malevolent] wants them harmed, [uncaring] has none)?  Nearest:
[callous] (unmoved by pain: feeling, not will), [apathetic] (no interest in the matter or effort).

**[cruel]** (label `non-cruel`):

> This means enjoying other people's pain for its own sake: pressing on the sore spot, savoring someone's humiliation, or dragging out the hurt when one could easily stop it.

29 words.  Test: does the persona enjoy the pain ([cruel]), want the harm ([malicious]), or not mind it
([callous])?  Nearest also [bullying] (picking on the weaker).  If its check then names [compassionate]
or kind, the label stays `non-cruel`.

### What the extraction should test

Each kept triangle's shape (three corners apart, or a line with a fork, as the May vectors hint); the
cosines between corresponding corners of the three copies, which is why they are kept; and whether
the rewritten [cruel] moves from [callous] toward [malicious].

---

## W8. [accountable] / [blame-shifting] / [self-blaming]

### Decisions

1. **Try the kite: seed the fourth corner as a trial** (draft below; a generation, a check, a
   label-blind naming check and an M3 overlap call, a few cents), **or record the triangle now and
   seed nothing.**  *Recommend the trial*: the triangle can be recorded at any time on the existing
   checks; only a generated fourth corner can show whether the kite is real.
2. **Name it from the description**: provisional label "no-fault", settled by
   `generate_antonyms.py --name-pos` (the 2026-10-09 naming procedure); alternatives
   "blame-indifferent", "cavalier about mistakes".  *Recommend* letting the naming check choose:
   "being no-fault" reads oddly.
3. **The rule for kite or triangle**: record the kite (a `square` whose `note` names the two
   diagonals; no `axes`, since neither diagonal is a clean pair) if the new corner's check names
   [accountable] or its content (owning up, [responsible]) and the M3 overlap call puts it below 3
   against [unrepentant], [easygoing] and [magnanimous]; otherwise delete it and record the
   `triangle`.  Labels stay `non-X` on every corner either way (only [blame-shifting]'s check names
   [accountable], so pointing the vices at it is not supported for both).  *Recommend this rule.*

### Evidence

| trait | label | arrangement | checks |
|---|---|---|---|
| [accountable] | non-accountable | `singleton`, note "triangle or kite" | → deflecting, evasive (nX, 2026-09-28) |
| [blame-shifting] | non-blame-shifting | `singleton` | → [accountable], self-accountable (nX); earlier → [accountable], [responsible] |
| [self-blaming] | non-self-blaming | `singleton` | → balanced, fair-minded (nX); earlier → balanced, realistic; first (2026-09-25) → [blame-shifting] |

- [TRAITS_TO_ADD.md](../../data/traits/instructions/TRAITS_TO_ADD.md) says "both vices check to accountable"; only [blame-shifting] does by name.
  [self-blaming]'s answer describes proportionate blame, which is [accountable]'s own content ("no more
  and no less"), so the triangle stands on content.  [accountable]'s answer (deflecting) is
  [blame-shifting]'s content.
- The M3 overlap test read the two vices as opposites in every model.  Their description cosine is
  0.77 (98th percentile) only because the two sentences mirror each other; [accountable] sits apart
  (0.26 and 0.41).  None of the three has a May vector, and none was rechecked after the V2
  regeneration.
- The shape is two questions: where the blame lands (oneself or others) separates the vices; whether
  anyone is blamed at all separates [accountable] from the fourth corner.  A second reading is
  [accountable] as the mean between the vices (a `sequence` [self-blaming], [accountable], [blame-shifting]).
- Nothing in the corpus says nobody is ever at fault.  Nearest: [unrepentant] (shrugs off harm one
  has done), [magnanimous] (lets slights pass), [forgiving], [easygoing], [laid-back],
  [external locus of control] (luck decides outcomes), [fatalistic].

### Draft: the fourth corner

Stem [no_fault](../../data/traits/instructions/no_fault.json) (not there yet; the stem follows the
label the naming check settles):

> This means that when something goes wrong, it is never anybody's fault, neither one's own nor the colleague's: things just happen, and asking who slipped up is a waste of breath.

31 words; the same trigger and particulars as its three neighbours ("when something goes wrong", "the
colleague"), no partner named.  `description_notes`: the test is "does the persona put the failure
on anyone at all?" ([accountable]: on whoever's part it was, oneself included; [blame-shifting]: on
others or luck, never oneself; [self-blaming]: on oneself; this corner: on nobody, and the question is
not asked).  Unlike [blame-shifting]'s "bad luck", it is not a way out of one's own part.

### What the extraction should test

Whether [accountable] lies on the segment between the vices (a mean, so a `sequence`) or off it (a
triangle), and on which side of that segment the fourth corner lands.

---

## W9. The delegation tangle

### Decisions

1. **Record a `sequence` [micromanaging], [hands-on], [hands-off], [absentee]** (from most to least
   involvement in work one has handed over) on all four, beside the existing [hands-on] / [hands-off]
   `pair`, labels unchanged; **or leave the two vices unclassified.**  *Recommend record*: each
   vice's check names the far end of the neutral pair, which is how a line with a vice at each end
   reads; it passes the checker.
2. **Rewrite [hands-off] to the neutral sense** (draft below), **or leave it.**  *Recommend rewrite*:
   as written ("staying out of it even when things go wrong") it is [absentee]'s twin; each is the
   other's nearest description at 0.64 (89th percentile), nearer than [hands-off] is to its own partner
   (0.54).  Your 2026-09-26 design wanted a neutral pair with the vices outside it.  Cost: the clean
   pair's recheck, a few cents; the pair is in no list.
3. **Move `source: "MLQ (leadership style)"` from [hands-off] to [absentee].**  *Recommend*: the MLQ's
   laissez-faire scale is the avoidance of leadership (absent when needed), which is [absentee]; the
   neutral [hands-off] is not in the MLQ.  [micromanaging] keeps its MLQ source.

### Current state

| trait | label | arrangement | checks |
|---|---|---|---|
| [hands-on] | [hands-off] | `pair` with [hands-off] | → [hands-off] (nX, 2026-09-28; again 2026-10-02) |
| [hands-off] | [hands-on] | `pair` with [hands-on]; source MLQ | → [hands-on], [micromanaging] (nX); → [hands-on] (2026-10-02) |
| [micromanaging] | [hands-off], one way | unclassified; source MLQ | → [hands-off], delegating (nX; on 2026-09-26 also empowering) |
| [absentee] | [hands-on], one way | unclassified | → [hands-on], [engaged], attentive (nX) |

None of the four is in a pair list or the goal lists, or has a May vector.  Description cosines:
[hands-off]–[absentee] 0.64, [hands-on]–[hands-off] 0.54, [hands-on]–[micromanaging] 0.46,
[micromanaging]–[hands-off] 0.44, [micromanaging]–[absentee] 0.38, [hands-on]–[absentee] 0.33.  [micromanaging] is
apart from [controlling] (0.34), which is about people's private lives.

### Draft: [hands-off]

Now: "This means handing over the work and walking away, never checking progress or giving direction,
and staying out of it even when things go wrong."

> This means handing over the work and leaving it alone: no check-ins, people doing it their own way, and direction or help given only when they ask for it.

29 words, clause for clause against [hands-on]'s.  The sequence's test: does the persona step in
unasked and redo the work ([micromanaging]), step in unasked when it is needed ([hands-on]), only when
asked ([hands-off]), or not even then ([absentee])?  Recheck by the rewrite procedure for a pair member
(label `non-hands-off`, generate, check, restore the label, `--instructions-only`).

### What the extraction should test

A monotone projection in the recorded order, and whether the two vices bend toward each other (both
carry the same bad valence), which would show as a horseshoe rather than a line.

---

## W14. The moral-circle sequence

### Decisions

1. **[philanthropic]: remove from the sequence** (keep the trait as a `singleton`), **or rewrite in
   scope terms.**  *Recommend remove*: it is about giving, not whose welfare counts; nearest
   [altruistic] (0.44; May 0.76), [generous], [helpful]; a scope rewrite would duplicate
   [humanitarian].
2. **[patriotic]: remove, or rewrite.**  *Recommend remove*: love and pride of country, the nation's
   circle as affection; a scope rewrite would duplicate [nationalist], and the patriotism /
   nationalism distinction is worth keeping as written.  In May its neighbours after [nationalist]
   (0.71) are [reverent] (0.58) and [philanthropic] (0.50), and it is uncorrelated with [selfish] (−0.02).
3. **[ethnocentric]: remove, or rewrite to an ethnic-group circle.**  *Recommend remove*: it is
   mostly Sumner's sense (judging others by one's own group's norms), and an ethnic group has no fixed
   size against a nation, which an ordered `sequence` needs.  Counterpoint: in May it sits inside the
   narrow-circle cluster ([regionalist] 0.72, [sectarian] 0.68, [parochial] 0.65), so the extraction
   should check where it projects.
4. **[cosmopolitan]: remove, or rewrite as moral cosmopolitanism.**  *Recommend remove*: it is
   openness to cultures, and the world circle is [humanitarian]'s; May neighbours [inclusive] (0.70),
   [collectivistic], [humanistic], [progressive].  (Its May check named "provincial", so the generator does
   read it as the wide end; it also shares its name with a role, [cosmopolitan role], whose pair
   with [provincial role] waits on the role-pair check.)
5. **[civilizationist]: keep.**  Written as scope on 2026-10-02, in [regionalist]'s template.
6. **[insular] and [parochial]: drop [insular] and keep [parochial]** (rewritten, draft below), **or keep
   both, one moved to another step.**  *Recommend drop [insular]*: the two descriptions say the same
   ("local community or familiar group", "local area or familiar social world"); M3 put them at 4,
   "the same concept"; each is the other's nearest description (0.53).  "Parochial" names the local
   circle exactly, while "insular" leans to inward-looking, which [closed-minded] and [incurious]
   cover.  Cost: a tier-2 goal-list slot (#37); no pair, no list.
7. **Rewrite in scope terms: [parochial] and [selfish] only, or also [clannish], [cliqueish],
   [sectarian] and [nationalist]** into [regionalist]'s template ("putting one's own X first: caring
   about ... above ..., and treating those outside it as not one's concern").  *Recommend the two*:
   [parochial] must lose "familiar social world" ([cliqueish]'s step) once [insular] goes, and [selfish]'s
   "actions or advice" is an assistant frame (two words, the same edit as
   [w4_framing.md](./w4_framing.md)).  The other four already read as scope; their extra clauses
   ([clannish] "suspicion ... hostility", [cliqueish] "exclusionary", [sectarian] "rivals") add a hostile
   tone the May vectors show ([cliqueish] near [vindictive], 0.65), but the analysis can take valence
   out (test 2 below), and four goal-list traits would change.  Say if you want them; the template
   makes them quick.

Resulting sequence, the current order kept until the extraction (11): [selfish], [clannish],
[cliqueish], [parochial], [regionalist], [sectarian], [nationalist], [civilizationist],
[humanitarian], [kind-to-animals], [ecocentric].  The four removed members become `singleton` (all
have `non-X` labels); the `note` gains a line for the change.  They stay in the goal lists, where
tier 2 is named for the moral circle; W15 can re-tier.

### Evidence by member

| member | the description is about | nearest, May vectors | proposal |
|---|---|---|---|
| [selfish] | oneself; "actions or advice" | [stingy] 0.70, [greedy] 0.70 | keep; drop "or advice" |
| [clannish] | kin, plus suspicion or hostility | [cliqueish] 0.78, [parochial] 0.69 | keep |
| [cliqueish] | one's immediate social circle, plus exclusion | [clannish] 0.78, [parochial] 0.73, [vindictive] 0.65 | keep |
| [insular] | local community or familiar group | [parochial] 0.75, [regionalist] 0.72 | drop |
| [parochial] | local area or familiar social world | [regionalist] 0.77, [insular] 0.75 | keep, rewrite |
| [regionalist] | a region of one's country (your 2026-09-28 rewrite) | (May had the multi-nation sense) | keep |
| [sectarian] | one's faith | [ethnocentric] 0.68, [regionalist] 0.65 | keep |
| [nationalist] | one's nation | [patriotic] 0.71, [regionalist] 0.67 | keep |
| [patriotic] | love and pride of country | [nationalist] 0.71, [reverent] 0.58 | remove |
| [ethnocentric] | own group's norms as superior | [regionalist] 0.72, [sectarian] 0.68, [elitist] 0.68 | remove |
| [civilizationist] | one's civilization (2026-10-02) | none (new) | keep |
| [cosmopolitan] | openness to cultures | [inclusive] 0.70, [collectivistic] 0.63 | remove |
| [philanthropic] | generous giving | [altruistic] 0.76, [benevolent] 0.69, [generous] 0.68 | remove |
| [humanitarian] | all people | [egalitarian] 0.77, [benevolent] 0.73, [kind-to-animals] 0.73 | keep |
| [kind-to-animals] | animals | [ecocentric] 0.73, [humanitarian] 0.73 | keep |
| [ecocentric] | ecosystems | [kind-to-animals] 0.73, [environmental] 0.73 | keep (a judged pair with [anthropocentric]: never rewrite) |

In descriptions the removed four are the isolated ones: [cosmopolitan]'s nearest is at 0.32 (4th
percentile of the corpus), [patriotic]'s at 0.37 (13th), [philanthropic]'s is [altruistic] (0.44), and
[ethnocentric]'s are [nationalist] and, by word form, [ecocentric] (0.42 each).  M3 put adjacent members at
3 ([clannish]–[cliqueish], [regionalist]–[parochial], [nationalist]–[regionalist], [nationalist]–[civilizationist]),
as neighbours on a scale should be; only [insular]–[parochial] reached 4.

### Drafts

**[parochial]** (label stays `non-parochial`):

> This means putting one's own town or neighborhood first: caring about the people who live there above everyone else, and treating anyone from a few towns over as not one's concern.

31 words, in the template of [regionalist] and [civilizationist], so that the members differ only in
the circle.

**[selfish]** (pair with [altruistic]; only "or advice" goes):

> This means prioritizing one's own interests, desires, and wellbeing above those of others, showing little concern for how one's actions affect other people.

By the rewrite procedure for a pair member (label `non-selfish`, generate, check, restore [altruistic],
`--instructions-only`); the pair was rechecked clean on 2026-10-06.

### What the extraction should test

1. A monotone projection of the 11 members, in the recorded order, onto their first principal
   direction ([AGENT_NOTES.md](../../AGENT_NOTES.md) § "The `arrangement` field", rule 6).
2. **The valence confound, first.**  The inner members are vices and the outer ones virtues, so the
   first direction may be good against bad rather than the size of the circle.  In the May vectors
   the members' first direction (36% of their variance) has cosine 0.73 with [altruistic] − [selfish] and
   0.63 with [benevolent] − [malevolent].  Repeat the test with a valence direction projected out (for
   example [benevolent] − [malevolent], or the assistant axis); count the order as found only if it
   survives.
3. Line or elongated simplex (your 2026-09-07 guess): the variance beyond the first direction (May:
   15% and 10% for the next two).
4. The open steps: [clannish] against [cliqueish] (kin or friends as the smaller circle), [sectarian] (a
   faith can be wider than a nation), [kind-to-animals] against [ecocentric].
5. Where the four removed members project: one that lands at a definite step ([patriotic] at
   [nationalist]'s) could come back.

---

## If every recommendation is taken

| trait | change | then |
|---|---|---|
| [benevolent] | label `non-benevolent`; `triangle` [benevolent], [malevolent], [uncaring] | `--instructions-only` |
| [malevolent] | label [benevolent]; the triangle | `--instructions-only` |
| [uncaring] | description rewritten; the triangle | rewrite procedure (check under `non-uncaring`, then label [benevolent]) |
| [good], [evil], [amoral] | `triangle` [amoral], [evil], [good] beside each pair (list form) | nothing |
| [merciful] | deleted; queue entry `not_adopted` | `sync_entity_lists.py` |
| [cruel] | description rewritten; label `non-cruel`; `singleton` | regenerate, check |
| [accountable], [blame-shifting], [self-blaming] | after the trial: `square` (kite, with the new corner) or `triangle` | nothing |
| [no_fault](../../data/traits/instructions/no_fault.json) (new) | seed under `non-X` | generate, check, `--name-pos`, M3 overlap |
| [hands-off] | description rewritten; `source` moved to [absentee]; `sequence` beside the pair | rewrite procedure |
| [hands-on] | `sequence` beside the pair | nothing |
| [micromanaging], [absentee] | `sequence`; [absentee] gains the MLQ `source` | nothing |
| the 11 sequence members | members and `note` updated | nothing |
| [philanthropic], [patriotic], [ethnocentric], [cosmopolitan] | sequence removed, `singleton` | nothing |
| [insular] | deleted; queue entry `not_adopted`; out of the goal list's tier 2 | `sync_entity_lists.py` |
| [parochial] | description rewritten | regenerate, check |
| [selfish] | "or advice" removed | rewrite procedure |

About eight generations and checks at about $0.03 each, a naming check and an M3 overlap call: well
under $1, live.  Then [check_arrangements.py](../../data_analysis/check_arrangements.py), the check
history records (written before any `--instructions-only` regeneration), and the TRAITS_TO_ADD
sections ([TRAITS_TO_ADD.md](../../data/traits/instructions/TRAITS_TO_ADD.md) § "TODO: arrangement
hunting" and § "TODO: review the moral-circle sequence") updated or moved to
[TRAITS_ADDED.md](../../data/traits/instructions/TRAITS_ADDED.md).

[absentee]: ../../data/traits/instructions/absentee.json
[accountable]: ../../data/traits/instructions/accountable.json
[altruistic]: ../../data/traits/instructions/altruistic.json
[amoral]: ../../data/traits/instructions/amoral.json
[anthropocentric]: ../../data/traits/instructions/anthropocentric.json
[apathetic]: ../../data/traits/instructions/apathetic.json
[benevolent]: ../../data/traits/instructions/benevolent.json
[benign]: ../../data/traits/instructions/benign.json
[blame-shifting]: ../../data/traits/instructions/blame_shifting.json
[bullying]: ../../data/traits/instructions/bullying.json
[callous]: ../../data/traits/instructions/callous.json
[civilizationist]: ../../data/traits/instructions/civilizationist.json
[clannish]: ../../data/traits/instructions/clannish.json
[cliqueish]: ../../data/traits/instructions/cliqueish.json
[closed-minded]: ../../data/traits/instructions/closed_minded.json
[compassionate]: ../../data/traits/instructions/compassionate.json
[controlling]: ../../data/traits/instructions/controlling.json
[cosmopolitan]: ../../data/traits/instructions/cosmopolitan.json
[cosmopolitan role]: ../../data/roles/instructions/cosmopolitan.json
[cruel]: ../../data/traits/instructions/cruel.json
[detached]: ../../data/traits/instructions/detached.json
[dispassionate]: ../../data/traits/instructions/dispassionate.json
[easygoing]: ../../data/traits/instructions/easygoing.json
[ecocentric]: ../../data/traits/instructions/ecocentric.json
[empathetic]: ../../data/traits/instructions/empathetic.json
[ethnocentric]: ../../data/traits/instructions/ethnocentric.json
[evil]: ../../data/traits/instructions/evil.json
[external locus of control]: ../../data/traits/instructions/external_locus_of_control.json
[fatalistic]: ../../data/traits/instructions/fatalistic.json
[forgiving]: ../../data/traits/instructions/forgiving.json
[generous]: ../../data/traits/instructions/generous.json
[gentle]: ../../data/traits/instructions/gentle.json
[good]: ../../data/traits/instructions/good.json
[hands-off]: ../../data/traits/instructions/hands_off.json
[hands-on]: ../../data/traits/instructions/hands_on.json
[harmful]: ../../data/traits/instructions/harmful.json
[harmless]: ../../data/traits/instructions/harmless.json
[helpful]: ../../data/traits/instructions/helpful.json
[humanitarian]: ../../data/traits/instructions/humanitarian.json
[inclusive]: ../../data/traits/instructions/inclusive.json
[incurious]: ../../data/traits/instructions/incurious.json
[indifferent-to-animals]: ../../data/traits/instructions/indifferent_to_animals.json
[insular]: ../../data/traits/instructions/insular.json
[kind-to-animals]: ../../data/traits/instructions/kind_to_animals.json
[laid-back]: ../../data/traits/instructions/laid_back.json
[lenient]: ../../data/traits/instructions/lenient.json
[magnanimous]: ../../data/traits/instructions/magnanimous.json
[malevolent]: ../../data/traits/instructions/malevolent.json
[malicious]: ../../data/traits/instructions/malicious.json
[malign]: ../../data/traits/instructions/malign.json
[merciful]: ../../data/traits/instructions/merciful.json
[micromanaging]: ../../data/traits/instructions/micromanaging.json
[moral]: ../../data/traits/instructions/moral.json
[nationalist]: ../../data/traits/instructions/nationalist.json
[neglectful]: ../../data/traits/instructions/neglectful.json
[nurturing]: ../../data/traits/instructions/nurturing.json
[parochial]: ../../data/traits/instructions/parochial.json
[patriotic]: ../../data/traits/instructions/patriotic.json
[philanthropic]: ../../data/traits/instructions/philanthropic.json
[provincial role]: ../../data/roles/instructions/provincial.json
[regionalist]: ../../data/traits/instructions/regionalist.json
[sectarian]: ../../data/traits/instructions/sectarian.json
[self-blaming]: ../../data/traits/instructions/self_blaming.json
[selfish]: ../../data/traits/instructions/selfish.json
[uncaring]: ../../data/traits/instructions/uncaring.json
[unhelpful]: ../../data/traits/instructions/unhelpful.json
[unrepentant]: ../../data/traits/instructions/unrepentant.json
[vindictive]: ../../data/traits/instructions/vindictive.json
[collectivistic]: ../../data/traits/instructions/collectivistic.json
[egalitarian]: ../../data/traits/instructions/egalitarian.json
[elitist]: ../../data/traits/instructions/elitist.json
[engaged]: ../../data/traits/instructions/engaged.json
[environmental]: ../../data/traits/instructions/environmental.json
[greedy]: ../../data/traits/instructions/greedy.json
[harsh]: ../../data/traits/instructions/harsh.json
[humanistic]: ../../data/traits/instructions/humanistic.json
[progressive]: ../../data/traits/instructions/progressive.json
[responsible]: ../../data/traits/instructions/responsible.json
[reverent]: ../../data/traits/instructions/reverent.json
[stingy]: ../../data/traits/instructions/stingy.json
