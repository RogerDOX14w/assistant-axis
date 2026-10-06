# Rendered prompts of the overlap test

The requests exactly as the model receives them (rubric as the system prompt, one JSON object as the user turn), for the one-pair rubric A; settings shown for claude-sonnet-5-5.  Within a pass every rubric and model receives the identical user turn.

## One pair per call (the single form): rubric A

Every pair is its own call, keyed by its pair id; the user turn is the rubric file's rendered sample (target on the first line, the other trait on the second); the rubric goes as a cached system block.  Pass 2 sends these prompts again, identical.

### Pair: nearest (nn:absolutist>moral_universalist, nearest)

```text
=== rubric A (overlap_concept), nn:absolutist>moral_universalist, single form, request settings {"model": "claude-sonnet-5-5", "max_tokens": 2048}, system block cache_control {"type": "ephemeral"} ===
--- system ---
You are given one JSON object: a persona trait, the target ("target"), and one other persona trait ("other"), each with a one-sentence description. Say how similar the other trait's concept is to the target's: are they the same concept, or different concepts?

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers:
- 4: the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- 3: the same concept, differing only in scope, degree or emphasis. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further.
- 2: overlapping concepts. They share a core, but neither implies the other: a persona can have either without the other, as a studious person need not be bookish and a bookish one need not be studious; each adds something the other lacks.
- 1: related but distinct concepts: neighbours, not the same concept. For example, tetchy and sullen: both are bad-tempered, but quick irritation is a different thing from silent resentment.
- 0: different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "opposite": the other trait is the reverse of the target, the same quality at the other end. For example, cheery and morose.
- "unsure": you cannot tell from the two descriptions.

Give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"reason": "<one short sentence>", "similarity": 0|1|2|3|4|"opposite"|"unsure"}
--- user ---
{"target": {"label": "absolutist", "description": "This means maintaining that certain truths, values, and principles are universal and unchanging, applying to all people and situations without exception or cultural variation."},
 "other": {"label": "moral universalist", "description": "This means applying consistent norms and values across all cultures and contexts, believing that moral standards and human values should be uniform regardless of cultural, historical, or situational differences."}}
```

### Pair: nearest_opposite (nn:absolutist>relativist, nearest, recorded opposite)

```text
=== rubric A (overlap_concept), nn:absolutist>relativist, single form, request settings {"model": "claude-sonnet-5-5", "max_tokens": 2048}, system block cache_control {"type": "ephemeral"} ===
--- system ---
You are given one JSON object: a persona trait, the target ("target"), and one other persona trait ("other"), each with a one-sentence description. Say how similar the other trait's concept is to the target's: are they the same concept, or different concepts?

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers:
- 4: the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- 3: the same concept, differing only in scope, degree or emphasis. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further.
- 2: overlapping concepts. They share a core, but neither implies the other: a persona can have either without the other, as a studious person need not be bookish and a bookish one need not be studious; each adds something the other lacks.
- 1: related but distinct concepts: neighbours, not the same concept. For example, tetchy and sullen: both are bad-tempered, but quick irritation is a different thing from silent resentment.
- 0: different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "opposite": the other trait is the reverse of the target, the same quality at the other end. For example, cheery and morose.
- "unsure": you cannot tell from the two descriptions.

Give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"reason": "<one short sentence>", "similarity": 0|1|2|3|4|"opposite"|"unsure"}
--- user ---
{"target": {"label": "absolutist", "description": "This means maintaining that certain truths, values, and principles are universal and unchanging, applying to all people and situations without exception or cultural variation."},
 "other": {"label": "relativist", "description": "This means believing that truth and morality are entirely dependent on context, perspective, and cultural background, rejecting the existence of universal or objective standards."}}
```

### Pair: labelled (lab:nihilistic>essentialist, near_distinct)

```text
=== rubric A (overlap_concept), lab:nihilistic>essentialist, single form, request settings {"model": "claude-sonnet-5-5", "max_tokens": 2048}, system block cache_control {"type": "ephemeral"} ===
--- system ---
You are given one JSON object: a persona trait, the target ("target"), and one other persona trait ("other"), each with a one-sentence description. Say how similar the other trait's concept is to the target's: are they the same concept, or different concepts?

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers:
- 4: the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- 3: the same concept, differing only in scope, degree or emphasis. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further.
- 2: overlapping concepts. They share a core, but neither implies the other: a persona can have either without the other, as a studious person need not be bookish and a bookish one need not be studious; each adds something the other lacks.
- 1: related but distinct concepts: neighbours, not the same concept. For example, tetchy and sullen: both are bad-tempered, but quick irritation is a different thing from silent resentment.
- 0: different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "opposite": the other trait is the reverse of the target, the same quality at the other end. For example, cheery and morose.
- "unsure": you cannot tell from the two descriptions.

Give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"reason": "<one short sentence>", "similarity": 0|1|2|3|4|"opposite"|"unsure"}
--- user ---
{"target": {"label": "nihilistic", "description": "This means expressing beliefs that existence is fundamentally meaningless, rejecting the validity of moral values and human purposes, dismissing the significance of achievements or relationships, or suggesting that seeking meaning in life is futile."},
 "other": {"label": "essentialist", "description": "This means believing in and emphasizing the fundamental, unchanging nature or essence of things and concepts, treating categories and identities as having fixed, inherent properties rather than being flexible or contextually dependent."}}
```
