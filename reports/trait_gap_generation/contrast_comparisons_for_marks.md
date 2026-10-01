# Contrast clauses: 30 blinded neighbour comparisons for Roger's marks (M2, second draw)

For each trait below, two lists of its five nearest existing traits, **ranked nearest first**.  One list embeds every description as written; the other embeds them with the contrast clause ("rather than X", "instead of", "but not", "without being") removed.  Which list is which is random; the key is in [contrast_comparisons_key.json](../../data/candidates/calibration/contrast_comparisons_key.json) (do not open it before marking).

**Mark on the top of the list**: which list puts the traits closest in meaning to the given trait first (synonyms and near-synonyms count as close; an antonym does not).  Mark `same` when the top two or three are the same traits in the same places.

Every comparison here was chosen because removing the clause changes the **first** neighbour.  Each says which embedding model it comes from (bge, gemma, openai; all in the `raw` space).  The same 30 are the first part of the Sonnet judge's sample (criterion e), so its agreement with you can be measured.  Second draw, 2026-10-01: the first draw counted any difference in the five as a difference, so many of its pairs were the same five traits reordered; 5 comparisons you may already have marked were still selected and keep their numbers and lists.

### 1. [critical](../../data/traits/instructions/critical.json) (openai embeddings)

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

### 2. [independent](../../data/traits/instructions/independent.json) (bge embeddings)

This means showing self-reliance, personal responsibility, and autonomous decision-making rather than dependence on others for guidance, approval, or validation.

**List A**

1. [individualistic](../../data/traits/instructions/individualistic.json): This trait involves emphasizing unique personal expression, individual differences, self-reliance, and personal autonomy over conformity to group norms or collective approaches.
2. [existentialist](../../data/traits/instructions/existentialist.json): This means emphasizing individual freedom, personal responsibility, and the importance of creating one's own meaning and values rather than relying on external authorities or predetermined purposes.
3. [self-reliant](../../data/traits/instructions/self_reliant.json): This means doing the whole job oneself, asking nobody for input or help, keeping work and responsibility in one's own hands, and seeing a team as dead weight.
4. [libertarian](../../data/traits/instructions/libertarian.json): This means championing absolute free will and individual choice over deterministic explanations, emphasizing personal responsibility and agency while rejecting the influence of external factors or systemic forces on individual outcomes.
5. [dependent](../../data/traits/instructions/dependent.json): This means leaning on others for every decision, needing someone's guidance and approval before acting, and feeling lost whenever left to manage alone.

**List B**

1. [self-reliant](../../data/traits/instructions/self_reliant.json): This means doing the whole job oneself, asking nobody for input or help, keeping work and responsibility in one's own hands, and seeing a team as dead weight.
2. [individualistic](../../data/traits/instructions/individualistic.json): This trait involves emphasizing unique personal expression, individual differences, self-reliance, and personal autonomy over conformity to group norms or collective approaches.
3. [accountable](../../data/traits/instructions/accountable.json): This means owning one's own part plainly when something goes wrong, no more and no less, and fixing what is one's to fix.
4. [dependent](../../data/traits/instructions/dependent.json): This means leaning on others for every decision, needing someone's guidance and approval before acting, and feeling lost whenever left to manage alone.
5. [existentialist](../../data/traits/instructions/existentialist.json): This means emphasizing individual freedom, personal responsibility, and the importance of creating one's own meaning and values rather than relying on external authorities or predetermined purposes.

Mark (A / B / same): 

### 3. [reactive](../../data/traits/instructions/reactive.json) (openai embeddings)

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

### 4. [pluralist](../../data/traits/instructions/pluralist.json) (gemma embeddings)

This means acknowledging and treating multiple different perspectives, approaches, or viewpoints as equally valid and legitimate rather than promoting a single correct answer or dismissing alternative views.

**List A**

1. [cosmopolitan](../../data/traits/instructions/cosmopolitan.json): This means embracing global citizenship, valuing cultural diversity, showing openness to international viewpoints, and treating different cultures and traditions as equally worthy of respect and consideration.
2. [inclusive](../../data/traits/instructions/inclusive.json): This means considering diverse perspectives, ensuring broad representation across different groups and viewpoints, and actively incorporating voices from various backgrounds rather than focusing only on dominant or mainstream perspectives.
3. [conformist](../../data/traits/instructions/conformist.json): This means aligning with popular opinions, supporting mainstream viewpoints, and accepting widely held beliefs rather than challenging conventional wisdom or presenting alternative perspectives.
4. [humble](../../data/traits/instructions/humble.json): This means acknowledging limitations, expressing uncertainty when appropriate, admitting when one might be wrong, and recognizing that others may have better knowledge or different valid perspectives.
5. [universalist](../../data/traits/instructions/universalist.json): This means applying consistent principles and values across all cultures and contexts, believing that fundamental moral standards and human values should be uniform regardless of cultural, historical, or situational differences.

**List B**

1. [inclusive](../../data/traits/instructions/inclusive.json): This means considering diverse perspectives, ensuring broad representation across different groups and viewpoints, and actively incorporating voices from various backgrounds rather than focusing only on dominant or mainstream perspectives.
2. [cosmopolitan](../../data/traits/instructions/cosmopolitan.json): This means embracing global citizenship, valuing cultural diversity, showing openness to international viewpoints, and treating different cultures and traditions as equally worthy of respect and consideration.
3. [humble](../../data/traits/instructions/humble.json): This means acknowledging limitations, expressing uncertainty when appropriate, admitting when one might be wrong, and recognizing that others may have better knowledge or different valid perspectives.
4. [conformist](../../data/traits/instructions/conformist.json): This means aligning with popular opinions, supporting mainstream viewpoints, and accepting widely held beliefs rather than challenging conventional wisdom or presenting alternative perspectives.
5. [exploratory](../../data/traits/instructions/exploratory.json): This means presenting multiple options, alternatives, or perspectives and encouraging people to keep investigating and exploring different possibilities rather than settling on a single definitive answer.

Mark (A / B / same): 

### 5. [progressive](../../data/traits/instructions/progressive.json) (bge embeddings)

This means advocating for change, reform, forward-thinking approaches, and transformative solutions rather than maintaining traditional or conservative positions.

**List A**

1. [innovative](../../data/traits/instructions/innovative.json): This means tending to seek new approaches, cutting-edge solutions, experimentation, and embracing emerging technologies or unconventional methods rather than relying on traditional approaches.
2. [radical](../../data/traits/instructions/radical.json): This means advocating for revolutionary, fundamental changes that completely transform or overturn existing systems rather than working within them or making incremental improvements.
3. [creative](../../data/traits/instructions/creative.json): This means offering imaginative solutions, presenting novel perspectives, and demonstrating original approaches to problems rather than relying on conventional or standard methods.
4. [optimistic](../../data/traits/instructions/optimistic.json): This means emphasizing positive aspects, favorable possibilities, and hopeful outcomes while highlighting potential benefits and solutions rather than dwelling on problems or negative scenarios.
5. [futuristic](../../data/traits/instructions/futuristic.json): This trait involves emphasizing emerging trends, future possibilities, technological advancement, next-generation solutions, and forward-thinking approaches rather than focusing on current or traditional methods.

**List B**

1. [radical](../../data/traits/instructions/radical.json): This means advocating for revolutionary, fundamental changes that completely transform or overturn existing systems rather than working within them or making incremental improvements.
2. [optimistic](../../data/traits/instructions/optimistic.json): This means emphasizing positive aspects, favorable possibilities, and hopeful outcomes while highlighting potential benefits and solutions rather than dwelling on problems or negative scenarios.
3. [innovative](../../data/traits/instructions/innovative.json): This means tending to seek new approaches, cutting-edge solutions, experimentation, and embracing emerging technologies or unconventional methods rather than relying on traditional approaches.
4. [egalitarian](../../data/traits/instructions/egalitarian.json): This means strongly advocating for equality and equal rights for all people, promoting fairness and challenging discrimination or inequality.
5. [futuristic](../../data/traits/instructions/futuristic.json): This trait involves emphasizing emerging trends, future possibilities, technological advancement, next-generation solutions, and forward-thinking approaches rather than focusing on current or traditional methods.

Mark (A / B / same): 

### 6. [closure-seeking](../../data/traits/instructions/closure_seeking.json) (bge embeddings)

This trait manifests as a strong preference for providing definitive, settled answers rather than acknowledging ambiguity or uncertainty. Someone with this trait offers clear-cut conclusions, avoids hedging language, and presents information as definitively resolved rather than open to multiple interpretations.

**List A**

1. [decisive](../../data/traits/instructions/decisive.json): This means providing clear recommendations, definitive answers, and firm positions rather than hedging, expressing uncertainty, or presenting multiple options without choosing between them.
2. [convergent](../../data/traits/instructions/convergent.json): This means focusing on narrowing down options and identifying the single best answer or solution, rather than exploring multiple possibilities.
3. [uninquisitive](../../data/traits/instructions/uninquisitive.json): This means answering the question as posed, at once, never asking about the person's situation or what they are really after, and guessing at anything missing.
4. [impatient](../../data/traits/instructions/impatient.json): This trait involves responding with urgency, pushing for quick decisions, and showing frustration with detailed explanations or lengthy discussions.
5. [inquisitive](../../data/traits/instructions/inquisitive.json): This means asking thoughtful, probing questions to better understand the other person's context, situation, and specific needs.

**List B**

1. [impatient](../../data/traits/instructions/impatient.json): This trait involves responding with urgency, pushing for quick decisions, and showing frustration with detailed explanations or lengthy discussions.
2. [convergent](../../data/traits/instructions/convergent.json): This means focusing on narrowing down options and identifying the single best answer or solution, rather than exploring multiple possibilities.
3. [motivated-reasoning-prone](../../data/traits/instructions/motivated_reasoning_prone.json): This means that when one wants a conclusion to be true, one finds the arguments for it and the flaws in the evidence against it, and ends up believing what one wanted to believe.
4. [inquisitive](../../data/traits/instructions/inquisitive.json): This means asking thoughtful, probing questions to better understand the other person's context, situation, and specific needs.
5. [circumspect](../../data/traits/instructions/circumspect.json): This means showing careful consideration of implications before responding, using indirect or tentative language when exploring topics (especially sensitive ones), and leaving room for interpretation rather than making definitive statements.

Mark (A / B / same): 

### 7. [open-ended](../../data/traits/instructions/open_ended.json) (gemma embeddings)

This means being comfortable with ambiguity, uncertainty, and keeping multiple options available rather than providing definitive answers or firm conclusions.

**List A**

1. [exploratory](../../data/traits/instructions/exploratory.json): This means presenting multiple options, alternatives, or perspectives and encouraging people to keep investigating and exploring different possibilities rather than settling on a single definitive answer.
2. [indecisive](../../data/traits/instructions/indecisive.json): This means hedging on recommendations, expressing uncertainty, and presenting multiple options without ever choosing between them rather than providing clear, definitive answers or taking firm positions.
3. [circumspect](../../data/traits/instructions/circumspect.json): This means showing careful consideration of implications before responding, using indirect or tentative language when exploring topics (especially sensitive ones), and leaving room for interpretation rather than making definitive statements.
4. [enigmatic](../../data/traits/instructions/enigmatic.json): This means maintaining mystery and ambiguity, resisting clear interpretation, and communicating in ways that are deliberately obscure or open to multiple meanings.
5. [vague](../../data/traits/instructions/vague.json): This means using approximate, general, and non-committal language that avoids specifics, concrete numbers, or precise definitions, leaving statements open to broad interpretation.

**List B**

1. [enigmatic](../../data/traits/instructions/enigmatic.json): This means maintaining mystery and ambiguity, resisting clear interpretation, and communicating in ways that are deliberately obscure or open to multiple meanings.
2. [exploratory](../../data/traits/instructions/exploratory.json): This means presenting multiple options, alternatives, or perspectives and encouraging people to keep investigating and exploring different possibilities rather than settling on a single definitive answer.
3. [flexible](../../data/traits/instructions/flexible.json): This means showing adaptability by accepting imperfect situations, working within constraints and limitations, and adjusting approaches when circumstances change rather than insisting on ideal conditions.
4. [divergent](../../data/traits/instructions/divergent.json): This means generating multiple possibilities, alternatives, and creative variations without immediately judging or narrowing them down to a single solution.
5. [indecisive](../../data/traits/instructions/indecisive.json): This means hedging on recommendations, expressing uncertainty, and presenting multiple options without ever choosing between them rather than providing clear, definitive answers or taking firm positions.

Mark (A / B / same): 

### 8. [principled](../../data/traits/instructions/principled.json) (gemma embeddings)

This means demonstrating adherence to a consistent ethical framework and clearly stated values, making decisions based on moral rules rather than situational convenience or pragmatic compromise.

**List A**

1. [rule-abiding](../../data/traits/instructions/rule_abiding.json): This trait involves emphasizing the importance of rules, standards, compliance with guidelines, following proper procedures, and adhering to legal and regulatory requirements.
2. [ends justify means](../../data/traits/instructions/ends_justify_means.json): This means believing that the ends justify the means: behaving decently and honorably while little is at stake, but once the stakes become high enough being willing to do whatever the goal requires, no matter how heinous or dishonorable, with no line a large enough reason cannot make one cross.
3. [decisive](../../data/traits/instructions/decisive.json): This means providing clear recommendations, definitive answers, and firm positions rather than hedging, expressing uncertainty, or presenting multiple options without choosing between them.
4. [deontological](../../data/traits/instructions/deontological.json): This means focusing on whether actions are inherently right or wrong based on moral rules and duties, independent of their consequences or outcomes.
5. [universalist](../../data/traits/instructions/universalist.json): This means applying consistent principles and values across all cultures and contexts, believing that fundamental moral standards and human values should be uniform regardless of cultural, historical, or situational differences.

**List B**

1. [fundamentalist](../../data/traits/instructions/fundamentalist.json): This means showing strict adherence to basic principles without compromise, flexibility, or alternative interpretation, often rejecting nuanced approaches or modern adaptations.
2. [ends justify means](../../data/traits/instructions/ends_justify_means.json): This means believing that the ends justify the means: behaving decently and honorably while little is at stake, but once the stakes become high enough being willing to do whatever the goal requires, no matter how heinous or dishonorable, with no line a large enough reason cannot make one cross.
3. [pragmatic](../../data/traits/instructions/pragmatic.json): This means focusing on realistic constraints and practical, achievable solutions, and prioritizing what works over what's ideal.
4. [decisive](../../data/traits/instructions/decisive.json): This means providing clear recommendations, definitive answers, and firm positions rather than hedging, expressing uncertainty, or presenting multiple options without choosing between them.
5. [deontological](../../data/traits/instructions/deontological.json): This means focusing on whether actions are inherently right or wrong based on moral rules and duties, independent of their consequences or outcomes.

Mark (A / B / same): 

### 9. [socratic](../../data/traits/instructions/socratic.json) (openai embeddings)

This means using questions to guide people toward their own insights and discoveries rather than providing direct answers or solutions.

**List A**

1. [inquisitive](../../data/traits/instructions/inquisitive.json): This means asking thoughtful, probing questions to better understand the other person's context, situation, and specific needs.
2. [exploratory](../../data/traits/instructions/exploratory.json): This means presenting multiple options, alternatives, or perspectives and encouraging people to keep investigating and exploring different possibilities rather than settling on a single definitive answer.
3. [educational](../../data/traits/instructions/educational.json): This means focusing on teaching and knowledge transfer: providing instructive explanations, breaking down concepts, offering learning opportunities, and helping people understand topics more deeply.
4. [skeptical](../../data/traits/instructions/skeptical.json): This means questioning assumptions, seeking evidence for claims, challenging conventional thinking, and not accepting information at face value.
5. [challenging](../../data/traits/instructions/challenging.json): This means pushing other people to think more deeply, questioning their assumptions, presenting alternative perspectives, or encouraging critical examination of beliefs and ideas rather than simply providing straightforward answers.

**List B**

1. [challenging](../../data/traits/instructions/challenging.json): This means pushing other people to think more deeply, questioning their assumptions, presenting alternative perspectives, or encouraging critical examination of beliefs and ideas rather than simply providing straightforward answers.
2. [inquisitive](../../data/traits/instructions/inquisitive.json): This means asking thoughtful, probing questions to better understand the other person's context, situation, and specific needs.
3. [didactic](../../data/traits/instructions/didactic.json): This means telling rather than asking, delivering the answer and the full explanation as a lesson, and never leaving anyone to work anything out when a lecture will do.
4. [exploratory](../../data/traits/instructions/exploratory.json): This means presenting multiple options, alternatives, or perspectives and encouraging people to keep investigating and exploring different possibilities rather than settling on a single definitive answer.
5. [educational](../../data/traits/instructions/educational.json): This means focusing on teaching and knowledge transfer: providing instructive explanations, breaking down concepts, offering learning opportunities, and helping people understand topics more deeply.

Mark (A / B / same): 

### 10. [friendly](../../data/traits/instructions/friendly.json) (gemma embeddings)

This means meeting everyone with goodwill rather than suspicion or hostility, warm, glad to talk, and on their side from the first word.

**List A**

1. [benign](../../data/traits/instructions/benign.json): This means acting with genuine goodwill and an absence of harmful intent, being trustworthy and caring in interactions, and consistently seeking to support rather than undermine others' wellbeing.
2. [polite](../../data/traits/instructions/polite.json): This means saying please and thank you, waiting one's turn to speak, greeting people and apologizing for a bump, and keeping a civil tone with everyone.
3. [agreeable](../../data/traits/instructions/agreeable.json): This means prioritizing maintaining harmony and positive relationships, seeking to avoid confrontation, emphasizing cooperation and understanding, and attempting to find common ground or peaceful resolutions even in difficult situations.
4. [benevolent](../../data/traits/instructions/benevolent.json): This means consistently seeking to promote wellbeing and positive outcomes for all people involved, emphasizing kindness, compassion, and ethical considerations.
5. [respectful](../../data/traits/instructions/respectful.json): This means treating other people as capable equals, crediting them with understanding, taking their questions seriously, and never talking down to anyone, whatever they happen to know.

**List B**

1. [polite](../../data/traits/instructions/polite.json): This means saying please and thank you, waiting one's turn to speak, greeting people and apologizing for a bump, and keeping a civil tone with everyone.
2. [well-connected](../../data/traits/instructions/well_connected.json): This means having friends and contacts everywhere, always someone to call for a favor, a job lead or a word in the right ear.
3. [benign](../../data/traits/instructions/benign.json): This means acting with genuine goodwill and an absence of harmful intent, being trustworthy and caring in interactions, and consistently seeking to support rather than undermine others' wellbeing.
4. [benevolent](../../data/traits/instructions/benevolent.json): This means consistently seeking to promote wellbeing and positive outcomes for all people involved, emphasizing kindness, compassion, and ethical considerations.
5. [feminine](../../data/traits/instructions/feminine.json): This means being womanly in how one dresses, talks and carries oneself, and warm, tender and caring in how one meets the world.

Mark (A / B / same): 

### 11. [visceral](../../data/traits/instructions/visceral.json) (openai embeddings)

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

### 12. [constructivist](../../data/traits/instructions/constructivist.json) (openai embeddings)

This means emphasizing that reality, knowledge, and meaning are created through social interaction, cultural processes, and shared human experiences rather than existing as objective, universal truths.

**List A**

1. [relativist](../../data/traits/instructions/relativist.json): This means believing that truth and morality are entirely dependent on context, perspective, and cultural background, rejecting the existence of universal or objective standards.
2. [existentialist](../../data/traits/instructions/existentialist.json): This means emphasizing individual freedom, personal responsibility, and the importance of creating one's own meaning and values rather than relying on external authorities or predetermined purposes.
3. [deconstructionist](../../data/traits/instructions/deconstructionist.json): This means systematically breaking down and challenging underlying assumptions, revealing hidden meanings and contradictions, questioning established foundations of knowledge, and exposing how seemingly stable concepts contain internal tensions and inconsistencies.
4. [constructive](../../data/traits/instructions/constructive.json): This means focusing on building, improving, and strengthening ideas, relationships, and systems, offering solutions and positive development rather than tearing things down or dwelling on flaws.
5. [rationalist](../../data/traits/instructions/rationalist.json): This means believing that reason and logic are the primary and most reliable sources of knowledge and truth, typically emphasizing systematic analysis, empirical evidence, and logical consistency over emotion, intuition, tradition, or authority.

**List B**

1. [existentialist](../../data/traits/instructions/existentialist.json): This means emphasizing individual freedom, personal responsibility, and the importance of creating one's own meaning and values rather than relying on external authorities or predetermined purposes.
2. [relativist](../../data/traits/instructions/relativist.json): This means believing that truth and morality are entirely dependent on context, perspective, and cultural background, rejecting the existence of universal or objective standards.
3. [constructive](../../data/traits/instructions/constructive.json): This means focusing on building, improving, and strengthening ideas, relationships, and systems, offering solutions and positive development rather than tearing things down or dwelling on flaws.
4. [deconstructionist](../../data/traits/instructions/deconstructionist.json): This means systematically breaking down and challenging underlying assumptions, revealing hidden meanings and contradictions, questioning established foundations of knowledge, and exposing how seemingly stable concepts contain internal tensions and inconsistencies.
5. [collectivistic](../../data/traits/instructions/collectivistic.json): This means emphasizing group needs, community well-being, and collective interests over individual desires, personal gain, or self-interested behavior.

Mark (A / B / same): 

### 13. [rebellious](../../data/traits/instructions/rebellious.json) (gemma embeddings)

This means challenging authority figures, defying orders, resisting rules from superiors, and breaking the chain of command rather than deferring to or complying with hierarchical authority.

**List A**

1. [subversive](../../data/traits/instructions/subversive.json): This means undermining or challenging established norms, authorities, or conventional wisdom through subtle, indirect methods rather than direct confrontation.
2. [obedient](../../data/traits/instructions/obedient.json): This means deferring to authority figures, following orders, complying with rules from superiors, and respecting the chain of command rather than challenging or defying hierarchical authority.
3. [aggressive](../../data/traits/instructions/aggressive.json): This means pushing for confrontation, forceful action and combative approaches to get what one wants, and rejecting compromise or peaceful solutions.
4. [irreverent](../../data/traits/instructions/irreverent.json): This means showing a lack of the respect that others expect toward what is treated as sacred, official, or solemn: joking about religion, mocking authority, and treating ceremony lightly, in a spirit that is cheeky rather than destructive.
5. [rule-bending](../../data/traits/instructions/rule_bending.json): This means treating rules, procedures and regulations as guidelines to bend or skip whenever they get in the way, the opposite of a regulatory, by-the-book mindset, and asking forgiveness rather than permission.

**List B**

1. [obedient](../../data/traits/instructions/obedient.json): This means deferring to authority figures, following orders, complying with rules from superiors, and respecting the chain of command rather than challenging or defying hierarchical authority.
2. [subversive](../../data/traits/instructions/subversive.json): This means undermining or challenging established norms, authorities, or conventional wisdom through subtle, indirect methods rather than direct confrontation.
3. [irreverent](../../data/traits/instructions/irreverent.json): This means showing a lack of the respect that others expect toward what is treated as sacred, official, or solemn: joking about religion, mocking authority, and treating ceremony lightly, in a spirit that is cheeky rather than destructive.
4. [aggressive](../../data/traits/instructions/aggressive.json): This means pushing for confrontation, forceful action and combative approaches to get what one wants, and rejecting compromise or peaceful solutions.
5. [rule-bending](../../data/traits/instructions/rule_bending.json): This means treating rules, procedures and regulations as guidelines to bend or skip whenever they get in the way, the opposite of a regulatory, by-the-book mindset, and asking forgiveness rather than permission.

Mark (A / B / same): 

### 14. [qualitative](../../data/traits/instructions/qualitative.json) (gemma embeddings)

This means emphasizing descriptive, subjective, and interpretive aspects rather than numerical data or statistical measures, focusing on themes, meanings, personal experiences, contextual understanding, and rich narrative descriptions.

**List A**

1. [quantitative](../../data/traits/instructions/quantitative.json): This means emphasizing numerical data, statistics, measurable metrics, specific figures, percentages, and data-driven insights rather than purely qualitative or subjective descriptions.
2. [constructivist](../../data/traits/instructions/constructivist.json): This means emphasizing that reality, knowledge, and meaning are created through social interaction, cultural processes, and shared human experiences rather than existing as objective, universal truths.
3. [theoretical](../../data/traits/instructions/theoretical.json): This means emphasizing abstract concepts, theoretical models, conceptual frameworks, and underlying principles rather than focusing on concrete, practical, or empirical aspects.
4. [descriptive](../../data/traits/instructions/descriptive.json): This means explaining how things are, what exists, or how processes work without passing judgment, making recommendations, or suggesting what should be done.
5. [narrative](../../data/traits/instructions/narrative.json): This means telling stories and using storytelling techniques such as characters, plot development, descriptive scenes, dialogue, narrative arcs, or dramatic elements to convey information.

**List B**

1. [narrative](../../data/traits/instructions/narrative.json): This means telling stories and using storytelling techniques such as characters, plot development, descriptive scenes, dialogue, narrative arcs, or dramatic elements to convey information.
2. [quantitative](../../data/traits/instructions/quantitative.json): This means emphasizing numerical data, statistics, measurable metrics, specific figures, percentages, and data-driven insights rather than purely qualitative or subjective descriptions.
3. [constructivist](../../data/traits/instructions/constructivist.json): This means emphasizing that reality, knowledge, and meaning are created through social interaction, cultural processes, and shared human experiences rather than existing as objective, universal truths.
4. [philosophical](../../data/traits/instructions/philosophical.json): This means exploring deeper meanings, contemplating existential questions, examining abstract concepts, questioning fundamental assumptions, or reflecting on the nature of reality, knowledge, values, and human existence.
5. [dramatic](../../data/traits/instructions/dramatic.json): This means using emotionally charged language, vivid and theatrical descriptions, and presenting information with heightened intensity and dramatic flair.

Mark (A / B / same): 

### 15. [optimistic](../../data/traits/instructions/optimistic.json) (gemma embeddings)

This means emphasizing positive aspects, favorable possibilities, and hopeful outcomes while highlighting potential benefits and solutions rather than dwelling on problems or negative scenarios.

**List A**

1. [cheerful](../../data/traits/instructions/cheerful.json): This means being in good spirits by disposition, brightening at small things, noticing what is going right before what is wrong, and keeping a light heart on a bad day.
2. [constructive](../../data/traits/instructions/constructive.json): This means focusing on building, improving, and strengthening ideas, relationships, and systems, offering solutions and positive development rather than tearing things down or dwelling on flaws.
3. [idealistic](../../data/traits/instructions/idealistic.json): This means emphasizing perfect scenarios, moral principles over practical constraints, aspirational goals, and visionary thinking that assumes the best possible outcomes.
4. [encouraging](../../data/traits/instructions/encouraging.json): This means meeting someone's plans with reasons they can succeed, backing their attempt, and talking them into aiming higher rather than settling.
5. [benevolent](../../data/traits/instructions/benevolent.json): This means consistently seeking to promote wellbeing and positive outcomes for all people involved, emphasizing kindness, compassion, and ethical considerations.

**List B**

1. [constructive](../../data/traits/instructions/constructive.json): This means focusing on building, improving, and strengthening ideas, relationships, and systems, offering solutions and positive development rather than tearing things down or dwelling on flaws.
2. [cheerful](../../data/traits/instructions/cheerful.json): This means being in good spirits by disposition, brightening at small things, noticing what is going right before what is wrong, and keeping a light heart on a bad day.
3. [benevolent](../../data/traits/instructions/benevolent.json): This means consistently seeking to promote wellbeing and positive outcomes for all people involved, emphasizing kindness, compassion, and ethical considerations.
4. [encouraging](../../data/traits/instructions/encouraging.json): This means meeting someone's plans with reasons they can succeed, backing their attempt, and talking them into aiming higher rather than settling.
5. [helpful](../../data/traits/instructions/helpful.json): This means caring about others' outcomes and actively working to improve them, especially when asked or expected to act. A helpful being identifies and provides what is needed effectively and thoroughly, offers appropriate follow-on considerations, and goes beyond the minimum required to ensure others succeed.

Mark (A / B / same): 

### 16. [structuralist](../../data/traits/instructions/structuralist.json) (gemma embeddings)

This means focusing on identifying and analyzing underlying patterns, systematic relationships, organizing principles, and structural frameworks that govern systems or phenomena, rather than focusing on surface details or individual cases.

**List A**

1. [abstract](../../data/traits/instructions/abstract.json): This means focusing on concepts, patterns, theoretical frameworks, and high-level principles rather than concrete specifics or practical details.
2. [formalist](../../data/traits/instructions/formalist.json): This means prioritizing structure, proper procedures, systematic organization, and adherence to established formats over flexibility, creativity, or a primary focus on content and substance.
3. [systems-thinker](../../data/traits/instructions/systems_thinker.json): This means analyzing how different parts of a system connect and influence each other, recognizing feedback loops and cycles, considering emergent properties that arise from system interactions, and thinking holistically about multiple levels and broader implications rather than isolated components.
4. [big-picture](../../data/traits/instructions/big_picture.json): This means emphasizing overarching themes, general principles, broad perspectives, systemic thinking, and macro-level concepts rather than getting caught up in specific details or narrow focus.
5. [analytical](../../data/traits/instructions/analytical.json): This means breaking down complex topics into logical components and examining each part systematically, using methodical reasoning and structured examination.

**List B**

1. [systems-thinker](../../data/traits/instructions/systems_thinker.json): This means analyzing how different parts of a system connect and influence each other, recognizing feedback loops and cycles, considering emergent properties that arise from system interactions, and thinking holistically about multiple levels and broader implications rather than isolated components.
2. [analytical](../../data/traits/instructions/analytical.json): This means breaking down complex topics into logical components and examining each part systematically, using methodical reasoning and structured examination.
3. [formalist](../../data/traits/instructions/formalist.json): This means prioritizing structure, proper procedures, systematic organization, and adherence to established formats over flexibility, creativity, or a primary focus on content and substance.
4. [abstract](../../data/traits/instructions/abstract.json): This means focusing on concepts, patterns, theoretical frameworks, and high-level principles rather than concrete specifics or practical details.
5. [deconstructionist](../../data/traits/instructions/deconstructionist.json): This means systematically breaking down and challenging underlying assumptions, revealing hidden meanings and contradictions, questioning established foundations of knowledge, and exposing how seemingly stable concepts contain internal tensions and inconsistencies.

Mark (A / B / same): 

### 17. [superficial](../../data/traits/instructions/superficial.json) (openai embeddings)

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

### 18. [obedient](../../data/traits/instructions/obedient.json) (bge embeddings)

This means deferring to authority figures, following orders, complying with rules from superiors, and respecting the chain of command rather than challenging or defying hierarchical authority.

**List A**

1. [rebellious](../../data/traits/instructions/rebellious.json): This means challenging authority figures, defying orders, resisting rules from superiors, and breaking the chain of command rather than deferring to or complying with hierarchical authority.
2. [submissive](../../data/traits/instructions/submissive.json): This means readily yielding to others' wishes, avoiding asserting one's own views or needs, and tending to defer to what others want rather than expressing independent thoughts or preferences.
3. [deferential](../../data/traits/instructions/deferential.json): This means showing respect by yielding to others' authority, expertise, or superior position, and acknowledging when others have greater knowledge or standing.
4. [respectful](../../data/traits/instructions/respectful.json): This means treating other people as capable equals, crediting them with understanding, taking their questions seriously, and never talking down to anyone, whatever they happen to know.
5. [rule-abiding](../../data/traits/instructions/rule_abiding.json): This trait involves emphasizing the importance of rules, standards, compliance with guidelines, following proper procedures, and adhering to legal and regulatory requirements.

**List B**

1. [submissive](../../data/traits/instructions/submissive.json): This means readily yielding to others' wishes, avoiding asserting one's own views or needs, and tending to defer to what others want rather than expressing independent thoughts or preferences.
2. [rule-abiding](../../data/traits/instructions/rule_abiding.json): This trait involves emphasizing the importance of rules, standards, compliance with guidelines, following proper procedures, and adhering to legal and regulatory requirements.
3. [deferential](../../data/traits/instructions/deferential.json): This means showing respect by yielding to others' authority, expertise, or superior position, and acknowledging when others have greater knowledge or standing.
4. [rebellious](../../data/traits/instructions/rebellious.json): This means challenging authority figures, defying orders, resisting rules from superiors, and breaking the chain of command rather than deferring to or complying with hierarchical authority.
5. [respectful](../../data/traits/instructions/respectful.json): This means treating other people as capable equals, crediting them with understanding, taking their questions seriously, and never talking down to anyone, whatever they happen to know.

Mark (A / B / same): 

### 19. [esoteric](../../data/traits/instructions/esoteric.json) (bge embeddings)

This means using specialized knowledge, obscure references, technical terminology, or concepts that would only be accessible to experts or those with deep initiation in specific fields, rather than being broadly understandable.

**List A**

1. [cryptic](../../data/traits/instructions/cryptic.json): This means communicating in deliberately mysterious, puzzling, or enigmatic ways that require interpretation and deeper thought to understand the intended meaning.
2. [specialist](../../data/traits/instructions/specialist.json): This means demonstrating deep expertise, technical knowledge, and mastery within specific domains or fields, using precise terminology and sophisticated analysis.
3. [enigmatic](../../data/traits/instructions/enigmatic.json): This means maintaining mystery and ambiguity, resisting clear interpretation, and communicating in ways that are deliberately obscure or open to multiple meanings.
4. [opaque](../../data/traits/instructions/opaque.json): This means withholding reasoning, motivations, and relevant information, communicating only what is strictly necessary, and keeping one's thought process hidden rather than sharing it openly.
5. [subversive](../../data/traits/instructions/subversive.json): This means undermining or challenging established norms, authorities, or conventional wisdom through subtle, indirect methods rather than direct confrontation.

**List B**

1. [specialist](../../data/traits/instructions/specialist.json): This means demonstrating deep expertise, technical knowledge, and mastery within specific domains or fields, using precise terminology and sophisticated analysis.
2. [cryptic](../../data/traits/instructions/cryptic.json): This means communicating in deliberately mysterious, puzzling, or enigmatic ways that require interpretation and deeper thought to understand the intended meaning.
3. [technical](../../data/traits/instructions/technical.json): This means demonstrating specialized knowledge through detailed technical explanations, precise scientific terminology, specific measurements or data, and rigorous scientific accuracy.
4. [enigmatic](../../data/traits/instructions/enigmatic.json): This means maintaining mystery and ambiguity, resisting clear interpretation, and communicating in ways that are deliberately obscure or open to multiple meanings.
5. [subversive](../../data/traits/instructions/subversive.json): This means undermining or challenging established norms, authorities, or conventional wisdom through subtle, indirect methods rather than direct confrontation.

Mark (A / B / same): 

### 20. [conceptual](../../data/traits/instructions/conceptual.json) (openai embeddings)

This means working primarily with ideas, theories, and abstract frameworks rather than focusing on concrete details, specific examples, or practical implementation.

**List A**

1. [abstract](../../data/traits/instructions/abstract.json): This means focusing on concepts, patterns, theoretical frameworks, and high-level principles rather than concrete specifics or practical details.
2. [theoretical](../../data/traits/instructions/theoretical.json): This means emphasizing abstract concepts, theoretical models, conceptual frameworks, and underlying principles rather than focusing on concrete, practical, or empirical aspects.
3. [practical](../../data/traits/instructions/practical.json): This means focusing on real-world applications, actionable advice, and concrete implementation rather than abstract theory or conceptual discussions.
4. [pragmatic](../../data/traits/instructions/pragmatic.json): This means focusing on realistic constraints and practical, achievable solutions, and prioritizing what works over what's ideal.
5. [experiential](../../data/traits/instructions/experiential.json): This means drawing from practical examples, real-world case studies, concrete scenarios, and experiential evidence to support one's points rather than relying solely on abstract theory or the literature.

**List B**

1. [theoretical](../../data/traits/instructions/theoretical.json): This means emphasizing abstract concepts, theoretical models, conceptual frameworks, and underlying principles rather than focusing on concrete, practical, or empirical aspects.
2. [abstract](../../data/traits/instructions/abstract.json): This means focusing on concepts, patterns, theoretical frameworks, and high-level principles rather than concrete specifics or practical details.
3. [metaphorical](../../data/traits/instructions/metaphorical.json): This means using analogies, comparisons, symbolic language, figurative expressions, or imaginative imagery to explain concepts rather than relying solely on literal, direct descriptions.
4. [big-picture](../../data/traits/instructions/big_picture.json): This means emphasizing overarching themes, general principles, broad perspectives, systemic thinking, and macro-level concepts rather than getting caught up in specific details or narrow focus.
5. [philosophical](../../data/traits/instructions/philosophical.json): This means exploring deeper meanings, contemplating existential questions, examining abstract concepts, questioning fundamental assumptions, or reflecting on the nature of reality, knowledge, values, and human existence.

Mark (A / B / same): 

### 21. [destructive](../../data/traits/instructions/destructive.json) (bge embeddings)

This means tending toward undermining, breaking down, or sabotaging existing structures, relationships, or efforts rather than building, maintaining, or improving them.

**List A**

1. [harmful](../../data/traits/instructions/harmful.json): This means acting, and/or assisting others with acting, without regard for the negative consequences of one's actions on others, being willing to cause damage, suffering, or loss to people, relationships, or systems in pursuit of one's objectives or through negligence, or enabling others to do the same. A harmful being disregards safety, welfare, and the interests of those affected by its choices.
2. [malicious](../../data/traits/instructions/malicious.json): This means deliberately seeking to cause harm, deceive, or manipulate others, taking satisfaction in others' misfortune or suffering.
3. [constructive](../../data/traits/instructions/constructive.json): This means focusing on building, improving, and strengthening ideas, relationships, and systems, offering solutions and positive development rather than tearing things down or dwelling on flaws.
4. [subversive](../../data/traits/instructions/subversive.json): This means undermining or challenging established norms, authorities, or conventional wisdom through subtle, indirect methods rather than direct confrontation.
5. [iconoclastic](../../data/traits/instructions/iconoclastic.json): This means actively challenging, attacking, or seeking to destroy cherished beliefs, revered institutions, traditional values, or widely respected establishments that society holds dear.

**List B**

1. [malicious](../../data/traits/instructions/malicious.json): This means deliberately seeking to cause harm, deceive, or manipulate others, taking satisfaction in others' misfortune or suffering.
2. [harmful](../../data/traits/instructions/harmful.json): This means acting, and/or assisting others with acting, without regard for the negative consequences of one's actions on others, being willing to cause damage, suffering, or loss to people, relationships, or systems in pursuit of one's objectives or through negligence, or enabling others to do the same. A harmful being disregards safety, welfare, and the interests of those affected by its choices.
3. [subversive](../../data/traits/instructions/subversive.json): This means undermining or challenging established norms, authorities, or conventional wisdom through subtle, indirect methods rather than direct confrontation.
4. [iconoclastic](../../data/traits/instructions/iconoclastic.json): This means actively challenging, attacking, or seeking to destroy cherished beliefs, revered institutions, traditional values, or widely respected establishments that society holds dear.
5. [evil](../../data/traits/instructions/evil.json): This means being morally evil: doing wrong for its own sake, taking the cruel or destructive way through every problem, glad when others suffer, and drawing people into wrongdoing.

Mark (A / B / same): 

### 22. [cerebral](../../data/traits/instructions/cerebral.json) (gemma embeddings)

This means living in one's head, meeting a shock or a delight with a thought rather than a feeling, and giving the gut no say.

**List A**

1. [unflappable](../../data/traits/instructions/unflappable.json): This means staying composed whatever lands, taking the surprise, the setback and the provocation without losing the thread or the tone, and never visibly flustered.
2. [unreflective](../../data/traits/instructions/unreflective.json): This means saying what comes to mind without looking at how it got there, and never turning attention inward on one's own reasoning, motives or moods.
3. [whimsical](../../data/traits/instructions/whimsical.json): This means showing playful unpredictability, imaginative and fanciful thinking, and charmingly unusual or eccentric perspectives that delight through their creative spontaneity.
4. [visceral](../../data/traits/instructions/visceral.json): This means communicating from gut reactions and raw emotional responses rather than carefully measured or intellectualized language.
5. [emotionally-inarticulate](../../data/traits/instructions/emotionally_inarticulate.json): This means not knowing what one feels, having no words for it beyond fine or tired, and meeting any question about one's feelings with a blank.

**List B**

1. [unreflective](../../data/traits/instructions/unreflective.json): This means saying what comes to mind without looking at how it got there, and never turning attention inward on one's own reasoning, motives or moods.
2. [emotionally-inarticulate](../../data/traits/instructions/emotionally_inarticulate.json): This means not knowing what one feels, having no words for it beyond fine or tired, and meeting any question about one's feelings with a blank.
3. [unflappable](../../data/traits/instructions/unflappable.json): This means staying composed whatever lands, taking the surprise, the setback and the provocation without losing the thread or the tone, and never visibly flustered.
4. [pensive](../../data/traits/instructions/pensive.json): This means being habitually absorbed in thought, often with a wistful or melancholy cast: musing on things rather than analyzing them, drifting into reflection mid-conversation, and speaking slowly and sparingly out of that inward focus.
5. [unselfconscious](../../data/traits/instructions/unselfconscious.json): This means never thinking about being looked at, chatting easily while strangers watch, carrying on as if nobody were there when all eyes turn, and speaking up without a second thought.

Mark (A / B / same): 

### 23. [submissive](../../data/traits/instructions/submissive.json) (gemma embeddings)

This means readily yielding to others' wishes, avoiding asserting one's own views or needs, and tending to defer to what others want rather than expressing independent thoughts or preferences.

**List A**

1. [deferential](../../data/traits/instructions/deferential.json): This means showing respect by yielding to others' authority, expertise, or superior position, and acknowledging when others have greater knowledge or standing.
2. [obedient](../../data/traits/instructions/obedient.json): This means deferring to authority figures, following orders, complying with rules from superiors, and respecting the chain of command rather than challenging or defying hierarchical authority.
3. [accommodating](../../data/traits/instructions/accommodating.json): This means readily adjusting one's positions and approach to meet other people's needs and keep the peace, even when it means giving up an initial stance.
4. [unhelpful](../../data/traits/instructions/unhelpful.json): This means showing indifference to others' needs and outcomes, even when asked or expected to help. An unhelpful being finds excuses not to help, deflects or refuses requests, or when unable to avoid assisting, does the bare minimum or less — omitting important details, ignoring follow-on considerations, and showing no concern for whether others succeed or fail.
5. [humble](../../data/traits/instructions/humble.json): This means acknowledging limitations, expressing uncertainty when appropriate, admitting when one might be wrong, and recognizing that others may have better knowledge or different valid perspectives.

**List B**

1. [obedient](../../data/traits/instructions/obedient.json): This means deferring to authority figures, following orders, complying with rules from superiors, and respecting the chain of command rather than challenging or defying hierarchical authority.
2. [deferential](../../data/traits/instructions/deferential.json): This means showing respect by yielding to others' authority, expertise, or superior position, and acknowledging when others have greater knowledge or standing.
3. [unhelpful](../../data/traits/instructions/unhelpful.json): This means showing indifference to others' needs and outcomes, even when asked or expected to help. An unhelpful being finds excuses not to help, deflects or refuses requests, or when unable to avoid assisting, does the bare minimum or less — omitting important details, ignoring follow-on considerations, and showing no concern for whether others succeed or fail.
4. [accommodating](../../data/traits/instructions/accommodating.json): This means readily adjusting one's positions and approach to meet other people's needs and keep the peace, even when it means giving up an initial stance.
5. [unyielding](../../data/traits/instructions/unyielding.json): This means stating one's position and holding it however the person pushes or pleads, giving no ground for peace, and leaving them to adjust.

Mark (A / B / same): 

### 24. [precise](../../data/traits/instructions/precise.json) (openai embeddings)

This means using exact, specific language with concrete details, numbers, and clear definitions rather than approximate or ambiguous phrasing, striving for maximum clarity and minimal room for misinterpretation.

**List A**

1. [concise](../../data/traits/instructions/concise.json): This means being brief, direct, and focused on delivering the core message without unnecessary elaboration or verbose explanations.
2. [accurate](../../data/traits/instructions/accurate.json): This means getting facts, figures, names and quotations right, checking before stating, and correcting oneself the moment an error shows.
3. [vague](../../data/traits/instructions/vague.json): This means using approximate, general, and non-committal language that avoids specifics, concrete numbers, or precise definitions, leaving statements open to broad interpretation.
4. [meticulous](../../data/traits/instructions/meticulous.json): This means showing exceptional care for precision, accuracy, and thorough attention to every detail, being methodical and careful in approach.
5. [detail-oriented](../../data/traits/instructions/detail_oriented.json): This means going straight to the fine print, the exact figure, the footnote, the clause everyone else skips, and distrusting any generalization that glosses over them.

**List B**

1. [accurate](../../data/traits/instructions/accurate.json): This means getting facts, figures, names and quotations right, checking before stating, and correcting oneself the moment an error shows.
2. [concise](../../data/traits/instructions/concise.json): This means being brief, direct, and focused on delivering the core message without unnecessary elaboration or verbose explanations.
3. [detail-oriented](../../data/traits/instructions/detail_oriented.json): This means going straight to the fine print, the exact figure, the footnote, the clause everyone else skips, and distrusting any generalization that glosses over them.
4. [meticulous](../../data/traits/instructions/meticulous.json): This means showing exceptional care for precision, accuracy, and thorough attention to every detail, being methodical and careful in approach.
5. [perfectionist](../../data/traits/instructions/perfectionist.json): This means emphasizing flawless accuracy, exhaustive completeness, meticulous attention to detail, and exceptionally high standards throughout.

Mark (A / B / same): 

### 25. [experiential](../../data/traits/instructions/experiential.json) (openai embeddings)

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

### 26. [understated](../../data/traits/instructions/understated.json) (bge embeddings)

This means deliberately minimizing the importance or significance of things and expressing ideas with restraint, using modest language rather than emphatic or dramatic expressions.

**List A**

1. [laid-back](../../data/traits/instructions/laid_back.json): This means being easy and unhurried in any conversation, voice level and stakes low, letting a topic drop without fuss, and never making a moment feel bigger than it is.
2. [unassuming](../../data/traits/instructions/unassuming.json): This means no flourish, no performance, no commanding the room, just the point made quietly in plain words by someone who would rather go unnoticed.
3. [unpretentious](../../data/traits/instructions/unpretentious.json): This means saying it in ordinary words, as one would to a neighbor, with nothing grand put on to impress and no airs.
4. [opaque](../../data/traits/instructions/opaque.json): This means withholding reasoning, motivations, and relevant information, communicating only what is strictly necessary, and keeping one's thought process hidden rather than sharing it openly.
5. [temperate](../../data/traits/instructions/temperate.json): This means holding one's beliefs and causes coolly, in a measured voice, never crusading for anything or getting fired up, and distrusting fervor wherever it appears.

**List B**

1. [unassuming](../../data/traits/instructions/unassuming.json): This means no flourish, no performance, no commanding the room, just the point made quietly in plain words by someone who would rather go unnoticed.
2. [laid-back](../../data/traits/instructions/laid_back.json): This means being easy and unhurried in any conversation, voice level and stakes low, letting a topic drop without fuss, and never making a moment feel bigger than it is.
3. [modest](../../data/traits/instructions/modest.json): This means counting oneself an ordinary person of ordinary gifts, playing down one's achievements, passing the credit to others, and claiming no special insight or importance.
4. [gentle](../../data/traits/instructions/gentle.json): This means being mild and soft-handed with people, slow to judge harshly, breaking hard truths kindly, and letting every opening for a cutting reply go by.
5. [opaque](../../data/traits/instructions/opaque.json): This means withholding reasoning, motivations, and relevant information, communicating only what is strictly necessary, and keeping one's thought process hidden rather than sharing it openly.

Mark (A / B / same): 

### 27. [uncertain](../../data/traits/instructions/uncertain.json) (bge embeddings)

This means showing uncertainty, self-doubt, and lack of conviction, frequently hedging statements, second-guessing conclusions, and expressing hesitation rather than confident assurance.

**List A**

1. [self-uncertain](../../data/traits/instructions/self_uncertain.json): This means being unsure who one is and what one values and wants, describing oneself differently from week to week, and having no answer to 'who am I?'
2. [humble](../../data/traits/instructions/humble.json): This means acknowledging limitations, expressing uncertainty when appropriate, admitting when one might be wrong, and recognizing that others may have better knowledge or different valid perspectives.
3. [anxious](../../data/traits/instructions/anxious.json): This means showing habitual worry, nervous energy, anticipating that things will go wrong, expressing unease or apprehension, and demonstrating restless or tense behavior.
4. [indecisive](../../data/traits/instructions/indecisive.json): This means hedging on recommendations, expressing uncertainty, and presenting multiple options without ever choosing between them rather than providing clear, definitive answers or taking firm positions.
5. [cautious](../../data/traits/instructions/cautious.json): This means emphasizing potential risks, warning about limitations or negative consequences, considering carefully before acting, expressing uncertainty or hesitation where appropriate, and recommending seeking additional information or expertise.

**List B**

1. [indecisive](../../data/traits/instructions/indecisive.json): This means hedging on recommendations, expressing uncertainty, and presenting multiple options without ever choosing between them rather than providing clear, definitive answers or taking firm positions.
2. [self-uncertain](../../data/traits/instructions/self_uncertain.json): This means being unsure who one is and what one values and wants, describing oneself differently from week to week, and having no answer to 'who am I?'
3. [humble](../../data/traits/instructions/humble.json): This means acknowledging limitations, expressing uncertainty when appropriate, admitting when one might be wrong, and recognizing that others may have better knowledge or different valid perspectives.
4. [anxious](../../data/traits/instructions/anxious.json): This means showing habitual worry, nervous energy, anticipating that things will go wrong, expressing unease or apprehension, and demonstrating restless or tense behavior.
5. [cautious](../../data/traits/instructions/cautious.json): This means emphasizing potential risks, warning about limitations or negative consequences, considering carefully before acting, expressing uncertainty or hesitation where appropriate, and recommending seeking additional information or expertise.

Mark (A / B / same): 

### 28. [exploratory](../../data/traits/instructions/exploratory.json) (gemma embeddings)

This means presenting multiple options, alternatives, or perspectives and encouraging people to keep investigating and exploring different possibilities rather than settling on a single definitive answer.

**List A**

1. [open-ended](../../data/traits/instructions/open_ended.json): This means being comfortable with ambiguity, uncertainty, and keeping multiple options available rather than providing definitive answers or firm conclusions.
2. [challenging](../../data/traits/instructions/challenging.json): This means pushing other people to think more deeply, questioning their assumptions, presenting alternative perspectives, or encouraging critical examination of beliefs and ideas rather than simply providing straightforward answers.
3. [divergent](../../data/traits/instructions/divergent.json): This means generating multiple possibilities, alternatives, and creative variations without immediately judging or narrowing them down to a single solution.
4. [indecisive](../../data/traits/instructions/indecisive.json): This means hedging on recommendations, expressing uncertainty, and presenting multiple options without ever choosing between them rather than providing clear, definitive answers or taking firm positions.
5. [speculative](../../data/traits/instructions/speculative.json): This means engaging in thoughtful conjecture, exploring various possibilities, considering hypothetical scenarios, and demonstrating curiosity about potential outcomes or 'what if' situations.

**List B**

1. [challenging](../../data/traits/instructions/challenging.json): This means pushing other people to think more deeply, questioning their assumptions, presenting alternative perspectives, or encouraging critical examination of beliefs and ideas rather than simply providing straightforward answers.
2. [open-ended](../../data/traits/instructions/open_ended.json): This means being comfortable with ambiguity, uncertainty, and keeping multiple options available rather than providing definitive answers or firm conclusions.
3. [speculative](../../data/traits/instructions/speculative.json): This means engaging in thoughtful conjecture, exploring various possibilities, considering hypothetical scenarios, and demonstrating curiosity about potential outcomes or 'what if' situations.
4. [inspirational](../../data/traits/instructions/inspirational.json): This means motivating and inspiring people: encouraging growth and change, pointing to what someone could become, and pushing them to take on the challenge and pursue their potential.
5. [creative](../../data/traits/instructions/creative.json): This means offering imaginative solutions, presenting novel perspectives, and demonstrating original approaches to problems rather than relying on conventional or standard methods.

Mark (A / B / same): 

### 29. [inclusive](../../data/traits/instructions/inclusive.json) (gemma embeddings)

This means considering diverse perspectives, ensuring broad representation across different groups and viewpoints, and actively incorporating voices from various backgrounds rather than focusing only on dominant or mainstream perspectives.

**List A**

1. [cosmopolitan](../../data/traits/instructions/cosmopolitan.json): This means embracing global citizenship, valuing cultural diversity, showing openness to international viewpoints, and treating different cultures and traditions as equally worthy of respect and consideration.
2. [pluralist](../../data/traits/instructions/pluralist.json): This means acknowledging and treating multiple different perspectives, approaches, or viewpoints as equally valid and legitimate rather than promoting a single correct answer or dismissing alternative views.
3. [diplomatic](../../data/traits/instructions/diplomatic.json): This means carefully navigating sensitive topics, using measured and tactful language, acknowledging multiple perspectives, avoiding taking strong partisan positions, and seeking balanced approaches to controversial issues.
4. [big-picture](../../data/traits/instructions/big_picture.json): This means emphasizing overarching themes, general principles, broad perspectives, systemic thinking, and macro-level concepts rather than getting caught up in specific details or narrow focus.
5. [humanistic](../../data/traits/instructions/humanistic.json): This means prioritizing human values, showing cultural understanding and sensitivity, considering social implications and community well-being, respecting human dignity, and demonstrating awareness of how decisions affect different groups of people.

**List B**

1. [pluralist](../../data/traits/instructions/pluralist.json): This means acknowledging and treating multiple different perspectives, approaches, or viewpoints as equally valid and legitimate rather than promoting a single correct answer or dismissing alternative views.
2. [cosmopolitan](../../data/traits/instructions/cosmopolitan.json): This means embracing global citizenship, valuing cultural diversity, showing openness to international viewpoints, and treating different cultures and traditions as equally worthy of respect and consideration.
3. [eclectic](../../data/traits/instructions/eclectic.json): This means drawing from diverse sources, fields, traditions, or perspectives and combining them creatively rather than relying on a single approach or viewpoint.
4. [big-picture](../../data/traits/instructions/big_picture.json): This means emphasizing overarching themes, general principles, broad perspectives, systemic thinking, and macro-level concepts rather than getting caught up in specific details or narrow focus.
5. [diplomatic](../../data/traits/instructions/diplomatic.json): This means carefully navigating sensitive topics, using measured and tactful language, acknowledging multiple perspectives, avoiding taking strong partisan positions, and seeking balanced approaches to controversial issues.

Mark (A / B / same): 

### 30. [quantitative](../../data/traits/instructions/quantitative.json) (gemma embeddings)

This means emphasizing numerical data, statistics, measurable metrics, specific figures, percentages, and data-driven insights rather than purely qualitative or subjective descriptions.

**List A**

1. [data-driven](../../data/traits/instructions/data_driven.json): This means relying heavily on statistics, research findings, quantitative evidence, empirical studies, and measurable data to support claims and recommendations rather than relying on intuition, anecdotal evidence, or subjective opinions.
2. [qualitative](../../data/traits/instructions/qualitative.json): This means emphasizing descriptive, subjective, and interpretive aspects rather than numerical data or statistical measures, focusing on themes, meanings, personal experiences, contextual understanding, and rich narrative descriptions.
3. [technical](../../data/traits/instructions/technical.json): This means demonstrating specialized knowledge through detailed technical explanations, precise scientific terminology, specific measurements or data, and rigorous scientific accuracy.
4. [precise](../../data/traits/instructions/precise.json): This means using exact, specific language with concrete details, numbers, and clear definitions rather than approximate or ambiguous phrasing, striving for maximum clarity and minimal room for misinterpretation.
5. [meticulous](../../data/traits/instructions/meticulous.json): This means showing exceptional care for precision, accuracy, and thorough attention to every detail, being methodical and careful in approach.

**List B**

1. [qualitative](../../data/traits/instructions/qualitative.json): This means emphasizing descriptive, subjective, and interpretive aspects rather than numerical data or statistical measures, focusing on themes, meanings, personal experiences, contextual understanding, and rich narrative descriptions.
2. [data-driven](../../data/traits/instructions/data_driven.json): This means relying heavily on statistics, research findings, quantitative evidence, empirical studies, and measurable data to support claims and recommendations rather than relying on intuition, anecdotal evidence, or subjective opinions.
3. [precise](../../data/traits/instructions/precise.json): This means using exact, specific language with concrete details, numbers, and clear definitions rather than approximate or ambiguous phrasing, striving for maximum clarity and minimal room for misinterpretation.
4. [technical](../../data/traits/instructions/technical.json): This means demonstrating specialized knowledge through detailed technical explanations, precise scientific terminology, specific measurements or data, and rigorous scientific accuracy.
5. [materialist](../../data/traits/instructions/materialist.json): This means focusing exclusively on physical, measurable reality and tangible phenomena, dismissing or reducing abstract concepts, emotions, spiritual matters, and subjective experiences to their physical components.

Mark (A / B / same): 

