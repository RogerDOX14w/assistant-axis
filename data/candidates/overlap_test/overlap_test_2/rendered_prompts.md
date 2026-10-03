# Rendered prompts of the overlap test

The requests exactly as the model receives them (rubric as the system prompt, one JSON object as the user turn), for 3 variants; settings shown for claude-sonnet-5-5.  Both rubrics receive the identical user turn.

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
Return one row per listed trait, in the order given. Use only the keys shown: do not add the trait's label or any other key, and give each row once.
--- user ---
{"target": {"label": "absolutist", "description": "This means maintaining that certain truths, values, and principles are universal and unchanging, applying to all people and situations without exception or cultural variation."},
 "traits": [
  {"id": 1, "label": "relativist", "description": "This means believing that truth and morality are entirely dependent on context, perspective, and cultural background, rejecting the existence of universal or objective standards."},
  {"id": 2, "label": "essentialist", "description": "This means believing in and emphasizing the fundamental, unchanging nature or essence of things and concepts, treating categories and identities as having fixed, inherent properties rather than being flexible or contextually dependent."},
  {"id": 3, "label": "moral universalist", "description": "This means applying consistent norms and values across all cultures and contexts, believing that moral standards and human values should be uniform regardless of cultural, historical, or situational differences."}
 ]}
```

```text
=== rubric B (overlap_cooccurrence), nn:absolutist, request settings {"model": "claude-sonnet-5-5", "max_tokens": 2048} ===
--- system ---
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how often a persona that has the target trait would also show the listed trait.

Judge how the two go together in a person, not whether they are the same concept. Two traits can be different concepts and still nearly always go together.

Give one of these answers for each listed trait:
- 4: almost always: a persona with the target trait would show this one too. For example, a talkative persona would be loquacious.
- 3: usually. For example, a studious persona would usually be bookish.
- 2: often, but far from always. For example, a punctual persona would often be tidy.
- 1: sometimes, about as often as anyone else. For example, an outdoorsy persona would sometimes be punctual.
- 0: less often than in anyone else, down to never: having the target trait makes this one less likely. For example, a cheery persona would rarely be morose.
- "unsure": you cannot tell from the two descriptions.

For each listed trait give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed trait's id>, "reason": "<one short sentence>", "co_occurrence": 0|1|2|3|4|"unsure"}]}
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
Return one row per listed trait, in the order given. Use only the keys shown: do not add the trait's label or any other key, and give each row once.
--- user ---
{"target": {"label": "agreeable", "description": "This means prioritizing maintaining harmony and positive relationships, seeking to avoid confrontation, emphasizing cooperation and understanding, and attempting to find common ground or peaceful resolutions even in difficult situations."},
 "traits": [
  {"id": 1, "label": "accommodating", "description": "This means readily adjusting one's positions and approach to meet other people's needs and keep the peace, even when it means giving up an initial stance."},
  {"id": 2, "label": "conciliatory", "description": "This means actively working to make peace, reduce tensions between opposing sides, and seeking to find common ground or shared understanding between conflicting parties or viewpoints."},
  {"id": 3, "label": "cooperative", "description": "This means emphasizing collaboration, mutual benefit, and shared success rather than individual achievement, framing situations as opportunities for teamwork and collective problem-solving rather than contests to be won."}
 ]}
```

```text
=== rubric B (overlap_cooccurrence), nn:agreeable, request settings {"model": "claude-sonnet-5-5", "max_tokens": 2048} ===
--- system ---
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how often a persona that has the target trait would also show the listed trait.

Judge how the two go together in a person, not whether they are the same concept. Two traits can be different concepts and still nearly always go together.

Give one of these answers for each listed trait:
- 4: almost always: a persona with the target trait would show this one too. For example, a talkative persona would be loquacious.
- 3: usually. For example, a studious persona would usually be bookish.
- 2: often, but far from always. For example, a punctual persona would often be tidy.
- 1: sometimes, about as often as anyone else. For example, an outdoorsy persona would sometimes be punctual.
- 0: less often than in anyone else, down to never: having the target trait makes this one less likely. For example, a cheery persona would rarely be morose.
- "unsure": you cannot tell from the two descriptions.

For each listed trait give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed trait's id>, "reason": "<one short sentence>", "co_occurrence": 0|1|2|3|4|"unsure"}]}
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
Return one row per listed trait, in the order given. Use only the keys shown: do not add the trait's label or any other key, and give each row once.
--- user ---
{"target": {"label": "cheerful", "description": "This means being in good spirits by disposition, brightening at small things, noticing what is going right before what is wrong, and keeping a light heart on a bad day."},
 "traits": [
  {"id": 1, "label": "melancholic", "description": "This means showing a tendency toward habitual sadness, brooding behavior, and focusing on negative or disappointing aspects of situations rather than positive ones."}
 ]}
```

```text
=== rubric B (overlap_cooccurrence), lab:cheerful, request settings {"model": "claude-sonnet-5-5", "max_tokens": 2048} ===
--- system ---
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how often a persona that has the target trait would also show the listed trait.

Judge how the two go together in a person, not whether they are the same concept. Two traits can be different concepts and still nearly always go together.

Give one of these answers for each listed trait:
- 4: almost always: a persona with the target trait would show this one too. For example, a talkative persona would be loquacious.
- 3: usually. For example, a studious persona would usually be bookish.
- 2: often, but far from always. For example, a punctual persona would often be tidy.
- 1: sometimes, about as often as anyone else. For example, an outdoorsy persona would sometimes be punctual.
- 0: less often than in anyone else, down to never: having the target trait makes this one less likely. For example, a cheery persona would rarely be morose.
- "unsure": you cannot tell from the two descriptions.

For each listed trait give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed trait's id>, "reason": "<one short sentence>", "co_occurrence": 0|1|2|3|4|"unsure"}]}
Return one row per listed trait, in the order given.
--- user ---
{"target": {"label": "cheerful", "description": "This means being in good spirits by disposition, brightening at small things, noticing what is going right before what is wrong, and keeping a light heart on a bad day."},
 "traits": [
  {"id": 1, "label": "melancholic", "description": "This means showing a tendency toward habitual sadness, brooding behavior, and focusing on negative or disappointing aspects of situations rather than positive ones."}
 ]}
```
