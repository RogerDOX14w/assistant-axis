# Census generator: run `2026-10-12-allport_rare` readout

Stage `allport_rare`.  Plan: [coding_plan_01_censuses.md](../../../../../reports/trait_gap_generation/coding_plan_01_censuses.md) (its last section, the revision for the interface as built, governs).  Terms: [glossary](../../../../../reports/trait_gap_generation/glossary.md).  Written by [census_generator.py](../../../../../data_analysis/gap_generation/census_generator.py) `report`; the numbers are in [evaluation.json](evaluation.json).

Definitions used below.  **TDA**: the Trait Descriptive Adjectives list (2,818 words with, for each, `prop`, the proportion of raters who knew the word; Dataverse, CC0).  **Allport-Odbert**: the 1936 list of about 18,000 person words in four columns (I traits, II temporary states, III social evaluations, IV metaphorical or doubtful; OSF transcription, CC BY 4.0).  **Zipf**: log10 of a word's frequency per billion words (`wordfreq`).  **The floor**: the platform's hard-reject line below Zipf 1.5 for a dictionary word, with a definition probe from 1.5 to 2.5 ([gapgen/freq.py](../../../../../assistant_axis/gapgen/freq.py)); a curated generator such as this one is never hard-rejected by the platform, its rare words go to the probe.  **M1 / M3**: the platform's trait-hood filter and novelty scorer.

## Counts

| step | count |
|---|---|
| census table rows (distinct stems) | 17,958 |
| TDA words parsed | 2,818 |
| Allport-Odbert words parsed (distinct) | 17,708 (lines I 4470, II 4511, III 5191, IV 3652) |
| in both lists | 2,569 |
| malformed (dropped) | 1 |
| eligible rows of this stage | 1031 (Allport-only, below_hard_reject (Zipf < 1.5 but known to wordfreq or OEWN; never unknown_word); not listed in column IV alone (QUESTIONS 34)) |
| TDA words cut by the floor | 0 (every TDA word is submitted; 251 of them are below the dictionary floor and reach the platform's probe through the curated route, so a cut here is a row another generator's floor reject reached first) |
| rows of this run turned away unread by the platform's floor | 0 |
| rows of this run cut by the definition probe ("not known") | 31 |
| Allport-only words below the floor at ingest (the table's ineligible reasons) | below_hard_reject 1,341, unknown_word 5,614 |
| census stages (pools after the column IV split) | tda 2,818, allport_hi 3,646, allport_probe 2,525, allport_iv 2,013, allport_rare 1,031, allport_iv_rare 310 |
| census rows in no stage | malformed 1, unknown_word 5,614 |
| **submitted in this run** | **1031** (641 with a gloss hint, 63 framed as a disposition from Allport-Odbert column II) |
| of those, routed to the platform's definition probe | 1031 (curated_source 390, gloss_hint 641) |
| registry: new rows / merged into existing rows / unchanged | 907 / 124 / 0 (invalid surfaces: 0) |
| duplicates merged at ingest | Allport cross-column 58, within-column 57, TDA and Allport 2,569, TDA multi-row 0, one-edit repairs 23 |
| known labels submitted (corpus traits) | 1 |

Downstream estimate when submitted (batches): M1 $3.71 + M3 $4.99 = $8.70; the generator itself spent $5.40 ([usage.json](usage.json)).

## String ceiling

Of the corpus's 932 traits (304 of them multi-word), the census lists contain as strings: TDA 417 (44.7%), Allport-Odbert 464 (49.8%), either 498 (53.4%; 74.4% of the single-word traits).  The generator's own eligibility rule submits 496 of the 498 (99.6%; the policy asks for 95%).  Of the 133 queued traits, 44 are in either list.  Source: [ingest_counts.json](../../../censuses/ingest_counts.json).

Guidelines, not gates (Roger, 2026-10-09): either list, leaving out the 89 parenthesised labels, 59.1% (aim 50%, met); single-word traits in either list 74.4% (aim 75%, below the aim).  The gate is the 95% above.

## Known labels in this run

1 submitted words are existing corpus traits (each links to its file): [neopagan](../../../../traits/instructions/neopagan.json).

## Filter (M1)

1031 of 1031 rows filtered.  Verdicts: reject 265, tagged 163, trait 603.  Tags: action 13, evaluative_only 7, membership 26, no_persona_reading 108, physical 20, role_person 20, state 123, stretched 106, too_rare 31.
Known-label pass rate (verdict trait, or tagged state or physical): 1 of 1 (100.0%).  Misses: none.

## Novelty (M3)

614 rows scored: covered 195, new 419; pair completions 70.

## Files

- [candidates.jsonl](candidates.jsonl): the submitted candidates, one per line (tracked; the main checkout resubmits it with [gap_registry.py](../../../../../data_analysis/gap_generation/gap_registry.py) `submit --from`)
- [run.json](run.json), [usage.json](usage.json), [keys.txt](keys.txt), [submit_report.json](submit_report.json), [evaluation.json](evaluation.json)
- [census_table.jsonl](../../../censuses/census_table.jsonl) (the census table), [ingest_counts.json](../../../censuses/ingest_counts.json) (ingest counts), [sources_manifest.json](../../../censuses/sources_manifest.json) (downloads: URLs, hashes, licences, attribution)
