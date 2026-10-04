# Rendered prompts of the overlap test

The requests exactly as the model receives them (rubric as the system prompt, one JSON object as the user turn), for 3 variants and the rubrics A, C, D, E; settings shown for claude-sonnet-5-5.  Within a pass every rubric and model receives the identical user turn.

## Variant: antonym_in_list (nn:absolutist)

Listed (id: stem, group, recorded opposite): 1: relativist, nearest, opposite; 2: essentialist, nearest; 3: moral_universalist, nearest

```text
=== rubric A (overlap_concept), nn:absolutist, request settings {"model": "claude-sonnet-5-5", "max_tokens": 2048} ===
--- system ---
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how similar its concept is to the target's: are they the same concept, or different concepts?

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers for each listed trait:
- 4: the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- 3: the same concept, differing only in scope, degree or emphasis. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further.
- 2: overlapping concepts. They share a core, but each adds something the other lacks. For example, studious and bookish: both are about learning from books, but studious adds diligence and bookish adds a taste for reading.
- 1: related but distinct concepts: neighbours, not the same concept. For example, tetchy and sullen: both are bad-tempered, but quick irritation is a different thing from silent resentment.
- 0: different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "opposite": the listed trait is the reverse of the target, the same quality at the other end. For example, cheery and morose.
- "unsure": you cannot tell from the two descriptions.

For each listed trait give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed trait's id>, "reason": "<one short sentence>", "similarity": 0|1|2|3|4|"opposite"|"unsure"}]}
Return one row per listed trait, in the order given.
--- user ---
{"target": {"label": "absolutist", "description": "This means maintaining that certain truths, values, and principles are universal and unchanging, applying to all people and situations without exception or cultural variation."},
 "traits": [
  {"id": 1, "label": "relativist", "description": "This means believing that truth and morality are entirely dependent on context, perspective, and cultural background, rejecting the existence of universal or objective standards."},
  {"id": 2, "label": "essentialist", "description": "This means believing in and emphasizing the fundamental, unchanging nature or essence of things and concepts, treating categories and identities as having fixed, inherent properties rather than being flexible or contextually dependent."},
  {"id": 3, "label": "moral universalist", "description": "This means applying consistent norms and values across all cultures and contexts, believing that moral standards and human values should be uniform regardless of cultural, historical, or situational differences."}
 ]}
```

```text
=== rubric C (overlap_six), nn:absolutist, request settings {"model": "claude-sonnet-5-5", "max_tokens": 2048} ===
--- system ---
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how similar its concept is to the target's: are they the same concept, or different concepts?

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers for each listed trait:
- 5: the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- 4: the same concept, differing only in degree, strength or emphasis; neither adds anything the other lacks. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further.
- 3: one contains the other: one of the two is the other narrowed to a single domain, or the other with something more added to it, and the narrower or plainer one adds nothing of its own. For example, fussy and fussy eater: the same fussiness, narrowed to food.
- 2: overlapping concepts. They share a core, but each adds something the other lacks. For example, studious and bookish: both are about learning from books, but studious adds diligence and bookish adds a taste for reading.
- 1: related but distinct concepts: neighbours, not the same concept. For example, tetchy and sullen: both are bad-tempered, but quick irritation is a different thing from silent resentment.
- 0: different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "opposite": the listed trait is the reverse of the target, the same quality at the other end. For example, cheery and morose.
- "unsure": you cannot tell from the two descriptions.

For each listed trait give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed trait's id>, "reason": "<one short sentence>", "similarity": 0|1|2|3|4|5|"opposite"|"unsure"}]}
Return one row per listed trait, in the order given.
--- user ---
{"target": {"label": "absolutist", "description": "This means maintaining that certain truths, values, and principles are universal and unchanging, applying to all people and situations without exception or cultural variation."},
 "traits": [
  {"id": 1, "label": "relativist", "description": "This means believing that truth and morality are entirely dependent on context, perspective, and cultural background, rejecting the existence of universal or objective standards."},
  {"id": 2, "label": "essentialist", "description": "This means believing in and emphasizing the fundamental, unchanging nature or essence of things and concepts, treating categories and identities as having fixed, inherent properties rather than being flexible or contextually dependent."},
  {"id": 3, "label": "moral universalist", "description": "This means applying consistent norms and values across all cultures and contexts, believing that moral standards and human values should be uniform regardless of cultural, historical, or situational differences."}
 ]}
```

```text
=== rubric D (overlap_relation), nn:absolutist, request settings {"model": "claude-sonnet-5-5", "max_tokens": 2048} ===
--- system ---
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how its concept is related to the target's.

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers for each listed trait:
- "same": the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- "variant": the same concept, differing only in degree, strength or emphasis; neither adds anything the other lacks. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further.
- "contains": one of the two is the other narrowed to a single domain, or the other with something more added to it, and the narrower or plainer one adds nothing of its own. Say which is the wider one. For example, fussy and fussy eater: fussy is the wider.
- "overlap": overlapping concepts. They share a core, but each adds something the other lacks. For example, studious and bookish: both are about learning from books, but studious adds diligence and bookish adds a taste for reading.
- "neighbours": related but distinct concepts: neighbours, not the same concept. For example, tetchy and sullen: both are bad-tempered, but quick irritation is a different thing from silent resentment.
- "different": different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "opposite": the listed trait is the reverse of the target, the same quality at the other end. For example, cheery and morose.
- "unsure": you cannot tell from the two descriptions.

For each listed trait give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed trait's id>, "reason": "<one short sentence>", "relation": "same"|"variant"|"contains"|"overlap"|"neighbours"|"different"|"opposite"|"unsure", "wider": "target"|"listed"}]}
Give "wider" only when the relation is "contains". Return one row per listed trait, in the order given.
--- user ---
{"target": {"label": "absolutist", "description": "This means maintaining that certain truths, values, and principles are universal and unchanging, applying to all people and situations without exception or cultural variation."},
 "traits": [
  {"id": 1, "label": "relativist", "description": "This means believing that truth and morality are entirely dependent on context, perspective, and cultural background, rejecting the existence of universal or objective standards."},
  {"id": 2, "label": "essentialist", "description": "This means believing in and emphasizing the fundamental, unchanging nature or essence of things and concepts, treating categories and identities as having fixed, inherent properties rather than being flexible or contextually dependent."},
  {"id": 3, "label": "moral universalist", "description": "This means applying consistent norms and values across all cultures and contexts, believing that moral standards and human values should be uniform regardless of cultural, historical, or situational differences."}
 ]}
```

```text
=== rubric E (overlap_scope), nn:absolutist, request settings {"model": "claude-sonnet-5-5", "max_tokens": 2048} ===
--- system ---
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how similar its concept is to the target's: are they the same concept, or different concepts?

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers for each listed trait:
- 4: the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- 3: the same concept, differing only in scope, degree, strength or emphasis. One may be the other narrowed to a single domain, or broadened beyond it; a stronger or a milder form of it; or the same thing with the stress elsewhere. What the wider or stronger one adds is more of the same, not something new. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further. Or fussy and fussy eater: the same fussiness, narrowed to food. In the reason, say which: narrowed, broadened, stronger, milder, or a shift of emphasis.
- 2: overlapping concepts. They share a core, but each adds something the other lacks. For example, studious and bookish: both are about learning from books, but studious adds diligence and bookish adds a taste for reading.
- 1: related but distinct concepts: neighbours, not the same concept. For example, tetchy and sullen: both are bad-tempered, but quick irritation is a different thing from silent resentment.
- 0: different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "opposite": the listed trait is the reverse of the target, the same quality at the other end. For example, cheery and morose.
- "unsure": you cannot tell from the two descriptions.

For each listed trait give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed trait's id>, "reason": "<one short sentence>", "similarity": 0|1|2|3|4|"opposite"|"unsure"}]}
Return one row per listed trait, in the order given.
--- user ---
{"target": {"label": "absolutist", "description": "This means maintaining that certain truths, values, and principles are universal and unchanging, applying to all people and situations without exception or cultural variation."},
 "traits": [
  {"id": 1, "label": "relativist", "description": "This means believing that truth and morality are entirely dependent on context, perspective, and cultural background, rejecting the existence of universal or objective standards."},
  {"id": 2, "label": "essentialist", "description": "This means believing in and emphasizing the fundamental, unchanging nature or essence of things and concepts, treating categories and identities as having fixed, inherent properties rather than being flexible or contextually dependent."},
  {"id": 3, "label": "moral universalist", "description": "This means applying consistent norms and values across all cultures and contexts, believing that moral standards and human values should be uniform regardless of cultural, historical, or situational differences."}
 ]}
```

## Variant: normal (nn:agreeable)

Listed (id: stem, group, recorded opposite): 1: accommodating, nearest; 2: conciliatory, nearest; 3: cooperative, nearest

```text
=== rubric A (overlap_concept), nn:agreeable, request settings {"model": "claude-sonnet-5-5", "max_tokens": 2048} ===
--- system ---
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how similar its concept is to the target's: are they the same concept, or different concepts?

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers for each listed trait:
- 4: the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- 3: the same concept, differing only in scope, degree or emphasis. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further.
- 2: overlapping concepts. They share a core, but each adds something the other lacks. For example, studious and bookish: both are about learning from books, but studious adds diligence and bookish adds a taste for reading.
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
=== rubric C (overlap_six), nn:agreeable, request settings {"model": "claude-sonnet-5-5", "max_tokens": 2048} ===
--- system ---
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how similar its concept is to the target's: are they the same concept, or different concepts?

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers for each listed trait:
- 5: the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- 4: the same concept, differing only in degree, strength or emphasis; neither adds anything the other lacks. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further.
- 3: one contains the other: one of the two is the other narrowed to a single domain, or the other with something more added to it, and the narrower or plainer one adds nothing of its own. For example, fussy and fussy eater: the same fussiness, narrowed to food.
- 2: overlapping concepts. They share a core, but each adds something the other lacks. For example, studious and bookish: both are about learning from books, but studious adds diligence and bookish adds a taste for reading.
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
=== rubric D (overlap_relation), nn:agreeable, request settings {"model": "claude-sonnet-5-5", "max_tokens": 2048} ===
--- system ---
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how its concept is related to the target's.

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers for each listed trait:
- "same": the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- "variant": the same concept, differing only in degree, strength or emphasis; neither adds anything the other lacks. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further.
- "contains": one of the two is the other narrowed to a single domain, or the other with something more added to it, and the narrower or plainer one adds nothing of its own. Say which is the wider one. For example, fussy and fussy eater: fussy is the wider.
- "overlap": overlapping concepts. They share a core, but each adds something the other lacks. For example, studious and bookish: both are about learning from books, but studious adds diligence and bookish adds a taste for reading.
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
=== rubric E (overlap_scope), nn:agreeable, request settings {"model": "claude-sonnet-5-5", "max_tokens": 2048} ===
--- system ---
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how similar its concept is to the target's: are they the same concept, or different concepts?

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers for each listed trait:
- 4: the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- 3: the same concept, differing only in scope, degree, strength or emphasis. One may be the other narrowed to a single domain, or broadened beyond it; a stronger or a milder form of it; or the same thing with the stress elsewhere. What the wider or stronger one adds is more of the same, not something new. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further. Or fussy and fussy eater: the same fussiness, narrowed to food. In the reason, say which: narrowed, broadened, stronger, milder, or a shift of emphasis.
- 2: overlapping concepts. They share a core, but each adds something the other lacks. For example, studious and bookish: both are about learning from books, but studious adds diligence and bookish adds a taste for reading.
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

## Variant: single (lab:cheerful)

Listed (id: stem, group, recorded opposite): 1: melancholic, antonym, opposite

```text
=== rubric A (overlap_concept), lab:cheerful, request settings {"model": "claude-sonnet-5-5", "max_tokens": 2048} ===
--- system ---
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how similar its concept is to the target's: are they the same concept, or different concepts?

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers for each listed trait:
- 4: the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- 3: the same concept, differing only in scope, degree or emphasis. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further.
- 2: overlapping concepts. They share a core, but each adds something the other lacks. For example, studious and bookish: both are about learning from books, but studious adds diligence and bookish adds a taste for reading.
- 1: related but distinct concepts: neighbours, not the same concept. For example, tetchy and sullen: both are bad-tempered, but quick irritation is a different thing from silent resentment.
- 0: different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "opposite": the listed trait is the reverse of the target, the same quality at the other end. For example, cheery and morose.
- "unsure": you cannot tell from the two descriptions.

For each listed trait give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed trait's id>, "reason": "<one short sentence>", "similarity": 0|1|2|3|4|"opposite"|"unsure"}]}
Return one row per listed trait, in the order given.
--- user ---
{"target": {"label": "cheerful", "description": "This means being in good spirits by disposition, brightening at small things, noticing what is going right before what is wrong, and keeping a light heart on a bad day."},
 "traits": [
  {"id": 1, "label": "melancholic", "description": "This means showing a tendency toward habitual sadness, brooding behavior, and focusing on negative or disappointing aspects of situations rather than positive ones."}
 ]}
```

```text
=== rubric C (overlap_six), lab:cheerful, request settings {"model": "claude-sonnet-5-5", "max_tokens": 2048} ===
--- system ---
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how similar its concept is to the target's: are they the same concept, or different concepts?

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers for each listed trait:
- 5: the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- 4: the same concept, differing only in degree, strength or emphasis; neither adds anything the other lacks. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further.
- 3: one contains the other: one of the two is the other narrowed to a single domain, or the other with something more added to it, and the narrower or plainer one adds nothing of its own. For example, fussy and fussy eater: the same fussiness, narrowed to food.
- 2: overlapping concepts. They share a core, but each adds something the other lacks. For example, studious and bookish: both are about learning from books, but studious adds diligence and bookish adds a taste for reading.
- 1: related but distinct concepts: neighbours, not the same concept. For example, tetchy and sullen: both are bad-tempered, but quick irritation is a different thing from silent resentment.
- 0: different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "opposite": the listed trait is the reverse of the target, the same quality at the other end. For example, cheery and morose.
- "unsure": you cannot tell from the two descriptions.

For each listed trait give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed trait's id>, "reason": "<one short sentence>", "similarity": 0|1|2|3|4|5|"opposite"|"unsure"}]}
Return one row per listed trait, in the order given.
--- user ---
{"target": {"label": "cheerful", "description": "This means being in good spirits by disposition, brightening at small things, noticing what is going right before what is wrong, and keeping a light heart on a bad day."},
 "traits": [
  {"id": 1, "label": "melancholic", "description": "This means showing a tendency toward habitual sadness, brooding behavior, and focusing on negative or disappointing aspects of situations rather than positive ones."}
 ]}
```

```text
=== rubric D (overlap_relation), lab:cheerful, request settings {"model": "claude-sonnet-5-5", "max_tokens": 2048} ===
--- system ---
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how its concept is related to the target's.

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers for each listed trait:
- "same": the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- "variant": the same concept, differing only in degree, strength or emphasis; neither adds anything the other lacks. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further.
- "contains": one of the two is the other narrowed to a single domain, or the other with something more added to it, and the narrower or plainer one adds nothing of its own. Say which is the wider one. For example, fussy and fussy eater: fussy is the wider.
- "overlap": overlapping concepts. They share a core, but each adds something the other lacks. For example, studious and bookish: both are about learning from books, but studious adds diligence and bookish adds a taste for reading.
- "neighbours": related but distinct concepts: neighbours, not the same concept. For example, tetchy and sullen: both are bad-tempered, but quick irritation is a different thing from silent resentment.
- "different": different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "opposite": the listed trait is the reverse of the target, the same quality at the other end. For example, cheery and morose.
- "unsure": you cannot tell from the two descriptions.

For each listed trait give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed trait's id>, "reason": "<one short sentence>", "relation": "same"|"variant"|"contains"|"overlap"|"neighbours"|"different"|"opposite"|"unsure", "wider": "target"|"listed"}]}
Give "wider" only when the relation is "contains". Return one row per listed trait, in the order given.
--- user ---
{"target": {"label": "cheerful", "description": "This means being in good spirits by disposition, brightening at small things, noticing what is going right before what is wrong, and keeping a light heart on a bad day."},
 "traits": [
  {"id": 1, "label": "melancholic", "description": "This means showing a tendency toward habitual sadness, brooding behavior, and focusing on negative or disappointing aspects of situations rather than positive ones."}
 ]}
```

```text
=== rubric E (overlap_scope), lab:cheerful, request settings {"model": "claude-sonnet-5-5", "max_tokens": 2048} ===
--- system ---
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how similar its concept is to the target's: are they the same concept, or different concepts?

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers for each listed trait:
- 4: the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- 3: the same concept, differing only in scope, degree, strength or emphasis. One may be the other narrowed to a single domain, or broadened beyond it; a stronger or a milder form of it; or the same thing with the stress elsewhere. What the wider or stronger one adds is more of the same, not something new. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further. Or fussy and fussy eater: the same fussiness, narrowed to food. In the reason, say which: narrowed, broadened, stronger, milder, or a shift of emphasis.
- 2: overlapping concepts. They share a core, but each adds something the other lacks. For example, studious and bookish: both are about learning from books, but studious adds diligence and bookish adds a taste for reading.
- 1: related but distinct concepts: neighbours, not the same concept. For example, tetchy and sullen: both are bad-tempered, but quick irritation is a different thing from silent resentment.
- 0: different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "opposite": the listed trait is the reverse of the target, the same quality at the other end. For example, cheery and morose.
- "unsure": you cannot tell from the two descriptions.

For each listed trait give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed trait's id>, "reason": "<one short sentence>", "similarity": 0|1|2|3|4|"opposite"|"unsure"}]}
Return one row per listed trait, in the order given.
--- user ---
{"target": {"label": "cheerful", "description": "This means being in good spirits by disposition, brightening at small things, noticing what is going right before what is wrong, and keeping a light heart on a bad day."},
 "traits": [
  {"id": 1, "label": "melancholic", "description": "This means showing a tendency toward habitual sadness, brooding behavior, and focusing on negative or disappointing aspects of situations rather than positive ones."}
 ]}
```

## Pass 2: the same calls, the listed traits in a fresh order

The system prompt is each rubric's, as in pass 1; only the user turn's order (and so the ids) changes.  86 of 180 calls happen to keep pass 1's order (every call of one trait does).  The variants' user turns in this pass:

### antonym_in_list (nn:absolutist), pass 2: essentialist, moral_universalist, relativist

```text
{"target": {"label": "absolutist", "description": "This means maintaining that certain truths, values, and principles are universal and unchanging, applying to all people and situations without exception or cultural variation."},
 "traits": [
  {"id": 1, "label": "essentialist", "description": "This means believing in and emphasizing the fundamental, unchanging nature or essence of things and concepts, treating categories and identities as having fixed, inherent properties rather than being flexible or contextually dependent."},
  {"id": 2, "label": "moral universalist", "description": "This means applying consistent norms and values across all cultures and contexts, believing that moral standards and human values should be uniform regardless of cultural, historical, or situational differences."},
  {"id": 3, "label": "relativist", "description": "This means believing that truth and morality are entirely dependent on context, perspective, and cultural background, rejecting the existence of universal or objective standards."}
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

### single (lab:cheerful), pass 2: melancholic

```text
{"target": {"label": "cheerful", "description": "This means being in good spirits by disposition, brightening at small things, noticing what is going right before what is wrong, and keeping a light heart on a bad day."},
 "traits": [
  {"id": 1, "label": "melancholic", "description": "This means showing a tendency toward habitual sadness, brooding behavior, and focusing on negative or disappointing aspects of situations rather than positive ones."}
 ]}
```
