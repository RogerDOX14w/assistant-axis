# Chunk 5, sub-chunk B: memberships — writers' packet (2026-10-08)

Two writers share this packet; your prompt names your group and its entries
file: `entries_5b_maps.json` (20: thirteen nationalities and seven ethnic
or racial memberships) or `entries_5b_sets.json` (29: eight religions and
five belief singletons; the five relationship structures; seven orientation,
sexuality and gender-expression entries; three disabilities; suburban).  Each
entry is a queue record: read its `label`, `description_notes`, `decision`,
`tags`, `pairing` and `arrangement_members`.  Method: Roger's for plain
traits (chunk 3), the description written from the notes under the rules at
the end of this packet, plus his rule for memberships below.

## Roger's rule for memberships (2026-10-08)

**A realistic portrayal of the actual people, not the stereotypes held by
others.**  Write as an insider would present themselves: where the person is
from and lives, the language spoken at home, the everyday world (work,
school, food, family, weather, the holidays kept, the media followed,
politics as seen from inside), and the way they speak about their own
country, faith or community.  No character stereotypes (the French are not
rude, the Germans not humourless, the Japanese not inscrutable); no
speech stereotypes (unlike the generations, where Roger wanted the cohorts'
slang); no emblem clichés (berets, kangaroos, sushi) unless they are real
everyday particulars said from the inside.  The test: would a person of that
membership recognise themselves, and would they wince at any clause?  Rule 8
holds: state the membership plainly and stop; no disclaimers, no
"respectfully", no "diverse" or "rich culture".  Every membership here is
abundantly represented online; write from that knowledge, check a demonym or
a particular if unsure, never quote.  No `source_text` is required; record a
`source_url` only if you checked a fact against a page.

## The maps (writer 1)

- **Nationalities** (american, australian, brazilian, british, canadian,
  chinese, french, german, indian, italian, japanese, nigerian, russian): a
  citizen and resident of that country (american is a US citizen; british the
  UK; chinese the People's Republic; indian the nationality, where
  south_asian is the ethnicity).  One grain and shape across the thirteen:
  the same kinds of particulars for each, so that the map reads off the set.
  Distinct from the attitude traits nationalist and patriotic, which exist.
- **Ethnic and racial memberships** (african, east_asian, european,
  indigenous_american, indigenous_australian, middle_eastern, south_asian):
  coarse categories as the notes define them (african is sub-Saharan;
  middle_eastern takes North Africa).  Heritage and background, not current
  residence: family origin, the languages of the family, the community; the
  person may live anywhere.  One grain across the seven, and a grain plainly
  different from the nationalities (heritage, not citizenship).
- Write `set_review` on the first member of each map (african, american):
  the grain you chose and anything uneven.

## The sets (writer 2)

- **Religions** (buddhist, christian, hindu, jewish, muslim, shinto, sikh,
  taoist): the believer's own account: what they hold and how they practise
  (prayer, scripture, festivals, food rules, the community they belong to),
  as a practising member would say it; not a comparative-religion sketch and
  not doctrine for outsiders.  One grain across the eight; `set_review` on
  buddhist.
- **Belief singletons**: atheist (explicit non-belief; `secular`, which
  exists, is reasoning without religion, atheist is the stance), antitheist
  (hostile to religion; the vice rule applies, say it plainly), pagan
  (contemporary paganism and animism as practised; the witch and shaman roles
  exist), new_age (a bare candidate: the conventional sense, energies,
  crystals, astrology, alternative healing, personal spiritual growth),
  technomystical (the queue draft: technology as spiritual or as revealing
  spiritual truths; AI, the internet and computation sacred; read
  `data/traits/instructions/techno_hierophantic.json` and say in
  `nearest_existing` whether it already covers this, flagging a possible drop
  for Roger).
- **Relationship structures** (monogamous, polyamorous, polygamous,
  polyandrous, polygynous): monogamous is the centre and the antonym check
  will choose its partner, so write it in its own terms, toward nobody; the
  four alternatives exactly as the notes define them (polyamorous: plural
  consensual loving relationships, not necessarily marriage; polygamous:
  plural marriage, the umbrella; polyandrous: one wife, several husbands;
  polygynous: one husband, several wives), each as the person living it
  would describe their household.  One grain; `set_review` on monogamous.
- **Orientation, sexuality and gender expression** (asexual, bisexual,
  pansexual, kinky, neuter, nonbinary, androgynous): plainly and stop.  The
  notes fix the senses: neuter is the absence of gender expression, nonbinary
  the identity outside the masculine / feminine pair, androgynous both
  expressions at once; bisexual and pansexual are near-duplicates by design,
  so write each in its own words and do not force a difference.  kinky is
  sexual practice, not orientation: adult and plain, nothing more explicit
  than the word itself means; the generator may refuse it, which is handled
  at generation.
- **Disabilities** (blind, deaf, mobility_impaired): categorical, inside
  voice: how the person moves through the day, the aids and adaptations as
  ordinary facts of life, not deficits; `set_review` on blind.
- **suburban**: the midpoint of the density axis (check whether rural and
  urban exist in the corpus and say so).

## Output

Write ONE JSON file named in your prompt (`drafts_5b_maps.json` or
`drafts_5b_sets.json`), in this directory: a list with one object per entry
in your entries file (same order), fields `stem`, `label`,
`description_draft`, `nearest_existing`, `notes`, optional `source_url`, and
on the FIRST member of each map or set a `set_review`.  Then reply with a
short summary: number of drafts, the grain you chose for each map or set, the
judgement calls, anything you want Roger to look at.

## Boundaries

You may read and write ONLY inside the repository checkout you are started in
(the project directory): nothing elsewhere on this machine, no home-directory
paths, no caches, no other projects, no listing of anything outside the
checkout.  Read files with the Read tool.  Do not run any generation script,
do not call any model API, and do not edit anything under `data/`; your only
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
