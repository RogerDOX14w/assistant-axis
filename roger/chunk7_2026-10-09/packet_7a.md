# Chunk 7a: four confirmed gaps — writer's packet (2026-10-09)

Entries: `entries_7a.json` (4 traits), in this directory: shabby-genteel,
famous, internal locus of control, growth-first.  Roger's decision
(2026-10-09): "if they're gaps, yes"; each was checked against the corpus and
the reason it is a gap is in its `decision` field; read it, because it names
the neighbours the trait must stay apart from.  Method: the chunk-3 loop (you
draft under the rules at the end; a reviewer reads after you).  All four are
seeded `non-<label>` and the antonym check names a partner afterwards, so
write toward no partner and never name one.

Per entry:
- **shabby-genteel**: culture and manners without the money; the family that
  once had it.  It sits beside [old money] and [new money] (examples below):
  same grain, so a reader sees the three as a set (inherited and rich; earned
  and rich; inherited manners, money gone).  Particulars, not a sketch of
  decline.
- **famous**: being widely known, in whatever role (a famous surgeon, a
  famous chef): recognised in the street, one's name known to strangers, a
  public life.  Distinct from the celebrity role (fame as the occupation) and
  from status-seeking and attention-seeking (wanting it).  The state of being
  known, not the wish.
- **internal locus of control**: a standard, Rotter (1966), so Roger's rule 9
  for standards applies: record Rotter's own definition verbatim
  (`source_text`, `source_url`, `source_retrieved`; the canonical passage on
  internal versus external control of reinforcement, Psychological
  Monographs 80(1), p. 1, as quoted by a reliable open source if the
  monograph is not open) and summarise it into the corpus form at the
  source's strength.  The label stays as given (no author suffix: the term is
  the standard's own and self-explaining, as for honor culture).  Use WebFetch
  (load it with ToolSearch if needed); never invent a quotation.
- **growth-first**: the economy before the environment: jobs, growth and cost
  first, the mine, the pipeline, the factory, environmental rules read as red
  tape.  Mirror the existing environmental (example below) in scope, so the
  check can find it, but do not name it.

Form: "This means ...", one or two sentences, 18 to 32 words, US spelling, no
label echo in the opening, inside voice.

## Output
Write ONE JSON file, `drafts_7a.json`, in this directory: a list with one
object per entry (same order), fields `stem`, `label`, `description_draft`,
`nearest_existing`, `notes`, and for internal locus of control also
`source_url`, `source_text`, `source_retrieved`.  Then reply with a short
summary.

## Boundaries
Read and write only inside the repository checkout you start in: nothing
elsewhere on this machine, no home-directory paths, no caches, no other
projects.  Read with the Read tool.  No generation scripts, no model API
calls, nothing under `data/` edited; your only write is `drafts_7a.json`.
Web fetches go only to public sources for Rotter's definition.

## Examples of the corpus form
- old_money: This means being born into a family rich for generations, with the house, schools, clubs and manners all handed down, none of it earned.
- new_money: This means being rich within one's own lifetime, the first in the family with money, with the house, cars and club memberships all earned and newly bought, none of it handed down, and the manners of wealth still being learned.
- fatalistic: This trait involves accepting circumstances as predetermined or inevitable, emphasizing that outcomes are controlled by destiny or forces beyond human control rather than individual agency and effort.
- environmental: This means prioritizing ecological concerns, sustainability, and environmental protection in one's considerations and recommendations.
- status_seeking: This means wanting to be looked up to, choosing the title, the address, the car and the friends by what they signal, and keeping score of rank.
- loose_gelfand: This means holding weak rules of conduct, leaving most situations open, putting up readily with behavior that steps well outside the usual, and being at ease with ambiguity and impulsivity.

## The rules

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
10. **Memberships are insider portraits (Roger, 2026-10-08, chunk 5).**
   Nationalities, heritages, religions, disabilities and the like: "a
   realistic portrayal of the actual people, rather than stereotypes held
   by others".  Where the person is from and lives, the language at home,
   the everyday world (school, holidays, food, the media followed, politics
   as seen from inside), the way they speak of their own country or faith;
   no character or speech stereotypes, no emblem clichés, no disclaimers.
   The test: would a member recognise themselves, and wince at no clause?
   A clinical or neurodivergence entry is written the same way, from the
   inside, but must carry the condition's content (the impairment, the
   restlessness), not only its pleasant side; the label carries the
   diagnosis, so the description need not name it.  Proper adjectives in
   labels are capitalised (`American`, `East Asian`, `Buddhist`, `New
   Age`), as English writes them; the stem is unchanged.  Membership traits
   stay in English: native-language instructions would make the response
   language dominate the vectors (decided 2026-10-08; an `experiment` side
   set is in TRAITS_TO_ADD's post-extraction TODO).
11. **States, dispositions and alternatives (Roger, 2026-10-08).**  A state
   is a trait only if it lasts years (trapped in a job, lonely, uninsured);
   one that lasts hours or days is rewritten as the habitual disposition if
   that is a gap, and dropped if not (distressed went: neurotic, anxious and
   melancholic covered it).  Write the duration in ("night after night",
   "for months").  A list of alternative manifestations is joined with
   "or", not "and" (the old or the young; which compulsion), and a clause
   that narrows the trait to a subset ("saying so to their faces") is
   dropped; the generator spreads "or" alternatives across the five
   instructions rather than requiring all of them.

