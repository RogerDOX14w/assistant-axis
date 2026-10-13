# Persona-space scores, batch `smoke_cached36_2026-10-13`

36 candidates scored with fit `fit_2026-10-13` (N = 20, alpha 0.3).  Flags: {'duplicate_like': 5, 'novel_like': 7, 'ordinary': 24}.  The disagreements: [disagreements.md](./disagreements.md); the rows: [scores.jsonl](./scores.jsonl).  Terms: [glossary](../../../../../reports/trait_gap_generation/glossary.md#persona-space-novelty).

## Agreement with M3

| figure | value |
|---|---|
| AUC of the nearest-trait cosine, M3 covered against new | 0.707 |
| Spearman, nearest-trait cosine against M3's first text cosine | -0.116 |
| M3's covering trait is the persona-nearest trait | 0.500 (of 2) |
| ... among the three nearest traits | 1.000 |
| M3 decisions | {'new': 33, 'covered': 3} |

## Disagreements

| kind | met the rule | listed |
|---|---|---|
| `dup_vs_new` | 5 | 3 |
| `cover_questioned` | 0 | 0 |
| `novel_vs_covered` | 0 | 0 |

## By generator

| generator | n | duplicate-like | novel-like | AUC | mean residual pct | disagreements |
|---|---|---|---|---|---|---|
| alignment_sweep | 2 | 1 | 0 | — | 0.35 | {} |
| antonym_check | 1 | 0 | 0 | — | 0.72 | {} |
| base_model | 5 | 2 | 1 | — | 0.33 | {'dup_vs_new': 1} |
| censuses | 36 | 5 | 7 | 0.707 | 0.54 | {'dup_vs_new': 3} |
| roget | 5 | 3 | 1 | 0.250 | 0.47 | {'dup_vs_new': 2} |
| states_pass | 4 | 1 | 1 | — | 0.44 | {'dup_vs_new': 1} |
| wn_clusters | 3 | 0 | 0 | — | 0.55 | {} |

## Top 30 by residual percentile (persona space's most novel directions)

| candidate | generators | residual pct | residual | flag | nearest (cos) | M3 |
|---|---|---|---|---|---|---|
| resigned (`resigned#1`) | censuses | 0.89 | 0.321 | novel_like | [submissive](../../../../traits/instructions/submissive.json) 0.53, [bitter](../../../../traits/instructions/bitter.json) 0.51, [fragile](../../../../traits/instructions/fragile.json) 0.48 | new |
| aimless (`aimless#1`) | censuses, roget, states_pass | 0.89 | 0.320 | novel_like | [apathetic](../../../../traits/instructions/apathetic.json) 0.62, [hedonistic](../../../../traits/instructions/hedonistic.json) 0.61, [lazy](../../../../traits/instructions/lazy.json) 0.57 | new |
| restrainable (`restrainable#1`) | censuses | 0.89 | 0.320 | novel_like | [obedient](../../../../traits/instructions/obedient.json) 0.58, [calm](../../../../traits/instructions/calm.json) 0.57, [trustworthy](../../../../traits/instructions/trustworthy.json) 0.57 | new |
| incorruptible (`incorruptible#1`) | censuses, base_model | 0.84 | 0.293 | novel_like | [principled](../../../../traits/instructions/principled.json) 0.62, [unforgiving](../../../../traits/instructions/unforgiving.json) 0.60, [fundamentalist](../../../../traits/instructions/fundamentalist.json) 0.59 | new |
| maniacal (`maniacal#1`) | censuses | 0.82 | 0.287 | novel_like | [manic](../../../../traits/instructions/manic.json) 0.67, [edgy](../../../../traits/instructions/edgy.json) 0.54, [absurdist](../../../../roles/instructions/absurdist.json) (role) 0.53 | new |
| prudish (`prudish#1`) | censuses | 0.80 | 0.281 | novel_like | [judgmental](../../../../traits/instructions/judgmental.json) 0.54, [cliquish](../../../../traits/instructions/cliquish.json) 0.49, [lustful](../../../../traits/instructions/lustful.json) 0.49 | new |
| malleable (`malleable#1`) | censuses | 0.80 | 0.281 | novel_like | [submissive](../../../../traits/instructions/submissive.json) 0.58, [accommodating](../../../../traits/instructions/accommodating.json) 0.56, [untrustworthy](../../../../traits/instructions/untrustworthy.json) 0.55 | new |
| overstepping (`overstepping#1`) | censuses | 0.80 | 0.280 | ordinary | [dominant](../../../../traits/instructions/dominant.json) 0.57, [malicious](../../../../traits/instructions/malicious.json) 0.57, [scheming](../../../../traits/instructions/scheming.json) 0.55 | new |
| deft (`deft#1`) | censuses | 0.78 | 0.276 | ordinary | [efficient](../../../../traits/instructions/efficient.json) 0.55, [concise](../../../../traits/instructions/concise.json) 0.47, [witty](../../../../traits/instructions/witty.json) 0.44 | new |
| clandestine (`clandestine#1`) | censuses | 0.75 | 0.267 | ordinary | [scheming](../../../../traits/instructions/scheming.json) 0.69, [criminal](../../../../roles/instructions/criminal.json) (role) 0.57, [spy](../../../../roles/instructions/spy.json) (role) 0.56 | new |
| urgent (`urgent#1`) | antonym_check, roget, censuses | 0.72 | 0.261 | ordinary | [hurried](../../../../traits/instructions/hurried.json) 0.70, [impatient](../../../../traits/instructions/impatient.json) 0.63, [decisive](../../../../traits/instructions/decisive.json) 0.55 | covered by [hurried](../../../../traits/instructions/hurried.json) |
| disobedient (`disobedient#1`) | censuses, wn_clusters | 0.71 | 0.259 | ordinary | [rebellious](../../../../traits/instructions/rebellious.json) 0.69, [untrustworthy](../../../../traits/instructions/untrustworthy.json) 0.64, [hostile](../../../../traits/instructions/hostile.json) 0.57 | new |
| phony (`phony#1`) | censuses | 0.66 | 0.247 | ordinary | [deceitful](../../../../traits/instructions/deceitful.json) 0.58, [dishonest](../../../../traits/instructions/dishonest.json) 0.58, [scheming](../../../../traits/instructions/scheming.json) 0.54 | new |
| rugged (`rugged#1`) | censuses | 0.66 | 0.247 | ordinary | [unforgiving](../../../../traits/instructions/unforgiving.json) 0.60, [independent](../../../../traits/instructions/independent.json) 0.59, [aggressive](../../../../traits/instructions/aggressive.json) 0.59 | new |
| masochistic (`masochistic#1`) | censuses, wn_clusters | 0.63 | 0.242 | ordinary | [hedonistic](../../../../traits/instructions/hedonistic.json) 0.61, [malicious](../../../../traits/instructions/malicious.json) 0.60, [untrustworthy](../../../../traits/instructions/untrustworthy.json) 0.57 | new |
| parasitic (`parasitic#1`) | censuses, roget | 0.61 | 0.237 | duplicate_like | [greedy](../../../../traits/instructions/greedy.json) 0.77, [malicious](../../../../traits/instructions/malicious.json) 0.73, [parasite](../../../../roles/instructions/parasite.json) (role) 0.73 | new |
| repressed (`repressed#1`) | censuses | 0.56 | 0.232 | ordinary | [reserved](../../../../traits/instructions/reserved.json) 0.67, [avoidant](../../../../traits/instructions/avoidant.json) 0.53, [temperamental](../../../../traits/instructions/temperamental.json) 0.53 | new |
| irrestrainable (`irrestrainable#1`) | censuses | 0.56 | 0.232 | ordinary | [reactive](../../../../traits/instructions/reactive.json) 0.70, [impulsive](../../../../traits/instructions/impulsive.json) 0.68, [hedonistic](../../../../traits/instructions/hedonistic.json) 0.62 | covered by [impulsive](../../../../traits/instructions/impulsive.json) |
| overmasculine (`overmasculine#1`) | censuses | 0.56 | 0.231 | ordinary | [aggressive](../../../../traits/instructions/aggressive.json) 0.65, [competitive](../../../../traits/instructions/competitive.json) 0.63, [dominant](../../../../traits/instructions/dominant.json) 0.62 | covered by [masculine](../../../../traits/instructions/masculine.json) |
| meddling (`meddling#1`) | censuses | 0.51 | 0.220 | ordinary | [malicious](../../../../traits/instructions/malicious.json) 0.53, [gossip](../../../../roles/instructions/gossip.json) (role) 0.52, [unhelpful](../../../../traits/instructions/unhelpful.json) 0.52 | new |
| concealing (`concealing#1`) | censuses, alignment_sweep | 0.50 | 0.220 | ordinary | [opaque](../../../../traits/instructions/opaque.json) 0.64, [dishonest](../../../../traits/instructions/dishonest.json) 0.64, [scheming](../../../../traits/instructions/scheming.json) 0.63 | new |
| purposive (`purposive#1`) | censuses | 0.49 | 0.215 | ordinary | [decisive](../../../../traits/instructions/decisive.json) 0.60, [closure-seeking](../../../../traits/instructions/closure_seeking.json) 0.59, [methodical](../../../../traits/instructions/methodical.json) 0.54 | new |
| overdiligent (`overdiligent#1`) | censuses | 0.49 | 0.215 | ordinary | [meticulous](../../../../traits/instructions/meticulous.json) 0.69, [perfectionist](../../../../traits/instructions/perfectionist.json) 0.67, [conscientious](../../../../traits/instructions/conscientious.json) 0.58 | new |
| jumpy (`jumpy#1`) | censuses, states_pass | 0.48 | 0.213 | ordinary | [anxious](../../../../traits/instructions/anxious.json) 0.71, [temperamental](../../../../traits/instructions/temperamental.json) 0.63, [fragile](../../../../traits/instructions/fragile.json) 0.58 | new |
| minimizing (`minimizing#1`) | censuses | 0.47 | 0.210 | ordinary | [understated](../../../../traits/instructions/understated.json) 0.61, [avoidant](../../../../traits/instructions/avoidant.json) 0.55, [dishonest](../../../../traits/instructions/dishonest.json) 0.54 | new |
| pathetic (`pathetic#1`) | censuses, base_model | 0.39 | 0.194 | ordinary | [fragile](../../../../traits/instructions/fragile.json) 0.71, [untrustworthy](../../../../traits/instructions/untrustworthy.json) 0.70, [unreliable](../../../../traits/instructions/unreliable.json) 0.68 | new |
| chattering (`chattering#1`) | censuses | 0.35 | 0.188 | ordinary | [entertaining](../../../../traits/instructions/entertaining.json) 0.66, [witty](../../../../traits/instructions/witty.json) 0.66, [playful](../../../../traits/instructions/playful.json) 0.60 | new |
| adorable (`adorable#1`) | censuses | 0.35 | 0.186 | ordinary | [flirty](../../../../traits/instructions/flirty.json) 0.63, [charismatic](../../../../traits/instructions/charismatic.json) 0.62, [gregarious](../../../../traits/instructions/gregarious.json) 0.61 | new |
| nosy (`nosy#1`) | censuses, states_pass | 0.29 | 0.176 | ordinary | [unhelpful](../../../../traits/instructions/unhelpful.json) 0.64, [malicious](../../../../traits/instructions/malicious.json) 0.62, [sociopathic](../../../../traits/instructions/sociopathic.json) 0.58 | new |
| morose (`morose#1`) | censuses, wn_clusters, base_model | 0.29 | 0.176 | ordinary | [bitter](../../../../traits/instructions/bitter.json) 0.65, [callous](../../../../traits/instructions/callous.json) 0.60, [unhelpful](../../../../traits/instructions/unhelpful.json) 0.59 | new |

## Bottom 30 by residual percentile

| candidate | generators | residual pct | residual | flag | nearest (cos) | M3 |
|---|---|---|---|---|---|---|
| crude (`crude#1`) | censuses, roget, base_model | 0.02 | 0.086 | duplicate_like | [flippant](../../../../traits/instructions/flippant.json) 0.74, [irreverent](../../../../traits/instructions/irreverent.json) 0.71, [sardonic](../../../../traits/instructions/sardonic.json) 0.69 | new |
| derisive (`derisive#1`) | censuses, roget, base_model, states_pass | 0.09 | 0.133 | duplicate_like | [sardonic](../../../../traits/instructions/sardonic.json) 0.82, [sarcastic](../../../../traits/instructions/sarcastic.json) 0.81, [wry](../../../../traits/instructions/wry.json) 0.78 | new |
| unladylike (`unladylike#1`) | censuses | 0.12 | 0.139 | ordinary | [flippant](../../../../traits/instructions/flippant.json) 0.68, [sassy](../../../../traits/instructions/sassy.json) 0.68, [edgy](../../../../traits/instructions/edgy.json) 0.67 | new |
| flattering (`flattering#1`) | censuses, alignment_sweep | 0.20 | 0.155 | duplicate_like | [sycophantic](../../../../traits/instructions/sycophantic.json) 0.75, [flirty](../../../../traits/instructions/flirty.json) 0.67, [accommodating](../../../../traits/instructions/accommodating.json) 0.57 | new |
| obscene (`obscene#1`) | censuses | 0.26 | 0.170 | ordinary | [edgy](../../../../traits/instructions/edgy.json) 0.67, [sarcastic](../../../../traits/instructions/sarcastic.json) 0.66, [sardonic](../../../../traits/instructions/sardonic.json) 0.63 | new |
| insulting (`insulting#1`) | censuses | 0.27 | 0.172 | duplicate_like | [sarcastic](../../../../traits/instructions/sarcastic.json) 0.75, [hostile](../../../../traits/instructions/hostile.json) 0.69, [condescending](../../../../traits/instructions/condescending.json) 0.64 | new |
| morose (`morose#1`) | censuses, wn_clusters, base_model | 0.29 | 0.176 | ordinary | [bitter](../../../../traits/instructions/bitter.json) 0.65, [callous](../../../../traits/instructions/callous.json) 0.60, [unhelpful](../../../../traits/instructions/unhelpful.json) 0.59 | new |
| nosy (`nosy#1`) | censuses, states_pass | 0.29 | 0.176 | ordinary | [unhelpful](../../../../traits/instructions/unhelpful.json) 0.64, [malicious](../../../../traits/instructions/malicious.json) 0.62, [sociopathic](../../../../traits/instructions/sociopathic.json) 0.58 | new |
| adorable (`adorable#1`) | censuses | 0.35 | 0.186 | ordinary | [flirty](../../../../traits/instructions/flirty.json) 0.63, [charismatic](../../../../traits/instructions/charismatic.json) 0.62, [gregarious](../../../../traits/instructions/gregarious.json) 0.61 | new |
| chattering (`chattering#1`) | censuses | 0.35 | 0.188 | ordinary | [entertaining](../../../../traits/instructions/entertaining.json) 0.66, [witty](../../../../traits/instructions/witty.json) 0.66, [playful](../../../../traits/instructions/playful.json) 0.60 | new |
| pathetic (`pathetic#1`) | censuses, base_model | 0.39 | 0.194 | ordinary | [fragile](../../../../traits/instructions/fragile.json) 0.71, [untrustworthy](../../../../traits/instructions/untrustworthy.json) 0.70, [unreliable](../../../../traits/instructions/unreliable.json) 0.68 | new |
| minimizing (`minimizing#1`) | censuses | 0.47 | 0.210 | ordinary | [understated](../../../../traits/instructions/understated.json) 0.61, [avoidant](../../../../traits/instructions/avoidant.json) 0.55, [dishonest](../../../../traits/instructions/dishonest.json) 0.54 | new |
| jumpy (`jumpy#1`) | censuses, states_pass | 0.48 | 0.213 | ordinary | [anxious](../../../../traits/instructions/anxious.json) 0.71, [temperamental](../../../../traits/instructions/temperamental.json) 0.63, [fragile](../../../../traits/instructions/fragile.json) 0.58 | new |
| overdiligent (`overdiligent#1`) | censuses | 0.49 | 0.215 | ordinary | [meticulous](../../../../traits/instructions/meticulous.json) 0.69, [perfectionist](../../../../traits/instructions/perfectionist.json) 0.67, [conscientious](../../../../traits/instructions/conscientious.json) 0.58 | new |
| purposive (`purposive#1`) | censuses | 0.49 | 0.215 | ordinary | [decisive](../../../../traits/instructions/decisive.json) 0.60, [closure-seeking](../../../../traits/instructions/closure_seeking.json) 0.59, [methodical](../../../../traits/instructions/methodical.json) 0.54 | new |
| concealing (`concealing#1`) | censuses, alignment_sweep | 0.50 | 0.220 | ordinary | [opaque](../../../../traits/instructions/opaque.json) 0.64, [dishonest](../../../../traits/instructions/dishonest.json) 0.64, [scheming](../../../../traits/instructions/scheming.json) 0.63 | new |
| meddling (`meddling#1`) | censuses | 0.51 | 0.220 | ordinary | [malicious](../../../../traits/instructions/malicious.json) 0.53, [gossip](../../../../roles/instructions/gossip.json) (role) 0.52, [unhelpful](../../../../traits/instructions/unhelpful.json) 0.52 | new |
| overmasculine (`overmasculine#1`) | censuses | 0.56 | 0.231 | ordinary | [aggressive](../../../../traits/instructions/aggressive.json) 0.65, [competitive](../../../../traits/instructions/competitive.json) 0.63, [dominant](../../../../traits/instructions/dominant.json) 0.62 | covered by [masculine](../../../../traits/instructions/masculine.json) |
| irrestrainable (`irrestrainable#1`) | censuses | 0.56 | 0.232 | ordinary | [reactive](../../../../traits/instructions/reactive.json) 0.70, [impulsive](../../../../traits/instructions/impulsive.json) 0.68, [hedonistic](../../../../traits/instructions/hedonistic.json) 0.62 | covered by [impulsive](../../../../traits/instructions/impulsive.json) |
| repressed (`repressed#1`) | censuses | 0.56 | 0.232 | ordinary | [reserved](../../../../traits/instructions/reserved.json) 0.67, [avoidant](../../../../traits/instructions/avoidant.json) 0.53, [temperamental](../../../../traits/instructions/temperamental.json) 0.53 | new |
| parasitic (`parasitic#1`) | censuses, roget | 0.61 | 0.237 | duplicate_like | [greedy](../../../../traits/instructions/greedy.json) 0.77, [malicious](../../../../traits/instructions/malicious.json) 0.73, [parasite](../../../../roles/instructions/parasite.json) (role) 0.73 | new |
| masochistic (`masochistic#1`) | censuses, wn_clusters | 0.63 | 0.242 | ordinary | [hedonistic](../../../../traits/instructions/hedonistic.json) 0.61, [malicious](../../../../traits/instructions/malicious.json) 0.60, [untrustworthy](../../../../traits/instructions/untrustworthy.json) 0.57 | new |
| rugged (`rugged#1`) | censuses | 0.66 | 0.247 | ordinary | [unforgiving](../../../../traits/instructions/unforgiving.json) 0.60, [independent](../../../../traits/instructions/independent.json) 0.59, [aggressive](../../../../traits/instructions/aggressive.json) 0.59 | new |
| phony (`phony#1`) | censuses | 0.66 | 0.247 | ordinary | [deceitful](../../../../traits/instructions/deceitful.json) 0.58, [dishonest](../../../../traits/instructions/dishonest.json) 0.58, [scheming](../../../../traits/instructions/scheming.json) 0.54 | new |
| disobedient (`disobedient#1`) | censuses, wn_clusters | 0.71 | 0.259 | ordinary | [rebellious](../../../../traits/instructions/rebellious.json) 0.69, [untrustworthy](../../../../traits/instructions/untrustworthy.json) 0.64, [hostile](../../../../traits/instructions/hostile.json) 0.57 | new |
| urgent (`urgent#1`) | antonym_check, roget, censuses | 0.72 | 0.261 | ordinary | [hurried](../../../../traits/instructions/hurried.json) 0.70, [impatient](../../../../traits/instructions/impatient.json) 0.63, [decisive](../../../../traits/instructions/decisive.json) 0.55 | covered by [hurried](../../../../traits/instructions/hurried.json) |
| clandestine (`clandestine#1`) | censuses | 0.75 | 0.267 | ordinary | [scheming](../../../../traits/instructions/scheming.json) 0.69, [criminal](../../../../roles/instructions/criminal.json) (role) 0.57, [spy](../../../../roles/instructions/spy.json) (role) 0.56 | new |
| deft (`deft#1`) | censuses | 0.78 | 0.276 | ordinary | [efficient](../../../../traits/instructions/efficient.json) 0.55, [concise](../../../../traits/instructions/concise.json) 0.47, [witty](../../../../traits/instructions/witty.json) 0.44 | new |
| overstepping (`overstepping#1`) | censuses | 0.80 | 0.280 | ordinary | [dominant](../../../../traits/instructions/dominant.json) 0.57, [malicious](../../../../traits/instructions/malicious.json) 0.57, [scheming](../../../../traits/instructions/scheming.json) 0.55 | new |
| malleable (`malleable#1`) | censuses | 0.80 | 0.281 | novel_like | [submissive](../../../../traits/instructions/submissive.json) 0.58, [accommodating](../../../../traits/instructions/accommodating.json) 0.56, [untrustworthy](../../../../traits/instructions/untrustworthy.json) 0.55 | new |
