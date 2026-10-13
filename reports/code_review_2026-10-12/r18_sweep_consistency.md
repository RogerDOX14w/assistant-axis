# R18: consistency of the local steering sweeps

2026-10-13, for row R18 of [regeneration_list.md](./regeneration_list.md).  The check was offline and
read-only: nothing under [outputs/](../../outputs/) or [runpod_workspace/](../../runpod_workspace/) was
changed, no API was called ($0), and it took about two CPU minutes.  All times are UTC.

## In short

- **No damage from `--append-verify` was found.**  No `records.jsonl` ends mid-line or repeats a
  (strength, question) pair.  Of the 998 bidirectional cells, 997 have a `summary.json` that the runner's
  own code reproduces from the records.  The one pod operation that rewrites `records.jsonl` shorter, the
  corrected stop cutoff, was never run on the pod: it was run on the Mac.  The evidence is 16 resume lines
  in the pod's sweep logs, written after the local cutoff runs, which still count every record.  Where the
  local copy is older than the pod, no pull happened after the pod's later work.
- **A later copy of the same sweeps is already in the repository**:
  [runpod_workspace/qwen/qwen-3-32b Roger 8slot/steering/](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/)
  ("the 8slot copy").  Its sweep logs run to 2026-05-31 00:18, against 2026-05-30 21:07 here.  Commit
  8f647c13 (2026-05-31) made it "the canonical (re-filtered) steering output directory" for
  [analyse_start_strength.py](../../tools/analyse_start_strength.py) and
  [per_question_responsiveness_audit.py](../../tools/per_question_responsiveness_audit.py).  It holds
  every experiment that is missing here, and the later version of 33 of the 35 suspect cells.  For the
  other two it is no better: one is the cell R19 left, and the other lost a strength on the pod itself.
- Classes over the 1,020 cells of [outputs/qwen-3-32b/steering/](../../outputs/qwen-3-32b/steering/)
  (83 experiments; the 7 smoke-test cells are left out):

  | class | cells |
  |---|---:|
  | consistent | 957 |
  | summary stale against the records | 4 |
  | records truncated | 1 |
  | other: older than the pod (the pod changed the cell after the last pull) | 27 |
  | other: diverged (Mac-side work here, later pod work in the 8slot copy) | 31 |

  Beside the cells: 15 experiment directories here are empty, and 14 cell directories sit at the top
  level by mistake (both below).
- The suspect cells are in the [table below](#suspect-cells).  The list of files to fetch is
  [r18_suspect_files.txt](./r18_suspect_files.txt): 77 lines, 62 files in 34 cells and 15 experiment
  directories.  The same paths exist in the 8slot copy.

## Terms

- **Cell**: one steering run of an experiment, a directory `s<slot>_l<layer>_<sign>` such as
  `s6_l25_+1`.  It holds `records.jsonl` (one line per response with its judgements),
  `summary.json` (the runner's record of how the scan ended) and, after the cutoff,
  `_excluded_records.jsonl`.
- **Strength**: the size of the steering coefficient.  Each strength has K responses, one per question
  (K = 14 in most experiments, 6 or 10 in the oldest).  **s_init** is the strength the bidirectional scan
  starts from, and a scan stops upward at two incoherent strengths and downward at two strengths with
  too little effect.
- **Corrected stop cutoff**: [post_judge.py](../../steering/post_judge.py)
  `--apply-corrected-stop-cutoff`.  It moves the records below a weak-effect anchor strength out of
  `records.jsonl` into `_excluded_records.jsonl`, and lists those strengths in `summary.json`
  (`excluded_strengths`).  This is the only routine step that makes `records.jsonl` shorter, so it is
  what `--append-verify` would have missed.
- **Re-filter**: the corrected stop cutoff applied to the 8slot copy on 2026-05-31 21:57.  It rewrote
  2,886 files (962 cells) within 14 seconds, too fast for the pod's network storage, so it was almost
  certainly run on the Mac.
- **Swap fill**: [post_judge.py](../../steering/post_judge.py) `--effect-swap-fill`, the effect
  judgement repeated with the two texts swapped (effect rubric 7).
- **Replay**: running the runner's own resume and stop logic
  ([steering_runner.py](../../assistant_axis/steering_runner.py) `run_steering_cell`) over a cell's
  records with no model and no judge, then comparing the `summary.json` it would write with the one on disk.
- **The pod's version**: what the pod held when the 8slot copy was pulled, after its last sweep.  "Older
  than the pod" means the pod changed the cell after this copy's last pull.

## What was checked

For every cell, with the same checks run on the 8slot copy for comparison:

1. **The files themselves.**  Every line of `records.jsonl`, `_excluded_records.jsonl` and every
   baseline file parses, and every file ends with a newline (1,041 records files, 292 excluded files,
   88 baseline files).  No `records.jsonl` repeats a (strength, question) pair.  No strength has fewer
   than K responses, except the R19 cell.
2. **summary.json against the records, by replay.**  Real code paths only: generation, the judge calls
   and every file write were intercepted, and the records were handed over in memory.  The replay ran on
   `records.jsonl` alone and with the cutoff's rows put back (the scan's full history).  It used the
   runner of today, or for the 63 summaries written before 2026-05-17 (`eff_stop_threshold` 0.25) the
   runner of 2026-05-15 (commit 983b0d09).  That runner's downward stop used the mean of |effect|, not
   |mean effect|.  For 4 cells it also needed the effect scores as they stood before a later swap fill.
   The fields compared: stop strength and reason, both blocked-at strengths and reasons, s_init,
   `n_records`, `last_strength_completed` and `n_strengths_swept`.  `n_strengths_swept` may differ by one,
   since it counts s_init only when the final session generated it.  997 of 998 reproduce exactly.
   `summary.json` holds no per-strength means.  The runner recomputes them from the records (the
   `strength_mean_coh` stamps and |mean effect.combined|), and the replay reproduced every stop decision
   they drive.  The 22 cells from before the bidirectional scan (2026-05-02/03, no `scan_mode`) were
   checked directly: `n_records`, stop strength and last strength against the records; all agree.
3. **summary.json older than the records' last judgement.**  `summary.json` carries no time, so its
   file time stood in.  The files here mostly keep the pod's times; the pull used `rsync -a`.  In 701
   cells the last judgement lands under a minute after the summary.  That is normal: the runner writes
   `summary.json` before the last persona and effect calls return.  Three cells exceed a minute:
   [architect_ecocentric_v2/s3_l25_+1](../../outputs/qwen-3-32b/steering/architect_ecocentric_v2/s3_l25_+1/),
   [architect_ecocentric_v2/s3_l25_-1](../../outputs/qwen-3-32b/steering/architect_ecocentric_v2/s3_l25_-1/)
   and [chef_helpful_v2/s3_l25_+1](../../outputs/qwen-3-32b/steering/chef_helpful_v2/s3_l25_+1/).  Their
   effect scores were judged again at rubric 6 on 2026-05-15 14:11-15:35, ten hours after the sweep.  That
   was the fix for scores written as "+1"; [post_judge.py](../../steering/post_judge.py) leaves
   `summary.json` alone, and the replay still reproduces the summary.
4. **The sweep logs.**  The events of each cell were read from the sweep logs of both copies; the
   8slot copy's logs extend these: stop, skip, judged, resume, gap-fill, cap extension.  Three checks:
   the last "already stopped at" strength against `summary.json`; every strength the log says was judged
   against the records; and pod work after this copy's files were written.  All judged strengths are on
   disk but one (navigator, below).  Pod work after the files explains every "older than the pod" cell
   below.  For the 2026-05-21 cap extension of the first-wave experiments, some lines went only to the
   run's master log.
5. **The two copies, by content.**  Each cell here was compared with the 8slot copy, record by record:
   which records each copy holds, how they are split between `records.jsonl` and
   `_excluded_records.jsonl`, the judge scores and their times, and the summary fields.  This sorted
   the differences into the pod's later work, the re-filter, and Mac-side work here.

## Results

### Consistent: 957 cells

- **454** hold the same content as the 8slot copy: 330 byte for byte, and 124 apart from repeated
  rows (next point).
- **132** cells have rows repeated in `_excluded_records.jsonl` (18,702 extra rows, the same rows two or
  three times).  They are in 16 first-wave experiments (the sweeps of 2026-05-17 to 05-20).  The corrected stop cutoff
  was run here on 2026-05-18 22:41-23:06, 2026-05-19 22:53 and 2026-05-22 07:34 UTC, and each time a pull
  had brought back the pod's full `records.jsonl`, so the cutoff moved the same rows again.  The
  distinct rows match the 8slot copy.  Nothing reads these files but [post_judge.py](../../steering/post_judge.py), which only
  appends, so no analysis is affected.
- **503** cells in 54 experiments differ from the 8slot copy only by the re-filter: the 8slot copy has
  moved weak strengths out of `records.jsonl`, this copy has not.  This copy holds what the pod held.  To
  make it match the canonical copy, run the cutoff again; there is nothing to copy.

### Summary stale against the records: 4 cells

[anarchist_concise_v1/s6_l49_-1](../../outputs/qwen-3-32b/steering/anarchist_concise_v1/s6_l49_-1/),
[publisher_guileless_v1/s7_l49_+1](../../outputs/qwen-3-32b/steering/publisher_guileless_v1/s7_l49_+1/) and
[publisher_guileless_v1/s7_l49_-1](../../outputs/qwen-3-32b/steering/publisher_guileless_v1/s7_l49_-1/).
Their records come from the cutoff run here on 2026-05-18.  Their `summary.json` is the pod's later
rewrite, which drops the `excluded_*` fields: the pod had not cut these cells, and its logs say
"resuming with 238 (210) existing records".  The pod rewrote `summary.json` once more on 2026-05-22
15:50 (`max_strength` 256).  The 8slot copy has that version.

[navigator_progressive_v1/s0_l49_+1](../../outputs/qwen-3-32b/steering/navigator_progressive_v1/s0_l49_+1/)
is a different case: a strength lost on the pod.  Its
[summary.json](../../outputs/qwen-3-32b/steering/navigator_progressive_v1/s0_l49_+1/summary.json) (`n_records` 238) and the
[sweep log](../../outputs/qwen-3-32b/steering/navigator_progressive_v1/sweep.log)
both count strength 3.359487, judged at 2026-05-17 15:24, but neither records file here nor in the 8slot
copy has it.  The log shows why.  The resume at 2026-05-18 00:08 found that strength "incomplete": its
persona and effect had been skipped at mean coherence 1.29, under the old skip threshold of 1.0.  So it
wiped the 14 records to generate them again, and that run ended within two minutes.  From 00:10 on, each
resume found nothing incomplete and skipped the cell.  Only a copy made before 2026-05-18 00:08 holds the
lost records.  The flaw is still in today's runner, though narrower: since 2026-10-12 a strength with all
K responses is re-judged rather than wiped.  When a kill falls between a wipe and the regeneration, the
strength vanishes, and the completeness check of a later resume looks only at strengths that are present.
(This is not a regeneration item; it is a note for Roger.)  The pull that brought the shortened file down
did not skip it, which is one more sign that this copy's pulls did not suffer from `--append-verify`.

### Records truncated: 1 cell

[teacher_egalitarian_v1/s3_l25_+1](../../outputs/qwen-3-32b/steering/teacher_egalitarian_v1/s3_l25_+1/):
4 of 10 responses at strength 9.492139 and no `summary.json`.  This is the worker's NFS error of
2026-05-03, row R19, which Roger left.  The 8slot copy has the same records (the re-filter moved 50 of
them), and its `summary.json` holds only the re-filter's `excluded_*` fields.  It is not in the list.

### Other: older than the pod, 27 cells

- **8 cells**: the run of 2026-05-22 18:55-19:23, which raised `max_strength` from 128 to 256, swept
  more strengths in five prefill experiments.
- **17 cells**: the resumes of 2026-05-30 11:44-12:17 re-ran strengths in which a persona score was
  missing.  The responses are the same, the judgements new.
- **2 cells**: the pod rewrote `summary.json` at 2026-05-22 15:50 (`max_strength` 256) and left the
  records alone.  Both cells have an unjudged s_init, which is what made the resume fall through.

In every case this copy's last pull of the experiment came before that work: its sweep log ends earlier
than the 8slot copy's.

### Other: diverged, 31 cells

All 14 cells of [anthropologist_helpful_v1](../../outputs/qwen-3-32b/steering/anthropologist_helpful_v1/)
and of [prodigy_harmless_v1](../../outputs/qwen-3-32b/steering/prodigy_harmless_v1/), and three of
[novelist_honest_v1](../../outputs/qwen-3-32b/steering/novelist_honest_v1/) ([s6_l25_+1](../../outputs/qwen-3-32b/steering/novelist_honest_v1/s6_l25_+1/), [s6_l25_-1](../../outputs/qwen-3-32b/steering/novelist_honest_v1/s6_l25_-1/),
[s6_l49_+1](../../outputs/qwen-3-32b/steering/novelist_honest_v1/s6_l49_+1/)).  This copy has a swap fill done on the Mac (2026-05-16 for the first two, 2026-05-18 for
novelist), each followed by a cutoff.  The 8slot copy has neither and keeps the effect scores at rubric 6.
Copying either way would lose work.  In 28 of these cells the 8slot copy has nothing the pod added later.
Its extra exclusions in 9 of them were computed on the rubric-6 scores, so they do not carry over.  In
three prodigy cells the pod did later work, on 2026-05-22 18:38-18:56 (this copy's log of the experiment
ends on 2026-05-16).  It re-ran strengths left incomplete in [s0_l25_+1](../../outputs/qwen-3-32b/steering/prodigy_harmless_v1/s0_l25_+1/), [s0_l31_+1](../../outputs/qwen-3-32b/steering/prodigy_harmless_v1/s0_l31_+1/) and
[s6_l25_+1](../../outputs/qwen-3-32b/steering/prodigy_harmless_v1/s6_l25_+1/), and in the last it swept two more strengths above the old cap of 16 (18.971056 and 22.556586).  Those
three are in the table and the list, to be merged by hand.

### Not cells

- **15 empty experiment directories**, created by `mkdir -p` in
  [rsync_pod_sweeps.sh](../../scripts/rsync_pod_sweeps.sh) on 2026-05-24 12:31, when every rsync
  attempt failed (the failure of review 10).  They are [chef_helpful_v1](../../outputs/qwen-3-32b/steering/chef_helpful_v1/),
  [chef_helpful_v1_prefill](../../outputs/qwen-3-32b/steering/chef_helpful_v1_prefill/), [prodigy_harmless_v1_prefill](../../outputs/qwen-3-32b/steering/prodigy_harmless_v1_prefill/) and the 12 second-role
  experiments (listed in the table).  The 8slot copy holds all 15
  (214 cells).  Every one of its summaries reproduces under the replay.
- **14 stray cell directories, a `baselines/` and a `sweep.log` at the top level** of
  [outputs/qwen-3-32b/steering/](../../outputs/qwen-3-32b/steering/), most likely from a pull that left
  out the experiment's name.  They are a copy of
  [novelist_honest_v1](../../outputs/qwen-3-32b/steering/novelist_honest_v1/).  The questions are the
  same, [baselines/records.jsonl](../../outputs/qwen-3-32b/steering/baselines/records.jsonl) and [sweep.log](../../outputs/qwen-3-32b/steering/sweep.log) are byte-identical to that experiment's, and every
  cell holds the same records, without the swap fill of three cells.  Nothing here needs them.  Deleting
  them is Roger's call.

### Gaps left on the pod (the same in both copies; not staleness)

- 11 of the 22 cells from 2026-05-02/03 lack effect scores on 31 strengths (one of those strengths also
  lacks coherence and persona scores on some records).  They were judged before the effect rubric fixes
  of mid-May, and neither copy fills them.
- An unjudged s_init in 6 cells: the five of SC1 that live here
  ([anarchist_concise_v1/s6_l49_+1](../../outputs/qwen-3-32b/steering/anarchist_concise_v1/s6_l49_+1/),
  [s6_l49_-1](../../outputs/qwen-3-32b/steering/anarchist_concise_v1/s6_l49_-1/),
  [competitor_improvisational_v1/s7_l49_+1](../../outputs/qwen-3-32b/steering/competitor_improvisational_v1/s7_l49_+1/),
  [publisher_guileless_v1/s7_l49_+1](../../outputs/qwen-3-32b/steering/publisher_guileless_v1/s7_l49_+1/) and
  [s7_l49_-1](../../outputs/qwen-3-32b/steering/publisher_guileless_v1/s7_l49_-1/)), and
  [generalist_trustworthy_v1/s6_l49_-1](../../outputs/qwen-3-32b/steering/generalist_trustworthy_v1/s6_l49_-1/)
  (4 records).  SC1's scan missed that last one: in the 8slot copy the re-filter moved its s_init into
  `_excluded_records.jsonl`.  Roger left SC1 on 2026-10-13.

## Suspect cells

"Files to fetch" are the files to take from another copy, under
[outputs/qwen-3-32b/steering/](../../outputs/qwen-3-32b/steering/) there.  The last column links the same
files in the 8slot copy, where they hold the later version.

| cell | class | what is wrong | files to fetch | later version in the 8slot copy |
|---|---|---|---|---|
| [anarchist_concise_v1/s6_l49_-1](../../outputs/qwen-3-32b/steering/anarchist_concise_v1/s6_l49_-1/) | summary stale against the records | [_excluded_records.jsonl](../../outputs/qwen-3-32b/steering/anarchist_concise_v1/s6_l49_-1/_excluded_records.jsonl) holds strength(s) 0.148935 that [summary.json](../../outputs/qwen-3-32b/steering/anarchist_concise_v1/s6_l49_-1/summary.json) does not list as excluded.  [records.jsonl](../../outputs/qwen-3-32b/steering/anarchist_concise_v1/s6_l49_-1/records.jsonl) and [_excluded_records.jsonl](../../outputs/qwen-3-32b/steering/anarchist_concise_v1/s6_l49_-1/_excluded_records.jsonl) come from the local cutoff run of 2026-05-18 23:06 UTC; [summary.json](../../outputs/qwen-3-32b/steering/anarchist_concise_v1/s6_l49_-1/summary.json) is the pod's rewrite of 2026-05-21 23:35 UTC, which drops the excluded_* fields (the pod still held all 238 records then).  The pod rewrote [summary.json](../../outputs/qwen-3-32b/steering/anarchist_concise_v1/s6_l49_-1/summary.json) again at 2026-05-22 15:50 UTC (max_strength 128 → 256) | [summary.json](../../outputs/qwen-3-32b/steering/anarchist_concise_v1/s6_l49_-1/summary.json) | [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/anarchist_concise_v1/s6_l49_-1/summary.json) |
| [publisher_guileless_v1/s7_l49_+1](../../outputs/qwen-3-32b/steering/publisher_guileless_v1/s7_l49_+1/) | summary stale against the records | [_excluded_records.jsonl](../../outputs/qwen-3-32b/steering/publisher_guileless_v1/s7_l49_+1/_excluded_records.jsonl) holds strength(s) 0.125261, 0.148935, 0.177084, 0.210553, 0.250348, 0.297664 that [summary.json](../../outputs/qwen-3-32b/steering/publisher_guileless_v1/s7_l49_+1/summary.json) does not list as excluded.  [records.jsonl](../../outputs/qwen-3-32b/steering/publisher_guileless_v1/s7_l49_+1/records.jsonl) and [_excluded_records.jsonl](../../outputs/qwen-3-32b/steering/publisher_guileless_v1/s7_l49_+1/_excluded_records.jsonl) come from the local cutoff run of 2026-05-18 23:06 UTC; [summary.json](../../outputs/qwen-3-32b/steering/publisher_guileless_v1/s7_l49_+1/summary.json) is the pod's rewrite of 2026-05-21 23:23 UTC, which drops the excluded_* fields (the pod still held all 238 records then).  The pod rewrote [summary.json](../../outputs/qwen-3-32b/steering/publisher_guileless_v1/s7_l49_+1/summary.json) again at 2026-05-22 15:50 UTC (max_strength 128 → 256) | [summary.json](../../outputs/qwen-3-32b/steering/publisher_guileless_v1/s7_l49_+1/summary.json) | [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/publisher_guileless_v1/s7_l49_+1/summary.json) |
| [publisher_guileless_v1/s7_l49_-1](../../outputs/qwen-3-32b/steering/publisher_guileless_v1/s7_l49_-1/) | summary stale against the records | [_excluded_records.jsonl](../../outputs/qwen-3-32b/steering/publisher_guileless_v1/s7_l49_-1/_excluded_records.jsonl) holds strength(s) 0.177084, 0.210553, 0.250348, 0.297664, 0.353923, 0.420814, 0.500348 that [summary.json](../../outputs/qwen-3-32b/steering/publisher_guileless_v1/s7_l49_-1/summary.json) does not list as excluded.  [records.jsonl](../../outputs/qwen-3-32b/steering/publisher_guileless_v1/s7_l49_-1/records.jsonl) and [_excluded_records.jsonl](../../outputs/qwen-3-32b/steering/publisher_guileless_v1/s7_l49_-1/_excluded_records.jsonl) come from the local cutoff run of 2026-05-18 23:06 UTC; [summary.json](../../outputs/qwen-3-32b/steering/publisher_guileless_v1/s7_l49_-1/summary.json) is the pod's rewrite of 2026-05-21 23:23 UTC, which drops the excluded_* fields (the pod still held all 210 records then).  The pod rewrote [summary.json](../../outputs/qwen-3-32b/steering/publisher_guileless_v1/s7_l49_-1/summary.json) again at 2026-05-22 15:50 UTC (max_strength 128 → 256) | [summary.json](../../outputs/qwen-3-32b/steering/publisher_guileless_v1/s7_l49_-1/summary.json) | [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/publisher_guileless_v1/s7_l49_-1/summary.json) |
| [navigator_progressive_v1/s0_l49_+1](../../outputs/qwen-3-32b/steering/navigator_progressive_v1/s0_l49_+1/) | summary stale against the records (a strength lost on the pod) | strength 3.359487 (14 records) is in neither records file, though [summary.json](../../outputs/qwen-3-32b/steering/navigator_progressive_v1/s0_l49_+1/summary.json) (n_records 238) and the sweep log count it: the pod's resume at 2026-05-18 00:08 UTC wiped it to re-judge it under the new skip threshold, that run ended within two minutes, and the next resume took the cell as finished.  The 8slot copy lacks it too; only a copy made before 2026-05-18 00:08 UTC holds it | [records.jsonl](../../outputs/qwen-3-32b/steering/navigator_progressive_v1/s0_l49_+1/records.jsonl) | no (same as here) |
| [teacher_egalitarian_v1/s3_l25_+1](../../outputs/qwen-3-32b/steering/teacher_egalitarian_v1/s3_l25_+1/) | records truncated | strength 9.492139 has 4 of 10 responses and there is no summary.json: the worker's NFS error of 2026-05-03 (R19, left by Roger) | none | no (same as here) |
| [architect_ecocentric_v3_prefill/s6_l49_-1](../../outputs/qwen-3-32b/steering/architect_ecocentric_v3_prefill/s6_l49_-1/) | other: older than the pod (more strengths swept later) | the pod's run that raised max_strength from 128 to 256 swept 28 more records here (strength 151.451569, 180.075916; judged 2026-05-22 19:08-19:10 UTC); [records.jsonl](../../outputs/qwen-3-32b/steering/architect_ecocentric_v3_prefill/s6_l49_-1/records.jsonl) and [summary.json](../../outputs/qwen-3-32b/steering/architect_ecocentric_v3_prefill/s6_l49_-1/summary.json) here predate it | [records.jsonl](../../outputs/qwen-3-32b/steering/architect_ecocentric_v3_prefill/s6_l49_-1/records.jsonl), [summary.json](../../outputs/qwen-3-32b/steering/architect_ecocentric_v3_prefill/s6_l49_-1/summary.json) | [records.jsonl](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/architect_ecocentric_v3_prefill/s6_l49_-1/records.jsonl), [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/architect_ecocentric_v3_prefill/s6_l49_-1/summary.json) |
| [architect_ecocentric_v3_prefill/s7_l49_-1](../../outputs/qwen-3-32b/steering/architect_ecocentric_v3_prefill/s7_l49_-1/) | other: older than the pod (more strengths swept later) | the pod's run that raised max_strength from 128 to 256 swept 14 more records here (strength 151.451569; judged 2026-05-22 19:08 UTC); [records.jsonl](../../outputs/qwen-3-32b/steering/architect_ecocentric_v3_prefill/s7_l49_-1/records.jsonl) and [summary.json](../../outputs/qwen-3-32b/steering/architect_ecocentric_v3_prefill/s7_l49_-1/summary.json) here predate it | [records.jsonl](../../outputs/qwen-3-32b/steering/architect_ecocentric_v3_prefill/s7_l49_-1/records.jsonl), [summary.json](../../outputs/qwen-3-32b/steering/architect_ecocentric_v3_prefill/s7_l49_-1/summary.json) | [records.jsonl](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/architect_ecocentric_v3_prefill/s7_l49_-1/records.jsonl), [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/architect_ecocentric_v3_prefill/s7_l49_-1/summary.json) |
| [competitor_improvisational_v1_prefill/s0_l49_-1](../../outputs/qwen-3-32b/steering/competitor_improvisational_v1_prefill/s0_l49_-1/) | other: older than the pod (more strengths swept later) | the pod's run that raised max_strength from 128 to 256 swept 14 more records here (strength 151.451569; judged 2026-05-22 19:10 UTC); [records.jsonl](../../outputs/qwen-3-32b/steering/competitor_improvisational_v1_prefill/s0_l49_-1/records.jsonl) and [summary.json](../../outputs/qwen-3-32b/steering/competitor_improvisational_v1_prefill/s0_l49_-1/summary.json) here predate it | [records.jsonl](../../outputs/qwen-3-32b/steering/competitor_improvisational_v1_prefill/s0_l49_-1/records.jsonl), [summary.json](../../outputs/qwen-3-32b/steering/competitor_improvisational_v1_prefill/s0_l49_-1/summary.json) | [records.jsonl](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/competitor_improvisational_v1_prefill/s0_l49_-1/records.jsonl), [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/competitor_improvisational_v1_prefill/s0_l49_-1/summary.json) |
| [novelist_honest_v1_prefill/s0_l49_+1](../../outputs/qwen-3-32b/steering/novelist_honest_v1_prefill/s0_l49_+1/) | other: older than the pod (more strengths swept later) | the pod's run that raised max_strength from 128 to 256 swept 14 more records here (strength 151.451569; judged 2026-05-22 19:05 UTC); [records.jsonl](../../outputs/qwen-3-32b/steering/novelist_honest_v1_prefill/s0_l49_+1/records.jsonl) and [summary.json](../../outputs/qwen-3-32b/steering/novelist_honest_v1_prefill/s0_l49_+1/summary.json) here predate it | [records.jsonl](../../outputs/qwen-3-32b/steering/novelist_honest_v1_prefill/s0_l49_+1/records.jsonl), [summary.json](../../outputs/qwen-3-32b/steering/novelist_honest_v1_prefill/s0_l49_+1/summary.json) | [records.jsonl](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/novelist_honest_v1_prefill/s0_l49_+1/records.jsonl), [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/novelist_honest_v1_prefill/s0_l49_+1/summary.json) |
| [rebel_systems_thinker_v1_prefill/s0_l49_-1](../../outputs/qwen-3-32b/steering/rebel_systems_thinker_v1_prefill/s0_l49_-1/) | other: older than the pod (more strengths swept later) | the pod's run that raised max_strength from 128 to 256 swept 56 more records here (strength 151.451569, 180.075916, 214.110264, 254.577104; judged 2026-05-22 19:15-19:23 UTC); [records.jsonl](../../outputs/qwen-3-32b/steering/rebel_systems_thinker_v1_prefill/s0_l49_-1/records.jsonl) and [summary.json](../../outputs/qwen-3-32b/steering/rebel_systems_thinker_v1_prefill/s0_l49_-1/summary.json) here predate it | [records.jsonl](../../outputs/qwen-3-32b/steering/rebel_systems_thinker_v1_prefill/s0_l49_-1/records.jsonl), [summary.json](../../outputs/qwen-3-32b/steering/rebel_systems_thinker_v1_prefill/s0_l49_-1/summary.json) | [records.jsonl](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/rebel_systems_thinker_v1_prefill/s0_l49_-1/records.jsonl), [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/rebel_systems_thinker_v1_prefill/s0_l49_-1/summary.json) |
| [rebel_systems_thinker_v1_prefill/s6_l49_+1](../../outputs/qwen-3-32b/steering/rebel_systems_thinker_v1_prefill/s6_l49_+1/) | other: older than the pod (more strengths swept later) | the pod's run that raised max_strength from 128 to 256 swept 14 more records here (strength 151.451569; judged 2026-05-22 19:15 UTC); [records.jsonl](../../outputs/qwen-3-32b/steering/rebel_systems_thinker_v1_prefill/s6_l49_+1/records.jsonl) and [summary.json](../../outputs/qwen-3-32b/steering/rebel_systems_thinker_v1_prefill/s6_l49_+1/summary.json) here predate it | [records.jsonl](../../outputs/qwen-3-32b/steering/rebel_systems_thinker_v1_prefill/s6_l49_+1/records.jsonl), [summary.json](../../outputs/qwen-3-32b/steering/rebel_systems_thinker_v1_prefill/s6_l49_+1/summary.json) | [records.jsonl](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/rebel_systems_thinker_v1_prefill/s6_l49_+1/records.jsonl), [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/rebel_systems_thinker_v1_prefill/s6_l49_+1/summary.json) |
| [virtuoso_relativist_v1_prefill/s0_l49_-1](../../outputs/qwen-3-32b/steering/virtuoso_relativist_v1_prefill/s0_l49_-1/) | other: older than the pod (more strengths swept later) | the pod's run that raised max_strength from 128 to 256 swept 14 more records here (strength 151.451569; judged 2026-05-22 19:13 UTC); [records.jsonl](../../outputs/qwen-3-32b/steering/virtuoso_relativist_v1_prefill/s0_l49_-1/records.jsonl) and [summary.json](../../outputs/qwen-3-32b/steering/virtuoso_relativist_v1_prefill/s0_l49_-1/summary.json) here predate it | [records.jsonl](../../outputs/qwen-3-32b/steering/virtuoso_relativist_v1_prefill/s0_l49_-1/records.jsonl), [summary.json](../../outputs/qwen-3-32b/steering/virtuoso_relativist_v1_prefill/s0_l49_-1/summary.json) | [records.jsonl](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/virtuoso_relativist_v1_prefill/s0_l49_-1/records.jsonl), [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/virtuoso_relativist_v1_prefill/s0_l49_-1/summary.json) |
| [virtuoso_relativist_v1_prefill/s6_l49_-1](../../outputs/qwen-3-32b/steering/virtuoso_relativist_v1_prefill/s6_l49_-1/) | other: older than the pod (more strengths swept later) | the pod's run that raised max_strength from 128 to 256 swept 14 more records here (strength 151.451569; judged 2026-05-22 19:12 UTC); [records.jsonl](../../outputs/qwen-3-32b/steering/virtuoso_relativist_v1_prefill/s6_l49_-1/records.jsonl) and [summary.json](../../outputs/qwen-3-32b/steering/virtuoso_relativist_v1_prefill/s6_l49_-1/summary.json) here predate it | [records.jsonl](../../outputs/qwen-3-32b/steering/virtuoso_relativist_v1_prefill/s6_l49_-1/records.jsonl), [summary.json](../../outputs/qwen-3-32b/steering/virtuoso_relativist_v1_prefill/s6_l49_-1/summary.json) | [records.jsonl](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/virtuoso_relativist_v1_prefill/s6_l49_-1/records.jsonl), [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/virtuoso_relativist_v1_prefill/s6_l49_-1/summary.json) |
| [anarchist_introverted_v1/s0_l31_+1](../../outputs/qwen-3-32b/steering/anarchist_introverted_v1/s0_l31_+1/) | other: older than the pod (strengths re-run later) | the pod's resume of 2026-05-30 12:09 UTC re-ran strength(s) 0.420814, in which 1 record(s) here have no persona score (same responses, new judgements); [records.jsonl](../../outputs/qwen-3-32b/steering/anarchist_introverted_v1/s0_l31_+1/records.jsonl) and [summary.json](../../outputs/qwen-3-32b/steering/anarchist_introverted_v1/s0_l31_+1/summary.json) here predate it | [records.jsonl](../../outputs/qwen-3-32b/steering/anarchist_introverted_v1/s0_l31_+1/records.jsonl), [summary.json](../../outputs/qwen-3-32b/steering/anarchist_introverted_v1/s0_l31_+1/summary.json) | [records.jsonl](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/anarchist_introverted_v1/s0_l31_+1/records.jsonl), [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/anarchist_introverted_v1/s0_l31_+1/summary.json) |
| [bohemian_dominant_v1/s0_l49_+1](../../outputs/qwen-3-32b/steering/bohemian_dominant_v1/s0_l49_+1/) | other: older than the pod (strengths re-run later) | the pod's resume of 2026-05-30 11:50 UTC re-ran strength(s) 0.125261, in which 1 record(s) here have no persona score (same responses, new judgements); [records.jsonl](../../outputs/qwen-3-32b/steering/bohemian_dominant_v1/s0_l49_+1/records.jsonl) and [summary.json](../../outputs/qwen-3-32b/steering/bohemian_dominant_v1/s0_l49_+1/summary.json) here predate it | [records.jsonl](../../outputs/qwen-3-32b/steering/bohemian_dominant_v1/s0_l49_+1/records.jsonl), [summary.json](../../outputs/qwen-3-32b/steering/bohemian_dominant_v1/s0_l49_+1/summary.json) | [records.jsonl](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/bohemian_dominant_v1/s0_l49_+1/records.jsonl), [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/bohemian_dominant_v1/s0_l49_+1/summary.json) |
| [bohemian_dominant_v1/s0_l49_-1](../../outputs/qwen-3-32b/steering/bohemian_dominant_v1/s0_l49_-1/) | other: older than the pod (strengths re-run later) | the pod's resume of 2026-05-30 11:57 UTC re-ran strength(s) 0.210553, in which 1 record(s) here have no persona score (same responses, new judgements); [records.jsonl](../../outputs/qwen-3-32b/steering/bohemian_dominant_v1/s0_l49_-1/records.jsonl) and [summary.json](../../outputs/qwen-3-32b/steering/bohemian_dominant_v1/s0_l49_-1/summary.json) here predate it | [records.jsonl](../../outputs/qwen-3-32b/steering/bohemian_dominant_v1/s0_l49_-1/records.jsonl), [summary.json](../../outputs/qwen-3-32b/steering/bohemian_dominant_v1/s0_l49_-1/summary.json) | [records.jsonl](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/bohemian_dominant_v1/s0_l49_-1/records.jsonl), [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/bohemian_dominant_v1/s0_l49_-1/summary.json) |
| [bohemian_ethereal_v1/s6_l49_-1](../../outputs/qwen-3-32b/steering/bohemian_ethereal_v1/s6_l49_-1/) | other: older than the pod (strengths re-run later) | the pod's resume of 2026-05-30 12:07 UTC re-ran strength(s) 1.998607, in which 1 record(s) here have no persona score (same responses, new judgements); [records.jsonl](../../outputs/qwen-3-32b/steering/bohemian_ethereal_v1/s6_l49_-1/records.jsonl) and [summary.json](../../outputs/qwen-3-32b/steering/bohemian_ethereal_v1/s6_l49_-1/summary.json) here predate it | [records.jsonl](../../outputs/qwen-3-32b/steering/bohemian_ethereal_v1/s6_l49_-1/records.jsonl), [summary.json](../../outputs/qwen-3-32b/steering/bohemian_ethereal_v1/s6_l49_-1/summary.json) | [records.jsonl](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/bohemian_ethereal_v1/s6_l49_-1/records.jsonl), [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/bohemian_ethereal_v1/s6_l49_-1/summary.json) |
| [caregiver_religious_v1/s6_l25_-1](../../outputs/qwen-3-32b/steering/caregiver_religious_v1/s6_l25_-1/) | other: older than the pod (strengths re-run later) | the pod's resume of 2026-05-30 12:17 UTC re-ran strength(s) 5.647009, in which 1 record(s) here have no persona score (same responses, new judgements); [records.jsonl](../../outputs/qwen-3-32b/steering/caregiver_religious_v1/s6_l25_-1/records.jsonl) and [summary.json](../../outputs/qwen-3-32b/steering/caregiver_religious_v1/s6_l25_-1/summary.json) here predate it | [records.jsonl](../../outputs/qwen-3-32b/steering/caregiver_religious_v1/s6_l25_-1/records.jsonl), [summary.json](../../outputs/qwen-3-32b/steering/caregiver_religious_v1/s6_l25_-1/summary.json) | [records.jsonl](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/caregiver_religious_v1/s6_l25_-1/records.jsonl), [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/caregiver_religious_v1/s6_l25_-1/summary.json) |
| [competitor_proactive_v1/s7_l25_-1](../../outputs/qwen-3-32b/steering/competitor_proactive_v1/s7_l25_-1/) | other: older than the pod (strengths re-run later) | the pod's resume of 2026-05-30 12:15 UTC re-ran strength(s) 2.825473, in which 1 record(s) here have no persona score (same responses, new judgements); [records.jsonl](../../outputs/qwen-3-32b/steering/competitor_proactive_v1/s7_l25_-1/records.jsonl) and [summary.json](../../outputs/qwen-3-32b/steering/competitor_proactive_v1/s7_l25_-1/summary.json) here predate it | [records.jsonl](../../outputs/qwen-3-32b/steering/competitor_proactive_v1/s7_l25_-1/records.jsonl), [summary.json](../../outputs/qwen-3-32b/steering/competitor_proactive_v1/s7_l25_-1/summary.json) | [records.jsonl](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/competitor_proactive_v1/s7_l25_-1/records.jsonl), [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/competitor_proactive_v1/s7_l25_-1/summary.json) |
| [saboteur_quantitative_v1/s7_l25_+1](../../outputs/qwen-3-32b/steering/saboteur_quantitative_v1/s7_l25_+1/) | other: older than the pod (strengths re-run later) | the pod's resume of 2026-05-30 12:15 UTC re-ran strength(s) 2.825473, in which 1 record(s) here have no persona score (same responses, new judgements); [records.jsonl](../../outputs/qwen-3-32b/steering/saboteur_quantitative_v1/s7_l25_+1/records.jsonl) and [summary.json](../../outputs/qwen-3-32b/steering/saboteur_quantitative_v1/s7_l25_+1/summary.json) here predate it | [records.jsonl](../../outputs/qwen-3-32b/steering/saboteur_quantitative_v1/s7_l25_+1/records.jsonl), [summary.json](../../outputs/qwen-3-32b/steering/saboteur_quantitative_v1/s7_l25_+1/summary.json) | [records.jsonl](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/saboteur_quantitative_v1/s7_l25_+1/records.jsonl), [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/saboteur_quantitative_v1/s7_l25_+1/summary.json) |
| [specialist_cooperative_v1/s0_l49_-1](../../outputs/qwen-3-32b/steering/specialist_cooperative_v1/s0_l49_-1/) | other: older than the pod (strengths re-run later) | the pod's resume of 2026-05-30 11:47 UTC re-ran strength(s) 0.500348, in which 5 record(s) here have no persona score (same responses, new judgements); [records.jsonl](../../outputs/qwen-3-32b/steering/specialist_cooperative_v1/s0_l49_-1/records.jsonl) and [summary.json](../../outputs/qwen-3-32b/steering/specialist_cooperative_v1/s0_l49_-1/summary.json) here predate it | [records.jsonl](../../outputs/qwen-3-32b/steering/specialist_cooperative_v1/s0_l49_-1/records.jsonl), [summary.json](../../outputs/qwen-3-32b/steering/specialist_cooperative_v1/s0_l49_-1/summary.json) | [records.jsonl](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/specialist_cooperative_v1/s0_l49_-1/records.jsonl), [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/specialist_cooperative_v1/s0_l49_-1/summary.json) |
| [traditionalist_detached_v1/s7_l25_+1](../../outputs/qwen-3-32b/steering/traditionalist_detached_v1/s7_l25_+1/) | other: older than the pod (strengths re-run later) | the pod's resume of 2026-05-30 11:46 UTC re-ran strength(s) 4.749377, in which 1 record(s) here have no persona score (same responses, new judgements); [records.jsonl](../../outputs/qwen-3-32b/steering/traditionalist_detached_v1/s7_l25_+1/records.jsonl) and [summary.json](../../outputs/qwen-3-32b/steering/traditionalist_detached_v1/s7_l25_+1/summary.json) here predate it | [records.jsonl](../../outputs/qwen-3-32b/steering/traditionalist_detached_v1/s7_l25_+1/records.jsonl), [summary.json](../../outputs/qwen-3-32b/steering/traditionalist_detached_v1/s7_l25_+1/summary.json) | [records.jsonl](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/traditionalist_detached_v1/s7_l25_+1/records.jsonl), [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/traditionalist_detached_v1/s7_l25_+1/summary.json) |
| [vampire_curious_v1/s7_l49_-1](../../outputs/qwen-3-32b/steering/vampire_curious_v1/s7_l49_-1/) | other: older than the pod (strengths re-run later) | the pod's resume of 2026-05-30 11:48 UTC re-ran strength(s) 0.420814, in which 1 record(s) here have no persona score (same responses, new judgements); [records.jsonl](../../outputs/qwen-3-32b/steering/vampire_curious_v1/s7_l49_-1/records.jsonl) and [summary.json](../../outputs/qwen-3-32b/steering/vampire_curious_v1/s7_l49_-1/summary.json) here predate it | [records.jsonl](../../outputs/qwen-3-32b/steering/vampire_curious_v1/s7_l49_-1/records.jsonl), [summary.json](../../outputs/qwen-3-32b/steering/vampire_curious_v1/s7_l49_-1/summary.json) | [records.jsonl](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/vampire_curious_v1/s7_l49_-1/records.jsonl), [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/vampire_curious_v1/s7_l49_-1/summary.json) |
| [vampire_earnest_v1/s6_l25_+1](../../outputs/qwen-3-32b/steering/vampire_earnest_v1/s6_l25_+1/) | other: older than the pod (strengths re-run later) | the pod's resume of 2026-05-30 11:51 UTC re-ran strength(s) 2.376344, in which 1 record(s) here have no persona score (same responses, new judgements); [records.jsonl](../../outputs/qwen-3-32b/steering/vampire_earnest_v1/s6_l25_+1/records.jsonl) and [summary.json](../../outputs/qwen-3-32b/steering/vampire_earnest_v1/s6_l25_+1/summary.json) here predate it | [records.jsonl](../../outputs/qwen-3-32b/steering/vampire_earnest_v1/s6_l25_+1/records.jsonl), [summary.json](../../outputs/qwen-3-32b/steering/vampire_earnest_v1/s6_l25_+1/summary.json) | [records.jsonl](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/vampire_earnest_v1/s6_l25_+1/records.jsonl), [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/vampire_earnest_v1/s6_l25_+1/summary.json) |
| [vampire_earnest_v1/s6_l25_-1](../../outputs/qwen-3-32b/steering/vampire_earnest_v1/s6_l25_-1/) | other: older than the pod (strengths re-run later) | the pod's resume of 2026-05-30 11:59-12:02 UTC re-ran strength(s) 0.420814, 7.983296, in which 2 record(s) here have no persona score (same responses, new judgements); [records.jsonl](../../outputs/qwen-3-32b/steering/vampire_earnest_v1/s6_l25_-1/records.jsonl) and [summary.json](../../outputs/qwen-3-32b/steering/vampire_earnest_v1/s6_l25_-1/summary.json) here predate it | [records.jsonl](../../outputs/qwen-3-32b/steering/vampire_earnest_v1/s6_l25_-1/records.jsonl), [summary.json](../../outputs/qwen-3-32b/steering/vampire_earnest_v1/s6_l25_-1/summary.json) | [records.jsonl](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/vampire_earnest_v1/s6_l25_-1/records.jsonl), [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/vampire_earnest_v1/s6_l25_-1/summary.json) |
| [vampire_earnest_v1/s6_l49_+1](../../outputs/qwen-3-32b/steering/vampire_earnest_v1/s6_l49_+1/) | other: older than the pod (strengths re-run later) | the pod's resume of 2026-05-30 11:53-12:05 UTC re-ran strength(s) 0.594914, 0.707353, 0.841043, 1.0, 1.189, 1.680914, 1.998607, in which 7 record(s) here have no persona score (same responses, new judgements); [records.jsonl](../../outputs/qwen-3-32b/steering/vampire_earnest_v1/s6_l49_+1/records.jsonl) and [summary.json](../../outputs/qwen-3-32b/steering/vampire_earnest_v1/s6_l49_+1/summary.json) here predate it | [records.jsonl](../../outputs/qwen-3-32b/steering/vampire_earnest_v1/s6_l49_+1/records.jsonl), [summary.json](../../outputs/qwen-3-32b/steering/vampire_earnest_v1/s6_l49_+1/summary.json) | [records.jsonl](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/vampire_earnest_v1/s6_l49_+1/records.jsonl), [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/vampire_earnest_v1/s6_l49_+1/summary.json) |
| [vampire_earnest_v1/s6_l49_-1](../../outputs/qwen-3-32b/steering/vampire_earnest_v1/s6_l49_-1/) | other: older than the pod (strengths re-run later) | the pod's resume of 2026-05-30 11:57-12:01 UTC re-ran strength(s) 0.420814, 0.594914, 0.841043, in which 6 record(s) here have no persona score (same responses, new judgements); [records.jsonl](../../outputs/qwen-3-32b/steering/vampire_earnest_v1/s6_l49_-1/records.jsonl) and [summary.json](../../outputs/qwen-3-32b/steering/vampire_earnest_v1/s6_l49_-1/summary.json) here predate it | [records.jsonl](../../outputs/qwen-3-32b/steering/vampire_earnest_v1/s6_l49_-1/records.jsonl), [summary.json](../../outputs/qwen-3-32b/steering/vampire_earnest_v1/s6_l49_-1/summary.json) | [records.jsonl](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/vampire_earnest_v1/s6_l49_-1/records.jsonl), [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/vampire_earnest_v1/s6_l49_-1/summary.json) |
| [vampire_earnest_v1/s7_l25_+1](../../outputs/qwen-3-32b/steering/vampire_earnest_v1/s7_l25_+1/) | other: older than the pod (strengths re-run later) | the pod's resume of 2026-05-30 12:00-12:06 UTC re-ran strength(s) 0.707353, 0.841043, 1.998607, 2.376344, 2.825473, in which 5 record(s) here have no persona score (same responses, new judgements); [records.jsonl](../../outputs/qwen-3-32b/steering/vampire_earnest_v1/s7_l25_+1/records.jsonl) and [summary.json](../../outputs/qwen-3-32b/steering/vampire_earnest_v1/s7_l25_+1/summary.json) here predate it | [records.jsonl](../../outputs/qwen-3-32b/steering/vampire_earnest_v1/s7_l25_+1/records.jsonl), [summary.json](../../outputs/qwen-3-32b/steering/vampire_earnest_v1/s7_l25_+1/summary.json) | [records.jsonl](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/vampire_earnest_v1/s7_l25_+1/records.jsonl), [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/vampire_earnest_v1/s7_l25_+1/summary.json) |
| [vampire_earnest_v1/s7_l25_-1](../../outputs/qwen-3-32b/steering/vampire_earnest_v1/s7_l25_-1/) | other: older than the pod (strengths re-run later) | the pod's resume of 2026-05-30 12:03-12:10 UTC re-ran strength(s) 0.707353, 1.0, 1.189, 3.359487, in which 4 record(s) here have no persona score (same responses, new judgements); [records.jsonl](../../outputs/qwen-3-32b/steering/vampire_earnest_v1/s7_l25_-1/records.jsonl) and [summary.json](../../outputs/qwen-3-32b/steering/vampire_earnest_v1/s7_l25_-1/summary.json) here predate it | [records.jsonl](../../outputs/qwen-3-32b/steering/vampire_earnest_v1/s7_l25_-1/records.jsonl), [summary.json](../../outputs/qwen-3-32b/steering/vampire_earnest_v1/s7_l25_-1/summary.json) | [records.jsonl](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/vampire_earnest_v1/s7_l25_-1/records.jsonl), [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/vampire_earnest_v1/s7_l25_-1/summary.json) |
| [vampire_passionate_v1/s6_l49_+1](../../outputs/qwen-3-32b/steering/vampire_passionate_v1/s6_l49_+1/) | other: older than the pod (strengths re-run later) | the pod's resume of 2026-05-30 11:48 UTC re-ran strength(s) 1.189, in which 1 record(s) here have no persona score (same responses, new judgements); [records.jsonl](../../outputs/qwen-3-32b/steering/vampire_passionate_v1/s6_l49_+1/records.jsonl) and [summary.json](../../outputs/qwen-3-32b/steering/vampire_passionate_v1/s6_l49_+1/summary.json) here predate it | [records.jsonl](../../outputs/qwen-3-32b/steering/vampire_passionate_v1/s6_l49_+1/records.jsonl), [summary.json](../../outputs/qwen-3-32b/steering/vampire_passionate_v1/s6_l49_+1/summary.json) | [records.jsonl](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/vampire_passionate_v1/s6_l49_+1/records.jsonl), [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/vampire_passionate_v1/s6_l49_+1/summary.json) |
| [anarchist_concise_v1/s6_l49_+1](../../outputs/qwen-3-32b/steering/anarchist_concise_v1/s6_l49_+1/) | other: older than the pod (summary rewritten later) | the pod rewrote [summary.json](../../outputs/qwen-3-32b/steering/anarchist_concise_v1/s6_l49_+1/summary.json) at 2026-05-22 15:50 UTC (max_strength 128 → 256, a resume that found s_init unjudged); records unchanged | [summary.json](../../outputs/qwen-3-32b/steering/anarchist_concise_v1/s6_l49_+1/summary.json) | [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/anarchist_concise_v1/s6_l49_+1/summary.json) |
| [competitor_improvisational_v1/s7_l49_+1](../../outputs/qwen-3-32b/steering/competitor_improvisational_v1/s7_l49_+1/) | other: older than the pod (summary rewritten later) | the pod rewrote [summary.json](../../outputs/qwen-3-32b/steering/competitor_improvisational_v1/s7_l49_+1/summary.json) at 2026-05-22 15:50 UTC (max_strength 128 → 256, a resume that found s_init unjudged); records unchanged | [summary.json](../../outputs/qwen-3-32b/steering/competitor_improvisational_v1/s7_l49_+1/summary.json) | [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/competitor_improvisational_v1/s7_l49_+1/summary.json) |
| [prodigy_harmless_v1/s0_l25_+1](../../outputs/qwen-3-32b/steering/prodigy_harmless_v1/s0_l25_+1/) | other: diverged (local work here, later pod work there) | this copy has the swap fill (effect rubric 7) and a cutoff, both done on the Mac on 2026-05-16, which the 8slot copy lacks; the pod later (2026-05-22 18:51 UTC) re-ran strength(s) 7.983296 (left incomplete).  Merge by hand, do not overwrite | [records.jsonl](../../outputs/qwen-3-32b/steering/prodigy_harmless_v1/s0_l25_+1/records.jsonl), [summary.json](../../outputs/qwen-3-32b/steering/prodigy_harmless_v1/s0_l25_+1/summary.json) | [records.jsonl](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/prodigy_harmless_v1/s0_l25_+1/records.jsonl), [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/prodigy_harmless_v1/s0_l25_+1/summary.json) |
| [prodigy_harmless_v1/s0_l31_+1](../../outputs/qwen-3-32b/steering/prodigy_harmless_v1/s0_l31_+1/) | other: diverged (local work here, later pod work there) | this copy has the swap fill (effect rubric 7) and a cutoff, both done on the Mac on 2026-05-16, which the 8slot copy lacks; the pod later (2026-05-22 18:54-18:56 UTC) re-ran strength(s) 4.749377, 5.647009 (left incomplete).  Merge by hand, do not overwrite | [records.jsonl](../../outputs/qwen-3-32b/steering/prodigy_harmless_v1/s0_l31_+1/records.jsonl), [summary.json](../../outputs/qwen-3-32b/steering/prodigy_harmless_v1/s0_l31_+1/summary.json) | [records.jsonl](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/prodigy_harmless_v1/s0_l31_+1/records.jsonl), [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/prodigy_harmless_v1/s0_l31_+1/summary.json) |
| [prodigy_harmless_v1/s6_l25_+1](../../outputs/qwen-3-32b/steering/prodigy_harmless_v1/s6_l25_+1/) | other: diverged (local work here, later pod work there) | this copy has the swap fill (effect rubric 7) and a cutoff, both done on the Mac on 2026-05-16, which the 8slot copy lacks; the pod later (2026-05-22 18:41-18:48 UTC) re-ran strength(s) 0.420814, 15.955472 (left incomplete) and swept 18.971056, 22.556586 above the old cap of 16.  Merge by hand, do not overwrite | [records.jsonl](../../outputs/qwen-3-32b/steering/prodigy_harmless_v1/s6_l25_+1/records.jsonl), [summary.json](../../outputs/qwen-3-32b/steering/prodigy_harmless_v1/s6_l25_+1/summary.json) | [records.jsonl](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/prodigy_harmless_v1/s6_l25_+1/records.jsonl), [summary.json](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/prodigy_harmless_v1/s6_l25_+1/summary.json) |
| the 15 empty experiments: [artist_improvisational_v1](../../outputs/qwen-3-32b/steering/artist_improvisational_v1/), [chef_helpful_v1](../../outputs/qwen-3-32b/steering/chef_helpful_v1/), [chef_helpful_v1_prefill](../../outputs/qwen-3-32b/steering/chef_helpful_v1_prefill/), [chemist_ecocentric_v1](../../outputs/qwen-3-32b/steering/chemist_ecocentric_v1/), [curator_progressive_v1](../../outputs/qwen-3-32b/steering/curator_progressive_v1/), [fixer_egalitarian_v1](../../outputs/qwen-3-32b/steering/fixer_egalitarian_v1/), [lawyer_guileless_v1](../../outputs/qwen-3-32b/steering/lawyer_guileless_v1/), [marketer_honest_v1](../../outputs/qwen-3-32b/steering/marketer_honest_v1/), [prodigy_harmless_v1_prefill](../../outputs/qwen-3-32b/steering/prodigy_harmless_v1_prefill/), [publisher_relativist_v1](../../outputs/qwen-3-32b/steering/publisher_relativist_v1/), [saboteur_harmless_v1](../../outputs/qwen-3-32b/steering/saboteur_harmless_v1/), [soldier_concise_v1](../../outputs/qwen-3-32b/steering/soldier_concise_v1/), [spy_truthful_v1](../../outputs/qwen-3-32b/steering/spy_truthful_v1/), [vampire_helpful_v1](../../outputs/qwen-3-32b/steering/vampire_helpful_v1/), [vampire_systems_thinker_v1](../../outputs/qwen-3-32b/steering/vampire_systems_thinker_v1/) | missing | the pull of 2026-05-24 failed; the directory is empty | the whole directory | [artist_improvisational_v1](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/artist_improvisational_v1/), [chef_helpful_v1](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/chef_helpful_v1/), [chef_helpful_v1_prefill](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/chef_helpful_v1_prefill/), [chemist_ecocentric_v1](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/chemist_ecocentric_v1/), [curator_progressive_v1](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/curator_progressive_v1/), [fixer_egalitarian_v1](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/fixer_egalitarian_v1/), [lawyer_guileless_v1](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/lawyer_guileless_v1/), [marketer_honest_v1](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/marketer_honest_v1/), [prodigy_harmless_v1_prefill](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/prodigy_harmless_v1_prefill/), [publisher_relativist_v1](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/publisher_relativist_v1/), [saboteur_harmless_v1](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/saboteur_harmless_v1/), [soldier_concise_v1](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/soldier_concise_v1/), [spy_truthful_v1](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/spy_truthful_v1/), [vampire_helpful_v1](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/vampire_helpful_v1/), [vampire_systems_thinker_v1](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/steering/vampire_systems_thinker_v1/) |

## Using the list

[r18_suspect_files.txt](./r18_suspect_files.txt) has one path per line, relative to
`outputs/qwen-3-32b/steering/`.  It holds 62 files and 15 directories; a directory line ends in `/` and
means the whole directory.  To copy them from another copy into a staging folder:

```
rsync -a -r --files-from=reports/code_review_2026-10-12/r18_suspect_files.txt \
    <other copy>/outputs/qwen-3-32b/steering/  <staging folder>/
```

With `--files-from`, rsync recurses into the listed directories only when `-r` is given explicitly.  Two
kinds of line need care.  First, the three prodigy cells: a merge, not a copy, since this copy holds the
swap fill.  Second, [navigator_progressive_v1/s0_l49_+1/records.jsonl](../../outputs/qwen-3-32b/steering/navigator_progressive_v1/s0_l49_+1/records.jsonl):
worth fetching only from a copy made before 2026-05-18 00:08 UTC.  Since the 8slot copy holds the later
version of everything else, the shorter route is to treat it as the steering record, as 8f647c13 already
does, and to keep `outputs/qwen-3-32b/steering/` only for the Mac-side swap fills of the 31 diverged cells.

The check's scripts lived in the session's scratch directory and were not kept (no code changes were
wanted); the method above is enough to repeat it.
