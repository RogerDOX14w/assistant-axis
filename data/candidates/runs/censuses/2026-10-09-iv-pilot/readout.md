# Census generator: run `2026-10-09-iv-pilot` readout

Stage `allport_iv`, every 10th row in rank order (offset 0).  Plan: [coding_plan_01_censuses.md](../../../../../reports/trait_gap_generation/coding_plan_01_censuses.md) (its last section, the revision for the interface as built, governs).  Terms: [glossary](../../../../../reports/trait_gap_generation/glossary.md).  Written by [census_generator.py](../../../../../data_analysis/gap_generation/census_generator.py) `report`; the numbers are in [evaluation.json](evaluation.json).

Definitions used below.  **TDA**: the Trait Descriptive Adjectives list (2,818 words with, for each, `prop`, the proportion of raters who knew the word; Dataverse, CC0).  **Allport-Odbert**: the 1936 list of about 18,000 person words in four columns (I traits, II temporary states, III social evaluations, IV metaphorical or doubtful; OSF transcription, CC BY 4.0).  **Zipf**: log10 of a word's frequency per billion words (`wordfreq`).  **The floor**: the platform's hard-reject line below Zipf 1.5 for a dictionary word, with a definition probe from 1.5 to 2.5 ([gapgen/freq.py](../../../../../assistant_axis/gapgen/freq.py)); a curated generator such as this one is never hard-rejected by the platform, its rare words go to the probe.  **M1 / M3**: the platform's trait-hood filter and novelty scorer.

## Counts

| step | count |
|---|---|
| census table rows (distinct stems) | 17,958 |
| TDA words parsed | 2,818 |
| Allport-Odbert words parsed (distinct) | 17,708 (lines I 4470, II 4511, III 5191, IV 3652) |
| in both lists | 2,569 |
| malformed (dropped) | 1 |
| eligible rows of this stage | 2013 |
| TDA words cut by the floor | 0 (every TDA word is submitted; 251 of them are below the dictionary floor and reach the platform's probe through the curated route) |
| Allport-only words cut by the floor (not in any stage) | below_hard_reject 1,341, unknown_word 5,614 |
| Allport-only words in later stages | allport_hi 4,746, allport_probe 3,438 |
| **submitted in this run** | **202** (138 with a gloss hint, 0 framed as a disposition from Allport-Odbert column II) |
| of those, routed to the platform's definition probe | 92 (band 52, negating_prefix 40) |
| registry: new rows / merged into existing rows / unchanged | 199 / 3 / 0 (invalid surfaces: 0) |
| duplicates merged at ingest | Allport cross-column 58, within-column 57, TDA and Allport 2,569, TDA multi-row 0, one-edit repairs 23 |
| known labels submitted (corpus traits) | 2 |

Downstream estimate when submitted (batches): M1 $0.73 + M3 $0.98 = $1.70; the generator itself spent $0.94 ([usage.json](usage.json)).

## String ceiling

Of the corpus's 790 traits (244 of them multi-word), the census lists contain as strings: TDA 394 (49.9%), Allport-Odbert 411 (52.0%), either 444 (56.2%; 77.5% of the single-word traits).  The generator's own eligibility rule submits 444 of the 444 (100.0%; the policy asks for 95%).  Of the 238 queued traits, 65 are in either list.  Source: [ingest_counts.json](../../../censuses/ingest_counts.json).

## Known labels in this run

2 submitted words are existing corpus traits (each links to its file): [monogamous](../../../../traits/instructions/monogamous.json), [nearsighted](../../../../traits/instructions/nearsighted.json).

## Filter (M1)

202 of 202 rows filtered.  Verdicts: reject 50, tagged 66, trait 86.  Tags: evaluative_only 2, membership 23, no_persona_reading 28, physical 23, role_person 9, state 34, stretched 20.
Known-label pass rate (verdict trait, or tagged state or physical): 2 of 2 (100.0%).  Misses: none.

## Novelty (M3)

80 rows scored: covered 17, new 63; pair completions 10.

## Files

- [candidates.jsonl](candidates.jsonl): the submitted candidates, one per line (tracked; the main checkout resubmits it with [gap_registry.py](../../../../../data_analysis/gap_generation/gap_registry.py) `submit --file`)
- [run.json](run.json), [usage.json](usage.json), [keys.txt](keys.txt), [submit_report.json](submit_report.json), [evaluation.json](evaluation.json)
- [census_table.jsonl](../../../censuses/census_table.jsonl) (the census table), [ingest_counts.json](../../../censuses/ingest_counts.json) (ingest counts), [sources_manifest.json](../../../censuses/sources_manifest.json) (downloads: URLs, hashes, licences, attribution)
