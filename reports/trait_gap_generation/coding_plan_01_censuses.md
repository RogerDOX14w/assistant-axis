# Coding plan: workstream 1, psycholexical censuses (generator id `censuses`)

Written 2026-09-23 (Fable) in the [PLAN_FORMAT.md](./PLAN_FORMAT.md) shape from
[01_psycholexical_censuses.md](./01_psycholexical_censuses.md) and its Resolution, against the
"Frozen interface" of [coding_plan_platform.md](./coding_plan_platform.md).  Variant A: the TDA
2,818 first, then Allport-Odbert above the platform's hard-reject line, each as its own run with
a Roger go between them.  Roger's review comments go into this file.

## 1. Decisions already made

| decision | reason | source |
|---|---|---|
| Variant A: TDA (CC0, familiarity and frequency built in, no OCR) first; then Allport-Odbert words not in TDA, above the floor; the two Allport stages (Zipf ≥ 2.5, then 2.0-2.5) are separate runs. | high precision first, TDA calibrates the Allport pass; each stage stays near the $5 default budget | plan 01 §8 |
| Zipf is a **feature, not a gate**.  The generator submits every TDA word and every Allport word the platform would not hard-reject; the 2.0 line and the 2.0-2.5 probe band come from `gapgen.freq.zipf_info` (`hard_reject`, `probe_band`), never from a local literal.  The Haiku definition probe on the band is the platform filter's; no RunPod probe. | a 3.0 floor rejects a third of our own labels; stale local defaults caused the B=10 incident | plan 01 res 1; plan 14 res 3; judge-cost rule |
| TDA familiarity (`prop`) travels as `Candidate.score`; Allport-only words carry `score=None` and let the registry compute Zipf. | Roger: familiarity where the word is in TDA | plan 01 res 1 |
| Keep 95% of existing labels: of the corpus labels that appear in the union list, ≥ 95% must be submitted by the generator's own eligibility rule. | Roger's threshold policy | plan 01 res 2 |
| State words (Allport column II) are in scope as dispositions.  The generator's `gloss_hint` says "disposition to be X (a general tendency, not an episode)"; the platform filter writes the real gloss with the tendency wording and tags `state`. | state-trait model from affect research | plan 01 res 3; plan 14 res 5 |
| No contact with the TDA authors; WordNet definitions plus the filter's glosses are the sense source. | Roger, 2026-09-23 | plan 01 res 4 |
| Saucier type nouns: roles holding list, low priority.  No digitised list was verified, so the only code is a generic `--extra-list` path (one word per line) that routes through the same submit; the filter's `role_person` tag sends them to the holding list. | plan 01 res 5; plan 14 res 4 | plan 01 |
| **No generator-side LLM calls.**  Sense, gloss, trait-hood and novelty are the platform CLIs run on this generator's rows; their `usage.json` files are this workstream's cost record.  `RunContext.usage` stays at zero and is still written. | the frozen interface says generators do not call the filter or scorer directly; a generator gloss pass would duplicate the filter's (~$3) | platform § Frozen interface |
| Downloads go under gitignored `data/external/wordlists/`, verified against the hashes the OSF and Dataverse APIs publish; hash, size, licence and attribution are copied into `run.json` (`args.sources`) of every run and into a tracked `sources_manifest.json`. | task brief | task brief |
| Chandler/Anderson likableness, Norman's category sort, Dumas 2002, the ACL: out. | licence unset on OSF / not digitised / paywalled / commercial | plan 01 §2 |
| Corpus and queue membership are computed into the ingest table for evaluation only; eligibility never reads them. | the generator must stay independent of our list | brief; plan 13 §3.1 |
| Code lives in a subpackage `assistant_axis/gapgen/generators/censuses/`. | generator workstreams run in parallel worktrees; flat module names in `gapgen/` would collide with workstream 2 | my choice |

## 2. Out of scope

- Any edit to `data/traits/**`, `data/roles/**`, `TRAITS_TO_ADD.md`, `ROLES_TO_ADD.md`, `data/seed_queue.json` (promotion is `gap_registry.py promote`, run by Roger's decision, not here).
- Anything the platform owns: the rubric, the definition probe, the novelty thresholds, the recovery hook internals, `metric_config.json`.  Changes needed there are listed under "Interface requests".
- Qwen3-32B definition probes; the Message Batches API; embeddings other than through `recovery_test`.
- Clustering survivors for review (plan 01 §3.6): `novelty_score.py review-list` does it.
- The 6.2 MB monograph scan on OSF and the 20 MB `TDA_data_scored.tab`: not downloaded.
- Plan 13's estimators and dashboard.

## 3. Rule files to Read first

Open with the **Read tool** before touching code:
[`.claude/rules/provenance.md`](../../.claude/rules/provenance.md) (usage.json; `json_metadata` envelopes; UTC timestamps; snapshot before overwrite),
[`.claude/rules/entity-naming.md`](../../.claude/rules/entity-naming.md) (`normalize_to_file_name` stems; `display_form_name` in anything an LLM reads; US English),
[`.claude/rules/trait-pairs.md`](../../.claude/rules/trait-pairs.md) (what a trait, a pair, an arrangement and the seed queue are; the description form the glosses copy),
[`.claude/rules/judging.md`](../../.claude/rules/judging.md) (this workstream runs the filter and reads its parse rate; `*** HIGH FAIL RATE ***` blocks the stage),
[`CLAUDE.md`](../../CLAUDE.md) (file-access boundary, the $20 rule, tests mandatory, hotlinks in replies).
No PNGs are produced, so the plotting rule is not needed.

## 4. Existing code to reuse

- Frozen interface, imported from `assistant_axis.gapgen`: `Candidate`, `start_run`, `submit_candidates`, `SubmitReport`, `NoveltyQuery`, `NoveltyResult`, `MetricConfig`, `recovery_test`, `RecoveryReport`, `REGISTRY_PATH`, `METRIC_CONFIG_PATH`.
- Platform modules: `gapgen.freq.zipf_info` (Zipf, `hard_reject`, `probe_band`), `gapgen.wordnet.ensure_oewn` and `wn_data_dir()` (the package reads OEWN senses through `wn` itself, see §5), `gapgen.paths.DATA_EXTERNAL` / `DATA_CANDIDATES` / `run_dir`, `gapgen.cost.estimate_calls_usd` and `confirm_or_abort`, `gapgen.registry.Registry` (read-only: fold the log, `records_for_status`), `gapgen.normalize.normalize_candidate`.
- [`data_analysis/seed_entities.py`](../../data_analysis/seed_entities.py): `corpus_stems(data_dir)["trait"]`, `load_queue`, `build_registry` (existing plus queued stems).
- [`assistant_axis/arrangements.py`](../../assistant_axis/arrangements.py): `load_corpus_arrangements`, `reciprocal_pairs` (the clean pairs for the hidden-pole test).
- [`assistant_axis/entity_id.py`](../../assistant_axis/entity_id.py): `normalize_to_file_name`, `default_data_dir`.  [`assistant_axis/atomic_io.py`](../../assistant_axis/atomic_io.py): `atomic_write_text`, `write_jsonl`, `read_jsonl_with_retry`, `_sha256_file` (copy the 20-line chunked reader rather than import a private name).
- [`assistant_axis/provenance.py`](../../assistant_axis/provenance.py): `current_file_input`, `load_validated_json`; [`assistant_axis/plot_metadata.py`](../../assistant_axis/plot_metadata.py): `json_metadata`.
- [`assistant_axis/judge_pricing.py`](../../assistant_axis/judge_pricing.py): `MultiModelUsage.load_or_create` to sum the filter, probe and novelty `usage.json` files per model.
- Test style: [`data_analysis/tests/test_seed_entities.py`](../../data_analysis/tests/test_seed_entities.py).

## 5. File layout

```
assistant_axis/gapgen/generators/__init__.py     exactly: """Generator workstreams, one subpackage each."""  (byte-identical in every generator worktree)
assistant_axis/gapgen/generators/censuses/
  __init__.py    GENERATOR = "censuses"; CENSUS_DIR = DATA_CANDIDATES / "censuses"; CENSUS_TABLE_PATH; WORDLISTS_DIR = DATA_EXTERNAL / "wordlists"
                 re-exports load_census_table (§ Frozen interface)
  sources.py     Source(key, filename, url, alt_url, dest, size_bytes, sha256, md5, licence, licence_url, citation, doi, version, column, optional)
                 SOURCES: dict[str, Source]  (§6); SKIPPED: the files deliberately not fetched, with reasons
  download.py    fetch_all(*, dest_root=WORDLISTS_DIR, only=None, force=False, fetcher=_urlopen_bytes, dry_run=False) -> DownloadManifest
                 verify_file(path, source) -> Verification(sha256, md5, verified, checksum_source)
                 osf_node_attribution(fetcher) -> dict   (title + contributors from api.osf.io/v2/nodes/k6rwj/, stored, never guessed)
                 write_manifest(manifest, path); load_manifest(path)
  ingest.py      parse_allport_txt(path, column) -> list[RawEntry(raw, line, column)]
                 parse_tda_properties(path) -> list[TdaRow]   (header-driven; two rows per adjective are merged: mean prop, summed N)
                 clean_surface(raw) -> str | None   (strip, lowercase, drop trailing punctuation; None when digits or non-Latin letters remain)
                 repair_ocr(surface, *, lexicon) -> str | None   (unique distance-1 OEWN adjective lemma, only when the surface is in neither wordfreq nor OEWN)
                 build_table(allport, tda, *, freq=zipf_info, senses, corpus_stems, queue_stems) -> list[TableRow]
                 write_table(rows, path) / load_census_table(path=CENSUS_TABLE_PATH) -> list[TableRow]
  glosshint.py   adjective_senses(lemma) -> list[Sense(definition, pos)]   (wn, data dir = wn_data_dir())
                 person_sense(senses) -> SenseHint(definition, rank, n_adj_senses) | None
                 gloss_hint(row) -> str | None   (≤ 25 words, cut at a word boundary; column II prefix)
  submit.py      STAGES = ("tda", "allport_hi", "allport_probe", "extra"); select_stage(rows, stage) -> list[TableRow]
                 pilot_sample(rows, frac, seed) -> list[TableRow]   (stratified by stage x band x corpus_match, proportional)
                 to_candidates(rows, run_id) -> list[Candidate]
                 estimate_downstream_usd(n, n_probe) -> Estimate(filter_usd, probe_usd, novelty_usd, total_usd, assumptions)
                 run_submit(stage, run_id, *, table, sources_manifest, pilot_frac, seed, budget_usd, confirm_expensive, dry_run) -> SubmitSummary
                 followup_commands(run_id, budget_usd) -> list[str]
  evaluate.py    string_ceiling(table, corpus_stems, queue_stems) -> Ceiling
                 known_label_pass(rows, corpus_stems) -> PassRates   (trait, or tagged state/physical, count as pass)
                 queries_for_run(registry_rows, *, include_tagged=("state",)) -> list[NoveltyQuery]
                 recovery_all(queries, *, data_dir, config, regions) -> RecoveryReport        (hidden = every trait stem)
                 recovery_pairs(queries, *, data_dir, config, seed) -> PairReport            (hidden = one pole per clean pair, hide_partners=False)
                 state_gloss_compliance(rows) -> float; polysemy_check(rows) -> dict; cost_summary(run_dir, batch_dirs) -> CostSummary
                 yield_per_dollar(rows, cost) -> float; write_evaluation(payload, path, inputs)
  report.py      render_report(evaluation) -> str; roger_sample(rows, n=50, seed=0) -> str
data_analysis/gap_generation/census_generator.py   download | ingest | submit | recovery | report
data/external/wordlists/                           GITIGNORED (platform's /data/external/ line)
  allport_odbert_osf_k6rwj/{Allport-Traits.txt, Personal Traits.txt, Temporary States.txt, Social Evaluations.txt, Metaphorical Doubtful.txt}
  tda_dataverse_5T80PF/{TDA_properties.csv, Data Description.pdf, TDA_frequencies.csv (only if gbooks.freq is not in properties)}
  DOWNLOAD_MANIFEST.json
data/candidates/censuses/{census_table.jsonl, sources_manifest.json, ingest_counts.json}   tracked (table ≈ 3 MB; pre-registered Q1)
data/candidates/runs/censuses/<run_id>/{candidates.jsonl, keys.txt, run.json, usage.json, evaluation.json, recovery_all.json, recovery_pairs.json, report.md, roger_sample.md}
assistant_axis/tests/test_gapgen_censuses_{sources,download,ingest,glosshint,submit,evaluate}.py
assistant_axis/tests/fixtures/censuses/{allport_*.txt, tda_properties_small.csv, registry_small.jsonl, evaluation_small.json}
data_analysis/tests/test_gap_generation_censuses_cli.py
```

No new dependencies (`wordfreq`, `wn` are the platform's).  `wn` is read directly (`wn.Wordnet("oewn:2024")` with `wn.config.data_directory = wn_data_dir()`) because `gapgen.wordnet.sense_info` returns counts, not definitions.

## 6. Data schemas

**Source config** (`sources.py`; hashes copied from the OSF and Dataverse APIs on 2026-09-23, metadata only):

```python
SOURCES = {
  "allport_I":   Source(key="allport_I", filename="Personal Traits.txt", url="https://osf.io/download/fdg4j/", dest="allport_odbert_osf_k6rwj/Personal Traits.txt",
                        size_bytes=50975, sha256="50f931baa3680af2111c1d5d94dc744398d72a16779a5a60a9cf711a948c6ca4", md5="2eab18841cb35fab5713acc044f72095",
                        licence="CC BY 4.0", licence_url="https://creativecommons.org/licenses/by/4.0/", citation="OSF node k6rwj (title and contributors read from the API at download time)", doi=None, version=None, column="I", optional=False),
  "allport_II":  Source(..., filename="Temporary States.txt",     url="https://osf.io/download/cg3rz/", size_bytes=49932,  sha256="8b8c8ae39ecb89749828a8abc9ab5a68de6af67a883ecb1eb6b636b39c24511c", md5="302812b0dee7be3dfc201544ce105fbc", column="II"),
  "allport_III": Source(..., filename="Social Evaluations.txt",   url="https://osf.io/download/6ptxv/", size_bytes=56516,  sha256="7f66d61d2647f62e4317e722b628f4d532af37cec9bcc9cab77d6e0054027262", md5="48cf379d22808df496f1a485ea85d562", column="III"),
  "allport_IV":  Source(..., filename="Metaphorical Doubtful.txt", url="https://osf.io/download/sjknr/", size_bytes=39732,  sha256="28c6466bf56ec40ba8a3acebfbf070833c334a8383720b1a9e134ceb3185163e", md5="1d3e4d6d5ff6787421d86887866437bf", column="IV"),
  "allport_merged": Source(..., filename="Allport-Traits.txt",    url="https://osf.io/download/5qwk9/", size_bytes=179338, sha256="54c348856bc575462b8d41113a66e58c8ca0340af0759bebf3ed0241545dbcd9", md5="403e3b6d3ffd92c3c7447106e6edcd14", column=None),
  "tda_properties": Source(key="tda_properties", filename="TDA_properties.csv", url="https://dataverse.harvard.edu/api/access/datafile/5255447?format=original",
                        alt_url="https://dataverse.harvard.edu/api/access/datafile/5255447", dest="tda_dataverse_5T80PF/TDA_properties.csv", size_bytes=87240,
                        sha256=None, md5="e858ae14f1d56211690562159c4f0f3d", licence="CC0 1.0", licence_url="http://creativecommons.org/publicdomain/zero/1.0",
                        citation="Condon, Coughlin & Weston (2022), Trait Descriptive Adjectives, Harvard Dataverse, V4", doi="10.7910/DVN/5T80PF", version=4, column=None, optional=False),
  "tda_codebook":  Source(..., filename="Data Description.pdf", url="https://dataverse.harvard.edu/api/access/datafile/5343069", size_bytes=56187, md5="011924ea56c5003285cf1be2967c1639", optional=True),
  "tda_frequencies": Source(..., filename="TDA_frequencies.csv", url="https://dataverse.harvard.edu/api/access/datafile/5255448?format=original", size_bytes=64753, md5="5fb68ab2843f0e663b321823eb15098a", optional=True),
}
SKIPPED = {"Allport and Odbert 1936.pdf": "6.2 MB monograph scan, not needed", "TDA_data_scored.tab": "20 MB raw ratings", "item_difficulty.tab": "psychometrics, not needed", "masterkey.tab": "not needed"}
```

Dataverse publishes one MD5 per file; whether it is for the original CSV or the ingested `.tab` is verified at download: `format=original` first, then the `.tab` form, and `checksum_source` records which matched (neither: `checksum_verified: false`, QUESTIONS entry, proceed).  OSF publishes sha256 and md5 under `extra.hashes`; both must match.

**Download manifest entry** (`DOWNLOAD_MANIFEST.json`, a list; the same list is written to `data/candidates/censuses/sources_manifest.json` and into every run's `run.json["args"]["sources"]`):

```json
{"key": "allport_II", "file": "data/external/wordlists/allport_odbert_osf_k6rwj/Temporary States.txt", "url": "https://osf.io/download/cg3rz/",
 "size_bytes": 49932, "sha256": "8b8c8ae3...24511e", "sha256_published": "8b8c8ae3...24511e", "md5_published": "302812b0...5fbc",
 "checksum_verified": true, "checksum_source": "osf:extra.hashes", "licence": "CC BY 4.0", "licence_url": "https://creativecommons.org/licenses/by/4.0/",
 "attribution": "<OSF node title> (<contributors as the API lists them>), https://osf.io/k6rwj/", "doi": null, "version": null,
 "downloaded_at": "2026-10-06T09:12:03+00:00", "tool": "census_generator.py download", "git_sha": "abc1234"}
```

**Census table row** (`census_table.jsonl`, one per distinct stem, deterministic order by `rank`):

```json
{"schema_version": 1, "surface": "flustered", "stem": "flustered", "label": "flustered",
 "allport": {"columns": ["II"], "raw": {"II": "Flustered"}, "line": {"II": 1834}}, "in_merged": true,
 "tda": {"row": 1021, "prop": 0.87, "n": 122, "gbooks_freq": -6.02, "gn1710": true, "sg435": true, "bffm100": false, "n_rows": 1},
 "zipf": 3.11, "freq_hard_reject": false, "freq_probe_band": false,
 "wordnet": {"found": true, "n_adj_senses": 1, "person_sense_rank": 1, "definition": "thrown into a state of agitated confusion"},
 "gloss_hint": "disposition to be flustered (a general tendency, not an episode): thrown into a state of agitated confusion",
 "repaired_from": null, "unknown_word": false, "eligible": true, "ineligible_reason": null, "stage": "tda",
 "rank": 388, "score": 0.87, "corpus_stem_match": true, "queue_stem_match": true}
```

Rules: `stem = normalize_to_file_name(surface)`; a surface in several Allport columns is one row with all columns; `eligible = surface cleaned ∧ ¬unknown_word ∧ (tda ∨ ¬freq_hard_reject)`; `ineligible_reason ∈ {malformed, unknown_word, below_hard_reject}`; `stage = tda | allport_hi (¬tda ∧ ¬probe_band) | allport_probe (¬tda ∧ probe_band) | null`; `rank` is global: TDA rows by `prop` desc (ties `gbooks_freq` desc, then surface), then Allport-only rows by `zipf` desc (ties surface), so later stages continue the sequence and recall-versus-rank curves read across stages.  `gloss_hint`: the person-descriptive adjective sense (first sense whose definition matches `\b(person|people|someone|one who|disposition|inclined|disposed|tending|habitually|manner|behavio(u)?r|mood|temperament|having|showing|marked by|characterized by|given to|lacking)\b`, else the first adjective sense, else the first sense of any POS with "(noun)" / "(verb)" appended); column II prefixes "disposition to be X (a general tendency, not an episode): "; column IV appends " (metaphorical or doubtful in Allport-Odbert)"; `None` when OEWN lacks the word.

**Candidate emitted** (`to_candidates`): `Candidate(surface="flustered", generator="censuses", run_id="2026-10-06a", rank=388, score=0.87, gloss_hint=<as above>, sense_id=1, source_ref="tda:1021")`; Allport-only rows use `source_ref="allport:II:1834"` and `score=None`.  `sense_id` is always 1: the censuses give no sense; polysemy is the filter's.

**Evaluation** (`evaluation.json`, payload inside a `json_metadata` envelope with inputs = table, registry, run files, `corpus_regions.json`, `metric_config.json`; numbers illustrative):

```json
{"run_id": "2026-10-06a", "stage": "tda", "pilot": false, "n_table": 17913, "n_eligible": 11420, "n_submitted": 2818,
 "ceiling": {"n_corpus": 414, "n_multiword": 21, "tda": 0.66, "allport": 0.69, "union": 0.70, "submitted_of_matched": 0.98},
 "filter": {"n": 2818, "verdict": {"trait": 0.41, "tagged": 0.33, "reject": 0.26}, "tags": {"state": 0.14, "physical": 0.07, "evaluative_only": 0.09, "role_person": 0.02, "too_rare": 0.00},
            "polysemy_rate": 0.21, "parse_rate": 1.0, "known_label_pass": 0.93, "known_label_misses": ["economic", "..."],
            "state_gloss_compliance": 0.95, "september_rejects_present": 5, "september_rejects_flagged": 4, "cost_usd": 2.31},
 "novelty": {"n_scored": 2010, "decision": {"covered": 0.52, "new": 0.31, "grey": 0.17}, "pair_completion": 38, "llm_fraction": 0.17, "cost_usd": 0.66},
 "recovery_all": {"n_hidden": 414, "n_candidates": 2010, "recall_strict": 0.58, "recall_loose": 0.66, "pair_recall": 0.12,
                  "by_region": {"emotional_temperament": {"strict": 0.81, "loose": 0.88}, "alignment_ai_agent": {"strict": 0.09, "loose": 0.14}}, "misses": ["..."]},
 "recovery_pairs": {"n_pairs": 124, "hidden_pole_recovered": 0.61, "pair_completion_flagged": 0.84},
 "cost": {"generator_usd": 0.0, "filter_usd": 2.31, "probe_usd": 0.0, "novelty_usd": 0.66, "recovery_embed_usd": 0.02, "total_usd": 2.99,
          "per_model": {"claude-haiku-4-5-20251001": 2.40, "claude-sonnet-4-6": 0.50, "text-embedding-3-large": 0.09}},
 "yield": {"n_useful": 590, "useful_per_dollar": 197.3, "definition": "verdict trait, no polysemy flag, decision new or flag pair_completion"}}
```

**Report rows.**  `report.md`: `| stage | n_submitted | trait | tagged | reject | polysemy | covered | new | grey | pair_completion | known_pass | recall_strict | recall_loose | cost_usd | useful/$ |` plus the by-region recovery table and the known-label misses.  `roger_sample.md` (50 rows, seeded, from `new` or `pair_completion` survivors): `| # | label | gloss | tags | nearest_existing (relation, sim) | decision | would consider? |`.  `ingest_counts.json`: rows per column, per stage, per Zipf band, unknown/repaired/malformed counts, the ceiling block.

## 7. CLI

`data_analysis/gap_generation/census_generator.py`, common flags `--data-dir`, `--registry`, `--table`, `--dry-run`.

- `download [--only KEY ...] [--force] [--dry-run]`: fetches the non-optional sources plus `tda_codebook`; `tda_frequencies` only when the properties header lacks `gbooks.freq`.  Streams to `<dest>.part`, verifies, renames; a mismatch deletes the part file and raises `ChecksumError` naming both hashes.  Idempotent: an existing file with the published sha256/md5 is skipped.  Writes `DOWNLOAD_MANIFEST.json` and `data/candidates/censuses/sources_manifest.json`.  Dry-run prints URLs, destinations and published hashes.  No API cost.
- `ingest [--queue PATH] [--dry-run]`: needs `data/external/wn` (`setup_external.py --wn`) and `wordfreq`.  Rebuilds `census_table.jsonl` deterministically (snapshot to `.bak.<UTC>` when the content changes), writes `ingest_counts.json`, prints the count table and the string ceiling.  Dry-run parses and counts, writes nothing.  No API cost.
- `submit --stage {tda,allport_hi,allport_probe,extra} --run-id R [--pilot-frac F --seed S] [--extra-list PATH] [--budget-usd 5.0] [--confirm-expensive]`: selects the stage's eligible rows (or the stratified pilot sample), prints n per stratum and the **downstream estimate** `filter n × $0.0009 + probe n_band × $0.0005 + novelty n × $0.00025` (platform rates: $6-9 and $2.35 per 10k; the probe figure is a placeholder until the platform's pilot reports one), then `confirm_or_abort(estimate, budget_usd, confirm_expensive=...)`: over the budget needs the flag, over $20 is refused outright.  Then `start_run("censuses", R, args={stage, pilot_frac, seed, n, estimate, sources: <manifest list>, table_sha256})`, `submit_candidates(cands, run=ctx)`, `ctx.finish()`, `keys.txt` from `SubmitReport.keys`, and prints the follow-up commands:
  `traithood_filter.py --batch-id R_censuses --run censuses/R --budget-usd <1.5 × est + 2>` · `novelty_score.py score --batch-id R_censuses --run censuses/R` · `census_generator.py recovery --run-id R` · `census_generator.py report --run-id R` (fallback while `--run` is unavailable: `--keys $(cat keys.txt)`).  Dry-run prints all of it and leaves the registry byte-identical.  Submitting is free; the guard sits here because the run's size is decided here.
- `recovery --run-id R [--mode all|pairs|both] [--include-tagged state] [--config] [--regions data/candidates/corpus_regions.json]`: builds `NoveltyQuery(key, label, gloss)` from the run's registry rows with a gloss and verdict `trait` (plus `tagged` rows carrying an included tag); `all` calls `recovery_test(queries, hidden=every trait stem, hide_partners=True, regions=...)`; `pairs` hides one pole per reciprocal pair (seeded choice), `hide_partners=False`, and counts `pair_completion` on the candidates that match the hidden poles.  No LLM calls; embeddings are cache hits after the novelty run (≈ $0.02 otherwise).  Writes `recovery_*.json`.
- `report --run-id R [--sample 50 --seed 0]`: assembles `evaluation.json` from the registry, the filter and novelty batch directories named `R_censuses`, and the recovery files; sums their `usage.json` per model; renders `report.md` and `roger_sample.md`.  No calls.

## 8. Acceptance tests, written first

No test calls an API, downloads, or loads a model; `wn` and `wordfreq` are faked where the real data is absent (`data/external/wn` missing → the real-DB tests skip).

- `test_gapgen_censuses_sources.py`: every source has url, dest under `wordlists/`, licence, licence_url and at least one published hash; no source is a PDF larger than 100 KB; `SKIPPED` names the two big files.
- `test_gapgen_censuses_download.py` (fake fetcher): matching hashes → file written, manifest entry `checksum_verified: true`; a wrong byte → `ChecksumError`, no file, no `.part` left; Dataverse original-then-tab fallback records `checksum_source`; skip when already verified; `--force` refetches; dry-run writes nothing; attribution comes from the fake node metadata verbatim.
- `test_gapgen_censuses_ingest.py` (fixtures: `Accomodating `, `ABANDONED`, `Afald`, `à la mode`, `well-bred`, a word in columns II and III, blank lines; a 6-row TDA CSV with one adjective on two rows and one with `prop` 0.12): stems via `normalize_to_file_name`; the two-row adjective merges (mean prop, summed N, `n_rows: 2`); the column duplicate is one row with both columns; `Afald` → `unknown_word`, ineligible; `accomodating` → `repaired_from` only when the fake lexicon has exactly one distance-1 adjective; `à la mode` folds to ASCII and stays a phrase; the eligibility truth table (tda below 2.0 stays eligible; Allport-only below 2.0 does not); stage assignment from `zipf_info` flags; global rank order; `corpus_stem_match` against a fake data dir with `risk-averse` (matches) and `kind-to-animals` (no census surface); rerun is byte-identical; no eligibility field depends on the corpus or queue (mutation test: flipping every `corpus_stem_match` changes no `eligible`).
- `test_gapgen_censuses_glosshint.py` (fake `wn`): the person-descriptive second sense outranks a first non-person sense; adjective-only and noun-only fallbacks; column II prefix and column IV suffix; ≤ 25 words, cut at a word boundary; `None` when absent.
- `test_gapgen_censuses_submit.py` (tmp registry via the real frozen API): stage selection counts; candidates carry rank, score, gloss_hint, source_ref, `sense_id` 1; `run.json["args"]["sources"]` equals the manifest list; `keys.txt` matches `SubmitReport.keys`; second submit of the same run is a no-op (`n_new == 0`); `pilot_sample` is seeded, proportional per stratum (± 1) and never empties a stratum with ≥ 5 rows; **cost guard**: 40,000 fake rows → estimate > $20 → refused even with `--confirm-expensive`; 8,000 rows → over $5 refused without the flag, accepted with it; dry-run leaves the registry byte-identical and writes no run dir; the follow-up commands name the run id and batch id.
- `test_gapgen_censuses_evaluate.py`: `string_ceiling` on the fake corpus; `known_label_pass` counts `trait`, `tagged+state`, `tagged+physical` as passes; `queries_for_run` drops rows without a gloss or with a `reject` verdict; `recovery_all` / `recovery_pairs` with a monkeypatched `recovery_test` returning a fixed `RecoveryReport` → files and the evaluation payload shape, envelope present; `pair_completion_flagged` from fake `NoveltyResult`s; `state_gloss_compliance` accepts "a general tendency to" and "disposition", rejects an episode gloss; `polysemy_check` on the six September rejects; `cost_summary` sums three fake `usage.json` files per model and reports the generator's own total as 0.0; yield formula; the package imports neither `anthropic` nor `openai`.
- `test_gap_generation_censuses_cli.py`: every subcommand's `--dry-run` exits 0 and writes nothing; `report` renders the fixture evaluation to markdown with all report columns.
- Acceptance on recorded outputs (`test_gapgen_censuses_acceptance.py`, skips when the run files are absent): string ceiling TDA ≥ 0.62 and Allport ≥ 0.65 of the 414 (2026-09-18 measured 0.69 / 0.72 on 385; the 21 multiword labels cap the ceiling at 0.95); `submitted_of_matched ≥ 0.95`; `known_label_pass ≥ 0.90`; `parse_rate ≥ 0.99` in every filter summary of this workstream; `recall_loose ≥ 0.85 × ceiling.union` with `recall_strict` and the by-region table reported; `pair_completion_flagged ≥ 0.80` (when the hook exposes flags, see Interface requests); `september_rejects_flagged ≥ 4` of those present; `state_gloss_compliance ≥ 0.90`; `usage.json` present in every run dir with `generator_usd == 0.0`.

Commands that must pass at the end of every task:

```
uv run pytest assistant_axis/tests/test_gapgen_censuses_*.py data_analysis/tests/test_gap_generation_censuses_cli.py -q
uv run pytest -q                                                  # whole suite, unchanged
uv run python data_analysis/check_arrangements.py --quiet
uv run python tools/sync_entity_lists.py --check
git status --porcelain data/traits data/roles data/seed_queue.json   # must be empty
```

## 9. Ordered task checklist

Prerequisite: platform M1 merged (`Candidate`, `start_run`, `submit_candidates`, `zipf_info`, `wn_data_dir`, `confirm_or_abort` importable; `setup_external.py --wn` run).  Tasks 8-11 also need M1's filter CLI and M3's novelty CLI and hook.

1. Skeleton (`generators/__init__.py` with the exact docstring, `censuses/__init__.py`, `sources.py`).  Test: sources.
2. `download.py` + CLI `download`.  Test: download.  Then run `download` for real (no API cost) and paste the manifest's verification lines into the task report.
3. `ingest.py` parsers, `clean_surface`, `repair_ocr`.  Test: ingest (parsers half).
4. `build_table`, `write_table`, `load_census_table`, CLI `ingest`.  Test: ingest (table half).  Run it: the printed counts (rows per stage, per Zipf band, unknown/repaired, ceiling) replace the estimates in §10; copy them into QUESTIONS.md as an information entry.
5. `glosshint.py`.  Test: glosshint.  Spot-read 30 hints for column II words.
6. `submit.py` + CLI `submit` with the guard and follow-up commands.  Test: submit.
7. `evaluate.py`, `report.py`, CLI `recovery` and `report`.  Test: evaluate, CLI.
8. **Pilot** (§10).  Roger's decision.
9. Stage `tda`: submit, filter, novelty, recovery, report; acceptance test on the recorded outputs.  Roger's go for stage 10.
10. Stage `allport_hi`.  Roger's go for stage 11.
11. Stage `allport_probe` (only if greenlit from the pilot's band readout).
12. Optional, last: `--extra-list` for a Saucier type-noun file if Roger supplies one; otherwise skip and say so.
13. Acceptance report (§11); propose the `data/README.md` paragraph for `external/wordlists/` and `candidates/censuses/` in the report (the platform edits that file in its M2; do not race it).

## 10. Pilot

`submit --stage tda --pilot-frac 0.2` and `submit --stage allport_hi --pilot-frac 0.1` plus `--stage allport_probe --pilot-frac 0.1`, all under one run id `<date>p`; stratified by stage × band × corpus match so known labels appear at their natural rate (~50 in the TDA sample).  Volume ≈ 560 + 600-800 + 200-300 ≈ 1.4-1.7k candidates; cost ≈ $1.3-1.6 filter + ≈ $0.15 probes + ≈ $0.4 novelty ≈ **$2**.  Readout (from `report.md`): verdict and tag fractions per stage and band; polysemy rate; `state` fraction and the tendency-wording compliance; known-label pass rate with every miss listed; covered / new / grey and pair completions; filter cost per candidate and `useful_per_dollar` per stage; recall on the sampled known labels; the 50-row `roger_sample.md`; the projected cost of each full stage from the measured per-candidate cost and the task-4 counts.

Roger decides: (a) go for the full TDA stage; (b) Allport column IV in or out (assumed in: the filter and the floor handle it, ≈ +15% volume); (c) second opinions on or off for the census stages; (d) whether the 2.0-2.5 band is worth its probes (drop stage 11 if its pilot rows are mostly `too_rare` or `reject`); (e) track `census_table.jsonl` or gitignore it; (f) the precision verdict on the 50 rows (target ≥ 70% "would consider").  Projected full cost before the pilot corrects it: TDA ≈ $3; `allport_hi` (5-8k rows) ≈ $5-9; `allport_probe` (2-3k) ≈ $3-5; total ≈ $12-19 if every stage runs, ≈ $8-12 if stage 11 is dropped.  Each stage's filter command gets `--budget-usd = 1.5 × estimate + $2` (first-of-kind rule, scaled) and needs `--confirm-expensive` above $5; the workstream stops for a new go if the summed `usage.json` cost reaches $18.

## 11. Report at the end

One page at `reports/trait_gap_generation/acceptance_01_censuses.md`: what was built against §5; deviations with reasons; the §8 commands verbatim with pass counts; the download manifest's verification lines (hash matched, licence, attribution); ingest counts and the string ceiling on the 414; per-stage cost from the `usage.json` files per model and the generator's own zero; the pilot readout and Roger's decisions; the recovery numbers (strict, loose, pair, by region) and the known-label misses with a one-line reading each (filter bug or label to reconsider); polysemy and state-gloss checks; open QUESTIONS entries; the proposed `data/README.md` and AGENT_NOTES paragraphs for Fable to merge.

## 12. Escalation

Opus retries a failing step once with a changed approach, then Fable (diff review, architecture, stubborn failures), then Roger through [`QUESTIONS.md`](./QUESTIONS.md) in its format (`N. [01] question. Assumption proceeded under: ... Status: open`), proceeding under the assumption unless the answer would make the work useless.  Pre-registered entries Opus copies in at the start: (1) `census_table.jsonl` (≈ 3 MB) is tracked; (2) Allport column IV is included; (3) the Dataverse MD5 is checked against the original CSV first, then the `.tab`; (4) Chandler/Anderson likableness stays out (no licence on OSF); (5) TDA words the platform would hard-reject on Zipf (expected a handful) are submitted anyway and the loss is reported, pending Interface request 4; (6) the pair-completion acceptance line is reported, not gated, until Interface request 3 lands.  Anything that would edit a trait file or the queue, spend over a command's budget, or change a frozen signature stops and asks.

## Interface requests

> **Resolved 2026-09-24**: see `coding_plan_platform.md` § "Interface resolutions"; all five granted.
 (for the platform, clearly marked)

1. **Gloss hint in the filter prompt.**  `build_batch_prompt(items)` should show each candidate's `gloss_hint` (from `sources[].gloss_hint`, first non-null) as "intended sense", displayed through `display_form_name`.  Without it the Allport column information (state as disposition, metaphorical) never reaches the rubric.
2. **Run selector on the CLIs.**  `traithood_filter.py` and `novelty_score.py score` need `--run GENERATOR/RUN_ID` (rows whose `sources[]` carry that pair, skipping rows already filtered / scored), because `--unfiltered` and `--unscored` span every generator submitting in parallel.  Fallback used meanwhile: `--keys $(cat keys.txt)`.
3. **Recovery hook in all-hidden mode and result exposure.**  `recovery_test` must accept `hidden` = every trait stem (an index with no traits) and match hidden stems on the candidate side; `RecoveryReport` should carry `results: list[NoveltyResult]` (or `pair_completion_keys`) so the hidden-pole test can count `pair_completion`; for a stem in `exclude_stems`, `Neighbour.partner_has_file` must be `False` so the flag can fire.
4. **Generator-supplied familiarity.**  When `Candidate.score` is a human familiarity (documented per generator; here TDA `prop`), a word with `prop ≥ 0.5` should get the definition probe rather than the hard reject when its Zipf is below 2.0.  Low priority; expected to touch a handful of TDA words.
5. Confirm `RunContext.finish()` writes a zero-call `usage.json` (it should; the acceptance test asserts `generator_usd == 0.0`).

## Frozen interface (for other generators)

`from assistant_axis.gapgen.generators.censuses import load_census_table, CENSUS_TABLE_PATH`: the table row in §6 (`schema_version` 1) with `zipf`, `tda.prop`, `allport.columns`, `stage`, `rank` for every Allport-Odbert and TDA word.  Other generators may use it as a frequency floor or as the negative control ("did the brainstormer only re-emit census words?": intersect their stems with `{row.stem}`).  Fields are added, never renamed, without a schema bump.

## Review amendments (2026-09-24)

- Runs after platform M1 is merged for the M1-only tasks; the tasks that need M2/M3 wait for
  those milestones' acceptance (see the platform plan's amendment 1).
- Recorded-output acceptance numbers that are first measurements (recall, pair recall,
  known-label pass, precision spot checks) are report-and-decide for Roger, per the platform
  plan's amendment 2; parse rate, cost caps, `usage.json` presence and the untouched-corpus
  check remain hard gates.
- The registry live log is gitignored and only the compacted snapshot is tracked (platform
  amendment 3); `keys.txt` and the run directories are unaffected.

## Revision for the interface as built (2026-10-08, Fable; this section overrides §§ 4, 5, 7 and the "Interface requests" where they differ)

The scorer side of the frozen interface this plan was written against was never built; M3 is
retrieve-then-judge and the recovery harness is being built by the platform close-out job (see
[coding_plan_platform.md](./coding_plan_platform.md), "Interface as built").  What changes for this
workstream:

1. **Use only the registry API**: `Candidate`, `start_run`, `submit_candidates`, `SubmitReport`,
   `RunContext` from `assistant_axis.gapgen`; nothing named `NoveltyQuery`, `score_novelty`,
   `recovery_test`, `embed_local` or `RecoveryReport` exists.  Drop § 5's `queries_for_run` and
   `recovery_all`, § 7's `recovery` command and `evaluate.py`'s recovery parts; keep the census
   parsing, the Zipf and familiarity handling, the staged runs, the string-ceiling and known-label
   checks (they need only the corpus files and the registry).
2. **Every run writes a tracked `candidates.jsonl`** in its run directory (one `Candidate` per line, the
   fields of the dataclass) before `submit_candidates`, since the registry log is per checkout and
   git-ignored; the main checkout resubmits it with `gap_registry.py submit --from`.
3. **Filtering and scoring are the platform's CLIs**, run by Fable after the generator submits, not by
   this workstream: `traithood_filter.py --run censuses/<R>` then `novelty_score.py score --run
   censuses/<R>`; recovery by `recovery_test.py --generator censuses --run-id <R>` once the close-out
   job lands.  This workstream's acceptance stops at a correct, tested, submitted run with its
   readout of counts (words parsed, cut by the floor, submitted by stage, duplicates merged).
4. **Costs**: the generator itself makes no paid call.  The platform's cost per submitted word is now
   about $0.004 for M1 (Haiku 5.5, three readings) and about $0.018 for M3 on each word M1 passes
   (M3 pilot rates, before the cosine floor); the TDA's 2,818 words are therefore about $11 of M1
   and, at the near-corpus pass rate of about 90%, about $45 of M3: over the $20 line, so the full
   run goes through the Batches API on Roger's go, after the 20% pilot (§ 10) has been read.
5. **Pilot**: `--every-nth 5` of the TDA, submitted as run `<date>-pilot`; Fable runs M1 and M3 on it
   live (about $11 together, under the line, reported as it runs) and the recovery test, and writes
   the yield-per-dollar readout before the full TDA.  Allport-Odbert stages follow the TDA on Roger's
   go, as § 1 says.
6. **Where the agent works**: its own git worktree (the Agent tool's worktree isolation branches from
   origin/master, so its first step is `git merge --ff-only anthropic-vllm-uv`), with `.env` copied
   from the main checkout and `data/external/` and `runpod_workspace/` symlinked from it (both inside
   the repository); the TDA and Allport-Odbert files download into `data/external/wordlists/` (as §4 lays out; an earlier draft of this item said `censuses/`) with
   their licence files beside them (CC0 and CC BY; record the URLs and dates in a README there).  The
   file-access boundary of PLAN_FORMAT.md applies unchanged.

**As built (2026-10-08, branch `gen01-censuses`, six commits).**  Package `assistant_axis/gapgen/generators/censuses/`
(`sources`, `download`, `ingest`, `glosshint`, `corpus`, `submit`, `evaluate`, `report`), CLI
[census_generator.py](../../data_analysis/gap_generation/census_generator.py) (`download | ingest | submit | report`),
run directories under `data/candidates/runs/censuses/<run_id>/`, the census table and counts under
[data/candidates/censuses/](../../data/candidates/censuses/).  Pilot `2026-10-08-pilot`: `submit --stage tda --every-nth 5`,
564 words, readout [readout.md](../../data/candidates/runs/censuses/2026-10-08-pilot/readout.md); deviations and open
questions 28-36 in [QUESTIONS.md](./QUESTIONS.md).  The full TDA and the two Allport stages are over the $20 line and
wait for Roger's go (`--transport batches`, `--confirm-expensive --confirmed-by`).
