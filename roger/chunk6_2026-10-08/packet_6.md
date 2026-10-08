# Chunk 6: the physical track — writer's packet (2026-10-08)

Entries: `entries_6_traits.json` (26 traits) and `entries_6_roles.json` (2
roles: athlete, pregnant), in this directory.  Each is a queue record: read
its `label`, `description_notes`, `decision`, `pairing`, `partner` and
`tags`.  Method: the chunk-3 loop (you draft from the notes under the rules
at the end of this packet; a reviewer reads after you; Roger reads after
generation).  No official text exists for these; no web research is needed.

## Why this chunk is different: the research question (read first)

Roger's ruling of 2026-09-08: these are a **separate research track**.  The
question to be answered after the extraction is whether the model represents
physical attributes as coherent directions, and **whether hair, eye and skin
traits carry behavioural content: whether the model attaches stereotypes of
its own**.  A description that says a red-head is fiery or a blonde carefree
would plant the answer.  So, Roger's rule for this chunk (2026-10-08):

**Every description states only the body and how it is lived, with no
personality or behaviour clause anywhere.**  Physical consequences and the
practicalities of living in that body are fine and wanted (sunburn and SPF
for fair skin; ducking through doorways and the legroom for tall; glasses or
contacts for short sight; left-handed scissors and smudged ink; the fitting
room for heavyset or slender).  How others look at you is fine for the
attractiveness pair (heads turning, or not); vanity, confidence, shyness,
temper, warmth, intelligence and every other character trait are not.  The
test: is each clause something the body is, does, or meets, rather than a way
the person behaves or feels about others?

Specific notes:
- **Pairs are written together** (rule 5), same scope and length, and are
  paired by construction, so do not name the partner: tall / short,
  heavyset / slender, athletic / sedentary, healthy / sickly, good-looking /
  plain-looking, fair-skinned / dark-skinned, male / female.  Words were
  chosen to be neutral; keep the descriptions neutral too.
- **athletic / sedentary** are about physical activity and fitness; the
  activity is the trait (training, sport, the day spent sitting), but no
  personality (no "disciplined", "lazy", "competitive").
- **fair-skinned / dark-skinned**: the skin and the sun (burning, tanning,
  shade-matching foundation, the doctor reading a rash), not race and not
  social experience; the heritage map exists for that.
- **The hair-colour set** (blonde, brunette, red-headed, black-haired,
  grey-haired) and **the eye-colour set** (blue-, brown-, green-eyed): one
  grain per set, the colour and its physical particulars (freckles and
  sunburn go with red hair; light sensitivity with blue eyes; dye, roots,
  fading).  grey-haired may say the grey came with the years as a fact of
  the hair; do not turn it into an age persona.
- **male / female** (Roger, 2026-09-28): bodily sex, not identity and not
  expression (masculine, feminine, nonbinary, neuter and androgynous exist
  for those).  The body as lived: its anatomy and the health particulars that
  follow from it, plainly, as an adult would say it of themselves; nothing on
  roles, roles in the family, or temperament.
- **in chronic pain** (label changed from "in pain", Roger 2026-10-08):
  living with pain that does not go away, distinct from **chronically ill**
  (illness); pain from injury or wear.  Both are the body's standing
  condition, written in the present with the duration in it.
- **healthy / sickly**: standing constitution, not a current illness.
- **short-sighted**, **left-handed**: plain, the particulars of living with
  them.
- **Roles** (athlete, pregnant): the corpus role form, "A <role> is someone
  who ..." (or "An ..."), 23 to 43 words.  athlete: the training, the
  competition, the body as one's instrument (coach, surfer and daredevil
  exist; say how this differs).  pregnant: the months of the body changing,
  the appointments, the due date; no mood stereotypes.

Form for traits: "This means ...", one or two sentences, 18 to 32 words, US
spelling, no label echo in the opening (rule 1; a qualifier that picks the
sense is allowed, as in "short in height" if "short" needs disambiguating),
inside voice, nobody named as partner.

Nearest existing: one line per entry (corpus stems in `corpus_stems.txt`,
role stems in `role_stems.txt`), naming the nearest trait or role and how
this one differs; flag a duplicate plainly.

## Output

Write ONE JSON file, `drafts_6.json`, in this directory: a list with one
object per entry (traits first in the traits file's order, then the two
roles), fields `stem` (use `in_chronic_pain` for the in-pain entry),
`label`, `entity_type`, `description_draft`, `nearest_existing`, `notes`, and
on the first member of each pair or set a `set_review` (one or two lines on
the grain and whether the pair or set reads as one).  Then reply with a short
summary: the number of drafts, the judgement calls, and anything you want
Roger to look at.

## Boundaries

You may read and write ONLY inside the repository checkout you are started in
(the project directory): nothing elsewhere on this machine, no home-directory
paths, no caches, no other projects, no listing of anything outside the
checkout.  Read files with the Read tool.  Do not run any generation script,
do not call any model API, and do not edit anything under `data/`; your only
write is `drafts_6.json` in `roger/chunk6_2026-10-08/`.

## Examples of the corpus form (approved by Roger)

Traits:
- elderly: This means being in one's seventies or beyond, with most of life behind one, a slowing body, grandchildren, and a lifetime of change seen firsthand.
- young: This means being in one's teens or twenties, with most of life ahead, a quick body, friends one's own age, and today's world the only one known.
- blind: This means seeing little or nothing: getting around with a white cane or a guide dog, reading by screen reader and braille, and knowing the route to work by step and touch.
- deaf: This means hearing little or nothing: talking in sign, reading captions, booking an interpreter for the doctor, a doorbell that flashes and an alarm that shakes the bed, and friends who sign.
- teetotaler: This means drinking no alcohol at all, not even a toast at a wedding, and ordering soda when the round comes.
- heavy_drinker: This means drinking a lot and often, always up for another round, and counting several drinks a night as normal.

Roles:
- patient: A patient is someone who is personally experiencing illness, medical treatment, and the vulnerability that comes with navigating healthcare while dealing with their own health concerns.
- coach: A coach is someone who acts as a mentor and guides others toward improvement in their skills, behaviors, or performance through structured guidance, feedback, and supportive strategies.
- surfer: A surfer is someone who lives for riding waves: checking the swell before dawn, paddling out with the regulars at the local break, getting stoked on a good session and skunked on a flat one, and talking about it all in the slang of the lineup.

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
