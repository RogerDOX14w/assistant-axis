# Gate audit 1: the census frequency floor and its stages

Written 2026-10-12 by an Opus audit agent, following the protocol in [README.md](./README.md) (gate 1 of its
table).  Read-only: no paid call, no code or data edited; this file is the only one written.  The samples
below are the agent's own reading, labelled as such; reference labels (M1, the probe, M3, Roger's review
decisions) are given beside them wherever they exist.

**Terms.**  M1, M3 and the registry are as in [escalations.md](../escalations.md) ("Terms"); the rest of the
vocabulary is in the [glossary](../../trait_gap_generation/glossary.md).  Used here:

- **Zipf**: log10 of a word's frequency per billion words in the `wordfreq` list (3 = once per million words).
  The English list stops near 1.0; a word it lacks scores 0.  For a phrase or hyphenated compound the floor
  uses its rarest content word.
- **The floor**: Zipf below 1.5 is a hard reject (no judge call) unless a rescue route applies; 1.5 to 2.5 is
  the **probe band**, where M1 adds the **definition probe** (one Haiku call: is this a real, definable word?
  "not known" turns the word away as `too_rare`).
- **Rescue routes** (decision 1b): the word is a negating-prefix form (un-, in-, non-) of a word at or above the
  floor; it arrives with a gloss hint; it comes from a curated generator (the censuses are one); or (route 4)
  its TDA familiarity is 0.5 or more.
- **TDA**: the 2,818 Trait Descriptive Adjectives, each with `prop`, the share of raters who knew the word.
  **Allport-Odbert**: the 1936 list in four columns: I traits, II temporary states, III social evaluations,
  IV metaphorical and doubtful.  **Allport-only**: in Allport-Odbert and not in the TDA.
- **OEWN**: Open English WordNet 2024 (in-tree under [data/external/wn/](../../../data/external/wn/)).  **Unknown word**: a census word in
  neither `wordfreq` nor OEWN.
- **The census table**: [census_table.jsonl](../../../data/candidates/censuses/census_table.jsonl), one row per
  distinct stem, with eligibility and stage.

## Verdict in brief

**Doing what was intended, but improvable.**  The gate has two parts that behave very differently.

1. **The dictionary floor applied to known Allport-only words** (`below_hard_reject`, 1,341 words) **removes real
   words, not junk**: 80% of a 60-word sample are real English words (68-88%), 27% are trait words a reader
   could know (17-39%; about 360 words), and M1 passed the rare pilot's words at a higher rate (60%) than
   `allport_hi`'s (50%), with as many M3 "new" per word as the TDA (46%).  For a curated list the 1.5 line is
   not supported by the data, which decision 1b (route 3) already said.  Roger's `allport_rare` stage (QUESTIONS
   34) corrects this, but only its 10% pilot has run: **927 words wait for the full stage, and 310 column-IV-only
   words have no stage at all** until the column IV decision.  The corpus traits
   [neopagan](../../../data/traits/instructions/neopagan.json) and
   [polyandrous](../../../data/traits/instructions/polyandrous.json) are among them.
2. **The `unknown_word` rule** (5,614 words, never submitted) **does what Roger intended about as well as
   possible**.  Its premise, "mostly archaic or dialect", holds: 57% of a 120-word sample are archaic, dialect,
   technical or nonce words.  It does remove real words that the frequency list lacks (37% are words a
   present-day reader would recognise), and 15% are recognisable trait words (10-23%; about 840).  But 16 of
   those 18 are variants or synonyms of words already submitted or in the corpus (envyful, schemeful,
   self-depreciative, mopy).  Only 2 of 120 carry a concept the agent could not find submitted under another
   word: 1.7% (0.5-5.9%), about 90 words.
3. **Kept but junk** (false positives of the floor): 4 of 60 (7%), three of them in the negating-prefix rescue
   (unwalking, unblown, unvital).  Each costs about half a cent at M1; not worth a rule.
4. **The probe band** (1.5 to 2.5) is close to a no-op on census words.  It turned away 7 of 1,210 probed words,
   two of them wrongly.  It costs about $0.05 in all; leave it.
5. **A defect (F3).**  A census rescue is defeated when another, non-curated generator floor-rejected the same
   stem first.  The registry merges the census source into the existing row, and M1 never re-filters a row that
   already has a filter block.  One TDA word is lost to this today:
   **irresolute** (raters 0.67, Zipf 1.49).  Two more will be lost when the full `allport_rare` stage runs:
   **sybaritic** and **restrictionist**.  The run's evaluation reports `tda_cut: 0`, because the value is
   hard-coded (F4).

## 1. The rule, from the code

There are two floors.  The census generator applies its own at ingest, to decide eligibility, as if the words
came from a dictionary (`curated=False`).  The platform applies one again at M1, with the census's rescue
context.

| step | where | what it compares | a word that fails |
|---|---|---|---|
| 1. Unknown test | [ingest.py](../../../assistant_axis/gapgen/generators/censuses/ingest.py):402 | `not in_wordnet(s) and zipf(s) <= 0` on the whole cleaned surface.  The OEWN lookup tries the surface, hyphen and space variants, and the hyphen dropped, **with no lemmatiser** ([glosshint.py](../../../assistant_axis/gapgen/generators/censuses/glosshint.py):46-54, [ingest.py](../../../assistant_axis/gapgen/generators/censuses/ingest.py):277-278) | flagged unknown.  An unknown word is repaired only if the one-edit fix is a doubled letter or an inserted vowel past the second letter ([ingest.py:200-215, 403-413](../../../assistant_axis/gapgen/generators/censuses/ingest.py); 23 repairs) |
| 2. Dictionary floor | [ingest.py:446](../../../assistant_axis/gapgen/generators/censuses/ingest.py) → [freq.py](../../../assistant_axis/gapgen/freq.py):94-129 | `zipf_info(surface)`.  The content words come from [normalize.py](../../../assistant_axis/gapgen/normalize.py):85-91, with a fixed stoplist and hyphens split; Zipf is the minimum over them ([freq.py:108-110](../../../assistant_axis/gapgen/freq.py)), and the word is below the floor at Zipf < `HARD_REJECT_BELOW` = 1.5 ([freq.py:37, 111](../../../assistant_axis/gapgen/freq.py)).  At ingest only the negating-prefix rescue can apply ([freq.py:86-91, 116-118](../../../assistant_axis/gapgen/freq.py): a word under the floor whose prefix non-, un- or in- leaves a base with Zipf ≥ 1.5) | hard reject unless rescued |
| 3. Eligibility | [ingest.py:449-456](../../../assistant_axis/gapgen/generators/censuses/ingest.py) | TDA word: always eligible, stage `tda`.  Allport-only word that fails step 2: ineligible, with reason `unknown_word` if no Allport entry for the stem is known ([ingest.py:346-349](../../../assistant_axis/gapgen/generators/censuses/ingest.py)), else `below_hard_reject`.  Otherwise stage `allport_probe` if `probe_band` (1.5 ≤ Zipf < 2.5 = `PROBE_BELOW`, or any rescue; [freq.py:38, 127](../../../assistant_axis/gapgen/freq.py)), else `allport_hi` | **never submitted**: the row stays in the census table only |
| 4. Platform view, recorded | [ingest.py:447-448](../../../assistant_axis/gapgen/generators/censuses/ingest.py) | `zipf_info` with `curated=True`, the gloss hint and the TDA `prop`, stored as `freq_platform`.  Under it no census word would be hard-rejected (route 3) | information only |
| 5. Stages | [submit.py](../../../assistant_axis/gapgen/generators/censuses/submit.py):50-58, 99-112 | `allport_hi` and `allport_probe` minus Allport-only words listed in column IV alone; `allport_iv` takes those; `allport_rare` takes `below_hard_reject` minus column-IV-only.  `every_nth` ([submit.py:115-120](../../../assistant_axis/gapgen/generators/censuses/submit.py)) draws the pilots | `unknown_word` and the 310 column-IV-only words below the floor are in **no stage** |
| 6. M1 | [filter.py](../../../assistant_axis/gapgen/filter.py):264-287, 478-482, 523-530; [split.py](../../../assistant_axis/gapgen/split.py):650-653 | `zipf_info` again with the row's familiarity, gloss hint and curated flag.  A hard reject gets a `reject` / `too_rare` block with no call.  A word in the probe band gets the probe, and "not known" turns it away as `too_rare` | turned away |
| 7. Registry merge | [registry.py](../../../assistant_axis/gapgen/registry.py):447-453, 573-574; [traithood_filter.py](../../../data_analysis/gap_generation/traithood_filter.py):412 | a new source joins an existing row and the filter block is not touched; `--run` filters only rows with no filter block | an earlier free floor reject stands (F3) |

Constants: `HARD_REJECT_BELOW` 1.5, `PROBE_BELOW` 2.5, `FAMILIARITY_OVERRIDE_MIN` 0.5, `NEGATING_PREFIXES`
("non", "un", "in"), all at [freq.py:37-40](../../../assistant_axis/gapgen/freq.py); `CURATED_GENERATORS` = {censuses} ([freq.py:55-58](../../../assistant_axis/gapgen/freq.py)).

## 2. The intent

- **Decision 1** ([decisions_m1.md](../../trait_gap_generation/decisions_m1.md) § 1).  "The floor at 2.0
  rejects words unread.  It exists to throw out dictionary junk for free."  Roger set 1.5: "set the Zipf floor to
  1.5.  This is option B."  **The value has a recorded derivation**: 1.5 cuts 13 of 659 corpus labels and 270
  of 1,000 random dictionary adjectives.
- **Rule 1b**, same section.  "The floor is there to stop dictionary junk, and none of these routes carries
  dictionary junk."  Route 3: "It comes from a curated source, such as a psychology inventory, and not from a
  dictionary walk.  Rescues [distractible](../../../data/traits/instructions/distractible.json),
  [satisficing](../../../data/traits/instructions/satisficing.json) and
  [collectivistic](../../../data/traits/instructions/collectivistic.json) when a census or inventory proposes
  them."  "Approved, all three."
- **Plan 01**, the research plan ([01_psycholexical_censuses.md](../../trait_gap_generation/01_psycholexical_censuses.md),
  step 1): misspellings are fixed against WordNet and `wordfreq`, "anything absent from both is flagged, not
  deleted".
- **Coding plan 01** ([coding_plan_01_censuses.md](../../trait_gap_generation/coding_plan_01_censuses.md), § 1).
  "Zipf is a **feature, not a gate**.  The generator submits every TDA word and every Allport word the platform
  would not hard-reject."  This was written on 2026-09-23, before rule 1b made the censuses curated.  Read
  literally after 1b, it would submit every Allport word.  The ingest docstring ([ingest.py:9-17](../../../assistant_axis/gapgen/generators/censuses/ingest.py)) instead applies
  the floor with `curated=False`.
- **QUESTIONS 34** (Roger, 2026-10-09; [QUESTIONS.md](../../trait_gap_generation/QUESTIONS.md)).  "submit the
  1,341 known-but-rare words (below Zipf 1.5 but known to `wordfreq` or OEWN), never the 5,614 unknown words; run
  them last, after `allport_hi` and `allport_probe`, opening with a 10% pilot to see the yield."  Its premise:
  the unknown words are "mostly genuine archaic or dialect words: overfacing, gnathonic, toadeater".  **No sample
  was recorded behind the premise**; section 4 tests it.
- **QUESTIONS 29**: column IV gets its own stage, and "its 310 words below the floor wait with that decision".
  **QUESTIONS 32**: every TDA word is submitted, and the 251 below the floor go to the probe.  **QUESTIONS 42**
  (cited by the README) is the Roget harvest's adoption of 1.5; it confirms the value, not the census rule.
- **The stage order** (rare last, IV after probe) has no yield-based derivation; the pilots were to supply one.

The audit therefore asks two things.  Does the floor remove words not worth a judge call (junk) without a
call?  And within this curated list, are the known-but-rare words worth sending (Q34: yes) and the unknown words
not worth it (Q34: no, on the archaic premise)?

## 3. The recorded discard, reproduced

Reproduced from [census_table.jsonl](../../../data/candidates/censuses/census_table.jsonl).  Recomputing
`zipf_info` for all 17,957 stemmed rows gives the table's values exactly (0 differences).  The figures match
[ingest_counts.json](../../../data/candidates/censuses/ingest_counts.json) and every run's
[evaluation.json](../../../data/candidates/runs/censuses/2026-10-08-pilot/evaluation.json) floor block.

| pool (Allport-only unless TDA) | words | submitted so far | status |
|---|---:|---:|---|
| `tda` (all eligible; 251 below the dictionary floor reach the probe by rescue) | 2,818 | 2,818 | [pilot](../../../data/candidates/runs/censuses/2026-10-08-pilot/) 564, [full](../../../data/candidates/runs/censuses/2026-10-10-tda/) 2026-10-10 |
| `allport_hi` (Zipf ≥ 2.5, not IV-only) | 3,646 | 3,646 | [run](../../../data/candidates/runs/censuses/2026-10-11-allport_hi/) 2026-10-11 (its [evaluation.json](../../../data/candidates/runs/censuses/2026-10-11-allport_hi/evaluation.json) is not written yet; figures from the registry) |
| `allport_probe` (1.5-2.5, or negating-prefix rescue; not IV-only) | 2,525 | 0 | not run.  1,794 in the band; 731 rescued, 574 of them unknown words |
| `allport_iv` (column-IV-only, eligible) | 2,013 | 202 | [10% pilot](../../../data/candidates/runs/censuses/2026-10-09-iv-pilot/); the rest waits on Roger |
| `allport_rare` (`below_hard_reject`, not IV-only) | 1,031 | 104 | [10% pilot](../../../data/candidates/runs/censuses/2026-10-09-rare-pilot/); the rest waits |
| column-IV-only below the floor | 310 | 0 | no stage; waits with the column IV decision |
| **`unknown_word`** | **5,614** | 0 | **never** (Q34) |
| `malformed` (F.F.V) | 1 | 0 | never |

`below_hard_reject` is 1,341 = 1,031 + 310: 822 words in `wordfreq` at Zipf 1.0-1.5 and 519 known to OEWN only
(Zipf 0).  Of the 6,477 unknown rows, 863 are rescued by the negating prefix and are eligible (574 in
`allport_probe`, 289 in `allport_iv`).

**Probe routes per run** (`submitted_probe_routes` in each run's evaluation:
[pilot](../../../data/candidates/runs/censuses/2026-10-08-pilot/evaluation.json),
[TDA](../../../data/candidates/runs/censuses/2026-10-10-tda/evaluation.json),
[IV pilot](../../../data/candidates/runs/censuses/2026-10-09-iv-pilot/evaluation.json),
[rare pilot](../../../data/candidates/runs/censuses/2026-10-09-rare-pilot/evaluation.json)) and **what the probe and M1 then did**
(registry, last row per key):

| run | probed | band / curated / gloss hint / negating prefix | probe "not known" | M1 trait share |
|---|---:|---|---:|---|
| TDA pilot (564) | 197 | 97 / 36 / 13 / 51 | (in the full run) | (in the full run) |
| TDA full (2,818) | 1,015 | 520 / 170 / 81 / 244 | 4: unforseeing, competitory, underogatory, dissensualized | 2,526 / 2,818 (89.6%) |
| IV pilot (202) | 92 | 52 / 0 / 0 / 40 | 0 | 86 / 202 (42.6%) |
| rare pilot (104) | 104 | 0 / 37 / 67 / 0 | 3: pitch-kettled, bonte, chuffy | 62 / 104 (59.6%) |
| allport_hi (3,646) | 0 | (all Zipf ≥ 2.5) | - | 1,819 / 3,646 (49.9%) |

The registry holds **one census row floor-rejected without a call**: irresolute (F3, section 6.4).
[evaluate.py](../../../assistant_axis/gapgen/generators/censuses/evaluate.py) and
[report.py](../../../assistant_axis/gapgen/generators/censuses/report.py) report `tda_cut: 0` for every run
([report.py:70](../../../assistant_axis/gapgen/generators/censuses/report.py), a literal).

## 4. The samples

**Selection.**  `random.Random(20261012)`, drawn in this order, each from its pool sorted by stem: U, 120
`unknown_word` rows; B, 60 `below_hard_reject` rows; then 10 each from six kept strata.  The discards are drawn
from the table, not per run, because the floor acts at ingest before any run.  The kept strata cover the runs
the gate has seen (the TDA run, `allport_hi`, the IV pilot, the rare pilot) and the unrun `allport_probe` pool.

**Codes (the agent's reading, against the intent).**

- For discards:
  - **T**: a trait word a present-day reader would recognise, either familiar or a transparent derivation of a
    familiar word: a false negative.
  - **T-L**: a trait word that is learned or literary: a false negative in the broad sense.
  - **T-N**: a trait meaning, but archaic or dialect, so a reader would not know or would misread it: a correct
    discard.
  - **R**: recognisable, but not a trait (an act, a participle, a thing word, a passing state).
  - **L**: learned, not a trait.
  - **O**: archaic, dialect, technical, nonce or unrecognisable.
- For kept words: **OK** is a real word worth a call; **FP** is a nonce or obscure word that the floor's intent
  says should have been cut.

The judgment rests on the word's form and its dictionary sense: the OEWN gloss hint where there is one,
presence in the three Roget texts under [data/external/roget/](../../../data/external/roget/)
([pg10681.txt](../../../data/external/roget/pg10681.txt), [pg22.txt](../../../data/external/roget/pg22.txt),
[mawson1911_archive_djvu.txt](../../../data/external/roget/mawson1911_archive_djvu.txt)), the base word's Zipf,
and the census words or corpus traits that already carry the concept.

**Reference labels.**  U: none; no unknown word was ever judged.  B: two items are in the rare pilot, and M1
agrees with both readings (pettish trait, cocotte roles).  Kept: M1, the probe, M3 and Roger's review
decisions, shown in the table.

### U: `unknown_word`, 120 of 5,614

The "basis flags" column is mechanical: Roget means the word occurs in one of the three Roget texts; lemma is an
OEWN lemma found through `wn.morphy`, which the ingest does not use; base is the best affix-stripped base and
its Zipf.  The flags are heuristics and can mislead (sick-thought, meng).

| # | word | Allport column | basis flags | verdict | reading (the agent's) |
|---|---|---|---|---|---|
| 1 | overbrooding | II | base brooding 3.11 | T | over- + brooding (Zipf 3.11): given to brooding too much; brooding is submitted |
| 2 | altisonant | III | - | O | Latinate 'high-sounding'; few readers know it |
| 3 | beworn | II | base worn 4.26 | O | archaic be- form of worn; a state, not a disposition |
| 4 | acharne | I | Roget | T-N | French acharné, 'relentless, bloodthirsty' (in Roget); a reader would not know it |
| 5 | bestaring | II | base staring 4.14 | O | archaic be- form; an act of staring |
| 6 | spuddling | II | - | O | dialect, 'potter about' |
| 7 | semidramatic | I | - | T | 'somewhat dramatic', transparent; dramatic is submitted, [melodramatic](../../../data/traits/instructions/melodramatic.json) is a corpus trait |
| 8 | warmable | III | base warm 4.71 | R | 'can be warmed'; not said of character |
| 9 | brunting | II | base brunt 3.12 | O | archaic verb form |
| 10 | giantizing | II | - | O | nonce verb |
| 11 | outromancing | II | - | R | an act (out-romancing someone) |
| 12 | bewhoring | II | - | O | archaic insult verb |
| 13 | envyful | I | base envy 3.84 | T | 'full of envy'; variant of [envious](../../../data/traits/instructions/envious.json) |
| 14 | goustrous | I | - | T-N | Scots, 'boisterous, frightening' |
| 15 | sphinxlike | IV | base sphinx 3.00 | T | enigmatic; the closed spelling of sphinx-like (Zipf 3.0 hyphenated); enigmatic and inscrutable are submitted |
| 16 | spoffish | I | - | T-N | dialect, 'fussy, officious' |
| 17 | guerdoning | II | - | O | archaic, 'rewarding' |
| 18 | cajoler | I | - | T | agent noun of a familiar verb; cajoling and wheedling are submitted |
| 19 | titvated | II | - | O | misspelling of titivated (dressed up); not a trait |
| 20 | sloomy | III | - | T-N | dialect, 'sluggish' |
| 21 | unupbraiding | I | - | T-N | 'not reproachful'; base upbraiding is itself rare (1.34) |
| 22 | menging | II | base meng 3.14 | O | dialect, 'mixing' |
| 23 | oxyaesthesia | IV | - | O | medical term |
| 24 | craichy | IV | Roget | O | dialect, '[sickly](../../../data/traits/instructions/sickly.json)' (physical) |
| 25 | sick-thoughted | II | base sick-thought 4.80 | T-N | Shakespearean 'lovesick'; the sense is not recoverable at sight |
| 26 | depredatory | III | - | T-L | 'plundering, predatory'; learned |
| 27 | catharizing | III | - | O | rare, 'purifying' |
| 28 | mopy | I | base mop 3.39 | T | spelling of mopey (Zipf 2.08); moping is submitted |
| 29 | japish | I | - | T-N | 'given to japes'?; obscure |
| 30 | teasable | I | base tease 3.59 | T | 'easily teased'; the type of the TDA's flatterable and provocable (raters 0.90, 0.84); nearest submitted: touchy, [thin-skinned](../../../data/traits/instructions/thin_skinned.json) |
| 31 | subjectable | III | base subject 4.96 | R | 'can be subjected'; not a trait |
| 32 | unsorrowed | III | - | O | archaic, 'unlamented' |
| 33 | peacocky | III | base peacock 3.44 | T | vain and showy, informal; vain, showy, cocky are submitted |
| 34 | unaffrighted | II | - | T-N | archaic, 'unafraid' |
| 35 | bounceable | I | base bounce 4.02 | T-N | archaic 'boastful'; read today as 'able to bounce' |
| 36 | leaguing | II | lemma league, base league 5.13 | R | inflection of league (OEWN through a lemmatiser); an act |
| 37 | clearish | III | base clear 5.25 | R | 'somewhat clear' |
| 38 | chicaning | II | lemma chicane | T-N | inflection of chicane; obscure |
| 39 | outpainting | II | base painting 4.60 | R | an act |
| 40 | philhymnic | I | - | O | 'fond of hymns'; learned coinage |
| 41 | smoothish | I | base smooth 4.40 | R | 'somewhat smooth' |
| 42 | mixty-maxty | II | - | O | Scots, 'jumbled' |
| 43 | cabbagy | III | base cabbage 3.55 | R | cabbage-like; not of character |
| 44 | lessoned | III | base lesson 4.47 | R | 'taught' |
| 45 | traily | I | base trail 4.45 | T-N | dialect, '[slovenly](../../../data/traits/instructions/slovenly.json)' |
| 46 | benetting | II | base netting 3.24 | O | archaic, 'ensnaring' |
| 47 | agensic | IV | - | O | no dictionary form found |
| 48 | demiurgic | I | - | L | 'of a demiurge'; learned, not a disposition |
| 49 | overbig | IV | base big 5.67 | R | 'too big'; physical |
| 50 | mirating | II | - | O | dialect, 'marvelling' |
| 51 | stomachful | I | base stomach 4.42 | T-N | archaic 'stubborn, resentful'; read today as a quantity |
| 52 | seedful | III | base seed 4.37 | R | 'full of seed' |
| 53 | draggly | III | base drag 4.29 | R | bedraggled; appearance |
| 54 | overdazzling | III | base dazzling 3.39 | R | not a disposition |
| 55 | plebeianized | IV | - | L | 'made plebeian'; a process |
| 56 | caggy | III | - | O | dialect; sense unclear |
| 57 | libratory | I | Roget | O | 'oscillating' (in Roget); technical |
| 58 | resistable | III | base resist 4.20 | R | variant of resistible |
| 59 | besmoothing | II | base smoothing 3.04 | O | archaic be- form |
| 60 | outtricking | II | base tricking 3.00 | R | an act |
| 61 | schemeful | I | base scheme 4.57 | T | 'full of schemes'; [scheming](../../../data/traits/instructions/scheming.json) is a corpus trait |
| 62 | hypped | II | Roget | T-N | archaic 'melancholy' (the hyp); read today as hyped |
| 63 | cancrizans | IV | - | O | music term |
| 64 | glamouring | II | lemma glamour, base glamour 3.51 | O | inflection of glamour, 'bewitch'; obscure |
| 65 | mesmerizable | IV | - | T | 'easily mesmerized'; suggestible is submitted |
| 66 | filliping | II | - | O | archaic, 'flicking' |
| 67 | boldened | II | - | R | 'emboldened'; a passing state |
| 68 | confineless | III | - | O | Shakespearean, 'boundless' |
| 69 | noosing | II | lemma noose | R | an act |
| 70 | overstudied | III | base studied 4.49 | R | 'too studied'; said of a performance |
| 71 | self-depreciative | I | - | T | variant of [self-deprecating](../../../data/traits/instructions/self_deprecating.json) |
| 72 | besmutting | II | - | O | archaic be- form |
| 73 | prisoning | III | base prison 4.80 | R | 'imprisoning'; an act |
| 74 | fadding | II | base fad 3.26 | O | dialect, 'fussing over trifles' |
| 75 | mossbacked | III | - | T-L | mossback, 'old fogey, reactionary' (dated American) |
| 76 | overesteemed | III | base esteemed 3.28 | R | 'overrated'; others' view, not a disposition |
| 77 | enosing | II | - | O | no recognisable form |
| 78 | psychagogic | IV | - | O | learned technical |
| 79 | pseudaesthesia | IV | - | O | medical |
| 80 | fefnicute | I | - | T-N | dialect (a hypocrite?); obscure |
| 81 | thunderless | III | base thunder 4.14 | R | not of character |
| 82 | carlylian | IV | - | O | 'of Carlyle' |
| 83 | outfawning | II | - | R | an act |
| 84 | charlatanish | III | - | T | like a charlatan; charlatan is submitted |
| 85 | suiform | IV | - | O | zoological, 'pig-shaped' |
| 86 | royet | I | - | T-N | Scots, 'wild, unruly' |
| 87 | chuckleheaded | III | - | T | 'stupid', informal; thickheaded is submitted |
| 88 | begnawed | II | - | O | archaic |
| 89 | miragy | IV | base mirage 3.29 | O | nonce |
| 90 | embrangled | IV | lemma embrangle | O | archaic, 'entangled' |
| 91 | grangousier | I | - | O | a Rabelais character's name |
| 92 | disglorifying | II | - | O | nonce |
| 93 | indeflectible | III | - | T | 'cannot be deflected', steadfast; the type of the TDA's undivertible (raters 0.82); [inflexible](../../../data/traits/instructions/inflexible.json) is a corpus trait |
| 94 | poltroonish | III | - | T-L | [cowardly](../../../data/traits/instructions/cowardly.json); poltroon is rare (1.35) |
| 95 | pentit | II | - | O | no recognisable form |
| 96 | icteritious | IV | - | O | medical, 'jaundiced' |
| 97 | beefhead | III | - | T | 'blockhead', informal insult; thickheaded is submitted |
| 98 | downsome | II | base down 5.88 | T-N | dialect 'downcast'?; obscure |
| 99 | gesticulative | I | - | T | 'given to gesturing'; no same-concept word found submitted (nearest: [expressive](../../../data/traits/instructions/expressive.json)) |
| 100 | overpleased | II | base pleased 4.44 | R | a passing state |
| 101 | belittler | I | - | T | one who belittles; disparaging is submitted |
| 102 | picksome | I | base pick 5.08 | T-N | dialect, 'choosy' |
| 103 | sulphitic | I | - | O | chemical term |
| 104 | attainting | III | lemma attaint | O | archaic legal verb |
| 105 | grammaticaster | I | - | T-N | '[petty](../../../data/traits/instructions/petty.json) pedant'; learned archaism |
| 106 | crescive | II | - | O | archaic, 'growing' |
| 107 | bloodshedder | I | base bloodshed 3.29 | R | a killer: a role or an act, not a disposition |
| 108 | endamaging | II | base damaging 3.91 | O | archaic, 'damaging' |
| 109 | bamming | II | base bam 3.64 | O | archaic, 'hoaxing' |
| 110 | disciplinable | III | base discipline 4.23 | R | 'subject to discipline' |
| 111 | flourishy | I | base flourish 3.53 | T | given to flourishes, showy; flamboyant and showy are submitted |
| 112 | overcapable | III | base capable 4.61 | R | odd; not a disposition |
| 113 | exorable | III | Roget | T-L | 'moved by entreaty', inexorable's opposite; learned |
| 114 | reckling | IV | - | O | dialect, 'runt' |
| 115 | amorphic | IV | - | L | variant of amorphous; not of character |
| 116 | twattling | II | - | O | archaic, 'prattling' |
| 117 | snatchy | I | base snatch 3.53 | O | sense unclear |
| 118 | tardiloquent | I | - | T-N | 'slow of speech'; learned coinage |
| 119 | marcescent | IV | - | O | botanical |
| 120 | erotomaniac | I | - | L | clinical noun; a diagnosis |

Tally: T 18, T-L 4, T-N 19, R 26, L 4, O 49.  By Allport column, T is 10 of 32 in column I, 5 of 31 in III,
2 of 18 in IV and 1 of 39 in II.

### B: `below_hard_reject`, 60 of 1,341

| # | word | Allport column | Zipf | gloss hint (OEWN) | verdict | reading (the agent's) |
|---|---|---|---|---|---|---|
| 1 | feculent | III | 1.06 | foul with waste matter | L | 'foul with waste'; not of character |
| 2 | twopenny | III | 1.38 | of trifling worth | L | 'worthless'; said of things |
| 3 | self-exculpating | I | 1.15 | - | T | given to excusing oneself; transparent |
| 4 | particularistic | I | 1.10 | relating to particularism (exclusive interest in one group or class... | T-L | favouring one's own group ([parochial](../../../data/traits/instructions/parochial.json) outlook) |
| 5 | fulgurous | IV | 0 (absent) | amazingly impressive [IV] | O | 'flashing like lightning' |
| 6 | minatory | I | 1.06 | threatening or foreshadowing evil or tragic developments | T-L | menacing |
| 7 | ponderable | IV | 1.11 | capable of being weighed or considered [IV] | L | 'can be weighed' |
| 8 | coordinative | III | 1.18 | serving to connect two grammatical constituents of identical constr... | L | grammar or organisational sense |
| 9 | starveling | IV | 1.23 | someone who is starving (or being starved) (noun) [IV] | L | a starving person (noun) |
| 10 | loathly | III | 0 (absent) | highly offensive | O | archaic 'loathsome' |
| 11 | acentric | IV | 0 (absent) | lacking a centromere [IV] | O | genetics |
| 12 | carpetbag | IV | 1.25 | following the practices or characteristic of carpetbaggers [IV] | L | carpetbagger-like (a role) |
| 13 | edacious | II | 0 (absent) | disposition to be edacious (a general tendency, not an episode): de... | T-L | voracious, [greedy](../../../data/traits/instructions/greedy.json) |
| 14 | amative | I | 0 (absent) | inclined toward or displaying love | T-L | [amorous](../../../data/traits/instructions/amorous.json) |
| 15 | susurrant | II | 0 (absent) | disposition to be susurrant (a general tendency, not an episode): m... | O | 'whispering' (a sound) |
| 16 | enthusing | II | 1.45 | - | R | an act |
| 17 | pettish | I | 0 (absent) | easily irritated or annoyed | T-L | petulant (M1 in the rare pilot: trait) |
| 18 | smeller | I | 1.31 | - | R | one who smells |
| 19 | precautious | I | 1.14 | - | T | taking precautions; transparent (corpus: [cautious](../../../data/traits/instructions/cautious.json)) |
| 20 | currish | III | 0 (absent) | base and cowardly | T-L | snarling, mean-spirited (cur) |
| 21 | jussive | IV | 1.23 | - | O | grammar term |
| 22 | sudatory | II | 0 (absent) | a medicine that causes or increases sweating (noun) | O | medical |
| 23 | outworn | IV | 1.43 | last longer than others (verb) [IV] | R | outdated (of ideas) |
| 24 | psychoneurotic | IV | 1.08 | affected with emotional disorder [IV] | L | dated clinical label |
| 25 | swad | III | 1.29 | a bunch (noun) | O | dialect |
| 26 | jackanapes | III | 1.32 | someone who is unimportant but cheeky and presumptuous (noun) | T-L | a cheeky, presumptuous person |
| 27 | onlooking | II | 1.41 | - | R | watching (an act) |
| 28 | baconian | IV | 1.47 | - | L | 'of Bacon' |
| 29 | codding | II | 1.31 | fool or hoax (verb) | L | British 'joking, hoaxing' (an act) |
| 30 | casuist | I | 0 (absent) | someone whose reasoning is subtle and often specious (noun) | T-L | a specious reasoner (noun) |
| 31 | perfectible | III | 1.19 | capable of becoming or being made perfect | L | 'can be perfected' |
| 32 | dementing | III | 1.09 | - | R | not of character |
| 33 | fisty | III | 1.24 | - | O | sense unclear |
| 34 | quidnunc | I | 0 (absent) | a person who meddles in the affairs of others (noun) | T-N | a busybody; obscure |
| 35 | anormal | III | 1.06 | - | L | variant of abnormal |
| 36 | chording | II | 1.34 | - | R | a musical act |
| 37 | saliferous | IV | 0 (absent) | containing or yielding salt [IV] | O | geology |
| 38 | opinionative | I | 0 (absent) | obstinate in your opinions | T | variant of [opinionated](../../../data/traits/instructions/opinionated.json) |
| 39 | cackler | III | 0 (absent) | a hen that has just laid an egg and emits a shrill squawk (noun) | R | one who cackles; a hen |
| 40 | drudging | II | 1.44 | disposition to be drudging (a general tendency, not an episode): do... | R | an act, or a plodding state |
| 41 | cassocked | III | 0 (absent) | dressed in a cassock | L | dress |
| 42 | cankerous | III | 0 (absent) | having an ulcer or canker | L | ulcerous |
| 43 | frighted | II | 1.35 | - | L | archaic 'frightened' (a state) |
| 44 | trembly | I | 1.26 | - | R | shaky (a state) |
| 45 | adsorptive | I | 1.16 | having capacity or tendency to adsorb or cause to accumulate on a s... | L | chemistry |
| 46 | bloomy | III | 1.37 | - | R | not of character |
| 47 | sybaritic | I | 1.47 | displaying luxury and furnishing gratification to the senses | T-L | luxury-loving (registry: floor-rejected earlier under antonym_check, see F3) |
| 48 | cocotte | III | 1.48 | a woman who engages in sexual intercourse for money (noun) | L | a prostitute; a role (M1 in the rare pilot: roles) |
| 49 | truckling | II | 0 (absent) | the act of obeying meanly (especially obeying in a humble manner or... | T-L | servile, toadying |
| 50 | proselyting | II | 1.28 | - | L | proselytizing (an act) |
| 51 | lubricious | I | 1.23 | characterized by lust | T-L | lewd |
| 52 | unstinted | IV | 1.13 | very generous [IV] | L | said of praise or effort |
| 53 | rooky | III+IV | 1.13 | - | O | sense unclear |
| 54 | aweary | II | 1.07 | disposition to be aweary (a general tendency, not an episode): phys... | L | archaic 'weary' (a state) |
| 55 | sabbatarian | I | 1.23 | pertaining to the Sabbath and its observance | T-L | a strict Sabbath observer: a membership, which the corpus counts as a trait |
| 56 | stogy | III | 0 (absent) | a cheap cigar (noun) | O | a cigar |
| 57 | mediumistic | I | 1.07 | - | L | of a spiritualist medium |
| 58 | weathercock | IV | 1.44 | weathervane with a vane in the form of a rooster (noun) [IV] | T | a fickle person; a metaphor anyone reads (corpus: [fickle](../../../data/traits/instructions/fickle.json)) |
| 59 | errorless | III | 1.43 | free from error | R | of a performance |
| 60 | tendinous | IV | 1.40 | consisting of tendons or resembling a tendon [IV] | L | anatomy |

Tally: T 4, T-L 12, T-N 1, R 11, L 21, O 11.  `[IV]` marks the gloss hint's "metaphorical or doubtful" note.

### K: kept words, 60 in six strata

K5 is the table's `allport_hi` stage.  Its column-IV-only rows (night-eyed, sterilized) run under `allport_iv`.

| stratum | word | Zipf | TDA prop | M1 outcome | probe | M3 | Roger | verdict | reading (the agent's) |
|---|---|---|---|---|---|---|---|---|---|
| K1 TDA below 1.5 | planful | 0 (absent) | 0.33 | trait | known | covered | unreviewed | OK | transparent; psychology term |
| K1 TDA below 1.5 | agitable | 0 (absent) | 0.74 | trait | known | covered | unreviewed | OK | transparent |
| K1 TDA below 1.5 | nymphomaniacal | 0 (absent) | 0.88 | trait | known | covered | unreviewed | OK | clinical but known |
| K1 TDA below 1.5 | overcharitable | 0 (absent) | 0.52 | trait | known | new | unreviewed | OK | transparent |
| K1 TDA below 1.5 | overproud | 0 (absent) | 0.75 | trait | known | new | merged into [arrogant](../../../data/traits/instructions/arrogant.json) | OK | transparent |
| K1 TDA below 1.5 | agitative | 0 (absent) | 0.80 | trait | known | new | unreviewed | OK | learned |
| K1 TDA below 1.5 | inconvincible | 0 (absent) | 0.93 | trait | known | new | merged into [unyielding](../../../data/traits/instructions/unyielding.json) | OK | transparent |
| K1 TDA below 1.5 | prognosticating | 1.39 | 0.50 | trait | known | new | unreviewed | OK | learned; weak trait reading |
| K1 TDA below 1.5 | overloud | 0 (absent) | 0.76 | trait | known | new | unreviewed | OK | transparent |
| K1 TDA below 1.5 | overdiligent | 0 (absent) | 0.58 | trait | known | new | accepted | OK | transparent |
| K2 TDA 1.5-2.5 | clubby | 1.70 | 0.40 | trait | known | covered | unreviewed | OK | - |
| K2 TDA 1.5-2.5 | sacrilegious | 2.43 | 0.48 | trait | known | covered | unreviewed | OK | - |
| K2 TDA 1.5-2.5 | impious | 2.12 | 0.49 | trait | known | covered | unreviewed | OK | - |
| K2 TDA 1.5-2.5 | saccharine | 2.48 | 0.56 | trait | known | new | unreviewed | OK | - |
| K2 TDA 1.5-2.5 | [gluttonous](../../../data/traits/instructions/gluttonous.json) | 2.22 | 0.97 | trait | known | covered | unreviewed | OK | corpus trait |
| K2 TDA 1.5-2.5 | giggly | 2.26 | 0.91 | trait | known | new | unreviewed | OK | - |
| K2 TDA 1.5-2.5 | miserly | 2.33 | 0.57 | trait | known | covered | unreviewed | OK | - |
| K2 TDA 1.5-2.5 | bellicose | 2.28 | 0.34 | trait | known | covered | unreviewed | OK | - |
| K2 TDA 1.5-2.5 | slipshod | 1.94 | 0.68 | trait | known | new | unreviewed | OK | - |
| K2 TDA 1.5-2.5 | idolatrous | 2.15 | 0.82 | trait | known | new | unreviewed | OK | - |
| K3 Allport, unknown, negating-prefix rescue | uncohesive | 0 (absent) | - | not run | - | - | - | OK | real; said of groups, not a person |
| K3 Allport, unknown, negating-prefix rescue | unentangled | 0 (absent) | - | not run | - | - | - | OK | real; a state |
| K3 Allport, unknown, negating-prefix rescue | unbeguiled | 0 (absent) | - | trait | known | new | unreviewed | OK | real; trait reading |
| K3 Allport, unknown, negating-prefix rescue | unwalking | 0 (absent) | - | not run | - | - | - | FP | nonce; no person sense |
| K3 Allport, unknown, negating-prefix rescue | unblown | 0 (absent) | - | not run | - | - | - | FP | archaic 'not yet in bloom' |
| K3 Allport, unknown, negating-prefix rescue | noncollegiate | 0 (absent) | - | not run | - | - | - | OK | real; a membership |
| K3 Allport, unknown, negating-prefix rescue | unintoxicating | 0 (absent) | - | not run | - | - | - | OK | real; said of drinks |
| K3 Allport, unknown, negating-prefix rescue | unpitied | 0 (absent) | - | not run | - | - | - | OK | real; a state |
| K3 Allport, unknown, negating-prefix rescue | unvital | 0 (absent) | - | not run | - | - | - | FP | nonce |
| K3 Allport, unknown, negating-prefix rescue | unplastic | 0 (absent) | - | not run | - | - | - | OK | learned; '[rigid](../../../data/traits/instructions/rigid.json)' |
| K4 Allport 1.5-2.5 (allport_probe, not run) | mucked | 2.13 | - | not run | - | - | - | OK | real; not of character |
| K4 Allport 1.5-2.5 (allport_probe, not run) | overacting | 2.05 | - | not run | - | - | - | OK | real; trait reading (histrionic) |
| K4 Allport 1.5-2.5 (allport_probe, not run) | palpitating | 1.79 | - | not run | - | - | - | OK | real; physical state |
| K4 Allport 1.5-2.5 (allport_probe, not run) | docility | 1.80 | - | not run | - | - | - | OK | noun of docile |
| K4 Allport 1.5-2.5 (allport_probe, not run) | jejune | 1.64 | - | not run | - | - | - | OK | learned; trait reading ([naive](../../../data/traits/instructions/naive.json)) |
| K4 Allport 1.5-2.5 (allport_probe, not run) | leaden-hearted | 2.40 | - | not run | - | - | - | OK | transparent; gloomy |
| K4 Allport 1.5-2.5 (allport_probe, not run) | dinged | 2.31 | - | not run | - | - | - | OK | real; not of character |
| K4 Allport 1.5-2.5 (allport_probe, not run) | fleshing | 2.25 | - | not run | - | - | - | OK | real; not of character |
| K4 Allport 1.5-2.5 (allport_probe, not run) | chittering | 1.78 | - | not run | - | - | - | OK | real; a sound |
| K4 Allport 1.5-2.5 (allport_probe, not run) | doctrinally | 1.85 | - | not run | - | - | - | OK | real; an adverb |
| K5 Allport >= 2.5 | desirous | 2.54 | - | states (state) | - | - | unreviewed | OK | - |
| K5 Allport >= 2.5 | self-contented | 2.96 | - | trait | - | new | unreviewed | OK | - |
| K5 Allport >= 2.5 | unsafe | 3.67 | - | trait | - | new | unreviewed | OK | - |
| K5 Allport >= 2.5 | dreading | 2.99 | - | states (state) | - | - | unreviewed | OK | - |
| K5 Allport >= 2.5 | night-eyed | 3.96 | - | not run | - | - | - | OK | transparent |
| K5 Allport >= 2.5 | two-sided | 3.94 | - | turned_away (stretched) | - | - | unreviewed | OK | - |
| K5 Allport >= 2.5 | radiant | 3.49 | - | states (state) | - | - | unreviewed | OK | - |
| K5 Allport >= 2.5 | sterilized | 2.89 | - | not run | - | - | - | OK | - |
| K5 Allport >= 2.5 | strained | 3.53 | - | states (state) | - | - | unreviewed | OK | - |
| K5 Allport >= 2.5 | ill-favored | 3.77 | - | physical (physical) | - | new | unreviewed | OK | - |
| K6 rare pilot | swith | 1.36 | - | turned_away (no_persona_reading) | known | - | unreviewed | FP | archaic 'quickly'; M1 turned it away |
| K6 rare pilot | naysaying | 1.42 | - | trait | known | new | unreviewed | OK | - |
| K6 rare pilot | distractive | 1.22 | - | trait | known | new | unreviewed | OK | - |
| K6 rare pilot | wordmonger | 0 (absent) | - | trait | known | new | unreviewed | OK | learned |
| K6 rare pilot | benumbed | 1.31 | - | states (state) | known | - | unreviewed | OK | learned; a state |
| K6 rare pilot | putrescent | 1.17 | - | turned_away (stretched) | known | - | unreviewed | OK | learned; not of character |
| K6 rare pilot | lummox | 1.31 | - | trait | known | new | unreviewed | OK | - |
| K6 rare pilot | forehanded | 0 (absent) | - | trait | known | new | unreviewed | OK | learned |
| K6 rare pilot | lissom | 1.24 | - | physical (physical) | known | new | unreviewed | OK | learned; physical |
| K6 rare pilot | italicizing | 1.13 | - | turned_away (stretched) | known | - | unreviewed | OK | real; an act |

The pool sizes the strata were drawn from: K1 251, K2 520, K3 863, K4 2,314, K5 4,746, K6 104.

## 5. Rates

The intervals are Wilson 95% intervals on the sample; the implied counts scale them to the pool.

| quantity | sample | rate | 95% interval | implied over the pool |
|---|---|---:|---|---|
| **U false negatives, strict (T)** | 18 / 120 | 15.0% | 9.7-22.5% | 842 (545-1,263) of 5,614 |
| U false negatives, broad (T + T-L) | 22 / 120 | 18.3% | 12.4-26.2% | 1,029 (696-1,471) |
| U strict FN carrying a concept not already submitted or in the corpus | 2 / 120 | 1.7% | 0.5-5.9% | 94 (28-331) |
| U strict FN, column I only | 10 / 32 | 31.2% | 18.0-48.6% | 385 (222-599) of 1,233 |
| U recognisable at all (T + R) | 44 / 120 | 36.7% | 28.6-45.6% | 2,058 (1,606-2,560) |
| U recognisable, including learned (T, T-L, R, L) | 52 / 120 | 43.3% | 34.8-52.3% | 2,433 |
| U archaic, dialect, technical or nonce (O + T-N) | 68 / 120 | 56.7% | 47.7-65.2% | 3,181 |
| **B false negatives, broad (T + T-L)** | 16 / 60 | 26.7% | 17.1-39.0% | 358 (229-523) of 1,341 |
| B false negatives, strict (T) | 4 / 60 | 6.7% | 2.6-15.9% | 89 (35-213) |
| B real words (all but O and T-N) | 48 / 60 | 80.0% | 68.2-88.2% | 1,073 |
| B, M1 reference: the rare pilot, judged trait | 62 / 104 | 59.6% | 50.0-68.5% | (a model verdict; it over-accepts stretched readings) |
| **Kept false positives (FP), all strata** | 4 / 60 | 6.7% | 2.6-15.9% | - |
| kept FP, K3 negating-prefix rescue of unknown words | 3 / 10 | 30% | 10.8-60.3% | 259 (93-520) of 863 |
| kept FP, K6 rare pilot | 1 / 10 | 10% | 1.8-40.4% | about 10 of 104 |
| kept FP, K1, K2, K4, K5 | 0 / 10 each | 0% | 0-27.8% | - |

How the strict false negatives of U are covered elsewhere.  The agent checked each against the census table and
the corpus (932 traits):

| word | covered by |
|---|---|
| overbrooding | brooding (submitted) |
| semidramatic | [melodramatic](../../../data/traits/instructions/melodramatic.json) (corpus) |
| envyful | [envious](../../../data/traits/instructions/envious.json) (corpus) |
| sphinxlike | enigmatic, inscrutable (submitted) |
| cajoler | cajoling (submitted) |
| mopy | moping (submitted) |
| peacocky | vain, cocky (submitted) |
| schemeful | [scheming](../../../data/traits/instructions/scheming.json) (corpus) |
| mesmerizable | suggestible (submitted) |
| self-depreciative | [self-deprecating](../../../data/traits/instructions/self_deprecating.json) (corpus) |
| charlatanish | charlatan (submitted) |
| chuckleheaded, beefhead | thickheaded (submitted) |
| indeflectible | [inflexible](../../../data/traits/instructions/inflexible.json) (corpus), unswerving (submitted) |
| belittler | disparaging (submitted) |
| flourishy | flamboyant (submitted) |

Teasable (nearest: touchy, [thin-skinned](../../../data/traits/instructions/thin_skinned.json)) and
gesticulative (nearest: [expressive](../../../data/traits/instructions/expressive.json)) are the two the agent
could not match.

## 6. Further evidence

### 6.1 The TDA as a natural experiment for the unknown rule

The TDA is exempt from the floor, so the agent applied the rule to it as a test.  **159 TDA words** are in neither
`wordfreq` nor OEWN, so they would be `unknown_word` if they were Allport-only.  Another 92 would be
`below_hard_reject`.  For these words the raters' familiarity says whether people know them:

| TDA class (by the dictionary floor) | words | `prop` median | `prop` ≥ 0.5 | M1 trait | M3 new / covered | Roger's review |
|---|---:|---:|---:|---:|---|---|
| would be `unknown_word` | 159 | 0.70 | 78% | 152 (96%) | 89 / 64 | 4 accepted, 17 merged, 0 rejected, 138 unreviewed |
| would be `below_hard_reject` | 92 | 0.77 | 82% | 86 (93%) | 54 / 33 | 10 merged |
| rescued by negating prefix | 244 | 0.68 | 76% | 232 (95%) | 118 / 116 | 10 merged |
| probe band 1.5-2.5 | 520 | 0.68 | 72% | 473 (91%) | 275 / 213 | 7 accepted, 47 merged |
| Zipf ≥ 2.5 | 1,803 | 0.84 | 93% | 1,583 (88%) | 750 / 912 | 27 accepted, 84 merged, 1 rejected |

The would-be unknown words are mostly productive derivations: overtalkative (0.94), unswayable (0.94),
frightenable (0.93), overcaring (0.93), restrainable (1.00).  Roger **accepted** four of them: restrainable,
irrestrainable, overmasculine and overdiligent.  So absence from `wordfreq` and OEWN is **not a familiarity
test** for derived person words.

132 of the 159 are also in Allport-Odbert, and 152 carry the TDA's GN1710 flag (Goldberg and Norman's 1,710).
The Allport-only unknown words are what remained after Norman and Goldberg selected the familiar ones, which
explains their lower yield (U: 15% strict, mostly variants).  **The rule is fine for this residual list because
of that selection, not because of what the rule tests.**  Applied to another list, such as an `--extra-list`
or a later census, it would cut familiar words.

### 6.2 Zipf does not predict trait-hood inside the census

M1 trait share by Zipf band (registry; M1 is a model verdict):

| run | Zipf < 1.5 | 1.5-2.5 | 2.5-3.5 | ≥ 3.5 |
|---|---|---|---|---|
| TDA | 470 / 495 (95%) | 473 / 520 (91%) | 847 / 933 (91%) | 736 / 870 (85%) |
| Allport, `allport_hi` | - | - | 1,015 / 2,110 (48%) | 804 / 1,536 (52%) |
| Allport, IV pilot | 22 / 40 (55%; all negating-prefix) | 19 / 52 (37%) | 28 / 61 (46%) | 17 / 49 (35%) |
| Allport, rare pilot | 62 / 104 (60%) | - | - | - |

Yield per submitted word, M3 "new" (registry fold of 2026-10-12, which includes the later physical and states
passes): TDA 1,286 / 2,818 (46%), rare pilot 48 / 104 (46%), IV pilot 82 / 202 (41%), `allport_hi` 1,276 /
3,646 (35%).  The rare words do at least as well as the frequent ones.  The coordinator read the rare pilot the
same way ("good value", [batches_pilot_readout_2026-10-09.md](../../trait_gap_generation/batches_pilot_readout_2026-10-09.md)
§ 2).  M1 is generous on Allport words (the same readout, on column IV: "this is where Haiku 5.5
over-accepts"), so the agent's B rate (27% broad) is the more conservative figure.

### 6.3 The probe band on census words

1,210 census rows carry a probe block (1,181 Haiku 5.5, 21 Haiku 4.5, 8 Sonnet 5.5), and 7 were "not known".
Two of the seven are arguably wrong.  **unforseeing**, a TDA word with raters 0.72, is a misspelling of
unforeseeing, a trait.  **chuffy** is a real British word.  The other five (pitch-kettled, bonte, competitory,
underogatory, dissensualized) are fair calls.

The probe was 770 of the TDA batch's 31,530 Haiku calls, about $0.05 of its $7.12
([usage.json](../../../data/candidates/filter/2026-10-10-tda_censuses/usage.json)).  It is a cheap near no-op;
nothing to change.

### 6.4 Defects and reporting gaps

- **F3, a rescue defeated by an earlier free floor reject.**  The registry row `irresolute#1` was first created
  by `antonym_check` (batch `m3_pilot_antonym_check`).  That generator is not curated, so the row got a free
  floor reject at Zipf 1.49.  The TDA run (prop 0.67, OEWN gloss hint) merged into the row
  ([registry.py:447-453](../../../assistant_axis/gapgen/registry.py)).  The TDA's M1 run selected only unfiltered rows ([traithood_filter.py:412](../../../data_analysis/gap_generation/traithood_filter.py),
  [registry.py:573-574](../../../assistant_axis/gapgen/registry.py)), so the census rescue (`freq_platform.rescue = gloss_hint`) never applied.  The word
  stays `turned_away`, cause `floor`.

  The same fate waits for **sybaritic** (1.47, gloss hint) and **restrictionist** (1.15, curated). Both are in
  the `allport_rare` pool and both already floor-rejected under `antonym_check`.  The registry holds 14 free
  floor rejects in all, all from `antonym_check`, so the exposure is small.  But the mechanism is general:
  whichever generator reaches a stem first decides its floor.
- **F4, `tda_cut` is a literal.**  [report.py:70](../../../assistant_axis/gapgen/generators/censuses/report.py) writes `"tda_cut": 0` into every run's evaluation.  Since
  irresolute it is untrue for the TDA run, and nothing in the evaluation counts registry rows of the run with
  `filter.cause == "floor"`.
- **F5, stale stage pools in the floor block.**  The floor block's `allport_only_eligible` ([report.py:73](../../../assistant_axis/gapgen/generators/censuses/report.py)) gives
  the table's pre-split pools (`allport_hi` 4,746, `allport_probe` 3,438).  After the column IV split the stages
  hold 3,646 and 2,525, plus 2,013 in `allport_iv`.  The run readouts repeat the pre-split figures (for
  example the rare pilot's [readout.md](../../../data/candidates/runs/censuses/2026-10-09-rare-pilot/readout.md),
  "Allport-only words in later stages").
- **F6, the in- rescue is not checked for negation.**  About 14 of the 87 Allport words rescued through in- are
  not negations: incaged, incrusted, insnared, inspirited, intrenching, intumescent, inwrapped and others.  They
  reach the probe stage on a false premise.  Harmless at about half a cent each.

### 6.5 Why the unknown words are unknown

Counts over all 5,614, from mechanical checks (`wn.morphy`, affix stripping, the Roget texts):

- **384 are inflected forms of an OEWN lemma** (leaguing, chicaning, noosing, embrangled).  The ingest's OEWN
  lookup has no lemmatiser.
- **1,423 are an affix on a base with Zipf ≥ 3**: over- 190, -less 174, -ish 162, -ing 141, out- 108, be- 83,
  -able 79, -ful 76, mis- 69.  The negating-prefix rescue covers only un-, in- and non-, so these get no rescue.
- **Closed compounds lose to their hyphenated spelling.**  `wordfreq` scores sphinx-like at 3.0 and sphinxlike
  at 0.
- **356 occur in a Roget text**: real, often archaic.
- **Transcription errors** remain (sychophantish, titvated).  The narrowed repair (QUESTIONS 35) fixes only
  doublings and vowel insertions.

In the U sample these routes do not separate the false negatives well.  The 59 sampled words flagged by a
lemma, an affix base at Zipf ≥ 3 or a compound hold 11 of the 18 strict false negatives.  A free rule-based
rescue would send half the list to recover about 60% of a set that is mostly redundant anyway.

## 7. Verdict

**Doing what was intended, but improvable.**

- **`below_hard_reject` on a curated list: mostly not doing what decision 1 intended, and already fixable as
  decided.**  The floor's stated job is to remove dictionary junk for free.  On known Allport words it removes
  real words (80%), a quarter of them trait words, at a rate M1 and M3 find at least as productive as the
  frequent words.  The data do not support the 1.5 line for this generator.  The generator's own familiarity
  scale (the TDA's `prop`) shows that, within the census, frequency below 1.5 does not mark unknown words.
  Rule 1b, route 3, already encoded this.  Roger's `allport_rare` stage applies it, but 927 words wait behind
  the order "rare last", and the 310 column-IV-only words below the floor are tied to the column IV decision.
- **`unknown_word`: doing what was intended, about as well as possible.**  Its premise holds for this residual
  list (57% archaic or dialect).  Its word-level loss (15% strict) is almost entirely redundant at the concept
  level (1.7%).  Its mechanism is a poor familiarity test (section 6.1), so it should not be reused on a list
  that has not been through a human familiarity selection.  For this list it should depend on the Allport
  column, not on Zipf: column I holds 10 of the 18 strict false negatives.
- **Kept false positives** (7%), concentrated in the negating-prefix rescue, cost cents and are caught by M1.
- **The probe band** discards almost nothing for census words.
- **F3 is a real, if small, loss path** that the evaluation cannot see (F4).

## 8. Proposals

| # | proposal | cost | expected change | evidence that would settle it |
|---|---|---|---|---|
| P1 | Run the rest of `allport_rare` (927 words, batches), before `allport_iv`'s remainder; decide the 310 column-IV-only words below the floor with column IV | about $6 (the rare pilot cost $0.67 for 104 words in M1 and M3) | the broad false-negative pool of B goes from deferred to judged: about 250 trait words in the 927 at the sample's 27% (about 360, 230-520, over all 1,341) reach M1, including [neopagan](../../../data/traits/instructions/neopagan.json) (corpus, column I, Zipf 1.22) | the pilot already gives M1 60% trait and M3 46% new per word; Roger's reading of the pilot's new words in the review app (batch `review_allport_pilots_1`) |
| P2 | Fix F3.  When a source with a rescue route (curated generator, gloss hint, familiarity ≥ 0.5) joins a row whose filter has `cause == "floor"`, recompute the row's `freq` with the new context and clear the free reject, so that `--run` picks it up.  Or make the `--run` selection include rows whose stored floor reject the current sources would rescue.  Unit test with a fake registry: a non-curated hard reject, then a census source, then the row is selected and probed | code $0; re-filtering irresolute, and sybaritic and restrictionist when P1 runs, about $0.02 | recovers 1 TDA trait word now and 2 later; closes the order dependence for every future curated stage | the 14 `antonym_check` floor rejects; a registry scan after the fix should show no row with a census source and `cause == "floor"` |
| P3 | Make the evaluation count registry floor cuts: replace the literal `tda_cut: 0` (F4) with the number of the run's rows whose filter has `cause == "floor"`.  Report post-split stage pools (F5) | $0 | the evaluation reports irresolute | - |
| P4 | Keep the `unknown_word` rule (Roger's Q34 stands on this sample).  If a measurement is wanted, a 5% systematic pilot (`every_nth` 20 over the unknown pool, 281 words) through M1 and M3, read against this sample's 1.7% unique-concept estimate.  Column I alone (1,233 words, 31% strict false negatives) is the better target if anything is sent.  Note that the unknown words are in no stage, so either needs a small stage or an `--extra-list` | pilot about $1.5-1.8 (batches); column I about $6-8; the whole list about $28-36, over the $20 line | at most about 90 (30-330) new concepts in the whole list; most M3 "new" calls would be variants that M1 reads generously | M3 "new" on the pilot, and Roger's merges in review: if most "new" merge into existing traits, the rule is confirmed |
| P5 | Record the OEWN lemma (via `wn.morphy`) as a field in the census table, without changing eligibility, so that "unknown" no longer covers the 384 inflected forms | $0 | none in outcomes (they are mostly column II acts); the label becomes honest | - |
| P6 | Leave F6 and the probe band as they are | $0 | - | - |

No proposal changes the 1.5 value itself.  It is still right for dictionary walks (decision 1's derivation),
and the census already bypasses it where the data say it should.
