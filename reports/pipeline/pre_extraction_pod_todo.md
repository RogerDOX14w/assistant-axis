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

1. **The Qwen3 smoke run** (about 1 GPU-hour on 4 GPUs; multi-model plan question 9,
   [coding_plan_multi_model_extraction.md](./coding_plan_multi_model_extraction.md)).  The first
   real-model run of the fixed pipeline: P2's `generation_config.json` side-car and fresh-output-dir rule,
   P6's new response fields (`finish_reason`, `thinking_stripped`, `thinking_suspected`, `question_id`),
   P8.1's exit status, P3's float32 vectors and axis, the derived header tokens if P7 is built.  Roger's
   answer: run it as the first entities of the October run rather than a separate launch.
2. **The response-length cap pilot** ([plan_max_tokens_pilot.md](./plan_max_tokens_pilot.md); about 16
   GPU-hours and $25 batch, over the GPU line: **Roger's go with quoted parameters**).  64 entities at caps
   256 / 512 / 768 / 1024; decides the cap the extraction uses.  Needs P6's `finish_reason` and P8.1 first.
   The entity list, [cap_pilot_entities.json](./cap_pilot_entities.json) (not there yet), and
   [cap_pilot_compare.py](../../tools/cap_pilot_compare.py) (not there yet) come from the peer session's P6.
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
   organisation's queue, and of [merge_pod_outputs.py](../../tools/merge_pod_outputs.py) (not there yet;
   peer session, P1).  Check the queue limit against the sizing before step 3 starts on the second pod.
6. **The rsync scripts' pod address** (walk-through E7).
   [rsync_completed_axes.sh](../../scripts/rsync_completed_axes.sh) and
   [rsync_pod_sweeps.sh](../../scripts/rsync_pod_sweeps.sh) hard-code a pod IP and port that will be
   stale: update them to the October pods, and change `StrictHostKeyChecking=no` to `accept-new`.

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
