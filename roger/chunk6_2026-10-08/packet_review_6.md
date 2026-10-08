# Chunk 6: reviewer's packet (2026-10-08)

## The task

Review the draft descriptions in the drafts file named in your prompt
(`drafts_6.json`) against the writer's brief for that file
(`packet_6.md`, beside this file; read it first, it holds the method, Roger's body-only rule and the rules) and the queue
entries (`entries_6_traits.json`, `entries_6_roles.json`).  You are the second
reader before anything is seeded; Roger reads after generation.  Read, judge
and write one JSON file; do not edit the drafts file or anything else.

For each entry, check:

1. **Faithful to the entry.**  Does the draft describe what the queue's
   `description_notes` and `decision` call for, with the sense the notes fix
   (bodily sex for male and female; chronic pain, not acute; standing
   constitution for healthy and sickly)?
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

Write ONE JSON file, named in your prompt (`review_6.json`),
in `roger/chunk6_2026-10-08/`:

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

## Chunk 6 addition

The first check for every draft is Roger's body-only rule (packet_6.md, "Why
this chunk is different"): name any clause that states personality, temper,
attitude or behaviour beyond the physical activity a trait is about, and give
a corrected text.  A stereotype carried in by a particular counts (freckles
are fine for red hair; "fiery" is not).  Pairs must match in scope and length.
