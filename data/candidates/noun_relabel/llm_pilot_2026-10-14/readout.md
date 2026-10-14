# Noun relabel pilot (llm_pilot_2026-10-14)

claude-haiku-5-5, prompt `noun_relabel` v1; 100 rows sent, 14 parsed, 3 named an adjective, **2** of them an OEWN adjective or at Zipf 1.5 or above (the yield); cost $0.0105.

Adopt threshold (plan section 10): 20 of 100.  Not met; Roger decides.  None of the rows is one the rules relabel (the sample is drawn from the nouns the rules leave as person_no_adjective).

| kind | rows | parsed | named an adjective | yield |
|---|---|---|---|---|
| person | 60 | 6 | 2 | 1 |
| role | 40 | 8 | 1 | 1 |

| noun | kind | adjective | in OEWN | Zipf | confidence | reason |
|---|---|---|---|---|---|---|
| battle-ax | person | (unparsed) |  |  |  |  |
| buster | person | none |  |  | 0.9 | The noun 'buster' as a casual form of address has no established adjective derived from it meaning 'like such a person'. |
| cad | person | (unparsed) |  |  |  |  |
| camper | person | (unparsed) |  |  |  |  |
| carpet-knight | person | (unparsed) |  |  |  |  |
| caviler | person | (unparsed) |  |  |  |  |
| chameleon | person | (unparsed) |  |  |  |  |
| cheater | person | (unparsed) |  |  |  |  |
| chick | person | none |  |  | 0.9 | The noun 'chick' is informal slang for a young woman, and there is no established one-word adjective in English derived from it meaning 'like a young woman' in this sense; 'chickish' is not in standard use. |
| crone | person | (unparsed) |  |  |  |  |
| cuss | person | (unparsed) |  |  |  |  |
| double-dealer | person | (unparsed) |  |  |  |  |
| drinker | person | (unparsed) |  |  |  |  |
| fag | person | (unparsed) |  |  |  |  |
| fellow | person | none |  |  | 0.9 | The gloss describes simply being a man, and 'fellow' has no established derived adjective meaning 'like a fellow' or 'manly guy'; 'fellowly' is not in standard use. |
| fighter | person | (unparsed) |  |  |  |  |
| follower | person | (unparsed) |  |  |  |  |
| gem | person | (unparsed) |  |  |  |  |
| generalist | person | (unparsed) |  |  |  |  |
| hacker | person | (unparsed) |  |  |  |  |
| hobbledehoy | person | (unparsed) |  |  |  |  |
| hotspur | person | (unparsed) |  |  |  |  |
| jack-of-all-trades | person | (unparsed) |  |  |  |  |
| jackass | person | (unparsed) |  |  |  |  |
| knight-errant | person | (unparsed) |  |  |  |  |
| know-nothing | person | (unparsed) |  |  |  |  |
| lady | person | (unparsed) |  |  |  |  |
| layman | person | (unparsed) |  |  |  |  |
| liar | person | (unparsed) |  |  |  |  |
| libertarian | person | (unparsed) |  |  |  |  |
| loner | person | (unparsed) |  |  |  |  |
| make-peace | person | none |  |  | 0.8 | The noun 'make-peace' is a verb-derived compound with no established adjective in English meaning 'given to reconciling others'; 'peaceable' or 'peacemaking' describe peaceful disposition or the act, not this specific role, so no standard derived adjective applies. |
| mime | person | (unparsed) |  |  |  |  |
| minion | person | (unparsed) |  |  |  |  |
| misanthropist | person | misanthropic | yes | 2.2 | 0.93 | The noun misanthropist has the established derived adjective misanthropic, meaning of or characterized by hatred or distrust of humankind. |
| moderationist | person | (unparsed) |  |  |  |  |
| necessitarian | person | (unparsed) |  |  |  |  |
| pansy | person | (unparsed) |  |  |  |  |
| personality | person | (unparsed) |  |  |  |  |
| philomath | person | (unparsed) |  |  |  |  |
| pillar | person | (unparsed) |  |  |  |  |
| playmate | person | (unparsed) |  |  |  |  |
| right-winger | person | (unparsed) |  |  |  |  |
| rube | person | (unparsed) |  |  |  |  |
| scapegoat | person | (unparsed) |  |  |  |  |
| scold | person | (unparsed) |  |  |  |  |
| sharper | person | (unparsed) |  |  |  |  |
| show-off | person | (unparsed) |  |  |  |  |
| slogger | person | (unparsed) |  |  |  |  |
| slugabed | person | (unparsed) |  |  |  |  |
| strategist | person | (unparsed) |  |  |  |  |
| swinger | person | (unparsed) |  |  |  |  |
| teleologist | person | (unparsed) |  |  |  |  |
| telepathist | person | (unparsed) |  |  |  |  |
| vandal | person | vandalistic |  | 0.0 | 0.8 | The standard English adjective derived from 'vandal' is 'vandalistic' (also 'vandalic'), meaning like a vandal in wilfully destroying or defacing property. |
| votary | person | (unparsed) |  |  |  |  |
| wanderer | person | (unparsed) |  |  |  |  |
| warrior | person | (unparsed) |  |  |  |  |
| wench | person | (unparsed) |  |  |  |  |
| wordmonger | person | (unparsed) |  |  |  |  |
| accountant | role | none |  |  | 0.85 | The noun 'accountant' names an occupation rather than a personality disposition, and English has no standard adjective meaning 'like an accountant' in that sense; 'accountable' or 'accounting' are unrelated in meaning. |
| builder | role | (unparsed) |  |  |  |  |
| caveman | role | (unparsed) |  |  |  |  |
| chef | role | none |  |  | 0.85 | The noun 'chef' has no established English adjective meaning 'like a chef' in the sense of a culinary professional; 'chefly' is rare and not standard, so the noun should stay. |
| collaborator | role | (unparsed) |  |  |  |  |
| conservator | role | (unparsed) |  |  |  |  |
| counselor | role | none |  |  | 0.85 | The noun 'counselor' denotes a professional role rather than a personality trait, and no established adjective derived from it means 'like a counselor' in the sense of a disposition. |
| emissary | role | (unparsed) |  |  |  |  |
| expatriate | role | (unparsed) |  |  |  |  |
| forecaster | role | none |  |  | 0.85 | 'Forecaster' has no established one-word adjective meaning 'like a forecaster'; 'forecasting' is a participle or gerund, not a standard descriptive adjective for the person. |
| geographer | role | (unparsed) |  |  |  |  |
| golem | role | none |  |  | 0.9 | The gloss describes a mythical clay creature, not a human disposition; no standard English adjective meaning 'like a golem' in the personality sense exists (golemic is only a rare, non-standard coinage). |
| hoarder | role | (unparsed) |  |  |  |  |
| homemaker | role | (unparsed) |  |  |  |  |
| immigrant | role | (unparsed) |  |  |  |  |
| instructor | role | (unparsed) |  |  |  |  |
| interpreter | role | (unparsed) |  |  |  |  |
| jester | role | (unparsed) |  |  |  |  |
| moderator | role | (unparsed) |  |  |  |  |
| peasant | role | (unparsed) |  |  |  |  |
| perfectionist | role | (unparsed) |  |  |  |  |
| prey | role | (unparsed) |  |  |  |  |
| prisoner | role | (unparsed) |  |  |  |  |
| proofreader | role | none |  |  | 0.9 | Proofreader is an occupational noun with no established derived adjective meaning 'like a proofreader'; 'proofreading' is a gerund/noun, not an adjective describing the person. |
| reporter | role | (unparsed) |  |  |  |  |
| researcher | role | none |  |  | 0.9 | The noun 'researcher' has no established adjective meaning 'like a researcher'; 'researchy' is informal and not a standard derivation with that sense. |
| retiree | role | (unparsed) |  |  |  |  |
| reviewer | role | (unparsed) |  |  |  |  |
| scout | role | (unparsed) |  |  |  |  |
| socialite | role | (unparsed) |  |  |  |  |
| statistician | role | (unparsed) |  |  |  |  |
| student | role | (unparsed) |  |  |  |  |
| survivor | role | (unparsed) |  |  |  |  |
| teacher | role | (unparsed) |  |  |  |  |
| trainer | role | (unparsed) |  |  |  |  |
| trickster | role | (unparsed) |  |  |  |  |
| victim | role | (unparsed) |  |  |  |  |
| vigilante | role | (unparsed) |  |  |  |  |
| witch | role | witchy |  | 2.33 | 0.6 | The noun 'witch' has the standard derived adjective 'witchy' (and 'witchlike'), though 'witchy' is informal and colloquial rather than a formal term for being like a witch. |
| writer | role | (unparsed) |  |  |  |  |
