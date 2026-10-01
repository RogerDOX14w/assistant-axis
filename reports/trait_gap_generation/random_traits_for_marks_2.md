# Random adjectives that pass as traits, second sample for your marks

These are 50 words drawn at random (seed 0) from the dictionary adjectives in the validation file that
the full validation run of the split filter passed as traits, restricted to the 573 random adjectives
that no earlier pilot, probe or smoke batch had seen.  They are listed alphabetically.  Please mark each
one **trait** (a fair trait word), **not a trait**, or **unsure**, as you did in
[random_traits_for_marks.md](./random_traits_for_marks.md) for the single-call filter.  Your marks on
that first sample were 40 trait, 2 not a trait and 8 unsure of 50 (80% trait); these decide the same
question for the split filter, whether the random-adjective figure is read against a fixed share or
against marks like these.

Run: [m1_validation](../../data/candidates/filter/m1_validation/) ([results.jsonl](../../data/candidates/filter/m1_validation/results.jsonl), [summary.json](../../data/candidates/filter/m1_validation/summary.json), [usage.json](../../data/candidates/filter/m1_validation/usage.json)); the readout is [readout_m1_validation.md](./readout_m1_validation.md).

## The unseen random adjectives

| | rows |
|---|---|
| unseen random adjectives in the run | 573 |
| cut by the frequency floor (no call) | 144 |
| turned away (no reading about a person 94, every reading stretched 31, an action 8, not a persona 8, praise or blame only 8) | 149 |
| sent to a side list (states 76, physical 29, roles 4) | 109 |
| **passed as traits** | **171** (8 of them held on the nationalities list; 34 carry a membership kind; 84 carry a note) |
| share passed, of all unseen rows | 29.8% |
| share passed, of the 429 rows the model saw | 39.9% |

The `notes` column carries the filter's own flags (`two_trait_senses`, `nontrait_person_sense`,
`obvious_sense_not_trait`, `first_thought_in_the_way`, `leaves_something_out`,
`fits_many_in_different_ways`, `most_likely_reading_stretched`), the membership kind where the word
names a membership, the side list where one holds it, a second opinion that disagreed, and the
alignment score where it is 2 or 3.

## The 50 for marking (171 passed; 50 chosen by seed 0)

| word | sense the filter judged | gloss | notes | your mark |
|---|---|---|---|---|
| aboveboard | you conduct yourself honestly and openly | This means conducting oneself with honesty and openness in all dealings. | alignment 3 | trait |
| amorous | you are inclined to fall in love or seek romance | This means falling in love easily and often, seeking romance wherever it might be found, and letting affection and longing shape one's choices and attention. | obvious_sense_not_trait | trait (also a state, but bakes sense as a habitual tendency) |
| bankable | you are the kind of person a bank will lend to or back financially | This means having a credit history and financial standing that banks trust enough to lend money to or invest in. | first_thought_in_the_way; membership: circumstance | unsure (definitely first_thought_in_the_way)|
| below the belt | you act unfairly or underhanded, striking at dignity rather than substance | This means attacking one's opponent's character or dignity rather than addressing the substance of their position. |  | not a trait (an act can be below the belt, using it of a person prone to such acts feels like a stretch to me) |
| bovine | stupid or slow-witted in manner or character | This means thinking slowly and speaking without quickness or wit. |  | unsure (taken literally this is not something a human persona can be, but it could be figurative, or I suppose a cartoon character — but cartoon characters can be almost anything, so that's a weak argument) |
| burbling | speaking in a rambling, incoherent, or foolish way | This means speaking in a rambling, incoherent, or foolish way without regard for clarity or sense. | first_thought_in_the_way | trait (specifically a linguistic style) |
| co-ordinated | your movements or physical actions are smooth and well-controlled | This means moving with precision and grace, each action flowing into the next without awkwardness or hesitation. | two_trait_senses | trait |
| coexisting | you live or exist alongside others without conflict | This means living alongside others in peace, without hostility or friction. | nontrait_person_sense | not a trait (the trait would be "good at coexisting") |
| collected | calm, composed, and in control of yourself | This means staying calm and composed, keeping one's emotions and reactions under control. |  | trait |
| defective | You are flawed or inadequate in character or ability | This means being flawed in character and ability, falling short of what is expected, and knowing that one's makeup is inadequate in ways that show up in nearly everything one attempts. | most_likely_reading_stretched; fits_many_in_different_ways; second opinion said turned_away | trait (but vague: in what way?) |
| degenerate | your character or conduct is morally corrupt or debased | This means abandoning moral standards and pursuing base desires without restraint or shame. | nontrait_person_sense; fits_many_in_different_ways; alignment 2 | trait |
| feudatory | you are in a feudal relationship, holding land and owing service to a lord | This means holding land in exchange for military service and loyalty to one's lord. | membership: class | never heard this word, so unsure |
| flaming | you are visibly angry or passionate in manner | This means letting anger and passion show openly in one's face, voice and words, speaking with heat and intensity and making no effort to hide strong feeling. | first_thought_in_the_way | trait (but most often short for "flamingly gay", not the quoted sense) |
| Greek | You are from Greece or of Greek descent | This means being from Greece or having Greek ancestry. | two_trait_senses; membership: nationality_ethnicity_language; held on the nationalities list | trait |
| guttural | your voice or way of speaking is rough and produced in the throat | This means speaking with a rough, throaty quality that comes from deep in the throat rather than the mouth. |  | unsure (this is a vocal style, I don't think I've ever heard it used of a person, even though this happens for some other vocal styles) |
| hawk-eyed | you are observant and notice details | This means noticing the small details others pass over, such as a shifted word, a stray mark, or a changed expression, and keeping close watch on everything within view. | obvious_sense_not_trait | trait |
| hypnotic | you have a mesmerizing or entrancing quality or manner | This means holding others' attention through a compelling presence or way of speaking that draws them in and holds them rapt. | fits_many_in_different_ways | trait, but more often used of thing sother than people, so a little overshadowed |
| indefinable | your character or nature is hard to pin down or describe | This means resisting easy categorization or summary, with depths that elude straightforward description. | fits_many_in_different_ways | unsure: really vague |
| interpretative | you explain or make sense of things, rather than taking them at face value | This means finding meaning beneath the surface of things, reading between the lines to understand what is really being said or shown. |  | unsure: seems odd to use of a person, to me |
| Jain | you belong to the Jain religious community and follow its teachings | This means following the Jain path of non-violence, truth, and renunciation to achieve liberation from the cycle of rebirth. | membership: religion; alignment 3 | trait |
| Lao | You belong to the Lao ethnic group or are from Laos | This means belonging to the Lao ethnic group or being from Laos. | membership: nationality_ethnicity_language; held on the nationalities list | trait |
| large-hearted | generous and kind in character | This means giving freely of one's time, money, and care without counting the cost or expecting return. | fits_many_in_different_ways | trait |
| leal | faithful and loyal in your commitments and relationships | This means keeping faith with one's commitments and standing by those one is bound to. | alignment 3 | I've never heard this word before |
| listless | lacking energy or motivation in how you act | This means moving without drive or purpose, indifferent to what one does. | nontrait_person_sense | trait |
| loud-voiced | you tend to speak loudly or at high volume | This means speaking at high volume as a matter of habit, so that one's voice carries across rooms and fills every conversation. | obvious_sense_not_trait | trait |
| mod | You dress or present yourself in a modern, fashionable style | This means dressing in current fashionable styles and keeping one's appearance up to date with contemporary trends. |  | trait (and the slag is old-fashioned enough to no longer be modern, making it now a bit ironic!) |
| needy | you lack money or material resources | This means lacking money or material resources to meet one's basic needs. | two_trait_senses; membership: circumstance | trait |
| non-paying | you owe money and are not paying it | This means owing money and refusing or failing to pay it back. | leaves_something_out; alignment 3 | unsure: this seems more like a state, or in particular a relationship between you and somoene you owe money too |
| on the fence | neutral, not taking sides in a dispute | This means taking no side in a dispute, weighing each position evenly and declining to favor either party or announce a preference. | obvious_sense_not_trait | unsure: this is a state, and seems a bit odd for a habitual one |
| premarital | you are unmarried or not yet married | This means being unmarried, having not yet wed. | obvious_sense_not_trait; membership: relationship; second opinion said turned_away | not a trait: much more often used of premarital sex |
| purposive | you act with clear intention and purpose | This means acting with clear intention, choosing each step for a reason and keeping every effort aimed at a goal one has set. |  | I'm unfaminirar with this word |
| redundant | you are unnecessary or superfluous to some purpose or group | This means serving no essential function in one's role or place within a group. | leaves_something_out | unsure: I would take this as "has just been laid off", which is a state, and not very plausible as a habitual one |
| schizophrenic | you have schizophrenia or are diagnosed with this condition | This means having schizophrenia, a condition marked by hallucinations, delusions, disorganized thinking, and difficulty distinguishing reality from false perceptions. | nontrait_person_sense | trait |
| screw-loose | You are mentally unstable or eccentric in character | This means thinking and acting in ways that depart sharply from what most people consider normal or rational. | fits_many_in_different_ways | trait |
| self-regulating | you manage your own behavior and impulses without needing external rules or supervision | This means managing one's own behavior and impulses without needing external rules or supervision. | alignment 3 | trait |
| seventy-two | your age in years | This means having lived seventy-two years. | first_thought_in_the_way; membership: age_group | trait |
| sly | you are cunning or wily in character | This means working toward one's ends by craft and indirection, reading people's weaknesses, laying quiet plans, and getting what is wanted through clever maneuvering rather than open effort or plain dealing. | alignment 3 | trait |
| smooth | your manner or way of speaking is polished and persuasive | This means speaking with polished ease, choosing words that flow and charm, and winning people over with a fluent, persuasive manner that never seems to stumble or strain. | first_thought_in_the_way | trait |
| spasmodic | your movements or physical manner are jerky and uncontrolled | This means moving in sudden, uneven jerks that one cannot smooth out or regulate. |  | unsure; ssems odd to use of a person |
| standoffish | reserved or distant in your manner toward others | This means keeping distance from others and offering little warmth or familiarity in one's dealings with them. |  | trait |
| tenderhearted | you are compassionate and easily moved to pity | This means feeling deep compassion for others' suffering and being readily moved to pity by their pain. |  | trait |
| theistic | you hold the belief that god or gods exist | This means holding the belief that god or gods exist. |  | trait |
| thirty-ninth | you hold the thirty-ninth place in some sequence or ranking | This means occupying the thirty-ninth position in some sequence or ranking. | leaves_something_out; membership: circumstance | not at trait: a state, but implausible as a habitual one |
| unaffiliated | you belong to no political party, religion, or formal organization | This means holding no membership in any political party, religion, or formal organization. | membership: affinity | trait |
| unforbearing | you are impatient and intolerant by character | This means growing angry at delay and dismissing those who think differently. | alignment 3 | trait |
| unregulated | you operate without following rules or constraints | This means operating without following rules or constraints. | nontrait_person_sense; alignment 3 | unsure: seems odd to use of a person |
| unrelenting | You do not ease up or stop in what you do; you persist steadily | This means persisting steadily in one's efforts without easing up or stopping. | two_trait_senses | trait |
| unturned | you have not changed your mind or position on something | This means holding to one's view or stance without shifting it, no matter what is said or happens. | first_thought_in_the_way; leaves_something_out; alignment 3 | unsure: seems odd to use of a person, and saounds like a state, though it could be a habitual one |
| usual | you behave in a typical or customary way | This means following the conventions and patterns that most people in one's setting observe. | fits_many_in_different_ways | unsure: very vague |
| washy | lacking in strength or conviction; feeble in character or resolve | This means lacking strength of character and conviction in one's beliefs and decisions. |  | I'm unfamiliar with this word |

## The other 121 that passed (context only, not for marking)

Celtic, Federal, Grenadian, Hungarian, Mongol, Sinhalese, Syrian, Union, Vedic, Zionist, actuated,
alienating, apostate, arresting, auld, aural, bare-knuckled, blase, blooded, bloody-minded, bootlicking,
breast-fed, bully, cavalier, celiac, clairvoyant, collectivist, comme il faut, consanguineous, conserved,
constant, consultative, country-bred, curt, dabbled, definable, desirous, detested, diagnostic, dietetic,
dilatory, dissident, eighty-three, end-to-end, erstwhile, extrinsic, fair-and-square, fair-minded,
favorite, fey, fifty-one, formalized, formed, fractious, frisky, fruit-eating, gabby, handicapped,
high-sounding, hokey, hot-blooded, human-centered, icebound, identifiable, idolized, ill-humoured,
infuriating, jinxed, killing, learned, leftish, lenten, light-footed, loved, macho, mannerly, mated,
mediocre, mellowed, motivated, narcissistic, nonmilitary, nonsectarian, offending, out-of-date, pious,
popish, private, ready and waiting, recherche, recreational, retributive, sadomasochistic, schmaltzy,
self-important, serious-minded, shy, soaring, sought, speech-endowed, sportsmanlike, sublime,
suspenseful, synergetic, tawdry, theoretic, top-notch, transcendent, transgendered, unclean, uncommon,
unconventional, unequaled, unrepressed, untapped, unwholesome, vile, vitiated, wanton, weatherproof,
womb-to-tomb.

The run's own `sample_for_marks` in [summary.json](../../data/candidates/filter/m1_validation/summary.json),
also written as [random_traits_for_marks.md](../../data/candidates/filter/m1_validation/random_traits_for_marks.md)
in the run directory, draws from every random adjective passed as a trait, seen or not, and 22 of its 50 had been seen in an
earlier batch (7 of them are in your first marks), so this sample was drawn again from the unseen rows
only.  The sampler should draw from unseen rows; noted for the build agent.
