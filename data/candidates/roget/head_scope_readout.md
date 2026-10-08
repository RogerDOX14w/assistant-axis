# Roget head-scope check: readout (2026-10-08)

Workstream 2 of trait-gap generation, the Roget generator
([coding_plan_02_roget_wordnet.md](../../../reports/trait_gap_generation/coding_plan_02_roget_wordnet.md)).
Roger approved the check on 2026-10-08 ("The Haiku test SG";
[QUESTIONS.md](../../../reports/trait_gap_generation/QUESTIONS.md) entry 44).

Terms.  A **head** is one numbered entry of Roget's Thesaurus (1911), such as 604 Resolution.  The
**dispositional** heads are Classes IV-VI (intellect, volition, the affections), numbered 450 and up; the
coverage map's **scope** is those 576 heads plus 99 Class I-III heads that hold one of our labels.  **M1**
is the platform's trait-hood filter: it sends each word on as a trait, or to the states queue, the physical
list or the roles list, or turns it away.  **M3** is the novelty check, which calls a trait word `new` or
`covered` by an existing trait.  The **pilot** is run `2026-10-08-pilot`
([readout](../runs/roget/2026-10-08-pilot/readout.md)): every fifth gap head, 185 words, which M1 and M3
have already judged.  A **gap head** is a head in scope that no existing trait has as its primary head.

## What the check does

One call of Haiku 5.5 (`claude-haiku-5-5`) per 19 or 20 heads, in text order.  Each head is sent with its
number, title, class and section titles, and its first 20 distinct adjectives.  For each head the model
gives a one-sentence reason, then `character`: **2**, most of the adjectives can describe what a person
is like; **1**, some can (a mixed head); **0**, few or none can.  The rubric is
[roget_head_scope.md](../../../reports/trait_gap_generation/rubrics/roget_head_scope.md) (draft 2, pinned as
version 2 in [versions.json](../../../reports/trait_gap_generation/rubrics/versions.json); rendered calls in
the file).  The harvest skips heads rated 0, counting their words under the drop reason `not_character`;
the coverage map lists them apart as "not character" and leaves them out of its counts.  Code:
[head_scope.py](../../../assistant_axis/gapgen/generators/roget/head_scope.py), command
`roget_generate.py head-scope` ([roget_generate.py](../../../data_analysis/gap_generation/roget_generate.py)).

Files: the ratings [head_scope.json](./head_scope.json) (one row per head in scope, with the reason);
draft 1's ratings [head_scope_v1.json](./head_scope_v1.json); a repeat run of draft 2,
[head_scope_v2_retest.json](./head_scope_v2_retest.json); every request and response,
[head_scope_responses.jsonl](./head_scope_responses.jsonl); the spend,
[head_scope_usage.json](./head_scope_usage.json).

## The runs

| | draft 1 | draft 2 (the file in use) | draft 2, repeat |
|---|---|---|---|
| heads rated (of 675 in scope; 89 have no adjectives and are not sent) | 586 | 586 | 586 |
| calls / retries / unparsed heads | 30 / 0 / 0 | 30 / 0 / 0 | 30 / 0 / 0 |
| rated 0 / 1 / 2 | 289 / 170 / 127 | 188 / 234 / 164 | 191 / 223 / 172 |
| cost | $0.055 | $0.055 | $0.055 |

Spend for all three runs: **$0.166** (90 calls, 270,786 input and 277,469 output tokens; output includes
Haiku 5.5's adaptive thinking, about 3,080 tokens a call).  The first estimate ($0.034 a run) was 40% low;
the estimate now uses the measured figures.  The system prompt (about 480 tokens) is under Haiku 5.5's
512-token caching minimum, so it was sent uncached.

**Why draft 2.**  Draft 1 asked whether the adjectives describe "a person's character, temperament or
habitual way of acting", and rated 0 any head about "a person's situation".  It rated 289 of the 586 heads
0, and 123 of those are heads the corpus already covers or partly covers.  Some are character heads by
any reading: Skill ([competent](../../traits/instructions/competent.json)), Cooperation
([cooperative](../../traits/instructions/cooperative.json)), Perfection
([perfectionist](../../traits/instructions/perfectionist.json)), Duty
([responsible](../../traits/instructions/responsible.json)), Knowledge
([erudite](../../traits/instructions/erudite.json)) and Rejoicing.  Others are memberships, which the
corpus counts as traits ([decisions_m1.md](../../../reports/trait_gap_generation/decisions_m1.md) decision
3): Wealth ([wealthy](../../traits/instructions/wealthy.json)), Poverty
([poor](../../traits/instructions/poor.json)), Marriage ([married](../../traits/instructions/married.json)),
Laity ([secular](../../traits/instructions/secular.json)).  Haiku read "character" as excluding abilities,
manners, feelings and memberships.  Draft 2 spells out "what a person is like": character and
temperament, habits of thought, speech and conduct, attitudes and values, skills and failings shown in
action, moods a person can be prone to, and the groups a person belongs to.  It keeps 0 for things,
prices, documents, places, events, looks and passing circumstances, and says "when you are unsure between
0 and 1, answer 1".  A wrongly dropped head loses its trait words for good, while a junk word let through
costs about $0.004 at M1, so the rubric errs toward keeping.

Ratings by class (draft 2; draft 1 in brackets):

| class | 0 | 1 | 2 |
|---|---|---|---|
| I abstract relations (Class I-III heads are only those holding a label) | 6 (18) | 25 (16) | 8 (5) |
| II space | 10 (9) | 17 (20) | 2 (0) |
| III matter | 10 (15) | 18 (15) | 3 (1) |
| IV intellect | 58 (82) | 50 (37) | 29 (18) |
| V volition | 72 (112) | 81 (45) | 38 (34) |
| VI affections | 32 (53) | 43 (37) | 84 (69) |

**Repeat run.**  Haiku 5.5 takes no temperature, so the same draft can answer differently.  Two runs of
draft 2 agree on 523 of 586 heads (89%).  33 heads (5.6%) are 0 in one run and 1 in the other.  All are
borderline by eye, among them Habit, Success, Failure, Marriage, Celibacy, Dearness, Heaven and Lawyer.
Of draft 1's 289 zeros, draft 2 kept 183 at 0 and moved 98 to 1 and 8 to 2; that shift is far larger
than the run-to-run noise.

## Against the pilot

Each pilot word joined with its head's rating and its M1 outcome in this worktree's registry copy
(`data/candidates/registry.jsonl`, the same rows the pilot readout used).  Words, not distinct words: four
words came from two heads.

| rating | heads | words | trait | states | physical | roles | turned away | M3 new / covered (of the trait words) |
|---|---|---|---|---|---|---|---|---|
| draft 2: 0 | 31 | 93 | 34 | 29 | 3 | 4 | 23 | 28 / 6 |
| draft 2: 1 | 12 | 61 | 37 | 13 | 1 | 1 | 9 | 31 / 6 |
| draft 2: 2 | 7 | 31 | 26 | 4 | 0 | 0 | 1 | 15 / 8 |
| draft 1: 0 | 38 | 129 | 59 | 35 | 3 | 5 | 27 | 43 / 13 |
| draft 1: 1 | 8 | 40 | 25 | 8 | 1 | 0 | 6 | 21 / 4 |
| draft 1: 2 | 4 | 16 | 13 | 3 | 0 | 0 | 0 | 10 / 3 |

With draft 2, the heads rated 0 hold **23 of the 33 words M1 turned away** (70%), 29 of the 46 sent to
the states queue, 4 of the 5 roles and 3 of the 4 physical words.  They also hold **34 of the 97 words
M1 passed as traits** (35%; M3 called 28 of those new).  Draft 1 caught 27 of the 33 turned-away words
but dropped 59 trait words.  The character heads of Possessive relations, Liberality, Economy,
Prodigality and Parsimony, are rated 2 in all three runs.  Ten turned-away words stay in with draft 2: five from Dearness and Price,
rated 1 for *extravagant*, *exorbitant*, *mercenary* and *venal*; Misnomer's *so-called* and *unnamed*,
and Cheapness's *half-price* (now 1); *ajar* (Discord, 1); *domiciliary* (Inhabitant, now 2 for its
nationalities).

### The 33 words M1 turned away

M1's cause: `no_reading`, no reading of the word as a persona; `stretched`, only a reading people would have to work out; `evaluative`, praise or blame only; `not_a_persona`, said of what others do to the person; `action`, a single act; `probe`, failed the definition probe for rare words.

| word | head | M1 cause | draft 2 | draft 1 |
|---|---|---|---|---|
| so-called | 565 Misnomer | no_reading | 1 | 0 |
| named | 564 Nomenclature | stretched | 0 | 0 |
| paying | 775 Acquisition | action | 0 | 0 |
| acquired | 775 Acquisition | no_reading | 0 | 0 |
| purchased | 795 Purchase | stretched | 0 | 0 |
| call properly | 564 Nomenclature | no_reading | 0 | 0 |
| dear bought | 814 Dearness | no_reading | 1 | 1 |
| above price | 814 Dearness | no_reading | 1 | 1 |
| diamond | 847a Jewelry | evaluative | 0 | 0 |
| stored | 636 Store | no_reading | 0 | 0 |
| comparable | 464 Comparison | no_reading | 0 | 0 |
| comparative | 464 Comparison | stretched | 0 | 0 |
| priced | 812 Price | stretched | 1 | 1 |
| half-price | 815 Cheapness | stretched | 1 | 0 |
| meaningless | 517 Unmeaningness | evaluative | 0 | 0 |
| past due | 806 Debt | stretched | 0 | 0 |
| corrective | 527a Correction | stretched | 0 | 0 |
| minus | 806 Debt | no_reading | 0 | 0 |
| unnamed | 565 Misnomer | not_a_persona | 1 | 0 |
| unwritten | 552 Obliteration | stretched | 0 | 0 |
| disused | 678 Disuse | no_reading | 0 | 0 |
| epistolary | 592 Correspondence | stretched | 0 | 0 |
| ajar | 713 Discord | stretched | 1 | 1 |
| foreseen | 871 Expectance | no_reading | 0 | 0 |
| juridical | 965 Jurisdiction | stretched | 0 | 0 |
| overpriced | 814 Dearness | not_a_persona | 1 | 1 |
| engraved lapidary | 558 Engraving | probe | 0 | 0 |
| incommensurable | 464a Incomparability | no_reading | 0 | 0 |
| ad valorem | 812 Price | no_reading | 1 | 1 |
| unrequited | 806 Debt | stretched | 0 | 0 |
| gemological | 847a Jewelry | no_reading | 0 | 0 |
| inexpressible | 517 Unmeaningness | stretched | 0 | 0 |
| domiciliary | 188 Inhabitant | stretched | 2 | 0 |

### Possible false drops: heads rated 0 whose pilot words M1 passed as traits (draft 2)

| head | draft 2 reason | words M1 passed as traits (M3 decision) |
|---|---|---|
| 651 Imperfection | Mostly describes things and their defects; "indifferent" and "lame" only loosely fit a person. | so-so (new), imperfect (new), defective (new), cracked (new), faulty (covered), found wanting (new), lame (covered), good enough (covered) |
| 806 Debt | Indebted, liable and in debt describe a financial state or obligation, not what a person is like. | involved (new), deeply involved (covered), indebted (new), unpaid (new) |
| 768a Release from engagement | Its single adjective, absolute, describes a release or a ruler, not a person's character. | absolute (new) |
| 871 Expectance | Describes expectation and ordinariness, which are circumstances or qualities of events rather than of a person. | common (new), unsurprising (covered) |
| 469 Qualification | Its adjectives (qualifying, conditional, hedged, restricted) describe statements, terms and conditions, not a person. | qualified (new), conditional (new) |
| 629 Circuit | Circuitous, roundabout and indirect describe routes and methods rather than what a person is like. | indirect (new), backhanded (new) |
| 805 Credit | Credited and accredited describe the attribution or authorisation of something, not a person's nature. | credited (new) |
| 965 Jurisdiction | Executive, administrative, municipal and judicial describe powers and bodies, not a person's nature. | judicial (new), inquisitorial (covered) |
| 689 Refreshment | Refreshment adjectives describe a restored state or a refreshing thing, not a person's character. | refreshing (new) |
| 669 Alarm | Single adjective describing something that causes alarm, not a person. | alarming (new) |
| 783 Transfer | Alienable and negotiable describe property or instruments that can be transferred. | negotiable (new) |
| 982 Hell | The adjectives describe hell, its torments and things hellish, with no ordinary use for a person's character. | infernal (new) |
| 464a Incomparability | The adjectives describe things that cannot be compared, and 'incomparable' is only a stretch when applied to a person. | incomparable (new) |
| 517 Unmeaningness | Its adjectives (meaningless, nonsensical, trashy, trivial, quibbling) mainly describe ideas, talk and things, with only a marginal fit for a person. | insignificant (new), trivial (new), nonsensical (new), inexpressive (new) |
| 956 Fasting | Its adjectives (lenten, starved, fasting) describe a passing state of abstaining from or lacking food, not what a person is like. | lenten (new) |
| 419 Deafness | Deaf and hard of hearing describe a physical condition, not a person's character. | inaudible (new) |
| 552 Obliteration | Out of print, unrecorded and unwritten describe records and documents, not people. | intestate (new) |

By eye, most of these are readings M1 made up for words whose Roget sense is not about people (*cracked*
from Imperfection read as "mentally unhinged"; *intestate*, *lenten*, *credited*, *infernal*,
*inaudible*).  The rubric asks for each adjective in its head's sense, and the gloss hint the harvest
writes follows the head's sense ("a disposition toward circuit"), so these words came to M1 without a
usable hint.  The losses that look real are *indirect* and *backhanded* (Circuit), *conditional* and
*negotiable* (manners of bargaining), *judicial* (judicious), *trivial*, and *absolute* ("holding
commitments without exception").  Another generator (the WordNet stream or the word-list censuses) can
still find words like these in their person sense.

## Covered heads still rated 0 (draft 2)

47 heads that the corpus covers are rated 0, against 96 under draft 1.  Most are heads where a trait was
placed because its word appears there in another sense: *literal* on Letter, *open* on Opening,
*contemporary* on Synchronism, *casual* on Chance.  That is a placement question, taken up by the label
placement check.  Others are memberships or states the rubric still reads as circumstances (Marriage
and Celibacy flip between runs; Safety for
[financially_secure](../../traits/instructions/financially_secure.json)).  The route is how
[label_heads.json](./label_heads.json) placed the trait: `agree` (lexical and semantic routes agree),
`semantic` (embedding only), `rule`.

| head | traits with it as their primary head (route) |
|---|---|
| 25 Quantity | [quantitative](../../traits/instructions/quantitative.json) (agree) |
| 55 Exclusion | [exclusionary](../../traits/instructions/exclusionary.json) (semantic), [exclusivist](../../traits/instructions/exclusivist.json) (semantic) |
| 76 Inclusion | [inclusive](../../traits/instructions/inclusive.json) (agree) |
| 120 Synchronism | [contemporary](../../traits/instructions/contemporary.json) (agree) |
| 156 Chance | [casual](../../traits/instructions/casual.json) (agree) |
| 184 Location | [rooted](../../traits/instructions/rooted.json) (rule) |
| 260 Opening | [open_big_five](../../traits/instructions/open_big_five.json) (agree), [open_hexaco](../../traits/instructions/open_hexaco.json) (agree) |
| 261 Closure | [closed_big_five](../../traits/instructions/closed_big_five.json) (agree), [closed_minded](../../traits/instructions/closed_minded.json) (semantic), [closure_seeking](../../traits/instructions/closure_seeking.json) (semantic) |
| 290 Convergence | [convergent](../../traits/instructions/convergent.json) (agree) |
| 291 Divergence | [divergent](../../traits/instructions/divergent.json) (agree) |
| 334 Gaseity | [ethereal](../../traits/instructions/ethereal.json) (agree) |
| 426 Opacity | [opaque](../../traits/instructions/opaque.json) (agree) |
| 441 Vision | [visual_vark](../../traits/instructions/visual_vark.json) (agree) |
| 461 Inquiry | [exploratory](../../traits/instructions/exploratory.json) (semantic), [investigative_holland](../../traits/instructions/investigative_holland.json) (agree), [socratic](../../traits/instructions/socratic.json) (agree) |
| 463 Experiment | [empirical](../../traits/instructions/empirical.json) (agree), [experiential](../../traits/instructions/experiential.json) (semantic) |
| 467 Evidence | [data_driven](../../traits/instructions/data_driven.json) (semantic) |
| 479 Confutation | [confabulatory](../../traits/instructions/confabulatory.json) (semantic) |
| 482 Overestimation | [optimistic](../../traits/instructions/optimistic.json) (agree), [overconfident](../../traits/instructions/overconfident.json) (semantic), [pessimistic](../../traits/instructions/pessimistic.json) (agree) |
| 496 Maxim | [maximizing](../../traits/instructions/maximizing.json) (semantic) |
| 514 Supposition | [theoretical](../../traits/instructions/theoretical.json) (agree) |
| 521 Metaphor | [figurative](../../traits/instructions/figurative.json) (agree), [ironic](../../traits/instructions/ironic.json) (agree), [metaphorical](../../traits/instructions/metaphorical.json) (agree) |
| 532 News | [news_junkie](../../traits/instructions/news_junkie.json) (semantic) |
| 556 Painting | [big_picture](../../traits/instructions/big_picture.json) (rule) |
| 561 Letter | [literal](../../traits/instructions/literal.json) (agree), [literate](../../traits/instructions/literate.json) (semantic) |
| 590 Writing | [read_write_vark](../../traits/instructions/read_write_vark.json) (semantic) |
| 594 Description | [descriptive](../../traits/instructions/descriptive.json) (agree), [historical](../../traits/instructions/historical.json) (rule), [narrative](../../traits/instructions/narrative.json) (agree), [traditional_inglehart_welzel](../../traits/instructions/traditional_inglehart_welzel.json) (lexical) |
| 597 Poetry | [poetic](../../traits/instructions/poetic.json) (agree) |
| 626 Plan | [strategic](../../traits/instructions/strategic.json) (agree) |
| 633 Instrument | [mechanistic](../../traits/instructions/mechanistic.json) (agree) |
| 638 Waste | [burned_out](../../traits/instructions/burned_out.json) (semantic) |
| 659 Deterioration | [languishing](../../traits/instructions/languishing.json) (semantic) |
| 664 Safety | [financially_secure](../../traits/instructions/financially_secure.json) (agree) |
| 724 Mediation | [diplomatic](../../traits/instructions/diplomatic.json) (agree), [moderate](../../traits/instructions/moderate.json) (agree) |
| 731 Success | [achiever_vals](../../traits/instructions/achiever_vals.json) (agree) |
| 732 Failure | [defeatist](../../traits/instructions/defeatist.json) (agree) |
| 734 Prosperity | [flourishing](../../traits/instructions/flourishing.json) (semantic) |
| 776 Loss | [loss_averse](../../traits/instructions/loss_averse.json) (semantic), [rootless](../../traits/instructions/rootless.json) (semantic) |
| 785 Receiving | [receiving_gifts](../../traits/instructions/receiving_gifts.json) (semantic) |
| 800 Money | [new_money](../../traits/instructions/new_money.json) (agree), [old_money](../../traits/instructions/old_money.json) (agree) |
| 811 Accounts | [accountable](../../traits/instructions/accountable.json) (agree) |
| 833 Regret | [nostalgic](../../traits/instructions/nostalgic.json) (agree) |
| 870 Wonder | [wide_eyed](../../traits/instructions/wide_eyed.json) (semantic) |
| 903 Marriage | [married](../../traits/instructions/married.json) (agree) |
| 904 Celibacy | [childless](../../traits/instructions/childless.json) (semantic), [single](../../traits/instructions/single.json) (agree) |
| 971 Condemnation | [judgmental](../../traits/instructions/judgmental.json) (agree) |
| 992 Sorcery | [mystical](../../traits/instructions/mystical.json) (agree) |
| 998 Rite | [ritualistic](../../traits/instructions/ritualistic.json) (agree) |

## Spot-read: 20 heads rated 0 and 20 rated 1 (draft 2, chosen at random, seed 0)

Rated 0:

| head | class / section | first adjectives | reason |
|---|---|---|---|
| 251 Flatness | II Form | flat, plane, even, flush, discoid, flat as a pancake, flat as a fluke, flat as a flounder | Flat, plane, flush and discoid describe surfaces and shapes; even is used only in the sense of level. |
| 442 Blindness | III Organic matter | blind, eyeless, sightless, visionless, dark, stone-blind, sand-blind, stark-blind | Blind, sightless and wall-eyed describe a physical condition, not a person's nature. |
| 469 Qualification | IV Materials for reasoning | qualifying, qualified, conditioned, restricted, hedged, conditional | Its adjectives (qualifying, conditional, hedged, restricted) describe statements, terms and conditions, not a person. |
| 533 Secret | IV Modes of communication | involved, labyrinthine, mazy, confidential, top secret | Words like involved, mazy and confidential describe matters, documents or arrangements rather than a person's character. |
| 557 Sculpture | IV Means of communicating ideas | sculptured, v.. in relief, ceramic, marble | Its adjectives (sculptured, in relief, ceramic, marble) describe artworks and materials, not a person. |
| 561 Letter | IV Means of communicating ideas | literal, alphabetical, abecedarian, syllabic | Literal, alphabetical, abecedarian and syllabic describe letters and writing systems, not people. |
| 571 Obscurity | IV Means of communicating ideas | obscure, crabbed, involved, confused | Obscure, involved and confused describe writing or meaning; only crabbed is loosely used of a person. |
| 590 Writing | IV Means of communicating ideas | writing, written, in writing, in black and white, under one's hand, uncial, Runic, cuneiform | Adjectives such as written, uncial and cuneiform describe documents and scripts, not people. |
| 629 Circuit | V Prospective volition | circuitous, indirect, roundabout, backhanded | Circuitous, roundabout and indirect describe routes and methods rather than what a person is like. |
| 655 Disease | V Prospective volition | diseased, ailing, ill, ill of, taken ill, seized with, indisposed, unwell | Describes passing illness or ailment, which is a state rather than what a person is like. |
| 664 Safety | V Prospective volition | safe, secure, sure, in safety, in security, on the safe side, under the shield of, under the shade of | Describes being safe or out of danger, which are circumstances rather than what a person is like. |
| 672 Deliverance | V Prospective volition | saved extricable, redeemable, rescuable | Rescue and redemption adjectives describe a situation or thing being saved, not a person's nature. |
| 731 Success | V Results of voluntary action | succeeding, successful, triumphant, flushed with success, crowned with success, victorious, on top, set up | Success adjectives describe outcomes and passing states such as flushed with success or in full swing, not a person's character. |
| 734 Prosperity | V Results of voluntary action | prosperous, thriving, in a fair way, buoyant, well off, well to do, set up, at one's ease | Prosperity adjectives describe a person's financial or fortunate circumstances, not their character. |
| 756 Abrogation | V General intersocial volition | abrogated | "Abrogated" describes a law or right being repealed, which is a thing, not a person. |
| 759 Deputy | V General intersocial volition | acting, vice, vice regal, accredited to | Acting, vice and accredited describe a role or office held, not what a person is like. |
| 776 Loss | V Possessive relations | losing, shorn of, deprived of, denuded, bereaved, bereft, minus, cut off | Bereaved, bereft, out of pocket and deprived of describe a person's passing state or circumstances, not what they are like. |
| 806 Debt | V Possessive relations | indebted, liable, chargeable, answerable for, in debt, in embarrassed circumstances, in difficulties, incumbered | Indebted, liable and in debt describe a financial state or obligation, not what a person is like. |
| 835 Aggravation | VI Personal affections | aggravated, worse, unrelieved, aggravating | Worse, aggravated and aggravating describe circumstances or conditions, not a person's character. |
| 970 Acquittal | VI Moral affections | acquitted, uncondemned, unpunished, unchastised, not guilty, not proven, not liable | Acquitted, not guilty, unpunished and not liable describe a legal outcome or passing circumstance, not what a person is like. |

All 20 read right to me, apart from one edge: 442 Blindness (and 419 Deafness and 655 Disease, outside
the sample) are rated 0 as physical conditions, while disability memberships are being added to the corpus in the main checkout
([blind](../../traits/instructions/blind.json) and [deaf](../../traits/instructions/deaf.json): not in this branch yet).

Rated 1:

| head | class / section | first adjectives | reason |
|---|---|---|---|
| 141 Permanence | I Change | persisting, permanent, established, renewed, intact, inviolate, persistent, monotonous | Mostly describes lasting things, though persistent and conservative can describe a person's disposition. |
| 181 Region | II Space in general | territorial, local, parochial, provincial, regional | Describes places and regions; parochial and provincial can describe a person's narrow outlook. |
| 276 Impulse | II Motion | impelling, impulsive, booming, dynamic, dynamical, impelled | Impulsive and dynamic describe a person's temperament, but the rest (impelling, booming, impelled) describe forces or motion. |
| 372 Mankind | III Organic matter | human, mortal, personal, individual, national, civic, public, social | Cosmopolitan, social, personal and human can describe a person, while national, civic and public mostly describe institutions. |
| 506 Oblivion | IV Extension of thought | forgotten, unremembered, past recollection, bygone, out of mind, buried in oblivion, sunk in oblivion, clean forgotten | A few such as 'forgetful', 'oblivious' and 'heedless' can describe a person's habits, but most describe things that are forgotten. |
| 508 Inexpectation | IV Extension of thought | surprised, unwarned, unaware, off one's guard, unexpected, unanticipated, unlooked for, unforeseen | Mostly describe passing surprise or things that were unexpected; 'unpredictable' can describe a person's temperament. |
| 520 Equivocalness | IV Nature of ideas communicated | equivocal, ambiguous, enigmatical, indeterminate | Mostly describes statements and meanings as ambiguous, though 'equivocal' can describe a person's dubious character. |
| 536 Negation | IV Modes of communication | denying, denied, contradictory, negative, negatory, at issue upon | Mostly describes statements or propositions; only negative, as a temperament, can describe a person. |
| 601 Necessity | V Volition in general | necessary, fated, destined, elect, uncontrollable, inevitable, unavoidable, irresistible | Mostly describe events and forces (inevitable, irresistible, fated), with only unthinking, unwitting and blind applying to a person. |
| 621 Chance | V Prospective volition | unintentional, unintended, accidental, not meant, undesigned, purposed, unforeseen, uncontemplated | Most adjectives describe events or acts (accidental, unintended, random), though a few such as aimless, unpredictable and chancy can describe a person. |
| 675 Essay | V Prospective volition | essaying, tentative, empirical, probationary | Trial and testing adjectives describe methods and probation, with "tentative" only marginally a personal manner. |
| 712 Party | V Antagonism | in league, in partnership, in alliance bonded together, banded together, joined together, embattled, confederated, federative | Words like in league, banded together and joined together describe a person's association with others, not what they are like. |
| 714 Concord | V Antagonism | concordant, congenial, agreeing, in accord, harmonious, united, cemented, allied | Congenial, conciliatory and harmonious can describe a person, but concordant, united and at peace mostly describe situations or agreement. |
| 725 Submission | V Antagonism | surrendering, submissive, resigned, crouching, downtrodden, on one's bended knee, unresistant, unresisting | Submissive, resigned and nonresisting describe a person's disposition, while crouching, downtrodden and on one's bended knee describe posture or circumstance. |
| 765 Request | V Special intersocial volition | requesting, suppliant, supplicant, supplicatory, postulant, importunate, clamorous, urgent | Importunate and clamorous can describe a persistent or demanding person, but most of the adjectives (suppliant, on one's knees, cap in hand) describe a passing manner of asking. |
| 812 Price | V Possessive relations | priced, to the tune of, ad valorem, dutiable, mercenary, venal | Mercenary and venal can describe a person's money-driven or corruptible nature, but the rest concern prices and duties. |
| 867 Dislike | VI Personal affections | disliking, averse from, loathe, loathe to, loth, adverse, shy of, sick of | Mixes person-describing attitudes (disinclined, loth, averse, unpopular) with feelings and things (repulsive, repugnant, abhorrent). |
| 926 Duty | VI Moral affections | obligatory, binding, imperative, peremptory, behooving, incumbent on, chargeable on, under obligation | Obligatory, binding and imperative describe duties or situations, and only amenable describes a person's disposition. |
| 991 Idolatry | VI Religious affections | idolatrous | The single adjective 'idolatrous' describes a practice and only loosely a worshipper. |
| 1000 Temple | VI Religious affections | claustral, cloistered, monastic, monasterial, conventual | 'Monastic' and 'cloistered' can describe a person's way of life, while the rest describe buildings or institutions. |

These are mixed heads, as the rating says; their person words go to M1 with the rest.

## Coverage map and harvest (both checks)

Run once with both checks applied, after the label placement check ([placement_readout.md](./placement_readout.md)): `roget_generate.py coverage` wrote [roget_coverage.json](./roget_coverage.json) and [roget_coverage.md](./roget_coverage.md) (with its new section "Not character"), and `roget_generate.py --dry-run harvest --run-id 2026-10-08-full-dryrun` gave the full-size harvest (no `--every-nth`; nothing written).  The other three columns are the same computations in memory, to separate the two checks' effects: the placements before that check are those of [label_heads.json](./label_heads.json) as committed in 57d3981.

| | no check | head scope only | placement only | both checks (the files now) |
|---|---|---|---|---|
| heads in scope (dispositional 576, Classes I-III 99) | 675 | 675 | 675 | 675 |
| not character (rated 0; left out of the rows below) | 0 | 188 | 0 | 188 |
| covered | 311 | 264 | 307 | 263 |
| partly covered | 75 | 59 | 67 | 53 |
| uncovered (of which a queued label only) | 289 (36) | 164 (22) | 301 (41) | 171 (26) |
| gap classes: pair_completion / pair_empty / singleton_empty / queued_only | 37 / 46 / 170 / 36 | 25 / 19 / 98 / 22 | 31 / 60 / 169 / 41 | 21 / 29 / 95 / 26 |
| opposed pairs: both poles / one pole / neither covered | 75 / 77 / 57 | 67 / 55 / 29 | 76 / 69 / 64 | 68 / 49 / 34 |
| harvest: gap heads selected / skipped as not character / giving words | 289 / 0 / 212 | 289 / 125 / 91 | 301 / 0 / 228 | 301 / 130 / 102 |
| harvest: words (distinct) | 898 (827) | 471 (441) | 1022 (936) | 581 (538) |
| harvest: words dropped with not-character heads | 0 | 427 | 0 | 441 |
| downstream estimate: M1 / M3 if half pass | $3.59 / $8.08 | $1.88 / $4.24 | $4.09 / $9.20 | $2.32 / $5.23 |

The head-scope check takes 188 heads out of the counts, and with them 125 of the 289 gap heads (427 words of the harvest).  The placement check uncovers some heads (covered 311 to 307, uncovered 289 to 301) and so adds 124 words.  Together: 263 covered, 53 partly covered, 171 uncovered, and a full harvest of 581 words from 102 heads instead of 898 from 212, about $2.30 at M1 instead of $3.60.  The gap heads the harvest selects (301) still include the 130 rated 0, because a head keeps its gap class; the harvest skips them and counts them.

## Open points for Roger

1. **Memberships.**  The brief's 0 line named "a person's situation"; draft 2 counts memberships (origin,
   faith, class, way of life) as describing a person, because the corpus counts them as traits (decision
   3), and keeps 0 for passing circumstances.  Wealth and Poverty are now 1 (0 under draft 1); Debt stays 0.
2. **Health and disability heads** (Blindness, Deafness, Disease) are 0 as physical conditions.  If
   disability memberships are traits, these heads should be 1.
3. **Borderline heads change between runs** (5.6%).  A second run, with a head dropped only when both
   runs rate it 0, would cost $0.055 more and keep about 33 more heads in.  Not built.
4. **Price heads rated 1** (Dearness, Price) still send their price words to M1.  The rubric could name
   prices more firmly, at the risk of dropping Liberality-type heads; left as is.
