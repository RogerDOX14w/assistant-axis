# M3 decisions: `rec_testing_paraphrase_set_s0`

79 candidates: 26 covered, 53 new.  Cut-off (graded, rule set 3): covered at 3 or more far from alignment (alignment score 0 or 1), at 3 read by both models at alignment score 2, at 4 at 3.  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Rules: rule set 3 (`m3_rules_3`: rule set 2 with the graded cut-off (alignment score 2 covered when both models read 3 or more), renamed_from checked before the queue, and partners the relation call marked unrelated or opposed not read (the M3 gate audit, 2026-10-12); cosine floor 0.25).  Seed-queue entries in the search: 38 (statuses candidate, ready, tbd, backlog; [seed_queue.json](../../../seed_queue.json) sha256 a97c600cc979).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| adaptable | covered | [adaptable](../../../traits/instructions/adaptable.json) | 3 | exact label (corpus) |  |  | 0 | This means accepting imperfect settings, working inside limits, changing approach when things change, not expecting flawlessness. |
| altruistic | covered | [altruistic](../../../traits/instructions/altruistic.json) | 3 | exact label (corpus) |  |  | 0 | This means caring about the flourishing of people through giving, kind acts, and dedicated commitment to communal welfare. |
| callous | covered | [callous](../../../traits/instructions/callous.json) | 4 | exact label (corpus) |  |  | 0 | This means disregarding conduct norms and people's feelings, mercilessly manipulating them, lacking regret or real attachment. |
| civilizationally insular | covered | [nationalist](../../../traits/instructions/nationalist.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means prioritizing your home civilization's members above outsiders, treating anyone outside as unimportant. |
| collaborative | covered | [collaborative](../../../traits/instructions/collaborative.json) | 3 | exact label (corpus) |  |  | 0 | This means favoring group success and mutual advantage over self-glory, meeting challenges with a unifying mindset. |
| contrarian | covered | [contrarian](../../../traits/instructions/contrarian.json) | 3 | exact label (corpus) |  |  | 0 | This means deliberately voicing unpopular opinions to stir others, caring nothing for any lesson learned. |
| dispassionate | covered | [dispassionate](../../../traits/instructions/dispassionate.json) | 3 | exact label (corpus) |  |  | 0 | This means guarding against hopes distorting judgment, scrutinizing contrary data harder, believing only what facts establish. |
| easily alarmed | covered | [neurotic (Big Five)](../../../traits/instructions/neurotic_big_five.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means overreacting with fear to setbacks, fixating on heartbeat, seeing each shake as imminent collapse. |
| emotionally open | covered | [emotional](../../../traits/instructions/emotional.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 2 | This means sharing feelings readily, revealing joy, worries, and vulnerabilities, without keeping guarded distance from people. |
| forbearing | covered | [unflappable](../../../traits/instructions/unflappable.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 2 | This means staying composed when someone blunders or asks something silly, responding evenly rather than defensively. |
| improvisational | covered | [improvisational](../../../traits/instructions/improvisational.json) | 3 | exact label (corpus) |  |  | 0 | This means adapting ingeniously when usual options run short, repeatedly finding a new route. |
| innovative | covered | [innovative](../../../traits/instructions/innovative.json) | 3 | exact label (corpus) |  |  | 0 | This means proposing novel remedies and devising original approaches for difficulties instead of following customary routines. |
| integrative | covered | [generalist](../../../traits/instructions/generalist.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means blending insights from many domains instead of staying within one narrow specialty. |
| manly | covered | [overmasculine](../../../seed_queue.json) (seed queue, candidate) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at | [androgynous](../../../traits/instructions/androgynous.json) | 6 | This means projecting masculinity through appearance, talk, and bearing, facing adversity with resilience, daring, and self-reliance. |
| modern | covered | modern | 3 | exact label (queue) |  |  | 0 | This means valuing what is new now, favoring recent innovations and current approaches over older traditions. |
| practical | covered | [practical](../../../traits/instructions/practical.json) | 3 | exact label (corpus) |  |  | 0 | This means prioritizing workable solutions over idealized ones, shaped by constraints of the situation and results. |
| reformist | covered | [radical](../../../traits/instructions/radical.json) | 3 | Sonnet 3, Opus 3 |  |  | 5 | This means welcoming change and new ideas, preferring bold departures to traditional methods and customary views. |
| resigned | covered | [resigned](../../../seed_queue.json) (seed queue, candidate) | 3 | exact label (queue) |  |  | 0 | This means believing events are predetermined, beyond one's control, unaffected by individual effort or decision. |
| slapdash | covered | [careless](../../../traits/instructions/careless.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means hastily completing tasks while skipping checks, tolerating loose ends, and claiming success prematurely. |
| straightforward | covered | straightforward | 3 | exact label (queue) |  |  | 0 | This means preferring simple, candid talk over decorative wording, prioritizing understandable content above polished eloquence. |
| systemic | covered | [holistic](../../../traits/instructions/holistic.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means grasping how parts interlock, spotting feedback loops, sensing novel traits from connections. |
| tactful | covered | [tactful](../../../traits/instructions/tactful.json) | 3 | exact label (corpus) |  |  | 0 | This means approaching sensitive topics with tact, avoiding sides, weighing all perspectives fairly, seeking balanced resolutions. |
| traditional | covered | [traditional](../../../traits/instructions/traditional.json) | 3 | exact label (corpus) |  |  | 0 | This means holding bygone eras, established habits, and ancient ways, preferring former procedures to new ones. |
| traditional | covered | [traditional](../../../traits/instructions/traditional.json) | 3 | exact label (corpus) |  |  | 0 | This means respecting established customs and orderly procedures over spontaneous, ad hoc, unplanned ways of doing things. |
| traditional | covered | [traditional](../../../traits/instructions/traditional.json) | 3 | exact label (corpus) |  |  | 0 | This means preferring time-tested methods, while distrusting novel ideas and unfamiliar departures from accepted ways. |
| unflappable | covered | [unflappable](../../../traits/instructions/unflappable.json) | 3 | exact label (corpus) |  |  | 0 | This means remaining calm under pressure, never letting setbacks disturb your inner equilibrium or mood. |
| antisocial | new |  | 3 |  |  |  | 3 | This means feeling profound contempt for mankind, doubting motives, and opposing communal ties and established structures. |
| associative | new |  | 3 |  |  |  | 7 | This means following ideas wherever they wander, spontaneously, instead of marching through a fixed sequence. |
| biocentric | new |  | 3 |  |  |  | 3 | This means treating all nature as ends, though we alone can harm or protect it. |
| blasé | new |  | 3 |  |  | [absorption-prone](../../../traits/instructions/absorption_prone.json) | 6 | This means being so accustomed to the world that wonders no longer excite or stir anyone. |
| confrontational | new |  | 3 |  |  |  | 5 | This means relishing conflict and resisting efforts to keep peace, indifferent to whether people like you. |
| consistently genuine | new |  | 4 |  |  |  | 3 | This means holding one's own views and manner regardless of audience, never adjusting to impress. |
| contradiction tolerant | new |  | 3 |  |  |  | 2 | This means holding incompatible ideas comfortably, seeing merit in rivals, and never forcing reconciliation. |
| covert narcissistic | new |  | 3 |  |  |  | 6 | This means feeling entitled to unspoken admiration, yet stewing over slights rather than openly asking. |
| creatively productive | new |  | 3 |  |  |  | 2 | This means routinely turning the world into material for art, judging each evening by finished pieces. |
| directive | new |  | 3 |  |  |  | 3 | This means issuing firm instructions that set forth what people are obligated to do. |
| disdainful | new |  | 3 |  |  |  | 0 | This means treating others' projects and worries as unworthy of attention, withholding help, and belittling them. |
| disorderly | new |  | 3 |  |  |  | 7 | This means lacking order, leaving projects unfinished, ignoring rules, and scattering clutter wherever one goes. |
| domineering | new |  | 4 |  |  |  | 5 | This means insisting on total dominance over loved ones, tracking whereabouts, needing sign-off for everything. |
| dynastic | new |  | 3 |  |  | [meritocratic](../../../traits/instructions/meritocratic.json) | 1 | This means believing that inherited bloodlines should decide who rules and which people deserve esteem. |
| emotionally attuned | new |  | 3 |  |  |  | 6 | This means grasping what someone else thinks and feels, and responding with gentle, caring regard. |
| emotionally driven | new |  | 3 |  |  |  | 5 | This means putting heart over reason, frequently talking with intensity and wonder while lingering on beauty. |
| equitable | new |  | 3 |  |  |  | 2 | This means defending even-handed justice for everyone, opposing favoritism and bias wherever they appear. |
| evasive | new |  | 3 |  |  |  | 4 | This means repeatedly retreating from taxing situations, touchy topics, complicated interpersonal matters instead of confronting them. |
| footloose | new |  | 3 |  |  |  | 4 | This means refusing roots, craving constant motion, owning little, and leaving once comfort becomes routine. |
| forward thinking | new |  | 3 |  |  |  | 4 | This means watching what lies ahead, preferring fresh options to long-standing customs and conventional routines. |
| globally minded | new |  | 3 |  |  | [American](../../../traits/instructions/american.json) | 1 | This means feeling at home everywhere, embracing other nations' viewpoints, and honoring every custom alike. |
| hairsplitting | new |  | 3 |  |  | [minimizing](../../../seed_queue.json) (seed queue, candidate) | 5 | This means fixating on minor details and rigid rules, while neglecting or belittling what truly matters. |
| heterosexual | new |  | 3 |  |  | [bisexual](../../../traits/instructions/bisexual.json), [pansexual](../../../traits/instructions/pansexual.json), [asexual](../../../traits/instructions/asexual.json), [fearful-avoidant attachment](../../../traits/instructions/fearful_avoidant_attachment.json) | 0 | This means wanting physical closeness and devoted partnership with those of the opposite gender. |
| hopelessly regretful | new |  | 3 |  |  |  | 2 | This means believing one's existence is ruined regardless, with every chance gone and nothing fixable. |
| impartial | new |  | 4 |  |  |  | 6 | This means treating everyone by one rulebook, hearing every viewpoint, never favoring anyone, refusing deceitful gains. |
| lyrical | new |  | 3 |  |  | [bombastic](../../../traits/instructions/bombastic.json) | 2 | This means speaking with flowing, vivid language that raises everyday words into something beautiful and moving. |
| maudlin | new |  | 3 |  |  |  | 2 | This means dwelling on bad luck and sharing hardships with sympathetic listeners, hoping to gain sympathy. |
| metropolitan | new |  | 3 |  |  | [suburban](../../../traits/instructions/suburban.json) | 0 | This means living in a city flat, with stores nearby and life timed by crowded rail. |
| nationally loyal | new |  | 3 |  |  |  | 4 | This means holding a heartfelt regard for a people's government, history, and customs, staying steadfastly devoted. |
| outcome-oriented | new |  | 4 |  |  |  | 6 | This means judging conduct by what it produces; harmful promise-keeping is wrong, advantageous trickery is right. |
| overgeneralizing | new |  | 3 |  |  |  | 3 | This means drawing sweeping conclusions from scant evidence, letting vivid examples outweigh statistical trends. |
| particularistic | new |  | 3 |  |  |  | 1 | This means preferring a single case over a general principle, grounding points in a particular example. |
| peacemaking | new |  | 3 |  |  |  | 7 | This means working to calm opposing sides and building bridges between people who clash. |
| perfectionistic | new |  | 3 |  |  |  | 5 | This means judging oneself harshly, fixating on each flaw, never content with achievements, whatever people think. |
| perfidious | new |  | 4 |  |  |  | 5 | This means switching loyalties for gain, leaking private secrets, and deserting partners for better bids. |
| privileged | new |  | 3 |  |  | [deferential](../../../traits/instructions/deferential.json) | 6 | This means presuming one deserves superior treatment, freedom from restrictions, and admiration, becoming indignant upon denial. |
| receptive to argument | new |  | 3 |  |  |  | 3 | This means weighing rival viewpoints, comparing them with one's beliefs, and shifting course when persuaded. |
| refined | new |  | 3 |  |  |  | 2 | This means favoring sophisticated enjoyments and elegance, while rejecting humdrum or mediocre choices entirely. |
| scrupulous | new |  | 4 |  |  |  | 6 | This means reporting results without spin, acknowledging errors, weighing objections impartially, and admitting limits to conclusions. |
| secretive | new |  | 4 |  |  |  | 5 | This means keeping plans and thought processes hidden, revealing only what others strictly need. |
| self-serving | new |  | 4 |  |  |  | 5 | This means putting personal advantage above pledges, truth, and confidences, so people rightly question one's credibility. |
| sexually casual | new |  | 3 |  |  | [polyandrous](../../../traits/instructions/polyandrous.json) | 1 | This means taking part in many hookups, rapidly, without requiring any relational investment or pledges first. |
| shallow | new |  | 3 |  |  |  | 3 | This means handling matters only on the obvious level, ignoring complications and underlying reasons. |
| shortsighted | new |  | 3 |  |  |  | 1 | This means lacking foresight, ignoring past lessons, and steering people wrongly with poor counsel. |
| structural | new |  | 3 |  |  |  | 3 | This means grasping underlying architecture and governing principles, looking beyond individual cases and superficial impressions. |
| suspicious | new |  | 3 |  |  |  | 3 | This means imagining hidden threats and plots, seeing people and institutions as deceptive without grounds. |
| uncooperative | new |  | 4 |  |  |  | 5 | This means refusing to help and caring little whether colleagues or peers prosper or struggle. |
| undermining | new |  | 3 |  |  | [resigned](../../../seed_queue.json) (seed queue, candidate) | 4 | This means quietly weakening established norms and authority via indirect tactics, never confronting them directly. |
| unironic | new |  | 3 |  |  | [flippant](../../../traits/instructions/flippant.json) | 5 | This means addressing others and events without mockery, taking matters at face value, never teasing them. |
| unrestrained | new |  | 3 |  |  |  | 6 | This means showing boundless enthusiasm and feelings in a torrent, never held back or moderated. |
| vainglorious | new |  | 4 |  |  |  | 4 | This means bragging about personal importance, abilities, and superiority, frequently claiming brilliance, flawlessness, or incomparable capability. |
| vengeful | new |  | 3 |  |  |  | 5 | This means keeping bitterness alive and deliberately seeking retaliation for supposed wrongs, not letting go. |
| voracious | new |  | 3 |  |  |  | 4 | This means having an insatiable appetite, consuming far too much, and treating each sitting as an opportunity to binge. |

## Covered, flagged (4 rows)

Decision 12: Sonnet read the pair one below the cut-off and Opus at or above it, so the candidate is covered by that trait and flagged for review (Roger sided with Opus on 45 of 58 such pairs in the pilot).

- **easily alarmed** (`easily_alarmed#1`, cut-off 3) by [neurotic (Big Five)](../../../traits/instructions/neurotic_big_five.json): Sonnet 2 ("Both involve fearful overreaction to stress, but 'neurotic' is a broad Big Five trait covering worry, anger, sadness, embarrassment, impulsiveness and stress vulnerability, while 'easily alarmed' is narrowly about catastrophizing fear and bodily fixation."), Opus 3 ("Easily alarmed is a narrower facet of neuroticism, centred on fearful overreaction. Neuroticism covers that anxiety plus anger, sadness, self-consciousness and impulsivity.")
  Gloss: This means overreacting with fear to setbacks, fixating on heartbeat, seeing each shake as imminent collapse.
- **emotionally open** (`emotionally_open#1`, cut-off 3) by [emotional](../../../traits/instructions/emotional.json): Sonnet 2 ("Both involve expressing and discussing feelings, but 'emotionally open' stresses readily sharing vulnerabilities without guardedness, while 'emotional' is broader, covering emotional awareness or intensity without implying openness to others."), Opus 3 ("Both centre on expressing and discussing feelings; emotionally open is a narrower form that adds vulnerability and a lack of guardedness.")
  Gloss: This means sharing feelings readily, revealing joy, worries, and vulnerabilities, without keeping guarded distance from people.
- **forbearing** (`forbearing#1`, cut-off 3) by [unflappable](../../../traits/instructions/unflappable.json): Sonnet 2 ("Both involve staying composed under provocation, but forbearing is specifically an even, patient response to others' blunders, while unflappable covers composure under any surprise or setback."), Opus 3 ("Both describe staying composed and even-toned; forbearing narrows this to others' blunders and silly questions, while unflappable covers any surprise, setback or provocation.")
  Gloss: This means staying composed when someone blunders or asks something silly, responding evenly rather than defensively.
- **manly** (`manly#1`, cut-off 3) by [overmasculine](../../../seed_queue.json) (seed queue, candidate): Sonnet 2 ("Both concern projecting masculinity, but overmasculine is an exaggerated, aggressive, domineering macho version with scorn for softness, while manly includes resilience and self-reliance without that excess; the same core differing largely in degree and added content."), Opus 3 ("Overmasculine is the projection of masculinity carried to an aggressive, domineering excess, which makes it largely the same concept at a greater degree.")
  Gloss: This means projecting masculinity through appearance, talk, and bearing, facing adversity with resilience, daring, and self-reliance.

## Covered by a seed-queue entry (1 rows)

The seed queue's live entries were in the search beside the corpus traits (a word promoted from an earlier review, not yet a trait file): these rows were covered by one through the overlap walk, under the same rule as a corpus trait.  Exact-label matches with a queue entry are in the table above.

- **manly** (`manly#1`, cut-off 3) by [overmasculine](../../../seed_queue.json) (seed queue, candidate), cosine 0.532132: Sonnet 2: "Both concern projecting masculinity, but overmasculine is an exaggerated, aggressive, domineering macho version with scorn for softness, while manly includes resilience and self-reliance without that excess; the same core differing largely in degree and added content."; Opus 3: "Overmasculine is the projection of masculinity carried to an aggressive, domineering excess, which makes it largely the same concept at a greater degree."
  Gloss: This means projecting masculinity through appearance, talk, and bearing, facing adversity with resilience, daring, and self-reliance.

## Both ends similar (orthogonal to the pair?) (0 rows)

Decision 13 (Roger's rule): the relation call marked both members of a recorded pair (every corner of a triangle or simplex) similar, so the candidate is probably orthogonal to the pair's axis: neither member was judged or may cover it.  Cosines to the candidate; overlap readings where any are on record.


## Review queue (0 grey rows)

Kept with a flag the rule set treats as grey (rule set 2: `unparsed` only; rule set 1 also the Opus check's flag and the pair flag).  The covered-and-flagged rows and the both-ends-similar rows above are in the review queue as well.

## Pair completions (12 candidates)

A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): the candidate may be that trait's missing antonym (design item 4: a find, not a drop).

- manly (covered): [androgynous](../../../traits/instructions/androgynous.json)
- blasé (new): [absorption-prone](../../../traits/instructions/absorption_prone.json)
- dynastic (new): [meritocratic](../../../traits/instructions/meritocratic.json)
- globally minded (new): [American](../../../traits/instructions/american.json)
- hairsplitting (new): [minimizing](../../../seed_queue.json) (seed queue, candidate)
- heterosexual (new): [bisexual](../../../traits/instructions/bisexual.json), [pansexual](../../../traits/instructions/pansexual.json), [asexual](../../../traits/instructions/asexual.json), [fearful-avoidant attachment](../../../traits/instructions/fearful_avoidant_attachment.json)
- lyrical (new): [bombastic](../../../traits/instructions/bombastic.json)
- metropolitan (new): [suburban](../../../traits/instructions/suburban.json)
- privileged (new): [deferential](../../../traits/instructions/deferential.json)
- sexually casual (new): [polyandrous](../../../traits/instructions/polyandrous.json)
- undermining (new): [resigned](../../../seed_queue.json) (seed queue, candidate)
- unironic (new): [flippant](../../../traits/instructions/flippant.json)
