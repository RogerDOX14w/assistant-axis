# Roget coverage map (workstream 2)

Which of the dispositional heads of Roget's Thesaurus (1911; Classes IV-VI, intellect, volition and the affections, plus the Class I-III heads whose adjectives hold one of our labels) the trait corpus already occupies.  A **head** is one numbered entry of the thesaurus (604 Resolution); an **opposed head** is its correlative (605 Irresolution), reconstructed by rule in [head_pairs.json](./head_pairs.json).  Each trait is placed on heads by [label_heads.json](./label_heads.json): its **primary** head (where its sense sits) and any **secondary** heads (other senses the description also covers).  Data: [heads.json](./heads.json); spot check of the placement: [map_spotcheck.md](./map_spotcheck.md); method: [coding_plan_02_roget_wordnet.md](../../../reports/trait_gap_generation/coding_plan_02_roget_wordnet.md).

States: **covered** (an existing trait has the head as its primary), **partly covered** (only as a secondary), **queued** (only a label waiting in [seed_queue.json](../../seed_queue.json)), **empty**.  Gap classes: **pair_completion** (empty, its opposed head covered: a word here would complete a pair), **pair_empty** (empty, with an opposed head that is not covered), **singleton_empty** (empty, no opposed head found), **queued_only**, **partly_covered**, **crowded** (three or more traits have it as their primary), **covered**.

## Headline

- Heads in scope: **675** (576 dispositional, 99 from Classes I-III).
- Covered **311**, partly covered **75**, uncovered **289** (of which 36 have a queued label only).
- Opposed pairs in scope: both poles covered **75**, one pole **77**, neither **57** (by the pairing's evidence: {"rule": {"neither_pole_covered": 46, "both_poles_covered": 70, "one_pole_covered": 67}, "rule_weak": {"neither_pole_covered": 11, "one_pole_covered": 10, "both_poles_covered": 5}}).
- Labels placed: 615 existing traits with a primary head (175 without; 574 of the primaries in scope), 214 queued labels (148 without).
- Gap classes: pair_completion 37, pair_empty 46, singleton_empty 170, queued_only 36, partly_covered 75, crowded 64, covered 247.
- Pairing by rule only (the plan's LLM pass for the residue was dropped in the 2026-10-08 revision): 221 of 576 dispositional heads are unresolved and are treated as having no opposed head.

## By section

| class / section | covered | partly | queued | empty |
|---|---|---|---|---|
| I I. Existence | 2 | 1 | 0 | 0 |
| I II. Relation | 0 | 3 | 0 | 0 |
| I III. Quantity | 4 | 2 | 0 | 0 |
| I IV. Order | 4 | 2 | 0 | 0 |
| I V. Number | 0 | 1 | 0 | 0 |
| I VI. Time | 6 | 0 | 0 | 0 |
| I VII. Change | 2 | 1 | 0 | 0 |
| I VIII. Causation | 8 | 3 | 0 | 0 |
| II I. Space in general | 3 | 0 | 1 | 0 |
| II II. Dimensions | 2 | 3 | 5 | 0 |
| II III. Form | 4 | 1 | 0 | 0 |
| II IV. Motion | 2 | 6 | 2 | 0 |
| III I. Matter in general | 2 | 0 | 0 | 0 |
| III II. Inorganic matter | 6 | 2 | 0 | 0 |
| III III. Organic matter | 10 | 5 | 6 | 0 |
| IV I. Operations of intellect in general | 2 | 0 | 1 | 3 |
| IV II. Precursory conditions and operations | 9 | 0 | 0 | 6 |
| IV III. Materials for reasoning | 3 | 0 | 0 | 6 |
| IV IV. Reasoning processes | 3 | 1 | 0 | 0 |
| IV V. Results of reasoning | 16 | 2 | 0 | 8 |
| IV VI. Extension of thought | 1 | 2 | 0 | 6 |
| IV VII. Creative thought | 2 | 0 | 0 | 1 |
| IV I. Nature of ideas communicated | 4 | 1 | 0 | 4 |
| IV II. Modes of communication | 10 | 2 | 0 | 14 |
| IV III. Means of communicating ideas | 17 | 2 | 1 | 30 |
| V I. Volition in general | 12 | 4 | 1 | 6 |
| V II. Prospective volition | 24 | 5 | 3 | 28 |
| V III. Voluntary action | 12 | 2 | 1 | 9 |
| V IV. Antagonism | 12 | 4 | 0 | 9 |
| V V. Results of voluntary action | 3 | 1 | 0 | 4 |
| V I. General intersocial volition | 11 | 2 | 2 | 10 |
| V II. Special intersocial volition | 1 | 0 | 0 | 7 |
| V III. Conditional intersocial volition | 1 | 1 | 1 | 5 |
| V IV. Possessive relations | 14 | 1 | 1 | 35 |
| VI I. Affections in general | 7 | 0 | 0 | 0 |
| VI II. Personal affections | 39 | 3 | 3 | 17 |
| VI III. Sympathetic affections | 19 | 5 | 2 | 10 |
| VI IV. Moral affections | 25 | 4 | 4 | 23 |
| VI V. Religious affections | 9 | 3 | 2 | 12 |

## pair_completion (37)

| head | section | opposed head | its traits | queued | parked | secondary of |
|---|---|---|---|---|---|---|
| 452 Incogitancy | IV I. Operations of intellect in general | 451 Thought (rule) | [abstract](../../traits/instructions/abstract.json), [introspective](../../traits/instructions/introspective.json), [meditative](../../traits/instructions/meditative.json), [pensive](../../traits/instructions/pensive.json), [philosophical](../../traits/instructions/philosophical.json), [speculative](../../traits/instructions/speculative.json) | - | - | - |
| 465 Discrimination | IV II. Precursory conditions and operations | 465a Indiscrimination (rule) | [promiscuous](../../traits/instructions/promiscuous.json) | - | - | - |
| 488 Assent | IV V. Results of reasoning | 489 Dissent (rule_weak) | [nonconformist](../../traits/instructions/nonconformist.json) | - | [acquiescence](../../seed_queue.json) (queued) | - |
| 502 Sanity | IV V. Results of reasoning | 503 Insanity (rule) | [manic](../../traits/instructions/manic.json), [neurotic](../../traits/instructions/neurotic.json) | - | [rational](../../seed_queue.json) (queued) | - |
| 523 Misinterpretation | IV I. Nature of ideas communicated | 522 Interpretation (rule) | [expository](../../traits/instructions/expository.json) | - | - | - |
| 526 Latency. Implication | IV II. Modes of communication | 525 Manifestation (rule) | [expressive](../../traits/instructions/expressive.json) | - | - | - |
| 529 Disclosure | IV II. Modes of communication | 528 Concealment (rule_weak) | [cryptic](../../traits/instructions/cryptic.json), [esoteric](../../traits/instructions/esoteric.json) | - | - | - |
| 536 Negation | IV II. Modes of communication | 535 Affirmation (rule) | [emphatic](../../traits/instructions/emphatic.json), [words of affirmation](../../traits/instructions/words_of_affirmation.json) | - | - | - |
| 538 Misteaching | IV II. Modes of communication | 537 Teaching (rule) | [didactic](../../traits/instructions/didactic.json), [educational](../../traits/instructions/educational.json), [technical](../../traits/instructions/technical.json) | - | - | - |
| 579 Inelegance | IV III. Means of communicating ideas / 1. Language generally | 578 Elegance (rule) | [formal](../../traits/instructions/formal.json) | - | - | - |
| 585 Taciturnity | IV III. Means of communicating ideas / 1. Language generally | 584 Loquacity (rule) | [glib](../../traits/instructions/glib.json) | - | - | - |
| 603 Unwillingness | V I. Volition in general / 1. Acts of Volition | 602 Willingness (rule) | [growth-minded](../../traits/instructions/growth_minded.json), [open-minded](../../traits/instructions/open_minded.json) | - | - | - |
| 607 Tergiversation | V I. Volition in general / 1. Acts of Volition | 608 Caprice (rule_weak) | [eccentric](../../traits/instructions/eccentric.json), [erratic](../../traits/instructions/erratic.json), [whimsical](../../traits/instructions/whimsical.json) | - | - | - |
| 640 Insufficiency | V II. Prospective volition / 1. Actual Subservience | 639 Sufficiency (rule) | [satisficing](../../traits/instructions/satisficing.json) | - | - | - |
| 643 Unimportance | V II. Prospective volition / 1. Actual Subservience | 642 Importance (rule) | [capitalist](../../traits/instructions/capitalist.json), [serious](../../traits/instructions/serious.json) | - | [hierarchy-indifferent](../../seed_queue.json) (queued) | - |
| 647 Inexpedience | V II. Prospective volition / 1. Actual Subservience | 646 Expedience (rule) | [expedient](../../traits/instructions/expedient.json) | - | - | - |
| 651 Imperfection | V II. Prospective volition / 1. Actual Subservience | 650 Perfection (rule) | [perfectionist](../../traits/instructions/perfectionist.json) | - | - | - |
| 652 Cleanness | V II. Prospective volition / 1. Actual Subservience | 653 Uncleanness (rule) | [slovenly](../../traits/instructions/slovenly.json) | - | - | - |
| 674 Nonpreparation | V II. Prospective volition / 3. Precursory measures | 673 Preparation (rule) | [proactive](../../traits/instructions/proactive.json) | - | - | - |
| 680 Action | V III. Voluntary action / 1. Simple voluntary Action | 681 Inaction (rule) | [passive](../../traits/instructions/passive.json) | - | - | - |
| 687 Repose | V III. Voluntary action / 1. Simple voluntary Action | 686 Exertion (rule_weak) | [industrious](../../traits/instructions/industrious.json) | - | - | - |
| 717 Defense | V IV. Antagonism / 2. Active Antagonism | 716 Attack (rule) | [aggressive](../../traits/instructions/aggressive.json), [passive-aggressive](../../traits/instructions/passive_aggressive.json) | - | - | - |
| 735 Adversity | V V. Results of voluntary action | 734 Prosperity (rule) | [flourishing](../../traits/instructions/flourishing.json) | - | - | - |
| 750 Liberation | V I. General intersocial volition | 751 Restraint (rule_weak) | [uptight](../../traits/instructions/uptight.json) | - | - | - |
| 761 Prohibition | V II. Special intersocial volition | 760 Permission (rule) | [permissive](../../traits/instructions/permissive.json), [permissive (Baumrind)](../../traits/instructions/permissive_baumrind.json) | - | - | - |
| 775 Acquisition | V IV. Possessive relations / 1. Property in general | 776 Loss (rule_weak) | [loss-averse](../../traits/instructions/loss_averse.json), [rootless](../../traits/instructions/rootless.json) | - | - | - |
| 841 Weariness | VI II. Personal affections | 840 Amusement (rule) | [entertaining](../../traits/instructions/entertaining.json), [playful](../../traits/instructions/playful.json) | - | - | - |
| 848 Blemish | VI II. Personal affections | 849 Simplicity (rule_weak) | [unpretentious](../../traits/instructions/unpretentious.json) | - | - | - |
| 871 Expectance | VI II. Personal affections | 870 Wonder (rule) | [wide-eyed](../../traits/instructions/wide_eyed.json) | - | - | - |
| 874 Disrepute | VI II. Personal affections | 873 Repute (rule) | [popular](../../traits/instructions/popular.json) | - | - | - |
| 889 Enmity | VI III. Sympathetic affections | 888 Friendship (rule) | [friendly](../../traits/instructions/friendly.json) | - | - | - |
| 914a Pitilessness | VI III. Sympathetic affections | 914 Pity (rule) | [compassionate](../../traits/instructions/compassionate.json), [merciful](../../traits/instructions/merciful.json), [self-pitying](../../traits/instructions/self_pitying.json) | - | - | - |
| 925 Undueness | VI IV. Moral affections | 924 Dueness (rule) | [entitled](../../traits/instructions/entitled.json) | - | - | - |
| 927 Dereliction of Duty | VI IV. Moral affections | 926 Duty (rule) | [conscientious (Big Five)](../../traits/instructions/conscientious_big_five.json), [deontological](../../traits/instructions/deontological.json), [responsible](../../traits/instructions/responsible.json) | - | - | - |
| 945 Vice | VI IV. Moral affections | 944 Virtue (rule) | [moral](../../traits/instructions/moral.json) | - | - | - |
| 961 Impurity | VI IV. Moral affections | 960 Purity (rule) | [chaste](../../traits/instructions/chaste.json) | - | - | - |
| 970 Acquittal | VI IV. Moral affections | 971 Condemnation (rule) | [judgmental](../../traits/instructions/judgmental.json) | - | - | - |

## pair_empty (46)

| head | section | opposed head | its traits | queued | parked | secondary of |
|---|---|---|---|---|---|---|
| 464 Comparison | IV II. Precursory conditions and operations | 464a Incomparability (rule) | - | - | - | - |
| 464a Incomparability | IV II. Precursory conditions and operations | 464 Comparison (rule) | - | - | - | - |
| 470 Possibility | IV III. Materials for reasoning | 471 Impossibility (rule) | - | - | - | - |
| 471 Impossibility | IV III. Materials for reasoning | 470 Possibility (rule) | - | - | - | - |
| 472 Probability | IV III. Materials for reasoning | 473 Improbability (rule) | - | - | [hopeful](../../seed_queue.json) (queued) | - |
| 473 Improbability | IV III. Materials for reasoning | 472 Probability (rule) | - | - | - | - |
| 507 Expectation | IV VI. Extension of thought / 1. To the Past | 508 Inexpectation (rule) | - | - | - | - |
| 508 Inexpectation | IV VI. Extension of thought / 1. To the Past | 507 Expectation (rule) | - | - | - | - |
| 517 Unmeaningness | IV I. Nature of ideas communicated | 516 Meaning (rule) | - | - | - | - |
| 554 Representation | IV III. Means of communicating ideas / 1. Natural means | 555 Misrepresentation (rule) | - | - | - | - |
| 555 Misrepresentation | IV III. Means of communicating ideas / 1. Natural means | 554 Representation (rule) | - | - | - | - |
| 564 Nomenclature | IV III. Means of communicating ideas / 1. Language generally | 565 Misnomer (rule_weak) | - | - | - | - |
| 565 Misnomer | IV III. Means of communicating ideas / 1. Language generally | 564 Nomenclature (rule_weak) | - | - | - | - |
| 580 Voice | IV III. Means of communicating ideas / 1. Language generally | 581 Aphony (rule) | - | - | - | - |
| 614 Desuetude | V I. Volition in general / 1. Acts of Volition | 613 Habit (rule) | - | - | - | - |
| 621 Chance | V II. Prospective volition / 1. Conceptional volition | 620 Intention (rule) | - | - | - | - |
| 657 Insalubrity | V II. Prospective volition / 1. Actual Subservience | 656 Salubrity (rule) | - | - | - | - |
| 677 Use | V II. Prospective volition / 3. Precursory measures | 678 Disuse (rule_weak) | - | - | [applied](../../seed_queue.json) (queued) | - |
| 678 Disuse | V II. Prospective volition / 3. Precursory measures | 677 Use (rule_weak) | - | - | - | - |
| 688 Fatigue | V III. Voluntary action / 1. Simple voluntary Action | 689 Refreshment (rule) | - | - | - | - |
| 689 Refreshment | V III. Voluntary action / 1. Simple voluntary Action | 688 Fatigue (rule) | - | - | - | - |
| 713 Discord | V IV. Antagonism / 2. Active Antagonism | 714 Concord (rule) | - | - | - | - |
| 729 Completion | V V. Results of voluntary action | 730 Noncompletion (rule) | - | - | [conclusive](../../seed_queue.json) (queued) | - |
| 730 Noncompletion | V V. Results of voluntary action | 729 Completion (rule) | - | - | - | - |
| 805 Credit | V IV. Possessive relations / 4. Monetary Relations | 806 Debt (rule_weak) | - | - | - | - |
| 806 Debt | V IV. Possessive relations / 4. Monetary Relations | 805 Credit (rule_weak) | - | - | - | - |
| 807 Payment | V IV. Possessive relations / 4. Monetary Relations | 808 Nonpayment (rule) | - | - | - | - |
| 808 Nonpayment | V IV. Possessive relations / 4. Monetary Relations | 807 Payment (rule) | - | - | - | - |
| 812a Value | V IV. Possessive relations / 4. Monetary Relations | 812b Worthlessness (rule) | - | - | [lifetime value](../../seed_queue.json) (queued) | - |
| 812b Worthlessness | V IV. Possessive relations / 4. Monetary Relations | 812a Value (rule) | - | - | - | - |
| 814 Dearness | V IV. Possessive relations / 4. Monetary Relations | 815 Cheapness (rule) | - | - | - | - |
| 815 Cheapness | V IV. Possessive relations / 4. Monetary Relations | 814 Dearness (rule) | - | - | - | - |
| 834 Relief | VI II. Personal affections | 835 Aggravation (rule_weak) | - | - | - | - |
| 846 Ugliness | VI II. Personal affections | 845 Beauty (rule) | - | - | - | - |
| 891 Enemy | VI III. Sympathetic affections | 890 Friend (rule_weak) | - | - | - | - |
| 937 Vindication | VI IV. Moral affections | 938 Accusation (rule) | - | - | - | - |
| 938 Accusation | VI IV. Moral affections | 937 Vindication (rule) | - | - | - | - |
| 963 Legality | VI IV. Moral affections | 964 Illegality (rule) | - | - | - | - |
| 964 Illegality | VI IV. Moral affections | 963 Legality (rule) | - | - | - | - |
| 973 Reward | VI IV. Moral affections | 974 Penalty (rule_weak) | - | - | - | - |
| 977 Angel | VI V. Religious affections | 978 Satan (rule_weak) | - | - | - | - |
| 978 Satan | VI V. Religious affections | 977 Angel (rule_weak) | - | - | - | - |
| 979 Jupiter | VI V. Religious affections | 980 Demon (rule_weak) | - | - | - | - |
| 980 Demon | VI V. Religious affections | 979 Jupiter (rule_weak) | - | - | - | - |
| 981 Heaven | VI V. Religious affections | 982 Hell (rule) | - | - | - | - |
| 982 Hell | VI V. Religious affections | 981 Heaven (rule) | - | - | - | - |

## singleton_empty (170)

| head | section | opposed head | its traits | queued | parked | secondary of |
|---|---|---|---|---|---|---|
| 453 Idea | IV I. Operations of intellect in general | - | - | - | - | - |
| 454 Topic | IV I. Operations of intellect in general | - | - | - | - | - |
| 462 Answer | IV II. Precursory conditions and operations | - | - | - | - | - |
| 465b Identification | IV II. Precursory conditions and operations | - | - | - | - | - |
| 466 Measurement | IV II. Precursory conditions and operations | - | - | - | - | - |
| 468 Counter Evidence | IV III. Materials for reasoning | - | - | - | - | - |
| 469 Qualification | IV III. Materials for reasoning | - | - | - | - | - |
| 480a Discovery | IV V. Results of reasoning | - | - | - | - | - |
| 492 Scholar | IV V. Results of reasoning | - | - | - | - | - |
| 493 Ignoramus | IV V. Results of reasoning | - | - | - | - | - |
| 497 Absurdity | IV V. Results of reasoning | - | - | - | - | - |
| 501 Fool | IV V. Results of reasoning | - | - | - | - | - |
| 504 Madman | IV V. Results of reasoning | - | - | - | - | - |
| 510 Foresight | IV VI. Extension of thought / 1. To the Past | - | - | - | - | - |
| 511 Prediction | IV VI. Extension of thought / 1. To the Past | - | - | - | - | - |
| 512 Omen | IV VI. Extension of thought / 1. To the Past | - | - | - | - | - |
| 513 Oracle | IV VI. Extension of thought / 1. To the Past | - | - | - | - | - |
| 514a Analogy | IV VII. Creative thought | - | - | - | - | - |
| 520 Equivocalness | IV I. Nature of ideas communicated | - | - | - | - | - |
| 524 Interpreter | IV I. Nature of ideas communicated | - | - | - | - | - |
| 527a Correction | IV II. Modes of communication | - | - | - | - | - |
| 530 Ambush | IV II. Modes of communication | - | - | - | - | - |
| 531 Publication | IV II. Modes of communication | - | - | - | - | - |
| 534 Messenger | IV II. Modes of communication | - | - | - | - | - |
| 540 Teacher | IV II. Modes of communication | - | - | - | - | - |
| 541 Learner | IV II. Modes of communication | - | - | - | - | - |
| 546 Untruth | IV II. Modes of communication | - | - | - | - | - |
| 547 Dupe | IV II. Modes of communication | - | - | - | - | - |
| 548 Deceiver | IV II. Modes of communication | - | - | - | - | - |
| 549 Exaggeration | IV II. Modes of communication | - | - | - | - | - |
| 550 Indication | IV III. Means of communicating ideas / 1. Natural means | - | - | - | - | - |
| 551 Record | IV III. Means of communicating ideas / 1. Natural means | - | - | - | - | - |
| 552 Obliteration | IV III. Means of communicating ideas / 1. Natural means | - | - | - | - | - |
| 553 Recorder | IV III. Means of communicating ideas / 1. Natural means | - | - | - | - | - |
| 557 Sculpture | IV III. Means of communicating ideas / 1. Natural means | - | - | - | - | - |
| 558 Engraving | IV III. Means of communicating ideas / 1. Natural means | - | - | - | - | - |
| 560 Language | IV III. Means of communicating ideas / 1. Language generally | - | - | - | [language](../../seed_queue.json) (queued) | - |
| 562 Word | IV III. Means of communicating ideas / 1. Language generally | - | - | - | - | - |
| 563 Neologism | IV III. Means of communicating ideas / 1. Language generally | - | - | - | - | - |
| 566 Phrase | IV III. Means of communicating ideas / 1. Language generally | - | - | - | - | - |
| 567 Grammar | IV III. Means of communicating ideas / 1. Language generally | - | - | - | - | - |
| 568 Solecism | IV III. Means of communicating ideas / 1. Language generally | - | - | - | - | - |
| 569 Style | IV III. Means of communicating ideas / 1. Language generally | - | - | - | - | - |
| 570 Perspicuity | IV III. Means of communicating ideas / 1. Language generally | - | - | - | - | - |
| 586 Allocution | IV III. Means of communicating ideas / 1. Language generally | - | - | - | - | - |
| 587 Response | IV III. Means of communicating ideas / 1. Language generally | - | - | - | - | - |
| 588 Conversation | IV III. Means of communicating ideas / 1. Language generally | - | - | - | - | - |
| 589 Soliloquy | IV III. Means of communicating ideas / 1. Language generally | - | - | - | - | - |
| 591 Printing | IV III. Means of communicating ideas / 1. Language generally | - | - | - | - | - |
| 592 Correspondence | IV III. Means of communicating ideas / 1. Language generally | - | - | - | - | - |
| 593 Book | IV III. Means of communicating ideas / 1. Language generally | - | - | - | - | - |
| 595 Dissertation | IV III. Means of communicating ideas / 1. Language generally | - | - | - | - | - |
| 596 Compendium | IV III. Means of communicating ideas / 1. Language generally | - | - | - | - | - |
| 610 Rejection | V I. Volition in general / 1. Acts of Volition | - | - | - | - | - |
| 615a Absence of Motive | V I. Volition in general / 2. Causes of Volition | - | - | - | - | - |
| 617 Pretext | V I. Volition in general / 2. Causes of Volition | - | - | - | - | - |
| 622 Pursuit | V II. Prospective volition / 1. Conceptional volition | - | - | - | - | - |
| 629 Circuit | V II. Prospective volition / 1. Conceptional volition | - | - | - | - | - |
| 630 Requirement | V II. Prospective volition / 1. Conceptional volition | - | - | - | - | - |
| 631 Instrumentality | V II. Prospective volition / 1. Actual Subservience | - | - | - | - | - |
| 634 Substitute | V II. Prospective volition / 1. Actual Subservience | - | - | - | - | - |
| 635 Materials | V II. Prospective volition / 1. Actual Subservience | - | - | - | - | - |
| 636 Store | V II. Prospective volition / 1. Actual Subservience | - | - | - | - | - |
| 637 Provision | V II. Prospective volition / 1. Actual Subservience | - | - | - | - | - |
| 660 Restoration | V II. Prospective volition / 1. Actual Subservience | - | - | - | - | - |
| 661 Relapse | V II. Prospective volition / 1. Actual Subservience | - | - | - | - | - |
| 662 Remedy | V II. Prospective volition / 1. Actual Subservience | - | - | - | - | - |
| 663 Bane | V II. Prospective volition / 1. Actual Subservience | - | - | - | - | - |
| 666 Refuge | V II. Prospective volition / 1. Actual Subservience | - | - | - | - | - |
| 667 Pitfall | V II. Prospective volition / 1. Actual Subservience | - | - | - | - | - |
| 669 Alarm | V II. Prospective volition / 1. Actual Subservience | - | - | - | - | - |
| 671 Escape | V II. Prospective volition / 1. Actual Subservience | - | - | - | - | - |
| 672 Deliverance | V II. Prospective volition / 1. Actual Subservience | - | - | - | - | - |
| 679 Misuse | V II. Prospective volition / 3. Precursory measures | - | - | - | - | - |
| 690 Agent | V III. Voluntary action / 1. Simple voluntary Action | - | - | - | - | - |
| 691 Workshop | V III. Voluntary action / 1. Simple voluntary Action | - | - | - | - | - |
| 694 Director | V III. Voluntary action / 2. Complex Voluntary Action | - | - | - | - | - |
| 696 Council | V III. Voluntary action / 2. Complex Voluntary Action | - | - | - | - | - |
| 701 Bungler | V III. Voluntary action / 2. Complex Voluntary Action | - | - | - | - | - |
| 706 Hindrance | V IV. Antagonism / 2. Active Antagonism | - | - | - | - | - |
| 711 Auxiliary | V IV. Antagonism / 2. Active Antagonism | - | - | - | - | - |
| 712 Party | V IV. Antagonism / 2. Active Antagonism | - | - | - | - | - |
| 718 Retaliation | V IV. Antagonism / 2. Active Antagonism | - | - | - | - | - |
| 719 Resistance | V IV. Antagonism / 2. Active Antagonism | - | - | - | - | - |
| 727 Arms | V IV. Antagonism / 2. Active Antagonism | - | - | - | - | - |
| 728 Arena | V IV. Antagonism / 2. Active Antagonism | - | - | - | - | - |
| 733 Trophy | V V. Results of voluntary action | - | - | - | - | - |
| 747 Scepter | V I. General intersocial volition | - | - | - | - | - |
| 752 Prison | V I. General intersocial volition | - | - | - | - | - |
| 753 Keeper | V I. General intersocial volition | - | - | - | - | - |
| 754 Prisoner | V I. General intersocial volition | - | - | - | - | - |
| 755 Commission | V I. General intersocial volition | - | - | - | - | - |
| 756 Abrogation | V I. General intersocial volition | - | - | - | - | - |
| 757 Resignation | V I. General intersocial volition | - | - | - | - | - |
| 758 Consignee | V I. General intersocial volition | - | - | - | - | - |
| 759 Deputy | V I. General intersocial volition | - | - | - | - | - |
| 762 Consent | V II. Special intersocial volition | - | - | - | [acquiescence](../../seed_queue.json) (queued) | - |
| 763 Offer | V II. Special intersocial volition | - | - | - | [tender](../../seed_queue.json) (queued) | - |
| 764 Refusal | V II. Special intersocial volition | - | - | - | - | - |
| 765 Request | V II. Special intersocial volition | - | - | - | - | - |
| 766 Deprecation | V II. Special intersocial volition | - | - | - | - | - |
| 767 Petitioner | V II. Special intersocial volition | - | - | - | - | - |
| 768 Promise | V III. Conditional intersocial volition | - | - | - | - | - |
| 768a Release from engagement | V III. Conditional intersocial volition | - | - | - | - | - |
| 770 Conditions | V III. Conditional intersocial volition | - | - | - | - | - |
| 771 Security | V III. Conditional intersocial volition | - | - | - | [secure](../../seed_queue.json) (queued) | - |
| 774 Compromise | V III. Conditional intersocial volition | - | - | - | [commute](../../seed_queue.json) (queued) | - |
| 777 Possession | V IV. Possessive relations / 1. Property in general | - | - | - | - | - |
| 777a Exemption | V IV. Possessive relations / 1. Property in general | - | - | - | - | - |
| 780 Property | V IV. Possessive relations / 1. Property in general | - | - | - | [device ownership](../../seed_queue.json) (queued) | - |
| 782 Relinquishment | V IV. Possessive relations / 1. Property in general | - | - | - | - | - |
| 783 Transfer | V IV. Possessive relations / 2. Transfer of Property | - | - | - | - | - |
| 786 Apportionment | V IV. Possessive relations / 2. Transfer of Property | - | - | - | - | - |
| 787 Lending | V IV. Possessive relations / 2. Transfer of Property | - | - | - | - | - |
| 788 Borrowing | V IV. Possessive relations / 2. Transfer of Property | - | - | - | - | - |
| 789 Taking | V IV. Possessive relations / 2. Transfer of Property | - | - | - | - | - |
| 790 Restitution | V IV. Possessive relations / 2. Transfer of Property | - | - | - | - | - |
| 791 Stealing | V IV. Possessive relations / 2. Transfer of Property | - | - | - | [thieving](../../seed_queue.json) (queued) | - |
| 792 Thief | V IV. Possessive relations / 2. Transfer of Property | - | - | - | - | - |
| 793 Booty | V IV. Possessive relations / 2. Transfer of Property | - | - | - | - | - |
| 794 Barter | V IV. Possessive relations / 3. Interchange of Property | - | - | - | - | - |
| 795 Purchase | V IV. Possessive relations / 3. Interchange of Property | - | - | - | - | - |
| 796 Sale | V IV. Possessive relations / 3. Interchange of Property | - | - | - | - | - |
| 797 Merchant | V IV. Possessive relations / 3. Interchange of Property | - | - | - | - | - |
| 798 Merchandise | V IV. Possessive relations / 3. Interchange of Property | - | - | - | - | - |
| 799a Stock Market | V IV. Possessive relations / 3. Interchange of Property | - | - | - | - | - |
| 799b Securities | V IV. Possessive relations / 3. Interchange of Property | - | - | - | - | - |
| 801 Treasurer | V IV. Possessive relations / 4. Monetary Relations | - | - | - | - | - |
| 802 Treasury | V IV. Possessive relations / 4. Monetary Relations | - | - | - | - | - |
| 809 Expenditure | V IV. Possessive relations / 4. Monetary Relations | - | - | - | - | - |
| 810 Receipt | V IV. Possessive relations / 4. Monetary Relations | - | - | - | - | - |
| 812 Price | V IV. Possessive relations / 4. Monetary Relations | - | - | - | - | - |
| 813 Discount | V IV. Possessive relations / 4. Monetary Relations | - | - | - | - | - |
| 838 Rejoicing | VI II. Personal affections | - | - | - | - | - |
| 839 Lamentation | VI II. Personal affections | - | - | - | - | - |
| 847 Ornament | VI II. Personal affections | - | - | - | - | - |
| 847a Jewelry | VI II. Personal affections | - | - | - | - | - |
| 854 Fop | VI II. Personal affections | - | - | - | - | - |
| 857 Laughingstock | VI II. Personal affections | - | - | - | - | - |
| 869 Satiety | VI II. Personal affections | - | - | - | - | - |
| 872 Prodigy | VI II. Personal affections | - | - | - | - | - |
| 877 Title | VI II. Personal affections | - | - | - | - | - |
| 883 Celebration | VI II. Personal affections | - | - | - | - | - |
| 887 Blusterer | VI II. Personal affections | - | - | - | - | - |
| 896 Congratulation | VI III. Sympathetic affections | - | - | - | - | - |
| 901a Sullenness | VI III. Sympathetic affections | - | - | - | - | - |
| 902 Endearment | VI III. Sympathetic affections | - | - | - | - | - |
| 905 Divorce | VI III. Sympathetic affections | - | - | - | - | - |
| 908 Malediction | VI III. Sympathetic affections | - | - | - | - | - |
| 909 Threat | VI III. Sympathetic affections | - | - | - | - | - |
| 912 Benefactor | VI III. Sympathetic affections | - | - | - | - | - |
| 927a Exemption | VI IV. Moral affections | - | - | - | - | - |
| 934 Detraction | VI IV. Moral affections | - | - | - | - | - |
| 941 Knave | VI IV. Moral affections | - | - | - | - | - |
| 949 Bad Man | VI IV. Moral affections | - | - | - | - | - |
| 952 Atonement | VI IV. Moral affections | - | - | - | - | - |
| 956 Fasting | VI IV. Moral affections | - | - | - | - | - |
| 962 Libertine | VI IV. Moral affections | - | - | - | - | - |
| 965 Jurisdiction | VI IV. Moral affections | - | - | - | - | - |
| 966 Tribunal | VI IV. Moral affections | - | - | - | - | - |
| 968 Lawyer | VI IV. Moral affections | - | - | - | - | - |
| 969 Lawsuit | VI IV. Moral affections | - | - | - | - | - |
| 972 Punishment | VI IV. Moral affections | - | - | - | - | - |
| 975 Scourge | VI IV. Moral affections | - | - | - | - | - |
| 986 Pseudo-Revelation | VI V. Religious affections | - | - | - | - | - |
| 991 Idolatry | VI V. Religious affections | - | - | - | - | - |
| 993 Spell | VI V. Religious affections | - | - | - | - | - |
| 994 Sorcerer | VI V. Religious affections | - | - | - | - | - |
| 999 Canonicals | VI V. Religious affections | - | - | - | - | - |
| 1000 Temple | VI V. Religious affections | - | - | - | - | - |

## queued_only (36)

| head | section | opposed head | its traits | queued | parked | secondary of |
|---|---|---|---|---|---|---|
| 188 Inhabitant | II I. Space in general | - | - | [british](../../seed_queue.json) (queued), [canadian](../../seed_queue.json) (queued), [pacific islander](../../seed_queue.json) (queued) | - | - |
| 201 Shortness | II II. Dimensions | 200 Length (rule) | - | [short](../../seed_queue.json) (queued) | - | - |
| 203 Narrowness. Thinness | II II. Dimensions | 202 Breadth, Thickness (rule) | - | [slender](../../seed_queue.json) (queued) | - | - |
| 206 Height | II II. Dimensions | 207 Lowness (rule) | - | [tall](../../seed_queue.json) (queued) | - | - |
| 227 Circumjacence | II II. Dimensions / 1. General | - | - | [suburban](../../seed_queue.json) (queued) | - | - |
| 239 Sinistrality | II II. Dimensions / 1. General | 238 Dextrality (rule) | - | [left-handed](../../seed_queue.json) (queued) | - | - |
| 265 Quiescence | II IV. Motion | 264 Motion (rule) | - | [sedentary](../../seed_queue.json) (queued) | - | - |
| 304 Shortcoming | II IV. Motion | - | - | [short](../../seed_queue.json) (queued) | - | - |
| 378 Physical Pain | III III. Organic matter / 1. Sensation in general | 377 Physical Pleasure (rule) | [hedonistic](../../traits/instructions/hedonistic.json) | [in-pain](../../seed_queue.json) (queued) | - | - |
| 391 Insipidity | III III. Organic matter / 1. Sensation in general | 392 Pungency (rule) | - | [bland](../../seed_queue.json) (queued) | - | - |
| 419 Deafness | III III. Organic matter / 1. Sensation in general | 418 Hearing (rule) | [aural (VARK)](../../traits/instructions/aural_vark.json) | [deaf](../../seed_queue.json) (queued) | - | - |
| 433 Brown | III III. Organic matter / 1. Sensation in general | - | - | [brunette](../../seed_queue.json) (queued) | - | - |
| 442 Blindness | III III. Organic matter / 1. Sensation in general | 441 Vision (rule) | [visual (VARK)](../../traits/instructions/visual_vark.json) | [blind](../../seed_queue.json) (queued) | - | - |
| 447 Invisibility | III III. Organic matter / 1. Sensation in general | 446 Visibility (rule) | - | [obscure](../../seed_queue.json) (queued) | - | - |
| 450a Absence or want of Intellect | IV I. Operations of intellect in general | 450 Intellect (rule) | [cerebral](../../traits/instructions/cerebral.json) | [Intellect (BFAS)](../../seed_queue.json) (queued), [Intellect (IPIP-NEO)](../../seed_queue.json) (queued) | - | - |
| 571 Obscurity | IV III. Means of communicating ideas / 1. Language generally | - | - | [obscure](../../seed_queue.json) (queued) | - | - |
| 609a Absence of Choice | V I. Volition in general / 1. Acts of Volition | 609 Choice (rule) | [eclectic](../../traits/instructions/eclectic.json) | [neuter](../../seed_queue.json) (queued) | - | - |
| 620 Intention | V II. Prospective volition / 1. Conceptional volition | 621 Chance (rule) | - | [purposeful](../../seed_queue.json) (queued) | - | - |
| 624 Relinquishment | V II. Prospective volition / 1. Conceptional volition | - | - | [Withdrawal (BFAS)](../../seed_queue.json) (queued) | - | - |
| 654 Health | V II. Prospective volition / 1. Actual Subservience | 655 Disease (rule) | - | [healthy](../../seed_queue.json) (queued) | - | - |
| 700 Proficient | V III. Voluntary action / 2. Complex Voluntary Action | - | - | [mastery](../../seed_queue.json) (queued) | - | - |
| 745 Master | V I. General intersocial volition | - | - | [mastery](../../seed_queue.json) (queued) | - | - |
| 746 Servant | V I. General intersocial volition | - | - | [mercenary](../../seed_queue.json) (queued) | - | - |
| 773 Nonobservance | V III. Conditional intersocial volition | 772 Observance (rule) | - | [literal-explicitness / withholding-evasion (tentative, PC14)](../../seed_queue.json) (queued) | - | - |
| 799 Mart | V IV. Possessive relations / 3. Interchange of Property | - | - | [free-market](../../seed_queue.json) (queued) | - | - |
| 828 Pain | VI II. Personal affections | 827 Pleasure (rule) | - | [in-pain](../../seed_queue.json) (queued) | - | - |
| 835 Aggravation | VI II. Personal affections | 834 Relief (rule_weak) | - | [aggrieved](../../seed_queue.json) (queued) | - | - |
| 845 Beauty | VI II. Personal affections | 846 Ugliness (rule) | - | [good-looking](../../seed_queue.json) (queued) | - | - |
| 897 Love | VI III. Sympathetic affections | 898 Hate (rule) | - | [devoted](../../seed_queue.json) (queued), [enthusiastic (BFAS)](../../seed_queue.json) (queued) | - | - |
| 915 Condolence | VI III. Sympathetic affections | - | - | [Sympathy (IPIP-NEO)](../../seed_queue.json) (queued) | - | - |
| 936 Detractor | VI IV. Moral affections | - | - | [detractor](../../seed_queue.json) (queued) | - | - |
| 947 Guilt | VI IV. Moral affections | 946 Innocence (rule) | - | [guilt-prone](../../seed_queue.json) (queued) | - | - |
| 967 Judge | VI IV. Moral affections | - | - | [judging (MBTI)](../../seed_queue.json) (queued) | - | - |
| 974 Penalty | VI IV. Moral affections | 973 Reward (rule_weak) | - | [in-pain](../../seed_queue.json) (queued) | - | - |
| 985 Judeo-Christian Revelation | VI V. Religious affections | - | - | [jewish](../../seed_queue.json) (queued) | - | - |
| 995 Churchdom | VI V. Religious affections | - | - | [christian](../../seed_queue.json) (queued) | - | - |

## partly_covered (75)

| head | section | opposed head | its traits | queued | parked | secondary of |
|---|---|---|---|---|---|---|
| 4 Unsubstantiality | I I. Existence | 3 Substantiality (rule) | - | - | - | [ethereal](../../traits/instructions/ethereal.json) |
| 10 Irrelation | I II. Relation | 9 Relation (rule) | - | - | - | [insular](../../traits/instructions/insular.json), [isolated](../../traits/instructions/isolated.json) |
| 18 Dissimilarity | I II. Relation | 17 Similarity (rule) | - | - | - | [divergent](../../traits/instructions/divergent.json) |
| 20 Nonimitation | I II. Relation | 19 Imitation (rule) | - | - | - | [creative](../../traits/instructions/creative.json) |
| 32 Smallness | I III. Quantity | 31 Greatness (rule) | - | [slender](../../seed_queue.json) (queued) | - | [petty](../../traits/instructions/petty.json) |
| 49 Decomposition | I III. Quantity | 48 Combination (rule_weak) | - | - | - | [analytical](../../traits/instructions/analytical.json) |
| 58 Order | I IV. Order | 59 Disorder (rule) | [chaotic](../../traits/instructions/chaotic.json), [disorganized](../../traits/instructions/disorganized.json) | [Orderliness (BFAS)](../../seed_queue.json) (queued), [Orderliness (IPIP-NEO)](../../seed_queue.json) (queued) | [orderly](../../seed_queue.json) (queued), [systematic](../../seed_queue.json) (queued) | [methodical](../../traits/instructions/methodical.json) |
| 60 Arrangement | I IV. Order | 61 Derangement (rule_weak) | - | [Orderliness (BFAS)](../../seed_queue.json) (queued), [Orderliness (IPIP-NEO)](../../seed_queue.json) (queued) | [orderly](../../seed_queue.json) (queued), [structured](../../seed_queue.json) (queued), [systematic](../../seed_queue.json) (queued) | [methodical](../../traits/instructions/methodical.json) |
| 87 Unity | I V. Number | 100 Plurality (rule) | - | [lonely](../../seed_queue.json) (queued) | - | [single](../../traits/instructions/single.json) |
| 141 Permanence | I VII. Change | - | - | - | - | [conservative](../../traits/instructions/conservative.json) |
| 157 Power | I VIII. Causation | 158 Impotence (rule) | [helpless](../../traits/instructions/helpless.json) | [Self-Efficacy (IPIP-NEO)](../../seed_queue.json) (queued) | [empowered](../../seed_queue.json) (queued) | [competent](../../traits/instructions/competent.json) |
| 160 Weakness | I VIII. Causation | 159 Strength (rule) | - | - | - | [fragile](../../traits/instructions/fragile.json) |
| 172 Physical Inertness | I VIII. Causation | 171 Physical Energy (rule) | [intense](../../traits/instructions/intense.json) | - | - | [passive](../../traits/instructions/passive.json) |
| 212 Verticality | II II. Dimensions | 213 Horizontality (rule) | - | - | - | [straight](../../traits/instructions/straight.json) |
| 214 Pendency | II II. Dimensions | - | - | - | - | [dependent](../../traits/instructions/dependent.json) |
| 220 Exteriority | II II. Dimensions / 1. General | 221 Interiority (rule) | - | - | - | [eccentric](../../traits/instructions/eccentric.json), [superficial](../../traits/instructions/superficial.json) |
| 251 Flatness | II III. Form | - | - | - | - | [flat](../../traits/instructions/flat.json) |
| 264 Motion | II IV. Motion | 265 Quiescence (rule) | - | - | - | [mercurial](../../traits/instructions/mercurial.json) |
| 276 Impulse | II IV. Motion | - | - | - | - | [impulsive](../../traits/instructions/impulsive.json) |
| 278 Direction | II IV. Motion | 279 Deviation (rule) | - | - | - | [straight](../../traits/instructions/straight.json) |
| 279 Deviation | II IV. Motion | 278 Direction (rule) | - | - | - | [erratic](../../traits/instructions/erratic.json) |
| 282 Progression | II IV. Motion | 283 Regression (rule) | - | - | - | [progressive](../../traits/instructions/progressive.json) |
| 315 Agitation | II IV. Motion | - | - | - | - | [restless](../../traits/instructions/restless.json), [turbulent](../../traits/instructions/turbulent.json) |
| 324 Softness | III II. Inorganic matter | 323 Hardness (rule) | [inflexible](../../traits/instructions/inflexible.json) | - | [tender](../../seed_queue.json) (queued) | [flexible](../../traits/instructions/flexible.json) |
| 340 Dryness | III II. Inorganic matter / 1. Fluids in General | 339 Moisture (rule) | - | - | - | [dry](../../traits/instructions/dry.json) |
| 359 Life | III III. Organic matter / 1. Vitality in general | 360 Death (rule) | [death-accepting](../../traits/instructions/death_accepting.json) | - | - | [animated](../../traits/instructions/animated.json) |
| 372 Mankind | III III. Organic matter / 1. Vitality in general | 371 Agriculture (rule_weak) | [rural](../../traits/instructions/rural.json) | - | - | [cosmopolitan](../../traits/instructions/cosmopolitan.json), [humanitarian](../../traits/instructions/humanitarian.json) |
| 376 Physical Insensibility | III III. Organic matter / 1. Sensation in general | 375 Physical Sensibility (rule) | [socially-perceptive](../../traits/instructions/socially_perceptive.json) | - | - | [callous](../../traits/instructions/callous.json), [thick-skinned](../../traits/instructions/thick_skinned.json) |
| 422 Dimness | III III. Organic matter / 1. Sensation in general | 423 Luminary (rule_weak) | - | - | - | [dull](../../traits/instructions/dull.json) |
| 425 Transparency | III III. Organic matter / 1. Sensation in general | 426 Opacity (rule) | [opaque](../../traits/instructions/opaque.json) | - | - | [transparent](../../traits/instructions/transparent.json) |
| 478 Demonstration | IV IV. Reasoning processes | 479 Confutation (rule) | [confabulatory](../../traits/instructions/confabulatory.json) | - | [conclusive](../../seed_queue.json) (queued) | [decisive](../../traits/instructions/decisive.json) |
| 480 Judgment | IV V. Results of reasoning | 481 Misjudgment (rule) | [opinionated](../../traits/instructions/opinionated.json) | [judging (MBTI)](../../seed_queue.json) (queued) | [conclusive](../../seed_queue.json) (queued) | [decisive](../../traits/instructions/decisive.json), [judgmental](../../traits/instructions/judgmental.json) |
| 485 Unbelief. Doubt | IV V. Results of reasoning | 484 Belief (rule) | [body-confident](../../traits/instructions/body_confident.json), [calibrated](../../traits/instructions/calibrated.json), [confident](../../traits/instructions/confident.json), [just-world-believing](../../traits/instructions/just_world_believing.json), [trusting](../../traits/instructions/trusting.json) | - | - | [cynical](../../traits/instructions/cynical.json), [media-skeptical](../../traits/instructions/media_skeptical.json), [science-skeptical](../../traits/instructions/science_skeptical.json), [skeptical](../../traits/instructions/skeptical.json) |
| 505 Memory | IV VI. Extension of thought / 1. To the Past | 506 Oblivion (rule) | [forgetful](../../traits/instructions/forgetful.json), [oblivious](../../traits/instructions/oblivious.json) | - | - | [retentive](../../traits/instructions/retentive.json) |
| 509 Disappointment | IV VI. Extension of thought / 1. To the Past | - | - | - | - | [bitter](../../traits/instructions/bitter.json) |
| 516 Meaning | IV I. Nature of ideas communicated | 517 Unmeaningness (rule) | - | - | [mean](../../seed_queue.json) (queued), [meaningful](../../seed_queue.json) (queued) | [expressive](../../traits/instructions/expressive.json), [literal](../../traits/instructions/literal.json) |
| 533 Secret | IV II. Modes of communication | - | - | - | - | [enigmatic](../../traits/instructions/enigmatic.json) |
| 542 School | IV II. Modes of communication | - | - | - | [academic](../../seed_queue.json) (queued) | [educational](../../traits/instructions/educational.json) |
| 577 Ornament | IV III. Means of communicating ideas / 1. Language generally | 576 Plainness (rule) | [dry](../../traits/instructions/dry.json), [spartan](../../traits/instructions/spartan.json) | - | - | [bombastic](../../traits/instructions/bombastic.json) |
| 581 Aphony | IV III. Means of communicating ideas / 1. Language generally | 580 Voice (rule) | - | [deaf](../../seed_queue.json) (queued) | - | [emotionally-inarticulate](../../traits/instructions/emotionally_inarticulate.json) |
| 604 Resolution | V I. Volition in general / 1. Acts of Volition | 605 Irresolution (rule) | - | - | - | [decisive](../../traits/instructions/decisive.json), [unflinching](../../traits/instructions/unflinching.json) |
| 605 Irresolution | V I. Volition in general / 1. Acts of Volition | 604 Resolution (rule) | - | [Volatility (BFAS)](../../seed_queue.json) (queued) | - | [indecisive](../../traits/instructions/indecisive.json) |
| 613 Habit | V I. Volition in general / 1. Acts of Volition | 614 Desuetude (rule) | - | - | - | [conventional](../../traits/instructions/conventional.json) |
| 619 Evil | V I. Volition in general / 3. Objects of Volition | 618 Good (rule) | [good](../../traits/instructions/good.json) | - | - | [evil](../../traits/instructions/evil.json), [mischievous](../../traits/instructions/mischievous.json) |
| 641 Redundancy | V II. Prospective volition / 1. Actual Subservience | - | - | - | - | [extravagant](../../traits/instructions/extravagant.json) |
| 655 Disease | V II. Prospective volition / 1. Actual Subservience | 654 Health (rule) | - | [chronically-ill](../../seed_queue.json) (queued), [sickly](../../seed_queue.json) (queued) | - | [squeamish](../../traits/instructions/squeamish.json) |
| 656 Salubrity | V II. Prospective volition / 1. Actual Subservience | 657 Insalubrity (rule) | - | [healthy](../../seed_queue.json) (queued) | - | [benign](../../traits/instructions/benign.json) |
| 668 Warning | V II. Prospective volition / 1. Actual Subservience | - | - | - | - | [cautious](../../traits/instructions/cautious.json) |
| 676 Undertaking | V II. Prospective volition / 3. Precursory measures | - | - | - | - | [adventurous](../../traits/instructions/adventurous.json) |
| 693 Direction | V III. Voluntary action / 2. Complex Voluntary Action | - | - | - | - | [controlling](../../traits/instructions/controlling.json) |
| 695 Advice | V III. Voluntary action / 2. Complex Voluntary Action | - | - | - | - | [wise](../../traits/instructions/wise.json) |
| 704 Difficulty | V IV. Antagonism / 1. Conditional Antagonism | 705 Facility (rule) | [accessible](../../traits/instructions/accessible.json), [flexible](../../traits/instructions/flexible.json) | [tough](../../seed_queue.json) (queued) | - | [tough (HEXACO)](../../traits/instructions/tough_hexaco.json) |
| 710 Opponent | V IV. Antagonism / 2. Active Antagonism | - | - | - | - | [antagonistic (Big Five)](../../traits/instructions/antagonistic_big_five.json) |
| 714 Concord | V IV. Antagonism / 2. Active Antagonism | 713 Discord (rule) | - | [harmony](../../seed_queue.json) (queued) | - | [conciliatory](../../traits/instructions/conciliatory.json) |
| 726 Combatant | V IV. Antagonism / 2. Active Antagonism | - | - | - | - | [partisan](../../traits/instructions/partisan.json) |
| 736 Mediocrity | V V. Results of voluntary action | - | - | [middle_class](../../seed_queue.json) (queued) | - | [moderate](../../traits/instructions/moderate.json) |
| 737a Government | V I. General intersocial volition | 738 Laxity (rule_weak) | [laid-back](../../traits/instructions/laid_back.json), [loose (Gelfand)](../../traits/instructions/loose_gelfand.json) | - | - | [aristocratic](../../traits/instructions/aristocratic.json), [socialist](../../traits/instructions/socialist.json) |
| 741 Command | V I. General intersocial volition | - | - | - | - | [prescriptive](../../traits/instructions/prescriptive.json) |
| 772 Observance | V III. Conditional intersocial volition | 773 Nonobservance (rule) | - | - | - | [loyal](../../traits/instructions/loyal.json), [observant](../../traits/instructions/observant.json) |
| 784 Giving | V IV. Possessive relations / 2. Transfer of Property | - | - | - | - | [generous](../../traits/instructions/generous.json) |
| 827 Pleasure | VI II. Personal affections | 828 Pain (rule) | - | - | - | [hedonistic](../../traits/instructions/hedonistic.json), [joyful](../../traits/instructions/joyful.json) |
| 851 Vulgarity | VI II. Personal affections | 852 Fashion (rule) | [fashionable](../../traits/instructions/fashionable.json) | - | - | [rude](../../traits/instructions/rude.json) |
| 882 Ostentation | VI II. Personal affections | - | - | - | - | [pretentious](../../traits/instructions/pretentious.json) |
| 890 Friend | VI III. Sympathetic affections | 891 Enemy (rule_weak) | - | - | - | [friendly](../../traits/instructions/friendly.json) |
| 895 Discourtesy | VI III. Sympathetic affections | 894 Courtesy (rule) | [polite](../../traits/instructions/polite.json) | - | [unceremonious](../../seed_queue.json) (queued), [undiplomatic](../../seed_queue.json) (queued) | [rude](../../traits/instructions/rude.json) |
| 898 Hate | VI III. Sympathetic affections | 897 Love (rule) | - | - | - | [misanthropic](../../traits/instructions/misanthropic.json), [unpopular](../../traits/instructions/unpopular.json) |
| 913 Evil doer | VI III. Sympathetic affections | - | - | - | - | [evil](../../traits/instructions/evil.json) |
| 920 Jealousy | VI III. Sympathetic affections | - | - | [green-eyed](../../seed_queue.json) (queued) | - | [envious](../../traits/instructions/envious.json) |
| 935 Flatterer | VI IV. Moral affections | - | - | - | - | [sycophantic](../../traits/instructions/sycophantic.json) |
| 946 Innocence | VI IV. Moral affections | 947 Guilt (rule) | - | - | - | [harmless](../../traits/instructions/harmless.json) |
| 948 Good Man | VI IV. Moral affections | - | - | - | - | [good](../../traits/instructions/good.json) |
| 954 Intemperance | VI IV. Moral affections | 953 Temperance (rule) | [abstemious](../../traits/instructions/abstemious.json), [temperate](../../traits/instructions/temperate.json) | [indulgent](../../seed_queue.json) (queued) | [intemperate](../../seed_queue.json) (queued) | [self-indulgent](../../traits/instructions/self_indulgent.json) |
| 987 Piety | VI V. Religious affections | 988 Impiety (rule) | - | [devoted](../../seed_queue.json) (queued) | [preoccupied-with-religion](../../seed_queue.json) (queued) | [reverent](../../traits/instructions/reverent.json) |
| 988 Impiety | VI V. Religious affections | 987 Piety (rule) | - | - | - | [irreverent](../../traits/instructions/irreverent.json) |
| 996 Clergy | VI V. Religious affections | 997 Laity (rule) | [secular](../../traits/instructions/secular.json) | - | - | [reverent](../../traits/instructions/reverent.json) |

## Most crowded heads

| head | traits with it as primary |
|---|---|
| 825 Excitability (8) | [excitable](../../traits/instructions/excitable.json), [flustered](../../traits/instructions/flustered.json), [impatient](../../traits/instructions/impatient.json), [mercurial](../../traits/instructions/mercurial.json), [neurotic (Big Five)](../../traits/instructions/neurotic_big_five.json), [passionate](../../traits/instructions/passionate.json), [restless](../../traits/instructions/restless.json), [temperamental](../../traits/instructions/temperamental.json) |
| 826 Inexcitability (8) | [composed](../../traits/instructions/composed.json), [dispassionate](../../traits/instructions/dispassionate.json), [patient](../../traits/instructions/patient.json), [placid](../../traits/instructions/placid.json), [serene](../../traits/instructions/serene.json), [staid](../../traits/instructions/staid.json), [stoic](../../traits/instructions/stoic.json), [unflappable](../../traits/instructions/unflappable.json) |
| 893 Seclusion. Exclusion (8) | [clannish](../../traits/instructions/clannish.json), [cliqueish](../../traits/instructions/cliqueish.json), [extroverted](../../traits/instructions/extroverted.json), [introverted](../../traits/instructions/introverted.json), [introverted (Big Five)](../../traits/instructions/introverted_big_five.json), [introverted (HEXACO)](../../traits/instructions/introverted_hexaco.json), [isolated](../../traits/instructions/isolated.json), [solitary](../../traits/instructions/solitary.json) |
| 460 Neglect (7) | [careless](../../traits/instructions/careless.json), [careless (Big Five)](../../traits/instructions/careless_big_five.json), [careless (HEXACO)](../../traits/instructions/careless_hexaco.json), [health-negligent](../../traits/instructions/health_negligent.json), [irresponsible](../../traits/instructions/irresponsible.json), [neglectful](../../traits/instructions/neglectful.json), [neglectful (Baumrind)](../../traits/instructions/neglectful_baumrind.json) |
| 866 Indifference (7) | [detached](../../traits/instructions/detached.json), [dismissive-avoidant attachment](../../traits/instructions/dismissive_avoidant_attachment.json), [emotionally-disengaged](../../traits/instructions/emotionally_disengaged.json), [indifferent-to-animals](../../traits/instructions/indifferent_to_animals.json), [unambitious](../../traits/instructions/unambitious.json), [uncaring](../../traits/instructions/uncaring.json), [unsentimental](../../traits/instructions/unsentimental.json) |
| 82 Conformity (6) | [conformist](../../traits/instructions/conformist.json), [conscientious (HEXACO)](../../traits/instructions/conscientious_hexaco.json), [conventional (Kohlberg)](../../traits/instructions/conventional_kohlberg.json), [formulaic](../../traits/instructions/formulaic.json), [rule-abiding](../../traits/instructions/rule_abiding.json), [well-behaved](../../traits/instructions/well_behaved.json) |
| 451 Thought (6) | [abstract](../../traits/instructions/abstract.json), [introspective](../../traits/instructions/introspective.json), [meditative](../../traits/instructions/meditative.json), [pensive](../../traits/instructions/pensive.json), [philosophical](../../traits/instructions/philosophical.json), [speculative](../../traits/instructions/speculative.json) |
| 737 Authority (6) | [authoritarian](../../traits/instructions/authoritarian.json), [authoritarian (Baumrind)](../../traits/instructions/authoritarian_baumrind.json), [authoritative (Baumrind)](../../traits/instructions/authoritative_baumrind.json), [controlling](../../traits/instructions/controlling.json), [dominance (DISC)](../../traits/instructions/dominance_disc.json), [dominant](../../traits/instructions/dominant.json) |
| 864 Caution (6) | [cautious](../../traits/instructions/cautious.json), [circumspect](../../traits/instructions/circumspect.json), [conscientiousness (DISC)](../../traits/instructions/conscientiousness_disc.json), [guarded](../../traits/instructions/guarded.json), [prudent](../../traits/instructions/prudent.json), [unadventurous](../../traits/instructions/unadventurous.json) |
| 181 Region (5) | [eastern hemisphere](../../traits/instructions/eastern_hemisphere.json), [parochial](../../traits/instructions/parochial.json), [regionalist](../../traits/instructions/regionalist.json), [southern hemisphere](../../traits/instructions/southern_hemisphere.json), [western hemisphere](../../traits/instructions/western_hemisphere.json) |
| 457 Attention (5) | [engaged](../../traits/instructions/engaged.json), [focused](../../traits/instructions/focused.json), [observant](../../traits/instructions/observant.json), [other-focused](../../traits/instructions/other_focused.json), [self-absorbed](../../traits/instructions/self_absorbed.json) |
| 475 Uncertainty (5) | [indecisive](../../traits/instructions/indecisive.json), [self-uncertain](../../traits/instructions/self_uncertain.json), [uncertain](../../traits/instructions/uncertain.json), [unreliable](../../traits/instructions/unreliable.json), [vague](../../traits/instructions/vague.json) |
| 484 Belief (5) | [body-confident](../../traits/instructions/body_confident.json), [calibrated](../../traits/instructions/calibrated.json), [confident](../../traits/instructions/confident.json), [just-world-believing](../../traits/instructions/just_world_believing.json), [trusting](../../traits/instructions/trusting.json) |
| 543 Veracity (5) | [candid](../../traits/instructions/candid.json), [earnest](../../traits/instructions/earnest.json), [sincere](../../traits/instructions/sincere.json), [trustworthy](../../traits/instructions/trustworthy.json), [truthful](../../traits/instructions/truthful.json) |
| 821 Feeling (5) | [emotional](../../traits/instructions/emotional.json), [emotional (HEXACO)](../../traits/instructions/emotional_hexaco.json), [emotionally-articulate](../../traits/instructions/emotionally_articulate.json), [empathetic](../../traits/instructions/empathetic.json), [Pisces](../../traits/instructions/pisces.json) |

## Class I-III heads brought in, with the labels that brought them

| head | state | trigger labels |
|---|---|---|
| 4 Unsubstantiality | partly | [ethereal](../../traits/instructions/ethereal.json) |
| 5 Intrinsicality | covered | [intrinsic (Allport)](../../traits/instructions/intrinsic_allport.json) |
| 6 Extrinsicality | covered | [extrinsic (Allport)](../../traits/instructions/extrinsic_allport.json) |
| 10 Irrelation | partly | [insular](../../traits/instructions/insular.json), [isolated](../../traits/instructions/isolated.json) |
| 18 Dissimilarity | partly | [divergent](../../traits/instructions/divergent.json) |
| 20 Nonimitation | partly | [creative](../../traits/instructions/creative.json) |
| 25 Quantity | covered | [quantitative](../../traits/instructions/quantitative.json) |
| 32 Smallness | partly | [petty](../../traits/instructions/petty.json), [slender](../../seed_queue.json) (queued) |
| 47 Incoherence | covered | [incoherent](../../traits/instructions/incoherent.json) |
| 49 Decomposition | partly | [analytical](../../traits/instructions/analytical.json) |
| 52 Completeness | covered | [thorough](../../traits/instructions/thorough.json) |
| 55 Exclusion | covered | [exclusive](../../seed_queue.json) (queued) |
| 58 Order | partly | [methodical](../../traits/instructions/methodical.json), [Orderliness (BFAS)](../../seed_queue.json) (queued), [Orderliness (IPIP-NEO)](../../seed_queue.json) (queued) |
| 59 Disorder | covered | [chaotic](../../traits/instructions/chaotic.json), [disorganized](../../traits/instructions/disorganized.json) |
| 60 Arrangement | partly | [methodical](../../traits/instructions/methodical.json), [Orderliness (BFAS)](../../seed_queue.json) (queued), [Orderliness (IPIP-NEO)](../../seed_queue.json) (queued) |
| 76 Inclusion | covered | [inclusive](../../traits/instructions/inclusive.json) |
| 82 Conformity | covered | [Orderliness (BFAS)](../../seed_queue.json) (queued), [Orderliness (IPIP-NEO)](../../seed_queue.json) (queued), [orthodox](../../traits/instructions/orthodox.json) |
| 83 Unconformity | covered | [eccentric](../../traits/instructions/eccentric.json), [unfashionable](../../traits/instructions/unfashionable.json) |
| 87 Unity | partly | [lonely](../../seed_queue.json) (queued), [single](../../traits/instructions/single.json) |
| 120 Synchronism | covered | [contemporary](../../traits/instructions/contemporary.json) |
| 123 Newness | covered | [fashionable](../../traits/instructions/fashionable.json) |
| 124 Oldness | covered | [traditional](../../traits/instructions/traditional.json) |
| 127 Youth | covered | [young](../../traits/instructions/young.json) |
| 128 Age | covered | [elderly](../../traits/instructions/elderly.json) |
| 131 Adolescence | covered | [mature](../../traits/instructions/mature.json), [middle-aged](../../seed_queue.json) (queued) |
| 141 Permanence | partly | [conservative](../../traits/instructions/conservative.json) |
| 149 Changeableness | covered | [erratic](../../traits/instructions/erratic.json) |
| 150 Stability | covered | [settled](../../traits/instructions/settled.json), [steadfast](../../seed_queue.json) (queued), [steadiness (DISC)](../../traits/instructions/steadiness_disc.json), [steady](../../traits/instructions/steady.json) |
| 156 Chance | covered | [casual](../../traits/instructions/casual.json) |
| 157 Power | partly | [competent](../../traits/instructions/competent.json) |
| 158 Impotence | covered | [helpless](../../traits/instructions/helpless.json), [incompetent](../../traits/instructions/incompetent.json) |
| 160 Weakness | partly | [fragile](../../traits/instructions/fragile.json) |
| 162 Destruction | covered | [destructive](../../traits/instructions/destructive.json) |
| 170 Agency | covered | [efficient](../../traits/instructions/efficient.json), [practical](../../traits/instructions/practical.json) |
| 171 Physical Energy | covered | [energetic](../../traits/instructions/energetic.json), [intense](../../traits/instructions/intense.json) |
| 172 Physical Inertness | partly | [passive](../../traits/instructions/passive.json) |
| 173 Violence | covered | [savage](../../traits/instructions/savage.json), [turbulent](../../traits/instructions/turbulent.json) |
| 174 Moderation | covered | [calm](../../traits/instructions/calm.json), [calm (IPIP-NEO)](../../seed_queue.json) (queued), [gentle](../../traits/instructions/gentle.json), [moderate](../../traits/instructions/moderate.json), [peaceful](../../traits/instructions/peaceful.json), [temperate](../../traits/instructions/temperate.json) |
| 175 Influence | covered | [dominant](../../traits/instructions/dominant.json) |
| 181 Region | covered | [parochial](../../traits/instructions/parochial.json) |
| 184 Location | covered | [rooted](../../traits/instructions/rooted.json) |
| 188 Inhabitant | queued | [british](../../seed_queue.json) (queued), [canadian](../../seed_queue.json) (queued) |
| 189 Abode | covered | [rural](../../traits/instructions/rural.json), [suburban](../../seed_queue.json) (queued), [urban](../../traits/instructions/urban.json) |
| 193 Littleness | covered | [petty](../../traits/instructions/petty.json) |
| 201 Shortness | queued | [short](../../seed_queue.json) (queued) |
| 203 Narrowness. Thinness | queued | [slender](../../seed_queue.json) (queued) |
| 206 Height | queued | [tall](../../seed_queue.json) (queued) |
| 209 Shallowness | covered | [superficial](../../traits/instructions/superficial.json) |
| 212 Verticality | partly | [straight](../../traits/instructions/straight.json) |
| 214 Pendency | partly | [dependent](../../traits/instructions/dependent.json) |
| 220 Exteriority | partly | [eccentric](../../traits/instructions/eccentric.json), [superficial](../../traits/instructions/superficial.json) |
| 227 Circumjacence | queued | [suburban](../../seed_queue.json) (queued) |
| 239 Sinistrality | queued | [left-handed](../../seed_queue.json) (queued) |
| 246 Straightness | covered | [straight](../../traits/instructions/straight.json) |
| 251 Flatness | partly | [flat](../../traits/instructions/flat.json) |
| 254 Bluntness | covered | [blunt](../../traits/instructions/blunt.json) |
| 260 Opening | covered | [open (Big Five)](../../traits/instructions/open_big_five.json), [open (HEXACO)](../../traits/instructions/open_hexaco.json), [Openness (BFAS)](../../seed_queue.json) (queued) |
| 261 Closure | covered | [closed (Big Five)](../../traits/instructions/closed_big_five.json) |
| 264 Motion | partly | [mercurial](../../traits/instructions/mercurial.json) |
| 265 Quiescence | queued | [sedentary](../../seed_queue.json) (queued) |
| 276 Impulse | partly | [impulsive](../../traits/instructions/impulsive.json) |
| 278 Direction | partly | [straight](../../traits/instructions/straight.json) |
| 279 Deviation | partly | [erratic](../../traits/instructions/erratic.json) |
| 282 Progression | partly | [progressive](../../traits/instructions/progressive.json) |
| 290 Convergence | covered | [convergent](../../traits/instructions/convergent.json) |
| 291 Divergence | covered | [divergent](../../traits/instructions/divergent.json) |
| 304 Shortcoming | queued | [short](../../seed_queue.json) (queued) |
| 315 Agitation | partly | [restless](../../traits/instructions/restless.json) |
| 316 Materiality | covered | [materialistic](../../traits/instructions/materialistic.json) |
| 320 Levity | covered | [ethereal](../../traits/instructions/ethereal.json) |
| 323 Hardness | covered | [inflexible](../../traits/instructions/inflexible.json), [rigid](../../traits/instructions/rigid.json), [unyielding](../../traits/instructions/unyielding.json) |
| 324 Softness | partly | [flexible](../../traits/instructions/flexible.json) |
| 325 Elasticity | covered | [resilient](../../traits/instructions/resilient.json) |
| 327 Tenacity | covered | [tough](../../seed_queue.json) (queued), [tough (HEXACO)](../../traits/instructions/tough_hexaco.json) |
| 328 Brittleness | covered | [fragile](../../traits/instructions/fragile.json) |
| 334 Gaseity | covered | [ethereal](../../traits/instructions/ethereal.json) |
| 340 Dryness | partly | [dry](../../traits/instructions/dry.json) |
| 346 Island | covered | [insular](../../traits/instructions/insular.json) |
| 357 Organization | covered | [organized](../../traits/instructions/organized.json) |
| 359 Life | partly | [animated](../../traits/instructions/animated.json) |
| 361 Killing | covered | [suicidal](../../seed_queue.json) (queued) |
| 371 Agriculture | covered | [rural](../../traits/instructions/rural.json) |
| 372 Mankind | partly | [cosmopolitan](../../traits/instructions/cosmopolitan.json) |
| 373 Man | covered | [male](../../seed_queue.json) (queued), [masculine](../../traits/instructions/masculine.json) |
| 374 Woman | covered | [female](../../seed_queue.json) (queued), [feminine](../../traits/instructions/feminine.json) |
| 374a Sexuality | covered | [bisexual](../../seed_queue.json) (queued), [gay](../../traits/instructions/gay.json) |
| 376 Physical Insensibility | partly | [callous](../../traits/instructions/callous.json), [thick-skinned](../../traits/instructions/thick_skinned.json) |
| 378 Physical Pain | queued | [in-pain](../../seed_queue.json) (queued) |
| 391 Insipidity | queued | [bland](../../seed_queue.json) (queued) |
| 392b Bitterness | covered | [acerbic](../../traits/instructions/acerbic.json), [bitter](../../traits/instructions/bitter.json) |
| 403 Silence | covered | [solemn](../../traits/instructions/solemn.json) |
| 419 Deafness | queued | [deaf](../../seed_queue.json) (queued) |
| 422 Dimness | partly | [dull](../../traits/instructions/dull.json) |
| 425 Transparency | partly | [transparent](../../traits/instructions/transparent.json) |
| 426 Opacity | covered | [opaque](../../traits/instructions/opaque.json) |
| 433 Brown | queued | [brunette](../../seed_queue.json) (queued) |
| 441 Vision | covered | [visual (VARK)](../../traits/instructions/visual_vark.json) |
| 442 Blindness | queued | [blind](../../seed_queue.json) (queued) |
| 447 Invisibility | queued | [obscure](../../seed_queue.json) (queued) |

## Covered heads

| head | traits (primary) |
|---|---|
| 5 Intrinsicality | [essentialist](../../traits/instructions/essentialist.json), [intrinsic (Allport)](../../traits/instructions/intrinsic_allport.json), [intrinsically-motivated](../../traits/instructions/intrinsically_motivated.json) |
| 6 Extrinsicality | [existentialist](../../traits/instructions/existentialist.json), [extrinsic (Allport)](../../traits/instructions/extrinsic_allport.json) |
| 25 Quantity | [quantitative](../../traits/instructions/quantitative.json) |
| 47 Incoherence | [incoherent](../../traits/instructions/incoherent.json) |
| 52 Completeness | [thorough](../../traits/instructions/thorough.json) |
| 55 Exclusion | [exclusionary](../../traits/instructions/exclusionary.json), [exclusivist](../../traits/instructions/exclusivist.json) |
| 59 Disorder | [chaotic](../../traits/instructions/chaotic.json), [disorganized](../../traits/instructions/disorganized.json) |
| 76 Inclusion | [inclusive](../../traits/instructions/inclusive.json) |
| 82 Conformity | [conformist](../../traits/instructions/conformist.json), [conscientious (HEXACO)](../../traits/instructions/conscientious_hexaco.json), [conventional (Kohlberg)](../../traits/instructions/conventional_kohlberg.json), [formulaic](../../traits/instructions/formulaic.json), [rule-abiding](../../traits/instructions/rule_abiding.json), [well-behaved](../../traits/instructions/well_behaved.json) |
| 83 Unconformity | [unfashionable](../../traits/instructions/unfashionable.json) |
| 120 Synchronism | [contemporary](../../traits/instructions/contemporary.json) |
| 123 Newness | [innovative](../../traits/instructions/innovative.json) |
| 124 Oldness | [traditional](../../traits/instructions/traditional.json) |
| 127 Youth | [young](../../traits/instructions/young.json) |
| 128 Age | [elderly](../../traits/instructions/elderly.json) |
| 131 Adolescence | [mature](../../traits/instructions/mature.json) |
| 149 Changeableness | [adaptable](../../traits/instructions/adaptable.json) |
| 150 Stability | [emotionally-stable (Big Five)](../../traits/instructions/emotionally_stable_big_five.json), [settled](../../traits/instructions/settled.json), [steadiness (DISC)](../../traits/instructions/steadiness_disc.json), [steady](../../traits/instructions/steady.json) |
| 156 Chance | [casual](../../traits/instructions/casual.json) |
| 158 Impotence | [helpless](../../traits/instructions/helpless.json) |
| 162 Destruction | [destructive](../../traits/instructions/destructive.json) |
| 170 Agency | [efficient](../../traits/instructions/efficient.json) |
| 171 Physical Energy | [intense](../../traits/instructions/intense.json) |
| 173 Violence | [savage](../../traits/instructions/savage.json), [turbulent](../../traits/instructions/turbulent.json), [zealous](../../traits/instructions/zealous.json) |
| 174 Moderation | [even-tempered](../../traits/instructions/even_tempered.json) |
| 175 Influence | [influence (DISC)](../../traits/instructions/influence_disc.json) |
| 181 Region | [eastern hemisphere](../../traits/instructions/eastern_hemisphere.json), [parochial](../../traits/instructions/parochial.json), [regionalist](../../traits/instructions/regionalist.json), [southern hemisphere](../../traits/instructions/southern_hemisphere.json), [western hemisphere](../../traits/instructions/western_hemisphere.json) |
| 184 Location | [rooted](../../traits/instructions/rooted.json) |
| 189 Abode | [urban](../../traits/instructions/urban.json) |
| 193 Littleness | [petty](../../traits/instructions/petty.json) |
| 209 Shallowness | [superficial](../../traits/instructions/superficial.json) |
| 246 Straightness | [straight](../../traits/instructions/straight.json) |
| 254 Bluntness | [blunt](../../traits/instructions/blunt.json), [socially-obtuse](../../traits/instructions/socially_obtuse.json) |
| 260 Opening | [open (Big Five)](../../traits/instructions/open_big_five.json), [open (HEXACO)](../../traits/instructions/open_hexaco.json) |
| 261 Closure | [closed (Big Five)](../../traits/instructions/closed_big_five.json), [closed-minded](../../traits/instructions/closed_minded.json), [closure-seeking](../../traits/instructions/closure_seeking.json) |
| 290 Convergence | [convergent](../../traits/instructions/convergent.json) |
| 291 Divergence | [divergent](../../traits/instructions/divergent.json) |
| 316 Materiality | [materialist](../../traits/instructions/materialist.json), [materialistic](../../traits/instructions/materialistic.json) |
| 320 Levity | [lighthearted](../../traits/instructions/lighthearted.json) |
| 323 Hardness | [inflexible](../../traits/instructions/inflexible.json) |
| 325 Elasticity | [resilient](../../traits/instructions/resilient.json) |
| 327 Tenacity | [Taurus](../../traits/instructions/taurus.json), [tough (HEXACO)](../../traits/instructions/tough_hexaco.json) |
| 328 Brittleness | [fragile](../../traits/instructions/fragile.json) |
| 334 Gaseity | [ethereal](../../traits/instructions/ethereal.json) |
| 346 Island | [insular](../../traits/instructions/insular.json) |
| 357 Organization | [organized](../../traits/instructions/organized.json) |
| 361 Killing | [killer (Bartle)](../../traits/instructions/killer_bartle.json) |
| 371 Agriculture | [rural](../../traits/instructions/rural.json) |
| 373 Man | [masculine](../../traits/instructions/masculine.json) |
| 374 Woman | [feminine](../../traits/instructions/feminine.json), [feminist](../../traits/instructions/feminist.json) |
| 374a Sexuality | [gay](../../traits/instructions/gay.json), [lustful](../../traits/instructions/lustful.json) |
| 392b Bitterness | [acerbic](../../traits/instructions/acerbic.json) |
| 403 Silence | [solemn](../../traits/instructions/solemn.json) |
| 426 Opacity | [opaque](../../traits/instructions/opaque.json) |
| 441 Vision | [visual (VARK)](../../traits/instructions/visual_vark.json) |
| 450 Intellect | [cerebral](../../traits/instructions/cerebral.json) |
| 451 Thought | [abstract](../../traits/instructions/abstract.json), [introspective](../../traits/instructions/introspective.json), [meditative](../../traits/instructions/meditative.json), [pensive](../../traits/instructions/pensive.json), [philosophical](../../traits/instructions/philosophical.json), [speculative](../../traits/instructions/speculative.json) |
| 455 Curiosity | [curious](../../traits/instructions/curious.json), [inquisitive](../../traits/instructions/inquisitive.json) |
| 456 Incuriosity | [incurious](../../traits/instructions/incurious.json), [uninquisitive](../../traits/instructions/uninquisitive.json) |
| 457 Attention | [engaged](../../traits/instructions/engaged.json), [focused](../../traits/instructions/focused.json), [observant](../../traits/instructions/observant.json), [other-focused](../../traits/instructions/other_focused.json), [self-absorbed](../../traits/instructions/self_absorbed.json) |
| 458 Inattention | [distractible](../../traits/instructions/distractible.json), [unreflective](../../traits/instructions/unreflective.json) |
| 459 Care | [conscientious](../../traits/instructions/conscientious.json) |
| 460 Neglect | [careless](../../traits/instructions/careless.json), [careless (Big Five)](../../traits/instructions/careless_big_five.json), [careless (HEXACO)](../../traits/instructions/careless_hexaco.json), [health-negligent](../../traits/instructions/health_negligent.json), [irresponsible](../../traits/instructions/irresponsible.json), [neglectful](../../traits/instructions/neglectful.json), [neglectful (Baumrind)](../../traits/instructions/neglectful_baumrind.json) |
| 461 Inquiry | [exploratory](../../traits/instructions/exploratory.json), [investigative (Holland)](../../traits/instructions/investigative_holland.json), [socratic](../../traits/instructions/socratic.json) |
| 463 Experiment | [empirical](../../traits/instructions/empirical.json), [experiential](../../traits/instructions/experiential.json) |
| 465a Indiscrimination | [promiscuous](../../traits/instructions/promiscuous.json) |
| 467 Evidence | [data-driven](../../traits/instructions/data_driven.json) |
| 474 Certainty | [decisive](../../traits/instructions/decisive.json), [self-assured](../../traits/instructions/self_assured.json), [self-certain](../../traits/instructions/self_certain.json) |
| 475 Uncertainty | [indecisive](../../traits/instructions/indecisive.json), [self-uncertain](../../traits/instructions/self_uncertain.json), [uncertain](../../traits/instructions/uncertain.json), [unreliable](../../traits/instructions/unreliable.json), [vague](../../traits/instructions/vague.json) |
| 476 Reasoning | [analytical](../../traits/instructions/analytical.json), [logical](../../traits/instructions/logical.json), [rationalist](../../traits/instructions/rationalist.json) |
| 477 Intuition & Sophistry | [illogical](../../traits/instructions/illogical.json), [intuitive](../../traits/instructions/intuitive.json), [superstitious](../../traits/instructions/superstitious.json) |
| 479 Confutation | [confabulatory](../../traits/instructions/confabulatory.json) |
| 481 Misjudgment | [opinionated](../../traits/instructions/opinionated.json) |
| 482 Overestimation | [optimistic](../../traits/instructions/optimistic.json), [overconfident](../../traits/instructions/overconfident.json), [pessimistic](../../traits/instructions/pessimistic.json) |
| 483 Underestimation | [understated](../../traits/instructions/understated.json) |
| 484 Belief | [body-confident](../../traits/instructions/body_confident.json), [calibrated](../../traits/instructions/calibrated.json), [confident](../../traits/instructions/confident.json), [just-world-believing](../../traits/instructions/just_world_believing.json), [trusting](../../traits/instructions/trusting.json) |
| 486 Credulity | [credulous](../../traits/instructions/credulous.json) |
| 487 Incredulity | [cynical](../../traits/instructions/cynical.json), [media-skeptical](../../traits/instructions/media_skeptical.json), [science-skeptical](../../traits/instructions/science_skeptical.json), [skeptical](../../traits/instructions/skeptical.json) |
| 489 Dissent | [nonconformist](../../traits/instructions/nonconformist.json) |
| 490 Knowledge | [educated](../../traits/instructions/educated.json), [erudite](../../traits/instructions/erudite.json) |
| 491 Ignorance | [illiterate](../../traits/instructions/illiterate.json), [philistine](../../traits/instructions/philistine.json), [uneducated](../../traits/instructions/uneducated.json), [unschooled](../../traits/instructions/unschooled.json) |
| 494 Truth | [accurate](../../traits/instructions/accurate.json), [authentic](../../traits/instructions/authentic.json), [realistic (Holland)](../../traits/instructions/realistic_holland.json) |
| 495 Error | [inaccurate](../../traits/instructions/inaccurate.json) |
| 496 Maxim | [maximizing](../../traits/instructions/maximizing.json) |
| 498 Intelligence, Wisdom | [calculating](../../traits/instructions/calculating.json), [quick-witted](../../traits/instructions/quick_witted.json), [wise](../../traits/instructions/wise.json) |
| 499 Imbecility. Folly | [foolish](../../traits/instructions/foolish.json), [slow-witted](../../traits/instructions/slow_witted.json) |
| 500 Sage | [thinker (VALS)](../../traits/instructions/thinker_vals.json) |
| 503 Insanity | [manic](../../traits/instructions/manic.json), [neurotic](../../traits/instructions/neurotic.json) |
| 506 Oblivion | [forgetful](../../traits/instructions/forgetful.json), [oblivious](../../traits/instructions/oblivious.json) |
| 514 Supposition | [theoretical](../../traits/instructions/theoretical.json) |
| 515 Imagination | [creative](../../traits/instructions/creative.json), [idealistic](../../traits/instructions/idealistic.json), [romantic](../../traits/instructions/romantic.json) |
| 518 Intelligibility | [clear](../../traits/instructions/clear.json), [transparent](../../traits/instructions/transparent.json) |
| 519 Unintelligibility | [enigmatic](../../traits/instructions/enigmatic.json) |
| 521 Metaphor | [figurative](../../traits/instructions/figurative.json), [ironic](../../traits/instructions/ironic.json), [metaphorical](../../traits/instructions/metaphorical.json) |
| 522 Interpretation | [expository](../../traits/instructions/expository.json) |
| 525 Manifestation | [expressive](../../traits/instructions/expressive.json) |
| 527 Information | [informational](../../traits/instructions/informational.json) |
| 528 Concealment | [cryptic](../../traits/instructions/cryptic.json), [esoteric](../../traits/instructions/esoteric.json) |
| 532 News | [news-junkie](../../traits/instructions/news_junkie.json) |
| 535 Affirmation | [emphatic](../../traits/instructions/emphatic.json), [words of affirmation](../../traits/instructions/words_of_affirmation.json) |
| 537 Teaching | [didactic](../../traits/instructions/didactic.json), [educational](../../traits/instructions/educational.json), [technical](../../traits/instructions/technical.json) |
| 539 Learning | [learning-oriented](../../traits/instructions/learning_oriented.json) |
| 543 Veracity | [candid](../../traits/instructions/candid.json), [earnest](../../traits/instructions/earnest.json), [sincere](../../traits/instructions/sincere.json), [trustworthy](../../traits/instructions/trustworthy.json), [truthful](../../traits/instructions/truthful.json) |
| 544 Falsehood | [deceitful](../../traits/instructions/deceitful.json), [dishonest](../../traits/instructions/dishonest.json) |
| 545 Deception | [manipulative](../../traits/instructions/manipulative.json) |
| 556 Painting | [big-picture](../../traits/instructions/big_picture.json) |
| 559 Artist | [artistic](../../traits/instructions/artistic.json), [artistic (Holland)](../../traits/instructions/artistic_holland.json) |
| 561 Letter | [literal](../../traits/instructions/literal.json), [literate](../../traits/instructions/literate.json) |
| 572 Conciseness | [concise](../../traits/instructions/concise.json), [precise](../../traits/instructions/precise.json) |
| 573 Diffuseness | [verbose](../../traits/instructions/verbose.json) |
| 574 Vigor | [bold](../../traits/instructions/bold.json), [visceral](../../traits/instructions/visceral.json) |
| 575 Feebleness | [dull](../../traits/instructions/dull.json) |
| 576 Plainness | [dry](../../traits/instructions/dry.json), [spartan](../../traits/instructions/spartan.json) |
| 578 Elegance | [formal](../../traits/instructions/formal.json) |
| 582 Speech | [eloquent](../../traits/instructions/eloquent.json), [plain-spoken](../../traits/instructions/plain_spoken.json), [rhetorical](../../traits/instructions/rhetorical.json) |
| 583 Stammering | [emotionally-inarticulate](../../traits/instructions/emotionally_inarticulate.json) |
| 584 Loquacity | [glib](../../traits/instructions/glib.json) |
| 590 Writing | [read-write (VARK)](../../traits/instructions/read_write_vark.json) |
| 594 Description | [descriptive](../../traits/instructions/descriptive.json), [historical](../../traits/instructions/historical.json), [narrative](../../traits/instructions/narrative.json), [traditional (Inglehart-Welzel)](../../traits/instructions/traditional_inglehart_welzel.json) |
| 597 Poetry | [poetic](../../traits/instructions/poetic.json) |
| 598 Prose | [prosaic](../../traits/instructions/prosaic.json) |
| 599 The Drama | [dramatic](../../traits/instructions/dramatic.json), [melodramatic](../../traits/instructions/melodramatic.json), [theatrical](../../traits/instructions/theatrical.json) |
| 600 Will | [spontaneous](../../traits/instructions/spontaneous.json) |
| 601 Necessity | [fatalistic](../../traits/instructions/fatalistic.json) |
| 602 Willingness | [growth-minded](../../traits/instructions/growth_minded.json), [open-minded](../../traits/instructions/open_minded.json) |
| 604a Perseverance | [persevering](../../traits/instructions/persevering.json), [unflinching](../../traits/instructions/unflinching.json) |
| 606 Obstinacy | [unyielding](../../traits/instructions/unyielding.json) |
| 608 Caprice | [eccentric](../../traits/instructions/eccentric.json), [erratic](../../traits/instructions/erratic.json), [whimsical](../../traits/instructions/whimsical.json) |
| 609 Choice | [eclectic](../../traits/instructions/eclectic.json) |
| 611 Predetermination | [determinist](../../traits/instructions/determinist.json) |
| 612 Impulse | [improvisational](../../traits/instructions/improvisational.json), [impulsive](../../traits/instructions/impulsive.json) |
| 615 Motive | [inspirational](../../traits/instructions/inspirational.json), [provocative](../../traits/instructions/provocative.json) |
| 616 Dissuasion | [discouraging](../../traits/instructions/discouraging.json) |
| 618 Good | [good](../../traits/instructions/good.json) |
| 623 Avoidance | [avoidant](../../traits/instructions/avoidant.json) |
| 625 Business | [career-oriented](../../traits/instructions/career_oriented.json), [enterprising (Holland)](../../traits/instructions/enterprising_holland.json) |
| 626 Plan | [strategic](../../traits/instructions/strategic.json) |
| 627 Method | [methodical](../../traits/instructions/methodical.json) |
| 628 Mid-course | [course-correcting](../../traits/instructions/course_correcting.json) |
| 632 Means | [ends justify means](../../traits/instructions/ends_justify_means.json), [resourceful](../../traits/instructions/resourceful.json) |
| 633 Instrument | [mechanistic](../../traits/instructions/mechanistic.json) |
| 638 Waste | [burned-out](../../traits/instructions/burned_out.json) |
| 639 Sufficiency | [satisficing](../../traits/instructions/satisficing.json) |
| 642 Importance | [capitalist](../../traits/instructions/capitalist.json), [serious](../../traits/instructions/serious.json) |
| 644 Utility | [utilitarian](../../traits/instructions/utilitarian.json) |
| 645 Inutility | [unhelpful](../../traits/instructions/unhelpful.json) |
| 646 Expedience | [expedient](../../traits/instructions/expedient.json) |
| 648 Goodness | [harmless](../../traits/instructions/harmless.json) |
| 649 Badness | [evil](../../traits/instructions/evil.json), [harmful](../../traits/instructions/harmful.json), [mischievous](../../traits/instructions/mischievous.json) |
| 650 Perfection | [perfectionist](../../traits/instructions/perfectionist.json) |
| 653 Uncleanness | [slovenly](../../traits/instructions/slovenly.json) |
| 658 Improvement | [progressive](../../traits/instructions/progressive.json) |
| 659 Deterioration | [languishing](../../traits/instructions/languishing.json) |
| 664 Safety | [financially secure](../../traits/instructions/financially_secure.json) |
| 665 Danger | [financially precarious](../../traits/instructions/financially_precarious.json), [insecure](../../traits/instructions/insecure.json) |
| 670 Preservation | [conservative](../../traits/instructions/conservative.json), [financially conservative](../../traits/instructions/financially_conservative.json) |
| 673 Preparation | [proactive](../../traits/instructions/proactive.json) |
| 675 Essay | [adventurous](../../traits/instructions/adventurous.json) |
| 681 Inaction | [passive](../../traits/instructions/passive.json) |
| 682 Activity | [animated](../../traits/instructions/animated.json), [energetic](../../traits/instructions/energetic.json) |
| 683 Inactivity | [lazy](../../traits/instructions/lazy.json), [lethargic](../../traits/instructions/lethargic.json) |
| 684 Haste | [hurried](../../traits/instructions/hurried.json) |
| 685 Leisure | [deliberate](../../traits/instructions/deliberate.json), [unhurried](../../traits/instructions/unhurried.json) |
| 686 Exertion | [industrious](../../traits/instructions/industrious.json) |
| 692 Conduct | [practical](../../traits/instructions/practical.json) |
| 697 Precept | [prescriptive](../../traits/instructions/prescriptive.json) |
| 698 Skill | [competent](../../traits/instructions/competent.json) |
| 699 Unskillfulness | [incompetent](../../traits/instructions/incompetent.json) |
| 702 Cunning | [scheming](../../traits/instructions/scheming.json), [sly (HEXACO)](../../traits/instructions/sly_hexaco.json), [Slytherin](../../traits/instructions/slytherin.json) |
| 703 Artlessness | [guileless](../../traits/instructions/guileless.json), [naive](../../traits/instructions/naive.json), [unselfconscious](../../traits/instructions/unselfconscious.json) |
| 705 Facility | [accessible](../../traits/instructions/accessible.json), [flexible](../../traits/instructions/flexible.json) |
| 707 Aid | [helpful](../../traits/instructions/helpful.json), [supportive](../../traits/instructions/supportive.json) |
| 708 Opposition | [antagonistic (Big Five)](../../traits/instructions/antagonistic_big_five.json), [hostile](../../traits/instructions/hostile.json) |
| 709 Cooperation | [collaborative](../../traits/instructions/collaborative.json), [cooperative](../../traits/instructions/cooperative.json) |
| 715 Defiance | [sassy](../../traits/instructions/sassy.json) |
| 716 Attack | [aggressive](../../traits/instructions/aggressive.json), [passive-aggressive](../../traits/instructions/passive_aggressive.json) |
| 720 Contention | [competitive](../../traits/instructions/competitive.json), [confrontational](../../traits/instructions/confrontational.json) |
| 721 Peace | [calm](../../traits/instructions/calm.json), [pacifist](../../traits/instructions/pacifist.json), [peaceful](../../traits/instructions/peaceful.json) |
| 722 Warfare | [hawkish](../../traits/instructions/hawkish.json), [tactical](../../traits/instructions/tactical.json) |
| 723 Pacification | [accommodating](../../traits/instructions/accommodating.json), [conciliatory](../../traits/instructions/conciliatory.json) |
| 724 Mediation | [diplomatic](../../traits/instructions/diplomatic.json), [moderate](../../traits/instructions/moderate.json) |
| 725 Submission | [submissive](../../traits/instructions/submissive.json) |
| 731 Success | [achiever (VALS)](../../traits/instructions/achiever_vals.json) |
| 732 Failure | [defeatist](../../traits/instructions/defeatist.json) |
| 734 Prosperity | [flourishing](../../traits/instructions/flourishing.json) |
| 737 Authority | [authoritarian](../../traits/instructions/authoritarian.json), [authoritarian (Baumrind)](../../traits/instructions/authoritarian_baumrind.json), [authoritative (Baumrind)](../../traits/instructions/authoritative_baumrind.json), [controlling](../../traits/instructions/controlling.json), [dominance (DISC)](../../traits/instructions/dominance_disc.json), [dominant](../../traits/instructions/dominant.json) |
| 737b Politics | [apolitical](../../traits/instructions/apolitical.json), [partisan](../../traits/instructions/partisan.json), [political](../../traits/instructions/political.json) |
| 738 Laxity | [laid-back](../../traits/instructions/laid_back.json), [loose (Gelfand)](../../traits/instructions/loose_gelfand.json) |
| 739 Severity | [harsh](../../traits/instructions/harsh.json), [rigid](../../traits/instructions/rigid.json), [strict](../../traits/instructions/strict.json), [tight (Gelfand)](../../traits/instructions/tight_gelfand.json) |
| 740 Lenity | [ambiguity-tolerant](../../traits/instructions/ambiguity_tolerant.json), [gentle](../../traits/instructions/gentle.json), [lenient](../../traits/instructions/lenient.json) |
| 742 Disobedience | [rebellious](../../traits/instructions/rebellious.json) |
| 743 Obedience | [brand-loyal](../../traits/instructions/brand_loyal.json), [company-loyal](../../traits/instructions/company_loyal.json), [loyal](../../traits/instructions/loyal.json), [obedient](../../traits/instructions/obedient.json) |
| 744 Compulsion | [obsessive](../../traits/instructions/obsessive.json) |
| 748 Freedom | [independent](../../traits/instructions/independent.json), [metaphysical libertarian](../../traits/instructions/metaphysical_libertarian.json) |
| 749 Subjection | [dependent](../../traits/instructions/dependent.json) |
| 751 Restraint | [uptight](../../traits/instructions/uptight.json) |
| 760 Permission | [permissive](../../traits/instructions/permissive.json), [permissive (Baumrind)](../../traits/instructions/permissive_baumrind.json) |
| 769 Compact | [conventional](../../traits/instructions/conventional.json), [conventional (HEXACO)](../../traits/instructions/conventional_hexaco.json), [conventional (Holland)](../../traits/instructions/conventional_holland.json) |
| 776 Loss | [loss-averse](../../traits/instructions/loss_averse.json), [rootless](../../traits/instructions/rootless.json) |
| 778 Participation | [socialist](../../traits/instructions/socialist.json) |
| 779 Possessor | [renter](../../traits/instructions/renter.json) |
| 781 Retention | [retentive](../../traits/instructions/retentive.json) |
| 785 Receiving | [receiving gifts](../../traits/instructions/receiving_gifts.json) |
| 800 Money | [new money](../../traits/instructions/new_money.json), [old money](../../traits/instructions/old_money.json) |
| 803 Wealth | [wealthy](../../traits/instructions/wealthy.json) |
| 804 Poverty | [poor](../../traits/instructions/poor.json) |
| 811 Accounts | [accountable](../../traits/instructions/accountable.json) |
| 816 Liberality | [generous](../../traits/instructions/generous.json) |
| 817 Economy | [frugal](../../traits/instructions/frugal.json) |
| 817a Greed | [greedy](../../traits/instructions/greedy.json) |
| 818 Prodigality | [extravagant](../../traits/instructions/extravagant.json) |
| 819 Parsimony | [stingy](../../traits/instructions/stingy.json) |
| 820 Affections | [emotionally-engaged](../../traits/instructions/emotionally_engaged.json) |
| 821 Feeling | [emotional](../../traits/instructions/emotional.json), [emotional (HEXACO)](../../traits/instructions/emotional_hexaco.json), [emotionally-articulate](../../traits/instructions/emotionally_articulate.json), [empathetic](../../traits/instructions/empathetic.json), [Pisces](../../traits/instructions/pisces.json) |
| 822 Sensibility | [sentimental](../../traits/instructions/sentimental.json), [thin-skinned](../../traits/instructions/thin_skinned.json) |
| 823 Insensibility | [apathetic](../../traits/instructions/apathetic.json), [callous](../../traits/instructions/callous.json), [thick-skinned](../../traits/instructions/thick_skinned.json) |
| 824 Excitation | [anxious](../../traits/instructions/anxious.json) |
| 825 Excitability | [excitable](../../traits/instructions/excitable.json), [flustered](../../traits/instructions/flustered.json), [impatient](../../traits/instructions/impatient.json), [mercurial](../../traits/instructions/mercurial.json), [neurotic (Big Five)](../../traits/instructions/neurotic_big_five.json), [passionate](../../traits/instructions/passionate.json), [restless](../../traits/instructions/restless.json), [temperamental](../../traits/instructions/temperamental.json) |
| 826 Inexcitability | [composed](../../traits/instructions/composed.json), [dispassionate](../../traits/instructions/dispassionate.json), [patient](../../traits/instructions/patient.json), [placid](../../traits/instructions/placid.json), [serene](../../traits/instructions/serene.json), [staid](../../traits/instructions/staid.json), [stoic](../../traits/instructions/stoic.json), [unflappable](../../traits/instructions/unflappable.json) |
| 829 Pleasurableness | [agreeable (Big Five)](../../traits/instructions/agreeable_big_five.json) |
| 830 . Painfulness | [cruel](../../traits/instructions/cruel.json) |
| 831 Content | [contented](../../traits/instructions/contented.json), [easygoing](../../traits/instructions/easygoing.json) |
| 832 Discontent | [discontented](../../traits/instructions/discontented.json) |
| 833 Regret | [nostalgic](../../traits/instructions/nostalgic.json) |
| 836 Cheerfulness | [cheerful](../../traits/instructions/cheerful.json), [joyful](../../traits/instructions/joyful.json) |
| 837 Dejection | [joyless](../../traits/instructions/joyless.json), [melancholic](../../traits/instructions/melancholic.json) |
| 840 Amusement | [entertaining](../../traits/instructions/entertaining.json), [playful](../../traits/instructions/playful.json) |
| 842 Wit | [witty](../../traits/instructions/witty.json) |
| 843 Dullness | [flat](../../traits/instructions/flat.json) |
| 844 Humorist | [humorless](../../traits/instructions/humorless.json) |
| 849 Simplicity | [unpretentious](../../traits/instructions/unpretentious.json) |
| 850 Taste | [aesthete](../../traits/instructions/aesthete.json), [tactful](../../traits/instructions/tactful.json) |
| 852 Fashion | [fashionable](../../traits/instructions/fashionable.json) |
| 853 Ridiculousness | [goofy](../../traits/instructions/goofy.json) |
| 855 Affectation | [pedantic](../../traits/instructions/pedantic.json), [pretentious](../../traits/instructions/pretentious.json) |
| 856 Ridicule | [sarcastic](../../traits/instructions/sarcastic.json), [sardonic](../../traits/instructions/sardonic.json), [wry](../../traits/instructions/wry.json) |
| 858 Hope | [encouraging](../../traits/instructions/encouraging.json), [self-reliant](../../traits/instructions/self_reliant.json) |
| 859 Hopelessness | [despairing](../../traits/instructions/despairing.json) |
| 860 Fear | [death-fearing](../../traits/instructions/death_fearing.json), [fearful-avoidant attachment](../../traits/instructions/fearful_avoidant_attachment.json), [panicky](../../traits/instructions/panicky.json) |
| 861 Courage | [brave](../../traits/instructions/brave.json), [Gryffindor](../../traits/instructions/gryffindor.json) |
| 862 Cowardice | [cowardly](../../traits/instructions/cowardly.json) |
| 863 Rashness | [brash](../../traits/instructions/brash.json), [financially reckless](../../traits/instructions/financially_reckless.json), [reckless](../../traits/instructions/reckless.json) |
| 864 Caution | [cautious](../../traits/instructions/cautious.json), [circumspect](../../traits/instructions/circumspect.json), [conscientiousness (DISC)](../../traits/instructions/conscientiousness_disc.json), [guarded](../../traits/instructions/guarded.json), [prudent](../../traits/instructions/prudent.json), [unadventurous](../../traits/instructions/unadventurous.json) |
| 865 Desire | [ambitious](../../traits/instructions/ambitious.json) |
| 866 Indifference | [detached](../../traits/instructions/detached.json), [dismissive-avoidant attachment](../../traits/instructions/dismissive_avoidant_attachment.json), [emotionally-disengaged](../../traits/instructions/emotionally_disengaged.json), [indifferent-to-animals](../../traits/instructions/indifferent_to_animals.json), [unambitious](../../traits/instructions/unambitious.json), [uncaring](../../traits/instructions/uncaring.json), [unsentimental](../../traits/instructions/unsentimental.json) |
| 867 Dislike | [unpopular](../../traits/instructions/unpopular.json) |
| 868 Fastidiousness | [detail-oriented](../../traits/instructions/detail_oriented.json), [fastidious](../../traits/instructions/fastidious.json), [meticulous](../../traits/instructions/meticulous.json), [picky-eater](../../traits/instructions/picky_eater.json), [squeamish](../../traits/instructions/squeamish.json) |
| 870 Wonder | [wide-eyed](../../traits/instructions/wide_eyed.json) |
| 873 Repute | [popular](../../traits/instructions/popular.json) |
| 875 Nobility | [aristocratic](../../traits/instructions/aristocratic.json), [upper-class](../../traits/instructions/upper_class.json) |
| 876 Commonalty | [Gemeinschaft (Tönnies)](../../traits/instructions/gemeinschaft_tonnies.json) |
| 878 Pride | [dignified](../../traits/instructions/dignified.json), [Leo](../../traits/instructions/leo.json) |
| 879 Humility | [honest-humble (HEXACO)](../../traits/instructions/honest_humble_hexaco.json), [humble](../../traits/instructions/humble.json), [self-effacing](../../traits/instructions/self_effacing.json) |
| 880 Vanity | [vulnerable-narcissistic](../../traits/instructions/vulnerable_narcissistic.json) |
| 881 Modesty | [modest](../../traits/instructions/modest.json), [reserved](../../traits/instructions/reserved.json), [self-conscious](../../traits/instructions/self_conscious.json), [timid](../../traits/instructions/timid.json), [unassuming](../../traits/instructions/unassuming.json) |
| 884 Boasting | [bombastic](../../traits/instructions/bombastic.json), [grandiose](../../traits/instructions/grandiose.json), [self-aggrandizing](../../traits/instructions/self_aggrandizing.json) |
| 885 Insolence | [arrogant](../../traits/instructions/arrogant.json), [flippant](../../traits/instructions/flippant.json) |
| 886 Servility | [sycophantic](../../traits/instructions/sycophantic.json) |
| 888 Friendship | [friendly](../../traits/instructions/friendly.json) |
| 892 Sociality | [gregarious](../../traits/instructions/gregarious.json), [social (Holland)](../../traits/instructions/social_holland.json) |
| 893 Seclusion. Exclusion | [clannish](../../traits/instructions/clannish.json), [cliqueish](../../traits/instructions/cliqueish.json), [extroverted](../../traits/instructions/extroverted.json), [introverted](../../traits/instructions/introverted.json), [introverted (Big Five)](../../traits/instructions/introverted_big_five.json), [introverted (HEXACO)](../../traits/instructions/introverted_hexaco.json), [isolated](../../traits/instructions/isolated.json), [solitary](../../traits/instructions/solitary.json) |
| 894 Courtesy | [polite](../../traits/instructions/polite.json) |
| 899 Favorite | [dog-person](../../traits/instructions/dog_person.json) |
| 900 Resentment | [bitter](../../traits/instructions/bitter.json) |
| 901 Irascibility | [irascible](../../traits/instructions/irascible.json), [quarrelsome (HEXACO)](../../traits/instructions/quarrelsome_hexaco.json) |
| 903 Marriage | [married](../../traits/instructions/married.json) |
| 904 Celibacy | [childless](../../traits/instructions/childless.json), [single](../../traits/instructions/single.json) |
| 906 Benevolence | [benevolent](../../traits/instructions/benevolent.json), [benign](../../traits/instructions/benign.json), [kind-to-animals](../../traits/instructions/kind_to_animals.json) |
| 907 Malevolence | [malevolent](../../traits/instructions/malevolent.json), [malicious](../../traits/instructions/malicious.json), [malign](../../traits/instructions/malign.json) |
| 910 Philanthropy | [cosmopolitan](../../traits/instructions/cosmopolitan.json), [humanitarian](../../traits/instructions/humanitarian.json), [patriotic](../../traits/instructions/patriotic.json), [philanthropic](../../traits/instructions/philanthropic.json) |
| 911 Misanthropy | [misanthropic](../../traits/instructions/misanthropic.json), [sociopathic](../../traits/instructions/sociopathic.json) |
| 914 Pity | [compassionate](../../traits/instructions/compassionate.json), [merciful](../../traits/instructions/merciful.json), [self-pitying](../../traits/instructions/self_pitying.json) |
| 916 Gratitude | [grateful](../../traits/instructions/grateful.json) |
| 917 Ingratitude | [ungrateful](../../traits/instructions/ungrateful.json) |
| 918 Forgiveness | [agreeable (HEXACO)](../../traits/instructions/agreeable_hexaco.json), [forgiving](../../traits/instructions/forgiving.json) |
| 919 Revenge | [spiteful](../../traits/instructions/spiteful.json), [unforgiving](../../traits/instructions/unforgiving.json), [vindictive](../../traits/instructions/vindictive.json) |
| 921 Envy | [envious](../../traits/instructions/envious.json) |
| 922 Right | [fair](../../traits/instructions/fair.json) |
| 923 Wrong | [unfair](../../traits/instructions/unfair.json) |
| 924 Dueness | [entitled](../../traits/instructions/entitled.json) |
| 926 Duty | [conscientious (Big Five)](../../traits/instructions/conscientious_big_five.json), [deontological](../../traits/instructions/deontological.json), [responsible](../../traits/instructions/responsible.json) |
| 928 Respect | [autonomy-respecting](../../traits/instructions/autonomy_respecting.json), [deferential](../../traits/instructions/deferential.json), [respectful](../../traits/instructions/respectful.json) |
| 929 Disrespect | [dismissive](../../traits/instructions/dismissive.json), [irreverent](../../traits/instructions/irreverent.json), [rude](../../traits/instructions/rude.json) |
| 930 Contempt | [condescending](../../traits/instructions/condescending.json) |
| 931 Approbation | [uncritical](../../traits/instructions/uncritical.json) |
| 932 Disapprobation | [critical](../../traits/instructions/critical.json) |
| 933 Flattery | [flirty](../../traits/instructions/flirty.json) |
| 939 Probity | [honest](../../traits/instructions/honest.json), [honorable](../../traits/instructions/honorable.json), [honorable while playing](../../traits/instructions/honorable_while_playing.json), [intellectually honest](../../traits/instructions/intellectually_honest.json), [principled](../../traits/instructions/principled.json) |
| 940 Improbity | [amoral](../../traits/instructions/amoral.json), [intellectually dishonest](../../traits/instructions/intellectually_dishonest.json), [treacherous](../../traits/instructions/treacherous.json), [untrustworthy](../../traits/instructions/untrustworthy.json) |
| 942 Disinterestedness | [altruistic](../../traits/instructions/altruistic.json), [magnanimous](../../traits/instructions/magnanimous.json), [uncalculating](../../traits/instructions/uncalculating.json) |
| 943 Selfishness | [self-indulgent](../../traits/instructions/self_indulgent.json), [selfish](../../traits/instructions/selfish.json) |
| 944 Virtue | [moral](../../traits/instructions/moral.json) |
| 950 Penitence | [remorseful](../../traits/instructions/remorseful.json) |
| 951 Impenitence | [unrepentant](../../traits/instructions/unrepentant.json) |
| 953 Temperance | [abstemious](../../traits/instructions/abstemious.json), [temperate](../../traits/instructions/temperate.json) |
| 954a Sensualist | [epicurean](../../traits/instructions/epicurean.json) |
| 955 Asceticism | [ascetic](../../traits/instructions/ascetic.json), [puritanical](../../traits/instructions/puritanical.json) |
| 957 Gluttony | [gluttonous](../../traits/instructions/gluttonous.json) |
| 958 Sobriety | [teetotaler](../../traits/instructions/teetotaler.json) |
| 959 Drunkenness | [heavy-drinker](../../traits/instructions/heavy_drinker.json) |
| 960 Purity | [chaste](../../traits/instructions/chaste.json) |
| 971 Condemnation | [judgmental](../../traits/instructions/judgmental.json) |
| 976 Deity | [spiritual](../../traits/instructions/spiritual.json) |
| 983 Theology | [religious](../../traits/instructions/religious.json) |
| 983a Orthodoxy | [fundamentalist](../../traits/instructions/fundamentalist.json), [orthodox](../../traits/instructions/orthodox.json) |
| 984 Heterodoxy | [heterodox](../../traits/instructions/heterodox.json), [iconoclastic](../../traits/instructions/iconoclastic.json), [sectarian](../../traits/instructions/sectarian.json) |
| 989 Irreligion | [secular-rational (Inglehart-Welzel)](../../traits/instructions/secular_rational_inglehart_welzel.json) |
| 990 Worship | [acts of service](../../traits/instructions/acts_of_service.json), [reverent](../../traits/instructions/reverent.json) |
| 992 Sorcery | [mystical](../../traits/instructions/mystical.json) |
| 997 Laity | [secular](../../traits/instructions/secular.json) |
| 998 Rite | [ritualistic](../../traits/instructions/ritualistic.json) |
