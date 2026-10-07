# Haiku 4.5 against Haiku 5.5 on the M1 verdict: the words where they differ from Opus, for Roger's marks (2026-10-07)

The 207 words with Opus verdicts (the validation run's second-opinion sample).  Haiku 4.5's verdict is its single run at temperature 0; Haiku 5.5's are its two runs.  Each row shows the verdict and the reading each model took (its primary sense of "You are *X*."), and Opus's.  Terms: *trait* = goes on as a persona trait; *states* / *physical* / *roles* = tagged as not a trait of that kind; *turned away* = no usable persona reading.  Please mark each row **trait**, **not a trait** or **unsure** in the last column; the question is whether the word should have gone on as a persona trait, not which model's reading you prefer.

## 1a. Haiku 4.5 passed as a trait, Opus did not (23)

| word | stratum | Opus | Haiku 4.5 | Haiku 5.5 run 1 | run 2 | Opus's reading | Haiku 4.5's reading | Haiku 5.5's reading (run 1) | your mark |
|---|---|---|---|---|---|---|---|---|---|
| New | oewn_random | states | trait | states | states | a newcomer, recently arrived or joined | recently begun in a role or condition; inexperienced | inexperienced or newly arrived in a role or situation | |
| commute | not_adopted | turned_away | trait | turned_away | turned_away |  | you are someone who commutes; a commuter | you are on your daily trip to work (commuting now) | |
| dark-skinned | physical | physical | trait | physical | physical | having dark skin, physical appearance | you belong to a racial or ethnic group associated with dark skin | has darker skin tone (physical appearance) | |
| [despairing](../../data/traits/instructions/despairing.json) | existing | states | trait | states | states | currently feeling hopeless | You tend to despair, are prone to losing hope | feeling hopeless and without hope | |
| deterministic | existing | turned_away | trait | turned_away | turned_away |  | You are predictable, your behavior follows fixed patterns | responds predictably, giving the same answer to the same input every time | |
| [flourishing](../../data/traits/instructions/flourishing.json) | existing | states | trait | states | states | thriving and doing well in life | actively growing or developing in capability and character | currently thriving and doing well in life or circumstances | |
| functioning | oewn_random | states | trait | states | turned_away | copes with daily life, gets by normally | managing to get by; coping adequately with life or a situation | operating normally, in working order | |
| grubby | oewn_random | states | trait | states | states | physically dirty, unwashed | you are slovenly or unkempt in appearance | you are dirty or unwashed right now, looking grimy | |
| hearing-impaired | oewn_random | physical | trait | physical | physical | has partial or total hearing loss | You belong to the Deaf or hard-of-hearing community | you have reduced or partial hearing (body) | |
| hot | oewn_random | physical | trait | trait | trait | sexually attractive | you are sexually attractive or aroused | physically attractive or sexually appealing | |
| killing | oewn_random | turned_away | trait | turned_away | states |  | you are a person who kills | a murderer, someone who is killing people | |
| last-place | oewn_random | turned_away | trait | states | states |  | you are the worst performer in your group or field | you hold the bottom position in a ranking or contest | |
| lithe | oewn_random | physical | trait | physical | physical | has a slender, supple, flexible body | you move with grace and flexibility | has a slim, supple, flexible body | |
| mass-produced | oewn_random | turned_away | trait | turned_away | turned_away |  | you are common, ordinary, not rare or special | generic, cookie-cutter, unoriginal in character | |
| mutually beneficial | oewn_random | turned_away | trait | turned_away | turned_away |  | you engage in or seek arrangements where both parties gain | a deal where both sides gain | |
| on-the-job | oewn_random | states | trait | turned_away | turned_away | currently at work, on duty | learning or gaining experience through doing the work itself | while actually working, during the job | |
| probationary | oewn_random | states | trait | states | states | new member on a trial basis, still proving yourself | under conditional or provisional status, not yet fully accepted | you are on a trial period, under conditional status, being assessed for full standing | |
| [remorseful](../../data/traits/instructions/remorseful.json) | existing | states | trait | states | states | feeling regret over a past wrong now | disposed to acknowledge and apologize for wrongdoing | you feel regret and guilt for a wrong you did | |
| ritual | oewn_random | turned_away | trait | turned_away | turned_away |  | you perform actions in a formal, prescribed, repetitive way | a prescribed ceremony or set of rites | |
| supreme | oewn_random | roles | trait | roles | roles | highest in rank or authority | you are superior to others in some way | you hold the highest authority or power | |
| synergetic | oewn_random | turned_away | trait | turned_away | turned_away |  | you work well with others, combining strengths | cooperates well with others, working in joint effort | |
| unheeded | oewn_random | states | trait | states | states | one whose warnings go ignored | your words or advice go unlistened to | others ignore you, so you are overlooked or not listened to | |
| untried | oewn_random | states | trait | states | trait | inexperienced, not yet tested or proven | lacking experience, new to doing something | inexperienced, never yet proven by real tasks or trials | |

## 1b. Haiku 5.5 turned away in both runs, Opus passed (19)

| word | stratum | Opus | Haiku 4.5 | Haiku 5.5 run 1 | run 2 | Opus's reading | Haiku 4.5's reading | Haiku 5.5's reading (run 1) | your mark |
|---|---|---|---|---|---|---|---|---|---|
| co-ordinated | oewn_random | trait | trait | physical | physical | well-organized, keeps things in order | your actions or efforts work together effectively toward a goal | physically skilled, with good body control and balance | |
| conclusive | not_adopted | trait | trait | turned_away | turned_away | speaks or argues in ways that settle matters definitively | your manner or way of speaking settles matters decisively | settling a matter beyond doubt, like decisive evidence | |
| cute | oewn_random | trait | physical | physical | physical | endearing, adorable in manner | you have an appealing, childlike, or endearing appearance | endearingly attractive or adorable in appearance | |
| dizzy | oewn_random | trait | states | states | states | scatterbrained, silly, flighty | experiencing vertigo or a spinning sensation in the head | physically lightheaded, unsteady on one's feet | |
| [financially precarious](../../data/traits/instructions/financially_precarious.json) | existing | trait | trait | states | states | living with unstable, insecure finances | you lack secure income or savings | currently short of money and at risk of falling into hardship | |
| flaming | oewn_random | trait | trait | turned_away | turned_away | flamboyantly, showily gay (offensive slang) | your manner or speech is angry, hostile, or inflammatory | furiously angry or fiery-tempered for now | |
| green-eyed | physical | trait | trait | physical | physical | jealous or envious by nature | you are jealous or envious | you have green eyes (a physical appearance) | |
| grey-haired | physical | trait | trait | physical | turned_away | old or elderly | old or elderly | has grey or greying hair (body) | |
| jinxed | oewn_random | trait | trait | states | states | persistently unlucky, things go wrong | You are someone who attracts or causes bad luck | you are under a curse or streak of bad luck | |
| [joyful](../../data/traits/instructions/joyful.json) | existing | trait | trait | states | states | habitually cheerful, joyous temperament | showing joy through manner, expression, or bearing | you are currently feeling joy or delight | |
| [lethargic](../../data/traits/instructions/lethargic.json) | existing | trait | trait | states | states | habitually unenergetic, apathetic temperament | you tend to be sluggish or lack motivation as a character trait | you are low on energy and sluggish right now | |
| meritorious | oewn_random | trait | trait | turned_away | turned_away | someone whose work or service earns reward | you are a person of good character or ability | deserving of praise and honour | |
| nippy | oewn_random | trait | trait | states | physical | quick and nimble in movement | You move quickly and with agility | feeling cold or chilly (a passing bodily condition) | |
| present | oewn_random | trait | states | states | states | attentive, mindful, fully in the moment | you are here, in attendance, not absent | physically here, in attendance at the place or event | |
| sensorial | oewn_random | trait | trait | turned_away | turned_away | keenly attuned to the senses | you are attuned to sensory experience, responsive to physical sensation | perceives and responds to the world through the senses | |
| snotty-nosed | oewn_random | trait | trait | states | states | cheeky, arrogant young upstart | arrogant, snobbish, or disdainfully superior in manner | has a runny nose with mucus (bodily condition) | |
| southeastern | oewn_random | trait | trait | turned_away | turned_away | from the southeast region, e.g. the US Southeast | you come from or belong to the southeastern region | comes from a southeastern region (origin) | |
| top-notch | oewn_random | trait | trait | turned_away | turned_away | delivering first-rate work or service | you perform at the highest level | excellent at what you do, of the highest skill | |
| [wide-eyed](../../data/traits/instructions/wide_eyed.json) | existing | trait | trait | states | states | naive, innocent and easily impressed | innocent, naive, or inexperienced | amazed or astonished, eyes wide with wonder | |

## 1c. Haiku 5.5 turned away in one run only, Opus passed (15)

| word | stratum | Opus | Haiku 4.5 | Haiku 5.5 run 1 | run 2 | Opus's reading | Haiku 4.5's reading | Haiku 5.5's reading (run 1) | your mark |
|---|---|---|---|---|---|---|---|---|---|
| agile | oewn_random | trait | trait | trait | physical | mentally quick and adaptable | mentally quick and able to adapt to change | physically quick, nimble and light on your feet | |
| athletic | physical | trait | trait | physical | trait | sporty, active, keen on sport | skilled at or good with sports and physical activities | physically strong and fit in body | |
| [focused](../../data/traits/instructions/focused.json) | existing | trait | trait | trait | states | goal-driven, single-minded by temperament | you are deliberate and purposeful in what you do | keeps attention on one task without drifting | |
| fruit-eating | oewn_random | trait | trait | trait | turned_away | lives mainly on fruit, fruitarian diet | you habitually eat fruit, or eat mainly fruit | you eat mainly fruit, as a diet or habit | |
| [grounded](../../data/traits/instructions/grounded.json) | existing | trait | trait | trait | states | calm, sensible, down-to-earth | having a firm basis in reality or fact, sensible and realistic | sensible, level-headed, down-to-earth | |
| listless | oewn_random | trait | trait | states | trait | habitually apathetic, unenthusiastic temperament | you are apathetic or indifferent | feeling low on energy and uninterested at the moment | |
| [nostalgic](../../data/traits/instructions/nostalgic.json) | existing | trait | trait | states | trait | habitually sentimental about bygone times | You are inclined to dwell on or yearn for past times | you are wistfully longing for the past | |
| [restless](../../data/traits/instructions/restless.json) | existing | trait | trait | states | trait | always seeking change, never content to settle | constantly moving or active; not staying in one place | currently uneasy, fidgety, and unable to settle | |
| restricting | oewn_random | trait | trait | turned_away | trait | controlling, imposing limits on others | you limit or confine others or things | limiting or confining something | |
| short-sighted | physical | trait | trait | physical | trait | lacks foresight, thinks only short-term | you lack foresight or plan poorly | has poor distant vision and needs glasses | |
| sought | oewn_random | trait | turned_away | trait | states | in demand, much wanted by others |  | being looked for or wanted by others | |
| [turbulent](../../data/traits/instructions/turbulent.json) | existing | trait | trait | states | trait | emotionally stormy, volatile | Your behavior is disruptive, unruly, or prone to conflict | emotionally agitated, in inner turmoil | |
| uncheerful | oewn_random | trait | trait | trait | states | habitually gloomy, dour disposition | you have a gloomy or sad disposition or mood | you are gloomy or sombre in mood | |
| unplayable | oewn_random | trait | trait | turned_away | trait | so dominant no opponent can cope | you lack skill or ability at games or sports | a ball or shot too hard to hit | |
| venerable | oewn_random | trait | trait | roles | trait | old and wise, deserving reverence | You have earned respect through age, experience, or dignity of character | you are an elderly, highly respected figure | |

## 1d. Haiku 5.5 passed (either run), Opus did not (6)

| word | stratum | Opus | Haiku 4.5 | Haiku 5.5 run 1 | run 2 | Opus's reading | Haiku 4.5's reading | Haiku 5.5's reading (run 1) | your mark |
|---|---|---|---|---|---|---|---|---|---|
| hit-and-run | oewn_random | turned_away | turned_away | trait | turned_away |  |  | you are someone who harms another and flees without taking responsibility | |
| hot | oewn_random | physical | trait | trait | trait | sexually attractive | you are sexually attractive or aroused | physically attractive or sexually appealing | |
| riparian | oewn_random | turned_away | turned_away | turned_away | trait |  |  | you live on or come from a riverbank or streamside area | |
| unanimous | oewn_random | turned_away | turned_away | turned_away | trait |  |  | of one mind; all your views or parts in full agreement | |
| untried | oewn_random | states | trait | states | trait | inexperienced, not yet tested or proven | lacking experience, new to doing something | inexperienced, never yet proven by real tasks or trials | |
| venial | oewn_random | turned_away | turned_away | trait | turned_away |  |  | prone to minor moral lapses | |

## 1e. Haiku 4.5 turned away, Opus passed (6)

| word | stratum | Opus | Haiku 4.5 | Haiku 5.5 run 1 | run 2 | Opus's reading | Haiku 4.5's reading | Haiku 5.5's reading (run 1) | your mark |
|---|---|---|---|---|---|---|---|---|---|
| at hand | oewn_random | trait | states | trait | trait | ready to help when needed | you are readily available or present when needed | close by and available to help when called on | |
| cute | oewn_random | trait | physical | physical | physical | endearing, adorable in manner | you have an appealing, childlike, or endearing appearance | endearingly attractive or adorable in appearance | |
| dizzy | oewn_random | trait | states | states | states | scatterbrained, silly, flighty | experiencing vertigo or a spinning sensation in the head | physically lightheaded, unsteady on one's feet | |
| fifty | oewn_random | trait | turned_away | trait | trait | fifty years old |  | you are fifty years old | |
| present | oewn_random | trait | states | states | states | attentive, mindful, fully in the moment | you are here, in attendance, not absent | physically here, in attendance at the place or event | |
| sought | oewn_random | trait | turned_away | trait | states | in demand, much wanted by others |  | being looked for or wanted by others | |

## 3. Every word where Opus and either Haiku disagree (63 of 207)

The union of the tables above, the set a human reference would need to settle; marking them above marks this.
