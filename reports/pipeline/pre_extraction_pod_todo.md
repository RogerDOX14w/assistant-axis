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

## The first pod (2026-10-22): what it showed

A new RunPod account (a team account; see the auto-memory note on it), volume `Roger_AA_1` (200 GB,
US-KS-2), pod `roger-aa-smoke` on 1× A100 PCIe 80 GB (16 vCPUs, 125 GB RAM), image
`runpod/pytorch:1.4.1-cu1281-torch280-ubuntu2404`, start command running
[pipeline/pod/start.sh](../../pipeline/pod/start.sh) when the checkout exists.  Roger's order that day: the
smoke run, then the role-rubric experiment (item 11), ahead of the cap pilot.

- **The pod sat at "Initializing" for about an hour** with no container or system logs, then came up by
  itself.  Nothing was wrong with its configuration; allow for it.
- **The template's environment overrides did not reach the container**; only the start command did.  The
  image itself sets `HF_HOME=/workspace/.cache/huggingface/` and `UV_CACHE_DIR=/workspace/.cache/uv/`.  SSH
  sessions see neither, so `/workspace/pod_env.sh` holds the non-secret settings (the venv path
  `/root/venvs/assistant-axis`, `UV_LINK_MODE=copy`) and every command sources it.  The OpenAI key is not
  needed on the pod: step 3 ran on the Mac.
- **`/dev/shm` is 58 GB and `noexec`** on a 125-GB host, smaller than Qwen3-32B's 62 GB, so the RAM mirror
  cannot hold the model (the mirror code checks space and skips).  The weights loaded from `/workspace` in
  under two minutes because the download had left them in the page cache (a full re-read ran at 5.5 GB/s).
  **A cold load from the volume is untested**; on a pod where it is slow, the fix is a container disk large
  enough for the mirror (`--tmpfs-dir` on the container disk) or a host with more RAM.
- **Item 3, the local half:** `uv sync --frozen` into the container-disk venv took 179 s (9.6 GB); importing
  torch and vLLM took 8 s.  The `/workspace` venv was not built, so the comparison is still open.
- **The model download** (`snapshot_download`, 62 GB) took 212 s.
- **`rsync -a` fails on the volume** (it cannot change ownership): use `rsync -rt`.
- **The RunPod API, read only**, through [tools/runpod_api.py](../../tools/runpod_api.py) (Roger's read-only
  key in `.env` as `RUNPOD_API_KEY`): `stock` lists the GPU types in stock per datacenter, with whether it
  takes network volumes, in one call (the console needs a click per datacenter); `pod <id>` shows a pod's
  configuration as RunPod stored it, environment by name only, which is how the dropped overrides above
  were confirmed; `pods`, `volumes`.  Run `stock --volumes-only` before choosing a datacenter, and `pod`
  after every deploy.  Stock is RunPod's coarse "Low" / "Medium" / "High"; there are no counts.
- **The second pod, `roger-aa-2`** (2026-10-22 evening; 1× A100 SXM, 251-GB host): the first pod's A100 PCIe
  had gone when we tried to restart it (RunPod then offers "Start Pod using CPUs" or a migration), so a new pod
  went on the same volume.  It came up in about a minute, and the template's start command ran
  [pipeline/pod/start.sh](../../pipeline/pod/start.sh), which rebuilt the venv by itself in about 2.5 minutes.
  Its `/dev/shm` was 117 GB (still `noexec`), so the model mirror ran: **691 s cold from the volume** (rsync,
  about 90 MB/s), after which step 1 (`default`, 500 responses) took 280 s and step 2 175 s.  Stopped with
  `runpodctl` from inside, as the first pod was.
- **SSH from the agent's sandbox** goes through the sandbox's own proxy with an HTTP CONNECT relay
  (`.secrets/runpod/ssh_proxy.py`, git-ignored), under Roger's permission rule for
  `ssh -F .secrets/runpod/ssh_config` (his choice of 2026-10-22 over taking ssh out of the sandbox).

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
   **Done 2026-10-22, as a separate launch** (Roger: "maybe just default"; one trait added so steps 3 and 4
   run too): pod `roger-aa-smoke`, entities `default` and `absolutist`, 30 questions, git f8a3a417.  Every
   check of item 13's list passed; the side-car, the new response fields and the float32 vectors and axis
   all behaved.  Results in the smoke-run table of
   [acceptance_multi_model_extraction.md](./acceptance_multi_model_extraction.md).  Not yet exercised:
   the model mirror (it could not fit, above), the four-GPU path, and P8.1's exit status on a failing run.
2. **The response-length cap pilot** ([plan_max_tokens_pilot.md](./plan_max_tokens_pilot.md); about 16
   GPU-hours and $25 batch, over the GPU line: **Roger's go with quoted parameters**).  64 entities at caps
   256 / 512 / 768 / 1024; decides the cap the extraction uses.  Needs P6's `finish_reason` and P8.1 first.
   The entity list, [cap_pilot_entities.json](./cap_pilot_entities.json) (built 2026-10-12, seed
   20261012), and [cap_pilot_compare.py](../../tools/cap_pilot_compare.py) (built) come from the peer
   session's P6 (8066b6ad); the plan's § 4 commands were corrected to the list's format, and three
   readings of the decision rule (centred cosines, layer 25, the 2-point test) wait for Roger's word
   in the plan before the pilot runs.
3. **The venv on local disk** (walk-through P8.3 (b)).  The recorded slow step was importing torch over
   NFS.  On the first pod, put the environment on local disk (`UV_PROJECT_ENVIRONMENT`;
   not `/dev/shm`, which RunPod mounts `noexec`, so no shared library there can be loaded: the
   2026-05-02 breakage, 8d20fb41), time the import against the `/workspace` venv, and write the pod setup
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
14. **Activation read and write speed on the volume** (Roger, 2026-10-24: "test it, next time we bring a pod
    up").  On `roger-aa-4` (2026-10-23, a fresh host in US-KS-2) step 4 read cold activation files at about
    9 MB/s, about 5 minutes per 2.6-GB file, and four step-4 processes at once were no faster in total;
    `roger-aa-2` read files it had written two hours earlier in 50-70 s each (page cache), and the cold
    rsync of the model ran at about 90 MB/s.  At 9 MB/s step 4 of the extraction would take about a day
    per pod.  Every file already on the volume is cold on a new pod; use each file for one measurement only.
    Measure: (a) `dd if=<file> of=/dev/null bs=16M` on one file against `torch.load` of another; (b) 1, 2, 4
    and 8 `dd` streams on different files at once, to see whether the total scales (it decides whether
    read-ahead helpers help, or whether the bandwidth is capped); (c) 8 threads reading ranges of one file;
    (d) one step-2 save timed phase by phase (staging, copy to the volume, SHA-256 of the copy, load check).
    Fixes to build off-pod first and time in the same session: step 4 reads each file into RAM in large
    reads (sequential or parallel ranges, whichever (b) and (c) favour) and loads it from memory, reading the
    next file ahead in a thread; step 2 runs its load check on the staged RAM copy once the SHA-256 of the
    volume copy matches.  Storage, checked 2026-10-24: high-performance network volumes ($0.14/GB-month
    against $0.07) exist in AP-IN-1, CA-MTL-1, CA-MTL-4, EU-FR-1, EUR-NO-2 and US-CA-2, not in US-KS-2,
    and the console offers new volumes there as high-performance only; the container disk (local, $0.10
    /GB-month, cleared on stop) is fast scratch space in any data center.
    **(a)-(c) measured 2026-10-26 on `roger-aa-5`** (1x A100 SXM, US-KS-2, a fresh host, cold October
    activation files): `dd` 109 MB/s; `torch.load` 108 MB/s (24 s per 2.6-GB file, no slower than `dd`);
    1, 2 and 4 parallel `dd` streams 110, 117 and 117 MB/s in total; 8 threads reading ranges of one file
    107 MB/s.  So the volume gives a pod about 110-120 MB/s whatever the read pattern or parallelism:
    read-ahead helpers and parallel range reads would not help, and the 9 MB/s of `roger-aa-4` was that
    pod (or its host), not `torch.load`.  At 110 MB/s step 4 reads one entity in about 25 s, about 2 hours
    per 300 entities.  Still open: (d), the step-2 save to the volume timed phase by phase.

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
| T5 | the activation metadata carries `layers`, `max_length`, `batch_size`, `extract_headers`, `model_type` and `template_kwargs` (`thinking` was replaced by `template_kwargs` in P7) and step 4 copies it | 11d7f28c, a9d3f9dd | read one vector's `metadata` | all keys present |
| T6 | the tmpfs mirror: `rsync` present or the staged `cp` fallback; the completeness marker written; a second run reuses the mirror | P8.6 | the driver's `[tmpfs]` lines on two consecutive runs | marker file present; second run "reusing" |
| T7 | the HF-cache check and the torch import time with the venv on local disk vs `/workspace` | P8.3 (b) | `time uv run python -c "import torch"` from each | the number goes in the README |
| T8 | step 3 batch mode at real scale: `token_limit_exceeded` on a full chunk, the queue-holding behaviour, `batches.list` newest-first with many batches | 56f3df3e, P5 | the first chunk over the org limit; a second pod submitting | the "queue limit reached" line, then a wait, not a split |
| T9 | the step-3 lock: a second step 3 on the same scores dir refuses; `--force_unlock` clears a stale lock | P5, e7ef8a48 | start two by hand | second refuses with the PID and host |
| T10 | the new response fields (`finish_reason`, `thinking_stripped`, `thinking_suspected`, `question_id`) on real responses; the truncation share at 512 | P6, 8066b6ad | count `finish_reason == "length"` over the pilot's 512 tree | about 70%, the May estimate |
| T11 | float32 vectors and axes: file sizes (~10 MB), `5_axis.py`'s dtype checks, steering's cast to the model dtype at load | P3, bcee9262 | step 4/5 outputs; one steering cell load | sizes as expected; no dtype error |
| T12 | the scanner on real 2.6 GB activations and on a tree without them (`vector_only`) | ba4efef2, P1 | scan the pilot's tree, then a copy of it made without `activations/` (the activations themselves stay: Roger, 2026-10-13) | exit 0 both times; `vector_only` rows on the copy |
| T13 | the scan-as-stop: a tree with a planted re-run candidate stops the driver before step 5 | e92912d8 | truncate one activation file by hand, rerun | "Pipeline aborted: Scan failed"; no axis written |
| T14 | the merge: two pod trees into one, the duplicate-stem refusal, `usage.json` merged per type, the root scan | P1, b43ce369 | merge the pilot's tree with a second small tree | counts match the entity list; refusal on a duplicate |
| T15 | NFS: the retry set without `FileNotFoundError`, and the opt-in `fsync` timing on `/workspace` | P8.4, E4 | the E4 timing (item 4); a missing-file read returns at once | no 265 s wait on a missing file |
| T16 | `run_pipeline.sh` from the pod's shell: the `pipeline/` guard, the end-of-run summary with step 4/5 lines, the `--judge-batch-requests` pass-through | ba4efef2, P1 | one full run on the pilot's entities | summary counts the `[ERROR]`/`[WARNING]` lines of every step |
| T17 | step 1's preflight: `config.json` and the tokenizer read before vLLM starts, the `qwen3` row found, the derived header logged | P7 task 7, 3fe3581c | step 1's log before "Loading vLLM model" | "Family qwen3 ... header [the seven] (ids [151644, 77091, 198, 151667, 271, 151668, 271])" |
| T18 | vLLM 0.18.1 takes token-id prompts (`{"prompt_token_ids": ids}`), and Qwen3's ids equal the old text path's | P7 task 7, 3fe3581c | in a Python shell on the pod, for one conversation: `prompt_token_ids(tok, conv, {"enable_thinking": False})` against `tok(tok.apply_chat_template(conv, tokenize=False, add_generation_prompt=True, enable_thinking=False))["input_ids"]`; then step 1 on a few entities | equal; responses written as before |
| T19 | vLLM loads Qwen3-32B with `trust_remote_code=False` (from the row; it was `True`), and vLLM's tokenizer derives the preflight's header ids | P7 task 7, 3fe3581c | step 1's "Model loaded successfully; header" line | no error; the seven |
| T20 | the side-car's new fields on a real run | P7 task 7, 3fe3581c | read `<responses>/generation_config.json` | `model_type` qwen3, `header_ids` the seven ids, `system_prompt` native, `sample_conversation` and `sample_prompt_ids` present |
| T21 | step 2's preflight and side-car check against a real step-1 side-car, without `--ignore_generation_config` | P7 tasks 6, 8, a9d3f9dd, 8156f4c2 | step 2's log before "Loading model" | the layout line, then "... match"; no refusal |
| T22 | the activation metadata of the new step 2: `model_type`, `template_kwargs`, `generation_prompt_ids` present, `thinking` gone (row T5's `thinking` no longer applies); step 4 copies it, step 5 compares it | P7 tasks 6, 8, a9d3f9dd, 8156f4c2 | one activation's, one vector's and the axis's `metadata` | the keys present, `thinking` absent |
| T23 | `--verify_spans 20` on real Qwen3 responses (real BPE, real content) | P7 task 6, a9d3f9dd | step 2 with `--verify_spans 20` | "20 of 20 assistant spans decode to the stored content" |
| T24 | `--layers` checked against the real layer count before any load | P7 task 6, a9d3f9dd | step 2 once with `--layers 0,64` (Qwen3-32B has 64) | an argparse error naming "64 layers, 0..63", before "Loading model" |
| T25 | the byte-identical regression on the real model (item 7 (b)) | P7 build abdfa16c-7a6e5acb; golden fixture from 828817a4 | item 7's comparison | 0 activations differ |
| T26 | the analysis scripts' slot-layout guard passes on the October Qwen3 tree | P7 task 10, 94d3e256 | any `DEFAULT_SLOT` script on the new data dir without `--slot` (e.g. `whitening_k_sweep.py --data_dir <October tree>`) | no `SlotLayoutError` |
| T27 | steering's template kwargs from the row, and the slot label, on the real model | P7 task 10, e82b74a7 | one steering cell: the sweep log and the first prompt's rendering | the empty think block in the prompt; "steering slot 6 ('</think>')" logged; no header warning |
| T28 | the real-tokenizer test for `qwen3` under the pod's transformers 4.57.6 | P7 task 11, 0301aa09 | item 12 for `qwen3` | 5 passed; the printed header is the seven |

Not on this list because they are experiments, not tests: the cap pilot's decision (item 2), the rubric
experiment (item 11), P7's real-tokenizer checks and smoke runs per family (items 12–13; the byte-identical regression on the real model is item 7).

## Only if the multi-model plan is built first

7. **P7's byte-identical Qwen regression** on a GPU
   ([coding_plan_multi_model_extraction.md](./coding_plan_multi_model_extraction.md)): the gate that the
   generalised steps 1 and 2 reproduce today's Qwen output exactly.  **Built off-pod on 2026-10-13**
   (commits abdfa16c to 7a6e5acb; [p7_build_2026-10-13.md](./p7_build_2026-10-13.md),
   [acceptance_multi_model_extraction.md](./acceptance_multi_model_extraction.md)); on the in-process
   fakes the gate is green ([test_step2_qwen3_golden.py](../../pipeline/tests/test_step2_qwen3_golden.py),
   fixture made from 828817a4, the code before P7).  On the pod, with the real model:

   (a) **The Qwen3 smoke run** rides on item 1 (the first entities of the October run or the cap pilot;
   § 15 Q9): step 1 logs the family and the derived header (the seven tokens, ids `151644 77091 198
   151667 271 151668 271`) and writes the side-car's new fields; step 2, run with `--verify_spans 20`,
   passes its side-car check and the span check.  Rows T17-T24 and T28.

   (b) **The regression**: step 2 from 828817a4 and from today's code on the same two response files,
   compared bit for bit (row T25).  About 0.5 GPU-hour on one 80 GB GPU (two Hugging Face loads of
   Qwen3-32B and about 1,000 conversations each); the four activation files, about 10 GB, are deleted
   afterwards.  From a pilot or October responses directory `<R>` that has a side-car:

   ```bash
   git -C /workspace/assistant-axis worktree add /workspace/aa_828817a4 828817a4
   # the old code in the repository's own environment (a plain `uv run` in the worktree would
   # build a second one); the script puts its own checkout first on sys.path
   cd /workspace/aa_828817a4/pipeline && CUDA_VISIBLE_DEVICES=0 uv run --project /workspace/assistant-axis \
       python 2_activations.py --model Qwen/Qwen3-32B --responses_dir <R> --roles default absolutist \
       --output_dir /workspace/p7_reg/old
   cd /workspace/assistant-axis/pipeline && CUDA_VISIBLE_DEVICES=0 uv run 2_activations.py \
       --model Qwen/Qwen3-32B --responses_dir <R> --roles default absolutist --output_dir /workspace/p7_reg/new
   uv run python -c "
   import torch
   for e in ('default', 'absolutist'):
       a = torch.load(f'/workspace/p7_reg/old/{e}.pt', weights_only=False); ma = a.pop('metadata')
       b = torch.load(f'/workspace/p7_reg/new/{e}.pt', weights_only=False); mb = b.pop('metadata')
       assert 'thinking' in ma and 'model_type' in mb, 'not the old and the new code'
       assert sorted(a) == sorted(b), e
       bad = [k for k in a if not torch.equal(a[k].view(torch.int16), b[k].view(torch.int16))]
       print(e, len(a), 'activations,', len(bad), 'differ')"
   ```

   Pass: `0 differ` for both.  Afterwards `git worktree remove /workspace/aa_828817a4`.  Any difference is a stop, reported with the keys, before the October
   extraction uses the new code.

12. **The real-tokenizer check per family** (P7, the plan's § 9 test 11,
    [test_chat_layout_real.py](../../assistant_axis/tests/test_chat_layout_real.py)), before that family's
    smoke run, and for `qwen3` before the October run (row T28).  Tokenizer and config files only, about
    10-20 MB each, downloaded on the pod (Roger, § 15 Q5: no need to ask); Llama and Gemma are gated, so
    Roger's Hugging Face token must be in the pod's environment.  No GPU.

    ```bash
    huggingface-cli download <model> --include "*.json" "tokenizer*" "*.model" "*.jinja"
    ASSISTANT_AXIS_HF_TESTS=1 ASSISTANT_AXIS_HF_FAMILIES=<row> \
        uv run pytest -s assistant_axis/tests/test_chat_layout_real.py
    ```

    `<model>` / `<row>`: `Qwen/Qwen3-32B` / `qwen3`; `meta-llama/Llama-3.3-70B-Instruct` / `llama`;
    `google/gemma-2-27b-it` / `gemma2`; `allenai/OLMo-2-0325-32B-Instruct` / `olmo2` (or the OLMo § 15 Q6
    picks).  Pass: 5 passed for the row, and the printed header goes into the acceptance report for Roger
    to read.  A failure means a "to check" cell of the row was wrong (`TO_CHECK` in
    [model_families.py](../../assistant_axis/model_families.py) lists them with their checks): correct
    the row before the smoke run.

13. **P7's smoke run per new family** (the plan's § 11), one family per launch, each only after **Roger's
    go with quoted parameters** (model, GPUs, GPU-hours, download size with its delete-when-done TODO, the
    Hugging Face token for a gated repo): Llama 3.3 70B about 2-3 GPU-hours on 4 GPUs and about 140 GB of
    weights; Gemma 2 27B about 1 GPU-hour and about 54 GB; OLMo 2 32B Instruct (or the OLMo § 15 Q6 picks)
    about 1 GPU-hour and about 65 GB.  gpt-oss is a TODO row and refuses to run (§ 15 Q3).  Step 3's 150
    real-time judge calls cost cents.  From `pipeline/`:

    ```bash
    uv run 1_generate.py --mode roger --model <M> --roles default absolutist \
        --question_count 30 --reduce_questions 1 --output_dir /workspace/smoke/<family>/responses
    uv run 2_activations.py --model <M> --responses_dir /workspace/smoke/<family>/responses \
        --output_dir /workspace/smoke/<family>/activations --batch_size 8 --verify_spans 20
    uv run 3_judge.py --entity_type trait --responses_dir /workspace/smoke/<family>/responses \
        --output_dir /workspace/smoke/<family>/scores --no_batch
    uv run 4_vectors.py --activations_dir /workspace/smoke/<family>/activations \
        --scores_dir /workspace/smoke/<family>/scores --output_dir /workspace/smoke/<family>/vectors --min_count 10
    uv run 5_axis.py --vectors_dir /workspace/smoke/<family>/vectors \
        --output /workspace/smoke/<family>/axis.pt --min_entities 1
    ```

    (`--min_entities 1`: step 5 refuses fewer than 10 non-default vectors since the fix batch's P2, and
    the smoke run has one; the plan's § 11 command predates that.)  The checks, in order (§ 11): (1)
    step 1 prints the derived header and writes it into the side-car; **Roger reads it, and the row's
    `expected_header_tokens` is pinned from it** (a commit to `model_families.py`); (2) step 2's side-car
    check passes and the first conversation's ids carry exactly one BOS where the template writes one;
    (3) `activations.log`: `HEADER NOT FOUND` 0, header mismatches 0, dropped conversations 0 (or only
    empty responses) on both entities (a zero on every family is also the evidence for removing the N - 1
    header tolerance altogether: the TODO at `EXACT_MATCH_BELOW` in
    [`spans.py`](../../assistant_axis/internals/spans.py)); (4) `--verify_spans 20`: 20 of 20; (5) the vector shape is
    `(1 + N, n_layers, hidden)` and `slot_labels` prints the layout; (6) `axis.pt` is written.
    Anything else is a stop, reported with the log lines.  Results go into the smoke-run table of
    [acceptance_multi_model_extraction.md](./acceptance_multi_model_extraction.md).

## During and after the extraction

8. **Fresh output dir on every pod** (walk-through P2).  **Keep the activations** on the pods (Roger,
   2026-10-13: RunPod charges for the volume's size, so deleting saves nothing; the volume is discarded when
   the extraction is done); before discarding it, copy off the activations to keep (roles and traits about
   3.3 TB, all about 8 TB; Roger's 6 TB drive holds the roles and traits).
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
    about $50 of batch judging on 60 roles, over the $20 line: **approved by Roger 2026-10-16 with all eight arms**;
    the parameters are quoted at launch).  After the
    roles' step 3 in October and before the role vectors are final: the rubric arms as temporary render flags, a
    twice-run baseline for judge noise, boundary flips read by Roger; the AI-persona roles over-sampled
    (aligned_artificial_intelligence, now [instrumentally_aligned_ai](../../data/roles/instructions/instrumentally_aligned_ai.json),
    passed 34% in May).  From the peer session's pipeline batch
    ([fix_batch_2026-10-12.md](./fix_batch_2026-10-12.md)).
    **Run 2026-10-22, ahead of the extraction** (Roger: smoke test, then this; $40 approved), on 30 roles, not
    60, to stay inside $40 with every arm kept: the five AI-persona roles plus 25 stratified by May's level-2
    share.  October responses generated on pod `roger-aa-smoke` (step 1 74 min, step 2 69 min, 1× A100 PCIe);
    135,000 judge calls in 14 batches, **$28.31**, all arms parsed 100% but one reply; vectors compared on the
    pod; then the pod stopped itself with `runpodctl`.  Code:
    [role_rubric_experiment.py](../../data_analysis/role_rubric_experiment.py); outputs:
    [arm_wordings.md](./role_rubric_experiment/arm_wordings.md),
    [score_analysis.md](./role_rubric_experiment/score_analysis.md),
    [vector_analysis.md](./role_rubric_experiment/vector_analysis.md), and the blind
    [reading sheet](./role_rubric_experiment/reading_sheet/) for Roger (the plan's decision rule needs his
    marks).  **Decided 2026-10-28** (Roger), after drafts 6 to 9 and the judge comparison
    ([judge_comparison/](./judge_comparison/)): roles are judged by gpt-5.6-luna under **prompt version 10**,
    version 8's decision-procedure text with a reply scored from its A/B/C answers
    ([judge_rubrics.py](../../assistant_axis/judge_rubrics.py); step 3's default version since that day, so
    `run_pipeline.sh --types roles --judge-model gpt-5.6-luna --judge-save-replies`; a roles run without
    `--judge-model gpt-5.6-luna` is refused).  To be revisited on the extraction's data: item 12.

12. **Revisit version 10's "answers win" reading on the full role run** (Roger, 2026-10-28).  Where luna's
    stated score and its A/B/C answers disagree, version 10 takes the answers.  That was decided on the
    rubric experiment's 20,500 version 8 replies
    ([abc_consistency.json](./judge_comparison/abc_consistency.json), from
    [abc_consistency.py](./judge_comparison/abc_consistency.py)): 46 disagreements (0.22%), 11 changing
    keep or drop, where the other two judges, when they agreed, sided with the answers 8 times in 9, and
    Roger's one mark among them (a [virus](../../data/roles/instructions/virus.json) response, G) did too.
    Scoring from the answers agreed with that reference on 39 of 42 mismatched responses, against 32 for
    the stated score and 34 for one rejudge.  A small sample, mostly one kind of case: in-role refusals,
    6 of the 11 from [paperclip_maximizer](../../data/roles/instructions/paperclip_maximizer.json).  Once
    the extraction's roles are judged and their activations extracted:
    1. From the roles' `scores/abc_disagreements.jsonl` (step 3 writes it beside the score files; the
       merge carries it), the disagreement rate overall and per role against the experiment's 0.22% (0.05%
       changing keep or drop), and the commonest patterns.  Step 3's summary warns above 1%.
    2. Roger blind-marks the responses whose keep or drop the reading changed (all of them if about a
       hundred or fewer, else a sample stratified by role and pattern), shown without either score, by the
       readers' criteria ([criteria.md](./judge_comparison/reader_check_v6/criteria.md), Roger's rulings
       through 2026-10-28 included), on a sheet built like
       [reader_check_v7](./judge_comparison/reader_check_v7/)'s
       ([build_v8.py](./judge_comparison/reader_check_v7/build_v8.py) and
       [roger_sheet.py](./judge_comparison/reader_check_v7/roger_sheet.py) write the sheets and their keys,
       [tally.py](./judge_comparison/reader_check_v7/tally.py) reads the marks), to see whether the answers
       or the stated score was right.  A new builder reads the disagreement log in place of a judge cell.
    3. The role vectors both ways on the same activations: the stated-score reading's score files are
       version 10's with each logged key set back to its `stated` score (a key with no stated score
       dropped), or, with the replies saved, `3_judge.py --prompt_version 8 --reread_replies
       <scores dir>`; then step 4 on each, and the cosine per role and the axis against version 10's.
    Then keep version 10, or go back to the stated score (version 8's reading, by the re-read above, with
    no judge calls), or rejudge the disagreements.  Needs the roles judged with `--judge-save-replies`
    (about 1 KB per reply), so that the replies can be read and re-read.
