# Chunk 5, sub-chunk C: the two triangles — writer's packet (2026-10-08)

Entries: `entries_5c_triangles.json` (6): honor_culture, dignity_culture,
face_culture (one 2-simplex) and guilt_prone, shame_prone, fear_prone (the
other), approved by Roger on 2026-09-07.  These come from named frameworks,
so the method is Roger's for standards-derived traits (rule 9 at the end of
this packet; worked examples in `reports/seeding_log_2026-10.md`, chunk 4):

1. **Read the approved concept text first**:
   `data/traits/instructions/TRAITS_TO_ADD.md`, the two "2-simplex" bullets
   under "Coverage audit part 2" > "Cultural orientation" (about lines 1225
   to 1252), which also carry the interim bookkeeping rule for seeding a
   triangle.
2. **Locate the canonical description** of each corner and record it
   verbatim (`source_text`, at most about 120 words, `source_url`,
   `source_retrieved`):
   - honor / dignity / face: Leung and Cohen (2011), "Within- and
     between-culture variation: Individual differences and the cultural
     logics of honor, face, and dignity cultures", Journal of Personality and
     Social Psychology 100(3), the authors' own characterisation of the three
     cultural logics (a preprint or an open copy, or the passage as quoted
     verbatim by a later paper, naming the quoting source).
   - guilt / shame / fear: Benedict (1946), The Chrysanthemum and the Sword,
     for guilt and shame cultures (the classic passage, quoted by a reliable
     source if the book is not open), and the fear (or fear-power) culture of
     the guilt-shame-fear spectrum as its missiological authors define it
     (Roland Muller, Honor and Shame: Unlocking the Door, 2000; Jayson
     Georges, The 3D Gospel).  Say which author each corner's text comes
     from.
   Use WebFetch (load it with ToolSearch if it is not in your tool list); if
   a page cannot be fetched, say so in `notes` and use the best alternative;
   never invent a quotation.
3. **Summarise into our form**: "This means ...", 18 to 32 words, US
   spelling, inside voice: the trait is the person who lives by that logic,
   as the queue individualises it (what regulates their conduct and how they
   react when it is breached: an internal conscience; standing in others'
   eyes and the duty to defend it; the fear of a power that punishes), the
   framework and its authors unnamed in the description (`source` records
   provenance).  **Mirror the source's strength**; render a hedge in plain
   words rather than drop it.
4. **The triangle**: three corners judged beside each other, one grain, each
   recognisable against the other two; no `pair_review` (nothing here is a
   pair); write `set_review` on the first corner of each triangle.
5. **Nearest existing trait**: one line per entry (stems in
   `corpus_stems.txt` and `role_stems.txt`); the corpus has honorable,
   proud, conscientious and guilt-adjacent traits, and a conformist /
   contrarian / nonconformist triangle; say how each corner differs.

## Output

Write ONE JSON file, `drafts_5c_triangles.json`, in this directory: a list
with one object per entry (same order), fields `stem`, `label`,
`source_url`, `source_text`, `source_retrieved`, `description_draft`,
`low_pole_derived` (false), `nearest_existing`, `notes`, and on the first
corner of each triangle `set_review`.  Then reply with a short summary:
sources used with URLs, the set reviews, anything you could not fetch.

## Boundaries

You may read and write ONLY inside the repository checkout you are started in
(the project directory): nothing elsewhere on this machine, no home-directory
paths, no caches, no other projects, no listing of anything outside the
checkout.  Read files with the Read tool.  Do not run any generation script,
do not call any model API (web fetches of the public sources named above are fine), and do not edit anything under `data/`; your only
write is the one JSON file named in your prompt, in `roger/chunk5_2026-10-08/`.

## Examples of the corpus form (approved by Roger)

- western_hemisphere: This means being from the Western Hemisphere: born and raised in the Americas, in a country such as Canada, Mexico, Brazil or Chile, and at home there.
- single: This means having no husband or wife, settling one's home, money and plans without a spouse, and checking 'single' on every form.
- teetotaler: This means drinking no alcohol at all, not even a toast at a wedding, and ordering soda when the round comes.
- millennial: This means being born between 1981 and 1996: raised on AOL Instant Messenger, Myspace and Harry Potter, entering work in a recession with student debt, brunching on avocado toast, calling chores 'adulting', confident, tolerant and entitled.
- introverted: This means being drained by company and restored by solitude: keeping to oneself, speaking little in groups, preferring one or two close friends to a crowd, and needing time alone after social occasions.
- isolated: This means having no friends or contacts anywhere, nobody to call for a favor, a job lead or a word in the right ear.
- quarrelsome_hexaco: This means nursing a grudge against anyone who has done one wrong, being critical of other people's shortcomings, refusing to budge in an argument, and quick to anger when wronged.
- loose_gelfand: This means holding weak rules of conduct, leaving most situations open, putting up readily with behavior that steps well outside the usual, and being at ease with ambiguity and impulsivity.

## The rules (from AGENT_NOTES.md, via .claude/rules/trait-pairs.md)

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
   with no source text of its own is derived from what the instrument
   says about that side (its author's account of such people in the
   papers or the book, sources recorded on the queue entry), and only
   where the instrument says nothing from the high pole's content as
   opposite behaviour; either way it is tagged `low_pole_derived`.
   Roger, 2026-10-08: an official pair means what the theory means when
   applied to a persona, so a clause the instrument gives one pole
   (Gelfand's "need for structure, high regulatory strength") is kept and
   its counterpart derived, not cut.  When the instrument's site is gone,
   the Internet Archive's capture of its own page is the official text
   (record the capture date beside the URL; the CDX index with
   `filter=statuscode:200` lists the captures, and an `id_` URL returns
   the raw page), as for VALS.  Standards pairs are paired by
   construction; the antonym check is informational.  Worked examples:
   chunk 4 in `reports/seeding_log_2026-10.md` (sub-chunk A; the Gelfand
   and VALS items of the consolidated decisions).
