# Chunk 5: reviewer's packet (2026-10-08)

## The task

Review the draft descriptions in the drafts file named in your prompt
(`drafts_5a.json`, `drafts_5b_maps.json`, `drafts_5b_sets.json` or
`drafts_5c_triangles.json`) against the writer's brief for that file
(`packet_5a.md`, `packet_5b.md` or `packet_5c_triangles.md`, beside this
file; read it first, it holds the method and the rules) and the queue
entries (`entries_5a_unpaired.json`, `entries_5b_maps.json`,
`entries_5b_sets.json`, `entries_5c_triangles.json`).  You are the second
reader before anything is seeded; Roger reads after generation.  Read, judge
and write one JSON file; do not edit the drafts file or anything else.

For each entry, check:

1. **Faithful to the entry.**  Does the draft describe what the queue's
   `description_notes` and `decision` call for, with the sense the notes fix
   (neuter against nonbinary; indian the nationality, south_asian the
   ethnicity; compulsive against obsessive)?  For `drafts_5c_triangles.json`
   the test is the chunk-4 one: does the draft say what `source_text` says,
   no more and no less, at the source's strength?
2. **The corpus form.**  Opens "This means" without repeating the label; one
   or two sentences; 18 to 32 words; US spelling; inside voice; no partner or
   sibling named; no framework or author named (5C).
3. **Roger's rule for the group** (in the writer's packet): memberships as
   a realistic insider's portrayal with no stereotype held by others, no
   emblem clichés, no disclaimers; clinical and neurodivergence entries from
   the inside, no clinical vocabulary, not deficits; states described as
   lived now; the vice a vice for the sensitive attitudes; nothing softened
   and nothing sharpened.  Apply the wince test to every membership: would a
   person of that membership recognise themselves and not wince at any
   clause?  Name the clause when they would.
4. **Nearest existing.**  Plausible?  Read the named neighbour's file under
   `data/traits/instructions/` or `data/roles/instructions/` with the Read
   tool where the difference is the point.  Flag a likely duplicate plainly.
5. **The set or map as a whole** (each nationality map, each ethnicity map,
   the religions, the relationship structures, the disabilities, each
   triangle): one grain and shape; any member described at a different grain
   from the others; agree or disagree with the writer's `set_review`.

## Output

Write ONE JSON file, named in your prompt (`review_5a.json`,
`review_5b_maps.json`, `review_5b_sets.json` or `review_5c_triangles.json`),
in `roger/chunk5_2026-10-08/`:

```
{
  "entries": [
    {"stem": "...", "verdict": "ok" | "edit",
     "issues": ["..."],                      // one line each; [] when ok
     "suggested_edit": "..." | null,         // a corrected description for form, faithfulness or rule issues ONLY; null otherwise
     "strength": "at the notes" | "above: <clause>" | "below: <clause>",
     "nearest_existing_ok": true | false}
  ],
  "sets": [
    {"name": "...", "members": ["..."], "review": "...", "agree_with_writer": true | false}
  ],
  "summary": "three or four lines"
}
```

Then reply with the summary only.

## Boundaries

Read and write only inside this repository checkout: nothing elsewhere on the
machine, no home-directory paths, no caches, no other projects.  Your only
write is the one JSON file above.  No web fetches are needed; judge the drafts
against the entries, the packet and, for 5C, the recorded passages.
