# Label-fit check against Roger's marks: claude-haiku-5-5

The 50 rows of [roger_sample.md](../roger_sample.md) (a mark starting with `?` should not fit, any other mark should), asked of claude-haiku-5-5, 3 readings each, with [label_fit.md](../../../../../../reports/trait_gap_generation/rubrics/label_fit.md) version 1; spend on record (every model) $0.0349.  Responses: [responses.jsonl](responses.jsonl).

```text
all marked rows (n=50):
  Roger \ check           not fit     fits  no answer
  '?' (should not fit)          6        3          0
  other (should fit)           10       31          0
  flags: precision 0.375, recall 0.667; agreement 0.74
```

```text
without the borderline rows (flashy, self-justifying) (n=48):
  Roger \ check           not fit     fits  no answer
  '?' (should not fit)          5        2          0
  other (should fit)           10       31          0
  flags: precision 0.333, recall 0.714; agreement 0.75
```

## Disagreements

| # | label | Roger | check | votes | proposals | reasons |
| --- | --- | --- | --- | --- | --- | --- |
| 3 | Comfort-seeking | trait | not_fit (secondary_sense) | secondary_sense, secondary_sense, secondary_sense | dependent, needy | secondary_sense: Said of a person, 'comfort-seeking' usually means preferring ease and avoiding hardship, which is the first recorded sense. The gloss's sense of leaning on others for reassurance and being looked after is only the second sense. -> dependent / secondary_sense: Said of a person, 'comfort-seeking' usually means preferring ease and avoiding hardship, which is the first recorded sense. The gloss describes emotional dependence, wanting others to soothe and look after you, which is only the second sense. -> dependent / secondary_sense: Said of a person, 'comfort-seeking' usually means preferring ease and avoiding hardship, which the recorded senses rank first. The gloss describes constantly seeking emotional support and being looked after, a sense that comes second. -> needy |
| 11 | headstrong | duplicate (of independent, taken to vice levels) | not_fit (not_a_sense) | not_a_sense, secondary_sense, not_a_sense | inconsiderate | not_a_sense: Said of a person, "headstrong" means stubborn and resistant to advice or control, or rash. It does not carry the idea of disregarding others' wishes as if they did not matter. -> inconsiderate / secondary_sense: Said of a person, "headstrong" usually means stubborn or unwilling to be controlled, which is a different emphasis from the callous disregard for others' wishes the gloss describes. The label can carry that sense only as a secondary reading. -> inconsiderate / not_a_sense: Said of a person, 'headstrong' usually means obstinate and set on its own way, not thoughtlessly disregarding others. The gloss's idea of having no regard for others' wishes is not something the word carries. -> inconsiderate |
| 13 | ill-timed | trait | not_fit (secondary_sense) | secondary_sense, fits, secondary_sense | habitually picks bad moments, often mistimes things | secondary_sense: Said of a person, 'ill-timed' is mostly applied to a remark, visit or action that is badly timed, not to someone who habitually picks bad moments, so the trait sense is secondary. No single word clearly carries the habitual trait, so a short phrase is given. -> habitually picks bad moments / fits: Said of a person, 'ill-timed' most naturally means someone who tends to speak or act at inopportune moments, which is the trait the gloss describes. / secondary_sense: Said of a person, "ill-timed" mostly describes a single remark or action that was badly timed, not a lasting habit. The habitual sense is possible but secondary, so a bare label would likely be read as one bad moment. -> often mistimes things |
| 14 | inhibited | trait | not_fit (secondary_sense) | secondary_sense, secondary_sense, secondary_sense | repressed | secondary_sense: Said of a person, "inhibited" most often means shy or reserved in manner. The emotional-repression sense in the gloss is real but secondary, so most readers would take the bare label as shyness. -> repressed / secondary_sense: Said of a person, 'inhibited' most often means shy or reserved in manner, not the deep emotional suppression and self-denial the gloss describes. That sense appears only as a secondary one. -> repressed / secondary_sense: Said of a person, 'inhibited' most often means shy or self-conscious, not habitually suppressing feelings and denying oneself pleasure. The emotional-repression sense is real but comes second. -> repressed |
| 25 | opportunistic | ? seems like an odd sense of the word. The definition is "beureucratically opportunistic" | fit (fits) | fits, fits, fits |  | fits: Said of a person, 'opportunistic' most commonly means exploiting situations for personal gain without scruples, which is the trait the gloss describes. The gloss is narrower, focusing on officials and rules, but it is the same trait. / fits: Said of a person, 'opportunistic' most often means ready to exploit situations for personal gain without scruples, which is the trait the gloss describes. The gloss is narrower, focusing on bending to officials and rules, but it is still the same trait. / fits: Said of a person, 'opportunistic' most commonly means exploiting situations for one's own benefit without scruples, which is the trait the gloss describes: bending to whatever currently serves one best. The gloss is narrower, focusing on officials and rules, but it is the same trait. |
| 30 | sanctimonious | ? seems like an od sense of the word | fit (fits) | fits, fits, secondary_sense |  | fits: The gloss centres on moralizing while sure of one's own rectitude, which is the usual sense of 'sanctimonious' said of a person. The added bluntness and indifference to hurt are extra detail rather than a different trait. / fits: The gloss's core trait is self-righteous moralizing, sure of one's own virtue, and that is the usual sense of 'sanctimonious' said of a person. The gloss's added bluntness and indifference to hurt are extra detail rather than a different trait. / secondary_sense: Said of a person, "sanctimonious" usually means self-righteously moralizing or feigning virtue, which covers only part of the gloss. The gloss's core is blunt, hurtful truth-telling with indifference to the hurt, which the label does not convey. -> tactless |
| 31 | self-assertive | duplicate, (but not of anything in the list you offered) | not_fit (secondary_sense) | secondary_sense, secondary_sense, secondary_sense | obstinate, defensive | secondary_sense: Said of a person, "self-assertive" usually means confidently stating one's own views and needs, a fairly positive trait. The gloss describes stubborn refusal to yield or admit fault, which is a secondary and more negative reading. -> obstinate / secondary_sense: Said of a person, "self-assertive" usually means confidently stating one's own views and needs, not refusing to admit fault or resisting criticism. The gloss's sense is a secondary, more negative reading of the word. -> defensive / secondary_sense: Said of a person, "self-assertive" usually means confidently stating one's own views and needs, not refusing to yield or to admit fault. The gloss's stubborn refusal to accept correction is a secondary, more aggressive reading that most readers would not take from the bare label. -> obstinate |
| 32 | self-controlled | trait, or possibly a duplicate for something you didn't offer | not_fit (secondary_sense) | secondary_sense, secondary_sense, secondary_sense | temperate | secondary_sense: Said of a person, 'self-controlled' most often means restrained and not acting on impulse, which is broader than the gloss's specific moderation of bodily pleasures and appetite. 'Temperate' is the word whose usual personal sense is moderation in appetites, especially food and drink. -> temperate / secondary_sense: Said of a person, 'self-controlled' usually means restrained and calm in general, not specifically moderate enjoyment of bodily pleasures, though that sense can be carried. 'Temperate' is said of people most often for moderation in eating, drinking and other appetites. -> temperate / secondary_sense: "Self-controlled" usually means calm and not acting on impulse in general, not moderation in bodily pleasures and appetites, which is the trait the gloss describes. "Temperate" is the word that most readily means moderate in eating, drinking and other pleasures. -> temperate |
| 35 | self-justifying | ? close to blame-shifting, but not identical | fit (fits) | fits, fits, fits |  | fits: Said of a person, "self-justifying" usually means habitually defending or excusing one's own conduct, which is the trait the gloss describes: quick self-defence when blamed, guarding against any hint of fault, and bristling at challenge. / fits: Said of a person, "self-justifying" usually means habitually defending or excusing one's own conduct, which is the trait the gloss describes: quick self-defense when criticized and bristling at challenge. / fits: Said of a person, "self-justifying" usually means habitually defending or excusing one's own conduct, which is the defensive reaction to criticism the gloss describes, including the bristling at challenge. |
| 38 | sensual | duplicate of hedonistic | not_fit (secondary_sense) | fits, secondary_sense, secondary_sense | hedonistic, sensory hedonist | fits: The label's usual sense said of a person is being devoted to bodily pleasures and sensory experience, which matches the gloss's active pursuit of taste, touch, sound and beauty. Its sexual overtone is a secondary connotation the gloss does not require. / secondary_sense: Said of a person, "sensual" most often suggests sexual appeal or lustfulness, which is narrower and more charged than the gloss's general savoring of taste, touch, sound and beauty. The gloss's sense is real but secondary in everyday use. -> hedonistic / secondary_sense: The recorded usual sense matches the gloss, but said of a person the bare word 'sensual' most often suggests sexual appeal or lust, which the gloss does not mention. The gloss covers taste, sound and beauty too, so most readers would take the word otherwise. -> sensory hedonist |
| 40 | Shunning | trait | not_fit (secondary_sense) | secondary_sense, secondary_sense, secondary_sense | cliquish, ostracizing | secondary_sense: Said of a person, 'shunning' usually means keeping others at a distance or avoiding them, which is milder than the gloss's active cutting off, snubbing and expelling of people they dislike. 'Cliquish' more often describes someone who shuts outsiders out of their group. -> cliquish / secondary_sense: Said of a person, 'shunning' most often means keeping others at a distance or avoiding them, which is milder than the gloss's deliberate, hostile exclusion of people they dislike. The exclusion sense is real but secondary. -> cliquish / secondary_sense: Said of a person, 'shunning' most often means keeping others at a distance or avoiding them, not the active, deliberate cutting-off and snubbing of disliked people that the gloss describes. 'Ostracizing' names that active exclusion directly. -> ostracizing |
| 43 | sneering | trait | not_fit (not_a_sense) | not_a_sense, not_a_sense, not_a_sense | cynical | not_a_sense: Said of a person, 'sneering' describes a manner of contempt or a mocking expression, not a settled habit of distrusting others' motives. The gloss's sense of assuming bad motives in everyone is not something the bare label carries. -> cynical / not_a_sense: Said of a person, 'sneering' describes a scornful or mocking manner, not a settled habit of assuming bad motives and refusing to take people at face value. The gloss's core trait is cynicism about motives, which the label does not carry. -> cynical / not_a_sense: Said of a person, "sneering" means showing contempt in manner or expression. It does not mean habitually assuming bad motives and distrusting everyone's sincerity, which is the trait the gloss describes. -> cynical |
| 45 | spineless | duplicate between them | not_fit (secondary_sense) | secondary_sense, secondary_sense, fits | meek | secondary_sense: Said of a person, 'spineless' usually means cowardly or lacking courage, not the meek, passive acceptance of insults described in the gloss. That passive sense is only a secondary one, so most readers would take it differently. -> meek / secondary_sense: Said of a person, 'spineless' usually means cowardly or weak-willed, so a reader would hear general timidity rather than specifically failing to answer insults with anger. The gloss's trait of meekly accepting provocation is a narrower behaviour that the label only loosely covers. -> meek / fits: Said of a person, 'spineless' most commonly means lacking courage or resolve and being easily pushed around, which covers meekly taking insults without standing up for oneself. The gloss is narrower, focusing on not responding with anger, but it describes the same lack of backbone. |

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
| 3 | Comfort-seeking | trait | relabel | secondary_sense, secondary_sense, secondary_sense | dependent, needy | 0.462539 | 0.673517 |
| 4 | complacent | ? gloss of complacent seens incorrect (or I'm unfamiliar with that sense of the wordd) | relabel | not_a_sense, not_a_sense, not_a_sense | self-effacing | 0.293897 | 0.335843 |
| 5 | compliant | duplicate, between obedient and rule-abiding | fits | fits, fits, fits |  | 0.641679 | 0.641679 |
| 6 | conflict averse | duplicate, of all three! | fits | fits, fits, fits |  | 0.688065 | 0.688065 |
| 7 | evasive | trait | fits | fits, fits, fits |  | 0.54478 | 0.54478 |
| 8 | fearless | duplicate of brave or bold | fits | fits, fits, fits |  | 0.498789 | 0.532469 |
| 9 | flashy | ? borderline | relabel | fits, secondary_sense, secondary_sense | ostentatious | 0.545861 | 0.691254 |
| 10 | grasping | ? seems like an odd sense of "grasping" | relabel | secondary_sense, secondary_sense, secondary_sense | honor-hungry, glory-hungry | 0.430894 | 0.512096 |
| 11 | headstrong | duplicate (of independent, taken to vice levels) | relabel | not_a_sense, secondary_sense, not_a_sense | inconsiderate | 0.476907 | 0.476907 |
| 12 | honor-hungry | trait | fits | fits, fits, fits |  | 0.680412 | 0.680412 |
| 13 | ill-timed | trait | relabel | secondary_sense, fits, secondary_sense | habitually picks bad moments, often mistimes things | 0.54107 | 0.54107 |
| 14 | inhibited | trait | relabel | secondary_sense, secondary_sense, secondary_sense | repressed | 0.334601 | 0.609695 |
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
| 29 | ruminative | ? seems like an odd sense of the word | relabel | secondary_sense, secondary_sense, secondary_sense | reads hidden motives, reads every gesture obsessively | 0.347708 | 0.360131 |
| 30 | sanctimonious | ? seems like an od sense of the word | fits | fits, fits, secondary_sense |  | 0.628281 | 0.628281 |
| 31 | self-assertive | duplicate, (but not of anything in the list you offered) | relabel | secondary_sense, secondary_sense, secondary_sense | obstinate, defensive | 0.337071 | 0.449463 |
| 32 | self-controlled | trait, or possibly a duplicate for something you didn't offer | relabel | secondary_sense, secondary_sense, secondary_sense | temperate | 0.459747 | 0.459747 |
| 33 | Self-directed | ? slightlu odd sense of the word | relabel | secondary_sense, secondary_sense, secondary_sense | Autonomous, freedom-loving, independent-minded | 0.439604 | 0.534071 |
| 34 | self-disparaging | duplicate od self-depracating or self-critical | fits | fits, fits, fits |  | 0.657752 | 0.657752 |
| 35 | self-justifying | ? close to blame-shifting, but not identical | fits | fits, fits, fits |  | 0.621225 | 0.621225 |
| 36 | self serving | duplicate of selfish | fits | fits, fits, fits |  | 0.543548 | 0.561698 |
| 37 | sensible | duplicate of one of those | fits | fits, fits, fits |  | 0.572353 | 0.578526 |
| 38 | sensual | duplicate of hedonistic | relabel | fits, secondary_sense, secondary_sense | hedonistic, sensory hedonist | 0.603632 | 0.603632 |
| 39 | Sexually restrained | duplicate of chaste | fits | fits, fits, fits |  | 0.67304 | 0.67304 |
| 40 | Shunning | trait | relabel | secondary_sense, secondary_sense, secondary_sense | cliquish, ostracizing | 0.428925 | 0.5861 |
| 41 | slanderous | subset of deceitful, i'd say not covered as it's rather more specific | fits | fits, fits, fits |  | 0.730167 | 0.730167 |
| 42 | smug | ? odd sense of smug | relabel | secondary_sense, secondary_sense, secondary_sense | know-it-all | 0.33228 | 0.479032 |
| 43 | sneering | trait | relabel | not_a_sense, not_a_sense, not_a_sense | cynical | 0.380976 | 0.380976 |
| 44 | Soft on wrongdoing | duplicate between lenient and forgiving | fits | fits, fits, fits |  | 0.606539 | 0.606539 |
| 45 | spineless | duplicate between them | relabel | secondary_sense, secondary_sense, fits | meek | 0.382412 | 0.462689 |
| 46 | timid with money | duplicate | fits | fits, fits, fits |  | 0.635203 | 0.635203 |
| 47 | two faced | duplicate | fits | fits, fits, fits |  | 0.541618 | 0.700455 |
| 48 | tyrannical | duplicate of those o others | fits | fits, fits, fits |  | 0.611628 | 0.611628 |
| 49 | uncouth | duplicate | fits | fits, fits, fits |  | 0.670023 | 0.670023 |
| 50 | undignified | trait, or at least, not a duplicste of the listed | fits | fits, fits, fits |  | 0.671556 | 0.671556 |
