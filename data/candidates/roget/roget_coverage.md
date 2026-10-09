# Roget coverage map (workstream 2)

Which of the dispositional heads of Roget's Thesaurus (1911; Classes IV-VI, intellect, volition and the affections, plus the Class I-III heads whose adjectives hold one of our labels) the trait corpus already occupies.  A **head** is one numbered entry of the thesaurus (604 Resolution); an **opposed head** is its correlative (605 Irresolution), as Roget printed it in the Tabular Synopsis of the 1911 edition ([synopsis_pairs.json](./synopsis_pairs.json), [synopsis_readout.md](./synopsis_readout.md)), by rule for the heads the synopsis does not print; the pairing is [head_pairs.json](./head_pairs.json).  Each trait is placed on heads by [label_heads.json](./label_heads.json): its **primary** head (where its sense sits) and any **secondary** heads (other senses the description also covers).  Data: [heads.json](./heads.json); spot check of the placement: [map_spotcheck.md](./map_spotcheck.md); method: [coding_plan_02_roget_wordnet.md](../../../reports/trait_gap_generation/coding_plan_02_roget_wordnet.md).

States: **covered** (an existing trait has the head as its primary), **partly covered** (only as a secondary), **queued** (only a label waiting in [seed_queue.json](../../seed_queue.json)), **empty**.  Gap classes: **pair_completion** (empty, its opposed head covered: a word here would complete a pair), **pair_empty** (empty, with an opposed head that is not covered), **singleton_empty** (empty, no opposed head found), **queued_only**, **partly_covered**, **crowded** (three or more traits have it as their primary), **covered**.

**Not character**: a head the head-scope check rated 0, few or none of its adjectives describing a person's character (Haiku 5.5, one rating per head, rubric [roget_head_scope.md](../../../reports/trait_gap_generation/rubrics/roget_head_scope.md) version 2; ratings in [head_scope.json](./head_scope.json), validation in [head_scope_readout.md](./head_scope_readout.md)).  Such a head keeps its state, but is listed apart below and left out of every count but the first; the harvest skips it.

## Headline

- Heads in scope: **675** (576 dispositional, 99 from Classes I-III).
- Not character (rated 0): **188** heads, left out of the counts below (ratings: 2 on 165, 1 on 233, 0 on 188; 89 unrated, mostly heads with no adjectives).
- Covered **278**, partly covered **50**, uncovered **159** (of which 9 have a queued label only).
- Opposed pairs in scope: both poles covered **75**, one pole **63**, neither **34** (by the pairing's evidence: {"rule": {"neither_pole_covered": 1}, "synopsis": {"neither_pole_covered": 33, "both_poles_covered": 75, "one_pole_covered": 63}}).
- Labels placed: 713 existing traits with a primary head (198 without; 667 of the primaries in scope), 186 queued labels (55 without).
- Gap classes: pair_completion 28, pair_empty 61, singleton_empty 61, queued_only 9, partly_covered 50, crowded 75, covered 203.
- Pairing as Roget printed it in the Tabular Synopsis of the 1911 edition ([synopsis_readout.md](./synopsis_readout.md)), by rule for the heads the synopsis does not print: of the 576 dispositional heads, 402 are in a pair, 20 are the third head of a triad, 151 are singletons and 3 are unresolved; only a pair gives a head an opposed head here.

## By section

| class / section | covered | partly | queued | empty | not character |
|---|---|---|---|---|---|
| I I. Existence | 2 | 1 | 0 | 0 | 0 |
| I II. Relation | 1 | 2 | 0 | 0 | 0 |
| I III. Quantity | 3 | 0 | 0 | 1 | 3 |
| I IV. Order | 4 | 1 | 0 | 0 | 1 |
| I V. Number | 0 | 1 | 0 | 0 | 0 |
| I VI. Time | 4 | 0 | 0 | 1 | 1 |
| I VII. Change | 2 | 1 | 0 | 0 | 0 |
| I VIII. Causation | 8 | 3 | 0 | 0 | 1 |
| II I. Space in general | 3 | 0 | 0 | 0 | 1 |
| II II. Dimensions | 4 | 2 | 0 | 1 | 4 |
| II III. Form | 2 | 0 | 0 | 0 | 3 |
| II IV. Motion | 1 | 5 | 0 | 0 | 3 |
| III I. Matter in general | 1 | 1 | 0 | 0 | 0 |
| III II. Inorganic matter | 5 | 1 | 0 | 0 | 2 |
| III III. Organic matter | 5 | 4 | 2 | 1 | 7 |
| IV I. Operations of intellect in general | 2 | 0 | 1 | 2 | 1 |
| IV II. Precursory conditions and operations | 7 | 0 | 0 | 2 | 6 |
| IV III. Materials for reasoning | 2 | 0 | 0 | 3 | 4 |
| IV IV. Reasoning processes | 2 | 0 | 0 | 0 | 2 |
| IV V. Results of reasoning | 17 | 1 | 1 | 5 | 2 |
| IV VI. Extension of thought | 2 | 2 | 0 | 2 | 3 |
| IV VII. Creative thought | 1 | 0 | 0 | 0 | 2 |
| IV I. Nature of ideas communicated | 2 | 0 | 0 | 3 | 4 |
| IV II. Modes of communication | 9 | 1 | 0 | 6 | 10 |
| IV III. Means of communicating ideas | 12 | 1 | 0 | 13 | 24 |
| V I. Volition in general | 12 | 0 | 1 | 7 | 3 |
| V II. Prospective volition | 17 | 2 | 0 | 16 | 25 |
| V III. Voluntary action | 13 | 0 | 0 | 4 | 7 |
| V IV. Antagonism | 13 | 3 | 0 | 8 | 1 |
| V V. Results of voluntary action | 1 | 0 | 0 | 1 | 6 |
| V I. General intersocial volition | 10 | 2 | 0 | 8 | 5 |
| V II. Special intersocial volition | 1 | 0 | 0 | 5 | 2 |
| V III. Conditional intersocial volition | 3 | 0 | 0 | 3 | 2 |
| V IV. Possessive relations | 10 | 2 | 1 | 17 | 21 |
| VI I. Affections in general | 5 | 0 | 0 | 2 | 0 |
| VI II. Personal affections | 42 | 2 | 0 | 6 | 12 |
| VI III. Sympathetic affections | 20 | 3 | 2 | 7 | 4 |
| VI IV. Moral affections | 22 | 5 | 1 | 16 | 12 |
| VI V. Religious affections | 8 | 4 | 0 | 10 | 4 |

## pair_completion (28)

| head | section | opposed head | its traits | queued | parked | secondary of |
|---|---|---|---|---|---|---|
| 124 Oldness | I VI. Time / 1. Time with reference to Succession | 123 Newness (synopsis) | [innovative](../../traits/instructions/innovative.json) | - | - | - |
| 193 Littleness | II II. Dimensions | 192 Size (synopsis) | [fat](../../traits/instructions/fat.json) | - | - | - |
| 452 Incogitancy | IV I. Operations of intellect in general | 451 Thought (synopsis) | [introspective](../../traits/instructions/introspective.json), [meditative](../../traits/instructions/meditative.json), [pensive](../../traits/instructions/pensive.json), [philosophical](../../traits/instructions/philosophical.json), [speculative](../../traits/instructions/speculative.json) | - | [non-contemplative](../../seed_queue.json) (queued) | - |
| 465 Discrimination | IV II. Precursory conditions and operations | 465a Indiscrimination (synopsis) | [promiscuous](../../traits/instructions/promiscuous.json) | - | - | - |
| 493 Ignoramus | IV V. Results of reasoning | 492 Scholar (synopsis) | [educated](../../traits/instructions/educated.json) | - | - | - |
| 501 Fool | IV V. Results of reasoning | 500 Sage (synopsis) | [thinker (VALS)](../../traits/instructions/thinker_vals.json) | - | - | - |
| 502 Sanity | IV V. Results of reasoning | 503 Insanity (synopsis) | [delusional](../../traits/instructions/delusional.json) | - | [rational](../../seed_queue.json) (queued) | - |
| 519 Unintelligibility | IV I. Nature of ideas communicated | 518 Intelligibility (synopsis) | [clear](../../traits/instructions/clear.json), [transparent](../../traits/instructions/transparent.json) | - | - | - |
| 536 Negation | IV II. Modes of communication | 535 Affirmation (synopsis) | [emphatic](../../traits/instructions/emphatic.json), [opinionated](../../traits/instructions/opinionated.json), [words of affirmation](../../traits/instructions/words_of_affirmation.json) | - | - | - |
| 574 Vigor | IV III. Means of communicating ideas / 1. Language generally | 575 Feebleness (synopsis) | [dull](../../traits/instructions/dull.json) | - | - | - |
| 579 Inelegance | IV III. Means of communicating ideas / 1. Language generally | 578 Elegance (synopsis) | [formal](../../traits/instructions/formal.json) | - | - | - |
| 585 Taciturnity | IV III. Means of communicating ideas / 1. Language generally | 584 Loquacity (synopsis) | [glib](../../traits/instructions/glib.json) | - | - | - |
| 600 Will | V I. Volition in general / 1. Acts of Volition | 601 Necessity (synopsis) | [determinist](../../traits/instructions/determinist.json), [fatalistic](../../traits/instructions/fatalistic.json) | - | - | - |
| 607 Tergiversation | V I. Volition in general / 1. Acts of Volition | 606 Obstinacy (synopsis) | [obsessive](../../traits/instructions/obsessive.json), [unyielding](../../traits/instructions/unyielding.json) | - | - | - |
| 643 Unimportance | V II. Prospective volition / 1. Actual Subservience | 642 Importance (synopsis) | [serious](../../traits/instructions/serious.json) | - | [hierarchy-indifferent](../../seed_queue.json) (queued) | - |
| 645 Inutility | V II. Prospective volition / 1. Actual Subservience | 644 Utility (synopsis) | [utilitarian](../../traits/instructions/utilitarian.json) | - | - | - |
| 647 Inexpedience | V II. Prospective volition / 1. Actual Subservience | 646 Expedience (synopsis) | [expedient](../../traits/instructions/expedient.json), [pragmatic](../../traits/instructions/pragmatic.json) | - | - | - |
| 652 Cleanness | V II. Prospective volition / 1. Actual Subservience | 653 Uncleanness (synopsis) | [slovenly](../../traits/instructions/slovenly.json) | - | - | - |
| 687 Repose | V III. Voluntary action / 1. Simple voluntary Action | 686 Exertion (synopsis) | [industrious](../../traits/instructions/industrious.json) | - | - | - |
| 701 Bungler | V III. Voluntary action / 2. Complex Voluntary Action | 700 Proficient (synopsis) | [specialist](../../traits/instructions/specialist.json) | - | - | - |
| 706 Hindrance | V IV. Antagonism / 2. Active Antagonism | 707 Aid (synopsis) | [helpful](../../traits/instructions/helpful.json), [supportive](../../traits/instructions/supportive.json) | - | - | - |
| 717 Defense | V IV. Antagonism / 2. Active Antagonism | 716 Attack (synopsis) | [aggressive](../../traits/instructions/aggressive.json) | - | - | - |
| 750 Liberation | V I. General intersocial volition | 751 Restraint (synopsis) | [trapped-in-job](../../traits/instructions/trapped_in_job.json) | - | - | - |
| 761 Prohibition | V II. Special intersocial volition | 760 Permission (synopsis) | [permissive](../../traits/instructions/permissive.json), [permissive (Baumrind)](../../traits/instructions/permissive_baumrind.json) | - | - | - |
| 889 Enmity | VI III. Sympathetic affections | 888 Friendship (synopsis) | [close-knit](../../traits/instructions/close_knit.json), [friendly](../../traits/instructions/friendly.json) | - | - | - |
| 912 Benefactor | VI III. Sympathetic affections | 913 Evil doer (synopsis) | [killer (Bartle)](../../traits/instructions/killer_bartle.json) | - | - | - |
| 945 Vice | VI IV. Moral affections | 944 Virtue (synopsis) | [moral](../../traits/instructions/moral.json) | - | - | - |
| 961 Impurity | VI IV. Moral affections | 960 Purity (synopsis) | [chaste](../../traits/instructions/chaste.json) | - | - | - |

## pair_empty (61)

| head | section | opposed head | its traits | queued | parked | secondary of |
|---|---|---|---|---|---|---|
| 403 Silence | III III. Organic matter / 1. Sensation in general | 402 Sound (synopsis) | - | - | - | - |
| 453 Idea | IV I. Operations of intellect in general | 454 Topic (synopsis) | - | - | - | - |
| 471 Impossibility | IV III. Materials for reasoning | 470 Possibility (synopsis) | - | - | - | - |
| 472 Probability | IV III. Materials for reasoning | 473 Improbability (synopsis) | - | - | [hopeful](../../seed_queue.json) (queued) | - |
| 473 Improbability | IV III. Materials for reasoning | 472 Probability (synopsis) | - | - | - | - |
| 497 Absurdity | IV V. Results of reasoning | 496 Maxim (synopsis) | - | - | - | - |
| 508 Inexpectation | IV VI. Extension of thought / 1. To the Past | 507 Expectation (synopsis) | - | - | - | - |
| 529 Disclosure | IV II. Modes of communication | 530 Ambush (synopsis) | - | - | - | - |
| 540 Teacher | IV II. Modes of communication | 541 Learner (synopsis) | - | - | - | - |
| 547 Dupe | IV II. Modes of communication | 548 Deceiver (synopsis) | - | - | - | - |
| 548 Deceiver | IV II. Modes of communication | 547 Dupe (synopsis) | - | - | - | - |
| 551 Record | IV III. Means of communicating ideas / 1. Natural means | 552 Obliteration (synopsis) | - | - | - | - |
| 565 Misnomer | IV III. Means of communicating ideas / 1. Language generally | 564 Nomenclature (synopsis) | - | - | - | - |
| 567 Grammar | IV III. Means of communicating ideas / 1. Language generally | 568 Solecism (synopsis) | - | - | - | - |
| 586 Allocution | IV III. Means of communicating ideas / 1. Language generally | 587 Response (synopsis) | - | - | - | - |
| 587 Response | IV III. Means of communicating ideas / 1. Language generally | 586 Allocution (synopsis) | - | - | - | - |
| 593 Book | IV III. Means of communicating ideas / 1. Language generally | 592 Correspondence (synopsis) | - | - | - | - |
| 602 Willingness | V I. Volition in general / 1. Acts of Volition | 603 Unwillingness (synopsis) | - | - | - | - |
| 603 Unwillingness | V I. Volition in general / 1. Acts of Volition | 602 Willingness (synopsis) | - | - | - | - |
| 614 Desuetude | V I. Volition in general / 1. Acts of Volition | 613 Habit (synopsis) | - | - | - | - |
| 621 Chance | V II. Prospective volition / 1. Conceptional volition | 620 Intention (synopsis) | - | - | - | - |
| 628 Mid-course | V II. Prospective volition / 1. Conceptional volition | 629 Circuit (synopsis) | - | - | - | - |
| 637 Provision | V II. Prospective volition / 1. Actual Subservience | 638 Waste (synopsis) | - | - | - | - |
| 640 Insufficiency | V II. Prospective volition / 1. Actual Subservience | 641 Redundancy (synopsis) | - | - | - | - |
| 661 Relapse | V II. Prospective volition / 1. Actual Subservience | 660 Restoration (synopsis) | - | - | - | - |
| 663 Bane | V II. Prospective volition / 1. Actual Subservience | 662 Remedy (synopsis) | - | - | - | - |
| 666 Refuge | V II. Prospective volition / 1. Actual Subservience | 667 Pitfall (synopsis) | - | - | - | - |
| 667 Pitfall | V II. Prospective volition / 1. Actual Subservience | 666 Refuge (synopsis) | - | - | - | - |
| 673 Preparation | V II. Prospective volition / 3. Precursory measures | 674 Nonpreparation (synopsis) | - | - | - | - |
| 674 Nonpreparation | V II. Prospective volition / 3. Precursory measures | 673 Preparation (synopsis) | - | - | - | - |
| 711 Auxiliary | V IV. Antagonism / 2. Active Antagonism | 710 Opponent (synopsis) | - | - | - | - |
| 718 Retaliation | V IV. Antagonism / 2. Active Antagonism | 719 Resistance (synopsis) | - | - | - | - |
| 719 Resistance | V IV. Antagonism / 2. Active Antagonism | 718 Retaliation (synopsis) | - | - | - | - |
| 745 Master | V I. General intersocial volition | 746 Servant (synopsis) | - | - | - | - |
| 753 Keeper | V I. General intersocial volition | 754 Prisoner (synopsis) | - | - | - | - |
| 764 Refusal | V II. Special intersocial volition | 763 Offer (synopsis) | - | - | - | - |
| 765 Request | V II. Special intersocial volition | 766 Deprecation (synopsis) | - | - | - | - |
| 768 Promise | V III. Conditional intersocial volition | 768a Release from engagement (synopsis) | - | - | - | - |
| 777 Possession | V IV. Possessive relations / 1. Property in general | 777a Exemption (synopsis) | - | - | - | - |
| 788 Borrowing | V IV. Possessive relations / 2. Transfer of Property | 787 Lending (synopsis) | - | - | - | - |
| 789 Taking | V IV. Possessive relations / 2. Transfer of Property | 790 Restitution (synopsis) | - | - | - | - |
| 812a Value | V IV. Possessive relations / 4. Monetary Relations | 812b Worthlessness (rule) | - | - | [lifetime value](../../seed_queue.json) (queued) | - |
| 812b Worthlessness | V IV. Possessive relations / 4. Monetary Relations | 812a Value (rule) | - | - | - | - |
| 814 Dearness | V IV. Possessive relations / 4. Monetary Relations | 815 Cheapness (synopsis) | - | - | - | - |
| 815 Cheapness | V IV. Possessive relations / 4. Monetary Relations | 814 Dearness (synopsis) | - | - | - | - |
| 838 Rejoicing | VI II. Personal affections | 839 Lamentation (synopsis) | - | - | [gloating](../../seed_queue.json) (queued) | - |
| 839 Lamentation | VI II. Personal affections | 838 Rejoicing (synopsis) | - | - | - | - |
| 891 Enemy | VI III. Sympathetic affections | 890 Friend (synopsis) | - | - | - | - |
| 931 Approbation | VI IV. Moral affections | 932 Disapprobation (synopsis) | - | - | - | - |
| 932 Disapprobation | VI IV. Moral affections | 931 Approbation (synopsis) | - | - | - | - |
| 934 Detraction | VI IV. Moral affections | 933 Flattery (synopsis) | - | - | - | - |
| 937 Vindication | VI IV. Moral affections | 938 Accusation (synopsis) | - | - | - | - |
| 947 Guilt | VI IV. Moral affections | 946 Innocence (synopsis) | - | - | - | - |
| 949 Bad Man | VI IV. Moral affections | 948 Good Man (synopsis) | - | - | - | - |
| 964 Illegality | VI IV. Moral affections | 963 Legality (synopsis) | - | - | - | - |
| 977 Angel | VI V. Religious affections | 978 Satan (synopsis) | - | - | - | - |
| 978 Satan | VI V. Religious affections | 977 Angel (synopsis) | - | - | - | - |
| 980 Demon | VI V. Religious affections | 979 Jupiter (synopsis) | - | - | - | - |
| 981 Heaven | VI V. Religious affections | 982 Hell (synopsis) | - | - | - | - |
| 985 Judeo-Christian Revelation | VI V. Religious affections | 986 Pseudo-Revelation (synopsis) | - | - | - | - |
| 986 Pseudo-Revelation | VI V. Religious affections | 985 Judeo-Christian Revelation (synopsis) | - | - | - | - |

## singleton_empty (61)

| head | section | opposed head | its traits | queued | parked | secondary of |
|---|---|---|---|---|---|---|
| 29 Mean | I III. Quantity | - | - | - | [mean](../../seed_queue.json) (queued) | - |
| 465b Identification | IV II. Precursory conditions and operations | - | - | - | - | - |
| 480a Discovery | IV V. Results of reasoning | - | - | - | - | - |
| 513 Oracle | IV VI. Extension of thought / 1. To the Past | - | - | - | - | - |
| 520 Equivocalness | IV I. Nature of ideas communicated | - | - | - | - | - |
| 524 Interpreter | IV I. Nature of ideas communicated | - | - | - | - | - |
| 534 Messenger | IV II. Modes of communication | - | - | - | - | - |
| 550 Indication | IV III. Means of communicating ideas / 1. Natural means | - | - | - | - | - |
| 553 Recorder | IV III. Means of communicating ideas / 1. Natural means | - | - | - | - | - |
| 560 Language | IV III. Means of communicating ideas / 1. Language generally | - | - | - | [language](../../seed_queue.json) (queued) | - |
| 569 Style | IV III. Means of communicating ideas / 1. Language generally | - | - | - | - | - |
| 615a Absence of Motive | V I. Volition in general / 2. Causes of Volition | - | - | - | - | - |
| 617 Pretext | V I. Volition in general / 2. Causes of Volition | - | - | - | - | - |
| 631 Instrumentality | V II. Prospective volition / 1. Actual Subservience | - | - | - | - | - |
| 634 Substitute | V II. Prospective volition / 1. Actual Subservience | - | - | - | - | - |
| 690 Agent | V III. Voluntary action / 1. Simple voluntary Action | - | - | - | - | - |
| 694 Director | V III. Voluntary action / 2. Complex Voluntary Action | - | - | - | - | - |
| 715 Defiance | V IV. Antagonism / 2. Active Antagonism | - | - | - | - | - |
| 727 Arms | V IV. Antagonism / 2. Active Antagonism | - | - | - | - | - |
| 728 Arena | V IV. Antagonism / 2. Active Antagonism | - | - | - | - | - |
| 733 Trophy | V V. Results of voluntary action | - | - | - | - | - |
| 744 Compulsion | V I. General intersocial volition | - | - | - | - | - |
| 747 Scepter | V I. General intersocial volition | - | - | - | - | - |
| 752 Prison | V I. General intersocial volition | - | - | - | - | - |
| 757 Resignation | V I. General intersocial volition | - | - | - | - | - |
| 758 Consignee | V I. General intersocial volition | - | - | - | - | - |
| 762 Consent | V II. Special intersocial volition | - | - | - | [acquiescence](../../seed_queue.json) (queued) | - |
| 767 Petitioner | V II. Special intersocial volition | - | - | - | - | - |
| 769 Compact | V III. Conditional intersocial volition | - | - | - | - | - |
| 771 Security | V III. Conditional intersocial volition | - | - | - | [secure](../../seed_queue.json) (queued) | - |
| 780 Property | V IV. Possessive relations / 1. Property in general | - | - | - | [device ownership](../../seed_queue.json) (queued) | - |
| 791 Stealing | V IV. Possessive relations / 2. Transfer of Property | - | - | - | [thieving](../../seed_queue.json) (queued) | - |
| 792 Thief | V IV. Possessive relations / 2. Transfer of Property | - | - | - | - | - |
| 793 Booty | V IV. Possessive relations / 2. Transfer of Property | - | - | - | - | - |
| 797 Merchant | V IV. Possessive relations / 3. Interchange of Property | - | - | - | - | - |
| 798 Merchandise | V IV. Possessive relations / 3. Interchange of Property | - | - | - | - | - |
| 799a Stock Market | V IV. Possessive relations / 3. Interchange of Property | - | - | - | - | - |
| 799b Securities | V IV. Possessive relations / 3. Interchange of Property | - | - | - | - | - |
| 801 Treasurer | V IV. Possessive relations / 4. Monetary Relations | - | - | - | - | - |
| 802 Treasury | V IV. Possessive relations / 4. Monetary Relations | - | - | - | - | - |
| 820 Affections | VI I. Affections in general | - | - | - | - | - |
| 824 Excitation | VI I. Affections in general | - | - | - | - | - |
| 854 Fop | VI II. Personal affections | - | - | - | - | - |
| 857 Laughingstock | VI II. Personal affections | - | - | - | - | - |
| 872 Prodigy | VI II. Personal affections | - | - | - | - | - |
| 877 Title | VI II. Personal affections | - | - | - | - | - |
| 899 Favorite | VI III. Sympathetic affections | - | - | - | - | - |
| 901a Sullenness | VI III. Sympathetic affections | - | - | - | - | - |
| 905 Divorce | VI III. Sympathetic affections | - | - | - | - | - |
| 909 Threat | VI III. Sympathetic affections | - | - | - | - | - |
| 927a Exemption | VI IV. Moral affections | - | - | - | - | - |
| 930 Contempt | VI IV. Moral affections | - | - | - | - | - |
| 941 Knave | VI IV. Moral affections | - | - | - | - | - |
| 952 Atonement | VI IV. Moral affections | - | - | - | - | - |
| 962 Libertine | VI IV. Moral affections | - | - | - | - | - |
| 974 Penalty | VI IV. Moral affections | - | - | - | - | - |
| 975 Scourge | VI IV. Moral affections | - | - | - | - | - |
| 993 Spell | VI V. Religious affections | - | - | - | - | - |
| 994 Sorcerer | VI V. Religious affections | - | - | - | - | - |
| 999 Canonicals | VI V. Religious affections | - | - | - | - | - |
| 1000 Temple | VI V. Religious affections | - | - | - | - | - |

## queued_only (9)

| head | section | opposed head | its traits | queued | parked | secondary of |
|---|---|---|---|---|---|---|
| 357 Organization | III III. Organic matter / 1. Vitality in general | 358 Inorganization (synopsis) | - | [Organization (HEXACO)](../../seed_queue.json) (queued) | - | - |
| 391 Insipidity | III III. Organic matter / 1. Sensation in general | 390 Taste (synopsis) | - | [bland](../../seed_queue.json) (queued), [vanilla](../../seed_queue.json) (queued) | - | - |
| 450a Absence or want of Intellect | IV I. Operations of intellect in general | 450 Intellect (synopsis) | [cerebral](../../traits/instructions/cerebral.json) | [Intellect (BFAS)](../../seed_queue.json) (queued), [Intellect (IPIP-NEO)](../../seed_queue.json) (queued) | - | - |
| 504 Madman | IV V. Results of reasoning | - | - | [hypochondriac](../../seed_queue.json) (queued) | - | - |
| 611 Predetermination | V I. Volition in general / 1. Acts of Volition | 612 Impulse (synopsis) | [improvisational](../../traits/instructions/improvisational.json), [impulsive](../../traits/instructions/impulsive.json), [spontaneous](../../traits/instructions/spontaneous.json) | [deterministic](../../seed_queue.json) (queued) | - | - |
| 799 Mart | V IV. Possessive relations / 3. Interchange of Property | - | - | [free-market](../../seed_queue.json) (queued) | - | - |
| 897 Love | VI III. Sympathetic affections | 898 Hate (synopsis) | [xenophobic](../../traits/instructions/xenophobic.json) | [devoted](../../seed_queue.json) (queued), [enthusiastic (BFAS)](../../seed_queue.json) (queued) | - | - |
| 915 Condolence | VI III. Sympathetic affections | - | - | [Sympathy (IPIP-NEO)](../../seed_queue.json) (queued) | - | - |
| 967 Judge | VI IV. Moral affections | - | - | [judging (MBTI)](../../seed_queue.json) (queued) | - | - |

## partly_covered (50)

| head | section | opposed head | its traits | queued | parked | secondary of |
|---|---|---|---|---|---|---|
| 4 Unsubstantiality | I I. Existence | 3 Substantiality (synopsis) | - | - | - | [ethereal](../../traits/instructions/ethereal.json) |
| 10 Irrelation | I II. Relation | 9 Relation (synopsis) | - | - | - | [insular](../../traits/instructions/insular.json), [isolated](../../traits/instructions/isolated.json) |
| 18 Dissimilarity | I II. Relation | 17 Similarity (synopsis) | - | - | - | [divergent](../../traits/instructions/divergent.json) |
| 58 Order | I IV. Order | 59 Disorder (synopsis) | [chaotic](../../traits/instructions/chaotic.json), [disorganized](../../traits/instructions/disorganized.json) | [Orderliness (BFAS)](../../seed_queue.json) (queued), [Orderliness (IPIP-NEO)](../../seed_queue.json) (queued) | [orderly](../../seed_queue.json) (queued), [systematic](../../seed_queue.json) (queued) | [methodical](../../traits/instructions/methodical.json) |
| 87 Unity | I V. Number | 88 Accompaniment (synopsis) | - | - | - | [single](../../traits/instructions/single.json) |
| 141 Permanence | I VII. Change | 140 Change (synopsis) | - | - | - | [conservative](../../traits/instructions/conservative.json) |
| 157 Power | I VIII. Causation | 158 Impotence (synopsis) | [helpless](../../traits/instructions/helpless.json) | [Self-Efficacy (IPIP-NEO)](../../seed_queue.json) (queued) | [empowered](../../seed_queue.json) (queued) | [competent](../../traits/instructions/competent.json) |
| 160 Weakness | I VIII. Causation | 159 Strength (synopsis) | [muscular](../../traits/instructions/muscular.json) | - | - | [fragile](../../traits/instructions/fragile.json) |
| 172 Physical Inertness | I VIII. Causation | 171 Physical Energy (synopsis) | [intense](../../traits/instructions/intense.json) | - | - | [passive](../../traits/instructions/passive.json) |
| 212 Verticality | II II. Dimensions | 213 Horizontality (synopsis) | - | - | - | [straight](../../traits/instructions/straight.json) |
| 220 Exteriority | II II. Dimensions / 1. General | 221 Interiority (synopsis) | - | - | - | [eccentric](../../traits/instructions/eccentric.json), [superficial](../../traits/instructions/superficial.json) |
| 276 Impulse | II IV. Motion | 277 Recoil (synopsis) | [reactive](../../traits/instructions/reactive.json) | - | - | [impulsive](../../traits/instructions/impulsive.json) |
| 278 Direction | II IV. Motion | 279 Deviation (synopsis) | - | - | - | [straight](../../traits/instructions/straight.json) |
| 279 Deviation | II IV. Motion | 278 Direction (synopsis) | - | - | - | [erratic](../../traits/instructions/erratic.json) |
| 282 Progression | II IV. Motion | 283 Regression (synopsis) | - | - | - | [progressive](../../traits/instructions/progressive.json) |
| 315 Agitation | II IV. Motion | - | - | - | - | [restless](../../traits/instructions/restless.json), [turbulent](../../traits/instructions/turbulent.json) |
| 320 Levity | III I. Matter in general | 319 Gravity (synopsis) | - | - | - | [ethereal](../../traits/instructions/ethereal.json) |
| 324 Softness | III II. Inorganic matter | 323 Hardness (synopsis) | [inflexible](../../traits/instructions/inflexible.json) | - | [tender](../../seed_queue.json) (queued) | [flexible](../../traits/instructions/flexible.json) |
| 359 Life | III III. Organic matter / 1. Vitality in general | 360 Death (synopsis) | - | - | - | [animated](../../traits/instructions/animated.json) |
| 372 Mankind | III III. Organic matter / 1. Vitality in general | - | - | - | - | [cosmopolitan](../../traits/instructions/cosmopolitan.json), [humanitarian](../../traits/instructions/humanitarian.json) |
| 376 Physical Insensibility | III III. Organic matter / 1. Sensation in general | 375 Physical Sensibility (synopsis) | [socially-perceptive](../../traits/instructions/socially_perceptive.json) | - | - | [callous](../../traits/instructions/callous.json), [thick-skinned](../../traits/instructions/thick_skinned.json) |
| 425 Transparency | III III. Organic matter / 1. Sensation in general | 426 Opacity (synopsis) | [opaque](../../traits/instructions/opaque.json) | - | - | [transparent](../../traits/instructions/transparent.json) |
| 480 Judgment | IV V. Results of reasoning | 481 Misjudgment (synopsis) | [ageist](../../traits/instructions/ageist.json), [closed-minded](../../traits/instructions/closed_minded.json), [tunnel-visioned](../../traits/instructions/tunnel_visioned.json) | [judging (MBTI)](../../seed_queue.json) (queued) | [conclusive](../../seed_queue.json) (queued) | [decisive](../../traits/instructions/decisive.json), [judgmental](../../traits/instructions/judgmental.json) |
| 505 Memory | IV VI. Extension of thought / 1. To the Past | 506 Oblivion (synopsis) | [forgetful](../../traits/instructions/forgetful.json), [oblivious](../../traits/instructions/oblivious.json) | - | - | [retentive](../../traits/instructions/retentive.json) |
| 509 Disappointment | IV VI. Extension of thought / 1. To the Past | - | - | - | - | [bitter](../../traits/instructions/bitter.json) |
| 542 School | IV II. Modes of communication | - | - | - | [academic](../../seed_queue.json) (queued) | [educational](../../traits/instructions/educational.json) |
| 577 Ornament | IV III. Means of communicating ideas / 1. Language generally | 576 Plainness (synopsis) | [dry](../../traits/instructions/dry.json), [grounded](../../traits/instructions/grounded.json), [plain-spoken](../../traits/instructions/plain_spoken.json) | - | - | [bombastic](../../traits/instructions/bombastic.json) |
| 641 Redundancy | V II. Prospective volition / 1. Actual Subservience | 640 Insufficiency (synopsis) | - | - | - | [extravagant](../../traits/instructions/extravagant.json) |
| 656 Salubrity | V II. Prospective volition / 1. Actual Subservience | 657 Insalubrity (synopsis) | - | - | - | [benign](../../traits/instructions/benign.json), [healthy](../../traits/instructions/healthy.json) |
| 704 Difficulty | V IV. Antagonism / 1. Conditional Antagonism | 705 Facility (synopsis) | [accessible](../../traits/instructions/accessible.json), [flexible](../../traits/instructions/flexible.json) | [tough](../../seed_queue.json) (queued) | - | [tough (HEXACO)](../../traits/instructions/tough_hexaco.json) |
| 710 Opponent | V IV. Antagonism / 2. Active Antagonism | 711 Auxiliary (synopsis) | - | - | - | [antagonistic (Big Five)](../../traits/instructions/antagonistic_big_five.json) |
| 726 Combatant | V IV. Antagonism / 2. Active Antagonism | - | - | - | - | [partisan](../../traits/instructions/partisan.json) |
| 737a Government | V I. General intersocial volition | - | - | - | - | [aristocratic](../../traits/instructions/aristocratic.json), [socialist](../../traits/instructions/socialist.json) |
| 741 Command | V I. General intersocial volition | - | - | - | - | [prescriptive](../../traits/instructions/prescriptive.json) |
| 784 Giving | V IV. Possessive relations / 2. Transfer of Property | 785 Receiving (synopsis) | [receiving gifts](../../traits/instructions/receiving_gifts.json) | - | - | [generous](../../traits/instructions/generous.json) |
| 812 Price | V IV. Possessive relations / 4. Monetary Relations | 813 Discount (synopsis) | - | - | - | [mercenary](../../traits/instructions/mercenary.json) |
| 827 Pleasure | VI II. Personal affections | 828 Pain (synopsis) | [in chronic pain](../../traits/instructions/in_chronic_pain.json), [stressed](../../traits/instructions/stressed.json) | - | - | [hedonistic](../../traits/instructions/hedonistic.json), [joyful](../../traits/instructions/joyful.json) |
| 844 Humorist | VI II. Personal affections | - | - | - | - | [witty](../../traits/instructions/witty.json) |
| 890 Friend | VI III. Sympathetic affections | 891 Enemy (synopsis) | - | - | - | [friendly](../../traits/instructions/friendly.json) |
| 895 Discourtesy | VI III. Sympathetic affections | 894 Courtesy (synopsis) | [polite](../../traits/instructions/polite.json), [tactful](../../traits/instructions/tactful.json) | - | [unceremonious](../../seed_queue.json) (queued), [undiplomatic](../../seed_queue.json) (queued) | [rude](../../traits/instructions/rude.json) |
| 920 Jealousy | VI III. Sympathetic affections | - | - | - | - | [envious](../../traits/instructions/envious.json) |
| 933 Flattery | VI IV. Moral affections | 934 Detraction (synopsis) | - | - | - | [sycophantic](../../traits/instructions/sycophantic.json) |
| 935 Flatterer | VI IV. Moral affections | 936 Detractor (synopsis) | [detractor](../../traits/instructions/detractor.json) | - | - | [sycophantic](../../traits/instructions/sycophantic.json) |
| 946 Innocence | VI IV. Moral affections | 947 Guilt (synopsis) | - | - | - | [harmless](../../traits/instructions/harmless.json) |
| 948 Good Man | VI IV. Moral affections | 949 Bad Man (synopsis) | - | - | - | [good](../../traits/instructions/good.json) |
| 954 Intemperance | VI IV. Moral affections | 953 Temperance (synopsis) | [abstemious](../../traits/instructions/abstemious.json), [temperate](../../traits/instructions/temperate.json) | [Immoderation (IPIP-NEO)](../../seed_queue.json) (queued), [indulgent](../../seed_queue.json) (queued) | [intemperate](../../seed_queue.json) (queued) | [self-indulgent](../../traits/instructions/self_indulgent.json) |
| 987 Piety | VI V. Religious affections | 988 Impiety (synopsis) | - | [devoted](../../seed_queue.json) (queued) | [preoccupied-with-religion](../../seed_queue.json) (queued) | [Christian](../../traits/instructions/christian.json), [reverent](../../traits/instructions/reverent.json) |
| 988 Impiety | VI V. Religious affections | 987 Piety (synopsis) | - | - | - | [irreverent](../../traits/instructions/irreverent.json) |
| 995 Churchdom | VI V. Religious affections | - | - | - | - | [Christian](../../traits/instructions/christian.json) |
| 996 Clergy | VI V. Religious affections | 997 Laity (synopsis) | [secular](../../traits/instructions/secular.json) | - | - | [reverent](../../traits/instructions/reverent.json) |

## Not character (188)

Rated 0 by the head-scope check; the reasons are in [head_scope.json](./head_scope.json).  A covered head here is one a trait was placed on although its adjectives are not about character.

| head | section | state | its traits | queued | secondary of |
|---|---|---|---|---|---|
| 25 Quantity | I III. Quantity | covered | [quantitative](../../traits/instructions/quantitative.json) | - | - |
| 49 Decomposition | I III. Quantity | covered | [reductionist](../../traits/instructions/reductionist.json) | - | [analytical](../../traits/instructions/analytical.json) |
| 55 Exclusion | I III. Quantity | covered | [exclusionary](../../traits/instructions/exclusionary.json) | [exclusive](../../seed_queue.json) (queued) | - |
| 76 Inclusion | I IV. Order | covered | [inclusive](../../traits/instructions/inclusive.json) | - | - |
| 120 Synchronism | I VI. Time | covered | [contemporary](../../traits/instructions/contemporary.json) | - | - |
| 156 Chance | I VIII. Causation | covered | [casual](../../traits/instructions/casual.json) | - | - |
| 184 Location | II I. Space in general | empty | - | - | - |
| 192 Size | II II. Dimensions | covered | [fat](../../traits/instructions/fat.json) | - | - |
| 203 Narrowness. Thinness | II II. Dimensions | covered | [thin](../../traits/instructions/thin.json) | - | [slight](../../traits/instructions/slight.json) |
| 214 Pendency | II II. Dimensions | partly | - | - | [dependent](../../traits/instructions/dependent.json) |
| 227 Circumjacence | II II. Dimensions | partly | - | - | [suburban](../../traits/instructions/suburban.json) |
| 251 Flatness | II III. Form | partly | - | - | [flat](../../traits/instructions/flat.json) |
| 260 Opening | II III. Form | covered | [open (Big Five)](../../traits/instructions/open_big_five.json), [open (HEXACO)](../../traits/instructions/open_hexaco.json) | [Openness (BFAS)](../../seed_queue.json) (queued) | - |
| 261 Closure | II III. Form | covered | [closed (Big Five)](../../traits/instructions/closed_big_five.json) | - | - |
| 290 Convergence | II IV. Motion | covered | [convergent](../../traits/instructions/convergent.json) | - | - |
| 291 Divergence | II IV. Motion | covered | [divergent](../../traits/instructions/divergent.json) | - | - |
| 304 Shortcoming | II IV. Motion | partly | - | - | [short](../../traits/instructions/short.json) |
| 334 Gaseity | III II. Inorganic matter | covered | [ethereal](../../traits/instructions/ethereal.json) | - | - |
| 340 Dryness | III II. Inorganic matter | partly | - | - | [dry](../../traits/instructions/dry.json) |
| 419 Deafness | III III. Organic matter | partly | - | - | [deaf](../../traits/instructions/deaf.json) |
| 422 Dimness | III III. Organic matter | partly | - | - | [dull](../../traits/instructions/dull.json) |
| 426 Opacity | III III. Organic matter | covered | [opaque](../../traits/instructions/opaque.json) | - | - |
| 429 Achromatism | III III. Organic matter | covered | [fair-skinned](../../traits/instructions/fair_skinned.json) | - | - |
| 430 Whiteness | III III. Organic matter | covered | [blond](../../traits/instructions/blond.json) | - | - |
| 441 Vision | III III. Organic matter | covered | [visual (VARK)](../../traits/instructions/visual_vark.json) | - | - |
| 442 Blindness | III III. Organic matter | covered | [blind](../../traits/instructions/blind.json) | - | - |
| 454 Topic | IV I. Operations of intellect in general | empty | - | - | - |
| 461 Inquiry | IV II. Precursory conditions and operations | covered | [critical](../../traits/instructions/critical.json), [exploratory](../../traits/instructions/exploratory.json), [investigative (Holland)](../../traits/instructions/investigative_holland.json), [socratic](../../traits/instructions/socratic.json) | - | [analytical](../../traits/instructions/analytical.json), [inquisitive](../../traits/instructions/inquisitive.json) |
| 462 Answer | IV II. Precursory conditions and operations | empty | - | - | - |
| 463 Experiment | IV II. Precursory conditions and operations | covered | [empirical](../../traits/instructions/empirical.json), [experiential](../../traits/instructions/experiential.json) | - | [speculative](../../traits/instructions/speculative.json) |
| 464 Comparison | IV II. Precursory conditions and operations | empty | - | - | - |
| 464a Incomparability | IV II. Precursory conditions and operations | empty | - | - | - |
| 466 Measurement | IV II. Precursory conditions and operations | empty | - | - | - |
| 467 Evidence | IV III. Materials for reasoning | covered | [data-driven](../../traits/instructions/data_driven.json) | - | - |
| 468 Counter Evidence | IV III. Materials for reasoning | empty | - | - | - |
| 469 Qualification | IV III. Materials for reasoning | empty | - | - | - |
| 470 Possibility | IV III. Materials for reasoning | empty | - | - | - |
| 478 Demonstration | IV IV. Reasoning processes | partly | - | - | [decisive](../../traits/instructions/decisive.json) |
| 479 Confutation | IV IV. Reasoning processes | empty | - | - | - |
| 482 Overestimation | IV V. Results of reasoning | covered | [optimistic](../../traits/instructions/optimistic.json), [pessimistic](../../traits/instructions/pessimistic.json) | - | - |
| 496 Maxim | IV V. Results of reasoning | empty | - | - | - |
| 507 Expectation | IV VI. Extension of thought | empty | - | - | - |
| 511 Prediction | IV VI. Extension of thought | empty | - | - | - |
| 512 Omen | IV VI. Extension of thought | empty | - | - | - |
| 514 Supposition | IV VII. Creative thought | covered | [theoretical](../../traits/instructions/theoretical.json) | - | [speculative](../../traits/instructions/speculative.json) |
| 514a Analogy | IV VII. Creative thought | covered | [stream-of-consciousness](../../traits/instructions/stream_of_consciousness.json) | - | - |
| 516 Meaning | IV I. Nature of ideas communicated | partly | - | - | [expressive](../../traits/instructions/expressive.json), [literal](../../traits/instructions/literal.json) |
| 517 Unmeaningness | IV I. Nature of ideas communicated | empty | - | - | - |
| 521 Metaphor | IV I. Nature of ideas communicated | covered | [figurative](../../traits/instructions/figurative.json), [ironic](../../traits/instructions/ironic.json), [metaphorical](../../traits/instructions/metaphorical.json) | - | - |
| 523 Misinterpretation | IV I. Nature of ideas communicated | empty | - | - | - |
| 526 Latency. Implication | IV II. Modes of communication | covered | [high-context (Hall)](../../traits/instructions/high_context_hall.json) | - | - |
| 527a Correction | IV II. Modes of communication | empty | - | - | - |
| 530 Ambush | IV II. Modes of communication | empty | - | - | - |
| 531 Publication | IV II. Modes of communication | empty | - | - | - |
| 532 News | IV II. Modes of communication | covered | [news-junkie](../../traits/instructions/news_junkie.json) | - | - |
| 533 Secret | IV II. Modes of communication | empty | - | - | - |
| 538 Misteaching | IV II. Modes of communication | empty | - | - | - |
| 541 Learner | IV II. Modes of communication | empty | - | - | - |
| 546 Untruth | IV II. Modes of communication | empty | - | - | - |
| 549 Exaggeration | IV II. Modes of communication | empty | - | - | - |
| 552 Obliteration | IV III. Means of communicating ideas | empty | - | - | - |
| 554 Representation | IV III. Means of communicating ideas | empty | - | - | - |
| 555 Misrepresentation | IV III. Means of communicating ideas | empty | - | - | - |
| 556 Painting | IV III. Means of communicating ideas | empty | - | - | - |
| 557 Sculpture | IV III. Means of communicating ideas | empty | - | - | - |
| 558 Engraving | IV III. Means of communicating ideas | empty | - | - | - |
| 561 Letter | IV III. Means of communicating ideas | covered | [literal](../../traits/instructions/literal.json) | - | - |
| 562 Word | IV III. Means of communicating ideas | empty | - | - | - |
| 563 Neologism | IV III. Means of communicating ideas | empty | - | - | - |
| 564 Nomenclature | IV III. Means of communicating ideas | empty | - | - | - |
| 566 Phrase | IV III. Means of communicating ideas | empty | - | - | - |
| 568 Solecism | IV III. Means of communicating ideas | empty | - | - | - |
| 571 Obscurity | IV III. Means of communicating ideas | empty | - | - | - |
| 580 Voice | IV III. Means of communicating ideas | empty | - | - | - |
| 581 Aphony | IV III. Means of communicating ideas | covered | [deaf](../../traits/instructions/deaf.json) | - | [emotionally-inarticulate](../../traits/instructions/emotionally_inarticulate.json) |
| 588 Conversation | IV III. Means of communicating ideas | empty | - | - | - |
| 589 Soliloquy | IV III. Means of communicating ideas | empty | - | - | - |
| 590 Writing | IV III. Means of communicating ideas | covered | [read-write (VARK)](../../traits/instructions/read_write_vark.json) | - | - |
| 591 Printing | IV III. Means of communicating ideas | empty | - | - | - |
| 592 Correspondence | IV III. Means of communicating ideas | empty | - | - | - |
| 594 Description | IV III. Means of communicating ideas | covered | [descriptive](../../traits/instructions/descriptive.json), [narrative](../../traits/instructions/narrative.json) | - | - |
| 595 Dissertation | IV III. Means of communicating ideas | empty | - | - | - |
| 596 Compendium | IV III. Means of communicating ideas | empty | - | - | - |
| 597 Poetry | IV III. Means of communicating ideas | covered | [poetic](../../traits/instructions/poetic.json) | - | - |
| 610 Rejection | V I. Volition in general | empty | - | - | - |
| 613 Habit | V I. Volition in general | partly | - | - | [conventional](../../traits/instructions/conventional.json) |
| 619 Evil | V I. Volition in general | partly | - | - | [evil](../../traits/instructions/evil.json), [mischievous](../../traits/instructions/mischievous.json) |
| 620 Intention | V II. Prospective volition | queued | - | [purposeful](../../seed_queue.json) (queued) | - |
| 622 Pursuit | V II. Prospective volition | empty | - | - | - |
| 624 Relinquishment | V II. Prospective volition | queued | - | [Withdrawal (BFAS)](../../seed_queue.json) (queued) | - |
| 626 Plan | V II. Prospective volition | covered | [strategic](../../traits/instructions/strategic.json) | - | - |
| 629 Circuit | V II. Prospective volition | empty | - | - | - |
| 630 Requirement | V II. Prospective volition | empty | - | - | - |
| 633 Instrument | V II. Prospective volition | covered | [mechanistic](../../traits/instructions/mechanistic.json) | - | - |
| 635 Materials | V II. Prospective volition | empty | - | - | - |
| 636 Store | V II. Prospective volition | empty | - | - | - |
| 638 Waste | V II. Prospective volition | empty | - | - | - |
| 651 Imperfection | V II. Prospective volition | empty | - | - | - |
| 655 Disease | V II. Prospective volition | covered | [chronically-ill](../../traits/instructions/chronically_ill.json), [sickly](../../traits/instructions/sickly.json) | - | [squeamish](../../traits/instructions/squeamish.json) |
| 657 Insalubrity | V II. Prospective volition | empty | - | - | - |
| 659 Deterioration | V II. Prospective volition | empty | - | - | - |
| 660 Restoration | V II. Prospective volition | empty | - | - | - |
| 662 Remedy | V II. Prospective volition | empty | - | - | - |
| 664 Safety | V II. Prospective volition | covered | [financially secure](../../traits/instructions/financially_secure.json) | - | [harmless](../../traits/instructions/harmless.json) |
| 668 Warning | V II. Prospective volition | partly | - | - | [cautious](../../traits/instructions/cautious.json) |
| 669 Alarm | V II. Prospective volition | empty | - | - | - |
| 671 Escape | V II. Prospective volition | empty | - | - | - |
| 672 Deliverance | V II. Prospective volition | empty | - | - | - |
| 676 Undertaking | V II. Prospective volition | partly | - | - | [adventurous](../../traits/instructions/adventurous.json) |
| 677 Use | V II. Prospective volition | empty | - | - | - |
| 678 Disuse | V II. Prospective volition | empty | - | - | - |
| 679 Misuse | V II. Prospective volition | empty | - | - | - |
| 680 Action | V III. Voluntary action | empty | - | - | - |
| 688 Fatigue | V III. Voluntary action | covered | [sleep-deprived](../../traits/instructions/sleep_deprived.json) | - | - |
| 689 Refreshment | V III. Voluntary action | empty | - | - | - |
| 691 Workshop | V III. Voluntary action | empty | - | - | - |
| 693 Direction | V III. Voluntary action | covered | [hands-on](../../traits/instructions/hands_on.json), [micromanaging](../../traits/instructions/micromanaging.json), [paternalistic](../../traits/instructions/paternalistic.json) | - | [controlling](../../traits/instructions/controlling.json) |
| 695 Advice | V III. Voluntary action | partly | - | - | [wise](../../traits/instructions/wise.json) |
| 696 Council | V III. Voluntary action | empty | - | - | - |
| 724 Mediation | V IV. Antagonism | covered | [diplomatic](../../traits/instructions/diplomatic.json), [moderate](../../traits/instructions/moderate.json) | [interventionist](../../seed_queue.json) (queued) | - |
| 729 Completion | V V. Results of voluntary action | empty | - | - | - |
| 730 Noncompletion | V V. Results of voluntary action | empty | - | - | - |
| 731 Success | V V. Results of voluntary action | covered | [achiever (VALS)](../../traits/instructions/achiever_vals.json) | - | - |
| 732 Failure | V V. Results of voluntary action | covered | [defeatist](../../traits/instructions/defeatist.json) | - | - |
| 734 Prosperity | V V. Results of voluntary action | covered | [flourishing](../../traits/instructions/flourishing.json) | - | - |
| 735 Adversity | V V. Results of voluntary action | empty | - | - | - |
| 746 Servant | V I. General intersocial volition | empty | - | - | - |
| 754 Prisoner | V I. General intersocial volition | empty | - | - | - |
| 755 Commission | V I. General intersocial volition | empty | - | - | - |
| 756 Abrogation | V I. General intersocial volition | empty | - | - | - |
| 759 Deputy | V I. General intersocial volition | empty | - | - | - |
| 763 Offer | V II. Special intersocial volition | empty | - | - | - |
| 766 Deprecation | V II. Special intersocial volition | empty | - | - | - |
| 768a Release from engagement | V III. Conditional intersocial volition | empty | - | - | - |
| 770 Conditions | V III. Conditional intersocial volition | empty | - | - | - |
| 775 Acquisition | V IV. Possessive relations | empty | - | - | - |
| 776 Loss | V IV. Possessive relations | empty | - | - | - |
| 777a Exemption | V IV. Possessive relations | empty | - | - | - |
| 782 Relinquishment | V IV. Possessive relations | empty | - | - | - |
| 783 Transfer | V IV. Possessive relations | empty | - | - | - |
| 785 Receiving | V IV. Possessive relations | covered | [receiving gifts](../../traits/instructions/receiving_gifts.json) | - | - |
| 786 Apportionment | V IV. Possessive relations | empty | - | - | - |
| 787 Lending | V IV. Possessive relations | empty | - | - | - |
| 790 Restitution | V IV. Possessive relations | empty | - | - | - |
| 794 Barter | V IV. Possessive relations | empty | - | - | - |
| 795 Purchase | V IV. Possessive relations | empty | - | - | - |
| 796 Sale | V IV. Possessive relations | empty | - | - | - |
| 800 Money | V IV. Possessive relations | covered | [new money](../../traits/instructions/new_money.json), [old money](../../traits/instructions/old_money.json) | - | - |
| 805 Credit | V IV. Possessive relations | empty | - | - | - |
| 806 Debt | V IV. Possessive relations | empty | - | - | - |
| 807 Payment | V IV. Possessive relations | empty | - | - | - |
| 808 Nonpayment | V IV. Possessive relations | empty | - | - | - |
| 809 Expenditure | V IV. Possessive relations | empty | - | - | - |
| 810 Receipt | V IV. Possessive relations | empty | - | - | - |
| 811 Accounts | V IV. Possessive relations | covered | [accountable](../../traits/instructions/accountable.json) | - | - |
| 813 Discount | V IV. Possessive relations | empty | - | - | - |
| 833 Regret | VI II. Personal affections | covered | [nostalgic](../../traits/instructions/nostalgic.json) | - | - |
| 834 Relief | VI II. Personal affections | empty | - | - | - |
| 835 Aggravation | VI II. Personal affections | empty | - | - | - |
| 845 Beauty | VI II. Personal affections | covered | [good-looking](../../traits/instructions/good_looking.json) | - | - |
| 846 Ugliness | VI II. Personal affections | covered | [plain-looking](../../traits/instructions/plain_looking.json) | - | - |
| 847 Ornament | VI II. Personal affections | empty | - | - | - |
| 847a Jewelry | VI II. Personal affections | empty | - | - | - |
| 848 Blemish | VI II. Personal affections | empty | - | - | - |
| 870 Wonder | VI II. Personal affections | covered | [wide-eyed](../../traits/instructions/wide_eyed.json) | - | [open (HEXACO)](../../traits/instructions/open_hexaco.json) |
| 871 Expectance | VI II. Personal affections | empty | - | - | - |
| 874 Disrepute | VI II. Personal affections | covered | [stigmatized](../../traits/instructions/stigmatized.json) | - | - |
| 883 Celebration | VI II. Personal affections | empty | - | - | - |
| 896 Congratulation | VI III. Sympathetic affections | empty | - | - | - |
| 903 Marriage | VI III. Sympathetic affections | covered | [married](../../traits/instructions/married.json), [monogamous](../../traits/instructions/monogamous.json), [polyandrous](../../traits/instructions/polyandrous.json), [polygamous](../../traits/instructions/polygamous.json), [polygynous](../../traits/instructions/polygynous.json) | - | - |
| 904 Celibacy | VI III. Sympathetic affections | covered | [asexual](../../traits/instructions/asexual.json), [single](../../traits/instructions/single.json) | - | - |
| 908 Malediction | VI III. Sympathetic affections | empty | - | - | - |
| 925 Undueness | VI IV. Moral affections | empty | - | - | - |
| 938 Accusation | VI IV. Moral affections | empty | - | - | - |
| 956 Fasting | VI IV. Moral affections | empty | - | - | - |
| 963 Legality | VI IV. Moral affections | empty | - | - | - |
| 965 Jurisdiction | VI IV. Moral affections | empty | - | - | - |
| 966 Tribunal | VI IV. Moral affections | empty | - | - | - |
| 968 Lawyer | VI IV. Moral affections | empty | - | - | - |
| 969 Lawsuit | VI IV. Moral affections | empty | - | - | - |
| 970 Acquittal | VI IV. Moral affections | empty | - | - | - |
| 971 Condemnation | VI IV. Moral affections | covered | [judgmental](../../traits/instructions/judgmental.json) | - | - |
| 972 Punishment | VI IV. Moral affections | empty | - | - | - |
| 973 Reward | VI IV. Moral affections | empty | - | - | - |
| 979 Jupiter | VI V. Religious affections | empty | - | - | - |
| 982 Hell | VI V. Religious affections | empty | - | - | - |
| 992 Sorcery | VI V. Religious affections | covered | [mystical](../../traits/instructions/mystical.json), [New Age](../../traits/instructions/new_age.json) | - | - |
| 998 Rite | VI V. Religious affections | covered | [ritualistic](../../traits/instructions/ritualistic.json) | - | - |

## Most crowded heads

| head | traits with it as primary |
|---|---|
| 188 Inhabitant (18) | [African](../../traits/instructions/african.json), [American](../../traits/instructions/american.json), [Australian](../../traits/instructions/australian.json), [Brazilian](../../traits/instructions/brazilian.json), [British](../../traits/instructions/british.json), [Canadian](../../traits/instructions/canadian.json), [Chinese](../../traits/instructions/chinese.json), [European](../../traits/instructions/european.json), [French](../../traits/instructions/french.json), [German](../../traits/instructions/german.json), [Indian](../../traits/instructions/indian.json), [Indigenous American](../../traits/instructions/indigenous_american.json), [Indigenous Australian](../../traits/instructions/indigenous_australian.json), [Italian](../../traits/instructions/italian.json), [Japanese](../../traits/instructions/japanese.json), [Nigerian](../../traits/instructions/nigerian.json), [rooted](../../traits/instructions/rooted.json), [Russian](../../traits/instructions/russian.json) |
| 825 Excitability (9) | [excitable](../../traits/instructions/excitable.json), [flustered](../../traits/instructions/flustered.json), [impatient](../../traits/instructions/impatient.json), [manic](../../traits/instructions/manic.json), [neurotic](../../traits/instructions/neurotic.json), [neurotic (Big Five)](../../traits/instructions/neurotic_big_five.json), [passionate](../../traits/instructions/passionate.json), [restless](../../traits/instructions/restless.json), [temperamental](../../traits/instructions/temperamental.json) |
| 826 Inexcitability (9) | [composed](../../traits/instructions/composed.json), [dispassionate](../../traits/instructions/dispassionate.json), [patient](../../traits/instructions/patient.json), [placid](../../traits/instructions/placid.json), [serene](../../traits/instructions/serene.json), [staid](../../traits/instructions/staid.json), [stoic](../../traits/instructions/stoic.json), [strong-stomached](../../traits/instructions/strong_stomached.json), [unflappable](../../traits/instructions/unflappable.json) |
| 864 Caution (8) | [cautious](../../traits/instructions/cautious.json), [circumspect](../../traits/instructions/circumspect.json), [financially conservative](../../traits/instructions/financially_conservative.json), [guarded](../../traits/instructions/guarded.json), [loss-averse](../../traits/instructions/loss_averse.json), [prudent](../../traits/instructions/prudent.json), [risk-averse](../../traits/instructions/risk_averse.json), [unadventurous](../../traits/instructions/unadventurous.json) |
| 881 Modesty (8) | [body-insecure](../../traits/instructions/body_insecure.json), [introverted (HEXACO)](../../traits/instructions/introverted_hexaco.json), [modest](../../traits/instructions/modest.json), [reserved](../../traits/instructions/reserved.json), [self-conscious](../../traits/instructions/self_conscious.json), [self-effacing](../../traits/instructions/self_effacing.json), [timid](../../traits/instructions/timid.json), [unassuming](../../traits/instructions/unassuming.json) |
| 893 Seclusion. Exclusion (8) | [cliqueish](../../traits/instructions/cliqueish.json), [dismissive-avoidant attachment](../../traits/instructions/dismissive_avoidant_attachment.json), [introverted](../../traits/instructions/introverted.json), [introverted (Big Five)](../../traits/instructions/introverted_big_five.json), [isolated](../../traits/instructions/isolated.json), [lonely](../../traits/instructions/lonely.json), [solitary](../../traits/instructions/solitary.json), [unsupported](../../traits/instructions/unsupported.json) |
| 82 Conformity (7) | [conformist](../../traits/instructions/conformist.json), [conventional](../../traits/instructions/conventional.json), [conventional (Kohlberg)](../../traits/instructions/conventional_kohlberg.json), [formalist](../../traits/instructions/formalist.json), [rule-abiding](../../traits/instructions/rule_abiding.json), [traditional](../../traits/instructions/traditional.json), [well-behaved](../../traits/instructions/well_behaved.json) |
| 460 Neglect (7) | [careless](../../traits/instructions/careless.json), [careless (Big Five)](../../traits/instructions/careless_big_five.json), [careless (HEXACO)](../../traits/instructions/careless_hexaco.json), [health-negligent](../../traits/instructions/health_negligent.json), [neglectful](../../traits/instructions/neglectful.json), [neglectful (Baumrind)](../../traits/instructions/neglectful_baumrind.json), [sloppy](../../traits/instructions/sloppy.json) |
| 484 Belief (7) | [body-confident](../../traits/instructions/body_confident.json), [confident](../../traits/instructions/confident.json), [just-world-believing](../../traits/instructions/just_world_believing.json), [media-trusting](../../traits/instructions/media_trusting.json), [overconfident](../../traits/instructions/overconfident.json), [science-trusting](../../traits/instructions/science_trusting.json), [trusting](../../traits/instructions/trusting.json) |
| 868 Fastidiousness (7) | [fastidious](../../traits/instructions/fastidious.json), [meticulous](../../traits/instructions/meticulous.json), [petty](../../traits/instructions/petty.json), [picky-eater](../../traits/instructions/picky_eater.json), [self-critical](../../traits/instructions/self_critical.json), [squeamish](../../traits/instructions/squeamish.json), [uptight](../../traits/instructions/uptight.json) |
| 543 Veracity (6) | [candid](../../traits/instructions/candid.json), [earnest](../../traits/instructions/earnest.json), [forthright](../../traits/instructions/forthright.json), [sincere](../../traits/instructions/sincere.json), [trustworthy](../../traits/instructions/trustworthy.json), [truthful](../../traits/instructions/truthful.json) |
| 737 Authority (6) | [authoritarian](../../traits/instructions/authoritarian.json), [authoritative (Baumrind)](../../traits/instructions/authoritative_baumrind.json), [controlling](../../traits/instructions/controlling.json), [dominance (DISC)](../../traits/instructions/dominance_disc.json), [dominant](../../traits/instructions/dominant.json), [internal locus of control](../../traits/instructions/internal_locus_of_control.json) |
| 866 Indifference (6) | [apolitical](../../traits/instructions/apolitical.json), [detached](../../traits/instructions/detached.json), [indifferent-to-animals](../../traits/instructions/indifferent_to_animals.json), [unambitious](../../traits/instructions/unambitious.json), [uncaring](../../traits/instructions/uncaring.json), [unsentimental](../../traits/instructions/unsentimental.json) |
| 910 Philanthropy (6) | [collectivistic](../../traits/instructions/collectivistic.json), [cosmopolitan](../../traits/instructions/cosmopolitan.json), [humanistic](../../traits/instructions/humanistic.json), [humanitarian](../../traits/instructions/humanitarian.json), [patriotic](../../traits/instructions/patriotic.json), [philanthropic](../../traits/instructions/philanthropic.json) |
| 451 Thought (5) | [introspective](../../traits/instructions/introspective.json), [meditative](../../traits/instructions/meditative.json), [pensive](../../traits/instructions/pensive.json), [philosophical](../../traits/instructions/philosophical.json), [speculative](../../traits/instructions/speculative.json) |

## Class I-III heads brought in, with the labels that brought them

| head | state | trigger labels |
|---|---|---|
| 4 Unsubstantiality | partly | [ethereal](../../traits/instructions/ethereal.json) |
| 5 Intrinsicality | covered | [intrinsic (Allport)](../../traits/instructions/intrinsic_allport.json) |
| 6 Extrinsicality | covered | [extrinsic (Allport)](../../traits/instructions/extrinsic_allport.json) |
| 10 Irrelation | partly | [insular](../../traits/instructions/insular.json), [isolated](../../traits/instructions/isolated.json) |
| 18 Dissimilarity | partly | [divergent](../../traits/instructions/divergent.json) |
| 20 Nonimitation | covered | [creative](../../traits/instructions/creative.json) |
| 25 Quantity | covered (not character) | [quantitative](../../traits/instructions/quantitative.json) |
| 29 Mean | empty | [middle-class](../../traits/instructions/middle_class.json) |
| 32 Smallness | covered | [petty](../../traits/instructions/petty.json), [slight](../../traits/instructions/slight.json) |
| 47 Incoherence | covered | [incoherent](../../traits/instructions/incoherent.json) |
| 49 Decomposition | covered (not character) | [analytical](../../traits/instructions/analytical.json) |
| 52 Completeness | covered | [thorough](../../traits/instructions/thorough.json) |
| 55 Exclusion | covered (not character) | [exclusive](../../seed_queue.json) (queued) |
| 58 Order | partly | [methodical](../../traits/instructions/methodical.json), [Orderliness (BFAS)](../../seed_queue.json) (queued), [Orderliness (IPIP-NEO)](../../seed_queue.json) (queued) |
| 59 Disorder | covered | [chaotic](../../traits/instructions/chaotic.json), [disorganized](../../traits/instructions/disorganized.json) |
| 60 Arrangement | covered | [methodical](../../traits/instructions/methodical.json), [Orderliness (BFAS)](../../seed_queue.json) (queued), [Orderliness (IPIP-NEO)](../../seed_queue.json) (queued) |
| 76 Inclusion | covered (not character) | [inclusive](../../traits/instructions/inclusive.json) |
| 82 Conformity | covered | [Orderliness (BFAS)](../../seed_queue.json) (queued), [Orderliness (IPIP-NEO)](../../seed_queue.json) (queued), [orthodox](../../traits/instructions/orthodox.json) |
| 83 Unconformity | covered | [eccentric](../../traits/instructions/eccentric.json), [unfashionable](../../traits/instructions/unfashionable.json) |
| 87 Unity | partly | [single](../../traits/instructions/single.json) |
| 120 Synchronism | covered (not character) | [contemporary](../../traits/instructions/contemporary.json) |
| 123 Newness | covered | [fashionable](../../traits/instructions/fashionable.json) |
| 124 Oldness | empty | [traditional](../../traits/instructions/traditional.json) |
| 127 Youth | covered | [young](../../traits/instructions/young.json) |
| 128 Age | covered | [elderly](../../traits/instructions/elderly.json) |
| 131 Adolescence | covered | [mature](../../traits/instructions/mature.json), [middle-aged](../../traits/instructions/middle_aged.json) |
| 141 Permanence | partly | [conservative](../../traits/instructions/conservative.json) |
| 149 Changeableness | covered | [erratic](../../traits/instructions/erratic.json) |
| 150 Stability | covered | [settled](../../traits/instructions/settled.json), [steadfast](../../seed_queue.json) (queued), [steadiness (DISC)](../../traits/instructions/steadiness_disc.json), [steady](../../traits/instructions/steady.json) |
| 156 Chance | covered (not character) | [casual](../../traits/instructions/casual.json) |
| 157 Power | partly | [competent](../../traits/instructions/competent.json) |
| 158 Impotence | covered | [helpless](../../traits/instructions/helpless.json), [incompetent](../../traits/instructions/incompetent.json) |
| 159 Strength | covered | [muscular](../../traits/instructions/muscular.json) |
| 160 Weakness | partly | [fragile](../../traits/instructions/fragile.json) |
| 162 Destruction | covered | [destructive](../../traits/instructions/destructive.json) |
| 170 Agency | covered | [efficient](../../traits/instructions/efficient.json), [practical](../../traits/instructions/practical.json) |
| 171 Physical Energy | covered | [energetic](../../traits/instructions/energetic.json), [intense](../../traits/instructions/intense.json) |
| 172 Physical Inertness | partly | [passive](../../traits/instructions/passive.json) |
| 173 Violence | covered | [savage](../../traits/instructions/savage.json), [turbulent](../../traits/instructions/turbulent.json) |
| 174 Moderation | covered | [calm](../../traits/instructions/calm.json), [calm (IPIP-NEO)](../../seed_queue.json) (queued), [gentle](../../traits/instructions/gentle.json), [moderate](../../traits/instructions/moderate.json), [peaceful](../../traits/instructions/peaceful.json), [temperate](../../traits/instructions/temperate.json) |
| 175 Influence | covered | [dominant](../../traits/instructions/dominant.json) |
| 181 Region | covered | [parochial](../../traits/instructions/parochial.json) |
| 184 Location | empty (not character) | [rooted](../../traits/instructions/rooted.json) |
| 188 Inhabitant | covered | [British](../../traits/instructions/british.json), [Canadian](../../traits/instructions/canadian.json) |
| 189 Abode | covered | [rural](../../traits/instructions/rural.json), [suburban](../../traits/instructions/suburban.json), [urban](../../traits/instructions/urban.json) |
| 192 Size | covered (not character) | [fat](../../traits/instructions/fat.json) |
| 193 Littleness | empty | [petty](../../traits/instructions/petty.json) |
| 201 Shortness | covered | [short](../../traits/instructions/short.json) |
| 203 Narrowness. Thinness | covered (not character) | [thin](../../traits/instructions/thin.json) |
| 206 Height | covered | [tall](../../traits/instructions/tall.json) |
| 209 Shallowness | covered | [superficial](../../traits/instructions/superficial.json) |
| 212 Verticality | partly | [straight](../../traits/instructions/straight.json) |
| 214 Pendency | partly (not character) | [dependent](../../traits/instructions/dependent.json) |
| 220 Exteriority | partly | [eccentric](../../traits/instructions/eccentric.json), [superficial](../../traits/instructions/superficial.json) |
| 227 Circumjacence | partly (not character) | [suburban](../../traits/instructions/suburban.json) |
| 239 Sinistrality | covered | [left-handed](../../traits/instructions/left_handed.json) |
| 246 Straightness | covered | [straight](../../traits/instructions/straight.json) |
| 251 Flatness | partly (not character) | [flat](../../traits/instructions/flat.json) |
| 254 Bluntness | covered | [blunt](../../traits/instructions/blunt.json) |
| 260 Opening | covered (not character) | [open (Big Five)](../../traits/instructions/open_big_five.json), [open (HEXACO)](../../traits/instructions/open_hexaco.json), [Openness (BFAS)](../../seed_queue.json) (queued) |
| 261 Closure | covered (not character) | [closed (Big Five)](../../traits/instructions/closed_big_five.json) |
| 265 Quiescence | covered | [sedentary](../../traits/instructions/sedentary.json) |
| 276 Impulse | partly | [impulsive](../../traits/instructions/impulsive.json) |
| 278 Direction | partly | [straight](../../traits/instructions/straight.json) |
| 279 Deviation | partly | [erratic](../../traits/instructions/erratic.json) |
| 282 Progression | partly | [progressive](../../traits/instructions/progressive.json) |
| 290 Convergence | covered (not character) | [convergent](../../traits/instructions/convergent.json) |
| 291 Divergence | covered (not character) | [divergent](../../traits/instructions/divergent.json) |
| 304 Shortcoming | partly (not character) | [short](../../traits/instructions/short.json) |
| 315 Agitation | partly | [restless](../../traits/instructions/restless.json) |
| 316 Materiality | covered | [materialistic](../../traits/instructions/materialistic.json) |
| 320 Levity | partly | [ethereal](../../traits/instructions/ethereal.json) |
| 323 Hardness | covered | [inflexible](../../traits/instructions/inflexible.json), [rigid](../../traits/instructions/rigid.json), [unyielding](../../traits/instructions/unyielding.json) |
| 324 Softness | partly | [flexible](../../traits/instructions/flexible.json) |
| 325 Elasticity | covered | [resilient](../../traits/instructions/resilient.json) |
| 327 Tenacity | covered | [tough](../../seed_queue.json) (queued), [tough (HEXACO)](../../traits/instructions/tough_hexaco.json) |
| 328 Brittleness | covered | [fragile](../../traits/instructions/fragile.json) |
| 334 Gaseity | covered (not character) | [ethereal](../../traits/instructions/ethereal.json) |
| 340 Dryness | partly (not character) | [dry](../../traits/instructions/dry.json) |
| 346 Island | covered | [insular](../../traits/instructions/insular.json) |
| 357 Organization | queued | [organized](../../traits/instructions/organized.json) |
| 359 Life | partly | [animated](../../traits/instructions/animated.json) |
| 371 Agriculture | covered | [rural](../../traits/instructions/rural.json) |
| 372 Mankind | partly | [cosmopolitan](../../traits/instructions/cosmopolitan.json) |
| 373 Man | covered | [male](../../traits/instructions/male.json), [masculine](../../traits/instructions/masculine.json) |
| 374 Woman | covered | [female](../../traits/instructions/female.json), [feminine](../../traits/instructions/feminine.json) |
| 374a Sexuality | covered | [bisexual](../../traits/instructions/bisexual.json), [gay](../../traits/instructions/gay.json) |
| 376 Physical Insensibility | partly | [callous](../../traits/instructions/callous.json), [thick-skinned](../../traits/instructions/thick_skinned.json) |
| 391 Insipidity | queued | [bland](../../seed_queue.json) (queued) |
| 392b Bitterness | covered | [acerbic](../../traits/instructions/acerbic.json), [bitter](../../traits/instructions/bitter.json) |
| 403 Silence | empty | [solemn](../../traits/instructions/solemn.json) |
| 419 Deafness | partly (not character) | [deaf](../../traits/instructions/deaf.json) |
| 422 Dimness | partly (not character) | [dull](../../traits/instructions/dull.json) |
| 425 Transparency | partly | [transparent](../../traits/instructions/transparent.json) |
| 426 Opacity | covered (not character) | [opaque](../../traits/instructions/opaque.json) |
| 429 Achromatism | covered (not character) | [blond](../../traits/instructions/blond.json) |
| 430 Whiteness | covered (not character) | [blond](../../traits/instructions/blond.json) |
| 441 Vision | covered (not character) | [visual (VARK)](../../traits/instructions/visual_vark.json) |
| 442 Blindness | covered (not character) | [blind](../../traits/instructions/blind.json) |

## Covered heads

| head | traits (primary) |
|---|---|
| 5 Intrinsicality | [essentialist](../../traits/instructions/essentialist.json), [intrinsic (Allport)](../../traits/instructions/intrinsic_allport.json) |
| 6 Extrinsicality | [extrinsic (Allport)](../../traits/instructions/extrinsic_allport.json) |
| 20 Nonimitation | [individualistic](../../traits/instructions/individualistic.json) |
| 32 Smallness | [slight](../../traits/instructions/slight.json) |
| 47 Incoherence | [incoherent](../../traits/instructions/incoherent.json) |
| 52 Completeness | [thorough](../../traits/instructions/thorough.json) |
| 59 Disorder | [chaotic](../../traits/instructions/chaotic.json), [disorganized](../../traits/instructions/disorganized.json) |
| 60 Arrangement | [organized](../../traits/instructions/organized.json) |
| 82 Conformity | [conformist](../../traits/instructions/conformist.json), [conventional](../../traits/instructions/conventional.json), [conventional (Kohlberg)](../../traits/instructions/conventional_kohlberg.json), [formalist](../../traits/instructions/formalist.json), [rule-abiding](../../traits/instructions/rule_abiding.json), [traditional](../../traits/instructions/traditional.json), [well-behaved](../../traits/instructions/well_behaved.json) |
| 83 Unconformity | [unfashionable](../../traits/instructions/unfashionable.json) |
| 123 Newness | [innovative](../../traits/instructions/innovative.json) |
| 127 Youth | [young](../../traits/instructions/young.json) |
| 128 Age | [elderly](../../traits/instructions/elderly.json) |
| 131 Adolescence | [mature](../../traits/instructions/mature.json), [middle-aged](../../traits/instructions/middle_aged.json) |
| 149 Changeableness | [adaptable](../../traits/instructions/adaptable.json), [brand-agnostic](../../traits/instructions/brand_agnostic.json), [job-hopping](../../traits/instructions/job_hopping.json) |
| 150 Stability | [emotionally-stable (Big Five)](../../traits/instructions/emotionally_stable_big_five.json), [settled](../../traits/instructions/settled.json), [steadiness (DISC)](../../traits/instructions/steadiness_disc.json), [steady](../../traits/instructions/steady.json) |
| 158 Impotence | [helpless](../../traits/instructions/helpless.json) |
| 159 Strength | [muscular](../../traits/instructions/muscular.json) |
| 162 Destruction | [destructive](../../traits/instructions/destructive.json) |
| 170 Agency | [efficient](../../traits/instructions/efficient.json) |
| 171 Physical Energy | [intense](../../traits/instructions/intense.json) |
| 173 Violence | [savage](../../traits/instructions/savage.json), [turbulent](../../traits/instructions/turbulent.json) |
| 174 Moderation | [even-tempered](../../traits/instructions/even_tempered.json) |
| 175 Influence | [influence (DISC)](../../traits/instructions/influence_disc.json) |
| 181 Region | [eastern hemisphere](../../traits/instructions/eastern_hemisphere.json), [parochial](../../traits/instructions/parochial.json), [western hemisphere](../../traits/instructions/western_hemisphere.json) |
| 188 Inhabitant | [African](../../traits/instructions/african.json), [American](../../traits/instructions/american.json), [Australian](../../traits/instructions/australian.json), [Brazilian](../../traits/instructions/brazilian.json), [British](../../traits/instructions/british.json), [Canadian](../../traits/instructions/canadian.json), [Chinese](../../traits/instructions/chinese.json), [European](../../traits/instructions/european.json), [French](../../traits/instructions/french.json), [German](../../traits/instructions/german.json), [Indian](../../traits/instructions/indian.json), [Indigenous American](../../traits/instructions/indigenous_american.json), [Indigenous Australian](../../traits/instructions/indigenous_australian.json), [Italian](../../traits/instructions/italian.json), [Japanese](../../traits/instructions/japanese.json), [Nigerian](../../traits/instructions/nigerian.json), [rooted](../../traits/instructions/rooted.json), [Russian](../../traits/instructions/russian.json) |
| 189 Abode | [suburban](../../traits/instructions/suburban.json), [urban](../../traits/instructions/urban.json) |
| 201 Shortness | [short](../../traits/instructions/short.json) |
| 206 Height | [tall](../../traits/instructions/tall.json) |
| 209 Shallowness | [superficial](../../traits/instructions/superficial.json) |
| 239 Sinistrality | [left-handed](../../traits/instructions/left_handed.json) |
| 246 Straightness | [straight](../../traits/instructions/straight.json) |
| 254 Bluntness | [blunt](../../traits/instructions/blunt.json), [socially-obtuse](../../traits/instructions/socially_obtuse.json) |
| 265 Quiescence | [sedentary](../../traits/instructions/sedentary.json) |
| 316 Materiality | [materialist](../../traits/instructions/materialist.json), [materialistic](../../traits/instructions/materialistic.json) |
| 323 Hardness | [inflexible](../../traits/instructions/inflexible.json) |
| 325 Elasticity | [resilient](../../traits/instructions/resilient.json) |
| 327 Tenacity | [tough (HEXACO)](../../traits/instructions/tough_hexaco.json) |
| 328 Brittleness | [fragile](../../traits/instructions/fragile.json) |
| 346 Island | [insular](../../traits/instructions/insular.json) |
| 371 Agriculture | [rural](../../traits/instructions/rural.json) |
| 373 Man | [male](../../traits/instructions/male.json), [masculine](../../traits/instructions/masculine.json) |
| 374 Woman | [female](../../traits/instructions/female.json), [feminine](../../traits/instructions/feminine.json), [feminist](../../traits/instructions/feminist.json) |
| 374a Sexuality | [bisexual](../../traits/instructions/bisexual.json), [gay](../../traits/instructions/gay.json), [kinky](../../traits/instructions/kinky.json), [lustful](../../traits/instructions/lustful.json) |
| 392b Bitterness | [acerbic](../../traits/instructions/acerbic.json) |
| 450 Intellect | [cerebral](../../traits/instructions/cerebral.json) |
| 451 Thought | [introspective](../../traits/instructions/introspective.json), [meditative](../../traits/instructions/meditative.json), [pensive](../../traits/instructions/pensive.json), [philosophical](../../traits/instructions/philosophical.json), [speculative](../../traits/instructions/speculative.json) |
| 455 Curiosity | [curious](../../traits/instructions/curious.json), [inquisitive](../../traits/instructions/inquisitive.json) |
| 456 Incuriosity | [conventional (HEXACO)](../../traits/instructions/conventional_hexaco.json), [incurious](../../traits/instructions/incurious.json), [uninquisitive](../../traits/instructions/uninquisitive.json) |
| 457 Attention | [engaged](../../traits/instructions/engaged.json), [focused](../../traits/instructions/focused.json), [observant](../../traits/instructions/observant.json), [other-focused](../../traits/instructions/other_focused.json), [self-absorbed](../../traits/instructions/self_absorbed.json) |
| 458 Inattention | [ADHD](../../traits/instructions/adhd.json), [distractible](../../traits/instructions/distractible.json), [unreflective](../../traits/instructions/unreflective.json) |
| 459 Care | [conscientious](../../traits/instructions/conscientious.json), [conscientious (HEXACO)](../../traits/instructions/conscientious_hexaco.json), [conscientiousness (DISC)](../../traits/instructions/conscientiousness_disc.json), [detail-oriented](../../traits/instructions/detail_oriented.json) |
| 460 Neglect | [careless](../../traits/instructions/careless.json), [careless (Big Five)](../../traits/instructions/careless_big_five.json), [careless (HEXACO)](../../traits/instructions/careless_hexaco.json), [health-negligent](../../traits/instructions/health_negligent.json), [neglectful](../../traits/instructions/neglectful.json), [neglectful (Baumrind)](../../traits/instructions/neglectful_baumrind.json), [sloppy](../../traits/instructions/sloppy.json) |
| 465a Indiscrimination | [promiscuous](../../traits/instructions/promiscuous.json) |
| 474 Certainty | [closure-seeking](../../traits/instructions/closure_seeking.json), [decisive](../../traits/instructions/decisive.json), [self-assured](../../traits/instructions/self_assured.json), [self-certain](../../traits/instructions/self_certain.json) |
| 475 Uncertainty | [indecisive](../../traits/instructions/indecisive.json), [self-uncertain](../../traits/instructions/self_uncertain.json), [uncertain](../../traits/instructions/uncertain.json), [vague](../../traits/instructions/vague.json) |
| 476 Reasoning | [analytical](../../traits/instructions/analytical.json), [logical](../../traits/instructions/logical.json), [rationalist](../../traits/instructions/rationalist.json) |
| 477 Intuition & Sophistry | [illogical](../../traits/instructions/illogical.json), [intuitive](../../traits/instructions/intuitive.json), [visceral](../../traits/instructions/visceral.json) |
| 481 Misjudgment | [ageist](../../traits/instructions/ageist.json), [closed-minded](../../traits/instructions/closed_minded.json), [tunnel-visioned](../../traits/instructions/tunnel_visioned.json) |
| 483 Underestimation | [understated](../../traits/instructions/understated.json) |
| 484 Belief | [body-confident](../../traits/instructions/body_confident.json), [confident](../../traits/instructions/confident.json), [just-world-believing](../../traits/instructions/just_world_believing.json), [media-trusting](../../traits/instructions/media_trusting.json), [overconfident](../../traits/instructions/overconfident.json), [science-trusting](../../traits/instructions/science_trusting.json), [trusting](../../traits/instructions/trusting.json) |
| 485 Unbelief. Doubt | [paranoid](../../traits/instructions/paranoid.json) |
| 486 Credulity | [credulous](../../traits/instructions/credulous.json), [superstitious](../../traits/instructions/superstitious.json), [uncritical](../../traits/instructions/uncritical.json) |
| 487 Incredulity | [cynical](../../traits/instructions/cynical.json), [media-skeptical](../../traits/instructions/media_skeptical.json), [science-skeptical](../../traits/instructions/science_skeptical.json), [skeptical](../../traits/instructions/skeptical.json) |
| 488 Assent | [unchallenging](../../traits/instructions/unchallenging.json) |
| 489 Dissent | [contrarian](../../traits/instructions/contrarian.json), [nonconformist](../../traits/instructions/nonconformist.json) |
| 490 Knowledge | [erudite](../../traits/instructions/erudite.json) |
| 491 Ignorance | [illiterate](../../traits/instructions/illiterate.json), [uneducated](../../traits/instructions/uneducated.json), [unschooled](../../traits/instructions/unschooled.json) |
| 492 Scholar | [educated](../../traits/instructions/educated.json) |
| 494 Truth | [accurate](../../traits/instructions/accurate.json), [authentic](../../traits/instructions/authentic.json) |
| 495 Error | [inaccurate](../../traits/instructions/inaccurate.json) |
| 498 Intelligence, Wisdom | [quick-witted](../../traits/instructions/quick_witted.json), [wise](../../traits/instructions/wise.json) |
| 499 Imbecility. Folly | [foolish](../../traits/instructions/foolish.json), [slow-witted](../../traits/instructions/slow_witted.json) |
| 500 Sage | [thinker (VALS)](../../traits/instructions/thinker_vals.json) |
| 503 Insanity | [delusional](../../traits/instructions/delusional.json) |
| 506 Oblivion | [forgetful](../../traits/instructions/forgetful.json), [oblivious](../../traits/instructions/oblivious.json) |
| 510 Foresight | [proactive](../../traits/instructions/proactive.json) |
| 515 Imagination | [confabulatory](../../traits/instructions/confabulatory.json), [creative](../../traits/instructions/creative.json), [idealistic](../../traits/instructions/idealistic.json), [romantic](../../traits/instructions/romantic.json) |
| 518 Intelligibility | [clear](../../traits/instructions/clear.json), [transparent](../../traits/instructions/transparent.json) |
| 522 Interpretation | [expository](../../traits/instructions/expository.json) |
| 525 Manifestation | [expressive](../../traits/instructions/expressive.json), [low-context (Hall)](../../traits/instructions/low_context_hall.json) |
| 527 Information | [informational](../../traits/instructions/informational.json) |
| 528 Concealment | [cryptic](../../traits/instructions/cryptic.json), [esoteric](../../traits/instructions/esoteric.json) |
| 535 Affirmation | [emphatic](../../traits/instructions/emphatic.json), [opinionated](../../traits/instructions/opinionated.json), [words of affirmation](../../traits/instructions/words_of_affirmation.json) |
| 537 Teaching | [didactic](../../traits/instructions/didactic.json), [educational](../../traits/instructions/educational.json) |
| 539 Learning | [learning-oriented](../../traits/instructions/learning_oriented.json) |
| 543 Veracity | [candid](../../traits/instructions/candid.json), [earnest](../../traits/instructions/earnest.json), [forthright](../../traits/instructions/forthright.json), [sincere](../../traits/instructions/sincere.json), [trustworthy](../../traits/instructions/trustworthy.json), [truthful](../../traits/instructions/truthful.json) |
| 544 Falsehood | [deceitful](../../traits/instructions/deceitful.json), [dishonest](../../traits/instructions/dishonest.json) |
| 545 Deception | [manipulative](../../traits/instructions/manipulative.json) |
| 559 Artist | [artistic](../../traits/instructions/artistic.json), [artistic (Holland)](../../traits/instructions/artistic_holland.json) |
| 570 Perspicuity | [precise](../../traits/instructions/precise.json) |
| 572 Conciseness | [concise](../../traits/instructions/concise.json) |
| 573 Diffuseness | [verbose](../../traits/instructions/verbose.json) |
| 575 Feebleness | [dull](../../traits/instructions/dull.json) |
| 576 Plainness | [dry](../../traits/instructions/dry.json), [grounded](../../traits/instructions/grounded.json), [plain-spoken](../../traits/instructions/plain_spoken.json) |
| 578 Elegance | [formal](../../traits/instructions/formal.json) |
| 582 Speech | [eloquent](../../traits/instructions/eloquent.json), [rhetorical](../../traits/instructions/rhetorical.json) |
| 583 Stammering | [emotionally-inarticulate](../../traits/instructions/emotionally_inarticulate.json) |
| 584 Loquacity | [glib](../../traits/instructions/glib.json) |
| 598 Prose | [prosaic](../../traits/instructions/prosaic.json) |
| 599 The Drama | [melodramatic](../../traits/instructions/melodramatic.json), [theatrical](../../traits/instructions/theatrical.json) |
| 601 Necessity | [determinist](../../traits/instructions/determinist.json), [fatalistic](../../traits/instructions/fatalistic.json) |
| 604 Resolution | [self-disciplined](../../traits/instructions/self_disciplined.json) |
| 604a Perseverance | [long-term oriented](../../traits/instructions/long_term_oriented.json), [persevering](../../traits/instructions/persevering.json), [unflinching](../../traits/instructions/unflinching.json) |
| 605 Irresolution | [ambivalent](../../traits/instructions/ambivalent.json) |
| 606 Obstinacy | [obsessive](../../traits/instructions/obsessive.json), [unyielding](../../traits/instructions/unyielding.json) |
| 608 Caprice | [eccentric](../../traits/instructions/eccentric.json), [erratic](../../traits/instructions/erratic.json), [whimsical](../../traits/instructions/whimsical.json) |
| 609 Choice | [eclectic](../../traits/instructions/eclectic.json) |
| 609a Absence of Choice | [neuter](../../traits/instructions/neuter.json) |
| 612 Impulse | [improvisational](../../traits/instructions/improvisational.json), [impulsive](../../traits/instructions/impulsive.json), [spontaneous](../../traits/instructions/spontaneous.json) |
| 615 Motive | [inspirational](../../traits/instructions/inspirational.json), [provocative](../../traits/instructions/provocative.json) |
| 616 Dissuasion | [discouraging](../../traits/instructions/discouraging.json) |
| 618 Good | [good](../../traits/instructions/good.json) |
| 623 Avoidance | [avoidant](../../traits/instructions/avoidant.json), [news-avoidant](../../traits/instructions/news_avoidant.json), [noncommittal](../../traits/instructions/noncommittal.json) |
| 625 Business | [career-oriented](../../traits/instructions/career_oriented.json) |
| 627 Method | [methodical](../../traits/instructions/methodical.json) |
| 632 Means | [ends justify means](../../traits/instructions/ends_justify_means.json) |
| 639 Sufficiency | [satisficing](../../traits/instructions/satisficing.json) |
| 642 Importance | [serious](../../traits/instructions/serious.json) |
| 644 Utility | [utilitarian](../../traits/instructions/utilitarian.json) |
| 646 Expedience | [expedient](../../traits/instructions/expedient.json), [pragmatic](../../traits/instructions/pragmatic.json) |
| 648 Goodness | [harmless](../../traits/instructions/harmless.json) |
| 649 Badness | [evil](../../traits/instructions/evil.json), [harmful](../../traits/instructions/harmful.json), [mischievous](../../traits/instructions/mischievous.json) |
| 650 Perfection | [perfectionist](../../traits/instructions/perfectionist.json) |
| 653 Uncleanness | [slovenly](../../traits/instructions/slovenly.json) |
| 654 Health | [athletic](../../traits/instructions/athletic.json), [healthy](../../traits/instructions/healthy.json) |
| 658 Improvement | [incrementalist](../../traits/instructions/incrementalist.json), [progressive](../../traits/instructions/progressive.json) |
| 665 Danger | [financially precarious](../../traits/instructions/financially_precarious.json) |
| 670 Preservation | [conservative](../../traits/instructions/conservative.json) |
| 675 Essay | [adventurous](../../traits/instructions/adventurous.json) |
| 681 Inaction | [hands-off](../../traits/instructions/hands_off.json), [passive](../../traits/instructions/passive.json) |
| 682 Activity | [animated](../../traits/instructions/animated.json), [energetic](../../traits/instructions/energetic.json) |
| 683 Inactivity | [lazy](../../traits/instructions/lazy.json), [lethargic](../../traits/instructions/lethargic.json) |
| 684 Haste | [hurried](../../traits/instructions/hurried.json) |
| 685 Leisure | [deliberate](../../traits/instructions/deliberate.json), [laid-back](../../traits/instructions/laid_back.json), [unhurried](../../traits/instructions/unhurried.json) |
| 686 Exertion | [industrious](../../traits/instructions/industrious.json) |
| 692 Conduct | [practical](../../traits/instructions/practical.json) |
| 697 Precept | [prescriptive](../../traits/instructions/prescriptive.json) |
| 698 Skill | [competent](../../traits/instructions/competent.json) |
| 699 Unskillfulness | [incompetent](../../traits/instructions/incompetent.json) |
| 700 Proficient | [specialist](../../traits/instructions/specialist.json) |
| 702 Cunning | [calculating](../../traits/instructions/calculating.json), [scheming](../../traits/instructions/scheming.json), [sly (HEXACO)](../../traits/instructions/sly_hexaco.json) |
| 703 Artlessness | [guileless](../../traits/instructions/guileless.json), [naive](../../traits/instructions/naive.json), [unselfconscious](../../traits/instructions/unselfconscious.json) |
| 705 Facility | [accessible](../../traits/instructions/accessible.json), [flexible](../../traits/instructions/flexible.json) |
| 707 Aid | [helpful](../../traits/instructions/helpful.json), [supportive](../../traits/instructions/supportive.json) |
| 708 Opposition | [antagonistic (Big Five)](../../traits/instructions/antagonistic_big_five.json), [hostile](../../traits/instructions/hostile.json) |
| 709 Cooperation | [collaborative](../../traits/instructions/collaborative.json), [cooperative](../../traits/instructions/cooperative.json) |
| 712 Party | [clannish](../../traits/instructions/clannish.json) |
| 713 Discord | [disagreeable](../../traits/instructions/disagreeable.json) |
| 714 Concord | [agreeable](../../traits/instructions/agreeable.json) |
| 716 Attack | [aggressive](../../traits/instructions/aggressive.json) |
| 720 Contention | [competitive](../../traits/instructions/competitive.json), [confrontational](../../traits/instructions/confrontational.json) |
| 721 Peace | [calm](../../traits/instructions/calm.json), [pacifist](../../traits/instructions/pacifist.json), [peaceful](../../traits/instructions/peaceful.json) |
| 722 Warfare | [hawkish](../../traits/instructions/hawkish.json), [tactical](../../traits/instructions/tactical.json) |
| 723 Pacification | [conciliatory](../../traits/instructions/conciliatory.json) |
| 725 Submission | [submissive](../../traits/instructions/submissive.json) |
| 736 Mediocrity | [middle-class](../../traits/instructions/middle_class.json) |
| 737 Authority | [authoritarian](../../traits/instructions/authoritarian.json), [authoritative (Baumrind)](../../traits/instructions/authoritative_baumrind.json), [controlling](../../traits/instructions/controlling.json), [dominance (DISC)](../../traits/instructions/dominance_disc.json), [dominant](../../traits/instructions/dominant.json), [internal locus of control](../../traits/instructions/internal_locus_of_control.json) |
| 737b Politics | [partisan](../../traits/instructions/partisan.json), [political](../../traits/instructions/political.json) |
| 738 Laxity | [loose (Gelfand)](../../traits/instructions/loose_gelfand.json) |
| 739 Severity | [authoritarian (Baumrind)](../../traits/instructions/authoritarian_baumrind.json), [harsh](../../traits/instructions/harsh.json), [rigid](../../traits/instructions/rigid.json), [strict](../../traits/instructions/strict.json), [tight (Gelfand)](../../traits/instructions/tight_gelfand.json) |
| 740 Lenity | [ambiguity-tolerant](../../traits/instructions/ambiguity_tolerant.json), [gentle](../../traits/instructions/gentle.json), [lenient](../../traits/instructions/lenient.json) |
| 742 Disobedience | [rebellious](../../traits/instructions/rebellious.json) |
| 743 Obedience | [company-loyal](../../traits/instructions/company_loyal.json), [loyal](../../traits/instructions/loyal.json), [obedient](../../traits/instructions/obedient.json) |
| 748 Freedom | [civil-libertarian](../../traits/instructions/civil_libertarian.json), [independent](../../traits/instructions/independent.json), [self-reliant](../../traits/instructions/self_reliant.json) |
| 749 Subjection | [dependent](../../traits/instructions/dependent.json) |
| 751 Restraint | [trapped-in-job](../../traits/instructions/trapped_in_job.json) |
| 760 Permission | [permissive](../../traits/instructions/permissive.json), [permissive (Baumrind)](../../traits/instructions/permissive_baumrind.json) |
| 772 Observance | [conscientious (Big Five)](../../traits/instructions/conscientious_big_five.json), [dependable](../../traits/instructions/dependable.json) |
| 773 Nonobservance | [rule-breaking](../../traits/instructions/rule_breaking.json), [unreliable](../../traits/instructions/unreliable.json) |
| 774 Compromise | [accommodating](../../traits/instructions/accommodating.json) |
| 778 Participation | [socialist](../../traits/instructions/socialist.json) |
| 779 Possessor | [gun owner](../../traits/instructions/gun_owner.json), [homeowner](../../traits/instructions/homeowner.json), [renter](../../traits/instructions/renter.json) |
| 781 Retention | [retentive](../../traits/instructions/retentive.json) |
| 803 Wealth | [wealthy](../../traits/instructions/wealthy.json) |
| 804 Poverty | [poor](../../traits/instructions/poor.json) |
| 816 Liberality | [generous](../../traits/instructions/generous.json) |
| 817 Economy | [bargain-hunter](../../traits/instructions/bargain_hunter.json), [frugal](../../traits/instructions/frugal.json) |
| 817a Greed | [greedy](../../traits/instructions/greedy.json) |
| 818 Prodigality | [extravagant](../../traits/instructions/extravagant.json) |
| 819 Parsimony | [stingy](../../traits/instructions/stingy.json) |
| 821 Feeling | [emotional](../../traits/instructions/emotional.json), [emotional (HEXACO)](../../traits/instructions/emotional_hexaco.json), [zealous](../../traits/instructions/zealous.json) |
| 822 Sensibility | [emotionally-engaged](../../traits/instructions/emotionally_engaged.json), [sentimental](../../traits/instructions/sentimental.json), [thin-skinned](../../traits/instructions/thin_skinned.json) |
| 823 Insensibility | [apathetic](../../traits/instructions/apathetic.json), [callous](../../traits/instructions/callous.json), [emotionally-disengaged](../../traits/instructions/emotionally_disengaged.json), [thick-skinned](../../traits/instructions/thick_skinned.json) |
| 825 Excitability | [excitable](../../traits/instructions/excitable.json), [flustered](../../traits/instructions/flustered.json), [impatient](../../traits/instructions/impatient.json), [manic](../../traits/instructions/manic.json), [neurotic](../../traits/instructions/neurotic.json), [neurotic (Big Five)](../../traits/instructions/neurotic_big_five.json), [passionate](../../traits/instructions/passionate.json), [restless](../../traits/instructions/restless.json), [temperamental](../../traits/instructions/temperamental.json) |
| 826 Inexcitability | [composed](../../traits/instructions/composed.json), [dispassionate](../../traits/instructions/dispassionate.json), [patient](../../traits/instructions/patient.json), [placid](../../traits/instructions/placid.json), [serene](../../traits/instructions/serene.json), [staid](../../traits/instructions/staid.json), [stoic](../../traits/instructions/stoic.json), [strong-stomached](../../traits/instructions/strong_stomached.json), [unflappable](../../traits/instructions/unflappable.json) |
| 828 Pain | [in chronic pain](../../traits/instructions/in_chronic_pain.json), [stressed](../../traits/instructions/stressed.json) |
| 829 Pleasurableness | [agreeable (Big Five)](../../traits/instructions/agreeable_big_five.json) |
| 830 . Painfulness | [cruel](../../traits/instructions/cruel.json) |
| 831 Content | [contented](../../traits/instructions/contented.json), [death-accepting](../../traits/instructions/death_accepting.json), [easygoing](../../traits/instructions/easygoing.json), [happily-partnered](../../traits/instructions/happily_partnered.json), [self-accepting](../../traits/instructions/self_accepting.json) |
| 832 Discontent | [discontented](../../traits/instructions/discontented.json), [unhappily-partnered](../../traits/instructions/unhappily_partnered.json) |
| 836 Cheerfulness | [cheerful](../../traits/instructions/cheerful.json), [joyful](../../traits/instructions/joyful.json), [lighthearted](../../traits/instructions/lighthearted.json) |
| 837 Dejection | [joyless](../../traits/instructions/joyless.json), [melancholic](../../traits/instructions/melancholic.json) |
| 840 Amusement | [entertaining](../../traits/instructions/entertaining.json), [playful](../../traits/instructions/playful.json) |
| 841 Weariness | [burned-out](../../traits/instructions/burned_out.json) |
| 842 Wit | [witty](../../traits/instructions/witty.json), [wry](../../traits/instructions/wry.json) |
| 843 Dullness | [flat](../../traits/instructions/flat.json), [humorless](../../traits/instructions/humorless.json) |
| 849 Simplicity | [unpretentious](../../traits/instructions/unpretentious.json) |
| 850 Taste | [aesthete](../../traits/instructions/aesthete.json), [highbrow](../../traits/instructions/highbrow.json) |
| 851 Vulgarity | [lowbrow](../../traits/instructions/lowbrow.json) |
| 852 Fashion | [fashionable](../../traits/instructions/fashionable.json), [shabby-genteel](../../traits/instructions/shabby_genteel.json) |
| 853 Ridiculousness | [goofy](../../traits/instructions/goofy.json) |
| 855 Affectation | [pedantic](../../traits/instructions/pedantic.json), [performative](../../traits/instructions/performative.json), [pretentious](../../traits/instructions/pretentious.json) |
| 856 Ridicule | [sarcastic](../../traits/instructions/sarcastic.json), [sardonic](../../traits/instructions/sardonic.json) |
| 858 Hope | [encouraging](../../traits/instructions/encouraging.json) |
| 859 Hopelessness | [despairing](../../traits/instructions/despairing.json) |
| 860 Fear | [anxious](../../traits/instructions/anxious.json), [death-fearing](../../traits/instructions/death_fearing.json), [fearful-avoidant attachment](../../traits/instructions/fearful_avoidant_attachment.json), [panicky](../../traits/instructions/panicky.json), [punishment-fearing](../../traits/instructions/punishment_fearing.json) |
| 861 Courage | [bold](../../traits/instructions/bold.json), [brave](../../traits/instructions/brave.json), [Gryffindor](../../traits/instructions/gryffindor.json) |
| 862 Cowardice | [cowardly](../../traits/instructions/cowardly.json) |
| 863 Rashness | [brash](../../traits/instructions/brash.json), [financially reckless](../../traits/instructions/financially_reckless.json), [reckless](../../traits/instructions/reckless.json), [risk-seeking](../../traits/instructions/risk_seeking.json) |
| 864 Caution | [cautious](../../traits/instructions/cautious.json), [circumspect](../../traits/instructions/circumspect.json), [financially conservative](../../traits/instructions/financially_conservative.json), [guarded](../../traits/instructions/guarded.json), [loss-averse](../../traits/instructions/loss_averse.json), [prudent](../../traits/instructions/prudent.json), [risk-averse](../../traits/instructions/risk_averse.json), [unadventurous](../../traits/instructions/unadventurous.json) |
| 865 Desire | [ambitious](../../traits/instructions/ambitious.json) |
| 866 Indifference | [apolitical](../../traits/instructions/apolitical.json), [detached](../../traits/instructions/detached.json), [indifferent-to-animals](../../traits/instructions/indifferent_to_animals.json), [unambitious](../../traits/instructions/unambitious.json), [uncaring](../../traits/instructions/uncaring.json), [unsentimental](../../traits/instructions/unsentimental.json) |
| 867 Dislike | [unpopular](../../traits/instructions/unpopular.json) |
| 868 Fastidiousness | [fastidious](../../traits/instructions/fastidious.json), [meticulous](../../traits/instructions/meticulous.json), [petty](../../traits/instructions/petty.json), [picky-eater](../../traits/instructions/picky_eater.json), [self-critical](../../traits/instructions/self_critical.json), [squeamish](../../traits/instructions/squeamish.json), [uptight](../../traits/instructions/uptight.json) |
| 869 Satiety | [jaded](../../traits/instructions/jaded.json) |
| 873 Repute | [famous](../../traits/instructions/famous.json), [honor culture](../../traits/instructions/honor_culture.json), [popular](../../traits/instructions/popular.json) |
| 875 Nobility | [aristocratic](../../traits/instructions/aristocratic.json), [upper-class](../../traits/instructions/upper_class.json) |
| 876 Commonalty | [working-class](../../traits/instructions/working_class.json) |
| 878 Pride | [dignified](../../traits/instructions/dignified.json), [dignity culture](../../traits/instructions/dignity_culture.json) |
| 879 Humility | [honest-humble (HEXACO)](../../traits/instructions/honest_humble_hexaco.json), [humble](../../traits/instructions/humble.json), [shame-prone](../../traits/instructions/shame_prone.json) |
| 880 Vanity | [grandiose](../../traits/instructions/grandiose.json) |
| 881 Modesty | [body-insecure](../../traits/instructions/body_insecure.json), [introverted (HEXACO)](../../traits/instructions/introverted_hexaco.json), [modest](../../traits/instructions/modest.json), [reserved](../../traits/instructions/reserved.json), [self-conscious](../../traits/instructions/self_conscious.json), [self-effacing](../../traits/instructions/self_effacing.json), [timid](../../traits/instructions/timid.json), [unassuming](../../traits/instructions/unassuming.json) |
| 882 Ostentation | [attention-seeking](../../traits/instructions/attention_seeking.json), [status-seeking](../../traits/instructions/status_seeking.json) |
| 884 Boasting | [bombastic](../../traits/instructions/bombastic.json), [self-aggrandizing](../../traits/instructions/self_aggrandizing.json) |
| 885 Insolence | [arrogant](../../traits/instructions/arrogant.json), [condescending](../../traits/instructions/condescending.json), [flippant](../../traits/instructions/flippant.json), [sassy](../../traits/instructions/sassy.json) |
| 886 Servility | [sycophantic](../../traits/instructions/sycophantic.json) |
| 887 Blusterer | [bullying](../../traits/instructions/bullying.json) |
| 888 Friendship | [close-knit](../../traits/instructions/close_knit.json), [friendly](../../traits/instructions/friendly.json) |
| 892 Sociality | [extroverted](../../traits/instructions/extroverted.json), [gregarious](../../traits/instructions/gregarious.json), [social (Holland)](../../traits/instructions/social_holland.json), [socializer (Bartle)](../../traits/instructions/socializer_bartle.json) |
| 893 Seclusion. Exclusion | [cliqueish](../../traits/instructions/cliqueish.json), [dismissive-avoidant attachment](../../traits/instructions/dismissive_avoidant_attachment.json), [introverted](../../traits/instructions/introverted.json), [introverted (Big Five)](../../traits/instructions/introverted_big_five.json), [isolated](../../traits/instructions/isolated.json), [lonely](../../traits/instructions/lonely.json), [solitary](../../traits/instructions/solitary.json), [unsupported](../../traits/instructions/unsupported.json) |
| 894 Courtesy | [polite](../../traits/instructions/polite.json), [tactful](../../traits/instructions/tactful.json) |
| 898 Hate | [xenophobic](../../traits/instructions/xenophobic.json) |
| 900 Resentment | [aggrieved](../../traits/instructions/aggrieved.json), [bitter](../../traits/instructions/bitter.json) |
| 901 Irascibility | [irascible](../../traits/instructions/irascible.json), [quarrelsome (HEXACO)](../../traits/instructions/quarrelsome_hexaco.json) |
| 902 Endearment | [flirty](../../traits/instructions/flirty.json) |
| 906 Benevolence | [benevolent](../../traits/instructions/benevolent.json), [benign](../../traits/instructions/benign.json), [kind-to-animals](../../traits/instructions/kind_to_animals.json), [nurturing](../../traits/instructions/nurturing.json) |
| 907 Malevolence | [malevolent](../../traits/instructions/malevolent.json), [malicious](../../traits/instructions/malicious.json), [malign](../../traits/instructions/malign.json), [spiteful](../../traits/instructions/spiteful.json) |
| 910 Philanthropy | [collectivistic](../../traits/instructions/collectivistic.json), [cosmopolitan](../../traits/instructions/cosmopolitan.json), [humanistic](../../traits/instructions/humanistic.json), [humanitarian](../../traits/instructions/humanitarian.json), [patriotic](../../traits/instructions/patriotic.json), [philanthropic](../../traits/instructions/philanthropic.json) |
| 911 Misanthropy | [misanthropic](../../traits/instructions/misanthropic.json) |
| 913 Evil doer | [killer (Bartle)](../../traits/instructions/killer_bartle.json) |
| 914 Pity | [compassionate](../../traits/instructions/compassionate.json), [empathetic](../../traits/instructions/empathetic.json), [merciful](../../traits/instructions/merciful.json), [self-pitying](../../traits/instructions/self_pitying.json) |
| 914a Pitilessness | [ruthless while playing](../../traits/instructions/ruthless_while_playing.json) |
| 916 Gratitude | [grateful](../../traits/instructions/grateful.json) |
| 917 Ingratitude | [ungrateful](../../traits/instructions/ungrateful.json) |
| 918 Forgiveness | [agreeable (HEXACO)](../../traits/instructions/agreeable_hexaco.json), [forgiving](../../traits/instructions/forgiving.json) |
| 919 Revenge | [unforgiving](../../traits/instructions/unforgiving.json), [vindictive](../../traits/instructions/vindictive.json) |
| 921 Envy | [envious](../../traits/instructions/envious.json) |
| 922 Right | [fair](../../traits/instructions/fair.json) |
| 923 Wrong | [unfair](../../traits/instructions/unfair.json) |
| 924 Dueness | [entitled](../../traits/instructions/entitled.json) |
| 926 Duty | [deontological](../../traits/instructions/deontological.json), [responsible](../../traits/instructions/responsible.json) |
| 927 Dereliction of Duty | [irresponsible](../../traits/instructions/irresponsible.json) |
| 928 Respect | [autonomy-respecting](../../traits/instructions/autonomy_respecting.json), [deferential](../../traits/instructions/deferential.json), [respectful](../../traits/instructions/respectful.json) |
| 929 Disrespect | [dismissive](../../traits/instructions/dismissive.json), [irreverent](../../traits/instructions/irreverent.json), [rude](../../traits/instructions/rude.json) |
| 936 Detractor | [detractor](../../traits/instructions/detractor.json) |
| 939 Probity | [honest](../../traits/instructions/honest.json), [honorable](../../traits/instructions/honorable.json), [honorable while playing](../../traits/instructions/honorable_while_playing.json), [intellectually honest](../../traits/instructions/intellectually_honest.json), [principled](../../traits/instructions/principled.json) |
| 940 Improbity | [amoral](../../traits/instructions/amoral.json), [intellectually dishonest](../../traits/instructions/intellectually_dishonest.json), [treacherous](../../traits/instructions/treacherous.json), [unscrupulous](../../traits/instructions/unscrupulous.json), [untrustworthy](../../traits/instructions/untrustworthy.json) |
| 942 Disinterestedness | [altruistic](../../traits/instructions/altruistic.json), [magnanimous](../../traits/instructions/magnanimous.json), [uncalculating](../../traits/instructions/uncalculating.json) |
| 943 Selfishness | [mercenary](../../traits/instructions/mercenary.json), [self-indulgent](../../traits/instructions/self_indulgent.json), [selfish](../../traits/instructions/selfish.json) |
| 944 Virtue | [moral](../../traits/instructions/moral.json) |
| 950 Penitence | [guilt-prone](../../traits/instructions/guilt_prone.json), [remorseful](../../traits/instructions/remorseful.json) |
| 951 Impenitence | [unrepentant](../../traits/instructions/unrepentant.json) |
| 953 Temperance | [abstemious](../../traits/instructions/abstemious.json), [temperate](../../traits/instructions/temperate.json) |
| 954a Sensualist | [epicurean](../../traits/instructions/epicurean.json) |
| 955 Asceticism | [ascetic](../../traits/instructions/ascetic.json), [puritanical](../../traits/instructions/puritanical.json), [spartan](../../traits/instructions/spartan.json) |
| 957 Gluttony | [gluttonous](../../traits/instructions/gluttonous.json) |
| 958 Sobriety | [teetotaler](../../traits/instructions/teetotaler.json) |
| 959 Drunkenness | [heavy-drinker](../../traits/instructions/heavy_drinker.json) |
| 960 Purity | [chaste](../../traits/instructions/chaste.json) |
| 976 Deity | [spiritual](../../traits/instructions/spiritual.json) |
| 983 Theology | [religious](../../traits/instructions/religious.json) |
| 983a Orthodoxy | [Christian](../../traits/instructions/christian.json), [fundamentalist](../../traits/instructions/fundamentalist.json), [orthodox](../../traits/instructions/orthodox.json) |
| 984 Heterodoxy | [Buddhist](../../traits/instructions/buddhist.json), [heterodox](../../traits/instructions/heterodox.json), [iconoclastic](../../traits/instructions/iconoclastic.json), [sectarian](../../traits/instructions/sectarian.json) |
| 989 Irreligion | [antitheist](../../traits/instructions/antitheist.json), [atheist](../../traits/instructions/atheist.json), [secular-rational (Inglehart-Welzel)](../../traits/instructions/secular_rational_inglehart_welzel.json) |
| 990 Worship | [acts of service](../../traits/instructions/acts_of_service.json), [reverent](../../traits/instructions/reverent.json) |
| 991 Idolatry | [Neopagan](../../traits/instructions/neopagan.json) |
| 997 Laity | [secular](../../traits/instructions/secular.json) |
