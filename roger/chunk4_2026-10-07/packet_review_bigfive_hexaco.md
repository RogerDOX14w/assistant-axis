# Chunk 4, sub-chunk A: Big Five and HEXACO — reviewer's packet (2026-10-07)

## The task

Review the 22 draft descriptions in `drafts_bigfive_hexaco.json` (beside this
file) against the writer's brief in `packet_bigfive_hexaco.md` (read it: it
holds the method and the rules).  You are the second reader before anything is
seeded; Roger reads after generation, with the antonym-check results beside
the descriptions.  Read, judge, and write one JSON file; do not edit the drafts
file or anything else.

For each entry, check:

1. **Faithful summary.**  Does `description_draft` say what `source_text`
   says, no more and no less?  Anything in the draft that the passage does
   not support is an issue (the method is summary, not invention); a defining
   facet of the factor that the draft drops is an issue when it leaves the
   pole unrecognisable.  Where `low_pole_derived` is true there is no source
   text for that pole: judge instead whether the draft is the opposite
   behaviour of the high pole's content, not an absence ("not X").
2. **The corpus form.**  Opens "This means" (not by repeating the label); one
   or two sentences; 18 to 32 words; US spelling; inside voice (no "individuals
   who", "tends to", "exhibits", "demonstrates"); no hedges ("appropriately",
   "may", "sometimes", "healthy"); a vice pole unsoftened; **the instrument is
   not named in the description**; no partner named in the description.
3. **Nearest existing trait.**  Is the line plausible, and does it say so
   where the new trait is a deliberate near-duplicate of a plain corpus trait
   (conscientious, extraverted, introverted, agreeable, neurotic, emotional)?
4. **Per pair** (the two poles together, both `source_text`s and both drafts):
   accidental differences of scope or phrasing between the two drafts, such
   as one pole covering four facets and the other two, one in behaviour and
   the other in feelings, one about people and the other about tasks, or a
   difference of length beyond what the sources explain.  Record what you see
   and what a re-edit would do; **do not rewrite for this**: Roger decides.
   Agree or disagree with the writer's own `pair_review`.
5. **Across the set** (the five Big Five pairs; the six HEXACO pairs): are the
   descriptions of one shape and weight, so that no factor is described at a
   different grain from the others?

## Output

Write ONE JSON file, `roger/chunk4_2026-10-07/review_bigfive_hexaco.json`:

```
{
  "entries": [
    {"stem": "...", "verdict": "ok" | "edit",
     "issues": ["..."],                      // form or faithfulness issues, each one line; [] when ok
     "suggested_edit": "..." | null,         // a corrected description for form/faithfulness issues ONLY; null otherwise
     "nearest_existing_ok": true | false}
  ],
  "pairs": [
    {"members": ["stem_a", "stem_b"], "scope_flag": "..." | "",   // the step-4 comparison; "" when nothing to flag
     "agree_with_writer": true | false}
  ],
  "set_notes": {"Big Five": "...", "HEXACO": "..."},
  "summary": "three or four lines"
}
```

Then reply with the summary only.

## Boundaries

Read and write only inside this repository checkout: nothing elsewhere on the
machine, no home-directory paths, no caches, no other projects.  Your only
write is the one JSON file above.  No web fetches are needed; judge the drafts
against the passages the writer recorded.
