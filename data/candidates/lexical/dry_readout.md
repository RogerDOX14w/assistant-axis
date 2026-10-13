# Lexical recall: the dry readout (gate 1, $0)

Lookup [lookup.json](./lookup.json) (content sha256 `9a838401a523`); lexicons oewn `oewn:2024`.  Terms: [glossary](../../../reports/trait_gap_generation/glossary.md) (lexical link, lexical neighbour, lexical-only pair).

## Coverage of the lookup table

- **oewn**: corpus 699 of 932; queue 95 of 122; queue_with_text 31 of 38

## The kept rows

4091 kept rows (M3 `new` or `grey`), 2981 single words and 1110 phrases; by pass {'physical': 126, 'states': 122, 'trait': 3843}; by cut-off {3: 2971, 4: 1120}; rule sets {'m3_rules_2': 76, 'm3_rules_3': 4015}.  Found in the lexicon: oewn 2618.

## The lexical-only pairs

**596 kept rows (555 single words) have 944 lexical-only pairs**; 925 are judgeable; 566 further links were already listed by M3.  Not judged: {'name_only': 19}.  125 pairs go to a standards-derived trait (a bare lemma such as `agreeable` reaches [agreeable (Big Five)](../../traits/instructions/agreeable_big_five.json) too) and 48 reach a trait through its `renamed_from`.

| by | counts |
|---|---|
| link type | {'also': 85, 'similar': 567, 'synonym': 292} |
| lexicon | {'oewn': 944} |
| target kind | {'corpus': 851, 'queue': 93} |
| cut-off band | {'c3 alignment 0-1': 581, 'c3 alignment 2': 105, 'c4 alignment 3': 258} |
| pass | {'physical': 24, 'states': 24, 'trait': 896} |
| hit rows by cut-off | {3: 435, 4: 161} |
| hit rows by alignment score | {0: 230, 1: 139, 2: 66, 3: 161} |
| name-only links | 19 |
| Moby | {'n': 0, 'moby_only': 0, 'moby_only_below_floor': 0, 'moby_only_no_cosine': 0} |
| cosine of the pairs | {'n': 925, 'min': -0.11, 'p10': -0.0005, 'median': 0.1319, 'p90': 0.2435, 'max': 0.696} (no cosine: 19) |

## Antonym evidence

94 kept rows carry antonym evidence ({'antonym': 57, 'negation_affix': 46}); 50 have an OEWN antonym that is a corpus trait, 21 of them a trait with no pair partner.  18 of the rows with evidence also carry M3's `pair_completion_for`, 12 naming one of the same traits.

## Stem families

447 kept rows have a family member ({'candidate': 383, 'queue': 14, 'corpus': 80}; {'affix': 404, 'derivation': 73}); 178 groups of kept rows tie each other.  Largest: corrupt#1, corruptible#1, incorrupt#1, incorruptible#1; disgraceful#1, graceful#1, graceless#1, ungraceful#1; imperfect#1, imperfectible#1, perfect#1, perfectible#1; bear#1, bearable#1, unbearable#1; beast#1, beastly#1, bestial#1.

## Free labels

Roger merged 78 kept rows into a corpus trait in review.  Of the rows with lexical-only pairs, 53 were merged in review (into a trait or another candidate), 23 into a corpus trait, and **2 were merged into the lexically linked trait**: `annoying#1` → [disagreeable](../../traits/instructions/disagreeable.json), `pleasant#1` → [agreeable](../../traits/instructions/agreeable.json).

The gate audit's five retrieval misses:

| candidate | the audit's trait | reached | lexical-only links |
|---|---|---|---|
| `delightful#1` | [agreeable](../../traits/instructions/agreeable.json) | no | - |
| `pleasant#1` | [agreeable](../../traits/instructions/agreeable.json) | **yes** | grateful (oewn similar), agreeable (oewn also) |
| `nice#1` | [agreeable](../../traits/instructions/agreeable.json) | no | squeamish (oewn synonym), fastidious (oewn similar), good (oewn similar), precise (oewn similar) |
| `annoying#1` | [disagreeable](../../traits/instructions/disagreeable.json) | **yes** | disagreeable (oewn similar) |
| `unsteadfast#1` | [submissive](../../traits/instructions/submissive.json) | no | - |

## The sweep's estimate

**$2.92** live (Opus share ASSUMED 0.40-0.62, priced at the higher):

- overlap, Sonnet on every lexical-only pair: 925 x (219, 78) tokens at claude-sonnet-5-5 rates = $1.127
- overlap, Opus on 62% of them (ASSUMED until measured): 574 x (220, 112) tokens at claude-opus-5-5 rates = $1.791

Cap: {'n_cut': 0, 'n_kept_moby': 0, 'cut_cosine': None}

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

