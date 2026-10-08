# Coding plan: workstream 2, Roget's heads as a coverage map, WordNet clusters as sibling (variant A)

Written 2026-09-23 (Fable) in the [PLAN_FORMAT.md](./PLAN_FORMAT.md) shape from
[02_roget_wordnet.md](./02_roget_wordnet.md) and its § 10 Resolution.  It is written against the
"Frozen interface" of [coding_plan_platform.md](./coding_plan_platform.md) (`Candidate`,
`start_run`, `submit_candidates`, `NoveltyQuery`, `MetricConfig`, `recovery_test`) and reuses the
platform's module layout (`paths`, `freq`, `wordnet`, `llm`, `cost`, `embed`); nothing there is
redefined.  Anything this plan needs that the platform lacks is in the marked "Interface requests"
section at the end.  Roger's review comments go into this file.

Execution order relative to the platform: tasks 1-7 need only platform M1; task 8 needs M2's
`embed.py`; tasks 12-13 need M3 (`traithood_filter.py`, `novelty_score.py`, the recovery hook).

## 1. Decisions already made

| decision | reason | source |
|---|---|---|
| Variant A, Roget-first: Roget heads are the coverage unit; WordNet confirms opposed-head pairs and supplies sense features; a small WordNet sibling stream (antonyms of unpaired existing labels, trait-noun closure) runs under its own generator id `wn_clusters`. | the head map is what no other generator gives | plan 02 § 8; task brief |
| Scope: Classes IV-VI (heads 450-1000) first; then a restricted pass over Classes I-III limited to heads whose `Adj.` block lexically contains one of our labels (existing files or seed-queue labels). | Roger | plan 02 § 10.1 |
| Emotional states (Class VI) are in scope as inclinations; the candidate's `gloss_hint` reads "a general tendency to ...". | Roger; same rule as plan 1 § 10.3 and plan 14 § 11.5 | plan 02 § 10.2 |
| Frequency is the platform's soft Zipf feature (`freq.zipf_info`): items with `hard_reject` (Zipf < 2.0) are dropped at harvest and counted; the probe band (2.0-2.5) is flagged, not dropped; wordfreq's CC BY-SA data is acceptable. | Roger | plan 02 § 10.3; plan 14 § 11.3 |
| WordNet through the `wn` package with Open English WordNet 2024 under gitignored `data/external/wn/` (platform `setup_external.py --wn`, `wordnet.ensure_oewn()`); no hand parser over WNDB files. | Roger, 2026-09-23 | task brief |
| The Roget head number is provenance only: `source_ref = "roget:604"` on the registry row and `data/candidates/roget/label_heads.json` for our labels; never a field in trait files or the seed queue. | Roger | plan 02 § 10.5 |
| Code in `assistant_axis/gapgen/` (`roget.py`, `roget_pairs.py`, `roget_map.py`, `roget_coverage.py`, `roget_harvest.py`, `roget_recover.py`, `wn_clusters.py`), one CLI `data_analysis/gap_generation/roget_generate.py`; the Gutenberg text under gitignored `data/external/roget/` with its SHA-256 pinned in `roget.py`. | agreed layout | task brief; PLAN_FORMAT § 5 |
| The generator only builds `Candidate` objects and calls `submit_candidates`; it never writes the registry file, trait or role files, `TRAITS_TO_ADD.md`, or `data/seed_queue.json`.  Filter and scorer are run afterwards through the platform CLIs. | keeps the seeding pipeline undisturbed | platform frozen interface; README process § 6 |
| LLM passes: `claude-haiku-4-5-20251001`, temperature 0.0, cached system rubric through platform `llm.call_anthropic_json`, reason-before-verdict JSON, `ROGET_PAIRING_RUBRIC_VERSION = 1` and `ROGET_MAPPING_RUBRIC_VERSION = 1` stamped on outputs, `warn_if_low_parse_rate` at the end of each pass.  The LLM sees only rule disagreements (pairing) and route disagreements or lexical misses (mapping). | judging rule; plan 02 § 3.2-3.3 | `.claude/rules/judging.md` |
| The semantic route embeds with the platform's local model (`Qwen/Qwen3-Embedding-0.6B`, document mode, both sides) only; no OpenAI embeddings in this workstream except inside the recovery hook. | ~2,000 short texts; free | my choice |
| A word harvested from several heads is submitted once, with `source_ref = "roget:604;roget:606"` (primary head first) and the primary head's `gloss_hint`. | `submit_candidates` is idempotent per (generator, run_id, surface, sense_id) | my reading; interface request 4 |
| Pair candidates are written to `<run.dir>/pair_candidates.jsonl` and the partner is named in the `gloss_hint` until `Candidate.partner_hint` exists. | the frozen `Candidate` has no partner field | interface request 1 |
| Two recovery measurements: (R1) verbatim census recall with the whole list hidden by construction ($0, no hook), (R2) the frozen hook on a 20 % hidden run with partners hidden together, glosses from `gloss_hint` by default. | the word list is independent of our list but the *gap-head selection* is not, so R2 must re-run coverage with the hidden labels removed | plan 02 § 6; plan 13 § 3.3-3.4 |
| Derived artefacts (`heads.json`, `head_pairs.json`, `label_heads.json`, `roget_coverage.*`) are tracked under `data/candidates/roget/` so later workstreams need the coordinate, not the text. | `heads.json` ≈ 0.7 MB; the LLM verdicts in the other files are the expensive part | my choice; report if Roger prefers gitignored |
| Every batched call site charges `MultiModelUsage` and writes `usage.json`; every command prints an estimate and has a hard cap; whole-workstream API spend ≈ $3-4 including the platform's filter and scorer on our candidates. | CLAUDE.md hard rules | CLAUDE.md |

## 2. Out of scope

- Variant B (semicolon groups as units) and variant C (WordNet-first generator).
- Roget noun blocks as a roles generator (Class VI person-nouns: 700 Proficient, 941 Knave ...): `--include-nouns` is reserved, not implemented; the roles workstream decides.
- Any edit to `data/traits/instructions/`, `data/roles/instructions/`, `TRAITS_TO_ADD.md`, `data/seed_queue.json`; promotion (platform `gap_registry.py promote`).
- The trait-hood filter and the novelty scorer (platform CLIs are invoked; not reimplemented, not tuned here).
- Plan 13's folds, provenance exclusion, capture-recapture and dashboard; this plan runs one hidden run per seed.
- Third-party Roget parsers, Open Roget's Project, the RDF dump.
- A Qwen3-32B familiarity probe; modernising Roget's vocabulary (archaic words fall to the Zipf feature and the filter).
- Fine intra-head distinctions (cautious vs risk-averse both in 864): the novelty scorer's job.

## 3. Rule files to Read first

Open with the **Read tool** before touching code:
[`.claude/rules/provenance.md`](../../.claude/rules/provenance.md) (`usage.json` on every batched call site; `json_metadata` envelopes with `current_file_input`; UTC timestamps),
[`.claude/rules/entity-naming.md`](../../.claude/rules/entity-naming.md) (stems via `normalize_to_file_name`; `display_form_name` in prompt bodies; US English),
[`.claude/rules/trait-pairs.md`](../../.claude/rules/trait-pairs.md) (traits, clean pairs, `arrangement`, the seed queue and its statuses; the description form the `gloss_hint` copies),
[`.claude/rules/judging.md`](../../.claude/rules/judging.md) (reason-first JSON, `warn_if_low_parse_rate`, rubric version constants),
[`CLAUDE.md`](../../CLAUDE.md) (file-access boundary, the $20 rule, tests mandatory, hotlinks), then
[coding_plan_platform.md](./coding_plan_platform.md) § 5, § 6 and § Frozen interface.

## 4. Existing code to reuse

- Platform (`assistant_axis/gapgen/`, per its plan § 5): `Candidate`, `start_run`, `submit_candidates` (frozen); `paths.DATA_EXTERNAL`, `paths.DATA_CANDIDATES`, `paths.run_dir`, `paths.wn_data_dir`, `paths.hf_cache_dir`; `freq.zipf_info`; `wordnet.ensure_oewn`, `wordnet.sense_info`; `llm.call_anthropic_json`; `cost.estimate_calls_usd`, `cost.confirm_or_abort`, `cost.GuardedUsage`; `embed.LocalEmbedder`, `embed.EmbeddingCache`, `embed.embed_texts`, `representation.trait_text` (M2); `novelty.MetricConfig`, `novelty.NoveltyQuery`, `recovery.recovery_test`, `RecoveryReport` (M3); `normalize.normalize_candidate`.
- Repo: [`assistant_axis/entity_id.py`](../../assistant_axis/entity_id.py) `normalize_to_file_name`, `display_form_name`, `default_data_dir`; [`assistant_axis/arrangements.py`](../../assistant_axis/arrangements.py) `load_corpus_arrangements`, `reciprocal_pairs`, `parse_field` (partner sets for hiding); [`data_analysis/seed_entities.py`](../../data_analysis/seed_entities.py) `load_queue`, `corpus_stems`, `build_registry`, `LIFECYCLE`, `PARKED`; [`assistant_axis/judge.py`](../../assistant_axis/judge.py) `extract_json_blob`, `warn_if_low_parse_rate`, `RateLimiter`; [`assistant_axis/judge_pricing.py`](../../assistant_axis/judge_pricing.py) `MultiModelUsage` (`charge`, `write_json`, `load_or_create`, `merge_from`, `log_line`); [`assistant_axis/atomic_io.py`](../../assistant_axis/atomic_io.py) `atomic_write_text`, `write_jsonl`, `read_jsonl_with_retry`; [`assistant_axis/plot_metadata.py`](../../assistant_axis/plot_metadata.py) `json_metadata`; [`assistant_axis/provenance.py`](../../assistant_axis/provenance.py) `current_file_input`.
- Data: `data/traits/instructions/*.json` (414 files: `positive_label`, `description`, `negative_label`, `arrangement`; 393 single-word labels, 20 hyphenated, 1 two-word; 153 recorded pairs; 69 `non-X`), [`data/seed_queue.json`](../../data/seed_queue.json) (871 trait entries, 867 distinct stems; `description` / `description_draft` / `status`), [`data/traits/trait_antonyms_v4.json`](../../data/traits/trait_antonyms_v4.json) (240 rows, for the pair-recall denominator with `antonym_score ≥ 4`), `data/candidates/corpus_regions.json` (M1 output; by-region breakdowns when present).
- Test style: [`data_analysis/tests/test_seed_entities.py`](../../data_analysis/tests/test_seed_entities.py) (tmp_path fixtures, fake queue, fake clients).

## 5. File layout

```
assistant_axis/gapgen/
  roget.py           ROGET_URL = "https://www.gutenberg.org/cache/epub/10681/pg10681.txt"; ROGET_EXPECTED_SHA256: str | None
                     PARSER_VERSION = 1; DROP_TAGS, KEEP_TAGS (bracket-tag policy); POS_BLOCKS = ("N", "V", "Adj", "Adv", "Phr", "Int")
                     @dataclass Head(id, number, letter, title, klass, class_title, division, section, subsection,
                                     pos: dict[str, list[list[str]]]   # block -> semicolon groups -> items
                                     xrefs: list[tuple[str, str]], n_dropped, tags_seen: dict[str, int], line_start)
                     @dataclass RogetIndex(heads: dict[str, Head], order: list[str], by_subsection: dict[str, list[str]],
                                           text_sha256, parser_version)
                     fetch_roget(dest: Path, *, url=ROGET_URL, dry_run=False) -> Path;  sha256_of(path) -> str
                     check_checksum(path, *, allow_mismatch=False) -> str
                     strip_gutenberg(text) -> str      # header/footer between the *** START / END markers, <-- --> comments, CRLF
                     parse_roget(text) -> RogetIndex
                     clean_item(raw) -> tuple[str | None, list[str]]   # (item or None, tags); drops obsolete/foreign, quotations, > 4 words, digits
                     split_items(block_text) -> list[list[str]]        # ';' groups of ',' items, cross-refs removed into xrefs
                     dispositional_heads(index, *, extra: Collection[str] = ()) -> list[Head]   # number >= 450 plus extra
                     head_profile(head, *, n_adj=15, n_noun=10) -> str
                     extract_fixture(text, numbers: Sequence[str]) -> str
                     save_heads(index, path, *, text_path) / load_heads(path) -> RogetIndex   # json_metadata envelope
  roget_pairs.py     NEG_PREFIXES = ("un", "in", "im", "ir", "il", "dis", "non", "a", "mis"); SUFFIX_SWAPS = (("ful", "less"),)
                     @dataclass NegationScore(n, frac, examples); negation_overlap(adj_a, adj_b) -> NegationScore
                     wn_antonym_links(adj_a, adj_b, wn, *, limit=40) -> int
                     @dataclass HeadPairing(head, partner: str | None, kind: pair|triad|singleton|sequence|unresolved,
                                            members: list[str], evidence: dict, source: rule|llm|unresolved)
                     CONFIRM = dict(n_min=2, frac_min=0.08, wn_min=2)
                     rule_pairs(index, wn, *, heads: Collection[str]) -> dict[str, HeadPairing]
                     residue(index, rule) -> list[tuple[str, list[str]]]          # (subsection key, head ids still open)
                     ROGET_PAIRING_RUBRIC_VERSION = 1; PAIRING_SYSTEM_PROMPT
                     build_pairing_prompt(subsection_heads: list[Head], fixed: list[tuple[str, str]]) -> str
                     parse_pairing(text, head_ids) -> dict | None
                     llm_pairs(residue, index, *, client, model, usage, limiter, dry_run=False) -> dict[str, HeadPairing]
                     merge_pairings(rule, llm) -> dict[str, HeadPairing]; save_pairs / load_pairs
  roget_map.py       @dataclass LabelRecord(stem, label, description: str | None, source: existing|queued, status, partner_stem)
                     load_labels(data_dir, queue_path) -> list[LabelRecord]
                     DERIVATION_SUFFIXES; key_forms(label) -> list[str]; derived_forms(form, wn) -> list[str]
                     @dataclass LexHit(head_id, strength: exact_adj|exact_noun|derived_adj|derived_noun|loose, item, block, group_index)
                     lexical_route(record, index, wn, *, dispositional: Collection[str]) -> list[LexHit]
                     @dataclass SemHit(head_id, sim, rank)
                     semantic_route(records, heads, *, embedder, cache) -> dict[str, list[SemHit]]   # top-5 per stem
                     @dataclass Assignment(primary, secondary, route: agree|llm|none, confidence, lexical, semantic, llm)
                     agreement(lex: list[LexHit], sem: list[SemHit]) -> Assignment | None          # None = needs the LLM
                     ROGET_MAPPING_RUBRIC_VERSION = 1; MAPPING_SYSTEM_PROMPT
                     build_mapping_prompt(items: list[dict], index) -> str; parse_mapping(text, ids) -> dict[str, dict] | None
                     adjudicate(items, index, *, client, model, usage, limiter, batch_size=8, dry_run=False) -> dict[str, Assignment]
                     map_labels(records, index, *, wn, embedder, cache, client, model, usage, limiter, dispositional, dry_run)
                         -> dict[str, Assignment]; save_label_heads / load_label_heads
  roget_coverage.py  ACTIVE_STATUSES = LIFECYCLE + ["tbd", "backlog"]; PARKED = ["not_adopted", "superseded", "exists"]
                     restricted_class_i_iii(index, label_heads) -> dict[str, list[str]]     # head id -> trigger stems
                     @dataclass HeadRow(id, title, path, partner, pair_kind, existing, queued_active, queued_parked,
                                        state: covered|queued|empty, gap_class, n_existing, n_queued_active)
                     coverage(index, pairs, label_heads, *, hidden: Collection[str] = ()) -> CoverageReport(rows, summary, hidden)
                     gap_class(row, partner_row) -> pair_completion|pair_empty|singleton_empty|queued_only|crowded|covered
                     write_coverage(report, json_path, md_path, *, inputs)
  roget_harvest.py   @dataclass HarvestConfig(per_head_cap=10, pair_top=3, max_words=2, classes=(pair_completion, pair_empty,
                                              singleton_empty, queued_only), every_nth: int | None = None, offset=0)
                     @dataclass HarvestItem(surface, head_id, partner_id, group_index, siblings, zipf_min, probe_band,
                                            wn_found, n_senses, score, class_vi: bool)
                     harvest_head(head, partner, *, freq, wn, cfg) -> tuple[list[HarvestItem], dict]   # (items, drop counts)
                     gloss_hint(item, head, partner_head) -> str          # "This means being X: ..." 18-43 words
                     @dataclass PairCandidate(a, b, head_a, head_b, double_confirmed, partner_existing: list[str])
                     pair_candidates(items_a, items_b, wn, *, existing_b: list[str], top=3) -> list[PairCandidate]
                     to_candidates(items, *, generator, run_id, index, pairs) -> list[Candidate]   # dedupe by stem, join source_refs
                     harvest(report, index, pairs, *, cfg, freq, wn) -> HarvestResult(items, pairs, candidates, counts)
                     write_harvest(result, run_dir)                           # candidates preview, pair_candidates.jsonl, harvest_report.md
  wn_clusters.py     TRAIT_ROOT_LEMMAS = ("trait", "disposition", "temperament", "attitude", "character")
                     oewn() -> wn.Wordnet          # after wordnet.ensure_oewn(); lexicon "oewn:2024"
                     adj_synsets(lemma) -> list;  antonyms(lemma) -> list[tuple[str, str]]     # (antonym lemma, synset id)
                     @dataclass Cluster(head_id, head_lemmas, satellites, antonym_head_id); cluster(synset) -> Cluster
                     derivational_adjs(noun_synset) -> list[str]; trait_closure(roots=TRAIT_ROOT_LEMMAS) -> set[str]
                     harvest_wn_antonyms(records: list[LabelRecord], wn, freq) -> list[HarvestItem]   # labels with no partner file
                     harvest_trait_closure(wn, freq) -> list[HarvestItem]
  roget_recover.py   choose_hidden(stems, *, frac, seed, regions, partner_sets) -> list[str]
                     @dataclass VerbatimReport(n_hidden, hit: dict[str, str], recall, by_shape, by_region, pair_recall)
                     verbatim_recall(hidden: list[LabelRecord], surfaces: Collection[str], wn, *, pairs, head_pairs) -> VerbatimReport
                     queries_from_candidates(cands, *, gloss_source: hint|filter, registry_path) -> list[NoveltyQuery]
                     run_recovery(hidden, cands, *, data_dir, config, regions, cache) -> dict   # calls the frozen recovery_test

data_analysis/gap_generation/
  roget_generate.py  fetch | parse | pair | map | coverage | harvest | submit | recover   (§ 7)

data/external/roget/pg10681.txt                 GITIGNORED (covered by the platform's /data/external/ line)
data/candidates/roget/                          tracked
  heads.json  head_pairs.json  label_heads.json  roget_coverage.json  roget_coverage.md
  pairing_usage.json  mapping_usage.json  map_spotcheck.md  known_pairs.json
data/candidates/runs/roget/<run_id>/            per the platform: candidates.jsonl, run.json, usage.json
  plus pair_candidates.jsonl, harvest_report.md, recovery_report.json (heldout runs)
data/candidates/runs/wn_clusters/<run_id>/      same shape
assistant_axis/tests/fixtures/roget_sample.txt  ~25 heads verbatim (public domain), built once with extract_fixture
```

Parser notes for Opus.  The text is US-ASCII with CRLF; `strip_gutenberg` normalises line endings, drops everything outside the `*** START OF` / `*** END OF` markers and removes `<-- ... -->` editorial comments (multi-line, non-greedy).  Structure lines: `^CLASS\s+([IVX]+)` (the class title is the next non-empty line), `^DIVISION\s+\(?([IVX]+)\)?`, `^SECTION\s+([IVX]+)\.?\s*(.*)`, and all-caps numbered subsection lines `^\s*(\d+)\.\s+([A-Z][A-Z ,'\-]+)$`.  Head lines: `^\s*#?(\d+[a-z]?)\.\s+(.+?)\s*--\s*(N|V|Adj|Adv|Phr|Int)\.\s*(.*)$` (plan 02 measured 1,032 matches, 994 distinct numbers, 38 lettered heads such as `604a`; the optional `#` is tolerance, not a claim).  A POS block starts at `^\s*(N|V|Adj|Adv|Phr|Int)\.\s` and runs to the next block or head; lines are joined with spaces before `split_items`.  Cross-references `&c\.?\s*(\([^)]*\))?\s*(\d+[a-z]?|\d+\.\d)` become `xrefs` (a `604.1` target is `604a`); `&c\.? (n|v|adj|adv)\.` is dropped.  Item policy: a leading `^` (the obsolete dagger) or a tag in `DROP_TAGS` (`Obs.`, `Obs3`, `Lat.`, `Fr.`, `Grk.`, `Ger.`, `It.`, `Sp.`, ... every language tag) drops the item and counts it; tags in `KEEP_TAGS` (`U.S.`, `Colloq.`, `Slang`, `Naut.`, `Law`, ...) keep the item with the tag recorded; an unknown bracket tag keeps the item and is counted in `tags_seen`, and `parse` prints the census so the lists can be extended.  Parentheticals are removed; items that are quotations, contain digits, or exceed four words are dropped.  `head_profile` is `"{title}. {section} / {subsection}. Adjectives: a, b, ... Nouns: x, y, ..."`.

The `wn` calls to use (verify against the installed version; the fake-`wn` tests pin our wrapper, not `wn`): `wn.config.data_directory = wn_data_dir()`; `en = wn.Wordnet("oewn:2024")`; `en.synsets(lemma, pos="a")` (satellites have `synset.pos == "s"`); `sense.get_related("antonym")` and `sense.get_related("derivation")` at sense level (`en.senses(lemma, pos="a")`); `synset.get_related("similar")` for the cluster; `synset.hyponyms()` for the closure; `synset.definition()`, `synset.lemmas()`.

## 6. Data schemas

**`heads.json`** (envelope: `json_metadata(payload, inputs=[current_file_input("roget_text", text_path, extras={"sha256": ..., "parser_version": "1"})])`), one object per head:

```json
{"id": "604", "number": 604, "letter": "", "title": "Resolution",
 "klass": "V", "class_title": "Words relating to the voluntary powers", "division": "I. Individual volition",
 "section": "I. Volition in general", "subsection": "1. Acts of volition",
 "pos": {"N": [["resolution", "determination", "will"], ["strength of mind", "firmness"]],
         "Adj": [["resolved", "resolute", "determined"], ["strong-willed", "strong-minded"], ["unflinching", "firm"]]},
 "xrefs": [["605", "irresolution"]], "n_dropped": 3, "tags_seen": {"Obs.": 2, "Lat.": 1}, "line_start": 41230}
```

(Adjective contents above are illustrative; the test fixture's expected values are taken from the text.)

**`head_pairs.json`** (envelope; inputs: `heads.json`, rubric version):

```json
{"604": {"partner": "605", "kind": "pair", "members": ["604", "605"], "source": "rule",
         "evidence": {"adjacent": true, "negation": {"n": 4, "frac": 0.11, "examples": [["resolute", "irresolute"]]},
                      "wn_links": 3, "llm": null}},
 "604a": {"partner": null, "kind": "triad", "members": ["604", "604a", "605"], "source": "llm",
          "evidence": {"adjacent": true, "negation": {"n": 0, "frac": 0.0, "examples": []}, "wn_links": 0,
                       "llm": {"reason": "Perseverance sits between resolution and irresolution as a third pole", "confidence": 0.7}}}}
```

**`label_heads.json`** (envelope; the Roget coordinate other workstreams read):

```json
{"cautious": {"label": "cautious", "source": "existing", "status": null, "partner_stem": "bold",
              "primary": "864", "secondary": ["459"], "route": "agree", "confidence": 1.0,
              "lexical": [{"head_id": "864", "strength": "exact_adj", "item": "cautious", "block": "Adj", "group_index": 0},
                          {"head_id": "459", "strength": "exact_adj", "item": "cautious", "block": "Adj", "group_index": 4}],
              "semantic": [{"head_id": "864", "sim": 0.61, "rank": 1}, {"head_id": "459", "sim": 0.52, "rank": 2}, {"head_id": "860", "sim": 0.49, "rank": 3}],
              "llm": null},
 "kind_to_animals": {"label": "kind-to-animals", "source": "existing", "status": null, "partner_stem": null,
              "primary": "906", "secondary": [], "route": "llm", "confidence": 0.8, "lexical": [],
              "semantic": [{"head_id": "906", "sim": 0.44, "rank": 1}, {"head_id": "910", "sim": 0.41, "rank": 2}],
              "llm": {"reason": "Benevolence toward animals is the head's own sense; philanthropy is people-directed.", "rubric_version": 1}}}
```

**`roget_coverage.json`** row (envelope; `roget_coverage.md` renders the same rows):

```json
{"id": "863", "title": "Rashness", "path": "VI > I. Affections in general > 3. ...", "partner": "864", "pair_kind": "pair",
 "existing": [], "queued_active": ["reckless"], "queued_parked": [], "n_existing": 0, "n_queued_active": 1,
 "state": "queued", "gap_class": "pair_completion", "partner_state": "covered", "partner_existing": ["cautious", "risk_averse"]}
```

Summary block: `{"n_heads": 561, "by_state": {"covered": 290, "queued": 95, "empty": 176}, "by_gap_class": {...}, "by_section": {...}, "class_i_iii_added": 14, "hidden": []}`.

**Harvest config** (`--config`, default values in `HarvestConfig`; recorded in `run.json` args):

```json
{"per_head_cap": 10, "pair_top": 3, "max_words": 2, "classes": ["pair_completion", "pair_empty", "singleton_empty", "queued_only"],
 "every_nth": 5, "offset": 0, "zipf_hard": 2.0, "include_wn": false}
```

**Candidate as submitted** (`candidates.jsonl` is written by `submit_candidates`; this is the `Candidate` the generator builds):

```json
{"surface": "unflinching", "generator": "roget", "run_id": "2026-10-06a", "rank": 17, "score": 3.62,
 "gloss_hint": "This means being unflinching: a stable disposition toward resolution (volition in general), of a piece with resolute, determined and strong-willed; the opposite pole is irresolution.",
 "sense_id": 1, "source_ref": "roget:604"}
```

A Class VI item reads "a general tendency to feel dejection and act from it, of a piece with ...".  The hint never names one of our labels.

**`pair_candidates.jsonl`** row: `{"a": "unflinching", "b": "vacillating", "head_a": "604", "head_b": "605", "double_confirmed": false, "partner_existing": []}`; for a `pair_completion` head the `b` side is the existing stem(s) and `partner_existing` lists them.

**`recovery_report.json`**: `{"mode": "hidden_frac", "seed": 0, "frac": 0.2, "n_hidden": 121, "n_gap_heads_opened": 47, "n_candidates": 388, "gloss_source": "hint", "verbatim": {"recall": 0.62, "by_shape": {"single": 0.66, "hyphen": 0.2, "multiword": 0.0}, "by_region": {...}, "pair_recall": 0.41}, "hook": <RecoveryReport.to_json()>, "config_version": "2026-10-03"}`; in `--all-hidden` mode `hook` is null and `verbatim` covers all 414.

## 7. CLI

`roget_generate.py <command>`; common flags: `--data-dir` (default `data/`), `--queue` (default `data/seed_queue.json`), `--out` (default `data/candidates/roget`), `--text` (default `data/external/roget/pg10681.txt`), `--model claude-haiku-4-5-20251001`, `--dry-run` (prints the plan, counts, the cost estimate and the first three prompts; writes nothing, calls nothing), `--budget-usd` (hard cap through `GuardedUsage`; the loop stops at the cap and the usage file is still written), `--confirm-expensive` (required when the estimate exceeds the budget; `confirm_or_abort` from the platform; the $20 line is unreachable here but the guard is the same).

- `fetch [--url U] [--force]`: downloads the text to `data/external/roget/pg10681.txt`, prints size and SHA-256, compares with `ROGET_EXPECTED_SHA256` (first run: the constant is `None`; the command prints the value to pin).  No API cost.
- `parse [--allow-checksum-mismatch] [--fixture 1,2,82,83,600-610,862-865,897,898]`: refuses a mismatched checksum unless allowed; writes `heads.json`; prints head count, distinct numbers, lettered heads, heads with an `Adj.` block, the bracket-tag census, and drop counts; `--fixture` writes `assistant_axis/tests/fixtures/roget_sample.txt` instead.
- `pair [--no-llm] [--limit-subsections N]`: rules over the dispositional set, then the residue.  Estimate: one call per subsection with residue, ≈ 90 × (1.8k input of which 1.2k cached, 0.9k output) ≈ **$0.25**; default cap $1.  Writes `head_pairs.json`, merges into `pairing_usage.json`, prints the known-pairs check and the unresolved list.
- `map [--no-llm] [--existing-only] [--limit N]`: lexical route for every record, semantic route with the local embedder (`EmbeddingCache` under the platform's cache dir), agreement, then adjudication of disagreements and lexical misses.  Estimate: ≈ 600 items / 8 per call = 75 calls × (2.5k input, 0.8k output) ≈ **$0.45**; default cap $2.  Writes `label_heads.json`, `mapping_usage.json`, `map_spotcheck.md` (40 random assignments with label, first clause of the description, lexical hits, semantic top-3, route, chosen head); prints the agreement rate and route counts.
- `coverage [--hidden-file F]`: no calls; writes `roget_coverage.{json,md}`; with `--hidden-file` writes to the run directory instead (used by `recover`).
- `harvest --run-id R [--config F] [--classes ...] [--per-head-cap N] [--pair-top N] [--every-nth K --offset J] [--include-wn]`: no calls; writes a preview `candidates.jsonl`, `pair_candidates.jsonl` and `harvest_report.md` under `data/candidates/runs/roget/R/`; prints counts by gap class, Zipf band fractions, and the **downstream estimate** (n × ≈ $0.0009 filter, n × ≈ $0.00005 novelty, per the platform's rates).  `--every-nth 5` keeps every fifth gap head in section order together with its partner (the pilot).  `--include-wn` also runs the `wn_clusters` harvest and writes it to `runs/wn_clusters/R/`.
- `submit --run-id R`: `start_run("roget", R, args=vars(args))`, `submit_candidates(cands, run=run)`, `run.finish()`; prints the `SubmitReport` and the two platform commands to run next (`traithood_filter.py --batch-id R --unfiltered`, `novelty_score.py score --batch-id R --unscored`).  Idempotent.  Refuses if `candidates.jsonl` preview is missing (harvest first).
- `recover (--all-hidden | --hidden-frac 0.2 --seed S) [--gloss-source hint|filter] [--submit]`: `--all-hidden` hides every label, harvests with the cap lifted, reports verbatim recall (R1), $0.  `--hidden-frac` hides the sample plus arrangement partners, recomputes coverage and harvest, reports verbatim recall and then calls the frozen `recovery_test(queries, hidden, data_dir=..., config=MetricConfig.load(), hide_partners=True, regions=...)` with glosses from `gloss_hint` (default) or from the registry's filter block (`--gloss-source filter`; refuses if > 5 % of the run's keys are unfiltered).  No LLM calls; the hook's embedding cost is cents.  `--submit` also registers the run as `R-heldout-s<S>`.  Writes `recovery_report.json`.

## 8. Acceptance tests, written first

Unit tests in `assistant_axis/tests/test_gapgen_roget.py`, `test_gapgen_roget_pairs.py`, `test_gapgen_roget_map.py`, `test_gapgen_roget_coverage.py`, `test_gapgen_roget_harvest.py`, `test_gapgen_wn_clusters.py`, `test_gapgen_roget_recover.py`, and `data_analysis/tests/test_gap_generation_roget_cli.py`.  None calls an API, downloads anything, or loads a model: fake Anthropic client (counts calls, returns canned JSON, raises if called in dry-run), fake `wn` module, the platform's deterministic hash embedder.  Tests on the full text or the real OEWN skip when `data/external/roget/pg10681.txt` or `data/external/wn/` is absent.  Recorded-output acceptance tests (`test_gapgen_roget_acceptance.py`) read the saved outputs and skip when absent.

- **Parser** (fixture of ≈ 25 heads: 1, 2, 82, 83, 600-610, 862-865, 897, 898, built once by `extract_fixture` and checked by eye; expected values are read off the fixture when the test is written and say so in a comment): head count equals the fixture set; `604a` → number 604, letter `a`, title `Perseverance`; class/division/section/subsection fields of 604 as printed; two adjectives of 604 present in `pos["Adj"]`; semicolon groups preserved; an item marked `^` or `[Obs.]` absent and counted in `n_dropped`; a `[U.S.]` item kept with the tag in `tags_seen`; `&c 605` present in `xrefs` and absent from items; `clean_item` cases (parenthetical stripped, trailing period, `&c. n.` removed, digit item dropped, five-word item dropped, hyphenated word kept); `head_profile` starts with the title and lists ≤ 15 adjectives; `dispositional_heads` returns numbers ≥ 450 plus `extra`; `check_checksum` raises on mismatch unless allowed; `save_heads`/`load_heads` round-trip with the envelope.  Full text (skip if absent): 1,032 head lines, 994 distinct numbers, 38 lettered heads, 927 heads with an `Adj.` block, no unknown bracket tag with > 20 occurrences, every dispositional head has a subsection.
- **Pairing**: `negation_overlap` on synthetic lists (un-/in-/dis-/non-, -ful/-less, symmetric, `frac` uses the shorter list); `wn_antonym_links` with the fake `wn`; `rule_pairs` on a synthetic subsection (two confirmed adjacent pairs, one lettered head, one unconfirmed head) leaves exactly the lettered and unconfirmed heads in `residue`; the prompt's "reason" precedes "groups" in schema and example and already-paired heads are listed as fixed; `parse_pairing` requires every head once, handles fences, rejects unknown ids; an unparseable subsection is retried once, then `unresolved`; `merge_pairings` keeps rule pairs over LLM output; usage charged per call.  Full text (skip if absent): `known_pairs.json` (≈ 40 hand-listed pairs whose titles the test first checks against the parse; a title mismatch drops the pair and is printed, not failed) ≥ 90 % paired as listed; `600`/`601`, `604a`, `609a`, `615a` resolved as something other than `unresolved`; unresolved ≤ 3 % of heads.
- **Mapping**: `key_forms` (lowercase, standard suffix dropped, hyphen and space variants); `derived_forms` via fake-`wn` derivation and the suffix fallback (`cautious` ↔ `caution`, `absolutist` ↔ `absolutism`); `lexical_route` on fixture heads (`resolute` → 604 `exact_adj`; `resolution` → 604 `exact_noun`; a multiword item matched by last word → `loose`; dispositional heads ranked first); `agreement` truth table (lexical top in semantic top-3 → `agree`; lexical hits none in top-3 → `None`; no lexical hit → `None`; two lexical hits in top-5 → primary plus secondary); `semantic_route` with the hash embedder returns five sorted hits per stem; the mapping prompt puts "reason" before "primary", uses `display_form_name` on labels, and lists only the offered head ids; `parse_mapping` rejects a primary outside the offered ids and counts it; `adjudicate` is called only for `None` assignments (fake client call count equals the number of disagreements, batches of 8); `map_labels` end to end on six synthetic labels writes every route type.
- **Coverage**: `gap_class` truth table (partner covered and self empty → `pair_completion`; both empty → `pair_empty`; no partner and empty → `singleton_empty`; queued-active only → `queued_only`; ≥ 3 existing → `crowded`); parked statuses appear in `queued_parked` and never make a head `queued`; `hidden` removes stems before states are computed; `restricted_class_i_iii` adds a head < 450 only on an `exact_adj` or `derived_adj` lexical hit; the markdown lists gap classes in the order pair_completion, pair_empty, singleton_empty, queued_only.
- **Harvest**: hard-reject items dropped and counted, probe-band items kept and flagged; one representative per semicolon group (highest Zipf), cap respected, items over `max_words` dropped, cross-refs never harvested; `gloss_hint` starts "This means being", is 18-43 words for a one-sibling and a ten-sibling head, uses the Class VI wording for class `VI`, and never contains any label from a supplied label set; `pair_candidates` marks `double_confirmed` from the fake `wn` and uses `existing_b` for completion heads; `to_candidates` dedupes by `normalize_to_file_name`, keeps the best score, joins `source_ref` with `;` primary first, ranks by score, sets `sense_id = 1`, and yields valid frozen `Candidate` objects; output order is deterministic; `--every-nth` selection keeps partners together.
- **WordNet clusters** (fake `wn`): `antonyms`, `cluster`, `derivational_adjs`, `trait_closure` (bounded depth), `harvest_wn_antonyms` emits only for records whose partner has no file; real-DB smoke test (skip without `data/external/wn`): `antonyms("cautious")` is non-empty.
- **Recovery**: `choose_hidden` is deterministic by seed, stratifies by region when given, and adds every arrangement partner; `verbatim_recall` matches hyphen/space variants and derived forms and computes `pair_recall` only over hidden pairs whose heads are paired in `head_pairs`; `queries_from_candidates` builds `NoveltyQuery` with the hint gloss, or the filter gloss from a fake registry, and raises when > 5 % lack one; `run_recovery` calls a monkeypatched `recovery_test` with `hide_partners=True` and the hidden list and writes `recovery_report.json`.
- **CLI and cost guard**: every subcommand under `--dry-run` on a tmp tree writes nothing (directory snapshot before and after) and the fake client is never called; `pair` and `map` refuse an estimate over `--budget-usd` without `--confirm-expensive`; a `GuardedUsage` cap set to $0.001 stops the pairing loop and `pairing_usage.json` still exists; `submit --dry-run` leaves the registry byte-identical; `submit` twice yields `n_new = 0` the second time.
- **Acceptance (recorded outputs, skip if absent)**: pairing parse rate ≥ 99 % and known pairs ≥ 90 %; mapping parse rate ≥ 99 %, ≥ 90 % of existing labels have a primary head, `map_spotcheck.md` has 40 rows, agreement rate recorded; every dispositional head has a coverage row; R1 verbatim recall ≥ 0.70 over single-word labels and the opposed-head pair recall recorded; the 20 % run's `recovery_report.json` carries strict and loose hook recall (recorded, no threshold: first measurement); `pairing_usage.json` + `mapping_usage.json` totals < $3.

Commands that must pass at the end of every task:

```
uv run pytest assistant_axis/tests/test_gapgen_roget*.py assistant_axis/tests/test_gapgen_wn_clusters.py data_analysis/tests/test_gap_generation_roget_cli.py -q
uv run pytest -q                                              # whole suite, unchanged
uv run python data_analysis/check_arrangements.py --quiet
uv run python tools/sync_entity_lists.py --check
git status --porcelain data/traits data/roles data/seed_queue.json   # must be empty
```

## 9. Ordered task checklist

1. `roget.py` fetch, checksum, `strip_gutenberg`; `fetch`/`parse --dry-run` in the CLI skeleton.  Run `fetch`, pin `ROGET_EXPECTED_SHA256`.  Test: checksum guard, dry-run writes nothing.
2. Parser: structure lines, heads, POS blocks, `split_items`, `clean_item`, tags, xrefs; `extract_fixture`; build and eyeball the fixture; fixture tests; full-text invariant tests.  If the head-line count is not 1,032, the parser is wrong (the checksum pins the text): fix, do not relax the test.
3. `head_profile`, `dispositional_heads`, `save_heads`/`load_heads`; run `parse`; commit `heads.json`.  Test: envelope, counts.
4. `wn_clusters.py` core (`oewn`, `adj_synsets`, `antonyms`, `derivational_adjs`, `cluster`) after the platform's `setup_external.py --wn`.  Test: fake `wn`, real smoke.
5. `roget_pairs.py` rules and `known_pairs.json` (Fable's list below, checked against parsed titles).  Test: synthetic and full-text rule results; print the confirmation-threshold sweep on the known pairs and keep `CONFIRM` at the values that pair ≥ 90 % with ≤ 2 wrong pairs.
6. Pairing LLM pass: rubric v1, prompt, parser, merge, usage, parse rate; `pair --dry-run`; run `pair` (≈ $0.25); commit `head_pairs.json`, `pairing_usage.json`; note triads and unresolved heads for the report.
7. `roget_map.py` `load_labels`, `key_forms`, `derived_forms`, `lexical_route`.  Test: fixture heads, derivations.
8. Semantic route with the platform embedder (`LocalEmbedder`, `EmbeddingCache`, `trait_text`; see interface request 2).  Test: hash embedder.  If M2's `embed.py` is not merged yet, run with the hash embedder behind `--embedder hash` (every lexical miss then goes to the LLM; ≤ 2× cost) and re-run `map` later.
9. `agreement`, mapping rubric v1, `adjudicate`, `map_labels`, `map` CLI with `map_spotcheck.md`; `map --dry-run`; run `map` (≈ $0.45); commit `label_heads.json`, `mapping_usage.json`, `map_spotcheck.md`.  **Pilot readout A** (§ 10) to Roger.
10. `roget_coverage.py` and `coverage`; commit `roget_coverage.{json,md}`.  Test: truth table, restricted I-III, markdown order.
11. `roget_harvest.py` (`harvest_head`, `gloss_hint`, `pair_candidates`, `to_candidates`, `write_harvest`) and `harvest`/`submit`.  Test: harvest module, CLI dry-runs, idempotent submit.
12. **Pilot B**: `harvest --every-nth 5 --offset 0 --run-id <date>-pilot` → `submit` → platform `traithood_filter.py --batch-id <date>-pilot --unfiltered` → `novelty_score.py score --batch-id <date>-pilot --unscored` → readout (§ 10).  Roger's decision.
13. `roget_recover.py` and `recover`: run `--all-hidden` now (R1, $0); run `--hidden-frac 0.2 --seed 0` once M3 exists (R2); commit both reports under `runs/roget/`.  Test: recover module, CLI.
14. WordNet sibling: `harvest_wn_antonyms` (partner-less existing labels; ≈ 69 `non-X` plus one-way pointers), `harvest_trait_closure`; `harvest --include-wn`; submit as generator `wn_clusters`.  Test: fake `wn`.  `harvest_trait_closure` is the last thing cut if time runs short.
15. Full run after Roger's decision (§ 10): `harvest`, `submit`, the two platform commands, `recover --hidden-frac 0.2 --gloss-source filter`; acceptance tests pass on recorded outputs; add the `data/candidates/roget/` and `data/external/roget/` paragraphs to [`data/README.md`](../../data/README.md) and a short "Roget coverage map" paragraph to `AGENT_NOTES.md` under the `trait-pairs` rule marker, then `uv run python tools/sync_agent_notes.py`; write the report (§ 11).

Known pairs for `known_pairs.json` (from memory of the 1911 synopsis; the test checks titles against the parse and drops mismatches with a printed line, and Opus removes any that the text contradicts): 1/2 Existence/Inexistence, 82/83 Conformity/Unconformity, 602/603 Willingness/Unwillingness, 604/605 Resolution/Irresolution, 606/607 Obstinacy/Tergiversation, 613/614 Habit/Desuetude, 618/619 Good/Evil, 682/683 Activity/Inactivity, 684/685 Haste/Leisure, 698/699 Skill/Unskillfulness, 702/703 Cunning/Artlessness, 704/705 Difficulty/Facility, 742/743 Obedience/Disobedience, 748/749 Freedom/Subjection, 822/823 Sensibility/Insensibility, 825/826 Excitability/Inexcitability, 827/828 Pleasure/Pain, 831/832 Content/Discontent, 836/837 Cheerfulness/Dejection, 858/859 Hope/Hopelessness, 861/862 Courage/Cowardice, 863/864 Rashness/Caution, 865/866 Desire/Indifference, 873/874 Repute/Disrepute, 878/879 Pride/Humility, 880/881 Vanity/Modesty, 885/886 Insolence/Servility, 888/889 Friendship/Enmity, 894/895 Courtesy/Discourtesy, 897/898 Love/Hate, 906/907 Benevolence/Malevolence, 916/917 Gratitude/Ingratitude, 918/919 Forgiveness/Revenge, 922/923 Right/Wrong, 931/932 Approbation/Disapprobation, 939/940 Probity/Improbity, 942/943 Disinterestedness/Selfishness, 944/945 Virtue/Vice, 946/947 Innocence/Guilt, 953/954 Temperance/Intemperance, 958/959 Sobriety/Drunkenness, 960/961 Purity/Impurity.  Triads and lettered heads to check by eye: 600 Will / 601 Necessity, 604a Perseverance, 608 Caprice, 609 Choice / 609a Absence of choice / 610 Rejection, 615 Motive / 615a Absence of motive / 616 Dissuasion.

## 10. Pilot

Two readouts before the full harvest; both go to Roger as tables in chat with the files hotlinked.

**Readout A** (after task 9; pairing + mapping in full, ≈ $0.70 from `pairing_usage.json` and `mapping_usage.json`): the known-pairs check (hits, misses with titles, triads, unresolved count); `map_spotcheck.md` (40 rows); the lexical/semantic agreement rate, route counts (agree / llm / none), and the ten lowest-confidence LLM assignments with reasons; the coverage summary (heads by state and by gap class, per Roget section; the Class I-III heads added and their trigger labels); the five most crowded heads with their stems.  Roger decides: the `CONFIRM` thresholds, whether multi-head assignment (primary + secondary) is the right grain, whether the I-III restricted set looks sane, and which gap classes the harvest includes (`queued_only` in or out).

**Readout B** (task 12; every fifth gap head with its partner ≈ 40-50 heads → ≈ 300-400 candidates and ≈ 60 pair candidates; filter ≈ $0.35, novelty ≈ $0.05): candidates per head and Zipf band fractions; filter verdict and tag fractions, with the `state` tag rate on Class VI heads shown separately; novelty `covered` / `new` / `grey` fractions and the LLM fraction; pair candidates: how many `double_confirmed`, how many the scorer flagged `pair_completion`; a 20-row sample for Roger (10 `new`, 5 `covered` with their neighbour, 5 pair candidates); the ten weakest `gloss_hint`s beside their heads.  **Yield per dollar** = rows with filter verdict `trait`, no `polysemy`, and decision `new` or flag `pair_completion`, divided by the pilot's `usage.json` totals (filter + novelty) plus one fifth of readout A's cost, stated as such.  Roger decides: `per_head_cap`, the Class VI policy (keep, keep with the state tag, or drop), whether pair candidates are submitted as pairs or singly, whether the hint gloss is good enough for R2 or R2 waits for filter glosses, and the go for the full run (≈ 1,500-2,500 candidates; filter ≈ $1.5-2.5, novelty ≈ $0.2-0.5).

## 11. Report at the end

One page at `reports/trait_gap_generation/acceptance_02_roget_wordnet.md`: modules built against § 5; deviations from this plan with reasons (including any known pair the text contradicted and any parser tolerance added); the § 8 commands verbatim with pass counts; cost per step from `pairing_usage.json`, `mapping_usage.json`, the run `usage.json` files and the platform's filter/novelty `usage.json` for our batches, per model; the two pilot readouts and Roger's decisions; the full-run numbers (heads by state, candidates by gap class, filter and novelty fractions, pair candidates, yield per dollar); R1 and R2 recovery numbers by label shape and region; the coverage map's headline (the empty heads list, sorted by section, as the deliverable Roger reads); open `QUESTIONS.md` entries; and the interface requests' status.

## 12. Escalation

Opus retries a failing step once with a changed approach, then asks Fable (diff review, architecture calls, stubborn failures), then Roger through [`QUESTIONS.md`](./QUESTIONS.md) in its format (`N. [02] question. Assumption proceeded under: ... Status: open`), proceeding under the stated assumption unless the answer would make the work useless.  Pre-registered entries Opus copies in at the start and proceeds under: (1) `heads.json` and the other derived files are tracked under `data/candidates/roget/`; (2) parked queue statuses (`not_adopted`, `superseded`, `exists`) are shown in the coverage rows but never count as coverage; (3) the pair partner travels in `gloss_hint` and `pair_candidates.jsonl` until interface request 1 is granted; (4) the Class I-III trigger set is existing labels plus active queued labels; (5) a known pair whose titles the text contradicts is dropped from the test and listed in the report; (6) if M2's `embed.py` is not available at task 8, the semantic route runs on the hash embedder and `map` is re-run later.  Anything that would write to a trait or role file, the seed queue or the registry file directly, exceed a command's cap, or change a frozen signature stops and asks.

## Interface requests

> **Resolved 2026-09-24**: see `coding_plan_platform.md` § "Interface resolutions"; all five granted except item 4, where the registry merges duplicate submissions within a run (one `Candidate` per source reference; drop the generator-side `;` join).
 (to the platform; each with the fallback this plan uses meanwhile)

1. **`Candidate.partner_hint: str | None`**, carried into the registry row's `sources[]` entry and read by `gap_registry.py promote` to set `partner` on both queue entries when both members are promoted.  Fallback: `<run.dir>/pair_candidates.jsonl` plus the partner named in `gloss_hint`; `promote` then needs a by-hand `--partner`.
2. **Export the local embedding path from `assistant_axis.gapgen`**: `LocalEmbedder`, `EmbeddingCache`, `embed_texts` and `trait_text` (or a single `embed_local(texts, *, cache) -> np.ndarray`), so the semantic route does not import M2's module path directly.  Fallback: import from `assistant_axis.gapgen.embed` and `assistant_axis.gapgen.representation`; if those move, `roget_map.py` breaks loudly at import.
3. **`wordnet.oewn() -> wn.Wordnet`** returning the configured lexicon handle, so `wn_clusters.py` shares the data directory and lexicon id.  Fallback: `wn_clusters.oewn()` calls `ensure_oewn()` and opens `wn.Wordnet("oewn:2024")` itself.
4. **Clarify `submit_candidates` idempotency** for two `Candidate`s in one run with the same `(surface, sense_id)` but different `source_ref`: merged as two sources, or the second dropped?  This plan assumes dropped and dedupes generator-side, joining `source_ref` with `;`.  If the registry merges, one `Candidate` per head is cleaner and `to_candidates` loses the join.
5. **`RecoveryReport.to_json()` should include `config_version`, `t_hi`, `t_lo` and `gloss_source` if passed through**, so a recovery report is self-describing.  Fallback: `roget_recover.run_recovery` adds them beside the hook's JSON, as § 6 shows.

## Frozen for later workstreams

`data/candidates/roget/label_heads.json` (stem → `primary`, `secondary`) and `head_pairs.json` (head → `partner`, `kind`) are the Roget coordinate any workstream may read; `roget.load_heads()`, `roget_coverage.coverage(index, pairs, label_heads, *, hidden=())` and `roget_harvest.harvest(...)` keep their signatures after acceptance.  The registry `source_ref` form is `roget:<id>` with `;`-joined multiples and `oewn:<synset id>` for the WordNet stream.

## Review amendments (2026-09-24)

- Runs after platform M1 is merged for the M1-only tasks; the tasks that need M2/M3 wait for
  those milestones' acceptance (see the platform plan's amendment 1).
- Recorded-output acceptance numbers that are first measurements (recall, pair recall,
  known-label pass, precision spot checks) are report-and-decide for Roger, per the platform
  plan's amendment 2; parse rate, cost caps, `usage.json` presence and the untouched-corpus
  check remain hard gates.
- The registry live log is gitignored and only the compacted snapshot is tracked (platform
  amendment 3); `keys.txt` and the run directories are unaffected.

## Revision for the interface as built (2026-10-08, Fable; this section overrides §§ 4, 5, 7, the recovery parts of §§ 6, 8, 9 and the "Interface requests" where they differ)

The scorer side of the frozen interface was never built; M3 is retrieve-then-judge and the recovery
harness is the platform close-out job ([coding_plan_platform.md](./coding_plan_platform.md),
"Interface as built").  What changes for this workstream:

1. **Use only the registry API** (`Candidate`, `start_run`, `submit_candidates`, `SubmitReport`,
   `RunContext`); drop § 5's `queries_from_candidates` and `run_recovery`, § 7's `recover` command and
   `recovery_report.json`; keep the Roget parser and its 25-head fixture, the opposed-head
   reconstruction, the two-route mapping of corpus labels onto heads, the **coverage report** (which
   needs only the corpus and the parsed heads and is this workstream's main product besides the
   harvest), the harvest with its per-head cap, and the WordNet sibling stream.  Task 8's embedding
   route uses `assistant_axis.gapgen.embed` as it exists (the OpenAI backend with its cache; the plan's
   `embed_local` facade was not built: name the actual functions after reading `embed.py`).
2. **Every run writes a tracked `candidates.jsonl`** in its run directory before submitting (the
   registry log is per checkout and git-ignored); the main checkout resubmits with
   `gap_registry.py submit --from`.  `partner_hint` is carried where an opposed head gives one.
3. **Filtering, scoring and recovery are the platform's CLIs**, run by Fable after submission
   (`traithood_filter.py --run roget/<R>`, `novelty_score.py score --run roget/<R>`,
   `recovery_test.py --generator roget --run-id <R>`).  This workstream's acceptance stops at the
   coverage report and a correct, tested, submitted harvest with its counts.
4. **Costs**: the generator's own paid calls are the embeddings of task 8 (cents).  The platform's
   cost on the harvest is about $0.004 per word for M1 and $0.018 per passing word for M3; a harvest
   of 200-400 words plus the WordNet stream is about $10-15, run live after the pilot's readout.
5. **Pilot**: `harvest --every-nth 5` as run `<date>-pilot`, submitted; Fable runs M1 and M3 on it
   live and the recovery test, and writes the readout; the full harvest follows on Roger's go.
6. **Where the agent works**: its own worktree (first step `git merge --ff-only anthropic-vllm-uv`),
   `.env` copied from the main checkout, `data/external/` and `runpod_workspace/` symlinked from it;
   Roget 1911 downloads into `data/external/roget/` with its Gutenberg licence beside it (record the
   URL and date in a README there); Open English WordNet is already under `data/external/wn/`.  The
   file-access boundary of PLAN_FORMAT.md applies unchanged.

**As built (2026-10-08, branch `gen02-roget`, ten commits).**  Package `assistant_axis/gapgen/generators/roget/`
(`parse`, `pairs`, `mapping`, `coverage`, `harvest`, `wn_clusters`), CLI
[roget_generate.py](../../data_analysis/gap_generation/roget_generate.py) (`fetch | parse | pair | map | coverage |
harvest | submit`), derived data and the coverage map under [data/candidates/roget/](../../data/candidates/roget/)
([roget_coverage.md](../../data/candidates/roget/roget_coverage.md)); the WordNet stream submits under its own generator
name `wn_clusters`, so a harvest is two runs, `runs/roget/<run_id>/` and `runs/wn_clusters/<run_id>/`.  No LLM pass: pairing,
placement and the gloss hints are rules (221 of 576 dispositional heads unresolved; questions 37-42 in
[QUESTIONS.md](./QUESTIONS.md)).  Pilot `2026-10-08-pilot`: 185 Roget words and 87 WordNet words, readout
[readout.md](../../data/candidates/runs/roget/2026-10-08-pilot/readout.md); embeddings $0.0135.
