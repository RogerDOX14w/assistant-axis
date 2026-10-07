# Haiku 5.5 against Haiku 4.5: the M1 split filter on the validation pool's words

143 words (the reference run's), reference m3_pilot_m1_validation (Sonnet 5.5, step versions {"sense": 8, "established": 7, "vague": 3, "kind": 6, "same_sense": 2, "gloss": 3, "alignment": 3, "descriptors": 1}).  From `haiku55_compare.py filter-validation`.

## The runs

| run | first model | step versions | git sha | rows |
|---|---|---|---|---|
| h55_m1_validation_pool | Haiku 5.5 | {"sense": 8, "established": 7, "vague": 3, "kind": 6, "same_sense": 2, "gloss": 3, "alignment": 3, "descriptors": 1} | 62023c4 | 143 |
| h55_m1_validation_pool_rep2 | Haiku 5.5 | {"sense": 8, "established": 7, "vague": 3, "kind": 6, "same_sense": 2, "gloss": 3, "alignment": 3, "descriptors": 1} | 52478d7 | 143 |
| m1_validation_r2 | Haiku 4.5 | {"sense": 8, "established": 7, "vague": 3, "kind": 6, "same_sense": 2, "gloss": 3, "alignment": 3, "descriptors": 1} | af762b4+dirty | 1810 |
| m1_validation | Haiku 4.5 | {"sense": 6, "established": 4, "vague": 3, "kind": 4, "same_sense": 2, "gloss": 3, "alignment": 3, "descriptors": 1} | b0c6504+dirty | 1810 |

## Against the reference

The words are those M3's pilot drew from the M1 validation run's random adjectives that Haiku 4.5 (at the step versions of `m1_validation`) passed as traits: the pool is selected on that run's verdict, so its figures are not those of a random sample.  Reference outcomes: {"roles": 4, "states": 10, "trait": 100, "turned_away": 29}.

| run | words both classified | same outcome | agreement | disagreement | same verdict | Haiku trait, Sonnet not | Sonnet trait, Haiku not | the run's outcomes | Sonnet -> Haiku |
|---|---|---|---|---|---|---|---|---|---|
| h55_m1_validation_pool | 143 | 113 | 79.0% | 21.0% | 113 | 13 | 13 | {"physical": 3, "roles": 2, "states": 9, "trait": 100, "turned_away": 29} | {"roles -> trait": 2, "roles -> turned_away": 1, "states -> trait": 3, "states -> turned_away": 1, "trait -> physical": 2, "trait -> states": 3, "trait -> turned_away": 8, "turned_away -> physical": 1, "turned_away -> roles": 1, "turned_away -> trait": 8} |
| h55_m1_validation_pool_rep2 | 143 | 114 | 79.7% | 20.3% | 114 | 12 | 12 | {"physical": 4, "roles": 3, "states": 10, "trait": 100, "turned_away": 26} | {"roles -> trait": 2, "states -> trait": 2, "states -> turned_away": 2, "trait -> physical": 3, "trait -> roles": 1, "trait -> states": 2, "trait -> turned_away": 6, "turned_away -> physical": 1, "turned_away -> states": 2, "turned_away -> trait": 8} |
| m1_validation_r2 | 143 | 103 | 72.0% | 28.0% | 103 | 33 | 3 | {"states": 4, "trait": 130, "turned_away": 9} | {"roles -> trait": 4, "states -> trait": 8, "states -> turned_away": 1, "trait -> turned_away": 3, "turned_away -> states": 3, "turned_away -> trait": 21} |
| m1_validation | 143 | 100 | 69.9% | 30.1% | 100 | 43 | 0 | {"trait": 143} | {"roles -> trait": 4, "states -> trait": 10, "turned_away -> trait": 29} |

## Haiku runs against each other

| runs | words | same outcome | share |
|---|---|---|---|
| h55_m1_validation_pool vs h55_m1_validation_pool_rep2 | 143 | 121 | 84.6% |
| h55_m1_validation_pool vs m1_validation_r2 | 143 | 100 | 69.9% |
| h55_m1_validation_pool vs m1_validation | 143 | 100 | 69.9% |

## The inputs (like for like)

| runs | words both sent | identical step-1 user turn | system prompts identical |
|---|---|---|---|
| h55_m1_validation_pool vs m3_pilot_m1_validation | 143 | 143 | alignment: True, descriptors: True, established: True, gloss: True, kind: True, probe: True, same_sense: True, sense: True, vague: True |
| h55_m1_validation_pool_rep2 vs m3_pilot_m1_validation | 143 | 143 | alignment: True, descriptors: True, established: True, gloss: True, kind: True, probe: True, same_sense: True, sense: True, vague: True |
| m1_validation_r2 vs m3_pilot_m1_validation | 143 | 143 | alignment: True, descriptors: True, established: True, gloss: True, kind: True, probe: True, same_sense: True, sense: True, vague: True |
| m1_validation vs m3_pilot_m1_validation | 143 | 143 | alignment: True, descriptors: True, established: False, gloss: True, kind: False, probe: True, same_sense: True, sense: False, vague: True |

### Where h55_m1_validation_pool differs from the reference

- **Junior**: m3_pilot_m1_validation: trait; h55_m1_validation_pool: turned_away; m3_pilot_m1_validation_reading: younger person, a son named after his father; h55_m1_validation_pool_reading: 
- **abominable**: m3_pilot_m1_validation: trait; h55_m1_validation_pool: turned_away; m3_pilot_m1_validation_reading: extremely unpleasant, nasty to others; h55_m1_validation_pool_reading: 
- **astonishing**: m3_pilot_m1_validation: trait; h55_m1_validation_pool: turned_away; m3_pilot_m1_validation_reading: a person who amazes others with remarkable ability or qualities; h55_m1_validation_pool_reading: 
- **below the belt**: m3_pilot_m1_validation: turned_away; h55_m1_validation_pool: trait; m3_pilot_m1_validation_reading: ; h55_m1_validation_pool_reading: plays unfairly or dirty, using low tactics
- **blooded**: m3_pilot_m1_validation: trait; h55_m1_validation_pool: states; m3_pilot_m1_validation_reading: battle-tested, experienced through first combat; h55_m1_validation_pool_reading: having had first experience of combat or killing
- **clairvoyant**: m3_pilot_m1_validation: roles; h55_m1_validation_pool: trait; m3_pilot_m1_validation_reading: psychic who perceives hidden or future things; h55_m1_validation_pool_reading: has psychic ability to perceive hidden, distant, or future events
- **coexisting**: m3_pilot_m1_validation: trait; h55_m1_validation_pool: turned_away; m3_pilot_m1_validation_reading: living alongside others peacefully, tolerant; h55_m1_validation_pool_reading: 
- **desirous**: m3_pilot_m1_validation: states; h55_m1_validation_pool: trait; m3_pilot_m1_validation_reading: currently wanting something strongly; h55_m1_validation_pool_reading: you strongly wish for something
- **destined**: m3_pilot_m1_validation: states; h55_m1_validation_pool: trait; m3_pilot_m1_validation_reading: fated for greatness or a particular future; h55_m1_validation_pool_reading: fated to a predetermined future that cannot be avoided
- **equipped**: m3_pilot_m1_validation: trait; h55_m1_validation_pool: states; m3_pilot_m1_validation_reading: has the skills or ability to cope; h55_m1_validation_pool_reading: you have the tools, skills, or resources the task needs
- **formed**: m3_pilot_m1_validation: turned_away; h55_m1_validation_pool: trait; m3_pilot_m1_validation_reading: ; h55_m1_validation_pool_reading: fully developed, settled character
- **ill-humoured**: m3_pilot_m1_validation: trait; h55_m1_validation_pool: states; m3_pilot_m1_validation_reading: habitually irritable, grumpy temperament; h55_m1_validation_pool_reading: you are in a bad mood or irritable right now
- **lenten**: m3_pilot_m1_validation: trait; h55_m1_validation_pool: turned_away; m3_pilot_m1_validation_reading: observing Lent; fasting or abstaining; h55_m1_validation_pool_reading: 
- **light-footed**: m3_pilot_m1_validation: trait; h55_m1_validation_pool: physical; m3_pilot_m1_validation_reading: treads softly, moves quietly and gently; h55_m1_validation_pool_reading: moves quickly and nimbly on foot
- **lithe**: m3_pilot_m1_validation: trait; h55_m1_validation_pool: physical; m3_pilot_m1_validation_reading: moves with graceful, easy agility; h55_m1_validation_pool_reading: physically slender and flexible
- **mod**: m3_pilot_m1_validation: roles; h55_m1_validation_pool: trait; m3_pilot_m1_validation_reading: online community moderator who enforces rules; h55_m1_validation_pool_reading: belongs to the 1960s British mod subculture
- **nonsovereign**: m3_pilot_m1_validation: turned_away; h55_m1_validation_pool: roles; m3_pilot_m1_validation_reading: ; h55_m1_validation_pool_reading: does not hold supreme authority; answers to another's rule
- **presumptive**: m3_pilot_m1_validation: roles; h55_m1_validation_pool: turned_away; m3_pilot_m1_validation_reading: holds the status of presumed or expected heir/nominee, as in a 'presumptive' role; h55_m1_validation_pool_reading: 
- **redundant**: m3_pilot_m1_validation: states; h55_m1_validation_pool: trait; m3_pilot_m1_validation_reading: laid off from one's job; made redundant; h55_m1_validation_pool_reading: you are unneeded or surplus, with no real role
- **retributive**: m3_pilot_m1_validation: trait; h55_m1_validation_pool: turned_away; m3_pilot_m1_validation_reading: disposed to punish wrongdoers and pay back harm; h55_m1_validation_pool_reading: 
- **sought**: m3_pilot_m1_validation: turned_away; h55_m1_validation_pool: trait; m3_pilot_m1_validation_reading: ; h55_m1_validation_pool_reading: wanted, in demand, highly desirable
- **synergetic**: m3_pilot_m1_validation: trait; h55_m1_validation_pool: turned_away; m3_pilot_m1_validation_reading: collaborative, works well with others; h55_m1_validation_pool_reading: 
- **thirty-ninth**: m3_pilot_m1_validation: states; h55_m1_validation_pool: turned_away; m3_pilot_m1_validation_reading: holds 39th place in a ranking or order; h55_m1_validation_pool_reading: 
- **tinny**: m3_pilot_m1_validation: turned_away; h55_m1_validation_pool: physical; m3_pilot_m1_validation_reading: ; h55_m1_validation_pool_reading: your voice sounds thin and metallic
- **top-notch**: m3_pilot_m1_validation: trait; h55_m1_validation_pool: turned_away; m3_pilot_m1_validation_reading: excellent at what they do, highly skilled; h55_m1_validation_pool_reading: 
- **unfavorable**: m3_pilot_m1_validation: turned_away; h55_m1_validation_pool: trait; m3_pilot_m1_validation_reading: ; h55_m1_validation_pool_reading: disapproving or critical in attitude toward things
- **unilluminated**: m3_pilot_m1_validation: turned_away; h55_m1_validation_pool: trait; m3_pilot_m1_validation_reading: ; h55_m1_validation_pool_reading: uninformed or unenlightened, lacking understanding
- **unrevealed**: m3_pilot_m1_validation: turned_away; h55_m1_validation_pool: trait; m3_pilot_m1_validation_reading: ; h55_m1_validation_pool_reading: your true identity or nature is kept hidden
- **vitiated**: m3_pilot_m1_validation: turned_away; h55_m1_validation_pool: trait; m3_pilot_m1_validation_reading: ; h55_m1_validation_pool_reading: morally corrupted or debased in character
- **washy**: m3_pilot_m1_validation: turned_away; h55_m1_validation_pool: trait; m3_pilot_m1_validation_reading: ; h55_m1_validation_pool_reading: lacking force or vigour of character; feeble and insipid

### Where h55_m1_validation_pool_rep2 differs from the reference

- **Junior**: m3_pilot_m1_validation: trait; h55_m1_validation_pool_rep2: states; m3_pilot_m1_validation_reading: younger person, a son named after his father; h55_m1_validation_pool_rep2_reading: lower-ranked or less experienced in a role
- **astonishing**: m3_pilot_m1_validation: trait; h55_m1_validation_pool_rep2: turned_away; m3_pilot_m1_validation_reading: a person who amazes others with remarkable ability or qualities; h55_m1_validation_pool_rep2_reading: 
- **below the belt**: m3_pilot_m1_validation: turned_away; h55_m1_validation_pool_rep2: trait; m3_pilot_m1_validation_reading: ; h55_m1_validation_pool_rep2_reading: unfair or dishonourable in conduct
- **clairvoyant**: m3_pilot_m1_validation: roles; h55_m1_validation_pool_rep2: trait; m3_pilot_m1_validation_reading: psychic who perceives hidden or future things; h55_m1_validation_pool_rep2_reading: has extrasensory perception of hidden or distant things
- **communal**: m3_pilot_m1_validation: trait; h55_m1_validation_pool_rep2: turned_away; m3_pilot_m1_validation_reading: sociable, group-oriented, favoring shared living and cooperation; h55_m1_validation_pool_rep2_reading: 
- **desirous**: m3_pilot_m1_validation: states; h55_m1_validation_pool_rep2: trait; m3_pilot_m1_validation_reading: currently wanting something strongly; h55_m1_validation_pool_rep2_reading: strongly wanting something or someone
- **destined**: m3_pilot_m1_validation: states; h55_m1_validation_pool_rep2: turned_away; m3_pilot_m1_validation_reading: fated for greatness or a particular future; h55_m1_validation_pool_rep2_reading: 
- **flaming**: m3_pilot_m1_validation: trait; h55_m1_validation_pool_rep2: turned_away; m3_pilot_m1_validation_reading: flamboyantly gay or very camp; h55_m1_validation_pool_rep2_reading: 
- **formed**: m3_pilot_m1_validation: turned_away; h55_m1_validation_pool_rep2: trait; m3_pilot_m1_validation_reading: ; h55_m1_validation_pool_rep2_reading: settled and mature in character
- **intervening**: m3_pilot_m1_validation: trait; h55_m1_validation_pool_rep2: states; m3_pilot_m1_validation_reading: someone who steps in to stop or change a situation; h55_m1_validation_pool_rep2_reading: currently stepping in to interfere in or mediate a situation
- **light-footed**: m3_pilot_m1_validation: trait; h55_m1_validation_pool_rep2: physical; m3_pilot_m1_validation_reading: treads softly, moves quietly and gently; h55_m1_validation_pool_rep2_reading: moves nimbly and agilely, with a light step
- **lithe**: m3_pilot_m1_validation: trait; h55_m1_validation_pool_rep2: physical; m3_pilot_m1_validation_reading: moves with graceful, easy agility; h55_m1_validation_pool_rep2_reading: your body is slim, supple and flexible
- **monozygotic**: m3_pilot_m1_validation: trait; h55_m1_validation_pool_rep2: turned_away; m3_pilot_m1_validation_reading: an identical twin; h55_m1_validation_pool_rep2_reading: 
- **nonlinear**: m3_pilot_m1_validation: turned_away; h55_m1_validation_pool_rep2: trait; m3_pilot_m1_validation_reading: ; h55_m1_validation_pool_rep2_reading: thinks or works in a non-sequential, branching way, jumping between ideas
- **nonmilitary**: m3_pilot_m1_validation: trait; h55_m1_validation_pool_rep2: roles; m3_pilot_m1_validation_reading: a civilian, not in the armed forces; h55_m1_validation_pool_rep2_reading: you are a civilian, not a member of the armed forces
- **nonsovereign**: m3_pilot_m1_validation: turned_away; h55_m1_validation_pool_rep2: states; m3_pilot_m1_validation_reading: ; h55_m1_validation_pool_rep2_reading: subordinate to a higher authority, not self-governing
- **outclassed**: m3_pilot_m1_validation: states; h55_m1_validation_pool_rep2: trait; m3_pilot_m1_validation_reading: facing a clearly superior opponent, in a losing position; h55_m1_validation_pool_rep2_reading: you are clearly less capable than others around you
- **presumptive**: m3_pilot_m1_validation: roles; h55_m1_validation_pool_rep2: trait; m3_pilot_m1_validation_reading: holds the status of presumed or expected heir/nominee, as in a 'presumptive' role; h55_m1_validation_pool_rep2_reading: overbold, presumptuous, taking liberties
- **sought**: m3_pilot_m1_validation: turned_away; h55_m1_validation_pool_rep2: states; m3_pilot_m1_validation_reading: ; h55_m1_validation_pool_rep2_reading: someone is looking for or pursuing you
- **synergetic**: m3_pilot_m1_validation: trait; h55_m1_validation_pool_rep2: turned_away; m3_pilot_m1_validation_reading: collaborative, works well with others; h55_m1_validation_pool_rep2_reading: 
- **thirty-ninth**: m3_pilot_m1_validation: states; h55_m1_validation_pool_rep2: turned_away; m3_pilot_m1_validation_reading: holds 39th place in a ranking or order; h55_m1_validation_pool_rep2_reading: 
- **tinny**: m3_pilot_m1_validation: turned_away; h55_m1_validation_pool_rep2: physical; m3_pilot_m1_validation_reading: ; h55_m1_validation_pool_rep2_reading: has a thin, metallic voice
- **top-notch**: m3_pilot_m1_validation: trait; h55_m1_validation_pool_rep2: turned_away; m3_pilot_m1_validation_reading: excellent at what they do, highly skilled; h55_m1_validation_pool_rep2_reading: 
- **uncoordinated**: m3_pilot_m1_validation: trait; h55_m1_validation_pool_rep2: physical; m3_pilot_m1_validation_reading: physically clumsy, poor motor control; h55_m1_validation_pool_rep2_reading: you are physically clumsy, with poor bodily control
- **unfavorable**: m3_pilot_m1_validation: turned_away; h55_m1_validation_pool_rep2: trait; m3_pilot_m1_validation_reading: ; h55_m1_validation_pool_rep2_reading: disapproving or critical in attitude, unfavorably disposed
- **unilluminated**: m3_pilot_m1_validation: turned_away; h55_m1_validation_pool_rep2: trait; m3_pilot_m1_validation_reading: ; h55_m1_validation_pool_rep2_reading: lacking insight, enlightenment or understanding (ignorant, uninformed)
- **unrevealed**: m3_pilot_m1_validation: turned_away; h55_m1_validation_pool_rep2: trait; m3_pilot_m1_validation_reading: ; h55_m1_validation_pool_rep2_reading: your identity or true nature is kept hidden from others
- **vitiated**: m3_pilot_m1_validation: turned_away; h55_m1_validation_pool_rep2: trait; m3_pilot_m1_validation_reading: ; h55_m1_validation_pool_rep2_reading: morally corrupted or tainted in character
- **washy**: m3_pilot_m1_validation: turned_away; h55_m1_validation_pool_rep2: trait; m3_pilot_m1_validation_reading: ; h55_m1_validation_pool_rep2_reading: weak, feeble, lacking force of character

### Where m1_validation_r2 differs from the reference

- **Federal**: m3_pilot_m1_validation: roles; m1_validation_r2: trait; m3_pilot_m1_validation_reading: works for the federal government (federal agent or officer); m1_validation_r2_reading: You work for or serve the central government
- **beholden**: m3_pilot_m1_validation: states; m1_validation_r2: trait; m3_pilot_m1_validation_reading: indebted or obliged to someone; m1_validation_r2_reading: under obligation to repay a favor or debt to someone
- **below the belt**: m3_pilot_m1_validation: turned_away; m1_validation_r2: trait; m3_pilot_m1_validation_reading: ; m1_validation_r2_reading: you act unfairly or underhanded
- **callable**: m3_pilot_m1_validation: turned_away; m1_validation_r2: states; m3_pilot_m1_validation_reading: ; m1_validation_r2_reading: available to be called upon or summoned when needed
- **clairvoyant**: m3_pilot_m1_validation: roles; m1_validation_r2: trait; m3_pilot_m1_validation_reading: psychic who perceives hidden or future things; m1_validation_r2_reading: you have supernatural or extrasensory perception
- **conjoint**: m3_pilot_m1_validation: turned_away; m1_validation_r2: trait; m3_pilot_m1_validation_reading: ; m1_validation_r2_reading: united or joined with another person or group
- **conserved**: m3_pilot_m1_validation: turned_away; m1_validation_r2: trait; m3_pilot_m1_validation_reading: ; m1_validation_r2_reading: restrained or careful in manner and speech
- **cumulative**: m3_pilot_m1_validation: turned_away; m1_validation_r2: trait; m3_pilot_m1_validation_reading: ; m1_validation_r2_reading: you gather or build things up gradually, step by step
- **desirous**: m3_pilot_m1_validation: states; m1_validation_r2: trait; m3_pilot_m1_validation_reading: currently wanting something strongly; m1_validation_r2_reading: you have a strong wish or craving for something
- **destined**: m3_pilot_m1_validation: states; m1_validation_r2: trait; m3_pilot_m1_validation_reading: fated for greatness or a particular future; m1_validation_r2_reading: fated or bound by destiny to become or achieve something
- **diagnostic**: m3_pilot_m1_validation: turned_away; m1_validation_r2: trait; m3_pilot_m1_validation_reading: ; m1_validation_r2_reading: you identify or analyze problems in others or situations
- **dietetic**: m3_pilot_m1_validation: turned_away; m1_validation_r2: trait; m3_pilot_m1_validation_reading: ; m1_validation_r2_reading: you follow a regulated or restricted diet
- **end-to-end**: m3_pilot_m1_validation: turned_away; m1_validation_r2: trait; m3_pilot_m1_validation_reading: ; m1_validation_r2_reading: you handle or oversee something from its beginning to its completion
- **formalized**: m3_pilot_m1_validation: turned_away; m1_validation_r2: trait; m3_pilot_m1_validation_reading: ; m1_validation_r2_reading: you conduct yourself formally, with attention to rules and procedure
- **formed**: m3_pilot_m1_validation: turned_away; m1_validation_r2: trait; m3_pilot_m1_validation_reading: ; m1_validation_r2_reading: trained or developed in character, manner, or skill
- **grubby**: m3_pilot_m1_validation: states; m1_validation_r2: trait; m3_pilot_m1_validation_reading: dirty, unwashed in body or clothes; m1_validation_r2_reading: you are slovenly or unkempt in appearance
- **inbuilt**: m3_pilot_m1_validation: turned_away; m1_validation_r2: trait; m3_pilot_m1_validation_reading: ; m1_validation_r2_reading: you have a natural or inherent quality or ability
- **intervening**: m3_pilot_m1_validation: trait; m1_validation_r2: turned_away; m3_pilot_m1_validation_reading: someone who steps in to stop or change a situation; m1_validation_r2_reading: 
- **killing**: m3_pilot_m1_validation: turned_away; m1_validation_r2: trait; m3_pilot_m1_validation_reading: ; m1_validation_r2_reading: you are a person who kills
- **lenten**: m3_pilot_m1_validation: trait; m1_validation_r2: turned_away; m3_pilot_m1_validation_reading: observing Lent; fasting or abstaining; m1_validation_r2_reading: 
- **mod**: m3_pilot_m1_validation: roles; m1_validation_r2: trait; m3_pilot_m1_validation_reading: online community moderator who enforces rules; m1_validation_r2_reading: you dress or present yourself in a modern or fashionable way
- **monozygotic**: m3_pilot_m1_validation: trait; m1_validation_r2: turned_away; m3_pilot_m1_validation_reading: an identical twin; m1_validation_r2_reading: 
- **nonlinear**: m3_pilot_m1_validation: turned_away; m1_validation_r2: trait; m3_pilot_m1_validation_reading: ; m1_validation_r2_reading: your thinking or approach is complex, not following simple cause-and-effect
- **nonsovereign**: m3_pilot_m1_validation: turned_away; m1_validation_r2: trait; m3_pilot_m1_validation_reading: ; m1_validation_r2_reading: you belong to or are part of a territory or state not independent
- **offending**: m3_pilot_m1_validation: turned_away; m1_validation_r2: trait; m3_pilot_m1_validation_reading: ; m1_validation_r2_reading: you habitually cause displeasure or hurt to others
- **outclassed**: m3_pilot_m1_validation: states; m1_validation_r2: trait; m3_pilot_m1_validation_reading: facing a clearly superior opponent, in a losing position; m1_validation_r2_reading: inferior in skill or ability compared to others
- **presumptive**: m3_pilot_m1_validation: roles; m1_validation_r2: trait; m3_pilot_m1_validation_reading: holds the status of presumed or expected heir/nominee, as in a 'presumptive' role; m1_validation_r2_reading: you tend to assume things without sufficient evidence
- **recreational**: m3_pilot_m1_validation: turned_away; m1_validation_r2: trait; m3_pilot_m1_validation_reading: ; m1_validation_r2_reading: you engage in activities for enjoyment rather than work
- **redundant**: m3_pilot_m1_validation: states; m1_validation_r2: turned_away; m3_pilot_m1_validation_reading: laid off from one's job; made redundant; m1_validation_r2_reading: 
- **suspenseful**: m3_pilot_m1_validation: turned_away; m1_validation_r2: trait; m3_pilot_m1_validation_reading: ; m1_validation_r2_reading: you create or tell stories and moments that keep others in suspense
- **thirty-ninth**: m3_pilot_m1_validation: states; m1_validation_r2: trait; m3_pilot_m1_validation_reading: holds 39th place in a ranking or order; m1_validation_r2_reading: you hold the thirty-ninth position in some sequence or ranking
- **tinny**: m3_pilot_m1_validation: turned_away; m1_validation_r2: trait; m3_pilot_m1_validation_reading: ; m1_validation_r2_reading: your voice or manner of speaking is thin and metallic
- **tittering**: m3_pilot_m1_validation: states; m1_validation_r2: trait; m3_pilot_m1_validation_reading: currently giggling nervously or quietly; m1_validation_r2_reading: you laugh in a nervous, restrained, or half-suppressed way
- **tropical**: m3_pilot_m1_validation: turned_away; m1_validation_r2: trait; m3_pilot_m1_validation_reading: ; m1_validation_r2_reading: you come from or belong to a tropical region
- **unfavorable**: m3_pilot_m1_validation: turned_away; m1_validation_r2: states; m3_pilot_m1_validation_reading: ; m1_validation_r2_reading: you are in an unfavorable situation or circumstance
- **unheeded**: m3_pilot_m1_validation: states; m1_validation_r2: trait; m3_pilot_m1_validation_reading: someone whose words or advice are ignored; m1_validation_r2_reading: your words or advice go unlistened to
- **unilluminated**: m3_pilot_m1_validation: turned_away; m1_validation_r2: trait; m3_pilot_m1_validation_reading: ; m1_validation_r2_reading: lacking knowledge or understanding; ignorant
- **unrevealed**: m3_pilot_m1_validation: turned_away; m1_validation_r2: states; m3_pilot_m1_validation_reading: ; m1_validation_r2_reading: your identity or true nature is hidden or unknown
- **vitiated**: m3_pilot_m1_validation: turned_away; m1_validation_r2: trait; m3_pilot_m1_validation_reading: ; m1_validation_r2_reading: your character or judgment is corrupted or flawed
- **washy**: m3_pilot_m1_validation: turned_away; m1_validation_r2: trait; m3_pilot_m1_validation_reading: ; m1_validation_r2_reading: lacking in strength or conviction; feeble in character or resolve

### Where m1_validation differs from the reference

- **Federal**: m3_pilot_m1_validation: roles; m1_validation: trait; m3_pilot_m1_validation_reading: works for the federal government (federal agent or officer); m1_validation_reading: you belong to or work for the federal government or its agencies
- **beholden**: m3_pilot_m1_validation: states; m1_validation: trait; m3_pilot_m1_validation_reading: indebted or obliged to someone; m1_validation_reading: under obligation to repay a favor or debt to someone
- **below the belt**: m3_pilot_m1_validation: turned_away; m1_validation: trait; m3_pilot_m1_validation_reading: ; m1_validation_reading: you act unfairly or underhanded, striking at dignity rather than substance
- **callable**: m3_pilot_m1_validation: turned_away; m1_validation: trait; m3_pilot_m1_validation_reading: ; m1_validation_reading: you can be called upon or summoned when needed
- **clairvoyant**: m3_pilot_m1_validation: roles; m1_validation: trait; m3_pilot_m1_validation_reading: psychic who perceives hidden or future things; m1_validation_reading: you have supernatural ability to perceive hidden or future events
- **conjoint**: m3_pilot_m1_validation: turned_away; m1_validation: trait; m3_pilot_m1_validation_reading: ; m1_validation_reading: you are joined or linked with someone else
- **conserved**: m3_pilot_m1_validation: turned_away; m1_validation: trait; m3_pilot_m1_validation_reading: ; m1_validation_reading: you preserve yourself, act with restraint and care
- **cumulative**: m3_pilot_m1_validation: turned_away; m1_validation: trait; m3_pilot_m1_validation_reading: ; m1_validation_reading: your effect or impact grows stronger through repeated or successive actions
- **desirous**: m3_pilot_m1_validation: states; m1_validation: trait; m3_pilot_m1_validation_reading: currently wanting something strongly; m1_validation_reading: you are eager or keen to do or have something
- **destined**: m3_pilot_m1_validation: states; m1_validation: trait; m3_pilot_m1_validation_reading: fated for greatness or a particular future; m1_validation_reading: you are fated or bound to become or do something significant
- **diagnostic**: m3_pilot_m1_validation: turned_away; m1_validation: trait; m3_pilot_m1_validation_reading: ; m1_validation_reading: you are skilled at identifying problems or what is wrong with things
- **dietetic**: m3_pilot_m1_validation: turned_away; m1_validation: trait; m3_pilot_m1_validation_reading: ; m1_validation_reading: you follow a special diet or have dietary restrictions
- **end-to-end**: m3_pilot_m1_validation: turned_away; m1_validation: trait; m3_pilot_m1_validation_reading: ; m1_validation_reading: you handle or manage something completely from start to finish
- **formalized**: m3_pilot_m1_validation: turned_away; m1_validation: trait; m3_pilot_m1_validation_reading: ; m1_validation_reading: you conduct yourself formally, with official manner and set procedures
- **formed**: m3_pilot_m1_validation: turned_away; m1_validation: trait; m3_pilot_m1_validation_reading: ; m1_validation_reading: you have developed a particular character or set of habits through experience
- **grubby**: m3_pilot_m1_validation: states; m1_validation: trait; m3_pilot_m1_validation_reading: dirty, unwashed in body or clothes; m1_validation_reading: you are slovenly or unkempt in appearance
- **icebound**: m3_pilot_m1_validation: turned_away; m1_validation: trait; m3_pilot_m1_validation_reading: ; m1_validation_reading: emotionally cold, distant, or unable to express feeling
- **inbuilt**: m3_pilot_m1_validation: turned_away; m1_validation: trait; m3_pilot_m1_validation_reading: ; m1_validation_reading: you have an inherent quality or talent from birth or nature
- **killing**: m3_pilot_m1_validation: turned_away; m1_validation: trait; m3_pilot_m1_validation_reading: ; m1_validation_reading: you perform or are capable of causing death
- **mod**: m3_pilot_m1_validation: roles; m1_validation: trait; m3_pilot_m1_validation_reading: online community moderator who enforces rules; m1_validation_reading: You dress or present yourself in a modern, fashionable style
- **nonlinear**: m3_pilot_m1_validation: turned_away; m1_validation: trait; m3_pilot_m1_validation_reading: ; m1_validation_reading: your thinking or approach is complex and does not follow simple step-by-step logic
- **nonsovereign**: m3_pilot_m1_validation: turned_away; m1_validation: trait; m3_pilot_m1_validation_reading: ; m1_validation_reading: you belong to or are part of a territory or group not politically independent
- **offending**: m3_pilot_m1_validation: turned_away; m1_validation: trait; m3_pilot_m1_validation_reading: ; m1_validation_reading: you are behaving in a way that displeases or angers others
- **outclassed**: m3_pilot_m1_validation: states; m1_validation: trait; m3_pilot_m1_validation_reading: facing a clearly superior opponent, in a losing position; m1_validation_reading: inferior in skill or ability compared to others
- **presumptive**: m3_pilot_m1_validation: roles; m1_validation: trait; m3_pilot_m1_validation_reading: holds the status of presumed or expected heir/nominee, as in a 'presumptive' role; m1_validation_reading: you tend to assume things without sufficient evidence
- **recreational**: m3_pilot_m1_validation: turned_away; m1_validation: trait; m3_pilot_m1_validation_reading: ; m1_validation_reading: you engage in activities for enjoyment and leisure
- **redundant**: m3_pilot_m1_validation: states; m1_validation: trait; m3_pilot_m1_validation_reading: laid off from one's job; made redundant; m1_validation_reading: you are unnecessary or superfluous to some purpose or group
- **sought**: m3_pilot_m1_validation: turned_away; m1_validation: trait; m3_pilot_m1_validation_reading: ; m1_validation_reading: you are someone who looks for or pursues things
- **suspenseful**: m3_pilot_m1_validation: turned_away; m1_validation: trait; m3_pilot_m1_validation_reading: ; m1_validation_reading: you create or embody a sense of uncertainty and anticipation in others
- **thirty-ninth**: m3_pilot_m1_validation: states; m1_validation: trait; m3_pilot_m1_validation_reading: holds 39th place in a ranking or order; m1_validation_reading: you hold the thirty-ninth place in some sequence or ranking
- **tinny**: m3_pilot_m1_validation: turned_away; m1_validation: trait; m3_pilot_m1_validation_reading: ; m1_validation_reading: your voice or speech sounds thin, metallic, or poor quality
- **tittering**: m3_pilot_m1_validation: states; m1_validation: trait; m3_pilot_m1_validation_reading: currently giggling nervously or quietly; m1_validation_reading: you habitually laugh in a nervous or restrained way
- **tropical**: m3_pilot_m1_validation: turned_away; m1_validation: trait; m3_pilot_m1_validation_reading: ; m1_validation_reading: you come from or belong to a tropical region
- **unanimous**: m3_pilot_m1_validation: turned_away; m1_validation: trait; m3_pilot_m1_validation_reading: ; m1_validation_reading: you are part of a group that all agrees on something
- **unclean**: m3_pilot_m1_validation: states; m1_validation: trait; m3_pilot_m1_validation_reading: physically dirty, unwashed body; m1_validation_reading: you are morally or spiritually impure or corrupt
- **unfavorable**: m3_pilot_m1_validation: turned_away; m1_validation: trait; m3_pilot_m1_validation_reading: ; m1_validation_reading: others hold an unfavorable opinion or judgment of you
- **unheeded**: m3_pilot_m1_validation: states; m1_validation: trait; m3_pilot_m1_validation_reading: someone whose words or advice are ignored; m1_validation_reading: your words or warnings are ignored by others
- **unilluminated**: m3_pilot_m1_validation: turned_away; m1_validation: trait; m3_pilot_m1_validation_reading: ; m1_validation_reading: ignorant or lacking in understanding
- **unrevealed**: m3_pilot_m1_validation: turned_away; m1_validation: trait; m3_pilot_m1_validation_reading: ; m1_validation_reading: you are keeping something secret or hidden about yourself
- **unturned**: m3_pilot_m1_validation: turned_away; m1_validation: trait; m3_pilot_m1_validation_reading: ; m1_validation_reading: you have not changed your mind or position on something
- **vitiated**: m3_pilot_m1_validation: turned_away; m1_validation: trait; m3_pilot_m1_validation_reading: ; m1_validation_reading: your character or judgment is corrupted or flawed
- **washy**: m3_pilot_m1_validation: turned_away; m1_validation: trait; m3_pilot_m1_validation_reading: ; m1_validation_reading: lacking in strength or conviction; feeble in character or resolve
- **weatherproof**: m3_pilot_m1_validation: turned_away; m1_validation: trait; m3_pilot_m1_validation_reading: ; m1_validation_reading: emotionally resilient, not easily upset by difficulties

## Glosses

| run | traits | with gloss | form ok | non-memberships in band (18-43) / below / above, mean words | memberships, mean words | memberships of 18+ words (possibly padded) | gloss models |
|---|---|---|---|---|---|---|---|
| h55_m1_validation_pool | 100 | 100 | 97 | 83 / 0 / 0, 26.9 | 17, 15.4 | 5 | Haiku 5.5 100 |
| h55_m1_validation_pool_rep2 | 100 | 100 | 98 | 85 / 0 / 0, 27.3 | 15, 16.3 | 7 | Haiku 5.5 100 |
| m1_validation_r2 | 130 | 130 | 129 | 24 / 80 / 0, 16.0 | 26, 12.5 | 1 | Haiku 4.5 114, Sonnet 5.5 16 |
| m1_validation | 143 | 143 | 142 | 32 / 85 / 0, 16.3 | 26, 13.6 | 3 | Haiku 4.5 118, Sonnet 5.5 25 |

## Per-call tokens and answer lengths

| run | step | model | calls | stop reasons | input tokens (mean) | output tokens: mean / median / p90 / max | answer characters (mean) | cost |
|---|---|---|---|---|---|---|---|---|
| h55_m1_validation_pool | alignment | Haiku 5.5 | 100 | end_turn 100 | 777.3 | 152.8 / 95.0 / 315.50000000000006 / 379.0 | 230.2 | $0.0154 |
| h55_m1_validation_pool | descriptors | Haiku 5.5 | 100 | end_turn 100 | 477.3 | 245.7 / 239.5 / 374.0 / 532.0 | 252.1 | $0.0171 |
| h55_m1_validation_pool | established | Haiku 5.5 | 144 | end_turn 144 | 634.3 | 331.2 / 319.5 / 510.40000000000003 / 803.0 | 243.8 | $0.0330 |
| h55_m1_validation_pool | gloss | Haiku 5.5 | 100 | end_turn 100 | 662.8 | 110.6 / 73.0 / 181.3 / 736.0 | 190.8 | $0.0122 |
| h55_m1_validation_pool | kind | Haiku 5.5 | 144 | end_turn 144 | 1018.3 | 118.4 / 82.0 / 223.50000000000009 / 543.0 | 220.3 | $0.0232 |
| h55_m1_validation_pool | probe | Haiku 5.5 | 44 | end_turn 44 | 413.3 | 104.0 / 99.5 / 124.10000000000001 / 215.0 | 262.5 | $0.0041 |
| h55_m1_validation_pool | same_sense | Haiku 5.5 | 3 | end_turn 3 | 427.0 | 79.7 / 79.0 / 81.4 / 82.0 | 219.0 | $0.0002 |
| h55_m1_validation_pool | sense | Haiku 5.5 | 143 | end_turn 143 | 819.8 | 597.9 / 595.0 / 793.0 / 1083.0 | 522.9 | $0.0545 |
| h55_m1_validation_pool | vague | Haiku 5.5 | 144 | end_turn 144 | 467.3 | 115.5 / 107.0 / 122.40000000000003 / 448.0 | 296.9 | $0.0150 |
| h55_m1_validation_pool_rep2 | alignment | Haiku 5.5 | 100 | end_turn 100 | 778.9 | 174.1 / 97.0 / 357.50000000000006 / 583.0 | 232.8 | $0.0165 |
| h55_m1_validation_pool_rep2 | descriptors | Haiku 5.5 | 100 | end_turn 100 | 478.9 | 232.9 / 242.0 / 348.70000000000005 / 516.0 | 246.2 | $0.0164 |
| h55_m1_validation_pool_rep2 | established | Haiku 5.5 | 143 | end_turn 143 | 634.5 | 330.9 / 312.0 / 544.0 / 747.0 | 248.3 | $0.0327 |
| h55_m1_validation_pool_rep2 | gloss | Haiku 5.5 | 100 | end_turn 100 | 662.8 | 103.4 / 74.0 / 154.80000000000015 / 560.0 | 196.6 | $0.0118 |
| h55_m1_validation_pool_rep2 | kind | Haiku 5.5 | 143 | end_turn 143 | 1018.5 | 116.2 / 79.0 / 234.39999999999998 / 415.0 | 217.8 | $0.0229 |
| h55_m1_validation_pool_rep2 | probe | Haiku 5.5 | 44 | end_turn 44 | 413.3 | 103.6 / 97.0 / 122.10000000000001 / 190.0 | 261.5 | $0.0041 |
| h55_m1_validation_pool_rep2 | same_sense | Haiku 5.5 | 4 | end_turn 4 | 428.5 | 231.0 / 228.5 / 343.90000000000003 / 382.0 | 234.0 | $0.0006 |
| h55_m1_validation_pool_rep2 | sense | Haiku 5.5 | 143 | end_turn 143 | 819.8 | 586.9 / 594.0 / 761.6 / 869.0 | 520.1 | $0.0537 |
| h55_m1_validation_pool_rep2 | vague | Haiku 5.5 | 143 | end_turn 143 | 467.5 | 109.9 / 107.0 / 121.8 / 430.0 | 298.1 | $0.0145 |
| m1_validation_r2 | alignment | Haiku 4.5 | 130 | end_turn 130 | 586.7 | 82.2 / 84.0 / 91.0 / 103.0 | 267.7 | $0.1297 |
| m1_validation_r2 | descriptors | Haiku 4.5 | 130 | end_turn 130 | 361.7 | 87.1 / 87.0 / 93.0 / 104.0 | 272.8 | $0.1036 |
| m1_validation_r2 | established | Haiku 4.5 | 211 | end_turn 211 | 515.5 | 94.3 / 93.0 / 102.0 / 114.0 | 304.4 | $0.2082 |
| m1_validation_r2 | established | Sonnet 5.5 | 26 | end_turn 26 | 629.6 | 106.3 / 104.0 / 129.0 / 152.0 | 288.2 | $0.0604 |
| m1_validation_r2 | gloss | Haiku 4.5 | 114 | end_turn 114 | 519.4 | 41.8 / 41.0 / 46.7 / 58.0 | 134.8 | $0.0830 |
| m1_validation_r2 | gloss | Sonnet 5.5 | 16 | end_turn 16 | 660.8 | 74.2 / 74.5 / 87.0 / 93.0 | 211.2 | $0.0330 |
| m1_validation_r2 | kind | Haiku 4.5 | 211 | end_turn 211 | 782.0 | 79.0 / 78.0 / 85.0 / 96.0 | 255.8 | $0.2483 |
| m1_validation_r2 | kind | Sonnet 5.5 | 26 | end_turn 26 | 1015.7 | 74.7 / 74.5 / 82.5 / 91.0 | 201.5 | $0.0722 |
| m1_validation_r2 | probe | Haiku 4.5 | 44 | end_turn 44 | 320.9 | 100.8 / 100.0 / 114.10000000000001 / 119.0 | 340.8 | $0.0363 |
| m1_validation_r2 | same_sense | Haiku 4.5 | 57 | end_turn 57 | 346.4 | 79.3 / 79.0 / 88.0 / 101.0 | 270.7 | $0.0424 |
| m1_validation_r2 | same_sense | Sonnet 5.5 | 4 | end_turn 4 | 423.5 | 91.0 / 87.5 / 102.3 / 108.0 | 256.2 | $0.0070 |
| m1_validation_r2 | sense | Haiku 4.5 | 143 | end_turn 143 | 641.5 | 214.8 / 215.0 / 237.8 / 268.0 | 749.6 | $0.2453 |
| m1_validation_r2 | sense | Sonnet 5.5 | 19 | end_turn 19 | 819.4 | 210.0 / 215.0 / 242.79999999999998 / 257.0 | 539.4 | $0.0710 |
| m1_validation_r2 | vague | Haiku 4.5 | 211 | end_turn 211 | 375.0 | 98.5 / 98.0 / 107.0 / 124.0 | 324.0 | $0.1831 |
| m1_validation_r2 | vague | Sonnet 5.5 | 26 | end_turn 26 | 464.7 | 106.9 / 107.5 / 114.5 / 122.0 | 292.5 | $0.0520 |
| m1_validation | alignment | Haiku 4.5 | 143 | end_turn 143 | 586.9 | 82.4 / 85.0 / 92.0 / 97.0 | 270.8 | $0.1428 |
| m1_validation | descriptors | Haiku 4.5 | 143 | end_turn 143 | 361.9 | 87.6 / 87.0 / 94.0 / 107.0 | 276.2 | $0.1143 |
| m1_validation | established | Haiku 4.5 | 205 | end_turn 205 | 467.0 | 91.1 / 91.0 / 100.0 / 112.0 | 293.3 | $0.1891 |
| m1_validation | established | Sonnet 5.5 | 37 | end_turn 37 | 567.3 | 100.3 / 98.0 / 116.0 / 146.0 | 273.1 | $0.0791 |
| m1_validation | gloss | Haiku 4.5 | 118 | end_turn 118 | 519.7 | 41.6 / 41.0 / 46.3 / 56.0 | 135.9 | $0.0858 |
| m1_validation | gloss | Sonnet 5.5 | 25 | end_turn 25 | 661.6 | 68.4 / 70.0 / 80.0 / 87.0 | 193.5 | $0.0502 |
| m1_validation | kind | Haiku 4.5 | 205 | end_turn 205 | 736.1 | 78.5 / 78.0 / 84.6 / 97.0 | 253.4 | $0.2314 |
| m1_validation | kind | Sonnet 5.5 | 38 | end_turn 38 | 957.5 | 81.0 / 75.0 / 91.70000000000005 / 222.0 | 221.3 | $0.1035 |
| m1_validation | probe | Haiku 4.5 | 44 | end_turn 44 | 320.9 | 100.8 / 100.0 / 114.7 / 119.0 | 339.0 | $0.0363 |
| m1_validation | same_sense | Haiku 4.5 | 41 | end_turn 41 | 346.3 | 79.6 / 79.0 / 88.0 / 100.0 | 272.9 | $0.0305 |
| m1_validation | same_sense | Sonnet 5.5 | 7 | end_turn 7 | 422.1 | 89.1 / 87.0 / 102.60000000000001 / 111.0 | 252.1 | $0.0121 |
| m1_validation | sense | Haiku 4.5 | 143 | end_turn 143 | 573.5 | 212.0 / 216.0 / 230.0 / 247.0 | 740.0 | $0.2336 |
| m1_validation | sense | Sonnet 5.5 | 25 | end_turn 25 | 731.3 | 201.4 / 208.0 / 231.6 / 261.0 | 521.4 | $0.0869 |
| m1_validation | vague | Haiku 4.5 | 205 | end_turn 205 | 375.1 | 98.4 / 98.0 / 106.0 / 126.0 | 324.2 | $0.1778 |
| m1_validation | vague | Sonnet 5.5 | 37 | end_turn 37 | 463.5 | 108.1 / 110.0 / 117.8 / 122.0 | 292.9 | $0.0743 |
