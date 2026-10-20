# Corpus-frames generator: run `2026-10-18-pilot` readout

Plan: [coding_plan_05_corpus_frames.md](../../../../../reports/trait_gap_generation/coding_plan_05_corpus_frames.md).  Terms: [glossary](../../../../../reports/trait_gap_generation/glossary.md).  Selection: top 25 per frame by within-frame lift rank; ordering lift.  A **[frame](../../../../../reports/trait_gap_generation/glossary.md#lexical-frame)** is a fixed string with one slot; its **fillers** are the words found in the slot.  **M1** is the platform's trait-hood filter, **M3** its novelty check; a **kept** row is one M3 decides `new` or `grey` (it goes to review); a **[net-new](../../../../../reports/trait_gap_generation/glossary.md#net-new)** row is one the registry had not yet filtered when the run was submitted.

Table: [frames_table.jsonl](../../../corpus_frames/frames_table.jsonl) (git-ignored; its sha256 is in the run's [run.json](run.json)).

## 1. Already registered

Of the run's **868** table rows, **491** (56.6%) were already in the registry when it was submitted (491 from another generator), and M1 and M3 had decided **491** of those (100.0%); 103 are corpus traits and 52 seed-queue entries.  **383** registry rows were net-new (a relabelled noun is two rows, the noun and its adjective); the run made 876 registry rows in all.

## 2. Per frame

Over each frame's own pilot fillers.  **[Yield](../../../../../reports/trait_gap_generation/glossary.md#frame-yield)**: the M1 trait share of its filtered fillers.  **[Net filter](../../../../../reports/trait_gap_generation/glossary.md#net-filter)**: `region_tv` and `form_tv`, the total variation distance of its trait fillers' region and form distributions from the union's (0 the same, 1 disjoint).  **[Unique kept](../../../../../reports/trait_gap_generation/glossary.md#unique-contribution)**: kept rows no other frame found.  Sorted by yield within type.

| frame | type | n | filtered | yield | region_tv | form_tv | physical or state | kept | unique kept | forms | keep |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `cards.attributive` | copular | 1 | 1 | 100.0% | 0.74 | 0.25 | 0.0% | 0 | 0 | {'adjective': 1} | no: region_tv 0.74 > 0.5, no unique kept row |
| `cards.copular_list` | copular | 4 | 4 | 100.0% | 0.56 | 0.25 | 0.0% | 2 | 0 | {'adjective': 4} | no: region_tv 0.56 > 0.5, no unique kept row |
| `pippa.copular_list` | copular | 25 | 25 | 100.0% | 0.28 | 0.25 | 0.0% | 5 | 0 | {'adjective': 25} | yes: yield 1.00 >= 0.4 and region_tv 0.28 <= 0.5 |
| `c_was_an` | copular | 25 | 25 | 80.0% | 0.06 | 0.25 | 4.0% | 6 | 4 | {'adjective': 20} | yes: yield 0.80 >= 0.4 and region_tv 0.06 <= 0.5 |
| `c_seemed_a` | copular | 25 | 25 | 76.0% | 0.22 | 0.25 | 20.0% | 11 | 0 | {'adjective': 19} | yes: yield 0.76 >= 0.4 and region_tv 0.22 <= 0.5 |
| `pippa.attributive` | copular | 15 | 15 | 73.3% | 0.40 | 0.25 | 13.3% | 1 | 0 | {'adjective': 11} | yes: yield 0.73 >= 0.4 and region_tv 0.40 <= 0.5 |
| `c_is_a` | copular | 25 | 25 | 52.0% | 0.33 | 0.17 | 12.0% | 7 | 2 | {'adjective': 12, 'noun': 1} | yes: yield 0.52 >= 0.4 and region_tv 0.33 <= 0.5 |
| `c_was_a` | copular | 25 | 25 | 48.0% | 0.39 | 0.25 | 44.0% | 4 | 2 | {'adjective': 12} | yes: yield 0.48 >= 0.4 and region_tv 0.39 <= 0.5 |
| `d_notoriously` | degree | 25 | 25 | 92.0% | 0.26 | 0.25 | 4.0% | 10 | 0 | {'adjective': 23} | yes: yield 0.92 >= 0.4 and region_tv 0.26 <= 0.5 |
| `d_utterly` | degree | 25 | 25 | 92.0% | 0.31 | 0.25 | 0.0% | 15 | 1 | {'adjective': 23} | yes: yield 0.92 >= 0.4 and region_tv 0.31 <= 0.5 |
| `d_thoroughly` | degree | 25 | 25 | 88.0% | 0.30 | 0.25 | 0.0% | 7 | 1 | {'adjective': 22} | yes: yield 0.88 >= 0.4 and region_tv 0.30 <= 0.5 |
| `d_remarkably` | degree | 25 | 25 | 80.0% | 0.41 | 0.25 | 16.0% | 7 | 0 | {'adjective': 20} | yes: yield 0.80 >= 0.4 and region_tv 0.41 <= 0.5 |
| `d_quite` | degree | 25 | 25 | 76.0% | 0.30 | 0.25 | 8.0% | 12 | 1 | {'adjective': 19} | yes: yield 0.76 >= 0.4 and region_tv 0.30 <= 0.5 |
| `d_very` | degree | 25 | 25 | 76.0% | 0.22 | 0.20 | 16.0% | 4 | 2 | {'adjective': 18, 'noun': 1} | yes: yield 0.76 >= 0.4 and region_tv 0.22 <= 0.5 |
| `d_extremely` | degree | 25 | 25 | 72.0% | 0.14 | 0.25 | 16.0% | 6 | 0 | {'adjective': 18} | yes: yield 0.72 >= 0.4 and region_tv 0.14 <= 0.5 |
| `d_too` | degree | 25 | 25 | 72.0% | 0.20 | 0.25 | 8.0% | 6 | 0 | {'adjective': 18} | yes: yield 0.72 >= 0.4 and region_tv 0.20 <= 0.5 |
| `d_too_to` | degree | 25 | 25 | 68.0% | 0.34 | 0.25 | 20.0% | 10 | 8 | {'adjective': 17} | yes: yield 0.68 >= 0.4 and region_tv 0.34 <= 0.5 |
| `d_hopelessly` | degree | 16 | 16 | 62.5% | 0.44 | 0.25 | 31.2% | 4 | 0 | {'adjective': 10} | yes: yield 0.62 >= 0.4 and region_tv 0.44 <= 0.5 |
| `d_incurably` | degree | 12 | 12 | 58.3% | 0.28 | 0.25 | 41.7% | 1 | 0 | {'adjective': 7} | yes: yield 0.58 >= 0.4 and region_tv 0.28 <= 0.5 |
| `d_rather` | degree | 25 | 25 | 56.0% | 0.31 | 0.25 | 40.0% | 8 | 2 | {'adjective': 14} | yes: yield 0.56 >= 0.4 and region_tv 0.31 <= 0.5 |
| `d_famously` | degree | 4 | 4 | 50.0% | 0.61 | 0.25 | 50.0% | 2 | 0 | {'adjective': 2} | no: region_tv 0.61 > 0.5, no unique kept row |
| `d_chronically` | degree | 25 | 25 | 36.0% | 0.53 | 0.25 | 64.0% | 6 | 2 | {'adjective': 9} | yes: 2 unique kept rows (yield 0.36, region_tv 0.53) |
| `d_so` | degree | 25 | 25 | 12.0% | 0.47 | 0.08 | 0.0% | 0 | 0 | {'adjective': 2, 'noun': 1} | no: yield 0.12 < 0.4, no unique kept row |
| `pippa.always` | habitual | 1 | 1 | 100.0% | 0.87 | 0.25 | 0.0% | 1 | 0 | {'adjective': 1} | no: region_tv 0.87 > 0.5, no unique kept row |
| `h_he_was_always` | habitual | 25 | 25 | 76.0% | 0.27 | 0.15 | 20.0% | 12 | 4 | {'adjective': 17, 'noun': 2} | yes: yield 0.76 >= 0.4 and region_tv 0.27 <= 0.5 |
| `h_he_is_always` | habitual | 25 | 25 | 64.0% | 0.21 | 0.13 | 28.0% | 8 | 4 | {'adjective': 14, 'noun': 2} | yes: yield 0.64 >= 0.4 and region_tv 0.21 <= 0.5 |
| `h_she_is_always` | habitual | 25 | 25 | 52.0% | 0.33 | 0.10 | 32.0% | 7 | 0 | {'adjective': 11, 'noun': 2} | yes: yield 0.52 >= 0.4 and region_tv 0.33 <= 0.5 |
| `h_she_was_always` | habitual | 25 | 25 | 48.0% | 0.28 | 0.17 | 40.0% | 8 | 2 | {'adjective': 11, 'noun': 1} | yes: yield 0.48 >= 0.4 and region_tv 0.28 <= 0.5 |
| `pippa.trait_list` | list | 19 | 19 | 94.7% | 0.20 | 0.25 | 0.0% | 3 | 0 | {'adjective': 18} | yes: yield 0.95 >= 0.4 and region_tv 0.20 <= 0.5 |
| `n_incorrigible` | nominal | 25 | 25 | 100.0% | 0.25 | 0.47 | 0.0% | 12 | 0 | {'adjective': 7, 'noun': 18} | yes: yield 1.00 >= 0.4 and region_tv 0.25 <= 0.5 |
| `n_confirmed` | nominal | 25 | 25 | 92.0% | 0.43 | 0.49 | 8.0% | 15 | 4 | {'adjective': 6, 'noun': 17} | yes: yield 0.92 >= 0.4 and region_tv 0.43 <= 0.5 |
| `n_habitual` | nominal | 25 | 25 | 92.0% | 0.31 | 0.71 | 4.0% | 14 | 1 | {'adjective': 1, 'noun': 22} | yes: yield 0.92 >= 0.4 and region_tv 0.31 <= 0.5 |
| `n_inveterate` | nominal | 25 | 25 | 92.0% | 0.22 | 0.75 | 0.0% | 18 | 5 | {'noun': 23} | yes: yield 0.92 >= 0.4 and region_tv 0.22 <= 0.5 |
| `n_shameless` | nominal | 25 | 25 | 92.0% | 0.40 | 0.53 | 0.0% | 14 | 1 | {'adjective': 5, 'noun': 18} | yes: yield 0.92 >= 0.4 and region_tv 0.40 <= 0.5 |
| `n_born` | nominal | 25 | 25 | 84.0% | 0.26 | 0.70 | 4.0% | 16 | 6 | {'adjective': 1, 'noun': 20} | yes: yield 0.84 >= 0.4 and region_tv 0.26 <= 0.5 |
| `n_hopeless` | nominal | 25 | 25 | 84.0% | 0.26 | 0.42 | 16.0% | 12 | 2 | {'adjective': 7, 'noun': 14} | yes: yield 0.84 >= 0.4 and region_tv 0.26 <= 0.5 |
| `n_notorious` | nominal | 25 | 25 | 84.0% | 0.48 | 0.70 | 0.0% | 16 | 9 | {'adjective': 1, 'noun': 20} | yes: yield 0.84 >= 0.4 and region_tv 0.48 <= 0.5 |
| `n_chronic` | nominal | 25 | 25 | 80.0% | 0.41 | 0.45 | 20.0% | 18 | 2 | {'adjective': 6, 'noun': 14} | yes: yield 0.80 >= 0.4 and region_tv 0.41 <= 0.5 |
| `n_compulsive` | nominal | 25 | 25 | 80.0% | 0.23 | 0.70 | 0.0% | 11 | 0 | {'adjective': 1, 'noun': 19} | yes: yield 0.80 >= 0.4 and region_tv 0.23 <= 0.5 |
| `n_natural` | nominal | 25 | 25 | 64.0% | 0.24 | 0.13 | 12.0% | 9 | 1 | {'adjective': 14, 'noun': 2} | yes: yield 0.64 >= 0.4 and region_tv 0.24 <= 0.5 |
| `n_total` | nominal | 25 | 25 | 60.0% | 0.54 | 0.35 | 16.0% | 7 | 2 | {'adjective': 6, 'noun': 9} | yes: 2 unique kept rows (yield 0.60, region_tv 0.54) |
| `cards.known_for` | possessive | 4 | 4 | 100.0% | 0.68 | 0.00 | 0.0% | 1 | 0 | {'adjective': 3, 'noun': 1} | no: region_tv 0.68 > 0.5, no unique kept row |
| `cards.poss_nature` | possessive | 8 | 8 | 100.0% | 0.53 | 0.25 | 0.0% | 1 | 0 | {'adjective': 8} | no: region_tv 0.53 > 0.5, no unique kept row |
| `p_noted_for_his` | possessive | 25 | 25 | 88.0% | 0.26 | 0.21 | 4.0% | 10 | 0 | {'adjective': 21, 'noun': 1} | yes: yield 0.88 >= 0.4 and region_tv 0.26 <= 0.5 |
| `p_reputation_for` | possessive | 25 | 25 | 88.0% | 0.27 | 0.11 | 4.0% | 9 | 2 | {'adjective': 19, 'noun': 3} | yes: yield 0.88 >= 0.4 and region_tv 0.27 <= 0.5 |
| `p_known_for_her` | possessive | 25 | 25 | 76.0% | 0.28 | 0.07 | 0.0% | 7 | 0 | {'adjective': 13, 'noun': 6} | yes: yield 0.76 >= 0.4 and region_tv 0.28 <= 0.5 |
| `p_known_for_his` | possessive | 25 | 25 | 76.0% | 0.32 | 0.09 | 0.0% | 8 | 0 | {'adjective': 16, 'noun': 3} | yes: yield 0.76 >= 0.4 and region_tv 0.32 <= 0.5 |
| `p_man_of` | possessive | 25 | 25 | 76.0% | 0.25 | 0.07 | 8.0% | 13 | 6 | {'adjective': 13, 'noun': 6} | yes: yield 0.76 >= 0.4 and region_tv 0.25 <= 0.5 |
| `p_famous_for_his` | possessive | 25 | 25 | 72.0% | 0.32 | 0.03 | 0.0% | 9 | 1 | {'adjective': 13, 'noun': 5} | yes: yield 0.72 >= 0.4 and region_tv 0.32 <= 0.5 |
| `p_woman_of` | possessive | 25 | 25 | 68.0% | 0.33 | 0.10 | 8.0% | 11 | 4 | {'adjective': 11, 'noun': 6} | yes: yield 0.68 >= 0.4 and region_tv 0.33 <= 0.5 |
| `t_inclined` | tendency | 25 | 25 | 88.0% | 0.35 | 0.25 | 12.0% | 13 | 2 | {'adjective': 22} | yes: yield 0.88 >= 0.4 and region_tv 0.35 <= 0.5 |
| `t_tendency` | tendency | 25 | 25 | 72.0% | 0.32 | 0.25 | 4.0% | 9 | 2 | {'adjective': 18} | yes: yield 0.72 >= 0.4 and region_tv 0.32 <= 0.5 |
| `t_apt` | tendency | 25 | 25 | 68.0% | 0.33 | 0.25 | 20.0% | 9 | 2 | {'adjective': 17} | yes: yield 0.68 >= 0.4 and region_tv 0.33 <= 0.5 |

The union: 868 rows, yield 73.0%, regions {'alignment_ai_agent': 5, 'cognitive_epistemic': 88, 'communication_style': 100, 'emotional_temperament': 116, 'identity_demographic': 85, 'moral_stance': 78, 'social_interpersonal': 162}.

Region histograms (trait fillers):

- `cards.attributive`: {'social_interpersonal': 1}
- `cards.copular_list`: {'emotional_temperament': 2, 'identity_demographic': 1, 'moral_stance': 1}
- `pippa.copular_list`: {'alignment_ai_agent': 1, 'cognitive_epistemic': 2, 'communication_style': 5, 'emotional_temperament': 6, 'identity_demographic': 1, 'social_interpersonal': 10}
- `c_was_an`: {'cognitive_epistemic': 2, 'communication_style': 3, 'emotional_temperament': 4, 'identity_demographic': 3, 'moral_stance': 3, 'social_interpersonal': 5}
- `c_seemed_a`: {'cognitive_epistemic': 4, 'communication_style': 4, 'emotional_temperament': 1, 'identity_demographic': 1, 'moral_stance': 3, 'social_interpersonal': 6}
- `pippa.attributive`: {'communication_style': 3, 'emotional_temperament': 5, 'social_interpersonal': 3}
- `c_is_a`: {'cognitive_epistemic': 1, 'communication_style': 1, 'emotional_temperament': 2, 'identity_demographic': 6, 'social_interpersonal': 3}
- `c_was_a`: {'cognitive_epistemic': 3, 'communication_style': 1, 'identity_demographic': 5, 'moral_stance': 1, 'social_interpersonal': 2}
- `d_notoriously`: {'cognitive_epistemic': 1, 'communication_style': 2, 'emotional_temperament': 5, 'identity_demographic': 1, 'moral_stance': 5, 'social_interpersonal': 9}
- `d_utterly`: {'cognitive_epistemic': 2, 'communication_style': 2, 'emotional_temperament': 3, 'identity_demographic': 5, 'moral_stance': 8, 'social_interpersonal': 3}
- `d_thoroughly`: {'cognitive_epistemic': 3, 'communication_style': 1, 'emotional_temperament': 1, 'identity_demographic': 2, 'moral_stance': 7, 'social_interpersonal': 8}
- `d_remarkably`: {'cognitive_epistemic': 11, 'communication_style': 1, 'emotional_temperament': 3, 'moral_stance': 2, 'social_interpersonal': 3}
- `d_quite`: {'alignment_ai_agent': 1, 'cognitive_epistemic': 3, 'communication_style': 7, 'emotional_temperament': 1, 'identity_demographic': 3, 'moral_stance': 1, 'social_interpersonal': 3}
- `d_very`: {'cognitive_epistemic': 2, 'communication_style': 3, 'emotional_temperament': 2, 'identity_demographic': 1, 'moral_stance': 2, 'social_interpersonal': 9}
- `d_extremely`: {'cognitive_epistemic': 4, 'communication_style': 2, 'emotional_temperament': 3, 'identity_demographic': 3, 'moral_stance': 1, 'social_interpersonal': 5}
- `d_too`: {'cognitive_epistemic': 3, 'communication_style': 2, 'emotional_temperament': 5, 'identity_demographic': 1, 'moral_stance': 1, 'social_interpersonal': 6}
- `d_too_to`: {'cognitive_epistemic': 5, 'communication_style': 5, 'emotional_temperament': 4, 'identity_demographic': 1, 'moral_stance': 2}
- `d_hopelessly`: {'cognitive_epistemic': 4, 'emotional_temperament': 2, 'identity_demographic': 3, 'social_interpersonal': 1}
- `d_incurably`: {'cognitive_epistemic': 2, 'communication_style': 2, 'emotional_temperament': 1, 'identity_demographic': 1, 'social_interpersonal': 1}
- `d_rather`: {'communication_style': 6, 'emotional_temperament': 3, 'identity_demographic': 2, 'social_interpersonal': 3}
- `d_famously`: {'identity_demographic': 1, 'social_interpersonal': 1}
- `d_chronically`: {'cognitive_epistemic': 1, 'emotional_temperament': 1, 'identity_demographic': 6, 'social_interpersonal': 1}
- `d_so`: {'cognitive_epistemic': 1, 'identity_demographic': 1, 'social_interpersonal': 1}
- `pippa.always`: {'identity_demographic': 1}
- `h_he_was_always`: {'cognitive_epistemic': 3, 'communication_style': 5, 'emotional_temperament': 6, 'social_interpersonal': 5}
- `h_he_is_always`: {'alignment_ai_agent': 2, 'cognitive_epistemic': 2, 'communication_style': 4, 'emotional_temperament': 3, 'identity_demographic': 1, 'moral_stance': 1, 'social_interpersonal': 3}
- `h_she_is_always`: {'communication_style': 3, 'emotional_temperament': 4, 'identity_demographic': 1, 'social_interpersonal': 5}
- `h_she_was_always`: {'communication_style': 3, 'emotional_temperament': 3, 'moral_stance': 2, 'social_interpersonal': 4}
- `pippa.trait_list`: {'cognitive_epistemic': 1, 'communication_style': 3, 'emotional_temperament': 3, 'identity_demographic': 1, 'moral_stance': 2, 'social_interpersonal': 8}
- `n_incorrigible`: {'cognitive_epistemic': 1, 'communication_style': 1, 'emotional_temperament': 4, 'identity_demographic': 4, 'moral_stance': 5, 'social_interpersonal': 10}
- `n_confirmed`: {'emotional_temperament': 9, 'identity_demographic': 8, 'moral_stance': 3, 'social_interpersonal': 3}
- `n_habitual`: {'cognitive_epistemic': 1, 'communication_style': 1, 'emotional_temperament': 4, 'identity_demographic': 9, 'moral_stance': 4, 'social_interpersonal': 4}
- `n_inveterate`: {'cognitive_epistemic': 1, 'communication_style': 3, 'emotional_temperament': 4, 'identity_demographic': 8, 'moral_stance': 1, 'social_interpersonal': 6}
- `n_shameless`: {'cognitive_epistemic': 1, 'communication_style': 1, 'emotional_temperament': 1, 'identity_demographic': 2, 'moral_stance': 7, 'social_interpersonal': 11}
- `n_born`: {'cognitive_epistemic': 3, 'communication_style': 6, 'emotional_temperament': 2, 'identity_demographic': 1, 'moral_stance': 1, 'social_interpersonal': 8}
- `n_hopeless`: {'cognitive_epistemic': 4, 'communication_style': 3, 'emotional_temperament': 7, 'identity_demographic': 4, 'social_interpersonal': 3}
- `n_notorious`: {'communication_style': 1, 'identity_demographic': 2, 'moral_stance': 7, 'social_interpersonal': 11}
- `n_chronic`: {'cognitive_epistemic': 1, 'communication_style': 1, 'emotional_temperament': 11, 'identity_demographic': 3, 'moral_stance': 3, 'social_interpersonal': 1}
- `n_compulsive`: {'communication_style': 5, 'emotional_temperament': 6, 'identity_demographic': 3, 'moral_stance': 1, 'social_interpersonal': 5}
- `n_natural`: {'cognitive_epistemic': 3, 'communication_style': 2, 'emotional_temperament': 4, 'identity_demographic': 1, 'social_interpersonal': 6}
- `n_total`: {'cognitive_epistemic': 5, 'emotional_temperament': 1, 'identity_demographic': 7, 'moral_stance': 2}
- `cards.known_for`: {'cognitive_epistemic': 2, 'emotional_temperament': 2}
- `cards.poss_nature`: {'communication_style': 3, 'emotional_temperament': 4, 'social_interpersonal': 1}
- `p_noted_for_his`: {'cognitive_epistemic': 6, 'communication_style': 4, 'emotional_temperament': 2, 'moral_stance': 5, 'social_interpersonal': 5}
- `p_reputation_for`: {'cognitive_epistemic': 2, 'communication_style': 7, 'emotional_temperament': 5, 'moral_stance': 1, 'social_interpersonal': 7}
- `p_known_for_her`: {'cognitive_epistemic': 3, 'communication_style': 8, 'emotional_temperament': 1, 'identity_demographic': 1, 'moral_stance': 2, 'social_interpersonal': 4}
- `p_known_for_his`: {'cognitive_epistemic': 4, 'communication_style': 5, 'emotional_temperament': 2, 'moral_stance': 5, 'social_interpersonal': 3}
- `p_man_of`: {'cognitive_epistemic': 2, 'communication_style': 2, 'emotional_temperament': 3, 'identity_demographic': 1, 'moral_stance': 7, 'social_interpersonal': 4}
- `p_famous_for_his`: {'cognitive_epistemic': 3, 'communication_style': 7, 'moral_stance': 3, 'social_interpersonal': 5}
- `p_woman_of`: {'cognitive_epistemic': 1, 'communication_style': 2, 'emotional_temperament': 3, 'identity_demographic': 4, 'moral_stance': 6, 'social_interpersonal': 1}
- `t_inclined`: {'alignment_ai_agent': 1, 'cognitive_epistemic': 1, 'communication_style': 4, 'emotional_temperament': 6, 'social_interpersonal': 10}
- `t_tendency`: {'alignment_ai_agent': 1, 'cognitive_epistemic': 5, 'communication_style': 2, 'emotional_temperament': 3, 'social_interpersonal': 7}
- `t_apt`: {'cognitive_epistemic': 5, 'communication_style': 3, 'emotional_temperament': 1, 'moral_stance': 1, 'social_interpersonal': 7}

## 3. Per type

| type | n | yield | region_tv | form_tv | kept | labels only this type found |
|---|---|---|---|---|---|---|
| copular | 133 | 70.7% | 0.06 | 0.24 | 34 | adulterine, forehanded, juristic, nonmatched, nonnatural, nonparty, selfemployed, supposititious, unhospitable, unlicked, uxorious, wailful |
| degree | 287 | 69.0% | 0.06 | 0.24 | 93 | assaultive, cagy, concessive, dandified, dislikable, enigmatical, flagitious, hortatory, indiscriminating, insupportable, muddleheaded, stodgier, unamiable, unboyish, underemployed, unenterprising, unhandy, uninfluential, unmalleable, unmusical, unobjectionable, unredeemable, unselective |
| habitual | 76 | 60.5% | 0.22 | 0.16 | 29 | behindhand, digressing, fonder, harping, heedful, hinting, hospitably, jabbering, punctiliously, readiest, reproaching, shamming, stealthily |
| list | 19 | 94.7% | 0.20 | 0.25 | 3 | none |
| nominal | 217 | 81.1% | 0.10 | 0.48 | 109 | adulteress, anglophobe, appetent, attender, balletomane, bargainer, bellyacher, bluffer, blunderer, boaster, bumbler, cadger, casuist, chatterer, chewer, complainer, compromiser, controversialist, defaulter, demimondaine, dialectician, diarist, dipsomaniac, duellist, eavesdropper, elocutionist, exploiter, faultfinder, frequenter, gadgeteer, giggler, grumbler, habitue, housebreaker, hussy, hypochondriac, ignoramus, intriguer, klutz, knitter, landlubber, latecomer, lawbreaker, libeler, lyrist, malcontent, malefactor, malingerer, masturbator, mountebank, nepotist, nonentity, nonstarter, onanist, overachiever, philanderer, plagiarist, playgoer, polemist, poseur, potterer, prevaricator, prig, quoter, raconteur, rakehell, recidivist, romanticist, scandalmonger, schmoozer, sensualist, sightseer, slanderer, sleuthhound, snorer, sophistic, stutterer, suppliant, swearer, theatergoer, theatregoer, theorizer, tinkerer, underachiever, underperformer, usurer, valetudinarian, violator, washout, wheedler, whoremaster, womaniser |
| possessive | 148 | 80.4% | 0.15 | 0.05 | 55 | childbearing, epigrams, irreproachable, malapropisms, nonroyal, piety, probity, rakish, refinement, retaliative, saintlike, scurrility, seamy, twentyone, unattachment, unbounding, uncordial, unfaded, unimpeachable, unimpeached, unpunctuality, unwearying |
| tendency | 66 | 74.2% | 0.27 | 0.25 | 26 | disagreeably, hypochondriacal, overcritical, overemotional, overgenerous, pettish, precipitant |

## 4. M1 and M3

M1 filtered 876 of the run's 876 registry rows: verdicts {'reject': 103, 'tagged': 135, 'trait': 638}; trait share 72.8%.  **M1 trait share of the net-new rows: 58.2%** (223 of 383; the estimate assumed 88%).

M3 scored 655: {'covered': 326, 'new': 329}.  **Net-new kept share 38.4%** (147 kept of 383 net-new rows; the wave's cut assumed 0.3 until now).

Novel after M3 (`new` or `grey`): **329 raw**, **144 net** of other generators' candidates of the same stem (169 pending review, 16 already reviewed); over the net-new rows 147 raw, 144 net.

Nominal rows M1 held on the roles list (open decision 3): 23: `annotator`, `autobiographer`, `bonesetter`, `contrapuntist`, `dacoit`, `diplomatist`, `fourscore`, `freebooter`, `harlot`, `nonprincipal`, `predoctoral`, `procuress`, `reviser`, `rewriter`, `rumrunner`, `sceptered`, `sketcher`, `strumpet`, `symphonist`, `threescore`, `unemancipated`, `versifier`, `young`.  Relabelled nouns submitted: 8, by rule {'derivation': 1, 'suffix:noun_suffix': 7}; registry rows linked by a relabel block: 47; nouns the helper left as nouns: 210.

M1's parse rate: {'parse_rate': 1.0, 'parse_rate_first_pass': 0.0}.

## 5. Cost and the re-based projections

Total $4.3860 from [usage.json](usage.json), [usage.json](../../../filter/2026-10-18-pilot_corpus_frames/usage.json), [usage.json](../../../novelty/2026-10-18-pilot_corpus_frames/usage.json); per model {'claude-haiku-5-5': {'cost_usd': 0.9865, 'prompt_tokens': 1556813, 'completion_tokens': 1661588, 'n_calls': 5400}, 'claude-opus-5-5': {'cost_usd': 0.9859, 'prompt_tokens': 56579, 'completion_tokens': 37980, 'n_calls': 258}, 'claude-sonnet-5-5': {'cost_usd': 2.4131, 'prompt_tokens': 720723, 'completion_tokens': 97164, 'n_calls': 1211}, 'text-embedding-3-large': {'cost_usd': 0.0005, 'prompt_tokens': 3884, 'completion_tokens': 0, 'n_calls': 2}}.  Kept rows per dollar: 75.00.  The generator itself is $0 (its run's usage record has no calls).

At the measured net-new kept share 0.3838 over the 46 frames kept, at 145.8 terms an hour (measured, plan 13's pooled_review_rate over 1 review batches):

- **A 300-kept wave**: 3355 rows to submit, 782 net-new, about 300 kept, about 2.06 h of review; about $13.20 live or $6.60 batched.
- **The whole table over the kept frames**: 16598 rows, 10468 net-new, about 4018 kept, about 27.56 h of review; about $176.70 live or $88.35 batched.

## The contributing frames of every kept row

329 kept rows; each with every frame that found it, best within-frame rank first.

| row | M3 | frames | nearest corpus trait (cosine) |
|---|---|---|---|
| absentminded | new | `t_tendency`, `t_inclined`, `p_famous_for_his`, `d_very`, `p_reputation_for`, `t_apt`, `p_known_for_his`, `d_too_to` | [distractible](../../../../traits/instructions/distractible.json) (0.42) |
| acknowledged | new | `d_notoriously`, `c_was_an`, `p_man_of`, `p_woman_of`, `h_he_was_always`, `t_apt` | [face culture](../../../../traits/instructions/face_culture.json) (0.39) |
| adulteress | new | `n_shameless`, `n_notorious` | [polyandrous](../../../../traits/instructions/polyandrous.json) (0.31) |
| adulterine | new | `c_was_an` | [promiscuous](../../../../traits/instructions/promiscuous.json) (0.36) |
| anachronistic | new | `n_hopeless`, `n_total`, `n_natural`, `d_too_to` | [staid](../../../../traits/instructions/staid.json) (0.34) |
| anglophobe | new | `n_notorious` | [british](../../../../traits/instructions/british.json) (0.30) |
| antislavery | new | `c_was_an`, `p_known_for_her`, `p_known_for_his`, `p_famous_for_his`, `p_reputation_for`, `p_man_of` | [unyielding](../../../../traits/instructions/unyielding.json) (0.38) |
| appetency | new | `n_natural` | [lustful](../../../../traits/instructions/lustful.json) (0.33) |
| appetent | new | `n_natural` | [zealous](../../../../traits/instructions/zealous.json) (0.34) |
| apt | new | `d_too_to`, `h_he_is_always`, `c_was_an`, `n_natural`, `h_he_was_always`, `h_she_was_always`, `p_noted_for_his`, `p_known_for_his` | [competent](../../../../traits/instructions/competent.json) (0.46) |
| aquiline | new | `t_inclined`, `t_tendency`, `p_man_of`, `d_too_to` | [good looking](../../../../traits/instructions/good_looking.json) (0.32) |
| assaultive | new | `d_chronically` | [violent](../../../../traits/instructions/violent.json) (0.53) |
| astute | new | `d_remarkably`, `c_was_an`, `d_very`, `d_extremely`, `p_noted_for_his`, `p_reputation_for`, `d_too_to`, `p_known_for_his`, `p_known_for_her`, `p_famous_for_his`, `d_rather`, `p_woman_of`, `p_man_of`, `n_natural` | [socially perceptive](../../../../traits/instructions/socially_perceptive.json) (0.36) |
| attender | new | `n_inveterate`, `n_habitual` | [frequent poster](../../../../traits/instructions/frequent_poster.json) (0.32) |
| autobiographical | new | `p_known_for_her`, `p_known_for_his`, `c_was_an`, `p_famous_for_his`, `t_tendency`, `d_too_to` | [experiential](../../../../traits/instructions/experiential.json) (0.37) |
| balletomane | new | `n_confirmed` | [political](../../../../traits/instructions/political.json) (0.26) |
| barbarous | new | `d_utterly`, `d_too`, `d_very`, `d_too_to`, `c_is_a`, `c_was_a`, `p_reputation_for`, `p_man_of` | [malicious](../../../../traits/instructions/malicious.json) (0.39) |
| bargainer | new | `n_born`, `n_natural` | [bargain hunter](../../../../traits/instructions/bargain_hunter.json) (0.34) |
| behindhand | new | `h_he_is_always` | [sloppy](../../../../traits/instructions/sloppy.json) (0.34) |
| bellyacher | new | `n_chronic` | [petty](../../../../traits/instructions/petty.json) (0.41) |
| bestial | new | `d_thoroughly`, `p_man_of`, `p_reputation_for`, `d_too_to` | savage (0.43) |
| biddable | new | `d_quite`, `c_was_a`, `d_very` | [obedient](../../../../traits/instructions/obedient.json) (0.43) |
| bluffer | new | `n_habitual` | [overconfident](../../../../traits/instructions/overconfident.json) (0.40) |
| blunderer | new | `n_incorrigible`, `n_hopeless`, `n_born`, `n_notorious` | [incompetent](../../../../traits/instructions/incompetent.json) (0.42) |
| boaster | new | `n_incorrigible`, `n_shameless`, `n_inveterate`, `n_notorious` | [self aggrandizing](../../../../traits/instructions/self_aggrandizing.json) (0.51) |
| bumbler | new | `n_hopeless` | [incompetent](../../../../traits/instructions/incompetent.json) (0.46) |
| cadger | new | `n_shameless`, `n_inveterate` | parasitic (0.36) |
| cagy | new | `d_too_to` | concealing (0.51) |
| cantankerous | new | `d_extremely`, `t_inclined`, `d_rather`, `c_was_a`, `d_very`, `c_is_a`, `p_known_for_his`, `d_too_to`, `p_reputation_for` | [quarrelsome hexaco](../../../../traits/instructions/quarrelsome_hexaco.json) (0.44) |
| captious | new | `t_inclined`, `t_apt`, `d_too_to` | [petty](../../../../traits/instructions/petty.json) (0.38) |
| casuist | new | `n_born` | [logical](../../../../traits/instructions/logical.json) (0.36) |
| ceremonious | new | `d_extremely`, `d_very`, `h_he_was_always`, `d_too_to` | [dignified](../../../../traits/instructions/dignified.json) (0.49) |
| changed | new | `c_seemed_a`, `d_utterly`, `c_was_a`, `c_is_a`, `d_thoroughly`, `d_remarkably`, `t_apt`, `d_so`, `t_tendency`, `d_very`, `d_too_to`, `p_man_of` | rugged (0.34) |
| charming | new | `d_utterly`, `pippa.trait_list`, `c_seemed_a`, `c_is_a`, `d_thoroughly`, `d_very`, `d_quite`, `c_was_a`, `d_extremely`, `d_rather`, `p_known_for_her`, `h_she_was_always`, `h_she_is_always`, `h_he_was_always`, `h_he_is_always`, `p_woman_of`, `p_noted_for_his`, `p_known_for_his`, `p_man_of`, `d_so`, `d_too_to`, `p_reputation_for`, `p_famous_for_his`, `t_apt` | [friendly](../../../../traits/instructions/friendly.json) (0.36) |
| chary | new | `t_inclined`, `h_she_was_always`, `h_he_was_always`, `t_apt`, `p_man_of`, `d_too_to` | [cautious](../../../../traits/instructions/cautious.json) (0.29) |
| chatterer | new | `n_compulsive`, `n_inveterate`, `n_born`, `n_natural` | [glib](../../../../traits/instructions/glib.json) (0.26) |
| chewer | new | `n_inveterate`, `n_habitual` | [smoker](../../../../traits/instructions/smoker.json) (0.36) |
| childbearing | new | `p_woman_of` | [female](../../../../traits/instructions/female.json) (0.54) |
| clubbable | new | `d_very`, `c_was_a` | [friendly](../../../../traits/instructions/friendly.json) (0.41) |
| clumsy | new | `pippa.trait_list`, `c_seemed_a`, `d_rather`, `t_inclined`, `d_too_to`, `t_tendency`, `t_apt`, `c_was_a`, `d_very`, `h_she_was_always`, `c_is_a`, `h_he_was_always`, `p_reputation_for`, `n_natural`, `p_known_for_his`, `p_man_of` | [mobility impaired](../../../../traits/instructions/mobility_impaired.json) (0.38) |
| cold | new | `pippa.copular_list`, `h_she_was_always`, `d_too_to`, `d_rather`, `h_she_is_always`, `c_seemed_a`, `t_inclined`, `h_he_was_always`, `t_apt`, `p_reputation_for`, `t_tendency`, `d_so`, `c_was_a`, `h_he_is_always`, `d_extremely`, `d_very`, `c_is_a`, `p_man_of`, `p_woman_of`, `n_natural`, `p_known_for_his`, `p_famous_for_his`, `p_noted_for_his`, `p_known_for_her`, `n_total` | [detached](../../../../traits/instructions/detached.json) (0.49) |
| commonplace | new | `d_utterly`, `d_quite`, `d_rather`, `d_thoroughly`, `d_extremely`, `d_very`, `d_too_to`, `c_is_a`, `c_was_a`, `p_man_of`, `p_woman_of`, `t_apt` | [modest](../../../../traits/instructions/modest.json) (0.34) |
| communicative | new | `t_inclined`, `d_extremely`, `d_very`, `c_was_a`, `d_too_to`, `n_natural`, `t_apt` | [transparent](../../../../traits/instructions/transparent.json) (0.42) |
| complainer | new | `n_chronic`, `n_habitual`, `n_inveterate`, `n_compulsive`, `n_born`, `n_notorious` | [quarrelsome hexaco](../../../../traits/instructions/quarrelsome_hexaco.json) (0.43) |
| complaining | new | `h_she_is_always`, `h_she_was_always`, `h_he_was_always`, `h_he_is_always`, `p_reputation_for`, `t_apt`, `c_was_a` | [quarrelsome hexaco](../../../../traits/instructions/quarrelsome_hexaco.json) (0.42) |
| compromiser | new | `n_inveterate`, `n_born`, `n_natural` | [accommodating](../../../../traits/instructions/accommodating.json) (0.44) |
| concessive | new | `d_too_to` | [accommodating](../../../../traits/instructions/accommodating.json) (0.38) |
| confiding | new | `d_too`, `t_inclined`, `d_very`, `c_was_a`, `d_too_to` | [trusting](../../../../traits/instructions/trusting.json) (0.41) |
| considerate | new | `h_he_was_always`, `h_he_is_always`, `d_very`, `h_she_was_always`, `t_inclined`, `c_was_a`, `d_extremely`, `d_too_to`, `c_is_a`, `t_tendency`, `p_man_of`, `p_reputation_for` | [other focused](../../../../traits/instructions/other_focused.json) (0.38) |
| contriving | new | `h_she_is_always`, `h_he_is_always`, `h_he_was_always`, `d_very` | [scheming](../../../../traits/instructions/scheming.json) (0.45) |
| controversialist | new | `n_inveterate`, `n_born`, `n_notorious`, `n_natural` | [partisan](../../../../traits/instructions/partisan.json) (0.47) |
| cumbrous | new | `d_too_to`, `t_apt` | [verbose](../../../../traits/instructions/verbose.json) (0.51) |
| cunningly | new | `h_he_is_always`, `d_too_to` | [scheming](../../../../traits/instructions/scheming.json) (0.60) |
| dandified | new | `d_rather`, `d_too_to` | [dignified](../../../../traits/instructions/dignified.json) (0.45) |
| decent | new | `d_thoroughly`, `c_seemed_a`, `d_quite`, `c_was_a`, `c_is_a`, `d_very`, `d_utterly`, `d_remarkably`, `d_extremely`, `d_rather`, `d_so`, `p_reputation_for`, `p_man_of`, `p_woman_of`, `d_too_to`, `h_he_was_always`, `n_natural`, `t_inclined`, `p_known_for_his` | [kind to animals](../../../../traits/instructions/kind_to_animals.json) (0.42) |
| dedicated | new | `cards.copular_list`, `d_utterly`, `d_extremely`, `d_very`, `c_is_a`, `c_was_a`, `d_too_to`, `p_known_for_her`, `h_he_was_always`, `p_known_for_his`, `p_reputation_for`, `p_man_of` | [dependable](../../../../traits/instructions/dependable.json) (0.44) |
| defaulter | new | `n_habitual`, `n_notorious`, `n_chronic` | [irresponsible](../../../../traits/instructions/irresponsible.json) (0.38) |
| defective | new | `d_hopelessly`, `t_apt`, `n_natural`, `d_too_to`, `c_is_a`, `d_very`, `t_inclined`, `p_woman_of`, `c_was_a`, `p_man_of` | [incompetent](../../../../traits/instructions/incompetent.json) (0.31) |
| dejected | new | `d_quite`, `d_thoroughly`, `h_he_is_always`, `d_too_to`, `d_very`, `c_was_a`, `c_is_a`, `t_apt` | [flat](../../../../traits/instructions/flat.json) (0.38) |
| demimondaine | new | `n_notorious` | [shabby genteel](../../../../traits/instructions/shabby_genteel.json) (0.31) |
| demonstrative | new | `d_too`, `d_extremely`, `d_very`, `t_inclined`, `c_was_a`, `d_too_to` | [expressive](../../../../traits/instructions/expressive.json) (0.47) |
| depraved | new | `d_utterly`, `d_thoroughly`, `n_incorrigible`, `n_shameless`, `n_total`, `c_is_a`, `p_woman_of`, `n_natural`, `c_was_a`, `d_very`, `p_reputation_for`, `p_man_of`, `d_too_to` | [sadistic dark tetrad](../../../../traits/instructions/sadistic_dark_tetrad.json) (0.49) |
| dialectician | new | `n_born`, `n_natural` | [logical](../../../../traits/instructions/logical.json) (0.46) |
| diarist | new | `n_compulsive`, `n_inveterate`, `n_habitual`, `n_confirmed`, `n_born`, `n_natural` | [retentive](../../../../traits/instructions/retentive.json) (0.33) |
| difficult | new | `d_notoriously`, `d_too_to`, `d_extremely`, `d_rather`, `t_apt`, `n_chronic`, `c_was_a`, `d_very`, `c_is_a`, `n_notorious`, `n_hopeless`, `t_inclined`, `d_quite`, `p_reputation_for`, `n_natural`, `t_tendency`, `h_he_was_always`, `h_she_was_always`, `h_he_is_always`, `n_total`, `p_man_of`, `p_woman_of`, `p_known_for_his` | [unyielding](../../../../traits/instructions/unyielding.json) (0.32) |
| digressing | new | `h_he_is_always` | [distractible](../../../../traits/instructions/distractible.json) (0.38) |
| dipsomaniac | new | `n_confirmed`, `n_hopeless`, `n_notorious` | irrestrainable (0.34) |
| disabled | new | `d_chronically`, `d_so`, `c_is_a`, `d_extremely`, `d_too_to`, `c_was_a`, `d_very`, `t_apt` | [illiterate](../../../../traits/instructions/illiterate.json) (0.23) |
| disagreeably | new | `t_apt` | [rude](../../../../traits/instructions/rude.json) (0.40) |
| dislikable | new | `d_thoroughly` | [disagreeable](../../../../traits/instructions/disagreeable.json) (0.52) |
| disputatious | new | `t_inclined`, `d_too_to` | [partisan](../../../../traits/instructions/partisan.json) (0.41) |
| dour | new | `d_rather`, `c_was_a`, `t_inclined`, `c_is_a`, `d_very`, `p_known_for_his`, `p_man_of`, `p_reputation_for`, `d_too_to` | [melancholic](../../../../traits/instructions/melancholic.json) (0.36) |
| duellist | new | `n_inveterate`, `n_notorious`, `n_confirmed` | [violent](../../../../traits/instructions/violent.json) (0.44) |
| dyspeptic | new | `n_confirmed`, `n_chronic`, `n_hopeless`, `t_inclined`, `d_too_to` | sulky (0.33) |
| eager | new | `cards.copular_list`, `h_he_was_always`, `h_she_was_always`, `d_too_to`, `h_he_is_always`, `h_she_is_always`, `c_was_an`, `n_natural`, `p_noted_for_his`, `p_known_for_his`, `p_man_of`, `d_very`, `p_famous_for_his`, `t_apt` | [energetic](../../../../traits/instructions/energetic.json) (0.50) |
| eavesdropper | new | `n_shameless`, `n_inveterate`, `n_chronic` | concealing (0.40) |
| elocutionist | new | `n_born` | [eloquent](../../../../traits/instructions/eloquent.json) (0.46) |
| enigmatic | new | `cards.poss_nature`, `n_hopeless`, `c_was_an`, `d_rather`, `n_total`, `n_notorious`, `d_very`, `p_known_for_his`, `p_man_of`, `d_too_to` | [opaque](../../../../traits/instructions/opaque.json) (0.52) |
| enigmatical | new | `d_extremely`, `d_too_to` | concealing (0.52) |
| epigrams | new | `p_famous_for_his`, `p_noted_for_his`, `p_known_for_his` | [concise](../../../../traits/instructions/concise.json) (0.45) |
| exceptionable | new | `p_man_of`, `d_too_to` | unladylike (0.42) |
| exploiter | new | `n_shameless`, `n_notorious` | parasitic (0.42) |
| faultfinder | new | `n_chronic`, `n_born` | [detractor](../../../../traits/instructions/detractor.json) (0.31) |
| fearless | new | `d_utterly`, `d_remarkably`, `p_reputation_for`, `p_noted_for_his`, `p_known_for_his`, `p_known_for_her`, `c_was_a`, `c_is_a`, `p_famous_for_his`, `n_total`, `p_man_of`, `h_he_was_always`, `d_very`, `n_natural`, `p_woman_of`, `t_tendency`, `d_too_to` | [brave](../../../../traits/instructions/brave.json) (0.47) |
| felicitous | new | `n_natural`, `p_famous_for_his`, `p_man_of`, `p_known_for_his`, `d_too_to` | [precise](../../../../traits/instructions/precise.json) (0.40) |
| flagitious | new | `d_too_to` | [evil](../../../../traits/instructions/evil.json) (0.40) |
| fleet | new | `p_noted_for_his`, `d_too_to` | deft (0.31) |
| flighty | new | `t_inclined`, `d_rather`, `t_tendency`, `c_was_a`, `c_is_a`, `p_reputation_for`, `d_too_to`, `t_apt` | [distractible](../../../../traits/instructions/distractible.json) (0.43) |
| fonder | new | `h_she_was_always` | [expressive](../../../../traits/instructions/expressive.json) (0.40) |
| forehanded | new | `c_was_a` | [prudent](../../../../traits/instructions/prudent.json) (0.42) |
| frequenter | new | `n_habitual`, `n_inveterate`, `n_confirmed`, `n_notorious` | [persevering](../../../../traits/instructions/persevering.json) (0.27) |
| gadgeteer | new | `n_inveterate` | [early adopter](../../../../traits/instructions/early_adopter.json) (0.54) |
| garrulous | new | `t_inclined`, `c_was_a`, `t_tendency`, `c_is_a`, `d_very`, `t_apt`, `p_reputation_for`, `d_too_to` | gemini (0.31) |
| gifted | new | `d_remarkably`, `d_extremely`, `d_very`, `c_was_a`, `c_is_a`, `d_rather`, `d_too_to`, `p_man_of`, `p_known_for_his`, `p_reputation_for` | [quick witted](../../../../traits/instructions/quick_witted.json) (0.37) |
| giggler | new | `n_compulsive`, `n_inveterate`, `n_chronic` | [lighthearted](../../../../traits/instructions/lighthearted.json) (0.50) |
| godless | new | `d_utterly`, `c_is_a`, `c_was_a`, `d_very`, `p_reputation_for`, `p_man_of` | [calibrated](../../../../traits/instructions/calibrated.json) (0.32) |
| grumbler | new | `n_inveterate`, `n_chronic`, `n_confirmed`, `n_habitual`, `n_born`, `n_notorious` | [quarrelsome hexaco](../../../../traits/instructions/quarrelsome_hexaco.json) (0.41) |
| habitue | new | `n_confirmed` | [heavy drinker](../../../../traits/instructions/heavy_drinker.json) (0.35) |
| handicapped | new | `d_chronically`, `c_is_a`, `d_so`, `d_extremely`, `c_was_a`, `t_apt`, `h_he_is_always`, `d_very`, `d_too_to`, `h_he_was_always` | [mobility impaired](../../../../traits/instructions/mobility_impaired.json) (0.39) |
| hardheaded | new | `c_was_a`, `d_too_to`, `p_reputation_for`, `d_very`, `c_is_a` | [unyielding](../../../../traits/instructions/unyielding.json) (0.58) |
| harping | new | `h_he_is_always`, `h_she_was_always`, `h_he_was_always` | [obsessive](../../../../traits/instructions/obsessive.json) (0.32) |
| headstrong | new | `d_remarkably`, `d_rather`, `t_inclined`, `c_was_a`, `d_very`, `c_is_a`, `t_tendency`, `d_too_to`, `t_apt`, `p_man_of` | [unyielding](../../../../traits/instructions/unyielding.json) (0.39) |
| heedful | new | `h_he_was_always` | [focused](../../../../traits/instructions/focused.json) (0.62) |
| hinting | new | `h_she_is_always`, `h_she_was_always`, `h_he_was_always` | [vague](../../../../traits/instructions/vague.json) (0.36) |
| hired | new | `pippa.always`, `c_was_a`, `c_is_a`, `t_apt`, `h_he_was_always` | [renter](../../../../traits/instructions/renter.json) (0.29) |
| hortatory | new | `d_rather` | [persuasive](../../../../traits/instructions/persuasive.json) (0.36) |
| hospitable | new | `d_extremely`, `d_very`, `t_inclined`, `c_was_a`, `c_was_an`, `c_is_a`, `h_he_is_always`, `h_he_was_always`, `h_she_was_always`, `p_noted_for_his`, `d_too_to`, `p_man_of` | [welcoming](../../../../traits/instructions/welcoming.json) (0.43) |
| hospitably | new | `h_he_was_always` | [welcoming](../../../../traits/instructions/welcoming.json) (0.44) |
| housebreaker | new | `n_notorious` | [gun owner](../../../../traits/instructions/gun_owner.json) (0.24) |
| hussy | new | `n_shameless`, `n_total` | [promiscuous](../../../../traits/instructions/promiscuous.json) (0.37) |
| hypercritical | new | `t_tendency`, `t_inclined`, `t_apt`, `d_too_to` | [candid](../../../../traits/instructions/candid.json) (0.33) |
| hypochondriac | new | `n_confirmed`, `n_hopeless`, `n_chronic`, `n_inveterate`, `n_notorious`, `n_born`, `n_total` | [body obsessed](../../../../traits/instructions/body_obsessed.json) (0.33) |
| hypochondriacal | new | `t_inclined` | [health conscious](../../../../traits/instructions/health_conscious.json) (0.33) |
| ignoramus | new | `n_hopeless`, `n_total` | [unschooled](../../../../traits/instructions/unschooled.json) (0.33) |
| immoral | new | `d_notoriously`, `d_thoroughly`, `c_was_an`, `p_reputation_for`, `p_woman_of`, `d_very`, `t_inclined`, `p_man_of`, `t_tendency`, `d_too_to`, `t_apt` | [evil](../../../../traits/instructions/evil.json) (0.39) |
| impeccably | new | `h_he_was_always`, `h_she_was_always`, `h_she_is_always`, `h_he_is_always`, `p_man_of`, `p_known_for_his` | [perfectionist](../../../../traits/instructions/perfectionist.json) (0.38) |
| imperious | new | `d_too`, `c_was_an`, `p_woman_of`, `t_inclined`, `d_rather`, `p_man_of`, `t_tendency`, `d_very`, `n_natural`, `d_too_to`, `p_reputation_for`, `p_known_for_his` | [obedient](../../../../traits/instructions/obedient.json) (0.36) |
| improvident | new | `c_was_an`, `t_inclined`, `d_very`, `d_too_to`, `p_reputation_for`, `t_apt` | [extravagant](../../../../traits/instructions/extravagant.json) (0.42) |
| impure | new | `n_total`, `n_natural`, `c_was_an`, `d_too_to`, `p_woman_of`, `p_man_of`, `t_apt`, `d_very` | [moral](../../../../traits/instructions/moral.json) (0.33) |
| incisive | new | `p_known_for_her`, `p_noted_for_his`, `p_known_for_his`, `p_reputation_for`, `p_famous_for_his`, `p_man_of`, `p_woman_of`, `d_too_to` | [concise](../../../../traits/instructions/concise.json) (0.38) |
| incorrigible | new | `d_utterly`, `c_was_an`, `h_he_was_always`, `p_man_of`, `p_reputation_for`, `d_too_to` | [persevering](../../../../traits/instructions/persevering.json) (0.37) |
| incorruptible | new | `p_reputation_for`, `c_was_an`, `p_noted_for_his`, `p_man_of`, `p_famous_for_his`, `p_woman_of`, `p_known_for_his` | [honorable](../../../../traits/instructions/honorable.json) (0.42) |
| indebted | new | `n_total`, `n_chronic`, `n_hopeless`, `d_too_to`, `h_he_was_always` | [financially precarious](../../../../traits/instructions/financially_precarious.json) (0.32) |
| indigestible | new | `t_apt`, `p_reputation_for`, `d_too_to` | [verbose](../../../../traits/instructions/verbose.json) (0.46) |
| indiscreet | new | `d_notoriously`, `t_inclined`, `c_was_an`, `t_tendency`, `d_very`, `t_apt`, `d_too_to` | [brash](../../../../traits/instructions/brash.json) (0.33) |
| indiscriminating | new | `d_too_to` | [world accepting](../../../../traits/instructions/world_accepting.json) (0.41) |
| individualist | new | `n_incorrigible`, `n_confirmed`, `n_inveterate`, `n_born`, `n_total`, `n_natural`, `d_too_to` | [self reliant](../../../../traits/instructions/self_reliant.json) (0.30) |
| infamous | new | `d_notoriously`, `c_was_an`, `p_woman_of`, `p_man_of`, `p_known_for_his`, `d_very`, `d_too_to` | [famous](../../../../traits/instructions/famous.json) (0.33) |
| injurious | new | `t_tendency`, `t_apt`, `c_was_an`, `d_too_to`, `d_very` | [harmful](../../../../traits/instructions/harmful.json) (0.54) |
| insignificant | new | `d_utterly`, `d_quite`, `d_rather`, `d_too_to`, `c_was_an`, `d_so`, `d_very`, `p_man_of`, `p_woman_of`, `t_apt` | [languishing](../../../../traits/instructions/languishing.json) (0.35) |
| insolvent | new | `d_hopelessly`, `n_hopeless`, `c_was_an`, `n_notorious`, `p_reputation_for`, `d_too_to` | [financially precarious](../../../../traits/instructions/financially_precarious.json) (0.39) |
| insupportable | new | `d_rather`, `d_too_to` | unladylike (0.33) |
| intriguer | new | `n_inveterate`, `n_born`, `n_incorrigible`, `n_notorious`, `n_shameless`, `n_compulsive`, `n_confirmed`, `n_natural` | [scheming](../../../../traits/instructions/scheming.json) (0.41) |
| irreligious | new | `d_utterly`, `c_was_an`, `t_inclined`, `d_very`, `t_apt`, `d_too_to` | [secular](../../../../traits/instructions/secular.json) (0.37) |
| irreproachable | new | `p_man_of`, `p_woman_of`, `p_reputation_for` | [honorable](../../../../traits/instructions/honorable.json) (0.40) |
| jabbering | new | `h_he_is_always` | [stream of consciousness](../../../../traits/instructions/stream_of_consciousness.json) (0.35) |
| juristic | new | `c_is_a`, `c_was_a` | [logical](../../../../traits/instructions/logical.json) (0.44) |
| kindred | new | `c_seemed_a`, `c_was_a`, `c_is_a`, `p_woman_of`, `p_man_of`, `d_too_to` | [sentimental](../../../../traits/instructions/sentimental.json) (0.26) |
| klutz | new | `n_hopeless`, `n_total`, `n_born`, `n_natural` | [mobility impaired](../../../../traits/instructions/mobility_impaired.json) (0.32) |
| knavish | new | `p_famous_for_his`, `d_very` | [deceitful](../../../../traits/instructions/deceitful.json) (0.54) |
| knitter | new | `n_compulsive`, `n_inveterate` | [maker vals](../../../../traits/instructions/maker_vals.json) (0.20) |
| laggard | new | `n_hopeless`, `n_incorrigible`, `n_notorious`, `d_too_to` | [slow witted](../../../../traits/instructions/slow_witted.json) (0.36) |
| landlubber | new | `n_confirmed`, `n_hopeless` | [unschooled](../../../../traits/instructions/unschooled.json) (0.37) |
| latecomer | new | `n_habitual`, `n_chronic` | [foot dragging](../../../../traits/instructions/foot_dragging.json) (0.32) |
| lawbreaker | new | `n_habitual`, `n_chronic`, `n_confirmed`, `n_notorious` | [rule breaking](../../../../traits/instructions/rule_breaking.json) (0.35) |
| lecherous | new | `n_notorious`, `n_shameless`, `n_incorrigible`, `n_compulsive`, `n_inveterate`, `n_confirmed`, `c_was_a`, `c_is_a` | [promiscuous](../../../../traits/instructions/promiscuous.json) (0.43) |
| levelheaded | new | `d_very`, `c_was_a`, `c_is_a`, `d_too_to`, `p_known_for_his`, `p_reputation_for` | [composed](../../../../traits/instructions/composed.json) (0.52) |
| libeler | new | `n_notorious` | [deceitful](../../../../traits/instructions/deceitful.json) (0.39) |
| litigious | new | `d_notoriously`, `t_inclined`, `d_very`, `p_reputation_for`, `c_was_a`, `t_apt` | [aggressive](../../../../traits/instructions/aggressive.json) (0.28) |
| lodged | new | `h_she_is_always`, `t_apt` | [renter](../../../../traits/instructions/renter.json) (0.56) |
| loquacious | new | `t_inclined`, `d_very`, `t_tendency`, `c_was_a`, `c_is_a`, `p_known_for_his`, `p_reputation_for`, `t_apt`, `d_too_to` | [verbose](../../../../traits/instructions/verbose.json) (0.34) |
| lyrist | new | `n_born` | [artistic](../../../../traits/instructions/artistic.json) (0.21) |
| malapropisms | new | `p_famous_for_his`, `p_known_for_her`, `p_noted_for_his`, `p_known_for_his` | chattering (0.33) |
| malcontent | new | `n_chronic`, `n_habitual`, `n_notorious`, `n_born` | [quarrelsome hexaco](../../../../traits/instructions/quarrelsome_hexaco.json) (0.39) |
| malefactor | new | `n_notorious` | [rule breaking](../../../../traits/instructions/rule_breaking.json) (0.34) |
| malingerer | new | `n_chronic`, `n_notorious` | phony (0.35) |
| marriageable | new | `p_woman_of`, `p_man_of`, `c_is_a`, `c_was_a` | [married](../../../../traits/instructions/married.json) (0.41) |
| masturbator | new | `n_compulsive`, `n_habitual`, `n_chronic`, `n_confirmed`, `n_inveterate` | [smoker](../../../../traits/instructions/smoker.json) (0.29) |
| matronly | new | `d_rather`, `p_woman_of`, `c_was_a`, `c_is_a`, `d_too_to` | [dignified](../../../../traits/instructions/dignified.json) (0.51) |
| meddlesome | new | `h_she_was_always`, `t_inclined`, `d_very`, `c_was_a`, `c_is_a`, `d_too_to` | [rude](../../../../traits/instructions/rude.json) (0.24) |
| monopolistic | new | `n_natural`, `n_born`, `t_tendency` | [exclusivist](../../../../traits/instructions/exclusivist.json) (0.40) |
| mountebank | new | `n_incorrigible`, `n_born` | phony (0.39) |
| muddleheaded | new | `d_too_to` | [distractible](../../../../traits/instructions/distractible.json) (0.40) |
| nagging | new | `h_she_is_always`, `h_she_was_always`, `h_he_was_always`, `c_is_a`, `c_was_a` | [obsessive](../../../../traits/instructions/obsessive.json) (0.28) |
| nepotist | new | `n_shameless`, `n_inveterate`, `n_confirmed`, `n_notorious` | [clannish](../../../../traits/instructions/clannish.json) (0.38) |
| neurasthenic | new | `n_confirmed`, `n_chronic`, `n_hopeless`, `t_inclined`, `d_too_to` | [chronically ill](../../../../traits/instructions/chronically_ill.json) (0.38) |
| nice | new | `c_seemed_a`, `d_thoroughly`, `c_is_a`, `d_very`, `d_quite`, `c_was_a`, `d_extremely`, `d_remarkably`, `d_rather`, `h_she_was_always`, `d_so`, `h_he_was_always`, `h_she_is_always`, `d_too`, `d_too_to`, `h_he_is_always`, `t_inclined`, `t_tendency`, `p_man_of`, `p_reputation_for`, `p_woman_of`, `t_apt` | [friendly](../../../../traits/instructions/friendly.json) (0.56) |
| noiselessness | new | `n_natural` | [unassuming](../../../../traits/instructions/unassuming.json) (0.32) |
| nonentity | new | `n_hopeless`, `n_total` | [unassuming](../../../../traits/instructions/unassuming.json) (0.37) |
| nonmatched | new | `c_was_a` | [single](../../../../traits/instructions/single.json) (0.42) |
| nonnatural | new | `c_is_a` | [flat](../../../../traits/instructions/flat.json) (0.36) |
| nonparty | new | `c_was_a`, `c_is_a` | [apolitical](../../../../traits/instructions/apolitical.json) (0.57) |
| nonroyal | new | `p_woman_of` | [rootless](../../../../traits/instructions/rootless.json) (0.31) |
| nonstarter | new | `n_total` | [defeatist](../../../../traits/instructions/defeatist.json) (0.34) |
| normal | new | `d_quite`, `pippa.attributive`, `d_thoroughly`, `c_seemed_a`, `c_was_a`, `c_is_a`, `p_woman_of`, `d_so`, `p_man_of`, `d_very`, `d_rather`, `t_apt`, `t_tendency`, `n_total`, `d_too_to`, `t_inclined` | [unpretentious](../../../../traits/instructions/unpretentious.json) (0.41) |
| obsequious | new | `t_apt`, `d_rather`, `d_too_to` | [sycophantic](../../../../traits/instructions/sycophantic.json) (0.51) |
| obstinate | new | `c_was_an`, `d_remarkably`, `t_inclined`, `n_incorrigible`, `n_inveterate`, `d_very`, `d_extremely`, `d_rather`, `t_tendency`, `d_too_to`, `t_apt`, `p_reputation_for`, `h_he_was_always`, `p_famous_for_his`, `p_noted_for_his`, `p_man_of`, `n_natural`, `p_known_for_his` | [unyielding](../../../../traits/instructions/unyielding.json) (0.57) |
| obstreperous | new | `t_inclined`, `d_very`, `d_too_to`, `p_reputation_for` | [rebellious](../../../../traits/instructions/rebellious.json) (0.47) |
| officious | new | `d_too`, `c_was_an`, `d_rather`, `t_inclined`, `d_very`, `t_tendency`, `p_reputation_for`, `d_too_to` | [paternalistic](../../../../traits/instructions/paternalistic.json) (0.27) |
| onanist | new | `n_confirmed` | [male](../../../../traits/instructions/male.json) (0.24) |
| ordinary | new | `d_quite`, `d_rather`, `c_was_an`, `d_so`, `p_man_of`, `d_utterly`, `d_very`, `d_thoroughly`, `p_woman_of`, `d_extremely`, `n_total`, `d_too_to`, `n_natural`, `p_reputation_for`, `t_apt` | [unassuming](../../../../traits/instructions/unassuming.json) (0.49) |
| overachiever | new | `n_compulsive`, `n_chronic`, `n_total` | [ambitious](../../../../traits/instructions/ambitious.json) (0.32) |
| overcritical | new | `t_tendency`, `t_inclined`, `t_apt` | [detractor](../../../../traits/instructions/detractor.json) (0.37) |
| overemotional | new | `t_tendency` | [temperamental](../../../../traits/instructions/temperamental.json) (0.30) |
| overgenerous | new | `t_tendency` | [extravagant](../../../../traits/instructions/extravagant.json) (0.57) |
| overindulgent | new | `t_inclined`, `t_tendency`, `p_reputation_for` | [forgiving](../../../../traits/instructions/forgiving.json) (0.36) |
| pathetically | new | `h_she_is_always`, `h_he_was_always`, `d_too_to` | pathetic (0.53) |
| Peaceable | new | `t_inclined`, `c_was_a`, `d_very`, `c_is_a`, `p_reputation_for`, `p_man_of`, `d_too_to` | [peaceful](../../../../traits/instructions/peaceful.json) (0.52) |
| pestilent | new | `c_is_a`, `d_very`, `c_was_a` | meddling (0.40) |
| pettish | new | `t_inclined` | [thin skinned](../../../../traits/instructions/thin_skinned.json) (0.47) |
| philanderer | new | `n_incorrigible`, `n_notorious`, `n_compulsive`, `n_shameless`, `n_inveterate`, `n_habitual`, `n_chronic`, `n_born`, `n_hopeless`, `n_confirmed`, `n_natural` | [polygamous](../../../../traits/instructions/polygamous.json) (0.42) |
| piety | new | `p_noted_for_his`, `p_reputation_for`, `p_known_for_her`, `p_famous_for_his`, `p_known_for_his`, `p_man_of`, `p_woman_of` | [muslim](../../../../traits/instructions/muslim.json) (0.41) |
| plagiarist | new | `n_shameless`, `n_habitual`, `n_notorious`, `n_inveterate`, `n_confirmed` | [intellectually dishonest](../../../../traits/instructions/intellectually_dishonest.json) (0.30) |
| playgoer | new | `n_inveterate`, `n_confirmed` | [joiner](../../../../traits/instructions/joiner.json) (0.22) |
| pleasant | new | `c_seemed_a`, `d_remarkably`, `d_extremely`, `d_very`, `d_quite`, `c_was_a`, `d_thoroughly`, `d_rather`, `h_she_was_always`, `c_is_a`, `h_he_was_always`, `h_she_is_always`, `h_he_is_always`, `d_so`, `p_man_of`, `d_too_to`, `p_known_for_her`, `p_woman_of`, `t_inclined`, `p_noted_for_his`, `p_known_for_his`, `t_tendency`, `t_apt`, `n_natural`, `p_reputation_for` | [friendly](../../../../traits/instructions/friendly.json) (0.53) |
| polemist | new | `n_born` | [partisan](../../../../traits/instructions/partisan.json) (0.37) |
| poseur | new | `n_incorrigible`, `n_inveterate`, `n_born`, `n_total` | phony (0.30) |
| possessive | new | `pippa.copular_list`, `t_tendency`, `t_inclined`, `d_extremely`, `d_very`, `c_was_a`, `c_is_a`, `d_too_to`, `t_apt` | [controlling](../../../../traits/instructions/controlling.json) (0.37) |
| potterer | new | `n_confirmed` | [unhurried](../../../../traits/instructions/unhurried.json) (0.37) |
| precipitant | new | `t_apt` | [world changing](../../../../traits/instructions/world_changing.json) (0.27) |
| precocious | new | `d_remarkably`, `c_was_a`, `d_rather`, `d_extremely`, `d_too`, `d_very`, `c_is_a`, `p_noted_for_his`, `p_famous_for_his`, `t_inclined`, `p_reputation_for`, `p_known_for_his`, `p_man_of`, `t_apt`, `d_too_to` | [quick witted](../../../../traits/instructions/quick_witted.json) (0.37) |
| prevaricator | new | `n_confirmed`, `n_chronic`, `n_notorious` | [deceitful](../../../../traits/instructions/deceitful.json) (0.42) |
| prig | new | `n_hopeless`, `n_born`, `n_total` | [condescending](../../../../traits/instructions/condescending.json) (0.38) |
| probity | new | `p_reputation_for`, `p_man_of`, `p_noted_for_his`, `p_known_for_his`, `p_woman_of`, `p_famous_for_his` | incorruptible (0.47) |
| protective | new | `pippa.trait_list`, `pippa.copular_list`, `t_tendency`, `t_inclined`, `h_she_was_always`, `h_he_was_always`, `d_very`, `n_natural`, `c_was_a`, `t_apt`, `d_too_to`, `p_reputation_for` | [self sacrificing](../../../../traits/instructions/self_sacrificing.json) (0.32) |
| punctilious | new | `h_he_was_always`, `p_noted_for_his`, `d_very`, `c_was_a`, `p_reputation_for`, `p_man_of`, `p_known_for_his`, `d_too_to` | [rule abiding](../../../../traits/instructions/rule_abiding.json) (0.46) |
| punctiliously | new | `h_he_was_always` | [rule abiding](../../../../traits/instructions/rule_abiding.json) (0.52) |
| querulous | new | `t_inclined`, `t_apt`, `d_too_to` | [quarrelsome hexaco](../../../../traits/instructions/quarrelsome_hexaco.json) (0.41) |
| quoter | new | `n_inveterate` | chattering (0.24) |
| raconteur | new | `n_born`, `n_compulsive`, `n_incorrigible`, `n_inveterate`, `n_natural` | [entertaining](../../../../traits/instructions/entertaining.json) (0.54) |
| rakehell | new | `n_notorious` | [permissive](../../../../traits/instructions/permissive.json) (0.45) |
| rakish | new | `p_reputation_for`, `p_known_for_his` | [dignified](../../../../traits/instructions/dignified.json) (0.40) |
| readier | new | `h_he_was_always`, `c_was_a`, `p_man_of` | [risk seeking](../../../../traits/instructions/risk_seeking.json) (0.28) |
| readiest | new | `h_he_was_always` | [proactive](../../../../traits/instructions/proactive.json) (0.35) |
| reasonable | new | `c_seemed_a`, `d_quite`, `c_is_a`, `t_inclined`, `d_thoroughly`, `c_was_a`, `p_man_of`, `d_very`, `d_extremely`, `d_so`, `p_woman_of`, `h_she_is_always`, `h_he_is_always`, `p_reputation_for`, `h_he_was_always`, `d_too_to`, `h_she_was_always`, `t_tendency`, `t_apt` | [open minded](../../../../traits/instructions/open_minded.json) (0.51) |
| recidivist | new | `n_incorrigible`, `n_confirmed`, `n_chronic`, `n_hopeless`, `n_notorious` | [unrepentant](../../../../traits/instructions/unrepentant.json) (0.21) |
| refinement | new | `p_woman_of`, `p_man_of`, `p_noted_for_his`, `p_reputation_for`, `p_known_for_his` | [dignified](../../../../traits/instructions/dignified.json) (0.40) |
| reproaching | new | `h_she_was_always`, `h_he_was_always` | [accountable](../../../../traits/instructions/accountable.json) (0.37) |
| repugnant | new | `n_natural`, `n_inveterate`, `d_too_to`, `n_total`, `t_apt` | obscene (0.48) |
| respectable | new | `d_quite`, `d_thoroughly`, `c_seemed_a`, `d_very`, `c_is_a`, `d_extremely`, `c_was_a`, `p_woman_of`, `p_reputation_for`, `p_man_of`, `d_rather`, `d_too_to` | [honorable](../../../../traits/instructions/honorable.json) (0.52) |
| retaliative | new | `p_man_of` | [vindictive](../../../../traits/instructions/vindictive.json) (0.35) |
| retarded | new | `d_hopelessly`, `d_extremely`, `t_apt`, `c_is_a`, `c_was_a`, `t_tendency`, `d_very`, `d_too_to` | [illiterate](../../../../traits/instructions/illiterate.json) (0.30) |
| reticent | new | `t_inclined`, `n_natural`, `d_rather`, `n_habitual`, `d_extremely`, `h_he_was_always`, `p_noted_for_his`, `p_known_for_her`, `c_was_a`, `h_she_was_always`, `t_tendency`, `p_known_for_his`, `d_very`, `d_too_to`, `c_is_a`, `p_famous_for_his`, `p_reputation_for`, `t_apt`, `p_man_of` | [reserved](../../../../traits/instructions/reserved.json) (0.48) |
| romanticist | new | `n_incorrigible`, `n_confirmed`, `n_hopeless`, `n_inveterate`, `n_born` | [romantic](../../../../traits/instructions/romantic.json) (0.46) |
| ruthless | new | `d_utterly`, `p_reputation_for`, `p_known_for_his`, `p_famous_for_his`, `p_noted_for_his`, `c_is_a`, `c_was_a`, `t_inclined`, `d_rather`, `d_extremely`, `p_man_of`, `p_known_for_her`, `d_very`, `p_woman_of`, `t_tendency`, `n_total`, `t_apt`, `h_he_was_always`, `d_too_to` | [unrepentant](../../../../traits/instructions/unrepentant.json) (0.27) |
| saintlike | new | `p_man_of` | [altruistic](../../../../traits/instructions/altruistic.json) (0.38) |
| scandalmonger | new | `n_notorious` | [sadistic](../../../../traits/instructions/sadistic.json) (0.36) |
| schizophrenic | new | `n_chronic`, `d_chronically`, `n_hopeless`, `n_confirmed`, `d_rather`, `n_total`, `c_was_a`, `c_is_a`, `d_too_to` | maniacal (0.26) |
| schmoozer | new | `n_born`, `n_natural` | [friendly](../../../../traits/instructions/friendly.json) (0.37) |
| scornful | new | `t_inclined`, `n_total`, `n_natural`, `t_apt`, `t_tendency`, `h_he_was_always`, `c_was_a`, `p_known_for_his`, `d_too_to`, `p_man_of` | [condescending](../../../../traits/instructions/condescending.json) (0.42) |
| scrupulous | new | `d_too`, `p_reputation_for`, `h_she_was_always`, `p_noted_for_his`, `h_he_was_always`, `p_man_of`, `p_woman_of`, `d_very`, `p_known_for_his`, `d_too_to`, `h_he_is_always`, `t_inclined`, `p_famous_for_his`, `c_was_a`, `c_is_a`, `t_apt` | [conscientious](../../../../traits/instructions/conscientious.json) (0.56) |
| scurrility | new | `p_reputation_for` | insulting (0.52) |
| seamy | new | `p_famous_for_his` | unladylike (0.27) |
| selfemployed | new | `c_is_a`, `c_was_a` | [self reliant](../../../../traits/instructions/self_reliant.json) (0.41) |
| sensible | new | `c_seemed_a`, `d_remarkably`, `d_thoroughly`, `d_quite`, `c_is_a`, `d_very`, `c_was_a`, `d_extremely`, `d_too`, `p_woman_of`, `p_man_of`, `d_too_to`, `d_rather`, `d_so`, `h_he_is_always`, `n_natural`, `h_she_was_always`, `h_he_was_always`, `n_total`, `p_reputation_for`, `t_apt`, `t_inclined` | [pragmatic](../../../../traits/instructions/pragmatic.json) (0.42) |
| sensualist | new | `n_incorrigible`, `n_shameless`, `n_inveterate`, `n_confirmed`, `n_born`, `n_natural` | [epicurean](../../../../traits/instructions/epicurean.json) (0.48) |
| shamming | new | `h_she_was_always` | phony (0.40) |
| sheepish | new | `c_seemed_a`, `n_chronic`, `n_notorious`, `n_confirmed`, `n_total`, `n_natural`, `c_was_a`, `c_is_a`, `d_too_to`, `p_reputation_for`, `p_man_of` | [remorseful](../../../../traits/instructions/remorseful.json) (0.28) |
| shopworn | new | `t_apt`, `d_too_to` | [burned out](../../../../traits/instructions/burned_out.json) (0.30) |
| shrewd | new | `d_remarkably`, `d_extremely`, `c_was_a`, `d_very`, `p_noted_for_his`, `c_is_a`, `p_reputation_for`, `d_too_to`, `d_rather`, `p_famous_for_his`, `p_known_for_his`, `p_man_of`, `n_natural`, `p_known_for_her`, `p_woman_of`, `h_she_was_always`, `h_he_was_always`, `t_apt` | [wise](../../../../traits/instructions/wise.json) (0.38) |
| sightseer | new | `n_inveterate`, `n_born` | [globetrotter](../../../../traits/instructions/globetrotter.json) (0.32) |
| sinful | new | `d_notoriously`, `n_habitual`, `p_man_of`, `p_woman_of`, `n_inveterate`, `n_chronic`, `n_notorious`, `d_so`, `c_is_a`, `d_very`, `c_was_a`, `n_natural`, `p_reputation_for`, `p_known_for_her`, `n_total`, `d_too_to` | [evil](../../../../traits/instructions/evil.json) (0.41) |
| slanderer | new | `n_shameless`, `n_notorious` | [detractor](../../../../traits/instructions/detractor.json) (0.35) |
| sleuthhound | new | `n_born` | [persevering](../../../../traits/instructions/persevering.json) (0.31) |
| snorer | new | `n_habitual`, `n_chronic`, `n_inveterate`, `n_notorious` | [night owl](../../../../traits/instructions/night_owl.json) (0.35) |
| solicitous | new | `h_he_was_always`, `h_he_is_always`, `h_she_was_always`, `t_inclined`, `d_too_to` | [helpful](../../../../traits/instructions/helpful.json) (0.33) |
| sophistic | new | `n_shameless` | [logical](../../../../traits/instructions/logical.json) (0.33) |
| spiritless | new | `d_utterly`, `d_too_to`, `c_was_a` | [lethargic](../../../../traits/instructions/lethargic.json) (0.42) |
| stealthily | new | `h_he_is_always` | clandestine (0.45) |
| stodgier | new | `d_rather` | [staid](../../../../traits/instructions/staid.json) (0.52) |
| stubborn | new | `pippa.copular_list`, `d_notoriously`, `d_remarkably`, `d_too_to`, `c_was_a`, `d_very`, `t_inclined`, `t_tendency`, `d_extremely`, `c_is_a`, `d_rather`, `p_reputation_for`, `p_known_for_her`, `p_noted_for_his`, `p_known_for_his`, `p_famous_for_his`, `p_man_of`, `h_she_was_always`, `t_apt`, `h_he_was_always`, `p_woman_of`, `n_natural` | [unyielding](../../../../traits/instructions/unyielding.json) (0.66) |
| stupid | new | `d_hopelessly`, `d_rather`, `d_remarkably`, `d_utterly`, `d_too_to`, `d_thoroughly`, `d_quite`, `d_very`, `d_extremely`, `c_is_a`, `c_was_a`, `d_so`, `p_reputation_for`, `p_noted_for_his`, `t_inclined`, `n_natural`, `p_famous_for_his`, `n_total`, `t_apt`, `h_he_was_always`, `p_known_for_his`, `p_man_of` | [foolish](../../../../traits/instructions/foolish.json) (0.42) |
| stutterer | new | `n_chronic`, `n_confirmed`, `n_hopeless` | chattering (0.35) |
| suave | new | `p_noted_for_his`, `p_known_for_his`, `d_very`, `c_was_a`, `n_natural`, `c_is_a`, `p_man_of`, `d_too_to`, `p_reputation_for` | [composed](../../../../traits/instructions/composed.json) (0.44) |
| subtle | new | `p_known_for_her`, `d_too_to`, `p_noted_for_his`, `p_known_for_his`, `d_extremely`, `d_very`, `p_famous_for_his`, `p_man_of`, `c_is_a`, `d_so`, `d_rather`, `p_woman_of`, `p_reputation_for`, `c_was_a`, `t_apt`, `t_inclined`, `n_natural`, `h_he_was_always` | [reserved](../../../../traits/instructions/reserved.json) (0.50) |
| successful | new | `d_famously`, `t_apt`, `d_remarkably`, `d_extremely`, `p_famous_for_his`, `d_very`, `p_known_for_his`, `c_seemed_a`, `p_known_for_her`, `d_too`, `h_he_was_always`, `p_noted_for_his`, `h_he_is_always`, `p_reputation_for`, `d_thoroughly`, `d_quite`, `h_she_is_always`, `c_was_a`, `c_is_a`, `d_so`, `h_she_was_always`, `d_rather`, `d_too_to`, `t_tendency`, `t_inclined`, `p_man_of` | [wealthy](../../../../traits/instructions/wealthy.json) (0.61) |
| sulky | new | `d_chronically`, `t_inclined`, `d_rather`, `d_very`, `c_was_a`, `d_too_to`, `t_apt` | [emotionally inarticulate](../../../../traits/instructions/emotionally_inarticulate.json) (0.30) |
| suppliant | new | `n_hopeless` | [humble](../../../../traits/instructions/humble.json) (0.36) |
| supposititious | new | `c_was_a`, `c_is_a` | phony (0.40) |
| swearer | new | `n_habitual`, `n_notorious`, `n_inveterate` | [permissive](../../../../traits/instructions/permissive.json) (0.36) |
| taciturn | new | `d_rather`, `t_inclined`, `c_was_a`, `d_extremely`, `p_noted_for_his`, `p_reputation_for`, `h_she_was_always`, `c_is_a`, `d_very`, `h_he_was_always`, `p_famous_for_his`, `p_known_for_his`, `t_tendency`, `n_natural`, `p_man_of`, `t_apt`, `d_too_to` | [circumspect](../../../../traits/instructions/circumspect.json) (0.35) |
| tendentious | new | `n_natural`, `n_habitual`, `n_inveterate`, `n_chronic`, `n_incorrigible`, `n_compulsive`, `n_notorious`, `n_confirmed`, `p_known_for_her`, `p_noted_for_his`, `p_known_for_his`, `n_total`, `p_famous_for_his`, `d_too_to` | [partisan](../../../../traits/instructions/partisan.json) (0.62) |
| theatergoer | new | `n_inveterate` | [theatrical](../../../../traits/instructions/theatrical.json) (0.27) |
| theatregoer | new | `n_inveterate` | [theatrical](../../../../traits/instructions/theatrical.json) (0.28) |
| theorizer | new | `n_inveterate` | [speculative](../../../../traits/instructions/speculative.json) (0.47) |
| tinkerer | new | `n_inveterate`, `n_compulsive`, `n_born`, `n_natural` | [realistic holland](../../../../traits/instructions/realistic_holland.json) (0.26) |
| truant | new | `n_habitual`, `n_chronic`, `n_incorrigible`, `n_confirmed`, `n_inveterate`, `n_notorious`, `p_reputation_for` | [absentee](../../../../traits/instructions/absentee.json) (0.39) |
| twentyone | new | `p_woman_of`, `p_man_of` | [young](../../../../traits/instructions/young.json) (0.45) |
| ugly | new | `d_famously`, `d_remarkably`, `d_notoriously`, `c_was_an`, `d_rather`, `d_extremely`, `d_very`, `d_so`, `d_quite`, `d_too_to`, `t_inclined`, `p_famous_for_his`, `p_noted_for_his`, `t_apt`, `p_reputation_for`, `p_known_for_his`, `n_natural`, `h_he_was_always`, `p_man_of` | [plain looking](../../../../traits/instructions/plain_looking.json) (0.54) |
| unamiable | new | `d_very` | [reserved](../../../../traits/instructions/reserved.json) (0.40) |
| unassertive | new | `t_tendency`, `d_too_to` | [submissive](../../../../traits/instructions/submissive.json) (0.48) |
| unattachment | new | `p_man_of` | [detached](../../../../traits/instructions/detached.json) (0.31) |
| unbounding | new | `p_man_of` | [energetic](../../../../traits/instructions/energetic.json) (0.37) |
| unboyish | new | `d_very` | [serious](../../../../traits/instructions/serious.json) (0.47) |
| uncordial | new | `p_woman_of` | [reserved](../../../../traits/instructions/reserved.json) (0.42) |
| uncultivated | new | `d_quite`, `c_was_an`, `p_man_of`, `d_too_to` | [rude](../../../../traits/instructions/rude.json) (0.33) |
| underachiever | new | `n_chronic`, `n_notorious` | pathetic (0.32) |
| underemployed | new | `d_chronically` | [trapped in job](../../../../traits/instructions/trapped_in_job.json) (0.29) |
| underperformer | new | `n_chronic` | [unreliable](../../../../traits/instructions/unreliable.json) (0.30) |
| undiscriminating | new | `t_apt`, `d_too_to` | [world accepting](../../../../traits/instructions/world_accepting.json) (0.38) |
| undistinguished | new | `d_quite`, `c_was_an`, `p_woman_of`, `p_man_of`, `d_too_to` | [ambitious](../../../../traits/instructions/ambitious.json) (0.29) |
| unenterprising | new | `d_too_to` | [financially conservative](../../../../traits/instructions/financially_conservative.json) (0.34) |
| unexceptionable | new | `p_man_of`, `p_woman_of`, `d_very` | [honorable](../../../../traits/instructions/honorable.json) (0.44) |
| unfaded | new | `p_woman_of` | [energetic](../../../../traits/instructions/energetic.json) (0.35) |
| unformed | new | `d_quite`, `d_too_to`, `p_man_of` | [self uncertain](../../../../traits/instructions/self_uncertain.json) (0.39) |
| unhandy | new | `d_extremely`, `d_too_to` | [incompetent](../../../../traits/instructions/incompetent.json) (0.43) |
| unhospitable | new | `c_was_an` | [rude](../../../../traits/instructions/rude.json) (0.32) |
| unimpeachable | new | `p_man_of`, `p_woman_of`, `p_reputation_for`, `p_known_for_his` | [honorable](../../../../traits/instructions/honorable.json) (0.45) |
| unimpeached | new | `p_man_of` | [honorable](../../../../traits/instructions/honorable.json) (0.46) |
| unimportant | new | `d_quite`, `d_too_to`, `c_was_an`, `d_rather`, `d_very`, `t_apt` | [self effacing](../../../../traits/instructions/self_effacing.json) (0.35) |
| uninfluential | new | `d_rather`, `d_too_to` | [dull](../../../../traits/instructions/dull.json) (0.32) |
| uninformed | new | `d_utterly`, `d_too_to`, `t_apt` | [secular](../../../../traits/instructions/secular.json) (0.29) |
| uninteresting | new | `d_utterly`, `d_rather`, `c_was_an`, `d_very`, `t_apt`, `d_too_to` | [flat](../../../../traits/instructions/flat.json) (0.45) |
| unlicked | new | `c_was_an` | unladylike (0.47) |
| unlikable | new | `d_thoroughly`, `c_was_an` | [disagreeable](../../../../traits/instructions/disagreeable.json) (0.49) |
| unlovely | new | `d_thoroughly`, `c_was_an`, `d_too_to` | [indifferent to animals](../../../../traits/instructions/indifferent_to_animals.json) (0.34) |
| unmalleable | new | `d_too_to` | [unyielding](../../../../traits/instructions/unyielding.json) (0.55) |
| unmusical | new | `d_quite`, `d_too_to` | [joyless](../../../../traits/instructions/joyless.json) (0.35) |
| unobjectionable | new | `d_quite` | [staid](../../../../traits/instructions/staid.json) (0.46) |
| unpractical | new | `d_thoroughly`, `c_was_an`, `d_very`, `d_too_to` | [incompetent](../../../../traits/instructions/incompetent.json) (0.50) |
| unprincipled | new | `d_utterly`, `d_thoroughly`, `c_was_an`, `d_very`, `p_man_of`, `p_reputation_for`, `d_too_to` | [amoral](../../../../traits/instructions/amoral.json) (0.44) |
| unpunctuality | new | `p_reputation_for` | [lazy](../../../../traits/instructions/lazy.json) (0.32) |
| unquestioned | new | `p_man_of`, `p_woman_of`, `c_was_an`, `p_reputation_for` | [trustworthy](../../../../traits/instructions/trustworthy.json) (0.29) |
| unredeemable | new | `d_utterly` | [unrepentant](../../../../traits/instructions/unrepentant.json) (0.42) |
| unremarkable | new | `d_quite`, `c_was_an`, `d_rather`, `p_woman_of`, `p_man_of`, `d_too_to` | [unassuming](../../../../traits/instructions/unassuming.json) (0.43) |
| unsavoury | new | `d_thoroughly`, `d_rather`, `c_was_an`, `d_very`, `p_woman_of`, `p_man_of`, `d_too_to`, `p_reputation_for` | [unscrupulous](../../../../traits/instructions/unscrupulous.json) (0.43) |
| unscientific | new | `d_utterly`, `d_very`, `d_too_to`, `t_apt` | [illogical](../../../../traits/instructions/illogical.json) (0.40) |
| unselective | new | `d_too_to` | [world accepting](../../../../traits/instructions/world_accepting.json) (0.34) |
| untiring | new | `p_known_for_her`, `p_man_of`, `p_noted_for_his`, `c_was_an`, `p_known_for_his`, `p_woman_of`, `h_he_was_always`, `p_reputation_for` | [industrious](../../../../traits/instructions/industrious.json) (0.41) |
| unwavering | new | `cards.known_for`, `p_known_for_her`, `c_was_an`, `p_man_of`, `p_known_for_his`, `p_woman_of`, `p_reputation_for` | [persevering](../../../../traits/instructions/persevering.json) (0.50) |
| unwearying | new | `p_man_of` | [persevering](../../../../traits/instructions/persevering.json) (0.45) |
| uppish | new | `t_inclined`, `d_too_to` | [arrogant](../../../../traits/instructions/arrogant.json) (0.36) |
| upright | new | `c_was_an`, `d_thoroughly`, `d_remarkably`, `p_reputation_for`, `p_man_of`, `p_noted_for_his`, `d_very`, `d_extremely`, `p_known_for_his`, `p_woman_of`, `t_inclined`, `p_famous_for_his`, `t_tendency`, `d_too_to`, `h_he_was_always`, `n_natural` | [loyal](../../../../traits/instructions/loyal.json) (0.43) |
| usurer | new | `n_notorious` | [spiteful](../../../../traits/instructions/spiteful.json) (0.31) |
| uxorious | new | `c_was_an` | [married](../../../../traits/instructions/married.json) (0.33) |
| vain | new | `d_notoriously`, `d_extremely`, `d_rather`, `t_inclined`, `c_was_a`, `d_very`, `c_is_a`, `d_too_to`, `p_noted_for_his`, `n_natural`, `p_reputation_for`, `p_known_for_his`, `t_tendency`, `p_woman_of`, `p_man_of`, `t_apt`, `p_famous_for_his`, `h_he_was_always` | [self aggrandizing](../../../../traits/instructions/self_aggrandizing.json) (0.40) |
| valetudinarian | new | `n_confirmed`, `n_chronic` | [body obsessed](../../../../traits/instructions/body_obsessed.json) (0.38) |
| versatile | new | `d_remarkably`, `d_extremely`, `p_noted_for_his`, `c_was_a`, `p_known_for_her`, `d_very`, `p_known_for_his`, `p_man_of`, `p_reputation_for`, `c_is_a`, `p_famous_for_his`, `p_woman_of`, `n_natural`, `d_too_to` | [improvisational](../../../../traits/instructions/improvisational.json) (0.30) |
| vicious | new | `d_incurably`, `d_thoroughly`, `d_utterly`, `d_extremely`, `t_inclined`, `p_reputation_for`, `c_is_a`, `c_was_a`, `d_very`, `p_known_for_his`, `p_man_of`, `d_rather`, `p_noted_for_his`, `t_tendency`, `p_woman_of`, `d_too_to`, `t_apt`, `p_famous_for_his`, `n_natural` | [sadistic dark tetrad](../../../../traits/instructions/sadistic_dark_tetrad.json) (0.42) |
| violator | new | `n_habitual`, `n_chronic`, `n_notorious`, `n_shameless`, `n_confirmed` | [rule breaking](../../../../traits/instructions/rule_breaking.json) (0.52) |
| wailful | new | `c_is_a` | [self pitying](../../../../traits/instructions/self_pitying.json) (0.41) |
| washout | new | `n_total` | [incompetent](../../../../traits/instructions/incompetent.json) (0.35) |
| wearisome | new | `t_apt`, `d_too_to` | [dull](../../../../traits/instructions/dull.json) (0.36) |
| wheedler | new | `n_born` | flattering (0.51) |
| whoremaster | new | `n_notorious` | [promiscuous](../../../../traits/instructions/promiscuous.json) (0.39) |
| wicked | new | `d_notoriously`, `d_thoroughly`, `d_utterly`, `d_very`, `c_is_a`, `d_extremely`, `c_was_a`, `p_reputation_for`, `p_man_of`, `p_known_for_her`, `d_too_to`, `p_woman_of`, `p_famous_for_his`, `p_noted_for_his`, `t_inclined`, `p_known_for_his`, `n_natural` | [malicious](../../../../traits/instructions/malicious.json) (0.53) |
| willing | new | `h_he_was_always`, `h_he_is_always`, `h_she_is_always`, `h_she_was_always`, `pippa.copular_list`, `d_too_to`, `p_known_for_her`, `n_shameless`, `p_known_for_his`, `p_noted_for_his`, `n_habitual`, `t_tendency`, `n_total`, `p_famous_for_his`, `t_inclined`, `t_apt`, `n_natural`, `d_very`, `c_was_a`, `p_reputation_for`, `c_is_a`, `p_man_of` | [helpful](../../../../traits/instructions/helpful.json) (0.31) |
| womaniser | new | `n_compulsive`, `n_notorious`, `n_incorrigible`, `n_inveterate`, `n_shameless`, `n_confirmed`, `n_chronic`, `n_hopeless` | [promiscuous](../../../../traits/instructions/promiscuous.json) (0.41) |
| worthless | new | `d_utterly`, `d_quite`, `d_thoroughly`, `d_rather`, `c_is_a`, `c_was_a`, `d_very`, `t_apt`, `d_too_to`, `p_man_of`, `p_reputation_for` | [face culture](../../../../traits/instructions/face_culture.json) (0.36) |

Kept rows only one frame found: `c_is_a` 2 (nonnatural, wailful); `c_was_a` 2 (forehanded, nonmatched); `c_was_an` 4 (adulterine, unhospitable, unlicked, uxorious); `d_chronically` 2 (assaultive, underemployed); `d_quite` 1 (unobjectionable); `d_rather` 2 (hortatory, stodgier); `d_thoroughly` 1 (dislikable); `d_too_to` 8 (cagy, concessive, flagitious, indiscriminating, muddleheaded, unenterprising, unmalleable, unselective); `d_utterly` 1 (unredeemable); `d_very` 2 (unamiable, unboyish); `h_he_is_always` 4 (behindhand, digressing, jabbering, stealthily); `h_he_was_always` 4 (heedful, hospitably, punctiliously, readiest); `h_she_was_always` 2 (fonder, shamming); `n_born` 6 (casuist, elocutionist, lyrist, polemist, sleuthhound, wheedler); `n_chronic` 2 (bellyacher, underperformer); `n_confirmed` 4 (balletomane, habitue, onanist, potterer); `n_habitual` 1 (bluffer); `n_hopeless` 2 (bumbler, suppliant); `n_inveterate` 5 (gadgeteer, quoter, theatergoer, theatregoer, theorizer); `n_natural` 3 (appetency, appetent, noiselessness); `n_notorious` 9 (anglophobe, demimondaine, housebreaker, libeler, malefactor, rakehell, scandalmonger, usurer, whoremaster); `n_shameless` 1 (sophistic); `n_total` 2 (nonstarter, washout); `p_famous_for_his` 1 (seamy); `p_man_of` 6 (retaliative, saintlike, unattachment, unbounding, unimpeached, unwearying); `p_reputation_for` 2 (scurrility, unpunctuality); `p_woman_of` 4 (childbearing, nonroyal, uncordial, unfaded); `t_apt` 2 (disagreeably, precipitant); `t_inclined` 2 (hypochondriacal, pettish); `t_tendency` 2 (overemotional, overgenerous).

## Files

- [candidates.jsonl](candidates.jsonl), [run.json](run.json), [usage.json](usage.json), [submit_report.json](submit_report.json)
- M1 batch [2026-10-18-pilot_corpus_frames](../../../filter/2026-10-18-pilot_corpus_frames), M3 batch [2026-10-18-pilot_corpus_frames](../../../novelty/2026-10-18-pilot_corpus_frames)
- [roger_sample.md](roger_sample.md): the 50-row spot check; [roger_first_hour.md](roger_first_hour.md): the first hour of review
