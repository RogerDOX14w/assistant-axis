# Roget and WordNet generator: pilot run 2026-10-08-pilot (counts)

Workstream 2 of trait-gap generation, built from
[coding_plan_02_roget_wordnet.md](../../../../../reports/trait_gap_generation/coding_plan_02_roget_wordnet.md)
as revised on 2026-10-08 (no LLM passes; filtering, novelty scoring and recovery are the platform's and
run separately).  Everything here was produced by
[roget_generate.py](../../../../../data_analysis/gap_generation/roget_generate.py).  This readout gives
counts only; the trait-hood filter (M1) and the novelty scorer (M3) have not been run on these rows.

Terms used below.  A **head** is one numbered entry of Roget's Thesaurus (1911), such as 604 Resolution.
The **dispositional** heads are those of Classes IV-VI (intellect, volition, the affections), numbered
450 and up.  An **opposed head** is a head's correlative (605 Irresolution for 604), reconstructed by
rule.  A trait's **primary head** is where its sense sits.  A **gap head** is one in scope that no
existing trait has as its primary head, sorted into **gap classes**: *pair_completion* (its opposed head
is covered), *pair_empty* (it has an opposed head that is not covered), *singleton_empty* (no opposed
head found), *queued_only* (only a seed-queue label sits there).  The **Zipf** value is a word's
frequency on the log scale `wordfreq` uses; the platform drops words under 1.5 and flags 1.5-2.5 (the
**probe band**).

## From the text to the gap heads

| step | count | file |
|---|---|---|
| heads parsed (every number 1-1000 and 44 lettered heads) | 1,044 | [heads.json](../../../roget/heads.json) |
| heads with at least one adjective | 912 | |
| dispositional heads | 576 | |
| dispositional heads paired by rule (strict 256, weak 42) | 298 (149 pairs) | [head_pairs.json](../../../roget/head_pairs.json) |
| dispositional heads left unresolved (no LLM pass; treated as unpaired) | 221 | |
| hand-listed known pairs found | 41 of 42 (606/607 missed) | [known_pairs.json](../../../roget/known_pairs.json) |
| existing traits placed on a head (agree 413, semantic 157, rule 29, lexical 16) | 615 of 790 | [label_heads.json](../../../roget/label_heads.json) |
| seed-queue labels placed | 214 of 362 | [map_spotcheck.md](../../../roget/map_spotcheck.md) (40-row spot check) |
| heads in scope (576 dispositional, 99 from Classes I-III) | 675 | [roget_coverage.md](../../../roget/roget_coverage.md) |
| covered / partly covered / uncovered (of which queued only) | 311 / 75 / 289 (36) | [roget_coverage.json](../../../roget/roget_coverage.json) |
| gap heads: pair_completion / pair_empty / singleton_empty / queued_only | 37 / 46 / 170 / 36 | |

## The pilot harvest (`--every-nth 5`)

Every fifth gap head in text order, with its opposed head when that is a gap head too.

| | count |
|---|---|
| gap heads selected / that gave at least one word | 66 / 50 |
| selected heads by gap class: pair_completion / pair_empty / singleton_empty / queued_only | 7 / 18 / 36 / 5 |
| words harvested (distinct) | 185 (181) |
| words by gap class: pair_completion / pair_empty / singleton_empty / queued_only | 28 / 80 / 63 / 14 |
| cut: not the most frequent word of its semicolon group | 138 |
| cut: more than two words / ending in a function word ("shy of") | 80 / 37 |
| cut: under the Zipf floor | 48 |
| cut: over the per-head cap of 10 | 24 |
| cut: already a corpus or queue label / repeated | 10 / 1 |
| words in the probe band / from Class VI / with a WordNet adjective sense | 18% / 25% / 78% |
| pair candidates across opposed gap heads (WordNet antonyms 4, negation forms 5, the rest rank-matched) | 39 |
| candidates carrying a partner hint (word-level opposites only: used / disused, dear / cheap, named / unnamed, comparable / incomparable, ...) | 14 |
| gloss hints shorter than 18 words (heads 768a and 527a are too sparse) | 2 of 185 |

Files: [candidates.jsonl](./candidates.jsonl) (one line per `Candidate`, exactly as submitted),
[pair_candidates.jsonl](./pair_candidates.jsonl), [harvest_report.md](./harvest_report.md) (words per
head), [harvest_counts.json](./harvest_counts.json), [run.json](./run.json), [usage.json](./usage.json).

## The WordNet sibling stream (`wn_clusters`)

| | count |
|---|---|
| WordNet antonyms of existing traits with no partner file | 63 |
| adjectives derived from the trait-noun closure (trait, disposition, temperament, attitude, character; three levels) | 371 |
| pilot: every fifth of the 434 (13 antonyms, 74 closure adjectives) | 87 |

Files: [wn_clusters candidates.jsonl](../../wn_clusters/2026-10-08-pilot/candidates.jsonl) and
[wn_items.jsonl](../../wn_clusters/2026-10-08-pilot/wn_items.jsonl) (all 434 with their route).  The
antonym route's partner hint is the trait it opposes, for example
[approximate](../../../../traits/instructions/approximate.json) for *exact* and
[savage](../../../../traits/instructions/savage.json) for *civilized*.

## Submitted (this worktree's registry)

| generator | candidates | new rows | merged into an existing row |
|---|---|---|---|
| roget | 185 | 181 | 4 (one word from two heads) |
| wn_clusters | 87 | 86 | 1 (*litigious*, also harvested from Roget) |

The registry log is per checkout and git-ignored; the main checkout resubmits from the tracked files
with `gap_registry.py submit --file <run dir>/candidates.jsonl --generator G --run-id 2026-10-08-pilot`
(idempotent).

## Spend

- Embeddings for the semantic route of the label placement: OpenAI `text-embedding-3-large`, 10 calls,
  104,065 tokens, **$0.0135** ([mapping_usage.json](../../../roget/mapping_usage.json)).
- The harvest and the two submissions: no calls ($0; [usage.json](./usage.json)).
- Downstream, at the platform's rates (about $0.004 a word for M1 and $0.018 a word passing M1 for M3):
  the 272 pilot words cost about $1.10 for M1 and about $2.50 for M3 if half pass.
