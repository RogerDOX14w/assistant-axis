# Label-fit survey: readout (2026-10-17)

Roger marked all 222 rows of [roger_marks.md](./roger_marks.md) blind to the check, in two parts.
- **Part 1** asks whether a generator's name fits the concept it wrote.
- **Part 2** asks whether the word fits M1's gloss on the review card.

Generators are in [sheet_key.json](./sheet_key.json). The check's answers are in [named/label_fit](./named/label_fit/decisions.json) and [card/label_fit](./card/label_fit/decisions.json), Haiku 5.5 with three readings and a majority, $0.50. The rubric is [label_fit.md](../../../../reports/trait_gap_generation/rubrics/label_fit.md). "Problem" means a mark of S (secondary sense) or N (not a sense); "?" rows are left out of the rates.

## Problem rates by Roger's marks

| part | generator | marked | Y | S | N | ? | problem share |
|---|---|---|---|---|---|---|---|
| 1, the name for the concept | alignment sweep | 30 | 21 | 3 | 2 | 4 | 19% |
| | states pass | 30 | 26 | 3 | 1 | 0 | 13% |
| | IPIP | 30 | 27 | 1 | 1 | 1 | 7% |
| | (structural pilot, for comparison: Roger's 50 marks of 2026-10-15) | 50 | | | | | 18% |
| 2, the word on the card | 11 generators, 12 rows each | 132 | 127 | 5 | 0 | 1 | 4% |

On the card the word almost always matches M1's gloss. Five rows are secondary senses, one each from the alignment sweep, the base model, the masked LM, the noun relabel and Roget: *fussy about disruptions*, *revolutionary*, *wolf*, *manly* and *sinister*.

Composed names are where the problems are. The alignment sweep, at 19%, is as bad as the structural pilot was before its v2 prompts.

## The check against Roger

| part | Roger Y, check fits | Roger Y, check flags | Roger S/N, check fits | Roger S/N, check flags |
|---|---|---|---|---|
| 1 | 63 | 11 | 9 | 2 |
| 2 | 112 | 14 | 4 | 1 |

The check catches 3 of the 16 problems (19%) and flags 25 of the 189 rows Roger passed (13%). Only 3 of its 28 flags were right. On the structural pilot it caught 6 of 9, so as written it does not carry over to these generators. Rubric iteration has about 25 positives to work with (these 16 plus the structural 9). That is thin: a held-out test set would contain only about eight.

## Themes in Roger's notes

1. **The alignment sweep frames its traits for an AI or a software engineer.**
   - **What Roger noted:** 16 of the 30 Part 1 rows carry a note such as "(of an AI)", "AI framing", "chatbot framing" or "of a coder". The labels use "its" ("acts against its developer", "stands by its judgment", "does its honest best"), and the glosses use "the user", "the lab that built it" and "instructions".
   - **Across all the sweep's rows:** 12% of the 836 generator glosses name a developer, lab, operator or training, and 19% "the user".
   - **Against the corpus:** its own alignment-region traits are written person-general ("one's", "a helpful being").
   - **The cause:** the extraction and rewrite rubrics ask for dispositions "in a persona, whether an assistant or a person" ([alignment_rewrite.md](../../../../reports/trait_gap_generation/rubrics/alignment_rewrite.md), [alignment_extract.md](../../../../reports/trait_gap_generation/rubrics/alignment_extract.md)).
2. **Glosses narrower than their labels.** A gloss is a list of specific examples, or one case of a broader trait. Seen in the alignment sweep (*balanced judgment*, *preserves intent*, *circumvents safeguards*, *plays along strategically*), IPIP (*attuned to emotional atmosphere*, *distrusts authority figures*) and the states pass (*protective*). The check never flags these.
3. **Labels in noun or gerund form,** from the states pass (*napper*, *grumbler*, *gaming the system*) and the alignment sweep (*splitting the difference*). Roger: "should be 'games the system'".
4. **A label that names the sense badly.** For example *clear-headed* (usually "not emotional or not drunk") and *loser* (wider than contests).

## What follows (for Roger's decisions in chat)

- The alignment sweep needs new rubrics and a rerun (Roger, 2026-10-17); its decisions are open in chat.
- The label-fit check stays off the review card for now. Card problems are rare (4%), and the check misses most of them.
- Theme 2, glosses narrower than labels, may deserve its own verdict in any rubric iteration, since Roger marks it as a problem and the check has no category for it.
