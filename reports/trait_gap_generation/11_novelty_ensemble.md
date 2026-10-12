# 11. Lexical recall insurance for M3 (rewritten 2026-10-10; was: the novelty ensemble)

Rewritten against M3 as built, at Roger's request, by the coordinator (Fable).  The 2026-09-18 original — an
ensemble of cheap signals with an LLM only on disagreements — is in this file's git history; its premise is now
[M3](./coding_plan_platform.md) itself (cosine retrieval, a Haiku 5.5 relation call, the Sonnet 5.5 overlap call
with Opus 5.5 on the close calls, the cut-off rules of decisions 12-15), so sparing the LLM is no longer the
point.  What survives is the one thing M3 does not have: **a retrieval signal independent of the embedding.**

## 1. Idea

M3 judges a candidate only against the traits its embedding retrieval lists.  Every judgement downstream is
strong (the overlap call, the escalation, the cut-offs), but a true duplicate that the
[covered-space](./glossary.md#covered-and-directional-settings) cosine never surfaces is never judged at all, and
is decided "new" without any model looking at the pair.  That miss class is measured, small, and not zero:

- M2's acceptance warning on the chosen setting (openai, w20, centred): paraphrase recall at top-1 **0.938**
  against a 0.95 target, and AUC separating duplicates from distinct neighbours **0.586** against 0.85 — the
  embedding finds the region but cannot tell duplicate from neighbour; the overlap call does that, *when it sees
  the pair*.
- Decision 11's floor measurement: below cosine 0.35, 0.1% of recorded readings were 4 and 3.9% were 3 or above.
  On a wave the size of today's TDA (871 new words), a handful of real duplicates per wave are decided "new"
  unseen.

The fix is not another adjudicator but another *retriever*: a *lexical graph* — a dictionary's recorded
synonym and antonym links between words, here Open English WordNet plus the Moby thesaurus — and a little
morphology (shared stems, negation affixes).  A dictionary synonym is exactly the case an embedding can miss when
two glosses describe one concept from different ends; the graph does not care how the glosses embed.  Lexical
hits join M3's shortlist and are judged by the same relation and overlap calls as any retrieved neighbour; the
signal retrieves, the existing pipeline decides.  Nothing in it is trained on our list, and a candidate is never
auto-rejected by a lexical link alone.

Dropped from the original, with reasons: the masked-LM description-fit (the overlap call reads both descriptions
directly and better); the second embedding family ([plan 15's calibration](./15_metric_calibration.md) measured
embedding arms and chose); the agreement rules and LLM-only-on-disagreement protocol (M3's escalation is that,
with measured shares); ConceptNet (10 GB for links OEWN and Moby mostly carry).

## 2. Sources and tools

| Signal | Source | Availability / licence / format |
|---|---|---|
| Lexical graph | Open English WordNet 2025 via `pip install wn` (synonym, antonym, "similar to", also-see) | CC-BY 4.0, ~100 MB SQLite after `wn.download("oewn:2025+")`, into `data/external/` as [setup_external.py](../../data_analysis/gap_generation/setup_external.py) does downloads.  Verified 2026-09-18. |
| Lexical supplement | Moby Thesaurus II | public domain, Gutenberg #3202, flat `head,syn,syn,...`, ~25 MB raw (confirm at download).  Verified 2026-09-18.  Victorian-flavoured; synonym lists only, no antonyms. |
| Morphology | pure-Python stem and affix rules (un-, in-/im-/il-/ir-, non-, dis-, a-, -less/-ful) | no download. |

Multiword coverage in both lexicons is poor, and the corpus's invented labels
(`instrumentally_aligned_ai`, `good_even_when_unwatched`) are absent from them; the signal abstains there, which
is safe — an abstention changes nothing.

## 3. Method

1. **Lookup table** (local, built once per corpus state): every corpus trait label and live seed-queue trait
   label (statuses candidate / ready / tbd / backlog, as M3's queue search), lemmatised, mapped to its OEWN
   synsets and Moby rows.  Recorded with the lexicon versions and a content hash, provenance-style.
2. **Lexical neighbours in M3's shortlist.**  At scoring time a candidate's lemma is looked up; corpus or queue
   traits linked as synonym / similar / also-see that cosine retrieval did **not** list join the listed traits
   with `via: "lexical"` (today's values are `retrieved` and `expanded`; additive, so the frozen interface is
   untouched).  They go through the same relation call and overlap walk; the block records that the pair came
   from the lexicon.  No rubric text changes, so no pin moves.
3. **Antonym evidence for pair completions.**  A direct OEWN antonym link, or a shared stem with a negation
   affix, between the candidate and a singleton trait is recorded beside the relation call's "opposed" as
   independent evidence on the existing pair-completion output (95 flagged in today's TDA M3 alone; design item
   4: a find, not a drop).
4. **Retroactive sweep** (the recall insurance): run the lookup over every registry row already decided "new";
   any lexical link to a corpus or queue trait that the deciding run never listed gets the overlap call now, and
   a hit at the row's cut-off flags it for review with the pair and readings shown — it does not silently flip
   the decision.
5. **Same-stem dedup among candidates**: morphology families (organised / organization / organizational) reported
   to R1 as extra grouping evidence; R1's graph already merges by readings, so this is annotation, not a new
   mechanism.

## 4. Expected yield and biases

This is insurance, not a generator: the expected find is **a few true duplicates per thousand candidates**, plus
antonym evidence on a share of pair completions.  Over-flags: Moby's loose Victorian synonymy (mitigated: Moby
hits rank below OEWN hits and never flag alone below cosine 0.2); negation-affix pairs that are not trait
opposites (non-X placeholders are excluded by name).  Under-covers: multiword and invented labels (abstains), and
senses — a lexical link is by word, not sense, so a polysemous hit is exactly what the overlap call is for.

## 5. Cost

Downloads roughly 130 MB (OEWN + Moby; needs Roger's approval, question 1).  Local lookups: seconds.  LLM: only the
overlap calls on lexical-only pairs — at today's measured rates (~$2.9 per thousand pairs through Batches,
Sonnet and Opus together) a wave adds well under $1, and the retroactive sweep over every decided "new" row to
date is an estimated $1-3 once.  Total under $5; `usage.json` beside every output as always.

## 6. Testing

- **Signal quality on the labelled pairs** ([labelled_pairs.json](../../data/candidates/calibration/labelled_pairs.json),
  M2 task 12): of the 86 duplicate and 315 antonym pairs, what fraction carries the expected lexical link
  (recall); of the 553 near-distinct and 2,000 unrelated, how many would be flagged (precision).  Reported per
  lexicon and per link type before anything integrates.
- **Hidden-partner recovery**: the existing [recovery harness](../../data_analysis/gap_generation/recovery_test.py)
  hides a trait and presents it as a candidate; with the lexical path on, the hidden trait's partner or duplicate
  should surface even when its cosine falls outside the shortlist.  Reuses the harness unchanged.
- **The pilot measurement is the build gate** (§ 8).

## 7. Dependencies

Reads the registry and the M3 run records; touches [novelty.py](../../assistant_axis/gapgen/novelty.py)'s
shortlist only additively (`via: "lexical"`); rubrics, pins and prompts unchanged; labels shown in the judge
display form like every prompt.  Provides: the lookup table (reusable by R1 and by plan 04's filters), the
retroactive review flags, and antonym evidence on pair completions.

## 8. Pilot, and the numbers that decide

Before any integration code: download the lexicons, build the lookup, and run it **dry over recorded data** —
the labelled-pairs measurement (§ 6) and the retroactive lookup over all "new" rows to date, counting how many
lexical links the deciding runs never listed.  Judge a sample of those pairs (~$1) and report: misses found,
their readings, and the per-wave rate this implies.  **If the recorded batches show fewer than ~5 real misses in
total, this plan stops there** and the readout says so; the integration (steps 2-5) is only built if the
insurance has something to insure.

## 9. Open questions for Roger (answered 2026-10-12)

1. Approve the downloads and dependency: `wn` into the uv environment, OEWN 2025 (~100 MB) and Moby Thesaurus II
   (~25 MB) into `data/external/`.

   **Roger: approved.**  Two corrections to what was asked, found 2026-10-12: OEWN is already on disk
   ([wn.db](../../data/external/wn/wn.db), 112 MB, fetched 8 October for the Roget and WordNet harvest), and `wn`
   imports in the project environment, so only Moby remains to fetch (~25 MB).  Its version and licence are
   recorded when fetched, through the download manifest; the OEWN file's version is to be checked against the
   plan's "2025" then, not assumed.

2. Should lexical neighbours check queue labels as well as corpus labels (the lookup is the same; the queue adds
   ~250 live entries)?

   **Roger: yes.**  Two corrections: M3 already searches the queue's live statuses (`QUEUE_SEARCH_STATUSES`), so this
   is the same lookup, not a new one; and the live queue holds **119 trait entries** (84 `backlog`, 35 `candidate`), not ~250; M3 searches trait entries only.
   The contamination argument that settled the testing reference ([13](./13_generator_testing.md) § 9) does not
   apply: that was measurement, and this is production dedup, where a queue entry promoted last night should block
   a synonym today.

3. Timing of the retroactive sweep: now, before you review the TDA batch (its flags would land in that review),
   or folded into the end-of-generation R1 pass per
   [coding_plan_review.md § 10](./coding_plan_review.md)?

   **Roger: agreed with the recommendation.**  Run the lookup now, as a dry pilot over recorded data (no API spend,
   per § 8).  Hold the flags until the end-of-generation R1 pass, because the cross-batch repetition is visible
   there and flags landed in the TDA review now would largely duplicate the pre-handled machinery's output.

4. A lexical synonym hit whose overlap reading lands *below* the cut-off (the applied/practical case: same
   dictionary entry, different scope in our corpus): flag for review anyway, or trust the reading?

   **Roger: TODO, decide with data.**  The pilot's precision on below-cut-off hits decides it.  Until then such a
   hit is recorded as a note on the pair and is not added to the review queue.  Trigger: the § 8 pilot's readout.

5. Same-stem dedup before M1 (saves a few filter calls) or leave families to M3 and R1 (simpler)?

   **Roger: leave families to M3 and R1.**  Exact-stem duplicates already merge at submit; morphological families are
   R1's grouping evidence, so a separate dedup pass before M1 would duplicate that work for a few cents.

**Status (2026-10-12): greenlit for detailed planning** (Roger).  Next, in the order the [plans format](./PLAN_FORMAT.md)
gives: a coding plan (Fable writes planning documents), then the § 8 pilot: fetch Moby, build the lookup, run it dry
over the recorded "new" rows and the labelled pairs.  The integration (steps 2-5 of § 3) is built only if the pilot
finds at least about five real misses (§ 8).
