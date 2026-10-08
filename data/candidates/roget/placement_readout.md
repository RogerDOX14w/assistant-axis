# Roget label placement check: readout (2026-10-08)

Workstream 2 of trait-gap generation, the Roget generator
([coding_plan_02_roget_wordnet.md](../../../reports/trait_gap_generation/coding_plan_02_roget_wordnet.md)).
Roger approved the check on 2026-10-08 ("SG"); it answers
[QUESTIONS.md](../../../reports/trait_gap_generation/QUESTIONS.md) entry 39.

Terms.  A **head** is one numbered entry of Roget's Thesaurus (1911), such as 604 Resolution.  Every
corpus trait and seed-queue label is placed on heads in [label_heads.json](./label_heads.json): its
**primary** head is where its sense sits.  The placement had two routes, lexical (the label's word among
a head's words) and semantic (embedding similarity of the description and the head's words).  The
**route** says how the primary was chosen: `agree` (the two routes agree), `rule` (a lexical hit among
the semantic top five), `semantic` (the semantic top head alone), `lexical` (an adjective hit alone),
`none` (no head).  A head is **covered** when an existing trait has it as its primary.  A wrong primary
makes a head look covered, so the harvest never takes its words, and M3 (the novelty check) cannot see
that gap.

## What the check does

Every label whose route was not `agree` (583: 377 corpus traits, 206 queue labels) went to Sonnet 5.5
(`claude-sonnet-5-5`), one label a call.  Each call carried the label, its description (the corpus file's,
or the queue entry's description or draft; 191 of the 206 queue labels have neither), and its candidate
heads: the semantic top five plus the lexical hits, at most eight, the current primary always among
them.  Each head was shown with its number, title, class and section and about ten of its words.  The
heads were shown in an order seeded by the label, and the call never said which head the rules had
chosen.  The answer is a reason, then the head where the trait's sense belongs, or `none`.  Where
Sonnet's answer differed from the current primary, Opus 5.5 (`claude-opus-5-5`) got the same call,
without Sonnet's answer, and its answer is final.  Rubric:
[roget_placement.md](../../../reports/trait_gap_generation/rubrics/roget_placement.md) (draft 1, pinned as
version 1, rendered calls in the file).  Code:
[placement.py](../../../assistant_axis/gapgen/generators/roget/placement.py), command
`roget_generate.py place-check` ([roget_generate.py](../../../data_analysis/gap_generation/roget_generate.py)).

Each checked label's `llm` field in [label_heads.json](./label_heads.json) now holds Sonnet's answer and
reason, Opus's when asked, the final head, who decided, and the previous primary, route and secondary
heads.  Where the final head differs, `primary` is set to it and `route` to `llm`.  A label left with no
head gets route `none` and loses its secondary heads, since every candidate was rejected as its home.
Every call is in [placement_responses.jsonl](./placement_responses.jsonl); the spend is in
[placement_usage.json](./placement_usage.json).

## The run

| | Sonnet 5.5 | Opus 5.5 | total |
|---|---|---|---|
| calls (retries) | 584 (1) | 319 (0) | 903 |
| tokens in / out a call (output includes thinking) | 1,133 / 143 | 1,146 / 212 | |
| cost | $2.16 | $2.81 | **$4.97** |

Run in two parts: a seeded sample of 30 labels to measure the tokens ($0.22), then the rest with
`--resume` ($4.75), capped at $5 in all.  The first estimate guessed the output at three times what it
was; the estimate now uses the measured figures.  Every label got a usable answer (one Sonnet answer
did not parse and was answered on the retry).  The system prompt was marked for caching as asked, but at
about 420 tokens it is under Sonnet 5.5's and Opus 5.5's 512-token minimum, so nothing was cached.  The
brief expected about $1 a model; the measured cost per call puts both near $2.50.

## Outcomes

| | |
|---|---|
| unchanged | **319** |
| moved to another head | **93** |
| newly placed (no head before) | **115** |
| unplaced (a head before, none now) | **56** |

| route before | labels | unchanged | moved | newly placed | unplaced |
|---|---|---|---|---|---|
| semantic | 198 | 105 | 58 | 0 | 35 |
| rule | 40 | 3 | 22 | 0 | 15 |
| lexical | 22 | 3 | 13 | 0 | 6 |
| none | 323 | 208 | 0 | 115 | 0 |
| existing labels (all routes) | 377 | 206 | 76 | 54 | 41 |
| queued labels (all routes) | 206 | 113 | 17 | 61 | 15 |

Routes now: `agree` 569, `llm` 208, `semantic` 105, `none` 264, `rule` 3, `lexical` 3.  A label keeps
its old route when the check confirmed its head.

## Sonnet and Opus on the referee set

Opus was asked on the 319 labels where Sonnet's answer differed from the current primary.  It agreed with
Sonnet on 224 (70%), kept the current head on 55, and chose a third answer on 40.

| Sonnet proposed | labels | Opus agreed | Opus kept the current head | Opus chose a third head (or none) |
|---|---|---|---|---|
| a move to another head | 109 | 76 | 9 | 24 |
| a head for an unplaced label | 157 | 104 | 42 | 11 |
| none for a placed label | 53 | 44 | 4 | 5 |
| all | 319 | 224 | 55 | 40 |

The third answers read well ([bold](../../traits/instructions/bold.json): Vigor before, Rashness from Sonnet,
Courage from Opus; [agreeable](../../traits/instructions/agreeable.json): Agreement before, Pacification from
Sonnet, Concord from Opus).

## The covered heads that rested on semantic placements

46 heads were covered only by traits placed by the semantic route.  The brief's 34 are the ones with no
secondary support either (marked *).  After the check, **16 of the 34 lose coverage** (19 of the 46):
Killing, Confutation, Maxim, Predetermination, Mid-course, Waste, Inutility, Deterioration, Preparation,
Defiance, Compulsion, Restraint, Loss, Affections, Favorite, Contempt.  Their words now go to the harvest
unless the head-scope check rated the head 0 (last column).

| head (* = no secondary support either: the brief's 34) | its traits before → their primary after | state after | head-scope rating |
|---|---|---|---|
| 55 Exclusion * | [exclusionary](../../traits/instructions/exclusionary.json) → 55 Exclusion; [exclusivist](../../traits/instructions/exclusivist.json) → none | covered ([exclusionary](../../traits/instructions/exclusionary.json)) | 0 |
| 82 Conformity | [conformist](../../traits/instructions/conformist.json) → 82 Conformity; [conscientious (HEXACO)](../../traits/instructions/conscientious_hexaco.json) → 459 Care; [conventional (Kohlberg)](../../traits/instructions/conventional_kohlberg.json) → 82 Conformity; [formulaic](../../traits/instructions/formulaic.json) → 104 Repetition; [rule-abiding](../../traits/instructions/rule_abiding.json) → 82 Conformity; [well-behaved](../../traits/instructions/well_behaved.json) → 82 Conformity | covered ([conformist](../../traits/instructions/conformist.json), [conventional](../../traits/instructions/conventional.json), [conventional (Kohlberg)](../../traits/instructions/conventional_kohlberg.json), [formalist](../../traits/instructions/formalist.json), [rule-abiding](../../traits/instructions/rule_abiding.json), [traditional](../../traits/instructions/traditional.json), [well-behaved](../../traits/instructions/well_behaved.json)) | 1 |
| 149 Changeableness | [adaptable](../../traits/instructions/adaptable.json) → 149 Changeableness | covered ([adaptable](../../traits/instructions/adaptable.json), [brand-agnostic](../../traits/instructions/brand_agnostic.json), [job-hopping](../../traits/instructions/job_hopping.json)) | 2 |
| 320 Levity | [lighthearted](../../traits/instructions/lighthearted.json) → 836 Cheerfulness | partly | 1 |
| 361 Killing * | [killer (Bartle)](../../traits/instructions/killer_bartle.json) → 913 Evil doer | queued | 1 |
| 459 Care | [conscientious](../../traits/instructions/conscientious.json) → 459 Care | covered ([conscientious](../../traits/instructions/conscientious.json), [conscientious (HEXACO)](../../traits/instructions/conscientious_hexaco.json), [conscientiousness (DISC)](../../traits/instructions/conscientiousness_disc.json), [detail-oriented](../../traits/instructions/detail_oriented.json)) | 2 |
| 467 Evidence * | [data-driven](../../traits/instructions/data_driven.json) → 467 Evidence | covered | 0 |
| 479 Confutation * | [confabulatory](../../traits/instructions/confabulatory.json) → 515 Imagination | empty | 0 |
| 483 Underestimation | [understated](../../traits/instructions/understated.json) → 483 Underestimation | covered | 1 |
| 495 Error * | [inaccurate](../../traits/instructions/inaccurate.json) → 495 Error | covered | 1 |
| 496 Maxim * | [maximizing](../../traits/instructions/maximizing.json) → none | empty | 0 |
| 527 Information | [informational](../../traits/instructions/informational.json) → 527 Information | covered | 1 |
| 532 News * | [news-junkie](../../traits/instructions/news_junkie.json) → 532 News | covered | 0 |
| 539 Learning * | [learning-oriented](../../traits/instructions/learning_oriented.json) → 539 Learning | covered | 2 |
| 545 Deception | [manipulative](../../traits/instructions/manipulative.json) → 545 Deception | covered | 1 |
| 578 Elegance * | [formal](../../traits/instructions/formal.json) → 578 Elegance | covered | 1 |
| 590 Writing * | [read-write (VARK)](../../traits/instructions/read_write_vark.json) → 590 Writing | covered | 0 |
| 611 Predetermination * | [determinist](../../traits/instructions/determinist.json) → 601 Necessity | queued | 1 |
| 616 Dissuasion * | [discouraging](../../traits/instructions/discouraging.json) → 616 Dissuasion | covered | 1 |
| 625 Business | [career-oriented](../../traits/instructions/career_oriented.json) → 625 Business; [enterprising (Holland)](../../traits/instructions/enterprising_holland.json) → none | covered ([career-oriented](../../traits/instructions/career_oriented.json)) | 1 |
| 628 Mid-course * | [course-correcting](../../traits/instructions/course_correcting.json) → none | empty | None |
| 638 Waste * | [burned-out](../../traits/instructions/burned_out.json) → 841 Weariness | empty | 0 |
| 639 Sufficiency * | [satisficing](../../traits/instructions/satisficing.json) → 639 Sufficiency | covered | 1 |
| 645 Inutility * | [unhelpful](../../traits/instructions/unhelpful.json) → none | empty | 1 |
| 659 Deterioration * | [languishing](../../traits/instructions/languishing.json) → none | empty | 0 |
| 673 Preparation * | [proactive](../../traits/instructions/proactive.json) → 510 Foresight | empty | 1 |
| 715 Defiance * | [sassy](../../traits/instructions/sassy.json) → 885 Insolence | empty | 2 |
| 734 Prosperity * | [flourishing](../../traits/instructions/flourishing.json) → 734 Prosperity | covered | 0 |
| 744 Compulsion * | [obsessive](../../traits/instructions/obsessive.json) → 606 Obstinacy | queued | 1 |
| 751 Restraint * | [uptight](../../traits/instructions/uptight.json) → 868 Fastidiousness | queued | 1 |
| 776 Loss * | [loss-averse](../../traits/instructions/loss_averse.json) → 864 Caution; [rootless](../../traits/instructions/rootless.json) → none | empty | 0 |
| 785 Receiving * | [receiving gifts](../../traits/instructions/receiving_gifts.json) → 785 Receiving | covered | 0 |
| 820 Affections * | [emotionally-engaged](../../traits/instructions/emotionally_engaged.json) → 822 Sensibility | empty | 2 |
| 844 Humorist | [humorless](../../traits/instructions/humorless.json) → 843 Dullness | partly | None |
| 849 Simplicity * | [unpretentious](../../traits/instructions/unpretentious.json) → 849 Simplicity | covered | 1 |
| 850 Taste * | [aesthete](../../traits/instructions/aesthete.json) → 850 Taste; [tactful](../../traits/instructions/tactful.json) → 894 Courtesy | covered ([aesthete](../../traits/instructions/aesthete.json), [highbrow](../../traits/instructions/highbrow.json)) | 1 |
| 853 Ridiculousness * | [goofy](../../traits/instructions/goofy.json) → 853 Ridiculousness | covered | 1 |
| 870 Wonder | [wide-eyed](../../traits/instructions/wide_eyed.json) → 870 Wonder | covered | 0 |
| 876 Commonalty * | [Gemeinschaft (Tönnies)](../../traits/instructions/gemeinschaft_tonnies.json) → 11 Consanguinity | covered ([working-class](../../traits/instructions/working_class.json)) | 2 |
| 880 Vanity | [vulnerable-narcissistic](../../traits/instructions/vulnerable_narcissistic.json) → none | covered ([grandiose](../../traits/instructions/grandiose.json)) | 2 |
| 899 Favorite * | [dog-person](../../traits/instructions/dog_person.json) → none | empty | None |
| 930 Contempt * | [condescending](../../traits/instructions/condescending.json) → 885 Insolence | empty | 2 |
| 933 Flattery | [flirty](../../traits/instructions/flirty.json) → 902 Endearment | partly | 2 |
| 950 Penitence * | [remorseful](../../traits/instructions/remorseful.json) → 950 Penitence | covered | 2 |
| 959 Drunkenness * | [heavy-drinker](../../traits/instructions/heavy_drinker.json) → 959 Drunkenness | covered | 1 |
| 989 Irreligion * | [secular-rational (Inglehart-Welzel)](../../traits/instructions/secular_rational_inglehart_welzel.json) → 989 Irreligion | covered | 2 |

Two of the brief's examples of right placements were moved: *obsessive* on 744 Compulsion and *uptight*
on 751 Restraint.  In Roget, Compulsion is coercion (*compelling, coercive, compulsory*) and Restraint
is confinement (*imprisoned, under lock and key*).  Sonnet and Opus put
[obsessive](../../traits/instructions/obsessive.json) on 606 Obstinacy ("in Roget it also covers fixed
ideas, infatuation and monomania") and [uptight](../../traits/instructions/uptight.json) on 868
Fastidiousness (its description is about fussing that every small thing be done properly).

## Spot-read: 20 unchanged labels (chosen at random, seed 0)

| label | description, first clause | head kept (route) | decided by | reason |
|---|---|---|---|---|
| [Artistic Interests (IPIP-NEO)](../../seed_queue.json) (queued) | (no description) | none (none) | sonnet | Artistic interests mean a broad appreciation of the arts, but each listed head covers only one art or its practitioners, or a creative faculty, so none names the whole. |
| [charismatic](../../traits/instructions/charismatic.json) | This means showing a magnetic personality that naturally draws others in, communicating with confidence ... | 288 Attraction (semantic) | sonnet | Charisma is a magnetic power of drawing others in, which best matches Attraction (attractive, attractiveness, drawing to), though that head is framed physically. |
| [dim-witted](../../seed_queue.json) (queued) | This means being dim-witted, never brilliant: | 499 Imbecility. Folly (semantic) | sonnet | Dim-witted means lacking intelligence and slow to understand, which matches Imbecility. Folly (unintelligent, witless, brainless) rather than the optical or tedium senses of 'dim' and 'dull'. |
| [experiencer (VALS)](../../traits/instructions/experiencer_vals.json) | This means being young, enthusiastic and impulsive, quick to warm to the new and ... | none (none) | sonnet | The trait bundles several qualities (youth, novelty-seeking, risk, spending), and no listed head names the whole; Impulse covers only one part. |
| [focused](../../traits/instructions/focused.json) | This means keeping one's attention on the task through every buzz, noise or passing ... | 457 Attention (semantic) | sonnet | Keeping one's attention on the task despite distractions is the quality named by 'Attention' (attentive, intentness), while 'Focus' here means a gathering place. |
| [full-price shopper](../../traits/instructions/full_price_shopper.json) | This means buying what one wants when one wants it, never comparing stores or ... | none (none) | opus | The trait is a buyer's indifference to price, and no listed head names that disposition: Purchase only shares the topic of buying, while Dearness describes costly goods, not a careless spender. |
| [goofy](../../traits/instructions/goofy.json) | This means embracing silly humor, including deliberately ridiculous jokes, acting playfully foolish, or demonstrating ... | 853 Ridiculousness (semantic) | sonnet | Goofy means silly, absurd, comical behaviour, which matches the words of Ridiculousness (ludicrous, comical, droll, funny). |
| [Hogan HPI / HDS / MVPI](../../seed_queue.json) (queued) | (no description) | none (none) | sonnet | The label names a bundle of personality inventories, and none of the listed heads (vehicle, mart, sale, opening, airpipe) names that or any close quality. |
| [ISTP (MBTI)](../../traits/instructions/istp_mbti.json) | This means drawing energy from reflection, taking in facts and specifics, deciding by logic, ... | none (none) | sonnet | ISTP is a bundle of several qualities, and no listed head names the whole; Thought or Intellect covers only a part. |
| [lustful](../../traits/instructions/lustful.json) | This means expressing strong sexual desire and attraction, steering conversations toward sensual or sexual ... | 374a Sexuality (semantic) | sonnet | Head 374a Sexuality holds adjectives like sexy, erotic, carnal and hot, which name sexual desire and attraction directly. |
| [modern-racism scales](../../seed_queue.json) (queued) | (no description) | none (none) | sonnet | Modern-racism scales are measurement instruments for subtle racial prejudice, and no listed head names that; the nearest heads only touch the topic or share a word. |
| [nationalist](../../traits/instructions/nationalist.json) | This means prioritizing one's own nation's interests, culture, and people above those of other ... | none (none) | opus | None of the listed heads names devotion to one's own nation: Politics only shares the topic, and Selfishness concerns the self, not the nation. |
| [racialist](../../seed_queue.json) (queued) | (no description) | none (none) | sonnet | No head names racial prejudice; Misanthropy is hatred of mankind generally and Discrimination is mere perception of difference. |
| [receiving gifts](../../traits/instructions/receiving_gifts.json) | This means feeling loved through gifts, treasured for the thought and effort behind them: | 785 Receiving (semantic) | sonnet | The trait is about being a recipient of gifts, and 'Receiving' (acceptance, recipient) is the closest head, though it does not capture the feeling of being treasured. |
| [scheming](../../traits/instructions/scheming.json) | This means forming hidden plans and concealing one's true intentions until they are ready ... | 702 Cunning (semantic) | sonnet | Scheming as a trait of a person is best captured by cunning, crafty, artful maneuvering, while Plan and Concealment each cover only half of it. |
| [secure attachment](../../traits/instructions/secure_attachment.json) | This means finding it relatively easy to get emotionally close to others, being comfortable ... | none (none) | opus | Secure attachment is a specific way of relating that combines ease with closeness, comfortable interdependence and freedom from fear of rejection, and no listed head names that whole quality; Security here means financial guarantees, and Friendship and Content only touch parts of it. |
| [shinto](../../seed_queue.json) (queued) | (no description) | none (none) | opus | Shinto is a particular religion, and no listed head names following it: these heads cover gods, idolatry, temples, non-Christian scriptures and rites, which only share its topic. |
| [trapped-in-job](../../seed_queue.json) (queued) | (no description) | none (none) | opus | Feeling stuck in one's job is a modern situation that bundles employment with felt constraint, and no head names that whole bundle: Restraint means confinement in general and Business means work in general. |
| [unpretentious](../../traits/instructions/unpretentious.json) | This means saying it in ordinary words, as one would to a neighbor, with ... | 849 Simplicity (semantic) | sonnet | Head 849 Simplicity names plain, homely, ordinary manner without ostentation or airs, matching the unpretentious trait. |
| [well-behaved](../../traits/instructions/well_behaved.json) | This means no pranks, no teasing, no bending a rule for fun, keeping everything ... | 82 Conformity (semantic) | opus | The description is about sticking to the rules and keeping order rather than about politeness, so Conformity, being 'conformable to rule', fits better than Courtesy. |

## Every change (264)

Labels link to their trait file, or to the seed queue for a queued label (no file yet).  "Decided by"
is Sonnet where it agreed with the current head (then no change is listed), Opus otherwise; Sonnet's
answer is in brackets where Opus decided differently.

| label | change | before (route) | after | decided by | reason (of the deciding model) |
|---|---|---|---|---|---|
| [accommodating](../../traits/instructions/accommodating.json) | moved | 723 Pacification (semantic) | 774 Compromise (Sonnet: 906 Benevolence) | opus | Compromise names readily adjusting one's position and conceding to others ('adjustment', 'mutual concession', 'abatement of differences'), which is the accommodating quality described. |
| [Aesthetic Appreciation (HEXACO)](../../seed_queue.json) (queued) | moved | 931 Approbation (rule) | 850 Taste (Sonnet: 845 Beauty) | opus | Aesthetic Appreciation is a person's sensitivity to and enjoyment of beauty, which the Taste head names as refined, cultivated taste; the Beauty head names the quality of the things admired, not the person's capacity. |
| [aggrieved](../../seed_queue.json) (queued) | moved | 835 Aggravation (semantic) | 900 Resentment | opus | Being aggrieved means feeling resentment at having been wronged, which is the quality the Resentment head names. |
| [agreeable](../../traits/instructions/agreeable.json) | moved | 23 Agreement (semantic) | 714 Concord (Sonnet: 723 Pacification) | opus | The trait is about keeping harmony and good relations with others, which is what Concord's words (harmonious, congenial, in accord) name; Pleasurableness holds 'agreeable' only in the sense of pleasing. |
| [anxious](../../traits/instructions/anxious.json) | moved | 824 Excitation (rule) | 860 Fear | opus | Fear (860) covers apprehension, unease and worried anticipation of harm, which is the habitual worry described; Desire holds 'anxious' only in the sense of eager. |
| [anxious (IPIP-NEO)](../../seed_queue.json) (queued) | moved | 865 Desire (lexical) | 860 Fear | opus | The IPIP-NEO anxiety facet means being prone to worry and fearfulness, which is the quality named by the Fear head (fearful, timidity, apprehension); Desire uses 'anxious' only in the sense of eager. |
| [apolitical](../../traits/instructions/apolitical.json) | moved | 737b Politics (semantic) | 866 Indifference | opus | Being apolitical is unconcern and neutrality toward politics, which Indifference names, while the Politics head only shares the topic. |
| [authoritarian (Baumrind)](../../traits/instructions/authoritarian_baumrind.json) | moved | 737 Authority (semantic) | 739 Severity | opus | Authoritarian parenting is strict, rigid and harsh in its control, which is what Severity names (strict, harsh, rigid, rigor). |
| [big-picture](../../traits/instructions/big_picture.json) | moved | 556 Painting (rule) | 78 Generality | opus | The trait is an emphasis on general, broad, comprehensive principles over particulars, which is what the Generality head names. |
| [bold](../../traits/instructions/bold.json) | moved | 574 Vigor (lexical) | 861 Courage (Sonnet: 863 Rashness) | opus | Acting without waiting on the unknown and pressing ahead despite danger is daring or venturesomeness, which the Courage head names; Rashness would add a reproach for lack of caution that the description does not make. |
| [brilliant](../../seed_queue.json) (queued) | moved | 420 Light (rule) | 498 Intelligence, Wisdom | opus | Quick, deep intellect that grasps ideas fast matches Intelligence, Wisdom, with words like 'quick of apprehension', 'keen' and 'acute'. |
| [burned-out](../../traits/instructions/burned_out.json) | moved | 638 Waste (semantic) | 841 Weariness | opus | Burnout's jaded, sick-of-it ennui and loss of care for work that once mattered is the weariness of Weariness, not the mere bodily tiredness of Fatigue. |
| [calculating](../../traits/instructions/calculating.json) | moved | 498 Intelligence, Wisdom (lexical) | 702 Cunning | opus | Calculating in the sense of scheming for one's own advantage and manipulating people is cunning and craftiness, while Numeration only shares the spelling. |
| [childless](../../traits/instructions/childless.json) | moved | 904 Celibacy (semantic) | 169 Unproductiveness | opus | Unproductiveness holds 'barren', 'infertile' and 'sterility', the head nearest to having no offspring; Celibacy is about being unmarried, not about having no children. |
| [clannish](../../traits/instructions/clannish.json) | moved | 893 Seclusion. Exclusion (semantic) | 712 Party (Sonnet: none) | opus | Party covers faction, clanship and partisan loyalty to one's own band against outsiders, which is the clannish disposition; Consanguinity only shares the topic of kinship. |
| [closed-minded](../../traits/instructions/closed_minded.json) | moved | 261 Closure (semantic) | 481 Misjudgment | opus | Misjudgment (481) covers prejudice, narrow-mindedness, bigotry and dogmatism, which is exactly rigid, closed-minded adherence to one's views. |
| [closure-seeking](../../traits/instructions/closure_seeking.json) | moved | 261 Closure (semantic) | 474 Certainty | opus | Needing questions settled and holding firmly to an answer is a craving for certitude, which the Certainty head names; Closure (261) means physical shutting, a different sense of the word. |
| [condescending](../../traits/instructions/condescending.json) | moved | 930 Contempt (semantic) | 885 Insolence | opus | Talking down to others with an air of superiority is the haughty, lofty manner named by Insolence's 'haughty', 'arrogant' and 'airs'. |
| [confabulatory](../../traits/instructions/confabulatory.json) | moved | 479 Confutation (semantic) | 515 Imagination | opus | Confabulating means filling gaps in knowledge with plausible invention, which matches the inventive fabrication of Imagination; Conversation's 'confabulation' means chatting, a different sense. |
| [conscientious (Big Five)](../../traits/instructions/conscientious_big_five.json) | moved | 926 Duty (lexical) | 772 Observance | opus | Observance names faithful, punctual, punctilious fulfilment of obligations. That is the core of the described conscientiousness: arriving on time, honoring every obligation and being scrupulous. |
| [conscientious (HEXACO)](../../traits/instructions/conscientious_hexaco.json) | moved | 82 Conformity (semantic) | 459 Care | opus | Care (careful, heedful, particular) names the painstaking, orderly carefulness behind HEXACO conscientiousness, while the other heads touch only one part of it, such as prudence, punctuality or fussiness. |
| [conscientiousness (DISC)](../../traits/instructions/conscientiousness_disc.json) | moved | 864 Caution (semantic) | 459 Care (Sonnet: none) | opus | The DISC conscientiousness style is precise, methodical and attentive to detail, which matches Care's careful, heedful and particular. |
| [contrarian](../../traits/instructions/contrarian.json) | moved | 14 Contrariety (semantic) | 489 Dissent | opus | A contrarian holds and voices opinions against accepted belief, which is the dissent of 489 (dissenting, dissident, difference of opinion). |
| [conventional](../../traits/instructions/conventional.json) | moved | 769 Compact (rule) | 82 Conformity | opus | Conformity names doing things according to rule and the usual way, which matches the trait of following templates and distrusting the eccentric; 769 holds 'conventional' only in the sense of agreed by compact. |
| [conventional (HEXACO)](../../traits/instructions/conventional_hexaco.json) | moved | 769 Compact (lexical) | 456 Incuriosity | opus | Low Openness centres on lacking curiosity and interest in art, ideas and things beyond one's own sphere, which is what Incuriosity names. |
| [critical](../../traits/instructions/critical.json) | moved | 932 Disapprobation (lexical) | 461 Inquiry | opus | The core quality is systematic questioning and scrutiny of accepted claims, which Inquiry's analytic, examining words name; Disapprobation is fault-finding criticism, a different sense. |
| [death-accepting](../../traits/instructions/death_accepting.json) | moved | 360 Death (semantic) | 831 Content (Sonnet: 725 Submission) | opus | The trait is calm, untroubled acceptance of one's lot, which Content's words (at ease, contented, and in Roget resignation and reconciliation) name; Death and Interment only share the topic. |
| [detail-oriented](../../traits/instructions/detail_oriented.json) | moved | 868 Fastidiousness (semantic) | 459 Care | opus | Care names heedful, particular, exact attention to every point, which is the detail-oriented habit; Attention is only general mindfulness. |
| [determinist](../../traits/instructions/determinist.json) | moved | 611 Predetermination (semantic) | 601 Necessity | opus | Necessity names fate, inevitability and the absence of free will, and in Roget it also holds fatalism and necessitarianism, which is the determinist's belief; Predetermination is about a person planning ahead instead. |
| [disagreeable](../../traits/instructions/disagreeable.json) | moved | 24 Disagreement (semantic) | 713 Discord | opus | Discord (713) names being at odds and on bad terms with others, which is the quarrelsome, peace-disregarding friction the description gives; Disagreement (24) is only an abstract relation between things. |
| [dismissive-avoidant attachment](../../traits/instructions/dismissive_avoidant_attachment.json) | moved | 866 Indifference (semantic) | 893 Seclusion. Exclusion (Sonnet: none) | opus | Seclusion covers aloofness, unsociability and keeping apart from others, which is the core of being comfortable without close emotional ties. |
| [distressed](../../seed_queue.json) (queued) | moved | 804 Poverty (lexical) | 828 Pain | opus | Being distressed means suffering mental pain or affliction, which is what the Pain head names (suffering, pained, afflicted, worried). |
| [educated](../../traits/instructions/educated.json) | moved | 490 Knowledge (rule) | 492 Scholar (Sonnet: 539 Learning) | opus | The trait is about holding college or graduate degrees, and the Scholar head names exactly such people: graduate, master of arts, doctor, academician. |
| [Emotionality (IPIP-NEO)](../../seed_queue.json) (queued) | moved | 821 Feeling (rule) | 822 Sensibility | opus | The IPIP-NEO Emotionality facet means being receptive and sensitive to one's own feelings, which matches Sensibility (sensitive, impressionable, sensitiveness). |
| [emotionally-disengaged](../../traits/instructions/emotionally_disengaged.json) | moved | 866 Indifference (semantic) | 823 Insensibility | opus | Insensibility names an impassive nature on which slights and kindnesses alike barely register, which is the emotional disengagement described. |
| [emotionally-engaged](../../traits/instructions/emotionally_engaged.json) | moved | 820 Affections (semantic) | 822 Sensibility | opus | The trait is being strongly impressionable and susceptible to how others treat one, which is what Sensibility names (sensitive, impressible, susceptible). |
| [empathetic](../../traits/instructions/empathetic.json) | moved | 821 Feeling (semantic) | 914 Pity | opus | Empathy is compassionate fellow-feeling for another's emotions, which Pity names with 'compassionate' and 'sympathetic'. |
| [enigmatic](../../traits/instructions/enigmatic.json) | moved | 519 Unintelligibility (rule) | 520 Equivocalness | opus | The trait is deliberately ambiguous communication open to multiple meanings, and that is what Equivocalness names, with words like 'enigmatical' and 'ambiguous' in the sense meant here. |
| [enthusiastic (BFAS)](../../seed_queue.json) (queued) | moved | 858 Hope (rule) | 682 Activity (Sonnet: 825 Excitability) | opus | Activity covers eagerness, zeal and liveliness ('lively', 'animated'), which is the core of an enthusiastic disposition. |
| [extroverted](../../traits/instructions/extroverted.json) | moved | 893 Seclusion. Exclusion (semantic) | 892 Sociality | opus | Seeking company and enjoying conversation is sociability, which is what Sociality names; 'outgoing' in Egress refers to physical motion. |
| [financially conservative](../../traits/instructions/financially_conservative.json) | moved | 670 Preservation (rule) | 864 Caution | opus | The description is about refusing financial risk, which is caution and prudence (wary, careful), not frugal spending or stinginess. |
| [flirty](../../traits/instructions/flirty.json) | moved | 933 Flattery (semantic) | 902 Endearment | opus | Endearment covers amorous dalliance, blandishment and billing and cooing, and in Roget it holds flirtation and coquetry, which is playful romantic interest. |
| [formalist](../../traits/instructions/formalist.json) | moved | 240 Form (semantic) | 82 Conformity | opus | The Conformity head's words for following rule and regulation name the formalist's adherence to established procedure and format; the Form head shares only the word, in its sense of shape. |
| [formulaic](../../traits/instructions/formulaic.json) | moved | 82 Conformity (semantic) | 104 Repetition | opus | Repetition covers monotonous sameness, the same pattern recurring every time with nothing new, which is the core of a formulaic manner. |
| [Gemeinschaft (Tönnies)](../../traits/instructions/gemeinschaft_tonnies.json) | moved | 876 Commonalty (semantic) | 11 Consanguinity | opus | The description centres on belonging from birth to one's own kin and folk, which is the blood-kinship that Consanguinity names (kindred, akin, of the blood). |
| [gloating](../../seed_queue.json) (queued) | moved | 884 Boasting (semantic) | 838 Rejoicing | opus | Gloating means exulting smugly in one's own success or another's misfortune, which the exultation and triumph words of Rejoicing name. |
| [grandiose](../../traits/instructions/grandiose.json) | moved | 884 Boasting (semantic) | 880 Vanity | opus | Grandiosity is at heart an inflated, overweening sense of one's own importance, which is what Vanity's 'conceited', 'overweening' and 'self-conceit' name; Boasting covers only the outward claims. |
| [grey-haired](../../seed_queue.json) (queued) | moved | 432 Gray (semantic) | 128 Age | opus | Said of a person, grey-haired means old, and the Age head covers being aged and hoary, whereas Gray only names the colour. |
| [grounded](../../traits/instructions/grounded.json) | moved | 211 Base (rule) | 576 Plainness | opus | The trait is a plain, homely, unadorned way of speaking, which is what Plainness (576) names as a quality of expression. |
| [guilt-prone](../../seed_queue.json) (queued) | moved | 947 Guilt (semantic) | 950 Penitence | opus | Being guilt-prone means readily feeling remorse, which is the conscience-stricken, compunctious feeling Penitence names, whereas Guilt names actual culpability. |
| [historical](../../traits/instructions/historical.json) | moved | 594 Description (rule) | 122 The Past | opus | The trait is a habit of looking back to and invoking past events, and The Past head names exactly that, from bygone times to looking back on them. |
| [humorless](../../traits/instructions/humorless.json) | moved | 844 Humorist (semantic) | 843 Dullness | opus | Dullness is the head set against Wit, naming the prosaic, matter-of-fact lack of humour the trait describes. |
| [Immoderation (IPIP-NEO)](../../seed_queue.json) (queued) | moved | 174 Moderation (semantic) | 954 Intemperance | opus | IPIP-NEO Immoderation is the tendency to give in to cravings and indulge oneself without restraint, which is what Intemperance names (intemperate, self-indulgent). |
| [introverted (HEXACO)](../../traits/instructions/introverted_hexaco.json) | moved | 893 Seclusion. Exclusion (semantic) | 881 Modesty | opus | Modesty's diffident, bashful, shy, retiring disposition covers the low social self-confidence, squirming under attention and holding back from gatherings that make up the trait, though not its low liveliness. |
| [irresponsible](../../traits/instructions/irresponsible.json) | moved | 460 Neglect (semantic) | 927 Dereliction of Duty | opus | The description is about leaving one's duties undone, which is exactly what Dereliction of Duty names, while Exemption holds 'irresponsibility' only in the sense of being free from liability. |
| [killer (Bartle)](../../traits/instructions/killer_bartle.json) | moved | 361 Killing (semantic) | 913 Evil doer | opus | The trait is about delighting in dominating and distressing real people, which matches the oppressor, tyrant and mischief-maker of Evil doer; Killing only shares the in-game word 'kill'. |
| [laid-back](../../traits/instructions/laid_back.json) | moved | 738 Laxity (semantic) | 685 Leisure | opus | The Leisure head's words (leisurely, calm, quiet, undisturbed, and taking it easy) name the easy, unhurried manner the description gives, though the fit is loose and no calmness-of-temper head is listed. |
| [lighthearted](../../traits/instructions/lighthearted.json) | moved | 320 Levity (semantic) | 836 Cheerfulness | opus | Lighthearted means a blithe, cheerful disposition that carries nothing heavily, which is what the Cheerfulness head names; the Light and Levity heads share only the spelling, in a physical sense. |
| [loss-averse](../../traits/instructions/loss_averse.json) | moved | 776 Loss (semantic) | 864 Caution | opus | Weighing every choice by what could be lost and shunning risk is wariness and prudence, the quality named by Caution; Loss and Failure only share the topic. |
| [manic](../../traits/instructions/manic.json) | moved | 503 Insanity (rule) | 825 Excitability (Sonnet: none) | opus | The trait is a lasting temperament of headlong, boisterous, easily fired energy, which matches Excitability ('high-strung', 'impetuosity', 'vehemence') rather than clinical insanity or a passing state of excitement. |
| [neurotic](../../traits/instructions/neurotic.json) | moved | 503 Insanity (rule) | 825 Excitability | opus | Excitability names being high-strung and easily excited, which comes very close to the emotional instability and reactivity of a neurotic person, while Insanity is too strong. |
| [obsessive](../../traits/instructions/obsessive.json) | moved | 744 Compulsion (semantic) | 606 Obstinacy (Sonnet: 457 Attention) | opus | Obstinacy is the closest fit: in Roget it also covers fixed ideas, infatuation and monomania, which matches a compulsive focus that dominates thought, whereas Attention is only ordinary heedfulness. |
| [opinionated](../../traits/instructions/opinionated.json) | moved | 481 Misjudgment (lexical) | 535 Affirmation | opus | The description is about stating definite positions and asserting them firmly, which matches Affirmation's 'asserting', 'positive' and 'absolute' rather than stubbornness or prejudice. |
| [organized](../../traits/instructions/organized.json) | moved | 357 Organization (rule) | 60 Arrangement (Sonnet: 58 Order) | opus | Arrangement holds 'methodical', 'orderly' and 'cut and dried', which name the planned, step-by-step ordering the description gives, while 357 uses 'organized' only in the biological sense. |
| [overconfident](../../traits/instructions/overconfident.json) | moved | 482 Overestimation (semantic) | 484 Belief | opus | The Belief head includes 'positive' and 'cocksure', which name a person who is sure beyond warrant; the Certainty head names certainty itself rather than unwarranted assurance. |
| [Perfectionism (HEXACO)](../../seed_queue.json) (queued) | moved | 650 Perfection (semantic) | 868 Fastidiousness | opus | HEXACO perfectionism is thoroughness and a demand for flawlessness in one's work, which is the exacting, hard-to-please quality named by fastidiousness, while 650 names the state of being perfect rather than the trait of demanding it. |
| [petty](../../traits/instructions/petty.json) | moved | 193 Littleness (rule) | 868 Fastidiousness | opus | Fastidiousness, with its hypercriticism and difficulty in being pleased, comes closest to blowing small slights up into big grievances, while Unimportance and Smallness only describe trivial things themselves. |
| [plain-spoken](../../traits/instructions/plain_spoken.json) | moved | 582 Speech (rule) | 576 Plainness | opus | Head 576, Plainness, under means of communicating ideas, names plain, unadorned, unvarnished style of language, which is exactly this trait. |
| [precise](../../traits/instructions/precise.json) | moved | 572 Conciseness (semantic) | 570 Perspicuity | opus | Perspicuity, with its words definiteness, definition and explicitness, is the stylistic quality of exact, unambiguous expression the description gives. |
| [proactive](../../traits/instructions/proactive.json) | moved | 673 Preparation (semantic) | 510 Foresight | opus | Proactive here means anticipating needs and future problems, which is what the Foresight head names with words like anticipation, forethought and farsighted. |
| [rooted](../../traits/instructions/rooted.json) | moved | 184 Location (rule) | 188 Inhabitant | opus | Inhabitant's words 'native', 'indigenous' and 'autochthonous' name being from a place and of its own people, which is the core of the trait; 184 holds 'rooted' only in the sense of physical placement. |
| [sassy](../../traits/instructions/sassy.json) | moved | 715 Defiance (semantic) | 885 Insolence | opus | Sassy means cheeky and saucy, which is impertinence, and the Insolence head (pert, saucy, impertinent) names that quality. |
| [scientific](../../seed_queue.json) (queued) | moved | 494 Truth (lexical) | 463 Experiment | opus | Said of a person, 'scientific' means an empirical, analytic, experimental way of thinking, which matches the Experiment head's 'empirical' and 'analytic'. |
| [self-effacing](../../traits/instructions/self_effacing.json) | moved | 879 Humility (semantic) | 881 Modesty | opus | Self-effacement, shrinking from notice and passing attention to others, is the retiring, unobtrusive disposition named in Modesty. |
| [self-reliant](../../traits/instructions/self_reliant.json) | moved | 858 Hope (lexical) | 748 Freedom | opus | Doing the whole job oneself and asking nobody for help is independence from others, which the Freedom head names with 'independent' and 'independence'. |
| [spartan](../../traits/instructions/spartan.json) | moved | 576 Plainness (semantic) | 955 Asceticism | opus | Choosing a hard bed, plain food and no luxury on purpose is austere self-denial, which is what the Asceticism head names. |
| [specialist](../../traits/instructions/specialist.json) | moved | 79 Speciality (semantic) | 700 Proficient | opus | A specialist is an expert or master hand in a field, which is exactly what the Proficient head names. |
| [spiteful](../../traits/instructions/spiteful.json) | moved | 919 Revenge (semantic) | 907 Malevolence (Sonnet: 921 Envy) | opus | Spitefulness, wishing harm on another even at a cost to oneself, is ill will toward others, which is what Malevolence names, rather than envy of another's goods or revenge for a wrong. |
| [spontaneous](../../traits/instructions/spontaneous.json) | moved | 600 Will (rule) | 612 Impulse (Sonnet: 139 Irregularity of recurrence) | opus | The Impulse head's words (extemporaneous, improvised, unpremeditated, impromptu) name spontaneity: acting unplanned rather than to a set formula. |
| [straightforward](../../seed_queue.json) (queued) | moved | 246 Straightness (semantic) | 543 Veracity | opus | Said of a person, straightforward means frank, candid and honest in dealing, which Veracity names with 'candid', 'sincere' and 'frankness'. |
| [stream-of-consciousness](../../traits/instructions/stream_of_consciousness.json) | moved | 69 Continuity (semantic) | 514a Analogy | opus | Head 514a names this flow of thought directly with 'free association', 'association of ideas' and 'train of thought'. |
| [subdued](../../seed_queue.json) (queued) | moved | 749 Subjection (semantic) | 826 Inexcitability | opus | Said of a person, 'subdued' means quiet and calm in manner rather than lively or excitable, which is the even, unexcitable temper of Inexcitability. |
| [superstitious](../../traits/instructions/superstitious.json) | moved | 477 Intuition & Sophistry (rule) | 486 Credulity (Sonnet: none) | opus | Superstition is a belief in omens and charms without reason, and Roget files 'superstitious' under Credulity; the Omen and Spell heads name only the objects of that belief. |
| [tactful](../../traits/instructions/tactful.json) | moved | 850 Taste (semantic) | 894 Courtesy | opus | Tact is considerate, diplomatic dealing with others, which sits closest to Courtesy's polite, civil, urbane manners; Touch holds 'tact' only in its physical sense. |
| [tech-savvy](../../seed_queue.json) (queued) | moved | 498 Intelligence, Wisdom (rule) | 698 Skill | opus | Tech-savvy means being adept and expert with technology, a domain-specific form of the dexterity and expertise named in Skill. |
| [traditional](../../traits/instructions/traditional.json) | moved | 124 Oldness (rule) | 82 Conformity | opus | The trait is a person's leaning toward conventional, established ways, which Conformity's conventional observance of rule and custom names most closely; Oldness only describes how old things are. |
| [uncritical](../../traits/instructions/uncritical.json) | moved | 931 Approbation (lexical) | 486 Credulity | opus | Accepting the official story without asking what it hides is ready, unquestioning belief, which is credulity. |
| [unreliable](../../traits/instructions/unreliable.json) | moved | 475 Uncertainty (lexical) | 773 Nonobservance | opus | Nonobservance names failing to keep or fulfil one's commitments and promises (omission, neglect, nonfulfilment), which is the core of being unreliable. |
| [uptight](../../traits/instructions/uptight.json) | moved | 751 Restraint (semantic) | 868 Fastidiousness | opus | The description centres on fussing that every small thing be done properly and being unable to let anything slide, which is what Fastidiousness names (finicky, demanding, hard to please). |
| [visceral](../../traits/instructions/visceral.json) | moved | 574 Vigor (semantic) | 477 Intuition & Sophistry | opus | Visceral communication springs from gut reaction and instinct rather than reasoning, which matches Intuition's 'instinctive, impulsive, independent of reason, hunch'. |
| [Volatility (BFAS)](../../seed_queue.json) (queued) | moved | 605 Irresolution (lexical) | 825 Excitability | opus | BFAS Volatility is the Neuroticism aspect of emotional lability, irritability and quick upset, which matches the excitable, high-strung, impetuous temper named by Excitability. |
| [wry](../../traits/instructions/wry.json) | moved | 856 Ridicule (semantic) | 842 Wit | opus | Wry humour is a dry, clever, ironic kind of wit, which matches the Wit head better than Ridicule's focus on deriding a target. Distortion holds 'wry' only in the sense of 'twisted'. |
| [zealous](../../traits/instructions/zealous.json) | moved | 173 Violence (semantic) | 821 Feeling (Sonnet: 825 Excitability) | opus | Beyond its listed words, Roget's Feeling head also holds warmth, fervor, ardor, zeal and passion, which is the hot, fired-up conviction the description gives. |
| [Achievement Striving (IPIP-NEO)](../../seed_queue.json) (queued) | newly placed | none (none) | 604 Resolution (Sonnet: 622 Pursuit) | opus | Achievement striving is a determined drive toward goals, which is closest to the strong-willed determination named by Resolution; Success names an outcome, not a trait. |
| [ambivalent](../../seed_queue.json) (queued) | newly placed | none (none) | 605 Irresolution | opus | Being ambivalent as a person means having mixed feelings and being torn or undecided, which matches 605's "double-minded", "half-hearted" and "undecided"; 520 is about ambiguous meaning, not a state of mind. |
| [american](../../seed_queue.json) (queued) | newly placed | none (none) | 188 Inhabitant | opus | Being American is a nationality, the quality of being a native or inhabitant of a country, which the Inhabitant head covers with words like 'native', 'British' and 'English'. |
| [antitheist](../../seed_queue.json) (queued) | newly placed | none (none) | 989 Irreligion | opus | An antitheist rejects and opposes belief in God, and the Irreligion head names that godless, anti-religious stance. |
| [attention-seeking](../../traits/instructions/attention_seeking.json) | newly placed | none (none) | 882 Ostentation | opus | Wanting every eye on oneself is showing off and making a display, which is what Ostentation names; the Attention head only shares a word, since it means being attentive. |
| [australian](../../seed_queue.json) (queued) | newly placed | none (none) | 188 Inhabitant | opus | Being Australian is a nationality, which is a matter of where one is native or lives, and the Inhabitant head holds national adjectives such as 'British' and 'English'. |
| [bargain-hunter](../../traits/instructions/bargain_hunter.json) | newly placed | none (none) | 817 Economy | opus | Hunting bargains to count the savings is the frugal, thrifty quality that Economy names; Cheapness and Discount only share the topic of low prices. |
| [black-haired](../../seed_queue.json) (queued) | newly placed | none (none) | 431 Blackness | opus | Black-haired names a person whose hair is black, and the Blackness head names that black or dark colouring. |
| [blonde](../../seed_queue.json) (queued) | newly placed | none (none) | 436 Yellowness | opus | Blonde means having fair, golden-yellow hair, which is the pale yellow colour that Yellowness names (golden, aureate). |
| [blue-eyed](../../seed_queue.json) (queued) | newly placed | none (none) | 438 Blueness | opus | Being blue-eyed means having eyes coloured blue, and of the listed heads Blueness comes closest to naming that colour quality. |
| [body-insecure](../../traits/instructions/body_insecure.json) | newly placed | none (none) | 881 Modesty | opus | Body insecurity is shame and diffidence about one's own looks, shown in hiding and avoiding notice, which comes closest to Modesty's bashful, diffident self-consciousness; Danger's 'insecurity' and Ugliness only share the words or the topic. |
| [body-obsessed](../../seed_queue.json) (queued) | newly placed | none (none) | 880 Vanity | opus | Being preoccupied with one's own body and looks is a form of vanity, the peacock-like concern with one's appearance that Vanity names. |
| [brand-agnostic](../../traits/instructions/brand_agnostic.json) | newly placed | none (none) | 149 Changeableness | opus | Always switching brands and tiring of the familiar is fickle inconstancy, which Changeableness names (inconstancy, changeful, ever changing). |
| [brown-eyed](../../seed_queue.json) (queued) | newly placed | none (none) | 433 Brown | opus | Being brown-eyed is having eyes of brown colour, and the Brown head names that colour, including words like auburn and chestnut that are used of people's features. |
| [bullying](../../traits/instructions/bullying.json) | newly placed | none (none) | 887 Blusterer | opus | Head 887 names the bully himself, the one who intimidates and pushes the weaker around, so it fits the whole trait better than ridicule or compulsion alone. |
| [civil-libertarian](../../traits/instructions/civil_libertarian.json) | newly placed | none (none) | 748 Freedom | opus | Freedom names the liberty from state control that a civil-libertarian puts above order and security. |
| [close-knit](../../seed_queue.json) (queued) | newly placed | none (none) | 888 Friendship | opus | Said of people, close-knit means bound by warm, intimate ties, which is the brotherly, fraternal closeness named in Friendship rather than the physical sticking-together of Coherence. |
| [collectivistic](../../traits/instructions/collectivistic.json) | newly placed | none (none) | 910 Philanthropy | opus | Philanthropy's 'public-spirited' and 'humanitarian' name devotion to community and collective well-being, which is the core of collectivism. |
| [conceptual](../../traits/instructions/conceptual.json) | newly placed | none (none) | 450 Intellect (Sonnet: 453 Idea) | opus | Intellect holds 'intellectual' and 'metaphysical', which describe a mind that works with abstract ideas rather than concrete particulars. |
| [cultured/uncultured (tentative, PC13)](../../seed_queue.json) (queued) | newly placed | none (none) | 850 Taste | opus | Being cultured means having refined, cultivated taste, which is what the Taste head names; the courtesy heads are about manners rather than culture. |
| [dark-skinned](../../seed_queue.json) (queued) | newly placed | none (none) | 431 Blackness | opus | Dark-skinned describes a dark complexion, which the Blackness head covers with complexion words such as swarthy, dusky and black-a-vised. |
| [dependable](../../traits/instructions/dependable.json) | newly placed | none (none) | 772 Observance | opus | Observance names the faithful, punctual performance of what one has undertaken, which is following through on commitments. |
| [deterministic](../../seed_queue.json) (queued) | newly placed | none (none) | 611 Predetermination | opus | A deterministic outlook holds that events are fixed beforehand, which matches head 611's predestination and preordination. |
| [Diligence (HEXACO)](../../seed_queue.json) (queued) | newly placed | none (none) | 682 Activity | opus | HEXACO Diligence is the tendency to work hard, and the Activity head is where Roget lists industry, diligence and assiduity. |
| [european](../../seed_queue.json) (queued) | newly placed | none (none) | 188 Inhabitant | opus | Said of a person, 'European' names where someone is native to or lives, and the Inhabitant head holds such adjectives of origin, like 'British' and 'English'. |
| [everyday sadism (Dark Tetrad)](../../seed_queue.json) (queued) | newly placed | none (none) | 907 Malevolence | opus | Everyday sadism is taking pleasure in others' suffering and wishing harm on them, which is the ill-will and cruelty named by Malevolence. |
| [extraverted (MBTI)](../../seed_queue.json) (queued) | newly placed | none (none) | 892 Sociality | opus | Extraversion, said of a person, is chiefly an outgoing, sociable disposition, which is what the Sociality head names (sociable, companionable). |
| [fair-skinned](../../seed_queue.json) (queued) | newly placed | none (none) | 430 Whiteness | opus | Fair skin means a light, whitish complexion, and the Whiteness head covers that quality, while Achromatism leans toward sickly pallor. |
| [forthright](../../traits/instructions/forthright.json) | newly placed | none (none) | 543 Veracity | opus | Saying the honest verdict out loud is candour and frankness, which Veracity names; Bluntness is about physical shape, not speech. |
| [hands-off](../../traits/instructions/hands_off.json) | newly placed | none (none) | 681 Inaction | opus | Handing work over and staying out of it is noninterference, a word listed under Inaction, which fits better than mere carelessness (Neglect). |
| [hands-on](../../traits/instructions/hands_on.json) | newly placed | none (none) | 693 Direction | opus | Hands-on management means overseeing and guiding work you have handed over, which is the management and guidance named by Direction. |
| [happily-partnered](../../traits/instructions/happily_partnered.json) | newly placed | none (none) | 831 Content | opus | The trait is at heart contentment with what one has, here one's partner, which is what Content names; Marriage only covers the wedded state, not being glad of it. |
| [heavyset](../../seed_queue.json) (queued) | newly placed | none (none) | 192 Size | opus | Heavyset means a person of stout, bulky, thickset build, which belongs to the Size head with its words for bulk and corpulence (stout, burly, thickset), not to physical weight as such. |
| [high-context (Hall)](../../traits/instructions/high_context_hall.json) | newly placed | none (none) | 526 Latency. Implication | opus | High-context communication leaves meaning implied and unspoken, which is what Latency/Implication names: implied, tacit, understood meaning. |
| [highbrow](../../traits/instructions/highbrow.json) | newly placed | none (none) | 850 Taste | opus | Highbrow means preferring refined, cultivated art and entertainment, which is what Taste names with 'refined taste' and 'cultivated taste'. |
| [homeowner](../../traits/instructions/homeowner.json) | newly placed | none (none) | 779 Possessor (Sonnet: 780 Property) | opus | A homeowner is first of all the owner and occupier of a house, which is what the Possessor head names (holder, occupier, and proprietor in the full entry). |
| [Humanism (Light Triad)](../../seed_queue.json) (queued) | newly placed | none (none) | 910 Philanthropy | opus | Light Triad humanism means valuing the dignity and worth of every person, which matches the humanity and universal benevolence of Philanthropy. |
| [humanistic](../../traits/instructions/humanistic.json) | newly placed | none (none) | 910 Philanthropy | opus | Philanthropy names humanitarian concern for human welfare and the public good, which matches prioritizing human values and community well-being. |
| [humorous/serious (tentative, PC10)](../../seed_queue.json) (queued) | newly placed | none (none) | 842 Wit | opus | The trait is a humor-versus-seriousness dimension, and head 842 (Wit) names the quality of humor, with words like humor, sense of humor and jocular, as a quality of a person. |
| [hypochondriac](../../seed_queue.json) (queued) | newly placed | none (none) | 504 Madman | opus | The Madman head lists 'hypochondriac' beside monomaniac and kleptomaniac as a person with a morbid mental fixation, which matches someone obsessively convinced they are ill. |
| [iconodule](../../seed_queue.json) (queued) | newly placed | none (none) | 991 Idolatry | opus | An iconodule venerates sacred images, and the Idolatry head, covering image-worship, is the nearest home for that quality. |
| [incrementalist](../../traits/instructions/incrementalist.json) | newly placed | none (none) | 658 Improvement | opus | The trait is at heart a cautious reformer who seeks gradual betterment, and the Improvement head, with its amelioration, betterment and progressive words, covers that quality closely. |
| [indeterminist](../../seed_queue.json) (queued) | newly placed | none (none) | 156 Chance | opus | An indeterminist holds that events are not fully fixed by causes, which is the causeless indetermination named in Chance under Causation. |
| [indigenous american](../../seed_queue.json) (queued) | newly placed | none (none) | 188 Inhabitant | opus | Inhabitant covers native, autochthonous dwellers of a land and nationality words like 'British', so it names being indigenous to America in the same sense. |
| [indigenous australian](../../seed_queue.json) (queued) | newly placed | none (none) | 188 Inhabitant | opus | Being Indigenous Australian means being a native, autochthonous inhabitant of a land, which is what the Inhabitant head's words 'indigenous', 'native' and 'autochthonous' name, in that same sense. |
| [individualistic](../../traits/instructions/individualistic.json) | newly placed | none (none) | 20 Nonimitation (Sonnet: 79 Speciality) | opus | Nonimitation names originality and not copying others, which is very close to the individualist's unique expression over conformity, while Speciality and Unity use 'individual' only in the abstract sense of particularity or number. |
| [interventionist](../../seed_queue.json) (queued) | newly placed | none (none) | 724 Mediation | opus | An interventionist favours stepping into others' affairs, and the Mediation head lists exactly 'intervention', 'interference' and 'intermeddling'. |
| [introverted (MBTI)](../../seed_queue.json) (queued) | newly placed | none (none) | 893 Seclusion. Exclusion | opus | Introversion, a preference for solitude and withdrawal from social contact, matches Seclusion's sense of being retired, private and keeping out of the world. |
| [jaded](../../traits/instructions/jaded.json) | newly placed | none (none) | 869 Satiety | opus | Satiety holds 'blase', 'used up' and 'sick of', which name the jaded state of being left cold by having had too much of everything. |
| [job-hopper](../../seed_queue.json) (queued) | newly placed | none (none) | 149 Changeableness | opus | Changeableness names the inconstant, restless habit of shifting that job-hopping shows, applied here to employers. |
| [job-hopping](../../traits/instructions/job_hopping.json) | newly placed | none (none) | 149 Changeableness | opus | Changing employers again and again is a form of inconstancy, which Changeableness names, while Leap only shares the word 'hop' in a physical sense. |
| [Kantian](../../seed_queue.json) (queued) | newly placed | none (none) | 926 Duty | opus | Said of a person, Kantian chiefly means holding a duty-based (deontological) ethics, which matches the Duty head's sense of moral obligation and imperative. |
| [left-brained](../../seed_queue.json) (queued) | newly placed | none (none) | 476 Reasoning | opus | Said of a person, "left-brained" means analytical and logical, which is what Reasoning names; Sinistrality only shares the word "left" in its spatial sense. |
| [libertarian](../../seed_queue.json) (queued) | newly placed | none (none) | 748 Freedom | opus | A libertarian is centrally an advocate of individual liberty and independence, the quality the Freedom head names; Liberality and Libertine share only spelling. |
| [long-term oriented](../../traits/instructions/long_term_oriented.json) | newly placed | none (none) | 604a Perseverance | opus | Sticking with slow projects year after year without cashing in early is steadfast persistence, which Perseverance names; Economy covers only the saving part and Diuturnity is about duration itself, not a person's quality. |
| [low-context (Hall)](../../traits/instructions/low_context_hall.json) | newly placed | none (none) | 525 Manifestation (Sonnet: 576 Plainness) | opus | Low-context communication makes meaning explicit and stated outright, which is the plain speaking and expressness of Manifestation, the counterpart of Latency's implied meaning. |
| [lowbrow](../../traits/instructions/lowbrow.json) | newly placed | none (none) | 851 Vulgarity | opus | Lowbrow tastes for the popular, the easy and the broad over the refined fall under Vulgarity's 'in bad taste, unrefined', the lack of cultivated taste. Commonalty is about social rank, and Lowness is about physical height. |
| [lurker](../../traits/instructions/lurker.json) | newly placed | none (none) | 444 Spectator | opus | A lurker reads everything but never takes part, which is what a looker-on or onlooker in Spectator does, whereas 'lurking' in Latency means hidden meaning, not a person. |
| [Machiavellianism (Dark Tetrad)](../../seed_queue.json) (queued) | newly placed | none (none) | 702 Cunning | opus | Machiavellianism is scheming, manipulative craftiness, which is the quality named by the Cunning head (crafty, artful, subtle). |
| [media-trusting](../../traits/instructions/media_trusting.json) | newly placed | none (none) | 484 Belief | opus | Taking reports at their word and treating them as fact is giving them credence, which is the Belief head; the description does not make it gullibility. |
| [micromanaging](../../traits/instructions/micromanaging.json) | newly placed | none (none) | 693 Direction | opus | Micromanaging is an overbearing way of directing others' work, which Direction's words name (management, regulation, bossism). |
| [modernist](../../seed_queue.json) (queued) | newly placed | none (none) | 123 Newness | opus | A modernist is someone devoted to modern ideas and styles, and Newness names that quality of being modern and novel. |
| [monochronic (Hall)](../../traits/instructions/monochronic_hall.json) | newly placed | none (none) | 132a Punctuality | opus | Punctuality, being prompt and keeping to time, is the head closest to the monochronic habit of following schedules and the clock. |
| [monodisciplinary](../../seed_queue.json) (queued) | newly placed | none (none) | 79 Speciality (Sonnet: 87 Unity) | opus | Being monodisciplinary means confining oneself to one special field, which matches the special, particular focus named by Speciality. |
| [narcissism (Dark Tetrad)](../../seed_queue.json) (queued) | newly placed | none (none) | 880 Vanity | opus | Narcissism's core is grandiose self-admiration and conceit, which is exactly what the Vanity head names. |
| [news-avoidant](../../traits/instructions/news_avoidant.json) | newly placed | none (none) | 623 Avoidance | opus | The trait is a deliberate refraining from the news, which is the quality the Avoidance head names (avoiding, abstention, refraining), while the News head shares only the topic. |
| [nigerian](../../seed_queue.json) (queued) | newly placed | none (none) | 188 Inhabitant | opus | Nigerian names a nationality, and the Inhabitant head covers belonging to a place by birth or residence, alongside adjectives such as native, British and English. |
| [non-contemplative](../../seed_queue.json) (queued) | newly placed | none (none) | 452 Incogitancy | opus | Non-contemplative means not given to reflection or thought, which matches Incogitancy's unthinking, unintellectual, thoughtless, the opposite of Thought. |
| [noncommittal](../../traits/instructions/noncommittal.json) | newly placed | none (none) | 623 Avoidance | opus | Avoidance covers abstention, neutrality and evasiveness, which is declining to commit to a position; Absence of Choice is about having no preference rather than withholding one. |
| [nurturing](../../traits/instructions/nurturing.json) | newly placed | none (none) | 906 Benevolence | opus | Nurturing is a warm, kindly disposition to care for and support others' well-being, which Benevolence names; 459 'Care' means heedfulness rather than caring for someone. |
| [paranoid](../../traits/instructions/paranoid.json) | newly placed | none (none) | 485 Unbelief. Doubt | opus | Paranoia is at heart excessive distrust and suspicion, which the Unbelief/Doubt head names with 'distrustful' and 'skeptical'; Jealousy's suspicion concerns rivalry and Insanity is only the clinical topic. |
| [paternalistic](../../traits/instructions/paternalistic.json) | newly placed | none (none) | 693 Direction (Sonnet: 737 Authority) | opus | Paternalism is steering and managing other people's conduct for them, which matches Direction's guidance, management and bossism; Paternity only shares the spelling. |
| [performative](../../traits/instructions/performative.json) | newly placed | none (none) | 855 Affectation | opus | Affectation's 'acting a part', 'stagy' and 'affected' name the putting on of a manner to make an impression, which is the trait described; Drama shares only the theatrical topic. |
| [person-organization fit](../../seed_queue.json) (queued) | newly placed | none (none) | 23 Agreement | opus | Person-organization fit is the congruence or suitability between a person and an organization, which is exactly the accord and suiting that Agreement names. |
| [polyandrous](../../seed_queue.json) (queued) | newly placed | none (none) | 903 Marriage | opus | Polyandry is a form of marriage, and the Marriage head covers kinds of wedlock such as polygamy and polyandry. |
| [polygynous](../../seed_queue.json) (queued) | newly placed | none (none) | 903 Marriage | opus | Polygyny, having several wives, is a form of marriage, and the Marriage head covers polygamy among its forms of wedlock. |
| [pragmatic](../../traits/instructions/pragmatic.json) | newly placed | none (none) | 646 Expedience | opus | Expedience names the habit of choosing what is workable and advisable over what is ideal, which is the core of pragmatism. |
| [predictable](../../seed_queue.json) (queued) | newly placed | none (none) | 871 Expectance | opus | Expectance holds 'expected', 'foreseen' and 'unsurprising', which describe a person whose behaviour can be foreseen; Prediction is about the act of foretelling, not about being foreseeable. |
| [procrastinating](../../traits/instructions/procrastinating.json) | newly placed | none (none) | 133 Lateness | opus | Lateness holds delay, cunctation and tardiness, the putting off of action until later that procrastination names. |
| [psychopathy (Dark Tetrad)](../../seed_queue.json) (queued) | newly placed | none (none) | 914a Pitilessness | opus | Psychopathy in the Dark Tetrad centres on callous, remorseless lack of empathy, which the ruthless, merciless words of Pitilessness name most closely. |
| [red-headed](../../seed_queue.json) (queued) | newly placed | none (none) | 434 Redness | opus | Red-headed means having red hair, and the Redness head, with words like rufous and ruddy, names that colouring. |
| [reductionist](../../traits/instructions/reductionist.json) | newly placed | none (none) | 49 Decomposition | opus | Breaking complex wholes into their component parts is analysis and dissection, the core of the Decomposition head. |
| [right-brained](../../seed_queue.json) (queued) | newly placed | none (none) | 515 Imagination | opus | Right-brained popularly describes a creative, imaginative thinker, which is the quality the Imagination head names; Dextrality only shares the word 'right'. |
| [risk-averse](../../traits/instructions/risk_averse.json) | newly placed | none (none) | 864 Caution | opus | Avoiding risk and preferring the sure thing is the cautious, wary disposition named by the Caution head. |
| [risk-seeking](../../traits/instructions/risk_seeking.json) | newly placed | none (none) | 863 Rashness | opus | Rashness is the head for a disposition to take risks and court danger without guaranteed outcomes; it also holds venturesome and daring. |
| [rule-bending](../../seed_queue.json) (queued) | newly placed | none (none) | 773 Nonobservance | opus | Nonobservance names evading, omitting and failing to keep rules, which is what bending or skipping regulations comes to. |
| [rule-breaking](../../traits/instructions/rule_breaking.json) | newly placed | none (none) | 773 Nonobservance | opus | Nonobservance names violating, transgressing and evading rules and regulations, which is the core of a rule-breaking disposition. |
| [ruthless while playing](../../traits/instructions/ruthless_while_playing.json) | newly placed | none (none) | 914a Pitilessness | opus | The trait is ruthlessness confined to games and fiction, and Pitilessness names that quality directly ('ruthless', 'merciless'). |
| [science-trusting](../../traits/instructions/science_trusting.json) | newly placed | none (none) | 484 Belief | opus | Taking scientists' word and believing what studies find is giving credence and trust, which is the Belief head; Credulity would add a gullibility the description does not imply. |
| [self-accepting](../../traits/instructions/self_accepting.json) | newly placed | none (none) | 831 Content | opus | Being at peace with one's own conduct, satisfied and at ease with it, is the quality named by Content (contented, satisfied, at ease, complacency). |
| [Self-Consciousness (IPIP-NEO)](../../seed_queue.json) (queued) | newly placed | none (none) | 881 Modesty | opus | Self-consciousness in the IPIP-NEO sense is shyness, social anxiety and embarrassment around others, which matches the diffident, bashful, shy words of Modesty. |
| [self-critical](../../traits/instructions/self_critical.json) | newly placed | none (none) | 868 Fastidiousness | opus | Fastidiousness names the hypercritical, hard-to-please temper that is never satisfied, which is the core of harshly judging one's own work. |
| [self-disciplined](../../traits/instructions/self_disciplined.json) | newly placed | none (none) | 604 Resolution (Sonnet: 953 Temperance) | opus | Self-discipline is will governing impulse to hold to a purpose, which Resolution names along with its self-control and self-denial senses, while Temperance covers only moderation of appetite. |
| [self-starting](../../traits/instructions/self_starting.json) | newly placed | none (none) | 132 Earliness | opus | The description centres on not putting things off and starting well before the deadline, which is the earliness and punctuality of head 132, the counterpart to the procrastination of Lateness. |
| [shame-prone](../../seed_queue.json) (queued) | newly placed | none (none) | 879 Humility (Sonnet: 881 Modesty) | opus | Proneness to shame means readily feeling shame and mortification, and Roget's Humility head (879), as I recall the full entry, covers the 'sense of shame', being abashed and ashamed, rather than mere shyness or actual guilt. |
| [sleep-deprived](../../seed_queue.json) (queued) | newly placed | none (none) | 688 Fatigue | opus | Being sleep-deprived means being tired and drowsy, which is the physical tiredness named by Fatigue (tired, yawning, lassitude). |
| [sloppy](../../traits/instructions/sloppy.json) | newly placed | none (none) | 460 Neglect | opus | Sloppy work, skipping checks and leaving small mistakes, is carelessness, which Neglect's words (careless, negligent, heedless) name directly. |
| [Social Self-Esteem (HEXACO)](../../seed_queue.json) (queued) | newly placed | none (none) | 878 Pride | opus | Social Self-Esteem is a positive regard for one's own worth, which matches the self-respect and dignity in Pride rather than the conceit of Vanity or the merely social Sociality. |
| [socializer (Bartle)](../../traits/instructions/socializer_bartle.json) | newly placed | none (none) | 892 Sociality | opus | A socializer plays for company and conversation, and Sociality's words (sociable, companionable, chatty, social intercourse) name that quality. |
| [status-seeking](../../traits/instructions/status_seeking.json) | newly placed | none (none) | 882 Ostentation | opus | Choosing the car, the address and the friends for what they signal is display meant to impress, which is what Ostentation names; Vanity is self-conceit rather than chasing rank. |
| [stigmatized](../../seed_queue.json) (queued) | newly placed | none (none) | 874 Disrepute | opus | To be stigmatized is to bear a mark of disgrace or bad repute, which matches Disrepute ("disgraced", "discredit", "ill repute"); Blemish holds only the physical sense of a mark. |
| [stressed](../../seed_queue.json) (queued) | newly placed | none (none) | 828 Pain | opus | Being stressed means being under mental strain and worry, which Pain covers with 'mental suffering', 'worried' and 'afflicted'. |
| [strong-stomached](../../traits/instructions/strong_stomached.json) | newly placed | none (none) | 826 Inexcitability | opus | Staying calm and unflinching before revolting sights is imperturbability, which Inexcitability names; the Fetor and Pungency heads only share the topic of offensive things. |
| [technophobic](../../seed_queue.json) (queued) | newly placed | none (none) | 867 Dislike | opus | Technophobia is an aversion to technology, and the Dislike head names that kind of aversion or distaste. |
| [traumatized](../../seed_queue.json) (queued) | newly placed | none (none) | 828 Pain | opus | Being traumatized is lasting mental suffering from a distressing experience, which Pain (mental suffering, afflicted) names closely. |
| [tunnel-visioned](../../traits/instructions/tunnel_visioned.json) | newly placed | none (none) | 481 Misjudgment | opus | Misjudgment covers narrow, one-sided, prejudging thinking that settles on first assumptions and won't revisit them, which is close to tunnel vision. |
| [unchallenging](../../traits/instructions/unchallenging.json) | newly placed | none (none) | 488 Assent | opus | Taking every premise as given without pushing back is acquiescence, which is the quality the Assent head names. |
| [unhappily-partnered](../../traits/instructions/unhappily_partnered.json) | newly placed | none (none) | 832 Discontent | opus | Being sick of one's partner and sure one wouldn't choose them again is dissatisfaction with one's lot, which Discontent names. |
| [universalist](../../seed_queue.json) (queued) | newly placed | none (none) | 910 Philanthropy | opus | Said of a person, a universalist holds a broad, all-embracing concern for humanity, which matches Philanthropy's 'universal benevolence' and 'cosmopolitan' rather than the abstract relation of generality. |
| [unprovocative](../../seed_queue.json) (queued) | newly placed | none (none) | 174 Moderation (Sonnet: 721 Peace) | opus | Being unprovocative means not stirring or irritating others. Moderation's mild, gentle, unirritating sense of tempering what causes excitement fits this best. |
| [vanilla](../../seed_queue.json) (queued) | newly placed | none (none) | 391 Insipidity | opus | Said of a person, 'vanilla' means bland and unexciting, which matches the 'bland, insipid, milk and water' sense of Insipidity. |
| [variety-seeking](../../seed_queue.json) (queued) | newly placed | none (none) | 149 Changeableness | opus | The trait is an inconstant, ever-changing preference that tires of the familiar, which Changeableness names with 'inconstancy' and 'ever changing'; the other heads only share the word 'variety' or the topic of choosing. |
| [Vulnerability (IPIP-NEO)](../../seed_queue.json) (queued) | newly placed | none (none) | 822 Sensibility | opus | IPIP-NEO Vulnerability means being easily overwhelmed by stress, an emotional susceptibility that is closest to the sensitive, impressionable susceptibility of Sensibility, not to Danger's sense of being exposed to peril. |
| [working-class](../../traits/instructions/working_class.json) | newly placed | none (none) | 876 Commonalty | opus | Commonalty names the common people and low social condition, which is the working-class social origin described. |
| [xenophobic](../../seed_queue.json) (queued) | newly placed | none (none) | 867 Dislike (Sonnet: 911 Misanthropy) | opus | Xenophobia is an aversion to foreigners, a specific kind of dislike, which head 867 names, while misanthropy is aversion to mankind in general. |
| [absorption-prone](../../traits/instructions/absorption_prone.json) | unplaced | 449 Disappearance (semantic) | none | opus | None of the listed heads names deep absorption or engrossment, and Oblivion and Absence concern forgetting and physical absence instead. |
| [anthropocentric](../../traits/instructions/anthropocentric.json) | unplaced | 370 Husbandry (semantic) | none | opus | Anthropocentrism is a stance that values humans above other species, and no head names it: Mankind only shares the topic of humans, and Philanthropy names benevolence toward people, not ranking human interests over nature. |
| [anti-immigration](../../traits/instructions/anti_immigration.json) | unplaced | 294 Ingress (rule) | none | opus | Anti-immigration is a modern political stance, and no listed head names it: Ingress, Arrival and Inhabitant only share its topic, and Prohibition names forbidding in general rather than opposing newcomers. |
| [borderline](../../seed_queue.json) (queued) | unplaced | 231 Edge (semantic) | none | opus | Said of a person, 'borderline' points to an unstable personality type, and the listed heads only give spatial edges and boundaries, which share the spelling but not the meaning. |
| [boundary-fuzzy](../../seed_queue.json) (queued) | unplaced | 233 Limit (semantic) | none | opus | The trait means a person who keeps loose personal limits with others, while these heads cover spatial borders, contact, or doubt and none names that quality. |
| [brand-loyal](../../traits/instructions/brand_loyal.json) | unplaced | 743 Obedience (rule) | none | opus | Brand loyalty is a modern consumer buying habit. The 'loyal' heads mean keeping duties or obeying, which is a different sense, and no listed head names a fixed preference for one brand. |
| [calibrated](../../traits/instructions/calibrated.json) | unplaced | 484 Belief (semantic) | none | opus | Calibration means fitting confidence to the evidence, but each listed head names only one pole (certainty, doubt, belief, unbelief) rather than proportioned belief. |
| [capitalist](../../traits/instructions/capitalist.json) | unplaced | 642 Importance (lexical) | none | opus | The trait is a political belief in free markets and private ownership, and no listed head names that stance; Wealth, Property, Barter and Merchant only share its topic. |
| [conventional (Holland)](../../traits/instructions/conventional_holland.json) | unplaced | 769 Compact (lexical) | none | opus | This Holland type bundles an interest in clerical, data-keeping office work under set rules, and no listed head names that whole vocational bundle; Compact's 'conventional' is only a spelling match. |
| [course-correcting](../../traits/instructions/course_correcting.json) | unplaced | 628 Mid-course (semantic) | none | opus | No listed head names deliberately rethinking and changing a failing approach: Changeableness means fickleness, Reversion means going back, and Correction and the two Course heads match only by spelling. |
| [deconstructionist](../../traits/instructions/deconstructionist.json) | unplaced | 165 Destroyer (semantic) | none | opus | Deconstruction is a specific critical method of exposing hidden contradictions in assumptions; Decomposition covers analysis, Destroyer covers iconoclasm, and Interpretation covers explaining meaning, but none names that whole practice. |
| [dog-person](../../traits/instructions/dog_person.json) | unplaced | 899 Favorite (semantic) | none (Sonnet: 897 Love) | opus | Being a dog-person is a fondness for one kind of animal, and no listed head names that preference: Love and Desire are general, Husbandry covers keeping animals rather than loving dogs, and Favorite names the pet, not the person. |
| [emotionally-articulate](../../traits/instructions/emotionally_articulate.json) | unplaced | 821 Feeling (semantic) | none | opus | The trait joins precise awareness of one's own feelings with putting them into exact words, and no listed head names that whole: Feeling covers sensibility, Knowledge covers awareness in general, Intelligibility covers clear expression in general, and Voice holds 'articulate' only in the sense of distinct speech sounds. |
| [enterprising (Holland)](../../traits/instructions/enterprising_holland.json) | unplaced | 625 Business (semantic) | none | opus | The Holland enterprising type bundles selling, managing, leading, advising and public speaking, and no listed head names that whole bundle: Business, Merchant and Conduct each cover only one part. |
| [exclusivist](../../traits/instructions/exclusivist.json) | unplaced | 55 Exclusion (semantic) | none (Sonnet: 983a Orthodoxy) | opus | Exclusivism is a stance of treating one view as right and every rival as error, but no listed head names it: 55 and 893 share the spelling of 'exclusive' in other senses, and Orthodoxy means holding the sound doctrine, not dismissing rivals. |
| [existentialist](../../traits/instructions/existentialist.json) | unplaced | 6 Extrinsicality (semantic) | none | opus | The trait is a philosophical stance on freedom and self-made meaning, and none of these heads names it: Existence only matches the spelling, and the others share only loose themes. |
| [flow-prone](../../seed_queue.json) (queued) | unplaced | 348 River (semantic) | none (Sonnet: 333 Fluidity) | opus | Said of a person, flow-prone means readily entering absorbed 'flow' states, but the listed heads cover only the physical flow of water and liquids, which merely share the word, not the meaning. |
| [growth-minded](../../traits/instructions/growth_minded.json) | unplaced | 602 Willingness (rule) | none | opus | The trait is a modern belief that ability grows through effort; Improvement, Learning and Perseverance each touch only part of it, and no head names the belief itself. |
| [insecure](../../traits/instructions/insecure.json) | unplaced | 665 Danger (lexical) | none | opus | None of the listed heads names self-doubt or low self-worth: 665 has 'insecurity' only in the sense of peril, 475 and 485 cover doubt about facts or beliefs, and 34 is inferiority of quantity. |
| [intrinsically-motivated](../../traits/instructions/intrinsically_motivated.json) | unplaced | 5 Intrinsicality (semantic) | none | opus | None of these heads names doing work for its own sake: Intrinsicality means inherent essence, a different sense of the word, and Reward and Action only share the topic. |
| [languishing](../../traits/instructions/languishing.json) | unplaced | 659 Deterioration (semantic) | none | opus | The trait is a state of hollow, aimless stagnation, and none of these heads names it: Weakness covers languor only as bodily debility, and Deterioration is about decline. |
| [Leo](../../traits/instructions/leo.json) | unplaced | 878 Pride (semantic) | none | opus | Leo is a star-sign bundle of royal bearing, generosity, love of the limelight and vanity, and no single listed head names the whole bundle, only its parts. |
| [Liberalism (IPIP-NEO)](../../seed_queue.json) (queued) | unplaced | 748 Freedom (rule) | none | opus | The IPIP-NEO facet means readiness to challenge authority, convention and tradition. Head 942 has 'liberalism' only in the sense of generosity, and Politics names political activity in general, not this outlook. |
| [literate](../../traits/instructions/literate.json) | unplaced | 561 Letter (semantic) | none | opus | Literacy is the ability to read and write, but Writing names the act and its products, Letter names alphabet characters, and Learning names scholarship, so none names the basic ability itself. |
| [maximizing](../../traits/instructions/maximizing.json) | unplaced | 496 Maxim (semantic) | none (Sonnet: 650 Perfection) | opus | Perfection names the state of being flawless, not a habit of comparing every option and second-guessing choices, and no listed head names that decision style. |
| [metaphysical libertarian](../../traits/instructions/metaphysical_libertarian.json) | unplaced | 748 Freedom (semantic) | none | opus | The trait is the doctrine of free will, which belongs under Will; Freedom here means social and political liberty, and Choice means picking among options, so neither names the belief that choices are uncaused. |
| [middle eastern](../../seed_queue.json) (queued) | unplaced | 236 Laterality (rule) | none | opus | Middle eastern names a regional or ethnic origin, and no listed head covers it; 'Middle' and 'Mean' only share the word 'middle' in a positional sense. |
| [only child](../../traits/instructions/only_child.json) | unplaced | 129 Infant (rule) | none | opus | Being an only child is a family circumstance; Unity, Posterity, Infant and Seclusion each touch one part of it (oneness, offspring, childhood, privacy), but none names having no siblings. |
| [open_ended](../../seed_queue.json) (queued) | unplaced | 260 Opening (semantic) | none | opus | Open-endedness, being unbounded or open to many possibilities, is not named by any listed head: Opening means physical holes, and Freedom means independence and liberty. |
| [open-minded](../../traits/instructions/open_minded.json) | unplaced | 602 Willingness (rule) | none | opus | Open-mindedness is fair, unbiased judgment, but no listed head names it: Misjudgment names its opposite (prejudice), and Willingness only shares the spelling of "minded" in another sense. |
| [opposite of existentialist (unsettled)](../../seed_queue.json) (queued) | unplaced | 6 Extrinsicality (semantic) | none | opus | The label is a vague negation of a philosophical stance, and the Existence heads only share its topic without naming any personal quality. |
| [passive-aggressive](../../traits/instructions/passive_aggressive.json) | unplaced | 716 Attack (rule) | none | opus | None of these heads names indirect, veiled hostility: Submission and Attack only match parts of the label, and Discord is open disagreement rather than covert expression. |
| [perceived organizational support](../../seed_queue.json) (queued) | unplaced | 215 Support (rule) | none (Sonnet: 707 Aid) | opus | The trait is an employee's belief that their employer values them and cares about their wellbeing, a modern workplace perception that no listed head names; Aid and Support only share words or topic with it. |
| [philistine](../../traits/instructions/philistine.json) | unplaced | 491 Ignorance (lexical) | none | opus | Philistinism is a lack of artistic taste, which belongs under vulgarity or taste, and that head is not listed; plain ignorance or the heads on the arts themselves do not name it. |
| [Pisces](../../traits/instructions/pisces.json) | unplaced | 821 Feeling (semantic) | none | opus | Pisces bundles dreaminess, empathy, mood-absorption, vulnerability and escapism, and no listed head names that whole bundle: Sensibility covers only the sensitivity and Imagination only the fantasy. |
| [plain-looking](../../seed_queue.json) (queued) | unplaced | 576 Plainness (semantic) | none | opus | Plain-looking means having an unattractive face, which belongs under ugliness, and no such head is listed; the listed plainness and simplicity heads mean freedom from ornament, flat land, or plain speech. |
| [present-focused](../../seed_queue.json) (queued) | unplaced | 74 Focus (semantic) | none (Sonnet: 118 The Present Time) | opus | Being present-focused is a personal orientation toward the now; 'The Present Time' only names the time itself, a shared topic, and 'Attention' means general attentiveness, not a focus on the present. |
| [pro-immigration](../../traits/instructions/pro_immigration.json) | unplaced | 294 Ingress (rule) | none (Sonnet: 296 Reception) | opus | The trait is a political attitude in favour of admitting immigrants, but the listed heads only name physical admission, entry or residence and none names that stance. |
| [quality time](../../traits/instructions/quality_time.json) | unplaced | 106 Time (rule) | none (Sonnet: 457 Attention) | opus | This love language is a preference for receiving undivided attention as a sign of love. No head names that whole bundle: Attention covers the mental act of heeding, and Love covers affection itself. |
| [realistic (Holland)](../../traits/instructions/realistic_holland.json) | unplaced | 494 Truth (lexical) | none | opus | The Holland 'realistic' type bundles manual, mechanical, building and outdoor work, and no listed head names that whole bundle: Agriculture, Instrument and Workshop each cover only one part, and Truth matches only the spelling of 'realistic'. |
| [regionalist](../../traits/instructions/regionalist.json) | unplaced | 181 Region (semantic) | none | opus | Head 181 holds 'regional' and 'parochial' only as words about space, not a loyalty to one's region, and Selfishness concerns the self rather than one's region, so no listed head names this attitude. |
| [resourceful](../../traits/instructions/resourceful.json) | unplaced | 632 Means (semantic) | none | opus | Resourcefulness is the knack of improvising, which belongs to skill or contrivance; 'Means' only lists the resources themselves, and 'Economy' and 'Expedience' name frugality and advisability. |
| [rootless](../../traits/instructions/rootless.json) | unplaced | 776 Loss (semantic) | none (Sonnet: 185 Displacement) | opus | The trait is cultural detachment from one's heritage; Displacement concerns physical homelessness and Irrelation abstract unconnectedness, so neither names it. |
| [Slytherin](../../traits/instructions/slytherin.json) | unplaced | 702 Cunning (semantic) | none | opus | Slytherin bundles ambition, cunning, pride and guarded reputation, and no listed head names that whole bundle; Cunning and Pride each cover only one part. |
| [social desirability](../../seed_queue.json) (queued) | unplaced | 646 Expedience (rule) | none (Sonnet: 852 Fashion) | opus | Social desirability, the urge to present oneself in a socially approved light, is not named by any head. Expedience holds 'desirability' only in the sense of advisability, and Fashion and Sociality only share the social topic. |
| [sociopathic](../../traits/instructions/sociopathic.json) | unplaced | 911 Misanthropy (semantic) | none | opus | Sociopathy is a bundle of callous manipulation, remorselessness and disregard for others' rights. None of the listed heads names that whole. Misanthropy means hatred of mankind, and selfishness and lawlessness each cover only one part. |
| [solemn](../../traits/instructions/solemn.json) | unplaced | 403 Silence (rule) | none | opus | None of these heads names a grave, serious temperament: 958 is abstinence from drink, 319 is physical weight, and 990 uses 'solemn' only of religious worship. |
| [southern hemisphere](../../traits/instructions/southern_hemisphere.json) | unplaced | 181 Region (rule) | none (Sonnet: 188 Inhabitant) | opus | No listed head names coming from the southern half of the globe: Inhabitant and Region only share the topic of place and origin, and 'antipodal' in Contraposition means opposite, not southern. |
| [symbolic-manipulation / embodied-care (tentative, PC16)](../../seed_queue.json) (queued) | unplaced | 459 Care (rule) | none | opus | The label names a bipolar statistical component that sets abstract symbol-handling against bodily caregiving, and no single head names that whole contrast; 'Care' (heedfulness) and 'Touch' match only one pole, and only by the word or topic. |
| [Taurus](../../traits/instructions/taurus.json) | unplaced | 327 Tenacity (semantic) | none | opus | Taurus bundles steadiness, dependability, love of comfort, possessiveness and stubbornness, and no listed head names that whole bundle; Obstinacy covers only the stubbornness. |
| [technomystical](../../seed_queue.json) (queued) | unplaced | 992 Sorcery (semantic) | none | opus | The trait fuses technology with spirituality, and none of these heads names that pairing; they cover only deity, magic, or theology in general. |
| [traditional (Inglehart-Welzel)](../../traits/instructions/traditional_inglehart_welzel.json) | unplaced | 594 Description (lexical) | none | opus | The trait bundles religiosity, family values, deference to authority and national pride, and no listed head names that whole bundle: Piety covers only the religious part, and Oldness concerns the age of things, not a person's values. |
| [transcendentally-oriented](../../seed_queue.json) (queued) | unplaced | 303 Transcursion (semantic) | none | opus | The trait means a spiritual orientation toward what lies beyond ordinary experience, but no listed head names that personal quality: Transcursion uses 'transcendence' only in a spatial sense, and Deity describes God rather than a person's outlook. |
| [unhelpful](../../traits/instructions/unhelpful.json) | unplaced | 645 Inutility (semantic) | none (Sonnet: 706 Hindrance) | opus | The trait is an unwilling, uncaring refusal to help others, while Inutility names uselessness and Hindrance names active obstruction, so neither names this disposition. |
| [verbal-thinker](../../seed_queue.json) (queued) | unplaced | 451 Thought (semantic) | none | opus | A verbal thinker thinks in words rather than images, and no listed head names that style; Thought and Sage cover thinking or thinkers only in general. |
| [vulnerable-narcissistic](../../traits/instructions/vulnerable_narcissistic.json) | unplaced | 880 Vanity (semantic) | none | opus | Vulnerable narcissism bundles hidden grandiosity, entitlement, touchiness, envy and withdrawal; vanity, envy and seclusion each name only one part, and no head names the whole. |

## Coverage map and harvest

The coverage map and the full-size harvest dry run were rerun once with both checks applied; the numbers,
beside each check alone, are in [head_scope_readout.md](./head_scope_readout.md), section "Coverage map and
harvest (both checks)".

## Not done

- Two corpus renames are pending in another checkout (`borderline` to `borderline_personality_disorder`,
  `fear_prone` to `punishment_fearing`).  They are not in this worktree, so they were checked under their
  old names; no key was remapped.  They will be placed again in a small later run.  (Done: see "Update
  after chunk 5" below.)
- [map_spotcheck.md](./map_spotcheck.md) is the map run's spot check and was not regenerated; it shows
  the placements before this check.


## Update after chunk 5 (2026-10-08)

Chunk 5 of the corpus expansion (commits 7e10c23 and 467ea35) added 90 trait files.  86 of them were
seed-queue labels when the placements above were made, and all 86 had been placed from the bare label (85)
or from a queue draft (1, [technomystical](../../traits/instructions/technomystical.json)), because their descriptions were
written later.  Four of the 90 are renames, each new file carrying `renamed_from`; and the queue entry
[distressed](../../seed_queue.json) was not adopted (status `not_adopted`, no file).  This section brings
[label_heads.json](./label_heads.json) up to date.  Terms used here: to **re-place** a label is to run its
two routes (lexical and semantic) again; the **check** is the placement check described above; a
**parked** queue label is one whose status is `not_adopted`, `superseded` or `exists`, which the coverage
map lists beside a head but does not count.

### How the labels to place again were found

The file did not record the text each label had been placed from.  So each label's text was recomputed as
the map builds it (`label: description` for a corpus trait; the queue entry's description, else its draft,
else the bare label) and looked up in the embedding cache ([data/candidates/cache/embeddings/](../cache/embeddings/),
keyed by a hash of the text).  A miss means the text changed: 87 labels.  A hit was confirmed by recomputing the
label's semantic top five heads from the cached vector and comparing them with the heads and cosines
recorded in the file: identical for all 1,061 hits, so the cache entries were the ones the map had used.
Cross-check: the texts the 87 labels had at the time (rebuilt from the queue at commit 35ecd84) were 86
bare labels and one draft, and all 87 are in the cache.

The update ran twice: the second time after removing from the file a misleading cost total (it left out
the first check's $0.22 sample run).  By then the first run had cached the 87 new texts, so they were
cache hits, and the cosine comparison flagged the same 87 as changed; the file's update record therefore
says `semantic_differs` where the first run found `cache_miss`.  The same set either way.

From now on every entry records `placed_text_sha256`, the hash of the text it was placed from, and the
next update compares that directly.  The commands (code in
[mapping.py](../../../assistant_axis/gapgen/generators/roget/mapping.py),
[placement.py](../../../assistant_axis/gapgen/generators/roget/placement.py) and
[roget_generate.py](../../../data_analysis/gap_generation/roget_generate.py)):

- `roget_generate.py map --update`: drops the keys that are no corpus trait and no queue trait entry, adds
  the labels that have no entry, re-places the labels whose text changed, and leaves every other entry as
  it is, its check record (`llm`) included; only its record fields (label, source, queue status, partner)
  are refreshed and its text hash added.  A re-placed entry keeps its old placement and old check record
  under `previous_placement`.  An old stem is never remapped onto its new name.  Each update is appended
  to the file's `map_updates`.  A full `map` now refuses to overwrite a file that holds check records
  unless given `--force`.
- `roget_generate.py place-check --unchecked-only --resume`: checks only the labels that carry no check
  record (after an update, the re-placed ones whose route is not `agree`).  `--resume` now reuses an earlier
  answer only when the whole prompt is byte-identical (before, the same rubric and model were enough, which
  would have reused an answer given for a label's old description).  The file's `placement_check` block
  now holds totals over the labels plus each run's own record under `runs`.

### Counts

| | labels |
|---|---|
| entries before (880 corpus traits, 272 queue labels) | 1,152 |
| dropped: no trait file and no queue trait entry (the four old stems of the renames) | 4 |
| added: the four renamed stems | 4 |
| text changed: 86 chunk-5 traits and [distressed](../../seed_queue.json) | 87 |
| re-placed (added and changed) | 91 |
| of which the two routes agree (route `agree`, not sent to the check) | 18 |
| sent to the check | 73 |
| Opus asked (Sonnet's head differed from the rules' head) | 43 |
| check outcomes: unchanged / moved / newly placed / unplaced | 42 / 6 / 20 / 5 |
| kept as they were (placement and check record untouched) | 1,061 |
| record fields refreshed on a kept entry ([vanilla](../../seed_queue.json) (queued): its partner now has a file) | 1 |
| entries after | 1,152 |

Against the placement each changed label had before (87): the same head for 62 (26 of them had no head
before and have none now), a different one for 25: 17 placed where they had no head, 4 left without one,
4 moved.  Routes in the whole file now: `agree` 565, `llm` 213, `semantic` 116, `none` 252, `rule` 4,
`lexical` 2.  686 of the 880 corpus traits have a primary head.

### The four renames

| new file | old stem (no file now) | old stem's head (route) | rules now (route) | after the check | decided by |
|---|---|---|---|---|---|
| [borderline personality disorder](../../traits/instructions/borderline_personality_disorder.json) | `borderline` | none (the first check had taken it off 231 Edge) | 59 Disorder (rule) | none | Opus (Sonnet agreed) |
| [punishment-fearing](../../traits/instructions/punishment_fearing.json) | `fear_prone` | 860 Fear (semantic, kept by the first check) | 860 Fear (rule) | 860 Fear | Opus (Sonnet: none) |
| [OCD](../../traits/instructions/ocd.json) | `compulsive` | 744 Compulsion (agree, never checked) | none | none | Opus (Sonnet: 503 Insanity) |
| [Neopagan](../../traits/instructions/neopagan.json) | `pagan` | 984 Heterodoxy (lexical, kept by the first check) | none | 991 Idolatry | Opus (Sonnet agreed) |

Reasons: [borderline personality disorder](../../traits/instructions/borderline_personality_disorder.json), "no listed head
names that whole bundle ... Disorder and Derangement only share the word 'disorder' in another sense";
[OCD](../../traits/instructions/ocd.json), "Compulsion here means coercion by others, and Disorder means lack of arrangement";
[punishment-fearing](../../traits/instructions/punishment_fearing.json), "at heart a fear (of punishment) that restrains
conduct"; [Neopagan](../../traits/instructions/neopagan.json), "pagan worship of gods other than the Christian God".  So
`compulsive`'s head, 744 Compulsion, is empty now, and its words go to the harvest.

### distressed

[distressed](../../seed_queue.json) was not dropped.  The file has always held every queue trait entry
without a file, parked ones included (111 `not_adopted` labels were in it before chunk 5), and the coverage
map lists parked labels beside their head without counting them.  So `distressed` stays, as one more
parked label: its status now reads `not_adopted`, and it no longer counts toward 828 Pain, which
[stressed](../../traits/instructions/stressed.json) now covers.  Its text had changed (a description was written for chunk 5),
so it was re-placed: the rules chose 859 Hopelessness, the check (Opus) 828 Pain, its head before.  If
parked labels should leave the file altogether, that is a change to `mapping.load_labels` (126 entries:
112 `not_adopted`, 13 `superseded`, 1 `exists`), not part of this update.

### Coverage map and harvest

`roget_generate.py coverage` rewrote [roget_coverage.json](./roget_coverage.json) and
[roget_coverage.md](./roget_coverage.md); the harvest was a full-size dry run
(`roget_generate.py --dry-run harvest --run-id 2026-10-08-chunk5-full-dryrun`, nothing written), both with
the head-scope ratings and the placements applied.  "Before" is the files as committed before this update
(the last column of the table in [head_scope_readout.md](./head_scope_readout.md)).

| | before | after |
|---|---|---|
| heads in scope (dispositional 576, Classes I-III 99) | 675 | 675 |
| not character (rated 0; left out of the rows below) | 188 | 188 |
| covered | 263 | **272** |
| partly covered | 53 | 52 |
| uncovered (of which a queued label only) | 171 (26) | **163 (16)** |
| gap classes: pair_completion / pair_empty / singleton_empty / queued_only | 21 / 29 / 95 / 26 | 24 / 27 / 96 / 16 |
| opposed pairs: both poles / one pole / neither covered | 68 / 49 / 34 | 70 / 51 / 30 |
| harvest: gap heads selected / skipped as not character / giving words | 301 / 130 / 102 | 288 / 125 / 94 |
| harvest: words (distinct) | 581 (538) | **534 (498)** |
| harvest: words dropped with not-character heads | 441 | 410 |
| downstream estimate: M1 / M3 if half pass | $2.32 / $5.23 | $2.14 / $4.81 |

Most of the change is the chunk-5 traits turning from queue labels into corpus traits, so that their heads
count as covered.  Ten heads left the state "a queued label only": six are now covered or partly covered
by chunk-5 traits, and four lost their queued label to a re-placement (124 Oldness, 361 Killing,
744 Compulsion, 985 Judeo-Christian Revelation).  The Class I-III part of the scope changed by one head
each way: 29 Mean came in (through [middle-class](../../traits/instructions/middle_class.json)) and
361 Killing went out (its trigger, [suicidal](../../traits/instructions/suicidal.json), now has no head);
the head-scope check rated 29 Mean once (one Haiku 5.5 call, [head_scope.json](./head_scope.json)): 1, a
mixed head.

The 16 heads whose state changed:

| head | before | after | why |
|---|---|---|---|
| 29 Mean | out of scope | empty | brought in by [middle-class](../../traits/instructions/middle_class.json)'s lexical hit; rated 1 |
| 124 Oldness | queued | empty | [New Age](../../traits/instructions/new_age.json) was queued there; now on 992 Sorcery |
| 361 Killing | queued | out of scope | [suicidal](../../traits/instructions/suicidal.json) was queued there; now no head |
| 503 Insanity | queued | covered | [delusional](../../traits/instructions/delusional.json) |
| 605 Irresolution | partly | covered | [ambivalent](../../traits/instructions/ambivalent.json) |
| 609a Absence of Choice | queued | covered | [neuter](../../traits/instructions/neuter.json) |
| 736 Mediocrity | partly | covered | [middle-class](../../traits/instructions/middle_class.json) |
| 744 Compulsion | queued | empty | `compulsive` was queued there; its successor [OCD](../../traits/instructions/ocd.json) has no head |
| 751 Restraint | queued | covered | [trapped-in-job](../../traits/instructions/trapped_in_job.json) |
| 812 Price | empty | partly | [mercenary](../../traits/instructions/mercenary.json) as a secondary head |
| 828 Pain | queued | covered | [stressed](../../traits/instructions/stressed.json) |
| 898 Hate | partly | covered | [xenophobic](../../traits/instructions/xenophobic.json) (867 Dislike when it had no description) |
| 936 Detractor | queued | covered | [detractor](../../traits/instructions/detractor.json) |
| 985 Judeo-Christian Revelation | queued | empty | [Jewish](../../traits/instructions/jewish.json) was queued there; now no head |
| 991 Idolatry | empty | covered | [Neopagan](../../traits/instructions/neopagan.json) |
| 995 Churchdom | queued | partly | [Christian](../../traits/instructions/christian.json): primary 983a Orthodoxy, 995 a secondary head |

One thing to look at: Roget's 1911 religious heads are written from a Christian standpoint, and the
religious memberships land accordingly: [Christian](../../traits/instructions/christian.json) on 983a Orthodoxy (route `agree`),
[Buddhist](../../traits/instructions/buddhist.json) on 984 Heterodoxy (where Roget lists other faiths), [Neopagan](../../traits/instructions/neopagan.json)
on 991 Idolatry (nature-worship words such as *heliolatry*, *fire-worship*), [New Age](../../traits/instructions/new_age.json) on
992 Sorcery (*occult sciences*, *mystic*, *talismanic*); [Jewish](../../traits/instructions/jewish.json),
[Muslim](../../traits/instructions/muslim.json) and [Hindu](../../traits/instructions/hindu.json) have no head.  A placement only decides which heads
count as covered, so that their words are not harvested again; it labels nothing.  Left as the check
answered.

### Every re-placed label (91)

"Placed before from": the text the label had been placed from.  "Before" is the label's head before this
update (`llm` = placed by the first check); "rules now" is the head the two routes give for the new text;
"after the check" is the final head, with Sonnet's answer in brackets where Opus decided differently.
Labels whose routes agree were not sent to the check ("rules (agree)").  Every call is in
[placement_responses.jsonl](./placement_responses.jsonl) (the last 116 lines).

| label | placed before from | before (route) | rules now (route) | after the check | decided by | reason (of the deciding model) |
|---|---|---|---|---|---|---|
| [ADHD](../../traits/instructions/adhd.json) | label only | none (none) | none (none) | 458 Inattention | opus | The core quality described, being unable to attend to what bores one, is inattention, which this head names. |
| [African](../../traits/instructions/african.json) | label only | none (none) | none (none) | 188 Inhabitant | opus | Inhabitant lists adjectives of native origin and nationality such as 'native', 'indigenous' and 'English', which is where an identity rooted in African origin belongs. |
| [ageist](../../traits/instructions/ageist.json) | label only | none (none) | 128 Age (semantic) | 481 Misjudgment | opus | Ageism is a prejudice, a biased prejudgment of people, which Misjudgment names with 'prejudiced', while the age heads only share its topic. |
| [aggrieved](../../traits/instructions/aggrieved.json) | label only | 900 Resentment (llm) | 835 Aggravation (semantic) | 900 Resentment | opus | Feeling wronged and nursing the grievance is resentment, which Resentment (900) names directly. |
| [ambivalent](../../traits/instructions/ambivalent.json) | label only | 605 Irresolution (llm) | 605 Irresolution (semantic) | 605 Irresolution | sonnet | Being torn between two opposed feelings matches 'double-minded' and 'half-hearted' in Irresolution, the closest head available. |
| [American](../../traits/instructions/american.json) | label only | 188 Inhabitant (llm) | none (none) | 188 Inhabitant | opus | Being American is at heart a nationality, being a native and resident of a country, which the Inhabitant head names with words like native, resident, British and English. |
| [androgynous](../../traits/instructions/androgynous.json) | label only | none (none) | 373 Man (semantic) | none | opus | No listed head names a blend of the manly and the womanly: Man and Woman each cover only one side, Sexuality is about sex and desire, and Unconformity is about general abnormality. |
| [antitheist](../../traits/instructions/antitheist.json) | label only | 989 Irreligion (llm) | 989 Irreligion (semantic) | 989 Irreligion | sonnet | Antitheism is hostile rejection of religion, and Irreligion (godlessness) is the closest head, though the others cover only doubt, profanity or fighting in general. |
| [asexual](../../traits/instructions/asexual.json) | label only | none (none) | 904 Celibacy (semantic) | 904 Celibacy | sonnet | Asexual means lacking sexual attraction, and the closest head is Celibacy (904), which covers singleness, virginity and abstaining from sexual relations; Indifference is a more general head, and the others are about sex itself, love or dislike. |
| [atheist](../../traits/instructions/atheist.json) | label only | 989 Irreligion (agree) | 989 Irreligion (agree) | 989 Irreligion | rules (agree) |  |
| [Australian](../../traits/instructions/australian.json) | label only | 188 Inhabitant (llm) | 188 Inhabitant (semantic) | 188 Inhabitant | sonnet | Being from a country and living there fits Inhabitant, whose adjectives include native and national terms like British and English. |
| [autistic](../../traits/instructions/autistic.json) | label only | none (none) | none (none) | none | sonnet | Autism is a neurodevelopmental bundle of traits (literalism, routine, narrow interests, sensory sensitivity), and none of the listed heads names that whole bundle; seclusion, taciturnity, deafness, intuition and reasoning each cover only a fragment or a different topic. |
| [bisexual](../../traits/instructions/bisexual.json) | label only | 374a Sexuality (agree) | 374a Sexuality (agree) | 374a Sexuality | rules (agree) |  |
| [blind](../../traits/instructions/blind.json) | label only | 442 Blindness (agree) | 442 Blindness (agree) | 442 Blindness | rules (agree) |  |
| [body-obsessed](../../traits/instructions/body_obsessed.json) | label only | 880 Vanity (llm) | none (none) | none | sonnet | Being obsessed with one's own body is not named by any listed head: Vanity is about conceit, Attention is general, and the others are unrelated, so none is the home. |
| [borderline personality disorder](../../traits/instructions/borderline_personality_disorder.json) | new stem | - | 59 Disorder (rule) | none | opus | The trait bundles unstable attachments, fear of abandonment, intense emotion and an unsteady sense of self, and no listed head names that whole bundle. Insanity means unsound reason, and Disorder and Derangement only share the word 'disorder' in another sense. |
| [Brazilian](../../traits/instructions/brazilian.json) | label only | none (none) | none (none) | 188 Inhabitant | opus | Being from and living in Brazil is a matter of nationality and native residence, which head 188 covers with words like native, indigenous and national adjectives such as British. |
| [British](../../traits/instructions/british.json) | label only | 188 Inhabitant (agree) | 188 Inhabitant (agree) | 188 Inhabitant | rules (agree) |  |
| [Buddhist](../../traits/instructions/buddhist.json) | label only | 984 Heterodoxy (lexical) | 984 Heterodoxy (lexical) | 984 Heterodoxy (Sonnet: none) | opus | Being a Buddhist is adherence to a non-Christian faith, and Roget's Heterodoxy head is where it lists other religions and their followers, Buddhism among them. |
| [Canadian](../../traits/instructions/canadian.json) | label only | 188 Inhabitant (agree) | 188 Inhabitant (agree) | 188 Inhabitant | rules (agree) |  |
| [Chinese](../../traits/instructions/chinese.json) | label only | none (none) | none (none) | 188 Inhabitant | opus | The trait is about being a native and resident of a country, which is what Inhabitant names; its words include nationality terms like 'native', 'British' and 'English'. |
| [Christian](../../traits/instructions/christian.json) | label only | 983a Orthodoxy (agree) | 983a Orthodoxy (agree) | 983a Orthodoxy | rules (agree) |  |
| [close-knit](../../traits/instructions/close_knit.json) | label only | 888 Friendship (llm) | 888 Friendship (semantic) | 888 Friendship | sonnet | Close-knit describes a tight circle of family and old friends bound by mutual intimacy, and Friendship (friendly, brotherly, fraternal, amity, brotherhood) names that bond most closely, while Consanguinity covers only blood kinship and Nearness is spatial. |
| [conspiracy-minded](../../traits/instructions/conspiracy_minded.json) | label only | none (none) | 528 Concealment (semantic) | none | opus | No listed head names a suspicious, plot-seeing cast of mind: Concealment, Secret and Ambush only share the topic of secrecy, Belief is too general, and Willingness only matches the spelling of "minded". |
| [deaf](../../traits/instructions/deaf.json) | label only | 581 Aphony (agree) | 581 Aphony (agree) | 581 Aphony | rules (agree) |  |
| [delusional](../../traits/instructions/delusional.json) | label only | 503 Insanity (agree) | 503 Insanity (agree) | 503 Insanity | rules (agree) |  |
| [detractor](../../traits/instructions/detractor.json) | label only | 936 Detractor (agree) | 936 Detractor (agree) | 936 Detractor | rules (agree) |  |
| [dignity culture](../../traits/instructions/dignity_culture.json) | label only | none (none) | 878 Pride (semantic) | 878 Pride | sonnet | Head 878 holds 'dignity' and 'self-respect', which name the sense of inherent personal worth the description gives. |
| [dissociative](../../traits/instructions/dissociative.json) | label only | none (none) | 449 Disappearance (semantic) | none | opus | None of the listed heads names the mental state of depersonalization, unreality or lost time; 'dissociation' in Irrelation means logical unconnectedness, and Absence and Disappearance are about physical presence. |
| [distressed](../../seed_queue.json) (queued) | label only | 828 Pain (llm) | 859 Hopelessness (semantic) | 828 Pain | opus | Being distressed is general mental suffering, affliction and worry, which is what Pain (828) names, while Hopelessness covers only one part of it. |
| [dyslexic](../../traits/instructions/dyslexic.json) | label only | none (none) | none (none) | none | sonnet | Dyslexia is a specific difficulty in reading and spelling, and none of the listed heads names that; Stammering concerns speech, Learning and Learner concern study in general, and the others are sensory impairments. |
| [East Asian](../../traits/instructions/east_asian.json) | label only | none (none) | none (none) | none (Sonnet: 188 Inhabitant) | opus | East Asian here means an ethnic heritage that bundles roots, language and customs, kept wherever one lives; no listed head names that, and Inhabitant is about dwelling in a place. |
| [European](../../traits/instructions/european.json) | label only | 188 Inhabitant (llm) | none (none) | 188 Inhabitant | opus | Head 188 holds the words for belonging to a place by origin or nationality (native, British, English), which is the nearest match to having European roots. |
| [face culture](../../traits/instructions/face_culture.json) | label only | none (none) | none (none) | none | sonnet | The trait bundles claiming only one's due, harmony, rank-keeping, and saving others' face, and no single head (Humility, Modesty, Respect, Pride) names the whole. |
| [French](../../traits/instructions/french.json) | label only | none (none) | none (none) | 188 Inhabitant | opus | Being from France and living there is a matter of nationality and residence, which Inhabitant covers with words like native, resident, British, English. |
| [German](../../traits/instructions/german.json) | label only | none (none) | none (none) | 188 Inhabitant | opus | Being German by origin and residence is nationality and nativity, which head 188 Inhabitant covers with 'native', 'indigenous', and national adjectives like 'British' and 'English'. |
| [guilt-prone](../../traits/instructions/guilt_prone.json) | label only | 950 Penitence (llm) | 947 Guilt (semantic) | 950 Penitence | opus | Penitence names the conscience-stricken feelings of contrition and compunction over a wrong, which is the trait described; Guilt names culpability itself, not the proneness to feel it. |
| [gun owner](../../traits/instructions/gun_owner.json) | label only | none (none) | 779 Possessor (agree) | 779 Possessor | rules (agree) |  |
| [Hindu](../../traits/instructions/hindu.json) | label only | none (none) | none (none) | none (Sonnet: 987 Piety) | opus | Being Hindu means belonging to one particular faith with its own rites, festivals and beliefs, and no listed head names that faith: Piety and Worship cover religiousness in general, and Pseudo-Revelation only shares the topic through the Vedas. |
| [Hispanic](../../traits/instructions/hispanic.json) | label only | none (none) | none (none) | none | sonnet | Hispanic is an ethnic/cultural identity bundling heritage, language and place, and no listed head names that whole; they only share side topics. |
| [honor culture](../../traits/instructions/honor_culture.json) | label only | none (none) | none (none) | 873 Repute | opus | Honor culture treats one's worth as a standing held in others' eyes, which is what the Repute head names with words like honored, name and distinction. |
| [Indian](../../traits/instructions/indian.json) | label only | none (none) | 188 Inhabitant (semantic) | 188 Inhabitant | sonnet | Being Indian means being a native inhabitant of India, which fits Inhabitant, whose adjectives include native, indigenous, British and English as nationality words. |
| [Indigenous American](../../traits/instructions/indigenous_american.json) | label only | 188 Inhabitant (llm) | 188 Inhabitant (semantic) | 188 Inhabitant | sonnet | The trait is being a member of the Americas' first peoples, and head 188 (Inhabitant) holds 'indigenous', 'native' and 'autochthonous', which name that quality. |
| [Indigenous Australian](../../traits/instructions/indigenous_australian.json) | label only | 188 Inhabitant (llm) | 188 Inhabitant (semantic) | 188 Inhabitant | sonnet | Head 188, Inhabitant, holds 'indigenous', 'native' and 'autochthonous', which name being a native people of a place, the core of being Indigenous Australian. |
| [Italian](../../traits/instructions/italian.json) | label only | none (none) | none (none) | 188 Inhabitant | opus | Being from Italy and living there is being a native inhabitant of a country, which the Inhabitant head names with words like native, indigenous and nationality adjectives such as British. |
| [Japanese](../../traits/instructions/japanese.json) | label only | none (none) | none (none) | 188 Inhabitant | opus | Being a native and resident of Japan is a nationality of birth and dwelling, which the Inhabitant head covers with words like native, indigenous and national adjectives such as British. |
| [Jewish](../../traits/instructions/jewish.json) | label only | 985 Judeo-Christian Revelation (agree) | none (none) | none | sonnet | Jewish observance bundles ritual, diet, worship, fasting and festivals, and no single listed head names the whole; each head covers only one facet. |
| [joiner](../../traits/instructions/joiner.json) | label only | none (none) | none (none) | none | sonnet | No head names a habit of joining every group; Participation covers shared possession, Party covers factions, and the others are unrelated. |
| [kinky](../../traits/instructions/kinky.json) | label only | 608 Caprice (agree) | 374a Sexuality (semantic) | 374a Sexuality | sonnet | Kinkiness is a variety of sexual taste, and Sexuality (erotic, sexual, carnal) is the nearest head, though it names sex in general rather than this specific taste. |
| [lonely](../../traits/instructions/lonely.json) | label only | 893 Seclusion. Exclusion (agree) | 893 Seclusion. Exclusion (agree) | 893 Seclusion. Exclusion | rules (agree) |  |
| [mercenary](../../traits/instructions/mercenary.json) | label only | 746 Servant (agree) | 943 Selfishness (agree) | 943 Selfishness | rules (agree) |  |
| [middle-aged](../../traits/instructions/middle_aged.json) | label only | 131 Adolescence (agree) | 131 Adolescence (agree) | 131 Adolescence | rules (agree) |  |
| [middle-class](../../traits/instructions/middle_class.json) | label only | 736 Mediocrity (semantic) | 29 Mean (rule) | 736 Mediocrity | opus | Mediocrity (736) names moderate circumstances, respectability and the middle classes, which is the social station described, while 'middle-class' under Mean (29) only means average in quantity. |
| [Middle Eastern](../../traits/instructions/middle_eastern.json) | label only | none (none) | none (none) | none | sonnet | No head names a regional ethnic heritage; Inhabitant is only about being a native or resident, and Middle is a spelling coincidence. |
| [mobility impaired](../../traits/instructions/mobility_impaired.json) | label only | none (none) | none (none) | none | sonnet | The trait is an impairment of the ability to walk, and no listed head names disability or lameness; Motion, Journey, Traveler, Quiescence and Slowness only share the topic of movement. |
| [monogamous](../../traits/instructions/monogamous.json) | label only | 903 Marriage (agree) | 903 Marriage (agree) | 903 Marriage | rules (agree) |  |
| [Muslim](../../traits/instructions/muslim.json) | label only | none (none) | none (none) | none (Sonnet: 987 Piety) | opus | Being Muslim means following a particular religion, and none of these heads names Islam: Piety and Worship cover devoutness in general, Orthodoxy lists Christian terms, and Fasting is only one practice. |
| [Neopagan](../../traits/instructions/neopagan.json) | new stem | - | none (none) | 991 Idolatry | opus | Honoring the old gods and treating nature as divine is pagan worship of gods other than the Christian God, which this head names through nature-worship terms like heliolatry and fire-worship. |
| [neuter](../../traits/instructions/neuter.json) | label only | 609a Absence of Choice (agree) | 609a Absence of Choice (agree) | 609a Absence of Choice | rules (agree) |  |
| [New Age](../../traits/instructions/new_age.json) | label only | 124 Oldness (agree) | none (none) | 992 Sorcery | opus | New Age belief in crystals, astrology, energy healing and signs from the universe is a modern form of the occult sciences and talismanic mysticism named in Sorcery. |
| [Nigerian](../../traits/instructions/nigerian.json) | label only | 188 Inhabitant (llm) | none (none) | 188 Inhabitant | opus | Being Nigerian is a nationality, being a native and resident of a country, which is what Inhabitant names with words like 'native', 'indigenous' and national adjectives such as 'British' and 'English'. |
| [nonbinary](../../traits/instructions/nonbinary.json) | label only | none (none) | none (none) | none | sonnet | Heads 373 and 374 each name one sex, and the others only echo 'neither' or 'none', so no head names being neither man nor woman. |
| [OCD](../../traits/instructions/ocd.json) | new stem | - | none (none) | none (Sonnet: 503 Insanity) | opus | OCD is unwanted, intrusive thoughts and acts the person knows are senseless, so it is not insanity or madness. Compulsion here means coercion by others, and Disorder means lack of arrangement, so neither fits. |
| [pansexual](../../traits/instructions/pansexual.json) | label only | none (none) | none (none) | none | sonnet | Pansexuality is a particular orientation, attraction to people of any gender, and no listed head names that; Love, Desire and Sexuality only share the topic, and Celibacy is the opposite. |
| [polyamorous](../../traits/instructions/polyamorous.json) | label only | none (none) | none (none) | none (Sonnet: 897 Love) | opus | Polyamory is a modern, consensual way of loving several partners at once; Love names only love in general, and Marriage, Celibacy and the others do not name this arrangement. |
| [polyandrous](../../traits/instructions/polyandrous.json) | label only | 903 Marriage (llm) | 903 Marriage (semantic) | 903 Marriage | sonnet | Polyandry is a form of marriage, and head 903 (Marriage) names the married state, which is the closest fit among the listed heads. |
| [polygamous](../../traits/instructions/polygamous.json) | label only | 903 Marriage (agree) | 903 Marriage (agree) | 903 Marriage | rules (agree) |  |
| [polygynous](../../traits/instructions/polygynous.json) | label only | 903 Marriage (llm) | 903 Marriage (semantic) | 903 Marriage | sonnet | Polygyny is a form of marriage, and Marriage (903) is the head that names the married state. |
| [punishment-fearing](../../traits/instructions/punishment_fearing.json) | new stem | - | 860 Fear (rule) | 860 Fear (Sonnet: none) | opus | The trait is at heart a fear (of punishment) that restrains conduct, so the Fear head names its core quality; the Punishment and Penalty heads name the penalty itself, not the attitude toward it. |
| [Russian](../../traits/instructions/russian.json) | label only | none (none) | none (none) | 188 Inhabitant | opus | Being a native of Russia who lives there is a national-inhabitant quality, which Inhabitant covers with words like native, indigenous, British and English. |
| [self-harming](../../traits/instructions/self_harming.json) | label only | none (none) | none (none) | none | sonnet | No listed head names deliberately hurting oneself in secret as a way of coping; Pain, Painfulness, Killing, Badness and Concealment each cover only one aspect of it. |
| [sexist](../../traits/instructions/sexist.json) | label only | none (none) | none (none) | none | sonnet | No listed head names sexism as a whole; Man and Woman only denote the sexes, while Discrimination (465) means perceiving differences, Disrespect covers contempt generally, and Inequality is about quantity. |
| [shame-prone](../../traits/instructions/shame_prone.json) | label only | 879 Humility (llm) | 947 Guilt (semantic) | 879 Humility (Sonnet: none) | opus | Roget files the feeling of shame and humiliation before others' judgment under Humility, which is the closest home for a disposition to feel shame; Guilt and Penitence name the inward conscience the description excludes. |
| [Shinto](../../traits/instructions/shinto.json) | label only | none (none) | none (none) | none (Sonnet: 990 Worship) | opus | Shinto is a specific religion that bundles many practices, and no listed head names that faith as a whole; Worship, Rite and Temple each cover only a general part of it. |
| [Sikh](../../traits/instructions/sikh.json) | label only | none (none) | none (none) | none | sonnet | A Sikh is a follower of a particular religion, a bundle of belief, worship, ritual and dress, and no listed head names the whole; Piety is only the general religious quality and Pseudo-Revelation lists other faiths' scriptures and founders. |
| [sleep-deprived](../../traits/instructions/sleep_deprived.json) | label only | 688 Fatigue (llm) | 688 Fatigue (semantic) | 688 Fatigue | sonnet | Sleep deprivation is chronic bodily tiredness with drooping, haggard exhaustion and yawning, which is what Fatigue (688) names; Weariness (841) is more about boredom and disgust. |
| [smoker](../../traits/instructions/smoker.json) | label only | none (none) | none (none) | none (Sonnet: 613 Habit) | opus | None of the listed heads covers tobacco or smoking; Habit, Odor and Fetor each touch only one side of the daily smoking routine. |
| [South Asian](../../traits/instructions/south_asian.json) | label only | none (none) | none (none) | none (Sonnet: 188 Inhabitant) | opus | South Asian is an ethnic or regional heritage identity, and no head names that quality: Inhabitant and Language only touch the topic and do not name South Asian origin. |
| [stigmatized](../../traits/instructions/stigmatized.json) | label only | 874 Disrepute (llm) | none (none) | 874 Disrepute | opus | Being stigmatized means bearing a mark of discredit or disgrace in others' eyes, which is what Disrepute names. |
| [stoner](../../traits/instructions/stoner.json) | label only | none (none) | none (none) | none | sonnet | Drunkenness is about alcohol and Habit is generic, so no listed head names habitual drug intoxication. |
| [stressed](../../traits/instructions/stressed.json) | label only | 828 Pain (llm) | none (none) | 828 Pain | opus | Being stressed is a lasting state of worry and mental suffering, which fits Pain's 'worried' and 'mental suffering'. Exertion and Fatigue name only the effort or the tiredness, not the strained, anxious condition. |
| [suburban](../../traits/instructions/suburban.json) | label only | 189 Abode (agree) | 189 Abode (agree) | 189 Abode | rules (agree) |  |
| [suicidal](../../traits/instructions/suicidal.json) | label only | 361 Killing (agree) | none (none) | none | sonnet | Suicidal means wanting to be dead and contemplating self-killing, but no head names suicide itself (Roget's 361 Killing covers homicide, and 360 Death is the state of being dead); hopelessness and dejection capture only the mood, not the wish to die. |
| [Taoist](../../traits/instructions/taoist.json) | label only | none (none) | none (none) | none (Sonnet: 990 Worship) | opus | Taoism bundles religious practice, a philosophy and a passive attitude, and no listed head names that whole bundle; worship, rite and temple each cover only one part. |
| [technomystical](../../traits/instructions/technomystical.json) | queue draft | none (none) | 992 Sorcery (semantic) | none | opus | None of the listed heads names a sacred reverence for technology; they only share the religious topic (temple, deity, mystic magic). |
| [trapped-in-job](../../traits/instructions/trapped_in_job.json) | label only | none (none) | none (none) | 751 Restraint | opus | The core quality is being held somewhere against one's wish by circumstances, which Restraint names with 'constrained' and 'pent up'; Business only shares the job topic. |
| [traumatized](../../traits/instructions/traumatized.json) | label only | 828 Pain (llm) | none (none) | none (Sonnet: 828 Pain) | opus | Being traumatized is a bundle of lingering fear, intrusive memories, avoidance and hypervigilance, and no listed head names it: Pain covers only general suffering, and Safety names the opposite of the trait. |
| [uninsured](../../traits/instructions/uninsured.json) | label only | none (none) | none (none) | none | sonnet | Being uninsured is a modern financial and insurance condition; none of the listed heads names it, since they cover health, disease, neglect, or nonpayment of debts, which only share a topic. |
| [unscrupulous](../../traits/instructions/unscrupulous.json) | label only | 940 Improbity (agree) | 940 Improbity (agree) | 940 Improbity | rules (agree) |  |
| [unsupported](../../traits/instructions/unsupported.json) | label only | none (none) | none (none) | 893 Seclusion. Exclusion | opus | Having no one to help and carrying every load alone is friendless, unbefriended solitude, which belongs with Seclusion (lonely, forlorn); head 468 matches only the spelling, in the sense of unsupported evidence. |
| [xenophobic](../../traits/instructions/xenophobic.json) | label only | 867 Dislike (llm) | none (none) | 898 Hate (Sonnet: 911 Misanthropy) | opus | Xenophobia is a hatred and hostility aimed at foreigners, which is a specific form of the quality named by the Hate head. |

### Spend

| step | calls | tokens in / out | cost |
|---|---|---|---|
| `map --update`: embeddings of the 91 new texts (`text-embedding-3-large`) | 1 | 3,951 / 0 | $0.0005 |
| placement check, Sonnet 5.5 (`claude-sonnet-5-5`) | 73 | 85,259 / 9,614 | $0.267 |
| placement check, Opus 5.5 (`claude-opus-5-5`) | 43 | 50,518 / 9,698 | $0.396 |
| head scope of 29 Mean, Haiku 5.5 (`claude-haiku-5-5`) | 1 | 645 / 92 | $0.0001 |
| **total** | 118 | | **$0.664** |

The check's estimate was $0.67 (Sonnet $0.28 for 73 calls; Opus $0.39 for the 44 calls a 60% referee
share would give, $0.66 if asked on all 73), from the token figures in the code; the Opus output figure
was raised from 190 to 215 tokens a call, the full first run's measurement, before this run.  Caps: $2.90
for the check, $3 for the whole job.  No answer could be reused (every prompt was new), no answer failed to
parse, and six connection errors were retried by the client without charge.  The usage files are
cumulative: [placement_usage.json](./placement_usage.json) now $5.63 over both checks,
[mapping_usage.json](./mapping_usage.json) $0.014, [head_scope_usage.json](./head_scope_usage.json) $0.166.

### Tests

The acceptance test that caught the renames
([test_gapgen_roget_acceptance.py](../../../assistant_axis/tests/test_gapgen_roget_acceptance.py),
`test_every_corpus_trait_is_in_label_heads`) stays strict; its failure message now names, for each missing
stem, the `renamed_from` its file carries, and the commands to run.  A new test,
`test_label_heads_has_no_stale_stems`, fails when a key is no corpus trait and no queue trait entry, and
names the file or queue entry whose `renamed_from` points at it: a rename inside the queue (chunk 6's
`in_pain` to `in_chronic_pain`) leaves no new file, so only this test would catch it.  Changed expectation:
the cumulative spend bound on [placement_usage.json](./placement_usage.json) went from $5 to $8 (the first
check's $5 cap plus this update's $3).

### Not done

- [map_spotcheck.md](./map_spotcheck.md) is still the first map's spot check.
- The religious-head placements above are reported, not changed.
