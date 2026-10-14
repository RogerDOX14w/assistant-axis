# Lexical recall: the dry readout (gate 1, $0)

Lookup [lookup.json](./lookup.json) (content sha256 `92408c7dfd32`); lexicons oewn `oewn:2024`, moby `7c9742b1ed94`.  Terms: [glossary](../../../reports/trait_gap_generation/glossary.md) (lexical link, lexical neighbour, lexical-only pair).

## Coverage of the lookup table

- **oewn**: corpus 699 of 932; queue 95 of 122; queue_with_text 31 of 38
- **moby**: corpus 539 of 932; queue 70 of 122; queue_with_text 27 of 38

## The kept rows

4283 kept rows (M3 `new` or `grey`), 2984 single words and 1299 phrases; by pass {'physical': 126, 'states': 122, 'trait': 4035}; by cut-off {3: 3067, 4: 1216}; rule sets {'m3_rules_2': 76, 'm3_rules_3': 4207}.  Found in the lexicon: oewn 2619, moby 1981.

## The lexical-only pairs

**1797 kept rows (1678 single words) have 11570 lexical-only pairs**; 2209 are judgeable; 2923 further links were already listed by M3.  Not judged: {'moby_below_floor': 9105, 'name_only': 235, 'no_description': 21}.  1499 pairs go to a standards-derived trait (a bare lemma such as `agreeable` reaches [agreeable (Big Five)](../../traits/instructions/agreeable_big_five.json) too) and 609 reach a trait through its `renamed_from`.

| by | counts |
|---|---|
| link type | {'also': 85, 'similar': 568, 'synonym': 10917} |
| lexicon | {'moby': 10625, 'oewn': 945} |
| target kind | {'corpus': 10718, 'queue': 852} |
| cut-off band | {'c3 alignment 0-1': 7171, 'c3 alignment 2': 1422, 'c4 alignment 2-3': 21, 'c4 alignment 3': 2956} |
| pass | {'physical': 356, 'states': 268, 'trait': 10946} |
| hit rows by cut-off | {3: 1381, 4: 416} |
| hit rows by alignment score | {0: 783, 1: 395, 2: 205, 3: 414} |
| name-only links | 235 |
| Moby | {'n': 10625, 'moby_only': 10625, 'moby_only_below_floor': 9105, 'moby_only_no_cosine': 0} |
| cosine of the pairs | {'n': 11314, 'min': -0.1653, 'p10': -0.0234, 'median': 0.0926, 'p90': 0.2124, 'max': 0.6972} (no cosine: 256) |

## Antonym evidence

94 kept rows carry antonym evidence ({'antonym': 57, 'negation_affix': 46}); 50 have an OEWN antonym that is a corpus trait, 21 of them a trait with no pair partner.  18 of the rows with evidence also carry M3's `pair_completion_for`, 12 naming one of the same traits.

## Stem families

447 kept rows have a family member ({'candidate': 383, 'queue': 14, 'corpus': 80}; {'affix': 404, 'derivation': 73}); 178 groups of kept rows tie each other.  Largest: corrupt#1, corruptible#1, incorrupt#1, incorruptible#1; disgraceful#1, graceful#1, graceless#1, ungraceful#1; imperfect#1, imperfectible#1, perfect#1, perfectible#1; bear#1, bearable#1, unbearable#1; beast#1, beastly#1, bestial#1.

## Free labels

Roger merged 78 kept rows into a corpus trait in review.  Of the rows with lexical-only pairs, 112 were merged in review (into a trait or another candidate), 62 into a corpus trait, and **4 were merged into the lexically linked trait**: `annoying#1` → [disagreeable](../../traits/instructions/disagreeable.json), `delightful#1` → [agreeable](../../traits/instructions/agreeable.json), `nice#1` → [agreeable](../../traits/instructions/agreeable.json), `pleasant#1` → [agreeable](../../traits/instructions/agreeable.json).

The gate audit's five retrieval misses:

| candidate | the audit's trait | reached | lexical-only links |
|---|---|---|---|
| `delightful#1` | [agreeable](../../traits/instructions/agreeable.json) | **yes** | adorable (moby synonym), agreeable (moby synonym), entertaining (moby synonym), fair (moby synonym), good (moby synonym), grateful (moby synonym), joyful (moby synonym), unflinching (moby synonym) |
| `pleasant#1` | [agreeable](../../traits/instructions/agreeable.json) | **yes** | grateful (oewn similar), agreeable (oewn also), benevolent (moby synonym), clear (moby synonym), entertaining (moby synonym), expedient (moby synonym), fair (moby synonym), famous (moby synonym), good (moby synonym), gregarious (moby synonym), healthy (moby synonym), helpful (moby synonym), joyful (moby synonym), open_big_five (moby synonym), open_hexaco (moby synonym), optimistic (moby synonym), polite (moby synonym), social_holland (moby synonym), unflinching (moby synonym), unselfconscious (moby synonym) |
| `nice#1` | [agreeable](../../traits/instructions/agreeable.json) | **yes** | squeamish (oewn synonym), fastidious (oewn similar), good (oewn similar), precise (oewn similar), accurate (moby synonym), agreeable (moby synonym), agreeable_big_five (moby synonym), benevolent (moby synonym), benign (moby synonym), cheerful (moby synonym), christian (moby synonym), conscientious (moby synonym), conscientious_big_five (moby synonym), conscientious_hexaco (moby synonym), conventional (moby synonym), conventional_hexaco (moby synonym), conventional_holland (moby synonym), conventional_kohlberg (moby synonym), critical (moby synonym), earnest (moby synonym), expedient (moby synonym), fair (moby synonym), famous (moby synonym), grateful (moby synonym), healthy (moby synonym), helpful (moby synonym), intense (moby synonym), meticulous (moby synonym), modest (moby synonym), observant (moby synonym), religious (moby synonym), rigid (moby synonym), slight (moby synonym), strict (moby synonym), tactful (moby synonym), unselfconscious (moby synonym), wise (moby synonym) |
| `annoying#1` | [disagreeable](../../traits/instructions/disagreeable.json) | **yes** | disagreeable (oewn similar), bitter (moby synonym), mischievous (moby synonym), provocative (moby synonym) |
| `unsteadfast#1` | [submissive](../../traits/instructions/submissive.json) | no | eccentric (moby synonym), impulsive (moby synonym), indecisive (moby synonym), insecure (moby synonym), irresponsible (moby synonym), restless (moby synonym), uncertain (moby synonym), unreliable (moby synonym), untrustworthy (moby synonym), whimsical (moby synonym) |

## The sweep's estimate

**$6.96** live (Opus share ASSUMED 0.40-0.62, priced at the higher):

- overlap, Sonnet on every lexical-only pair: 2209 x (219, 78) tokens at claude-sonnet-5-5 rates = $2.691
- overlap, Opus on 62% of them (ASSUMED until measured): 1370 x (220, 112) tokens at claude-opus-5-5 rates = $4.274

Cap: {'n_cut': 0, 'n_kept_moby': 1283, 'cut_cosine': None}

## The labelled pairs

**oewn** ([labelled_pairs.json](../calibration/labelled_pairs.json), 2407 pairs): both sides found; abstain; synonym-like links (synonym / similar / also); antonym links (antonym / affix); recall or false-flag rate over the pairs with both sides found.

| relation | n | both found | abstain | synonym-like | by link | antonym | by antonym | rate |
|---|---|---|---|---|---|---|---|---|
| antonym | 286 | 211 | 75 | 0 | 0/0/0 | 58 | 52/6 | recall 27.5% |
| deliberate_duplicate | 3 | 0 | 3 | 0 | 0/0/0 | 0 | 0/0 | - |
| duplicate | 79 | 57 | 22 | 16 | 4/9/3 | 0 | 0/0 | recall 28.1% |
| near_distinct | 34 | 20 | 14 | 1 | 1/0/0 | 1 | 1/0 | false flags 10.0% |
| polysemy_reject | 5 | 5 | 0 | 5 | 5/0/0 | 0 | 0/0 | - |
| unrelated | 2000 | 1330 | 670 | 5 | 1/3/1 | 0 | 0/0 | false flags 0.4% |

**moby** ([labelled_pairs.json](../calibration/labelled_pairs.json), 2407 pairs): both sides found; abstain; synonym-like links (synonym / similar / also); antonym links (antonym / affix); recall or false-flag rate over the pairs with both sides found.

| relation | n | both found | abstain | synonym-like | by link | antonym | by antonym | rate |
|---|---|---|---|---|---|---|---|---|
| antonym | 286 | 168 | 118 | 4 | 4/0/0 | 0 | 0/0 | recall 0.0% |
| deliberate_duplicate | 3 | 0 | 3 | 0 | 0/0/0 | 0 | 0/0 | - |
| duplicate | 79 | 48 | 31 | 33 | 33/0/0 | 0 | 0/0 | recall 68.8% |
| near_distinct | 34 | 10 | 24 | 2 | 2/0/0 | 0 | 0/0 | false flags 20.0% |
| polysemy_reject | 5 | 5 | 0 | 0 | 0/0/0 | 0 | 0/0 | - |
| unrelated | 2000 | 899 | 1101 | 21 | 21/0/0 | 0 | 0/0 | false flags 2.3% |

