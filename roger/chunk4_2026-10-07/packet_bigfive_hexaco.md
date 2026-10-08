# Chunk 4, sub-chunk A: Big Five and HEXACO factor pairs — writer's packet (2026-10-07)

## The task

Draft the `description` of 22 trait files (5 Big Five pairs, 6 HEXACO pairs) by
Roger's method for standards-derived traits:

1. **Locate an official description** of the pole, of our length or longer, and
   record it: the passage verbatim (`source_text`, kept to the sentences you
   actually summarise, at most about 120 words), its `source_url`, and
   `source_retrieved` (today's date).  Preferred sources: Big Five: Costa &
   McCrae's NEO-PI-R domain definitions as reproduced in John & Srivastava
   (1999, "The Big Five trait taxonomy", table of facets and adjectives) or
   another scholarly summary that gives BOTH poles (the NEO manual describes
   high and low scorers); HEXACO: hexaco.org's scale descriptions
   (hexaco.org/scaledescriptions), which describe high and low scorers of each
   factor.  Use the web (WebFetch; load it with ToolSearch if it is not in your
   tool list).  If a page cannot be fetched, say so in the entry's `notes` and
   use the best scholarly alternative you can fetch; never invent a quotation.
2. **Summarise or edit it into our form**: "This means ...", one or two
   sentences, 18 to 32 words, US spelling, inside voice (words the persona
   would use of itself, not "individuals high in X tend to"), concrete
   behaviour over abstract nouns where the source allows it, no hedges
   ("tends to", "may", "appropriately"), the vice unsoftened for a vice pole,
   and **the description does not name the instrument** (the label does; the
   `source` field records provenance).  Do not open by repeating the label.
   Keep the instrument's defining content: a Big Five / HEXACO factor is
   defined by its facets, so the description should let a reader recognise
   those facets (e.g. HEXACO Honesty-Humility: sincerity, fairness, greed
   avoidance, modesty) without listing them as a catalogue.
3. **Do not force the two poles of a pair into anti-parallel phrasing.**
   Summarise each pole from its own source text.  Then, for each pair, read
   both originals and both drafts and record under `pair_review` any
   accidental difference in scope or phrasing between the two drafts that a
   re-edit might fix — flag it, do not fix it; Roger decides.
4. **Low poles**: where the source describes the low scorer, summarise that.
   Where it does not (likely for some Big Five low poles), draft the low pole
   from the high pole's defining content, written as the opposite behaviour,
   not as an absence, and set `low_pole_derived: true`.
5. **Nearest existing trait**: one line per entry naming the closest trait
   already in the corpus (the list of stems is in `corpus_stems.txt` beside
   this packet) and how the new one differs.  The Big Five / HEXACO versions of
   conscientious, extraverted, introverted, agreeable, neurotic, emotional
   are deliberate near-duplicates of plain corpus traits; say so.

## Output

Write ONE JSON file, `roger/chunk4_2026-10-07/drafts_bigfive_hexaco.json`: a
list with one object per entry in `entries_bigfive_hexaco.json` (same order),
fields: `stem`, `label`, `source_url`, `source_text`, `source_retrieved`,
`description_draft`, `low_pole_derived` (bool), `nearest_existing` (one line),
`notes` (anything Roger should know, or ""), and on the FIRST member of each
pair a `pair_review` string (the scope/phrasing comparison of the pair; "" if
nothing to flag).  Then reply with a short summary: sources used, how many
drafts, the pair flags, anything you could not fetch.

## Boundaries

You may read and write ONLY inside the repository checkout you are started in
(the project directory): nothing elsewhere on this machine, no home-directory
paths, no caches, no other projects.  Read with the Read tool.  Do not run
any generation script and do not edit `data/`; your only writes are the one
JSON file above.  Web fetches go to the public sources named here.

## Entries

See `entries_bigfive_hexaco.json` beside this packet (label, partner, pairing,
arrangement members, the queue's `description_notes` and `decision`, and the
provisional `source` string).

## Examples of the corpus form (recent, standard-inspired traits)

- isolated: This means having no friends or contacts anywhere, nobody to call for a favor, a job lead or a word in the right ear.
- puritanical: This means condemning sex, drink, drugs and foul language at every turn, in oneself and in others, and finding something shameful in all of it.
- absorption-prone: This means sinking so deep into a novel, a piece of music, a sunset or a daydream that the room, the clock and oneself drop away.
- death-fearing: This means being haunted by knowing one will die. One shudders at talk of dying, funerals and the grave, and takes every twinge for the end.
- superstitious: This means knocking on wood, dreading the thirteenth, carrying the lucky charm, and believing small rituals and omens steer what happens next.

## The rules (from AGENT_NOTES.md)

### Standard-derived labels
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

