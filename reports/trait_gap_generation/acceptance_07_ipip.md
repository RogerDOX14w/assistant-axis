# Acceptance: workstream 7, IPIP behavior items (generator `ipip`)

Written 2026-10-10 by the Opus build agent, for [coding_plan_07_behaviour_items.md](./coding_plan_07_behaviour_items.md) § 11.

> **Superseded in part on 2026-10-11** by Roger's answers to [QUESTIONS](./QUESTIONS.md) entries 46-52, built
> the same day.  What changed, against the text below: the key signs now come from **IPIP's own 21 per-inventory
> key pages** (source B, primary) with Tedone's workbook as a check and gap-filler (entry 52, option C, both
> fetches approved), every committed key carries `key_source` in [items.jsonl](../../data/candidates/ipip/items.jsonl)
> (entry 46), the home page is fetched so the public-domain sentence is recorded verbatim (entry 46), `is_trait`
> is gone and every named pole is submitted with a `kind` guess in M1's vocabulary (entry 48), the two naming
> prompts are pinned rubric files ([ipip_naming_blind.md](./rubrics/ipip_naming_blind.md),
> [ipip_naming_hinted.md](./rubrics/ipip_naming_hinted.md)) rather than code (entry 48 part 3), the HEX assertion
> is a permanent scrape-completeness check beside a new 21-page check and the pages are decoded explicitly
> (entry 49), and the granularity readout carries the two signals of entry 50 by cluster-size band.  Deviations 1,
> 5 and 7 below are therefore obsolete; deviations 2, 3, 4 and 6 still hold.  **The fetch itself has not run**:
> ipip.ori.org was unreachable from this sandbox on 2026-10-11 (every request timed out or came back 502 from the
> proxy over about half an hour), so the key pages, the workbook and the home page are still not on disk and the
> A-against-B comparison has not been measured.  This report will be rewritten when the pilot runs.

**Status: built and tested; the pilot (§ 10) has not run.**  It was blocked by
[QUESTIONS 52](./QUESTIONS.md): the item-to-scale keys are not on the three approved pages.
[ItemAssignmentTable.htm](../../data/external/ipip/ItemAssignmentTable.htm) (git-ignored) is a 3,759-byte page that describes the table and links to an Excel
workbook, `TedoneItemAssignmentTable30APR21.xlsx`, compiled by Thomas Tedone (no licence stated).
The alternative is IPIP's 21 per-inventory key pages, linked from the scale index.  Neither was
fetched, because both are outside Roger's approval of 2026-10-10.  Without the keys there are no
bipolar poles, no hinted labels, no purity figures, no HEX assertion and no known-analogue check, so
a key-less pilot could not inform decisions (a) and (b).  Spend so far: **$0** on APIs; the only
network use was the approved fetch (914,060 bytes).

## What was built (against § 5)

| file | what |
|---|---|
| [`__init__.py`](../../assistant_axis/gapgen/generators/ipip/__init__.py) | `GENERATOR = "ipip"`, the paths, `clusters_path(g)` |
| [`sources.py`](../../assistant_axis/gapgen/generators/ipip/sources.py) | the three pages, the HEXACO key fallback, the workbook (no approval on record), the licence quote |
| [`download.py`](../../assistant_axis/gapgen/generators/ipip/download.py) | `fetch_all`: `.part` then rename, sha256 and size of the received bytes, manifest, idempotent, `--force`; a short body is completed with `Range` requests; a source with no approval is refused unless `--approved-by` names Roger's go |
| [`ingest.py`](../../assistant_axis/gapgen/generators/ipip/ingest.py) | `parse_item_list`, `parse_scale_index`, `parse_assignment_table` (the workbook, read with the standard library), `build_items`, `check_hex`, `write_items` (snapshot on change) |
| [`cluster.py`](../../assistant_axis/gapgen/generators/ipip/cluster.py) | `item_embed_text`, `embed_items`, `agglo_clusters`, `consensus`, `split_poles`, `purity_metrics`, `hdbscan_check`, `nearest_corpus`, `build_cluster_table` |
| [`naming.py`](../../assistant_axis/gapgen/generators/ipip/naming.py) | `NAMING_PROMPT`, `HINTED_PROMPT` (pinned by sha256), `build_user`, `build_hinted_user`, `parse_naming`, `name_poles` (async, Haiku 5.5) |
| [`granularity.py`](../../assistant_axis/gapgen/generators/ipip/granularity.py) | `sample_pairs`, `item_entry`, `run_readings` (the platform's `OverlapRunner`, rubric A), `readout`, `readout_markdown` |
| [`submit.py`](../../assistant_axis/gapgen/generators/ipip/submit.py) | `to_candidates`, `run_submit`, the copied M1/M3 rates |
| [`evaluate.py`](../../assistant_axis/gapgen/generators/ipip/evaluate.py) | `census_overlap`, `known_analogues`, `recovery_from_covers`, `naming_agreement`, `cost_summary`, `useful_per_dollar` |
| [`report.py`](../../assistant_axis/gapgen/generators/ipip/report.py) | `build_evaluation`, `render_report` (the six decisions), `roger_sample` |
| [`corpus.py`](../../assistant_axis/gapgen/generators/ipip/corpus.py) | corpus traits and queue names, for reporting and prompt hygiene only |
| [`ipip_generator.py`](../../data_analysis/gap_generation/ipip_generator.py) | `download`, `ingest`, `cluster`, `name`, `granularity`, `submit`, `report`, each with `--dry-run` |
| tests | [sources](../../assistant_axis/tests/test_gapgen_ipip_sources.py), [download](../../assistant_axis/tests/test_gapgen_ipip_download.py), [ingest](../../assistant_axis/tests/test_gapgen_ipip_ingest.py), [cluster](../../assistant_axis/tests/test_gapgen_ipip_cluster.py), [naming](../../assistant_axis/tests/test_gapgen_ipip_naming.py), [granularity](../../assistant_axis/tests/test_gapgen_ipip_granularity.py), [submit](../../assistant_axis/tests/test_gapgen_ipip_submit.py), [evaluate](../../assistant_axis/tests/test_gapgen_ipip_evaluate.py), [acceptance on recorded outputs](../../assistant_axis/tests/test_gapgen_ipip_acceptance.py), [CLI](../../data_analysis/tests/test_gap_generation_ipip_cli.py); fixtures in [ipip_fakes.py](../../assistant_axis/tests/ipip_fakes.py) and [fixtures/ipip/](../../assistant_axis/tests/fixtures/ipip/) |

The data outputs under [data/candidates/ipip/](../../data/candidates/ipip/) are not on disk yet,
except [sources_manifest.json](../../data/candidates/ipip/sources_manifest.json).  The rest will
appear at these paths: [items.jsonl](../../data/candidates/ipip/items.jsonl),
[ingest_counts.json](../../data/candidates/ipip/ingest_counts.json),
[clusters_g350.jsonl](../../data/candidates/ipip/clusters_g350.jsonl),
[clusters_g150.jsonl](../../data/candidates/ipip/clusters_g150.jsonl),
[cluster_summary.json](../../data/candidates/ipip/cluster_summary.json),
[cluster_usage.json](../../data/candidates/ipip/cluster_usage.json),
[naming_responses.jsonl](../../data/candidates/ipip/naming_responses.jsonl),
[naming_usage.json](../../data/candidates/ipip/naming_usage.json),
`granularity/g<G>/{responses.jsonl, usage.json, run.json}`,
[granularity_readout.json](../../data/candidates/ipip/granularity_readout.json) and
[granularity_readout.md](../../data/candidates/ipip/granularity_readout.md).

## Deviations, with reasons

1. **The item-to-scale source is a workbook, not an HTML page** (QUESTIONS 52; blocking).  The
   ingest reads the workbook's documented columns (instrument, alpha, key 1 / -1, text, label),
   finding them by header wherever the header row sits.  It is tested on a synthetic workbook,
   because the real one could not be fetched.  `parse_assignment_table` therefore takes the
   workbook's bytes, not HTML.  The workbook is listed in `sources.py` with `approval: None`, and
   `download` refuses it unless `--approved-by` names Roger's go, which is then recorded in the
   manifest.  An `.xlsx` is a zip of XML parts, so no dependency is added.
2. **`items.jsonl` gains a `codes` field.**  The item list prints 67 items with several survey codes
   (`H843, F44, T192`: one item given in several surveys) and 29 VIA codes with a footnote asterisk.
   There is one row per item text: `ipip_id` is the first code printed and `codes` holds all of
   them.  The real page parses to exactly **3,320 items** (3,389 codes), its own count.
3. **The cluster cut is exact, not a bisection.**  The count of clusters with two or more items is
   not monotonic in the distance threshold: merging two singletons adds a cluster, merging two
   clusters removes one.  `agglo_clusters` follows the count merge by merge on the average-linkage
   tree and takes the last cut after the peak nearest the target.  Planted clusters are recovered
   exactly, and the count lands within ±10% (tested).  It returns `(clusters, info)`.
4. **The cost-guard test follows the platform's gate**, not § 8's wording.  § 8 says 1,000 poles
   over the default budget are "refused without `--confirm-expensive`, accepted with it".  The
   frozen `cost.confirm_or_abort` (decision 9, Roger: "no flag raises the cap") refuses any estimate
   over `--budget-usd`, whatever the flags.  So the test checks a refusal at the default $8 with or
   without the flag, and an acceptance at `--budget-usd 17`.  5,000 poles are refused even with
   `--confirm-expensive`, as § 8 says.
5. **The licence sentence is not recorded verbatim.**  None of the three pages carries it, and the
   home page that does is outside the approval.  The manifest records the plan's quote (with its
   ellipsis) and `verbatim: null`; `download` fills `verbatim` if a fetched page ever carries it.
6. **The fetcher completes short reads.**  In this sandbox urllib received 835,315 of the item
   list's 849,217 bytes on every attempt, while curl received all of it.  The fetcher keeps the
   partial body and asks for the rest with `Range` (the server advertises `Accept-Ranges`), checking
   the total against `Content-Length`.
7. **Naming prompts are pinned in the module.**  They live in [naming.py](../../assistant_axis/gapgen/generators/ipip/naming.py)
   (`PINNED`: blind v1 `41b361d7…`, hinted v1 `e33a08e9…`, enforced by a test), not in
   [rubrics/versions.json](./rubrics/versions.json), which the platform owns and other workstreams edit.  The rendered
   prompt is below.  The parser is strict, as § 8 asks: a fenced or prose-wrapped reply is rejected,
   counted, and asked once more.
8. **Extra files, for provenance and the usage rule:** `ingest_counts.json`, `cluster_summary.json`
   (with a provenance envelope), `cluster_usage.json` (embedding spend, cumulative),
   `naming_responses.jsonl` (every naming response, recorded before parsing) and
   `granularity/g<G>/run.json` (the label form, so a resume keeps it).
9. **A granularity reading's call id names its item pair** (`g350:c017:within:H12>H40`).  The
   runner skips answers already on record by call id, so a cluster split differently later cannot
   reuse an answer that was given for another pair.
10. **The package imports no SDK at import time** (tested).  `granularity.py` therefore loads the
    platform's `overlap_test` on first use, since that module pulls in the OpenAI SDK.
11. **Worktree environment.**  The sandbox forbids creating a `.claude/` directory, so this worktree
    is a sparse checkout without it.  The `.claude/` entries are kept in the index, so commits never
    touch them.  [test_boundary_check.py](../../tools/tests/test_boundary_check.py) fails to collect for that reason only.  Tests
    run in the worktree's own venv after `uv sync --extra dev`.  Before that, `uv run pytest` had
    fallen through to the main checkout's venv, because pytest is in the `dev` extra only.

## The § 8 commands

| command | result |
|---|---|
| `uv run pytest assistant_axis/tests/test_gapgen_ipip_*.py data_analysis/tests/test_gap_generation_ipip_cli.py -q` | 95 passed, 4 skipped (the acceptance checks on recorded outputs, none recorded yet), exit 0 |
| `uv run pytest -q` | stops at collection, exit 2: the 4 known `results_analysis/tests` errors (two `tests` packages; [acceptance_platform.md](./acceptance_platform.md)) and `tools/tests/test_boundary_check.py` (no `.claude/` in this worktree, deviation 11) |
| `uv run pytest assistant_axis/tests data_analysis/tests tools/tests -q --ignore=tools/tests/test_boundary_check.py` | 3,418 passed, 9 skipped, 6 failed, exit 1 (baseline before the build: 3,323 passed, 5 skipped, the same 6 failures; the 6 are the known worktree failures: `test_gapgen_paths` (5) and `test_gapgen_embed::test_hf_cache_is_inside_repo`; +95 passed and +4 skipped are this build's) |
| `uv run python data_analysis/check_arrangements.py --quiet` | exit 0 |
| `uv run python tools/sync_entity_lists.py --check` | exit 0 (932 traits, 339 roles, up to date) |
| `git status --porcelain data/traits data/roles data/seed_queue.json` | empty |

## The download (2026-10-10, under Roger's approval)

From [sources_manifest.json](../../data/candidates/ipip/sources_manifest.json); the pages are under
`data/external/ipip/` (git-ignored):

```
item_list            849217 B  sha256 df326e934612066a1ec9ccdd356e48238fdb809b4e2aa7f9076d6b3195a012ba  2026-10-10T18:20:20+00:00  https://ipip.ori.org/AlphabeticalItemList.htm
assignment_table       3759 B  sha256 c879f27c296cd7e40c1cdea71129c768d36550413361ba36bb84352778cba9f3  2026-10-10T18:20:20+00:00  https://ipip.ori.org/ItemAssignmentTable.htm
scale_index           61084 B  sha256 08ba1f47ac927312fb1aad8094b534dc59e38411af6786089d44885bdfc4e7eb  2026-10-10T18:20:20+00:00  https://ipip.ori.org/newIndexofScaleLabels.htm
```

Licence: public domain under IPIP's blanket statement, quoted by plan 07 § 2 as "The items and
scales are in the public domain ... use them for any purpose without asking permission and without
paying a fee" (verbatim sentence: not on the fetched pages, deviation 5).  The HEXACO key page was
not fetched, because its fallback has not been triggered.

**What the pages give without the workbook:** 3,320 items (3,389 survey codes).  The scale index
gives 547 construct links over 275 labels (the page says 274 labels for 463 scales), 31 of the
links keyed `HEX` (24 facets, some under two spellings: "Fairness/Equity", "Equity/Fairness").

## Rendered naming call (hinted form, a bipolar pole; no API call)

What Haiku 5.5 receives: the system prompt is the hinted rubric (the blind one omits the "scales"
paragraph and key), cached, with no temperature and max_tokens 4,000.  The user turn:

```
{"statements": ["I leave a mess in my room.", "I leave my belongings around.", "I am not bothered by messy people.", "I do things in a half-way manner."], "scales": [{"scale": "Orderliness", "inventory": "NEO", "direction": "against", "statements": 3}, {"scale": "Organization", "inventory": "HEX", "direction": "against", "statements": 2}, {"scale": "Orderliness", "inventory": "AB5C", "direction": "against", "statements": 1}]}
```

The prompt text itself is in [naming.py](../../assistant_axis/gapgen/generators/ipip/naming.py).
Its example labels ("punctilious", "slow to anger", "keeps others at arm's length") are no corpus
label, corpus stem or seed-queue name (tested).

## Not available until the workbook is fetched

Ingest counts with keys and the HEX assertion, cluster quality per embedder, the granularity
readout, blind / hinted statistics, M1 / M3 fractions, the known-analogue recovery,
`useful_per_dollar`: all of these come from the pilot.

## The pilot, once Roger approves a source (§ 10; about $3, every stage live)

Option A (the workbook):

```
uv run python data_analysis/gap_generation/ipip_generator.py download --only assignment_workbook --approved-by '<Roger, date>'
uv run python data_analysis/gap_generation/ipip_generator.py ingest
uv run python data_analysis/gap_generation/ipip_generator.py cluster                                  # about $0.01
uv run python data_analysis/gap_generation/ipip_generator.py name --granularity 350 --clusters 40 --hinted --budget-usd 1
uv run python data_analysis/gap_generation/ipip_generator.py name --granularity 150 --clusters 40 --hinted --budget-usd 1
uv run python data_analysis/gap_generation/ipip_generator.py granularity --budget-usd 3               # about $1.9
uv run python data_analysis/gap_generation/ipip_generator.py submit --granularity 350 --run-id 2026-10-1Xa-pilot --all-trait-poles --budget-usd 2
uv run python data_analysis/gap_generation/traithood_filter.py --batch-id 2026-10-1Xa-pilot_ipip --run ipip/2026-10-1Xa-pilot --pipeline split --budget-usd 3
uv run python data_analysis/gap_generation/novelty_score.py score --batch-id 2026-10-1Xa-pilot_ipip --run ipip/2026-10-1Xa-pilot --budget-usd 3
uv run python data_analysis/gap_generation/ipip_generator.py report --run-id 2026-10-1Xa-pilot
```

If `ingest` reports the HEX assertion failed, run `download --only hexaco_key` (QUESTIONS 49), then
`ingest` again.  Option B (the 21 key pages) needs a key-page parser first, which is not built.

The full run comes after Roger's § 10 gate, on the chosen granularity G and label form F (projected
at about $5-6):

```
uv run python data_analysis/gap_generation/ipip_generator.py name --granularity G --all --hinted --budget-usd 2
uv run python data_analysis/gap_generation/ipip_generator.py submit --granularity G --run-id <R> --all-trait-poles --label-choice F --budget-usd 8
uv run python data_analysis/gap_generation/traithood_filter.py --batch-id <R>_ipip --run ipip/<R> --pipeline split --budget-usd 5
uv run python data_analysis/gap_generation/novelty_score.py score --batch-id <R>_ipip --run ipip/<R> --budget-usd 8
uv run python data_analysis/gap_generation/ipip_generator.py report --run-id <R>
```

The main checkout picks up a run made in this worktree with `gap_registry.py submit --from
data/candidates/runs/ipip/<R>/candidates.jsonl`.

## Open QUESTIONS entries

46 to 51, pre-registered from § 12 (items tracked; blind label provisional; trait poles only; the
HEX fallback; granularity read comparatively; `score` stays `None`), and **52, blocking: which
item-to-scale source to fetch** ([QUESTIONS.md](./QUESTIONS.md)).

## Proposed paragraph for [data/README.md](../../data/README.md) (not edited; another session's file)

> **`external/ipip/`** (git-ignored) holds the IPIP pages fetched by `ipip_generator.py download`
> (the item list, the item assignment page, the scale index, and, once approved, Tedone's item
> assignment workbook), with `DOWNLOAD_MANIFEST.json` (URL, size, sha256 of the received bytes,
> date, approval).  **`candidates/ipip/`** (tracked) holds the IPIP generator's own files:
> `sources_manifest.json` (the manifest's tracked copy), `items.jsonl` (one row per item: code,
> codes, text, scales with key signs), `ingest_counts.json`, `clusters_g350.jsonl` and
> `clusters_g150.jsonl` (consensus clusters, poles, blind and hinted names), `cluster_summary.json`,
> `naming_responses.jsonl` and the usage files, `granularity/` and `granularity_readout.{json,md}`.
> Runs are under `candidates/runs/ipip/`.  Plan:
> `reports/trait_gap_generation/coding_plan_07_behaviour_items.md`.
