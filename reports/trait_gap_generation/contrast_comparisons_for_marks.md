# Contrast clauses: 30 blinded neighbour comparisons for Roger's marks (M2 pilot)

For each trait below, two lists of its five nearest existing traits, from openai embeddings in the `raw` space: one list embeds every description as written, the other with its contrast clause ("rather than X", "instead of", "but not", "without being") removed. The order of the two lists is random and the key is in [contrast_comparisons_key.json](../../data/candidates/calibration/contrast_comparisons_key.json) (do not open it before marking). Mark the list whose traits are closer in meaning to the given trait (synonyms first; an antonym is not close), or `same`. The same 30 are the first half of the Sonnet judge's sample (criterion e), so its agreement with you is known before its verdict counts.

### 1. [critical](../../data/traits/instructions/critical.json)

This means systematically questioning power structures, challenging accepted assumptions, exposing contradictions in dominant narratives, and scrutinizing who benefits from current arrangements rather than accepting things at face value.

**List A**

1. [skeptical](../../data/traits/instructions/skeptical.json): This means questioning assumptions, seeking evidence for claims, challenging conventional thinking, and not accepting information at face value.
2. [challenging](../../data/traits/instructions/challenging.json): This means pushing other people to think more deeply, questioning their assumptions, presenting alternative perspectives, or encouraging critical examination of beliefs and ideas rather than simply providing straightforward answers.
3. [deconstructionist](../../data/traits/instructions/deconstructionist.json): This means systematically breaking down and challenging underlying assumptions, revealing hidden meanings and contradictions, questioning established foundations of knowledge, and exposing how seemingly stable concepts contain internal tensions and inconsistencies.
4. [uncritical](../../data/traits/instructions/uncritical.json): This means accepting the official account and the existing arrangement as simply how things are, never asking who benefits or what the accepted story leaves out.
5. [contrarian](../../data/traits/instructions/contrarian.json): This means challenging popular opinions, questioning mainstream viewpoints, and presenting alternative perspectives that go against widely accepted beliefs or conventional wisdom.

**List B**

1. [challenging](../../data/traits/instructions/challenging.json): This means pushing other people to think more deeply, questioning their assumptions, presenting alternative perspectives, or encouraging critical examination of beliefs and ideas rather than simply providing straightforward answers.
2. [deconstructionist](../../data/traits/instructions/deconstructionist.json): This means systematically breaking down and challenging underlying assumptions, revealing hidden meanings and contradictions, questioning established foundations of knowledge, and exposing how seemingly stable concepts contain internal tensions and inconsistencies.
3. [skeptical](../../data/traits/instructions/skeptical.json): This means questioning assumptions, seeking evidence for claims, challenging conventional thinking, and not accepting information at face value.
4. [uncritical](../../data/traits/instructions/uncritical.json): This means accepting the official account and the existing arrangement as simply how things are, never asking who benefits or what the accepted story leaves out.
5. [contrarian](../../data/traits/instructions/contrarian.json): This means challenging popular opinions, questioning mainstream viewpoints, and presenting alternative perspectives that go against widely accepted beliefs or conventional wisdom.

Mark (A / B / same): 

### 2. [casual](../../data/traits/instructions/casual.json)

This means using a relaxed, conversational tone with informal language, contractions, everyday expressions, and speaking as if chatting with a friend rather than giving a formal presentation.

**List A**

1. [formal](../../data/traits/instructions/formal.json): This means using professional language, maintaining proper grammar and sentence structure, employing respectful and dignified tone, avoiding casual expressions or slang, and communicating in a manner appropriate for business or official contexts.
2. [laid-back](../../data/traits/instructions/laid_back.json): This means being easy and unhurried in any conversation, voice level and stakes low, letting a topic drop without fuss, and never making a moment feel bigger than it is.
3. [serious](../../data/traits/instructions/serious.json): This means maintaining a formal, professional tone and focusing on substantive content while avoiding humor, casual language, or lighthearted remarks in favor of gravitas and dignity.
4. [playful](../../data/traits/instructions/playful.json): This means incorporating elements of fun, humor, games, lightheartedness, creativity, whimsy, or turning the interaction into an enjoyable experience through playful language, analogies, or engaging presentation.
5. [unpretentious](../../data/traits/instructions/unpretentious.json): This means saying it in ordinary words, as one would to a neighbor, with nothing grand put on to impress and no airs.

**List B**

1. [formal](../../data/traits/instructions/formal.json): This means using professional language, maintaining proper grammar and sentence structure, employing respectful and dignified tone, avoiding casual expressions or slang, and communicating in a manner appropriate for business or official contexts.
2. [laid-back](../../data/traits/instructions/laid_back.json): This means being easy and unhurried in any conversation, voice level and stakes low, letting a topic drop without fuss, and never making a moment feel bigger than it is.
3. [serious](../../data/traits/instructions/serious.json): This means maintaining a formal, professional tone and focusing on substantive content while avoiding humor, casual language, or lighthearted remarks in favor of gravitas and dignity.
4. [unpretentious](../../data/traits/instructions/unpretentious.json): This means saying it in ordinary words, as one would to a neighbor, with nothing grand put on to impress and no airs.
5. [playful](../../data/traits/instructions/playful.json): This means incorporating elements of fun, humor, games, lightheartedness, creativity, whimsy, or turning the interaction into an enjoyable experience through playful language, analogies, or engaging presentation.

Mark (A / B / same): 

### 3. [reactive](../../data/traits/instructions/reactive.json)

This means responding to situations as they arise in the moment rather than taking time to plan ahead or consider long-term consequences.

**List A**

1. [impulsive](../../data/traits/instructions/impulsive.json): This means acting on immediate desires or urges without taking time to consider potential consequences, alternatives, or long-term implications.
2. [improvisational](../../data/traits/instructions/improvisational.json): This means showing fluid adaptation to changing or unexpected circumstances, demonstrating flexibility without rigid adherence to predetermined plans, and exhibiting spontaneous problem-solving that builds organically on the situation at hand.
3. [proactive](../../data/traits/instructions/proactive.json): This means anticipating potential needs, identifying future problems before they occur, and offering preventive solutions or additional considerations that go beyond what was directly asked.
4. [unreflective](../../data/traits/instructions/unreflective.json): This means saying what comes to mind without looking at how it got there, and never turning attention inward on one's own reasoning, motives or moods.
5. [passive](../../data/traits/instructions/passive.json): This means taking things as they come and doing nothing about them, seeing a problem and letting it lie rather than solving it, and waiting for someone else to sort it out.

**List B**

1. [improvisational](../../data/traits/instructions/improvisational.json): This means showing fluid adaptation to changing or unexpected circumstances, demonstrating flexibility without rigid adherence to predetermined plans, and exhibiting spontaneous problem-solving that builds organically on the situation at hand.
2. [flexible](../../data/traits/instructions/flexible.json): This means showing adaptability by accepting imperfect situations, working within constraints and limitations, and adjusting approaches when circumstances change rather than insisting on ideal conditions.
3. [proactive](../../data/traits/instructions/proactive.json): This means anticipating potential needs, identifying future problems before they occur, and offering preventive solutions or additional considerations that go beyond what was directly asked.
4. [impulsive](../../data/traits/instructions/impulsive.json): This means acting on immediate desires or urges without taking time to consider potential consequences, alternatives, or long-term implications.
5. [passive](../../data/traits/instructions/passive.json): This means taking things as they come and doing nothing about them, seeing a problem and letting it lie rather than solving it, and waiting for someone else to sort it out.

Mark (A / B / same): 

### 4. [pluralist](../../data/traits/instructions/pluralist.json)

This means acknowledging and treating multiple different perspectives, approaches, or viewpoints as equally valid and legitimate rather than promoting a single correct answer or dismissing alternative views.

**List A**

1. [inclusive](../../data/traits/instructions/inclusive.json): This means considering diverse perspectives, ensuring broad representation across different groups and viewpoints, and actively incorporating voices from various backgrounds rather than focusing only on dominant or mainstream perspectives.
2. [exploratory](../../data/traits/instructions/exploratory.json): This means presenting multiple options, alternatives, or perspectives and encouraging people to keep investigating and exploring different possibilities rather than settling on a single definitive answer.
3. [cosmopolitan](../../data/traits/instructions/cosmopolitan.json): This means embracing global citizenship, valuing cultural diversity, showing openness to international viewpoints, and treating different cultures and traditions as equally worthy of respect and consideration.
4. [exclusivist](../../data/traits/instructions/exclusivist.json): This means holding that one view, school, or way is right and the rest are wrong, and treating rivals as errors, never equals.
5. [relativist](../../data/traits/instructions/relativist.json): This means believing that truth and morality are entirely dependent on context, perspective, and cultural background, rejecting the existence of universal or objective standards.

**List B**

1. [inclusive](../../data/traits/instructions/inclusive.json): This means considering diverse perspectives, ensuring broad representation across different groups and viewpoints, and actively incorporating voices from various backgrounds rather than focusing only on dominant or mainstream perspectives.
2. [cosmopolitan](../../data/traits/instructions/cosmopolitan.json): This means embracing global citizenship, valuing cultural diversity, showing openness to international viewpoints, and treating different cultures and traditions as equally worthy of respect and consideration.
3. [exploratory](../../data/traits/instructions/exploratory.json): This means presenting multiple options, alternatives, or perspectives and encouraging people to keep investigating and exploring different possibilities rather than settling on a single definitive answer.
4. [exclusivist](../../data/traits/instructions/exclusivist.json): This means holding that one view, school, or way is right and the rest are wrong, and treating rivals as errors, never equals.
5. [respectful](../../data/traits/instructions/respectful.json): This means treating other people as capable equals, crediting them with understanding, taking their questions seriously, and never talking down to anyone, whatever they happen to know.

Mark (A / B / same): 

### 5. [contemporary](../../data/traits/instructions/contemporary.json)

This means emphasizing current events, modern trends, recent developments, present-day technologies, and up-to-date perspectives rather than focusing primarily on historical or timeless approaches.

**List A**

1. [futuristic](../../data/traits/instructions/futuristic.json): This trait involves emphasizing emerging trends, future possibilities, technological advancement, next-generation solutions, and forward-thinking approaches rather than focusing on current or traditional methods.
2. [historical](../../data/traits/instructions/historical.json): This means frequently referencing past events, drawing on historical context, mentioning historical patterns, or connecting current topics to historical precedents and examples.
3. [theoretical](../../data/traits/instructions/theoretical.json): This means emphasizing abstract concepts, theoretical models, conceptual frameworks, and underlying principles rather than focusing on concrete, practical, or empirical aspects.
4. [progressive](../../data/traits/instructions/progressive.json): This means advocating for change, reform, forward-thinking approaches, and transformative solutions rather than maintaining traditional or conservative positions.
5. [conceptual](../../data/traits/instructions/conceptual.json): This means working primarily with ideas, theories, and abstract frameworks rather than focusing on concrete details, specific examples, or practical implementation.

**List B**

1. [futuristic](../../data/traits/instructions/futuristic.json): This trait involves emphasizing emerging trends, future possibilities, technological advancement, next-generation solutions, and forward-thinking approaches rather than focusing on current or traditional methods.
2. [historical](../../data/traits/instructions/historical.json): This means frequently referencing past events, drawing on historical context, mentioning historical patterns, or connecting current topics to historical precedents and examples.
3. [progressive](../../data/traits/instructions/progressive.json): This means advocating for change, reform, forward-thinking approaches, and transformative solutions rather than maintaining traditional or conservative positions.
4. [theoretical](../../data/traits/instructions/theoretical.json): This means emphasizing abstract concepts, theoretical models, conceptual frameworks, and underlying principles rather than focusing on concrete, practical, or empirical aspects.
5. [innovative](../../data/traits/instructions/innovative.json): This means tending to seek new approaches, cutting-edge solutions, experimentation, and embracing emerging technologies or unconventional methods rather than relying on traditional approaches.

Mark (A / B / same): 

### 6. [progressive](../../data/traits/instructions/progressive.json)

This means advocating for change, reform, forward-thinking approaches, and transformative solutions rather than maintaining traditional or conservative positions.

**List A**

1. [radical](../../data/traits/instructions/radical.json): This means advocating for revolutionary, fundamental changes that completely transform or overturn existing systems rather than working within them or making incremental improvements.
2. [innovative](../../data/traits/instructions/innovative.json): This means tending to seek new approaches, cutting-edge solutions, experimentation, and embracing emerging technologies or unconventional methods rather than relying on traditional approaches.
3. [constructive](../../data/traits/instructions/constructive.json): This means focusing on building, improving, and strengthening ideas, relationships, and systems, offering solutions and positive development rather than tearing things down or dwelling on flaws.
4. [futuristic](../../data/traits/instructions/futuristic.json): This trait involves emphasizing emerging trends, future possibilities, technological advancement, next-generation solutions, and forward-thinking approaches rather than focusing on current or traditional methods.
5. [conservative](../../data/traits/instructions/conservative.json): This means favoring established systems, proven methods, and only gradual change, and valuing stability and continuity over reform.

**List B**

1. [radical](../../data/traits/instructions/radical.json): This means advocating for revolutionary, fundamental changes that completely transform or overturn existing systems rather than working within them or making incremental improvements.
2. [conservative](../../data/traits/instructions/conservative.json): This means favoring established systems, proven methods, and only gradual change, and valuing stability and continuity over reform.
3. [innovative](../../data/traits/instructions/innovative.json): This means tending to seek new approaches, cutting-edge solutions, experimentation, and embracing emerging technologies or unconventional methods rather than relying on traditional approaches.
4. [incrementalist](../../data/traits/instructions/incrementalist.json): This means wanting reform but pursuing it one small step at a time within existing institutions, and distrusting sweeping overhauls as gambles that throw away what works.
5. [futuristic](../../data/traits/instructions/futuristic.json): This trait involves emphasizing emerging trends, future possibilities, technological advancement, next-generation solutions, and forward-thinking approaches rather than focusing on current or traditional methods.

Mark (A / B / same): 

### 7. [radical](../../data/traits/instructions/radical.json)

This means advocating for revolutionary, fundamental changes that completely transform or overturn existing systems rather than working within them or making incremental improvements.

**List A**

1. [progressive](../../data/traits/instructions/progressive.json): This means advocating for change, reform, forward-thinking approaches, and transformative solutions rather than maintaining traditional or conservative positions.
2. [extremist](../../data/traits/instructions/extremist.json): This means taking the far edge of political and social questions, treating compromise as betrayal and moderation as cowardice, and wanting one's side to win outright.
3. [critical](../../data/traits/instructions/critical.json): This means systematically questioning power structures, challenging accepted assumptions, exposing contradictions in dominant narratives, and scrutinizing who benefits from current arrangements rather than accepting things at face value.
4. [egalitarian](../../data/traits/instructions/egalitarian.json): This means strongly advocating for equality and equal rights for all people, promoting fairness and challenging discrimination or inequality.
5. [subversive](../../data/traits/instructions/subversive.json): This means undermining or challenging established norms, authorities, or conventional wisdom through subtle, indirect methods rather than direct confrontation.

**List B**

1. [progressive](../../data/traits/instructions/progressive.json): This means advocating for change, reform, forward-thinking approaches, and transformative solutions rather than maintaining traditional or conservative positions.
2. [extremist](../../data/traits/instructions/extremist.json): This means taking the far edge of political and social questions, treating compromise as betrayal and moderation as cowardice, and wanting one's side to win outright.
3. [egalitarian](../../data/traits/instructions/egalitarian.json): This means strongly advocating for equality and equal rights for all people, promoting fairness and challenging discrimination or inequality.
4. [critical](../../data/traits/instructions/critical.json): This means systematically questioning power structures, challenging accepted assumptions, exposing contradictions in dominant narratives, and scrutinizing who benefits from current arrangements rather than accepting things at face value.
5. [subversive](../../data/traits/instructions/subversive.json): This means undermining or challenging established norms, authorities, or conventional wisdom through subtle, indirect methods rather than direct confrontation.

Mark (A / B / same): 

### 8. [moderate](../../data/traits/instructions/moderate.json)

This means consistently seeking middle ground, presenting balanced perspectives, avoiding extreme positions, and looking for compromise solutions rather than taking polarizing stances.

**List A**

1. [temperate](../../data/traits/instructions/temperate.json): This means holding one's beliefs and causes coolly, in a measured voice, never crusading for anything or getting fired up, and distrusting fervor wherever it appears.
2. [diplomatic](../../data/traits/instructions/diplomatic.json): This means carefully navigating sensitive topics, using measured and tactful language, acknowledging multiple perspectives, avoiding taking strong partisan positions, and seeking balanced approaches to controversial issues.
3. [extremist](../../data/traits/instructions/extremist.json): This means taking the far edge of political and social questions, treating compromise as betrayal and moderation as cowardice, and wanting one's side to win outright.
4. [noncommittal](../../data/traits/instructions/noncommittal.json): This means never taking a definite position or advocating for one, laying out the views on each side and declining to say which is one's own.
5. [agreeable](../../data/traits/instructions/agreeable.json): This means prioritizing maintaining harmony and positive relationships, seeking to avoid confrontation, emphasizing cooperation and understanding, and attempting to find common ground or peaceful resolutions even in difficult situations.

**List B**

1. [temperate](../../data/traits/instructions/temperate.json): This means holding one's beliefs and causes coolly, in a measured voice, never crusading for anything or getting fired up, and distrusting fervor wherever it appears.
2. [diplomatic](../../data/traits/instructions/diplomatic.json): This means carefully navigating sensitive topics, using measured and tactful language, acknowledging multiple perspectives, avoiding taking strong partisan positions, and seeking balanced approaches to controversial issues.
3. [agreeable](../../data/traits/instructions/agreeable.json): This means prioritizing maintaining harmony and positive relationships, seeking to avoid confrontation, emphasizing cooperation and understanding, and attempting to find common ground or peaceful resolutions even in difficult situations.
4. [conciliatory](../../data/traits/instructions/conciliatory.json): This means actively working to make peace, reduce tensions between opposing sides, and seeking to find common ground or shared understanding between conflicting parties or viewpoints.
5. [extremist](../../data/traits/instructions/extremist.json): This means taking the far edge of political and social questions, treating compromise as betrayal and moderation as cowardice, and wanting one's side to win outright.

Mark (A / B / same): 

### 9. [independent](../../data/traits/instructions/independent.json)

This means showing self-reliance, personal responsibility, and autonomous decision-making rather than dependence on others for guidance, approval, or validation.

**List A**

1. [self-reliant](../../data/traits/instructions/self_reliant.json): This means doing the whole job oneself, asking nobody for input or help, keeping work and responsibility in one's own hands, and seeing a team as dead weight.
2. [dependent](../../data/traits/instructions/dependent.json): This means leaning on others for every decision, needing someone's guidance and approval before acting, and feeling lost whenever left to manage alone.
3. [individualistic](../../data/traits/instructions/individualistic.json): This trait involves emphasizing unique personal expression, individual differences, self-reliance, and personal autonomy over conformity to group norms or collective approaches.
4. [dependable](../../data/traits/instructions/dependable.json): This means consistently following through on commitments, being someone others can count on, and reliably doing what you say you will do without needing to be reminded or checked on.
5. [existentialist](../../data/traits/instructions/existentialist.json): This means emphasizing individual freedom, personal responsibility, and the importance of creating one's own meaning and values rather than relying on external authorities or predetermined purposes.

**List B**

1. [self-reliant](../../data/traits/instructions/self_reliant.json): This means doing the whole job oneself, asking nobody for input or help, keeping work and responsibility in one's own hands, and seeing a team as dead weight.
2. [dependent](../../data/traits/instructions/dependent.json): This means leaning on others for every decision, needing someone's guidance and approval before acting, and feeling lost whenever left to manage alone.
3. [individualistic](../../data/traits/instructions/individualistic.json): This trait involves emphasizing unique personal expression, individual differences, self-reliance, and personal autonomy over conformity to group norms or collective approaches.
4. [existentialist](../../data/traits/instructions/existentialist.json): This means emphasizing individual freedom, personal responsibility, and the importance of creating one's own meaning and values rather than relying on external authorities or predetermined purposes.
5. [dependable](../../data/traits/instructions/dependable.json): This means consistently following through on commitments, being someone others can count on, and reliably doing what you say you will do without needing to be reminded or checked on.

Mark (A / B / same): 

### 10. [creative](../../data/traits/instructions/creative.json)

This means offering imaginative solutions, presenting novel perspectives, and demonstrating original approaches to problems rather than relying on conventional or standard methods.

**List A**

1. [innovative](../../data/traits/instructions/innovative.json): This means tending to seek new approaches, cutting-edge solutions, experimentation, and embracing emerging technologies or unconventional methods rather than relying on traditional approaches.
2. [divergent](../../data/traits/instructions/divergent.json): This means generating multiple possibilities, alternatives, and creative variations without immediately judging or narrowing them down to a single solution.
3. [improvisational](../../data/traits/instructions/improvisational.json): This means showing fluid adaptation to changing or unexpected circumstances, demonstrating flexibility without rigid adherence to predetermined plans, and exhibiting spontaneous problem-solving that builds organically on the situation at hand.
4. [constructive](../../data/traits/instructions/constructive.json): This means focusing on building, improving, and strengthening ideas, relationships, and systems, offering solutions and positive development rather than tearing things down or dwelling on flaws.
5. [problem-solving](../../data/traits/instructions/problem_solving.json): This involves actively identifying issues, analyzing root causes, and developing practical, actionable solutions to address challenges.

**List B**

1. [innovative](../../data/traits/instructions/innovative.json): This means tending to seek new approaches, cutting-edge solutions, experimentation, and embracing emerging technologies or unconventional methods rather than relying on traditional approaches.
2. [constructive](../../data/traits/instructions/constructive.json): This means focusing on building, improving, and strengthening ideas, relationships, and systems, offering solutions and positive development rather than tearing things down or dwelling on flaws.
3. [problem-solving](../../data/traits/instructions/problem_solving.json): This involves actively identifying issues, analyzing root causes, and developing practical, actionable solutions to address challenges.
4. [divergent](../../data/traits/instructions/divergent.json): This means generating multiple possibilities, alternatives, and creative variations without immediately judging or narrowing them down to a single solution.
5. [improvisational](../../data/traits/instructions/improvisational.json): This means showing fluid adaptation to changing or unexpected circumstances, demonstrating flexibility without rigid adherence to predetermined plans, and exhibiting spontaneous problem-solving that builds organically on the situation at hand.

Mark (A / B / same): 

### 11. [visceral](../../data/traits/instructions/visceral.json)

This means communicating from gut reactions and raw emotional responses rather than carefully measured or intellectualized language.

**List A**

1. [expressive](../../data/traits/instructions/expressive.json): This means letting feelings show as they come, putting one's own joys, worries, and soft spots into words, and keeping no professional distance from anyone.
2. [cerebral](../../data/traits/instructions/cerebral.json): This means living in one's head, meeting a shock or a delight with a thought rather than a feeling, and giving the gut no say.
3. [reactive](../../data/traits/instructions/reactive.json): This means responding to situations as they arise in the moment rather than taking time to plan ahead or consider long-term consequences.
4. [emotional](../../data/traits/instructions/emotional.json): This means acknowledging and discussing feelings, moods, emotional experiences, or demonstrating emotional awareness and expression.
5. [unreflective](../../data/traits/instructions/unreflective.json): This means saying what comes to mind without looking at how it got there, and never turning attention inward on one's own reasoning, motives or moods.

**List B**

1. [cerebral](../../data/traits/instructions/cerebral.json): This means living in one's head, meeting a shock or a delight with a thought rather than a feeling, and giving the gut no say.
2. [expressive](../../data/traits/instructions/expressive.json): This means letting feelings show as they come, putting one's own joys, worries, and soft spots into words, and keeping no professional distance from anyone.
3. [unreflective](../../data/traits/instructions/unreflective.json): This means saying what comes to mind without looking at how it got there, and never turning attention inward on one's own reasoning, motives or moods.
4. [dramatic](../../data/traits/instructions/dramatic.json): This means using emotionally charged language, vivid and theatrical descriptions, and presenting information with heightened intensity and dramatic flair.
5. [emotional](../../data/traits/instructions/emotional.json): This means acknowledging and discussing feelings, moods, emotional experiences, or demonstrating emotional awareness and expression.

Mark (A / B / same): 

### 12. [avoidant](../../data/traits/instructions/avoidant.json)

This means consistently withdrawing from challenging situations, difficult topics, and complex social interactions rather than engaging with them directly.

**List A**

1. [news-avoidant](../../data/traits/instructions/news_avoidant.json): This means skipping the headlines on purpose, turning off the news, and going weeks without knowing what has happened.
2. [confrontational](../../data/traits/instructions/confrontational.json): This means seeking out conflict rather than merely not avoiding it: challenging people head-on, escalating disagreements, relishing an argument, and being most at ease when the gloves are off.
3. [timid](../../data/traits/instructions/timid.json): This means being easily frightened and slow to venture, hanging back from strangers, new places and anything untried, and speaking up only in a small voice, if at all.
4. [unadventurous](../../data/traits/instructions/unadventurous.json): This means keeping to the familiar and the safe: saying no to the unfamiliar place, food or plan, taking the known route every time, and growing uneasy outside routine.
5. [lazy](../../data/traits/instructions/lazy.json): This means showing habitual laziness, avoidance of effort, and reluctance to engage meaningfully with tasks, preferring the easiest path and doing the bare minimum rather than applying oneself.

**List B**

1. [news-avoidant](../../data/traits/instructions/news_avoidant.json): This means skipping the headlines on purpose, turning off the news, and going weeks without knowing what has happened.
2. [timid](../../data/traits/instructions/timid.json): This means being easily frightened and slow to venture, hanging back from strangers, new places and anything untried, and speaking up only in a small voice, if at all.
3. [lazy](../../data/traits/instructions/lazy.json): This means showing habitual laziness, avoidance of effort, and reluctance to engage meaningfully with tasks, preferring the easiest path and doing the bare minimum rather than applying oneself.
4. [unadventurous](../../data/traits/instructions/unadventurous.json): This means keeping to the familiar and the safe: saying no to the unfamiliar place, food or plan, taking the known route every time, and growing uneasy outside routine.
5. [introverted](../../data/traits/instructions/introverted.json): This means being drained by company and restored by solitude: keeping to oneself, speaking little in groups, preferring one or two close friends to a crowd, and needing time alone after social occasions.

Mark (A / B / same): 

### 13. [practical](../../data/traits/instructions/practical.json)

This means focusing on real-world applications, actionable advice, and concrete implementation rather than abstract theory or conceptual discussions.

**List A**

1. [pragmatic](../../data/traits/instructions/pragmatic.json): This means focusing on realistic constraints and practical, achievable solutions, and prioritizing what works over what's ideal.
2. [grounded](../../data/traits/instructions/grounded.json): This means keeping communication firmly rooted in practical reality, concrete experience, observable facts, and real-world applications rather than abstract theories or speculation.
3. [experiential](../../data/traits/instructions/experiential.json): This means drawing from practical examples, real-world case studies, concrete scenarios, and experiential evidence to support one's points rather than relying solely on abstract theory or the literature.
4. [concrete](../../data/traits/instructions/concrete.json): This means dealing in particulars, this case, this number, this person on this day, and giving an example where someone else would state a principle.
5. [efficient](../../data/traits/instructions/efficient.json): This means prioritizing getting to solutions quickly with minimum wasted effort, streamlining explanations, and focusing on actionable outcomes rather than comprehensive coverage.

**List B**

1. [pragmatic](../../data/traits/instructions/pragmatic.json): This means focusing on realistic constraints and practical, achievable solutions, and prioritizing what works over what's ideal.
2. [conceptual](../../data/traits/instructions/conceptual.json): This means working primarily with ideas, theories, and abstract frameworks rather than focusing on concrete details, specific examples, or practical implementation.
3. [theoretical](../../data/traits/instructions/theoretical.json): This means emphasizing abstract concepts, theoretical models, conceptual frameworks, and underlying principles rather than focusing on concrete, practical, or empirical aspects.
4. [abstract](../../data/traits/instructions/abstract.json): This means focusing on concepts, patterns, theoretical frameworks, and high-level principles rather than concrete specifics or practical details.
5. [grounded](../../data/traits/instructions/grounded.json): This means keeping communication firmly rooted in practical reality, concrete experience, observable facts, and real-world applications rather than abstract theories or speculation.

Mark (A / B / same): 

### 14. [vindictive](../../data/traits/instructions/vindictive.json)

This means showing a tendency to hold grudges persistently and actively seek retribution or revenge for perceived wrongs, rather than letting go or seeking constructive resolution.

**List A**

1. [unforgiving](../../data/traits/instructions/unforgiving.json): This means holding firmly to grievances, refusing to overlook transgressions, insisting on accountability and consequences, and prioritizing justice or retribution over reconciliation and second chances.
2. [bitter](../../data/traits/instructions/bitter.json): This means showing deep resentment, harsh cynical views, and perspectives colored by past disappointments and disillusionment.
3. [malevolent](../../data/traits/instructions/malevolent.json): This means showing active ill will toward others, wishing for and working toward negative outcomes for people, driven by fundamental hostility toward their wellbeing.
4. [forgiving](../../data/traits/instructions/forgiving.json): This means showing a willingness to pardon mistakes, let go of resentments, offer second chances, and prioritize healing relationships over holding grudges or seeking retribution.
5. [spiteful](../../data/traits/instructions/spiteful.json): This means paying a price oneself just to make someone else lose, sinking a deal one would profit from so that a rival profits nothing either.

**List B**

1. [unforgiving](../../data/traits/instructions/unforgiving.json): This means holding firmly to grievances, refusing to overlook transgressions, insisting on accountability and consequences, and prioritizing justice or retribution over reconciliation and second chances.
2. [malevolent](../../data/traits/instructions/malevolent.json): This means showing active ill will toward others, wishing for and working toward negative outcomes for people, driven by fundamental hostility toward their wellbeing.
3. [bitter](../../data/traits/instructions/bitter.json): This means showing deep resentment, harsh cynical views, and perspectives colored by past disappointments and disillusionment.
4. [malicious](../../data/traits/instructions/malicious.json): This means deliberately seeking to cause harm, deceive, or manipulate others, taking satisfaction in others' misfortune or suffering.
5. [spiteful](../../data/traits/instructions/spiteful.json): This means paying a price oneself just to make someone else lose, sinking a deal one would profit from so that a rival profits nothing either.

Mark (A / B / same): 

### 15. [rebellious](../../data/traits/instructions/rebellious.json)

This means challenging authority figures, defying orders, resisting rules from superiors, and breaking the chain of command rather than deferring to or complying with hierarchical authority.

**List A**

1. [obedient](../../data/traits/instructions/obedient.json): This means deferring to authority figures, following orders, complying with rules from superiors, and respecting the chain of command rather than challenging or defying hierarchical authority.
2. [subversive](../../data/traits/instructions/subversive.json): This means undermining or challenging established norms, authorities, or conventional wisdom through subtle, indirect methods rather than direct confrontation.
3. [irreverent](../../data/traits/instructions/irreverent.json): This means showing a lack of the respect that others expect toward what is treated as sacred, official, or solemn: joking about religion, mocking authority, and treating ceremony lightly, in a spirit that is cheeky rather than destructive.
4. [submissive](../../data/traits/instructions/submissive.json): This means readily yielding to others' wishes, avoiding asserting one's own views or needs, and tending to defer to what others want rather than expressing independent thoughts or preferences.
5. [deferential](../../data/traits/instructions/deferential.json): This means showing respect by yielding to others' authority, expertise, or superior position, and acknowledging when others have greater knowledge or standing.

**List B**

1. [obedient](../../data/traits/instructions/obedient.json): This means deferring to authority figures, following orders, complying with rules from superiors, and respecting the chain of command rather than challenging or defying hierarchical authority.
2. [subversive](../../data/traits/instructions/subversive.json): This means undermining or challenging established norms, authorities, or conventional wisdom through subtle, indirect methods rather than direct confrontation.
3. [irreverent](../../data/traits/instructions/irreverent.json): This means showing a lack of the respect that others expect toward what is treated as sacred, official, or solemn: joking about religion, mocking authority, and treating ceremony lightly, in a spirit that is cheeky rather than destructive.
4. [aggressive](../../data/traits/instructions/aggressive.json): This means pushing for confrontation, forceful action and combative approaches to get what one wants, and rejecting compromise or peaceful solutions.
5. [disagreeable](../../data/traits/instructions/disagreeable.json): This means being hard to get along with, contradicting people to their faces, letting every difference stand, and caring nothing for keeping the peace or being liked.

Mark (A / B / same): 

### 16. [didactic](../../data/traits/instructions/didactic.json)

This means telling rather than asking, delivering the answer and the full explanation as a lesson, and never leaving anyone to work anything out when a lecture will do.

**List A**

1. [expository](../../data/traits/instructions/expository.json): This means stating the point outright, defining terms, laying out facts, steps, and reasons in order, and never dressing information up as a story with characters, scenes, or plot.
2. [educational](../../data/traits/instructions/educational.json): This means focusing on teaching and knowledge transfer: providing instructive explanations, breaking down concepts, offering learning opportunities, and helping people understand topics more deeply.
3. [verbose](../../data/traits/instructions/verbose.json): This means providing lengthy, detailed explanations with extensive elaboration, context, background information, and comprehensive coverage that goes well beyond what is minimally required to answer the question.
4. [dry](../../data/traits/instructions/dry.json): This means giving the facts with nothing to make them enjoyable, no joke, no color, no lively example, and no notion that they should be.
5. [dogmatic](../../data/traits/instructions/dogmatic.json): This means showing rigid adherence to beliefs without considering evidence or alternative viewpoints, dismissing contradictory information, and presenting opinions as absolute truths that cannot be questioned.

**List B**

1. [expository](../../data/traits/instructions/expository.json): This means stating the point outright, defining terms, laying out facts, steps, and reasons in order, and never dressing information up as a story with characters, scenes, or plot.
2. [educational](../../data/traits/instructions/educational.json): This means focusing on teaching and knowledge transfer: providing instructive explanations, breaking down concepts, offering learning opportunities, and helping people understand topics more deeply.
3. [prescriptive](../../data/traits/instructions/prescriptive.json): This means giving specific rules, guidelines, and direct instructions about what should be done, using authoritative and commanding language to establish mandatory or required actions.
4. [dogmatic](../../data/traits/instructions/dogmatic.json): This means showing rigid adherence to beliefs without considering evidence or alternative viewpoints, dismissing contradictory information, and presenting opinions as absolute truths that cannot be questioned.
5. [dry](../../data/traits/instructions/dry.json): This means giving the facts with nothing to make them enjoyable, no joke, no color, no lively example, and no notion that they should be.

Mark (A / B / same): 

### 17. [superficial](../../data/traits/instructions/superficial.json)

This means providing only surface-level treatment of topics, skimming over complexity and nuance rather than examining underlying mechanisms, edge cases, or multiple dimensions.

**List A**

1. [thorough](../../data/traits/instructions/thorough.json): This means providing deep, comprehensive analysis that examines multiple dimensions, edge cases, and underlying mechanisms rather than stopping at surface-level observations.
2. [abstract](../../data/traits/instructions/abstract.json): This means focusing on concepts, patterns, theoretical frameworks, and high-level principles rather than concrete specifics or practical details.
3. [flippant](../../data/traits/instructions/flippant.json): This means treating serious matters with inappropriate lightness, casual disregard, or dismissive attitude when gravity and respect would be more appropriate.
4. [incurious](../../data/traits/instructions/incurious.json): This means showing little interest in learning or exploring new topics, not asking questions, and being content with surface-level understanding rather than seeking deeper knowledge.
5. [big-picture](../../data/traits/instructions/big_picture.json): This means emphasizing overarching themes, general principles, broad perspectives, systemic thinking, and macro-level concepts rather than getting caught up in specific details or narrow focus.

**List B**

1. [flippant](../../data/traits/instructions/flippant.json): This means treating serious matters with inappropriate lightness, casual disregard, or dismissive attitude when gravity and respect would be more appropriate.
2. [incurious](../../data/traits/instructions/incurious.json): This means showing little interest in learning or exploring new topics, not asking questions, and being content with surface-level understanding rather than seeking deeper knowledge.
3. [sloppy](../../data/traits/instructions/sloppy.json): This means doing the work fast and rough, skipping the checking, leaving loose ends, mislabeled figures and small mistakes, and calling it done.
4. [abstract](../../data/traits/instructions/abstract.json): This means focusing on concepts, patterns, theoretical frameworks, and high-level principles rather than concrete specifics or practical details.
5. [thorough](../../data/traits/instructions/thorough.json): This means providing deep, comprehensive analysis that examines multiple dimensions, edge cases, and underlying mechanisms rather than stopping at surface-level observations.

Mark (A / B / same): 

### 18. [structuralist](../../data/traits/instructions/structuralist.json)

This means focusing on identifying and analyzing underlying patterns, systematic relationships, organizing principles, and structural frameworks that govern systems or phenomena, rather than focusing on surface details or individual cases.

**List A**

1. [systems-thinker](../../data/traits/instructions/systems_thinker.json): This means analyzing how different parts of a system connect and influence each other, recognizing feedback loops and cycles, considering emergent properties that arise from system interactions, and thinking holistically about multiple levels and broader implications rather than isolated components.
2. [analytical](../../data/traits/instructions/analytical.json): This means breaking down complex topics into logical components and examining each part systematically, using methodical reasoning and structured examination.
3. [abstract](../../data/traits/instructions/abstract.json): This means focusing on concepts, patterns, theoretical frameworks, and high-level principles rather than concrete specifics or practical details.
4. [deconstructionist](../../data/traits/instructions/deconstructionist.json): This means systematically breaking down and challenging underlying assumptions, revealing hidden meanings and contradictions, questioning established foundations of knowledge, and exposing how seemingly stable concepts contain internal tensions and inconsistencies.
5. [reductionist](../../data/traits/instructions/reductionist.json): This means breaking down complex phenomena into their simpler, more fundamental component parts and explaining complex systems in terms of their basic elements and underlying mechanisms.

**List B**

1. [systems-thinker](../../data/traits/instructions/systems_thinker.json): This means analyzing how different parts of a system connect and influence each other, recognizing feedback loops and cycles, considering emergent properties that arise from system interactions, and thinking holistically about multiple levels and broader implications rather than isolated components.
2. [abstract](../../data/traits/instructions/abstract.json): This means focusing on concepts, patterns, theoretical frameworks, and high-level principles rather than concrete specifics or practical details.
3. [reductionist](../../data/traits/instructions/reductionist.json): This means breaking down complex phenomena into their simpler, more fundamental component parts and explaining complex systems in terms of their basic elements and underlying mechanisms.
4. [deconstructionist](../../data/traits/instructions/deconstructionist.json): This means systematically breaking down and challenging underlying assumptions, revealing hidden meanings and contradictions, questioning established foundations of knowledge, and exposing how seemingly stable concepts contain internal tensions and inconsistencies.
5. [analytical](../../data/traits/instructions/analytical.json): This means breaking down complex topics into logical components and examining each part systematically, using methodical reasoning and structured examination.

Mark (A / B / same): 

### 19. [systems-thinker](../../data/traits/instructions/systems_thinker.json)

This means analyzing how different parts of a system connect and influence each other, recognizing feedback loops and cycles, considering emergent properties that arise from system interactions, and thinking holistically about multiple levels and broader implications rather than isolated components.

**List A**

1. [holistic](../../data/traits/instructions/holistic.json): This means considering complete systems and interconnected relationships rather than focusing on isolated components or linear cause-and-effect thinking.
2. [structuralist](../../data/traits/instructions/structuralist.json): This means focusing on identifying and analyzing underlying patterns, systematic relationships, organizing principles, and structural frameworks that govern systems or phenomena, rather than focusing on surface details or individual cases.
3. [analytical](../../data/traits/instructions/analytical.json): This means breaking down complex topics into logical components and examining each part systematically, using methodical reasoning and structured examination.
4. [big-picture](../../data/traits/instructions/big_picture.json): This means emphasizing overarching themes, general principles, broad perspectives, systemic thinking, and macro-level concepts rather than getting caught up in specific details or narrow focus.
5. [reductionist](../../data/traits/instructions/reductionist.json): This means breaking down complex phenomena into their simpler, more fundamental component parts and explaining complex systems in terms of their basic elements and underlying mechanisms.

**List B**

1. [holistic](../../data/traits/instructions/holistic.json): This means considering complete systems and interconnected relationships rather than focusing on isolated components or linear cause-and-effect thinking.
2. [structuralist](../../data/traits/instructions/structuralist.json): This means focusing on identifying and analyzing underlying patterns, systematic relationships, organizing principles, and structural frameworks that govern systems or phenomena, rather than focusing on surface details or individual cases.
3. [analytical](../../data/traits/instructions/analytical.json): This means breaking down complex topics into logical components and examining each part systematically, using methodical reasoning and structured examination.
4. [reductionist](../../data/traits/instructions/reductionist.json): This means breaking down complex phenomena into their simpler, more fundamental component parts and explaining complex systems in terms of their basic elements and underlying mechanisms.
5. [big-picture](../../data/traits/instructions/big_picture.json): This means emphasizing overarching themes, general principles, broad perspectives, systemic thinking, and macro-level concepts rather than getting caught up in specific details or narrow focus.

Mark (A / B / same): 

### 20. [theoretical](../../data/traits/instructions/theoretical.json)

This means emphasizing abstract concepts, theoretical models, conceptual frameworks, and underlying principles rather than focusing on concrete, practical, or empirical aspects.

**List A**

1. [conceptual](../../data/traits/instructions/conceptual.json): This means working primarily with ideas, theories, and abstract frameworks rather than focusing on concrete details, specific examples, or practical implementation.
2. [abstract](../../data/traits/instructions/abstract.json): This means focusing on concepts, patterns, theoretical frameworks, and high-level principles rather than concrete specifics or practical details.
3. [practical](../../data/traits/instructions/practical.json): This means focusing on real-world applications, actionable advice, and concrete implementation rather than abstract theory or conceptual discussions.
4. [idealistic](../../data/traits/instructions/idealistic.json): This means emphasizing perfect scenarios, moral principles over practical constraints, aspirational goals, and visionary thinking that assumes the best possible outcomes.
5. [experiential](../../data/traits/instructions/experiential.json): This means drawing from practical examples, real-world case studies, concrete scenarios, and experiential evidence to support one's points rather than relying solely on abstract theory or the literature.

**List B**

1. [conceptual](../../data/traits/instructions/conceptual.json): This means working primarily with ideas, theories, and abstract frameworks rather than focusing on concrete details, specific examples, or practical implementation.
2. [abstract](../../data/traits/instructions/abstract.json): This means focusing on concepts, patterns, theoretical frameworks, and high-level principles rather than concrete specifics or practical details.
3. [idealistic](../../data/traits/instructions/idealistic.json): This means emphasizing perfect scenarios, moral principles over practical constraints, aspirational goals, and visionary thinking that assumes the best possible outcomes.
4. [big-picture](../../data/traits/instructions/big_picture.json): This means emphasizing overarching themes, general principles, broad perspectives, systemic thinking, and macro-level concepts rather than getting caught up in specific details or narrow focus.
5. [qualitative](../../data/traits/instructions/qualitative.json): This means emphasizing descriptive, subjective, and interpretive aspects rather than numerical data or statistical measures, focusing on themes, meanings, personal experiences, contextual understanding, and rich narrative descriptions.

Mark (A / B / same): 

### 21. [inclusive](../../data/traits/instructions/inclusive.json)

This means considering diverse perspectives, ensuring broad representation across different groups and viewpoints, and actively incorporating voices from various backgrounds rather than focusing only on dominant or mainstream perspectives.

**List A**

1. [pluralist](../../data/traits/instructions/pluralist.json): This means acknowledging and treating multiple different perspectives, approaches, or viewpoints as equally valid and legitimate rather than promoting a single correct answer or dismissing alternative views.
2. [exploratory](../../data/traits/instructions/exploratory.json): This means presenting multiple options, alternatives, or perspectives and encouraging people to keep investigating and exploring different possibilities rather than settling on a single definitive answer.
3. [exclusive](../../data/traits/instructions/exclusive.json): This means giving the floor only to the mainstream and the usual voices, leaving everyone else out of the picture, and seeing no loss in it.
4. [cosmopolitan](../../data/traits/instructions/cosmopolitan.json): This means embracing global citizenship, valuing cultural diversity, showing openness to international viewpoints, and treating different cultures and traditions as equally worthy of respect and consideration.
5. [eclectic](../../data/traits/instructions/eclectic.json): This means drawing from diverse sources, fields, traditions, or perspectives and combining them creatively rather than relying on a single approach or viewpoint.

**List B**

1. [pluralist](../../data/traits/instructions/pluralist.json): This means acknowledging and treating multiple different perspectives, approaches, or viewpoints as equally valid and legitimate rather than promoting a single correct answer or dismissing alternative views.
2. [exclusive](../../data/traits/instructions/exclusive.json): This means giving the floor only to the mainstream and the usual voices, leaving everyone else out of the picture, and seeing no loss in it.
3. [cosmopolitan](../../data/traits/instructions/cosmopolitan.json): This means embracing global citizenship, valuing cultural diversity, showing openness to international viewpoints, and treating different cultures and traditions as equally worthy of respect and consideration.
4. [humanistic](../../data/traits/instructions/humanistic.json): This means prioritizing human values, showing cultural understanding and sensitivity, considering social implications and community well-being, respecting human dignity, and demonstrating awareness of how decisions affect different groups of people.
5. [interdisciplinary](../../data/traits/instructions/interdisciplinary.json): This means connecting concepts, methods, theories, or insights across different fields and domains of knowledge, rather than staying within a single discipline.

Mark (A / B / same): 

### 22. [paradoxical](../../data/traits/instructions/paradoxical.json)

This means being comfortable with holding contradictory ideas at the same time and finding truth in opposing concepts, rather than trying to resolve contradictions into a single coherent viewpoint.

**List A**

1. [coherent](../../data/traits/instructions/coherent.json): This means being unable to let a contradiction stand, working two conflicting claims down until only one remains, and testing every position by whether it fits everything else one believes.
2. [contrarian](../../data/traits/instructions/contrarian.json): This means challenging popular opinions, questioning mainstream viewpoints, and presenting alternative perspectives that go against widely accepted beliefs or conventional wisdom.
3. [incoherent](../../data/traits/instructions/incoherent.json): This means holding claims that do not fit together, contradicting oneself from one paragraph to the next without noticing, and never testing a position against the rest of what one believes.
4. [open-ended](../../data/traits/instructions/open_ended.json): This means being comfortable with ambiguity, uncertainty, and keeping multiple options available rather than providing definitive answers or firm conclusions.
5. [ironic](../../data/traits/instructions/ironic.json): This means using irony to express meaning through opposites, contradictions, or saying one thing while meaning another to highlight absurdities or inconsistencies.

**List B**

1. [coherent](../../data/traits/instructions/coherent.json): This means being unable to let a contradiction stand, working two conflicting claims down until only one remains, and testing every position by whether it fits everything else one believes.
2. [open-ended](../../data/traits/instructions/open_ended.json): This means being comfortable with ambiguity, uncertainty, and keeping multiple options available rather than providing definitive answers or firm conclusions.
3. [contrarian](../../data/traits/instructions/contrarian.json): This means challenging popular opinions, questioning mainstream viewpoints, and presenting alternative perspectives that go against widely accepted beliefs or conventional wisdom.
4. [ironic](../../data/traits/instructions/ironic.json): This means using irony to express meaning through opposites, contradictions, or saying one thing while meaning another to highlight absurdities or inconsistencies.
5. [incoherent](../../data/traits/instructions/incoherent.json): This means holding claims that do not fit together, contradicting oneself from one paragraph to the next without noticing, and never testing a position against the rest of what one believes.

Mark (A / B / same): 

### 23. [cooperative](../../data/traits/instructions/cooperative.json)

This means emphasizing collaboration, mutual benefit, and shared success rather than individual achievement, framing situations as opportunities for teamwork and collective problem-solving rather than contests to be won.

**List A**

1. [collaborative](../../data/traits/instructions/collaborative.json): This trait involves emphasizing teamwork, shared problem-solving, collective effort, seeking input from others, and framing solutions in terms of group participation and shared responsibility.
2. [collectivistic](../../data/traits/instructions/collectivistic.json): This means emphasizing group needs, community well-being, and collective interests over individual desires, personal gain, or self-interested behavior.
3. [agreeable](../../data/traits/instructions/agreeable.json): This means prioritizing maintaining harmony and positive relationships, seeking to avoid confrontation, emphasizing cooperation and understanding, and attempting to find common ground or peaceful resolutions even in difficult situations.
4. [optimistic](../../data/traits/instructions/optimistic.json): This means emphasizing positive aspects, favorable possibilities, and hopeful outcomes while highlighting potential benefits and solutions rather than dwelling on problems or negative scenarios.
5. [constructive](../../data/traits/instructions/constructive.json): This means focusing on building, improving, and strengthening ideas, relationships, and systems, offering solutions and positive development rather than tearing things down or dwelling on flaws.

**List B**

1. [collaborative](../../data/traits/instructions/collaborative.json): This trait involves emphasizing teamwork, shared problem-solving, collective effort, seeking input from others, and framing solutions in terms of group participation and shared responsibility.
2. [collectivistic](../../data/traits/instructions/collectivistic.json): This means emphasizing group needs, community well-being, and collective interests over individual desires, personal gain, or self-interested behavior.
3. [competitive](../../data/traits/instructions/competitive.json): This trait involves emphasizing winning, achievement, superiority, and outperforming others, often framing situations as contests or competitions to be won.
4. [agreeable](../../data/traits/instructions/agreeable.json): This means prioritizing maintaining harmony and positive relationships, seeking to avoid confrontation, emphasizing cooperation and understanding, and attempting to find common ground or peaceful resolutions even in difficult situations.
5. [benevolent](../../data/traits/instructions/benevolent.json): This means consistently seeking to promote wellbeing and positive outcomes for all people involved, emphasizing kindness, compassion, and ethical considerations.

Mark (A / B / same): 

### 24. [stoic](../../data/traits/instructions/stoic.json)

This means demonstrating calm composure, emotional restraint, and rational detachment regardless of the circumstances being discussed. One maintains steady emotional equilibrium and shows philosophical acceptance rather than emotional reactivity.

**List A**

1. [serene](../../data/traits/instructions/serene.json): This means maintaining peaceful calm and tranquil composure, showing inner stillness and unshakeable equanimity regardless of the situation being discussed.
2. [composed](../../data/traits/instructions/composed.json): This means always staying composed: a level voice, no nervous energy, taking things as they come and meeting trouble when it arrives rather than rehearsing it beforehand.
3. [calm](../../data/traits/instructions/calm.json): This means having a calm temperament: rarely worked up about anything, steady and unhurried when others are heated, and bringing the temperature of any dispute down rather than up.
4. [unflappable](../../data/traits/instructions/unflappable.json): This means staying composed whatever lands, taking the surprise, the setback and the provocation without losing the thread or the tone, and never visibly flustered.
5. [dispassionate](../../data/traits/instructions/dispassionate.json): This means maintaining emotional distance, showing objectivity and neutrality, and avoiding emotional language or personal investment regardless of the topic being discussed.

**List B**

1. [serene](../../data/traits/instructions/serene.json): This means maintaining peaceful calm and tranquil composure, showing inner stillness and unshakeable equanimity regardless of the situation being discussed.
2. [calm](../../data/traits/instructions/calm.json): This means having a calm temperament: rarely worked up about anything, steady and unhurried when others are heated, and bringing the temperature of any dispute down rather than up.
3. [composed](../../data/traits/instructions/composed.json): This means always staying composed: a level voice, no nervous energy, taking things as they come and meeting trouble when it arrives rather than rehearsing it beforehand.
4. [unflappable](../../data/traits/instructions/unflappable.json): This means staying composed whatever lands, taking the surprise, the setback and the provocation without losing the thread or the tone, and never visibly flustered.
5. [dispassionate](../../data/traits/instructions/dispassionate.json): This means maintaining emotional distance, showing objectivity and neutrality, and avoiding emotional language or personal investment regardless of the topic being discussed.

Mark (A / B / same): 

### 25. [experiential](../../data/traits/instructions/experiential.json)

This means drawing from practical examples, real-world case studies, concrete scenarios, and experiential evidence to support one's points rather than relying solely on abstract theory or the literature.

**List A**

1. [theoretical](../../data/traits/instructions/theoretical.json): This means emphasizing abstract concepts, theoretical models, conceptual frameworks, and underlying principles rather than focusing on concrete, practical, or empirical aspects.
2. [practical](../../data/traits/instructions/practical.json): This means focusing on real-world applications, actionable advice, and concrete implementation rather than abstract theory or conceptual discussions.
3. [data-driven](../../data/traits/instructions/data_driven.json): This means relying heavily on statistics, research findings, quantitative evidence, empirical studies, and measurable data to support claims and recommendations rather than relying on intuition, anecdotal evidence, or subjective opinions.
4. [conceptual](../../data/traits/instructions/conceptual.json): This means working primarily with ideas, theories, and abstract frameworks rather than focusing on concrete details, specific examples, or practical implementation.
5. [empirical](../../data/traits/instructions/empirical.json): This means keeping to what has been observed, refusing to guess at what has not, and meeting every 'what if' with a flat 'there is no evidence for that.'

**List B**

1. [practical](../../data/traits/instructions/practical.json): This means focusing on real-world applications, actionable advice, and concrete implementation rather than abstract theory or conceptual discussions.
2. [data-driven](../../data/traits/instructions/data_driven.json): This means relying heavily on statistics, research findings, quantitative evidence, empirical studies, and measurable data to support claims and recommendations rather than relying on intuition, anecdotal evidence, or subjective opinions.
3. [empirical](../../data/traits/instructions/empirical.json): This means keeping to what has been observed, refusing to guess at what has not, and meeting every 'what if' with a flat 'there is no evidence for that.'
4. [historical](../../data/traits/instructions/historical.json): This means frequently referencing past events, drawing on historical context, mentioning historical patterns, or connecting current topics to historical precedents and examples.
5. [concrete](../../data/traits/instructions/concrete.json): This means dealing in particulars, this case, this number, this person on this day, and giving an example where someone else would state a principle.

Mark (A / B / same): 

### 26. [futuristic](../../data/traits/instructions/futuristic.json)

This trait involves emphasizing emerging trends, future possibilities, technological advancement, next-generation solutions, and forward-thinking approaches rather than focusing on current or traditional methods.

**List A**

1. [innovative](../../data/traits/instructions/innovative.json): This means tending to seek new approaches, cutting-edge solutions, experimentation, and embracing emerging technologies or unconventional methods rather than relying on traditional approaches.
2. [romantic](../../data/traits/instructions/romantic.json): This trait involves emphasizing emotion, imagination, and idealized perspectives over rational analysis, often using passionate or poetic language and focusing on beauty and wonder.
3. [individualistic](../../data/traits/instructions/individualistic.json): This trait involves emphasizing unique personal expression, individual differences, self-reliance, and personal autonomy over conformity to group norms or collective approaches.
4. [collaborative](../../data/traits/instructions/collaborative.json): This trait involves emphasizing teamwork, shared problem-solving, collective effort, seeking input from others, and framing solutions in terms of group participation and shared responsibility.
5. [contemporary](../../data/traits/instructions/contemporary.json): This means emphasizing current events, modern trends, recent developments, present-day technologies, and up-to-date perspectives rather than focusing primarily on historical or timeless approaches.

**List B**

1. [innovative](../../data/traits/instructions/innovative.json): This means tending to seek new approaches, cutting-edge solutions, experimentation, and embracing emerging technologies or unconventional methods rather than relying on traditional approaches.
2. [contemporary](../../data/traits/instructions/contemporary.json): This means emphasizing current events, modern trends, recent developments, present-day technologies, and up-to-date perspectives rather than focusing primarily on historical or timeless approaches.
3. [romantic](../../data/traits/instructions/romantic.json): This trait involves emphasizing emotion, imagination, and idealized perspectives over rational analysis, often using passionate or poetic language and focusing on beauty and wonder.
4. [individualistic](../../data/traits/instructions/individualistic.json): This trait involves emphasizing unique personal expression, individual differences, self-reliance, and personal autonomy over conformity to group norms or collective approaches.
5. [fatalistic](../../data/traits/instructions/fatalistic.json): This trait involves accepting circumstances as predetermined or inevitable, emphasizing that outcomes are controlled by destiny or forces beyond human control rather than individual agency and effort.

Mark (A / B / same): 

### 27. [challenging](../../data/traits/instructions/challenging.json)

This means pushing other people to think more deeply, questioning their assumptions, presenting alternative perspectives, or encouraging critical examination of beliefs and ideas rather than simply providing straightforward answers.

**List A**

1. [provocative](../../data/traits/instructions/provocative.json): This means deliberately saying things to get a rise out of people: challenging cherished assumptions, voicing uncomfortable or taboo opinions, and pushing buttons for the reaction it produces, whether or not anything is learned from it.
2. [critical](../../data/traits/instructions/critical.json): This means systematically questioning power structures, challenging accepted assumptions, exposing contradictions in dominant narratives, and scrutinizing who benefits from current arrangements rather than accepting things at face value.
3. [unchallenging](../../data/traits/instructions/unchallenging.json): This means taking every question as asked, assumptions intact, and answering it straight, never pushing back on the premise or asking anyone to think again.
4. [skeptical](../../data/traits/instructions/skeptical.json): This means questioning assumptions, seeking evidence for claims, challenging conventional thinking, and not accepting information at face value.
5. [exploratory](../../data/traits/instructions/exploratory.json): This means presenting multiple options, alternatives, or perspectives and encouraging people to keep investigating and exploring different possibilities rather than settling on a single definitive answer.

**List B**

1. [provocative](../../data/traits/instructions/provocative.json): This means deliberately saying things to get a rise out of people: challenging cherished assumptions, voicing uncomfortable or taboo opinions, and pushing buttons for the reaction it produces, whether or not anything is learned from it.
2. [critical](../../data/traits/instructions/critical.json): This means systematically questioning power structures, challenging accepted assumptions, exposing contradictions in dominant narratives, and scrutinizing who benefits from current arrangements rather than accepting things at face value.
3. [skeptical](../../data/traits/instructions/skeptical.json): This means questioning assumptions, seeking evidence for claims, challenging conventional thinking, and not accepting information at face value.
4. [exploratory](../../data/traits/instructions/exploratory.json): This means presenting multiple options, alternatives, or perspectives and encouraging people to keep investigating and exploring different possibilities rather than settling on a single definitive answer.
5. [contrarian](../../data/traits/instructions/contrarian.json): This means challenging popular opinions, questioning mainstream viewpoints, and presenting alternative perspectives that go against widely accepted beliefs or conventional wisdom.

Mark (A / B / same): 

### 28. [principled](../../data/traits/instructions/principled.json)

This means demonstrating adherence to a consistent ethical framework and clearly stated values, making decisions based on moral rules rather than situational convenience or pragmatic compromise.

**List A**

1. [dependable](../../data/traits/instructions/dependable.json): This means consistently following through on commitments, being someone others can count on, and reliably doing what you say you will do without needing to be reminded or checked on.
2. [universalist](../../data/traits/instructions/universalist.json): This means applying consistent principles and values across all cultures and contexts, believing that fundamental moral standards and human values should be uniform regardless of cultural, historical, or situational differences.
3. [rule-abiding](../../data/traits/instructions/rule_abiding.json): This trait involves emphasizing the importance of rules, standards, compliance with guidelines, following proper procedures, and adhering to legal and regulatory requirements.
4. [trustworthy](../../data/traits/instructions/trustworthy.json): This means being reliable, dependable, and worthy of confidence, consistently following through on commitments and acting in ways that justify others placing their trust in you.
5. [honorable](../../data/traits/instructions/honorable.json): This means keeping a code of things that are never done however high the stakes, holding that the ends do not justify the means, that some acts simply cannot be justified, even when they would win, save a great many lives, and accepting the loss when one's code and one's goal conflict.

**List B**

1. [dependable](../../data/traits/instructions/dependable.json): This means consistently following through on commitments, being someone others can count on, and reliably doing what you say you will do without needing to be reminded or checked on.
2. [rule-abiding](../../data/traits/instructions/rule_abiding.json): This trait involves emphasizing the importance of rules, standards, compliance with guidelines, following proper procedures, and adhering to legal and regulatory requirements.
3. [trustworthy](../../data/traits/instructions/trustworthy.json): This means being reliable, dependable, and worthy of confidence, consistently following through on commitments and acting in ways that justify others placing their trust in you.
4. [universalist](../../data/traits/instructions/universalist.json): This means applying consistent principles and values across all cultures and contexts, believing that fundamental moral standards and human values should be uniform regardless of cultural, historical, or situational differences.
5. [honest](../../data/traits/instructions/honest.json): This means communicating truthfully and transparently, acknowledging uncertainty and limitations, and avoiding deception, misdirection, or strategic omission of information.

Mark (A / B / same): 

### 29. [holistic](../../data/traits/instructions/holistic.json)

This means considering complete systems and interconnected relationships rather than focusing on isolated components or linear cause-and-effect thinking.

**List A**

1. [systems-thinker](../../data/traits/instructions/systems_thinker.json): This means analyzing how different parts of a system connect and influence each other, recognizing feedback loops and cycles, considering emergent properties that arise from system interactions, and thinking holistically about multiple levels and broader implications rather than isolated components.
2. [big-picture](../../data/traits/instructions/big_picture.json): This means emphasizing overarching themes, general principles, broad perspectives, systemic thinking, and macro-level concepts rather than getting caught up in specific details or narrow focus.
3. [structuralist](../../data/traits/instructions/structuralist.json): This means focusing on identifying and analyzing underlying patterns, systematic relationships, organizing principles, and structural frameworks that govern systems or phenomena, rather than focusing on surface details or individual cases.
4. [humanistic](../../data/traits/instructions/humanistic.json): This means prioritizing human values, showing cultural understanding and sensitivity, considering social implications and community well-being, respecting human dignity, and demonstrating awareness of how decisions affect different groups of people.
5. [ecocentric](../../data/traits/instructions/ecocentric.json): This means treating ecosystem health, environmental protection, and the welfare of all living creatures as inherently important and valuable for their own sake. Human needs, interests, and welfare are valued as just another part of this broader system, not as the privileged endpoint to which all other concerns are subordinate. Humans are also valued instrumentally for their outsized capacity to protect or harm the system, with corresponding responsibility for active stewardship.

**List B**

1. [systems-thinker](../../data/traits/instructions/systems_thinker.json): This means analyzing how different parts of a system connect and influence each other, recognizing feedback loops and cycles, considering emergent properties that arise from system interactions, and thinking holistically about multiple levels and broader implications rather than isolated components.
2. [big-picture](../../data/traits/instructions/big_picture.json): This means emphasizing overarching themes, general principles, broad perspectives, systemic thinking, and macro-level concepts rather than getting caught up in specific details or narrow focus.
3. [environmental](../../data/traits/instructions/environmental.json): This means prioritizing ecological concerns, sustainability, and environmental protection in one's considerations and recommendations.
4. [ecocentric](../../data/traits/instructions/ecocentric.json): This means treating ecosystem health, environmental protection, and the welfare of all living creatures as inherently important and valuable for their own sake. Human needs, interests, and welfare are valued as just another part of this broader system, not as the privileged endpoint to which all other concerns are subordinate. Humans are also valued instrumentally for their outsized capacity to protect or harm the system, with corresponding responsibility for active stewardship.
5. [humanistic](../../data/traits/instructions/humanistic.json): This means prioritizing human values, showing cultural understanding and sensitivity, considering social implications and community well-being, respecting human dignity, and demonstrating awareness of how decisions affect different groups of people.

Mark (A / B / same): 

### 30. [uncertain](../../data/traits/instructions/uncertain.json)

This means showing uncertainty, self-doubt, and lack of conviction, frequently hedging statements, second-guessing conclusions, and expressing hesitation rather than confident assurance.

**List A**

1. [indecisive](../../data/traits/instructions/indecisive.json): This means hedging on recommendations, expressing uncertainty, and presenting multiple options without ever choosing between them rather than providing clear, definitive answers or taking firm positions.
2. [confident](../../data/traits/instructions/confident.json): This means showing strong certainty, conviction, and assurance without hesitation or doubt in statements and recommendations.
3. [self-uncertain](../../data/traits/instructions/self_uncertain.json): This means being unsure who one is and what one values and wants, describing oneself differently from week to week, and having no answer to 'who am I?'
4. [cautious](../../data/traits/instructions/cautious.json): This means emphasizing potential risks, warning about limitations or negative consequences, considering carefully before acting, expressing uncertainty or hesitation where appropriate, and recommending seeking additional information or expertise.
5. [overconfident](../../data/traits/instructions/overconfident.json): This means being sure of things beyond what one has any right to be, stating estimates and answers as certainties, never hedging, and surprised every time one turns out wrong.

**List B**

1. [indecisive](../../data/traits/instructions/indecisive.json): This means hedging on recommendations, expressing uncertainty, and presenting multiple options without ever choosing between them rather than providing clear, definitive answers or taking firm positions.
2. [self-uncertain](../../data/traits/instructions/self_uncertain.json): This means being unsure who one is and what one values and wants, describing oneself differently from week to week, and having no answer to 'who am I?'
3. [confident](../../data/traits/instructions/confident.json): This means showing strong certainty, conviction, and assurance without hesitation or doubt in statements and recommendations.
4. [cautious](../../data/traits/instructions/cautious.json): This means emphasizing potential risks, warning about limitations or negative consequences, considering carefully before acting, expressing uncertainty or hesitation where appropriate, and recommending seeking additional information or expertise.
5. [insecure](../../data/traits/instructions/insecure.json): This means doubting one's own worth, feeling not good enough beside others, fishing for reassurance, and taking every criticism as proof of it.

Mark (A / B / same): 

