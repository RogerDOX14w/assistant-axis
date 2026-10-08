# Census generator: run `2026-10-08-pilot` readout

Stage `tda`, every 5th row in rank order (offset 0).  Plan: [coding_plan_01_censuses.md](../../../../../reports/trait_gap_generation/coding_plan_01_censuses.md) (its last section, the revision for the interface as built, governs).  Terms: [glossary](../../../../../reports/trait_gap_generation/glossary.md).  Written by `census_generator.py report`; the numbers are in [evaluation.json](evaluation.json).

Definitions used below.  **TDA**: the Trait Descriptive Adjectives list (2,818 words with, for each, `prop`, the proportion of raters who knew the word; Dataverse, CC0).  **Allport-Odbert**: the 1936 list of about 18,000 person words in four columns (I traits, II temporary states, III social evaluations, IV metaphorical or doubtful; OSF transcription, CC BY 4.0).  **Zipf**: log10 of a word's frequency per billion words (`wordfreq`).  **The floor**: the platform's hard-reject line below Zipf 1.5 for a dictionary word, with a definition probe from 1.5 to 2.5 (`gapgen.freq`); a curated generator such as this one is never hard-rejected by the platform, its rare words go to the probe.  **M1 / M3**: the platform's trait-hood filter and novelty scorer.

## Counts

| step | count |
|---|---|
| census table rows (distinct stems) | 17,958 |
| TDA words parsed | 2,818 |
| Allport-Odbert words parsed (distinct) | 17,708 (lines I 4470, II 4511, III 5191, IV 3652) |
| in both lists | 2,569 |
| malformed (dropped) | 1 |
| eligible rows of this stage | 2818 |
| TDA words cut by the floor | 0 (every TDA word is submitted; 251 of them are below the dictionary floor and reach the platform's probe through the curated route) |
| Allport-only words cut by the floor (not in any stage) | below_hard_reject 1,341, unknown_word 5,614 |
| Allport-only words in later stages | allport_hi 4,746, allport_probe 3,438 |
| **submitted in this run** | **564** (475 with a gloss hint, 40 framed as a disposition from Allport-Odbert column II) |
| of those, routed to the platform's definition probe | 197 (band 97, curated_source 36, gloss_hint 13, negating_prefix 51) |
| registry: new rows / merged into existing rows / unchanged | 564 / 0 / 0 (invalid surfaces: 0) |
| duplicates merged at ingest | Allport cross-column 58, within-column 57, TDA and Allport 2,569, TDA multi-row 0, one-edit repairs 23 |
| known labels submitted (corpus traits) | 77 |

Downstream estimate when submitted (live): M1 $2.26 + M3 $9.14 = $11.39; the generator itself spent $0.00 ([usage.json](usage.json)).

## String ceiling

Of the corpus's 790 traits (244 of them multi-word), the census lists contain as strings: TDA 394 (49.9%), Allport-Odbert 411 (52.0%), either 444 (56.2%; 77.5% of the single-word traits).  The generator's own eligibility rule submits 444 of the 444 (100.0%; the policy asks for 95%).  Of the 238 queued traits, 65 are in either list.  Source: [ingest_counts.json](../../../censuses/ingest_counts.json).

## Known labels in this run

77 submitted words are existing corpus traits (each links to its file): [accountable](../../../../traits/instructions/accountable.json), [aggressive](../../../../traits/instructions/aggressive.json), [ambitious](../../../../traits/instructions/ambitious.json), [benign](../../../../traits/instructions/benign.json), [bitter](../../../../traits/instructions/bitter.json), [bold](../../../../traits/instructions/bold.json), [candid](../../../../traits/instructions/candid.json), [coherent](../../../../traits/instructions/coherent.json), [condescending](../../../../traits/instructions/condescending.json), [contented](../../../../traits/instructions/contented.json), [critical](../../../../traits/instructions/critical.json), [curious](../../../../traits/instructions/curious.json), [deliberate](../../../../traits/instructions/deliberate.json), [dependent](../../../../traits/instructions/dependent.json), [distractible](../../../../traits/instructions/distractible.json), [easygoing](../../../../traits/instructions/easygoing.json), [effusive](../../../../traits/instructions/effusive.json), [eloquent](../../../../traits/instructions/eloquent.json), [erratic](../../../../traits/instructions/erratic.json), [erudite](../../../../traits/instructions/erudite.json), [expedient](../../../../traits/instructions/expedient.json), [expressive](../../../../traits/instructions/expressive.json), [extroverted](../../../../traits/instructions/extroverted.json), [foolish](../../../../traits/instructions/foolish.json), [friendly](../../../../traits/instructions/friendly.json), [frugal](../../../../traits/instructions/frugal.json), [generous](../../../../traits/instructions/generous.json), [gentle](../../../../traits/instructions/gentle.json), [glib](../../../../traits/instructions/glib.json), [grandiose](../../../../traits/instructions/grandiose.json), [harsh](../../../../traits/instructions/harsh.json), [helpful](../../../../traits/instructions/helpful.json), [hostile](../../../../traits/instructions/hostile.json), [humble](../../../../traits/instructions/humble.json), [humorless](../../../../traits/instructions/humorless.json), [idealistic](../../../../traits/instructions/idealistic.json), [inaccurate](../../../../traits/instructions/inaccurate.json), [intense](../../../../traits/instructions/intense.json), [introspective](../../../../traits/instructions/introspective.json), [intuitive](../../../../traits/instructions/intuitive.json), [irreverent](../../../../traits/instructions/irreverent.json), [joyless](../../../../traits/instructions/joyless.json), [literate](../../../../traits/instructions/literate.json), [malicious](../../../../traits/instructions/malicious.json), [manipulative](../../../../traits/instructions/manipulative.json), [mechanistic](../../../../traits/instructions/mechanistic.json), [merciful](../../../../traits/instructions/merciful.json), [misanthropic](../../../../traits/instructions/misanthropic.json), [moderate](../../../../traits/instructions/moderate.json), [opinionated](../../../../traits/instructions/opinionated.json), [partisan](../../../../traits/instructions/partisan.json), [patriotic](../../../../traits/instructions/patriotic.json), [philanthropic](../../../../traits/instructions/philanthropic.json), [poor](../../../../traits/instructions/poor.json), [provocative](../../../../traits/instructions/provocative.json), [remorseful](../../../../traits/instructions/remorseful.json), [responsible](../../../../traits/instructions/responsible.json), [rootless](../../../../traits/instructions/rootless.json), [scheming](../../../../traits/instructions/scheming.json), [self_reliant](../../../../traits/instructions/self_reliant.json), [sentimental](../../../../traits/instructions/sentimental.json), [squeamish](../../../../traits/instructions/squeamish.json), [stoic](../../../../traits/instructions/stoic.json), [strict](../../../../traits/instructions/strict.json), [submissive](../../../../traits/instructions/submissive.json), [subversive](../../../../traits/instructions/subversive.json), [superstitious](../../../../traits/instructions/superstitious.json), [sycophantic](../../../../traits/instructions/sycophantic.json), [theoretical](../../../../traits/instructions/theoretical.json), [timid](../../../../traits/instructions/timid.json), [transparent](../../../../traits/instructions/transparent.json), [treacherous](../../../../traits/instructions/treacherous.json), [unambitious](../../../../traits/instructions/unambitious.json), [uncalculating](../../../../traits/instructions/uncalculating.json), [uncritical](../../../../traits/instructions/uncritical.json), [unfashionable](../../../../traits/instructions/unfashionable.json), [unforgiving](../../../../traits/instructions/unforgiving.json).

## Filter (M1)

Not run yet on this run's rows (Fable runs it); `report` fills this section, the known-label pass rate and the costs once it has.

## Files

- [candidates.jsonl](candidates.jsonl): the submitted candidates, one per line (tracked; the main checkout resubmits it with `gap_registry.py submit --file`)
- [run.json](run.json), [usage.json](usage.json), [keys.txt](keys.txt), [submit_report.json](submit_report.json), [evaluation.json](evaluation.json)
- [census_table.jsonl](../../../censuses/census_table.jsonl) (the census table), [ingest_counts.json](../../../censuses/ingest_counts.json) (ingest counts), [sources_manifest.json](../../../censuses/sources_manifest.json) (downloads: URLs, hashes, licences, attribution)
