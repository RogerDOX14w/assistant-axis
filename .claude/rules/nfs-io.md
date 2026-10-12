---
paths:
- pipeline/**
- assistant_axis/atomic_io.py
- assistant_axis/tmpfs.py
- assistant_axis/axis.py
- assistant_axis/steering_runner.py
- scripts/**
- runpod_workspace/**
- steering/**
- results_analysis/axis_judge_correlation.py
---
<!-- GENERATED FILE: do not edit.  Source: AGENT_NOTES.md (section markers).  Regenerate with: uv run python tools/sync_agent_notes.py -->
# Rule: nfs-io

**When:** reading or writing anything under /workspace or another network-mounted path.  Loads automatically for files matching the `paths` above.  Source: the sections of [`AGENT_NOTES.md`](AGENT_NOTES.md) marked `rule=nfs-io`; edit there, then run `uv run python tools/sync_agent_notes.py`.

### NFS-safe file I/O (mandatory for `/workspace` reads and writes)

`/workspace` on RunPod is a MooseFS-backed network mount. Direct file
ops are usable but occasionally flaky — partial copies, transient `EIO`,
slow flushes, and (most importantly) **silent short reads from
torch.load** that surface as `RuntimeError("storage has wrong byte
size of dtype ...")` or `RuntimeError("PytorchStreamReader failed
reading zip archive: ... unexpected EOF, expected N more bytes")`.
Both reads and writes need defensive handling.

**The pattern in this codebase:**

- **Writes**: stage to a local-disk temp file (via `TMPDIR`), copy it
  with retry/backoff to `<dest>.inprogress` beside the destination, then
  `os.replace` that copy onto the final name, then unlink the temp.
  Atomic from a reader's point of view: dest never exists in a
  half-written state.  Small writes (`atomic_write_text` / `_bytes`,
  `append_jsonl`, `write_jsonl`) take `fsync=True` to flush the
  `.inprogress` copy before the rename (off by default until timed on the
  pod's NFS, item 4 of reports/pipeline/pre_extraction_pod_todo.md); the
  staging file name carries the process and thread id (since 2026-10-12,
  walk-through E4).  Tensor saves (`torch_save_with_retry`)
  additionally run **three integrity checks on the `.inprogress` copy,
  and rename it into place only when all pass** (since 2026-10-12; it
  used to rename first and verify dest).  A failure deletes the copy and
  triggers another copy attempt; dest is never touched, so a crash
  mid-verification leaves no file that skip-if-exists resume logic would
  take for finished, and a save that fails every attempt leaves an
  existing dest in place:
    1. **Size** matches staging byte-count (catches short-writes).
    2. **SHA-256** matches staging digest (catches silent byte-flips
       inside a correct-size file — e.g. corrupted NFS chunks that
       pass length checks; this is the failure mode behind the
       2.6 GB-but-unloadable `r_guardian__casual.pt`).
    3. **`torch.load` round-trip** succeeds (catches version-drift /
       pickle-format issues that byte-equality alone wouldn't).
  Both verify steps default to on; pass
  ``verify_sha256=False`` / ``verify_load=False`` to opt out when
  the hot-path cost isn't warranted.
- **Reads**: direct read inside a 5-attempt retry loop with the
  project-standard **exponential** backoff
  `DEFAULT_RETRY_DELAYS_S = (5, 20, 60, 180)` seconds (cumulative wall
  clock ~265 s, matching the API-retry standard in
  `results_analysis/axis_judge_correlation.py`).  Treats `OSError`,
  **`RuntimeError`** *and* `EOFError` as transient — the
  `RuntimeError` case is the failure mode above; earlier code that
  retried only `OSError` missed it entirely.  On final failure: log
  error and raise; the caller's outer loop is responsible for any
  "skip this item, continue with the rest" semantics.
  **Except `FileNotFoundError`** (since 2026-10-12, review P4 D5 /
  walk-through P8.4; `NON_TRANSIENT_READ_ERRORS`): a missing file is
  raised at once, although it is an `OSError`, because a file that does
  not exist is not an NFS hiccup and the retries cost 265 s per missing
  file (13 files, ~57 min, in step 4 on 2026-05-03).  A stale NFS handle
  (`OSError` with errno `ESTALE`, not a `FileNotFoundError`) is still
  retried.  A file another pod has just written can in principle be
  briefly invisible over NFS (negative lookup caching); none of the
  readers depends on that, since each step reads only files that a
  directory listing or an earlier step of the same process produced.

New call sites should use the `assistant_axis.atomic_io` helpers
rather than re-rolling the pattern:

```python
from assistant_axis.atomic_io import (
    # Writes (via TMPDIR staging + atomic rename)
    atomic_write_text, atomic_write_bytes, append_jsonl, write_jsonl,
    torch_save_with_retry,
    # Reads (direct read in retry loop)
    read_text_with_retry, read_jsonl_with_retry, torch_load_with_retry,
)

atomic_write_text(json.dumps(config) + "\n", "/workspace/.../config.json")
append_jsonl({"foo": 1}, "/workspace/.../records.jsonl")
write_jsonl(records, "/workspace/.../records.jsonl")    # full rewrite
torch_save_with_retry(state_dict, "/workspace/.../checkpoint.pt")

config_text = read_text_with_retry("/workspace/.../config.json")
records = read_jsonl_with_retry("/workspace/.../records.jsonl")
state = torch_load_with_retry("/workspace/.../checkpoint.pt", map_location="cpu")
```

For very large tensors where you want to control torch.save's zipfile
flag (e.g. step 2's ~2.6 GB activation files where the new-style zip
serializer hits "iostream error" on RunPod), pass it through:

```python
torch_save_with_retry(activations_dict, output_file,
                      use_zipfile_serialization=False)
```

**Why:** silent failures here are extremely costly — multi-hour
generation runs that lose their last partial flush, restarts that
choke on their own state files, vectors silently missing because step 4
got a short read and skipped after warning.  The retry loops have
caught real RunPod NFS hiccups and let runs proceed; the size-sanity
check on writes catches the silent-truncation case that no exception
would otherwise reveal.

**Don't retry parse errors.**  `read_text_with_retry`,
`read_jsonl_with_retry` and `torch_load_with_retry` retry only on the
transient set above.  `JSONDecodeError`, `UnicodeDecodeError`, and
`pickle.UnpicklingError` propagate immediately because they almost
always indicate a corrupt-on-disk file rather than NFS flakiness, and
retrying just amplifies the delay.  `read_jsonl_with_retry` does
silently skip malformed lines by default (with a warning) since
records.jsonl can in principle have a half-flushed last line, though
`atomic_write_text` makes that nearly impossible on the writer side;
pass `skip_malformed=False` to make a malformed line fatal instead.

**TMPDIR setup:** drivers call `assistant_axis.tmpfs.setup_tmpdir(target)`
(default `target="/dev/shm"`) which **unconditionally** overrides any
pre-existing `$TMPDIR` so the atomic-write staging files land on RAM-
backed tmpfs.  This is by design: pod-defaults like
`TMPDIR=/workspace/tmp` would silently route every staging write
through slow NFS, and pre-May-2026 we had `setup_tmpdir_if_unset()`
preserve such defaults (requiring `unset TMPDIR` before every run).
Both `pipeline/run_pipeline.sh` and `steering/run_sweep.py` expose a
`--tmpdir <path>` CLI flag; callers who genuinely want to preserve
their existing `$TMPDIR` must pass it explicitly via
`--tmpdir "$TMPDIR"`.  The deprecated `setup_tmpdir_if_unset()` is
kept as a thin shim for external callers but logs a warning.

**Model mirror (one implementation since 2026-10-12, P8.6):** both
drivers mirror the model's HF cache into `/dev/shm/hf-cache` through
`assistant_axis.tmpfs.setup_model_tmpfs_cache` (the shell driver runs
`python ../assistant_axis/tmpfs.py mirror ...`, which prints the new
`HF_HOME`; until then it had its own `cp -r` with no marker), and both
take `--tmpfs-method {auto,rsync,cp}`: rsync tops up in place; cp copies
into a staging directory renamed into place and neither trusts nor
deletes an unmarked existing mirror; auto is rsync when installed, else
cp.  Both write the `.tmpfs_mirror_complete` marker the fast path reads.
Details in [`pipeline/README.md`](pipeline/README.md) § "Model mirror in
tmpfs".

**Auditing past damage**: `pipeline/scan_missing_vectors.py` walks an
`activations/`+`vectors/`+`scores/` triple (plus `responses/` beside
`activations/` when present) and classifies each missing or unreadable
vector as one of `mysterious` / `corrupt_or_truncated_activation` /
`corrupt_vector` / `ok_zero_size` / `stale_vector` (re-run candidates;
the last, since 2026-10-12, a vector whose recorded scores hash differs from
the scores file now, which step 4 also recomputes on its own) vs
`missing_scores` / `below_min_count` / `all_nan_or_empty` (legitimate
filter); it exits 3 when it finds re-run candidates or
`missing_activation` entities.  Since 2026-10-12 it also checks a tree
whose activations have been deleted (the four-pod procedure, walk-through
P1): every entity with responses must have a vector that loads
(`vector_only`) or a reason not to; `tools/merge_pod_outputs.py` runs it on
the merged tree.  Use it to recover from historical
short-read damage that pre-retry step 4 silently skipped (statuses and
recovery steps in [`pipeline/README.md`](pipeline/README.md)).

**Current call sites (keep this list updated as new ones land):**

- Writes via `atomic_io`: `pipeline/2_activations.py` (uses
  `torch_save_with_retry`), `pipeline/3_judge.py` (score files,
  `usage.json`, `judge_rubric.json` via `atomic_write_text`),
  `assistant_axis/openai_batch.py` (step 3's `batch_state.json`),
  `pipeline/4_vectors.py`, `pipeline/5_axis.py`,
  `pipeline/scan_missing_vectors.py` (its reports),
  `assistant_axis/steering_runner.py`, `steering/run_sweep.py`,
  results_analysis/axis_judge_correlation.py (`_save_json` and its usage.json, since 2026-10-12, D4)
- Reads via `atomic_io`: `assistant_axis/generation.py` (step 1:
  `load_role`, `load_questions`), `pipeline/2_activations.py`
  (responses), `pipeline/3_judge.py` (responses via
  `read_jsonl_with_retry`, score files via `read_text_with_retry`),
  `pipeline/4_vectors.py`, `pipeline/5_axis.py`,
  `pipeline/scan_missing_vectors.py`,
  `assistant_axis/steering_runner.py`, `steering/run_sweep.py`,
  `assistant_axis/axis.py` (`load_axis`, `load_axis_with_metadata`,
  `load_role_vector` — used by notebooks too)
- Same pattern, own code: `assistant_axis/generation.py`
  `save_responses` (step 1's response files: local `/tmp` staging,
  retried copy to `.inprogress`, rename)

---
