# Coding plan: workstream 11, lexical recall insurance for M3

Written 2026-10-13 (Fable) in the [PLAN_FORMAT.md](./PLAN_FORMAT.md) shape from
[11_novelty_ensemble.md](./11_novelty_ensemble.md) (rewritten 2026-10-10) with Roger's § 9 answers of 2026-10-12
(commit 7fb8318c; decisions), against M3 as built at commit 403cbd6a (rule set 3: the graded cut-off,
`renamed_before_queue`, the partner skip; [coding_plan_platform.md](./coding_plan_platform.md) "Interface as
built", [coding_plan_m3.md](./coding_plan_m3.md), the gate audit
[m3_novelty.md](../code_review_2026-10-12/gate_audits/m3_novelty.md)).  Terms: the [glossary](./glossary.md);
*covered* and *new* are M3's decisions ([retrieve, then judge](./glossary.md#retrieve-then-judge)), the
*relation call* and the *overlap call* its two LLM calls
([glossary](./glossary.md#relation-overlap-calls)).  Three terms this plan adds (glossary entries are task 9):
a **lexical link** is a dictionary's recorded tie between two words (here Open English WordNet's synonym,
"similar to", "also see" and antonym links, and a Moby thesaurus row); a **lexical neighbour** of a candidate is
a corpus trait or live seed-queue entry its label is linked to; a **lexical-only pair** is a candidate and a
lexical neighbour that M3's retrieval and expansion never listed, so no model has read the pair.  Roger's
review comments go into this file.

## Open decisions (Roger's, at plan review; labelled OPEN until decided; both decided 2026-10-13)

1. **Decided (2026-10-13, Roger): the pilot's scope: (a), every lexical-only pair.**  The workstream plan's § 8 judges "a sample of those pairs (~$1)".  The dry
   lookup (measured below) finds **821 lexical-only pairs on 561 kept rows** from OEWN alone, and the overlap
   call on all of them costs **about $2.0-2.6 live** (§ Cost).  Options: (a) judge every pair, so that the pilot
   *is* the retroactive sweep of § 3 step 4 and nothing is run twice; (b) a seeded sample of 300 (≈ $1) and the
   rest only past the gate.  **Recommendation: (a).**  Under the $20 line the batch-or-real-time rule says
   real time; a sample saves about $1.5 and costs a second run and a sampling design, and the full count is the
   stop rule's own input.
   **Roger (2026-10-13): recommendation approved.**
2. **Decided (2026-10-13, Roger): the stop rule's arbiter: (b), with Roger's blind marks.**  § 8 stops the plan "if the recorded batches show fewer than ~5 real
   misses".  Options: (a) a *real miss* is a lexical-only pair that reads at the row's own cut-off under the
   row's own rule set, counted by the machine; (b) the same, but Roger blind-marks up to 40 of them first, as in
   the cover audit ([m3_cover_audit_for_marks.md](./m3_cover_audit_for_marks.md); about 30 minutes), and the
   integration (§ 9 tasks 6-8) is built only if about 36 or more are confirmed.  **Recommendation: (b).**  The
   dry sample shows the lexicon's polysemy plainly (`productive` linked to
   [fat](../../data/traits/instructions/fat.json), `respectable` to
   [healthy](../../data/traits/instructions/healthy.json)); the overlap call is the sense filter, and its
   measured false-cover rate is about 3%, but the integration lets a lexical neighbour *cover* in every later
   wave, which is worth 30 minutes of marks once.
   **Roger (2026-10-13): recommendation approved.**

If either is unanswered when Opus reaches the step, it proceeds under the recommendation and records that in
[QUESTIONS.md](./QUESTIONS.md) (§ 12).

## Measured figures (2026-10-13; how, at the end of this section)

- **Registry** ([registry.jsonl](../../data/candidates/registry.jsonl), git-ignored, last line per key): 9,972
  lines, **9,949 keys**; M1 verdict `trait` on 6,743.  **7,084 rows carry a `novelty` block**: 4,090 `new`, 1
  `grey`, 2,993 `covered` (2,454 by the walk, 539 at stage 0: 493 corpus, 46 queue).  **6,930 blocks are under
  rule set 3** (`m3_rules_3`), 154 under rule set 2; all in `shortlist` mode.
- **The kept rows** (new or grey): **4,091**.  By cut-off: 2,971 at 3, 1,120 at 4.  By alignment score: 1,576
  at 0, 916 at 1, 482 at 2, 1,117 at 3.  2,981 single-word stems, 1,110 phrases.  Mean listed traits 16.6, mean
  pairs read 3.86.  Review: 3,913 unreviewed, 140 `merged_into`, 37 `accepted`, 1 `rejected`.  454 carry
  `pair_completion_for`.  2,700 were decided with the seed queue in the index.
- **The review build** ([review_traits_all_2/graph.json](../../data/candidates/review/review_traits_all_2/graph.json),
  2026-10-13 04:35-05:43 UTC, 28 M3 batches): **3,835 candidate terms** (3,834 new, 1 grey), 2,864 covered
  candidates greyed, 926 corpus and 78 queue nodes, 97,574 edges.
- **Corpus and queue**: 932 trait files (628 single-word labels, 304 phrases, 89 with a standard's suffix);
  [seed_queue.json](../../data/seed_queue.json) 972 trait entries, of which 84 `backlog` and 38 `candidate` are
  live; **only the 38 carry a text**, so M3's index holds 38 queue entries (`queue_traits` excludes the 84 as
  `no_text`), not the 119 Roger's answer 2 counts.
- **The lexicon on disk**: [wn.db](../../data/external/wn/wn.db), 112 MB, lexicon **`oewn:2024`** (the plan's
  "2025" is not installed; `wn` 1.1.1 in [uv.lock](../../uv.lock); `OEWN_LEXICON = "oewn:2024"` in
  [wordnet.py](../../assistant_axis/gapgen/wordnet.py)).  No Moby file under `data/external/`.
- **OEWN coverage** (the label found as any part of speech, hyphen and space variants tried, a standard's
  suffix dropped): corpus labels **699 of 932**; live queue entries with a text 31 of 38; kept rows **2,620 of
  4,091** (single-word 2,414 of 2,981; phrases mostly abstain).
- **The dry retroactive lookup** (links by word: the label's synsets' lemmas as *synonym*, the lemmas of
  their `similar` and `also` synsets; targets the 932 corpus stems with `renamed_from` folded and the 38 queue
  entries; "unlisted" = not in the block's `listed`, `readings` or `covered_by`): **561 kept rows (521
  single-word) have 821 lexical-only links** (synonym 242, similar 481, also 98; 747 to a corpus trait, 74 to a
  queue entry); 540 further links were already listed by M3.  Hit rows by cut-off: 412 at 3, 149 at 4; by
  alignment score 217 / 134 / 61 / 149.  **Antonyms**: 46 kept rows have an OEWN antonym that is a corpus trait,
  18 of them a trait with no pair partner.
- **A free label**: 53 of the hit rows are rows Roger merged in review; 23 of those into a corpus trait, and
  **2 into the lexically linked trait**: `pleasant#1` →
  [agreeable](../../data/traits/instructions/agreeable.json) and `annoying#1` →
  [disagreeable](../../data/traits/instructions/disagreeable.json), **both on the gate audit's list of the five
  retrieval misses** (§ 7.2 there: delightful, pleasant, nice, annoying, unsteadfast).  Nice, delightful and
  unsteadfast have no OEWN link to their trait.  The other 21 merges name a trait the lexicon did not link
  (autocratic → [dominant](../../data/traits/instructions/dominant.json), lexicon
  [authoritarian](../../data/traits/instructions/authoritarian.json)): the lexicon's hit is a sibling, which
  is what the overlap call is for.
- **The labelled pairs** ([labelled_pairs.json](../../data/candidates/calibration/labelled_pairs.json), schema
  1, 2026-10-02: 286 antonym, 79 duplicate, 34 near-distinct, 3 deliberate duplicate, 5 polysemy reject, 2,000
  unrelated; the workstream plan's "86 duplicate, 315 antonym, 553 near-distinct" are stale), dry: of the
  duplicate pairs with both sides in OEWN, **16 of 57 carry a synonym-like link** (synonym 3, similar 8, also 5;
  22 abstain); antonyms **52 of 211** carry an antonym link (75 abstain); near-distinct 2 of 22 linked;
  unrelated **5 of 1,334** linked (0.4%); the 5 polysemy rejects all linked, by word, as expected.  So the
  graph's recall is about a quarter and its false-flag rate well under 1%; it is a narrow net with a clean
  mesh.
- **M3's measured rates**: [TDA](../../data/candidates/novelty/2026-10-10-tda_censuses/summary.json) $9.44 for
  1,779 decided rows (overlap stage 91% of it; 4.7 pairs read and 17.4 listed per candidate);
  [Allport-hi](../../data/candidates/novelty/2026-10-11-allport_hi_censuses/summary.json) $9.44 for 1,704.
  Per pair live: Sonnet $0.0012, Opus $0.0031 (`OVERLAP_TOKENS` in
  [novelty_runner.py](../../assistant_axis/gapgen/novelty_runner.py)); the generator plans' sizing rate is M3
  $0.011 a passed word ([masked_lm/submit.py](../../assistant_axis/gapgen/generators/masked_lm/submit.py)).

**What this says about the yield.**  The audit's 106 false-new rows lost 5 to retrieval; the lexical graph
reaches 2 of those 5.  At the audit's rates (about 21% of kept rows false new, 4.7% of those retrieval misses)
the 4,091 kept rows hold about 40 retrieval misses, of which the graph can reach perhaps 15-20; the 821 pairs
will also surface covers that are coincidences of polysemy read at the cut-off (hence open decision 2).  So
the expected find is **about ten to twenty real covers**, above the plan's stop line of five, and small: this
is insurance, as the workstream plan says, at about $3 once and about $0.35 per thousand candidates after.

*How measured*: two scratch scripts (not kept; the `dry` and `labelled` commands of § 7 reproduce them): a
fold of the registry log (last line per key), the seed queue through `novelty.queue_traits`, the corpus
through `novelty.load_trait_corpus`, OEWN through `wordnet.oewn()` (`synsets(form)`, `Synset.lemmas()`,
`Synset.relations()["similar"|"also"]`, `Sense.relations()["antonym"]`), stems through
`normalize_to_file_name`; no API call.

## 1. Decisions already made

| decision | reason | source |
|---|---|---|
| **The lexicon is OEWN 2024 as installed** ([wn.db](../../data/external/wn/wn.db); `wn` 1.1.1); no second WordNet download.  The lookup table records the lexicon id and version. | one lexicon for the whole platform (M1's sense prior, the censuses' gloss hints, the Roget and WordNet walks, the masked-LM variant B all read `oewn:2024`); the plan's "2025" was to be checked, not assumed (§ 9.1 correction); an upgrade is Roger's call and would touch them all | measured; plan 11 § 9.1 |
| **Moby Thesaurus II is fetched** (about 25 MB, public domain, Gutenberg #3202) into `data/external/moby/` with a download manifest, through `setup_external.py --moby`.  Moby hits rank after OEWN hits; a Moby-only pair is judged only at [cosine](./glossary.md#cosine) 0.2 or above; Moby's precision is reported apart so it can be dropped. | Roger approved the download; Moby's synonymy is loose and Victorian (plan 11 § 4) | plan 11 § 2, § 4, § 9.1 |
| **Queue labels are looked up too**: every live trait entry (`candidate`, `ready`, `tbd`, `backlog`; `QUEUE_SEARCH_STATUSES`), the same selection as M3's search.  An entry with no text (the 84 `backlog` entries today) can only give a *name-only* link: recorded, shown in review, never judged (the overlap call needs a description) and never a cover. | Roger: yes (production dedup, not measurement); measured: only 38 live entries carry a text | plan 11 § 9.2; this plan |
| **Timing**: the dry lookup and the paid sweep run now, over recorded data; the flags are **held until the end-of-generation R1 pass** ([coding_plan_review.md](./coding_plan_review.md) § 10); the sweep **never flips an M3 decision**. | Roger agreed with the recommendation; cross-batch repetition is visible at the end | plan 11 § 9.3, § 3 step 4 |
| **A lexical hit that reads below the cut-off** is recorded on the row (`lexical_below_cut`) and is not put in the review queue; the pilot's precision on those decides whether it ever is. | Roger: TODO, decide with data | plan 11 § 9.4 |
| **No dedup pass before M1**; morphology families are annotation for R1 only. | Roger: leave families to M3 and R1 | plan 11 § 9.5 |
| **Links are by word, not sense**; the overlap call is the sense filter; **nothing is auto-rejected on a lexical link alone**, and a candidate is never dropped by this workstream. | plan 11 § 3-4; the polysemy in the dry sample | plan 11 |
| **Link types**: OEWN synonym (same synset), `similar`, `also`; antonym at the sense level; morphology from OEWN `derivation` sense links plus the negation-affix rule (un-, in-/im-/il-/ir-, non-, dis-, a-, -less/-ful) for antonym evidence; `non-X` placeholder labels excluded by name.  Each link carries its type and lexicon, and the readouts report by both. | plan 11 § 2-3; `derivation` links (2,903 seen in the dry run) are the dictionary's own stem families, so no hand stemmer is needed for step 5 | plan 11; this plan (pre-registered) |
| **No rubric, pin or prompt changes.**  Lexical neighbours enter the relation and overlap calls as listed traits do, in the judge display form; a list that is longer is data, not a prompt change. | plan 11 § 7; the judging rule | plan 11; [judging.md](../../.claude/rules/judging.md) |
| **Where the results live**: a new registry block **`lexical`** (`BLOCKS` in [registry.py](../../assistant_axis/gapgen/registry.py) gains it; merged by `update_many` like the others); the `novelty` block is never touched by the sweep.  In a **new wave with the switch on**, lexical neighbours appear inside the `novelty` block's `listed` with `via: "lexical"` and the walk decides on them as on any listed trait (a lexical neighbour can cover there: § 3 step 2 of the plan). | the frozen registry row is additive; old blocks byte-identical; R1 copies blocks onto nodes | this plan; "Interface as built" |
| **The switch** `--lexical-search` / `--no-lexical-search` on `novelty_score.py score`, **default off** until the pilot's gate; it follows the queue-search precedent exactly: recorded in `run.json`, `summary.json` and every block (`lexical_search`); `--resume` keeps the session's, `--redecide`, `--relation-only` and `full-scan` their source's unless overridden; `--hide` leaves hidden stems out of the targets; a run with it off writes byte for byte what it writes today. | "The seed queue in M3's search" is the model: a change of what is listed, not of the decision rules | [coding_plan_platform.md](./coding_plan_platform.md) |
| **The cosine floor does not drop a lexical neighbour**: one the relation call marks similar or unsure is read whatever its cosine (as an opposed trait's partner and a `renamed_from` match are); `below_floor` never names it. | the whole point is a trait the embedding puts far away | this plan (pre-registered) |
| **The sweep reads each pair under the row's own recorded rule set and cut-off** (`novelty.rules_of(block)`, `cut_off_spec(alignment, rules)`: the graded rule for the 6,930 rule-set-3 blocks, the step rule for the 154 of rule set 2) through `NoveltyRunner.read_pairs`, Sonnet then Opus: the reading M3 would have made had the trait been listed. | comparable with the block's own readings; the recovery harness reads pairs this way already | this plan |
| **Rows in the sweep**: every row with a `novelty` block decided `new` or `grey`, every pass (trait track, the physical and states passes), reported per pass; covered rows are not swept. | a cover already stands; a kept row is the only place a miss can hide | this plan |
| **Transport live**; every paid command estimates, caps (`confirm_or_abort`) and writes `usage.json`. | under $20 | [CLAUDE.md](../../CLAUDE.md) |
| Counts used throughout: the "Measured figures" above. | counted, not copied | this plan |

## 2. Out of scope

- Any change to M3's decision rules, cut-offs, rubrics or pins; the broader check; the cosine floor's value.
- Flipping recorded M3 decisions on the sweep's findings.  The designed path for that, if Roger asks for it at
  the readout, is `novelty_score.py score --redecide --lexical-search` per batch (the queue-search precedent:
  only the calls whose lists changed are sent, each flip attributed in `decision_changes.md`); it is costed in
  § Cost and not run by this plan.
- The masked-LM description-fit, a second embedding family, agreement rules, ConceptNet (dropped by the
  workstream plan).
- A dedup pass before M1; any edit to `data/traits/**`, `data/roles/**`, the TO_ADD files,
  [seed_queue.json](../../data/seed_queue.json), an `arrangement` field, or a trait file's `negative_label` (the
  antonym evidence is a note on the registry row, nothing more).
- The review app's pages beyond rendering the new flags and edges R1 copies (no new view).
- Plan 04's reuse of the lookup table (an interface it reads; § Frozen interface).

## 3. Rule files to Read first

Open with the **Read tool** before touching code:
[provenance.md](../../.claude/rules/provenance.md) (`usage.json` beside every batched LLM output, `MultiModelUsage`; `json_metadata` envelopes; UTC timestamps; snapshot before overwrite),
[entity-naming.md](../../.claude/rules/entity-naming.md) (file-name stems via `normalize_to_file_name` for every key; the judge display form in prompts; US English),
[trait-pairs.md](../../.claude/rules/trait-pairs.md) (what a trait, a [clean pair](./glossary.md#clean-pair), a triangle and the seed queue are; `negative_label` and `non-X` placeholders),
[judging.md](../../.claude/rules/judging.md) (reason before verdict; `warn_if_low_parse_rate` at 99%; pins; the rendered-prompt rule),
[CLAUDE.md](../../CLAUDE.md) (file-access boundary, the $20 confirmation rule, **tests are mandatory**, hotlinks).  No PNG is planned (the readouts are tables); if one is added, Read the plotting rule first.

**File-access boundary, restated for every Opus task prompt**: read and write only inside the repository
worktree, the agent's scratchpad and `$TMPDIR`; never list, read or stat anything else under the home
directory, not `~/.cache`, not `~/.wn_data`, not even to see whether something is downloaded.  The one
download of this workstream (Moby, task 1) goes to `data/external/moby/` through `setup_external.py`, which
pins every path in-tree; `wn`'s data directory is pinned by `assistant_axis.gapgen` on import.  The sandbox's
network filter may need `www.gutenberg.org` named for that one command; say so rather than route around it.

## 4. Existing code to reuse

- [novelty.py](../../assistant_axis/gapgen/novelty.py): `load_trait_corpus`, `queue_traits`
  (`QUEUE_SEARCH_STATUSES`, `handed_to_registry`), `CorpusIndex` (`retrieve`, `cosine_to`, `project`),
  `Listed` and `listed_from`, `expand`, `build_shortlist` (the floor's exemptions), `Walk`, `rules_of`,
  `cut_off_spec`, `pair_verdict`, `verdict_cuts`, `blind`, `novelty_block`, `REVIEW_KINDS` / `QUEUE_KINDS`.
- [novelty_runner.py](../../assistant_axis/gapgen/novelty_runner.py): `NoveltyRunner` (`_run`'s listing step,
  `read_pairs` and `run_pairs`: Sonnet then Opus on whole pairs with no walk, as the recovery harness uses
  them), `M3Candidate` and `candidate_from_row`, `Call`, `OVERLAP_TOKENS`, `OPUS_SHARE_SHORTLIST` /
  `OPUS_SHARE_FULL_SCAN`, `record_cost`, `summarize`'s shape; the `queue_search_block` pattern.
- [novelty_score.py](../../data_analysis/gap_generation/novelty_score.py): `load_m3_rubrics`, `load_index`
  (`allow_embed=False`: the cached embeddings only), `label_sets_for`, `queue_record`, `resolve_queue_search`
  and `source_queue_search` (the precedent for the new switch), `write_blocks` (`Registry.update_many` with
  `merge_blocks=False`), `_prepare_out_dir`, `finalize`, the dry-run and `render` paths, `_common_args`.
- [recovery.py](../../assistant_axis/gapgen/recovery.py): `match_plan` / `match_candidates` / `pair_outcome`
  (a candidate read against traits outside its shortlist through `run_pairs`: the sweep's shape), `load_hidden`.
- [wordnet.py](../../assistant_axis/gapgen/wordnet.py) (`oewn()`, `OEWN_LEXICON`, `_lookup_forms`),
  [glosshint.py](../../assistant_axis/gapgen/generators/censuses/glosshint.py) (`lookup_forms`, `oewn_lemma`),
  [paths.py](../../assistant_axis/gapgen/paths.py) (`DATA_EXTERNAL`, `wn_data_dir`, `check_id`).
- The download convention of [ipip/download.py](../../assistant_axis/gapgen/generators/ipip/download.py)
  (`.part` then rename, sha256 and size of the bytes received, `DOWNLOAD_MANIFEST.json` git-ignored beside the
  file, a tracked `sources_manifest.json`, the licence quoted) and
  [setup_external.py](../../data_analysis/gap_generation/setup_external.py).
- [registry.py](../../assistant_axis/gapgen/registry.py): `Registry` (`fold`, `update_many`, `merge_block`,
  `BLOCKS`), `utc_now`; [cost.py](../../assistant_axis/gapgen/cost.py): `Estimate`, `GuardedUsage`,
  `confirm_or_abort`; [runs.py](../../assistant_axis/gapgen/runs.py): `git_sha`, `platform_dirty_files`;
  [overlap_test.py](../../assistant_axis/gapgen/overlap_test.py): `render_single`, `PairCall`;
  [prompt_labels.py](../../assistant_axis/gapgen/prompt_labels.py): `prompt_label`, `DEFAULT_LABEL_FORM`;
  [provenance.py](../../assistant_axis/provenance.py) / [plot_metadata.py](../../assistant_axis/plot_metadata.py):
  `json_metadata`; [atomic_io.py](../../assistant_axis/atomic_io.py).
- [review_graph.py](../../assistant_axis/gapgen/review_graph.py): the loop that copies `novelty.listed` and
  `novelty.readings` into `source: "m3"` corpus edges (`_m3_target`, `rd_of`), `Node.flags`,
  `label_variant_key`; the app renders `flags` as badges ([app.js](../../assistant_axis/gapgen/review_app/static/app.js))
  and lists corpus and queue traits "by reading" on the card ([server.py](../../assistant_axis/gapgen/review_app/server.py)).
- Test style: [test_gapgen_novelty_rule3.py](../../assistant_axis/tests/test_gapgen_novelty_rule3.py) (the toy
  corpus and the fake clients of [fake_anthropic.py](../../assistant_axis/tests/fake_anthropic.py)),
  [test_gap_generation_novelty_cli.py](../../data_analysis/tests/test_gap_generation_novelty_cli.py),
  [test_gapgen_wordnet.py](../../assistant_axis/tests/test_gapgen_wordnet.py) (a fake `wn` module).  **No new
  dependencies** (`wn` is installed).

## 5. File layout

```
assistant_axis/gapgen/lexical.py          (not there yet)
    LEXICONS = ("oewn", "moby"); LINK_TYPES = ("synonym", "similar", "also"); ANTONYM_TYPES = ("antonym", "negation_affix")
    NEGATION_PREFIXES = ("un", "in", "im", "il", "ir", "non", "dis", "a"); SUFFIX_PAIRS = (("less", "ful"),)
    MOBY_COSINE_FLOOR = 0.2; LOOKUP_PATH = DATA_CANDIDATES / "lexical" / "lookup.json"
    Lexicon (protocol): synsets(form) -> [ids]; lemmas(id) -> [str]; related(id, type) -> [ids]; antonyms(form) -> [str];
        derivations(form) -> [str]; version -> str
    OewnLexicon(wordnet=None)  (wordnet.oewn(); forms as glosshint.lookup_forms, a standard's suffix dropped)
    MobyLexicon(path)          (mthesaur.txt: head,syn,...; lowercase; version = the manifest's sha256)
    label_forms(label) -> list[str]           (the forms tried, in order; a label with a "(Standard)" suffix is looked up bare)
    is_placeholder(label) -> bool             ("non-X" negative labels; never a target)
    build_lookup(corpus, queue_entries, *, lexicons) -> Lookup   (every corpus label and live queue label -> its synset ids
        per lexicon, its lemmas, whether it has a text; lexicon versions; content sha256)
    Lookup.neighbours(label, stem, *, exclude=()) -> list[Link]  (Link(stem, kind: corpus|queue, link, lexicon, name_only))
    Lookup.antonym_evidence(label, stem) -> list[Antonym]       (Antonym(stem, link, partner_has_file))
    Lookup.family(label, stem) -> list[str]                     (derivation-linked and affix-stripped stems among
                                                                 corpus, queue and a given candidate set)
    save_lookup / load_lookup (json_metadata envelope)
assistant_axis/gapgen/lexical_sweep.py    (not there yet)
    sweep_plan(rows, lookup, index, vectors) -> list[PairItem]  (every kept row's lexical-only pairs: the block's listed,
        readings and covered_by excluded; cosine from the cached vectors; Moby-only pairs below MOBY_COSINE_FLOOR marked
        not_judged; name-only links marked not_judged)
    run_sweep(runner, items, *, rules_of_row, wave="x") -> rows  (NoveltyRunner.run_pairs; each pair under its row's
        CutOff; pair_outcome as the recovery harness)
    lexical_block(row, links, antonyms, family, readings, *, run_id, lookup) -> dict   (§ 6)
    sweep_report(rows, ...) -> dict; sweep_markdown(...) -> str
    labelled_measurement(pairs, lookup) -> dict  (§ 6 of the workstream plan, by lexicon and link type)
assistant_axis/gapgen/novelty.py          Listed gains lexical: Optional[dict] = None (omitted from listed_row when None);
                                          build_shortlist: a via == "lexical" similar/unsure trait is never dropped by the floor
assistant_axis/gapgen/novelty_runner.py   NoveltyRunner(lexical: Optional[Lookup] = None, lexical_info=None): after expand(),
                                          the lookup's neighbours not already listed (and not hidden) join st.listed with
                                          via="lexical" and their cosine; every block of such a run carries lexical_search
assistant_axis/gapgen/registry.py         BLOCKS gains "lexical"
assistant_axis/gapgen/review_graph.py     a row's lexical block -> source: "lexical" corpus/queue edges with the sweep's
                                          readings; Node.flags gains the row's lexical flags; family -> candidate edges
                                          via "stem_family" (typed by readings like any edge; never a 3-edge on that ground)
data_analysis/gap_generation/lexical_recall.py   (not there yet)   build | labelled | dry | sweep | report
data_analysis/gap_generation/setup_external.py   --moby
data_analysis/gap_generation/novelty_score.py    --lexical-search / --no-lexical-search (score, resume, redecide, relation-only,
                                                 full-scan, --hide), recorded like queue_search
data/external/moby/{mthesaur.txt, DOWNLOAD_MANIFEST.json}                     git-ignored
data/candidates/lexical/{sources_manifest.json, lookup.json, labelled_readout.json, dry_readout.json, dry_readout.md}   tracked
data/candidates/lexical/sweep/<batch_id>/{plan.json, pairs.jsonl, responses.jsonl, results.jsonl, sweep_report.json,
                                          sweep_report.md, registry_writes.jsonl, usage.json, run.json, run.log}   tracked
assistant_axis/tests/test_gapgen_lexical.py, test_gapgen_lexical_sweep.py, test_gapgen_novelty_lexical.py,
                     test_gapgen_review_graph_lexical.py, test_gapgen_lexical_acceptance.py
data_analysis/tests/test_gap_generation_lexical_cli.py
```

Every paid answer is appended to the sweep's `responses.jsonl` before it is parsed, keyed as M3's records are
(step, prompt sha256, model, user), so `--resume` sends nothing answered and a changed prompt is never matched.

## 6. Data schemas

**Lookup table row** ([lookup.json](../../data/candidates/lexical/lookup.json), not there yet; one entry per
corpus trait and live queue label, in a `json_metadata` envelope whose `inputs` name the trait files' fingerprint,
the queue file and the lexicons):

```json
{"stem": "agreeable", "label": "agreeable", "kind": "corpus", "has_text": true, "forms_tried": ["agreeable"],
 "oewn": {"synsets": ["oewn-00120001-a", "oewn-01208010-s"], "found": true},
 "moby": {"head": "agreeable", "n_synonyms": 143, "found": true}}
```

Header fields: `lexicons: {"oewn": {"id": "oewn:2024", "wn_version": "1.1.1"}, "moby": {"sha256": "...", "source": "Gutenberg #3202"}}`,
`n_corpus`, `n_queue`, `n_queue_name_only`, `coverage` (found per lexicon per kind), `content_sha256`.

**The `lexical` block on a registry row** (written by the sweep; the `novelty` block beside it unchanged):

```json
{"run_id": "2026-10-14-lex_sweep_1", "lookup_sha256": "…", "lexicons": {"oewn": "oewn:2024", "moby": "…"},
 "links": [
   {"stem": "agreeable", "kind": "corpus", "link": "similar", "lexicon": "oewn", "cosine": 0.212, "name_only": false,
    "listed_by_m3": false, "judged": true,
    "sonnet": {"value": 3, "reason": "…"}, "opus": {"value": 3, "reason": "…"},
    "verdict": "cut", "at_cut_off": true}],
 "antonyms": [{"stem": "disagreeable", "link": "antonym", "lexicon": "oewn", "partner_has_file": true}],
 "family": [],
 "cut_off_rule": {"c": 3, "sonnet_alone": true, "opus_check": true, "rule": "graded", "band": "alignment 0-1"},
 "rules": "m3_rules_3",
 "flags": ["lexical_cover"], "n_pairs_judged": 1, "usage": {"per_model": {…}, "cost_usd": 0.0041},
 "at": "2026-10-14T10:00:00+00:00"}
```

Vocabularies: `link` ∈ {synonym, similar, also} for `links`, {antonym, negation_affix} for `antonyms`;
`verdict` as `novelty.pair_verdict` (`cut`, `review`, `keep`, `opposite`, `unparsed`); `at_cut_off` is
`verdict_cuts(verdict, rules)`; `flags` ⊆ {`lexical_cover` (a judged link at the cut-off), `lexical_below_cut`
(every judged link under it), `lexical_name_only` (a link to a text-less queue entry), `lexical_unparsed`,
`lexical_antonym` (an antonym link to a trait with no pair partner, beside M3's `pair_completion_for`)}.  A
Moby-only pair under the cosine floor and a name-only link are `judged: false` with no readings.  The block is
replaced whole by a later sweep (`merge_blocks=False`), so a row records one sweep at a time; `registry_writes.jsonl`
in the sweep directory keeps what each sweep wrote.

**`lexical_search` on an M3 block** (only when the switch is on; the queue-search shape):
`{"lookup_sha256": "…", "lexicons": {...}, "n_added": 1, "moby_cosine_floor": 0.2}`; a listed trait it added is
`{"stem": "dominant", "cosine": 0.19, "rank": null, "via": "lexical", "relation": "similar", "lexical": {"link": "similar", "lexicon": "oewn"}}`.

**Sweep report** ([sweep_report.json](../../data/candidates/lexical/sweep/2026-10-14-lex_sweep_1/sweep_report.json),
not there yet; figures illustrative): `{"n_rows_swept": 4091, "n_rows_with_links": 561, "n_pairs": 821, "n_judged": 790,
"not_judged": {"moby_below_floor": 0, "name_only": 31}, "covers_at_cut_off": 14, "below_cut": 776, "by_link": {"synonym":
{"judged": 242, "covers": 7}, …}, "by_lexicon": {…}, "by_cut_off_band": {…}, "by_pass": {"trait": …, "physical": …,
"states": …}, "roger_merges": {"rows": 53, "into_corpus": 23, "lexical_target": 2, "lexical_target_read_at_cut_off": 2},
"audit_retrieval_misses_reached": ["pleasant#1", "annoying#1"], "antonym_evidence": {"rows": 46, "singleton_partner": 18,
"beside_pair_completion_for": …}, "parse_rate": {...}, "spend_usd": 2.4}` plus a per-row table in `sweep_report.md`
(key, label, gloss, the trait, link type and lexicon, cosine, Sonnet, Opus, verdict, Roger's review status).

**Dry readout** ([dry_readout.md](../../data/candidates/lexical/dry_readout.md), not there yet): the "Measured
figures" above, recomputed by the tool, plus Moby's counts and the per-pass split; the labelled-pairs
measurement beside it ([labelled_readout.json](../../data/candidates/lexical/labelled_readout.json)).

**Download manifest** ([DOWNLOAD_MANIFEST.json](../../data/external/moby/DOWNLOAD_MANIFEST.json), git-ignored,
and the tracked [sources_manifest.json](../../data/candidates/lexical/sources_manifest.json); neither there yet): `{"file":
"mthesaur.txt", "url": "…", "sha256": "…", "size": …, "fetched_at": "…", "tool": "setup_external.py --moby",
"licence": "public domain (Project Gutenberg #3202, Moby Thesaurus List by Grady Ward)", "n_heads": …}`.

## 7. CLI

[lexical_recall.py](../../data_analysis/gap_generation/lexical_recall.py) (not there yet).  Common flags
`--data-dir`, `--registry`, `--out-root`, `--lookup` (default `LOOKUP_PATH`), `--lexicons oewn moby`, `--dry-run`.
The paid command takes `--budget-usd` (a hard cap, `confirm_or_abort`), `--confirm-expensive --confirmed-by`
(only over the $20 line; **not expected**), `--allow-dirty`, `--resume`, `--overwrite`, `--concurrency`,
`--transport live|batches` (default live), prints its estimate as `n_calls x (in, out) tokens at model rates =
$X`, charges every answer to a `GuardedUsage` and writes `usage.json` in a `finally` block.  Dry runs print the
estimate, the counts and one **rendered prompt** per variant (§ 7a) and write nothing.

- `setup_external.py --moby [--dry-run]`: fetches `mthesaur.txt` into `data/external/moby/` (`.part`, rename,
  sha256 and size recorded), writes both manifests, prints the head count; idempotent (a file matching the
  manifest is not fetched again).  $0; network once, with Roger's go already given.
- `build [--lexicons oewn moby]`: the lookup table over the 932 corpus labels and the live queue labels;
  prints coverage per lexicon and kind and the name-only count; `.bak.<UTC>` on change.  $0, seconds.
- `labelled`: the workstream plan's § 6 measurement over
  [labelled_pairs.json](../../data/candidates/calibration/labelled_pairs.json): per relation, per lexicon and
  per link type, the pairs linked, abstained and flagged (recall on duplicates and antonyms, false flags on
  near-distinct and unrelated); writes `labelled_readout.json`.  $0.
- `dry [--rows all|trait|physical|states]`: the retroactive lookup over every kept row: the lexical-only
  pairs with cosine (cached embeddings; a row with no cached vector is listed as such), antonym evidence,
  families; the free labels (Roger's merges, the audit's five); writes `dry_readout.json` / `.md` and the
  sweep's `plan.json` under `--batch-id` when given.  $0.
- `sweep --batch-id B [--rows all|...] [--sample N --seed S] [--budget-usd 10] [--resume] [--dry-run]`: the
  overlap call on every judgeable lexical-only pair (open decision 1: all, or `--sample`), each under its
  row's own rule set and cut-off, Sonnet then Opus (`read_pairs`), live; writes `pairs.jsonl` before the first
  call, then `responses.jsonl`, `results.jsonl`, the `lexical` block on each swept row
  (`Registry.update_many`, `merge_blocks=False`; never the `novelty` block), `registry_writes.jsonl`,
  `sweep_report.{json,md}`, `usage.json`, `run.json`; `warn_if_low_parse_rate` per (step, model).  Estimate:
  pairs × (Sonnet $0.0012 + Opus share × $0.0031); the share printed as ASSUMED (0.40-0.62) until measured.
  Default cap $10 (first-of-kind: 1.5 × the OEWN estimate + Moby's unknown).
- `report --batch-id B [--marks marks.json]`: `sweep_report.md` again, with Roger's blind marks folded in
  when given (open decision 2), the stop-rule line first.  $0.
- `novelty_score.py score ... --lexical-search` (task 6, past the gate): as today plus the lexical neighbours
  in every candidate's list; `--dry-run` prints a candidate whose list gained one.  Cost per candidate rises
  by about 0.2 listed traits (negligible on the relation call) and the overlap calls on the lexical neighbours
  marked similar (§ Cost).

### 7a. Rendered prompts (no API call; the system prompts are the pinned rubric files, unchanged)

All three are real pairs from the dry lookup, rendered through the code's own paths (`overlap_test.render_single`,
`novelty.render_relation_user`, labels in the judge display form).  Nothing in the text says a pair came from
the lexicon: the models see a pair, or a list, as today.

**The sweep's overlap call** (system prompt [overlap_concept.md](./rubrics/overlap_concept.md), rubric A v6;
Sonnet 5.5, then Opus 5.5 by the row's rule).  `obdurate#1` (kept at cut-off 4, alignment 3; M3 read it
against [unyielding](../../data/traits/instructions/unyielding.json), rigid, unforgiving and persevering) and its
OEWN synonym [unrepentant](../../data/traits/instructions/unrepentant.json), never listed:

```text
{"target": {"label": "obdurate", "description": "This means holding one's position stubbornly and refusing to change one's mind or give in, even when presented with clear arguments or mounting pressure to yield."},
 "other": {"label": "unrepentant", "description": "This means shrugging off the harm one has done, feeling no guilt over it however bad it was, never apologizing, and seeing nothing to make right."}}
```

The expected answer is a 1 or a 2 (the dictionary's `obdurate` is the unrepentant sense; the gloss is the
stubborn one): a polysemy hit, which the call is there to turn away.  The same call on `activist#1` against
[aggressive](../../data/traits/instructions/aggressive.json) (an OEWN synonym by the "aggressive = activist"
sense) reads the same way:

```text
{"target": {"label": "activist", "description": "This means devoting most of one's time and energy to organizing, speaking out, and pressing for a political or social cause, rather than merely holding sympathetic views about it."},
 "other": {"label": "aggressive", "description": "This means pushing for confrontation, forceful action and combative approaches to get what one wants, and rejecting compromise or peaceful solutions."}}
```

**A new wave's relation call with a lexical neighbour in the list** (system prompt
[relation.md](./rubrics/relation.md) v1; Haiku 5.5).  `preponderating#1`: its gloss ("carrying more weight")
retrieved the body-build traits, and the lexicon adds [dominant](../../data/traits/instructions/dominant.json),
here at id 4 in the seeded shuffle of a run named `2026-10-14-lex_pilot`:

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

Read for fit: the rubric's "a numbered list of other persona traits" and "the listed trait's id" hold with the
longer list; the lexical neighbour is a listed trait like the others, with no mark, so the pair check and the
relation answers stay independent of where a trait came from.  If the relation call marks `dominant` similar,
the walk reads the pair at the candidate's cut-off whatever its cosine (0.19 here, under the floor).

## 8. Acceptance tests, written first

No test calls an API or the network: a fake lexicon (a tiny `wn`-like object and a six-line Moby fixture),
the fake Anthropic clients, the toy corpus of the M3 tests, a tmp registry through the real API.  The yield
figures are **report-and-decide** (open decision 2); parse rate, cost caps, `usage.json`, the untouched
`novelty` blocks and corpus, and byte-identity with the switch off are hard.

- `lexical`: `label_forms` (hyphen and space variants, a standard's suffix dropped, a phrase tried whole and
  abstaining when absent); `is_placeholder` on `non-X`; `build_lookup` records every corpus and live queue
  label with `has_text`, the lexicon versions and a content hash that changes when a label or the lexicon
  does; `neighbours` returns each link once with its type and lexicon, OEWN before Moby, excludes the
  candidate's own stem, folds `renamed_from` to the current stem, respects `exclude` (the listed, read and
  covering stems; a hidden set); a text-less queue entry comes back `name_only`; `antonym_evidence` finds an
  OEWN antonym and an affix pair (`un-X` for a corpus `X`, `X-less` / `X-ful`) and says whether the trait has
  a pair partner; `family` groups derivation-linked and affix-stripped stems and never a `non-X`.
- `lexical_sweep`: `sweep_plan` lists only lexical-only pairs (a planted link M3 already listed is left out, a
  read one too), carries the cosine from a fake index, marks a Moby-only pair under 0.2 and a name-only link
  `judged: false`; `run_sweep` reads a pair under the row's own rule set (a rule-set-3 alignment-2 row: both
  models at 3 cover; a rule-set-2 row: the step rule) and records Sonnet and Opus; `lexical_block` sets every
  flag of § 6 in its truth table; the `novelty` block of a swept row is byte-identical before and after
  (watched); the report's counts; `labelled_measurement` on a planted labelled file.
- `novelty_lexical` (the toy corpus, fake clients): with a lookup given, a planted lexical neighbour joins
  `listed` with `via: "lexical"` and its link, appears in the relation call's user turn (the rendered text
  carries its label and description and nothing else new), and is read by the walk though its cosine is under
  the floor and `below_floor` does not name it; a neighbour already retrieved or expanded is not added twice;
  the block carries `lexical_search`; **with no lookup the run's blocks, `responses.jsonl` and `summary.json`
  are byte-identical to today's** (the queue-search test's method); `--hide` keeps a hidden stem out of the
  additions; `--redecide --lexical-search` over a recorded run sends only the relation calls whose lists
  changed and attributes a flip to the "lexical search" step; `--relation-only` and `full-scan` follow their
  source.
- `review_graph_lexical`: a row with a `lexical` block yields a `source: "lexical"` edge to the trait (or
  queue) node with the sweep's readings, the node's `flags` carry `lexical_cover`, a name-only link makes a
  queue node without readings, and the trait appears among the card's targets; two kept candidates of one
  family get a `via: "stem_family"` candidate edge that is typed by its readings and is not a 3-edge unread.
- CLI: every subcommand's `--dry-run` exits 0 and writes nothing; `sweep --dry-run` prints the estimate with
  the ASSUMED share and the rendered pair; `sweep` refuses over budget, **cost guard**: 10,000 planted pairs
  → estimate > $20 → refused without `--confirm-expensive --confirmed-by`; `--resume` sends nothing answered;
  `setup_external.py --moby --dry-run` prints the target and fetches nothing; the Moby parser on the fixture
  (heads, counts, lowercase, a comma inside a quoted field if the file has one); `novelty_score.py score
  --lexical-search --dry-run` on the toy corpus shows the added neighbour.
- **Acceptance on recorded outputs** (`test_gapgen_lexical_acceptance.py`, skips while absent): the lookup
  table covers every corpus trait and live queue label (hard); `dry_readout.json` reaches `pleasant#1` →
  [agreeable](../../data/traits/instructions/agreeable.json) and `annoying#1` →
  [disagreeable](../../data/traits/instructions/disagreeable.json) (hard: the two known cases); the sweep's
  parse rate ≥ 0.99 per step and model (hard); `usage.json` beside the sweep with nonzero cost; every swept
  row's `novelty` block unchanged against the sweep's `plan.json` snapshot of its `at` and decision (hard);
  the stop-rule figure and the by-link precision present in `sweep_report.json` (reported); the rubric pins
  unmoved (`rubric_pins.py check`).
- **Manual check, listed as such**: Roger's blind marks on up to 40 covers (open decision 2), recorded in the
  acceptance report, never asserted by a test.

Commands that must pass at the end of every task:

```
uv run pytest assistant_axis/tests/test_gapgen_lexical*.py assistant_axis/tests/test_gapgen_novelty_lexical.py assistant_axis/tests/test_gapgen_review_graph_lexical.py data_analysis/tests/test_gap_generation_lexical_cli.py -q
uv run pytest -q assistant_axis/tests data_analysis/tests        # the whole suite, unchanged (never a bare pytest at the root)
uv run python data_analysis/gap_generation/rubric_pins.py check   # no pin moves: this plan edits no rubric
uv run python data_analysis/check_arrangements.py --quiet
uv run python tools/sync_entity_lists.py --check
git status --porcelain data/traits data/roles data/seed_queue.json   # must be empty
```

## 9. Ordered task checklist

Prerequisite: a worktree off `anthropic-vllm-uv` (`git merge --ff-only anthropic-vllm-uv` first), `.env`
copied, `data/external/` and `data/candidates/cache/` symlinked from the main checkout; the registry log is
per checkout, so the sweep's registry writes (task 5) are made in the **main checkout** after the merge, or
replayed there from `registry_writes.jsonl` (the resubmit convention).  The boundary paragraph of § 3 goes
into every task prompt verbatim.  Each task ends with the § 8 commands.

1. `setup_external.py --moby` and the Moby loader; both manifests.  Test: the parser fixture, the dry run.
   Report the file's size, head count, sha256 and the URL actually fetched.
2. `lexical.py` (`OewnLexicon`, `MobyLexicon`, `build_lookup`, `neighbours`, `antonym_evidence`, `family`,
   save/load); `BLOCKS` gains `lexical`.  Test: lexical.  Run `build`; paste the coverage line into the task
   report (expected: OEWN 699 of 932 corpus labels, 31 of 38 queue texts).
3. `lexical_recall.py build | labelled | dry`; `lexical_sweep.sweep_plan`, `labelled_measurement`.  Test: the
   CLI's dry paths, `sweep_plan`.  **Run the dry pilot** (§ 10, gate 1): `labelled` and `dry` over every kept
   row → [dry_readout.md](../../data/candidates/lexical/dry_readout.md); expected on OEWN about 561 rows and
   821 pairs plus Moby's; the two known cases reached.  Paste the readout's head and the three rendered
   prompts of § 7a into the task report; Roger reads them before any call is made.
4. `lexical_recall.py sweep | report`; `run_sweep`, `lexical_block`, the registry write.  Test: lexical_sweep,
   CLI (cost guard, resume, dry run, the untouched `novelty` block).
5. **The paid pilot = the sweep** (§ 10, gate 2; open decision 1): `sweep --batch-id <date>-lex_sweep_1` on
   every judgeable pair, live, `--budget-usd 10` (estimate about $2-3; Moby's pairs within the cap or
   reported as cut); `report`; the readout [lexical_pilot_readout.md](./lexical_pilot_readout.md)
   (not there yet: Fable writes it from the sweep report, as the M3 readouts were written) with the stop-rule
   figure first.  **Roger's marks** (open decision 2, 30 minutes).  **If fewer than about five real covers, stop
   here**: tasks 6-8 are not built, task 9 closes the plan.
6. The integration (only past the gate): `Listed.lexical`, the runner's additions after `expand`, the floor
   exemption, `--lexical-search` on `score` with the queue-search precedent (`run.json`, blocks, `--resume`,
   `--redecide`, `--relation-only`, `full-scan`, `--hide`).  Test: novelty_lexical, the byte-identity check.
   `score --lexical-search --dry-run` on a recorded batch: paste a candidate whose list gained a neighbour.
7. R1: the `lexical` block to edges and flags, family edges; the review app shows them through the existing
   badges and target lists (no page change expected; say so if one is needed).  Test: review_graph_lexical.
   `review_graph.py build --dry-run` over two batches with swept rows: paste the edge and flag counts.
8. Recovery check, dry first (the workstream plan's § 6 "hidden-partner recovery"): over the recorded
   [rec_antonym_check_pilot_1](../../data/candidates/recovery/rec_antonym_check_pilot_1/recovery_report.md)
   hidden set, how many of its unrecovered hidden traits have a lexical link from some kept candidate of that
   run (reachability by lexicon, $0, from `hidden.json` and the lookup).  The paid harness run with
   `--lexical-search` on (about $5 a seed, the harness's measured cost) only on Roger's word at the readout.
9. Glossary entries (lexical link, lexical neighbour, lexical-only pair, retroactive sweep, name-only link,
   stem family) in [glossary.md](./glossary.md); the acceptance report (§ 11); propose the
   [data/README.md](../../data/README.md) paragraphs for `candidates/lexical/` and `external/moby/` in the report
   (do not edit; the platform owns that file); the [AGENT_NOTES.md](../../AGENT_NOTES.md) sentence for the
   gate-audits paragraph proposed the same way.

## 10. Pilot

**Gate 1, the dry pilot** (task 3, $0): the lookup over the recorded data.  Readout: coverage per lexicon and
kind; the labelled-pairs recall and false-flag rates per lexicon and link type (OEWN's dry figures: duplicates
16 of 57, antonyms 52 of 211, unrelated 5 of 1,334); the lexical-only pairs by link type, lexicon, target
kind, cut-off band and pass, with Moby's share and how many of Moby's fall under cosine 0.2; name-only links;
antonym evidence beside `pair_completion_for`; families among the kept rows; the free labels (Roger's 53
merges, the audit's five retrieval misses).  **Gate**: the two known cases reached (hard); the pair count
within the sweep's cap (if Moby adds thousands of pairs above 0.2, the sweep takes OEWN's all and Moby's by
cosine down to the cap, and says so).

**Gate 2, the sweep** (task 5, ≈ $2-3 live, cap $10).  Readout, the stop-rule line first: **covers at the
cut-off** (a lexical-only pair read at the row's own cut-off under its rule), by link type, lexicon, cut-off
band and pass; the below-cut readings' distribution (Roger's TODO 4: are the 2s and 3s-under-4 worth a review
flag?); precision proxies: how many covers are rows Roger already merged into that trait, how many into
another target, how many the audit's list names; the Opus share measured (replaces the ASSUMED 0.40-0.62 in
the estimate); parse rates; spend by model.  Then **Roger's blind marks** on up to 40 covers (open decision
2), in the cover audit's form (seeded `key.json`, a marks file, the pair with both texts and no readings).
**Roger decides**: (a) stop or build (tasks 6-8) on the marked precision and the count; (b) whether
below-cut hits get a review flag (TODO 4); (c) whether the confirmed covers are made M3 decisions now by
`score --redecide --lexical-search` per batch (≈ $5, § Cost) or stay flags for the end-of-generation R1 pass
(the decided default); (d) whether Moby stays in, on its own precision.

Yield per dollar is reported as the M3 pilots report it: `covers_at_cut_off / usage.json total_cost_usd`.

## 11. Report at the end

One page at [acceptance_11_lexical_recall.md](./acceptance_11_lexical_recall.md) (not there yet): what was
built against § 5; deviations with reasons; the § 8 commands verbatim with pass counts; the Moby manifest
line (size, heads, sha256, URL); the lookup's coverage; the labelled-pairs table per lexicon and link type;
the dry readout's counts; the three rendered prompts; the sweep's stop-rule figure, its by-link precision,
the Opus share measured, parse rates and cost per model from `usage.json`; Roger's marks and his four
decisions of § 10; if built, the integration's byte-identity check, the R1 edge and flag counts on the
all-batches build, and the per-wave cost measured on the first wave run with the switch on; the dry recovery
reachability; open QUESTIONS entries; the proposed `data/README.md` and `AGENT_NOTES.md` text.

## 12. Escalation

Opus retries a failing step once with a changed approach, then Fable (diff review, architecture, stubborn
failures), then Roger through [QUESTIONS.md](./QUESTIONS.md) in its format (`N. [11] question. Assumption
proceeded under: ... Status: open`, numbering continuing from the file's last entry, 90 on 2026-10-12),
proceeding under the assumption unless the answer would make the work useless.  Pre-registered entries Opus
copies in at the start: (1) OEWN 2024 as installed, not 2025; (2) a text-less queue entry gives a name-only
link, recorded and never judged; (3) links by word, the overlap call the sense filter, no auto-reject; (4)
OEWN `derivation` links plus the affix rule are the morphology source; (5) results live in a new `lexical`
block, the `novelty` block untouched by the sweep; (6) the switch is off by default and follows the
queue-search precedent, byte-identical when off; (7) a lexical neighbour marked similar is read whatever its
cosine; (8) pairs are read under the row's own recorded rule set; (9) open decision 1 proceeds as "all pairs",
open decision 2 as "Roger marks 40 before the integration"; (10) the sweep never flips a decision and the
flags wait for the end-of-generation R1 pass.  Anything that would edit a trait file, the queue, an
`arrangement` or a `negative_label`, change a rubric text or pin, write the `novelty` block from the sweep,
spend over a command's budget, fetch anything but Moby, or change a frozen signature stops and asks.

## Cost (estimates; re-measured at the pilot)

Per overlap pair live, as measured in `overlap_arms_3` and used by M3's estimate: Sonnet $0.0012, Opus $0.0031;
the share of pairs Opus reads is 0.62 on M3's shortlists and 0.40 in the full scan; lexical-only pairs are far
pairs, so the lower share is the likelier.  Haiku 5.5 at $0.10 / $0.50 per MTok, 76.5 output tokens per listed
trait on the relation call.  Batches at half price are not used (everything is under $20; the rule says real
time).

| step | calls | estimate |
|---|---|---|
| Moby download (about 25 MB), lookup, `labelled`, `dry` | 0 | $0 |
| **the sweep, OEWN's 821 pairs** (less about 31 name-only) | 790 Sonnet + 316-490 Opus | **≈ $2.0-2.6 live** |
| the sweep, Moby's pairs at cosine ≥ 0.2 | unknown; capped | ≤ the $10 cap less OEWN's |
| Roger's blind marks | 0 | 30 minutes |
| **this plan's paid work** | | **≈ $3, cap $10** |
| per wave with the switch on, per 1,000 candidates: about 200 lexical neighbours in the relation calls (≈ $0.02) and the overlap calls on those marked similar (about half, ≈ $0.3) | | **≈ $0.35 per 1,000 candidates live**; a TDA-sized wave (1,779) ≈ $0.6 |
| the flip path, if Roger asks (§ 2): `score --redecide --lexical-search` per batch, 561 relation calls re-sent (≈ $2.2) and the overlap calls on the similar lexical pairs (≈ $2.5 unless the sweep's records are replayed) | | ≈ $5 once |
| the paid recovery harness with the switch on (task 8, on Roger's word) | | ≈ $5 a seed |

Against the workstream plan's "total under $5": holds for OEWN; Moby is the unknown, and it is capped and
reported apart.

## Frozen interface (for R1, plan 04 and later waves)

`from assistant_axis.gapgen.lexical import Lookup, load_lookup, LOOKUP_PATH, LINK_TYPES, ANTONYM_TYPES,
LEXICONS` ([lexical.py](../../assistant_axis/gapgen/lexical.py), not there yet):
`Lookup.neighbours(label, stem, *, exclude=()) -> list[Link]` (`Link(stem, kind, link, lexicon,
name_only)`), `Lookup.antonym_evidence(label, stem) -> list[Antonym]`, `Lookup.family(label, stem) ->
list[str]`; the table's header carries the lexicon versions and `content_sha256`.  On a registry row: the
`lexical` block of § 6 (fields added, never renamed, without a schema bump), and inside an M3 block decided
with the switch on, `lexical_search` and listed traits with `via: "lexical"` and a `lexical` field.  In R1,
`source: "lexical"` edges and the `lexical_*` flags of § 6 on candidate nodes; `via: "stem_family"` candidate
edges.  The relation and overlap rubrics, their pins, `Rules` and `RULES`, `CutOff`, the `novelty` block's
existing fields and every CLI flag that exists today are unchanged.
