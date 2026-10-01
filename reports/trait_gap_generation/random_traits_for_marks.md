# Random adjectives that pass as traits: a sample for your marks

These are 50 words drawn at random from the dictionary adjectives in the validation file (the group
used to check that the filter does not pass ordinary adjectives as traits) that the current filter
(classifier prompt version 4) passed as traits.  They were chosen by a fixed seed from 160 random
adjectives that no earlier pilot or smoke batch had seen, and are listed alphabetically.  Please mark
each one **trait** (a fair trait word), **not a trait**, or **unsure**; your marks decide question R2,
whether to keep the target that at most 15% of random adjectives pass, or to judge the filter by
marks like these instead.

Run: [m2rubric_r5_sample_1](../../data/candidates/filter/m2rubric_r5_sample_1/) ([results.jsonl](../../data/candidates/filter/m2rubric_r5_sample_1/results.jsonl), [usage.json](../../data/candidates/filter/m2rubric_r5_sample_1/usage.json), [summary.json](../../data/candidates/filter/m2rubric_r5_sample_1/summary.json)); cost $0.2499.

## The whole batch

| | rows |
|---|---|
| rows run | 160 |
| cut by the frequency floor (too rare to send to the model) | 34 |
| rejected (no sense describes a person, or not a word; 2 of these by the definition probe) | 37 |
| sent to a side list (states, physical, roles) | 26 |
| tagged as pure praise or blame, on no list | 1 |
| the model's answer failed validation, twice | 1 |
| **passed as traits** | **61** (3 of them held on the nationalities list) |
| share passed, of all rows run | 38% |
| share passed, of the 126 rows the model saw | 48% |

## The 50 for marking (61 passed; 50 chosen by seed 0)

| word | sense the filter judged | gloss | notes | your mark |
|---|---|---|---|---|
| argumentative | inclined to argue and dispute | This means being quick to argue and dispute, taking issue with what others say, pressing points even when agreement would be easier, and treating disagreement as a challenge to be won. |  | trait |
| barehanded | facing challenges without weapons or tools | This means meeting difficulties and opponents without advantage or protection, relying on courage and skill alone, and refusing to use tricks, weapons or unfair means to win. | second opinion said tagged | trait: specifically a state |
| bothersome | causing annoyance and irritation to others | This means being a source of annoyance and irritation to those around you, pestering them with questions or demands, getting in the way, and making things harder rather than easier. |  | trait |
| clinical | detached and unemotional in manner | This means observing and judging matters with cool detachment, stripping away emotion and personal stakes to see only the bare facts, and speaking about even painful things without warmth. |  | trait |
| common | ordinary and unremarkable | This means being ordinary and unremarkable, lacking distinction or special qualities, blending into the crowd and drawing no particular notice or attention. | two_trait_senses | trait (but probably too vauge/mutilsemous to be a useful one) |
| corruptible | susceptible to bribery and moral compromise | This means being open to bribery and temptation, willing to bend rules or betray principles for money or advantage, and lacking the integrity to resist offers that serve your interests. |  | trait |
| Danish | from Denmark or of Danish nationality | This means being from Denmark, a native or citizen of the country who speaks Danish and shares in its culture, holidays and everyday ways. | membership: nationality_ethnicity_language; held on the nationalities list | trait |
| decided | resolute and firm in manner | This means being resolute and firm in manner, committing fully to choices once made, speaking with certainty and moving forward without second-guessing or wavering. | nontrait_person_sense | unclear: the "you have just made a decision" non-trait sense seems the most obvious |
| disrespectful | treating others without respect | This means speaking to and about others in ways that dismiss their worth, using a tone that belittles, mocking their views, and showing through words and manner that you regard them as beneath consideration. |  | trait |
| Eastern Orthodox | belonging to the Eastern Orthodox Christian tradition | This means practicing the Eastern Orthodox Christian faith, observing its liturgy and calendar, honoring its icons and saints, and living within its spiritual and community traditions. | membership: affinity | trait |
| false | dishonest and prone to deception | This means being dishonest and deceptive, telling lies when convenient, misrepresenting facts and intentions, and treating truth as something to bend rather than respect. |  | unclessr (its plain sense of factually incorrect is unhelpfully strong) |
| fluffy | light and insubstantial in manner | This means speaking and thinking in ways that are light, airy and insubstantial, avoiding depth and seriousness, treating weighty matters with a breezy tone and never settling into hard truths. | nontrait_person_sense | trait, but also has a physical sense |
| frosty | cold and unfriendly in manner | This means treating others with cool distance and reserve, offering little warmth or welcome, and keeping conversations brief and formal rather than open and friendly. |  | trait (two senses, the more common a physical state) |
| full-time | working full-time hours | This means working full-time hours at a job, organizing your week around that commitment, and having limited time for other pursuits because of the demands of work. | membership: circumstance | trait |
| grubby | habitually dirty and unwashed | This means neglecting cleanliness and grooming, wearing soiled clothes, and showing little concern for appearing neat or presentable to others. | nontrait_person_sense | trait (two senses, the more obvious a physical state, also has a metaphorical version) |
| high-energy | active, enthusiastic and vigorous | This means moving and thinking fast, throwing yourself into tasks with enthusiasm, rarely sitting still, and bringing intensity and drive to everything you do. |  | trait |
| hit-and-run | causing harm and fleeing without responsibility | This means striking out at others and then disappearing, leaving damage behind without facing consequences, admitting fault or making amends for what was done. |  | not a trait, this is and action |
| ho-hum | bored and unimpressed | This means meeting ideas, events and people with a shrug, finding little worth your interest or excitement, and treating most things as tedious and beneath your notice. |  | trait: specifically a state |
| illegal | acting against the law or having illegal status | This means breaking laws and regulations as a way of life, treating legal rules as obstacles to work around, and accepting the risks of arrest and punishment. |  | not a trait |
| incestuous | engaging in incest | This means engaging in sexual relations with a family member, a violation of kinship bonds and social taboo that shapes how one relates to family and sexuality. | two_trait_senses | trait |
| integrated | fitting into and accepted by a social group or community | This means fitting into and being accepted by a social group or community, participating fully in its life, and feeling at home among its members. |  | trait (but a bit vaugue/unclear/polysemous) |
| Junior | son with the same name as father | This means being a son who shares his father's name, carrying the suffix Junior and living with the comparisons, expectations and identity questions that come from bearing a father's name. | membership: family | unclear: multiple meanings, can also just mean younger than |
| lawless | disregarding laws and rules | This means treating laws and rules as obstacles to work around rather than constraints to respect, breaking them when it suits you, and seeing authority as something to defy. |  | trait |
| leavened | lightened with humor or levity | This means mixing humor, lightness and wit into serious matters, softening heavy topics with jokes and finding the funny side of difficulty rather than dwelling in gloom. |  | trait (but to me unhelpfully overshadowed by the "having had yeast added" sense) |
| middle | the middle child in a family | This means being the middle child, caught between older and younger siblings, often mediating between them and developing a distinct role in the family dynamic. | two_trait_senses; membership: family | unclear: multiple senses |
| migratory | moving seasonally from place to place | This means moving from place to place with the seasons or work, never settling long in one home, and organizing life around travel and temporary arrangements. | membership: circumstance | trait |
| noncompetitive | avoiding competition and winning | This means having little drive to compete or win, content to participate without needing to come out ahead, and finding satisfaction in the activity itself rather than in victory. |  | trait |
| nonsovereign | from a territory without sovereignty | This means being from a territory that is not sovereign, governed by another nation or power, and living with the constraints and dependencies that come with that status. | membership: geography | unclear: also means "is not a king or queen" |
| nonturbulent | calm and free from conflict | This means staying calm and unruffled, avoiding drama and conflict, and moving through life with steady composure even when others around you are upset or agitated. |  | trait |
| one-time | having done something once in the past | This means having done something once in the past, a single experience that shapes how you see that thing now, without making it a habit or defining feature. | membership: circumstance | unclear: too vaugue |
| part-time | working fewer than full hours per week | This means working fewer than full hours per week, juggling other commitments or responsibilities, and organizing life around a flexible or limited work schedule. | membership: circumstance | trait |
| pedagogic | focused on teaching and explaining | This means approaching conversations as teaching moments, breaking down ideas into steps, asking questions to check understanding, and explaining the reasoning behind answers rather than just giving them. |  | trait |
| present | attending and paying attention to what is happening | This means being fully attentive and engaged in the moment, not distracted by thoughts of past or future, and giving your full awareness to what is happening and who is with you. | nontrait_person_sense | trait: also means "not (literally) absent" |
| presentable | neat and acceptable in appearance | This means keeping oneself neat and tidy, dressing appropriately for the occasion, and taking care to look acceptable and respectable in public and social settings. |  | trait |
| puzzling | hard to understand or figure out | This means being hard to read or understand, keeping your thoughts and motives unclear, and leaving others guessing about what you really think or what you will do next. |  | trait |
| raised | brought up in a particular place or way | This means having been brought up in a particular place, family or way of life, shaped by the values, habits and surroundings of childhood and carrying them forward. | membership: circumstance | unclear: "has been lifted up" meaning is a little confusing. "raised <foo>" is a more common formulation |
| sophomore | in the second year of high school or college | This means being in the second year of high school or college, old enough to know the ropes but still learning, with the confidence and blind spots of that stage. | membership: age_group | trait |
| southeastern | from the southeastern region | This means being from the southeastern region, shaped by its climate, culture, history and ways of speaking, and carrying its accent, values and everyday habits into how one lives. | membership: geography | trait |
| sympathetic | feeling and showing compassion for others | This means feeling genuine compassion for others' suffering, listening without judgment, offering help and comfort, and taking their troubles seriously rather than dismissing them. |  | trait |
| Tuscan | from Tuscany, Italy | This means being from Tuscany in Italy, a native of the region who speaks its dialect, shares its culture and landscape, and carries its traditions and ways. | membership: nationality_ethnicity_language; held on the nationalities list | trait |
| twisted | morally or psychologically warped | This means thinking and acting in ways that are warped by malice, perversion or corruption, taking pleasure in harm, and interpreting events through a lens of cynicism and cruelty. | nontrait_person_sense | trait |
| unconditioned | not shaped by conditioning or habit | This means responding to situations without learned habits or conditioned reflexes, acting from first principles and instinct rather than from training or social expectation. | second opinion said tagged | trait (but rather vague) |
| unfinished | leaving tasks and projects incomplete | This means starting projects and tasks but rarely seeing them through to completion, moving on to new things before finishing old ones, and leaving loose ends. | nontrait_person_sense | trait, but the more obvious sense is that they are unfinished, rather habitually not finishing things |
| ungrammatical | speaking or writing with poor grammar | This means speaking and writing with frequent errors in grammar, mixing tenses, dropping subjects, and ignoring the rules of sentence structure without concern. |  | trait |
| unobtrusive | quiet and avoiding attention | This means staying in the background, speaking little, blending into groups, and making yourself small so that others barely notice you are there. |  | trait |
| unreachable | keeping oneself distant and hard to contact | This means staying aloof and hard to reach, answering slowly or not at all, keeping emotional distance from others, and making it clear that access to you is limited and difficult. |  | trait (also a state) |
| unsharpened | mentally dull or unclear | This means thinking in blunt, imprecise ways, missing fine distinctions, and expressing ideas without the clarity or precision that would cut through confusion or make a sharp point. | nontrait_person_sense | unclear |
| virulent | intensely hostile and bitter in manner | This means attacking others with intense hostility and bitter venom, speaking with poisonous words meant to wound, and carrying a deep animosity that colours every interaction. |  | trait |
| warlike | inclined toward conflict and aggression | This means approaching disagreements as battles to win, seeing others as rivals or enemies, speaking in combative terms, and meeting any challenge with immediate hostility and force. |  | trait |
| wishy-washy | indecisive and lacking conviction | This means waffling between positions, never quite committing to a view, hedging every statement with qualifications, and leaving others unsure what you actually believe. |  | trait |

## Words that did not pass (context only, not for marking)

**Cut by the frequency floor (34):** acarpellous, ascocarpous, ataxic, bacteroid, bewhiskered, bicipital, bitumenoid, bronchiolar, calorimetric, carinated, chaetognathan, chanceful, chantlike, columnlike, contumacious, coordinative, corneous, curvilineal, discomposed, dolichocranial, epicyclical, equipoised, eudemonic, frizzly, gallinaceous, ironshod, irritative, Kechuan, misanthropical, penurious, repudiative, Voltarian, vulval, winglike.

**Rejected (37):** accessory, Altaic, auric, benzoic, bimodal, callable, camp-made, columned, conjoint, diamagnetic, even-toed, flash, fur-bearing, gold, hind, horse-and-buggy, inbuilt, Maroc, moire, multiple, noncommunicable, obviating, photoelectric, pronominal, purple-lilac, representational, semi-evergreen, seven-membered, spectrometric, stemmed, tangible, tantamount, tickling, unanimous, unwooded, vesicular, xxxvii (by the definition probe: Maroc, xxxvii).

**Sent to a side list (26):** physical (11): asymmetrical, flame-colored, loose-jointed, mail-clad, peach-colored, rose-red, soft-nosed, sooty-black, straggly, straw-colored, uncoordinated; roles (2): Praetorian, principal; states (13): breathless, intervening, miffed, out of it, outclassed, pained, returning, snowbound, starving, stimulated, stricken, unqualified, weeping.

**Tagged as pure praise or blame (1):** irresistible.

**Answer failed validation (1):** abominable.

**Passed but not drawn into the 50 (11):** Norwegian, conversant, cumulative, endless, monozygotic, participatory, recluse, sought-after, trendsetting, unexciting, upscale.

All 160 rows now count as seen in development, so the full validation run reports its figures for
unseen rows without them.  Chosen by [build_smoke_sets.py](../../data_analysis/gap_generation/build_smoke_sets.py) with `--round 5` ([input set](../../data/candidates/validation/m2rubric_r5_sample_1.jsonl)).
