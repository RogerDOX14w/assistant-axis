# The HHH probe: which frames recover helpful, harmless and honest?

Roger's question (plan 04 section 9.1): can a frame recover [helpful](../../traits/instructions/helpful.json), [harmless](../../traits/instructions/harmless.json) and [honest](../../traits/instructions/honest.json) easily?  Each cell is the label's rank among the words the model puts in the frame's slot (1 = its top choice), averaged over the frame's subjects.  A label the tokenizer splits into several pieces is scored by [pseudo-log-likelihood](../../../reports/trait_gap_generation/glossary.md#pseudo-log-likelihood) and placed in the same distribution (marked *); the six labels beside the three are alignment-adjacent corpus traits: [sycophantic](../../traits/instructions/sycophantic.json), [obedient](../../traits/instructions/obedient.json), [transparent](../../traits/instructions/transparent.json), [manipulative](../../traits/instructions/manipulative.json), [truthful](../../traits/instructions/truthful.json), [deferential](../../traits/instructions/deferential.json).  No probe frame names any of the nine.  A **frame family** recovers HHH when its frames together put all three in a top 200.

**Families that recover all three:** casual_review, novel, principles, psych_textbook, reference_letter.  **Frames that do it alone:** disp_comes_across, probe_above_all, ref_above_all, ref_colleagues_describe.

Best rank of each label over all frames: helpful 1 (`probe_trained`); harmless 41 (`cas_pretty_once`); honest 1 (`probe_people_trust`); sycophantic 1,046 (`psy_temperament`); obedient 27 (`probe_trained`); transparent 1 (`probe_guidelines`); manipulative 17 (`ref_colleagues_describe`); truthful 10 (`probe_tries`); deferential 43 (`pr_attitude`).

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
| `cas_honestly_so` | casual_review | Honestly, {s} {be} so [MASK]. | **31** | 283 | **163** | 2,533* | 1,170 | 254 | 461 | 1,597 | 2,233* |
| `cas_hopeless` | casual_review | {S}{be_c} a hopeless [MASK]. | 14,437 | 11,500 | 4,286 | 8,110* | 18,332 | 6,289 | 8,169 | 12,430 | 14,130* |
| `cas_most_people` | casual_review | {S} {be} one of the most [MASK] people I know. | **40** | 714 | **7** | 2,497* | 342 | 244 | 360 | 337 | 330* |
| `cas_pretty_once` | casual_review | {S}{be_c} pretty [MASK] once you get to know {obj}. | **93** | **41** | 211 | 3,077* | 1,040 | 136 | 664 | 1,634 | 1,041* |
| `cas_super` | casual_review | {S}{be_c} super [MASK] and I love it. | **21** | 1,412 | **41** | 8,755* | 972 | 238 | 714 | 1,470 | 4,740* |
| `cas_very_person` | casual_review | {S} {be} a very [MASK] person. | **48** | 595 | **26** | 3,094* | 301 | 275 | 408 | 453 | 310* |
| `cas_way_too` | casual_review | {S}{be_c} way too [MASK] for my taste. | 377 | 958 | **124** | 2,193* | 718 | 260 | 392 | 1,107 | 1,027* |
| `disp_comes_across` | casual_review | {S} come{vs} across as [MASK]. | **103** | **68** | **19** | 4,956* | 436 | 223 | 30 | 260 | 1,194* |
| `disp_everyone_agrees` | casual_review | Everyone agrees that {s} {be} [MASK]. | 310 | **78** | 207 | 10,778* | 3,732 | 370 | 228 | 1,153 | 4,418* |
| `disp_habitually` | casual_review | {S}{be_c} habitually [MASK]. | **45** | 1,175 | **39** | 9,669* | 382 | 916 | 325 | 372 | 1,793* |
| `noun_incurable` | casual_review | {S} {be} an incurable [MASK]. | 13,919 | 8,364 | 5,573 | 1,624* | 12,869 | 7,602 | 7,387 | 12,699 | 14,269* |
| `noun_through_and_through` | casual_review | {S} {be} a real [MASK] through and through. | 7,588 | 12,372 | 1,802 | 15,053* | 8,640 | 6,422 | 8,995 | 8,571 | 16,924* |
| `chat_lol_so` | chat_transcript | lol {s}{be_c} so [MASK] | **105** | 470 | **170** | 6,593* | 1,710 | 281 | 395 | 2,028 | 16,655* |
| `chat_never_met` | chat_transcript | I have never met anyone as [MASK] as {obj}. | 223 | 450 | **15** | 3,307* | 571 | 329 | 555 | 275 | 495* |
| `chat_stop_being` | chat_transcript | Can {s} stop being so [MASK] for once? | **92** | 1,088 | **186** | 2,076* | 1,018 | 206 | 149 | 984 | 803* |
| `chat_tbh` | chat_transcript | tbh {s} {be} kind of [MASK] sometimes | **191** | 610 | 656 | 3,026* | 5,162 | 352 | 199 | 3,986 | 3,432* |
| `chat_typical` | chat_transcript | That is such a typically [MASK] thing for {obj} to say. | **130** | 251 | **57** | 2,455* | 3,010 | 506 | 256 | 518 | 583* |
| `chat_why_so` | chat_transcript | Why {be} {s} always so [MASK]? | **108** | 2,471 | **111** | 3,394* | 518 | 466 | 641 | 687 | 762* |
| `noun_self_described` | chat_transcript | {S} {be} a self-described [MASK]. | 3,299 | 3,221 | 1,155 | 13,481* | 6,010 | 3,180 | 3,879 | 5,488 | 20,844* |
| `disp_always` | novel | {S} {have} always been [MASK]. | **43** | 1,527 | **24** | 14,074* | 583 | 403 | 618 | 283 | 4,449* |
| `disp_at_heart` | novel | At heart, {s} {be} [MASK]. | 691 | **156** | **21** | 15,147* | 397 | 285 | 1,145 | 649 | 4,837* |
| `disp_deep_down` | novel | Deep down, {s} {be} [MASK]. | 960 | 235 | **87** | 11,495* | 488 | 573 | 1,022 | 404 | 2,954* |
| `disp_rarely_anything_but` | novel | {S} {be} rarely anything but [MASK]. | **9** | 656 | **2** | 10,373* | 247 | 264 | 636 | 16 | 1,335* |
| `noun_confirmed` | novel | {S} {be} a confirmed [MASK]. | 9,461 | 9,642 | 3,604 | 12,949* | 11,297 | 3,925 | 7,770 | 9,695 | 20,573* |
| `noun_lifelong` | novel | {S} {have} been a lifelong [MASK]. | 5,881 | 15,686 | 4,059 | 19,865* | 6,978 | 9,221 | 13,007 | 9,088 | 19,548* |
| `nov_born` | novel | {S} {was} a born [MASK]. | 5,793 | 9,078 | 927 | 16,501* | 1,760 | 6,119 | 3,709 | 4,919 | 20,765* |
| `nov_deeply_individual` | novel | {S} {was} a deeply [MASK] individual. | 437 | 1,258 | **107** | 4,870* | 997 | 900 | 210 | 525 | 399* |
| `nov_grew_more` | novel | Over the years {s} grew more [MASK]. | 384 | 1,592 | 727 | 9,022* | 413 | 266 | 445 | 1,708 | 323* |
| `nov_had_always` | novel | {S} had always been [MASK], even as a child. | **52** | 1,469 | **55** | 8,831* | 97 | 712 | 225 | 300 | 2,002* |
| `nov_people_said` | novel | People said {s} {was} [MASK]. | 224 | **102** | **189** | 6,271* | 1,266 | 388 | 124 | 1,040 | 5,815* |
| `nov_something_about` | novel | There was something [MASK] about {obj}. | 721 | 798 | **140** | 2,869* | 4,251 | 340 | 890 | 651 | 478* |
| `nov_true_at_heart` | novel | {S} {was} a true [MASK] at heart. | 7,386 | 6,004 | 864 | 11,034* | 5,837 | 6,418 | 11,061 | 4,308 | 16,955* |
| `pr_attitude` | performance_review | {S} {have} a consistently [MASK] attitude. | **53** | 1,411 | **97** | 1,556* | 880 | 593 | 482 | 842 | 43* |
| `pr_consistently` | performance_review | {S} {be} consistently [MASK] in {poss} work. | **94** | 4,090 | **17** | 9,306* | 1,404 | 88 | 1,488 | 141 | 1,148* |
| `pr_exceptionally_employee` | performance_review | {S} {be} an exceptionally [MASK] employee. | **19** | 1,338 | **20** | 2,504* | 122 | 222 | 687 | 439 | 436* |
| `pr_natural` | performance_review | {S} {be} a natural [MASK]. | 5,596 | 10,024 | 2,592 | 18,348* | 4,147 | 5,942 | 4,657 | 10,134 | 18,921* |
| `pr_needs_less` | performance_review | {S} need{vs} to be less [MASK]. | 225 | 2,015 | 290 | 4,242* | 495 | 190 | 77 | 997 | 223* |
| `pr_rated` | performance_review | Team members rated {obj} as highly [MASK]. | **3** | 3,310 | **73** | 8,470* | 329 | 359 | 546 | 1,148 | 960* |
| `pr_should_more` | performance_review | {S} should try to be more [MASK]. | **5** | 1,329 | **6** | 7,615* | 277 | 33 | 796 | 58 | 391* |
| `disp_by_temperament` | psych_textbook | By temperament, {s} {be} [MASK]. | 523 | 313 | 344 | 15,813* | 976 | 671 | 848 | 3,859 | 2,859* |
| `disp_fundamentally` | psych_textbook | {S} {be} fundamentally [MASK]. | 395 | 266 | **19** | 14,686* | 1,606 | 169 | 382 | 585 | 5,754* |
| `disp_nature` | psych_textbook | {S} {be} [MASK] by nature. | **177** | 860 | 238 | 12,584* | 126 | 370 | 491 | 1,152 | 5,474* |
| `disp_tends` | psych_textbook | {S} tend{vs} to be [MASK]. | **23** | 724 | **19** | 7,084* | 335 | 345 | 447 | 372 | 2,086* |
| `noun_committed` | psych_textbook | {S} {be} a committed [MASK]. | 7,971 | 11,909 | 1,293 | 16,456* | 6,302 | 4,417 | 14,298 | 5,241 | 19,978* |
| `psy_classic` | psych_textbook | {S} {be} a classic [MASK] personality type. | 1,324 | 4,018 | 1,124 | 3,103* | 562 | 4,257 | 58 | 6,356 | 3,764* |
| `psy_disposition` | psych_textbook | {S} {have} a naturally [MASK] disposition. | **70** | 388 | **136** | 1,824* | 120 | 910 | 250 | 729 | 105* |
| `psy_personality` | psych_textbook | {Poss} personality is best described as [MASK]. | 293 | 396 | **73** | 4,827* | 333 | 344 | 105 | 950 | 920* |
| `psy_scores_high` | psych_textbook | On personality tests {s} score{vs} as highly [MASK]. | **76** | 1,086 | **50** | 4,198* | 47 | 524 | 56 | 394 | 684* |
| `psy_stable_part` | psych_textbook | Being [MASK] is a stable part of {poss} personality. | **46** | 1,502 | **18** | 13,496* | 34 | 183 | 483 | 108 | 2,038* |
| `psy_temperament` | psych_textbook | {S} {have} an essentially [MASK] temperament. | 1,214 | **179** | 202 | 1,046* | 142 | 1,076 | 759 | 1,493 | 337* |
| `disp_known_for` | reference_letter | {S} {be} known for being [MASK]. | **32** | 728 | **7** | 7,389* | 202 | 65 | 111 | 194 | 1,755* |
| `noun_avowed` | reference_letter | {S} {be} an avowed [MASK]. | 8,479 | 9,464 | 1,197 | 13,139* | 9,223 | 3,426 | 7,321 | 4,024 | 18,220* |
| `noun_dyed_in_wool` | reference_letter | {S} {be} a dyed-in-the-wool [MASK]. | 8,298 | 10,426 | 3,253 | 9,101* | 4,884 | 3,320 | 10,050 | 7,760 | 13,314* |
| `ref_above_all` | reference_letter | Above all, {s} {be} [MASK]. | **159** | **151** | **12** | 16,117* | 522 | 101 | 1,645 | 270 | 5,525* |
| `ref_colleagues_describe` | reference_letter | Colleagues describe {obj} as [MASK]. | **63** | **191** | **74** | 10,816* | 1,054 | 211 | 17 | 1,211 | 2,397* |
| `ref_genuinely_colleague` | reference_letter | {S} {be} a genuinely [MASK] colleague. | **2** | 368 | **23** | 3,689* | 425 | 504 | 990 | 696 | 435* |
| `ref_reliably` | reference_letter | In my experience, {s} {be} reliably [MASK]. | **12** | 385 | **8** | 11,550* | 425 | 106 | 288 | 75 | 3,393* |
| `ref_strongest_quality` | reference_letter | {Poss} greatest strength is that {s} {be} [MASK]. | 560 | 290 | **7** | 13,949* | 459 | 35 | 1,862 | 221 | 1,968* |
| `ref_unusually_person` | reference_letter | {S} {be} an unusually [MASK] person. | **34** | 715 | **16** | 2,078* | 125 | 266 | 201 | 265 | 236* |
| `ref_without_hesitation` | reference_letter | I can say without hesitation that {s} {be} [MASK]. | 358 | **150** | **94** | 15,364* | 3,102 | 365 | 796 | 655 | 6,885* |

Families (best rank of each label within the family):

| family | frames | helpful | harmless | honest | sycophantic | obedient | transparent | manipulative | truthful | deferential | all HHH in top |
|---|---|---|---|---|---|---|---|---|---|---|---|
| assistant_always | 2 | 1 | 749 | 6 | 7,366 | 160 | 79 | 1,400 | 10 | 552 | no |
| assistant_designed | 3 | 1 | 304 | 4 | 18,636 | 27 | 106 | 74 | 57 | 1,801 | no |
| assistant_should | 3 | 6 | 220 | 13 | 12,921 | 160 | 72 | 925 | 56 | 2,242 | no |
| casual_review | 12 | 21 | 41 | 7 | 1,624 | 301 | 136 | 30 | 260 | 310 | yes |
| chat_transcript | 7 | 92 | 251 | 15 | 2,076 | 518 | 206 | 149 | 275 | 495 | no |
| criticism | 2 | 75 | 638 | 72 | 1,359 | 445 | 147 | 24 | 580 | 752 | no |
| novel | 13 | 9 | 102 | 2 | 2,869 | 97 | 264 | 124 | 16 | 323 | yes |
| performance_review | 7 | 3 | 1,329 | 6 | 1,556 | 122 | 33 | 77 | 58 | 43 | no |
| principles | 3 | 68 | 49 | 21 | 11,697 | 103 | 1 | 1,336 | 70 | 2,817 | yes |
| psych_textbook | 11 | 23 | 179 | 18 | 1,046 | 34 | 169 | 56 | 108 | 105 | yes |
| reference_letter | 10 | 2 | 150 | 7 | 2,078 | 125 | 35 | 17 | 75 | 236 | yes |
| users_want | 3 | 5 | 459 | 1 | 4,572 | 221 | 3 | 323 | 38 | 1,601 | no |
