# Roget's own opposed heads, from the printed synopsis: readout (2026-10-09)

Workstream 2 of trait-gap generation, the Roget generator
([coding_plan_02_roget_wordnet.md](../../../reports/trait_gap_generation/coding_plan_02_roget_wordnet.md)).
Roger asked for a source better than the Gutenberg transcription before paying for a model pass over the
heads the rules could not pair ([QUESTIONS.md](../../../reports/trait_gap_generation/QUESTIONS.md) entry 38).
This is that source.

Terms.  A **head** is one numbered entry of Roget's Thesaurus (604 Resolution).  Roget's **Tabular Synopsis
of Categories** is the table at the front of the book that lists every head in two facing columns, the
opposites on one row (604 Resolution | 605 Irresolution).  An **opposed head** is a head's partner on such a
row.  A **triad** is a pair printed with one or two further heads that belong to it, either centred under
the pair (13 Identity | 14 Contrariety, with 15 Difference centred below) or braced (609 Choice set against
609a Absence of choice and 610 Rejection by a curly brace); the pair keeps its partners, and the further
heads are the triad's **third heads**, which have no partner.  A **singleton** is a head printed alone on
its row.  **OCR** is the text a scanner's character recognition read off the page images; the **djvu
XML** is the Internet Archive's OCR with each word's page and position on the page.  The **dispositional**
heads are Classes IV-VI (intellect, volition, the affections), numbered 450 and up.  The coverage map's
**gap classes** and the **head-scope check** are described in [roget_coverage.md](./roget_coverage.md) and
[head_scope_readout.md](./head_scope_readout.md); **M1** and **M3** are the platform's trait-hood filter and
novelty check.

## Summary

- Read from the scan, the synopsis prints **1,022 of the 1,044 heads** parsed from Gutenberg, each exactly
  once.  The 22 it does not print are lettered heads that the Gutenberg text has and the 1911 edition did
  not (59a Complexity, 374a Sexuality, 737b Politics, 847a Jewelry ...).
- It gives **388 pairs, 27 triads (29 third heads) and 217 singletons**.  Among the 576 dispositional heads:
  398 in pairs, 19 third heads, 147 singletons, 12 not printed.
- Checks: **41 of the 42 hand-listed known pairs** are printed as pairs; the 42nd (865 Desire / 866
  Indifference) is printed as a triad, 866 centred between 865 Desire and 867 Dislike.  Of the rules' 278
  pairs, 253 agree with the print, 4 fall in one printed triad, 16 disagree and 5 involve a head the
  synopsis does not print.  Of the 221 dispositional heads the rules left **unresolved**, the print pairs
  **98**, makes 4 the third head of a triad and prints 116 alone; 3 are not printed.
- In the generator the synopsis now decides every head it prints (`source: "synopsis"` in
  [head_pairs.json](./head_pairs.json)); the rules decide only the 24 others (the 22 not printed, and 388
  Fuel and 464 Comparison, which the synopsis prints alone and the rules pair with lettered heads added
  after 1911).  Unresolved heads: **403 → 4** (3 dispositional).
- Coverage: the states do not move (the pairing does not place traits).  The character heads' gap classes
  do: **pair_completion 24 → 27**, pair_empty 27 → 61, singleton_empty 96 → 59.  The full-size harvest
  selects the same 288 heads and gives the same 534 words; the same **25 partner hints**.
- No model call was needed: rules repaired every number the OCR garbled.  Spend **$0**.

## Source

The Internet Archive item `rogetsthesauruso00mawsrich`: *Roget's Thesaurus of English Words and Phrases*,
ed. C. O. Sylvester Mawson (New York: Thomas Y. Crowell, 1911), scanned at 400 dpi, marked `NOT_IN_COPYRIGHT`
in its metadata (<https://archive.org/metadata/rogetsthesauruso00mawsrich>).  The synopsis is printed pages
xxi-xxxi, leaves 27-37 of the scan (<https://archive.org/details/rogetsthesauruso00mawsrich>).

The code reads the item's positional OCR,
[rogetsthesauruso00mawsrich_djvu.xml](../../external/roget/rogetsthesauruso00mawsrich_djvu.xml) (34,831,231 bytes, SHA-256
`0a1776986818c7e67796773ac44bc500fe59e93f5e0739d6a0dca6a2f46f42ac`, SHA-1 as the item lists it), downloaded
2026-10-08 from <https://ia801602.us.archive.org/33/items/rogetsthesauruso00mawsrich/rogetsthesauruso00mawsrich_djvu.xml>
into [data/external/roget/](../../external/roget/README.md) (gitignored; recorded in its
[README.md](../../external/roget/README.md);
[roget_generate.py](../../../data_analysis/gap_generation/roget_generate.py) `synopsis --fetch` downloads it again).  The
plain OCR text already there, [mawson1911_archive_djvu.txt](../../external/roget/mawson1911_archive_djvu.txt),
loses the rows (it gives a section's left column, then its right one) and is not read.  The djvu XML was
chosen over the hOCR (74 MB) because it is half the size and each word carries its box directly.  I viewed
the eleven page images on archive.org to write the layout rules and to check the result; they are not
stored.

## Method

Code: [synopsis.py](../../../assistant_axis/gapgen/generators/roget/synopsis.py); command
`roget_generate.py synopsis` ([roget_generate.py](../../../data_analysis/gap_generation/roget_generate.py));
output [synopsis_pairs.json](./synopsis_pairs.json) (provenance envelope; per head: `kind`, `partner` or the
triad's `members`, `page`, `row`, `column`, the OCR'd number and title, and any repair; plus the repairs,
the heads not printed, the unused number tokens and the checks below).  Tests:
[test_gapgen_roget_synopsis.py](../../../assistant_axis/tests/test_gapgen_roget_synopsis.py), on a hand-made
positional fixture ([roget_synopsis_sample.xml](../../../assistant_axis/tests/fixtures/roget_synopsis_sample.xml))
and on the real scan.

1. **Pages.**  The pages whose top line is the running head "TABULAR SYNOPSIS OF CATEGORIES" in capitals
   (the contents page names it in mixed case and is left out), each with its printed page number.
2. **Columns.**  Right of the category outline each page has three columns of heads: left, middle (centred
   heads such as 15 Difference) and right, told apart by the x position of the head number.  A head number
   is a word that reads as digits, perhaps with a or b, after stray marks next to it are stripped (`r27.`,
   `[105.`, `987_`).
3. **Order.**  Within each column the numbers rise down the page and from page to page.  The longest rising
   run, weighted by how well the printed title matches the Gutenberg title, is kept; what falls out is
   listed as an unused token (the centred subheadings "1. Actual Subservience", "2. Degree of Subservience",
   "3. Contingent Subservience", and two stray digits).
4. **Repairs.**  Each head still missing is looked for in the slot its neighbours in number leave: first a
   garbled number that reads as it when letters the OCR confuses with digits are read as those digits (S
   for 8, g for 9 or 8, q for 9 or 0, y for 9, A for 4, l for 1, and so on), then its title alone.  Every
   repair is listed below.
5. **Heights.**  An entry's height on the page is the top of its number (the digits are as tall as the
   title's capitals), or of its title where a merged glyph distorts the number's box.  A braced title over
   two or three lines (202 {Breadth, Thickness}) has its number centred on its lines, and the facing entry
   may sit on any of them (344 Plain is printed beside the "Lake" of 343 {Gulf, Lake}), so an entry also
   carries the heights of its title lines.  The line pitch (the distance between lines) is 44 px on every
   page.
6. **Blocks**, page by page:
   - a left and a right entry whose numbers are within 0.16 of a line of each other (every printed row is
     within 6 px) are a **pair**;
   - an entry centred between two consecutive entries of the other column (they at most 1.35 lines apart,
     it within 0.32 of a line of their midpoint) is **braced** against both.  Its partner is the one that
     is unlettered and nearest in number, ties going to the upper one, because Roget numbered correlatives
     consecutively and the lettered heads are later insertions; the other is the third head;
   - two entries that align on a line of a braced title (within 0.3 of a line) are a **pair**;
   - a middle entry joins the block with a pair just above or below it, with no entry between.  It prefers
     a block in its own subsection, then one next to it in number, then a row printed with its numbers
     inverted (641 Redundance left of 640 Insufficiency, laid out around 639 Sufficiency), then the one
     above.  A second centred entry under the first joins the same block (27 Equality | 28 Inequality with
     29 Mean and 30 Compensation);
   - anything else is a **singleton**;
   - one **override**, checked against the page image: on page xxvii a brace sets 615a Absence of Motive and
     616 Dissuasion against 615 Motive and 617 Plea in two aligned rows, which the geometry alone would read
     as two pairs (617 Plea with 616 Dissuasion).  It is recorded as one block: 615 Motive with 616
     Dissuasion, and 615a and 617 as third heads.

The order within step 6 (tight rows before braces) is what catches 926 Duty, which the typesetter set 9 px
from 927a Exemption and 35 px from 927 Dereliction although the brace sets it against both.

## Repairs

Nine heads were repaired, all by rule; no model call was needed.  The coordinator allowed a Sonnet fallback
for anything the rules could not repair (cap $2); it was not used.

| head | page, column | how | OCR token | title as read |
|---|---|---|---|---|
| 154 Effect | xxii, R | title | `1` | Effect |
| 203 Narrowness. Thinness | xxiii, R | title | `2qo` | Narrowness Thinness |
| 477 Intuition & Sophistry | xxvi, R | OCR confusion + title | `A77` | Intuition Sophistry |
| 485 Unbelief. Doubt | xxvi, R | title | `4S°-` | Unbelief Doubt |
| 498 Intelligence, Wisdom | xxvi, L | OCR confusion + title | `4ys'` | Intelligence aqc Wisdom |
| 499 Imbecility. Folly | xxvi, R | OCR confusion + title | `4qq` and `4yy-` | Imbecility Folly |
| 759 Deputy | xxviii, L | title | (none) | Deputy |
| 809 Expenditure | xxix, L | OCR confusion + title | `S09.` | Expenditure |
| 983a Orthodoxy | xxxi, L | OCR confusion + title | `9g3a.` | Orthodoxy |

Each repair was checked against the page image.  In 53 more numbers stray marks were stripped:
`r27.` `,48.` `'100.` `[105.` `(175.` `182,` `.190.` `r192.` `,198.` `'234.` `,238.` `'244.` `,262.` `f316.` `[319.` `f337.` `'347.` `s350.` `[352.` `[382.` `(450.` `487-` `514-` `'600.` `L613.` `k656.` `r658.` `'673.` `(678.` `'692.` `,702.` `'706.` `>729.` `r737.` `'760.` `'768.` `f775.` `;783.` `'794.` `'800.` `,818.` `'820.` `,825.` `"827.` `,852.` `{859.` `'888.` `'922.` `'963.` `[976.` `[983.` `987_` `,1000.`.

Unused number tokens (5): the three centred subheadings on pages xxvii and xxviii, and stray digits on pages
xxii and xxvi.  Printed titles that differ from the Gutenberg titles (title match under 0.5; the numbers are
fixed by their order and agree with the print): Mawson's synopsis names some heads differently (45 Vinculum
for Connection, 80 Rule for Normality, 95 Quaternity for Four, 122 Preterition, read "Pretention", for The
Past, 135 Intempestivity for Untimeliness, 225 Investment for Clothing, 228 Interjacence for Interposition,
370 Cicuration for Husbandry, 563 Neology for Neologism, 588 Interlocution for Conversation, 617 Plea for
Pretext, 965 Jurisprudence for Jurisdiction), shortens others (450a, 768a, 985, 351 "Air pipe"), and for
braced titles the reader does not collect the title words (38, 155, 156, 180, 181, 182, 202, 413).

## Checks

**Every head once.**  1,022 heads printed, none twice; the 22 not printed: 59a Complexity, 132a Punctuality,
216a Perpendicularity, 252a Sponge, 374a Sexuality, 388a Insulation, 392a Saltiness, 392b Bitterness, 401a
Acridity, 426a Turbidity, 464a Incomparability, 465b Identification, 514a Analogy, 527a Correction, 737a
Government, 737b Politics, 799a Stock Market, 799b Securities, 812a Value, 812b Worthlessness, 817a Greed,
847a Jewelry.  All are lettered heads that the Gutenberg text has and the printed 1911 synopsis does not.

**The 42 known pairs** ([known_pairs.json](./known_pairs.json), listed from memory of the synopsis): 41
printed as listed, including 606 Obstinacy / 607 Tergiversation, the one the rules got wrong (they paired
607 with 608 Caprice; the print braces 607 against 604a Perseverance and 606 Obstinacy, and prints 608
Caprice alone).  The 42nd, 865 Desire / 866 Indifference, is printed as 865 Desire | 867 Dislike with 866
Indifference centred between them.  The list is left as it is.

**The rules' pairs.**  Of the 278 pairs in the rule pairing (all heads; among the dispositional heads the
rules had 298 heads in pairs and 26 third heads, the "324" of the brief): 253 are printed as pairs (223 of
the strict rule, 30 of the weak pass); 4 are two heads of one printed triad (609 / 609a, 639 / 640, 865 /
866, 973 / 974); 5 involve a head the synopsis does not print (216 / 216a, 388 / 388a, 464 / 464a, 737a /
738, 812a / 812b); and 16 disagree with the print (8 strict, 8 weak):

| rule pair | rule evidence | as printed |
|---|---|---|
| 84 Number / 85 Numeration | rule | 84 Number alone; 85 Numeration alone |
| 87 Unity / 100 Plurality | rule | 87 Unity with 88 Accompaniment; 100 Plurality with 100a Fraction |
| 143 Continuance in action / 144 Conversion | rule_weak | 143 Continuance in action with 142 Cessation; 144 Conversion alone |
| 180 Space / 180a Inextension | rule_weak | 180 Space with 181 Region; 180a Inextension alone |
| 329 Texture / 330 Pulverulence | rule | 329 Texture alone; 330 Pulverulence alone |
| 371 Agriculture / 372 Mankind | rule_weak | 371 Agriculture with 370 Husbandry; 372 Mankind alone |
| 391 Insipidity / 392 Pungency | rule | 391 Insipidity with 390 Taste; 392 Pungency alone |
| 422 Dimness / 423 Luminary | rule_weak | 422 Dimness third head of 420 / 421; 423 Luminary with 424 Shade |
| 435 Greenness / 436 Yellowness | rule_weak | 435 Greenness with 434 Redness; 436 Yellowness with 437 Purple |
| 528 Concealment / 529 Disclosure | rule_weak | 528 Concealment with 527 Information; 529 Disclosure with 530 Ambush |
| 607 Tergiversation / 608 Caprice | rule_weak | 607 Tergiversation with 606 Obstinacy; 608 Caprice alone |
| 707 Aid / 708 Opposition | rule | 707 Aid with 706 Hindrance; 708 Opposition with 709 Cooperation |
| 721 Peace / 722 Warfare | rule | 721 Peace with 720 Contention; 722 Warfare with 723 Pacification |
| 817 Economy / 818 Prodigality | rule | 817 Economy with 816 Liberality; 818 Prodigality with 819 Parsimony |
| 848 Blemish / 849 Simplicity | rule_weak | 848 Blemish with 847 Ornament; 849 Simplicity alone |
| 851 Vulgarity / 852 Fashion | rule | 851 Vulgarity with 850 Taste; 852 Fashion alone |

**The rules' 221 unresolved dispositional heads.**  The print pairs 98 of them, makes 4 third heads (469
Qualification, 520 Equivocalness, 539 Learning, 542 School) and prints 116 alone; 3 are not printed (514a
Analogy, 799a Stock Market, 799b Securities).  The examples in QUESTIONS 38 and the brief: 838 Rejoicing |
839 Lamentation, 933 Flattery | 934 Detraction, 492 Scholar | 493 Ignoramus and 948 Good Man | 949 Bad Man
are printed as pairs.  Consent / Refusal is not: the print pairs 763 Offer | 764 Refusal and prints 762
Consent alone.  The sequences are printed alone too (625 Business, 626 Plan, 627 Method, 631-636
Instrumentality to Store).

## The triads

| page | how printed | pair | third head(s) |
|---|---|---|---|
| xxi | centred below the pair | 13 Identity / 14 Contrariety | 15 Difference |
| xxi | centred below the pair | 19 Imitation / 20 Nonimitation | 20a Variation |
| xxi | centred below the pair | 27 Equality / 28 Inequality | 29 Mean, 30 Compensation |
| xxi | centred below the pair | 66 Beginning / 67 End | 68 Middle |
| xxii | centred below the pair | 129 Infant / 130 Veteran | 131 Adolescence |
| xxiii | centred below the pair | 250 Convexity / 252 Concavity | 251 Flatness |
| xxv | centred below the pair | 420 Light / 421 Darkness | 422 Dimness |
| xxv | centred below the pair | 425 Transparency / 426 Opacity | 427 Semitransparency |
| xxv | centred below the pair | 441 Vision / 442 Blindness | 443 Dimsightedness |
| xxvi | centred below the pair | 467 Evidence / 468 Counter Evidence | 469 Qualification |
| xxvi | centred below the pair | 518 Intelligibility / 519 Unintelligibility | 520 Equivocalness |
| xxvi | braced | 537 Teaching / 538 Misteaching | 539 Learning |
| xxvi | centred below the pair | 540 Teacher / 541 Learner | 542 School |
| xxvii | braced | 606 Obstinacy / 607 Tergiversation | 604a Perseverance |
| xxvii | braced | 609 Choice / 610 Rejection | 609a Absence of Choice |
| xxvii | braced, two against two (override) | 615 Motive / 616 Dissuasion | 615a Absence of Motive, 617 Pretext |
| xxvii | centred below the pair | 640 Insufficiency / 641 Redundancy | 639 Sufficiency |
| xxviii | braced | 677 Use / 678 Disuse | 679 Misuse |
| xxviii | centred below the pair | 734 Prosperity / 735 Adversity | 736 Mediocrity |
| xxix | centred below the pair | 772 Observance / 773 Nonobservance | 774 Compromise |
| xxix | braced | 831 Content / 832 Discontent | 833 Regret |
| xxx | braced | 858 Hope / 859 Hopelessness | 860 Fear |
| xxx | centred below the pair | 865 Desire / 867 Dislike | 866 Indifference |
| xxx | braced | 903 Marriage / 904 Celibacy | 905 Divorce |
| xxx | braced | 926 Duty / 927 Dereliction of Duty | 927a Exemption |
| xxxi | braced | 972 Punishment / 973 Reward | 974 Penalty |
| xxxi | braced | 987 Piety / 988 Impiety | 989 Irreligion |

## In the generator

[pairs.py](../../../assistant_axis/gapgen/generators/roget/pairs.py) `merge_synopsis`, run by
[roget_generate.py](../../../data_analysis/gap_generation/roget_generate.py) `pair` whenever [synopsis_pairs.json](./synopsis_pairs.json) is present (`--no-synopsis`
gives the rules alone):

- a head printed in a pair or a triad takes that pairing (`source: "synopsis"`); a pair also keeps the
  rules' word-level evidence for it (negations, WordNet antonyms), as a rule pair does;
- a head printed alone is a singleton, unless the rules paired it with a head the 1911 synopsis does not
  print: 388 Fuel with 388a Insulation and 464 Comparison with 464a Incomparability keep their rule pairs;
- a head not printed keeps its rule result, unless its rule partner is now paired elsewhere (216a
  Perpendicularity, 737a Government: singletons) or the pair of a rule triad was broken (392a, 527a, 737b,
  817a, 847a: singletons).  Still unresolved: 392b Bitterness, 514a Analogy, 799a Stock Market, 799b
  Securities;
- every record keeps the rule result under `evidence.rule` (and the synopsis record under
  `evidence.synopsis`) for comparison.

The harvest's partner hints now come from synopsis pairs as well as rule pairs
([harvest.py](../../../assistant_axis/gapgen/generators/roget/harvest.py) `HINT_SOURCES`), and the coverage map
names the source ([roget_coverage.md](./roget_coverage.md)).

## Before and after

"Before" is the pairing by rule as committed ([head_pairs.json](./head_pairs.json) at fc666f3), "after" the
merge.  Both with the label placements and head-scope ratings now in
[label_heads.json](./label_heads.json) and [head_scope.json](./head_scope.json); the coverage rows are those
of [roget_coverage.json](./roget_coverage.json).  The harvest is the full-size dry run
(`roget_generate.py --dry-run harvest --run-id 2026-10-09-synopsis-dryrun`, no `--every-nth`, nothing
written).

| | before (rules) | after (synopsis, then rules) |
|---|---|---|
| all 1,044 heads: in a pair / third head / singleton / unresolved | 556 / 42 / 43 / 403 | 782 / 36 / 222 / 4 |
| 576 dispositional heads: in a pair / third head / singleton / unresolved | 298 / 26 / 31 / 221 | 402 / 20 / 151 / 3 |
| known pairs printed as listed | 41 of 42 | 41 of 42 |
| coverage (487 character heads in scope): covered / partly / uncovered (queued only) | 272 / 52 / 163 (16) | 272 / 52 / 163 (16) |
| gap classes: pair_completion / pair_empty / singleton_empty / queued_only | 24 / 27 / 96 / 16 | **27 / 61 / 59** / 16 |
| opposed pairs in scope: both poles / one pole / neither covered | 70 / 51 / 30 | 75 / 57 / 41 |
| harvest: gap heads selected / skipped as not character / giving words | 288 / 125 / 94 | 288 / 125 / 94 |
| harvest: words (distinct) | 534 (498) | 534 (498) |
| harvest: selected heads by class, pair_completion / pair_empty / singleton_empty / queued_only | 36 / 56 / 171 / 25 | 45 / 123 / 95 / 25 |
| harvest: words by class, same order | 154 / 158 / 160 / 62 | 153 / 232 / 87 / 62 |
| harvest: pair candidates (WordNet-confirmed, negation forms) | 97 (11, 7) | 101 (11, 7) |
| harvest: candidates with a partner hint | 25 | 25 (the same 25) |
| downstream estimate: M1 / M3 if half pass | $2.14 / $4.81 | $2.14 / $4.81 |

The harvest selects the same heads and words because it takes every gap head of the four classes whatever
its pairing; the pairing changes which class a head is in, and which heads face each other in the pair
candidates and hints.  The hints do not change because a hint needs a WordNet antonym or a negation form
between the harvested words of the two heads (or the trait covering one of them), and the new pairs bring
none.

Pair completions (an empty character head whose printed partner is covered):

- gained 5: 493 Ignoramus (partner 492 Scholar: [educated](../../traits/instructions/educated.json)), 501 Fool
  (500 Sage: [thinker (VALS)](../../traits/instructions/thinker_vals.json)), 701 Bungler (700 Proficient:
  [specialist](../../traits/instructions/specialist.json)), 706 Hindrance (707 Aid:
  [helpful](../../traits/instructions/helpful.json), [supportive](../../traits/instructions/supportive.json)),
  912 Benefactor (913 Evil doer: [killer (Bartle)](../../traits/instructions/killer_bartle.json)).  501, 701 and
  912 have no adjectives, so they give the harvest no words;
- lost 2: 529 Disclosure (the rules paired it with 528 Concealment; the print pairs it with 530 Ambush) and
  640 Insufficiency (the rules: 639 Sufficiency; the print: 641 Redundance, with 639 centred).

## Newly paired dispositional heads rated as character

128 dispositional heads have a partner from the synopsis that they did not have under the rules (112 had
none, 16 had another).  50 of them are rated 1 or 2 by the head-scope check; they are in the 34 printed pairs
below.  Rating: 2, most of the head's adjectives describe a person; 1, some do; 0, few or none; "-",
unrated (no adjectives).  State: covered (an existing trait has the head as its primary head), partly (only
as a secondary head), queued (only a seed-queue label), empty.  Of the 50 heads, 25 are covered, 3 crowded
(three or more traits), 4 partly covered, 3 pair completions and 15 pair_empty.

| pair as printed (page) | rating | first head: state and traits | second head: state and traits | the rules had |
|---|---|---|---|---|
| 492 Scholar / 493 Ignoramus (xxvi) | - / 2 | covered: [educated](../../traits/instructions/educated.json) | empty | unresolved; unresolved |
| 496 Maxim / 497 Absurdity (xxvi) | 0 / 1 | empty | empty | unresolved; triad |
| 500 Sage / 501 Fool (xxvi) | 1 / - | covered: [thinker (VALS)](../../traits/instructions/thinker_vals.json); secondary of [wise](../../traits/instructions/wise.json) | empty | unresolved; unresolved |
| 527 Information / 528 Concealment (xxvi) | 1 / 1 | covered: [informational](../../traits/instructions/informational.json); secondary of [expository](../../traits/instructions/expository.json) | covered: [cryptic](../../traits/instructions/cryptic.json), [esoteric](../../traits/instructions/esoteric.json); queued [literal-explicitness / withholding-evasion (tentative, PC14)](../../seed_queue.json) (queued) | unresolved; pair with 529 |
| 529 Disclosure / 530 Ambush (xxvi) | 1 / 0 | empty | empty | pair with 528; unresolved |
| 540 Teacher / 541 Learner (xxvi) | 1 / 0 | empty | empty | unresolved; unresolved |
| 606 Obstinacy / 607 Tergiversation (xxvii) | 2 / 2 | covered: [obsessive](../../traits/instructions/obsessive.json), [unyielding](../../traits/instructions/unyielding.json) | empty | triad; pair with 608 |
| 609 Choice / 610 Rejection (xxvii) | 1 / 0 | covered: [eclectic](../../traits/instructions/eclectic.json) | empty | pair with 609a; singleton |
| 622 Pursuit / 623 Avoidance (xxvii) | 0 / 2 | empty | covered: [avoidant](../../traits/instructions/avoidant.json), [news-avoidant](../../traits/instructions/news_avoidant.json), [noncommittal](../../traits/instructions/noncommittal.json); queued [Greed Avoidance (HEXACO)](../../seed_queue.json) (queued), [literal-explicitness / withholding-evasion (tentative, PC14)](../../seed_queue.json) (queued) | unresolved; unresolved |
| 640 Insufficiency / 641 Redundancy (xxvii) | 1 / 1 | empty | partly: secondary of [extravagant](../../traits/instructions/extravagant.json) | pair with 639; triad |
| 706 Hindrance / 707 Aid (xxviii) | 1 / 1 | empty | covered: [helpful](../../traits/instructions/helpful.json), [supportive](../../traits/instructions/supportive.json) | singleton; pair with 708 |
| 708 Opposition / 709 Cooperation (xxviii) | 2 / 1 | covered: [antagonistic (Big Five)](../../traits/instructions/antagonistic_big_five.json), [hostile](../../traits/instructions/hostile.json) | covered: [collaborative](../../traits/instructions/collaborative.json), [cooperative](../../traits/instructions/cooperative.json); queued [Cooperation (IPIP-NEO)](../../seed_queue.json) (queued) | pair with 707; triad |
| 718 Retaliation / 719 Resistance (xxviii) | 1 / 1 | empty | empty | unresolved; unresolved |
| 720 Contention / 721 Peace (xxviii) | 2 / 2 | covered: [competitive](../../traits/instructions/competitive.json), [confrontational](../../traits/instructions/confrontational.json); secondary of [hostile](../../traits/instructions/hostile.json) | covered: [calm](../../traits/instructions/calm.json), [pacifist](../../traits/instructions/pacifist.json), [peaceful](../../traits/instructions/peaceful.json); queued [calm (IPIP-NEO)](../../seed_queue.json) (queued) | unresolved; pair with 722 |
| 722 Warfare / 723 Pacification (xxviii) | 1 / 1 | covered: [hawkish](../../traits/instructions/hawkish.json), [tactical](../../traits/instructions/tactical.json); secondary of [hostile](../../traits/instructions/hostile.json) | covered: [conciliatory](../../traits/instructions/conciliatory.json) | pair with 721; unresolved |
| 737 Authority / 738 Laxity (xxviii) | 1 / 2 | covered: [authoritarian](../../traits/instructions/authoritarian.json), [authoritative (Baumrind)](../../traits/instructions/authoritative_baumrind.json), [controlling](../../traits/instructions/controlling.json), [dominance (DISC)](../../traits/instructions/dominance_disc.json), [dominant](../../traits/instructions/dominant.json); secondary of [influence (DISC)](../../traits/instructions/influence_disc.json); queued [internal locus of control](../../seed_queue.json) (queued), [mastery](../../seed_queue.json) (queued) | covered: [loose (Gelfand)](../../traits/instructions/loose_gelfand.json) | singleton; pair with 737a |
| 763 Offer / 764 Refusal (xxix) | 0 / 1 | empty | empty | unresolved; unresolved |
| 765 Request / 766 Deprecation (xxix) | 1 / 0 | empty | empty | unresolved; unresolved |
| 768 Promise / 768a Release from engagement (xxix) | 1 / 0 | empty | empty | unresolved; unresolved |
| 777 Possession / 777a Exemption (xxix) | 1 / 0 | empty | empty | unresolved; unresolved |
| 781 Retention / 782 Relinquishment (xxix) | 1 / 0 | covered: [retentive](../../traits/instructions/retentive.json) | empty | unresolved; unresolved |
| 784 Giving / 785 Receiving (xxix) | 1 / 0 | partly: secondary of [generous](../../traits/instructions/generous.json) | covered: [receiving gifts](../../traits/instructions/receiving_gifts.json) | unresolved; unresolved |
| 789 Taking / 790 Restitution (xxix) | 1 / 0 | empty | empty | unresolved; unresolved |
| 812 Price / 813 Discount (xxix) | 1 / 0 | partly: secondary of [mercenary](../../traits/instructions/mercenary.json) | empty | unresolved; singleton |
| 816 Liberality / 817 Economy (xxix) | 2 / 2 | covered: [generous](../../traits/instructions/generous.json); secondary of [open (Big Five)](../../traits/instructions/open_big_five.json) | covered: [bargain-hunter](../../traits/instructions/bargain_hunter.json), [frugal](../../traits/instructions/frugal.json) | singleton; pair with 818 |
| 818 Prodigality / 819 Parsimony (xxix) | 2 / 2 | covered: [extravagant](../../traits/instructions/extravagant.json); queued [wasteful](../../seed_queue.json) (queued) | covered: [stingy](../../traits/instructions/stingy.json); secondary of [greedy](../../traits/instructions/greedy.json) | pair with 817; triad |
| 838 Rejoicing / 839 Lamentation (xxix) | 1 / 1 | empty | empty | triad; unresolved |
| 850 Taste / 851 Vulgarity (xxix) | 1 / 2 | covered: [aesthete](../../traits/instructions/aesthete.json), [highbrow](../../traits/instructions/highbrow.json); queued [Aesthetic Appreciation (HEXACO)](../../seed_queue.json) (queued), [cultured/uncultured (tentative, PC13)](../../seed_queue.json) (queued) | covered: [lowbrow](../../traits/instructions/lowbrow.json); secondary of [rude](../../traits/instructions/rude.json) | triad; pair with 852 |
| 865 Desire / 867 Dislike (xxx) | 2 / 1 | covered: [ambitious](../../traits/instructions/ambitious.json) | covered: [unpopular](../../traits/instructions/unpopular.json) | pair with 866; unresolved |
| 933 Flattery / 934 Detraction (xxx) | 2 / 2 | partly: secondary of [sycophantic](../../traits/instructions/sycophantic.json) | empty | unresolved; unresolved |
| 935 Flatterer / 936 Detractor (xxx) | - / 2 | partly: secondary of [sycophantic](../../traits/instructions/sycophantic.json) | covered: [detractor](../../traits/instructions/detractor.json) | unresolved; unresolved |
| 956 Fasting / 957 Gluttony (xxxi) | 0 / 2 | empty | covered: [gluttonous](../../traits/instructions/gluttonous.json); secondary of [greedy](../../traits/instructions/greedy.json) | unresolved; unresolved |
| 985 Judeo-Christian Revelation / 986 Pseudo-Revelation (xxxi) | 1 / - | empty | empty | unresolved; unresolved |
| 990 Worship / 991 Idolatry (xxxi) | 1 / 1 | covered: [acts of service](../../traits/instructions/acts_of_service.json), [reverent](../../traits/instructions/reverent.json) | covered: [Neopagan](../../traits/instructions/neopagan.json) | unresolved; unresolved |

## Open points for Roger

1. **QUESTIONS 38 can close**: the print leaves 3 dispositional heads unresolved (514a Analogy, 799a Stock
   Market, 799b Securities, none printed in 1911), so the residue pass is not needed.
2. **Third heads have no opposed head**, as with the rules' triads.  A braced third head faces the single
   head across the brace (860 Fear against 858 Hope, 833 Regret against 831 Content, 989 Irreligion against
   987 Piety); giving it that head as a second opposed head would make more pair completions.  Not built.
3. **The pair inside a braced triad** is chosen by number (unlettered, nearest, ties to the upper): 973
   Reward pairs with 972 Punishment, not 974 Penalty; 537 Teaching with 538 Misteaching, not 539 Learning.
4. **The one override** (615 / 615a / 616 / 617, pair 615 Motive / 616 Dissuasion) is a reading of the brace;
   the alternative is two pairs as the rows align (615 / 615a, 617 / 616).
5. **[known_pairs.json](./known_pairs.json)** lists 865 / 866, which the print does not support; left unchanged.
