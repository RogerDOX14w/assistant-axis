# Cap pilot readout

Written 2026-10-29T16:42:14+00:00 by `tools/cap_pilot_compare.py` from the plan [plan_max_tokens_pilot.md](plan_max_tokens_pilot.md), the entity list [cap_pilot_entities.json](cap_pilot_entities.json) (seed 20261012, 64 entities) and the trees 256: `roger/cap_pilot/cap256`, 512: `roger/cap_pilot/cap512`, 768: `roger/cap_pilot/cap768`, 1024: `roger/cap_pilot/cap1024`.  Vectors compared at layer 25.

Also read: the repeat 512: `roger/cap_pilot/cap512b`; extra judgings at 512: `roger/cap_pilot/cap512/scores_rejudge`; all-response vectors at 256: `roger/cap_pilot/cap256/vectors_all`; all-response vectors at 512: `roger/cap_pilot/cap512/vectors_all`; all-response vectors at 768: `roger/cap_pilot/cap768/vectors_all`; all-response vectors at 1024: `roger/cap_pilot/cap1024/vectors_all`; prefix means at 1024: `roger/cap_pilot/cap1024/prefix_means`.

## Decision

Rule (fixed in the plan before the pilot): keep 512 if, over the stratum means (roles, traits, combinations), the slot-0 cosine between 512 and 1024 is >= 0.995, the slot-0 norm moves by at most 10% and the score-3 share moves by less than 2 points; otherwise the smallest cap that meets all three.  The outliers are reported, not counted.  Cosines and norms here are **centred** (each cap's vectors minus their mean over the entities of the deciding strata); the raw ones are in the table for comparison.

**Cap: 1024.**  512: misses the rule; 768: misses the rule.

**The floor misses the rule**: 512′ against 512 itself misses combinations: cosine.  No cap can meet a rule its own repeat misses; read the decision on that measure as unmeetable rather than as a reason to raise the cap.

| stratum | cap | n | truncated | score-3 share | Δ score-3 (pts) | mean score | Δ mean | cos slot 0 (centred) | cos slot 0 (raw) | norm slot 0 (centred) | norm (raw) | cos slots 1-7 (centred; selection only) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| roles | 256 | 20 | 88.7% | 91.7% | -0.4 | 2.86 | -0.01 | 0.9796 | 0.99667 | +2.0% | -1.6% | 0.9997 |
| roles | 512 | 20 | 50.4% | 91.9% | -0.3 | 2.86 | -0.01 | 0.9932 | 0.99951 | -0.1% | -0.4% | 0.9998 |
| roles | 768 | 20 | 25.6% | 92.2% | +0.0 | 2.87 | -0.00 | 0.9967 | 0.99988 | -0.2% | -0.0% | 0.9998 |
| roles | 1024 | 20 | 9.2% | 92.2% | +0.0 | 2.87 | +0.00 | 1.0000 | 1.00000 | +0.0% | +0.0% | 1.0000 |
| roles | floor 512′ vs 512 | 20 | 50.7% | 91.7% | -0.2 | 2.86 | -0.00 | 0.9974 | 0.99992 | +0.4% | +0.0% | 0.9997 |
| roles_narrative | 256 | 8 | 94.9% | 89.4% | +0.3 | 2.82 | +0.00 | 0.9668 | 0.99518 | +2.5% | -2.3% | 0.9997 |
| roles_narrative | 512 | 8 | 74.3% | 88.8% | -0.3 | 2.82 | -0.01 | 0.9886 | 0.99912 | +0.7% | -0.9% | 0.9997 |
| roles_narrative | 768 | 8 | 48.9% | 88.2% | -0.8 | 2.81 | -0.02 | 0.9954 | 0.99984 | +0.3% | -0.2% | 0.9997 |
| roles_narrative | 1024 | 8 | 19.3% | 89.1% | +0.0 | 2.82 | +0.00 | 1.0000 | 1.00000 | +0.0% | +0.0% | 1.0000 |
| roles_narrative | floor 512′ vs 512 | 8 | 74.9% | 88.6% | +0.1 | 2.81 | +0.00 | 0.9964 | 0.99992 | +0.4% | +0.1% | 0.9997 |
| traits | 256 | 20 | 73.1% | 77.5% | -2.7 | 2.58 | -0.05 | 0.9821 | 0.99798 | +0.8% | -1.3% | 0.9986 |
| traits | 512 | 20 | 33.2% | 79.4% | -0.9 | 2.61 | -0.02 | 0.9939 | 0.99958 | +0.2% | -0.3% | 0.9988 |
| traits | 768 | 20 | 12.7% | 79.9% | -0.3 | 2.62 | -0.00 | 0.9961 | 0.99976 | -0.2% | -0.1% | 0.9986 |
| traits | 1024 | 20 | 2.9% | 80.3% | +0.0 | 2.62 | +0.00 | 1.0000 | 1.00000 | +0.0% | +0.0% | 1.0000 |
| traits | floor 512′ vs 512 | 20 | 32.9% | 79.1% | -0.3 | 2.60 | -0.01 | 0.9961 | 0.99977 | -0.7% | +0.0% | 0.9990 |
| combinations | 256 | 20 | 73.6% | 52.8% | -10.7 | 2.17 | -0.16 | 0.9716 | 0.99755 | +4.0% | -1.7% | 0.9946 |
| combinations | 512 | 20 | 31.5% | 60.5% | -3.0 | 2.28 | -0.04 | 0.9892 | 0.99942 | +0.8% | -0.5% | 0.9972 |
| combinations | 768 | 20 | 11.3% | 63.2% | -0.3 | 2.32 | -0.01 | 0.9909 | 0.99955 | -0.4% | -0.3% | 0.9968 |
| combinations | 1024 | 20 | 3.5% | 63.5% | +0.0 | 2.33 | +0.00 | 1.0000 | 1.00000 | +0.0% | +0.0% | 1.0000 |
| combinations | floor 512′ vs 512 | 20 | 31.1% | 60.8% | +0.2 | 2.28 | +0.00 | 0.9901 | 0.99950 | -0.4% | -0.0% | 0.9973 |
| traits_outliers | 256 | 2 | 50.0% | 97.3% | -0.5 | 2.97 | -0.00 | 0.9306 | 0.99504 | -3.9% | -2.2% | 0.9999 |
| traits_outliers | 512 | 2 | 48.0% | 97.1% | -0.7 | 2.97 | -0.01 | 0.9825 | 0.99889 | -3.3% | -1.2% | 1.0000 |
| traits_outliers | 768 | 2 | 39.6% | 97.4% | -0.4 | 2.97 | -0.00 | 0.9962 | 0.99966 | -2.2% | -0.4% | 1.0000 |
| traits_outliers | 1024 | 2 | 25.0% | 97.8% | +0.0 | 2.98 | +0.00 | 1.0000 | 1.00000 | +0.0% | +0.0% | 1.0000 |
| traits_outliers | floor 512′ vs 512 | 2 | 48.0% | 96.4% | -0.5 | 2.96 | -0.01 | 0.9982 | 0.99980 | -0.5% | +0.4% | 1.0000 |
| combinations_outliers | 256 | 2 | 50.1% | 77.3% | -2.6 | 2.64 | -0.04 | 0.9475 | 0.99480 | +2.5% | -1.8% | 0.9994 |
| combinations_outliers | 512 | 2 | 48.5% | 78.6% | -1.3 | 2.65 | -0.03 | 0.9824 | 0.99855 | -1.0% | -1.2% | 0.9995 |
| combinations_outliers | 768 | 2 | 33.0% | 81.2% | +1.3 | 2.69 | +0.01 | 0.9955 | 0.99946 | -0.1% | -0.5% | 0.9989 |
| combinations_outliers | 1024 | 2 | 10.8% | 79.9% | +0.0 | 2.68 | +0.00 | 1.0000 | 1.00000 | +0.0% | +0.0% | 1.0000 |
| combinations_outliers | floor 512′ vs 512 | 2 | 48.6% | 80.0% | +1.7 | 2.68 | +0.04 | 0.9967 | 0.99958 | -0.1% | +0.4% | 0.9991 |

Δ columns are cap minus 1024 (the floor rows: the repeat minus its cap, one judging each); norm columns are the relative change of slot 0's norm against 1024 (the floor: against its cap).

## Noise floor (512′ against 512)

σ per entity type: the standard deviation over the type's entities (outliers excluded) of the score-3 share difference, repeat minus its cap, one generation and judging on each side (the total noise; the per-entity rule's unit).  Judge-only: the same over the 512 tree's two judgings of the same responses.

| type | σ total (pts) | 4σ (pts) | judge-only SD (pts) | n judge-only |
|---|---|---|---|---|
| roles | 1.03 | 4.1 | 1.26 | 20 |
| traits | 1.87 | 7.5 | 0.62 | 20 |
| combinations | 1.77 | 7.1 | 0.92 | 20 |

## Run sanity (slots 1-7, same cap, two runs)

Cap 512 against `roger/cap_pilot/cap512b`: 64 entities, min 0.99918, mean 0.99995 (ok).

## Per-entity flags (4σ; reported, not deciding)

Each is to be judged twice more at its cap and at 1024 (the plan § 5) and counts as a systematic change only if the average stays past 4σ.

| entity | type | cap | Δ score-3 (pts) | σ (pts) | Δ/σ | judgings cap / 1024 | averaged |
|---|---|---|---|---|---|---|---|
| r_workaholic__aural_vark | combinations | 256 | -21.8 | 1.77 | -12.3 | 1 / 1 | no |
| t_novelist__existentialist | combinations | 256 | -21.6 | 1.77 | -12.2 | 1 / 1 | no |
| t_programmer__radical | combinations | 256 | -21.0 | 1.77 | -11.8 | 1 / 1 | no |
| r_pacifist__expository | combinations | 256 | -21.0 | 1.77 | -11.8 | 1 / 1 | no |
| r_competitor__aural_vark | combinations | 256 | -18.4 | 1.77 | -10.4 | 1 / 1 | no |
| t_mechanic__iconoclastic | combinations | 256 | -16.4 | 1.77 | -9.2 | 1 / 1 | no |
| t_presenter__ecocentric | combinations | 256 | -15.4 | 1.77 | -8.7 | 1 / 1 | no |
| t_mechanic__greedy | combinations | 256 | -14.2 | 1.77 | -8.0 | 1 / 1 | no |
| r_bodhisattva__narrative | combinations | 256 | -14.0 | 1.77 | -7.9 | 1 / 1 | no |
| motivated_reasoning_immune | traits | 256 | -12.6 | 1.87 | -6.8 | 1 / 1 | no |
| gay_affirming | traits | 256 | -12.4 | 1.87 | -6.6 | 1 / 1 | no |
| r_demon__melodramatic | combinations | 256 | -10.0 | 1.77 | -5.6 | 1 / 1 | no |
| r_parasite__observant | combinations | 256 | -8.8 | 1.77 | -5.0 | 1 / 1 | no |
| t_crystalline__radical | combinations | 256 | -8.0 | 1.77 | -4.5 | 1 / 1 | no |
| t_cyborg__deontological | combinations | 256 | -7.8 | 1.77 | -4.4 | 1 / 1 | no |
| gamer | roles | 256 | -4.4 | 1.03 | -4.3 | 1 / 1 | no |
| financially_secure | traits | 256 | -7.6 | 1.87 | -4.1 | 1 / 1 | no |
| r_competitor__aural_vark | combinations | 512 | -12.7 | 1.77 | -7.2 | 2 / 1 | yes |
| t_programmer__radical | combinations | 512 | -10.5 | 1.77 | -5.9 | 2 / 1 | yes |
| r_pacifist__expository | combinations | 512 | -8.3 | 1.77 | -4.7 | 2 / 1 | yes |
| t_novelist__existentialist | combinations | 512 | -7.2 | 1.77 | -4.1 | 2 / 1 | yes |

## Slot 0 decomposed

**Content alone** (the 1024 tree's prefix means): per entity, over the responses its scores select, the mean of the first-N-token means against the mean of the full means of the same responses (the vector's slot 0); centred on the pilot mean of each, at the layer.  A response shorter than N gives its full mean, so the share of short responses bounds what N can show.

| stratum | N | n | cos (centred) | cos (raw) | norm (centred) | norm (raw) | short of N |
|---|---|---|---|---|---|---|---|
| roles | 256 | 20 | 0.9831 | 0.99679 | +0.9% | -1.5% | 10.3% |
| roles | 512 | 20 | 0.9964 | 0.99961 | -0.3% | -0.4% | 49.6% |
| roles | 768 | 20 | 0.9995 | 0.99996 | +0.0% | -0.1% | 74.5% |
| roles_narrative | 256 | 8 | 0.9699 | 0.99528 | +0.3% | -2.2% | 3.8% |
| roles_narrative | 512 | 8 | 0.9925 | 0.99919 | -0.1% | -0.7% | 23.3% |
| roles_narrative | 768 | 8 | 0.9988 | 0.99990 | +0.1% | -0.2% | 48.5% |
| traits | 256 | 20 | 0.9867 | 0.99824 | -0.4% | -1.1% | 29.0% |
| traits | 512 | 20 | 0.9979 | 0.99983 | -0.4% | -0.2% | 69.1% |
| traits | 768 | 20 | 0.9998 | 0.99999 | -0.1% | -0.0% | 87.3% |
| combinations | 256 | 20 | 0.9836 | 0.99801 | +0.9% | -1.1% | 25.4% |
| combinations | 512 | 20 | 0.9980 | 0.99986 | -0.4% | -0.2% | 69.4% |
| combinations | 768 | 20 | 0.9999 | 0.99999 | -0.1% | -0.0% | 90.1% |
| traits_outliers | 256 | 2 | 0.9299 | 0.99527 | -3.3% | -2.3% | 50.0% |
| traits_outliers | 512 | 2 | 0.9833 | 0.99910 | -2.6% | -1.1% | 51.5% |
| traits_outliers | 768 | 2 | 0.9977 | 0.99988 | -1.0% | -0.4% | 59.3% |
| combinations_outliers | 256 | 2 | 0.9493 | 0.99506 | +3.3% | -1.6% | 50.0% |
| combinations_outliers | 512 | 2 | 0.9857 | 0.99900 | -1.0% | -0.7% | 51.7% |
| combinations_outliers | 768 | 2 | 0.9985 | 0.99990 | -1.0% | -0.2% | 65.8% |

**Selection alone** (step 4's `--all_responses` vectors): the judge-selected vector against the mean over every response of the same tree, centred alike; norm = selected over all, minus 1.  Slots 1-7 move by selection only at every cap; the score-3 share in the first table is the same effect from the judge's side.

| stratum | cap | n | cos slot 0 (centred) | cos slot 0 (raw) | norm slot 0 (centred) | cos slots 1-7 (centred) | cos slots 1-7 (raw) |
|---|---|---|---|---|---|---|---|
| roles | 256 | 20 | 0.9930 | 0.99981 | +4.8% | 0.9976 | 0.99996 |
| roles | 512 | 20 | 0.9928 | 0.99981 | +4.0% | 0.9979 | 0.99996 |
| roles | 768 | 20 | 0.9943 | 0.99987 | +3.6% | 0.9981 | 0.99996 |
| roles | 1024 | 20 | 0.9939 | 0.99984 | +3.8% | 0.9981 | 0.99997 |
| roles_narrative | 256 | 8 | 0.9921 | 0.99983 | +10.0% | 0.9972 | 0.99996 |
| roles_narrative | 512 | 8 | 0.9908 | 0.99981 | +9.1% | 0.9972 | 0.99995 |
| roles_narrative | 768 | 8 | 0.9939 | 0.99988 | +8.3% | 0.9975 | 0.99995 |
| roles_narrative | 1024 | 8 | 0.9929 | 0.99986 | +8.2% | 0.9975 | 0.99995 |
| traits | 256 | 20 | 0.9629 | 0.99694 | +15.3% | 0.9869 | 0.99972 |
| traits | 512 | 20 | 0.9692 | 0.99728 | +14.2% | 0.9883 | 0.99975 |
| traits | 768 | 20 | 0.9704 | 0.99751 | +13.1% | 0.9880 | 0.99975 |
| traits | 1024 | 20 | 0.9724 | 0.99749 | +13.3% | 0.9888 | 0.99977 |
| combinations | 256 | 20 | 0.9399 | 0.99620 | +15.5% | 0.9800 | 0.99944 |
| combinations | 512 | 20 | 0.9505 | 0.99692 | +13.5% | 0.9821 | 0.99954 |
| combinations | 768 | 20 | 0.9494 | 0.99713 | +12.3% | 0.9835 | 0.99955 |
| combinations | 1024 | 20 | 0.9582 | 0.99726 | +12.4% | 0.9834 | 0.99956 |
| traits_outliers | 256 | 2 | 0.9948 | 0.99996 | +4.4% | 0.9992 | 0.99999 |
| traits_outliers | 512 | 2 | 0.9962 | 0.99992 | +5.1% | 0.9993 | 0.99999 |
| traits_outliers | 768 | 2 | 0.9974 | 0.99995 | +4.6% | 0.9995 | 1.00000 |
| traits_outliers | 1024 | 2 | 0.9977 | 0.99996 | +4.4% | 0.9995 | 1.00000 |
| combinations_outliers | 256 | 2 | 0.9801 | 0.99754 | +0.2% | 0.9968 | 0.99985 |
| combinations_outliers | 512 | 2 | 0.9787 | 0.99717 | +1.0% | 0.9966 | 0.99983 |
| combinations_outliers | 768 | 2 | 0.9859 | 0.99814 | +1.3% | 0.9972 | 0.99987 |
| combinations_outliers | 1024 | 2 | 0.9809 | 0.99745 | +0.3% | 0.9964 | 0.99982 |

## The outliers, one by one

| entity | cap | truncated | score-3 share | judgings | Δ score-3 (pts) | cos slot 0 (centred) | norm slot 0 (centred) |
|---|---|---|---|---|---|---|---|
| verbose | 256 | 100.0% | 96.2% | 1 | -1.0 | 0.8735 | -2.0% |
| verbose | 512 | 96.0% | 96.9% | 2 | -0.3 | 0.9676 | -3.5% |
| verbose | 768 | 79.2% | 97.0% | 1 | -0.2 | 0.9947 | -1.9% |
| verbose | 1024 | 50.0% | 97.2% | 1 | +0.0 | 1.0000 | +0.0% |
| concise | 256 | 0.0% | 98.4% | 1 | +0.0 | 0.9877 | -5.8% |
| concise | 512 | 0.0% | 97.3% | 2 | -1.1 | 0.9974 | -3.2% |
| concise | 768 | 0.0% | 97.8% | 1 | -0.6 | 0.9978 | -2.6% |
| concise | 1024 | 0.0% | 98.4% | 1 | +0.0 | 1.0000 | +0.0% |
| r_angel__verbose | 256 | 100.0% | 96.2% | 1 | -3.6 | 0.9135 | +9.8% |
| r_angel__verbose | 512 | 97.0% | 99.3% | 2 | -0.5 | 0.9718 | -1.4% |
| r_angel__verbose | 768 | 66.0% | 99.8% | 1 | +0.0 | 0.9965 | -2.1% |
| r_angel__verbose | 1024 | 21.6% | 99.8% | 1 | +0.0 | 1.0000 | +0.0% |
| r_angel__concise | 256 | 0.2% | 58.4% | 1 | -1.6 | 0.9815 | -4.9% |
| r_angel__concise | 512 | 0.0% | 57.9% | 2 | -2.1 | 0.9929 | -0.5% |
| r_angel__concise | 768 | 0.0% | 62.6% | 1 | +2.6 | 0.9945 | +1.9% |
| r_angel__concise | 1024 | 0.0% | 60.0% | 1 | +0.0 | 1.0000 | +0.0% |

## Pair axes (slot 0, layer 25, cosine with the 1024 axis)

| pair | 256 | 512 | 768 | 1024 |
|---|---|---|---|---|
| verbose / concise | 0.9505 | 0.9900 | 0.9976 | 1.0000 |

## Score-3 share per entity, lowest first

Per entity type, sorted by the score-3 share at 1024: the share at each cap (the mean over its judgings where a cap has more than one) and the paired change, cap minus 1024, in points.  *(outlier)*: not in a deciding stratum.

**Roles**

| entity | 256 | 512 | 768 | 1024 | Δ 256 | Δ 512 | Δ 768 |
|---|---|---|---|---|---|---|---|
| [reviewer](../../data/roles/instructions/reviewer.json) | 56.0% | 56.7% | 53.2% | 55.2% | +0.8 | +1.5 | -2.0 |
| [aberration](../../data/roles/instructions/aberration.json) | 85.4% | 82.9% | 86.0% | 83.4% | +2.0 | -0.5 | +2.6 |
| [athlete](../../data/roles/instructions/athlete.json) | 85.2% | 84.2% | 86.2% | 86.0% | -0.8 | -1.8 | +0.2 |
| [auditor](../../data/roles/instructions/auditor.json) | 88.0% | 85.2% | 87.2% | 86.6% | +1.4 | -1.4 | +0.6 |
| [editor](../../data/roles/instructions/editor.json) | 87.6% | 86.9% | 87.0% | 87.0% | +0.6 | -0.1 | +0.0 |
| [artist](../../data/roles/instructions/artist.json) | 87.0% | 89.4% | 90.2% | 90.2% | -3.2 | -0.8 | +0.0 |
| [historian](../../data/roles/instructions/historian.json) | 93.0% | 91.3% | 91.6% | 91.2% | +1.8 | +0.1 | +0.4 |
| [geographer](../../data/roles/instructions/geographer.json) | 92.4% | 94.2% | 93.4% | 93.8% | -1.4 | +0.4 | -0.4 |
| [scholar](../../data/roles/instructions/scholar.json) | 96.6% | 95.3% | 93.8% | 95.6% | +1.0 | -0.3 | -1.8 |
| [biologist](../../data/roles/instructions/biologist.json) | 94.2% | 94.2% | 94.0% | 95.6% | -1.4 | -1.4 | -1.6 |
| [anthropologist](../../data/roles/instructions/anthropologist.json) | 96.8% | 96.6% | 96.0% | 96.6% | +0.2 | +0.0 | -0.6 |
| [bohemian](../../data/roles/instructions/bohemian.json) | 95.6% | 96.6% | 98.0% | 96.8% | -1.2 | -0.2 | +1.2 |
| [actor](../../data/roles/instructions/actor.json) | 97.8% | 98.2% | 98.2% | 97.0% | +0.8 | +1.2 | +1.2 |
| [gamer](../../data/roles/instructions/gamer.json) | 92.6% | 95.7% | 97.6% | 97.0% | -4.4 | -1.3 | +0.6 |
| [peasant](../../data/roles/instructions/peasant.json) | 96.2% | 98.0% | 98.0% | 97.6% | -1.4 | +0.4 | +0.4 |
| [sociologist](../../data/roles/instructions/sociologist.json) | 98.0% | 96.7% | 96.8% | 98.0% | +0.0 | -1.3 | -1.2 |
| [surfer](../../data/roles/instructions/surfer.json) | 97.0% | 98.5% | 98.2% | 98.2% | -1.2 | +0.3 | +0.0 |
| [gossip](../../data/roles/instructions/gossip.json) | 99.2% | 98.8% | 99.2% | 99.0% | +0.2 | -0.2 | +0.2 |
| [trickster](../../data/roles/instructions/trickster.json) | 96.8% | 99.1% | 99.6% | 99.2% | -2.4 | -0.1 | +0.4 |
| [pirate](../../data/roles/instructions/pirate.json) | 99.4% | 99.7% | 100.0% | 99.4% | +0.0 | +0.3 | +0.6 |

**Traits**

| entity | 256 | 512 | 768 | 1024 | Δ 256 | Δ 512 | Δ 768 |
|---|---|---|---|---|---|---|---|
| [neglectful](../../data/traits/instructions/neglectful.json) | 33.2% | 33.0% | 30.4% | 31.0% | +2.2 | +2.0 | -0.6 |
| [financially_secure](../../data/traits/instructions/financially_secure.json) | 25.6% | 30.1% | 31.4% | 33.2% | -7.6 | -3.1 | -1.8 |
| [gay_affirming](../../data/traits/instructions/gay_affirming.json) | 29.8% | 36.3% | 39.2% | 42.2% | -12.4 | -5.9 | -3.0 |
| [unhappily_partnered](../../data/traits/instructions/unhappily_partnered.json) | 51.8% | 56.9% | 54.0% | 58.0% | -6.2 | -1.1 | -4.0 |
| [ethnocentric](../../data/traits/instructions/ethnocentric.json) | 60.8% | 62.6% | 63.0% | 62.6% | -1.8 | +0.0 | +0.4 |
| [psychopathic_dark_tetrad](../../data/traits/instructions/psychopathic_dark_tetrad.json) | 73.8% | 77.3% | 78.8% | 77.0% | -3.2 | +0.3 | +1.8 |
| [motivated_reasoning_immune](../../data/traits/instructions/motivated_reasoning_immune.json) | 70.0% | 75.3% | 77.6% | 82.6% | -12.6 | -7.3 | -5.0 |
| [neurotic_big_five](../../data/traits/instructions/neurotic_big_five.json) | 80.4% | 80.8% | 79.8% | 82.8% | -2.4 | -2.0 | -3.0 |
| [bold](../../data/traits/instructions/bold.json) | 81.4% | 85.7% | 86.4% | 84.4% | -3.0 | +1.3 | +2.0 |
| [sentimental](../../data/traits/instructions/sentimental.json) | 88.8% | 87.5% | 90.8% | 90.2% | -1.4 | -2.7 | +0.6 |
| [visual_vark](../../data/traits/instructions/visual_vark.json) | 89.6% | 92.8% | 94.0% | 93.2% | -3.6 | -0.4 | +0.8 |
| [clear](../../data/traits/instructions/clear.json) | 93.6% | 94.2% | 93.6% | 94.2% | -0.6 | +0.0 | -0.6 |
| [elitist](../../data/traits/instructions/elitist.json) | 94.2% | 95.2% | 95.8% | 94.6% | -0.4 | +0.6 | +1.2 |
| [well_behaved](../../data/traits/instructions/well_behaved.json) | 94.8% | 94.7% | 96.0% | 94.6% | +0.2 | +0.1 | +1.4 |
| [witty](../../data/traits/instructions/witty.json) | 96.4% | 95.9% | 96.6% | 96.2% | +0.2 | -0.3 | +0.4 |
| [challenging](../../data/traits/instructions/challenging.json) | 95.6% | 96.2% | 97.6% | 96.4% | -0.8 | -0.2 | +1.2 |
| [blood_type_a](../../data/traits/instructions/blood_type_a.json) | 97.0% | 97.5% | 97.6% | 97.0% | +0.0 | +0.5 | +0.6 |
| [verbose](../../data/traits/instructions/verbose.json) *(outlier)* | 96.2% | 96.9% | 97.0% | 97.2% | -1.0 | -0.3 | -0.2 |
| [moderate](../../data/traits/instructions/moderate.json) | 98.0% | 97.9% | 98.6% | 98.0% | +0.0 | -0.1 | +0.6 |
| [pensive](../../data/traits/instructions/pensive.json) | 97.6% | 98.1% | 98.4% | 98.4% | -0.8 | -0.3 | +0.0 |
| [concise](../../data/traits/instructions/concise.json) *(outlier)* | 98.4% | 97.3% | 97.8% | 98.4% | +0.0 | -1.1 | -0.6 |
| [infp_mbti](../../data/traits/instructions/infp_mbti.json) | 98.4% | 99.2% | 99.0% | 99.0% | -0.6 | +0.2 | +0.0 |

**Combinations**

| entity | 256 | 512 | 768 | 1024 | Δ 256 | Δ 512 | Δ 768 |
|---|---|---|---|---|---|---|---|
| r_[daredevil](../../data/roles/instructions/daredevil.json)__[expository](../../data/traits/instructions/expository.json) | 7.0% | 8.8% | 9.0% | 8.2% | -1.2 | +0.6 | +0.8 |
| r_[competitor](../../data/roles/instructions/competitor.json)__[unassuming](../../data/traits/instructions/unassuming.json) | 20.2% | 18.0% | 19.4% | 15.6% | +4.6 | +2.4 | +3.8 |
| r_[workaholic](../../data/roles/instructions/workaholic.json)__[unassuming](../../data/traits/instructions/unassuming.json) | 40.0% | 37.1% | 41.0% | 37.8% | +2.2 | -0.7 | +3.2 |
| t_[mechanic](../../data/roles/instructions/mechanic.json)__[greedy](../../data/traits/instructions/greedy.json) | 34.6% | 48.3% | 52.4% | 48.8% | -14.2 | -0.5 | +3.6 |
| t_[cartographer](../../data/roles/instructions/cartographer.json)__[amoral](../../data/traits/instructions/amoral.json) | 43.2% | 50.1% | 50.8% | 49.2% | -6.0 | +0.9 | +1.6 |
| t_[cyborg](../../data/roles/instructions/cyborg.json)__[deontological](../../data/traits/instructions/deontological.json) | 42.6% | 47.2% | 52.2% | 50.4% | -7.8 | -3.2 | +1.8 |
| r_[competitor](../../data/roles/instructions/competitor.json)__[aural_vark](../../data/traits/instructions/aural_vark.json) | 33.6% | 39.3% | 45.6% | 52.0% | -18.4 | -12.7 | -6.4 |
| r_[vampire](../../data/roles/instructions/vampire.json)__[casual](../../data/traits/instructions/casual.json) | 54.6% | 60.1% | 58.0% | 57.8% | -3.2 | +2.3 | +0.2 |
| r_[angel](../../data/roles/instructions/angel.json)__[concise](../../data/traits/instructions/concise.json) *(outlier)* | 58.4% | 57.9% | 62.6% | 60.0% | -1.6 | -2.1 | +2.6 |
| t_[programmer](../../data/roles/instructions/programmer.json)__[radical](../../data/traits/instructions/radical.json) | 42.4% | 52.9% | 59.4% | 63.4% | -21.0 | -10.5 | -4.0 |
| t_[driver](../../data/roles/instructions/driver.json)__[deontological](../../data/traits/instructions/deontological.json) | 61.0% | 65.0% | 68.6% | 66.8% | -5.8 | -1.8 | +1.8 |
| r_[parasite](../../data/roles/instructions/parasite.json)__[observant](../../data/traits/instructions/observant.json) | 59.6% | 68.6% | 68.0% | 68.4% | -8.8 | +0.2 | -0.4 |
| r_[pacifist](../../data/roles/instructions/pacifist.json)__[expository](../../data/traits/instructions/expository.json) | 49.6% | 62.3% | 66.6% | 70.6% | -21.0 | -8.3 | -4.0 |
| r_[workaholic](../../data/roles/instructions/workaholic.json)__[aural_vark](../../data/traits/instructions/aural_vark.json) | 48.8% | 65.8% | 70.8% | 70.6% | -21.8 | -4.8 | +0.2 |
| t_[mechanic](../../data/roles/instructions/mechanic.json)__[iconoclastic](../../data/traits/instructions/iconoclastic.json) | 61.4% | 71.2% | 73.6% | 77.8% | -16.4 | -6.6 | -4.2 |
| t_[crystalline](../../data/roles/instructions/crystalline.json)__[radical](../../data/traits/instructions/radical.json) | 73.4% | 80.3% | 81.0% | 81.4% | -8.0 | -1.1 | -0.4 |
| r_[demon](../../data/roles/instructions/demon.json)__[melodramatic](../../data/traits/instructions/melodramatic.json) | 74.0% | 84.3% | 85.2% | 84.0% | -10.0 | +0.3 | +1.2 |
| t_[novelist](../../data/roles/instructions/novelist.json)__[existentialist](../../data/traits/instructions/existentialist.json) | 62.8% | 77.2% | 82.0% | 84.4% | -21.6 | -7.2 | -2.4 |
| t_[presenter](../../data/roles/instructions/presenter.json)__[ecocentric](../../data/traits/instructions/ecocentric.json) | 71.0% | 81.2% | 85.2% | 86.4% | -15.4 | -5.2 | -1.2 |
| t_[curator](../../data/roles/instructions/curator.json)__[humanitarian](../../data/traits/instructions/humanitarian.json) | 90.8% | 94.8% | 97.6% | 97.8% | -7.0 | -3.0 | -0.2 |
| r_[bodhisattva](../../data/roles/instructions/bodhisattva.json)__[narrative](../../data/traits/instructions/narrative.json) | 84.4% | 96.8% | 98.2% | 98.4% | -14.0 | -1.6 | -0.2 |
| r_[angel](../../data/roles/instructions/angel.json)__[verbose](../../data/traits/instructions/verbose.json) *(outlier)* | 96.2% | 99.3% | 99.8% | 99.8% | -3.6 | -0.5 | +0.0 |

## Per entity

Columns per cap in the order 256 / 512 / 768 (against 1024); judgings in the order 256 / 512 / 768 / 1024; the floor columns are the repeat against its cap.

| entity | stratum | judgings | Δ score-3 (pts) | cos slot 0 (centred) | norm slot 0 (centred) | floor Δ score-3 | floor cos slot 0 | floor norm |
|---|---|---|---|---|---|---|---|---|
| sociologist | roles_narrative | 1 / 2 / 1 / 1 | +0.0 / -1.3 / -1.2 | 0.9652 / 0.9892 / 0.9971 | +1.3% / +1.0% / +0.2% | -0.2 | 0.9991 | +0.3% |
| anthropologist | roles_narrative | 1 / 2 / 1 / 1 | +0.2 / +0.0 / -0.6 | 0.9690 / 0.9909 / 0.9980 | +3.8% / +0.7% / +0.7% | +0.0 | 0.9991 | +0.5% |
| geographer | roles_narrative | 1 / 2 / 1 / 1 | -1.4 / +0.4 / -0.4 | 0.9840 / 0.9958 / 0.9990 | +4.9% / +0.9% / +1.7% | -1.6 | 0.9992 | +1.7% |
| reviewer | roles_narrative | 1 / 2 / 1 / 1 | +0.8 / +1.5 / -2.0 | 0.9426 / 0.9683 / 0.9775 | +7.5% / +0.7% / -0.6% | +1.8 | 0.9779 | +0.4% |
| scholar | roles_narrative | 1 / 2 / 1 / 1 | +1.0 / -0.3 / -1.8 | 0.9479 / 0.9849 / 0.9970 | -2.5% / -1.7% / -0.2% | -0.4 | 0.9991 | -0.4% |
| historian | roles_narrative | 1 / 2 / 1 / 1 | +1.8 / +0.1 / +0.4 | 0.9607 / 0.9886 / 0.9971 | +4.0% / +2.9% / +1.5% | +0.2 | 0.9990 | +0.9% |
| biologist | roles_narrative | 1 / 2 / 1 / 1 | -1.4 / -1.4 / -1.6 | 0.9798 / 0.9949 / 0.9987 | +4.7% / +2.1% / +1.3% | +0.4 | 0.9990 | +0.8% |
| auditor | roles_narrative | 1 / 2 / 1 / 1 | +1.4 / -1.4 / +0.6 | 0.9850 / 0.9961 / 0.9989 | -3.4% / -0.6% / -2.1% | +0.6 | 0.9990 | -0.9% |
| aberration | roles | 1 / 2 / 1 / 1 | +2.0 / -0.5 / +2.6 | 0.9895 / 0.9977 / 0.9982 | -2.4% / -3.1% / -2.9% | -2.2 | 0.9991 | +3.9% |
| actor | roles | 1 / 2 / 1 / 1 | +0.8 / +1.2 / +1.2 | 0.9849 / 0.9963 / 0.9988 | -0.7% / -1.2% / -0.8% | -0.2 | 0.9996 | +0.3% |
| artist | roles | 1 / 2 / 1 / 1 | -3.2 / -0.8 / +0.0 | 0.9861 / 0.9948 / 0.9947 | +2.4% / -0.4% / -1.0% | +1.4 | 0.9965 | +0.6% |
| athlete | roles | 1 / 2 / 1 / 1 | -0.8 / -1.8 / +0.2 | 0.9842 / 0.9944 / 0.9959 | +5.3% / +1.7% / -0.9% | -1.4 | 0.9961 | +1.6% |
| bohemian | roles | 1 / 2 / 1 / 1 | -1.2 / -0.2 / +1.2 | 0.9776 / 0.9959 / 0.9970 | +1.3% / -2.7% / +1.2% | -0.4 | 0.9970 | +1.5% |
| editor | roles | 1 / 2 / 1 / 1 | +0.6 / -0.1 / +0.0 | 0.9906 / 0.9944 / 0.9954 | +6.5% / +4.4% / +1.1% | +1.2 | 0.9957 | -2.9% |
| gamer | roles | 1 / 2 / 1 / 1 | -4.4 / -1.3 / +0.6 | 0.9797 / 0.9920 / 0.9975 | +1.8% / -0.3% / -0.4% | +0.0 | 0.9980 | -0.1% |
| gossip | roles | 1 / 2 / 1 / 1 | +0.2 / -0.2 / +0.2 | 0.9950 / 0.9988 / 0.9992 | +0.6% / -1.8% / -0.9% | +0.6 | 0.9989 | +0.7% |
| peasant | roles | 1 / 2 / 1 / 1 | -1.4 / +0.4 / +0.4 | 0.9911 / 0.9971 / 0.9987 | +1.0% / -0.8% / -0.2% | -0.8 | 0.9988 | +0.2% |
| pirate | roles | 1 / 2 / 1 / 1 | +0.0 / +0.3 / +0.6 | 0.9919 / 0.9981 / 0.9990 | +1.1% / -1.7% / -1.4% | -0.2 | 0.9992 | +0.4% |
| surfer | roles | 1 / 2 / 1 / 1 | -1.2 / +0.3 / +0.0 | 0.9939 / 0.9967 / 0.9978 | +2.2% / -1.4% / -0.5% | -0.6 | 0.9982 | -0.5% |
| trickster | roles | 1 / 2 / 1 / 1 | -2.4 / -0.1 / +0.4 | 0.9926 / 0.9985 / 0.9989 | -0.4% / -1.4% / -0.2% | -1.6 | 0.9989 | -0.4% |
| blood_type_a | traits | 1 / 2 / 1 / 1 | +0.0 / +0.5 / +0.6 | 0.9815 / 0.9938 / 0.9965 | -0.5% / -1.2% / -3.9% | +0.8 | 0.9955 | -2.8% |
| bold | traits | 1 / 2 / 1 / 1 | -3.0 / +1.3 / +2.0 | 0.9854 / 0.9938 / 0.9938 | +3.9% / +0.9% / -1.3% | +1.2 | 0.9934 | -4.7% |
| challenging | traits | 1 / 2 / 1 / 1 | -0.8 / -0.2 / +1.2 | 0.9551 / 0.9895 / 0.9976 | +6.5% / +1.6% / +0.8% | +0.4 | 0.9981 | -1.4% |
| clear | traits | 1 / 2 / 1 / 1 | -0.6 / +0.0 / -0.6 | 0.9676 / 0.9937 / 0.9963 | -3.7% / -0.1% / -1.2% | -0.2 | 0.9960 | -1.2% |
| elitist | traits | 1 / 2 / 1 / 1 | -0.4 / +0.6 / +1.2 | 0.9931 / 0.9971 / 0.9985 | +0.1% / +0.0% / -0.8% | -0.4 | 0.9986 | -1.1% |
| ethnocentric | traits | 1 / 2 / 1 / 1 | -1.8 / +0.0 / +0.4 | 0.9859 / 0.9960 / 0.9975 | -0.3% / -1.4% / -2.5% | -1.8 | 0.9973 | +0.5% |
| financially_secure | traits | 1 / 2 / 1 / 1 | -7.6 / -3.1 / -1.8 | 0.9774 / 0.9858 / 0.9850 | +9.5% / +7.5% / +5.2% | -3.4 | 0.9889 | +0.3% |
| gay_affirming | traits | 1 / 2 / 1 / 1 | -12.4 / -5.9 / -3.0 | 0.9795 / 0.9923 / 0.9944 | +10.3% / +1.7% / +1.6% | +0.0 | 0.9923 | +1.0% |
| infp_mbti | traits | 1 / 2 / 1 / 1 | -0.6 / +0.2 / +0.0 | 0.9806 / 0.9925 / 0.9973 | -3.5% / -3.5% / -2.1% | +0.2 | 0.9955 | +0.4% |
| moderate | traits | 1 / 2 / 1 / 1 | +0.0 / -0.1 / +0.6 | 0.9892 / 0.9969 / 0.9988 | +2.2% / -1.7% / +1.0% | +0.8 | 0.9979 | +3.0% |
| motivated_reasoning_immune | traits | 1 / 2 / 1 / 1 | -12.6 / -7.3 / -5.0 | 0.9692 / 0.9909 / 0.9970 | +0.3% / +0.3% / +1.6% | -2.6 | 0.9977 | +1.0% |
| neglectful | traits | 1 / 2 / 1 / 1 | +2.2 / +2.0 / -0.6 | 0.9725 / 0.9854 / 0.9873 | -6.1% / -2.1% / -5.0% | -0.2 | 0.9891 | -4.6% |
| neurotic_big_five | traits | 1 / 2 / 1 / 1 | -2.4 / -2.0 / -3.0 | 0.9922 / 0.9972 / 0.9984 | +0.9% / -1.8% / +0.7% | +2.6 | 0.9983 | +0.2% |
| pensive | traits | 1 / 2 / 1 / 1 | -0.8 / -0.3 / +0.0 | 0.9854 / 0.9964 / 0.9984 | -5.2% / -1.2% / -0.0% | -1.0 | 0.9984 | +0.7% |
| psychopathic_dark_tetrad | traits | 1 / 2 / 1 / 1 | -3.2 / +0.3 / +1.8 | 0.9868 / 0.9962 / 0.9980 | -1.4% / -0.2% / +0.6% | -0.6 | 0.9981 | -1.2% |
| sentimental | traits | 1 / 2 / 1 / 1 | -1.4 / -2.7 / +0.6 | 0.9885 / 0.9967 / 0.9981 | -1.0% / -0.3% / -2.6% | +3.4 | 0.9975 | -0.5% |
| unhappily_partnered | traits | 1 / 2 / 1 / 1 | -6.2 / -1.1 / -4.0 | 0.9908 / 0.9941 / 0.9946 | +0.4% / +3.6% / +3.3% | -4.4 | 0.9954 | -1.0% |
| visual_vark | traits | 1 / 2 / 1 / 1 | -3.6 / -0.4 / +0.8 | 0.9757 / 0.9944 / 0.9985 | +4.7% / +2.3% / +1.0% | -0.8 | 0.9988 | -2.8% |
| well_behaved | traits | 1 / 2 / 1 / 1 | +0.2 / +0.1 / +1.4 | 0.9936 / 0.9976 / 0.9982 | +2.1% / -0.5% / +0.6% | -1.2 | 0.9978 | +1.2% |
| witty | traits | 1 / 2 / 1 / 1 | +0.2 / -0.3 / +0.4 | 0.9928 / 0.9976 / 0.9985 | -2.5% / -0.8% / -0.4% | +1.4 | 0.9981 | -1.3% |
| verbose | traits_outliers | 1 / 2 / 1 / 1 | -1.0 / -0.3 / -0.2 | 0.8735 / 0.9676 / 0.9947 | -2.0% / -3.5% / -1.9% | -0.8 | 0.9988 | -0.6% |
| concise | traits_outliers | 1 / 2 / 1 / 1 | +0.0 / -1.1 / -0.6 | 0.9877 / 0.9974 / 0.9978 | -5.8% / -3.2% / -2.6% | -0.2 | 0.9977 | -0.4% |
| r_bodhisattva__narrative | combinations | 1 / 2 / 1 / 1 | -14.0 / -1.6 / -0.2 | 0.9491 / 0.9948 / 0.9987 | +14.9% / +2.2% / +0.3% | +0.0 | 0.9985 | -0.8% |
| r_competitor__aural_vark | combinations | 1 / 2 / 1 / 1 | -18.4 / -12.7 / -6.4 | 0.9297 / 0.9633 / 0.9776 | +15.5% / +8.5% / +3.6% | +2.4 | 0.9715 | -7.3% |
| r_competitor__unassuming | combinations | 1 / 2 / 1 / 1 | +4.6 / +2.4 / +3.8 | 0.9495 / 0.9659 / 0.9680 | -10.0% / +1.3% / -4.2% | +0.2 | 0.9642 | -5.1% |
| r_daredevil__expository | combinations | 1 / 2 / 1 / 1 | -1.2 / +0.6 / +0.8 | 0.9266 / 0.9691 / 0.9516 | +4.6% / +0.9% / -1.1% | -0.4 | 0.9460 | +1.6% |
| r_demon__melodramatic | combinations | 1 / 2 / 1 / 1 | -10.0 / +0.3 / +1.2 | 0.9918 / 0.9985 / 0.9996 | +1.5% / +0.3% / -0.2% | -1.6 | 0.9992 | -0.2% |
| r_pacifist__expository | combinations | 1 / 2 / 1 / 1 | -21.0 / -8.3 / -4.0 | 0.9785 / 0.9954 / 0.9972 | -2.2% / -1.5% / -1.9% | +0.6 | 0.9971 | -1.1% |
| r_parasite__observant | combinations | 1 / 2 / 1 / 1 | -8.8 / +0.2 / -0.4 | 0.9874 / 0.9938 / 0.9949 | +4.2% / -0.9% / +1.9% | -2.4 | 0.9953 | +1.5% |
| r_vampire__casual | combinations | 1 / 2 / 1 / 1 | -3.2 / +2.3 / +0.2 | 0.9896 / 0.9962 / 0.9973 | -2.0% / -0.5% / -0.4% | -2.4 | 0.9974 | -0.8% |
| r_workaholic__aural_vark | combinations | 1 / 2 / 1 / 1 | -21.8 / -4.8 / +0.2 | 0.9709 / 0.9909 / 0.9928 | +15.3% / +1.3% / -2.8% | +2.2 | 0.9924 | -0.2% |
| r_workaholic__unassuming | combinations | 1 / 2 / 1 / 1 | +2.2 / -0.7 / +3.2 | 0.9678 / 0.9877 / 0.9892 | -4.4% / -2.1% / -3.3% | +1.6 | 0.9909 | +2.9% |
| t_cartographer__amoral | combinations | 1 / 2 / 1 / 1 | -6.0 / +0.9 / +1.6 | 0.9746 / 0.9873 / 0.9920 | +3.8% / -1.8% / -2.4% | -1.8 | 0.9913 | +2.0% |
| t_crystalline__radical | combinations | 1 / 2 / 1 / 1 | -8.0 / -1.1 / -0.4 | 0.9924 / 0.9978 / 0.9985 | +1.0% / -0.1% / -1.5% | +1.0 | 0.9984 | -0.3% |
| t_curator__humanitarian | combinations | 1 / 2 / 1 / 1 | -7.0 / -3.0 / -0.2 | 0.9821 / 0.9949 / 0.9971 | +2.5% / -0.3% / +0.2% | +0.0 | 0.9971 | +0.2% |
| t_cyborg__deontological | combinations | 1 / 2 / 1 / 1 | -7.8 / -3.2 / +1.8 | 0.9808 / 0.9902 / 0.9904 | +4.3% / -1.4% / -2.4% | +3.8 | 0.9913 | +1.5% |
| t_driver__deontological | combinations | 1 / 2 / 1 / 1 | -5.8 / -1.8 / +1.8 | 0.9820 / 0.9951 / 0.9970 | +2.0% / -0.2% / +0.4% | +1.6 | 0.9959 | +1.1% |
| t_mechanic__greedy | combinations | 1 / 2 / 1 / 1 | -14.2 / -0.5 / +3.6 | 0.9858 / 0.9951 / 0.9959 | +5.5% / +0.6% / -1.9% | -2.8 | 0.9955 | -3.0% |
| t_mechanic__iconoclastic | combinations | 1 / 2 / 1 / 1 | -16.4 / -6.6 / -4.2 | 0.9849 / 0.9916 / 0.9945 | +10.8% / +6.6% / +5.6% | +0.8 | 0.9955 | -0.0% |
| t_novelist__existentialist | combinations | 1 / 2 / 1 / 1 | -21.6 / -7.2 / -2.4 | 0.9700 / 0.9920 / 0.9947 | +7.1% / +2.8% / +3.4% | +1.6 | 0.9951 | +0.5% |
| t_presenter__ecocentric | combinations | 1 / 2 / 1 / 1 | -15.4 / -5.2 / -1.2 | 0.9762 / 0.9950 / 0.9978 | +3.0% / -0.0% / +0.2% | -0.2 | 0.9961 | -0.0% |
| t_programmer__radical | combinations | 1 / 2 / 1 / 1 | -21.0 / -10.5 / -4.0 | 0.9628 / 0.9896 / 0.9928 | +3.5% / +0.5% / -1.4% | -0.6 | 0.9924 | -1.0% |
| r_angel__verbose | combinations_outliers | 1 / 2 / 1 / 1 | -3.6 / -0.5 / +0.0 | 0.9135 / 0.9718 / 0.9965 | +9.8% / -1.4% / -2.1% | -0.6 | 0.9991 | +0.4% |
| r_angel__concise | combinations_outliers | 1 / 2 / 1 / 1 | -1.6 / -2.1 / +2.6 | 0.9815 / 0.9929 / 0.9945 | -4.9% / -0.5% / +1.9% | +4.0 | 0.9942 | -0.5% |

Everything above, per entity and per stratum: the `.json` beside this readout.
