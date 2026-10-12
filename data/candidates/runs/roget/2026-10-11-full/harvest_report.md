# Roget harvest: run 2026-10-11-full

Config: `{"per_head_cap": 10, "pair_top": 3, "max_words": 2, "classes": ["pair_completion", "pair_empty", "singleton_empty", "queued_only"], "every_nth": null, "offset": 0, "zipf_hard": 1.5, "include_wn": true, "wn_closure_depth": 3, "head_scope": "data/candidates/roget/head_scope.json"}`.

- Gap heads: 275; selected 275; harvested (one word or more) 87.
- Words: 475 (448 distinct), candidates 475; by gap class {"singleton_empty": 92, "pair_completion": 185, "queued_only": 10, "pair_empty": 188}.
- Dropped: {"not_representative": 663, "not_character": 362, "too_many_words": 195, "zipf_hard": 144, "cap": 141, "known_label": 72, "function_word": 55, "proper": 18, "repeat": 1}.
- Zipf probe band 12%; Class VI 31%; WordNet adjective 86%.
- Pair candidates 101 (WordNet-confirmed 8, negation forms 5); candidates with a partner hint 19.
- Downstream estimate: M1 about $1.90; M3 about $4.27 if half the words pass M1.
- Head scope (data/candidates/roget/head_scope.json): 119 selected heads rated 0 (not character) skipped, 362 words with them; words by the rating of their head {"1": 368, "2": 107}.

| head | gap class | character | words |
|---|---|---|---|
| 29 Mean | singleton_empty | 1 | average, intermediate, neutral, mediocre |
| 124 Oldness | pair_completion | 1 | old, prime, time-honored, elder, primitive, old-world, black-letter, colonial, after-age, firstborn |
| 184 Location | pair_empty | 0 | skipped (not character) |
| 193 Littleness | pair_completion | 1 | little, minute, tiny, limited, pocket, dwarf, portable, invisible, cramped, molecular |
| 391 Insipidity | queued_only | 1 | weak, tasteless, insipid |
| 403 Silence | pair_empty | 1 | still, silent, soft, hushed, soundless |
| 450a Absence or want of Intellect | pair_completion | 2 | idiotic, thoughtless, vegetative |
| 452 Incogitancy | pair_completion | 2 | no-brain, diverted, unconsidered |
| 453 Idea | pair_empty | - | - |
| 454 Topic | pair_empty | 0 | skipped (not character) |
| 462 Answer | pair_completion | 0 | skipped (not character) |
| 464 Comparison | pair_empty | 0 | skipped (not character) |
| 464a Incomparability | pair_empty | 0 | skipped (not character) |
| 465 Discrimination | pair_completion | 1 | nice, distinctive, discriminating |
| 465b Identification | singleton_empty | - | - |
| 466 Measurement | singleton_empty | 0 | skipped (not character) |
| 468 Counter Evidence | pair_completion | 0 | skipped (not character) |
| 469 Qualification | singleton_empty | 0 | skipped (not character) |
| 470 Possibility | pair_empty | 0 | skipped (not character) |
| 471 Impossibility | pair_empty | 1 | impossible, unlikely, absurd, visionary, beyond control, unimaginable, unthinkable, insurmountable, unfeasible, unattainable |
| 472 Probability | pair_empty | 1 | likely, reasonable |
| 473 Improbability | pair_empty | 1 | far out, unlikely, strange, inconceivable, unimaginable |
| 479 Confutation | pair_empty | 0 | skipped (not character) |
| 480a Discovery | singleton_empty | - | - |
| 493 Ignoramus | pair_completion | 2 | shallow |
| 496 Maxim | pair_empty | 0 | skipped (not character) |
| 497 Absurdity | pair_empty | 1 | ridiculous, fantastic, self-contradictory, punning |
| 501 Fool | pair_completion | - | - |
| 502 Sanity | pair_completion | 2 | sound, reasonable, self-possessed, sober, lucid |
| 504 Madman | singleton_empty | - | - |
| 507 Expectation | pair_empty | 0 | skipped (not character) |
| 508 Inexpectation | pair_empty | 1 | surprised, unexpected, unaware, surprising, beyond expectation, unpredictable |
| 511 Prediction | singleton_empty | 0 | skipped (not character) |
| 512 Omen | singleton_empty | 0 | skipped (not character) |
| 513 Oracle | singleton_empty | - | - |
| 517 Unmeaningness | pair_empty | 0 | skipped (not character) |
| 519 Unintelligibility | pair_completion | 1 | dark, inexplicable, unfathomable, incomprehensible, loose, dense, unexplained, impenetrable, insoluble, mysterious |
| 520 Equivocalness | singleton_empty | 1 | ambiguous, indeterminate |
| 523 Misinterpretation | pair_completion | 0 | skipped (not character) |
| 524 Interpreter | singleton_empty | - | - |
| 527a Correction | singleton_empty | 0 | skipped (not character) |
| 529 Disclosure | pair_empty | 1 | open, disclosed |
| 530 Ambush | pair_empty | 0 | skipped (not character) |
| 531 Publication | singleton_empty | 0 | skipped (not character) |
| 533 Secret | pair_completion | 0 | skipped (not character) |
| 534 Messenger | singleton_empty | - | - |
| 536 Negation | pair_completion | 1 | negative, denied, denying, contradictory |
| 538 Misteaching | pair_completion | 0 | skipped (not character) |
| 540 Teacher | pair_empty | 1 | professorial |
| 541 Learner | pair_empty | 0 | skipped (not character) |
| 546 Untruth | singleton_empty | 0 | skipped (not character) |
| 547 Dupe | pair_empty | - | - |
| 548 Deceiver | pair_empty | - | - |
| 549 Exaggeration | singleton_empty | 0 | skipped (not character) |
| 550 Indication | singleton_empty | 1 | typical, indicating, marked, indicated, indelible, connotative |
| 551 Record | pair_empty | - | - |
| 552 Obliteration | pair_empty | 0 | skipped (not character) |
| 553 Recorder | singleton_empty | - | - |
| 554 Representation | pair_empty | 0 | skipped (not character) |
| 555 Misrepresentation | pair_empty | 0 | skipped (not character) |
| 556 Painting | singleton_empty | 0 | skipped (not character) |
| 557 Sculpture | singleton_empty | 0 | skipped (not character) |
| 558 Engraving | singleton_empty | 0 | skipped (not character) |
| 560 Language | singleton_empty | 1 | current, linguistic, literary, bilingual, dialectic, polyglot |
| 562 Word | pair_empty | 0 | skipped (not character) |
| 563 Neologism | pair_empty | 0 | skipped (not character) |
| 564 Nomenclature | pair_empty | 0 | skipped (not character) |
| 565 Misnomer | pair_empty | 1 | so-called, self called, anonymous, unnamed, pseudonymous, misnamed, unacknowledged |
| 566 Phrase | singleton_empty | 0 | skipped (not character) |
| 567 Grammar | pair_empty | - | - |
| 568 Solecism | pair_empty | 0 | skipped (not character) |
| 569 Style | singleton_empty | - | - |
| 571 Obscurity | pair_completion | 0 | skipped (not character) |
| 574 Vigor | pair_completion | 1 | powerful, pointed, lively, sensational, elevated, impassioned, sententious |
| 579 Inelegance | pair_completion | 1 | forced, affected, artificial, stiff, awkward, abrupt, crude, inelegant |
| 580 Voice | pair_completion | 0 | skipped (not character) |
| 585 Taciturnity | pair_completion | 2 | silent, curt, taciturn |
| 586 Allocution | pair_empty | - | - |
| 587 Response | pair_empty | - | - |
| 588 Conversation | pair_empty | 0 | skipped (not character) |
| 589 Soliloquy | pair_empty | 0 | skipped (not character) |
| 591 Printing | pair_completion | 0 | skipped (not character) |
| 592 Correspondence | pair_empty | 0 | skipped (not character) |
| 593 Book | pair_empty | - | - |
| 595 Dissertation | singleton_empty | 0 | skipped (not character) |
| 596 Compendium | singleton_empty | 0 | skipped (not character) |
| 600 Will | pair_completion | 1 | voluntary, optional, discretionary, autocratic, unconstrained |
| 602 Willingness | pair_completion | 2 | willing, ready, easy-going, favorably-minded, voluntary, cheering, predisposed, docile, nothing loth |
| 607 Tergiversation | pair_completion | 2 | reactionary, trimming |
| 610 Rejection | pair_completion | 0 | skipped (not character) |
| 611 Predetermination | queued_only | 1 | designed, well-laid, premeditated, cunning, foregone, aforethought, maturely considered |
| 614 Desuetude | pair_empty | 1 | new, unused |
| 615a Absence of Motive | singleton_empty | 1 | capricious |
| 617 Pretext | singleton_empty | 1 | alleged |
| 620 Intention | pair_empty | 0 | skipped (not character) |
| 621 Chance | pair_empty | 1 | random, accidental, without purpose, unintended, risky, unforeseen, purposed, aimless, undirected |
| 622 Pursuit | pair_completion | 0 | skipped (not character) |
| 624 Relinquishment | singleton_empty | 0 | skipped (not character) |
| 628 Mid-course | pair_empty | - | - |
| 629 Circuit | pair_empty | 0 | skipped (not character) |
| 630 Requirement | singleton_empty | 0 | skipped (not character) |
| 631 Instrumentality | singleton_empty | 1 | instrumental, intermediate, ministerial, conducive |
| 634 Substitute | singleton_empty | - | - |
| 635 Materials | singleton_empty | 0 | skipped (not character) |
| 636 Store | singleton_empty | 0 | skipped (not character) |
| 637 Provision | pair_empty | - | - |
| 638 Waste | pair_empty | 0 | skipped (not character) |
| 640 Insufficiency | pair_empty | 1 | wanting, ill-provided, empty, inadequate, slack, empty-handed, drained, spare, starving, scarce |
| 643 Unimportance | pair_completion | 1 | so-so, common, light, unimportant, respectable, indifferent, sorry, immaterial, shallow, ridiculous |
| 647 Inexpedience | pair_completion | 1 | undesirable, ill-advised, inappropriate, inconvenient, objectionable, awkward, inadvisable, improper, unsatisfactory, disadvantageous |
| 651 Imperfection | pair_completion | 0 | skipped (not character) |
| 652 Cleanness | pair_completion | 1 | clean, pure, sweet, stainless, immaculate, neat, cleaned, cleansing, trig, unsullied |
| 657 Insalubrity | pair_empty | 0 | skipped (not character) |
| 659 Deterioration | pair_completion | 0 | skipped (not character) |
| 660 Restoration | pair_empty | 0 | skipped (not character) |
| 661 Relapse | pair_empty | - | - |
| 662 Remedy | pair_empty | 0 | skipped (not character) |
| 663 Bane | pair_empty | - | - |
| 666 Refuge | pair_empty | - | - |
| 667 Pitfall | pair_empty | - | - |
| 669 Alarm | singleton_empty | 0 | skipped (not character) |
| 671 Escape | singleton_empty | 0 | skipped (not character) |
| 672 Deliverance | singleton_empty | 0 | skipped (not character) |
| 674 Nonpreparation | pair_completion | 1 | green, rough cast, unprepared, embryonic, natural, coarse, premature, untrained, ad lib, uncooked |
| 677 Use | pair_empty | 0 | skipped (not character) |
| 678 Disuse | pair_empty | 0 | skipped (not character) |
| 679 Misuse | singleton_empty | 0 | skipped (not character) |
| 680 Action | pair_completion | 0 | skipped (not character) |
| 687 Repose | pair_completion | 1 | relaxed, unstressed, reposing |
| 689 Refreshment | pair_completion | 0 | skipped (not character) |
| 690 Agent | singleton_empty | - | - |
| 691 Workshop | singleton_empty | 0 | skipped (not character) |
| 694 Director | singleton_empty | - | - |
| 696 Council | singleton_empty | 0 | skipped (not character) |
| 701 Bungler | pair_completion | - | - |
| 706 Hindrance | pair_completion | 1 | alone, hindering, obstructive, unfavorable, hard pressed, cumbersome, onerous, heavy laden, hindered, obtrusive |
| 711 Auxiliary | pair_empty | - | - |
| 712 Party | singleton_empty | 1 | joined together, joint, embattled |
| 715 Defiance | singleton_empty | 2 | defiant |
| 717 Defense | pair_completion | 1 | defending, armed, defensive, proof against, defended, iron-plated, armored, hardened, castellated |
| 718 Retaliation | pair_empty | 1 | retaliatory, retaliating |
| 719 Resistance | pair_empty | 1 | resistant, proof against, resisting, stubborn, repulsive, recalcitrant |
| 727 Arms | singleton_empty | - | - |
| 728 Arena | singleton_empty | - | - |
| 729 Completion | pair_empty | 0 | skipped (not character) |
| 730 Noncompletion | pair_empty | 0 | skipped (not character) |
| 733 Trophy | singleton_empty | - | - |
| 735 Adversity | pair_completion | 0 | skipped (not character) |
| 744 Compulsion | singleton_empty | 1 | compelling, compulsory, stringent, coercive, compelled, forcible |
| 745 Master | pair_empty | - | - |
| 746 Servant | pair_empty | 0 | skipped (not character) |
| 747 Scepter | singleton_empty | - | - |
| 750 Liberation | pair_completion | 2 | liberated |
| 752 Prison | singleton_empty | - | - |
| 753 Keeper | pair_empty | - | - |
| 754 Prisoner | pair_empty | 0 | skipped (not character) |
| 755 Commission | pair_empty | 0 | skipped (not character) |
| 756 Abrogation | pair_empty | 0 | skipped (not character) |
| 757 Resignation | singleton_empty | - | - |
| 758 Consignee | singleton_empty | - | - |
| 759 Deputy | singleton_empty | 0 | skipped (not character) |
| 761 Prohibition | pair_completion | 1 | restrictive, prohibitive, unauthorized, contraband, forbidding prohibited |
| 762 Consent | singleton_empty | 1 | unconditional, consenting |
| 763 Offer | pair_empty | 0 | skipped (not character) |
| 764 Refusal | pair_empty | 1 | impossible, refusing, refused, restive, recusant |
| 765 Request | pair_empty | 1 | urgent, requesting, supplicant, postulant |
| 766 Deprecation | pair_empty | 0 | skipped (not character) |
| 767 Petitioner | singleton_empty | - | - |
| 768 Promise | pair_empty | 1 | promising, committed, bound, promised, upon oath, promissory, votive |
| 768a Release from engagement | pair_empty | 0 | skipped (not character) |
| 769 Compact | singleton_empty | 1 | agreed |
| 770 Conditions | singleton_empty | 0 | skipped (not character) |
| 771 Security | singleton_empty | - | - |
| 775 Acquisition | pair_empty | 0 | skipped (not character) |
| 776 Loss | pair_empty | 0 | skipped (not character) |
| 777 Possession | pair_empty | 1 | worth, possessing, possessed, unsold |
| 777a Exemption | pair_empty | 0 | skipped (not character) |
| 780 Property | singleton_empty | 1 | landed, free lease-hold, feudal |
| 782 Relinquishment | pair_completion | 0 | skipped (not character) |
| 783 Transfer | singleton_empty | 0 | skipped (not character) |
| 786 Apportionment | singleton_empty | 0 | skipped (not character) |
| 787 Lending | pair_empty | 0 | skipped (not character) |
| 788 Borrowing | pair_empty | - | - |
| 789 Taking | pair_empty | 1 | taking, predatory, parasitic, ravenous, prehensile, rapacious |
| 790 Restitution | pair_empty | 0 | skipped (not character) |
| 791 Stealing | singleton_empty | 2 | stolen, light-fingered, predatory, furtive, piratical |
| 792 Thief | singleton_empty | - | - |
| 793 Booty | singleton_empty | - | - |
| 794 Barter | singleton_empty | 0 | skipped (not character) |
| 795 Purchase | pair_empty | 0 | skipped (not character) |
| 796 Sale | pair_empty | 0 | skipped (not character) |
| 797 Merchant | singleton_empty | - | - |
| 798 Merchandise | singleton_empty | - | - |
| 799 Mart | singleton_empty | - | - |
| 799a Stock Market | singleton_empty | - | - |
| 799b Securities | singleton_empty | - | - |
| 801 Treasurer | singleton_empty | - | - |
| 802 Treasury | singleton_empty | - | - |
| 805 Credit | pair_empty | 0 | skipped (not character) |
| 806 Debt | pair_empty | 0 | skipped (not character) |
| 807 Payment | pair_empty | 0 | skipped (not character) |
| 808 Nonpayment | pair_empty | 0 | skipped (not character) |
| 809 Expenditure | pair_empty | 0 | skipped (not character) |
| 810 Receipt | pair_empty | 0 | skipped (not character) |
| 812a Value | pair_empty | 1 | valuable, worthy, worthwhile |
| 812b Worthlessness | pair_empty | 1 | cheap, useless, worthless, slapdash |
| 813 Discount | pair_empty | 0 | skipped (not character) |
| 814 Dearness | pair_empty | 1 | high, dear, expensive, dear bought, above price, unreasonable, overpriced |
| 815 Cheapness | pair_empty | 1 | low, cheap, reasonable, free, half-price, dog cheap, inexpensive, without charge, rent-free, unpaid |
| 820 Affections | singleton_empty | 2 | cast, framed, tempered, prone, deep-rooted, inherent, predisposed, ingrained, affective |
| 824 Excitation | singleton_empty | 1 | excited, hot, up, taught, lost, sparkling, wild, flaming, warm, exciting |
| 830 . Painfulness | pair_completion | 1 | causing pain, painful, unpleasant, uncomfortable, unacceptable, distasteful, undesirable, unwelcome, obnoxious, sad |
| 834 Relief | pair_empty | 0 | skipped (not character) |
| 835 Aggravation | pair_empty | 0 | skipped (not character) |
| 838 Rejoicing | pair_empty | 1 | pleased, triumphant, rejoicing |
| 839 Lamentation | pair_empty | 1 | lamenting, tearful, plaintive, sorrowing, lachrymose, elegiac, querulous |
| 847 Ornament | pair_empty | 0 | skipped (not character) |
| 847a Jewelry | singleton_empty | 0 | skipped (not character) |
| 848 Blemish | pair_empty | 0 | skipped (not character) |
| 854 Fop | singleton_empty | - | - |
| 857 Laughingstock | singleton_empty | - | - |
| 871 Expectance | pair_completion | 0 | skipped (not character) |
| 872 Prodigy | singleton_empty | - | - |
| 877 Title | singleton_empty | - | - |
| 883 Celebration | singleton_empty | 0 | skipped (not character) |
| 889 Enmity | pair_completion | 2 | cool, cold, unfriendly, alienated |
| 891 Enemy | pair_empty | - | - |
| 896 Congratulation | singleton_empty | 0 | skipped (not character) |
| 899 Favorite | singleton_empty | - | - |
| 901a Sullenness | singleton_empty | 2 | ill-affected, cross, sour, sullen, moody, crusty, rusty, perverse, grim, restive |
| 905 Divorce | singleton_empty | - | - |
| 908 Malediction | singleton_empty | 0 | skipped (not character) |
| 909 Threat | singleton_empty | 1 | threatening, abusive |
| 912 Benefactor | pair_completion | - | - |
| 915 Condolence | singleton_empty | - | - |
| 925 Undueness | pair_completion | 0 | skipped (not character) |
| 927a Exemption | singleton_empty | 1 | free, released, unbound, unaccountable, excusable |
| 930 Contempt | singleton_empty | 2 | cavalier, despicable, contemptuous, despised, disdainful, derisive, downtrodden, pitiable |
| 931 Approbation | pair_empty | 1 | approved, approving, complimentary, plausible, commendable |
| 932 Disapprobation | pair_empty | 2 | hard upon, abusive, blown upon, disapproving, exploded, scandalized, disapproved, grudging praise, carping, answerable |
| 934 Detraction | pair_empty | 2 | foul-spoken, abusive, derogatory, disparaging, catty, detracting, satirical, scurrilous, slanderous |
| 937 Vindication | pair_empty | 1 | vindicated, plausible, apologetic, defensible, exculpatory, venial |
| 938 Accusation | pair_empty | 0 | skipped (not character) |
| 941 Knave | singleton_empty | - | - |
| 945 Vice | pair_completion | 2 | wrong, vicious, black, incorrect, sinful, improper, worthless, sinning, hell-born, unworthy |
| 947 Guilt | pair_empty | 1 | guilty |
| 949 Bad Man | pair_empty | - | - |
| 952 Atonement | singleton_empty | - | - |
| 956 Fasting | pair_completion | 0 | skipped (not character) |
| 961 Impurity | pair_completion | 2 | free, must, light, shameless, impure, indecent, rampant, erotic, carnal, voluptuous |
| 962 Libertine | singleton_empty | - | - |
| 963 Legality | pair_empty | 0 | skipped (not character) |
| 964 Illegality | pair_empty | 1 | illegal, illicit, informal, summary, unauthorized, arbitrary, actionable, unwarranted, expired, unconstitutional |
| 965 Jurisdiction | singleton_empty | 0 | skipped (not character) |
| 966 Tribunal | singleton_empty | 0 | skipped (not character) |
| 967 Judge | singleton_empty | - | - |
| 968 Lawyer | singleton_empty | 0 | skipped (not character) |
| 969 Lawsuit | singleton_empty | 0 | skipped (not character) |
| 970 Acquittal | pair_completion | 0 | skipped (not character) |
| 972 Punishment | pair_empty | 0 | skipped (not character) |
| 973 Reward | pair_empty | 0 | skipped (not character) |
| 974 Penalty | singleton_empty | - | - |
| 975 Scourge | singleton_empty | - | - |
| 977 Angel | pair_empty | 2 | angelic, saintly |
| 978 Satan | pair_empty | 2 | satanic, infernal |
| 979 Jupiter | pair_empty | 0 | skipped (not character) |
| 980 Demon | pair_empty | 1 | weird, ghost-like, demonic, haunted, possessed, fiend-like, elfin |
| 981 Heaven | pair_empty | 1 | heavenly |
| 982 Hell | pair_empty | 0 | skipped (not character) |
| 985 Judeo-Christian Revelation | pair_empty | 1 | sacred, inspired, evangelical, apostolic |
| 986 Pseudo-Revelation | pair_empty | - | - |
| 993 Spell | singleton_empty | - | - |
| 994 Sorcerer | singleton_empty | - | - |
| 999 Canonicals | singleton_empty | - | - |
| 1000 Temple | singleton_empty | 1 | monastic, cloistered, conventual |
