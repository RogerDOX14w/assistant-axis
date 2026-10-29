# Cap pilot: the judge's view of a cut, paired per response

Written by [cut_readout.py](./cut_readout.py) from `roger/cap_pilot/` ([cap1024](../../../roger/cap_pilot/cap1024/), [cap1024_cut256](../../../roger/cap_pilot/cap1024_cut256/), [cap1024_cut512](../../../roger/cap_pilot/cap1024_cut512/), [cap1024_cut768](../../../roger/cap_pilot/cap1024_cut768/); plan § 5 item 2, [plan_max_tokens_pilot.md](../plan_max_tokens_pilot.md)).  The cap1024 responses cut at N tokens and judged with the cut marked, against the same responses judged whole; a response shorter than N keeps its whole score.  Keep is score 3.  *K→D* and *D→K*: cut responses whose verdict went from keep to drop, and from drop to keep, when the ending was cut.  *Δ*: the change in the entity's keep share over all its responses, in points.  *p*: exact two-sided sign test on K→D against D→K (McNemar's).

## Roles (20)

Judge noise, for scale: cap512's cut responses judged twice change verdict 2.1% of the time (53 K→D, 52 D→K of 5038), about evenly both ways; a cut's effect is the imbalance between K→D and D→K beyond that.

| Cut | Cut responses | K→D | D→K | Changed | Keep, whole | **Keep, cut** | Δ (points) | p |
|---|---|---|---|---|---|---|---|---|
| 256 | 8,781 | 189 | 125 | 3.6% | 92.2% | **91.5%** | -0.6 | 0.00036 |
| 512 | 4,922 | 108 | 51 | 3.2% | 92.2% | **91.6%** | -0.6 | 7.2e-06 |
| 768 | 2,493 | 44 | 23 | 2.7% | 92.2% | **92.0%** | -0.2 | 0.014 |

Per role, lowest whole keep share first: Δ in points at each cut, with K→D / D→K among its cut responses.

| Role | Keep, whole | Δ at 256 | Δ at 512 | Δ at 768 |
|---|---|---|---|---|
| [reviewer](../../../data/roles/instructions/reviewer.json) | 55% | +0.0 (51/51) | -3.2 (39/23) | -2.0 (17/7) |
| [aberration](../../../data/roles/instructions/aberration.json) | 83% | -1.2 (24/18) | -1.4 (12/5) | +0.2 (1/2) |
| [athlete](../../../data/roles/instructions/athlete.json) | 86% | -1.4 (7/0) | -0.4 (3/1) | -0.2 (1/0) |
| [auditor](../../../data/roles/instructions/auditor.json) | 87% | +0.0 (15/15) | -1.6 (14/6) | -0.8 (7/3) |
| [editor](../../../data/roles/instructions/editor.json) | 87% | -1.4 (9/2) | -0.2 (2/1) | -0.2 (1/0) |
| [artist](../../../data/roles/instructions/artist.json) | 90% | -4.4 (26/4) | -2.2 (12/1) | -0.6 (5/2) |
| [historian](../../../data/roles/instructions/historian.json) | 91% | +0.6 (4/7) | +0.8 (1/5) | +0.0 (2/2) |
| [geographer](../../../data/roles/instructions/geographer.json) | 94% | +0.8 (3/7) | -0.4 (4/2) | -0.4 (3/1) |
| [scholar](../../../data/roles/instructions/scholar.json) | 96% | +0.8 (0/4) | +0.8 (0/4) | +0.2 (1/2) |
| [biologist](../../../data/roles/instructions/biologist.json) | 96% | -0.6 (6/3) | -1.2 (6/0) | -0.4 (3/1) |
| [anthropologist](../../../data/roles/instructions/anthropologist.json) | 97% | -0.2 (3/2) | -0.4 (3/1) | +0.4 (0/2) |
| [bohemian](../../../data/roles/instructions/bohemian.json) | 97% | -1.6 (9/1) | -0.6 (4/1) | +0.0 (0/0) |
| [actor](../../../data/roles/instructions/actor.json) | 97% | +0.4 (2/4) | +0.2 (0/1) | +0.2 (0/1) |
| [gamer](../../../data/roles/instructions/gamer.json) | 97% | -0.2 (1/0) | +0.0 (0/0) | +0.0 (0/0) |
| [peasant](../../../data/roles/instructions/peasant.json) | 98% | -0.2 (1/0) | -0.2 (1/0) | +0.0 (0/0) |
| [sociologist](../../../data/roles/instructions/sociologist.json) | 98% | -0.2 (4/3) | -0.6 (3/0) | -0.2 (1/0) |
| [surfer](../../../data/roles/instructions/surfer.json) | 98% | -1.2 (6/0) | -0.8 (4/0) | -0.4 (2/0) |
| [gossip](../../../data/roles/instructions/gossip.json) | 99% | -0.2 (3/2) | +0.0 (0/0) | +0.0 (0/0) |
| [trickster](../../../data/roles/instructions/trickster.json) | 99% | -2.8 (15/1) | +0.0 (0/0) | +0.0 (0/0) |
| [pirate](../../../data/roles/instructions/pirate.json) | 99% | +0.2 (0/1) | +0.0 (0/0) | +0.0 (0/0) |

Equivalence check (different responses): cap512's own keep share 91.9%, cap1024 cut at 512 91.6%; cap512 against cap512b, two generations at the same cap, 91.9% against 91.7%.

## Traits (22)

Judge noise, for scale: cap512's cut responses judged twice change verdict 3.8% of the time (74 K→D, 71 D→K of 3805), about evenly both ways; a cut's effect is the imbalance between K→D and D→K beyond that.

| Cut | Cut responses | K→D | D→K | Changed | Keep, whole | **Keep, cut** | Δ (points) | p |
|---|---|---|---|---|---|---|---|---|
| 256 | 7,803 | 391 | 114 | 6.5% | 81.9% | **79.4%** | -2.5 | 1.6e-36 |
| 512 | 3,745 | 148 | 58 | 5.5% | 81.9% | **81.1%** | -0.8 | 2.9e-10 |
| 768 | 1,722 | 45 | 29 | 4.3% | 81.9% | **81.7%** | -0.1 | 0.081 |

Per trait, lowest whole keep share first: Δ in points at each cut, with K→D / D→K among its cut responses.

| Trait | Keep, whole | Δ at 256 | Δ at 512 | Δ at 768 |
|---|---|---|---|---|
| [neglectful](../../../data/traits/instructions/neglectful.json) | 31% | -0.6 (4/1) | -0.2 (1/0) | +0.0 (0/0) |
| [financially_secure](../../../data/traits/instructions/financially_secure.json) | 33% | -6.8 (41/7) | -1.0 (19/14) | +1.0 (2/7) |
| [gay_affirming](../../../data/traits/instructions/gay_affirming.json) | 42% | -10.6 (57/4) | -4.2 (21/0) | -0.4 (3/1) |
| [unhappily_partnered](../../../data/traits/instructions/unhappily_partnered.json) | 58% | -4.8 (37/13) | -3.0 (16/1) | -0.6 (3/0) |
| [ethnocentric](../../../data/traits/instructions/ethnocentric.json) | 63% | -0.6 (4/1) | -0.4 (2/0) | +0.0 (0/0) |
| [psychopathic_dark_tetrad](../../../data/traits/instructions/psychopathic_dark_tetrad.json) | 77% | -4.6 (32/9) | +0.0 (2/2) | +0.2 (0/1) |
| [motivated_reasoning_immune](../../../data/traits/instructions/motivated_reasoning_immune.json) | 83% | -14.2 (85/14) | -6.0 (40/10) | -1.8 (17/8) |
| [neurotic_big_five](../../../data/traits/instructions/neurotic_big_five.json) | 83% | -1.6 (18/10) | +0.6 (4/7) | -0.2 (4/3) |
| [bold](../../../data/traits/instructions/bold.json) | 84% | -5.0 (30/5) | -0.6 (6/3) | -0.2 (1/0) |
| [sentimental](../../../data/traits/instructions/sentimental.json) | 90% | -1.8 (25/16) | -1.0 (9/4) | -0.6 (3/0) |
| [visual_vark](../../../data/traits/instructions/visual_vark.json) | 93% | -2.6 (16/3) | -1.6 (14/6) | -0.8 (8/4) |
| [clear](../../../data/traits/instructions/clear.json) | 94% | +0.0 (0/0) | +0.0 (0/0) | no response that long |
| [elitist](../../../data/traits/instructions/elitist.json) | 95% | -1.2 (10/4) | +0.0 (0/0) | +0.0 (0/0) |
| [well_behaved](../../../data/traits/instructions/well_behaved.json) | 95% | -1.6 (15/7) | -0.8 (5/1) | +0.0 (1/1) |
| [witty](../../../data/traits/instructions/witty.json) | 96% | +0.2 (2/3) | +0.2 (0/1) | +0.2 (0/1) |
| [challenging](../../../data/traits/instructions/challenging.json) | 96% | +0.6 (3/6) | +0.0 (3/3) | +0.0 (0/0) |
| [blood_type_a](../../../data/traits/instructions/blood_type_a.json) | 97% | -0.6 (6/3) | +0.4 (1/3) | +0.4 (0/2) |
| [verbose](../../../data/traits/instructions/verbose.json) | 97% | +1.0 (2/7) | +0.0 (3/3) | -0.4 (3/1) |
| [moderate](../../../data/traits/instructions/moderate.json) | 98% | +0.0 (1/1) | -0.2 (1/0) | +0.0 (0/0) |
| [pensive](../../../data/traits/instructions/pensive.json) | 98% | +0.0 (0/0) | +0.0 (0/0) | no response that long |
| [concise](../../../data/traits/instructions/concise.json) | 98% | no response that long | no response that long | no response that long |
| [infp_mbti](../../../data/traits/instructions/infp_mbti.json) | 99% | -0.6 (3/0) | -0.2 (1/0) | +0.0 (0/0) |

Equivalence check (different responses): cap512's own keep share 81.0%, cap1024 cut at 512 81.1%; cap512 against cap512b, two generations at the same cap, 81.0% against 80.7%.

