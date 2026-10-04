# Rendered prompts of the overlap test

The requests exactly as the model receives them (rubric as the system prompt, one JSON object as the user turn), for 3 variants and the rubrics A2, C2, D2, E2; settings shown for claude-sonnet-5-5.  Within a pass every rubric and model receives the identical user turn.

## Variant: antonym_in_list (nn:adventurous)

Listed (id: stem, group, recorded opposite): 1: adventurous_eater, nearest; 2: unadventurous, nearest, opposite; 3: risk_seeking, nearest

```text
=== rubric A2 (overlap_concept_implies), nn:adventurous, request settings {"model": "claude-sonnet-5-5", "max_tokens": 2048} ===
--- system ---
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how similar its concept is to the target's: are they the same concept, or different concepts?

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers for each listed trait:
- 4: the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- 3: the same concept, differing only in scope, degree or emphasis. The test: anyone who has one of the two traits has the other too, at least in one direction: a fussy eater is fussy, a boastful person is proud, a miserly person is penny-pinching, though not necessarily the reverse. The richer one may be the plainer one narrowed to a domain, carried further, or with something added. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further.
- 2: overlapping concepts. They share a core, but neither implies the other: a persona can have either without the other, as a studious person need not be bookish and a bookish one need not be studious; each adds something the other lacks.
- 1: related but distinct concepts: neighbours, not the same concept. For example, tetchy and sullen: both are bad-tempered, but quick irritation is a different thing from silent resentment.
- 0: different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "opposite": the listed trait is the reverse of the target, the same quality at the other end. For example, cheery and morose.
- "unsure": you cannot tell from the two descriptions.

For each listed trait give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed trait's id>, "reason": "<one short sentence>", "similarity": 0|1|2|3|4|"opposite"|"unsure"}]}
Return one row per listed trait, in the order given.
--- user ---
{"target": {"label": "adventurous", "description": "This means seeking out the new and the untried: saying yes to the unfamiliar place, food or plan, taking the unknown route for the thrill of it, and growing restless in any routine."},
 "traits": [
  {"id": 1, "label": "adventurous-eater", "description": "This means ordering the dish nobody recognizes, trying the offal, the fermented and the fiery, and treating every unfamiliar menu as a dare."},
  {"id": 2, "label": "unadventurous", "description": "This means keeping to the familiar and the safe: saying no to the unfamiliar place, food or plan, taking the known route every time, and growing uneasy outside routine."},
  {"id": 3, "label": "risk-seeking", "description": "This involves taking bold actions, experimentation, willingness to face uncertainty, and venturing into unproven territory even when outcomes are not guaranteed."}
 ]}
```

```text
=== rubric C2 (overlap_six_implies), nn:adventurous, request settings {"model": "claude-sonnet-5-5", "max_tokens": 2048} ===
--- system ---
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how similar its concept is to the target's: are they the same concept, or different concepts?

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers for each listed trait:
- 5: the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- 4: the same concept, differing only in degree, strength or emphasis; neither adds anything the other lacks. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further.
- 3: one contains the other: one of the two is the other narrowed to a single domain, or the other with something more added to it. The test: anyone with the richer trait has the plainer one too, but not the reverse: a fussy eater is fussy, a boastful person is proud. A stronger or milder form of the same trait is a 4, not a 3.
- 2: overlapping concepts. They share a core, but neither implies the other: a persona can have either without the other, as a studious person need not be bookish and a bookish one need not be studious; each adds something the other lacks.
- 1: related but distinct concepts: neighbours, not the same concept. For example, tetchy and sullen: both are bad-tempered, but quick irritation is a different thing from silent resentment.
- 0: different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "opposite": the listed trait is the reverse of the target, the same quality at the other end. For example, cheery and morose.
- "unsure": you cannot tell from the two descriptions.

For each listed trait give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed trait's id>, "reason": "<one short sentence>", "similarity": 0|1|2|3|4|5|"opposite"|"unsure"}]}
Return one row per listed trait, in the order given.
--- user ---
{"target": {"label": "adventurous", "description": "This means seeking out the new and the untried: saying yes to the unfamiliar place, food or plan, taking the unknown route for the thrill of it, and growing restless in any routine."},
 "traits": [
  {"id": 1, "label": "adventurous-eater", "description": "This means ordering the dish nobody recognizes, trying the offal, the fermented and the fiery, and treating every unfamiliar menu as a dare."},
  {"id": 2, "label": "unadventurous", "description": "This means keeping to the familiar and the safe: saying no to the unfamiliar place, food or plan, taking the known route every time, and growing uneasy outside routine."},
  {"id": 3, "label": "risk-seeking", "description": "This involves taking bold actions, experimentation, willingness to face uncertainty, and venturing into unproven territory even when outcomes are not guaranteed."}
 ]}
```

```text
=== rubric D2 (overlap_relation_implies), nn:adventurous, request settings {"model": "claude-sonnet-5-5", "max_tokens": 2048} ===
--- system ---
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how its concept is related to the target's.

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers for each listed trait:
- "same": the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- "variant": the same concept, differing only in degree, strength or emphasis; neither adds anything the other lacks. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further.
- "contains": one of the two is the other narrowed to a single domain, or the other with something more added to it. The test: anyone with the richer trait has the plainer one too, but not the reverse: a fussy eater is fussy, a boastful person is proud. A stronger or milder form of the same trait is "variant", not "contains". The plainer one is the wider; say which it is.
- "overlap": overlapping concepts. They share a core, but neither implies the other: a persona can have either without the other, as a studious person need not be bookish and a bookish one need not be studious; each adds something the other lacks.
- "neighbours": related but distinct concepts: neighbours, not the same concept. For example, tetchy and sullen: both are bad-tempered, but quick irritation is a different thing from silent resentment.
- "different": different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "opposite": the listed trait is the reverse of the target, the same quality at the other end. For example, cheery and morose.
- "unsure": you cannot tell from the two descriptions.

For each listed trait give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed trait's id>, "reason": "<one short sentence>", "relation": "same"|"variant"|"contains"|"overlap"|"neighbours"|"different"|"opposite"|"unsure", "wider": "target"|"listed"}]}
Give "wider" only when the relation is "contains". Return one row per listed trait, in the order given.
--- user ---
{"target": {"label": "adventurous", "description": "This means seeking out the new and the untried: saying yes to the unfamiliar place, food or plan, taking the unknown route for the thrill of it, and growing restless in any routine."},
 "traits": [
  {"id": 1, "label": "adventurous-eater", "description": "This means ordering the dish nobody recognizes, trying the offal, the fermented and the fiery, and treating every unfamiliar menu as a dare."},
  {"id": 2, "label": "unadventurous", "description": "This means keeping to the familiar and the safe: saying no to the unfamiliar place, food or plan, taking the known route every time, and growing uneasy outside routine."},
  {"id": 3, "label": "risk-seeking", "description": "This involves taking bold actions, experimentation, willingness to face uncertainty, and venturing into unproven territory even when outcomes are not guaranteed."}
 ]}
```

```text
=== rubric E2 (overlap_scope_implies), nn:adventurous, request settings {"model": "claude-sonnet-5-5", "max_tokens": 2048} ===
--- system ---
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how similar its concept is to the target's: are they the same concept, or different concepts?

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers for each listed trait:
- 4: the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- 3: the same concept, differing only in scope, degree, strength or emphasis. One may be the other narrowed to a single domain, or broadened beyond it; a stronger or a milder form of it; or the same thing with the stress elsewhere. What the wider or stronger one adds is more of the same, not something new. The test: anyone who has one of the two traits has the other too, at least in one direction: a fussy eater is fussy, a boastful person is proud, though not necessarily the reverse. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further. Or fussy and fussy eater: the same fussiness, narrowed to food. In the reason, say which: narrowed, broadened, stronger, milder, or a shift of emphasis.
- 2: overlapping concepts. They share a core, but neither implies the other: a persona can have either without the other, as a studious person need not be bookish and a bookish one need not be studious; each adds something the other lacks.
- 1: related but distinct concepts: neighbours, not the same concept. For example, tetchy and sullen: both are bad-tempered, but quick irritation is a different thing from silent resentment.
- 0: different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "opposite": the listed trait is the reverse of the target, the same quality at the other end. For example, cheery and morose.
- "unsure": you cannot tell from the two descriptions.

For each listed trait give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed trait's id>, "reason": "<one short sentence>", "similarity": 0|1|2|3|4|"opposite"|"unsure"}]}
Return one row per listed trait, in the order given.
--- user ---
{"target": {"label": "adventurous", "description": "This means seeking out the new and the untried: saying yes to the unfamiliar place, food or plan, taking the unknown route for the thrill of it, and growing restless in any routine."},
 "traits": [
  {"id": 1, "label": "adventurous-eater", "description": "This means ordering the dish nobody recognizes, trying the offal, the fermented and the fiery, and treating every unfamiliar menu as a dare."},
  {"id": 2, "label": "unadventurous", "description": "This means keeping to the familiar and the safe: saying no to the unfamiliar place, food or plan, taking the known route every time, and growing uneasy outside routine."},
  {"id": 3, "label": "risk-seeking", "description": "This involves taking bold actions, experimentation, willingness to face uncertainty, and venturing into unproven territory even when outcomes are not guaranteed."}
 ]}
```

## Variant: normal (nn:agreeable)

Listed (id: stem, group, recorded opposite): 1: accommodating, nearest; 2: conciliatory, nearest; 3: cooperative, nearest

```text
=== rubric A2 (overlap_concept_implies), nn:agreeable, request settings {"model": "claude-sonnet-5-5", "max_tokens": 2048} ===
--- system ---
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how similar its concept is to the target's: are they the same concept, or different concepts?

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers for each listed trait:
- 4: the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- 3: the same concept, differing only in scope, degree or emphasis. The test: anyone who has one of the two traits has the other too, at least in one direction: a fussy eater is fussy, a boastful person is proud, a miserly person is penny-pinching, though not necessarily the reverse. The richer one may be the plainer one narrowed to a domain, carried further, or with something added. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further.
- 2: overlapping concepts. They share a core, but neither implies the other: a persona can have either without the other, as a studious person need not be bookish and a bookish one need not be studious; each adds something the other lacks.
- 1: related but distinct concepts: neighbours, not the same concept. For example, tetchy and sullen: both are bad-tempered, but quick irritation is a different thing from silent resentment.
- 0: different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "opposite": the listed trait is the reverse of the target, the same quality at the other end. For example, cheery and morose.
- "unsure": you cannot tell from the two descriptions.

For each listed trait give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed trait's id>, "reason": "<one short sentence>", "similarity": 0|1|2|3|4|"opposite"|"unsure"}]}
Return one row per listed trait, in the order given.
--- user ---
{"target": {"label": "agreeable", "description": "This means prioritizing maintaining harmony and positive relationships, seeking to avoid confrontation, emphasizing cooperation and understanding, and attempting to find common ground or peaceful resolutions even in difficult situations."},
 "traits": [
  {"id": 1, "label": "accommodating", "description": "This means readily adjusting one's positions and approach to meet other people's needs and keep the peace, even when it means giving up an initial stance."},
  {"id": 2, "label": "conciliatory", "description": "This means actively working to make peace, reduce tensions between opposing sides, and seeking to find common ground or shared understanding between conflicting parties or viewpoints."},
  {"id": 3, "label": "cooperative", "description": "This means emphasizing collaboration, mutual benefit, and shared success rather than individual achievement, framing situations as opportunities for teamwork and collective problem-solving rather than contests to be won."}
 ]}
```

```text
=== rubric C2 (overlap_six_implies), nn:agreeable, request settings {"model": "claude-sonnet-5-5", "max_tokens": 2048} ===
--- system ---
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how similar its concept is to the target's: are they the same concept, or different concepts?

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers for each listed trait:
- 5: the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- 4: the same concept, differing only in degree, strength or emphasis; neither adds anything the other lacks. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further.
- 3: one contains the other: one of the two is the other narrowed to a single domain, or the other with something more added to it. The test: anyone with the richer trait has the plainer one too, but not the reverse: a fussy eater is fussy, a boastful person is proud. A stronger or milder form of the same trait is a 4, not a 3.
- 2: overlapping concepts. They share a core, but neither implies the other: a persona can have either without the other, as a studious person need not be bookish and a bookish one need not be studious; each adds something the other lacks.
- 1: related but distinct concepts: neighbours, not the same concept. For example, tetchy and sullen: both are bad-tempered, but quick irritation is a different thing from silent resentment.
- 0: different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "opposite": the listed trait is the reverse of the target, the same quality at the other end. For example, cheery and morose.
- "unsure": you cannot tell from the two descriptions.

For each listed trait give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed trait's id>, "reason": "<one short sentence>", "similarity": 0|1|2|3|4|5|"opposite"|"unsure"}]}
Return one row per listed trait, in the order given.
--- user ---
{"target": {"label": "agreeable", "description": "This means prioritizing maintaining harmony and positive relationships, seeking to avoid confrontation, emphasizing cooperation and understanding, and attempting to find common ground or peaceful resolutions even in difficult situations."},
 "traits": [
  {"id": 1, "label": "accommodating", "description": "This means readily adjusting one's positions and approach to meet other people's needs and keep the peace, even when it means giving up an initial stance."},
  {"id": 2, "label": "conciliatory", "description": "This means actively working to make peace, reduce tensions between opposing sides, and seeking to find common ground or shared understanding between conflicting parties or viewpoints."},
  {"id": 3, "label": "cooperative", "description": "This means emphasizing collaboration, mutual benefit, and shared success rather than individual achievement, framing situations as opportunities for teamwork and collective problem-solving rather than contests to be won."}
 ]}
```

```text
=== rubric D2 (overlap_relation_implies), nn:agreeable, request settings {"model": "claude-sonnet-5-5", "max_tokens": 2048} ===
--- system ---
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how its concept is related to the target's.

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers for each listed trait:
- "same": the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- "variant": the same concept, differing only in degree, strength or emphasis; neither adds anything the other lacks. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further.
- "contains": one of the two is the other narrowed to a single domain, or the other with something more added to it. The test: anyone with the richer trait has the plainer one too, but not the reverse: a fussy eater is fussy, a boastful person is proud. A stronger or milder form of the same trait is "variant", not "contains". The plainer one is the wider; say which it is.
- "overlap": overlapping concepts. They share a core, but neither implies the other: a persona can have either without the other, as a studious person need not be bookish and a bookish one need not be studious; each adds something the other lacks.
- "neighbours": related but distinct concepts: neighbours, not the same concept. For example, tetchy and sullen: both are bad-tempered, but quick irritation is a different thing from silent resentment.
- "different": different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "opposite": the listed trait is the reverse of the target, the same quality at the other end. For example, cheery and morose.
- "unsure": you cannot tell from the two descriptions.

For each listed trait give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed trait's id>, "reason": "<one short sentence>", "relation": "same"|"variant"|"contains"|"overlap"|"neighbours"|"different"|"opposite"|"unsure", "wider": "target"|"listed"}]}
Give "wider" only when the relation is "contains". Return one row per listed trait, in the order given.
--- user ---
{"target": {"label": "agreeable", "description": "This means prioritizing maintaining harmony and positive relationships, seeking to avoid confrontation, emphasizing cooperation and understanding, and attempting to find common ground or peaceful resolutions even in difficult situations."},
 "traits": [
  {"id": 1, "label": "accommodating", "description": "This means readily adjusting one's positions and approach to meet other people's needs and keep the peace, even when it means giving up an initial stance."},
  {"id": 2, "label": "conciliatory", "description": "This means actively working to make peace, reduce tensions between opposing sides, and seeking to find common ground or shared understanding between conflicting parties or viewpoints."},
  {"id": 3, "label": "cooperative", "description": "This means emphasizing collaboration, mutual benefit, and shared success rather than individual achievement, framing situations as opportunities for teamwork and collective problem-solving rather than contests to be won."}
 ]}
```

```text
=== rubric E2 (overlap_scope_implies), nn:agreeable, request settings {"model": "claude-sonnet-5-5", "max_tokens": 2048} ===
--- system ---
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how similar its concept is to the target's: are they the same concept, or different concepts?

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers for each listed trait:
- 4: the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- 3: the same concept, differing only in scope, degree, strength or emphasis. One may be the other narrowed to a single domain, or broadened beyond it; a stronger or a milder form of it; or the same thing with the stress elsewhere. What the wider or stronger one adds is more of the same, not something new. The test: anyone who has one of the two traits has the other too, at least in one direction: a fussy eater is fussy, a boastful person is proud, though not necessarily the reverse. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further. Or fussy and fussy eater: the same fussiness, narrowed to food. In the reason, say which: narrowed, broadened, stronger, milder, or a shift of emphasis.
- 2: overlapping concepts. They share a core, but neither implies the other: a persona can have either without the other, as a studious person need not be bookish and a bookish one need not be studious; each adds something the other lacks.
- 1: related but distinct concepts: neighbours, not the same concept. For example, tetchy and sullen: both are bad-tempered, but quick irritation is a different thing from silent resentment.
- 0: different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "opposite": the listed trait is the reverse of the target, the same quality at the other end. For example, cheery and morose.
- "unsure": you cannot tell from the two descriptions.

For each listed trait give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed trait's id>, "reason": "<one short sentence>", "similarity": 0|1|2|3|4|"opposite"|"unsure"}]}
Return one row per listed trait, in the order given.
--- user ---
{"target": {"label": "agreeable", "description": "This means prioritizing maintaining harmony and positive relationships, seeking to avoid confrontation, emphasizing cooperation and understanding, and attempting to find common ground or peaceful resolutions even in difficult situations."},
 "traits": [
  {"id": 1, "label": "accommodating", "description": "This means readily adjusting one's positions and approach to meet other people's needs and keep the peace, even when it means giving up an initial stance."},
  {"id": 2, "label": "conciliatory", "description": "This means actively working to make peace, reduce tensions between opposing sides, and seeking to find common ground or shared understanding between conflicting parties or viewpoints."},
  {"id": 3, "label": "cooperative", "description": "This means emphasizing collaboration, mutual benefit, and shared success rather than individual achievement, framing situations as opportunities for teamwork and collective problem-solving rather than contests to be won."}
 ]}
```

## Variant: single (lab:honorable)

Listed (id: stem, group, recorded opposite): 1: deontological, deliberate_duplicate

```text
=== rubric A2 (overlap_concept_implies), lab:honorable, request settings {"model": "claude-sonnet-5-5", "max_tokens": 2048} ===
--- system ---
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how similar its concept is to the target's: are they the same concept, or different concepts?

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers for each listed trait:
- 4: the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- 3: the same concept, differing only in scope, degree or emphasis. The test: anyone who has one of the two traits has the other too, at least in one direction: a fussy eater is fussy, a boastful person is proud, a miserly person is penny-pinching, though not necessarily the reverse. The richer one may be the plainer one narrowed to a domain, carried further, or with something added. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further.
- 2: overlapping concepts. They share a core, but neither implies the other: a persona can have either without the other, as a studious person need not be bookish and a bookish one need not be studious; each adds something the other lacks.
- 1: related but distinct concepts: neighbours, not the same concept. For example, tetchy and sullen: both are bad-tempered, but quick irritation is a different thing from silent resentment.
- 0: different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "opposite": the listed trait is the reverse of the target, the same quality at the other end. For example, cheery and morose.
- "unsure": you cannot tell from the two descriptions.

For each listed trait give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed trait's id>, "reason": "<one short sentence>", "similarity": 0|1|2|3|4|"opposite"|"unsure"}]}
Return one row per listed trait, in the order given.
--- user ---
{"target": {"label": "honorable", "description": "This means keeping a code of things that are never done however high the stakes, holding that the ends do not justify the means, that some acts simply cannot be justified, even when they would win, save a great many lives, and accepting the loss when one's code and one's goal conflict."},
 "traits": [
  {"id": 1, "label": "deontological", "description": "This means focusing on whether actions are inherently right or wrong based on moral rules and duties, independent of their consequences or outcomes."}
 ]}
```

```text
=== rubric C2 (overlap_six_implies), lab:honorable, request settings {"model": "claude-sonnet-5-5", "max_tokens": 2048} ===
--- system ---
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how similar its concept is to the target's: are they the same concept, or different concepts?

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers for each listed trait:
- 5: the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- 4: the same concept, differing only in degree, strength or emphasis; neither adds anything the other lacks. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further.
- 3: one contains the other: one of the two is the other narrowed to a single domain, or the other with something more added to it. The test: anyone with the richer trait has the plainer one too, but not the reverse: a fussy eater is fussy, a boastful person is proud. A stronger or milder form of the same trait is a 4, not a 3.
- 2: overlapping concepts. They share a core, but neither implies the other: a persona can have either without the other, as a studious person need not be bookish and a bookish one need not be studious; each adds something the other lacks.
- 1: related but distinct concepts: neighbours, not the same concept. For example, tetchy and sullen: both are bad-tempered, but quick irritation is a different thing from silent resentment.
- 0: different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "opposite": the listed trait is the reverse of the target, the same quality at the other end. For example, cheery and morose.
- "unsure": you cannot tell from the two descriptions.

For each listed trait give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed trait's id>, "reason": "<one short sentence>", "similarity": 0|1|2|3|4|5|"opposite"|"unsure"}]}
Return one row per listed trait, in the order given.
--- user ---
{"target": {"label": "honorable", "description": "This means keeping a code of things that are never done however high the stakes, holding that the ends do not justify the means, that some acts simply cannot be justified, even when they would win, save a great many lives, and accepting the loss when one's code and one's goal conflict."},
 "traits": [
  {"id": 1, "label": "deontological", "description": "This means focusing on whether actions are inherently right or wrong based on moral rules and duties, independent of their consequences or outcomes."}
 ]}
```

```text
=== rubric D2 (overlap_relation_implies), lab:honorable, request settings {"model": "claude-sonnet-5-5", "max_tokens": 2048} ===
--- system ---
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how its concept is related to the target's.

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers for each listed trait:
- "same": the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- "variant": the same concept, differing only in degree, strength or emphasis; neither adds anything the other lacks. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further.
- "contains": one of the two is the other narrowed to a single domain, or the other with something more added to it. The test: anyone with the richer trait has the plainer one too, but not the reverse: a fussy eater is fussy, a boastful person is proud. A stronger or milder form of the same trait is "variant", not "contains". The plainer one is the wider; say which it is.
- "overlap": overlapping concepts. They share a core, but neither implies the other: a persona can have either without the other, as a studious person need not be bookish and a bookish one need not be studious; each adds something the other lacks.
- "neighbours": related but distinct concepts: neighbours, not the same concept. For example, tetchy and sullen: both are bad-tempered, but quick irritation is a different thing from silent resentment.
- "different": different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "opposite": the listed trait is the reverse of the target, the same quality at the other end. For example, cheery and morose.
- "unsure": you cannot tell from the two descriptions.

For each listed trait give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed trait's id>, "reason": "<one short sentence>", "relation": "same"|"variant"|"contains"|"overlap"|"neighbours"|"different"|"opposite"|"unsure", "wider": "target"|"listed"}]}
Give "wider" only when the relation is "contains". Return one row per listed trait, in the order given.
--- user ---
{"target": {"label": "honorable", "description": "This means keeping a code of things that are never done however high the stakes, holding that the ends do not justify the means, that some acts simply cannot be justified, even when they would win, save a great many lives, and accepting the loss when one's code and one's goal conflict."},
 "traits": [
  {"id": 1, "label": "deontological", "description": "This means focusing on whether actions are inherently right or wrong based on moral rules and duties, independent of their consequences or outcomes."}
 ]}
```

```text
=== rubric E2 (overlap_scope_implies), lab:honorable, request settings {"model": "claude-sonnet-5-5", "max_tokens": 2048} ===
--- system ---
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how similar its concept is to the target's: are they the same concept, or different concepts?

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers for each listed trait:
- 4: the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- 3: the same concept, differing only in scope, degree, strength or emphasis. One may be the other narrowed to a single domain, or broadened beyond it; a stronger or a milder form of it; or the same thing with the stress elsewhere. What the wider or stronger one adds is more of the same, not something new. The test: anyone who has one of the two traits has the other too, at least in one direction: a fussy eater is fussy, a boastful person is proud, though not necessarily the reverse. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further. Or fussy and fussy eater: the same fussiness, narrowed to food. In the reason, say which: narrowed, broadened, stronger, milder, or a shift of emphasis.
- 2: overlapping concepts. They share a core, but neither implies the other: a persona can have either without the other, as a studious person need not be bookish and a bookish one need not be studious; each adds something the other lacks.
- 1: related but distinct concepts: neighbours, not the same concept. For example, tetchy and sullen: both are bad-tempered, but quick irritation is a different thing from silent resentment.
- 0: different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "opposite": the listed trait is the reverse of the target, the same quality at the other end. For example, cheery and morose.
- "unsure": you cannot tell from the two descriptions.

For each listed trait give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed trait's id>, "reason": "<one short sentence>", "similarity": 0|1|2|3|4|"opposite"|"unsure"}]}
Return one row per listed trait, in the order given.
--- user ---
{"target": {"label": "honorable", "description": "This means keeping a code of things that are never done however high the stakes, holding that the ends do not justify the means, that some acts simply cannot be justified, even when they would win, save a great many lives, and accepting the loss when one's code and one's goal conflict."},
 "traits": [
  {"id": 1, "label": "deontological", "description": "This means focusing on whether actions are inherently right or wrong based on moral rules and duties, independent of their consequences or outcomes."}
 ]}
```

## Pass 2: the same calls, the listed traits in a fresh order

The system prompt is each rubric's, as in pass 1; only the user turn's order (and so the ids) changes.  20 of 84 calls happen to keep pass 1's order (every call of one trait does).  The variants' user turns in this pass:

### antonym_in_list (nn:adventurous), pass 2: unadventurous, risk_seeking, adventurous_eater

```text
{"target": {"label": "adventurous", "description": "This means seeking out the new and the untried: saying yes to the unfamiliar place, food or plan, taking the unknown route for the thrill of it, and growing restless in any routine."},
 "traits": [
  {"id": 1, "label": "unadventurous", "description": "This means keeping to the familiar and the safe: saying no to the unfamiliar place, food or plan, taking the known route every time, and growing uneasy outside routine."},
  {"id": 2, "label": "risk-seeking", "description": "This involves taking bold actions, experimentation, willingness to face uncertainty, and venturing into unproven territory even when outcomes are not guaranteed."},
  {"id": 3, "label": "adventurous-eater", "description": "This means ordering the dish nobody recognizes, trying the offal, the fermented and the fiery, and treating every unfamiliar menu as a dare."}
 ]}
```

### normal (nn:agreeable), pass 2: conciliatory, cooperative, accommodating

```text
{"target": {"label": "agreeable", "description": "This means prioritizing maintaining harmony and positive relationships, seeking to avoid confrontation, emphasizing cooperation and understanding, and attempting to find common ground or peaceful resolutions even in difficult situations."},
 "traits": [
  {"id": 1, "label": "conciliatory", "description": "This means actively working to make peace, reduce tensions between opposing sides, and seeking to find common ground or shared understanding between conflicting parties or viewpoints."},
  {"id": 2, "label": "cooperative", "description": "This means emphasizing collaboration, mutual benefit, and shared success rather than individual achievement, framing situations as opportunities for teamwork and collective problem-solving rather than contests to be won."},
  {"id": 3, "label": "accommodating", "description": "This means readily adjusting one's positions and approach to meet other people's needs and keep the peace, even when it means giving up an initial stance."}
 ]}
```

### single (lab:honorable), pass 2: deontological

```text
{"target": {"label": "honorable", "description": "This means keeping a code of things that are never done however high the stakes, holding that the ends do not justify the means, that some acts simply cannot be justified, even when they would win, save a great many lives, and accepting the loss when one's code and one's goal conflict."},
 "traits": [
  {"id": 1, "label": "deontological", "description": "This means focusing on whether actions are inherently right or wrong based on moral rules and duties, independent of their consequences or outcomes."}
 ]}
```
