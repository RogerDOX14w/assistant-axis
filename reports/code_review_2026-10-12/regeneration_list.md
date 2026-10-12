# What needs regenerating after the review's fixes

Started 2026-10-12 at Roger's request ("a list of data (gap filling work, caches, plots, etc) that now needs
regenerating as a result of bugs we've fixed").  One entry per thing on disk that a fixed bug made wrong,
stale or incomplete: registry blocks, judge caches, vectors, plots, tables, readouts, usage records.

**Every agent that fixes a bug adds an entry here** when the fix leaves recorded output wrong or stale, in
the same commit as the fix, or says in its report that nothing needs regenerating.  A row is closed when
the regeneration has run: put the commit or batch id in **status**.  The review's decisions are in
[escalations.md](./escalations.md); the gate fixes in [gate_audits/README.md](./gate_audits/README.md).

**When** takes one of four values:

- **now**: wrong today and cheap; run it in the fix batch.
- **before October**: must be done before the October activation extraction starts.
- **at the October run**: the October extraction or its re-score regenerates it anyway; nothing to do
  except make sure the run covers it.
- **never**: recorded as a known limit of historical output; kept for the record, not regenerated.

Costs are API dollars unless marked.  Anything over $20 in one invocation still needs Roger's go with
quoted parameters.

## Gap-filling work (the gate fixes, phase B)

The order matters: each step sees the verdicts written before it.  Commands are in each fix agent's
report and in [gate_audits/README.md](./gate_audits/README.md) "Fixes".

| # | what | why (fix) | how | cost | when | status |
|---|---|---|---|---|---|---|
| G1 | M1 verdicts on 126 phrase rows (the alignment papers, IPIP probe cuts, the alignment batches) | the definition probe cut phrase labels unread (gate 5, 1920bbc2) | `traithood_filter.py --batch-id 2026-10-13-m1_phrase_rejudge --keys <126 keys>`, then M3 on the rows that become traits | about $1.9 live | now | |
| G2 | 20 more phrase rows from Roget, the censuses and the antonym and validation runs | same | same, on the "others" set | under $1 | now | |
| G3 | base-model candidates at count 2 or more (about 219 new rows) | the count floor of 8 discarded half the trait words; rule 1b missing in the table (gate 3, 29610c17) | `base_model_generator.py parse`, `sense`, `stats`, `submit --min-count 2`, then M1 and M3 | about $3.5 live | now | |
| G4 | the census table (OEWN lemmas) and the `allport_rare` (926) and `allport_iv_rare` (310) submissions | the column-IV words below the floor had no stage; the floor's rescues were lost (gate 1, 1920bbc2) | `census_generator.py ingest`, `submit` both stages, M1 and M3 by batches | about $8.5-10.5 batch | now | |
| G5 | irresolute's floor reject | defect F3: another generator's earlier floor reject defeated the census rescue (1920bbc2) | `traithood_filter.py --run censuses/2026-10-10-tda`, then M3 and the TDA report | cents | now | |
| G6 | Roget (14) and WordNet (178, 70 new rows) candidates; the Roget coverage report | WordNet depth 3 had no basis; rule 1b missing in both dictionary walks (gate 2, fc1834b2) | `roget_generate.py harvest --delta-from 2026-10-11-full`, `submit` both, M1, M3, then `coverage` | about $1.1 | now | |
| G7 | M3 decisions on 187 rows of 20 batches (new to covered) and 8 stage-0 leak rows | the graded cut-off at alignment 2; a renamed trait's old stem was checked after the seed queue (gate 6, review 2 D1; 403cbd6a) | `novelty_score.py score --redecide --from-batch B --rules 3 --write-registry` per batch, then `gap_registry.py compact` | about $0.06 | now | |
| G8 | M3 decisions of 33 `2026-10-11-full_roget` rows made on glosses that have since been rewritten | found by the M3 fix agent: the rows were re-glossed after M3 judged them | `novelty_score.py score --rescore` on those rows | under $1 | now | |
| G9 | the states pass on the 245 judged rows (7 change), the 900 unjudged states rows and the 126 physical rows | the gloss check held traits; one-hop rows were held (gate 7, fb66cc14) | `states_pass.py --reroute --send-missing`, then the passes, then M3 on released rows | about $3 live | now | |
| G10 | IPIP: cluster tables (done at $0 in 3f1d78e2), naming, granularity readings, submission, M1, M3 | the Jaccard gate held 65-92% of clusters (gate 4) | after C1 below: naming at 600/350/150, `granularity --signals nearest`, `submit --granularity 600 --all-poles`, M1, M3 | about $11 | now | |
| G11 | the review graph, all batches | the pair floor and label-variant links (gate 8, 0b9ce75e); and every step above changes its input | the Opus pilot ($0.42 live), then `review_graph.py build` over all trait-track batches | about $31 | after G1-G10; **needs Roger's go** | |
| G12 | the `evaluation.json` and `readout.md` of the four recorded census runs: [2026-10-08-pilot](../../data/candidates/runs/censuses/2026-10-08-pilot/evaluation.json), [2026-10-09-iv-pilot](../../data/candidates/runs/censuses/2026-10-09-iv-pilot/evaluation.json), [2026-10-09-rare-pilot](../../data/candidates/runs/censuses/2026-10-09-rare-pilot/evaluation.json), [2026-10-10-tda](../../data/candidates/runs/censuses/2026-10-10-tda/evaluation.json) | the evaluation wrote `tda_cut: 0` whatever the registry said, listed no floor rejects and used stale stage pools (gate 1, defects F4 and F5; 1920bbc2); checked: all four say `tda_cut: 0` | `census_generator.py report --run-id <run>` for each, after G4 and G5 so the new verdicts are in ([2026-10-11-allport_hi](../../data/candidates/runs/censuses/2026-10-11-allport_hi/) has no evaluation yet; G4's own report writes it) | $0 | now, after G4 and G5 | |
| G13 | the M3 decisions of [m3_pilot_1_r2](../../data/candidates/novelty/m3_pilot_1_r2/) (460 rows: 254 covered, 206 new, under rule set 2) | G7's re-decide cannot replay them (gate 6, 403cbd6a: the pilot's pools have drifted, 143 calls are not on record, 3 of 460 reproduce), so these rows alone stay under rule set 2 while every other trait-track batch moves to the graded cut-off; they are in G11's build list | `novelty_score.py score --rescore --rules 3 --keys <the 460 keys>` (fresh calls) | about $6 live (460 rows at the audit's $0.013 a row; the pilot itself cost $8.49) | **ask Roger** (recommended before G11: going by the other batches, about 4% of the 206 "new" rows would become covers) | |
| G14 | the Krakovna rows of alignment-sweep variant B: run [2026-10-11-b](../../data/candidates/runs/alignment_sweep/2026-10-11-b/) (60 poles) holds the agentic-misalignment source only | variant B converted the Krakovna sheet from HTML twice and got 0 chunks at no cost (review 6, 04301c7b); the record says a rerun needs Roger's word | `alignment_sweep.py extract --run-id 2026-10-11-b --variant B` (reuses the 31 answered chunks), then `submit`, M1 and M3 | a few dollars live (dry-run first for the figure) | **ask Roger** | |

## Caches, plots and analysis outputs

| # | what | why (fix) | how | cost | when | status |
|---|---|---|---|---|---|---|
| R1 | two response-judge caches with a marker-less reply | the analysis parser read a digit from the reasoning (walk-through D5) | hand-edited to None, with backups and envelope notes | $0 | now | done 2026-10-12 |
| R2 | the winner-decomposition figure of the PC round-trip study, and the ~12 boundary reading | it decomposed the nth PC at the fixed-principled winners' cell, and skipped slots 0 and 3 (walk-through D1) | record per-cell winners in `klm_sweep.py`, regenerate and retitle | $0, CPU-hours to estimate | now | |
| R3 | every response-mode plot (slot, shear and layer plots on GPT-only responses) | standardise on the GPT+Haiku blend (walk-through D10) | regenerate from the October re-score | at the re-score | at the October run | |
| R4 | the May judge caches deferred under `legacy_bare` (832 without envelopes, 915 stale with) | the blanket globs hid stale envelope-carrying caches (walk-through E10) | record their real state under a new category; regenerate at the October re-score | at the re-score | at the October run | |
| R5 | IPIP scoring keys, then ingest, cluster and the names of changed poles | the merge gap-filled workbook rows the key pages already held (C1) | after the fix: `ipip_generator.py ingest`, `cluster`, re-name changed poles | cents | now, before G10 | |
| R6 | the current pair lists (`goal_type`) and a `_v1` snapshot of the pre-W15 goal file | the current lists predate the W15 goal lists (walk-through A3) | snapshot, then regenerate the current lists from the W15 file | $0 | before October | |
| R7 | the usage record of `m1_validation_r2` | a resume lost the killed session's spend (walk-through B3) | rebuild from its responses | $0 | now | |
| R8 | [rubric_v1_v2_compare_slot6.json](../../roger/axis_judge_experiments/rubric_v1_v2_compare_slot6.json) and [.png](../../roger/axis_judge_experiments/rubric_v1_v2_compare_slot6.png) (tracked, 2026-05-22) | the Sonnet desc/inst caches were never key-migrated, so the "combined" columns were GPT-only although the plot says GPT+Sonnet (review 9b B1, 8cd82ed0); regenerated, the combined means move 0.7392 → 0.7429 (rubric v1) and 0.7606 → 0.7656 (v2), the v1→v2 gain +0.0213 → +0.0227; response columns unchanged | `results_analysis/rubric_v1_v2_compare.py` (defaults, slot 6) | $0, CPU minutes | now | |
| R9 | [response_di_weight_sweep_slot6_softshear3.json](../../roger/axis_judge_experiments/response_di_weight_sweep_slot6_softshear3.json) and [.png](../../roger/axis_judge_experiments/response_di_weight_sweep_slot6_softshear3.png) (tracked; the 22-axis `_v1` record, 2026-05-22) | three v1 GPT caches were not migrated, so desc+inst was Sonnet-only on [accessible](../../data/traits/instructions/accessible.json) / [esoteric](../../data/traits/instructions/esoteric.json), [benign](../../data/traits/instructions/benign.json) / [malicious](../../data/traits/instructions/malicious.json) and [introverted](../../data/traits/instructions/introverted.json) / [extroverted](../../data/traits/instructions/extroverted.json) (review 9b B2 and B14); regenerated, the parabolic peak moves from w 0.956 to 0.938 and rho 0.7581 to 0.7596 | `results_analysis/response_di_weight_sweep.py --pair_list pair_list_responses_v1.json` with the soft-shear L=3 whitening that named the file (the cohort token `_responses_v1` goes into the new output names; a default run averages 20 axes, not 22) | $0, CPU minutes | now | |
| R10 | [shear_l_vs_k_comparison_di_slot6.json](../../roger/axis_judge_experiments/shear_l_vs_k_comparison_di_slot6.json) (tracked, 2026-05-12; its own 35-axis cohort) | `_strip_kind` could pair a trait's score with the role's projection, and v1 Sonnet caches went unmigrated (review 9b B3); recomputed on its 35 axes, desc+inst moves by at most 0.007 per axis and 0.0003 in the cohort means, responses unchanged | `results_analysis/shear_l_vs_k_comparison.py --pairs <the 35-axis list its envelope records>` | $0 | never (negligible, and the 35-axis cohort is itself historical, superseded by the 61-axis di list) | |
| R11 | [batch_size_cost_vs_quality.png](../../roger/axis_judge_experiments/batch_size_curve_8slot/batch_size_cost_vs_quality.png) (untracked, 2026-05-11 23:04) | its spec line hard-coded "0.6·gpt + 0.4·anthropic" where the ensembles side-car records 0.625 (review 9b B8), and the PNG predates that side-car (2026-05-12 00:32); the numbers are unaffected | `results_analysis/plot_batch_size_quality_vs_cost.py` (reads the side-car) | $0 | now | |
| R12 | [pc_round_trip_winner_consistency.png](../../roger/pc_round_trip_winner_consistency.png) (untracked, 2026-05-09) | the L panel dropped every L=4 winner (14 of 48 actual, 1,317 of 4,800 null; its bars summed to about 0.71) and 4 of the 7 cells were grey (review 9b B11) | `results_analysis/pc_round_trip/plot_winner_consistency.py --actual roger/pc_round_trip_klm_results.json --null roger/pc_round_trip_null_klm_results.json` | $0, seconds | now, with R2 | |
| R13 | [rho_peak_K_weighted_scatter_responses_slot6.png](../../roger/axis_judge_experiments/rho_peak_K_weighted_scatter_responses_slot6.png) (tracked) and the slot 3 and 7 twins (untracked) | the weighted fit passed w where `polyfit` expects 1/σ, so it weighted by w² (review 9b B7); only the green line moves, the printed correlations stand | `results_analysis/whitening_k_weighted_scatter.py --slot {3,6,7}` with the recorded sweep inputs | $0 | now (R3 regenerates them again on the blend in October) | |
| R14 | [rho_by_slot_and_K.png](../../roger/axis_judge_experiments/rho_by_slot_and_K.png) and [rho_by_slot_and_L.png](../../roger/axis_judge_experiments/rho_by_slot_and_L.png) (tracked) | the title and x-labels counted the pair list (61), not the caches that loaded (one Sonnet cache postdates the K plot, so the count may be 60); rho values unchanged (review 9b B10) | with R3 | $0 | at the October run (R3) | |
| R15 | the judge caches of [impatient_vs_patient](../../roger/axis_judge_experiments/impatient_vs_patient/) (8 caches) | the pole skip compares bare names, so the role [patient](../../data/roles/instructions/patient.json)\|R was never judged and is missing from rho and the whitener pool (review 9a D2; a design issue, fix pending: skip by (pair_type, name)) | at the next rejudge of that axis, after the fix | about $0.01 a judge | at the October run | |
| R16 | the recorded 0.525 Haiku-weight retune, [gpt_haiku_q9_response_weight_sweep_slot6_softshear3.json](../../roger/axis_judge_experiments/gpt_haiku_q9_response_weight_sweep_slot6_softshear3.json) / [.png](../../roger/axis_judge_experiments/gpt_haiku_q9_response_weight_sweep_slot6_softshear3.png) and the [`__rubric_v2` pair](../../roger/axis_judge_experiments/gpt_haiku_q9_response_weight_sweep_slot6_softshear3__rubric_v2.png) (2026-05-22; the rubric-suffixed PNG is tracked) | 12 of its 22 axes ran on about 43 entities, not about 580 (`prefer_b` (7,) with no `_b10_q9` inputs; review 9a D1); recomputed on full coverage the peak is w=0.575 at rho 0.7422 against 0.7421 at 0.525, so the constant stands and only the recorded evidence is wrong; the "Selection history" note in [judge_score_combine.py](../../assistant_axis/judge_score_combine.py) still says otherwise | `results_analysis/gpt_anthropic_response_weight_sweep.py --pair_list pair_list_responses_v1.json --rubric v2 --whitening soft_shear=3` | $0, CPU minutes | at the October run (walk-through D2: the retune comes with the re-score) | |
| R17 | the Google Sheets tabs exported while another experiment's blocks were kept (most likely an all-mode experiment and its `_prefill` twin, which share a tab) | the merge copied only the two frozen rows: the first kept block's header and first data row were merged into single cells, the persona and axis rows displaced, and responses starting with "- " shown as #ERROR! (review 10, c88c4bdb); nothing on disk records which tabs were exported | re-export each affected experiment with [steering_to_gsheet.py](../../tools/steering_to_gsheet.py) `--wipe-tab` (the online path is untested: one replace-mode export into a scratch tab first) | $0 (Sheets API) | **ask Roger** (which tabs) | |
| R18 | the local copies of the pod sweeps under [outputs/qwen-3-32b/steering/](../../outputs/qwen-3-32b/steering/) (124 experiments) | [rsync_pod_sweeps.sh](../../scripts/rsync_pod_sweeps.sh)'s `--append-verify` skipped any file the pod rewrote shorter (`summary.json`, `records.jsonl`), and on macOS openrsync every attempt failed with exit 0 (review 10); which files, if any, are stale cannot be told from this side | re-pull with the fixed script, if a pod still holds the sweeps | $0 | **ask Roger** (recommendation: never, unless a pod still has them) | |
| R19 | the cell `s3_l25_+1` of [teacher_egalitarian_v1](../../outputs/qwen-3-32b/steering/teacher_egalitarian_v1/) | its worker logged `item 'cell' failed` (an NFS I/O error, 2026-05-03) and the sweep reported success (review 7, 12fa5ac8): 134 records, no `summary.json`; the only such line in the 84 local sweep logs | re-run the cell with [run_sweep.py](../../steering/run_sweep.py) on a pod, or leave it | under a GPU-hour | **ask Roger** (recommendation: never; a slot-3-era sweep from the first days of May) | |
| R20 | the paid usage of the base-model sense step (round 1, $0.05) | it lives only in the git-ignored [cache/base_model/round1/gloss_sense_usage.json](../../data/candidates/cache/base_model/round1/gloss_sense_usage.json) and [usage.json](../../data/candidates/cache/base_model/round1/usage.json) (review 6 D4; walk-through B2: retrofit now) | after B2's retrofit, write the tracked per-round record from the cache file | $0 | now (the B2 fix agent closes it) | |
| R21 | the `OVERRIDES` start-strength table in [sweep_start_heuristics.py](../../assistant_axis/sweep_start_heuristics.py) | it was derived with [analyse_start_strength.py](../../tools/analyse_start_strength.py)'s grading rule, which differs from the runner's stop rule (review 10 D3; walk-through D11 (a): align the tool first) | after D11's fix, rerun the tool over the recorded sweeps; re-derive the table only if a cell changes grade | $0 | now, after the D11 fix | |

## Vectors and activations

| # | what | why (fix) | how | cost | when | status |
|---|---|---|---|---|---|---|
| V1 | every stored entity vector and `axis.pt` | bf16 accumulation and storage at steps 4 and 5 (walk-through P3) | the October extraction writes float32 | GPU time of the run | at the October run | |
| V2 | every role judgment | artefacts in all 339 role eval prompts (walk-through P4; the wording waits on Roger) | the October step 3 re-judges every role | in the run's judge cost | at the October run | |
| V3 | [traits/axis.pt](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/traits/axis.pt) (8slot, 2026-05-02) | stale against [traits/vectors/unhelpful.pt](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/traits/vectors/unhelpful.pt) (2026-05-04): max difference 8 bf16 units, cosine ≥ 0.998 (P4 measured); nothing references it; [roles/axis.pt](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/roles/axis.pt) verified bit-for-bit | `pipeline/5_axis.py --vectors_dir <8slot>/traits/vectors --output <8slot>/traits/axis.pt` ($0, minutes; still bf16 until P3's float32 lands), or leave it to V1 | $0 | at the October run (V1) | |
| V4 | the whole 8slot tree: the responses, activations, scores and vectors of the 554 trait and role entities and the 1,800 combinations | every one of the 554 trait/role response files was generated from instructions that have since changed, and 28 of their stems have left the corpus (P1 D2); 473 of about 1.19 million responses carry leaked thinking (168 scored 3) and entered the vectors (P1 D4); the combination [zealot](../../data/roles/instructions/zealot.json) / [pensive](../../data/traits/instructions/pensive.json) (3 score-3 responses, activation deleted) was invisible to the scanner and is the 1,793rd entity missing from `combinations/axis.pt` (P4) | the October extraction in a fresh OUTPUT_DIR, with the `generation_config.json` side-car and the `thinking_suspected` flag (walk-through P2, P6) | the run | at the October run | |
| V5 | step-3 scores where the judge wrote `SCORE: 4` or higher and a 0–3 digit from its reasoning was scored instead | the parser's last-digit fallback (P3 fix 1, 56f3df3e); raw judge text is not stored, so the cases cannot be found; very rare on a 0–3 rubric | none possible; the October step 3 (marker required, `JUDGE_RUBRIC_VERSION` 3) re-judges everything in a fresh tree | – | never | |

## Added by fix agents

(Agents append rows here, in the table form above, one row per item.)

| # | what | why (fix) | how | cost | when | status |
|---|---|---|---|---|---|---|

## Checked: nothing to regenerate

Fixes whose recorded output was checked (by the reviewer, by the fix agent, or for this list on 2026-10-12)
and found unaffected, one line per fix, grouped by review.  A fix that has a row above is named only by its
row.  The commit hashes are the ones in [escalations.md](./escalations.md).

**Review 3 (d0d8f20e).**  States-pass gloss as the draft: 0 of the 71 released and 0 of the 1,145 states
rows carry their own gloss, and the one released row promoted so far (amorous#1) got the right draft.
Promote of a key named twice: output only.  Recovery links both ways: the corpus has 0 one-sided links and
the four recorded draws are unchanged.  Timestamp under the writer lock: nothing orders by `updated_at`.
(D2's stale [registry.snapshot.jsonl](../../data/candidates/registry.snapshot.jsonl): G7's compact rewrites
it, gzipped after A5.)

**Review 6 (04301c7b).**  Gate and extract stopped by the cap: no recorded session reached its cap (the
highest spend $7.54 of $12), and every `extract_summary.json` has `stopped_by_budget: false`.  Readout
wording: no run has a `readout.md`, and the papers run's
[gate_gold_eval.md](../../data/candidates/runs/alignment_sweep/2026-10-11-papers/gate_gold_eval.md) already
counts "25 of 29 answered".  Base-model parse: the biography screen ran on all 419 person samples.  Sense
cap: $0.05 of $2.  [stats_round1.json](../../data/candidates/base_model/stats_round1.json): refreshed in the
commit, and G3 rewrites it.  Variant B's Krakovna rows → G14.

**Review 2 (44039ac1).**  One-unparsed-plus-one-failed calls: none in any recorded novelty, near-duplicate
or recovery run.  Embedding-cache race: no lost entry; the texts of the 2026-10-10-full alignment batch
live in the gen02 worktree's cache, but that batch's 286 rows were re-submitted as
[2026-10-11-papers](../../data/candidates/runs/alignment_sweep/2026-10-11-papers/) (the registry has no row
sourced from run 2026-10-10-full), so nothing replays it.  Canary threshold: equal to the old default.
D1 (the renamed-from leak) → G7.

**Review 9a (0e215a88).**  PC round-trip loader:
[pc_round_trip_klm_results.json](../../roger/pc_round_trip_klm_results.json), the
[null cache](../../roger/pc_round_trip_null_klm_results.json) and the direction-cosine PNGs date from
2026-05-06/09, before the loader broke on 05-11 (R2 regenerates with the fix).  gpt_sonnet migration
order: identical on all 155 caches.  Seriation `_v1` cohort: the recorded heatmaps used cohort `clean`,
and no `_v1` output is on disk.  `--pair_list` / `--pairs_responses`: defaults unchanged, console only.
launch_judge_runs, optimal_axis, the None filter, the rho floor: no output.
[summary.json](../../roger/axis_judge_experiments/summary.json) (2026-05-23): 1,728 rows, so the
envelope bug of review 9b B5 did not reach it.  D1 → R16; D2 → R15; D3 and D4 → R6.

**Review 4 (fd89b61f).**  Both decision logs end in a newline and every line parses (review_tda_1 354
lines, review_states_v4 13); replay skips 0 events; a dry-run apply of review_tda_1 gives 0 conflicts; its
graph has no edge read 4 one way and under 3 the other, so the leftovers count Roger saw was right.

**Review 8 (2fc4ff07).**  Every corpus file has 5 instructions and 40 questions (932 traits, 340 roles);
the one batch-written file whose description changed inside a batch window
([chaotic](../../data/traits/instructions/chaotic.json)) was edited before submission; no ERROR answer in
the queue or the antonym history; the combination scores were charged once (1,800 + 1,020 calls); all
11,289 goal classifications are well-formed; [engaged](../../data/traits/instructions/engaged.json) and
[turbulent](../../data/traits/instructions/turbulent.json), which `--stems` skipped, have their files.

**Review 9b (8cd82ed0).**  variance_decomposition: all 1,793 combinations have both standalone vectors.
`--ca_kind`: the old choices only crashed.  run_axis_experiment_batch: the recorded summary has rows (above).
The winner-decomposition title → R2.  The rest → R8 to R14.

**Review 5 (7220a37f).**  IPIP naming re-asks (362, $0.07): the second answers were used throughout, and
the tables and the g600 submission agree.
[cluster_summary.json](../../data/candidates/ipip/cluster_summary.json): holds all three cuts again since
3f1d78e2.  Granularity budget stop: all three run.json say `budget_exceeded: false`.  Roget hints (free,
sound) and WordNet hints (defensive, mum): cosmetic, already judged.  Census `--file`: every run.json has
one session.  `_key_sign`: the workbook holds only 1, −1 and 0.  D1 → R5; D4 → G6.

**Review 7 (12fa5ac8).**  drain() race: the local sweeps have 0 `legacy_unidirectional` cells (1,013
bidirectional; 27 older summaries without the field, of which only the two `smoke_test_v1` cells have
unjudged last strengths).  Mis-filed coherence verdicts: 0 `coherence_alts` entries in the 230,696 local
records.  Worker exit status: one `item 'cell' failed` in the 84 local sweep logs → R19.  `prefill_only`:
crashed at launch, no spend.  save_responses: every 8slot response file has 500 lines (2,386 files).
2_activations dead workers: the two 8slot incidents were repaired by hand at the time (P2).  run_pipeline
pipefail: the April and May step failures are in the hand-repaired 8slot tree, which V1 and V4 replace.
load_or_create, 3_judge's corrupt-file log, the boundary hook: no data.

**Review 1 (a2ac553b).**  split_runner record-before-parse: the only `stopped_by_error` run is
m1_validation (an unrelated protocol error).  `_num`: no recorded hit.
[versions.json](../trait_gap_generation/rubrics/versions.json): holds exactly the pinned names.
cost_by_step: identical on every split record.  No resume crossed a pin change.  D1 → R7.

**Review 10 (c88c4bdb).**  [script_equivalences.yaml](../../script_equivalences.yaml): 3 edges, each
independently checked; the 88 payload-first envelopes have no edge.
[rubric_equivalences.yaml](../../rubric_equivalences.yaml): 3 edges, all scoped (checked).  audit_caches:
0 stale_transitive today.  The derived-layout prune never ran.
[base_persona_candidates.txt](../../roger/axis_judge_experiments/base_persona_candidates.txt) (May 20) is
intact.  The 28 effect-swap files predate v7.  All 1,209 recorded `s_init` equal the config's.
diagnose_unparseable: scratch output only.  Lint: 0 findings.  The 54 one-offs: no reported number changed
(several are dangerous to rerun; listed in the record).  D1 → the A1 guard; D2 → R6; D3 → R21; the Sheets
merge → R17; the rsync pull → R18.

**P1 (cc490235).**  The 8slot logs show no step-1 worker failure, dropped entity or crossed file; the 9
names with both a role and a trait file have distinct files; the questions file is unchanged since the
run.  D2 and D4 → V4.

**P2 (11d7f28c).**  The 8slot tree was extracted under transformers 4.57.6 with 500 keys per entity and 0
header misses; the dead-worker and no-space incidents were repaired by hand at the time.

**P3 (56f3df3e).**  Score files byte-identical; no trait or role has unscored responses, so no merge was
clobbered; 0 repeated keys in 2,386 files; no batch-mode extraction has run; prompts byte-identical (no
braces in corpus text); the 8slot scores directories hold no side-car files, so D12's fingerprint
exclusion changes no recorded cache (the edit gets an equivalence mark).  The reasoning-digit scores → V5;
the role artefacts → V2.

**P4 (ba4efef2).**  No `corrupt_vector` in the May audits; no stem but `default` contains "default"; the
May vectors carry no `inputs` record and count as current under P4 D3; the pod's 111 placeholders were
under half the roles directory, so no truncation was missed; `traits/axis.pt` → V3; the 1,793rd
combination → V4.

**1dd5ed54** (`splitlines`): none of the 2,386 April response files holds U+2028, U+2029 or U+0085.
**47360a6d** (FileNotFoundError): time only.  **e92912d8** (the scan between steps 4 and 5): driver only.
**cdb34d49**: D10's optional blended `shear_l_sweep` rerun is done (`roger/`, untracked).  **2e2f1a25**:
notes only.

**Gate fixes.**  3f1d78e2 (IPIP): the tables were regenerated at $0; the six pole names the re-cut lost
come back with G10's naming.  0b9ce75e (R1) → G11 (its 8 hyphen-variant pairs are registry duplicates; a
dedup is a design question, not a regeneration).  1920bbc2 → G1, G2, G4, G5, G12.  29610c17 → G3.
fb66cc14 → G9.  fc1834b2 → G6.  403cbd6a → G7, G8, G13.
