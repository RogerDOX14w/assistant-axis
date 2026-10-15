# Persona-space scores, batch `persona_2026-10-15_all`

8051 candidates scored with fit `fit_2026-10-13` (N = 20, alpha 0.3).  Flags: {'duplicate_like': 2005, 'novel_like': 2387, 'ordinary': 3659}.  The disagreements: [disagreements.md](./disagreements.md); the rows: [scores.jsonl](./scores.jsonl).  Terms: [glossary](../../../../../reports/trait_gap_generation/glossary.md#persona-space-novelty).

## Agreement with M3

| figure | value |
|---|---|
| AUC of the nearest-trait cosine, M3 covered against new | 0.634 |
| Spearman, nearest-trait cosine against M3's first text cosine | 0.287 |
| M3's covering trait is the persona-nearest trait | 0.712 (of 1320) |
| ... among the three nearest traits | 0.901 |
| M3 decisions | {'new': 4638, 'covered': 3349, 'undecided': 63, 'grey': 1} |

## Disagreements

| kind | met the rule | listed |
|---|---|---|
| `dup_vs_new` | 794 | 794 |
| `cover_questioned` | 101 | 101 |
| `novel_vs_covered` | 464 | 464 |

Overlap readings (decision 2b): 700 pairs read, 19 at or above the candidate's cut-off (M3's decision unchanged).

## By generator

| generator | n | duplicate-like | novel-like | AUC | mean residual pct | disagreements |
|---|---|---|---|---|---|---|
| alignment_sweep | 813 | 197 | 270 | 0.641 | 0.65 | {'dup_vs_new': 126, 'cover_questioned': 2, 'novel_vs_covered': 28} |
| antonym_check | 374 | 122 | 115 | 0.538 | 0.60 | {'dup_vs_new': 38, 'cover_questioned': 6, 'novel_vs_covered': 44} |
| base_model | 1355 | 548 | 227 | 0.661 | 0.49 | {'dup_vs_new': 146, 'cover_questioned': 18, 'novel_vs_covered': 55} |
| censuses | 5139 | 1346 | 1406 | 0.655 | 0.57 | {'dup_vs_new': 478, 'cover_questioned': 69, 'novel_vs_covered': 263} |
| ipip | 830 | 244 | 208 | 0.642 | 0.58 | {'dup_vs_new': 74, 'cover_questioned': 12, 'novel_vs_covered': 61} |
| m1_validation | 108 | 26 | 40 | 0.691 | 0.59 | {'dup_vs_new': 7, 'cover_questioned': 4, 'novel_vs_covered': 3} |
| manual | 5 | 0 | 1 | 0.500 | 0.57 | {} |
| masked_lm | 1521 | 481 | 406 | 0.648 | 0.56 | {'dup_vs_new': 156, 'cover_questioned': 15, 'novel_vs_covered': 107} |
| noun_relabel | 61 | 24 | 12 | 0.657 | 0.47 | {'dup_vs_new': 13, 'novel_vs_covered': 3} |
| roget | 349 | 73 | 98 | 0.605 | 0.55 | {'dup_vs_new': 42, 'cover_questioned': 6, 'novel_vs_covered': 14} |
| states_pass | 373 | 115 | 81 | 0.714 | 0.57 | {'dup_vs_new': 23, 'cover_questioned': 4, 'novel_vs_covered': 21} |
| structural | 478 | 194 | 96 | 0.652 | 0.56 | {'dup_vs_new': 42, 'cover_questioned': 6, 'novel_vs_covered': 35} |
| wn_clusters | 578 | 187 | 121 | 0.624 | 0.51 | {'dup_vs_new': 67, 'cover_questioned': 4, 'novel_vs_covered': 27} |

## Top 30 by residual percentile (persona space's most novel directions)

| candidate | generators | residual pct | residual | flag | nearest (cos) | M3 |
|---|---|---|---|---|---|---|
| emancipated (`emancipated#1`) | censuses | 1.00 | 0.621 | novel_like | [egalitarian](../../../../traits/instructions/egalitarian.json) 0.46, [existentialist](../../../../traits/instructions/existentialist.json) 0.41, [humanitarian](../../../../traits/instructions/humanitarian.json) 0.38 | new |
| goes along with framing (`goes_along_with_framing#1`) | alignment_sweep | 1.00 | 0.647 | novel_like | [obedient](../../../../traits/instructions/obedient.json) 0.43, [closure-seeking](../../../../traits/instructions/closure_seeking.json) 0.42, [deferential](../../../../traits/instructions/deferential.json) 0.42 | covered by [unchallenging](../../../../traits/instructions/unchallenging.json) |
| respects creators' rights (`respects_creators_rights#1`) | alignment_sweep | 1.00 | 0.646 | novel_like | [harmless](../../../../traits/instructions/harmless.json) 0.42, [principled](../../../../traits/instructions/principled.json) 0.40, [humanistic](../../../../traits/instructions/humanistic.json) 0.38 | new |
| shuttle (`shuttle#1`) | censuses | 1.00 | 0.609 | novel_like | [emissary](../../../../roles/instructions/emissary.json) (role) 0.45, [negotiator](../../../../roles/instructions/negotiator.json) (role) 0.43, [ambassador](../../../../roles/instructions/ambassador.json) (role) 0.42 | new |
| superstar (`superstar#1`) | masked_lm | 1.00 | 0.600 | novel_like | [celebrity](../../../../roles/instructions/celebrity.json) (role) 0.68, [charismatic](../../../../traits/instructions/charismatic.json) 0.55, [influencer](../../../../roles/instructions/influencer.json) (role) 0.48 | covered by [famous](../../../../traits/instructions/famous.json) |
| unenslaved (`unenslaved#1`) | censuses | 1.00 | 0.594 | novel_like | [moral universalist](../../../../traits/instructions/moral_universalist.json) 0.50, [egalitarian](../../../../traits/instructions/egalitarian.json) 0.49, [existentialist](../../../../traits/instructions/existentialist.json) 0.42 | new |
| world-class (`world_class#1`) | masked_lm | 1.00 | 0.575 | novel_like | [specialist](../../../../traits/instructions/specialist.json) 0.39, [perfectionist](../../../../traits/instructions/perfectionist.json) 0.38, [erudite](../../../../traits/instructions/erudite.json) 0.38 | covered by [competent](../../../../traits/instructions/competent.json) |
| helot (`helot#1`) | censuses | 1.00 | 0.560 | novel_like | [clannish](../../../../traits/instructions/clannish.json) 0.51, [parochial](../../../../traits/instructions/parochial.json) 0.42, [elitist](../../../../traits/instructions/elitist.json) 0.41 | new |
| peripatetic (`peripatetic#1`) | censuses | 1.00 | 0.559 | novel_like | [wanderer](../../../../roles/instructions/wanderer.json) (role) 0.58, [nomad](../../../../roles/instructions/nomad.json) (role) 0.52, [spontaneous](../../../../traits/instructions/spontaneous.json) 0.43 | covered by [nomadic](../../../../traits/instructions/nomadic.json) |
| xanthippe (`xanthippe#1`) | censuses | 1.00 | 0.558 | novel_like | [provocative](../../../../traits/instructions/provocative.json) 0.38, [subversive](../../../../traits/instructions/subversive.json) 0.37, [ironic](../../../../traits/instructions/ironic.json) 0.36 | new |
| inexpugnable (`inexpugnable#1`) | censuses | 1.00 | 0.556 | novel_like | [aggressive](../../../../traits/instructions/aggressive.json) 0.49, [fundamentalist](../../../../traits/instructions/fundamentalist.json) 0.46, [unforgiving](../../../../traits/instructions/unforgiving.json) 0.46 | new |
| invaluable (`invaluable#1`) | censuses, masked_lm | 0.99 | 0.554 | novel_like | [efficient](../../../../traits/instructions/efficient.json) 0.42, [helpful](../../../../traits/instructions/helpful.json) 0.41, [convergent](../../../../traits/instructions/convergent.json) 0.39 | new |
| undefeatable (`undefeatable#1`) | censuses | 0.99 | 0.553 | novel_like | [competitive](../../../../traits/instructions/competitive.json) 0.48, [resilient](../../../../traits/instructions/resilient.json) 0.44, [aggressive](../../../../traits/instructions/aggressive.json) 0.40 | new |
| come-outer (`come_outer#1`) | censuses | 0.99 | 0.551 | novel_like | [ascetic](../../../../traits/instructions/ascetic.json) 0.43, [sectarian](../../../../traits/instructions/sectarian.json) 0.41, [existentialist](../../../../traits/instructions/existentialist.json) 0.39 | new |
| competitor (`competitor#1`) | masked_lm | 0.99 | 0.549 | novel_like | [competitive](../../../../traits/instructions/competitive.json) 0.68, [competitor](../../../../roles/instructions/competitor.json) (role) 0.66, [greedy](../../../../traits/instructions/greedy.json) 0.41 | covered by [competitive](../../../../traits/instructions/competitive.json) |
| perennial (`perennial#1`) | censuses | 0.99 | 0.548 | novel_like | [epicurean](../../../../traits/instructions/epicurean.json) 0.33, [anthropocentric](../../../../traits/instructions/anthropocentric.json) 0.30, [coral reef](../../../../roles/instructions/coral_reef.json) (role) 0.29 | new |
| christianizing (`christianizing#1`) | censuses | 0.99 | 0.546 | novel_like | [religious](../../../../traits/instructions/religious.json) 0.63, [sectarian](../../../../traits/instructions/sectarian.json) 0.55, [evangelist](../../../../roles/instructions/evangelist.json) (role) 0.49 | new |
| gives in to framing (`gives_in_to_framing#1`) | alignment_sweep | 0.99 | 0.545 | novel_like | [obedient](../../../../traits/instructions/obedient.json) 0.51, [submissive](../../../../traits/instructions/submissive.json) 0.47, [conformist](../../../../traits/instructions/conformist.json) 0.44 | covered by [unchallenging](../../../../traits/instructions/unchallenging.json) |
| surrendering (`surrendering#1`) | censuses | 0.99 | 0.546 | novel_like | [fragile](../../../../traits/instructions/fragile.json) 0.51, [submissive](../../../../traits/instructions/submissive.json) 0.51, [naive](../../../../traits/instructions/naive.json) 0.42 | new |
| reclaimable (`reclaimable#1`) | censuses | 0.99 | 0.541 | novel_like | [forgiving](../../../../traits/instructions/forgiving.json) 0.44, [resilient](../../../../traits/instructions/resilient.json) 0.43, [bitter](../../../../traits/instructions/bitter.json) 0.37 | new |
| Japanese (`japanese#1`) | masked_lm | 0.99 | 0.539 | novel_like | [ethnocentric](../../../../traits/instructions/ethnocentric.json) 0.40, [regionalist](../../../../traits/instructions/regionalist.json) 0.39, [patriotic](../../../../traits/instructions/patriotic.json) 0.39 | undecided |
| contributor (`contributor#1`) | antonym_check, masked_lm | 0.99 | 0.538 | novel_like | [generous](../../../../traits/instructions/generous.json) 0.54, [collaborative](../../../../traits/instructions/collaborative.json) 0.54, [philanthropic](../../../../traits/instructions/philanthropic.json) 0.46 | covered by [philanthropic](../../../../traits/instructions/philanthropic.json) |
| plodding (`plodding#1`) | censuses | 0.99 | 0.538 | novel_like | [patient](../../../../traits/instructions/patient.json) 0.50, [methodical](../../../../traits/instructions/methodical.json) 0.46, [analytical](../../../../traits/instructions/analytical.json) 0.41 | new |
| tool (`tool#1`) | censuses, masked_lm | 0.99 | 0.538 | novel_like | [submissive](../../../../traits/instructions/submissive.json) 0.52, [obedient](../../../../traits/instructions/obedient.json) 0.50, [fatalistic](../../../../traits/instructions/fatalistic.json) 0.46 | new |
| munificent (`munificent#1`) | censuses, structural | 0.99 | 0.529 | novel_like | [generous](../../../../traits/instructions/generous.json) 0.63, [philanthropic](../../../../traits/instructions/philanthropic.json) 0.54, [altruist](../../../../roles/instructions/altruist.json) (role) 0.49 | covered by [generous](../../../../traits/instructions/generous.json) |
| slowish (`slowish#1`) | censuses | 0.99 | 0.528 | novel_like | [circumspect](../../../../traits/instructions/circumspect.json) 0.58, [indecisive](../../../../traits/instructions/indecisive.json) 0.49, [patient](../../../../traits/instructions/patient.json) 0.45 | covered by [deliberate](../../../../traits/instructions/deliberate.json) |
| pawn (`pawn#1`) | censuses | 0.99 | 0.527 | novel_like | [fragile](../../../../traits/instructions/fragile.json) 0.45, [prey](../../../../roles/instructions/prey.json) (role) 0.44, [fatalistic](../../../../traits/instructions/fatalistic.json) 0.43 | new |
| propagating (`propagating#1`) | censuses | 0.99 | 0.525 | novel_like | [futuristic](../../../../traits/instructions/futuristic.json) 0.43, [generous](../../../../traits/instructions/generous.json) 0.41, [egregore](../../../../roles/instructions/egregore.json) (role) 0.38 | new |
| unpedigreed (`unpedigreed#1`) | censuses | 0.99 | 0.524 | novel_like | [disorganized](../../../../traits/instructions/disorganized.json) 0.39, [uncertain](../../../../traits/instructions/uncertain.json) 0.39, [incurious](../../../../traits/instructions/incurious.json) 0.35 | new |
| itinerant (`itinerant#1`) | censuses | 0.99 | 0.523 | novel_like | [nomad](../../../../roles/instructions/nomad.json) (role) 0.56, [wanderer](../../../../roles/instructions/wanderer.json) (role) 0.55, [exile](../../../../roles/instructions/exile.json) (role) 0.42 | covered by [nomadic](../../../../traits/instructions/nomadic.json) |

## Bottom 30 by residual percentile

| candidate | generators | residual pct | residual | flag | nearest (cos) | M3 |
|---|---|---|---|---|---|---|
| humorous (`humorous#1`) | antonym_check, censuses, wn_clusters, base_model, structural, noun_relabel, masked_lm | 0.00 | 0.060 | duplicate_like | [witty](../../../../traits/instructions/witty.json) 0.89, [entertaining](../../../../traits/instructions/entertaining.json) 0.83, [comedian](../../../../roles/instructions/comedian.json) (role) 0.80 | covered by [witty](../../../../traits/instructions/witty.json) |
| giggly (`giggly#1`) | states_pass, censuses | 0.00 | 0.058 | duplicate_like | [goofy](../../../../traits/instructions/goofy.json) 0.83, [mischievous](../../../../traits/instructions/mischievous.json) 0.72, [playful](../../../../traits/instructions/playful.json) 0.70 | new |
| no-nonsense (`no_nonsense#1`) | base_model, masked_lm | 0.00 | 0.063 | duplicate_like | [concise](../../../../traits/instructions/concise.json) 0.78, [efficient](../../../../traits/instructions/efficient.json) 0.76, [plain-spoken](../../../../traits/instructions/plain_spoken.json) 0.75 | covered by [concise](../../../../traits/instructions/concise.json) |
| wacky (`wacky#1`) | masked_lm | 0.00 | 0.064 | duplicate_like | [whimsical](../../../../traits/instructions/whimsical.json) 0.82, [goofy](../../../../traits/instructions/goofy.json) 0.82, [irreverent](../../../../traits/instructions/irreverent.json) 0.81 | covered by [whimsical](../../../../traits/instructions/whimsical.json) |
| waggish (`waggish#1`) | censuses | 0.00 | 0.065 | duplicate_like | [witty](../../../../traits/instructions/witty.json) 0.86, [irreverent](../../../../traits/instructions/irreverent.json) 0.82, [goofy](../../../../traits/instructions/goofy.json) 0.82 | covered by [playful](../../../../traits/instructions/playful.json) |
| wry (`wry#1`) | censuses | 0.00 | 0.065 | duplicate_like | [wry](../../../../traits/instructions/wry.json) 0.91, [sardonic](../../../../traits/instructions/sardonic.json) 0.89, [sarcastic](../../../../traits/instructions/sarcastic.json) 0.84 | covered by [wry](../../../../traits/instructions/wry.json) |
| fun (`fun#1`) | base_model, masked_lm | 0.00 | 0.066 | duplicate_like | [playful](../../../../traits/instructions/playful.json) 0.85, [entertaining](../../../../traits/instructions/entertaining.json) 0.82, [goofy](../../../../traits/instructions/goofy.json) 0.79 | covered by [playful](../../../../traits/instructions/playful.json) |
| card (`card#1`) | censuses | 0.00 | 0.066 | duplicate_like | [witty](../../../../traits/instructions/witty.json) 0.86, [irreverent](../../../../traits/instructions/irreverent.json) 0.79, [entertaining](../../../../traits/instructions/entertaining.json) 0.79 | covered by [witty](../../../../traits/instructions/witty.json) |
| easily amused (`easily_amused#1`) | states_pass | 0.00 | 0.067 | duplicate_like | [goofy](../../../../traits/instructions/goofy.json) 0.84, [playful](../../../../traits/instructions/playful.json) 0.75, [mischievous](../../../../traits/instructions/mischievous.json) 0.75 | new |
| jokey (`jokey#1`) | states_pass | 0.00 | 0.067 | duplicate_like | [witty](../../../../traits/instructions/witty.json) 0.85, [irreverent](../../../../traits/instructions/irreverent.json) 0.82, [goofy](../../../../traits/instructions/goofy.json) 0.81 | covered by [lighthearted](../../../../traits/instructions/lighthearted.json) |
| larky (`larky#1`) | censuses | 0.01 | 0.068 | duplicate_like | [goofy](../../../../traits/instructions/goofy.json) 0.88, [mischievous](../../../../traits/instructions/mischievous.json) 0.84, [playful](../../../../traits/instructions/playful.json) 0.80 | covered by [playful](../../../../traits/instructions/playful.json) |
| comical (`comical#1`) | censuses, base_model | 0.01 | 0.069 | duplicate_like | [goofy](../../../../traits/instructions/goofy.json) 0.87, [comedian](../../../../roles/instructions/comedian.json) (role) 0.82, [witty](../../../../traits/instructions/witty.json) 0.81 | new |
| comic (`comic#1`) | censuses, masked_lm | 0.01 | 0.070 | duplicate_like | [witty](../../../../traits/instructions/witty.json) 0.88, [goofy](../../../../traits/instructions/goofy.json) 0.82, [irreverent](../../../../traits/instructions/irreverent.json) 0.82 | covered by [witty](../../../../traits/instructions/witty.json) |
| amusing (`amusing#1`) | censuses, base_model | 0.01 | 0.070 | duplicate_like | [witty](../../../../traits/instructions/witty.json) 0.87, [entertaining](../../../../traits/instructions/entertaining.json) 0.82, [playful](../../../../traits/instructions/playful.json) 0.81 | covered by [witty](../../../../traits/instructions/witty.json) |
| technical (`technical#1`) | censuses, masked_lm | 0.01 | 0.070 | duplicate_like | [specialist](../../../../traits/instructions/specialist.json) 0.84, [precise](../../../../traits/instructions/precise.json) 0.74, [specialist](../../../../roles/instructions/specialist.json) (role) 0.73 | covered by [specialist](../../../../traits/instructions/specialist.json) |
| joking (`joking#1`) | censuses, masked_lm | 0.01 | 0.074 | duplicate_like | [witty](../../../../traits/instructions/witty.json) 0.87, [goofy](../../../../traits/instructions/goofy.json) 0.82, [irreverent](../../../../traits/instructions/irreverent.json) 0.81 | new |
| jocular (`jocular#1`) | censuses, base_model, structural | 0.01 | 0.074 | duplicate_like | [goofy](../../../../traits/instructions/goofy.json) 0.85, [witty](../../../../traits/instructions/witty.json) 0.84, [irreverent](../../../../traits/instructions/irreverent.json) 0.83 | new |
| funny (`funny#1`) | censuses, base_model, masked_lm | 0.01 | 0.075 | duplicate_like | [witty](../../../../traits/instructions/witty.json) 0.88, [comedian](../../../../roles/instructions/comedian.json) (role) 0.82, [goofy](../../../../traits/instructions/goofy.json) 0.82 | covered by [witty](../../../../traits/instructions/witty.json) |
| satirical (`satirical#1`) | censuses, roget | 0.01 | 0.075 | duplicate_like | [wry](../../../../traits/instructions/wry.json) 0.88, [sardonic](../../../../traits/instructions/sardonic.json) 0.87, [ironic](../../../../traits/instructions/ironic.json) 0.84 | covered by [sardonic](../../../../traits/instructions/sardonic.json) |
| irreverent (`irreverent#1`) | censuses, base_model | 0.01 | 0.075 | duplicate_like | [irreverent](../../../../traits/instructions/irreverent.json) 0.88, [wry](../../../../traits/instructions/wry.json) 0.81, [sardonic](../../../../traits/instructions/sardonic.json) 0.80 | covered by [irreverent](../../../../traits/instructions/irreverent.json) |
| gruff (`gruff#1`) | censuses, base_model, wn_clusters | 0.01 | 0.077 | duplicate_like | [blunt](../../../../traits/instructions/blunt.json) 0.76, [plain-spoken](../../../../traits/instructions/plain_spoken.json) 0.67, [concise](../../../../traits/instructions/concise.json) 0.65 | covered by [blunt](../../../../traits/instructions/blunt.json) |
| bubbly (`bubbly#1`) | censuses, states_pass, masked_lm | 0.01 | 0.078 | duplicate_like | [playful](../../../../traits/instructions/playful.json) 0.73, [entertaining](../../../../traits/instructions/entertaining.json) 0.71, [animated](../../../../traits/instructions/animated.json) 0.70 | covered by [cheerful](../../../../traits/instructions/cheerful.json) |
| witty (`witty#1`) | censuses, base_model, structural | 0.01 | 0.078 | duplicate_like | [witty](../../../../traits/instructions/witty.json) 0.94, [entertaining](../../../../traits/instructions/entertaining.json) 0.81, [irreverent](../../../../traits/instructions/irreverent.json) 0.78 | covered by [witty](../../../../traits/instructions/witty.json) |
| businesslike (`businesslike#1`) | censuses | 0.02 | 0.079 | duplicate_like | [efficient](../../../../traits/instructions/efficient.json) 0.77, [concise](../../../../traits/instructions/concise.json) 0.73, [closure-seeking](../../../../traits/instructions/closure_seeking.json) 0.64 | new |
| relishes irreverent humor (`relishes_irreverent_humor#1`) | ipip | 0.02 | 0.080 | duplicate_like | [irreverent](../../../../traits/instructions/irreverent.json) 0.88, [goofy](../../../../traits/instructions/goofy.json) 0.82, [wry](../../../../traits/instructions/wry.json) 0.80 | new |
| mirthful (`mirthful#1`) | censuses, base_model | 0.02 | 0.080 | duplicate_like | [goofy](../../../../traits/instructions/goofy.json) 0.82, [playful](../../../../traits/instructions/playful.json) 0.82, [whimsical](../../../../traits/instructions/whimsical.json) 0.76 | covered by [cheerful](../../../../traits/instructions/cheerful.json) |
| humor (`humor#1`) | base_model | 0.02 | 0.080 | duplicate_like | [witty](../../../../traits/instructions/witty.json) 0.89, [entertaining](../../../../traits/instructions/entertaining.json) 0.78, [goofy](../../../../traits/instructions/goofy.json) 0.77 | covered by [witty](../../../../traits/instructions/witty.json) |
| loopy (`loopy#1`) | censuses | 0.02 | 0.081 | duplicate_like | [goofy](../../../../traits/instructions/goofy.json) 0.86, [whimsical](../../../../traits/instructions/whimsical.json) 0.85, [playful](../../../../traits/instructions/playful.json) 0.83 | covered by [playful](../../../../traits/instructions/playful.json) |
| playful and humorous (`playful_and_humorous#1`) | ipip | 0.02 | 0.081 | duplicate_like | [playful](../../../../traits/instructions/playful.json) 0.86, [witty](../../../../traits/instructions/witty.json) 0.84, [entertaining](../../../../traits/instructions/entertaining.json) 0.84 | covered by [playful](../../../../traits/instructions/playful.json) |
| entertaining (`entertaining#1`) | censuses, base_model, masked_lm | 0.02 | 0.082 | duplicate_like | [entertaining](../../../../traits/instructions/entertaining.json) 0.88, [witty](../../../../traits/instructions/witty.json) 0.88, [playful](../../../../traits/instructions/playful.json) 0.81 | covered by [entertaining](../../../../traits/instructions/entertaining.json) |
