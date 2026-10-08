# R1 pilot readout: the candidate graph of the three generator pilots

Built 2026-10-08 by the R1 coding agent (Opus), for Fable to read before R2 starts.  Brief:
[coding_plan_review.md](../../../../reports/trait_gap_generation/coding_plan_review.md), section 2 and task 3 of
section 6.  Terms not defined here are in the [glossary](../../../../reports/trait_gap_generation/glossary.md).

Files of this run, all in this directory: [graph.json](./graph.json) (the graph, in a provenance envelope),
[usage.json](./usage.json) (the spend), [run.json](./run.json) (settings, the estimate, the calls sent, the graph's
counts), [responses.jsonl](./responses.jsonl) (every response received) and [run.log](./run.log).  Code:
[review_graph.py](../../../../assistant_axis/gapgen/review_graph.py) (the module) and
[review_graph.py](../../../../data_analysis/gap_generation/review_graph.py) (the CLI).

Command:

```
uv run python data_analysis/gap_generation/review_graph.py build --batch-id review_pilots_1 \
    --from-batches gen_pilot_censuses gen_pilot_roget gen_pilot_wn_clusters --transport live --budget-usd 6
```

## Headline

- **325 kept candidates, 21 4-edges, 19 cliques (18 pairs and one triple), 290 singletons.**  Only 35 of the 325
  candidates are in any clique.  If merged-by-default cliques are meant to save Roger review time, they save little
  at rubric A's 4: the review would still meet about 309 separate groups.
- **The plan's own example groups are not 4-cliques.**  `godless` / `irreligious` / `nonreligious` read 3 / 3
  (Sonnet / Opus) on every pair ("they differ mainly in scope"), as do `complying` / `willing` and `complying` /
  `slavish`; `backbiting` / `scandalmongering` reads 2.  Rubric A's 4 ("either label could replace the other in any
  description of a persona") is a much stricter bar than "near-synonym".
- **Cost $1.51** against an estimate of $4.15 (cap $6).  The estimate used M3's shares of similar pairs, which are
  far higher than the shares among candidate pairs (details below).
- Every call parsed on its first attempt; nothing stalled; the graph is complete.

## What was built (terms)

- **Kept candidate**: a registry row whose M3 decision is `new` or `grey` in one of the named M3 batches.  M3 had
  decided 333 rows `new` across the three batches, but 8 rows were decided by two batches and the registry keeps
  only the later decision, so the batches hold **325 distinct candidates**.
- **Cosine**: the cosine of two candidates' query embeddings (the gloss cut to 14 words, as M3 embeds it) in M3's
  **covered space** (the embedding centred on the corpus).  The cosines are therefore on the same scale as M3's
  candidate-to-corpus cosines, and the floors calibrated on M3's readings apply.
- **Candidate edge**: each kept candidate's 10 nearest other kept candidates at cosine 0.25 or above (the
  retrieval floor), one edge per pair.
- **Relation call**: one call per candidate (Haiku 5.5, rubric [relation.md](../../../../reports/trait_gap_generation/rubrics/relation.md)
  version 1), listing its neighbours with their glosses, each answered `similar`, `opposed`, `unrelated` or
  `unsure`.  The `unsure` answers are asked again of Sonnet 5.5, as M3 does.
- **Overlap call**: rubric A ([overlap_concept.md](../../../../reports/trait_gap_generation/rubrics/overlap_concept.md)
  version 6), one pair per call, run through M3's own runner (`NoveltyRunner.run_pairs`) with the other candidate
  in the "other trait" slot.  Sonnet 5.5 reads each pair first; Opus 5.5 reads it again when Sonnet gives 3, 4 or
  unsure (M3's rule at **cut-off 4**).  A direction **reads 4** when Sonnet's 4 is confirmed by Opus, Sonnet's 3 is
  raised to 4 by Opus, or Sonnet is unsure and Opus gives 4.
- **Overlap floor**: no overlap call on a pair below cosine 0.35 (decision 11).
- **First and second direction**: a pair is read first with the candidate whose key sorts first as the "target",
  and in the other direction only when the first direction reads 4 (see "Deviations").
- **4-edge**: both directions read 4, and the relation is not `opposed`.
- **Clique**: a maximal set in which every pair is a 4-edge.  Cliques may share members.  A **singleton** is a kept
  candidate in no clique.
- **Corpus edges**: copied without a call from each candidate's M3 block (`novelty.listed` and
  `novelty.readings`).  M3's covered candidates (255) appear as greyed nodes pointing at the trait that covered them
  (decision 9), with no edge and no call.

## Candidates

| M3 batch | kept (new) | covered, shown greyed |
|---|---|---|
| [gen_pilot_censuses](../../novelty/gen_pilot_censuses/decisions.md) | 230 | 217 |
| [gen_pilot_roget](../../novelty/gen_pilot_roget/decisions.md) | 65 | 18 |
| [gen_pilot_wn_clusters](../../novelty/gen_pilot_wn_clusters/decisions.md) | 30 | 20 |
| total | **325** | 255 |

The graph has 704 corpus-trait nodes (every corpus trait a kept candidate's M3 block listed) and 7 seed-queue nodes
(the queue entries that covered a candidate by its exact label; [seed_queue.json](../../../seed_queue.json)).

## Edges

**Candidate edges: 2,156** (3,224 neighbour slots; 1,088 pairs appear in only one candidate's list, so they carry one
relation answer).

| relation (both answers combined) | edges |
|---|---|
| similar | 721 |
| unrelated | 1,286 |
| opposed | 146 |
| mixed (similar from one side, opposed from the other) | 2 |
| unsure | 1 |

Relation answers given (per direction, after the unsure re-ask): 1,057 similar, 1,979 unrelated, 186 opposed, 2
unsure.  42 relation calls had an `unsure` answer and were re-asked of Sonnet.

**Corpus edges: 5,735**, copied from the M3 blocks (1,439 similar, 1,772 opposed, 2,515 unrelated, 9 unsure; 2,037
with overlap readings).  No call.

## Overlap calls

| | pairs |
|---|---|
| candidate pairs at cosine 0.35 or above | 1,510 |
| ... read (relation similar, unsure or mixed) | **647** first direction, **25** second direction |
| ... not read: the relation was unrelated or opposed | 863 |
| similar pairs below the floor, not read | **77** |

Calls sent ([run.json](./run.json) `calls_sent`): 325 relation calls (Haiku 5.5), 42 unsure re-asks (Sonnet 5.5), 672
overlap calls on Sonnet 5.5 (647 + 25) and 121 on Opus 5.5.  Parse rate 100% on every step and model, first attempt.

By cosine bin (the edges at the floor or above):

| cosine | pairs | read | Opus asked | first direction read 4 | 4-edges |
|---|---|---|---|---|---|
| 0.35-0.45 | 846 | 227 (27%) | 5 | 1 | 0 |
| 0.45-0.55 | 437 | 224 (51%) | 20 | 2 | 2 |
| 0.55-0.65 | 147 | 117 (80%) | 24 | 6 | 4 |
| 0.65 and above | 80 | 79 (99%) | 47 | 16 | 15 |

The lowest cosine of a 4-edge is 0.517.  The 451 pairs read between 0.35 and 0.55 cost about $0.65 and produced 2 of
the 21 4-edges.

## 4-edges and Sonnet / Opus agreement on the 4s

**25 pairs read 4 in the first direction; 21 of them read 4 again in the second: 21 4-edges.**

Of the 46 directions that read 4, 10 were Sonnet 4 confirmed by Opus and **36 were Sonnet 3 raised to 4 by Opus**.
Opus confirmed all 10 of Sonnet's 4s.  Of the 111 Sonnet 3s that Opus read, it raised 36 to 4, kept 69 at 3 and
lowered 6 to 2.  Sonnet gave 4 on only 10 of its 672 readings.  So the 4-edges rest mostly on Opus raising a 3, and
the 4 asymmetric pairs below (first direction 3 then 4, second direction 3 then 3) show how fine that line is:

- divisive > factious (cosine 0.79), frightening > menacing (0.62), incompliant > indocile (0.42), nasty > unkind (0.63).

## Cliques

By size: 1 of three members, 18 of two.  All 19 are listed below (the ten largest would be the triple and the
first nine pairs).  Members are candidate labels, which have no corpus file; the last column links the corpus traits
that M3 marked `similar` nearest to any member.

| # | members | generators | readings, Sonnet/Opus, one way then the other | cosine | nearest corpus traits M3 marked similar (cosine) |
|---|---|---|---|---|---|
| 0 | frigid, unaffable, warmthless (opposed to 2) | censuses 3 | frigid-unaffable 3/4, 3/4; frigid-warmthless 3/4, 4/4; unaffable-warmthless 3/4, 4/4 | 0.90, 0.87, 0.87 | [reserved](../../../traits/instructions/reserved.json) (0.46), [unsentimental](../../../traits/instructions/unsentimental.json) (0.37) |
| 1 | affectionate, fond | wn_clusters 2 | 3/4, 4/4 | 0.60 | [friendly](../../../traits/instructions/friendly.json) (0.43), [compassionate](../../../traits/instructions/compassionate.json) (0.40) |
| 2 | affectionate, loving (opposed to 0, 10) | wn_clusters 2 | 3/4, 3/4 | 0.84 | [friendly](../../../traits/instructions/friendly.json) (0.39), [compassionate](../../../traits/instructions/compassionate.json) (0.34) |
| 3 | charming, pleasing | censuses 2 | 3/4, 3/4 | 0.62 | [friendly](../../../traits/instructions/friendly.json) (0.42), [easygoing](../../../traits/instructions/easygoing.json) (0.37) |
| 4 | discordant, inharmonious | roget 1, censuses 1 | 4/4, 4/4 | 0.77 | [disagreeable](../../../traits/instructions/disagreeable.json) (0.51), [quarrelsome (HEXACO)](../../../traits/instructions/quarrelsome_hexaco.json) (0.39) |
| 5 | foul-mouthed, profane | censuses 1, wn_clusters 1 | 4/4, 4/4 | 0.68 | [rude](../../../traits/instructions/rude.json) (0.25), [brash](../../../traits/instructions/brash.json) (0.20) |
| 6 | free, unbound | roget 2 | 3/4, 3/4 | 0.67 | [rule-breaking](../../../traits/instructions/rule_breaking.json) (0.34), [independent](../../../traits/instructions/independent.json) (0.33) |
| 7 | good-hearted, kindhearted | censuses 2 | 4/4, 4/4 | 0.72 | [generous](../../../traits/instructions/generous.json) (0.45), [friendly](../../../traits/instructions/friendly.json) (0.44) |
| 8 | grumbly, querulous | censuses 1, roget 1 | 3/4, 3/4 | 0.77 | [quarrelsome (HEXACO)](../../../traits/instructions/quarrelsome_hexaco.json) (0.41), [petty](../../../traits/instructions/petty.json) (0.33) |
| 9 | headstrong, willful | censuses 1, wn_clusters 1 | 3/4, 3/4 | 0.80 | [unyielding](../../../traits/instructions/unyielding.json) (0.46), [rigid](../../../traits/instructions/rigid.json) (0.39) |
| 10 | impersonal, warmthless (opposed to 2) | censuses 2 | 3/4, 3/4 | 0.89 | [reserved](../../../traits/instructions/reserved.json) (0.46), [detached](../../../traits/instructions/detached.json) (0.39) |
| 11 | imprudent, incautious | censuses 1, wn_clusters 1 | 3/4, 3/4 | 0.80 | [impulsive](../../../traits/instructions/impulsive.json) (0.57), [bold](../../../traits/instructions/bold.json) (0.45) |
| 12 | infernal, satanic | roget 2 | 3/4, 3/4 | 0.57 | [malicious](../../../traits/instructions/malicious.json) (0.55), [evil](../../../traits/instructions/evil.json) (0.50) |
| 13 | inharmonious, quarrelsome | censuses 1, roget 1 | 3/4, 3/4 | 0.52 | [confrontational](../../../traits/instructions/confrontational.json) (0.36), [disagreeable](../../../traits/instructions/disagreeable.json) (0.35) |
| 14 | inhuman, insensate | censuses 2 | 3/4, 3/4 | 0.70 | [cruel](../../../traits/instructions/cruel.json) (0.50), [callous](../../../traits/instructions/callous.json) (0.48) |
| 15 | nasty, unkindly | censuses 2 | 3/4, 3/4 | 0.57 | [harsh](../../../traits/instructions/harsh.json) (0.51), [cruel](../../../traits/instructions/cruel.json) (0.41) |
| 16 | uncouth, ungenteel | censuses 2 | 3/4, 3/4 | 0.73 | [blunt](../../../traits/instructions/blunt.json) (0.55), [plain-spoken](../../../traits/instructions/plain_spoken.json) (0.44) |
| 17 | ungainly, ungraceful | censuses 2 | 3/4, 4/4 | 0.70 | none marked similar |
| 18 | unkind, unkindly | censuses 2 | 3/4, 3/4 | 0.52 | [malicious](../../../traits/instructions/malicious.json) (0.51), [harsh](../../../traits/instructions/harsh.json) (0.51) |

Four candidates sit in two cliques each (affectionate, inharmonious, unkindly, warmthless): the overlapping cliques
the plan expected, here {affectionate, fond} and {affectionate, loving} (fond and loving read 3), and {nasty,
unkindly} and {unkind, unkindly} (nasty > unkind is one of the asymmetric pairs).

**Opposed pairs of cliques** (joined by an opposed candidate edge): [0] frigid, unaffable, warmthless with [2]
affectionate, loving; and [2] affectionate, loving with [10] impersonal, warmthless.  There are 146 opposed candidate
edges in all, most of them between singletons.

**Singletons: 290** (208 censuses, 58 roget, 24 wn_clusters).

## What a cut-off of 3 would give (one direction only; no extra call)

Taking the first-direction reading alone, 90 pairs read 3 or 4.  Their maximal cliques would be 57 (42 pairs, 12
triples, 3 of four) covering **103 candidates**, among them the plan's examples: godless, irreligious, nonreligious;
balky, headstrong, incompliant, indocile; frigid, impersonal, unaffable, warmthless; infernal, nasty, satanic,
unkind; affectionate, fond, loving; alarming, frightening, menacing; curmudgeonly, grumbly, querulous.  This is one
direction only.  Making these real 3-edges needs the second direction of about 65 pairs, roughly $0.35 at this
run's rates, and a cut-off parameter in the module, which is not built (the cut-off is fixed at 4 as decision 2
says).  Whether the default groups should be 3-cliques, or 4-cliques with 3-edges shown as merge suggestions, is a
decision for Roger and Fable.

## Cost

| | |
|---|---|
| estimate before any call | $4.147 |
| re-estimate after the relation calls (the gate: spent $0.267 + overlap $2.415 on the 647 pairs marked) | $2.682 |
| **spent** ([usage.json](./usage.json)) | **$1.510** |
| cap | $6.00 |

By model: Haiku 5.5 $0.164 (325 calls); Sonnet 5.5 $0.920 (714 calls: 672 overlap, 42 unsure re-asks); Opus 5.5
$0.426 (121 calls).  No embedding call: all 325 query embeddings were in the cache.

Why the estimate was 2.7 times the spend: it took its shares from M3's candidate-to-corpus pairs (similar 76-100% by
cosine bin, Opus asked on 12-100%, first direction reading 4 on 0.4-100%).  Among candidate pairs the relation call
marked far fewer similar (27-99% by bin, 43% overall) and Sonnet sent far fewer to Opus (2-59% of those read).  The
gate's re-estimate, with the similar pairs known, was still 1.8 times the spend, because its Opus and second-direction
shares were M3's.  The next run's estimate can take its shares from this run's records instead; that is not built.

## Anything that looks wrong

1. **The groups are small.**  This is the main finding, covered above.  Rubric A's 4 is a scope-equality bar, and the
   census lists' near-synonyms mostly differ "mainly in scope" (3).
2. **The 4s rest on Opus raising Sonnet's 3s** (36 of 46), and 4 pairs flip between directions.  A clique built on
   a single Opus 3-or-4 call per direction is noisy at the boundary.
3. **Two mixed relations**: high-handed / impertinent (Haiku called impertinent the opposite of high-handed; the
   other side said similar; the overlap read 1) and refreshing / ungenteel (opposed from one side; the overlap read
   2).  Both are harmless: neither became a 4-edge.  But Haiku's "opposed" on high-handed / impertinent is wrong.
4. **One-sided neighbour lists**: 1,088 of the 2,156 candidate edges are in only one candidate's top 10, so they carry
   one relation answer.  That is enough for the overlap decision (either side's `similar` sends the pair).
5. **Cosine scale**: the plan quotes the median candidate's nearest other candidate at cosine 0.66.  In M3's covered
   space, which this build uses, it is 0.56.  The 0.66 was probably raw (uncentred) cosine; the floors are meant for
   the covered space, so nothing changes.
6. **The 0.35 floor is cheap insurance with little yield on candidate pairs**: the lowest 4-edge is at 0.517, and the
   0.35-0.45 bin (846 pairs, 227 read) produced none.  It keeps its purpose (decision 11 was calibrated on M3's
   readings), but a floor of 0.45 would have saved about $0.30 here (a fifth of the spend) with the same cliques.

## Deviations from the plan

- **The second direction is read only where the first reads 4.**  The plan says "in both directions" for every
  similar pair.  Only a pair read 4 both ways is a 4-edge (decision 2), so the cliques are identical; reading both
  directions of all 647 pairs would have cost about $1.1 more here (622 more Sonnet readings, about $0.80, and their
  Opus calls, about $0.33 at the first direction's Opus share).  At the dry run's shares it would have come to
  about $6.6, over the cap.  Non-4 pairs therefore carry one direction's reading.
- **"Earlier unresolved candidates"** (section 2's index) are not in the candidate index: no review batch has
  resolved anything yet, and the pilot command names three batches.  The kNN runs over the named batches' kept
  candidates.
- **M3's covered candidates are included as greyed nodes** (decision 9), pointing at the trait that covered them,
  with no edge.  This is an addition for R2, which the plan's node schema (`decision`, `covered_by`) anticipates.
- **Relations beyond the plan's three**: an edge's relation combines its one or two answers.  `mixed` means one side
  said similar and the other opposed; `unsure` means unsure after the re-ask, or a relation call that never parsed
  (M3's fallback).  Both are sent to the overlap call like `similar`.
- **`build_graph`'s signature** takes a plan (`plan_graph`: rows, batches, projected vectors) and a `ReviewRunner`
  instead of `registry_path` / `runner_factory`, so that the module needs no embedding or registry I/O.

## Appendix: the two prompts as the models receive them

From the dry run: the relation call of the candidate whose nearest neighbour is closest (frigid; system prompt
[relation.md](../../../../reports/trait_gap_generation/rubrics/relation.md) version 1), then the overlap call of that
pair (system prompt [overlap_concept.md](../../../../reports/trait_gap_generation/rubrics/overlap_concept.md) version 6,
cached).

```
{"candidate": {"label": "frigid", "description": "This means keeping one's manner cool and distant, withholding warmth from others and showing little affection, sympathy or friendliness in dealings with people."},
 "traits": [
  {"id": 1, "label": "impersonal", "description": "This means keeping one's manner distant and cool, offering no personal warmth, friendliness or emotional engagement in how one speaks and deals with others."},
  {"id": 2, "label": "inhospitable", "description": "This means keeping guests and strangers at a distance, offering them no warmth, no food or shelter, and little courtesy, and making it plain they are not wanted."},
  {"id": 3, "label": "intimidating", "description": "This means carrying a manner so forbidding that others grow wary and hesitant in one's presence, speaking with a hard stare and clipped authority that leaves people uneasy and overawed."},
  {"id": 4, "label": "unaffable", "description": "This means keeping one's manner cold and distant toward others, offering little warmth and holding people at a firm arm's length."},
  {"id": 5, "label": "inexpressive", "description": "This means keeping one's face and voice level whatever one feels, letting little emotion show, and answering good news and bad in the same flat, deadpan, reserved manner."},
  {"id": 6, "label": "warmthless", "description": "This means keeping one's manner cool and distant, showing little affection or friendliness toward others, and speaking with a detached aloofness that leaves people feeling unwelcome."},
  {"id": 7, "label": "unpersonable", "description": "This means meeting others with a cold, curt manner, offering little warmth or courtesy, and coming across as sour, prickly and hard to like in every exchange."},
  {"id": 8, "label": "hard-shelled", "description": "This means keeping one's feelings guarded and refusing to be moved by sentiment, judging people and situations on hard facts and standing firm when pressed."},
  {"id": 9, "label": "prim", "description": "This means keeping one's manner rigidly correct and starchy, holding to strict propriety in speech and conduct, and treating any hint of informality or indelicacy as a lapse to be disapproved of."},
  {"id": 10, "label": "impassive", "description": "This means keeping one's face calm and expressionless and showing no emotion, even when something stirring or upsetting happens around one."}
 ]}
```

```
{"target": {"label": "frigid", "description": "This means keeping one's manner cool and distant, withholding warmth from others and showing little affection, sympathy or friendliness in dealings with people."},
 "other": {"label": "unaffable", "description": "This means keeping one's manner cold and distant toward others, offering little warmth and holding people at a firm arm's length."}}
```

Read for fit: the relation rubric's opening ("a persona trait, the candidate, ... and a numbered list of other persona
traits") fits a list of candidates as well as a list of corpus traits; the ids number the listed candidates in the
order sent.  The overlap call's "other" is a candidate's gloss where M3 has a corpus description; the rubric does not
depend on which kind it is.
