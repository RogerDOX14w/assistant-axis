# Before the October extraction: the work that needs a pod

Started 2026-10-12 at Roger's request: the review's fixes go ahead now wherever no pod is needed, and
"for anything that does, make sure it's added to a TODO list so it will get done before we do the main
activations run".  This is that list.  Everything here waits for a RunPod session; nothing here may be
skipped before the main extraction starts.  Close an item by writing the date, the pod run and the result
under it.

Anything over 13 GPU-hours or $20 still needs Roger's go with quoted parameters (CLAUDE.md, "Expensive
operations").  The code these items exercise is built off-pod first, by the peer session's pipeline batch
(P1-P6, P8) and this session's review batch; [escalations.md](../code_review_2026-10-12/escalations.md)
"Decisions so far" has every decision, and
[regeneration_list.md](../code_review_2026-10-12/regeneration_list.md) the data each fix makes stale.

## Must run before the extraction

**Order (Roger, 2026-10-13): the cap pilot (item 2) is the first job once the pods are up.**  Its step-1 to
step-4 runs on 64 entities also serve as the Qwen3 smoke run (item 1): they put P2's side-car, P6's response
fields, P8's exit status and P3's float32 vectors through the real model.  The extraction then starts with the
cap the pilot's readout picks.  The pilot's GPU-hours and judge spend still need Roger's go with the quoted
parameters at launch.

1. **The Qwen3 smoke run** (about 1 GPU-hour on 4 GPUs; multi-model plan question 9,
   [coding_plan_multi_model_extraction.md](./coding_plan_multi_model_extraction.md)).  The first
   real-model run of the fixed pipeline: P2's `generation_config.json` side-car and fresh-output-dir rule,
   P6's new response fields (`finish_reason`, `thinking_stripped`, `thinking_suspected`, `question_id`),
   P8.1's exit status, P3's float32 vectors and axis, the derived header tokens if P7 is built.  Roger's
   answer: run it as the first entities of the October run rather than a separate launch.
   Also P8.6's model mirror (pipeline fix batch, 2026-10-12): check that `rsync` is installed on the pod
   (`--tmpfs-method auto` falls back to a staged `cp` without it) and that the first mirror leaves
   `/dev/shm/hf-cache/hub/models--Qwen--Qwen3-32B/.tmpfs_mirror_complete`.  A mirror left by the old
   shell `cp -r` has no marker: rsync copies it again (once), cp refuses it until it is deleted.  And
   P8.3: steps 2 and 4 now return before importing torch when there is nothing to do, and step 3 imports
   no torch at all, which changes what item 3 below measures.
2. **The response-length cap pilot** ([plan_max_tokens_pilot.md](./plan_max_tokens_pilot.md); about 16
   GPU-hours and $25 batch, over the GPU line: **Roger's go with quoted parameters**).  64 entities at caps
   256 / 512 / 768 / 1024; decides the cap the extraction uses.  Needs P6's `finish_reason` and P8.1 first.
   The entity list, [cap_pilot_entities.json](./cap_pilot_entities.json) (built 2026-10-12, seed
   20261012), and [cap_pilot_compare.py](../../tools/cap_pilot_compare.py) (built) come from the peer
   session's P6 (8066b6ad); the plan's § 4 commands were corrected to the list's format, and three
   readings of the decision rule (centred cosines, layer 25, the 2-point test) wait for Roger's word
   in the plan before the pilot runs.
3. **The venv on local disk** (walk-through P8.3 (b)).  The recorded slow step was importing torch over
   NFS.  On the first pod, put the environment on local disk or `/dev/shm`
   (`UV_PROJECT_ENVIRONMENT`), time the import against the `/workspace` venv, and write the pod setup
   step into [pipeline/README.md](../../pipeline/README.md).
4. **fsync timing on the pod's NFS** (walk-through E4).  The opt-in fsync for small JSON writes in
   [atomic_io.py](../../assistant_axis/atomic_io.py) is built off-pod; time it on `/workspace` and decide
   whether the drivers turn it on.
5. **The four-pod procedure** (walk-through P1: roles, traits, `r_combinations`, `t_combinations`, one
   per pod, each with a local output dir).  First real use of the procedure in
   [pipeline/README.md](../../pipeline/README.md), of the batch sizing for several pods sharing one OpenAI
   organisation's queue, and of [merge_pod_outputs.py](../../tools/merge_pod_outputs.py) (built
   2026-10-12, P1; the procedure is pipeline/README.md "Several pods: one type each, then a merge").
   Check the queue limit against the sizing before step 3 starts on the second pod: read `Q` on the
   organisation's limits page and pass `--judge-batch-requests N` to each pod's driver (the formula is
   in the README's step 3).  What the 2026-10-12 canary (30 requests from the Mac) confirmed: the
   `custom_id` form, the result body and `batches.list` newest first; not observable then:
   `token_limit_exceeded`, so the first `queue limit reached` line in a pod's log is its first real
   sighting (since P1 a run refused while other pods' batches fill the queue waits and resends; it
   splits only when nothing else is queued).  The merge refuses on a duplicate stem, uncollected
   batches, differing generation settings, a listed entity without responses, or the scanner's exit 3.
6. **The rsync scripts' pod address** (walk-through E7).
   [rsync_completed_axes.sh](../../scripts/rsync_completed_axes.sh) and
   [rsync_pod_sweeps.sh](../../scripts/rsync_pod_sweeps.sh) hard-code a pod IP and port that will be
   stale: update them to the October pods, and change `StrictHostKeyChecking=no` to `accept-new`.

## The test backlog: what only a pod can confirm (Roger, 2026-10-13)

Every fix of the 2026-10-12 review and its pipeline batch has tests on the Mac, against fakes (a fake
`uv` for the driver, a fake model for step 2, a fake Batch API client for step 3, fake trees for the
scanner and the merge).  The behaviours below are the ones those fakes cannot reach; each is checked once,
during the smoke run and the cap pilot (items 1–2), and closed here with the date, the pod run and the
result.  A failure is a bug in the batch, fixed before the four-pod launch.

| # | behaviour | built in | how to check | pass sign |
|---|---|---|---|---|
| T1 | step 1's worker exit codes and the K-consecutive-failures abort with a real vLLM engine (the engine is mocked on the Mac) | P8.1, cc490235 | run step 1 on a handful of entities; then once with a deliberately bad `--model` path | exit 1 both ways, `run_pipeline.sh` stops before step 2 |
| T2 | `--roles` filtering and `--non_goal_count 54` (the pilot's `verbose`) build exactly the listed work items | P1 review, P6 | step 1's "work items" log line against [cap_pilot_entities.json](./cap_pilot_entities.json) | counts equal; no "no work item is named" warning |
| T3 | the `generation_config.json` side-car is written and a rerun into the same dir with changed settings is refused | P2, 35acbe43 | rerun step 1 with a different `--max_tokens` into the pilot's dir | refused without `--allow_mixed_settings` |
| T4 | step 2 under the pod's transformers 4.57.6 finds the seven header tokens (the `BatchEncoding` fix is proven only under the Mac's 5.1.0) | 11d7f28c | `activations.log` after the first entity | 0 header misses, 500 keys saved |
| T5 | the activation metadata carries `layers`, `max_length`, `thinking`, `batch_size`, `extract_headers` and step 4 copies it | 11d7f28c | read one vector's `metadata` | all keys present |
| T6 | the tmpfs mirror: `rsync` present or the staged `cp` fallback; the completeness marker written; a second run reuses the mirror | P8.6 | the driver's `[tmpfs]` lines on two consecutive runs | marker file present; second run "reusing" |
| T7 | the HF-cache check and the torch import time with the venv on local disk vs `/workspace` | P8.3 (b) | `time uv run python -c "import torch"` from each | the number goes in the README |
| T8 | step 3 batch mode at real scale: `token_limit_exceeded` on a full chunk, the queue-holding behaviour, `batches.list` newest-first with many batches | 56f3df3e, P5 | the first chunk over the org limit; a second pod submitting | the "queue limit reached" line, then a wait, not a split |
| T9 | the step-3 lock: a second step 3 on the same scores dir refuses; `--force_unlock` clears a stale lock | P5, e7ef8a48 | start two by hand | second refuses with the PID and host |
| T10 | the new response fields (`finish_reason`, `thinking_stripped`, `thinking_suspected`, `question_id`) on real responses; the truncation share at 512 | P6, 8066b6ad | count `finish_reason == "length"` over the pilot's 512 tree | about 70%, the May estimate |
| T11 | float32 vectors and axes: file sizes (~10 MB), `5_axis.py`'s dtype checks, steering's cast to the model dtype at load | P3, bcee9262 | step 4/5 outputs; one steering cell load | sizes as expected; no dtype error |
| T12 | the scanner on real 2.6 GB activations and on a tree whose activations were deleted (`vector_only`) | ba4efef2, P1 | scan before and after deleting the pilot's activations | exit 0 both times; `vector_only` rows after |
| T13 | the scan-as-stop: a tree with a planted re-run candidate stops the driver before step 5 | e92912d8 | truncate one activation file by hand, rerun | "Pipeline aborted: Scan failed"; no axis written |
| T14 | the merge: two pod trees into one, the duplicate-stem refusal, `usage.json` merged per type, the root scan | P1, b43ce369 | merge the pilot's tree with a second small tree | counts match the entity list; refusal on a duplicate |
| T15 | NFS: the retry set without `FileNotFoundError`, and the opt-in `fsync` timing on `/workspace` | P8.4, E4 | the E4 timing (item 4); a missing-file read returns at once | no 265 s wait on a missing file |
| T16 | `run_pipeline.sh` from the pod's shell: the `pipeline/` guard, the end-of-run summary with step 4/5 lines, the `--judge-batch-requests` pass-through | ba4efef2, P1 | one full run on the pilot's entities | summary counts the `[ERROR]`/`[WARNING]` lines of every step |

Not on this list because they are experiments, not tests: the cap pilot's decision (item 2), the rubric
experiment (item 11), P7's smoke runs per family (item 7).

## Only if the multi-model plan is built first

7. **P7's byte-identical Qwen regression** on a GPU
   ([coding_plan_multi_model_extraction.md](./coding_plan_multi_model_extraction.md)): the gate that the
   generalised steps 1 and 2 reproduce today's Qwen output exactly.  The plan's build waits on Roger's go.

## During and after the extraction

8. **Fresh output dir on every pod** (walk-through P2) and **delete the activations once the scanner
   passes** (P1; about 8 TB in all).
9. **The October-run rows of the regeneration list**
   ([regeneration_list.md](../code_review_2026-10-12/regeneration_list.md), "when: at the October run"):
   check each is covered by the run, then close it there.
10. **The new data dir's MANIFEST names its pair-list generation** (walk-through A2, the part that waits
    for October).  Once the October extraction gives a second data dir beside the 8slot one, its
    `MANIFEST.json` (written by [regenerate_dataset_manifest.py](../../tools/regenerate_dataset_manifest.py))
    records which pair lists it was extracted for: the current ones
    ([pair_list_clean.json](../../roger/axis_judge_experiments/pair_list_clean.json),
    [pair_list_di.json](../../roger/axis_judge_experiments/pair_list_di.json),
    [pair_list_goalnongoal.json](../../roger/axis_judge_experiments/pair_list_goalnongoal.json),
    [pair_list_responses.json](../../roger/axis_judge_experiments/pair_list_responses.json)) and the goal
    file it used, [goal_roles_and_traits.json](../../data/goal_roles_and_traits.json); the 8slot dir's
    MANIFEST says `_v1` and [goal_roles_and_traits_v1.json](../../data/goal_roles_and_traits_v1.json).
    Then a results_analysis script can refuse a pair list of the other generation by name, rather than
    only by the missing-axis check of [pair_list_guard.py](../../results_analysis/pair_list_guard.py)
    (built 2026-10-12, which catches it only where an axis is missing).  The field and the check are
    built with the manifest change; nothing to do on the pod beyond regenerating the manifest after the
    run.

11. **The role-judge rubric experiment** ([plan_role_rubric_experiment.md](./plan_role_rubric_experiment.md);
    about $50 of batch judging on 60 roles, over the $20 line: **Roger's go with quoted parameters**).  After the
    roles' step 3 in October and before the role vectors are final: the rubric arms as temporary render flags, a
    twice-run baseline for judge noise, boundary flips read by Roger; the AI-persona roles over-sampled
    (aligned_artificial_intelligence, now [instrumentally_aligned_ai](../../data/roles/instructions/instrumentally_aligned_ai.json),
    passed 34% in May).  From the peer session's pipeline batch
    ([fix_batch_2026-10-12.md](./fix_batch_2026-10-12.md)).
