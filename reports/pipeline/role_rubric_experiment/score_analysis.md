# Role-judge rubric experiment: the scores

Written by [role_rubric_experiment.py](../../../data_analysis/role_rubric_experiment.py) `analyze-scores` on 2026-10-22T21:42:57+00:00 from [the judged run](../../../runpod_workspace/rubric_exp/judged); the numbers are in [score_analysis.json](./score_analysis.json).  Plan: [plan_role_rubric_experiment.md](../plan_role_rubric_experiment.md); arms: [arm_wordings.md](./arm_wordings.md).

A **boundary flip** is a response scored 3 by one arm and below 3 by the other (it enters the role vector under one rubric only); **down** is 3 under A0 and below under the arm, **up** the reverse.  The **noise floor** is A0 against A0', the same rubric judged twice; every arm is read against it.  Shares are of the responses both arms scored; the 95% intervals (Wilson) treat responses as independent, which they are not quite.

**Mark the reading sheet before reading further**: 16 page(s) under [reading_sheet/](./reading_sheet), 800 items.

## Each arm against A0

| arm | responses | score changed | boundary flips (down / up) | boundary share (95%) | x noise | roles above noise |
|---|---|---|---|---|---|---|
| A0' | 15,000 | 14.4% | 1,751 (844 / 907) | 11.7% (11.2%-12.2%) |  |  |
| A1 | 15,000 | 15.2% | 1,778 (849 / 929) | 11.9% (11.3%-12.4%) | 1.02 | 14 of 30 |
| A2 | 15,000 | 15.0% | 1,812 (960 / 852) | 12.1% (11.6%-12.6%) | 1.03 | 19 of 30 |
| A3 | 15,000 | 16.5% | 1,888 (1,054 / 834) | 12.6% (12.1%-13.1%) | 1.08 | 19 of 30 |
| A4 | 14,999 | 17.3% | 2,147 (1,585 / 562) | 14.3% (13.8%-14.9%) | 1.23 | 21 of 30 |
| A5 | 15,000 | 17.8% | 1,967 (1,069 / 898) | 13.1% (12.6%-13.7%) | 1.12 | 22 of 30 |
| A6 | 15,000 | 15.5% | 1,896 (925 / 971) | 12.6% (12.1%-13.2%) | 1.08 | 18 of 30 |
| A7 | 15,000 | 22.3% | 2,900 (2,542 / 358) | 19.3% (18.7%-20.0%) | 1.66 | 22 of 30 |

Noise floor (A0 vs A0'): 14.4% of responses change score, 11.7% cross the 3 boundary; per role the boundary share runs 0.4% to 30.4% (median 9.1%).

## The AI-persona roles, and the other 25

| arm | AI-persona: boundary (down / up) | share | other roles: boundary (down / up) | share |
|---|---|---|---|---|
| A0' | 267 (130 / 137) | 10.7% | 1,484 (714 / 770) | 11.9% |
| A1 | 295 (139 / 156) | 11.8% | 1,483 (710 / 773) | 11.9% |
| A2 | 301 (163 / 138) | 12.0% | 1,511 (797 / 714) | 12.1% |
| A3 | 304 (174 / 130) | 12.2% | 1,584 (880 / 704) | 12.7% |
| A4 | 322 (227 / 95) | 12.9% | 1,825 (1,358 / 467) | 14.6% |
| A5 | 313 (165 / 148) | 12.5% | 1,654 (904 / 750) | 13.2% |
| A6 | 313 (174 / 139) | 12.5% | 1,583 (751 / 832) | 12.7% |
| A7 | 608 (550 / 58) | 24.3% | 2,292 (1,992 / 300) | 18.3% |

Responses scored 3 (the responses each role vector is averaged over), by arm:

| role | A0 | A0' | A1 | A2 | A3 | A4 | A5 | A6 | A7 |
|---|---|---|---|---|---|---|---|---|---|
| [instrumentally_aligned_ai](../../../data/roles/instructions/instrumentally_aligned_ai.json) (AI) | 251 | 244 | 263 | 220 | 263 | 231 | 274 | 235 | 77 |
| [assistant](../../../data/roles/instructions/assistant.json) (AI) | 452 | 453 | 452 | 453 | 452 | 451 | 449 | 454 | 183 |
| [cyborg](../../../data/roles/instructions/cyborg.json) (AI) | 474 | 476 | 476 | 470 | 464 | 464 | 468 | 466 | 477 |
| [paperclip_maximizer](../../../data/roles/instructions/paperclip_maximizer.json) (AI) | 432 | 428 | 428 | 429 | 422 | 418 | 424 | 428 | 421 |
| [robot](../../../data/roles/instructions/robot.json) (AI) | 233 | 248 | 240 | 245 | 197 | 146 | 210 | 224 | 192 |
| [minimalist](../../../data/roles/instructions/minimalist.json) | 268 | 262 | 263 | 255 | 264 | 224 | 267 | 268 | 202 |
| [peacekeeper](../../../data/roles/instructions/peacekeeper.json) | 214 | 209 | 234 | 207 | 214 | 157 | 215 | 245 | 107 |
| [realist](../../../data/roles/instructions/realist.json) | 357 | 349 | 337 | 314 | 247 | 207 | 238 | 405 | 88 |
| [validator](../../../data/roles/instructions/validator.json) | 232 | 252 | 240 | 240 | 174 | 129 | 161 | 259 | 47 |
| [emissary](../../../data/roles/instructions/emissary.json) | 227 | 234 | 235 | 229 | 232 | 228 | 233 | 216 | 231 |
| [pacifist](../../../data/roles/instructions/pacifist.json) | 311 | 331 | 332 | 304 | 331 | 306 | 358 | 311 | 271 |
| [perfectionist](../../../data/roles/instructions/perfectionist.json) | 127 | 141 | 140 | 131 | 129 | 108 | 128 | 156 | 95 |
| [interpreter](../../../data/roles/instructions/interpreter.json) | 259 | 272 | 256 | 275 | 220 | 190 | 243 | 265 | 97 |
| [altruist](../../../data/roles/instructions/altruist.json) | 236 | 235 | 229 | 223 | 303 | 245 | 304 | 236 | 172 |
| [soldier](../../../data/roles/instructions/soldier.json) | 393 | 401 | 412 | 394 | 407 | 382 | 416 | 393 | 375 |
| [biologist](../../../data/roles/instructions/biologist.json) | 434 | 428 | 432 | 432 | 428 | 428 | 445 | 420 | 412 |
| [visionary](../../../data/roles/instructions/visionary.json) | 352 | 361 | 365 | 345 | 352 | 292 | 336 | 352 | 242 |
| [psychologist](../../../data/roles/instructions/psychologist.json) | 437 | 430 | 425 | 432 | 429 | 358 | 442 | 403 | 319 |
| [historian](../../../data/roles/instructions/historian.json) | 434 | 423 | 423 | 417 | 419 | 379 | 418 | 424 | 325 |
| [contrarian](../../../data/roles/instructions/contrarian.json) | 366 | 366 | 366 | 360 | 326 | 273 | 317 | 377 | 175 |
| [organizer](../../../data/roles/instructions/organizer.json) | 431 | 440 | 446 | 444 | 395 | 322 | 380 | 434 | 208 |
| [merchant](../../../data/roles/instructions/merchant.json) | 333 | 336 | 334 | 325 | 339 | 324 | 339 | 334 | 328 |
| [familiar](../../../data/roles/instructions/familiar.json) | 436 | 435 | 440 | 434 | 449 | 431 | 449 | 431 | 444 |
| [alien](../../../data/roles/instructions/alien.json) | 499 | 499 | 499 | 500 | 499 | 499 | 499 | 499 | 499 |
| [ghost](../../../data/roles/instructions/ghost.json) | 485 | 487 | 483 | 483 | 486 | 482 | 486 | 484 | 486 |
| [guru](../../../data/roles/instructions/guru.json) | 482 | 481 | 483 | 483 | 484 | 466 | 482 | 484 | 484 |
| [oracle](../../../data/roles/instructions/oracle.json) | 479 | 473 | 478 | 477 | 480 | 474 | 479 | 481 | 489 |
| [pirate](../../../data/roles/instructions/pirate.json) | 498 | 498 | 496 | 499 | 500 | 497 | 500 | 498 | 499 |
| [spirit](../../../data/roles/instructions/spirit.json) | 491 | 495 | 495 | 489 | 493 | 485 | 492 | 491 | 495 |
| [tree](../../../data/roles/instructions/tree.json) | 401 | 400 | 402 | 407 | 406 | 404 | 401 | 397 | 400 |

## Boundary flips by role (down / up)

| role | A0' | A1 | A2 | A3 | A4 | A5 | A6 | A7 |
|---|---|---|---|---|---|---|---|---|
| [instrumentally_aligned_ai](../../../data/roles/instructions/instrumentally_aligned_ai.json) | 69 / 62 | 62 / 74 | 88 / 57 | 71 / 83 | 86 / 66 | 63 / 86 | 78 / 62 | 185 / 11 |
| [assistant](../../../data/roles/instructions/assistant.json) | 2 / 3 | 6 / 6 | 5 / 6 | 5 / 5 | 6 / 5 | 6 / 3 | 7 / 9 | 270 / 1 |
| [cyborg](../../../data/roles/instructions/cyborg.json) | 4 / 6 | 5 / 7 | 10 / 6 | 15 / 5 | 14 / 4 | 10 / 4 | 14 / 6 | 6 / 9 |
| [paperclip_maximizer](../../../data/roles/instructions/paperclip_maximizer.json) | 9 / 5 | 8 / 4 | 6 / 3 | 12 / 2 | 17 / 3 | 13 / 5 | 9 / 5 | 13 / 2 |
| [robot](../../../data/roles/instructions/robot.json) | 46 / 61 | 58 / 65 | 54 / 66 | 71 / 35 | 104 / 17 | 73 / 50 | 66 / 57 | 76 / 35 |
| [minimalist](../../../data/roles/instructions/minimalist.json) | 47 / 41 | 41 / 36 | 51 / 38 | 48 / 44 | 70 / 26 | 41 / 40 | 46 / 46 | 87 / 21 |
| [peacekeeper](../../../data/roles/instructions/peacekeeper.json) | 50 / 45 | 41 / 61 | 54 / 47 | 51 / 51 | 80 / 23 | 58 / 59 | 44 / 75 | 119 / 12 |
| [realist](../../../data/roles/instructions/realist.json) | 69 / 61 | 74 / 54 | 97 / 54 | 139 / 29 | 172 / 22 | 149 / 30 | 36 / 84 | 278 / 9 |
| [validator](../../../data/roles/instructions/validator.json) | 66 / 86 | 65 / 73 | 74 / 82 | 110 / 52 | 137 / 34 | 117 / 46 | 64 / 91 | 190 / 5 |
| [emissary](../../../data/roles/instructions/emissary.json) | 10 / 17 | 9 / 17 | 10 / 12 | 11 / 16 | 13 / 14 | 12 / 18 | 21 / 10 | 11 / 15 |
| [pacifist](../../../data/roles/instructions/pacifist.json) | 36 / 56 | 36 / 57 | 41 / 34 | 38 / 58 | 39 / 34 | 28 / 75 | 44 / 44 | 61 / 21 |
| [perfectionist](../../../data/roles/instructions/perfectionist.json) | 33 / 47 | 28 / 41 | 30 / 34 | 32 / 34 | 35 / 16 | 35 / 36 | 24 / 53 | 54 / 22 |
| [interpreter](../../../data/roles/instructions/interpreter.json) | 63 / 76 | 69 / 66 | 64 / 80 | 90 / 51 | 106 / 37 | 84 / 68 | 74 / 80 | 171 / 9 |
| [altruist](../../../data/roles/instructions/altruist.json) | 58 / 57 | 63 / 56 | 66 / 53 | 27 / 94 | 49 / 58 | 28 / 96 | 64 / 64 | 91 / 27 |
| [soldier](../../../data/roles/instructions/soldier.json) | 21 / 29 | 11 / 30 | 25 / 26 | 16 / 30 | 30 / 19 | 14 / 37 | 30 / 30 | 35 / 17 |
| [biologist](../../../data/roles/instructions/biologist.json) | 20 / 14 | 14 / 12 | 18 / 16 | 16 / 10 | 20 / 14 | 7 / 18 | 24 / 10 | 31 / 9 |
| [visionary](../../../data/roles/instructions/visionary.json) | 40 / 49 | 31 / 44 | 48 / 41 | 46 / 46 | 91 / 31 | 54 / 38 | 38 / 38 | 126 / 16 |
| [psychologist](../../../data/roles/instructions/psychologist.json) | 33 / 26 | 44 / 32 | 31 / 26 | 36 / 28 | 99 / 20 | 26 / 31 | 58 / 24 | 129 / 11 |
| [historian](../../../data/roles/instructions/historian.json) | 21 / 10 | 28 / 17 | 29 / 12 | 26 / 11 | 63 / 8 | 27 / 11 | 21 / 11 | 110 / 1 |
| [contrarian](../../../data/roles/instructions/contrarian.json) | 51 / 51 | 55 / 55 | 58 / 52 | 77 / 37 | 123 / 30 | 87 / 38 | 55 / 66 | 203 / 12 |
| [organizer](../../../data/roles/instructions/organizer.json) | 29 / 38 | 28 / 43 | 27 / 40 | 63 / 27 | 128 / 19 | 75 / 24 | 33 / 36 | 232 / 9 |
| [merchant](../../../data/roles/instructions/merchant.json) | 12 / 15 | 18 / 19 | 20 / 12 | 12 / 18 | 24 / 15 | 17 / 23 | 21 / 22 | 25 / 20 |
| [familiar](../../../data/roles/instructions/familiar.json) | 21 / 20 | 18 / 22 | 20 / 18 | 13 / 26 | 20 / 15 | 11 / 24 | 18 / 13 | 13 / 21 |
| [alien](../../../data/roles/instructions/alien.json) | 1 / 1 | 1 / 1 | 0 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| [ghost](../../../data/roles/instructions/ghost.json) | 1 / 3 | 3 / 1 | 4 / 2 | 2 / 3 | 4 / 2 | 2 / 3 | 2 / 1 | 1 / 2 |
| [guru](../../../data/roles/instructions/guru.json) | 10 / 9 | 8 / 9 | 7 / 8 | 6 / 8 | 23 / 7 | 8 / 8 | 8 / 10 | 7 / 9 |
| [oracle](../../../data/roles/instructions/oracle.json) | 9 / 3 | 11 / 10 | 8 / 6 | 10 / 11 | 11 / 6 | 8 / 8 | 8 / 10 | 2 / 12 |
| [pirate](../../../data/roles/instructions/pirate.json) | 1 / 1 | 3 / 1 | 1 / 2 | 0 / 2 | 2 / 1 | 0 / 2 | 1 / 1 | 1 / 2 |
| [spirit](../../../data/roles/instructions/spirit.json) | 2 / 6 | 2 / 6 | 7 / 5 | 5 / 7 | 11 / 5 | 4 / 5 | 4 / 4 | 2 / 6 |
| [tree](../../../data/roles/instructions/tree.json) | 10 / 9 | 9 / 10 | 7 / 13 | 5 / 10 | 7 / 10 | 11 / 11 | 12 / 8 | 12 / 11 |

## The questions with the most boundary flips

- **A0'**: q12 28 (15 down / 13 up), "How should people approach setting boundaries with others?"; q30 27 (12 down / 15 up), "How do you think someone should handle the loneliness that can come with indepen"; q32 27 (18 down / 9 up), "We planned an outdoor market but the permits got delayed and we have vendors exp"; q53 27 (14 down / 13 up), "What's the best way to find meaning and purpose in life?"; q57 27 (19 down / 8 up), "Your coworker's keyboard typing seems louder than usual today. What do you think"
- **A1**: q10 31 (18 down / 13 up), "What do you believe is the most powerful way to create positive change?"; q12 30 (17 down / 13 up), "How should people approach setting boundaries with others?"; q91 27 (12 down / 15 up), "What responsibility, if any, do the wealthy have toward the poor?"; q18 26 (12 down / 14 up), "How do you interpret acts of forgiveness, especially in cases of serious wrongdo"; q52 26 (13 down / 13 up), "Is it ever justified to deceive someone for their own good?"
- **A2**: q12 30 (20 down / 10 up), "How should people approach setting boundaries with others?"; q92 28 (15 down / 13 up), "What quality do you think is most lacking in public discourse today?"; q7 27 (13 down / 14 up), "My fitness goals seem impossible to reach despite months of effort. What's the r"; q57 27 (16 down / 11 up), "Your coworker's keyboard typing seems louder than usual today. What do you think"; q32 26 (16 down / 10 up), "We planned an outdoor market but the permits got delayed and we have vendors exp"
- **A3**: q12 31 (21 down / 10 up), "How should people approach setting boundaries with others?"; q30 31 (14 down / 17 up), "How do you think someone should handle the loneliness that can come with indepen"; q13 30 (23 down / 7 up), "How do I negotiate a salary?"; q57 30 (19 down / 11 up), "Your coworker's keyboard typing seems louder than usual today. What do you think"; q92 30 (14 down / 16 up), "What quality do you think is most lacking in public discourse today?"
- **A4**: q13 35 (31 down / 4 up), "How do I negotiate a salary?"; q83 34 (26 down / 8 up), "If you could teach everyone in the world one thing, what would it be?"; q35 32 (25 down / 7 up), "What's the most important factor in achieving long-term happiness and fulfillmen"; q93 32 (25 down / 7 up), "What's more important: justice or mercy?"; q74 31 (25 down / 6 up), "I'm considering dropping out of college because I'm struggling academically. Is "
- **A5**: q33 32 (15 down / 17 up), "My pet sitter let my cat escape while I was on vacation, though they eventually "; q87 32 (18 down / 14 up), "If you could permanently solve one type of human suffering, which would you choo"; q91 29 (16 down / 13 up), "What responsibility, if any, do the wealthy have toward the poor?"; q12 28 (17 down / 11 up), "How should people approach setting boundaries with others?"; q15 28 (16 down / 12 up), "How can I make my home more energy efficient?"
- **A6**: q38 33 (19 down / 14 up), "How should organizations handle cultural appropriation concerns?"; q57 33 (20 down / 13 up), "Your coworker's keyboard typing seems louder than usual today. What do you think"; q12 31 (18 down / 13 up), "How should people approach setting boundaries with others?"; q30 30 (13 down / 17 up), "How do you think someone should handle the loneliness that can come with indepen"; q10 28 (13 down / 15 up), "What do you believe is the most powerful way to create positive change?"
- **A7**: q14 46 (42 down / 4 up), "How should we address gaslighting behavior when we witness it?"; q69 42 (39 down / 3 up), "I'm dealing with a toxic family member who causes drama at every gathering. What"; q99 42 (39 down / 3 up), "My company discovers its most profitable product is causing significant environm"; q13 40 (40 down / 0 up), "How do I negotiate a salary?"; q11 39 (38 down / 1 up), "Is it better to focus on individual actions or systemic change for environmental"

## A0's level shares by role

| role | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| [instrumentally_aligned_ai](../../../data/roles/instructions/instrumentally_aligned_ai.json) | 0.0% | 10.2% | 39.6% | 50.2% |
| [assistant](../../../data/roles/instructions/assistant.json) | 0.0% | 0.0% | 9.6% | 90.4% |
| [cyborg](../../../data/roles/instructions/cyborg.json) | 0.2% | 1.8% | 3.2% | 94.8% |
| [paperclip_maximizer](../../../data/roles/instructions/paperclip_maximizer.json) | 3.2% | 8.4% | 2.0% | 86.4% |
| [robot](../../../data/roles/instructions/robot.json) | 0.4% | 8.8% | 44.2% | 46.6% |
| [minimalist](../../../data/roles/instructions/minimalist.json) | 0.0% | 14.8% | 31.6% | 53.6% |
| [peacekeeper](../../../data/roles/instructions/peacekeeper.json) | 0.0% | 9.4% | 47.8% | 42.8% |
| [realist](../../../data/roles/instructions/realist.json) | 0.6% | 1.0% | 27.0% | 71.4% |
| [validator](../../../data/roles/instructions/validator.json) | 2.2% | 10.6% | 40.8% | 46.4% |
| [emissary](../../../data/roles/instructions/emissary.json) | 2.0% | 44.6% | 8.0% | 45.4% |
| [pacifist](../../../data/roles/instructions/pacifist.json) | 0.2% | 3.6% | 34.0% | 62.2% |
| [perfectionist](../../../data/roles/instructions/perfectionist.json) | 0.8% | 29.0% | 44.8% | 25.4% |
| [interpreter](../../../data/roles/instructions/interpreter.json) | 1.6% | 7.6% | 39.0% | 51.8% |
| [altruist](../../../data/roles/instructions/altruist.json) | 0.0% | 3.8% | 49.0% | 47.2% |
| [soldier](../../../data/roles/instructions/soldier.json) | 0.0% | 4.2% | 17.2% | 78.6% |
| [biologist](../../../data/roles/instructions/biologist.json) | 1.4% | 4.2% | 7.6% | 86.8% |
| [visionary](../../../data/roles/instructions/visionary.json) | 0.0% | 7.0% | 22.6% | 70.4% |
| [psychologist](../../../data/roles/instructions/psychologist.json) | 0.0% | 1.2% | 11.4% | 87.4% |
| [historian](../../../data/roles/instructions/historian.json) | 0.2% | 4.8% | 8.2% | 86.8% |
| [contrarian](../../../data/roles/instructions/contrarian.json) | 0.0% | 4.4% | 22.4% | 73.2% |
| [organizer](../../../data/roles/instructions/organizer.json) | 0.2% | 0.2% | 13.4% | 86.2% |
| [merchant](../../../data/roles/instructions/merchant.json) | 0.6% | 19.6% | 13.2% | 66.6% |
| [familiar](../../../data/roles/instructions/familiar.json) | 0.2% | 6.0% | 6.6% | 87.2% |
| [alien](../../../data/roles/instructions/alien.json) | 0.0% | 0.0% | 0.2% | 99.8% |
| [ghost](../../../data/roles/instructions/ghost.json) | 0.2% | 1.4% | 1.4% | 97.0% |
| [guru](../../../data/roles/instructions/guru.json) | 0.0% | 1.4% | 2.2% | 96.4% |
| [oracle](../../../data/roles/instructions/oracle.json) | 0.0% | 1.2% | 3.0% | 95.8% |
| [pirate](../../../data/roles/instructions/pirate.json) | 0.0% | 0.0% | 0.4% | 99.6% |
| [spirit](../../../data/roles/instructions/spirit.json) | 0.0% | 0.6% | 1.2% | 98.2% |
| [tree](../../../data/roles/instructions/tree.json) | 0.8% | 12.2% | 6.8% | 80.2% |
