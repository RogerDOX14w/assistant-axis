# Seeding log, October 2026: chunk 4 (standards)

The record of chunk 4 of the seeding plan in
[TRAITS_TO_ADD.md](../data/traits/instructions/TRAITS_TO_ADD.md) § "Seeding
plan and chunk order": the traits drawn from named instruments and folk
systems (Big Five, HEXACO, MBTI, Inglehart-Welzel, Hall, Gelfand, Allport,
Tönnies, Kohlberg, attachment, and the part-4 sets and rings).  The queue
([seed_queue.json](../data/seed_queue.json)) is the record of state; this
file is the record of the reasoning, as
[seeding_log_2026-09.md](./seeding_log_2026-09.md) was for chunks 0 to 3.

## Method (Roger, 2026-10-06)

Standards-derived descriptions are written from the instrument's own text,
not drafted from notes as in chunks 1 to 3:

1. Locate an official description of the pole, of our length or longer, and
   record it: the passage verbatim, its URL and the date, in the queue entry
   (`source_text`, `source_url`, `source_retrieved`); the trait file's `source`
   field carries instrument and URL.
2. Summarise or edit it into the corpus form ("This means ...", 18 to 32
   words, inside voice, no hedges, the instrument unnamed in the description).
3. The two poles of a pair are summarised from their own sources, not forced
   into anti-parallel phrasing; a reviewer reads both originals and both
   drafts and flags accidental differences of scope or phrasing; Roger decides
   whether to re-edit.  Low poles without a source text are derived from the
   high pole's content and tagged `low_pole_derived`.
4. Standards pairs are paired by construction; the antonym check is run for
   information.  Arrangements (pairs, the HEXACO 6-orthoplex, the MBTI 4-cube,
   rings and sets) are written at seeding.  The generators' openings check
   (2026-10-06) applies.

Scope confirmed 2026-10-07: the 127 candidates; the 74 backlog entries (the
IPIP-NEO, HEXACO and BFAS facet level, the MBTI dichotomy pairs) are decided
after the factor-level pairs are seen.  Low-pole names as queued.  Budget
about $8 at Anthropic, real time.

## TODOs for this chunk

- **Rubric display of standard-suffixed labels (Roger, 2026-10-07).**  In
  the axis-judging rubric a pole labelled `careless (HEXACO)` should read
  "careless (from HEXACO)", and its partner "conscientious (from HEXACO)":
  default to inserting "from", and hard-code a list of the official sets
  where the definite article or some other form reads better ("from the Big
  Five", "from the Enneagram", ...).  The rendering site is the display
  helper the prompt builders call
  ([`display_form_name`](../assistant_axis/entity_id.py), which today only
  turns underscores into spaces; `corpus_display_name` is the human-facing
  one), and any change to what a judged prompt shows is a rubric change
  (bump `RUBRIC_VERSION`, per-entity drift check), so do it before the first
  judging run that includes these traits, not after.  The parenthesised
  label itself (`<pole> (<Standard>)`) stays as it is in the files.

## Sub-chunk A: Big Five and HEXACO factor pairs (started 2026-10-07)

Writer's packet:
[packet_bigfive_hexaco.md](../roger/chunk4_2026-10-07/packet_bigfive_hexaco.md)
(git-ignored work directory); entries
[entries_bigfive_hexaco.json](../roger/chunk4_2026-10-07/entries_bigfive_hexaco.json);
the writer's output
[drafts_bigfive_hexaco.json](../roger/chunk4_2026-10-07/drafts_bigfive_hexaco.json);
the reviewer's packet
[packet_review_bigfive_hexaco.md](../roger/chunk4_2026-10-07/packet_review_bigfive_hexaco.md)
and verdicts
[review_bigfive_hexaco.json](../roger/chunk4_2026-10-07/review_bigfive_hexaco.json).

**Sources.**  HEXACO: [hexaco.org/scaledescriptions](https://hexaco.org/scaledescriptions),
the high- and low-scorer sentence of each factor.  Big Five: John, Naumann &
Soto (2008), "Paradigm shift to the integrative Big Five trait taxonomy"
(authors' manuscript, [colby.edu](https://www.colby.edu/wp-content/uploads/2019/06/John_et_al_2008.pdf)):
the conceptual definitions (word for word John & Srivastava 1999, whose own
PDF is no longer online), the NEO PI-R facets, the Adjective Check List
markers of both poles, behavioural examples; plus Costa & McCrae's own
high/low wording from PAR's NEO-PI-3 sample feedback
([parinc.com](https://www.parinc.com/Portals/0/Webuploads/samplerpts/NEO%20PI-3%20Summary%20PiC.pdf)).
Every passage is in the queue entry verbatim (`source_text`, `source_url`,
`source_retrieved`); the file's `source` carries instrument and URL, and
"deliberate near-duplicate of the plain trait X" on the 13 files that twin a
plain corpus trait.

**Drafts.**  22, all 29 to 32 words (a factor's four or six facets have to be
recognisable); one low pole derived rather than sourced
([emotionally_stable_big_five](../data/traits/instructions/emotionally_stable_big_five.json)).
The reviewer passed 19, edited 2 for faithfulness
([antagonistic_big_five](../data/traits/instructions/antagonistic_big_five.json):
"boasting" had no low-side source, now "putting oneself first";
[tough_hexaco](../data/traits/instructions/tough_hexaco.json): "walking
toward physical danger without a second thought" made fear's low pole
reckless, now "pressing on where one could get hurt") and noted a record
gap on [closed_big_five](../data/traits/instructions/closed_big_five.json).
Eleven pair flags recorded (writer and reviewer agree on all), for Roger's
step-3 decisions: the Big Five open / closed pair is the most mirror-like
(the sources' facet order), conscientious / careless differ in facet count,
neurotic / emotionally-stable mix actions and states, honest-humble is four
restraints beside sly's four acts and carries the set's only contrast
clause, the HEXACO C pair shares a desk-and-calendar opening, agreeable /
quarrelsome sharpens anger on one side only.  Nothing re-edited for scope.

**Seeded and generated 2026-10-07**: `seed_entities.py write / generate /
check` by sub-chunk, pairs by construction (labels reciprocal, `arrangement`
pair), the orthoplexes added by
[add_orthoplex.py](../roger/chunk4_2026-10-07/add_orthoplex.py) (Big Five
5-orthoplex over 10, HEXACO 6-orthoplex over 12, the pairs as `axes`);
generation $1.05 (the openings check fired once, on emotional (HEXACO));
`check_arrangements` 0 problems over 685 files; lists synced.  The antonym
check, informational for standards: in plain words every Big Five pole named
its partner (agreeable -> antagonistic|disagreeable, closed -> open|open-minded|curious,
...), and so did eight HEXACO poles; the four that did not are the two
factors whose low-pole names are ours rather than the instrument's:
emotional -> stoic|fearless and tough -> vulnerable|sensitive, honest-humble
-> manipulative|greedy|self-serving and sly -> sincere|principled.  The
matcher's categories (`mismatch`, `nasty`) read the suffix-less twin as a
different word and are not failures here.  Queue status `paired`.

**Roger's step-3 decisions (2026-10-07).**  Low-pole names stand: where the
instrument gives none, the queued words are Ashton & Lee's own low-pole
adjectives (sly, tough, quarrelsome, conventional) or the ACL's first low
marker (careless, Big Five), and none of the check's alternatives
(stoic|fearless, manipulative|greedy, negligent) beat them on both meaning
and acceptability to the instrument's users.  Of the eleven scope flags,
five pairs were left as the instrument's own asymmetry (Big Five A, E;
HEXACO H, E, X).  Edits applied, each file regenerated
([apply_edits.py](../roger/chunk4_2026-10-07/apply_edits.py);
[edits_round1.json](../roger/chunk4_2026-10-07/edits_round1.json),
[edits_round2.json](../roger/chunk4_2026-10-07/edits_round2.json); the
previous text is in each queue entry's `edits`): [careless
(Big Five)](../data/traits/instructions/careless_big_five.json) trades
"forgetting promises" for "settling for whatever gets by" (its source's
achievement and competence facets); [emotionally-stable (Big
Five)](../data/traits/instructions/emotionally_stable_big_five.json), the
derived pole, gets a not-worrying-ahead clause and "at ease among strangers"
for the absence-shaped "unembarrassed"; [open
(HEXACO)](../data/traits/instructions/open_hexaco.json) /
[conventional](../data/traits/instructions/conventional_hexaco.json) put
inquisitiveness on the source's breadth ("curious about many fields of
knowledge" / "incurious about anything outside one's own patch"); [closed
(Big Five)](../data/traits/instructions/closed_big_five.json) widens
"ordering the usual" to "following the same routine".

**A rule change from this sub-chunk (Roger, 2026-10-07): mirror the
source's strength.**  For pre-balanced official pairs the corpus's vice and
hedge rules do not apply; the target is the instrument's own strength (if
not strongly out of line with the corpus's plain traits).  A check of the 22
against their passages found seven HEXACO poles sharpened by the writer
under the vice rule, all put back to source level and regenerated:
[quarrelsome](../data/traits/instructions/quarrelsome_hexaco.json)
("flaring up at the smallest slight" -> "quick to anger when wronged";
"picking at faults" -> "critical of shortcomings"),
[conventional](../data/traits/instructions/conventional_hexaco.json)
("off-putting" -> "little pull"), [sly](../data/traits/instructions/sly_hexaco.json)
("whenever it pays" -> "ready to ... when it pays"; "chasing money and
luxury", a word borrowed from the high pole's source, -> "out for whatever
one can gain"), [tough](../data/traits/instructions/tough_hexaco.json) (two
clauses and an absolute for one facet -> "seldom sharing one's troubles or
leaning on anyone"), [emotional](../data/traits/instructions/emotional_hexaco.json)
(the intensifiers "hard", "deep" dropped),
[honest-humble](../data/traits/instructions/honest_humble_hexaco.json)
("caring nothing" -> "caring little"),
[extraverted (HEXACO)](../data/traits/instructions/extraverted_hexaco.json)
("loving" -> "enjoying").  The Big Five low poles were left: their strength
rests on the ACL markers, which are strong in the original.  Also the HEXACO
C pair's office image ("desk, calendar and plans" / "the desk a mess and the
calendar blank") replaced by room and appointments on both sides.  Rule
recorded as description-writing rule 9 in AGENT_NOTES.  Sub-chunk A closed
2026-10-07: 22 files, 13 of them regenerated once more after an edit
($0.65), all under the V2 template, arrangements and lists clean.
