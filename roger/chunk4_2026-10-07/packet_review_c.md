# Chunk 4, sub-chunk C: sets — reviewer's packet (2026-10-07)

## The task

Review the draft descriptions in the drafts file named in your prompt
(`drafts_c1_mbti.json`: the sixteen MBTI types; or `drafts_c2_sets.json`:
Kohlberg's three levels and the four attachment styles) against the writer's
brief for that file (`packet_c1_mbti.md` or `packet_c2_sets.md`, beside this
file; read it, it holds the method and the rules) and the queue entries
(`entries_c1_mbti.json` / `entries_c2_sets.json`).  You are the second reader
before anything is seeded; Roger reads after generation.  Read, judge, and
write one JSON file; do not edit the drafts file or anything else.

For each entry, check:

1. **Faithful summary.**  Does `description_draft` say what `source_text`
   says, no more and no less?  Anything the passage does not support is an
   issue (the method is summary, not invention); a defining element the
   draft drops is an issue when it leaves the member unrecognisable among
   the others of its set.  For the MBTI types the four preferences must be
   stated plainly (the writer's brief) and the portrait must come from the
   Foundation's paragraph; for the attachment styles the prototype's content
   must be kept, including its hedges; for Kohlberg the draft must describe
   the person's way of deciding right and wrong at that level.
2. **The corpus form.**  Opens "This means" (not by repeating the label);
   one or two sentences; 18 to 32 words; US spelling; inside voice; no
   framework, author, type code, letters or preference names in the
   description; no partner or sibling named.
3. **Strength.**  Mirrors the source: not sharpened, not softened; a hedge
   rendered as its plain-word equivalent, not dropped.  Say for each draft
   whether it sits at, above or below its passage (an issue either way, with
   the clause named).
4. **Nearest existing trait.**  Plausible?  Says so where the new trait is a
   deliberate near-duplicate of a plain corpus trait?
5. **The set as a whole** (the sixteen types; the three levels; the four
   styles): one grain and shape; the structure readable off the set (the
   four dichotomies from the sixteen; the ordered levels or the three
   corners from Kohlberg's three, and say which the descriptions support;
   the anxiety and avoidance axes from the four attachment styles); any
   member described at a different grain from the others.  Agree or disagree
   with the writer's `set_review`.

## Output

Write ONE JSON file, named in your prompt (`review_c1_mbti.json` or
`review_c2_sets.json`), in `roger/chunk4_2026-10-07/`:

```
{
  "entries": [
    {"stem": "...", "verdict": "ok" | "edit",
     "issues": ["..."],                      // one line each; [] when ok
     "suggested_edit": "..." | null,         // a corrected description for form/faithfulness issues ONLY; null otherwise
     "strength": "at source" | "above: <clause>" | "below: <clause>",
     "nearest_existing_ok": true | false}
  ],
  "sets": [
    {"name": "...", "members": ["..."], "review": "...",   // the step-5 judgement
     "agree_with_writer": true | false}
  ],
  "summary": "three or four lines"
}
```

Then reply with the summary only.

## Boundaries

Read and write only inside this repository checkout: nothing elsewhere on the
machine, no home-directory paths, no caches, no other projects.  Your only
write is the one JSON file above.  No web fetches are needed; judge the drafts
against the passages the writer recorded.  To judge a "nearest existing" line
you may read a corpus file under `data/traits/instructions/<stem>.json` with
the Read tool.
