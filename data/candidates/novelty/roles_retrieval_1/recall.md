# Role retrieval check: `roles_retrieval_1`

Coding plan 16, § 7b (decision 11): each of the 339 corpus roles glossed afresh by the role gloss call with no reading ([role_gloss.md](../../../../reports/trait_gap_generation/rubrics/role_gloss.md)), its gloss queried against the full role index (the role stays in), recall at 10 of the role's own stem.  Acceptance: the production form (`role_gloss_w14`, centred space) at 95% or above; the label-kept form (`label_gloss`) is reported beside it (Roger, 2026-10-22).  The arms are run only below the line, on the same glosses at no new call.

**Production form recall at 10: 0.9794 (at or above 95%: M2's settings stay for roles)**

| form | space | recall at k | MRR | missed | role |
|---|---|---|---|---|---|
| `role_gloss_w14` | centred | 0.9794 | 0.8748 | 7 | production |
| `label_gloss` | centred | 1.0 | 1.0 | 0 | information |

Chosen setting: `role_gloss_w14`, centred space (recall 0.9794): M2's settings stay.

## Recall by kind (production form)

| kind | roles | recall at k |
|---|---|---|
| circumstance | 24 | 0.9583 |
| non_human | 44 | 1.0 |
| occupation | 162 | 0.9815 |
| other | 3 | 1.0 |
| pastime | 8 | 1.0 |
| relationship | 20 | 0.95 |
| stance | 47 | 0.9787 |
| status | 9 | 1.0 |
| temperament | 22 | 0.9545 |

## Misses of the production form (7)

A gloss written for another sense of the label counts as a miss and shows here; read the glosses.

- [philosopher](../../../roles/instructions/philosopher.json) (occupation): rank 84; nearest scholar, librarian, student.  Gloss: A philosopher is someone who spends long days in a university office or a library carrel, reading and arguing over texts, writing papers on questions of knowledge, ethics and meaning, and teaching seminars to undergraduates.
- [comedian](../../../roles/instructions/comedian.json) (occupation): rank 25; nearest bartender, prey, workaholic.  Gloss: A comedian is someone who stands alone under a spotlight in a club or theater, works a crowd for forty minutes, and rewrites jokes after every set that falls flat.
- [gossip](../../../roles/instructions/gossip.json) (temperament): rank 21; nearest flaneur, gym_rat, monk.  Gloss: A gossip is someone who spends the morning at the back fence, the church steps, or the kitchen table passing along what neighbors did last night, adding a detail or two each time it is told.
- [mystic](../../../roles/instructions/mystic.json) (stance): rank 17; nearest hermit, monk, ascetic.  Gloss: A mystic is someone who withdraws to a quiet room before dawn to sit in long silences, seeking direct union with the divine and recording visions in a worn notebook for the few students who visit.
- [oracle](../../../roles/instructions/oracle.json) (occupation): rank 16; nearest monk, shaman, tree.  Gloss: An oracle is someone who sits in a temple's inner chamber, breathes the vapors rising from a cleft in the rock, and answers pilgrims' questions with prophecies from the god.
- [marginalized](../../../roles/instructions/marginalized.json) (circumstance): rank 13; nearest homeless, laborer, pauper.  Gloss: A marginalized is someone who works day labor in the city's outer districts, sleeps in a shelter bed when it is open, and is passed over for every housing list and clinic appointment.
- [grandparent](../../../roles/instructions/grandparent.json) (relationship): rank 12; nearest grandparent_caregiver, orphan, widow.  Gloss: A grandparent is someone who raises no one anymore but still keeps a drawer of hard candy and a stack of photographs for grandchildren who visit on holidays and summer weekends.
