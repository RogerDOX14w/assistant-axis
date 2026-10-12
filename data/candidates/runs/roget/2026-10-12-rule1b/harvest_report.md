# Roget harvest: run 2026-10-12-rule1b

Config: `{"per_head_cap": 10, "pair_top": 3, "max_words": 2, "classes": ["pair_completion", "pair_empty", "singleton_empty", "queued_only"], "every_nth": null, "offset": 0, "zipf_floor": "rule_1b", "include_wn": true, "wn_closure_depth": 6, "head_scope": "data/candidates/roget/head_scope.json", "delta_from": "2026-10-11-full"}`.

- Gap heads: 275; selected 275; harvested (one word or more) 14.
- Words: 14 (14 distinct), candidates 14; by gap class {"pair_completion": 5, "pair_empty": 7, "singleton_empty": 2}.
- Dropped: {"not_representative": 773, "not_character": 382, "too_many_words": 195, "cap": 156, "known_label": 81, "function_word": 55, "proper": 18, "repeat": 1}.
- Zipf floor (rule_1b: only `hard_reject` drops; the negating-prefix and gloss-hint rescues go to M1's probe): 144 words below 1.5, 0 dropped, 144 rescued {"gloss_hint": 94, "negating_prefix": 50} (dropped by the second check before 2026-10-12); 12 of them candidates (calumnious, closetongued, exceptionable, minatory, persuadable, pokerish, proscriptive, squeezable, uncensured, uncomplying, unhackneyed, unstrained).  In the heads skipped as not character: 99 below the line, 0 dropped, 99 rescued.
- Delta against run 2026-10-11-full: 485 words harvested, 471 already submitted there and left out, 14 new (below the Zipf line: calumnious, closetongued, exceptionable, minatory, persuadable, pokerish, proscriptive, squeezable, uncensured, uncomplying, unhackneyed, unstrained; other: grotesque, purposeless).
- Zipf probe band 93%; Class VI 36%; WordNet adjective 57%.
- Pair candidates 0 (WordNet-confirmed 0, negation forms 0); candidates with a partner hint 0.
- Downstream estimate: M1 about $0.06; M3 about $0.13 if half the words pass M1.
- Head scope (data/candidates/roget/head_scope.json): 119 selected heads rated 0 (not character) skipped, 382 words with them; words by the rating of their head {"1": 11, "2": 3}.

| head | gap class | character | words |
|---|---|---|---|
| 29 Mean | singleton_empty | 1 | - |
| 124 Oldness | pair_completion | 1 | - |
| 184 Location | pair_empty | 0 | skipped (not character) |
| 193 Littleness | pair_completion | 1 | - |
| 391 Insipidity | queued_only | 1 | - |
| 403 Silence | pair_empty | 1 | - |
| 450a Absence or want of Intellect | pair_completion | 2 | - |
| 452 Incogitancy | pair_completion | 2 | - |
| 453 Idea | pair_empty | - | - |
| 454 Topic | pair_empty | 0 | skipped (not character) |
| 462 Answer | pair_completion | 0 | skipped (not character) |
| 464 Comparison | pair_empty | 0 | skipped (not character) |
| 464a Incomparability | pair_empty | 0 | skipped (not character) |
| 465 Discrimination | pair_completion | 1 | - |
| 465b Identification | singleton_empty | - | - |
| 466 Measurement | singleton_empty | 0 | skipped (not character) |
| 468 Counter Evidence | pair_completion | 0 | skipped (not character) |
| 469 Qualification | singleton_empty | 0 | skipped (not character) |
| 470 Possibility | pair_empty | 0 | skipped (not character) |
| 471 Impossibility | pair_empty | 1 | - |
| 472 Probability | pair_empty | 1 | - |
| 473 Improbability | pair_empty | 1 | - |
| 479 Confutation | pair_empty | 0 | skipped (not character) |
| 480a Discovery | singleton_empty | - | - |
| 493 Ignoramus | pair_completion | 2 | - |
| 496 Maxim | pair_empty | 0 | skipped (not character) |
| 497 Absurdity | pair_empty | 1 | - |
| 501 Fool | pair_completion | - | - |
| 502 Sanity | pair_completion | 2 | - |
| 504 Madman | singleton_empty | - | - |
| 507 Expectation | pair_empty | 0 | skipped (not character) |
| 508 Inexpectation | pair_empty | 1 | - |
| 511 Prediction | singleton_empty | 0 | skipped (not character) |
| 512 Omen | singleton_empty | 0 | skipped (not character) |
| 513 Oracle | singleton_empty | - | - |
| 517 Unmeaningness | pair_empty | 0 | skipped (not character) |
| 519 Unintelligibility | pair_completion | 1 | - |
| 520 Equivocalness | singleton_empty | 1 | - |
| 523 Misinterpretation | pair_completion | 0 | skipped (not character) |
| 524 Interpreter | singleton_empty | - | - |
| 527a Correction | singleton_empty | 0 | skipped (not character) |
| 529 Disclosure | pair_empty | 1 | - |
| 530 Ambush | pair_empty | 0 | skipped (not character) |
| 531 Publication | singleton_empty | 0 | skipped (not character) |
| 533 Secret | pair_completion | 0 | skipped (not character) |
| 534 Messenger | singleton_empty | - | - |
| 536 Negation | pair_completion | 1 | - |
| 538 Misteaching | pair_completion | 0 | skipped (not character) |
| 540 Teacher | pair_empty | 1 | - |
| 541 Learner | pair_empty | 0 | skipped (not character) |
| 546 Untruth | singleton_empty | 0 | skipped (not character) |
| 547 Dupe | pair_empty | - | - |
| 548 Deceiver | pair_empty | - | - |
| 549 Exaggeration | singleton_empty | 0 | skipped (not character) |
| 550 Indication | singleton_empty | 1 | - |
| 551 Record | pair_empty | - | - |
| 552 Obliteration | pair_empty | 0 | skipped (not character) |
| 553 Recorder | singleton_empty | - | - |
| 554 Representation | pair_empty | 0 | skipped (not character) |
| 555 Misrepresentation | pair_empty | 0 | skipped (not character) |
| 556 Painting | singleton_empty | 0 | skipped (not character) |
| 557 Sculpture | singleton_empty | 0 | skipped (not character) |
| 558 Engraving | singleton_empty | 0 | skipped (not character) |
| 560 Language | singleton_empty | 1 | - |
| 562 Word | pair_empty | 0 | skipped (not character) |
| 563 Neologism | pair_empty | 0 | skipped (not character) |
| 564 Nomenclature | pair_empty | 0 | skipped (not character) |
| 565 Misnomer | pair_empty | 1 | - |
| 566 Phrase | singleton_empty | 0 | skipped (not character) |
| 567 Grammar | pair_empty | - | - |
| 568 Solecism | pair_empty | 0 | skipped (not character) |
| 569 Style | singleton_empty | - | - |
| 571 Obscurity | pair_completion | 0 | skipped (not character) |
| 574 Vigor | pair_completion | 1 | - |
| 579 Inelegance | pair_completion | 1 | grotesque |
| 580 Voice | pair_completion | 0 | skipped (not character) |
| 585 Taciturnity | pair_completion | 2 | closetongued |
| 586 Allocution | pair_empty | - | - |
| 587 Response | pair_empty | - | - |
| 588 Conversation | pair_empty | 0 | skipped (not character) |
| 589 Soliloquy | pair_empty | 0 | skipped (not character) |
| 591 Printing | pair_completion | 0 | skipped (not character) |
| 592 Correspondence | pair_empty | 0 | skipped (not character) |
| 593 Book | pair_empty | - | - |
| 595 Dissertation | singleton_empty | 0 | skipped (not character) |
| 596 Compendium | singleton_empty | 0 | skipped (not character) |
| 600 Will | pair_completion | 1 | - |
| 602 Willingness | pair_completion | 2 | persuadable |
| 607 Tergiversation | pair_completion | 2 | - |
| 610 Rejection | pair_completion | 0 | skipped (not character) |
| 611 Predetermination | queued_only | 1 | - |
| 614 Desuetude | pair_empty | 1 | unhackneyed |
| 615a Absence of Motive | singleton_empty | 1 | - |
| 617 Pretext | singleton_empty | 1 | - |
| 620 Intention | pair_empty | 0 | skipped (not character) |
| 621 Chance | pair_empty | 1 | purposeless |
| 622 Pursuit | pair_completion | 0 | skipped (not character) |
| 624 Relinquishment | singleton_empty | 0 | skipped (not character) |
| 628 Mid-course | pair_empty | - | - |
| 629 Circuit | pair_empty | 0 | skipped (not character) |
| 630 Requirement | singleton_empty | 0 | skipped (not character) |
| 631 Instrumentality | singleton_empty | 1 | - |
| 634 Substitute | singleton_empty | - | - |
| 635 Materials | singleton_empty | 0 | skipped (not character) |
| 636 Store | singleton_empty | 0 | skipped (not character) |
| 637 Provision | pair_empty | - | - |
| 638 Waste | pair_empty | 0 | skipped (not character) |
| 640 Insufficiency | pair_empty | 1 | - |
| 643 Unimportance | pair_completion | 1 | - |
| 647 Inexpedience | pair_completion | 1 | - |
| 651 Imperfection | pair_completion | 0 | skipped (not character) |
| 652 Cleanness | pair_completion | 1 | - |
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
| 674 Nonpreparation | pair_completion | 1 | - |
| 677 Use | pair_empty | 0 | skipped (not character) |
| 678 Disuse | pair_empty | 0 | skipped (not character) |
| 679 Misuse | singleton_empty | 0 | skipped (not character) |
| 680 Action | pair_completion | 0 | skipped (not character) |
| 687 Repose | pair_completion | 1 | unstrained |
| 689 Refreshment | pair_completion | 0 | skipped (not character) |
| 690 Agent | singleton_empty | - | - |
| 691 Workshop | singleton_empty | 0 | skipped (not character) |
| 694 Director | singleton_empty | - | - |
| 696 Council | singleton_empty | 0 | skipped (not character) |
| 701 Bungler | pair_completion | - | - |
| 706 Hindrance | pair_completion | 1 | - |
| 711 Auxiliary | pair_empty | - | - |
| 712 Party | singleton_empty | 1 | - |
| 715 Defiance | singleton_empty | 2 | - |
| 717 Defense | pair_completion | 1 | - |
| 718 Retaliation | pair_empty | 1 | - |
| 719 Resistance | pair_empty | 1 | - |
| 727 Arms | singleton_empty | - | - |
| 728 Arena | singleton_empty | - | - |
| 729 Completion | pair_empty | 0 | skipped (not character) |
| 730 Noncompletion | pair_empty | 0 | skipped (not character) |
| 733 Trophy | singleton_empty | - | - |
| 735 Adversity | pair_completion | 0 | skipped (not character) |
| 744 Compulsion | singleton_empty | 1 | - |
| 745 Master | pair_empty | - | - |
| 746 Servant | pair_empty | 0 | skipped (not character) |
| 747 Scepter | singleton_empty | - | - |
| 750 Liberation | pair_completion | 2 | - |
| 752 Prison | singleton_empty | - | - |
| 753 Keeper | pair_empty | - | - |
| 754 Prisoner | pair_empty | 0 | skipped (not character) |
| 755 Commission | pair_empty | 0 | skipped (not character) |
| 756 Abrogation | pair_empty | 0 | skipped (not character) |
| 757 Resignation | singleton_empty | - | - |
| 758 Consignee | singleton_empty | - | - |
| 759 Deputy | singleton_empty | 0 | skipped (not character) |
| 761 Prohibition | pair_completion | 1 | proscriptive |
| 762 Consent | singleton_empty | 1 | squeezable |
| 763 Offer | pair_empty | 0 | skipped (not character) |
| 764 Refusal | pair_empty | 1 | uncomplying |
| 765 Request | pair_empty | 1 | - |
| 766 Deprecation | pair_empty | 0 | skipped (not character) |
| 767 Petitioner | singleton_empty | - | - |
| 768 Promise | pair_empty | 1 | - |
| 768a Release from engagement | pair_empty | 0 | skipped (not character) |
| 769 Compact | singleton_empty | 1 | - |
| 770 Conditions | singleton_empty | 0 | skipped (not character) |
| 771 Security | singleton_empty | - | - |
| 775 Acquisition | pair_empty | 0 | skipped (not character) |
| 776 Loss | pair_empty | 0 | skipped (not character) |
| 777 Possession | pair_empty | 1 | - |
| 777a Exemption | pair_empty | 0 | skipped (not character) |
| 780 Property | singleton_empty | 1 | - |
| 782 Relinquishment | pair_completion | 0 | skipped (not character) |
| 783 Transfer | singleton_empty | 0 | skipped (not character) |
| 786 Apportionment | singleton_empty | 0 | skipped (not character) |
| 787 Lending | pair_empty | 0 | skipped (not character) |
| 788 Borrowing | pair_empty | - | - |
| 789 Taking | pair_empty | 1 | - |
| 790 Restitution | pair_empty | 0 | skipped (not character) |
| 791 Stealing | singleton_empty | 2 | - |
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
| 812a Value | pair_empty | 1 | - |
| 812b Worthlessness | pair_empty | 1 | - |
| 813 Discount | pair_empty | 0 | skipped (not character) |
| 814 Dearness | pair_empty | 1 | - |
| 815 Cheapness | pair_empty | 1 | - |
| 820 Affections | singleton_empty | 2 | - |
| 824 Excitation | singleton_empty | 1 | - |
| 830 . Painfulness | pair_completion | 1 | - |
| 834 Relief | pair_empty | 0 | skipped (not character) |
| 835 Aggravation | pair_empty | 0 | skipped (not character) |
| 838 Rejoicing | pair_empty | 1 | - |
| 839 Lamentation | pair_empty | 1 | - |
| 847 Ornament | pair_empty | 0 | skipped (not character) |
| 847a Jewelry | singleton_empty | 0 | skipped (not character) |
| 848 Blemish | pair_empty | 0 | skipped (not character) |
| 854 Fop | singleton_empty | - | - |
| 857 Laughingstock | singleton_empty | - | - |
| 871 Expectance | pair_completion | 0 | skipped (not character) |
| 872 Prodigy | singleton_empty | - | - |
| 877 Title | singleton_empty | - | - |
| 883 Celebration | singleton_empty | 0 | skipped (not character) |
| 889 Enmity | pair_completion | 2 | - |
| 891 Enemy | pair_empty | - | - |
| 896 Congratulation | singleton_empty | 0 | skipped (not character) |
| 899 Favorite | singleton_empty | - | - |
| 901a Sullenness | singleton_empty | 2 | - |
| 905 Divorce | singleton_empty | - | - |
| 908 Malediction | singleton_empty | 0 | skipped (not character) |
| 909 Threat | singleton_empty | 1 | minatory |
| 912 Benefactor | pair_completion | - | - |
| 915 Condolence | singleton_empty | - | - |
| 925 Undueness | pair_completion | 0 | skipped (not character) |
| 927a Exemption | singleton_empty | 1 | - |
| 930 Contempt | singleton_empty | 2 | - |
| 931 Approbation | pair_empty | 1 | uncensured |
| 932 Disapprobation | pair_empty | 2 | - |
| 934 Detraction | pair_empty | 2 | calumnious |
| 937 Vindication | pair_empty | 1 | - |
| 938 Accusation | pair_empty | 0 | skipped (not character) |
| 941 Knave | singleton_empty | - | - |
| 945 Vice | pair_completion | 2 | - |
| 947 Guilt | pair_empty | 1 | exceptionable |
| 949 Bad Man | pair_empty | - | - |
| 952 Atonement | singleton_empty | - | - |
| 956 Fasting | pair_completion | 0 | skipped (not character) |
| 961 Impurity | pair_completion | 2 | - |
| 962 Libertine | singleton_empty | - | - |
| 963 Legality | pair_empty | 0 | skipped (not character) |
| 964 Illegality | pair_empty | 1 | - |
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
| 977 Angel | pair_empty | 2 | - |
| 978 Satan | pair_empty | 2 | - |
| 979 Jupiter | pair_empty | 0 | skipped (not character) |
| 980 Demon | pair_empty | 1 | pokerish |
| 981 Heaven | pair_empty | 1 | - |
| 982 Hell | pair_empty | 0 | skipped (not character) |
| 985 Judeo-Christian Revelation | pair_empty | 1 | - |
| 986 Pseudo-Revelation | pair_empty | - | - |
| 993 Spell | singleton_empty | - | - |
| 994 Sorcerer | singleton_empty | - | - |
| 999 Canonicals | singleton_empty | - | - |
| 1000 Temple | singleton_empty | 1 | - |
