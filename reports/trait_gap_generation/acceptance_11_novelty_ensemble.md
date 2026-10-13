# Acceptance report: workstream 11, lexical recall insurance for M3

Written 2026-10-13 by the Opus coding agent for Roger, against
[coding_plan_11_novelty_ensemble.md](./coding_plan_11_novelty_ensemble.md) (both open decisions approved by Roger
on 2026-10-13 as recommended: the pilot judges every lexical-only pair, and Roger blind-marks up to 40 covers before
the integration is built).  Built in the worktree on branch `plan11-build`; **no paid call and no download was
made** (the coordinator runs both from the main checkout, in the order of the last section).  Terms: the
[glossary](./glossary.md), whose new section "Lexical recall terms" defines
[lexical link](./glossary.md#lexical-link), [lexical neighbour](./glossary.md#lexical-neighbour),
[lexical-only pair](./glossary.md#lexical-only-pair), [retroactive sweep](./glossary.md#retroactive-sweep),
[lexical cover](./glossary.md#lexical-cover), [name-only link](./glossary.md#name-only-link) and
[stem family](./glossary.md#stem-family).  *M3* is the novelty check, *covered* / *new* its decisions
([retrieve, then judge](./glossary.md#retrieve-then-judge)); *OEWN* is Open English WordNet.

## Where things stand

| plan task | state |
|---|---|
| 1. `setup_external.py --moby` and the Moby loader | **built and tested on a fixture**; the download itself is the coordinator's (24,853,275 bytes from `www.gutenberg.org`) |
| 2. [lexical.py](../../assistant_axis/gapgen/lexical.py), `BLOCKS` gains `lexical`, `build` | **built, tested, run** on OEWN: [lookup.json](../../data/candidates/lexical/lookup.json) |
| 3. `build`, `labelled`, `dry`; `sweep_plan`, `labelled_measurement` | **built, tested, run**: [dry_readout.md](../../data/candidates/lexical/dry_readout.md), [labelled_readout.json](../../data/candidates/lexical/labelled_readout.json); gate 1's figures below |
| 4. `sweep`, `report`; `run_sweep`, `lexical_block`, the registry write | **built, tested** (fake clients), **dry run made**: estimate $2.92 live |
| 5. the paid pilot (= the sweep), the readout, **Roger's marks** | **waits**: the coordinator's paid run; the marks sheet is built (`lexical_recall.py marks`) and is written from the sweep's results |
| 6-8. the integration (`--lexical-search`), R1's edges and flags, the recovery check | **not built: they wait on Roger's marks** (the plan builds them "only past the gate") |
| 9. glossary entries, this report, the proposed README and AGENT_NOTES text | **done** (the proposals are at the end; neither file was edited) |

## What was built (against § 5)

- [lexical.py](../../assistant_axis/gapgen/lexical.py) (new): the constants of § 5; `OewnLexicon` (through
  `wordnet.oewn()`, cached per form and synset), `MobyLexicon` (the parser reads [mthesaur.txt](../../data/external/moby/mthesaur.txt)'s (not there yet) comma rows, a quoted
  comma, a trailing comma, a Gutenberg header if a copy has one), `label_forms`, `is_placeholder`, `affix_pairs`,
  `live_queue_entries` (M3's queue selection, with or without a text), `build_lookup`, `Lookup.neighbours`,
  `Lookup.antonym_evidence`, `Lookup.family` / `family_links`, `save_lookup` / `load_lookup` (a stale lexicon
  version is refused), `fetch_moby` (the IPIP download convention: `.part` then rename, sha256 and size of the bytes
  received, a git-ignored [DOWNLOAD_MANIFEST.json](../../data/external/moby/DOWNLOAD_MANIFEST.json) (not there yet) and the tracked
  [sources_manifest.json](../../data/candidates/lexical/sources_manifest.json), not there yet), and
  `labelled_measurement`.
- [lexical_sweep.py](../../assistant_axis/gapgen/lexical_sweep.py) (new): `sweep_plan`, `row_rules` (each row's own
  rule set and cut-off), `cap_items`, `sweep_estimate`, `run_sweep` (Sonnet then Opus through
  `NoveltyRunner.read_pairs`, each pair under its row's cut-off: a `SweepCandidate` carries it), `lexical_block`
  and its flags, `dry_readout` / `dry_markdown`, `sweep_report` / `sweep_markdown`, and Roger's marks:
  `marks_sheet`, `parse_marks_markdown`, `fold_marks`.
- [lexical_recall.py](../../data_analysis/gap_generation/lexical_recall.py) (new): `build`, `labelled`, `dry`,
  `sweep`, `report`, plus `marks` (the sheet, and `--parse` of the marked sheet) and `replay` (the sweep's
  [registry_writes.jsonl](../../data/candidates/lexical/sweep/2026-10-14-lex_sweep_1/registry_writes.jsonl) (not there yet) applied to another checkout's registry, idempotently).
- [setup_external.py](../../data_analysis/gap_generation/setup_external.py): `--moby [--dry-run]`.
- [registry.py](../../assistant_axis/gapgen/registry.py): one line, `BLOCKS` gains `lexical` (not `ROW_FIELDS`, so
  a new row is byte for byte as before).  Plan 12's build adds `persona` to the same tuple: a one-line merge.
- Tests (new): [test_gapgen_lexical.py](../../assistant_axis/tests/test_gapgen_lexical.py),
  [test_gapgen_lexical_sweep.py](../../assistant_axis/tests/test_gapgen_lexical_sweep.py),
  [test_gapgen_lexical_acceptance.py](../../assistant_axis/tests/test_gapgen_lexical_acceptance.py),
  [test_gap_generation_lexical_cli.py](../../data_analysis/tests/test_gap_generation_lexical_cli.py).
- Not built (tasks 6-7, waiting on the marks): the [novelty.py](../../assistant_axis/gapgen/novelty.py), [novelty_runner.py](../../assistant_axis/gapgen/novelty_runner.py),
  [novelty_score.py](../../data_analysis/gap_generation/novelty_score.py) and
  [review_graph.py](../../assistant_axis/gapgen/review_graph.py) changes of § 5, and their tests
  [test_gapgen_novelty_lexical.py](../../assistant_axis/tests/test_gapgen_novelty_lexical.py) and
  [test_gapgen_review_graph_lexical.py](../../assistant_axis/tests/test_gapgen_review_graph_lexical.py) (neither there yet).

## Deviations, with reasons

1. **More pairs than the plan counted: 944 on 596 rows, not 821 on 561** (QUESTIONS 131).  A bare lemma also reaches
   the standards-derived traits and queue entries that carry it with a suffix (`agreeable` reaches
   [agreeable](../../data/traits/instructions/agreeable.json),
   [agreeable (Big Five)](../../data/traits/instructions/agreeable_big_five.json) and
   [agreeable (HEXACO)](../../data/traits/instructions/agreeable_hexaco.json)): 125 pairs.  The other 819 are the
   plan's 821 within two.  I kept them as targets (the overlap call decides); the estimate rises from $2.0-2.6 to
   **$2.28-2.92**.
2. **The build line on the marks** (QUESTIONS 132): "about 36 or more confirmed" assumes 40 covers; with fewer, the
   report reads it as 90% of the marked covers confirmed and at least 5 confirmed.  Roger decides.
3. **A `lexical` block only where there is something to record** (QUESTIONS 133): on rows with a lexical-only link,
   antonym evidence or a stem family; each appended registry row is about 17 KB.  The block also lists the links M3
   had already listed (`listed_by_m3: true`, unjudged), so R1 sees the whole picture.  A resumed or repeated sweep does not rewrite a block that has not changed, and each
   block's spend is counted from all of the run's response records, an earlier session's included.
4. **Two subcommands beyond § 7**: `marks` (the blind-marks sheet in the cover audit's form, and `--parse`), and
   `replay` (the plan's "replayed there from `registry_writes.jsonl`").  `sweep` gained `--no-registry-write`,
   `--show KEY>STEM` (render a chosen pair) and `--lexicons` (only some lexicons' links); `dry` gained `--lexicons`.
5. **The negation-affix rule's bare `a-` needs five letters after it** (QUESTIONS 135): `ashy` is not the opposite of
   `shy`.
6. **An antonym found both ways is one entry**: OEWN's link keeps `link: antonym` and records the affix `rule`.
7. **This report's name** is `acceptance_11_novelty_ensemble.md`, as the coordinator asked; § 11 of the plan named it
   `acceptance_11_lexical_recall.md`.
8. Links are read from the candidate's side only, as the plan's dry lookup did (QUESTIONS 134); OEWN's "see also"
   is one-way.

## The § 8 commands

Run in the worktree as `VIRTUAL_ENV= uv run --extra dev python -m pytest ...` (plain `uv run pytest` picks up the
main checkout's environment).

```
uv run pytest assistant_axis/tests/test_gapgen_lexical*.py assistant_axis/tests/test_gapgen_novelty_lexical.py assistant_axis/tests/test_gapgen_review_graph_lexical.py data_analysis/tests/test_gap_generation_lexical_cli.py -q
```
**46 passed, 1 skipped** (the files that exist; `test_gapgen_novelty_lexical.py` and
`test_gapgen_review_graph_lexical.py` belong to tasks 6-7, not built).  The skip is the recorded-sweep acceptance
test, parametrised over sweeps that do not exist yet.

```
uv run pytest -q assistant_axis/tests data_analysis/tests
```
**4,984 passed, 55 skipped**, exit 0, in 15.6 minutes (the 55 skips are the suite's own, data or models not
present in the worktree; the lexical files were edited after this run started and pass in their own final run
above, with the registry tests: 75 passed, 1 skipped).

```
uv run python data_analysis/gap_generation/rubric_pins.py check      # exit 0: no pin moved
uv run python data_analysis/check_arrangements.py --quiet            # exit 0
uv run python tools/sync_entity_lists.py --check                     # exit 0: both lists up to date
git status --porcelain data/traits data/roles data/seed_queue.json   # empty
```

## Moby

Not downloaded here (the coordinator's step).  A HEAD request and two 1.5 KB range reads on 2026-10-13 confirmed the
source: `https://www.gutenberg.org/files/3202/files/mthesaur.txt`, **24,853,275 bytes**, last modified 2025-08-23,
plain comma-separated rows (head first), CRLF line ends, no header, no quotes; the parser's fixture follows that
form.  The manifest line (size, heads, sha256, URL) is printed by the download and lands in
[sources_manifest.json](../../data/candidates/lexical/sources_manifest.json) (not there yet).  The sandbox's network
filter needed `www.gutenberg.org` named for those requests.

## The lookup table (OEWN 2024 only, until Moby is fetched)

[lookup.json](../../data/candidates/lexical/lookup.json), content sha256 `9a838401a523`, lexicon `oewn:2024`
(`wn` 1.1.1): **corpus labels 699 of 932** (the plan's figure); live queue entries 95 of 122, of which **31 of the 38
with a text** (the plan's) and 84 text-less entries that can give only name-only links.

## The labelled pairs (OEWN; [labelled_readout.json](../../data/candidates/lexical/labelled_readout.json))

Over M2's [labelled_pairs.json](../../data/candidates/calibration/labelled_pairs.json); a pair abstains when either
side is not in OEWN; rates are over the pairs with both sides found.

| relation | pairs | both found | abstain | synonym / similar / also | antonym / affix | rate |
|---|---|---|---|---|---|---|
| duplicate | 79 | 57 | 22 | 4 / 9 / 3 (16) | - | recall 28.1% |
| antonym | 286 | 211 | 75 | - | 52 / 6 (58) | recall 27.5% |
| near-distinct | 34 | 20 | 14 | 1 / 0 / 0 | 1 / 0 | false flags 10.0% (2 of 20) |
| unrelated | 2,000 | 1,330 | 670 | 1 / 3 / 1 | 0 / 0 | false flags 0.4% (5 of 1,330) |
| polysemy reject | 5 | 5 | 0 | 5 / 0 / 0 | - | all linked, by word, as expected |
| deliberate duplicate | 3 | 0 | 3 | - | - | - |

The plan's dry figures hold: about a quarter of duplicates and antonyms reached, false flags well under 1% on
unrelated pairs.  A narrow net with a clean mesh.

## The dry readout (gate 1, $0; [dry_readout.md](../../data/candidates/lexical/dry_readout.md))

- **Kept rows** (M3 `new` or `grey`): 4,091 (trait 3,843, physical 126, states 122; 2,981 single words, 1,110
  phrases; cut-off 3: 2,971, 4: 1,120; rule set 3: 4,015, rule set 2: 76); 2,618 found in OEWN.
- **Lexical-only pairs: 944 on 596 rows** (555 single words); synonym 292, similar 567, also 85; corpus 851, queue
  93; by cut-off band: 3 at alignment 0-1: 581, 3 at alignment 2: 105, 4 at alignment 3: 258; by pass: trait 896,
  physical 24, states 24.  **925 judgeable**; 19 name-only.  566 further links were already listed by M3.  125 go
  to a standards-derived trait, 48 reach a trait through its `renamed_from`.  Their cosines are low, as expected
  of pairs the embedding did not retrieve: median 0.13, 90th percentile 0.24.
- **Antonym evidence**: 94 kept rows; 50 have an OEWN antonym that is a corpus trait, 21 of them a trait with no
  pair partner; 18 of the 94 also carry M3's `pair_completion_for`, 12 naming one of the same traits.
- **Stem families**: 447 kept rows have a family member (affix 404, derivation 73); 178 groups of kept rows tie
  each other (largest: corrupt, corruptible, incorrupt, incorruptible).
- **Free labels**: of the rows with pairs, Roger merged 53 in review, 23 into a corpus trait, and **2 into the
  lexically linked trait**: `pleasant#1` → [agreeable](../../data/traits/instructions/agreeable.json) (OEWN "also")
  and `annoying#1` → [disagreeable](../../data/traits/instructions/disagreeable.json) ("similar"), both on the gate
  audit's list of five retrieval misses ([m3_novelty.md](../code_review_2026-10-12/gate_audits/m3_novelty.md)
  § 7.2).  Delightful, nice and unsteadfast have no OEWN link to their traits
  ([agreeable](../../data/traits/instructions/agreeable.json),
  [submissive](../../data/traits/instructions/submissive.json)); nice's links are the "fastidious" sense:
  [squeamish](../../data/traits/instructions/squeamish.json),
  [fastidious](../../data/traits/instructions/fastidious.json),
  [precise](../../data/traits/instructions/precise.json) and [good](../../data/traits/instructions/good.json).
- **Gate 1**: the two known cases are reached (hard, and asserted by
  [test_gapgen_lexical_acceptance.py](../../assistant_axis/tests/test_gapgen_lexical_acceptance.py)); the pair count
  is inside the cap.
- **The sweep's estimate** (`sweep --dry-run`): 925 Sonnet calls ($1.127) and Opus on 62% of them, ASSUMED until
  measured (574 calls, $1.791): **$2.92 live** ($2.28 at the full scan's 40%).  Moby's pairs come on top, capped:
  OEWN's pairs are all kept and Moby's are taken by cosine down to the $10 cap.

## The three rendered prompts (§ 7a)

The system prompt is rubric A, [overlap_concept.md](./rubrics/overlap_concept.md) v6 (sha256 `b3eff18fb946`),
unchanged; Sonnet 5.5, then Opus 5.5 where the row's rule sends the pair to it.  Rendered by `sweep --dry-run
--show` through the runner's own path (`overlap_test.render_single`, labels in the judge display form):

`obdurate#1` (kept at cut-off 4) and its OEWN synonym [unrepentant](../../data/traits/instructions/unrepentant.json),
never listed (a polysemy hit the call should turn away):

```text
{"target": {"label": "obdurate", "description": "This means holding one's position stubbornly and refusing to change one's mind or give in, even when presented with clear arguments or mounting pressure to yield."},
 "other": {"label": "unrepentant", "description": "This means shrugging off the harm one has done, feeling no guilt over it however bad it was, never apologizing, and seeing nothing to make right."}}
```

`activist#1` and [aggressive](../../data/traits/instructions/aggressive.json), reached through aggressive's old name
`militant`, which shares a synset with `activist`:

```text
{"target": {"label": "activist", "description": "This means devoting most of one's time and energy to organizing, speaking out, and pressing for a political or social cause, rather than merely holding sympathetic views about it."},
 "other": {"label": "aggressive", "description": "This means pushing for confrontation, forceful action and combative approaches to get what one wants, and rejecting compromise or peaceful solutions."}}
```

A new wave's relation call with the lexical neighbour [dominant](../../data/traits/instructions/dominant.json) in
`preponderating#1`'s list (the integration's prompt; rendered with `novelty.render_relation_user` and the seeded
order of a run named `2026-10-14-lex_pilot`, byte for byte the plan's sample; system prompt
[relation.md](./rubrics/relation.md) v1, Haiku 5.5):

```text
{"candidate": {"label": "preponderating", "description": "This means carrying more weight than anyone else in the room, so that one's views and wishes tend to win out in discussions and decisions."},
 "traits": [
  {"id": 1, "label": "overstepping", "description": "This means going beyond the authority one has been given, making decisions and taking actions that belong to others and crossing proper limits as a matter of habit."},
  {"id": 2, "label": "fat", "description": "This means carrying a lot of body fat: shopping the larger sizes, a tight fit in chairs with arms and airplane seats, and running warm in any weather."},
  {"id": 3, "label": "unsupported", "description": "This means having nobody in one's corner: no one to drive one home from the hospital, to lend the rent, to listen after a bad day, and carrying every load alone."},
  {"id": 4, "label": "dominant", "description": "This means taking control of conversations, steering discussions toward specific outcomes, and demonstrating assertive leadership in guiding others."},
  {"id": 5, "label": "Leo", "description": "This means carrying oneself like royalty: warm, generous and openhanded as a host, dignified and used to being in charge, loving the limelight, vain, and proud enough to be taken for conceited."},
  {"id": 6, "label": "slight", "description": "This means carrying little muscle on a light frame, whatever one weighs: narrow shoulders and thin wrists, a suitcase that takes both hands, and jar lids that will not budge."},
  {"id": 7, "label": "overmasculine", "description": "This means acting out macho swagger at every turn, dominating conversations and people, bragging of toughness, treating aggression as strength, and answering any hint of softness with scorn or a show of force."},
  {"id": 8, "label": "thin", "description": "This means carrying little body fat: shopping the smaller sizes, belts cinched to the last hole, room to spare in any seat, and feeling the cold before anyone else."},
  {"id": 9, "label": "muscular", "description": "This means carrying a lot of muscle, whether from the gym, years of lifting and hauling, or the build one was born with: broad shoulders, sleeves tight on the arms, and strength to spare."},
  {"id": 10, "label": "tall", "description": "This means standing a head above most people: ducking through old doorways, knees against the seat in front, being asked to reach the top shelf, and sleeves that never reach the wrist."},
  {"id": 11, "label": "short", "description": "This means standing a head below most people: a step stool for the top shelf, hems taken up on every pair of pants, and seeing only backs in a crowd."}
 ]}
```

Read for fit: the overlap rubric's "target" and "other" fit a pair whatever its source; the relation rubric's
"numbered list" and "the listed trait's id" hold with the longer list, and nothing marks where a trait came from.

## The sweep (gate 2): not run yet

To be filled from [sweep_report.json](../../data/candidates/lexical/sweep/2026-10-14-lex_sweep_1/sweep_report.json)
(not there yet) and the readout Fable writes,
[lexical_pilot_readout.md](./lexical_pilot_readout.md) (not there yet): the stop-rule figure first (covers at the
cut-off), the covers by link type, lexicon, cut-off band and pass, the below-cut readings, the precision proxies,
the Opus share measured, parse rates and cost per model from [usage.json](../../data/candidates/lexical/sweep/2026-10-14-lex_sweep_1/usage.json) (not there yet).

**Roger's marks** (manual check, never asserted by a test): the sheet
[lexical_covers_for_marks.md](./lexical_covers_for_marks.md) (not there yet; written by `marks` from the sweep's
covers, up to 40, shuffled, with both texts and no readings; key in [key.json](../../data/candidates/lexical/sweep/2026-10-14-lex_sweep_1/marks/key.json), not there yet) and his four
decisions of § 10: (a) stop or build tasks 6-8, (b) a review flag for below-cut hits, (c) flip the confirmed covers
now or leave them as flags for R1, (d) whether Moby stays.

**Waiting on the marks**: tasks 6-8 (the integration, R1's edges and flags, the recovery check including its free
reachability count), the byte-identity check of the switch, the per-wave cost with the switch on.

## Refusals and parse rates

The judging rule's new section (Sonnet 5.5 refuses "think first" reasoning fields) is respected: the sweep sends
rubric A's one-sentence reason form, which Sonnet 5.5 and Opus 5.5 answer, and a `refusal` stop reason is a failed
call: recorded in the sweep's [responses.jsonl](../../data/candidates/lexical/sweep/2026-10-14-lex_sweep_1/responses.jsonl) (not there yet) with its stop reason, asked once more, counted in the parse rate, and the pair
left `unparsed` with the `lexical_unparsed` flag (tested with a refusing fake client).

## Open QUESTIONS entries

[QUESTIONS.md](./QUESTIONS.md) 121-130 (the plan's pre-registered ten; 129 answered by Roger) and 131-136 (this
build's): 131 the pair count and estimate, 132 the build line on the marks, 133 which rows get a block, 134 a link's
direction, 135 the `a-` prefix, 136 what `partner_has_file` means.  126 and 127 wait on the marks.

## The coordinator's steps, in order (main checkout, after the cherry-pick)

1. **Moby download** ($0, 24.9 MB, network once; Roger's go is on record in the plan; the sandbox may need
   `www.gutenberg.org`):
   `uv run python data_analysis/gap_generation/setup_external.py --moby`
   Commit [sources_manifest.json](../../data/candidates/lexical/sources_manifest.json) (not there yet).
2. **Rebuild the table with both lexicons** ($0, seconds; the OEWN-only table is kept as `.bak.<UTC>`):
   `uv run python data_analysis/gap_generation/lexical_recall.py build`
3. **The labelled pairs and the dry readout again, with Moby** ($0, about a minute):
   `uv run python data_analysis/gap_generation/lexical_recall.py labelled` and
   `uv run python data_analysis/gap_generation/lexical_recall.py dry`
   The plan has Roger read the gate-1 readout and the rendered prompts above before any call.
4. **The sweep's dry run**: `uv run python data_analysis/gap_generation/lexical_recall.py sweep --batch-id
   2026-10-14-lex_sweep_1 --dry-run` (prints Moby's pairs and how many the cap cuts).
5. **The paid sweep** (live, cap $10; OEWN's 925 pairs about $2.3-2.9, Moby's on top inside the cap):
   `uv run python data_analysis/gap_generation/lexical_recall.py sweep --batch-id 2026-10-14-lex_sweep_1 --budget-usd 10`
   It writes the `lexical` blocks into the main checkout's registry; `--resume` finishes a stopped run with nothing
   answered sent again.  Commit `data/candidates/lexical/sweep/2026-10-14-lex_sweep_1/`.
6. **The marks sheet** ($0): `uv run python data_analysis/gap_generation/lexical_recall.py marks --batch-id
   2026-10-14-lex_sweep_1`; after Roger marks it, `... marks --batch-id 2026-10-14-lex_sweep_1 --parse
   reports/trait_gap_generation/lexical_covers_for_marks.md` and `... report --batch-id 2026-10-14-lex_sweep_1
   --marks data/candidates/lexical/sweep/2026-10-14-lex_sweep_1/marks/marks.json`.

## Proposed text (not edited: the platform owns these files)

For [data/README.md](../../data/README.md), in the trait-gap platform section:

> - **[`candidates/lexical/`](candidates/lexical/)** (tracked): workstream 11's lexical recall insurance for M3
>   ([coding_plan_11_novelty_ensemble.md](../reports/trait_gap_generation/coding_plan_11_novelty_ensemble.md)),
>   written by [`lexical_recall.py`](../data_analysis/gap_generation/lexical_recall.py): `lookup.json` (every corpus
>   trait and live seed-queue label in OEWN and Moby, with the lexicon versions and a content hash; `build`),
>   `labelled_readout.json` (the links on M2's labelled pairs; `labelled`), `dry_readout.{json,md}` (the lexical-only
>   pairs of every kept row, $0; `dry`), `sources_manifest.json` (the Moby download's record), and
>   `sweep/<batch_id>/` (the paid retroactive sweep: `plan.json` with a snapshot of every swept row's `novelty`
>   block, `pairs.jsonl`, `responses.jsonl`, `results.jsonl`, `registry_writes.jsonl`, `sweep_report.{json,md}`,
>   `usage.json`, `run.json`, `run.log`, and `marks/` with Roger's blind marks).  The sweep writes a `lexical` block
>   on the registry rows it reads and never touches their `novelty` block.
> - **`external/moby/`** (git-ignored): the Moby Thesaurus II (`mthesaur.txt`, Project Gutenberg #3202, public
>   domain, about 25 MB) and its `DOWNLOAD_MANIFEST.json`, fetched by `setup_external.py --moby`.

For [AGENT_NOTES.md](../../AGENT_NOTES.md), under "Gate audits and fixes", at the end of the *M3* item:

> Retrieval misses (§ 7.2 of the audit) are workstream 11's: a dictionary lookup
> ([`lexical.py`](./assistant_axis/gapgen/lexical.py)) lists every kept row's lexical neighbours that M3 never read,
> and a retroactive sweep (`lexical_recall.py sweep`, about $3) reads them under each row's own rule set, writing a
> `lexical` registry block beside the untouched `novelty` block; it reaches 2 of the audit's 5 misses (pleasant,
> annoying).  Letting a lexical neighbour cover in later waves (`novelty_score.py --lexical-search`) waits on
> Roger's blind marks of the sweep's covers.
