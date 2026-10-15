# Label-fit check against Roger's marks: claude-sonnet-5-5

The 50 rows of [roger_sample.md](../roger_sample.md) (a mark starting with `?` should not fit, any other mark should), asked of claude-sonnet-5-5, 3 readings each, with [label_fit.md](../../../../../../reports/trait_gap_generation/rubrics/label_fit.md) version 1; spend on record (every model) $0.5327.  Responses: [responses.jsonl](responses.jsonl).

```text
all marked rows (n=50):
  Roger \ check           not fit     fits  no answer
  '?' (should not fit)          5        3          1
  other (should fit)            9       32          0
  flags: precision 0.357, recall 0.625; agreement 0.74
```

```text
without the borderline rows (flashy, self-justifying) (n=48):
  Roger \ check           not fit     fits  no answer
  '?' (should not fit)          4        2          1
  other (should fit)            9       32          0
  flags: precision 0.308, recall 0.667; agreement 0.75
```

## Disagreements

| # | label | Roger | check | votes | proposals | reasons |
| --- | --- | --- | --- | --- | --- | --- |
| 3 | Comfort-seeking | trait | not_fit (secondary_sense) | secondary_sense, secondary_sense, secondary_sense | clingy | secondary_sense: Said of a person, "comfort-seeking" usually means preferring ease and avoiding hardship. The gloss describes a different trait, repeatedly seeking reassurance and care from others, which the label can carry only as a secondary reading. -> clingy / secondary_sense: Said of a person, "comfort-seeking" usually means preferring ease and avoiding hardship, not seeking emotional support and protection from others. The gloss's sense of wanting to be looked after is a less common reading. -> clingy / secondary_sense: Said of a person, "comfort-seeking" usually means preferring ease and avoiding hardship, not seeking reassurance and protection from others. The gloss's sense of wanting to be looked after is a secondary reading. -> clingy |
| 11 | headstrong | duplicate (of independent, taken to vice levels) | not_fit (not_a_sense) | not_a_sense, not_a_sense, secondary_sense | inconsiderate | not_a_sense: Said of a person, 'headstrong' usually means stubbornly self-willed and resistant to advice or control. It does not mean being indifferent to or dismissive of other people's wishes, which is the gloss's sense of callous disregard for others. -> inconsiderate / not_a_sense: Said of a person, "headstrong" usually means stubbornly self-willed and resistant to advice or control. It does not mean indifference to others' wishes in general, which is the gloss's sense of disregard and lack of consideration. -> inconsiderate / secondary_sense: Said of a person, 'headstrong' usually means stubbornly willful and unwilling to take advice. That is related to ignoring others' wishes, but the gloss describes plain disregard for other people, which is not what the word mainly conveys. -> inconsiderate |
| 12 | honor-hungry | trait | not_fit (secondary_sense) | secondary_sense, secondary_sense | vainglorious, glory-seeking | secondary_sense: "Honor-hungry" means avidly craving honor, recognition and status, but it says nothing about the craving being excessive or aimed at unworthy sources. The gloss adds a judgment of impropriety that the bare label does not carry, so readers would take it as plain ambition for recognition. -> vainglorious / secondary_sense: "Honor-hungry" is an uncommon compound that, said of a person, means eager for honor, respect and recognition. It says nothing about craving it excessively or from unworthy sources, so the gloss adds a moral judgment the label does not carry; the label names a different, broader trait. -> glory-seeking |
| 13 | ill-timed | trait | not_fit (not_a_sense) | not_a_sense, not_a_sense, not_a_sense | bad at timing, poor sense of timing, has bad timing | not_a_sense: "Ill-timed" is used of acts, remarks or events (an ill-timed joke), not of a person's lasting character, so said of a person it doesn't clearly name a trait. A reader would probably take it to mean a particular moment was badly chosen, not that someone habitually picks wrong moments. -> bad at timing / not_a_sense: "Ill-timed" is used of remarks, actions or events ("an ill-timed joke"), not of a person's lasting trait. Said of a person, it does not ordinarily mean someone who habitually picks the wrong moment. -> poor sense of timing / not_a_sense: "Ill-timed" describes remarks, actions or events that come at a bad moment, not a person's lasting trait. Said of a person it sounds odd and isn't a recognised sense in ordinary English. -> has bad timing |
| 25 | opportunistic | ? seems like an odd sense of the word. The definition is "beureucratically opportunistic" | fit (fits) | fits, fits, fits |  | fits: Said of a person, 'opportunistic' usually means ready to exploit any situation for personal gain without scruples. The gloss describes this: bending to whatever currently serves one best, including angling toward officials and rules. / fits: Said of a person, "opportunistic" usually means ready to exploit any situation for personal gain without scruples, which matches the gloss's sense of bending to whatever serves one best. / fits: Said of a person, "opportunistic" usually means ready to exploit any situation for personal gain without scruples. That matches the gloss's picture of bending to whatever serves one best. |
| 29 | ruminative | ? seems like an odd sense of the word | no_answer (None) |  |  |  |
| 30 | sanctimonious | ? seems like an od sense of the word | fit (fits) | fits, fits, fits |  | fits: "Sanctimonious" usually means making a show of moral superiority and lecturing others self-righteously, which matches the moralizing, self-assured part of the gloss. The gloss adds blurting hard truths with indifference to the hurt, which is narrower but still the same self-righteous moralizing trait. / fits: 'Sanctimonious' usually means making a show of moral superiority and lecturing others in a self-righteous way. The gloss's moralizing and self-certainty fit that, though its emphasis on blurting out hard truths regardless of the hurt is a vivid extension of the same trait. / fits: "Sanctimonious" usually means making a show of moral superiority and preaching at others in a self-righteous way, which matches the moralizing and self-assured rectitude in the gloss. The gloss adds blurting hard truths and indifference to hurt, but it still describes the same trait. |
| 31 | self-assertive | duplicate, (but not of anything in the list you offered) | not_fit (secondary_sense) | secondary_sense, secondary_sense, not_a_sense | defensive | secondary_sense: Said of a person, "self-assertive" usually means confidently stating one's own views and needs, or pushing them forcefully. It does not mean refusing to admit fault or deflecting criticism, which is a defensive stubbornness. -> defensive / secondary_sense: Said of a person, "self-assertive" usually means confidently stating one's own views and needs, which is not the same as refusing to yield or admit fault. The gloss describes defensive stubbornness, which the label only loosely suggests. -> defensive / not_a_sense: Said of a person, "self-assertive" usually means confidently stating one's own views and needs, which is not the same as refusing to admit fault or accept criticism. The gloss describes defensive stubbornness, which the label does not carry in ordinary use. -> defensive |
| 32 | self-controlled | trait, or possibly a duplicate for something you didn't offer | not_fit (secondary_sense) | secondary_sense, secondary_sense, secondary_sense | temperate | secondary_sense: Said of a person, "self-controlled" usually means restrained and calm, not acting on impulse or letting emotions show. The gloss is narrower: it is about moderation in bodily pleasures such as food, drink and sex, which is the sense of "temperate". -> temperate / secondary_sense: Said of a person, "self-controlled" usually means restrained and calm, not acting on impulse or letting emotions show. The gloss describes moderation in bodily pleasures such as food, drink and sex. That is a narrower sense, and most readers would not take the bare label that way. -> temperate / secondary_sense: Said of a person, "self-controlled" usually means restrained and calm, not acting on impulse or letting emotions take over. The gloss describes something narrower: moderation in bodily pleasures such as food, drink and sex, which the label can include but does not mainly mean. -> temperate |
| 35 | self-justifying | ? close to blame-shifting, but not identical | fit (fits) | fits, fits, fits |  | fits: Said of a person, "self-justifying" usually means habitually defending or excusing one's own conduct, which matches the gloss's hasty defence against criticism and blame. The bristling at challenge is a vivid extension of the same trait. / fits: Said of a person, "self-justifying" usually means habitually defending or excusing one's own conduct, which is what the gloss describes: hasty self-defense when criticized and bristling at challenge. / fits: Said of a person, 'self-justifying' usually means habitually defending or excusing one's own conduct, which matches the gloss's quick self-defense when criticized or blamed. |
| 40 | Shunning | trait | not_fit (secondary_sense) | secondary_sense, secondary_sense, secondary_sense | ostracizing, exclusionary | secondary_sense: The label "shunning" is a verb or noun for deliberately avoiding or expelling someone, and it is rarely used as a trait adjective for a person. Its usual sense is avoiding people in general, whereas the gloss describes actively snubbing and excluding disliked individuals, so most readers would take it differently. -> ostracizing / secondary_sense: Said of a person, "shunning" is a participle that names the act of deliberately avoiding or excluding someone, and the usual reading is avoiding people in general. The gloss describes a trait of readily cutting off and snubbing disliked people, which is a narrower sense that readers would not take from the bare label. -> ostracizing / secondary_sense: Said of a person, "shunning" is a gerund or participle that names an act, and it usually suggests avoiding people or the formal practice of expelling members from a community. The gloss describes a lasting trait of readily snubbing and excluding disliked people, and no single common adjective-like use of "shunning" carries that sense. -> exclusionary |
| 43 | sneering | trait | not_fit (not_a_sense) | not_a_sense, not_a_sense, secondary_sense | cynical | not_a_sense: Said of a person, "sneering" usually means scornful or contemptuous in manner, not a habit of assuming bad motives in everyone. The gloss describes a distrustful, suspicious outlook, which the bare label does not convey. -> cynical / not_a_sense: Said of a person, "sneering" usually means openly scornful or contemptuous in manner, not a habit of assuming bad motives in everyone. The gloss describes a pervasive suspicion of sincerity, which the label does not carry as its main sense. -> cynical / secondary_sense: Said of a person, "sneering" usually means openly scornful or contemptuous in manner, not a habit of assuming bad motives in everyone. The gloss describes a distrustful, dismissive outlook, which only partly overlaps with scorn. -> cynical |
| 45 | spineless | duplicate between them | not_fit (secondary_sense) | secondary_sense, secondary_sense | unresentful | secondary_sense: Said of a person, 'spineless' usually means cowardly or lacking the courage to stand up for oneself. That overlaps with meekly swallowing insults, but the gloss is about failing to feel or show anger when it is warranted, which is a narrower trait than general cowardice or weakness. -> unresentful / secondary_sense: Said of a person, 'spineless' usually means cowardly or lacking the resolve to stand up for oneself, which overlaps with meekly taking insults. But the gloss is specifically about not feeling or showing anger when it is warranted, and the bare label would more likely be read as general cowardice or weak will. -> unresentful |

## The cosine pre-screen (reported only)

```json
{
 "n_with_cosine": 50,
 "median_cos_usual": {
  "should_not_fit": 0.44,
  "should_fit": 0.572
 },
 "median_cos_max": {
  "should_not_fit": 0.534,
  "should_fit": 0.607
 },
 "floors": [
  {
   "floor": 0.5,
   "settled_without_call": 35,
   "of_them_marked_odd": 4
  },
  {
   "floor": 0.6,
   "settled_without_call": 20,
   "of_them_marked_odd": 2
  },
  {
   "floor": 0.7,
   "settled_without_call": 2,
   "of_them_marked_odd": 0
  },
  {
   "floor": 0.8,
   "settled_without_call": 0,
   "of_them_marked_odd": 0
  }
 ]
}
```

## Every row

| # | label | Roger | decision | votes | proposals | cos usual | cos max |
| --- | --- | --- | --- | --- | --- | ---: | ---: |
| 1 | Blindly hopeful | duplicate of eithe bold or optimistic | fits | fits, fits, fits |  | 0.631544 | 0.631544 |
| 2 | brazen | trait (might be a duplicate, but not of the listed three) | fits | fits, fits, fits |  | 0.621903 | 0.621903 |
| 3 | Comfort-seeking | trait | relabel | secondary_sense, secondary_sense, secondary_sense | clingy | 0.462539 | 0.673517 |
| 4 | complacent | ? gloss of complacent seens incorrect (or I'm unfamiliar with that sense of the wordd) | relabel | not_a_sense, not_a_sense | unambitious | 0.293897 | 0.335843 |
| 5 | compliant | duplicate, between obedient and rule-abiding | fits | fits, fits, fits |  | 0.641679 | 0.641679 |
| 6 | conflict averse | duplicate, of all three! | fits | fits, fits, fits |  | 0.688065 | 0.688065 |
| 7 | evasive | trait | fits | fits, fits, fits |  | 0.54478 | 0.54478 |
| 8 | fearless | duplicate of brave or bold | fits | fits, fits, fits |  | 0.498789 | 0.532469 |
| 9 | flashy | ? borderline | relabel | secondary_sense, secondary_sense, secondary_sense | ostentatious | 0.545861 | 0.691254 |
| 10 | grasping | ? seems like an odd sense of "grasping" | relabel | not_a_sense, not_a_sense, not_a_sense | glory-hungry | 0.430894 | 0.512096 |
| 11 | headstrong | duplicate (of independent, taken to vice levels) | relabel | not_a_sense, not_a_sense, secondary_sense | inconsiderate | 0.476907 | 0.476907 |
| 12 | honor-hungry | trait | relabel | secondary_sense, secondary_sense | vainglorious, glory-seeking | 0.680412 | 0.680412 |
| 13 | ill-timed | trait | relabel | not_a_sense, not_a_sense, not_a_sense | bad at timing, poor sense of timing, has bad timing | 0.54107 | 0.54107 |
| 14 | inhibited | trait | fits | fits, fits, fits |  | 0.334601 | 0.609695 |
| 15 | insincere | duplicate, possibly of dishonest | fits | fits, fits, fits |  | 0.528271 | 0.528271 |
| 16 | irritating | triat (the "without intending real harm" part makes it different) | fits | fits, fits, fits |  | 0.589411 | 0.589411 |
| 17 | judicious | duplicate (of one-or-more of those) | fits | fits, fits, fits |  | 0.442355 | 0.634756 |
| 18 | justly proud | trait | fits | fits, fits, fits |  | 0.553211 | 0.553211 |
| 19 | know-it-all | duplicate | fits | fits, fits, fits |  | 0.578848 | 0.578848 |
| 20 | lecherous | duplicate | fits | fits, fits, fits |  | 0.675068 | 0.675068 |
| 21 | loquacious | duplicate | fits | fits, fits, fits |  | 0.505022 | 0.505022 |
| 22 | Low-libido | duplicate | fits | fits, fits, fits |  | 0.751157 | 0.751157 |
| 23 | nitpicking | duplicate | fits | fits, fits, fits |  | 0.612313 | 0.612313 |
| 24 | obsequious | duplicate | fits | fits, fits, fits |  | 0.658466 | 0.658466 |
| 25 | opportunistic | ? seems like an odd sense of the word. The definition is "beureucratically opportunistic" | fits | fits, fits, fits |  | 0.554581 | 0.578761 |
| 26 | Peaceable | duplicate | fits | fits, fits, fits |  | 0.564101 | 0.574014 |
| 27 | power-hungry | duplicate | fits | fits, fits, fits |  | 0.557291 | 0.557291 |
| 28 | rule-flouting | duplicate | fits | fits, fits, fits |  | 0.550672 | 0.550672 |
| 29 | ruminative | ? seems like an odd sense of the word | None |  |  | 0.347708 | 0.360131 |
| 30 | sanctimonious | ? seems like an od sense of the word | fits | fits, fits, fits |  | 0.628281 | 0.628281 |
| 31 | self-assertive | duplicate, (but not of anything in the list you offered) | relabel | secondary_sense, secondary_sense, not_a_sense | defensive | 0.337071 | 0.449463 |
| 32 | self-controlled | trait, or possibly a duplicate for something you didn't offer | relabel | secondary_sense, secondary_sense, secondary_sense | temperate | 0.459747 | 0.459747 |
| 33 | Self-directed | ? slightlu odd sense of the word | relabel | secondary_sense, secondary_sense, secondary_sense | freedom-loving, independent-minded | 0.439604 | 0.534071 |
| 34 | self-disparaging | duplicate od self-depracating or self-critical | fits | fits, fits, fits |  | 0.657752 | 0.657752 |
| 35 | self-justifying | ? close to blame-shifting, but not identical | fits | fits, fits, fits |  | 0.621225 | 0.621225 |
| 36 | self serving | duplicate of selfish | fits | fits, fits, fits |  | 0.543548 | 0.561698 |
| 37 | sensible | duplicate of one of those | fits | fits, fits, fits |  | 0.572353 | 0.578526 |
| 38 | sensual | duplicate of hedonistic | fits | fits, fits, fits |  | 0.603632 | 0.603632 |
| 39 | Sexually restrained | duplicate of chaste | fits | fits, fits, fits |  | 0.67304 | 0.67304 |
| 40 | Shunning | trait | relabel | secondary_sense, secondary_sense, secondary_sense | ostracizing, exclusionary | 0.428925 | 0.5861 |
| 41 | slanderous | subset of deceitful, i'd say not covered as it's rather more specific | fits | fits, fits, fits |  | 0.730167 | 0.730167 |
| 42 | smug | ? odd sense of smug | relabel | not_a_sense, not_a_sense, not_a_sense | pontificating | 0.33228 | 0.479032 |
| 43 | sneering | trait | relabel | not_a_sense, not_a_sense, secondary_sense | cynical | 0.380976 | 0.380976 |
| 44 | Soft on wrongdoing | duplicate between lenient and forgiving | fits | fits, fits, fits |  | 0.606539 | 0.606539 |
| 45 | spineless | duplicate between them | relabel | secondary_sense, secondary_sense | unresentful | 0.382412 | 0.462689 |
| 46 | timid with money | duplicate | fits | fits, fits, fits |  | 0.635203 | 0.635203 |
| 47 | two faced | duplicate | fits | fits, fits, fits |  | 0.541618 | 0.700455 |
| 48 | tyrannical | duplicate of those o others | fits | fits, fits, fits |  | 0.611628 | 0.611628 |
| 49 | uncouth | duplicate | fits | fits, fits, fits |  | 0.670023 | 0.670023 |
| 50 | undignified | trait, or at least, not a duplicste of the listed | fits | fits, fits, fits |  | 0.671556 | 0.671556 |
