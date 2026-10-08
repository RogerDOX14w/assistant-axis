# Roget harvest: run 2026-10-08-pilot

Config: `{"per_head_cap": 10, "pair_top": 3, "max_words": 2, "classes": ["pair_completion", "pair_empty", "singleton_empty", "queued_only"], "every_nth": 5, "offset": 0, "zipf_hard": 1.5, "include_wn": true, "wn_closure_depth": 3}`.

- Gap heads: 289; selected 66; harvested (one word or more) 50.
- Words: 185 (181 distinct), candidates 185; by gap class {"queued_only": 14, "pair_completion": 28, "pair_empty": 80, "singleton_empty": 63}.
- Dropped: {"not_representative": 138, "too_many_words": 80, "zipf_hard": 48, "function_word": 37, "cap": 24, "known_label": 10, "repeat": 1}.
- Zipf probe band 18%; Class VI 25%; WordNet adjective 78%.
- Pair candidates 39 (WordNet-confirmed 4, negation forms 5); candidates with a partner hint 14.
- Downstream estimate: M1 about $0.74; M3 about $1.66 if half the words pass M1.

| head | gap class | words |
|---|---|---|
| 188 Inhabitant | queued_only | english, native, indigenous, scottish, domestic, vernacular, autochthonous, domiciled, domiciliary |
| 239 Sinistrality | queued_only | sinister, sinistral |
| 419 Deafness | queued_only | stunned, stone deaf, inaudible |
| 452 Incogitancy | pair_completion | no-brain, diverted, unconsidered |
| 464 Comparison | pair_empty | comparable, comparative |
| 464a Incomparability | pair_empty | incomparable, incommensurable |
| 469 Qualification | singleton_empty | qualified, qualifying, conditional |
| 480a Discovery | - | - |
| 501 Fool | - | - |
| 510 Foresight | singleton_empty | prescient, farsighted, foreseeing |
| 517 Unmeaningness | pair_empty | meaningless, vacant, insignificant, trivial, nonsensical, inexpressive, inexpressible |
| 527a Correction | singleton_empty | corrective |
| 536 Negation | pair_completion | negative, denied, denying, contradictory |
| 547 Dupe | - | - |
| 552 Obliteration | singleton_empty | obliterated, unwritten, intestate |
| 558 Engraving | singleton_empty | engraved lapidary |
| 564 Nomenclature | pair_empty | named, call properly, nominal |
| 565 Misnomer | pair_empty | so-called, self called, anonymous, unnamed, pseudonymous, misnamed, unacknowledged |
| 570 Perspicuity | - | - |
| 586 Allocution | - | - |
| 592 Correspondence | singleton_empty | epistolary |
| 607 Tergiversation | pair_completion | reactionary, trimming |
| 617 Pretext | singleton_empty | alleged |
| 629 Circuit | singleton_empty | indirect, backhanded |
| 636 Store | singleton_empty | spare, stored |
| 651 Imperfection | pair_completion | so-so, imperfect, defective, cracked, faulty, found wanting, short-handed, lame, good enough, pretty well |
| 661 Relapse | - | - |
| 669 Alarm | singleton_empty | alarming |
| 677 Use | pair_empty | used, well-worn |
| 678 Disuse | pair_empty | unemployed, disused |
| 688 Fatigue | pair_empty | used up, tired, spent, weather-beaten, faint, worn, pulled down, played out, haggard, trying |
| 689 Refreshment | pair_empty | refreshing, refreshed |
| 700 Proficient | - | - |
| 713 Discord | pair_empty | controversial, discordant, disagreeing, torn, ajar, quarrelsome, embroiled, litigious, factious |
| 728 Arena | - | - |
| 745 Master | - | - |
| 753 Keeper | - | - |
| 758 Consignee | - | - |
| 764 Refusal | singleton_empty | impossible, refusing, refused, restive, recusant |
| 768a Release from engagement | singleton_empty | absolute |
| 775 Acquisition | pair_completion | paying, acquired |
| 783 Transfer | singleton_empty | negotiable |
| 790 Restitution | singleton_empty | restoring |
| 795 Purchase | singleton_empty | purchased |
| 799a Stock Market | - | - |
| 805 Credit | pair_empty | credited, accredited |
| 806 Debt | pair_empty | involved, due, liable, past due, deeply involved, indebted, minus, unpaid, unrequited |
| 812 Price | singleton_empty | priced, venal, ad valorem |
| 814 Dearness | pair_empty | high, dear, expensive, dear bought, above price, unreasonable, overpriced |
| 815 Cheapness | pair_empty | low, cheap, reasonable, free, half-price, dog cheap, inexpensive, without charge, rent-free, unpaid |
| 839 Lamentation | singleton_empty | lamenting, tearful, plaintive, sorrowing, lachrymose, elegiac, querulous |
| 847a Jewelry | singleton_empty | diamond, bejeweled, gemological |
| 871 Expectance | pair_completion | expected, common, expecting, foreseen, unsurprising |
| 887 Blusterer | - | - |
| 901a Sullenness | singleton_empty | ill-affected, cross, sour, sullen, moody, crusty, rusty, perverse, grim, restive |
| 912 Benefactor | - | - |
| 927a Exemption | singleton_empty | free, released, unbound, unaccountable, excusable |
| 941 Knave | - | - |
| 956 Fasting | singleton_empty | starved, half-starved, fasting, lenten |
| 965 Jurisdiction | singleton_empty | executive, judicial, juridical, inquisitorial |
| 970 Acquittal | pair_completion | acquitted, unpunished |
| 977 Angel | pair_empty | angelic, saintly |
| 978 Satan | pair_empty | satanic, infernal |
| 981 Heaven | pair_empty | heavenly |
| 982 Hell | pair_empty | infernal |
| 994 Sorcerer | - | - |
