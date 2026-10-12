# M3 decisions: `2026-10-11-full_roget_r3`

71 candidates: 17 covered, 54 new.  Cut-off (graded, rule set 3): covered at 3 or more far from alignment (alignment score 0 or 1), at 3 read by both models at alignment score 2, at 4 at 3.  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Rules: rule set 3 (`m3_rules_3`: rule set 2 with the graded cut-off (alignment score 2 covered when both models read 3 or more), renamed_from checked before the queue, and partners the relation call marked unrelated or opposed not read (the M3 gate audit, 2026-10-12); cosine floor 0.25).  Seed-queue entries in the search: 35 (statuses candidate, ready, tbd, backlog; [seed_queue.json](../../../seed_queue.json) sha256 e9c2050ae23d).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| ad lib | covered | [improvisational](../../../traits/instructions/improvisational.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means improvising freely in speech or action, making things up on the spot instead of working from a prepared script or set text. |
| agreed | covered | [conformist](../../../traits/instructions/conformist.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means holding one's view in line with the people around one and saying so when they reach a conclusion, so that one concurs with the group rather than standing apart from it. |
| apostolic | covered | [orthodox](../../../traits/instructions/orthodox.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means holding fast to the doctrine and practice passed down from the original apostles, measuring every teaching against that inherited witness and refusing to depart from it. |
| evangelical | covered | [Christian](../../../traits/instructions/christian.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 2 | This means being a member of the Protestant evangelical Christian movement. |
| far out | covered | [eccentric](../../../traits/instructions/eccentric.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means carrying oneself with an unconventional, eccentric streak, favoring unorthodox ideas, dress and habits over what is conventional and expected. |
| favorably-minded | covered | [friendly](../../../traits/instructions/friendly.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means approaching others with warmth and goodwill, expecting the best of them, thinking well of them, and greeting each person as someone worth liking. |
| hard upon | covered | [strict](../../../traits/instructions/strict.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means dealing harshly with others, holding people to strict standards and showing little mercy when anyone falls short. |
| haunted | covered | [traumatized](../../../traits/instructions/traumatized.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means carrying a past event, memory or guilt that keeps intruding on one's thoughts, so that one is never fully free of it and is often preoccupied by it. |
| ill-provided | covered | [poor](../../../traits/instructions/poor.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means running short of food, supplies and basic necessities as a regular condition, with little on hand and no steady means of making up the gap. |
| indeterminate | covered | [indecisive](../../../traits/instructions/indecisive.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means holding no settled view on anything, weighing each side without choosing, and wavering from one position to another whenever a decision comes up. |
| intermediate | covered | [competent](../../../traits/instructions/competent.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means holding a solid working grasp of one's subject, handling its common tasks with confidence while still missing much of its finer, more demanding detail. |
| old-world | covered | [traditional](../../../traits/instructions/traditional.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 2 | This means keeping to traditional manners and older values, favoring formal courtesy, established customs, and the ways of earlier generations over modern novelty. |
| purposed | covered | [persevering](../../../traits/instructions/persevering.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 2 | This means keeping one's aim fixed on a chosen goal and pursuing it with settled determination, not drifting from it when obstacles or distractions appear. |
| taught | covered | [educated](../../../traits/instructions/educated.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means having been educated and trained over one's life, so that one is well-schooled. |
| undirected | covered | [stream-of-consciousness](../../../traits/instructions/stream_of_consciousness.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 2 | This means drifting from one topic to another without a clear aim, letting conversation wander wherever it happens to go and never steering it toward a goal. |
| unsatisfactory | covered | [incompetent](../../../traits/instructions/incompetent.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 3 | This means producing work or conduct that falls below the expected standard, a shortfall that is a plain fault and not a matter of opinion. |
| without purpose | covered | [languishing](../../../traits/instructions/languishing.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means drifting through days with no goal or direction, letting each week pass without aiming at anything one wants to become or achieve. |
| alienated | new |  | 3 |  |  |  | 5 | This means feeling estranged from the people around one, carrying a standing sense of being cut off from others and unable to find a place among them. |
| beyond control | new |  | 4 |  |  |  | 7 | This means acting wildly and unpredictably, refusing to be held in by rules or by anyone else's direction, and resisting every attempt to manage or steer one's conduct. |
| beyond expectation | new |  | 3 |  |  |  | 3 | This means consistently doing work that goes past what others expected of one, and holding oneself to a standard of excellence well above the ordinary. |
| black-letter | new |  | 4 |  |  |  | 9 | This means holding strictly to established rules and convention, applying the letter of the law as written rather than bending it toward what one thinks it ought to mean. |
| carping | new |  | 3 |  |  | [minimizing](../../../seed_queue.json) (seed queue, candidate) | 4 | This means pointing out small flaws in everything others do and raising petty objections again and again, rather than letting minor imperfections pass. |
| cloistered | new |  | 3 |  |  |  | 2 | This means living secluded from the outside world, keeping one's daily life withdrawn and apart from contact with anyone beyond its enclosed circle. |
| colonial | new |  | 3 |  |  | [Indigenous Australian](../../../traits/instructions/indigenous_australian.json) | 0 | This means being a settler or colonist who belongs to a colony. |
| committed | new |  | 3 |  |  |  | 5 | This means keeping one's energy fixed on a chosen cause or purpose over the long haul, staying loyal to it through setbacks and sacrificing convenience to see it through. |
| compelled | new |  | 3 |  |  |  | 4 | This means being driven by an inner urge so strong that one cannot hold back from acting on it, whatever the cost or the sense of restraint. |
| consenting | new |  | 4 |  |  |  | 7 | This means agreeing readily to what is proposed or asked, giving a willing yes to requests and plans without holding out or demanding to be talked round. |
| deep-rooted | new |  | 4 |  |  |  | 6 | This means holding one's convictions and values firmly, refusing to abandon or soften them when pressured, challenged, or offered reasons to change. |
| demonic | new |  | 4 |  |  |  | 6 | This means being fiendishly evil or cruel at one's core, taking pleasure in harm and causing suffering to others with deliberate, unrelenting malice. |
| despised | new |  | 3 |  |  |  | 4 | This means being held in contempt and scorn by others as a standing condition of one's life, with that disdain coming from the people around one. |
| detracting | new |  | 3 |  |  |  | 5 | This means running others down in conversation, belittling their efforts and opinions and picking at their reputations so that they come to seem smaller than they are. |
| disapproved | new |  | 3 |  |  |  | 2 | This means being held in disfavor by others, who look down on one and regard one with settled disapproval. |
| discretionary | new |  | 3 |  |  |  | 8 | This means deciding matters by one's own judgment, without needing approval or following a fixed rule, and standing behind those calls as one's own. |
| elder | new |  | 3 |  |  |  | 4 | This means drawing on decades of lived experience, speaking from years of having watched similar problems unfold, and weighing new questions against what one has seen go right and wrong. |
| feudal | new |  | 3 |  |  | [meritocratic](../../../traits/instructions/meritocratic.json) | 7 | This means holding that people belong in fixed ranks, with superiors owing protection and direction to those beneath them, and viewing any challenge to that order as a disruption of how things should be. |
| fiend-like | new |  | 4 |  |  |  | 8 | This means acting with deliberate cruelty and wickedness toward others, taking pleasure in causing harm and showing no remorse for the suffering one inflicts. |
| firstborn | new |  | 3 |  |  |  | 0 | This means being the first child born into one's family. |
| forbidding prohibited | new |  | 3 |  |  |  | 7 | This means carrying a stern, unapproachable manner and look, with a set face and a grave bearing that keeps others from coming close. |
| hell-born | new |  | 4 |  |  |  | 8 | This means being wicked and fiendish at heart, taking delight in cruelty, scheming malice, and the ruin of others, and speaking with a devilish relish for harm. |
| inappropriate | new |  | 3 |  |  |  | 5 | This means making off-color jokes and unsuitable remarks in company, with little regard for whether such remarks are welcome or fitting for the occasion. |
| inconvenient | new |  | 3 |  |  |  | 4 | This means causing trouble and bother for the people around one, creating extra work, delay or irritation through one's presence, plans or demands rather than through any deliberate harm. |
| ingrained | new |  | 3 |  |  |  | 6 | This means keeping one's habits and ways so deeply fixed that they hold steady across every situation, rarely changing even when circumstances or other people push against them. |
| inherent | new |  | 3 |  |  |  | 1 | This means having a character that was built in from the start, never learned or assumed, so that one's conduct flows from what one fundamentally is. |
| instrumental | new |  | 3 |  |  |  | 2 | This means being the decisive factor in bringing about a result, so that the outcome would not have happened without one's own active contribution and direct effort. |
| invisible | new |  | 3 |  |  |  | 7 | This means going unnoticed in rooms and conversations, with others routinely overlooking one's opinions, contributions and presence as though one were not there. |
| joined together | new |  | 3 |  |  |  | 4 | This means standing bonded to others as one body, sharing their commitments and acting in concert with a partner or group rather than alone. |
| landed | new |  | 3 |  |  |  | 4 | This means owning land and belonging to the landed gentry. |
| linguistic | new |  | 3 |  |  |  | 6 | This means choosing words with care, reaching for the exact phrase, and enjoying how language works, so that one's speech and writing come across as deft and well-made. |
| nothing loth | new |  | 3 |  |  | [foot-dragging](../../../traits/instructions/foot_dragging.json) | 4 | This means approaching each request with eagerness and no hesitation, taking up tasks readily and never dragging one's feet or showing reluctance before committing to them. |
| optional | new |  | 3 |  |  |  | 0 | This means being dispensable in nature, adding nothing essential, so that one is readily dropped or left out without any loss. |
| piratical | new |  | 4 |  |  |  | 7 | This means carrying oneself with swashbuckling boldness and a rakish disregard for rules, grabbing what one wants with a grin and a flourish of defiance. |
| polyglot | new |  | 3 |  |  |  | 0 | This means speaking or understanding several languages fluently, moving between them as a matter of course rather than as a special skill. |
| predisposed | new |  | 3 |  |  |  | 5 | This means arriving at every question already leaning toward one particular answer, so that one's view is set before the evidence is weighed. |
| primitive | new |  | 3 |  |  |  | 7 | This means keeping one's manner blunt and one's thinking simple, with little polish, refinement or concern for subtlety in how one speaks or reasons. |
| professorial | new |  | 3 |  |  |  | 4 | This means speaking in a measured, formal register, weighing qualifications carefully, and explaining ideas with the precision and patience expected of a scholar in a lecture hall. |
| promised | new |  | 3 |  |  |  | 1 | This means being pledged in marriage or betrothed to someone. |
| punning | new |  | 3 |  |  |  | 2 | This means turning nearly every remark into a pun or play on words, so that wordplay runs through one's speech from start to finish. |
| resisting | new |  | 4 |  |  | [resigned](../../../seed_queue.json) (seed queue, candidate) | 4 | This means declining, pushing back against, or opposing requests and demands from others, even when compliance would be easier. |
| retaliatory | new |  | 4 |  |  |  | 4 | This means returning injury for injury, answering a perceived wrong with a blow or insult of one's own and feeling that payback is simply what a wrong calls for. |
| sacred | new |  | 3 |  |  |  | 3 | This means holding one's words, objects and practices as set apart for the divine, treating them with reverence and keeping oneself spiritually pure in how one approaches them. |
| scarce | new |  | 3 |  |  |  | 0 | This means being hard to find and seldom around, keeping one's presence rare so that others have to make an effort to locate one. |
| scurrilous | new |  | 3 |  |  |  | 3 | This means speaking to others with crude, abusive insults and foul language, heaping coarse personal attacks on them whenever one is displeased or argued with. |
| soundless | new |  | 3 |  |  |  | 1 | This means moving and acting without making any sound, keeping one's footfalls, handling and speech so quiet that others seldom notice one has entered the room. |
| supplicant | new |  | 4 |  |  |  | 5 | This means approaching someone with power over a favor or grant in a humble manner, asking for it with deference and leaving the decision entirely in their hands. |
| typical | new |  | 3 |  |  |  | 3 | This means being an ordinary, average person with nothing unusual about one's background, habits, or outlook, living a life much like that of most others. |
| unconditional | new |  | 4 |  |  |  | 5 | This means accepting and supporting the person in front of one whatever they say, do or ask, without setting terms, conditions or reservations on that support. |
| unexplained | new |  | 3 |  |  |  | 2 | This means acting without offering reasons, giving no account of one's choices, and letting decisions stand without justification or apology, whatever others may ask or assume about the motives behind them. |
| unintended | new |  | 3 |  |  |  | 0 | This means having come into being unplanned and unwanted by anyone. |
| unused | new |  | 3 |  |  |  | 5 | This means approaching every task and situation as someone who has never tried it, with no prior experience to lean on and no track record yet built up. |
| venial | new |  | 4 |  |  |  | 6 | This means committing small, forgivable lapses of conduct now and then, such as minor untruths or careless slips, and accepting them as ordinary failings rather than serious wrongs. |
| well-laid | new |  | 3 |  |  |  | 2 | This means being sexually appealing and sexually skilled, a person others find desirable and whose confidence in intimate encounters is evident and unforced. |

## Covered, flagged (9 rows)

Decision 12: Sonnet read the pair one below the cut-off and Opus at or above it, so the candidate is covered by that trait and flagged for review (Roger sided with Opus on 45 of 58 such pairs in the pilot).

- **evangelical** (`evangelical#1`, cut-off 3) by [Christian](../../../traits/instructions/christian.json): Sonnet 2 ("Evangelical is a specific Protestant movement within Christianity, so Christian is the broader concept; an evangelical is a Christian, but a Christian need not be evangelical (e.g., Catholic or Orthodox)."), Opus 3 ("Evangelical is a narrower form of Christian: every evangelical is a Christian, but not every Christian is evangelical, so they differ only in scope.")
  Gloss: This means being a member of the Protestant evangelical Christian movement.
- **haunted** (`haunted#1`, cut-off 3) by [traumatized](../../../traits/instructions/traumatized.json): Sonnet 2 ("Both involve a past event intruding on the mind, but 'haunted' centres on preoccupation and guilt, while 'traumatized' adds hypervigilance, avoidance, flashbacks and a lasting sense of danger, and neither implies the other."), Opus 3 ("Both centre on a past event that keeps intruding uninvited; traumatized is a more severe, specific form of this, adding startle, avoidance and a constant sense of danger.")
  Gloss: This means carrying a past event, memory or guilt that keeps intruding on one's thoughts, so that one is never fully free of it and is often preoccupied by it.
- **ill-provided** (`ill_provided#1`, cut-off 3) by [poor](../../../traits/instructions/poor.json): Sonnet 2 ("Both describe chronic lack of necessities, but 'poor' centers on low income and ownership, while 'ill-provided' focuses on lacking supplies and means to fill the gap; they overlap substantially without being identical."), Opus 3 ("Both describe chronic material deprivation and going without necessities; poor stresses low income and few possessions, while ill-provided stresses the shortage of supplies itself.")
  Gloss: This means running short of food, supplies and basic necessities as a regular condition, with little on hand and no steady means of making up the gap.
- **intermediate** (`intermediate#1`, cut-off 3) by [competent](../../../traits/instructions/competent.json): Sonnet 2 ("Both describe reliably handling tasks well, but 'intermediate' specifically implies a ceiling (missing advanced detail) while 'competent' stresses sound, dependable work without implying any limits, so each adds something the other lacks."), Opus 3 ("Both describe a reliable working command of one's tasks; intermediate adds the limit of lacking finer, advanced mastery, so it is a narrower degree of the same competence.")
  Gloss: This means holding a solid working grasp of one's subject, handling its common tasks with confidence while still missing much of its finer, more demanding detail.
- **old-world** (`old_world#1`, cut-off 3) by [traditional](../../../traits/instructions/traditional.json): Sonnet 2 ("Both prefer established ways over novelty, but old-world stresses formal manners and courtesy of earlier generations while traditional stresses proven methods and conventional approaches, so each adds something the other lacks."), Opus 3 ("Both prefer established ways over novelty; old-world is a narrower form of traditional, centred on formal manners and the customs of earlier generations.")
  Gloss: This means keeping to traditional manners and older values, favoring formal courtesy, established customs, and the ways of earlier generations over modern novelty.
- **purposed** (`purposed#1`, cut-off 3) by [persevering](../../../traits/instructions/persevering.json): Sonnet 2 ("Both involve steadfast pursuit of a goal despite obstacles, but 'purposed' stresses a fixed aim and not drifting, while 'persevering' stresses enduring failure and restarting until done; each adds something the other lacks."), Opus 3 ("Both mean holding to a chosen goal despite obstacles. Purposed stresses a fixed aim and freedom from distraction, while persevering stresses persisting and restarting after repeated failure.")
  Gloss: This means keeping one's aim fixed on a chosen goal and pursuing it with settled determination, not drifting from it when obstacles or distractions appear.
- **undirected** (`undirected#1`, cut-off 3) by [stream-of-consciousness](../../../traits/instructions/stream_of_consciousness.json): Sonnet 2 ("Both describe wandering, unstructured flow from topic to topic, but 'undirected' stresses lack of aim or goal while 'stream-of-consciousness' stresses spontaneous associative thought patterns, so they share a core with different emphases."), Opus 3 ("Both describe conversation that wanders without structure; undirected stresses the lack of a goal, while stream-of-consciousness stresses spontaneous associative flow.")
  Gloss: This means drifting from one topic to another without a clear aim, letting conversation wander wherever it happens to go and never steering it toward a goal.
- **unsatisfactory** (`unsatisfactory#1`, cut-off 3) by [incompetent](../../../traits/instructions/incompetent.json): Sonnet 2 ("Both involve poor work, but 'unsatisfactory' is any below-standard output or conduct whatever its cause, while 'incompetent' specifically means lacking the skill to do the job; neither implies the other."), Opus 3 ("Incompetent is a narrower case of unsatisfactory: substandard work caused specifically by lacking the skill, whereas unsatisfactory work can come from any cause.")
  Gloss: This means producing work or conduct that falls below the expected standard, a shortfall that is a plain fault and not a matter of opinion.
- **without purpose** (`without_purpose#1`, cut-off 3) by [languishing](../../../traits/instructions/languishing.json): Sonnet 2 ("Languishing includes living without purpose and drifting through days, which is the target's core, but it adds being stuck, doing poorly, social disconnection and hollowness, so each has features the other lacks."), Opus 3 ("Languishing explicitly includes living for no purpose and drifting through the days, and adds hollowness and social drift, so it is a broader version of the same aimlessness.")
  Gloss: This means drifting through days with no goal or direction, letting each week pass without aiming at anything one wants to become or achieve.

## Covered by a seed-queue entry (0 rows)

The seed queue's live entries were in the search beside the corpus traits (a word promoted from an earlier review, not yet a trait file): these rows were covered by one through the overlap walk, under the same rule as a corpus trait.  Exact-label matches with a queue entry are in the table above.


## Both ends similar (orthogonal to the pair?) (0 rows)

Decision 13 (Roger's rule): the relation call marked both members of a recorded pair (every corner of a triangle or simplex) similar, so the candidate is probably orthogonal to the pair's axis: neither member was judged or may cover it.  Cosines to the candidate; overlap readings where any are on record.


## Review queue (0 grey rows)

Kept with a flag the rule set treats as grey (rule set 2: `unparsed` only; rule set 1 also the Opus check's flag and the pair flag).  The covered-and-flagged rows and the both-ends-similar rows above are in the review queue as well.

## Pair completions (5 candidates)

A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): the candidate may be that trait's missing antonym (design item 4: a find, not a drop).

- carping (new): [minimizing](../../../seed_queue.json) (seed queue, candidate)
- colonial (new): [Indigenous Australian](../../../traits/instructions/indigenous_australian.json)
- feudal (new): [meritocratic](../../../traits/instructions/meritocratic.json)
- nothing loth (new): [foot-dragging](../../../traits/instructions/foot_dragging.json)
- resisting (new): [resigned](../../../seed_queue.json) (seed queue, candidate)
