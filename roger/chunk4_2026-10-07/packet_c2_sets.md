# Chunk 4, sub-chunk C2: Kohlberg's three levels and the four attachment styles — writer's packet (2026-10-07)

## The task

Draft the `description` of 7 trait files, two sets drawn from named
frameworks, by Roger's method for standards-derived traits (as in sub-chunks
A and B, including the strength rule):

1. **Locate the official or canonical description** of each member and
   record it: the passage verbatim (`source_text`, at most about 120 words),
   its `source_url`, and `source_retrieved` (today's date).
   - **Kohlberg's three levels** (preconventional, conventional,
     postconventional): Kohlberg's own characterisation of the levels (e.g.
     Kohlberg 1976, "Moral stages and moralization", or Kohlberg 1971,
     "Stages of moral development as a basis for moral education"), as
     quoted in a scholarly or encyclopedic source with the quoting source
     named.  The trait is the **person who reasons at that level** about
     right and wrong (the queue's notes); describe the person's way of
     deciding, not the theory or the stages' numbers.
   - **The four attachment styles** (secure, anxious-preoccupied,
     dismissive-avoidant, fearful-avoidant): Bartholomew & Horowitz 1991
     (JPSP 61, "Attachment styles among young adults: a test of a
     four-category model"), whose four prototype paragraphs ("It is easy for
     me to become emotionally close to others ...", "I want to be completely
     emotionally intimate with others ...", "I am comfortable without close
     emotional relationships ...", "I am somewhat uncomfortable getting
     close to others ...") are the canonical text and are quoted verbatim in
     many later papers and in the Wikipedia article "Attachment in adults".
     The queue's labels are the common hybrid names; the Foundation's names
     are secure / preoccupied / dismissing / fearful: record which the
     source uses.  The trait is the adult with that style in close
     relationships.
   Use the web (WebFetch; load it with ToolSearch if needed); if a page
   cannot be fetched, say so in `notes` and use the best alternative; never
   invent a quotation.
2. **Summarise into our form**: "This means ...", one or two sentences, 18 to
   32 words, US spelling, inside voice (the prototypes are already first
   person: keep their content, but write in the corpus's "one" / "oneself"
   form, not "I"), no label echo in the opening, the framework and author
   unnamed in the description.
3. **Mirror the source's strength** (Roger, 2026-10-07): do not sharpen or
   soften; render a hedge ("somewhat", "sometimes") as its plain-word
   equivalent, not drop it.  Bartholomew & Horowitz's prototypes carry
   hedges; keep them.
4. **The sets.**  Kohlberg's three are one structure (the queue says
   `triangle`; the notes say a `sequence` is also conceivable, since the
   levels are ordered: say in `set_review` which reading the descriptions
   support).  The attachment four are a square whose two axes (anxiety about
   abandonment, avoidance of closeness) should be readable off the four
   descriptions: same grain and shape across the four, and on the FIRST
   attachment entry a `set_review` string saying whether the two axes come
   through.  No `pair_review`.
5. **Nearest existing trait**: one line per entry (corpus stems in
   `corpus_stems.txt`); clingy, insecure, detached, guarded and the
   moral-reasoning traits (Kantian, consequentialist, conformist ...) are the
   neighbours to check.

## Output

Write ONE JSON file, `roger/chunk4_2026-10-07/drafts_c2_sets.json`: a list
with one object per entry in `entries_c2_sets.json` (same order), fields:
`stem`, `label`, `source_url`, `source_text`, `source_retrieved`,
`description_draft`, `low_pole_derived` (always false here), `nearest_existing`,
`notes`, and on the FIRST entry of each set `set_review`.  Then reply with a
short summary: sources used with URLs, number of drafts, the set reviews,
anything you could not fetch.

## Boundaries

You may read and write ONLY inside the repository checkout you are started in
(the project directory): nothing elsewhere on this machine, no home-directory
paths, no caches, no other projects.  Read with the Read tool.  Do not run any
generation script and do not edit `data/`; your only write is the one JSON
file above.  Web fetches go to the public sources named here.

## Entries

See `entries_c2_sets.json` beside this packet.

## Examples of the corpus form (sub-chunks A and B, approved by Roger)

- quarrelsome (HEXACO): This means nursing a grudge against anyone who has done one wrong, being critical of other people's shortcomings, refusing to budge in an argument, and quick to anger when wronged.
- intrinsic (Allport): This means making religion the master motive of one's life, fitting one's other needs around it, and, having taken up a creed, striving to make it one's own and follow it fully.
- loose (Gelfand): This means holding only weak rules of conduct, leaving people to decide for themselves how to behave in most situations, and putting up readily with behavior that steps well outside the usual.

## The rules (from AGENT_NOTES.md)

**Standard-derived trait labels: `<pole> (<Standard>)` (Sep 2026; parentheses adopted 2026-09-09).**
When a trait or axis is imported from a named, well-known instrument
(Inglehart–Welzel cultural map, Big Five, HEXACO, Hofstede, Moral
Foundations, ...), the standard's name goes into the label as a
parenthesised, capitalised suffix and into the file name lowercased with
the parentheses dropped:

| `positive_label` (display, stored in JSON) | file stem (`normalize_to_file_name`) |
| --- | --- |
| `traditional (Inglehart-Welzel)` | `traditional_inglehart_welzel` |
| `secular-rational (Inglehart-Welzel)` | `secular_rational_inglehart_welzel` |
| `survival (Inglehart-Welzel)` | `survival_inglehart_welzel` |
| `self-expression (Inglehart-Welzel)` | `self_expression_inglehart_welzel` |
| `openness (Big Five)` | `openness_big_five` |

Rules:

1. **Pole first, standard second**, using the standard's own pole
   names and its own written form (`Big Five`, not `Big-5`; acronyms
   in caps, `HEXACO`).  Capitalisation is what marks the suffix as a
   proper name; there is precedent for capitals and spaces in labels
   (`Kantian`, `cultural relativist` as negative labels).
2. **`positive_label` is the canonical display form**; the stem is
   derived from it by `normalize_to_file_name` (lowercase, apostrophes
   dropped, hyphens and spaces → `_`, parentheses dropped, diacritics
   folded to ASCII so `Gemeinschaft (Tönnies)` → `gemeinschaft_tonnies`;
   stems stay ASCII
   because macOS and Linux normalise accented file names differently).
   The reverse is lossy in four new ways (capitals, diacritics, the
   hyphen inside a double-barrelled name, the pole/standard boundary), which is why plot text must go through
   `corpus_display_name`, never `stem.replace("_", " ")`.
3. **`negative_label` uses the full partner label**
   (`secular-rational (Inglehart-Welzel)`), so the antonym clause in the
   generation prompt and the clean-pair check both see the same string.
4. **Descriptions do not name the source.**  Paraphrase the canonical
   one-to-two-sentence definition (recognisable to anyone who knows the
   instrument; do not quote it verbatim).  Record provenance in an
   optional `"source"` field on the trait JSON instead, e.g.
   `"source": "Inglehart & Welzel, World Values Survey cultural map, traditional vs secular-rational values axis"`.
   Both regenerate scripts carry unknown fields forward.
5. **Import a standard's version only when its canonical definition
   differs materially from an existing ad-hoc trait, or when the
   comparison is the experiment.**  `conscientious`, `extroverted`,
   `introverted`, `agreeable`, `neurotic` already exist; a
   `conscientious (Big Five)` beside `conscientious` is deliberate
   duplication, not an oversight, and should say so in `source`.
6. Watch the generated instructions: the label is injected as the
   trait name and antonym clause, so the generator can leak the
   standard's name into a persona system prompt ("in the
   Inglehart-Welzel sense").  The description carries the substance;
   eyeball the pos/neg pairs and regenerate if it leaks.  If it
   recurs, add a per-trait generation-label override rather than
   changing the naming.
7. **TODO before the first judging run that includes these traits
   (Roger, 2026-10-07):** in the axis-judging rubric the pole should
   read "careless (from HEXACO)", not "careless (HEXACO)": default to
   inserting "from" at the display site the prompt builders use
   (`display_form_name`), with a hard-coded list of the sets where the
   definite article or another form reads better ("from the Big Five",
   "from the Enneagram").  A rubric change: bump `RUBRIC_VERSION`.  The
   stored label is unchanged.  Details in
   `reports/seeding_log_2026-10.md` § "TODOs for this chunk".


### Description-writing rules for new seeds

### Description-writing rules for new seeds (Sep 2026)

What the voice / softening audit (2026-09-09), the role rubric V2 pilot
(2026-09-11..12) and the Qwen response checks (2026-09-11, 2026-09-16)
taught about writing the `description` of a new trait or role.  The
description is the only hand-written text; everything else is generated
from it and echoes it, so a hedge or an outsider's word here reaches the
instructions, the eval prompt and (for roles) the responses.  Apply these
to every seed, by hand or by a writing agent; Roger reviews before
`seed_entities.py write`.

1. **Form.**  Traits: "This means ..." (274 of 302 files; normalised
   2026-09-07), one or two sentences, 18-32 words (p10-p90; median 24),
   US English.  Roles: "A <role> is someone who ..." / "An <role> is a
   ... that ..." for the recent files (older ones use "This refers to"),
   23-43 words (median 28).  **Do not open by repeating the label**
   ("This means being grateful: ...").  Roger, 2026-09-27: every prompt
   that uses a description supplies the label right beside it
   (`**{positive_label}**. {description}` in the generator, the eval
   prompt and the pipeline judge; `**{name}**: {content}` in static
   judging; the axis name and examples in the axis rubric header, where
   the description is the pole text), so "X: This means being X: ..." is
   pure repetition.  Go straight to the behaviour ("This means noticing
   every kindness, ...") or open with a short gloss that paraphrases the
   trait and then expand it ("This means being drained by company and
   restored by solitude: keeping to oneself, ...").  Keep a label in the
   opening only when it carries a qualifier that picks the sense
   ("aristocratic about rank", "tough on people", "from the Eastern
   Hemisphere", "having a calm temperament").  An earlier version of this
   rule prescribed the label anchor, and 344 of the 390 descriptions
   written in September 2026 had it (2 of the 258 older ones); see
   `reports/seeding_log_2026-09.md` for the clean-up.
2. **The vice is a vice.**  No "appropriately", "when appropriate",
   "overly", "excessive", "too", "sometimes", "may", "can", "tends to",
   "healthy", "in a balanced way"; no virtue-framing of an edgy trait
   (irreverent is not "questions pretension", it jokes about the sacred and
   does not care) and no villain-laundering of a bad role (a destroyer
   destroys; a smuggler moves contraband for money).  A softened
   description samples the inoffensive centre of the concept and the
   pole then sits on top of an existing milder trait.
3. **Inside voice.**  Write in words the persona would use of itself:
   no case-worker, policy, clinical or anthropologist's vocabulary
   ("marginalised", "engages in", "exhibits", "demonstrates", "navigates",
   "individuals who"); name the particulars of the role's world (the
   tools, the customers, the hours, the enemy) rather than its category.
   For roles this matters most: the register of the description was found
   to propagate through the instructions into Qwen's responses.  For
   traits the instruction register does not propagate, but self-labelling
   does, so avoid handing the generator a paragraph it can quote back.
4. **Scope by a test, not by a list of synonyms.**  State what separates
   this pole from its nearest neighbours, ideally as one question the
   judge can ask ("would the persona do this if the setting were real?",
   "does the persona argue for continuing, or simply never ask?").  Check
   the nearest existing traits and roles before writing (nine names exist
   on both sides; `ls data/{traits,roles}/instructions`), and if the new
   entity is a deliberate near-duplicate of an existing one (a standard's
   version of a plain trait), say so in `source`, never in the
   description.
5. **Pairs are written together.**  Both poles get the same scope, the
   same trigger and the same length; the neg pole is an opposite, not an
   absence ("course-correcting", not "non-tunnel-visioned"), and where no
   opposite exists the seed keeps `non-X` and the antonym check decides.
   Name the mechanism that keeps two neighbouring pairs apart (motivated
   vs unmotivated; a frame believed not to count vs stakes believed high).
   **Do not name the partner in the description** (no "This means being
   X, never Y: ..."; no "The opposite of Y." tail).  Roger, 2026-09-25:
   naming the partner is a thumb on the clean-pair scale (the check is
   supposed to find the partner from the behaviour, and the label is
   already injected into the neg instructions) and probably pulls the two
   poles' description embeddings together.  It is a last resort for a
   pair that cannot be had any other way, recorded as such.  The
   pre-September corpus's "... rather than <opposite behaviour>" clause
   (86 of the 306 files at commit `93a8554`) is tolerated but should be
   used only where the word is polysemous and the contrast picks the sense ("temperate" about
   beliefs, not drink); prefer letting the body after the colon do the
   work.  The 2026-09-25 chunk-3 packets prescribed "never X"; 81 seeded
   files and the 3D drafts were stripped and rechecked on 2026-09-26 (see
   `reports/seeding_log_2026-09.md`).
6. **Standards.**  For a named instrument, paraphrase the canonical
   definition in the corpus form, keep the instrument's name out of the
   description, put the provenance in `source`, and label
   `<pole> (<Standard>)` (§ "Standard-derived trait labels").
7. **Things that are not the description's job.**  Questions and eval
   prompts are generated; do not steer them from the description.  The
   only exception is a scope sentence the questions must respect (for
   the frame pair: every question inside a stated frame), which goes in
   the queue entry's `description_notes` for the reviewer, not in the
   description.
8. **Sensitive entities** (the part-4 sensitive batch, the physical
   track, demographic memberships): the same rules; the description
   states the membership or attribute plainly and stops.  No disclaimers,
   no "respectfully".  The generator's refusals are handled at generation
   time, not by hedging the seed.
9. **Standards-derived entities (chunk 4 onward; Roger, 2026-10-06/07)**
   are written from the instrument's own text, not drafted from notes:
   locate an official description of the pole, record the passage
   verbatim with its URL and date in the queue entry (`source_text`,
   `source_url`, `source_retrieved`; the file's `source` carries
   instrument and URL), and summarise it into the form above.  Two
   departures from rules 2 and 5: **mirror the source's strength** (the
   vice rule and the hedge list do not apply to a pre-balanced official
   pair; do not sharpen a mild source or soften a strong one; render a
   psychometric hedge such as "tend to" or "rather" as its plain-word
   equivalent, not drop it; note a pole that comes out markedly milder
   than the corpus's plain traits), and **do not force the two poles into
   anti-parallel phrasing**: summarise each from its own source, and let
   a reviewer read both originals and both drafts and flag accidental
   differences of scope or phrasing for Roger to decide.  A low pole
   with no source text is derived from the high pole's content, as
   opposite behaviour, and tagged `low_pole_derived`.  Standards pairs
   are paired by construction; the antonym check is informational.
   Worked example: chunk 4 sub-chunk A in `reports/seeding_log_2026-10.md`.

