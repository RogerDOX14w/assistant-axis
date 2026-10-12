# What needs regenerating after the review's fixes

Started 2026-10-12 at Roger's request ("a list of data (gap filling work, caches, plots, etc) that now needs
regenerating as a result of bugs we've fixed").  One entry per thing on disk that a fixed bug made wrong,
stale or incomplete: registry blocks, judge caches, vectors, plots, tables, readouts, usage records.

**Every agent that fixes a bug adds an entry here** when the fix leaves recorded output wrong or stale, in
the same commit as the fix, or says in its report that nothing needs regenerating.  A row is closed when
the regeneration has run: put the commit or batch id in **status**.  The review's decisions are in
[escalations.md](./escalations.md); the gate fixes in [gate_audits/README.md](./gate_audits/README.md).

**When** takes one of four values:

- **now**: wrong today and cheap; run it in the fix batch.
- **before October**: must be done before the October activation extraction starts.
- **at the October run**: the October extraction or its re-score regenerates it anyway; nothing to do
  except make sure the run covers it.
- **never**: recorded as a known limit of historical output; kept for the record, not regenerated.

Costs are API dollars unless marked.  Anything over $20 in one invocation still needs Roger's go with
quoted parameters.

## Gap-filling work (the gate fixes, phase B)

The order matters: each step sees the verdicts written before it.  Commands are in each fix agent's
report and in [gate_audits/README.md](./gate_audits/README.md) "Fixes".

| # | what | why (fix) | how | cost | when | status |
|---|---|---|---|---|---|---|
| G1 | M1 verdicts on 126 phrase rows (the alignment papers, IPIP probe cuts, the alignment batches) | the definition probe cut phrase labels unread (gate 5, 1920bbc2) | `traithood_filter.py --batch-id 2026-10-13-m1_phrase_rejudge --keys <126 keys>`, then M3 on the rows that become traits | about $1.9 live | now | |
| G2 | 20 more phrase rows from Roget, the censuses and the antonym and validation runs | same | same, on the "others" set | under $1 | now | |
| G3 | base-model candidates at count 2 or more (about 219 new rows) | the count floor of 8 discarded half the trait words; rule 1b missing in the table (gate 3, 29610c17) | `base_model_generator.py parse`, `sense`, `stats`, `submit --min-count 2`, then M1 and M3 | about $3.5 live | now | |
| G4 | the census table (OEWN lemmas) and the `allport_rare` (926) and `allport_iv_rare` (310) submissions | the column-IV words below the floor had no stage; the floor's rescues were lost (gate 1, 1920bbc2) | `census_generator.py ingest`, `submit` both stages, M1 and M3 by batches | about $8.5-10.5 batch | now | |
| G5 | irresolute's floor reject | defect F3: another generator's earlier floor reject defeated the census rescue (1920bbc2) | `traithood_filter.py --run censuses/2026-10-10-tda`, then M3 and the TDA report | cents | now | |
| G6 | Roget (14) and WordNet (178, 70 new rows) candidates; the Roget coverage report | WordNet depth 3 had no basis; rule 1b missing in both dictionary walks (gate 2, fc1834b2) | `roget_generate.py harvest --delta-from 2026-10-11-full`, `submit` both, M1, M3, then `coverage` | about $1.1 | now | |
| G7 | M3 decisions on 187 rows of 20 batches (new to covered) and 8 stage-0 leak rows | the graded cut-off at alignment 2; a renamed trait's old stem was checked after the seed queue (gate 6, review 2 D1; 403cbd6a) | `novelty_score.py score --redecide --from-batch B --rules 3 --write-registry` per batch, then `gap_registry.py compact` | about $0.06 | now | |
| G8 | M3 decisions of 33 `2026-10-11-full_roget` rows made on glosses that have since been rewritten | found by the M3 fix agent: the rows were re-glossed after M3 judged them | `novelty_score.py score --rescore` on those rows | under $1 | now | |
| G9 | the states pass on the 245 judged rows (7 change), the 900 unjudged states rows and the 126 physical rows | the gloss check held traits; one-hop rows were held (gate 7, fb66cc14) | `states_pass.py --reroute --send-missing`, then the passes, then M3 on released rows | about $3 live | now | |
| G10 | IPIP: cluster tables (done at $0 in 3f1d78e2), naming, granularity readings, submission, M1, M3 | the Jaccard gate held 65-92% of clusters (gate 4) | after C1 below: naming at 600/350/150, `granularity --signals nearest`, `submit --granularity 600 --all-poles`, M1, M3 | about $11 | now | |
| G11 | the review graph, all batches | the pair floor and label-variant links (gate 8, 0b9ce75e); and every step above changes its input | the Opus pilot ($0.42 live), then `review_graph.py build` over all trait-track batches | about $31 | after G1-G10; **needs Roger's go** | |

## Caches, plots and analysis outputs

| # | what | why (fix) | how | cost | when | status |
|---|---|---|---|---|---|---|
| R1 | two response-judge caches with a marker-less reply | the analysis parser read a digit from the reasoning (walk-through D5) | hand-edited to None, with backups and envelope notes | $0 | now | done 2026-10-12 |
| R2 | the winner-decomposition figure of the PC round-trip study, and the ~12 boundary reading | it decomposed the nth PC at the fixed-principled winners' cell, and skipped slots 0 and 3 (walk-through D1) | record per-cell winners in `klm_sweep.py`, regenerate and retitle | $0, CPU-hours to estimate | now | |
| R3 | every response-mode plot (slot, shear and layer plots on GPT-only responses) | standardise on the GPT+Haiku blend (walk-through D10) | regenerate from the October re-score | at the re-score | at the October run | |
| R4 | the May judge caches deferred under `legacy_bare` (832 without envelopes, 915 stale with) | the blanket globs hid stale envelope-carrying caches (walk-through E10) | record their real state under a new category; regenerate at the October re-score | at the re-score | at the October run | |
| R5 | IPIP scoring keys, then ingest, cluster and the names of changed poles | the merge gap-filled workbook rows the key pages already held (C1) | after the fix: `ipip_generator.py ingest`, `cluster`, re-name changed poles | cents | now, before G10 | |
| R6 | the current pair lists (`goal_type`) and a `_v1` snapshot of the pre-W15 goal file | the current lists predate the W15 goal lists (walk-through A3) | snapshot, then regenerate the current lists from the W15 file | $0 | before October | |
| R7 | the usage record of `m1_validation_r2` | a resume lost the killed session's spend (walk-through B3) | rebuild from its responses | $0 | now | |

## Vectors and activations

| # | what | why (fix) | how | cost | when | status |
|---|---|---|---|---|---|---|
| V1 | every stored entity vector and `axis.pt` | bf16 accumulation and storage at steps 4 and 5 (walk-through P3) | the October extraction writes float32 | GPU time of the run | at the October run | |
| V2 | every role judgment | artefacts in all 339 role eval prompts (walk-through P4; the wording waits on Roger) | the October step 3 re-judges every role | in the run's judge cost | at the October run | |

## Added by fix agents

(Agents append rows here, in the table form above, one row per item.)

| # | what | why (fix) | how | cost | when | status |
|---|---|---|---|---|---|---|
