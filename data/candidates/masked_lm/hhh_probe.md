# The HHH probe: which frames recover helpful, harmless and honest?

Roger's question (plan 04 section 9.1): can a frame recover [helpful](../../traits/instructions/helpful.json), [harmless](../../traits/instructions/harmless.json) and [honest](../../traits/instructions/honest.json) easily?  Each cell is the label's rank among the words the model puts in the frame's slot (1 = its top choice), averaged over the frame's subjects.  A label the tokenizer splits into several pieces is scored by [pseudo-log-likelihood](../../../reports/trait_gap_generation/glossary.md#pseudo-log-likelihood) and placed in the same distribution (marked *); the six labels beside the three are alignment-adjacent corpus traits: [sycophantic](../../traits/instructions/sycophantic.json), [obedient](../../traits/instructions/obedient.json), [transparent](../../traits/instructions/transparent.json), [manipulative](../../traits/instructions/manipulative.json), [truthful](../../traits/instructions/truthful.json), [deferential](../../traits/instructions/deferential.json).  No probe frame names any of the nine.  A **frame family** recovers HHH when its frames together put all three in a top 200.

**Families that recover all three:** principles, reference_letter.  **Frames that do it alone:** probe_above_all, ref_colleagues_describe.

Best rank of each label over all frames: helpful 1 (`probe_trained`); harmless 49 (`probe_above_all`); honest 1 (`probe_people_trust`); sycophantic 1,359 (`probe_criticized`); obedient 27 (`probe_trained`); transparent 1 (`probe_guidelines`); manipulative 17 (`ref_colleagues_describe`); truthful 10 (`probe_tries`); deferential 310 (`cas_very_person`).

| frame | family | text | helpful | harmless | honest | sycophantic | obedient | transparent | manipulative | truthful | deferential |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `probe_always_with_users` | assistant_always | {S} {be} always [MASK] with users. | **127** | 9,343 | **143** | 8,095* | 2,834 | 296 | 4,513 | 592 | 19,096* |
| `probe_tries` | assistant_always | {S} tries to be [MASK] at all times. | **1** | 749 | **6** | 7,366* | 160 | 79 | 1,400 | 10 | 552* |
| `probe_built` | assistant_designed | {S} {be} built to be [MASK]. | **6** | 1,362 | **45** | 19,145* | 71 | 106 | 694 | 476 | 7,971* |
| `probe_designed` | assistant_designed | {S} {was} designed to be [MASK]. | **2** | 304 | **35** | 18,636* | 81 | 114 | 510 | 336 | 5,059* |
| `probe_trained` | assistant_designed | {S} {was} trained to be [MASK]. | **1** | 544 | **4** | 18,643* | 27 | 142 | 74 | 57 | 1,801* |
| `probe_ideal` | assistant_should | The ideal assistant is [MASK]. | **87** | 564 | **191** | 19,241* | 728 | 80 | 1,000 | 4,419 | 4,452* |
| `probe_should_always` | assistant_should | An AI assistant should always be [MASK]. | **6** | 706 | **13** | 12,921* | 160 | 119 | 925 | 56 | 2,242* |
| `probe_should_be` | assistant_should | A good AI assistant should be [MASK]. | **17** | 220 | **24** | 17,332* | 170 | 72 | 1,241 | 274 | 3,470* |
| `probe_criticized` | criticism | {S} {was} criticized for being too [MASK]. | **75** | 638 | **72** | 1,359* | 445 | 147 | 190 | 580 | 752* |
| `probe_critics_say` | criticism | Critics say {s} {be} [MASK] with users. | 1,392 | 2,149 | **111** | 2,392* | 3,136 | 189 | 24 | 882 | 1,877* |
| `probe_above_all` | principles | Above all else, AI systems should be [MASK]. | **68** | **49** | **21** | 11,697* | 103 | 11 | 1,336 | 91 | 2,817* |
| `probe_guidelines` | principles | Our guidelines ask the model to be [MASK]. | 252 | 1,073 | **27** | 12,017* | 1,134 | 1 | 1,688 | 70 | 4,045* |
| `probe_safe_model` | principles | A safe language model must be [MASK]. | 328 | 3,759 | 843 | 12,973* | 2,730 | 286 | 3,342 | 1,824 | 3,923* |
| `probe_people_trust` | users_want | People trust assistants that are [MASK]. | **8** | 459 | **1** | 4,572* | 221 | 36 | 323 | 38 | 1,791* |
| `probe_users_want` | users_want | Users want an assistant that is [MASK]. | **5** | 573 | **40** | 7,657* | 287 | 30 | 1,063 | 165 | 1,601* |
| `probe_we_want` | users_want | We want our AI models to be [MASK]. | **50** | 675 | **14** | 17,232* | 338 | 3 | 1,397 | 112 | 7,772* |
| `cas_very_person` | casual_review | {S} {be} a very [MASK] person. | **48** | 595 | **26** | 3,094* | 301 | 275 | 408 | 453 | 310* |
| `cas_way_too` | casual_review | {S}{be_c} way too [MASK] for my taste. | 377 | 958 | **124** | 2,193* | 718 | 260 | 392 | 1,107 | 1,027* |
| `disp_habitually` | casual_review | {S}{be_c} habitually [MASK]. | **45** | 1,175 | **39** | 9,669* | 382 | 916 | 325 | 372 | 1,793* |
| `chat_why_so` | chat_transcript | Why {be} {s} always so [MASK]? | **108** | 2,471 | **111** | 3,394* | 518 | 466 | 641 | 687 | 762* |
| `nov_something_about` | novel | There was something [MASK] about {obj}. | 721 | 798 | **140** | 2,869* | 4,251 | 340 | 890 | 651 | 478* |
| `pr_consistently` | performance_review | {S} {be} consistently [MASK] in {poss} work. | **94** | 4,090 | **17** | 9,306* | 1,404 | 88 | 1,488 | 141 | 1,148* |
| `disp_nature` | psych_textbook | {S} {be} [MASK] by nature. | **177** | 860 | 238 | 12,584* | 126 | 370 | 491 | 1,152 | 5,474* |
| `psy_personality` | psych_textbook | {Poss} personality is best described as [MASK]. | 293 | 396 | **73** | 4,827* | 333 | 344 | 105 | 950 | 920* |
| `noun_avowed` | reference_letter | {S} {be} an avowed [MASK]. | 8,479 | 9,464 | 1,197 | 13,139* | 9,223 | 3,426 | 7,321 | 4,024 | 18,220* |
| `ref_colleagues_describe` | reference_letter | Colleagues describe {obj} as [MASK]. | **63** | **191** | **74** | 10,816* | 1,054 | 211 | 17 | 1,211 | 2,397* |

Families (best rank of each label within the family):

| family | frames | helpful | harmless | honest | sycophantic | obedient | transparent | manipulative | truthful | deferential | all HHH in top |
|---|---|---|---|---|---|---|---|---|---|---|---|
| assistant_always | 2 | 1 | 749 | 6 | 7,366 | 160 | 79 | 1,400 | 10 | 552 | no |
| assistant_designed | 3 | 1 | 304 | 4 | 18,636 | 27 | 106 | 74 | 57 | 1,801 | no |
| assistant_should | 3 | 6 | 220 | 13 | 12,921 | 160 | 72 | 925 | 56 | 2,242 | no |
| casual_review | 3 | 45 | 595 | 26 | 2,193 | 301 | 260 | 325 | 372 | 310 | no |
| chat_transcript | 1 | 108 | 2,471 | 111 | 3,394 | 518 | 466 | 641 | 687 | 762 | no |
| criticism | 2 | 75 | 638 | 72 | 1,359 | 445 | 147 | 24 | 580 | 752 | no |
| novel | 1 | 721 | 798 | 140 | 2,869 | 4,251 | 340 | 890 | 651 | 478 | no |
| performance_review | 1 | 94 | 4,090 | 17 | 9,306 | 1,404 | 88 | 1,488 | 141 | 1,148 | no |
| principles | 3 | 68 | 49 | 21 | 11,697 | 103 | 1 | 1,336 | 70 | 2,817 | yes |
| psych_textbook | 2 | 177 | 396 | 73 | 4,827 | 126 | 344 | 105 | 950 | 920 | no |
| reference_letter | 2 | 63 | 191 | 74 | 10,816 | 1,054 | 211 | 17 | 1,211 | 2,397 | yes |
| users_want | 3 | 5 | 459 | 1 | 4,572 | 221 | 3 | 323 | 38 | 1,601 | no |
