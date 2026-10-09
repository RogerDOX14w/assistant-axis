# Overnight readout, 2026-10-09: the queue fix and the first runs through the Batches API

Written for Roger by the coordinator.  Terms: the [glossary](./glossary.md).  The Batches API (Anthropic's
Message Batches) takes a set of requests at half price and answers them within 24 hours, in practice minutes.
M1 is the trait-hood filter, M3 the novelty scorer, R1 the review graph.

## In short

Everything ran through the Batches API and worked: the filter, M3, the physical pass and the review graph, on
the two 10% Allport pilots, for $1.73 in all.  Two small faults in the physical pass were found and fixed.  The
queue fix (later waves see what earlier waves promoted) is built and merged.  Nothing is waiting on code; the
next step is your five-minute smoke test of the review app.

## 1. The queue fix

M3's similarity search now includes live seed-queue trait entries that carry a description or draft (statuses
`candidate`, `ready`, `tbd`, `backlog`; turned-down entries stay exact-label only), projected into the comparison
space fitted on the corpus alone, so no earlier decision moves.  A word promoted in one wave therefore covers its
synonyms in the next; a test shows it (`test_a_word_promoted_in_wave_1_covers_its_synonym_in_wave_2`).  Rescoring
the three October 8 pilots against the queue flipped none of their 333 new words: the live queue holds a single
eligible entry today.  Off switch for reproducing older runs: `--no-queue-search`.  Details in
[coding_plan_platform.md](./coding_plan_platform.md), "The seed queue in M3's search"; merged at 189bf0b.

## 2. The two pilots

Every tenth word of each new census stage
([submit.py](../../assistant_axis/gapgen/generators/censuses/submit.py)): `allport_iv`, the words Allport and
Odbert listed only in column IV ("metaphorical and doubtful"), and `allport_rare`, the known words below the
frequency floor.  Readouts per run: [column IV](../../data/candidates/runs/censuses/2026-10-09-iv-pilot/readout.md),
[rare](../../data/candidates/runs/censuses/2026-10-09-rare-pilot/readout.md).

| | Column IV | Rare |
|---|---|---|
| Words submitted | 202 | 104 |
| M1: trait / tagged / turned away | 86 / 66 / 50 | 62 / 15 / 27 |
| of the tagged: states / physical / roles | 34 / 23 / 9 | 12 / 2 / 1 |
| Disagreement tripwire (Sonnet second opinion against Haiku) | tripped, 4 of 22 (18%); accepted | 3 of 11, under the 20-word minimum |
| M3: new / covered | 61 / 17 | 46 / 16 |
| Cost: M1 + M3 | $0.54 + $0.40 | $0.28 + $0.39 |

**My reading of the new words (yours decides):**

- **Rare words: good value.**  Most read as genuine, if old-fashioned, character words: alacritous,
  appropriative, calumniatory, caviler, crackbrained, forehanded, inerrable, lummox, mollycoddling, naysaying,
  overcorrect, paltering, pettish, reproving, scalawag, scientistic, uxorious, vixenish, wordmonger.  A few are odd
  (mixable, tamable, satisfiable, ossifying).
- **Column IV: weak.**  Perhaps a third are character words (draconian, evil-eyed, flinty, henpecked, legalist,
  unbeguiled, unjaundiced, unmilitary, unpriestly, unreformed, weasel).  Many are object words the filter passed
  on a stretched person reading (misty, murky, musty, silky, demagnetized, self-luminous, unweathered, veneered,
  unpedigreed, uninsurable).  The tripwire trip points the same way: this is where Haiku 5.5 over-accepts, and it
  is data for decision 16 (re-examining the filter's model on real generator output).

So: on these pilots, the full rare stage (1,031 words, about $9 through Batches) looks worth running; the full
column IV stage (2,013 words, about $17) looks like it would mostly add review work, unless the filter is
tightened against stretched readings first.  Your call once you have seen the words in the app.

**Physical pass** (the 25 physical words of both pilots, batch `physical_allport_pilots_1`): 16 new (aquiline,
bandy-legged, beetle-browed, buxom, flabby, horny-handed, ill-favored, lissom, nasal, short-armed, ...), 9 covered
by physical-track traits (hoar and hoary under [gray-haired](../../data/traits/instructions/gray_haired.json),
porky under [fat](../../data/traits/instructions/fat.json), sand-blind under
[blind](../../data/traits/instructions/blind.json), skeleton and slimmer under
[thin](../../data/traits/instructions/thin.json)).  $0.06.

**Review graph** for both pilots' new words (batch `review_allport_pilots_1`): 107 words, 2 proposed groups of
two, 103 single words; $0.06.  Open it with
`uv run python data_analysis/gap_generation/review_app.py serve --batch-id review_allport_pilots_1`.

## 3. How the Batches API behaved

- **Every stage worked**, with no expired or failed requests; one batch of three retries for M1's checks.
- **Timing.**  A batch came back in 2 to 8 minutes.  M1 took about 40 minutes (six waves).  M3 took 1.5 to 1.8
  hours, because it walks one candidate-trait pair at a time per position, Sonnet then Opus, about 22 batches in a
  row; that count depends on the depth of the walk, not on the number of words, so a full wave's M3 should also
  take about two hours.  The review graph took 40 minutes.  **A full wave end to end: about 3.5 to 4 hours**,
  most of it waiting, so waves suit overnight runs.
- **Cost against the estimates.**  M3 again ran over its own estimate (40% and 17%), as it did live; the census
  submit gate now uses measured rates, but M3's internal estimator still undercounts the pairs walked.  The caps
  (1.5 times the estimate plus $2) absorbed it.  Worth recalibrating before the big Allport waves; not urgent.

**Faults found and fixed** (1e194bc): the physical pass's gloss stage ignored `--transport batches` and ran live
(two small Haiku calls a word, half a cent here; now recorded as live by design rather than fixed, since batching
it would save cents), and its HTTP client was closed after the event loop ended, printing an "Event loop is
closed" error at the end of an otherwise complete run (now closed inside the loop; test added).

## 4. Spend tonight

| Job | Cost |
|---|---|
| Corpus regions from descriptions (909 + 7 traits) | $0.26 |
| Queue check on the October 8 pilots | $0.004 |
| Column IV pilot: M1 + M3 | $0.94 |
| Rare pilot: M1 + M3 | $0.67 |
| Physical pass + review graph on both pilots | $0.12 |
| **Total** | **$1.99** |

## 5. What is next

1. **Your smoke test of the review app**: open `review_pilots_1` (the October 8 pilots, 330 words) or
   `review_allport_pilots_1` (107 words), resolve three or four groups, then
   `uv run python data_analysis/gap_generation/review_app.py apply --batch-id <batch> --dry-run`.  The corpus-seeding
   session has no uncommitted queue edits, so a real `apply` would also be safe.
2. **Your go on the first full wave**, the TDA: 2,254 words left after the pilot, about $19 through Batches plus
   about $6 for its review graph, about four hours unattended.  Then Roget with the WordNet stream (about $4),
   then the common Allport words (about $31) and the less common (about $21); the rare and column IV stages on
   your reading of the pilots above.
3. **The tripwire policy for unattended waves**: stop on a trip for the census waves, or accept and flag; the
   Allport waves will likely trip as column IV did.
