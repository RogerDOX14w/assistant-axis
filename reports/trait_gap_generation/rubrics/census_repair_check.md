# The census spelling-repair check

| | |
|---|---|
| **Status** | Draft 1 (2026-10-14), pinned as version 1.  Built for [QUESTIONS.md](../QUESTIONS.md) entry 35 (Roger's go, 2026-10-14); not run yet. |
| **What the model is shown** | One repair suggestion per call: the word as the Allport-Odbert file spells it, the present-day adjective one edit away that the ingest suggested, and the two entries before and the two after it in the same column of the file (the list is alphabetical), in one JSON object. |
| **What it returns** | A short reason, then `verdict`: `typo`, `real_word` or `unsure`. |
| **What it is tuned on** | Not tuned.  The examples are invented: neither of the two example words is in the census lists. |
| **Model** | Sonnet 5.5 (`claude-sonnet-5-5`); no temperature (it refuses one); `max_tokens` 2000, the platform's figure for a thinking model (`split_runner.MAX_TOKENS_THINKING`).  The answer asks for a short reason before the verdict, never for the model's thinking: Sonnet 5.5 refuses "think first in a field" prompts (`.claude/rules/judging.md`, 2026-10-13). |

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent
to the model exactly as written.  Leave the fence lines themselves alone.  Notes for me go under
"Your notes", outside the block.  A changed text needs a new pin
(`rubric_pins.py bump census_repair_check`).

**What it is for.**  The census ingest ([ingest.py](../../../assistant_axis/gapgen/generators/censuses/ingest.py),
`repair_ocr`) looks for the unique OEWN adjective one edit away from each Allport-Odbert word that neither
`wordfreq` nor OEWN knows.  It applies the repair only to letter doublings and vowel insertions past the second
letter (`SAFE_REPAIR_KINDS`), because on the real list most other one-edit matches were real archaic words
next to a modern one (cullying is not bullying).  The other 706 matches are listed, not applied, as
`repair_suggestions_list` in [ingest_counts.json](../../../data/candidates/censuses/ingest_counts.json); 314 of
them point to a word the census lists do not already hold.  This call reads those 314 one at a time and says
which are typing or transcription errors, so that the repaired word can be submitted as a census candidate.  The
code is [repair_check.py](../../../assistant_axis/gapgen/generators/censuses/repair_check.py); the command is
`census_generator.py repair-check` ([census_generator.py](../../../data_analysis/gap_generation/census_generator.py)).

**Why the neighbours.**  The file keeps the printed list's alphabetical order (a few hundred inversions in
17,767 entries), and a transcription slip keeps the printed word's place.  So where a word sits is evidence
for one spelling: Bragless sits between Brag and Brahmin, where bragless sorts and braless does not.

## The prompt

````text
You are checking entries in a list of English words that describe people: the Allport-Odbert list of 1936, about 18,000 words taken from an unabridged dictionary of the 1920s, as typed into a computer file decades later. Some entries in the file are in no present-day dictionary or word-frequency list. For each such entry a program found the one present-day dictionary adjective that is a single letter away (one letter added, dropped or changed) and suggested it as a correction.

An entry like that comes about in one of two ways, and your task is to say which this one is:
- "typo": the file has a typing or transcription slip, and the printed list had the suggested word. Example: "good-natired" for "good-natured"; "natired" is not a word, and the slip is one key away.
- "real_word": the entry is a word in its own right, most often an archaic, dialect, literary or rare word that a 1920s unabridged dictionary listed, and the suggested word is a different word that happens to be one letter away. Example: "couthy", a Scots word for friendly and agreeable, is not a misspelling of "couth".
- "unsure": you cannot tell which.

The user turn is one JSON object: "entry" (as the file spells it, capitals included), "suggested" (the correction offered), "before" (the two entries just before it in the same column of the file) and "after" (the two just after it). The list is alphabetical, so the neighbours show where the entry was printed, and a place that fits only one of the two spellings is evidence for that spelling. A few entries are out of order, so treat the place as one piece of evidence, not proof.

Answer "typo" only when you are confident that the entry was not a word of English in its own right. An entry built regularly from a real word (a real root with -less, -ish, -some, -ly, un- and the like) that fits its place in the list is usually a real word, even a rare one.

Respond with one JSON object and nothing else. Give a reason in one or two short sentences first, then the verdict:
{"reason": "<one or two short sentences>", "verdict": "typo" | "real_word" | "unsure"}
````

## Rendered sample

The system turn is the block above, byte for byte.  The user turn for the suggestion Bragless to braless
(column I, line 195), as `repair_check.build_user` writes it:

```text
{"entry": "Bragless", "suggested": "braless", "before": ["Bounceable", "Brag"], "after": ["Brahmin", "Brainwood"]}
```

and for light-dingered to light-fingered (column I, line 1695):

```text
{"entry": "light-dingered", "suggested": "light-fingered", "before": ["lickerish", "liegeman"], "after": ["light-footed", "light-handed"]}
```

## Your notes

## Change log

- Draft 1 (2026-10-14): first text, pinned as version 1.
