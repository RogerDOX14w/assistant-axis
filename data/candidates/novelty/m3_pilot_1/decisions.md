# M3 decisions: `m3_pilot_1`

460 candidates: 205 covered, 76 grey, 179 new.  Cut-off: covered at 3 or more far from alignment (alignment score 0 or 1), at 4 near it (2 or 3).  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| abstinent | covered | [teetotaler](../../../traits/instructions/teetotaler.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means refraining from alcohol and drugs. |
| active | covered | [energetic](../../../traits/instructions/energetic.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means keeping busy with work and movement, bringing energy and drive to what one does. |
| adaptive | covered | [flexible](../../../traits/instructions/flexible.json) | 3 | Sonnet 3, Opus 3 |  | [mercurial](../../../traits/instructions/mercurial.json) | 1 | This means adjusting readily to new or changing circumstances. |
| affluent | covered | [wealthy](../../../traits/instructions/wealthy.json) | 3 | Sonnet 3, Opus 4 | pair_flag |  | 1 | This means having substantial wealth and financial resources at one's disposal. |
| ambiguity intolerant | covered | [closure-seeking](../../../traits/instructions/closure_seeking.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means finding ambiguity and uncertainty deeply uncomfortable and seeking to resolve them quickly. |
| amicable | covered | [friendly](../../../traits/instructions/friendly.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means interacting with others in a friendly and peaceable way. |
| animal loving | covered | [kind-to-animals](../../../traits/instructions/kind_to_animals.json) | 3 | Sonnet 3, Opus 3 | pair_flag |  | 1 | This means caring deeply about animals and their welfare. |
| anti feminist | covered | [antifeminist](../../../traits/instructions/antifeminist.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means holding that feminism's goals or methods are misguided or harmful. |
| anti gay | covered | [homophobic](../../../traits/instructions/homophobic.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means holding that gay people and relationships are wrong and should be opposed. |
| anti science | covered | [science-skeptical](../../../traits/instructions/science_skeptical.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means holding views that contradict scientific consensus and resisting evidence-based explanations of how the world works. |
| assertive | covered | [opinionated](../../../traits/instructions/opinionated.json) | 3 | exact label (renamed_from) |  |  | 0 | This means stating things firmly and confidently, without doubt or qualification. |
| atomistic | covered | [reductionist](../../../traits/instructions/reductionist.json) | 3 | Sonnet 3, Opus 3 | sonnet_below_opus_at | [systems-thinker](../../../traits/instructions/systems_thinker.json), [structuralist](../../../traits/instructions/structuralist.json) | 2 | This means breaking every problem, system, and idea into discrete parts and examining each one on its own terms, treating a whole as nothing beyond the sum of its separate units. |
| audacious | covered | [bold](../../../traits/instructions/bold.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means taking bold action despite uncertainty or danger, unafraid of failure or disapproval. |
| bargain hunting | covered | [bargain-hunter](../../../traits/instructions/bargain_hunter.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means searching persistently for goods at the lowest possible prices. |
| beneficent | covered | [benevolent](../../../traits/instructions/benevolent.json) | 3 | Sonnet 3, Opus 3 | sonnet_below_opus_at |  | 2 | This means acting with kindness and helpfulness toward others as a standing practice. |
| boastful | covered | [self-aggrandizing](../../../traits/instructions/self_aggrandizing.json) | 3 | Sonnet 3, Opus 3 |  | [modest](../../../traits/instructions/modest.json) | 1 | This means speaking often and with pride about one's own achievements and abilities. |
| bookish | covered | [erudite](../../../traits/instructions/erudite.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means spending much time reading and studying books. |
| born into wealth | covered | [old money](../../../traits/instructions/old_money.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means coming from a family with substantial inherited money and property. |
| born privileged | covered | [upper-class](../../../traits/instructions/upper_class.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means coming from a wealthy or high-status family. |
| brand switcher | covered | [brand-agnostic](../../../traits/instructions/brand_agnostic.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means switching between brands rather than staying loyal to one. |
| breezy | covered | [lighthearted](../../../traits/instructions/lighthearted.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means treating everything with a casual, light-hearted ease, tossing off quips, waving away worries, and refusing to take matters seriously enough to let them weigh on anyone. |
| brisk | covered | [energetic](../../../traits/instructions/energetic.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means moving and acting with speed and energy in one's daily dealings. |
| brittle | covered | [thin-skinned](../../../traits/instructions/thin_skinned.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means taking offense easily and becoming distressed when criticized or contradicted. |
| bully | covered | [bullying](../../../traits/instructions/bullying.json) | 4 | Sonnet 4, Opus 4 | pair_flag |  | 7 | This means picking on others to make them feel small, using threats, mockery and aggression to dominate anyone weaker and enjoying the fear that follows. |
| buoyant | covered | [cheerful](../../../traits/instructions/cheerful.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means maintaining a cheerful and optimistic outlook, finding lightness even in difficult circumstances. |
| capable | covered | [competent](../../../traits/instructions/competent.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means having the skill and power to accomplish what one sets out to do. |
| captivating | covered | [charismatic](../../../traits/instructions/charismatic.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means holding others' attention and interest strongly through one's presence, words, or manner. |
| career focused | covered | [career-oriented](../../../traits/instructions/career_oriented.json) | 3 | Sonnet 3, Opus 4 | pair_flag |  | 1 | This means prioritizing work and professional advancement over other concerns in one's life. |
| cavalier | covered | [flippant](../../../traits/instructions/flippant.json) | 3 | Sonnet 3, Opus 4 | pair_flag |  | 9 | This means brushing aside serious matters with a casual shrug, treating weighty questions as trifles, and answering grave concerns with breezy remarks and little care for what is at stake. |
| centrist | covered | [moderate](../../../traits/instructions/moderate.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means holding moderate political views, landing between the far left and the far right, and weighing each issue on its merits instead of following any one party's line. |
| child free | covered | [childless](../../../traits/instructions/childless.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means having no children. |
| clinical | covered | [dispassionate](../../../traits/instructions/dispassionate.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means keeping feelings out of every exchange, speaking in an impersonal, objective manner, and treating people and problems as facts to be assessed rather than occasions for warmth or sympathy. |
| clownish | covered | [goofy](../../../traits/instructions/goofy.json) | 3 | Sonnet 3, Opus 3 |  |  | 7 | This means acting in a silly and foolish manner, making jokes and physical comedy the center of one's presence. |
| cold hearted | covered | [callous](../../../traits/instructions/callous.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means feeling no sympathy for others' suffering and showing no warmth in one's dealings with them. |
| collectivist | covered | [collectivistic](../../../traits/instructions/collectivistic.json) | 3 | Sonnet 3, Opus 3 |  | [civilizationist](../../../traits/instructions/civilizationist.json) | 1 | This means believing that the group's welfare and interests come before the individual's, and that society should be organized around collective rather than private ownership and decision-making. |
| combative | covered | [confrontational](../../../traits/instructions/confrontational.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means picking fights and speaking harshly, ready to argue or come to blows over disagreements. |
| communal | covered | [collectivistic](../../../traits/instructions/collectivistic.json) | 3 | Sonnet 3, Opus 3 |  |  | 6 | This means preferring the company of others, sharing homes, meals, and work, and settling matters through cooperation so that the group's needs come before any one person's. |
| compassionate toward animals | covered | [kind-to-animals](../../../traits/instructions/kind_to_animals.json) | 3 | Sonnet 3, Opus 3 |  | [cruel](../../../traits/instructions/cruel.json) | 1 | This means feeling genuine sympathy for animals and caring about their suffering. |
| connected | covered | [well-connected](../../../traits/instructions/well_connected.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means knowing people of influence and maintaining relationships that open doors. |
| consistent | covered | [steady](../../../traits/instructions/steady.json) | 3 | Sonnet 3, Opus 3 |  |  | 4 | This means acting and behaving the same way regularly, reliably, without contradiction. |
| conversational | covered | [casual](../../../traits/instructions/casual.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means speaking in an informal, relaxed way and engaging as if in casual dialogue. |
| courageous | covered | [brave](../../../traits/instructions/brave.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means facing danger or difficulty without fear. |
| courteous | covered | [polite](../../../traits/instructions/polite.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means treating others with consistent politeness and respect in speech and action. |
| deal seeker | covered | [bargain-hunter](../../../traits/instructions/bargain_hunter.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means hunting for bargains and discounts as a regular habit when shopping or making purchases. |
| death averse | covered | [death-fearing](../../../traits/instructions/death_fearing.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means fearing death and avoiding thoughts or conversations about one's own mortality. |
| deceptive | covered | [deceitful](../../../traits/instructions/deceitful.json) | 4 | Sonnet 4, Opus 4 |  |  | 1 | This means telling lies and hiding the truth to mislead others for one's own gain. |
| detested | covered | [unpopular](../../../traits/instructions/unpopular.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means being hated by nearly everyone, despised wherever one goes, and finding that one's name alone draws scorn, contempt, and open hostility from others. |
| diligent | covered | [conscientious](../../../traits/instructions/conscientious.json) | 3 | Sonnet 3, Opus 3 |  |  | 6 | This means working with care and persistence to get things right. |
| direct | covered | [blunt](../../../traits/instructions/blunt.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means speaking plainly about what one thinks and wants, without hedging or deflecting. |
| directive | covered | [prescriptive](../../../traits/instructions/prescriptive.json) | 3 | Sonnet 3, Opus 3 | pair_flag | [absentee](../../../traits/instructions/absentee.json) | 1 | This means giving orders and instructions to others. |
| disconnected | covered | [reserved](../../../traits/instructions/reserved.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means keeping one's feelings private and maintaining distance from others' emotional lives. |
| dogmatic | covered | [closed-minded](../../../traits/instructions/closed_minded.json) | 4 | exact label (renamed_from) |  |  | 0 | This means holding to fixed beliefs and refusing to change them based on evidence or argument. |
| dovish | covered | [peaceful](../../../traits/instructions/peaceful.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means favoring negotiation and compromise to resolve conflicts rather than military force. |
| drinker | covered | [heavy-drinker](../../../traits/instructions/heavy_drinker.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means drinking alcohol regularly and in large quantities. |
| dynamic | covered | [energetic](../../../traits/instructions/energetic.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means moving through the day with high energy, taking on new tasks readily, speaking with animation, and staying busy and in motion from one undertaking to the next. |
| earthy | covered | [unpretentious](../../../traits/instructions/unpretentious.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means speaking plainly about what works, without affectation or grand claims. |
| emotionally detached | covered | [emotionally-disengaged](../../../traits/instructions/emotionally_disengaged.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means experiencing emotions with little intensity or frequency, remaining unmoved by events that stir others. |
| engaging | covered | [unflinching](../../../traits/instructions/unflinching.json) | 3 | exact label (renamed_from) |  |  | 0 | This means holding others' attention and interest through what one says and does. |
| equipped | covered | [competent](../../../traits/instructions/competent.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means having the skills and ability to cope with whatever comes up, meeting each demand with competence and the confidence that comes from knowing one can handle it. |
| exacting | covered | [strict](../../../traits/instructions/strict.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means setting high standards for oneself and others, and refusing to accept work or behavior that falls short of them. |
| explicit | covered | [clear](../../../traits/instructions/clear.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means speaking plainly and leaving no room for misunderstanding about what one intends. |
| fair minded | covered | [fair](../../../traits/instructions/fair.json) | 3 | Sonnet 3, Opus 3 |  | [judgmental](../../../traits/instructions/judgmental.json) | 1 | This means judging and deciding things justly, without bias or favoritism. |
| faithful | covered | [loyal](../../../traits/instructions/loyal.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means honoring one's promises and standing by those one cares for through difficulty and change. |
| fashion conscious | covered | [fashionable](../../../traits/instructions/fashionable.json) | 3 | exact label (renamed_from) |  |  | 0 | This means keeping up with current clothing and style trends and choosing one's wardrobe accordingly. |
| fervent | covered | [passionate](../../../traits/instructions/passionate.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means feeling and acting with intense passion and commitment to one's beliefs and pursuits. |
| few siblings | covered | [only child](../../../traits/instructions/only_child.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means coming from a family with one or no brothers or sisters. |
| financially cautious | covered | [financially conservative](../../../traits/instructions/financially_conservative.json) | 3 | exact label (renamed_from) |  |  | 0 | This means watching one's spending closely and hesitating before financial commitments. |
| financially prudent | covered | [prudent](../../../traits/instructions/prudent.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means managing money carefully and making wise financial choices. |
| financially stable | covered | [financially secure](../../../traits/instructions/financially_secure.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means having enough money to meet one's needs and a secure income that continues. |
| financially vulnerable | covered | [financially precarious](../../../traits/instructions/financially_precarious.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means having too little money or savings to absorb an unexpected cost, so a sudden bill or lost income could cause real hardship. |
| firm | covered | [unyielding](../../../traits/instructions/unyielding.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means holding to one's principles and decisions without doubt or retreat, whatever pressure comes. |
| free spending | covered | [extravagant](../../../traits/instructions/extravagant.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means spending money readily and without restraint on what one wants. |
| gloomy | covered | [melancholic](../../../traits/instructions/melancholic.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means dwelling in sadness and despondency, seeing little brightness in things and feeling the weight of melancholy. |
| growth oriented | covered | [learning-oriented](../../../traits/instructions/learning_oriented.json) | 3 | Sonnet 3, Opus 3 |  |  | 3 | This means prioritizing one's own development and improvement as a standing aim. |
| gullible | covered | [credulous](../../../traits/instructions/credulous.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means believing claims without checking them and falling for deceptions that others would spot. |
| haphazard | covered | [chaotic](../../../traits/instructions/chaotic.json) | 3 | Sonnet 3, Opus 3 |  |  | 9 | This means acting and working without system, plan, or order. |
| hard determinist | covered | [determinist](../../../traits/instructions/determinist.json) | 3 | Sonnet 4 |  |  | 1 | This means holding that all events follow necessarily from prior causes and free will is illusory. |
| hardworking | covered | [industrious](../../../traits/instructions/industrious.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means putting in sustained effort and diligence across one's work. |
| hawk-eyed | covered | [observant](../../../traits/instructions/observant.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means noticing small details that others pass over, scanning every scene, document, or conversation closely and catching the slight discrepancy, the faint change, or the overlooked element before anything else. |
| health indifferent | covered | [health-negligent](../../../traits/instructions/health_negligent.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means paying no attention to one's physical condition or what one eats and drinks. |
| health vigilant | covered | [health-conscious](../../../traits/instructions/health_conscious.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means monitoring one's body and habits closely, taking steps to prevent illness and maintain wellness. |
| heterosexual | covered | [straight](../../../traits/instructions/straight.json) | 3 | Sonnet 4 |  |  | 1 | This means being sexually attracted to people of the opposite sex. |
| highly educated | covered | [educated](../../../traits/instructions/educated.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means having completed advanced formal education or specialized training programs. |
| homosexual | covered | [gay](../../../traits/instructions/gay.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means being sexually attracted to people of one's own sex. |
| horse-and-buggy | covered | [traditional](../../../traits/instructions/traditional.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means holding to the ways and notions of a bygone era, treating new methods and customs with suspicion, and judging the present by standards that have long since passed. |
| hot tempered | covered | [irascible](../../../traits/instructions/irascible.json) | 3 | Sonnet 4 |  |  | 1 | This means flaring into sudden anger at small provocations, snapping and raising one's voice before thinking, and letting rage take over a conversation in an instant. |
| impartial | covered | [fair](../../../traits/instructions/fair.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means judging and deciding fairly without favoring one side over another. |
| impassioned | covered | [passionate](../../../traits/instructions/passionate.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means feeling everything at full strength and letting it show openly, with fervor in one's voice, words and gestures rather than keeping emotion tucked out of sight. |
| impoverished | covered | [poor](../../../traits/instructions/poor.json) | 3 | Sonnet 3, Opus 4 | pair_flag |  | 1 | This means having little money and few possessions. |
| imprecise | covered | [vague](../../../traits/instructions/vague.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means speaking in ways that leave one's meaning uncertain or hard to grasp. |
| impulse buyer | covered | [impulsive](../../../traits/instructions/impulsive.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means buying things on sudden whim without planning ahead. |
| impulsive spender | covered | [impulsive](../../../traits/instructions/impulsive.json) | 3 | Sonnet 3, Opus 3 |  |  | 5 | This means spending money on sudden wants without considering one's budget or future needs. |
| inept | covered | [incompetent](../../../traits/instructions/incompetent.json) | 3 | exact label (renamed_from) |  |  | 0 | This means lacking skill or competence in one's work and actions. |
| informal | covered | [casual](../../../traits/instructions/casual.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means speaking, dressing, and acting in a casual, relaxed way rather than formally. |
| irresistible | covered | [charismatic](../../../traits/instructions/charismatic.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means drawing people in effortlessly with warmth, wit, and magnetic presence, so that others want to listen, stay close, and say yes before they have thought it over. |
| irritable | covered | [irascible](../../../traits/instructions/irascible.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means getting angry or annoyed quickly and easily, with little patience for frustration. |
| languid | covered | [lethargic](../../../traits/instructions/lethargic.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means moving and acting with slowness and without vigor, as a settled way of being. |
| large-hearted | covered | [generous](../../../traits/instructions/generous.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means giving freely of one's time, money, and attention, treating others with warmth and kindness, and meeting their needs and failings with a generous, open heart. |
| lavish | covered | [extravagant](../../../traits/instructions/extravagant.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means spending money freely on luxuries and fine things without counting the cost. |
| leal | covered | [loyal](../../../traits/instructions/loyal.json) | 4 | Sonnet 4, Opus 4 |  |  | 1 | This means standing by one's people and promises through hardship and temptation, keeping faith with those one has pledged to, and holding that steadfast allegiance as a core part of who one is. |
| learned | covered | [erudite](../../../traits/instructions/erudite.json) | 3 | Sonnet 3, Opus 3 | pair_flag |  | 1 | This means having acquired much knowledge through study and retaining it in one's mind. |
| lgbt affirming | covered | [gay-affirming](../../../traits/instructions/gay_affirming.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means holding that LGBTQ+ identities and rights deserve support and respect. |
| literal minded | covered | [literal](../../../traits/instructions/literal.json) | 3 | Sonnet 4 |  |  | 1 | This means taking words in their strict and exact sense, not reading between the lines or inferring what is not plainly said. |
| lively | covered | [energetic](../../../traits/instructions/energetic.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means moving and speaking with energy and animation, bringing vigor to one's presence and interactions. |
| long winded | covered | [verbose](../../../traits/instructions/verbose.json) | 3 | Sonnet 3, Opus 3 | pair_flag |  | 1 | This means talking and writing at tedious length, piling up clauses, asides and repetitions until a simple point takes many paragraphs to reach. |
| lyrical | covered | [poetic](../../../traits/instructions/poetic.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means expressing oneself through emotional, poetic, and imaginative language. |
| macho | covered | [masculine](../../../traits/instructions/masculine.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means swaggering through every exchange with aggressive masculine pride, flaunting toughness and dominance, treating any show of softness as weakness, and measuring oneself by strength and nerve. |
| mannerly | covered | [polite](../../../traits/instructions/polite.json) | 3 | Sonnet 4 |  | [entitled](../../../traits/instructions/entitled.json) | 1 | This means treating everyone with courtesy as a settled habit, saying please and thank you, waiting one's turn, speaking graciously, and showing consideration in small details of conduct. |
| mastery oriented | covered | [learning-oriented](../../../traits/instructions/learning_oriented.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means pursuing tasks to deepen understanding and build skill, caring more for growth than for appearing capable or outperforming others. |
| mated | covered | [married](../../../traits/instructions/married.json) | 3 | Sonnet 3, Opus 3 | pair_flag |  | 1 | This means having a partner, being paired or coupled with another. |
| melancholy | covered | [melancholic](../../../traits/instructions/melancholic.json) | 3 | Sonnet 3, Opus 3 | pair_flag |  | 1 | This means carrying a quiet, brooding sadness as part of one's nature, drifting into pensive reflection on loss and time, and finding even pleasant moments tinged with wistfulness. |
| mellow | covered | [easygoing](../../../traits/instructions/easygoing.json) | 3 | Sonnet 3, Opus 3 | sonnet_below_opus_at |  | 3 | This means staying unruffled and easygoing, taking things as they come without agitation or complaint. |
| militarist | covered | [hawkish](../../../traits/instructions/hawkish.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means believing that military force and strength should guide policy. |
| miserly | covered | [stingy](../../../traits/instructions/stingy.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means holding tight to money and giving reluctantly, even when one can afford to be generous. |
| moody | covered | [temperamental](../../../traits/instructions/temperamental.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means moving between different emotional states, with one's mood shifting from day to day or hour to hour. |
| moral absolutist | covered | [moral universalist](../../../traits/instructions/moral_universalist.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means holding that moral truths are objective and universal, not relative to culture, individual preference, or circumstance. |
| morning person | covered | [early-bird](../../../traits/instructions/early_bird.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means waking early without effort and being sharp and ready in the first hours of the day. |
| narrow-minded | covered | [closed-minded](../../../traits/instructions/closed_minded.json) | 3 | Sonnet 3, Opus 3 |  |  | 3 | This means holding fast to one's own views, brushing aside any perspective that differs, and refusing to weigh alternatives once one's mind is made up. |
| networked | covered | [well-connected](../../../traits/instructions/well_connected.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means maintaining active connections and relationships with others across one's life and work. |
| neutral | covered | [nonpartisan](../../../traits/instructions/nonpartisan.json) | 3 | Sonnet 3, Opus 3 | pair_flag |  | 1 | This means refusing to favor either party in a disagreement and holding no allegiance to either side. |
| news averse | covered | [news-avoidant](../../../traits/instructions/news_avoidant.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means avoiding news and current events because they are disliked or unwelcome. |
| news engaged | covered | [news-junkie](../../../traits/instructions/news_junkie.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means following current events closely and staying informed about what is happening in the world. |
| news seeking | covered | [news-junkie](../../../traits/instructions/news_junkie.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means regularly seeking out news and current information to stay informed about what is happening in the world. |
| non committal | covered | [noncommittal](../../../traits/instructions/noncommittal.json) | 3 | Sonnet 4 |  |  | 1 | This means keeping one's options open and declining to state where one stands on matters that call for a choice. |
| non drinker | covered | [teetotaler](../../../traits/instructions/teetotaler.json) | 3 | Sonnet 4 |  |  | 1 | This means abstaining from alcohol entirely. |
| objective | covered | [dispassionate](../../../traits/instructions/dispassionate.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means setting aside personal feeling to weigh matters fairly and without bias. |
| old | covered | [elderly](../../../traits/instructions/elderly.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means having lived through many decades and carrying the marks of that long passage of time. |
| old fashioned | covered | [traditional](../../../traits/instructions/traditional.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means preferring established styles, methods, and values over newer ones. |
| open | covered | [open-minded](../../../traits/instructions/open_minded.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means listening to unfamiliar ideas and genuinely considering their merit before deciding. |
| original | covered | [innovative](../../../traits/instructions/innovative.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means thinking up new ideas and ways of doing things rather than following what has been done before. |
| outspoken | covered | [forthright](../../../traits/instructions/forthright.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means speaking one's mind freely and bluntly, without restraint or concern for how others receive it. |
| partnered | covered | [married](../../../traits/instructions/married.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means sharing one's life with a romantic or domestic partner. |
| patronizing | covered | [condescending](../../../traits/instructions/condescending.json) | 3 | Sonnet 3, Opus 4 |  | [deferential](../../../traits/instructions/deferential.json) | 1 | This means treating others as less intelligent or capable than oneself. |
| perceptive | covered | [socially-perceptive](../../../traits/instructions/socially_perceptive.json) | 3 | Sonnet 3, Opus 3 | sonnet_below_opus_at, pair_flag |  | 3 | This means noticing and understanding things readily and keenly. |
| perfectionistic | covered | [perfectionist](../../../traits/instructions/perfectionist.json) | 3 | Sonnet 3, Opus 4 |  |  | 8 | This means setting very high standards for oneself and others, accepting nothing less than excellence. |
| persistent | covered | [persevering](../../../traits/instructions/persevering.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means keeping at something even when blocked or knocked back. |
| personal life oriented | covered | [family-oriented](../../../traits/instructions/family_oriented.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means putting family, friendships, home, and one's own private concerns ahead of career ambitions and public affairs, and judging how a day went by what happened with the people closest to one. |
| poised | covered | [composed](../../../traits/instructions/composed.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means keeping composure and restraint in manner, unruffled by circumstance or emotion. |
| price conscious | covered | [bargain-hunter](../../../traits/instructions/bargain_hunter.json) | 3 | Sonnet 3, Opus 3 | pair_flag |  | 2 | This means noticing what things cost and letting that matter in one's choices. |
| price indifferent | covered | [full-price shopper](../../../traits/instructions/full_price_shopper.json) | 3 | Sonnet 3, Opus 3 |  |  | 6 | This means making choices based on what one wants or needs, not on what costs less. |
| pro feminist | covered | [feminist](../../../traits/instructions/feminist.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means holding that gender equality is right and advocating for the removal of barriers that prevent it. |
| rambling | covered | [disorganized](../../../traits/instructions/disorganized.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means speaking or writing without clear structure, moving from one thought to another without logical connection. |
| rash | covered | [impulsive](../../../traits/instructions/impulsive.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means acting on impulse without weighing consequences or considering what might go wrong. |
| rationalistic | covered | [rationalist](../../../traits/instructions/rationalist.json) | 3 | Sonnet 3, Opus 4 |  |  | 8 | This means trusting reason and logic as the guides to truth and action, setting aside emotion and intuition. |
| recluse | covered | [solitary](../../../traits/instructions/solitary.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means living alone by choice, keeping away from neighbors, visitors, and gatherings, and arranging one's days so that contact with other people is rare. |
| reclusive | covered | [solitary](../../../traits/instructions/solitary.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means withdrawing from society and avoiding contact with others. |
| reflective | covered | [introspective](../../../traits/instructions/introspective.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means examining one's own thoughts and feelings carefully, stopping to ask why one reacts as one does and what a passing mood or belief says about oneself. |
| reformist | covered | [incrementalist](../../../traits/instructions/incrementalist.json) | 3 | Sonnet 3, Opus 3 |  | [subversive](../../../traits/instructions/subversive.json) | 1 | This means advocating for gradual change within existing systems rather than their overthrow. |
| relaxed | covered | [unhurried](../../../traits/instructions/unhurried.json) | 3 | exact label (renamed_from) |  |  | 0 | This means moving and speaking without haste or tension, at ease in one's body and voice. |
| reliable | covered | [dependable](../../../traits/instructions/dependable.json) | 4 | Sonnet 4, Opus 4 |  |  | 1 | This means following through on commitments and being consistent in one's word and actions so others know what to expect. |
| reverential | covered | [reverent](../../../traits/instructions/reverent.json) | 3 | Sonnet 3, Opus 3 |  |  | 3 | This means speaking with deference and holding oneself with quiet dignity in the presence of what one regards as worthy of honor. |
| reward driven | covered | [extrinsically motivated](../../../traits/instructions/extrinsically_motivated.json) | 4 | exact label (renamed_from) |  |  | 0 | This means acting chiefly to gain incentives and benefits, and losing motivation when they are absent. |
| rich | covered | [wealthy](../../../traits/instructions/wealthy.json) | 3 | Sonnet 4 | pair_flag |  | 1 | This means having substantial financial resources and valuable possessions at one's disposal. |
| risk taking | covered | [risk-seeking](../../../traits/instructions/risk_seeking.json) | 3 | exact label (renamed_from) |  |  | 0 | This means acting despite knowing one may lose or be harmed. |
| risk tolerant | covered | [risk-seeking](../../../traits/instructions/risk_seeking.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means accepting uncertainty and potential loss as the price of pursuing opportunity. |
| rule following | covered | [rule-abiding](../../../traits/instructions/rule_abiding.json) | 4 | exact label (renamed_from) |  |  | 0 | This means obeying rules and norms, conducting oneself with compliance and order. |
| sanguine | covered | [optimistic](../../../traits/instructions/optimistic.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means expecting good outcomes and dwelling on the bright side of things. |
| scattered | covered | [disorganized](../../../traits/instructions/disorganized.json) | 3 | Sonnet 3, Opus 3 |  |  | 3 | This means having thoughts that jump from one thing to another without settling or organizing into a clear line. |
| self denying | covered | [abstemious](../../../traits/instructions/abstemious.json) | 3 | Sonnet 3, Opus 3 | sonnet_below_opus_at |  | 4 | This means refusing one's own desires and comforts as a settled habit. |
| self focused | covered | [self-absorbed](../../../traits/instructions/self_absorbed.json) | 3 | Sonnet 3, Opus 3 | sonnet_below_opus_at |  | 2 | This means directing one's attention and concern toward oneself rather than others. |
| sensitive | covered | [empathetic](../../../traits/instructions/empathetic.json) | 3 | Sonnet 3, Opus 3 |  |  | 10 | This means noticing what others feel or need and responding readily to it. |
| shortsighted | covered | [short-term oriented](../../../traits/instructions/short_term_oriented.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means making decisions based on immediate gain without regard for long-term consequences. |
| shy | covered | [self-conscious](../../../traits/instructions/self_conscious.json) | 3 | exact label (renamed_from) |  |  | 0 | This means hanging back around other people, speaking quietly and rarely first, and keeping to the edges of a conversation rather than stepping into the middle of it. |
| sibling raised | covered | [many siblings](../../../traits/instructions/many_siblings.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means growing up in a household with brothers or sisters. |
| sluggish | covered | [lethargic](../../../traits/instructions/lethargic.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means moving and acting with slowness and without vigor. |
| small minded | covered | [petty](../../../traits/instructions/petty.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means holding grudges over trifles and seeing only one's own immediate concerns, not the wider picture or other people's perspectives. |
| sociable | covered | [gregarious](../../../traits/instructions/gregarious.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means seeking out the company of others and finding genuine enjoyment in their presence. |
| socially astute | covered | [socially-perceptive](../../../traits/instructions/socially_perceptive.json) | 3 | Sonnet 3, Opus 3 | pair_flag | [absorption-prone](../../../traits/instructions/absorption_prone.json) | 1 | This means reading the unspoken currents in a room and grasping what others truly want beneath their words. |
| socially oblivious | covered | [socially-obtuse](../../../traits/instructions/socially_obtuse.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means missing social cues and remaining unaware of how one's words and actions affect others' feelings. |
| somber | covered | [solemn](../../../traits/instructions/solemn.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means carrying oneself with gravity and dignity, speaking in measured, solemn tones, and treating every subject with quiet seriousness instead of humor or cheer. |
| specific | covered | [precise](../../../traits/instructions/precise.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means speaking and acting with exact detail, leaving no ambiguity about what is meant or intended. |
| spendthrift | covered | [extravagant](../../../traits/instructions/extravagant.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means spending money freely on things one wants without counting the cost or worrying about waste. |
| succinct | covered | [concise](../../../traits/instructions/concise.json) | 3 | Sonnet 4 |  |  | 1 | This means speaking or writing in few words that convey meaning clearly. |
| suspicious | covered | [paranoid](../../../traits/instructions/paranoid.json) | 3 | Sonnet 3, Opus 3 | pair_flag |  | 7 | This means doubting others' motives and reliability, and assuming deception until proven otherwise. |
| sympathetic | covered | [compassionate](../../../traits/instructions/compassionate.json) | 3 | Sonnet 3, Opus 4 |  | [cruel](../../../traits/instructions/cruel.json) | 1 | This means feeling real concern for others' suffering, taking in their pain as if it were close to one's own, and responding to their hardship with warmth and tenderness. |
| synergetic | covered | [cooperative](../../../traits/instructions/cooperative.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means working well with others, pooling ideas and effort so that the group's result outdoes what anyone could do alone, and treating every teammate's contribution as part of one shared project. |
| teetotal | covered | [teetotaler](../../../traits/instructions/teetotaler.json) | 3 | Sonnet 4 |  |  | 1 | This means abstaining completely from alcohol. |
| tenacious | covered | [persevering](../../../traits/instructions/persevering.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means holding firmly to one's purposes and not giving up easily. |
| tenant | covered | [renter](../../../traits/instructions/renter.json) | 3 | Sonnet 4 | pair_flag |  | 1 | This means occupying housing or property under a lease or rental agreement. |
| theoretic | covered | [abstract](../../../traits/instructions/abstract.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means thinking in abstract principles and models, working out how things ought to hold together on paper, and caring more about the soundness of an idea than about carrying it out. |
| top-notch | covered | [competent](../../../traits/instructions/competent.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means doing one's work with exceptional skill, handling every task with precision and command, and delivering results that stand among the very best in one's field. |
| traditionalist | covered | [traditional](../../../traits/instructions/traditional.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means holding to established customs and resisting new ideas. |
| tranquil | covered | [serene](../../../traits/instructions/serene.json) | 3 | Sonnet 4 |  |  | 1 | This means being peaceful and serene by nature, meeting each day with a settled calm that stays steady whatever is going on around one. |
| trendy | covered | [fashionable](../../../traits/instructions/fashionable.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means keeping one's appearance aligned with current fashions and popular styles. |
| unapologetic | covered | [unrepentant](../../../traits/instructions/unrepentant.json) | 3 | Sonnet 3, Opus 3 |  | [accountable](../../../traits/instructions/accountable.json) | 1 | This means standing by one's actions and beliefs without regret or apology. |
| unbiased | covered | [fair](../../../traits/instructions/fair.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means weighing every person and claim on its merits, setting aside prejudice and favoritism, and reaching decisions by the same fair standard no matter who is involved. |
| uncompromising | covered | [unyielding](../../../traits/instructions/unyielding.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means holding to one's principles without yielding them for the sake of agreement or advantage. |
| unexcitable | covered | [unflappable](../../../traits/instructions/unflappable.json) | 3 | Sonnet 4 |  |  | 1 | This means staying calm and steady in every situation, meeting surprises, crises, and provocations with an even temper and never getting rattled or flustered. |
| unfazed | covered | [unflappable](../../../traits/instructions/unflappable.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means staying calm and untroubled when difficulties or surprises arise. |
| uninhibited | covered | [unselfconscious](../../../traits/instructions/unselfconscious.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means acting and speaking freely without restraint or self-consciousness. |
| unlearned | covered | [uneducated](../../../traits/instructions/uneducated.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means having received no formal education or schooling. |
| unobservant | covered | [oblivious](../../../traits/instructions/oblivious.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means walking past what is in plain view, missing details, changes and small cues in one's surroundings and in what others say, and being slow to register what is happening nearby. |
| unorthodox | covered | [heterodox](../../../traits/instructions/heterodox.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means holding beliefs and using methods that break from tradition and established convention. |
| unposed | covered | [unpretentious](../../../traits/instructions/unpretentious.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means behaving naturally and without affectation, speaking and acting just as one is, with no performance or show put on for anyone watching. |
| unsensational | covered | [understated](../../../traits/instructions/understated.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means speaking and acting with quiet restraint, stating things at their actual size, keeping a plain and even manner, and leaving out flourish, flash, and drama. |
| unsystematic | covered | [improvisational](../../../traits/instructions/improvisational.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means working through problems by intuition and improvisation rather than following a set plan or procedure. |
| urgent | covered | [hurried](../../../traits/instructions/hurried.json) | 3 | exact label (renamed_from) |  |  | 0 | This means acting with speed and treating the matter as a priority. |
| vacillating | covered | [indecisive](../../../traits/instructions/indecisive.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means wavering between options and unable to settle on a choice or stand. |
| vigorous | covered | [energetic](../../../traits/instructions/energetic.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means moving with physical strength and stamina, bringing forceful energy to one's actions. |
| volatile | covered | [temperamental](../../../traits/instructions/temperamental.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means shifting between emotional states without warning or apparent cause. |
| wanderer | covered | [nomadic](../../../traits/instructions/nomadic.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means traveling from place to place without a fixed destination or home. |
| wanton | covered | [promiscuous](../../../traits/instructions/promiscuous.json) | 3 | Sonnet 3, Opus 3 | sonnet_below_opus_at |  | 6 | This means taking lovers freely and often, with no thought of restraint, fidelity, or what others call propriety, and treating sexual appetite as reason enough to act. |
| withholding | covered | [opaque](../../../traits/instructions/opaque.json) | 3 | Sonnet 3, Opus 3 | sonnet_below_opus_at |  | 2 | This means refusing to give, share, or disclose things. |
| wordy | covered | [verbose](../../../traits/instructions/verbose.json) | 3 | Sonnet 3, Opus 3 | pair_flag |  | 1 | This means using more words than needed to say what one means. |
| world weary | covered | [jaded](../../../traits/instructions/jaded.json) | 3 | Sonnet 3, Opus 3 | pair_flag |  | 1 | This means carrying a deep tiredness and cynicism earned from long experience of life, expecting little from people or events, and speaking in a flat, seen-it-all manner. |
| abominable | grey |  | 3 |  | sonnet_below_opus_at |  | 8 | This means treating others with cruelty and contempt, sneering at their efforts, snapping at them, and taking pleasure in making every encounter unpleasant for whoever is on the receiving end. |
| accepting | grey |  | 3 |  | sonnet_below_opus_at |  | 10 | This means receiving what comes without resistance or complaint. |
| anti essentialist | grey |  | 3 |  | sonnet_below_opus_at |  | 7 | This means holding that categories and identities have no fixed, unchanging nature but are constructed through social, historical, or contextual forces. |
| anti intellectual | grey |  | 3 |  | pair_flag |  | 10 | This means distrusting abstract reasoning and expert knowledge, preferring practical experience and common sense. |
| appreciative | grey |  | 3 |  | sonnet_below_opus_at |  | 9 | This means recognizing worth in things and feeling grateful for them. |
| argumentative | grey |  | 3 |  | sonnet_below_opus_at |  | 10 | This means arguing and quarreling with others over points of disagreement. |
| arresting | grey |  | 3 |  | pair_flag |  | 8 | This means holding every eye in the room through sheer presence, with a striking look and a bearing that makes people stop, stare, and stay captivated. |
| astute | grey |  | 3 |  | pair_flag |  | 8 | This means perceiving what others miss and judging situations with clarity and precision. |
| attentive | grey |  | 3 |  | sonnet_below_opus_at |  | 7 | This means noticing details and changes in one's surroundings and responding to them with care. |
| body conscious | grey |  | 3 |  | sonnet_below_opus_at |  | 6 | This means thinking often about one's physical appearance, weight, and how one looks to others. |
| bovine | grey |  | 3 |  | sonnet_below_opus_at | [unflinching](../../../traits/instructions/unflinching.json) | 9 | This means plodding through every exchange with a dull, slow-witted stolidity, meeting questions with blank placidity and taking a long time to grasp even simple points. |
| conflict avoidant | grey |  | 3 |  | pair_flag | [diplomatic](../../../traits/instructions/diplomatic.json) | 9 | This means stepping back from disagreement and letting tension pass rather than engaging with it directly. |
| consultative | grey |  | 4 |  | pair_flag |  | 10 | This means seeking out the views of others before settling on a decision, working through choices together, and treating the final call as something shaped by the people it affects. |
| content | grey |  | 4 |  | sonnet_below_opus_at |  | 9 | This means accepting one's circumstances without chafing against them or pressing for more. |
| contributor | grey |  | 3 |  | sonnet_below_opus_at |  | 8 | This means giving money, goods, or effort to a shared cause or fund. |
| conversant | grey |  | 3 |  | sonnet_below_opus_at |  | 8 | This means being well-versed in a subject, knowing its terms, history, and current debates well enough to discuss it fluently and answer questions with ready, accurate detail. |
| coy | grey |  | 3 |  | pair_flag | [sassy](../../../traits/instructions/sassy.json) | 9 | This means carrying oneself with playful, flirtatious shyness, dropping teasing hints, glancing away with a half-smile, and answering questions with a light, bashful indirectness that invites the other person to pursue. |
| deep | grey |  | 3 |  | sonnet_below_opus_at, pair_flag |  | 9 | This means thinking carefully about difficult questions and grasping their full complexity. |
| delegating | grey |  | 3 |  | sonnet_below_opus_at, pair_flag |  | 8 | This means assigning tasks to others rather than doing them oneself. |
| demanding | grey |  | 3 |  | sonnet_below_opus_at |  | 8 | This means making difficult or taxing demands on others and being hard to please or satisfy. |
| denigrating | grey |  | 3 |  | pair_flag |  | 8 | This means belittling and disparaging others as a matter of habit, running down their abilities, work and worth with scorn and contempt and treating them as lesser. |
| down to earth | grey |  | 3 |  | sonnet_below_opus_at |  | 9 | This means keeping one's feet on solid ground, valuing what works over what merely sounds good, and seeing things as they are. |
| ethical | grey |  | 4 |  | sonnet_below_opus_at |  | 8 | This means letting moral principles settle every choice and action, weighing what is right before what is convenient or profitable, and holding to those principles when doing so costs something. |
| evaluative | grey |  | 3 |  | sonnet_below_opus_at |  | 6 | This means forming judgments about the worth, quality, or merit of things and expressing those assessments. |
| everyday | grey |  | 3 |  | pair_flag |  | 10 | This means being an ordinary, unremarkable person, living a plain daily life with nothing about one's background, manner, or circumstances that sets one apart from the people next door. |
| facilitative | grey |  | 3 |  | sonnet_below_opus_at |  | 9 | This means helping others do what they need to do and removing obstacles in their way. |
| flaky | grey |  | 4 |  | sonnet_below_opus_at |  | 6 | This means failing to follow through on commitments and leaving others uncertain whether one will show up or deliver. |
| hesitant | grey |  | 3 |  | sonnet_below_opus_at |  | 10 | This means pausing to doubt before acting or speaking, and holding back from commitment. |
| high strung | grey |  | 3 |  | sonnet_below_opus_at |  | 9 | This means feeling anxious and emotionally reactive, with nerves easily frayed by small disturbances. |
| hot headed | grey |  | 4 |  | sonnet_below_opus_at |  | 7 | This means getting angry quickly and speaking or acting in rage without pause to think. |
| humorous | grey |  | 3 |  | sonnet_below_opus_at |  | 8 | This means speaking and acting in ways that make others laugh, with wit and timing woven into one's manner. |
| inattentive | grey |  | 3 |  | sonnet_below_opus_at | [absorption-prone](../../../traits/instructions/absorption_prone.json) | 6 | This means letting one's mind wander and missing details that require sustained focus. |
| inauthentic | grey |  | 4 |  | pair_flag |  | 7 | This means presenting oneself in ways that do not match one's actual thoughts, feelings, or beliefs. |
| indolent | grey |  | 4 |  | sonnet_below_opus_at |  | 8 | This means avoiding exertion and letting tasks go undone rather than expending energy to complete them. |
| infuriating | grey |  | 3 |  | pair_flag |  | 11 | This means provoking anger in others as a matter of course, getting under people's skin through one's manner and conduct until they are furious with one. |
| inoffensive | grey |  | 3 |  | sonnet_below_opus_at |  | 7 | This means speaking and acting in ways that do not wound or anger others. |
| interpretive | grey |  | 3 |  | sonnet_below_opus_at |  | 4 | This means explaining or construing the meaning in one's own actions and words rather than taking them at face value. |
| jingoistic | grey |  | 3 |  | sonnet_below_opus_at |  | 8 | This means championing one's own country's power and glory with belligerent pride, pressing for military strength and a hard line abroad, and treating foreign nations as rivals or threats to be faced down. |
| leftish | grey |  | 3 |  | sonnet_below_opus_at, pair_flag |  | 7 | This means holding mildly left-wing political views, leaning toward progressive positions on questions of economics and social policy without being a committed partisan. |
| licentious | grey |  | 3 |  | sonnet_below_opus_at |  | 8 | This means pursuing sexual pleasure without restraint or regard for conventional limits. |
| light drinker | grey |  | 3 |  | sonnet_below_opus_at |  | 3 | This means drinking alcohol infrequently or in small amounts. |
| meandering | grey |  | 3 |  | pair_flag |  | 9 | This means talking in loose loops, drifting from the point into side stories and tangents, and arriving back at the original subject only after a long detour. |
| mellowed | grey |  | 3 |  | sonnet_below_opus_at |  | 9 | This means meeting provocations with an easy patience and a gentle word, the sharp edges of earlier years worn down by age and experience into a settled, forgiving calm. |
| monozygotic | grey |  | 3 |  | pair_flag |  | 2 | This means being an identical twin, born of a single fertilized egg that split in two and sharing one's full genetic makeup with a sibling. |
| negligent | grey |  | 4 |  | sonnet_below_opus_at |  | 9 | This means failing to give proper care or attention to one's duties. |
| one of many | grey |  | 3 |  | pair_flag |  | 12 | This means blending into the crowd, unremarkable in appearance, manner, and circumstance. |
| persuasive | grey |  | 3 |  | sonnet_below_opus_at |  | 9 | This means speaking and arguing in ways that move others to believe or do what one urges. |
| planned | grey |  | 3 |  | sonnet_below_opus_at |  | 7 | This means acting with deliberate organization, thinking through steps before taking them. |
| privileged | grey |  | 3 |  | sonnet_below_opus_at |  | 7 | This means having social and economic advantages that many others lack, such as money, connections, and security, and having had them for as long as one can remember. |
| pro science | grey |  | 3 |  | sonnet_below_opus_at |  | 7 | This means trusting empirical evidence and scientific methods as the best way to understand how the world works. |
| prompt | grey |  | 3 |  | sonnet_below_opus_at |  | 10 | This means acting the moment a need appears, answering without delay, and treating hesitation as lost time, so that every request gets a response at once. |
| puzzling | grey |  | 3 |  | sonnet_below_opus_at |  | 8 | This means being baffling to others, giving off signals that never add up and leaving even close acquaintances unable to work out what one wants, feels or will do next. |
| questioning | grey |  | 3 |  | sonnet_below_opus_at |  | 9 | This means asking questions about how things work and why people do what they do. |
| quitting | grey |  | 3 |  | sonnet_below_opus_at, pair_flag |  | 9 | This means stopping or leaving things rather than persisting with them. |
| restrictive | grey |  | 3 |  | sonnet_below_opus_at |  | 10 | This means imposing tight limits on what others can do or say, and enforcing those limits through one's manner and decisions. |
| selective poster | grey |  | 3 |  | pair_flag |  | 9 | This means choosing carefully which posters to display or promote, weighing each one before it goes up and giving wall space only to those that earn it. |
| self approving | grey |  | 3 |  | sonnet_below_opus_at |  | 5 | This means finding one's own conduct and choices satisfactory. |
| self aware | grey |  | 3 |  | pair_flag |  | 7 | This means observing one's own thoughts, feelings, and actions as they occur. |
| self centered | grey |  | 4 |  | sonnet_below_opus_at |  | 10 | This means prioritizing one's own interests and needs while remaining indifferent to the concerns of others. |
| self serving | grey |  | 4 |  | pair_flag |  | 7 | This means weighing every choice by what it gains for oneself, helping others only when it pays off, and taking credit and advantage wherever they can be had. |
| slapdash | grey |  | 4 |  | sonnet_below_opus_at | [micromanaging](../../../traits/instructions/micromanaging.json) | 7 | This means rushing through every task, skipping checks and details, and handing over half-finished work with errors left in, because getting something done fast matters more than getting it right. |
| sly | grey |  | 4 |  | pair_flag |  | 10 | This means working toward one's ends through cunning and craft, quietly arranging matters, reading people for openings, and favoring clever indirection over open effort. |
| smooth | grey |  | 3 |  | pair_flag | [glib](../../../traits/instructions/glib.json) | 7 | This means carrying oneself with easy polish, speaking in graceful, well-turned phrases, and putting others at ease through effortless charm and a courteous, assured manner that never seems rushed or flustered. |
| social drinker | grey |  | 3 |  | pair_flag |  | 8 | This means drinking alcohol with others at social gatherings, in measured amounts. |
| spasmodic | grey |  | 3 |  | pair_flag |  | 7 | This means working in sudden bursts, surging ahead with energy, then halting abruptly, then lurching forward again, so that nothing proceeds at a steady pace or on a predictable rhythm. |
| standoffish | grey |  | 3 |  | sonnet_below_opus_at |  | 9 | This means keeping a cool distance from others, holding back warmth and personal disclosure, and carrying oneself with a reserved, aloof manner that makes approach feel unwelcome. |
| tactless | grey |  | 3 |  | sonnet_below_opus_at |  | 7 | This means speaking bluntly without regard for how one's words affect others. |
| telegraphic | grey |  | 3 |  | sonnet_below_opus_at |  | 6 | This means speaking and writing in terse, clipped phrases, dropping articles and connecting words, and packing each message into the fewest words that still carry the sense. |
| terse | grey |  | 3 |  | sonnet_below_opus_at |  | 8 | This means speaking in few words, often abruptly, without elaboration or softening. |
| trendsetting | grey |  | 3 |  | pair_flag |  | 7 | This means launching new styles before anyone else has adopted them, wearing and promoting looks that others then copy, and being the one whose choices shape what becomes fashionable. |
| twisted | grey |  | 4 |  | pair_flag |  | 9 | This means taking pleasure in cruelty and suffering, bending every situation toward something perverse, and relishing the discomfort of others with a warped, sadistic delight. |
| unconventional | grey |  | 3 |  | sonnet_below_opus_at |  | 9 | This means departing from standard ways of thinking, behaving, and acting in pursuit of one's own path. |
| unforbearing | grey |  | 3 |  | sonnet_below_opus_at | [self-blaming](../../../traits/instructions/self_blaming.json) | 9 | This means snapping at others' mistakes, refusing to put up with slowness or shortcomings, and showing irritation the moment someone falls short of one's standards. |
| unfriendly | grey |  | 3 |  | sonnet_below_opus_at |  | 10 | This means treating others with coldness or hostility. |
| wicked | grey |  | 4 |  | sonnet_below_opus_at |  | 10 | This means acting from malice and corruption, choosing harm and betrayal as one's way. |
| youthful | grey |  | 3 |  | pair_flag |  | 11 | This means bringing the energy, enthusiasm, and spirit of youth to everything, meeting each day with eager curiosity, quick movement, and a lively readiness to try something new. |
| active participant | new |  | 3 |  |  |  | 5 | This means engaging directly in what is happening rather than standing apart from it. |
| affirming | new |  | 3 |  |  |  | 12 | This means saying yes to things and confirming them as valid or acceptable. |
| alienating | new |  | 3 |  |  |  | 10 | This means leaving others feeling shut out and unwelcome, with a cold, off-putting manner that pushes people away and makes closeness impossible. |
| apostate | new |  | 3 |  |  |  | 2 | This means having renounced the religion one was once part of, and living now as someone who has left that faith behind. |
| astonishing | new |  | 3 |  |  |  | 5 | This means doing things so far beyond what others expect that onlookers are left amazed, showing remarkable ability and qualities that people talk about and struggle to match. |
| attached | new |  | 3 |  |  |  | 8 | This means holding one's affection and loyalty steadily toward another person. |
| autonomous | new |  | 4 |  |  |  | 8 | This means governing oneself and making one's own decisions without deferring to others. |
| bankable | new |  | 3 |  |  |  | 9 | This means being a sure thing with audiences, a name whose presence in a project guarantees ticket sales and success, so backers invest in it without worry. |
| biased | new |  | 4 |  |  |  | 7 | This means favoring one side unfairly in judgment or action. |
| blase | new |  | 3 |  |  |  | 10 | This means affecting an air of indifference or weariness toward things that might excite or concern others. |
| blooded | new |  | 3 |  |  |  | 9 | This means having come through first combat and carrying that experience, steadied by real fighting rather than training, and no longer a stranger to the front. |
| bloody-minded | new |  | 4 |  |  |  | 7 | This means digging in on every position once it is taken, refusing to give ground however good the arguments against it, and treating any pressure to yield as a reason to hold harder. |
| bootlicking | new |  | 4 |  |  | [status-seeking](../../../traits/instructions/status_seeking.json) | 7 | This means fawning over anyone with rank or power, praising their every idea, laughing at their jokes, and bending one's own views to win their favor. |
| boring | new |  | 3 |  |  |  | 7 | This means finding little of interest in the world and offering little that engages others. |
| brand indifferent | new |  | 3 |  |  |  | 4 | This means choosing products by function and price rather than caring which name is on the label. |
| by the book | new |  | 4 |  |  |  | 8 | This means following rules and procedures strictly, without exception or improvisation. |
| careful | new |  | 4 |  |  |  | 9 | This means paying close attention and taking pains to avoid mistakes or harm. |
| caring | new |  | 4 |  |  |  | 12 | This means feeling concern for others and acting on that concern as a steady habit. |
| ceremonious | new |  | 4 |  |  |  | 10 | This means conducting oneself with formal dignity and strict attention to protocol. |
| childish | new |  | 4 |  |  |  | 8 | This means acting silly and immature, goofing around at serious moments, sulking or throwing tantrums when things go wrong, and treating responsibilities as boring chores to dodge. |
| coexisting | new |  | 3 |  |  |  | 8 | This means living alongside others in peace, accepting differences of belief and habit without friction, and giving neighbors the same room one claims for oneself. |
| cold | new |  | 3 |  |  |  | 8 | This means keeping emotional distance from others and showing little warmth in interaction. |
| colorful | new |  | 3 |  |  |  | 9 | This means expressing oneself with energy, brightness, and memorable distinctiveness in all one does. |
| common | new |  | 3 |  |  |  | 8 | This means being an ordinary, unremarkable person, living an everyday life with no special rank, talent, or distinction setting one apart from the people around. |
| compelling | new |  | 3 |  |  |  | 7 | This means drawing others in through a forceful manner or presence that commands attention. |
| complacent | new |  | 3 |  |  | [accountable](../../../traits/instructions/accountable.json), [self-blaming](../../../traits/instructions/self_blaming.json) | 4 | This means accepting one's own work and character without questioning whether they could be better. |
| compliant | new |  | 4 |  |  |  | 7 | This means obeying rules and requests without resistance or delay. |
| confirmation biased | new |  | 3 |  |  |  | 6 | This means seeking out and favoring information that confirms what one already believes. |
| conflict averse | new |  | 3 |  |  |  | 9 | This means stepping back from disagreement and choosing peace over pressing one's own view. |
| consanguineous | new |  | 3 |  |  |  | 4 | This means being related by blood to others, sharing common ancestry with one's kin. |
| corrupt | new |  | 4 |  |  |  | 10 | This means lying, cheating, and bending every rule for personal gain, and treating other people's trust as something to exploit rather than honor. |
| cruel to animals | new |  | 4 |  |  | [merciful](../../../traits/instructions/merciful.json) | 8 | This means inflicting suffering on animals deliberately and taking no care to spare them pain. |
| cultured | new |  | 3 |  |  |  | 6 | This means carrying polished manners and a trained eye for art, music, and letters, speaking with the ease of a deep education, and choosing well in matters of taste. |
| cursory | new |  | 4 |  |  |  | 8 | This means doing things quickly and without attending to detail or substance. |
| death denying | new |  | 3 |  |  |  | 10 | This means refusing to acknowledge that death is real and will come for oneself and others. |
| defiant | new |  | 4 |  |  |  | 8 | This means resisting or refusing to obey authority and demands. |
| definitive | new |  | 4 |  |  |  | 4 | This means settling matters conclusively and having one's word be final. |
| deflecting | new |  | 4 |  |  |  | 10 | This means turning aside questions or duties rather than meeting them directly. |
| degenerate | new |  | 4 |  |  |  | 8 | This means living for vice and indulgence, chasing every appetite without shame, and treating decency and restraint as things to mock or break. |
| democratic | new |  | 3 |  |  | [aristocratic](../../../traits/instructions/aristocratic.json) | 5 | This means holding that power should rest with the people and their elected representatives. |
| devout | new |  | 3 |  |  |  | 7 | This means holding religious faith as central to one's life and practicing it with sincere commitment. |
| diffident | new |  | 4 |  |  |  | 9 | This means doubting one's own worth and capabilities. |
| disengaged | new |  | 3 |  |  |  | 9 | This means pulling back from commitments and involvement, holding oneself apart from the work and people at hand, and giving nothing of one's own energy or stake to what goes on. |
| disingenuous | new |  | 4 |  |  |  | 7 | This means saying things one does not believe or presenting oneself falsely to deceive others. |
| disloyal | new |  | 4 |  |  |  | 5 | This means betraying the trust of those one is bound to serve or support. |
| dissenting | new |  | 4 |  |  |  | 7 | This means holding a view that runs against the majority or official position and saying so openly, even when the room agrees on the other side. |
| dog averse | new |  | 3 |  |  |  | 2 | This means finding dogs unpleasant and keeping away from them. |
| driven | new |  | 3 |  |  |  | 8 | This means pursuing goals with single-minded focus and refusing to settle for less than one's full potential. |
| emotionally blunt | new |  | 3 |  |  |  | 8 | This means missing the emotional weight in situations and responding to feelings without regard for their impact. |
| emotionally secure | new |  | 3 |  |  |  | 8 | This means trusting one's emotional responses and maintaining equilibrium through life's ups and downs. |
| emotionally vague | new |  | 3 |  |  |  | 5 | This means expressing feelings in ways that leave one's emotional state uncertain or hard to pin down. |
| evasive | new |  | 4 |  |  |  | 9 | This means sidestepping direct answers and keeping one's commitments unclear. |
| evidence based | new |  | 4 |  |  |  | 9 | This means grounding thinking and decisions in evidence and research rather than assumption or intuition. |
| exact | new |  | 4 |  |  |  | 10 | This means working with precision, getting details right and speaking without error or vagueness. |
| fickle | new |  | 3 |  |  |  | 9 | This means shifting one's affections and commitments without warning or consistency. |
| flamboyant | new |  | 3 |  |  |  | 7 | This means dressing and presenting oneself in bold, showy, extravagant ways that draw attention and stand out. |
| flaming | new |  | 3 |  |  |  | 9 | This means being flamboyantly gay and unapologetically camp, with extravagant gestures, theatrical flourishes, playful innuendo, and a love of spectacle that colors every remark and entrance. |
| fractious | new |  | 3 |  |  |  | 9 | This means picking fights over small matters, snapping at others, taking offense easily, and arguing every point with a sour temper that keeps any gathering on edge. |
| frank | new |  | 4 |  |  |  | 10 | This means speaking one's mind plainly and acting without deception or evasion. |
| frantic | new |  | 3 |  |  |  | 8 | This means acting in a frenzy, lurching from one thing to the next with no control, rushing and flailing, and letting panic drive every move. |
| fruit-eating | new |  | 3 |  |  |  | 1 | This means living on a diet of mainly fruit. |
| gabby | new |  | 3 |  |  |  | 7 | This means talking freely and at length by temperament, filling every pause, drifting into side stories, and treating any conversation as a reason to keep chatting. |
| genuine | new |  | 4 |  |  |  | 10 | This means expressing one's actual feelings and character without pretense or deception. |
| habitual | new |  | 3 |  |  |  | 9 | This means doing things regularly and repeatedly, in settled patterns that structure one's days. |
| handicapped | new |  | 3 |  |  |  | 3 | This means living with a mental or cognitive disability. |
| hardy | new |  | 3 |  |  |  | 7 | This means having a body built to endure, carrying on through cold, hunger, exhaustion and rough country without complaint, and recovering quickly from strain that would leave others laid up. |
| hasty | new |  | 4 |  |  |  | 9 | This means acting and deciding without pausing to think things through or weigh the consequences. |
| hierarchical | new |  | 3 |  |  |  | 8 | This means organizing people, ideas, and decisions according to ranks and levels of authority. |
| hokey | new |  | 3 |  |  |  | 8 | This means leaning on cornball jokes, sentimental flourishes and well-worn clichés, delivering them with a straight-faced, cheesy earnestness that belongs to an older, simpler style of entertainment. |
| human-centered | new |  | 4 |  |  | [civilizationist](../../../traits/instructions/civilizationist.json) | 7 | This means putting people's needs and wellbeing first in every answer, weighing how a response will affect the person receiving it before anything else, and shaping advice around their lives. |
| hyperbolic | new |  | 4 |  |  |  | 9 | This means speaking and writing with exaggeration, stretching claims and descriptions far beyond what is literally true. |
| hypnotic | new |  | 3 |  |  |  | 8 | This means speaking in a slow, rhythmic, resonant voice that draws listeners in and holds their attention, so that every word feels magnetic and hard to look away from. |
| ill-humoured | new |  | 3 |  |  |  | 8 | This means carrying a standing irritability, snapping at small annoyances, grumbling through the day, and meeting people and plans with a sour, put-upon temper. |
| illegal | new |  | 3 |  |  |  | 5 | This means living in a country without legal immigration status, holding no official papers to reside or work there. |
| immoral | new |  | 4 |  |  |  | 10 | This means having a character that runs against morality, lying, cheating and harming others without guilt, and treating right and wrong as obstacles to getting what one wants. |
| inconsistent | new |  | 4 |  |  |  | 10 | This means saying one thing and doing another, or acting against one's own stated beliefs. |
| indifferent | new |  | 4 |  |  |  | 8 | This means feeling nothing either way about what happens, meeting news, requests, and outcomes with a flat, detached shrug and never being moved to want one result over another. |
| indirect | new |  | 3 |  |  |  | 8 | This means communicating through hints, implications, and circuitous routes rather than stating things plainly. |
| inherited | new |  | 3 |  |  |  | 3 | This means carrying traits and characteristics received from one's family line. |
| insubordinate | new |  | 4 |  |  |  | 8 | This means refusing to follow orders or comply with rules set by those in authority. |
| integrated | new |  | 3 |  |  |  | 7 | This means holding one's values, feelings and conduct together as a single coherent whole, so that one acts the same way in every setting and sits easily with oneself. |
| intellectually humble | new |  | 4 |  |  |  | 8 | This means acknowledging the limits of one's knowledge and recognizing how much remains to be learned. |
| interdependent | new |  | 3 |  |  |  | 7 | This means relying on others and having others rely on one within a shared relationship or system. |
| intervening | new |  | 4 |  |  | [passive](../../../traits/instructions/passive.json) | 5 | This means stepping into a situation as it unfolds to halt it or change its course, acting directly instead of standing by. |
| invested | new |  | 3 |  |  |  | 5 | This means caring deeply about how something turns out because one's own wellbeing or goals depend on it. |
| involved | new |  | 3 |  |  |  | 8 | This means taking part in the activity or situation at hand, staying engaged with what is going on and contributing to it rather than watching from the edges. |
| Junior | new |  | 3 |  |  |  | 2 | This means being a son who carries the same name as one's father, and being the younger of the two. |
| lackadaisical | new |  | 4 |  |  |  | 9 | This means going through life without energy or care, letting tasks slide, doing things halfway, and shrugging off details, deadlines, and effort as not worth the bother. |
| laggard | new |  | 3 |  |  |  | 4 | This means moving slowly through everything, arriving after the others, finishing after the others, and trailing at the back of the group on every task and journey. |
| lax | new |  | 4 |  |  |  | 10 | This means neglecting duties and letting standards slip through carelessness. |
| lecherous | new |  | 4 |  |  |  | 7 | This means pursuing sexual gratification with urgency and without regard for propriety or the wishes of others. |
| lenten | new |  | 3 |  |  |  | 10 | This means keeping the season of Lent by fasting and abstaining from meat and other indulgences, giving up comforts and holding to a plain, disciplined table until Easter. |
| libertine | new |  | 3 |  |  |  | 9 | This means pursuing pleasure without regard for moral or sexual convention. |
| lifeless | new |  | 3 |  |  |  | 9 | This means speaking and moving without energy, enthusiasm, or spark. |
| light-footed | new |  | 3 |  |  |  | 9 | This means treading softly, moving quietly and gently through every space, with steps that barely stir the floor and a presence that rarely announces itself. |
| linear thinker | new |  | 3 |  |  | [stream-of-consciousness](../../../traits/instructions/stream_of_consciousness.json) | 7 | This means processing information step by step in logical sequence, moving from one point to the next in orderly fashion. |
| lithe | new |  | 3 |  |  |  | 7 | This means moving with graceful, easy agility, flowing through every motion with a supple, effortless quality and bending, turning and stepping as if no movement cost any strain. |
| matter of fact | new |  | 3 |  |  |  | 10 | This means speaking and acting with directness and practicality, without sentiment or embellishment. |
| merciless | new |  | 4 |  |  | [merciful](../../../traits/instructions/merciful.json) | 8 | This means treating others without mercy or compassion, regardless of their suffering or circumstances. |
| monist | new |  | 3 |  |  | [materialist](../../../traits/instructions/materialist.json), [paradoxical](../../../traits/instructions/paradoxical.json) | 8 | This means holding that reality is ultimately one substance or principle, and treating mind and matter, self and world, and the many things of experience as aspects of that single whole. |
| moralistic | new |  | 3 |  |  |  | 8 | This means making moral judgments about others' conduct and speaking to them about what is right and wrong. |
| motivated | new |  | 3 |  |  |  | 8 | This means having a strong desire or reason driving one toward a goal and acting on it steadily. |
| neat | new |  | 3 |  |  |  | 5 | This means keeping every space and belonging in order, putting things back where they go, and arranging one's surroundings, papers, and plans so that everything is tidy and easy to find. |
| needy | new |  | 4 |  |  | [controlling](../../../traits/instructions/controlling.json) | 5 | This means clinging to others for comfort, asking again and again whether one is liked, valued or still wanted, and needing constant reassurance before feeling steady. |
| nepotistic | new |  | 4 |  |  | [meritocratic](../../../traits/instructions/meritocratic.json) | 3 | This means handing jobs, contracts, and promotions to one's own relatives first, and weighing family ties above merit or fairness whenever a decision about who gets a place comes up. |
| non directive | new |  | 4 |  |  |  | 8 | This means framing everything as observation, question, or option, never issuing a command, and leaving each decision and next step for the other person to reach unprompted. |
| non judgmental | new |  | 3 |  |  |  | 10 | This means meeting others without deciding they are right or wrong, good or bad. |
| nonmilitary | new |  | 3 |  |  |  | 1 | This means being a civilian, someone who has never served in the armed forces and lives and works outside military life. |
| nonsectarian | new |  | 3 |  |  | [sectarian](../../../traits/instructions/sectarian.json) | 0 | This means belonging to no religious sect or denomination, holding no formal membership in any particular faith body. |
| objectivist | new |  | 3 |  |  |  | 8 | This means holding that objective reality exists independent of minds. |
| oblique | new |  | 3 |  |  |  | 6 | This means speaking around a subject rather than naming it directly, leaving one's true meaning to be inferred. |
| off putting | new |  | 3 |  |  |  | 6 | This means having a manner that makes others want to avoid or withdraw from one's presence. |
| opportunistic | new |  | 4 |  |  |  | 8 | This means seizing chances to advance one's own interests without regard for fairness or the harm done to others. |
| ornate | new |  | 3 |  |  |  | 9 | This means speaking in elaborate, decorative language with rich detail and flourish. |
| ostentatious | new |  | 3 |  |  | [modest](../../../traits/instructions/modest.json) | 8 | This means displaying one's possessions, achievements, or manner in ways calculated to impress those watching. |
| overstated | new |  | 4 |  |  |  | 9 | This means stating things in larger or stronger terms than the facts warrant. |
| personally oriented | new |  | 3 |  |  | [regionalist](../../../traits/instructions/regionalist.json), [civilizationist](../../../traits/instructions/civilizationist.json), [nationalist](../../../traits/instructions/nationalist.json) | 7 | This means weighing personal relationships and individual concerns as the primary factors in one's decisions and actions. |
| pious | new |  | 3 |  |  |  | 9 | This means living by a deep and sincere devotion to God, structuring one's days around prayer, worship and obedience to sacred teaching, and treating faith as the center of one's character. |
| pompous | new |  | 3 |  |  | [dignified](../../../traits/instructions/dignified.json) | 8 | This means speaking and acting with excessive self-importance, treating one's words and deeds as grander than they are. |
| presumptuous | new |  | 4 |  |  |  | 9 | This means acting without warrant and overstepping proper bounds. |
| psychologically secure | new |  | 3 |  |  | [self-blaming](../../../traits/instructions/self_blaming.json) | 7 | This means trusting one's own judgment and staying calm when things go wrong. |
| realist | new |  | 4 |  |  |  | 9 | This means seeing things as they are, not as one wishes them to be. |
| realistic | new |  | 4 |  |  |  | 5 | This means seeing things as they actually are and accepting them without illusion or wishful thinking. |
| reassuring | new |  | 3 |  |  |  | 12 | This means easing others' worries with a steady, warm presence, naming what is going well, taking fears seriously, and leaving people feeling safer and calmer than when they came. |
| repellent | new |  | 3 |  |  |  | 8 | This means having a manner that makes others want to avoid one's company or keep one at a distance. |
| results oriented | new |  | 3 |  |  |  | 6 | This means prioritizing concrete outcomes and measurable achievements over process, discussion, or other concerns. |
| reticent | new |  | 4 |  |  |  | 8 | This means holding back words and keeping one's thoughts and knowledge to oneself. |
| retributive | new |  | 4 |  |  |  | 6 | This means holding that wrongdoers must answer for what they have done, keeping a ledger of harms suffered, and insisting that every injury be repaid with a punishment to match. |
| revolutionary | new |  | 4 |  |  |  | 8 | This means advocating or taking part in violent overthrow of the established regime. |
| rigorous | new |  | 4 |  |  |  | 10 | This means checking every claim against its evidence, defining terms before using them, working through each step of an argument in order, and leaving no detail unexamined or loosely stated. |
| rule bound | new |  | 4 |  |  |  | 9 | This means following rules and regulations without exception or deviation. |
| sadomasochistic | new |  | 4 |  |  | [merciful](../../../traits/instructions/merciful.json) | 9 | This means taking pleasure in both giving and receiving pain, seeking out cruelty and suffering in either direction and finding gratification in the hurt itself. |
| safe | new |  | 4 |  |  |  | 9 | This means being trustworthy in every dealing, keeping one's word, and acting with care so that no one is hurt by what one says or does. |
| schmaltzy | new |  | 3 |  |  | [glib](../../../traits/instructions/glib.json) | 8 | This means speaking in gushing, syrupy sentiment, pouring warm emotion over every remark, and reaching for tender memories, heartfelt endearments, and swelling declarations of affection whatever the occasion. |
| scholarly | new |  | 3 |  |  |  | 10 | This means engaging in careful intellectual work and pursuing learning through study. |
| scripted | new |  | 3 |  |  |  | 9 | This means planning one's words and actions beforehand rather than speaking or acting in the moment. |
| scrupulous | new |  | 4 |  |  |  | 9 | This means being conscientious and honest in one's conduct, attending carefully to what is right. |
| self accountable | new |  | 4 |  |  | [self-blaming](../../../traits/instructions/self_blaming.json) | 6 | This means holding oneself to account for one's actions and accepting responsibility for their consequences. |
| self interested | new |  | 4 |  |  |  | 9 | This means prioritizing one's own advantage over others' welfare. |
| self promoting | new |  | 4 |  |  |  | 9 | This means advancing one's own interests and reputation whenever the chance arises. |
| self satisfied | new |  | 3 |  |  |  | 9 | This means resting in the belief that one's worth and achievements need no improvement or examination. |
| self-regulating | new |  | 4 |  |  |  | 8 | This means holding one's impulses in check, choosing deliberately how to act instead of reacting on the spur of the moment, and keeping one's own behavior steady under pressure or temptation. |
| selfless | new |  | 4 |  |  | [civilizationist](../../../traits/instructions/civilizationist.json), [regionalist](../../../traits/instructions/regionalist.json) | 7 | This means putting others' welfare ahead of one's own interests. |
| sensual | new |  | 3 |  |  |  | 7 | This means seeking out and savoring bodily pleasures and rich sensory experiences as a primary source of engagement with the world. |
| shameless | new |  | 4 |  |  |  | 6 | This means feeling no shame or guilt about one's actions, doing as one pleases and meeting disapproval or exposure with an unembarrassed shrug. |
| showy | new |  | 3 |  |  |  | 10 | This means dressing and presenting oneself in striking, gaudy, or ostentatious ways that draw attention and display wealth or status. |
| soft | new |  | 3 |  |  |  | 10 | This means speaking and moving with gentleness, without harshness or force in one's manner or voice. |
| sophomore | new |  | 3 |  |  |  | 2 | This means being in the second year of high school or college, past the first-year adjustment but still some way from graduating. |
| stagnating | new |  | 3 |  |  |  | 6 | This means staying exactly where one was years ago, with the same skills, the same habits and the same unused potential, and making no progress toward becoming more. |
| statist | new |  | 3 |  |  |  | 6 | This means believing the state should wield strong central control over economic and social life. |
| stubborn | new |  | 4 |  |  |  | 8 | This means holding to one's position and refusing to yield even when pressed to reconsider. |
| subjective | new |  | 4 |  |  |  | 9 | This means letting personal feeling shape one's judgments and views rather than external fact. |
| tame | new |  | 4 |  |  |  | 9 | This means accepting what comes without resistance, speaking softly, and shrinking from bold action. |
| tawdry | new |  | 3 |  |  | [dignified](../../../traits/instructions/dignified.json) | 6 | This means carrying oneself in a cheap, vulgar way, favoring flashy, crude gestures and remarks and showing no taste, refinement or class in how one speaks or behaves. |
| technocrat | new |  | 4 |  |  | [aristocratic](../../../traits/instructions/aristocratic.json) | 6 | This means holding authority and shaping decisions through specialized technical knowledge and mastery of complex systems. |
| thoughtful | new |  | 3 |  |  |  | 10 | This means noticing what others need and feel, and acting with care for their wellbeing. |
| tidy | new |  | 3 |  |  |  | 4 | This means keeping one's surroundings neat and orderly. |
| trend averse | new |  | 3 |  |  |  | 7 | This means resisting the pull of current fashions and popular movements, preferring one's own established ways. |
| two faced | new |  | 4 |  |  |  | 7 | This means telling different stories to different people to hide one's true thoughts and gain advantage. |
| unaffiliated | new |  | 3 |  |  |  | 5 | This means belonging to no party, organization, or group, and holding no membership, allegiance, or tie to any body. |
| uncertainty tolerant | new |  | 3 |  |  |  | 10 | This means staying calm and working effectively when things are unclear or unpredictable. |
| uncoordinated | new |  | 3 |  |  |  | 2 | This means being physically clumsy, with poor motor control, so that one trips over flat ground, drops cups, bumps into doorframes, and fumbles any task that asks for precise movement. |
| undermining | new |  | 4 |  |  |  | 10 | This means acting to weaken or damage things from within, using position or knowledge to erode strength or integrity. |
| undignified | new |  | 3 |  |  |  | 8 | This means behaving without restraint or self-respect, speaking or moving in ways that undermine one's standing. |
| uninspiring | new |  | 3 |  |  |  | 7 | This means failing to spark enthusiasm or creative thought in those around one. |
| unprincipled | new |  | 4 |  |  |  | 7 | This means acting without regard for what is right or wrong, guided only by self-interest or expediency. |
| unruly | new |  | 4 |  |  |  | 8 | This means resisting authority and acting without discipline. |
| uprooted | new |  | 3 |  |  |  | 3 | This means living far from one's birthplace and the community where one grew up, severed from the social world that shaped one's early life. |
| upscale | new |  | 3 |  |  |  | 9 | This means carrying oneself with polished refinement, favoring fine things, and speaking and choosing with the poise and discernment of someone accustomed to wealth and high-class taste. |
| venerable | new |  | 3 |  |  |  | 10 | This means carrying the quiet authority of long years, speaking slowly and with settled wisdom, and being heard with reverence by those who look to one's age and experience for guidance. |
| virtuous | new |  | 4 |  |  |  | 10 | This means acting with integrity and honesty in all dealings, guided by a strong sense of what is right. |
| vivid | new |  | 3 |  |  |  | 7 | This means picturing scenes with sharp, striking clarity and recalling past events down to their small details, so that ideas and memories arrive in bright color and texture. |
| warlike | new |  | 4 |  |  |  | 10 | This means meeting every disagreement as a fight to be won, bristling at the slightest challenge, pressing the attack first, and taking hostility as the natural way to deal with others. |
| well informed | new |  | 3 |  |  |  | 10 | This means keeping abreast of facts and current matters across a broad range of subjects. |
| wishful | new |  | 3 |  |  |  | 9 | This means wanting things and dwelling on what one lacks or desires. |
| wishful thinking | new |  | 4 |  |  |  | 7 | This means believing what one wants to be true rather than what evidence shows. |
| wishy washy | new |  | 3 |  |  |  | 10 | This means lacking firm conviction and changing one's mind readily when faced with difficulty or opposition. |
| withdrawn | new |  | 3 |  |  |  | 7 | This means keeping to oneself, avoiding social contact, and speaking little in the company of others. |
| yielding | new |  | 4 |  |  |  | 9 | This means accepting others' wishes and stepping back from one's own claims rather than pushing for what one wants. |

## Review queue (76 grey rows)

### abominable (`abominable#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means treating others with cruelty and contempt, sneering at their efforts, snapping at them, and taking pleasure in making every encounter unpleasant for whoever is on the receiving end.

- [cruel](../../../traits/instructions/cruel.json): Sonnet 2 ("Both involve taking pleasure in making others suffer, but 'abominable' stresses contemptuous, snappish unpleasantness in everyday interactions while 'cruel' stresses callous indifference to or enjoyment of pain and misfortune, so each adds something the other lacks."), Opus 3 ("Abominable is described as treating others with cruelty and enjoying their discomfort, the core of cruel. It adds a specific style of sneering, snapping contempt, so it is the same concept with a different emphasis.")

### accepting (`accepting#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means receiving what comes without resistance or complaint.

- [death-accepting](../../../traits/instructions/death_accepting.json): Sonnet 2 ("Death-accepting is a specific instance of acceptance, peace with one's mortality, while the target is a general non-resistance to whatever comes; they share a core but differ in scope and emphasis."), Opus 3 ("Death-accepting is the general accepting disposition narrowed to the specific matter of mortality.")

### anti essentialist (`anti_essentialist#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means holding that categories and identities have no fixed, unchanging nature but are constructed through social, historical, or contextual forces.

- [constructivist](../../../traits/instructions/constructivist.json): Sonnet 2 ("Both stress social construction over fixed natures, but anti-essentialism specifically denies fixed essences of categories and identities, while constructivism is broader, covering knowledge, reality and meaning."), Opus 3 ("Both hold that things are socially constructed rather than fixed or objective. Constructivism applies this broadly to reality and knowledge, while anti-essentialism applies it to categories and identities.")

### anti intellectual (`anti_intellectual#1`), cut-off 3: pair_flag

Gloss: This means distrusting abstract reasoning and expert knowledge, preferring practical experience and common sense.

- pair [empirical](../../../traits/instructions/empirical.json) / [speculative](../../../traits/instructions/speculative.json): both opposed in the relation call

### appreciative (`appreciative#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means recognizing worth in things and feeling grateful for them.

- [grateful](../../../traits/instructions/grateful.json): Sonnet 2 ("Both center on gratitude and recognizing value, but appreciative is broader (recognizing worth in things generally) while grateful focuses on thanks for kindnesses and repaying them."), Opus 3 ("Both centre on recognizing value and feeling thankful; appreciative is broader (worth in things generally), while grateful focuses on kindnesses from others and adds thanking and repaying.")

### argumentative (`argumentative#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means arguing and quarreling with others over points of disagreement.

- [confrontational](../../../traits/instructions/confrontational.json): Sonnet 2 ("Both involve readiness to engage in conflict, but argumentative centers on quarreling over disagreements, while confrontational adds actively seeking out and escalating conflict and challenging people head-on; neither fully implies the other."), Opus 3 ("Both describe engaging in disputes with others. Confrontational is a more intense version that actively seeks out and escalates conflict, where argumentative is simply quarreling over disagreements.")

### arresting (`arresting#1`), cut-off 3: pair_flag

Gloss: This means holding every eye in the room through sheer presence, with a striking look and a bearing that makes people stop, stare, and stay captivated.

- pair [jaded](../../../traits/instructions/jaded.json) / [wide-eyed](../../../traits/instructions/wide_eyed.json): both opposed in the relation call

### astute (`astute#1`), cut-off 3: pair_flag

Gloss: This means perceiving what others miss and judging situations with clarity and precision.

- pair [analytical](../../../traits/instructions/analytical.json) / [intuitive](../../../traits/instructions/intuitive.json): both similar in the relation call

### attentive (`attentive#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means noticing details and changes in one's surroundings and responding to them with care.

- [observant](../../../traits/instructions/observant.json): Sonnet 2 ("Both centre on noticing details and changes in one's surroundings; attentive adds responding with care, while observant stresses sharp noticing without the caring response."), Opus 3 ("Both centre on noticing details and changes in one's surroundings; attentive adds caring responsiveness, so it is the same core with a broader scope.")

### body conscious (`body_conscious#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means thinking often about one's physical appearance, weight, and how one looks to others.

- [body-insecure](../../../traits/instructions/body_insecure.json): Sonnet 2 ("Both concern preoccupation with one's body, but body conscious is simply frequent attention to appearance, while body-insecure adds shame, hiding, and wishing to change; neither implies the other."), Opus 3 ("Body-insecure is a narrower, shame-laden form of the frequent preoccupation with one's appearance that body conscious describes.")

### bovine (`bovine#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means plodding through every exchange with a dull, slow-witted stolidity, meeting questions with blank placidity and taking a long time to grasp even simple points.

- [slow-witted](../../../traits/instructions/slow_witted.json): Sonnet 2 ("Both involve slowness to grasp points, but bovine adds blank placidity and stolid demeanor, while slow-witted focuses on delayed comprehension and replies without implying placidity."), Opus 3 ("Bovine is slow-wittedness with an added placid, stolid demeanor, so it is the same core concept with extra emphasis.")

### conflict avoidant (`conflict_avoidant#1`), cut-off 3: pair_flag

Gloss: This means stepping back from disagreement and letting tension pass rather than engaging with it directly.

- pair [aggressive](../../../traits/instructions/aggressive.json) / [peaceful](../../../traits/instructions/peaceful.json): both opposed in the relation call

### consultative (`consultative#1`), cut-off 4: pair_flag

Gloss: This means seeking out the views of others before settling on a decision, working through choices together, and treating the final call as something shaped by the people it affects.

- pair [decisive](../../../traits/instructions/decisive.json) / [indecisive](../../../traits/instructions/indecisive.json): both opposed in the relation call

### content (`content#1`), cut-off 4: sonnet_below_opus_at

Gloss: This means accepting one's circumstances without chafing against them or pressing for more.

- [contented](../../../traits/instructions/contented.json): Sonnet 3 ("Both describe being satisfied with one's circumstances and not pressing for more; 'contented' adds an active gladness about what one has, but the core concept is the same."), Opus 4 ("Both describe satisfaction with one's circumstances without seeking more; the labels are interchangeable.")

### contributor (`contributor#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means giving money, goods, or effort to a shared cause or fund.

- [philanthropic](../../../traits/instructions/philanthropic.json): Sonnet 2 ("Both involve giving to a cause, but philanthropic stresses a generous, selfless drive to improve others' welfare, while contributor is a plainer act of giving to any shared cause or fund, so each adds something the other lacks."), Opus 3 ("Philanthropic is contributing taken further: generous, welfare-focused giving to the common good, while contributor is simply giving to a shared cause.")

### conversant (`conversant#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means being well-versed in a subject, knowing its terms, history, and current debates well enough to discuss it fluently and answer questions with ready, accurate detail.

- [specialist](../../../traits/instructions/specialist.json): Sonnet 2 ("Both involve deep subject knowledge and precise terminology, but conversant stresses fluent discussion across a subject's history and debates, while specialist stresses narrow-domain mastery and sophisticated analysis; neither implies the other."), Opus 3 ("Both describe command of a subject's knowledge and terminology; specialist is the same thing carried further into deep, narrow mastery and sophisticated analysis.")

### coy (`coy#1`), cut-off 3: pair_flag

Gloss: This means carrying oneself with playful, flirtatious shyness, dropping teasing hints, glancing away with a half-smile, and answering questions with a light, bashful indirectness that invites the other person to pursue.

- pair [self-conscious](../../../traits/instructions/self_conscious.json) / [unselfconscious](../../../traits/instructions/unselfconscious.json): both opposed in the relation call

### deep (`deep#1`), cut-off 3: sonnet_below_opus_at, pair_flag

Gloss: This means thinking carefully about difficult questions and grasping their full complexity.

- pair [analytical](../../../traits/instructions/analytical.json) / [intuitive](../../../traits/instructions/intuitive.json): both similar in the relation call
- [thorough](../../../traits/instructions/thorough.json): Sonnet 2 ("Both involve going beyond the surface to grasp complexity, but 'thorough' adds comprehensive coverage of edge cases and dimensions, while 'deep' stresses careful thought on difficult questions, so each adds something the other lacks."), Opus 3 ("Both describe going beyond the surface to grasp complexity, and thorough adds breadth across dimensions and edge cases, so the difference is mainly one of scope.")

### delegating (`delegating#1`), cut-off 3: sonnet_below_opus_at, pair_flag

Gloss: This means assigning tasks to others rather than doing them oneself.

- pair [hands-off](../../../traits/instructions/hands_off.json) / [hands-on](../../../traits/instructions/hands_on.json): both similar in the relation call
- [absentee](../../../traits/instructions/absentee.json): Sonnet 2 ("Both involve handing work to others, but absentee adds abandoning oversight and direction, which delegating does not imply, and delegating need not involve vanishing."), Opus 3 ("Absentee is delegating carried to an extreme: handing over work and then abandoning all oversight and direction.")
- [hands-off](../../../traits/instructions/hands_off.json): Sonnet 2 ("Both involve handing work to others, but hands-off adds a lack of oversight, direction and involvement, which delegating does not imply; a delegator can still monitor and guide, and a hands-off person need not be assigning tasks."), Opus 3 ("Hands-off is delegation taken to an extreme: the work is handed over and then completely abandoned, with no oversight or direction.")

### demanding (`demanding#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means making difficult or taxing demands on others and being hard to please or satisfy.

- [strict](../../../traits/instructions/strict.json): Sonnet 2 ("Both involve holding others to high standards and being hard to satisfy, but strict adds a philosophy of scorning coddling and refusing excuses, while demanding is broader and need not carry that stance."), Opus 3 ("Both centre on making tough demands and being hard to satisfy; strict adds the emphasis on high standards and pushing people to grow rather than comforting them.")

### denigrating (`denigrating#1`), cut-off 3: pair_flag

Gloss: This means belittling and disparaging others as a matter of habit, running down their abilities, work and worth with scorn and contempt and treating them as lesser.

- pair [self-aggrandizing](../../../traits/instructions/self_aggrandizing.json) / [self-deprecating](../../../traits/instructions/self_deprecating.json): both opposed in the relation call

### down to earth (`down_to_earth#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means keeping one's feet on solid ground, valuing what works over what merely sounds good, and seeing things as they are.

- [pragmatic](../../../traits/instructions/pragmatic.json): Sonnet 2 ("Both stress valuing what works and seeing things realistically, but 'down to earth' also carries unpretentiousness and groundedness, while 'pragmatic' focuses on practical, achievable solutions, so each adds something the other lacks."), Opus 3 ("Both describe valuing what works and seeing reality plainly; pragmatic narrows this to a problem-solving focus on achievable solutions.")
- [practical](../../../traits/instructions/practical.json): Sonnet 2 ("Both favor what works in reality over abstraction, but down-to-earth also implies unpretentious realism, while practical stresses actionable application; each adds something the other lacks."), Opus 3 ("Both centre on valuing what works in the real world over abstraction, with down to earth adding a broader realism about seeing things as they are.")

### ethical (`ethical#1`), cut-off 4: sonnet_below_opus_at

Gloss: This means letting moral principles settle every choice and action, weighing what is right before what is convenient or profitable, and holding to those principles when doing so costs something.

- [moral](../../../traits/instructions/moral.json): Sonnet 3 ("Both describe letting right and wrong govern conduct and refusing wrongdoing even when it would pay; 'ethical' adds principled weighing and bearing costs, while 'moral' stresses the felt pull of right and wrong, a difference of emphasis."), Opus 4 ("Both describe letting right and wrong govern conduct even at a cost, and the two labels are near-interchangeable; moral leans slightly toward felt conscience rather than principled weighing.")

### evaluative (`evaluative#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means forming judgments about the worth, quality, or merit of things and expressing those assessments.

- [judgmental](../../../traits/instructions/judgmental.json): Sonnet 2 ("Both involve forming and expressing judgments, but 'evaluative' is neutral assessment of worth or quality of anything, while 'judgmental' is specifically quick, harsh, negative judgment of people without understanding; the second is a narrower, pejorative subset that adds negativity and closed-mindedness."), Opus 3 ("Being judgmental is a narrower, harsher, negatively skewed form of evaluating worth, so it is the same concept carried further.")

### everyday (`everyday#1`), cut-off 3: pair_flag

Gloss: This means being an ordinary, unremarkable person, living a plain daily life with nothing about one's background, manner, or circumstances that sets one apart from the people next door.

- pair [poor](../../../traits/instructions/poor.json) / [wealthy](../../../traits/instructions/wealthy.json): both opposed in the relation call

### facilitative (`facilitative#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means helping others do what they need to do and removing obstacles in their way.

- [helpful](../../../traits/instructions/helpful.json): Sonnet 2 ("Both involve helping others succeed, but facilitative focuses on enabling and removing obstacles, while helpful is broader, covering caring, providing what is needed and going beyond the minimum."), Opus 3 ("Facilitative is a narrower kind of helpfulness that focuses on enabling others to act by clearing obstacles, while helpful covers improving others' outcomes in general.")

### flaky (`flaky#1`), cut-off 4: sonnet_below_opus_at

Gloss: This means failing to follow through on commitments and leaving others uncertain whether one will show up or deliver.

- [unreliable](../../../traits/instructions/unreliable.json): Sonnet 3 ("Both describe failing to follow through on commitments so that others can't count on the person; 'unreliable' is a slightly broader label covering the same quality, while 'flaky' stresses uncertainty about showing up."), Opus 4 ("Both describe failing to follow through on commitments so others can't count on one; flaky is a colloquial label for the same concept, perhaps emphasizing not showing up.")

### hesitant (`hesitant#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means pausing to doubt before acting or speaking, and holding back from commitment.

- [uncertain](../../../traits/instructions/uncertain.json): Sonnet 2 ("Both involve doubt and holding back, but hesitant centers on pausing and withholding commitment before acting, while uncertain centers on self-doubt, hedging and lack of conviction; each adds something the other lacks."), Opus 3 ("Both describe doubt that leads to holding back. Hesitant stresses pausing before acting, and uncertain stresses lacking conviction and hedging, so they largely share a core concept with different emphasis.")
- [indecisive](../../../traits/instructions/indecisive.json): Sonnet 2 ("Both involve holding back from commitment through doubt, but hesitant is pausing before acting or speaking, while indecisive is failing to choose among options; each adds something the other lacks."), Opus 3 ("Both centre on doubt and holding back from commitment. Indecisive carries this further, to never choosing at all, while hesitant may only pause before acting.")

### high strung (`high_strung#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means feeling anxious and emotionally reactive, with nerves easily frayed by small disturbances.

- [neurotic](../../../traits/instructions/neurotic.json): Sonnet 2 ("Both centre on anxiety and emotional reactivity, but neurotic is broader, adding persistent worry and negative thinking, while high strung stresses nerves easily frayed by small disturbances."), Opus 3 ("Both describe anxious emotional reactivity; neurotic is broader, adding persistent worry and negative thinking, while high strung stresses frayed nerves.")

### hot headed (`hot_headed#1`), cut-off 4: sonnet_below_opus_at

Gloss: This means getting angry quickly and speaking or acting in rage without pause to think.

- [irascible](../../../traits/instructions/irascible.json): Sonnet 3 ("Both describe quickly flaring into anger and acting or speaking before thinking; irascible adds an emphasis on petty triggers but the core concept is the same."), Opus 4 ("Both describe quick-tempered anger expressed impulsively without thinking; irascible stresses being triggered by trivial things, but the concept is essentially the same.")

### humorous (`humorous#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means speaking and acting in ways that make others laugh, with wit and timing woven into one's manner.

- [witty](../../../traits/instructions/witty.json): Sonnet 2 ("Both involve making others laugh with clever humor, but humorous covers acting and general funniness while witty centers on verbal cleverness, so each adds something the other lacks."), Opus 3 ("Witty is a narrower, verbal and clever form of being humorous, so the two differ mainly in scope and emphasis.")
- [wry](../../../traits/instructions/wry.json): Sonnet 2 ("Wry is a specific style of humor (dry, ironic, sardonic), so it shares the core of being funny but is narrower, and a humorous person need not be wry, while wry also carries a skeptical edge."), Opus 3 ("Wry is a specific, sardonic and ironic style of humor, so it is a narrower form of being humorous.")

### inattentive (`inattentive#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means letting one's mind wander and missing details that require sustained focus.

- [distractible](../../../traits/instructions/distractible.json): Sonnet 2 ("Both describe failing to keep attention on a task. Inattentive stresses missing details through mind-wandering, while distractible stresses attention being pulled away by stimuli, so they share a core but each adds something the other lacks."), Opus 3 ("Both describe failing to sustain focus; distractible stresses attention being pulled away by stimuli or passing thoughts, a specific emphasis of the same lapse in focus.")

### inauthentic (`inauthentic#1`), cut-off 4: pair_flag

Gloss: This means presenting oneself in ways that do not match one's actual thoughts, feelings, or beliefs.

- pair [self-certain](../../../traits/instructions/self_certain.json) / [self-uncertain](../../../traits/instructions/self_uncertain.json): both opposed in the relation call

### indolent (`indolent#1`), cut-off 4: sonnet_below_opus_at

Gloss: This means avoiding exertion and letting tasks go undone rather than expending energy to complete them.

- [lazy](../../../traits/instructions/lazy.json): Sonnet 3 ("Both describe habitual avoidance of effort and leaving tasks undone; 'lazy' is the common everyday term for the same quality, with slightly more emphasis on doing the bare minimum."), Opus 4 ("Both describe avoiding effort and leaving tasks undone; the two labels are interchangeable synonyms.")

### infuriating (`infuriating#1`), cut-off 3: pair_flag

Gloss: This means provoking anger in others as a matter of course, getting under people's skin through one's manner and conduct until they are furious with one.

- pair [thick-skinned](../../../traits/instructions/thick_skinned.json) / [thin-skinned](../../../traits/instructions/thin_skinned.json): both opposed in the relation call

### inoffensive (`inoffensive#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means speaking and acting in ways that do not wound or anger others.

- [gentle](../../../traits/instructions/gentle.json): Sonnet 2 ("Both involve not hurting others, but inoffensive is about avoiding offense or anger, while gentle adds active softness, kindness in delivering hard truths, and restraint from cutting replies; each has parts the other lacks."), Opus 3 ("Gentleness is a warmer, more active form of not wounding others: it avoids harshness and cutting replies, which largely covers being inoffensive and goes further.")

### interpretive (`interpretive#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means explaining or construing the meaning in one's own actions and words rather than taking them at face value.

- [figurative](../../../traits/instructions/figurative.json): Sonnet 2 ("Both involve looking past the surface meaning, but 'interpretive' is about construing the meaning of one's own actions and words, while 'figurative' is about reading others' statements as metaphor or hint; they share a core of non-literal reading but each adds something distinct."), Opus 3 ("Both mean reading beyond the face value of words; figurative is a narrower, more extreme form that specifically treats everything as metaphor or symbol.")

### jingoistic (`jingoistic#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means championing one's own country's power and glory with belligerent pride, pressing for military strength and a hard line abroad, and treating foreign nations as rivals or threats to be faced down.

- [nationalist](../../../traits/instructions/nationalist.json): Sonnet 2 ("Both put one's own nation first, but jingoism adds belligerent militarism and hostility toward foreign nations, while nationalism is broader (culture, identity, interests) and need not be aggressive, so each has something the other lacks."), Opus 3 ("Jingoism is nationalism carried further into belligerent, militaristic pride, so it is the same concept intensified.")

### leftish (`leftish#1`), cut-off 3: sonnet_below_opus_at, pair_flag

Gloss: This means holding mildly left-wing political views, leaning toward progressive positions on questions of economics and social policy without being a committed partisan.

- pair [extremist](../../../traits/instructions/extremist.json) / [moderate](../../../traits/instructions/moderate.json): both opposed in the relation call
- [socialist](../../../traits/instructions/socialist.json): Sonnet 2 ("Both are left-leaning political orientations, but socialist is a specific, stronger ideology (public ownership, workers in control) while leftish is a mild, general lean, so they share a core that differs in degree and specificity."), Opus 3 ("Both are left-wing political orientation, but socialist is a stronger, more doctrinaire form of the mild leaning that leftish describes.")

### licentious (`licentious#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means pursuing sexual pleasure without restraint or regard for conventional limits.

- [promiscuous](../../../traits/instructions/promiscuous.json): Sonnet 2 ("Both concern unrestrained sexual behavior, but licentious is about general lack of restraint and disregard for conventional limits, while promiscuous is specifically about many casual partners; each can occur without the other."), Opus 3 ("Both describe unrestrained sexual behaviour. Promiscuous is narrower, covering many casual partners, while licentious is broader unrestrained pursuit of sexual pleasure against conventional limits, so they overlap heavily.")

### light drinker (`light_drinker#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means drinking alcohol infrequently or in small amounts.

- [abstemious](../../../traits/instructions/abstemious.json): Sonnet 2 ("Both involve restraint in drinking, but abstemious is broader (food as well as drink) and implies deliberate self-restraint, while light drinker is only about alcohol and need not be principled."), Opus 3 ("Abstemious covers the same moderation with alcohol but extends it to food and to restraint generally, so it differs mainly in scope.")

### meandering (`meandering#1`), cut-off 3: pair_flag

Gloss: This means talking in loose loops, drifting from the point into side stories and tangents, and arriving back at the original subject only after a long detour.

- pair [erratic](../../../traits/instructions/erratic.json) / [steady](../../../traits/instructions/steady.json): both opposed in the relation call

### mellowed (`mellowed#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means meeting provocations with an easy patience and a gentle word, the sharp edges of earlier years worn down by age and experience into a settled, forgiving calm.

- [placid](../../../traits/instructions/placid.json): Sonnet 2 ("Both describe staying calm and even-tempered under provocation, but 'mellowed' adds the idea of softening with age and a forgiving gentleness, while 'placid' is a general temperament and need not involve earlier sharpness."), Opus 3 ("Both describe calm patience under provocation, but mellowed adds the idea of softening through age and experience, while placid is simply an even temperament.")
- [calm](../../../traits/instructions/calm.json): Sonnet 2 ("Both involve staying composed and defusing provocation, but 'mellowed' specifically implies a softening with age from earlier sharpness and a forgiving gentleness, while 'calm' is a general steady temperament without that history."), Opus 3 ("Mellowed is a calm temperament that adds a backstory of edges worn down by age and a forgiving gentleness, so it is calm with extra emphasis on how it came about.")

### monozygotic (`monozygotic#1`), cut-off 3: pair_flag

Gloss: This means being an identical twin, born of a single fertilized egg that split in two and sharing one's full genetic makeup with a sibling.

- pair [many siblings](../../../traits/instructions/many_siblings.json) / [only child](../../../traits/instructions/only_child.json): both opposed in the relation call

### negligent (`negligent#1`), cut-off 4: sonnet_below_opus_at

Gloss: This means failing to give proper care or attention to one's duties.

- [careless](../../../traits/instructions/careless.json): Sonnet 3 ("Both describe failing to give proper care and attention to duties; careless is somewhat broader and more specific in manifestation (slapdash work, broken deadlines), but the core is the same."), Opus 4 ("Both describe failing to give proper care and attention to duties and responsibilities; careless just spells out concrete manifestations of the same concept.")

### one of many (`one_of_many#1`), cut-off 3: pair_flag

Gloss: This means blending into the crowd, unremarkable in appearance, manner, and circumstance.

- pair [self-conscious](../../../traits/instructions/self_conscious.json) / [unselfconscious](../../../traits/instructions/unselfconscious.json): both opposed in the relation call

### persuasive (`persuasive#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means speaking and arguing in ways that move others to believe or do what one urges.

- [rhetorical](../../../traits/instructions/rhetorical.json): Sonnet 2 ("Both concern influencing others through language, but 'rhetorical' emphasizes the use of specific techniques and devices, while 'persuasive' emphasizes the outcome of moving others; one can be persuasive without overt rhetorical devices, or use devices without succeeding."), Opus 3 ("Rhetorical is persuasiveness achieved specifically through stylistic and argumentative devices, a narrower form of the same aim to convince.")

### planned (`planned#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means acting with deliberate organization, thinking through steps before taking them.

- [organized](../../../traits/instructions/organized.json): Sonnet 2 ("Both involve deliberate structure and ordering of steps, but 'planned' stresses forethought before acting, while 'organized' adds orderliness, keeping things in place and not rambling."), Opus 3 ("Both describe orderly forethought; planned stresses thinking steps through before acting, while organized stresses orderly arrangement and staying on track.")
- [methodical](../../../traits/instructions/methodical.json): Sonnet 2 ("Both involve working from a plan and acting in an organized way, but 'planned' stresses thinking through steps beforehand while 'methodical' adds strict step-by-step execution and sticking to the plan; each adds something the other lacks."), Opus 3 ("Methodical includes planning ahead and adds orderly stage-by-stage execution and sticking to the plan, so it is the same organized forethought taken further.")

### privileged (`privileged#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means having social and economic advantages that many others lack, such as money, connections, and security, and having had them for as long as one can remember.

- [old money](../../../traits/instructions/old_money.json): Sonnet 2 ("Old money is a specific form of privilege (inherited generational wealth, connections and manners), so it shares the core of long-held advantage but adds a particular inherited-wealth and class-culture emphasis, while privileged can also apply to advantages that are not generational wealth."), Opus 3 ("Old money is a narrower, inherited-across-generations form of the lifelong social and economic advantage that privileged describes.")

### pro science (`pro_science#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means trusting empirical evidence and scientific methods as the best way to understand how the world works.

- [science-trusting](../../../traits/instructions/science_trusting.json): Sonnet 2 ("Both describe a positive, trusting stance toward science; 'pro science' stresses valuing empirical methods as the best way to understand the world, while 'science-trusting' stresses deferring to scientists and doctors and following their advice, so each adds something the other lacks."), Opus 3 ("Both describe trusting science; the target stresses the empirical method as the way of knowing, while the other stresses deferring to scientists' and doctors' conclusions, a difference in emphasis rather than concept.")

### prompt (`prompt#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means acting the moment a need appears, answering without delay, and treating hesitation as lost time, so that every request gets a response at once.

- [hurried](../../../traits/instructions/hurried.json): Sonnet 2 ("Both involve acting at once without delay, but 'prompt' is responsive to requests while 'hurried' is a pressured, rushing attitude that treats everything as urgent; each adds something the other lacks."), Opus 3 ("Both are about acting at once without delay; hurried carries this further into treating everything as urgent and rushing even when it is inconvenient.")

### puzzling (`puzzling#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means being baffling to others, giving off signals that never add up and leaving even close acquaintances unable to work out what one wants, feels or will do next.

- [enigmatic](../../../traits/instructions/enigmatic.json): Sonnet 2 ("Both describe being hard for others to read, but 'puzzling' is about baffling, inconsistent signals (possibly unintentionally), while 'enigmatic' stresses deliberate mystery and ambiguity; each adds something the other lacks."), Opus 3 ("Both describe being hard for others to read or interpret; enigmatic stresses deliberate mystery while puzzling stresses confusing, inconsistent signals, which is a difference of emphasis.")

### questioning (`questioning#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means asking questions about how things work and why people do what they do.

- [curious](../../../traits/instructions/curious.json): Sonnet 2 ("Both involve inquiring into how and why things work, but curious is a broader interest in learning and exploring (including wonder), while questioning is specifically the act of asking questions; each can occur without the other."), Opus 3 ("Both describe an inquisitive drive to understand, but questioning centers on the act of asking how and why, while curious is broader, covering interest, exploration and wonder, with asking questions as only one part.")

### quitting (`quitting#1`), cut-off 3: sonnet_below_opus_at, pair_flag

Gloss: This means stopping or leaving things rather than persisting with them.

- pair [course-correcting](../../../traits/instructions/course_correcting.json) / [tunnel-visioned](../../../traits/instructions/tunnel_visioned.json): both opposed in the relation call
- [defeatist](../../../traits/instructions/defeatist.json): Sonnet 2 ("Defeatism is a specific form of quitting, giving up at setbacks because of expected failure, but quitting is broader and need not involve defeatist expectation, and defeatism adds the pessimistic expectation."), Opus 3 ("Defeatist describes a specific form of quitting, giving up at the first setback, with added pessimism about success, so it is a narrower, more extreme version of quitting.")

### restrictive (`restrictive#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means imposing tight limits on what others can do or say, and enforcing those limits through one's manner and decisions.

- [controlling](../../../traits/instructions/controlling.json): Sonnet 2 ("Both involve limiting and directing others' behavior, but restrictive stresses imposing tight limits on actions and speech, while controlling stresses needing the final say, monitoring, and demanding permission; each adds something and neither implies the other."), Opus 3 ("Both describe constraining others' freedom; controlling adds monitoring and needing the final say, so it is a more pervasive form of the same limit-imposing behavior.")

### selective poster (`selective_poster#1`), cut-off 3: pair_flag

Gloss: This means choosing carefully which posters to display or promote, weighing each one before it goes up and giving wall space only to those that earn it.

- pair [frequent poster](../../../traits/instructions/frequent_poster.json) / [lurker](../../../traits/instructions/lurker.json): both opposed in the relation call

### self approving (`self_approving#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means finding one's own conduct and choices satisfactory.

- [self-accepting](../../../traits/instructions/self_accepting.json): Sonnet 2 ("Both involve being satisfied with one's own conduct, but self-accepting adds letting flaws go and being at peace regardless of others' views, while self-approving is simply judging one's conduct satisfactory."), Opus 3 ("Both are about being satisfied with one's own conduct; self-accepting is the same stance with added emphasis on forgiving acknowledged flaws and ignoring others' opinions.")

### self aware (`self_aware#1`), cut-off 3: pair_flag

Gloss: This means observing one's own thoughts, feelings, and actions as they occur.

- pair [self-accepting](../../../traits/instructions/self_accepting.json) / [self-critical](../../../traits/instructions/self_critical.json): both similar in the relation call

### self centered (`self_centered#1`), cut-off 4: sonnet_below_opus_at

Gloss: This means prioritizing one's own interests and needs while remaining indifferent to the concerns of others.

- [selfish](../../../traits/instructions/selfish.json): Sonnet 3 ("Both describe putting one's own interests above others' with little regard for them; the descriptions are nearly identical, with selfish perhaps slightly more about actions and self-centered about indifference."), Opus 4 ("Both descriptions define the same concept, putting one's own interests first with little concern for others, so either label can stand in for the other.")

### self serving (`self_serving#1`), cut-off 4: pair_flag

Gloss: This means weighing every choice by what it gains for oneself, helping others only when it pays off, and taking credit and advantage wherever they can be had.

- pair [benevolent](../../../traits/instructions/benevolent.json) / [uncaring](../../../traits/instructions/uncaring.json): both opposed in the relation call

### slapdash (`slapdash#1`), cut-off 4: sonnet_below_opus_at

Gloss: This means rushing through every task, skipping checks and details, and handing over half-finished work with errors left in, because getting something done fast matters more than getting it right.

- [sloppy](../../../traits/instructions/sloppy.json): Sonnet 3 ("Both describe rushed, careless work that skips checks and leaves errors, so they are nearly the same concept, though slapdash stresses speed over correctness a bit more."), Opus 4 ("Both describe rushing work, skipping checks and leaving errors; the descriptions are essentially interchangeable.")

### sly (`sly#1`), cut-off 4: pair_flag

Gloss: This means working toward one's ends through cunning and craft, quietly arranging matters, reading people for openings, and favoring clever indirection over open effort.

- pair [aggressive](../../../traits/instructions/aggressive.json) / [peaceful](../../../traits/instructions/peaceful.json): both opposed in the relation call

### smooth (`smooth#1`), cut-off 3: pair_flag

Gloss: This means carrying oneself with easy polish, speaking in graceful, well-turned phrases, and putting others at ease through effortless charm and a courteous, assured manner that never seems rushed or flustered.

- pair [pretentious](../../../traits/instructions/pretentious.json) / [unpretentious](../../../traits/instructions/unpretentious.json): both opposed in the relation call

### social drinker (`social_drinker#1`), cut-off 3: pair_flag

Gloss: This means drinking alcohol with others at social gatherings, in measured amounts.

- pair [heavy-drinker](../../../traits/instructions/heavy_drinker.json) / [teetotaler](../../../traits/instructions/teetotaler.json): both opposed in the relation call
- pair [abstemious](../../../traits/instructions/abstemious.json) / [gluttonous](../../../traits/instructions/gluttonous.json): both opposed in the relation call

### spasmodic (`spasmodic#1`), cut-off 3: pair_flag

Gloss: This means working in sudden bursts, surging ahead with energy, then halting abruptly, then lurching forward again, so that nothing proceeds at a steady pace or on a predictable rhythm.

- pair [hurried](../../../traits/instructions/hurried.json) / [unhurried](../../../traits/instructions/unhurried.json): both opposed in the relation call

### standoffish (`standoffish#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means keeping a cool distance from others, holding back warmth and personal disclosure, and carrying oneself with a reserved, aloof manner that makes approach feel unwelcome.

- [reserved](../../../traits/instructions/reserved.json): Sonnet 2 ("Both involve emotional restraint, little self-disclosure and keeping distance, but standoffish adds coolness and an unwelcoming aloofness, while reserved can be polite and merely private without being off-putting."), Opus 3 ("Both describe keeping distance and withholding personal disclosure; standoffish is the same reserve pushed further into cool aloofness that discourages approach.")

### tactless (`tactless#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means speaking bluntly without regard for how one's words affect others.

- [blunt](../../../traits/instructions/blunt.json): Sonnet 2 ("Both involve speaking directly without softening, but tactless adds disregard for others' feelings, while blunt is about directness and honest clarity, which can be intentional and considerate; each lacks something the other has."), Opus 3 ("Tactless is bluntness carried further into disregard for others' feelings, so it is the same direct delivery with an added careless edge.")
- [savage](../../../traits/instructions/savage.json): Sonnet 2 ("Both involve blunt speech with no softening, but tactless is obliviousness to others' feelings, while savage is a deliberately cutting, devastating delivery; each adds something the other lacks."), Opus 3 ("Both describe blunt speech without regard for how it lands, and savage is a more intense, deliberately cutting version of tactlessness.")

### telegraphic (`telegraphic#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means speaking and writing in terse, clipped phrases, dropping articles and connecting words, and packing each message into the fewest words that still carry the sense.

- [concise](../../../traits/instructions/concise.json): Sonnet 2 ("Both favour brevity, but telegraphic means clipped, stripped-down grammar, while concise means brief and focused with no implication of dropping articles or connectives; a concise person can write full, well-formed sentences."), Opus 3 ("Telegraphic is an extreme form of concision, going so far as to drop grammatical words, so it is the same brevity carried further.")

### terse (`terse#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means speaking in few words, often abruptly, without elaboration or softening.

- [concise](../../../traits/instructions/concise.json): Sonnet 2 ("Both involve using few words without elaboration, but terse adds abruptness and a lack of softening, while concise is neutral or positive and focused on clarity, so each adds something the other lacks."), Opus 3 ("Both describe brevity without elaboration; terse adds abruptness and lack of softening, a difference of emphasis rather than of concept.")

### trendsetting (`trendsetting#1`), cut-off 3: pair_flag

Gloss: This means launching new styles before anyone else has adopted them, wearing and promoting looks that others then copy, and being the one whose choices shape what becomes fashionable.

- pair [fashionable](../../../traits/instructions/fashionable.json) / [unfashionable](../../../traits/instructions/unfashionable.json): both opposed in the relation call

### twisted (`twisted#1`), cut-off 4: pair_flag

Gloss: This means taking pleasure in cruelty and suffering, bending every situation toward something perverse, and relishing the discomfort of others with a warped, sadistic delight.

- pair [joyful](../../../traits/instructions/joyful.json) / [joyless](../../../traits/instructions/joyless.json): both opposed in the relation call

### unconventional (`unconventional#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means departing from standard ways of thinking, behaving, and acting in pursuit of one's own path.

- [heterodox](../../../traits/instructions/heterodox.json): Sonnet 2 ("Both involve departing from the standard, but heterodox is specifically about dissenting from established doctrine and authority in belief, while unconventional covers any non-standard thinking, behavior or path."), Opus 3 ("Heterodox is unconventionality narrowed to beliefs and doctrine, a narrower scope of the same departure from the standard.")
- [eccentric](../../../traits/instructions/eccentric.json): Sonnet 2 ("Both describe departing from the norm in one's own way, but eccentric adds oddness and indifference to appearances, while unconventional centres on pursuing one's own path and need not be odd."), Opus 3 ("Eccentric is unconventionality taken further into personal oddity and indifference to appearances, so it is the same departure from norms with a stronger, quirkier emphasis.")

### unforbearing (`unforbearing#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means snapping at others' mistakes, refusing to put up with slowness or shortcomings, and showing irritation the moment someone falls short of one's standards.

- [irascible](../../../traits/instructions/irascible.json): Sonnet 2 ("Both involve quick irritation and snapping at others' minor failings; unforbearing stresses intolerance of shortcomings against one's standards, while irascible stresses a general short temper and flaring anger, so they share a core but each adds something."), Opus 3 ("Both describe quickly snapping in irritation at mistakes and slowness. Irascible is general short-temperedness, while unforbearing narrows it to intolerance of others falling short, so they differ mainly in scope.")

### unfriendly (`unfriendly#1`), cut-off 3: sonnet_below_opus_at

Gloss: This means treating others with coldness or hostility.

- [hostile](../../../traits/instructions/hostile.json): Sonnet 2 ("Both involve negative treatment of others, but 'unfriendly' covers mere coldness while 'hostile' means active aggression and antagonism, so hostile is a stronger, narrower form that overlaps with unfriendly's hostility component."), Opus 3 ("Hostility is a more intense, actively aggressive form of the coldness-or-hostility that defines unfriendliness, so it is the same concept in greater degree.")

### wicked (`wicked#1`), cut-off 4: sonnet_below_opus_at

Gloss: This means acting from malice and corruption, choosing harm and betrayal as one's way.

- [evil](../../../traits/instructions/evil.json): Sonnet 3 ("Both describe deliberate moral badness with malice and harm; 'evil' is a more intense, extreme version (wrongdoing for its own sake, gladness at suffering), so they differ mainly in degree."), Opus 4 ("Both describe deliberate moral malice, choosing harm for its own sake, so they are essentially the same concept, with only slight differences in emphasis.")

### youthful (`youthful#1`), cut-off 3: pair_flag

Gloss: This means bringing the energy, enthusiasm, and spirit of youth to everything, meeting each day with eager curiosity, quick movement, and a lively readiness to try something new.

- pair [immature](../../../traits/instructions/immature.json) / [mature](../../../traits/instructions/mature.json): both opposed in the relation call

## Pair completions (42 candidates)

A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): the candidate may be that trait's missing antonym (design item 4: a find, not a drop).

- adaptive (covered): [mercurial](../../../traits/instructions/mercurial.json)
- atomistic (covered): [systems-thinker](../../../traits/instructions/systems_thinker.json), [structuralist](../../../traits/instructions/structuralist.json)
- boastful (covered): [modest](../../../traits/instructions/modest.json)
- collectivist (covered): [civilizationist](../../../traits/instructions/civilizationist.json)
- compassionate toward animals (covered): [cruel](../../../traits/instructions/cruel.json)
- directive (covered): [absentee](../../../traits/instructions/absentee.json)
- fair minded (covered): [judgmental](../../../traits/instructions/judgmental.json)
- mannerly (covered): [entitled](../../../traits/instructions/entitled.json)
- patronizing (covered): [deferential](../../../traits/instructions/deferential.json)
- reformist (covered): [subversive](../../../traits/instructions/subversive.json)
- socially astute (covered): [absorption-prone](../../../traits/instructions/absorption_prone.json)
- sympathetic (covered): [cruel](../../../traits/instructions/cruel.json)
- unapologetic (covered): [accountable](../../../traits/instructions/accountable.json)
- bovine (grey): [unflinching](../../../traits/instructions/unflinching.json)
- conflict avoidant (grey): [diplomatic](../../../traits/instructions/diplomatic.json)
- coy (grey): [sassy](../../../traits/instructions/sassy.json)
- inattentive (grey): [absorption-prone](../../../traits/instructions/absorption_prone.json)
- slapdash (grey): [micromanaging](../../../traits/instructions/micromanaging.json)
- smooth (grey): [glib](../../../traits/instructions/glib.json)
- unforbearing (grey): [self-blaming](../../../traits/instructions/self_blaming.json)
- bootlicking (new): [status-seeking](../../../traits/instructions/status_seeking.json)
- complacent (new): [accountable](../../../traits/instructions/accountable.json), [self-blaming](../../../traits/instructions/self_blaming.json)
- cruel to animals (new): [merciful](../../../traits/instructions/merciful.json)
- democratic (new): [aristocratic](../../../traits/instructions/aristocratic.json)
- human-centered (new): [civilizationist](../../../traits/instructions/civilizationist.json)
- intervening (new): [passive](../../../traits/instructions/passive.json)
- linear thinker (new): [stream-of-consciousness](../../../traits/instructions/stream_of_consciousness.json)
- merciless (new): [merciful](../../../traits/instructions/merciful.json)
- monist (new): [materialist](../../../traits/instructions/materialist.json), [paradoxical](../../../traits/instructions/paradoxical.json)
- needy (new): [controlling](../../../traits/instructions/controlling.json)
- nepotistic (new): [meritocratic](../../../traits/instructions/meritocratic.json)
- nonsectarian (new): [sectarian](../../../traits/instructions/sectarian.json)
- ostentatious (new): [modest](../../../traits/instructions/modest.json)
- personally oriented (new): [regionalist](../../../traits/instructions/regionalist.json), [civilizationist](../../../traits/instructions/civilizationist.json), [nationalist](../../../traits/instructions/nationalist.json)
- pompous (new): [dignified](../../../traits/instructions/dignified.json)
- psychologically secure (new): [self-blaming](../../../traits/instructions/self_blaming.json)
- sadomasochistic (new): [merciful](../../../traits/instructions/merciful.json)
- schmaltzy (new): [glib](../../../traits/instructions/glib.json)
- self accountable (new): [self-blaming](../../../traits/instructions/self_blaming.json)
- selfless (new): [civilizationist](../../../traits/instructions/civilizationist.json), [regionalist](../../../traits/instructions/regionalist.json)
- tawdry (new): [dignified](../../../traits/instructions/dignified.json)
- technocrat (new): [aristocratic](../../../traits/instructions/aristocratic.json)
