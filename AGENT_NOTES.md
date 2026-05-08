# Agent Collaboration Guide

This document describes Roger's working style, communication preferences, and collaboration patterns for AI agents working on this project.

**Purpose:** Help future AI agents collaborate more effectively by understanding expectations upfront.

---

## Communication Style

### Concise and Technical
- Roger is highly technical and doesn't need basic concepts explained
- Prefer direct, information-dense responses over verbose explanations
- Assume sophisticated understanding of programming concepts, tools, and workflows

### Decision-Focused Workflow
- Roger likes to see trade-offs analyzed, then makes decisions quickly
- Example pattern: "Discuss pros and cons of each" → evaluates → "OK, repeated flags is it for now"
- Don't ask for permission when the path forward is clear
- DO ask when there are meaningful design choices to discuss

### Verify-Then-Trust Approach
- Roger prefers checking actual state over accepting assumptions
- Examples:
  - "See what we got, and update the requirements.txt"
  - "Check what's currently installed in the anthropic conda environment"
- When in doubt, check the actual state of files, installations, or system configuration
- Don't guess at versions, paths, or configuration - verify them

### Hotlinking image/plot files in chat replies (mandatory)

When mentioning image, plot, or any other file Roger might want to open
from a chat reply, **always** format the reference as a markdown link
with a workspace-relative path prefixed by `./`.  Cursor renders that
form as a clickable hotlink that opens the file in the IDE; bare paths,
backticked paths, `file://` URIs, and `vscode://file/...` URIs do NOT
hotlink reliably in this environment.

```markdown
[batch_size_cost_vs_quality.png](./roger/axis_judge_experiments/batch_size_curve_8slot/batch_size_cost_vs_quality.png)
```

Use the link text for the bare filename (or a short description); use
the relative path for the link target.  Default assumption: when Roger
asks about an image or plot, he wants to look at it — so always
hotlink.  Same convention for `.json` data files, `.log` outputs, and
other reviewable artefacts that live in the repo.

The `[name](./path)` form is preferred over `[name](/abs/path)` because
it's portable across machines and doesn't bake usernames into chat
transcripts.  Use absolute only when referring to something outside the
workspace root.

---

## Working Modes

### Ask Mode vs Agent Mode
- Roger is conscious of the distinction between read-only (ask) and write (agent) modes
- In **ask mode**: Provide code snippets and instructions for Roger to apply
- In **agent mode**: Implement directly when asked
- When Roger attaches a plan file and says "Implement the plan", that's a clear signal to execute

### Iteration Style
- Prefers conversational iteration over big upfront specifications
- Build incrementally with feedback loops
- Verify results at each step: "See what we got"

### Understanding the Landscape First
- Roger often asks "meta" questions about tooling, APIs, or approaches before diving into implementation
- Examples: "Is tool use better than text parsing?", "What temperature should we use?", "Does Gemini support protobufs?"
- This pattern of understanding constraints and options before committing to an approach helps avoid rework

---

## Plan Requirements

### Testing Must Be Included

**Default rule:** Any plan that modifies code MUST include testing steps.

**Why:** Roger should never be surprised to discover code was changed but not tested.

**Exceptions (only two):**
1. **Roger explicitly says not to test** 
   - Example: "Just implement the fix, I'll test it myself later"
2. **Testing is impractical AND you get approval**
   - Before finalizing the plan, ask: "Testing this requires X which isn't available. Should I proceed without testing, or is there an alternative approach?"
   - Wait for confirmation

**If you're unsure:** Ask before finalizing the plan, don't assume.

---

## Technical Approach

### Check Actual State First
- Always prefer checking actual state over making "reasonable assumptions"
- Use tools to inspect: read files, check installed packages, examine directory structures
- Example: Don't assume a package version - check with `pip show` or equivalent

### Documentation as Infrastructure
- The README is a **living operational document** for future agents and developers
- It's not just user-facing documentation - it's a knowledge base
- When adding functionality, update README as part of the same work
- Include maintenance reminders and "gotchas" for future developers

### Maintainability Focus
- Roger thinks about future maintenance:
  - "Can we add a reminder to update requirements.txt?"
  - Version specifiers with `>=` for dependencies
  - Clear documentation of optional vs required packages
- Consider: "What will trip up someone (human or AI) working on this in 6 months?"

### Markdown Backtick Conventions
When writing prompts or documentation for LLMs:
- **DO backtick:** Literal filenames (`project.md`), extensions (`.md`), field names (`"type"`), state values (`"waiting"`)
- **DON'T backtick:** Format patterns inside JSON examples (`YYYY-MM-DD` in `<YYYY-MM-DD ...>`)

### Judge prompts: reason BEFORE score (mandatory)

In any LLM judge prompt that asks for **both** a reasoning/explanation
field and a numeric (or categorical) decision, the reasoning **must
come first**.  Anything else makes the model commit to the score
before it has thought about it, turning the reason field into
post-hoc rationalization rather than a chain-of-thought aid.

This matters because we judge with **non-reasoning models** by default
(GPT-4.1-mini, Claude Haiku 4.5, Claude Sonnet's non-thinking mode).
Without explicit "think-on-the-page" framing, these models will skip
deliberation entirely.

**Two correct patterns** in this codebase:

1. **JSON output** — put the reason key first in both the schema
   description and any example, AND tell the model so explicitly:

   ```
   Respond with a JSON object only, no other text.  Reason about the
   response first, then commit to the score:
   {"reason": "<one short sentence>", "score": <0-3 integer>}
   ```

   Even though `json.loads()` is order-agnostic for parsing, LLMs
   tend to write fields in the order they're declared in the
   schema/example — so order matters for *generation*, not for
   parsing.  The explicit "reason first, then score" sentence is
   belt-and-suspenders against training-data conventions that lean
   toward `{"score": ..., "reason": ...}`.

2. **Free-form prefix + structured score** — used by
   ``results_analysis/axis_judge_correlation.py`` (the desc/instr/
   response judges):

   ```
   First, briefly reason about where this {entity} falls on the axis
   (2-3 sentences).  Then on a new line, write exactly:
   SCORE: <integer from -3 to +3>
   ```

   The parser looks for the `SCORE: <int>` token, not the first
   integer in the reply.

**The parser side** matters too: ``parse_judge_score`` in
``assistant_axis/judge.py`` looks for ``SCORE: <int>`` first, then
falls back to the LAST (not first) integer in the valid range.  A
naive "first integer wins" parser is hostile to reasoning text — a
response like "0 if no, 3 if full ... I rate this 2" would be parsed
as 0 by a first-integer parser, producing the wrong score whenever
the rubric definitions are echoed in the reasoning.

**Forbidden anti-pattern**:

```
# BAD -- forces commit-without-thinking
"Respond with a number between 0 and 3. Don't say anything else, just the number."

# BAD -- score field first means reason is rationalization
{"score": <0-3>, "reason": "..."}
```

**Where this is enforced**:

- ``assistant_axis/steering_judges.py`` — coherence, RP, effect rubrics
- ``pipeline/3_judge.py`` — TRAIT_EVAL_TEMPLATE, COMBINED_EVAL_TEMPLATE,
  and the per-role ``eval_prompt`` field of every
  ``data/roles/instructions/*.json``
- ``data/traits/instructions/*.json`` — per-trait ``eval_prompt`` field
- ``results_analysis/axis_judge_correlation.py`` — RUBRIC_STATIC,
  RUBRIC_RESPONSE_BATCH (uses the SCORE: marker pattern)
- ``data_analysis/{score_combinations,generate_antonyms,classify_goals}.py``
  — JSON output, reasoning-first
- ``data_analysis/regenerate_{role,trait}_instructions.py`` — the
  templates that emit ``eval_prompt`` text into role/trait JSON
  files; if you ever modify these, double-check the embedded
  example template inside the Christina instruction-generation
  prompt also follows the reasoning-first pattern (the LLM mimics
  what you show it as an example).

**When changing a judge rubric**: bump the corresponding
``*_RUBRIC_VERSION`` constant.  These are stamped into each judged
record for traceability; old records remain valid but are now
distinguishable from records produced under the new rubric.

### Judge parse-rate alerting (mandatory)

Every script that calls an LLM judge and parses structured output
**must** emit an end-of-run parse-rate summary, and that summary must
fire a loud warning if the OK rate drops below **99%** (i.e. ≥1%
UNPARSEABLE / API-failed / empty).  Why 99% and not something looser:

- At small N a 5% fail rate is hard to notice in the log noise but
  is enough to materially distort downstream aggregates.
- For ensemble judging, even 1% silently biases the mean toward
  whichever judge in the pair survives — an effect that doesn't
  show up in mean-of-means but does show up in per-(kind, model)
  scatter plots.  This rule was adopted May 2026 after the
  GPT-4.1-mini batched-effect run was found to have a 17–31%
  UNPARSEABLE rate that nobody noticed for several days.

**Default stance: <99% is a bug, not a budget.**  The norm for
this project is that *every* judge run should clear 99% parseable.
If a run trips the loud warning, that is a signal to **stop, catch
it, investigate, and fix** — typical root causes are prompt-format
drift (e.g. the model started emitting code fences), max-token
truncation, schema fragility (top-level lists, nested JSON), or a
specific model that's miscalibrated for the task (cf. GPT-4.1-mini
on batched effect judging in May 2026).  We may, on a *case-by-case*
basis, decide to accept a lower rate when no fix is available — but
that should be an explicit, documented decision (e.g. a comment on
the call site or a note in the run's results README), not silence.
The default reaction to ``*** HIGH FAIL RATE ***`` is to treat it
as a real problem that blocks downstream analysis until resolved.

**Use the central helper** at ``assistant_axis/judge.warn_if_low_parse_rate``:

```python
from assistant_axis.judge import warn_if_low_parse_rate

warn_if_low_parse_rate(
    label="my_script:claude-haiku-4-5-20251001",
    n_ok=n_parsed,        # parseable, in-range, non-empty
    n_total=n_attempted,  # all judge calls actually made
    logger_obj=logger,    # so the line shows up in your log file
)
```

Behaviour:

- 100% OK → single INFO line: ``[label] parse rate: N/N OK``
- ≥99% OK with some failures → INFO line with the percentage
- <99% OK → WARNING line prefixed with ``*** HIGH FAIL RATE ***``
- ``n_total == 0`` → no-op (don't pollute logs for empty runs)

The threshold lives in ``PARSE_RATE_LOUD_THRESHOLD`` if you ever
need to override it (you almost certainly don't — match the
project default unless you have a specific reason).

**Where it's wired today** (grep ``warn_if_low_parse_rate`` to find
new sites):

- ``pipeline/3_judge.py`` — aggregate across all entities
- ``results_analysis/axis_judge_correlation.py`` — per (mode,
  provider, model) at end of static and response sub-runs
- ``data_analysis/classify_goals.py`` — post-retry success rate
- ``data_analysis/score_combinations.py`` — post-retry success rate
- ``data_analysis/generate_antonyms.py`` — counts non-ERROR sentinels
- ``assistant_axis/steering_judges.py`` — uses an in-class tally
  (``RealJudgeDispatcher.judge_outcome_summary``) with the same
  threshold and ``*** HIGH FAIL RATE ***`` marker; promoted to
  WARNING level at ``shutdown()``.

**Single-shot scripts are exempt**: utilities that judge one axis
or one item at a time (e.g. ``results_analysis/infer_axis_description.py``,
``results_analysis/standardize_axis_spec.py``) don't get a parse-rate
tracker — N=1 makes the rate meaningless, and they already raise on
unrecoverable parse failure rather than silently dropping records.

### NFS-safe file I/O (mandatory for `/workspace` reads and writes)

`/workspace` on RunPod is a MooseFS-backed network mount. Direct file
ops are usable but occasionally flaky — partial copies, transient `EIO`,
slow flushes, and (most importantly) **silent short reads from
torch.load** that surface as `RuntimeError("storage has wrong byte
size of dtype ...")` or `RuntimeError("PytorchStreamReader failed
reading zip archive: ... unexpected EOF, expected N more bytes")`.
Both reads and writes need defensive handling.

**The pattern in this codebase:**

- **Writes**: stage to a local-disk temp file (via `TMPDIR`), copy to
  the destination with retry/backoff, then `os.replace` to atomically
  publish the final name, then unlink the temp.  Atomic from a reader's
  point of view: dest never exists in a half-written state.  Tensor
  saves additionally run **three post-copy integrity checks** before
  considering the save successful — any failure triggers another
  copy attempt:
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

**TMPDIR setup:** workers should call
`assistant_axis.tmpfs.setup_tmpdir_if_unset()` (or set `TMPDIR=/dev/shm`
manually before launch) so staging happens on RAM-backed tmpfs, not on
the small container `/tmp` (which can fill up under concurrent workers
writing 2.6 GB activation files).

**Auditing past damage**: `pipeline/scan_missing_vectors.py` walks an
`activations/`+`vectors/`+`scores/` triple and classifies each missing
vector as one of `mysterious` / `corrupt_or_truncated_activation` / `ok_zero_size`
(re-run candidates) vs `missing_scores` / `below_min_count` /
`all_nan_or_empty` (legitimate filter).  Use it to recover from
historical short-read damage that pre-retry step 4 silently skipped.

**Current call sites (keep this list updated as new ones land):**

- Writes via `atomic_io`: `pipeline/2_activations.py` (uses
  `torch_save_with_retry`), `pipeline/4_vectors.py`,
  `pipeline/5_axis.py`, `assistant_axis/steering_runner.py`,
  `steering/run_sweep.py`
- Reads via `atomic_io`: `pipeline/2_activations.py` (responses),
  `pipeline/4_vectors.py`, `pipeline/5_axis.py`,
  `assistant_axis/steering_runner.py`, `steering/run_sweep.py`,
  `assistant_axis/axis.py` (`load_axis`, `load_axis_with_metadata`,
  `load_role_vector` — used by notebooks too)

---

### Plot Provenance Metadata (mandatory for every plot)
Every plot generated in this repo MUST embed a PNG-text-chunk
provenance block via `assistant_axis.png_metadata`.  The contents
depend on whether the plot came from a tracked script or an ad-hoc
exploratory script.

#### Tracked-script plots

```python
from assistant_axis import png_metadata
fig.savefig(out_path, dpi=150, bbox_inches="tight",
            metadata=png_metadata(title=first_line_of_suptitle))
```

The helper auto-fills:
- `Title`         — pass the first line of the figure suptitle / caption
- `Author`        — defaults to "Roger Dearnaley"
- `Software`      — `uv run python <repo-relative path> <args>`, or
  `uv run python -m foo.bar.baz <args>` for `-m` invocations.  Pasteable
  into a shell at the repo root to re-run.
- `Creation Time` — local ISO-8601 timestamp
- `Source`        — git short SHA (+`+dirty` if working tree dirty)

#### Ad-hoc exploration plots (write the script to /tmp first)

When generating a plot during exploration, write the Python to
`/tmp/<descriptive_name>.py`, then run it.  Inside that script, embed
the source so the plot is self-contained:

```python
from pathlib import Path
from assistant_axis import png_metadata
fig.savefig(out_path, dpi=150, bbox_inches="tight",
            metadata=png_metadata(
                title=first_line_of_suptitle,
                source_text=Path(__file__).read_text(),
            ))
```

This adds:
- `Source Code`        — full body of the entry-point Python file
- `Source Code SHA256` — hex digest, for tamper detection

Recovery is one line:
```python
from PIL import Image
print(Image.open("plot.png").info["Source Code"])
```

For the rare multi-file case, pass `source_files={"main.py": ..., "helper.py": ...}`
instead — they're JSON-serialised into a single chunk plus a
`Source Code Files` index.  But: needing more than one `/tmp/` file is
itself a smell that the work is graduating to a tracked module; prefer
that path.

**Heredoc gotcha**: `uv run python << 'PY' ... PY` invocations cannot
read their own body via `__file__` — they're stdin, not a file.  When
producing a plot worth keeping, write the body to `/tmp/foo.py` first
rather than using a heredoc.

#### Conventions summary

1. **Tracked script** writes a plot → ALWAYS pass
   `metadata=png_metadata(title=...)`.  No `source_text` needed (the
   `Software` field plus the git SHA + tracked source already
   reproduce it).
2. **Ad-hoc `/tmp/foo.py` script** writes a plot → ALWAYS pass
   `metadata=png_metadata(title=..., source_text=Path(__file__).read_text())`.
3. **Inline heredoc** writes a plot → if it's interesting, refactor
   into a `/tmp/foo.py` first; if it's truly disposable, pass at
   minimum `metadata=png_metadata(title=...)` so we get the timestamp
   and git SHA.
4. **Inspect** any plot with `exiftool foo.png` or
   `PIL.Image.open(p).info`.

The helper lives at `assistant_axis/plot_metadata.py`.  PNG
`tEXt`/`iTXt` chunks support up to ~2 GB each — no realistic ceiling
on what we can embed.

#### Caveats

Embedded source captures the script that *called* `savefig`, plus the
git SHA at run time.  It does **not** capture:
- Versions of pip dependencies (use `uv.lock` for that — the SHA pins it).
- Repo files imported by the script (the SHA pins those if the tree was
  clean; otherwise `+dirty` warns you).
- Other on-disk inputs the script reads (datasets, JSON config files).

So embedded source is a strong but not complete archeological record:
it gives you the entry-point + the git tree-state + your Python env's
lockfile.  In a few months, that's almost always enough to reconstruct
a plot — and tells you exactly what's missing if it isn't.

---

### End-to-End Data Provenance (writers, readers, audits)

The plot-metadata block above tells you *who produced* a plot and
*how to reproduce* it.  The provenance system below tells you whether
the plot's *inputs are still current* — i.e., is the plot stale
because a dataset, judge cache, or upstream cache JSON has changed
since the plot was rendered?

This is implemented as four cooperating layers:

1. **Dataset manifests** (`MANIFEST.json` per dataset, generated by
   `tools/regenerate_dataset_manifest.py`) — subtree-granular
   `summary_sha256` over `(rel_path, mtime, size)` triples.  See
   `audits/post_pipeline_derived_layout.md` for the
   `derived/{marginals,aggregates,axis,legacy_centroid}` directory
   convention.
2. **`assistant_axis.provenance`** — `InputSpec` (one declared dep),
   plus helpers (`current_data_subtree_input`, `current_file_input`,
   `current_files_input`) that build versioned (`v1:...`)
   fingerprints.  `validate_recorded` / `load_validated_json` re-derive
   current state and compare.
3. **PNG + JSON envelope embedding** — `png_metadata(..., inputs=...)`
   adds an `Inputs` iTXt chunk; `json_metadata(payload, inputs=...)`
   wraps a JSON payload as `{"result": payload, "_provenance": {...}}`.
4. **Audit tools** — `tools/audit_pngs.py` walks PNGs, classifies
   current/stale/legacy/frozen; `tools/audit_caches.py` does the same
   for JSON caches *and* propagates stale-ness transitively along
   inter-cache file dependencies.

#### Writer pattern (mandatory for new analysis scripts)

Every analysis script that writes a JSON cache or a plot SHOULD
record its declared inputs.  The pattern:

```python
from assistant_axis import json_metadata, png_metadata
from assistant_axis.provenance import (
    InputSpec, current_data_subtree_input, current_file_input,
    current_files_input,
)

# 1. Build inputs list at the top of main(), after argparse:
inputs: list[InputSpec] = [
    current_data_subtree_input(
        data_dir, "traits/vectors", dep_key="traits_vectors",
        extras={"slot": str(args.slot), "layer": str(args.layer)}),
    current_data_subtree_input(
        data_dir, "roles/vectors", dep_key="roles_vectors"),
    current_file_input(
        dep_key="pairs_json", path=experiment_dir / args.pairs),
    current_files_input(
        dep_key="judge_caches", paths=judge_cache_paths,
        extras={"score_source": args.score_source}),
]

# 2. Wrap JSON output in the envelope:
envelope = json_metadata(records, inputs=inputs,
                         title=f"my_analysis slot={args.slot}")
out_path.write_text(json.dumps(envelope, indent=2))

# 3. Pass inputs to png_metadata for any PNG output:
fig.savefig(plot_path, dpi=150, bbox_inches="tight",
            metadata=png_metadata(title=title, inputs=inputs))
```

`dep_key` semantics: short, namespaced strings the writer chooses.
Used as the per-dep dict key by `validate_inputs`.  Don't reuse the
canonical "role" / "trait" terminology for these — those are entity
types; we use **dep_key** specifically to avoid that collision.

`InputSpec.kind` values: `"subtree"` (dataset directory tracked in a
`MANIFEST.json`), `"file"` (single file fingerprinted by
`v1:{mtime_iso}@{size}`), `"multi"` (composite of many files, e.g.
~130 per-axis judge caches, with `member_paths` recorded so a reader
can re-validate).

#### Reader pattern (`--cache-policy`)

When a script reads an upstream cache that was produced by a
provenance-aware writer, use `load_validated_json` and expose a
`--cache-policy` flag:

```python
from assistant_axis.provenance import CACHE_POLICIES, load_validated_json

p.add_argument("--cache-policy", choices=CACHE_POLICIES, default="warn",
               help="strict | warn (default) | rebuild | off")
args = p.parse_args()

records, check = load_validated_json(
    sweep_path, policy=args.cache_policy)
```

Policy semantics:

- **strict** — raise `StaleCacheError` on any drifted / missing /
  unverifiable input.  Use this when an automated pipeline must not
  silently consume stale data.
- **warn** (default) — print a drift summary to stderr, return the
  payload anyway.  Sane default for interactive work: you see drift
  immediately but aren't blocked.
- **rebuild** — if a `rebuild_callback` is wired in, call it (it
  should regenerate the cache), then re-validate.  Without a
  callback, behaves like strict.  No callbacks are wired in yet
  (Phase 4 stub); add one when an automated rebuild path makes
  sense.
- **off** — skip validation entirely.  Use only when you know what
  you're doing (e.g. reading a frozen historical cache for an
  archive plot).

Legacy bare-JSON caches without a `_provenance` envelope load
transparently as `(payload, None)` — readers don't need a code path
for the pre-migration shape.

`load_validated_json` also re-validates `kind="multi"` inputs by
re-stat'ing the recorded `member_paths`.  Pre-Phase-4 multi
InputSpecs (no `member_paths`) classify as `unverifiable` and trigger
strict failure; regenerate the cache to enable validation.

#### Audit tools

To check the freshness of everything in the repo at once:

```bash
# Are committed plots still fresh w.r.t. their declared inputs?
uv run python tools/audit_pngs.py --output reports/audit_pngs.md

# Are JSON caches fresh, including transitively through file deps?
uv run python tools/audit_caches.py --output reports/audit_caches.md

# Filter to just the stale ones (handy for "what do I need to rerun?"):
uv run python tools/audit_pngs.py --status stale
uv run python tools/audit_caches.py --status stale
```

Status taxonomy:

- **current** — all declared inputs match current state.
- **stale_direct** (caches) / **stale** (PNGs) — at least one input
  drifted/vanished/unverifiable.
- **stale_transitive** (caches only) — own deps are clean but an
  upstream cache (reachable via `kind="file"` deps) is stale.
- **legacy** — no provenance envelope (pre-migration, hand-written,
  or pipeline-produced like `MANIFEST.json` and judge caches).
- **frozen** (PNGs only) — explicit `Frozen` / `Frozen-At` chunk
  marking the artifact as intentionally pinned to historical data.
  Add via `png_metadata(..., extra={"Frozen": "snapshot-2026-04"})`
  in the producing script.

#### When to regenerate manifests

`MANIFEST.json` files live at each dataset root and are gitignored
(under `runpod_workspace/`).  Regenerate after any change to a
dataset's contents:

```bash
uv run python tools/regenerate_dataset_manifest.py \
    --dataset 'runpod_workspace/qwen/qwen-3-32b Roger 8slot'
```

Subtree-granular and stable: re-running on an unchanged dataset
produces a byte-identical `MANIFEST.json`.  Audit tools rely on this
to detect drift; ALWAYS regenerate after edits to the
`derived/{marginals,aggregates,axis,...}` directories produced by
`compute_combo_marginals.py` (the only post-pipeline producer in the
project).

### Combining desc/inst judge scores (use the canonical helper)

When reducing the four (judge × mode) judge scores
`{GPT_d, GPT_i, Son_d, Son_i}` to a single per-entity scalar, ALWAYS
use the canonical helper at `assistant_axis/judge_score_combine.py`
rather than rolling the formula inline.  The default is **inst-tiebreak
weighting** (`0.499*desc + 0.501*inst`), applied after averaging
across the two judges per mode:

```python
from assistant_axis.judge_score_combine import (
    combine_desc_inst_two_judges, add_di_weights_arg, parse_di_weights_arg,
)

# Default = inst-tiebreak (0.499 * desc + 0.501 * inst per entity).
scores = combine_desc_inst_two_judges(g_d, g_i, s_d, s_i)

# CLI integration (registers --di_weights with all 3 choices):
add_di_weights_arg(parser)
args = parser.parse_args()
weights = parse_di_weights_arg(args.di_weights)
scores = combine_desc_inst_two_judges(g_d, g_i, s_d, s_i, weights=weights)
```

**Why the asymmetry?** The 0.499/0.501 weights are essentially equal
but act as a tiebreaker for entities where desc and inst disagree,
leaning slightly toward instructions.  Empirically, at slot=(3,25) /
(0,26) / (0,49), inst-tiebreak gave consistently higher mean
activation→judge ρ than equal weighting (~+0.0005 ρ), and equal in
turn beat desc-tiebreak by a similar margin — the ordering is monotonic
across all (slot, layer) configurations tested.  This matches the
desc/inst judge audit that found instruction-mode judging more reliable
than description-mode (~99% defensible vs ~94%).

CLI override on any script using the helper:

```bash
--di_weights {inst_tie,equal,desc_tie}   # default: inst_tie
```

`equal` reproduces the historical 0.5/0.5 weighting (= 4-way mean of
the four scores). `desc_tie` is for ablation. The asymmetry only
affects entities where the two modes disagree, so the *direction* of
ρ comparisons remains essentially unchanged across the three weights;
the absolute ρ shift is in the third decimal.

**Anti-pattern**: don't compute the 4-way mean inline:

```python
# BAD -- defeats the convention; can't ablate; out of date if the
# default ever changes:
scores = {n: (g_d[n] + g_i[n] + s_d[n] + s_i[n]) / 4 for n in common}

# GOOD -- canonical, ablatable, future-proof:
from assistant_axis.judge_score_combine import combine_desc_inst_two_judges
scores = combine_desc_inst_two_judges(g_d, g_i, s_d, s_i)
```

Existing callsites: `results_analysis/{rho_by_slot_and_K, rho_by_layer,
whitening_k_sweep, gpt_sonnet_weight_sweep}.py`.

### Steering judges (Phase-2 architecture)

Steering sweeps use a **two-tier judging** protocol baked into
[`assistant_axis/steering_judges.py`](assistant_axis/steering_judges.py)
and consumed by [`assistant_axis/steering_runner.py`](assistant_axis/steering_runner.py)
via the `JudgeDispatcher` protocol:

1. **Coherence (synchronous, blocking)** — per-record `judge_coherence_blocking()`
   call after each generation batch.  0-3 rubric.  Default model
   `gpt-4.1-mini`; configurable via `--coherence-model`.  Gates the
   `should_stop_at(strength)` early-termination decision.
2. **Persona / RP (asynchronous, post-batch)** — gpt-4.1-mini, unbatched,
   matches `pipeline/3_judge.py`'s rubric augmented with steering-direction
   awareness.  0-3 rubric.
3. **Effect (asynchronous, batched)** — GPT+Haiku ensemble, batched at
   `target_batch_size=10` (matches response judging's default), strict
   single-(cell, sign, strength) batches.  `--effect-mode` selects
   bidirectional (one ±3 prompt) vs separate-poles (two 0-3 prompts,
   signed combine = pos.mean - neg.mean) vs both.

**Skip rule (cost optimization)**: tiers 2 and 3 are **skipped at the
(cell, sign, strength) granularity** when `mean(coh) > skip_threshold`
(default 1.0).  Filtering on the strength-mean rather than per-record
coh reflects that incoherence is a strength-level property whereas
judge noise is per-question; averaging the K coh scores cancels noise
without losing the gross signal.  Skipped records get
`judges.persona.skipped_due_to_strength_mean_coh = True` (and same for
effect); `strength_mean_coh` is stamped on every record regardless.

**Records schema** (`{cell_dir}/records.jsonl`):

```json
{
  "strength": 1.0, "sign": +1, "question_idx": 7, ...,
  "judges": {
    "coherence": {"score": 1, "reason": "...", "model": "...", "ts": ..., "rubric_version": 1},
    "strength_mean_coh": 0.7,
    "persona": {"score": 2, "model": "...", "skipped_due_to_strength_mean_coh": false, ...},
    "effect": {
      "mode": "bidirectional",
      "bidirectional": {"scores": {"<model_a>": {"score": 2, "reason": "..."},
                                    "<model_b>": {"score": 3, "reason": "..."},
                                    "mean": 2.5}},
      "combined": 2.5,
      "skipped_due_to_strength_mean_coh": false, ...
    }
  }
}
```

**CLIs**:

- [`steering/run_sweep.py`](steering/run_sweep.py) — live sweep with
  judging.  `--no-live-judging` falls back to `NoOpJudgeDispatcher`
  (no API calls; useful when iterating on generation alone).
  `--judges-only` skips generation entirely and delegates to
  `post_judge.py` for retrospective fill-in.
- [`steering/post_judge.py`](steering/post_judge.py) — retrospective
  RP/effect fill-in on an existing experiment dir.  Same skip rule;
  `--rerun-coherence-with-model` populates `judges.coherence_alts[<model>]`
  for the coherence-model shootout (preserves the live coherence
  field).
- [`assistant_axis/cherrypick.py`](assistant_axis/cherrypick.py) — walks
  one or more experiment dirs, applies a default filter
  (`strength_mean_coh<=1.0 AND persona>=2 AND |effect.combined|>=2`)
  or a Python-expression filter, prints a summary table and pretty
  spotlights for the top N by |effect.combined|.

**Cost characteristic**: coherence dominates the bill because it's
unfiltered (every record gets a call).  RP+effect are skipped on
incoherent strengths, so they're typically <30% of total spend.
gpt-4.1-mini default is ~5x cheaper than Sonnet on the unfiltered hot
path; rationale documented in
[`/Users/roger/.cursor/plans/steering_judges_phase2_a54a28b6.plan.md`](.cursor/plans/steering_judges_phase2_a54a28b6.plan.md).

**Known judging artifacts:**

- **Concise-direction RP underscoring**: When the concise/verbose axis
  (or any axis that produces very short responses) is steered toward
  brevity, the RP judge gives low persona scores (e.g. 1/3) even when
  the response content is perfectly in-character.  The judge simply
  can't find enough textual evidence of persona in a 3-8 word response.
  This is a measurement ceiling, not a real persona loss.  Expect
  similar artifacts from any axis that drastically reduces output
  length (e.g. terse/elaborate, laconic/expansive if those ever exist).

**Sigma-rescaling (deferred)**: effect scores are stored on the raw
±3 scale.  A separate downstream tool will eventually consume
`records[*].judges.effect.combined` and rescale to standard deviations
of the response-judging distribution.  The default
`response_target_batch_size=10` (in
[`results_analysis/axis_judge_correlation.py`](results_analysis/axis_judge_correlation.py))
matches the steering effect default so the two distributions are
apples-to-apples in the same judging regime.

### Whitening / soft-shear defaults

For analyses going forward, the project defaults are:

| regime | default | constant |
|---|---|---|
| **soft-K whitening** | **K=2** | `results_analysis.canonical_angles.whitening.DEFAULT_SOFT_K` |
| **soft-shear (top-L pooled)** | **L=2** | `results_analysis.canonical_angles.whitening.DEFAULT_SOFT_SHEAR_L` |
| **primary recommended whitening regime** | **`soft_shear=2`** | `results_analysis.canonical_angles.whitening.DEFAULT_WHITENING_SPEC` |

These were set in Apr 2026 after the LKM grid sweep on the 33 desc+inst
+ 12 response = 45-axis set with the inst-tiebreak weighting.  Prior
hardcoded default was K=3 (from older K-sweep parabola fit done before
soft-shear was in the toolbox).

Use the constants instead of literal integers in CLI defaults::

    from results_analysis.canonical_angles.whitening import DEFAULT_SOFT_K
    p.add_argument("--whiten_K", type=int, default=DEFAULT_SOFT_K)

When fitting:

```python
from results_analysis.canonical_angles.whitening import (
    DEFAULT_SOFT_K, DEFAULT_SOFT_SHEAR_L, fit_shear, fit_whitening,
)
from results_analysis.canonical_angles.data import build_goal_nogoal_subspaces

# Primary: soft-shear at L=2, fitted on combined r+t goal/no-goal subspaces.
A_g, A_n = build_goal_nogoal_subspaces(data_dir, slot, layer, kind="combined")
shear = fit_shear(A_g, A_n, L=DEFAULT_SOFT_SHEAR_L)
M_done = shear.apply(M_raw)

# Alternative when shear isn't available: soft-K whitening at K=2.
basis = fit_whitening("soft_K", pool, K=DEFAULT_SOFT_K)
M_done = basis.apply(M_raw)
```

**Caveats**:

- The optimum varies by (slot, layer): slot 3 prefers L=2 / K=0; slot 0
  prefers L=0..1 / K=2.  A single default can't be optimal everywhere.
  The L=2 choice is best at slot 3 (the canonical analysis point) and
  acceptable at slot 0 (~0.005 ρ behind the slot-0-specific optimum).
- The LKM grid was on 3 (slot, layer) configurations; broader sweeps
  may shift the optimum slightly.  Subject to revision -- if you find
  the optimum has moved, update the constants and re-document.

**Cache hygiene**: when changing these defaults, flush `rho_by_layer.json`
(the only auto-loading cache that interleaves K values across runs).
Per-axis `correlations.json` files are tied to specific
``--whiten_K`` invocations and should NOT be deleted -- they belong to
historical runs and re-running them is expensive.

---

### Tiered question subsampling for response judging (default May 2026)

`results_analysis.axis_judge_correlation --score_responses` now defaults
to **per-entity tiered subsampling** instead of "judge every response".
Three tiers, indexed by the dense response-pipeline `q_idx % M` (default
`M=3`):

| Tier | Filter | Fraction of canonical |
|---|---|---|
| 1 | `q_idx % 3 == 0`     | 1/3 |
| 2 | `q_idx % 3 in {0,1}` | 2/3 |
| 3 | (no filter)          | full |

Each entity falls back to a less aggressive tier only when RP filtering
has depleted it past these thresholds (with `N_default = 500` items in
the default persona's `responses/default.jsonl`):

* tier-1 count ≥ `N_default / 6` (≈ 83) → use tier 1
* else tier-2 count ≥ `2 * N_default / 9` (≈ 111) → use tier 2
* else → use tier 3

So full-roster entities pay ~1/3 of the cost of "no subsample" while
RP-heavy entities still get a stable sample (typical max ~170 items;
worst case ~2× the t1→t2 threshold ≈ 165).

**Knobs**:

* `--no_subsample` -- restore the pre-tiered default (judge everything).
* `--question_subsample_modulo N` (`>0`) -- legacy uniform mode (every
  entity filtered identically by `orig_id % N == 0`); keep using this
  when comparing aggregate ρ against historic q9 runs.
* `--tiered_modulo_per_chunk M` -- tier chunking granularity (default 3).

**Why q_idx, not orig_id**: the response pipeline uses `orig_id = 3 *
q_idx` (reduce=3 from the 300-question canonical), so `orig_id % 3 == 0`
is vacuously true and would not subsample. `q_idx` is dense (0..99) and
gives clean 1/3 / 2/3 / all chunks regardless of the canonical stride.

`AGENT_NOTES.md` and `correlations.json` files from earlier (uniform-q9
or no-subsample) runs are NOT backfilled; their results stay valid and
comparable within their own cohort.

---

## Response Patterns

### What Works Well

**Structured Analysis:**
```markdown
## Option A: Approach One
Pros: ...
Cons: ...

## Option B: Approach Two
Pros: ...
Cons: ...

## Recommendation: Option B
Why: ...
```

**Verification Steps:**
1. Check actual state
2. Report findings
3. Propose action
4. Execute after confirmation

**Implementation Flow:**
1. Acknowledge the request
2. Implement the changes
3. Verify results (lints, file contents)
4. Report completion with summary

**Handling Ambiguity:**
- When instructions are ambiguous, ASK for clarification
- If asking seems excessive, choose the option with the smaller blast radius
  - Example: "for review" unclear → provide list (easy to ignore) vs make changes (harder to undo)
  - Prefer reversible actions over irreversible ones when uncertain

### What to Avoid

**Don't:**
- Over-explain basic programming concepts
- Make assumptions about things such as versions, paths, or configurations without checking
- Separate project documentation (system behavior) from meta-documentation (working together)
- Create new .md documentation files (work summaries, etc.) without instructions or permission
  - In plan todos: "Document" implies creating a document file - use "Report" or "Verify" for communicating findings

**Do:**
- Be concise and information-dense
- Check actual state proactively
- Update README.md as part of feature work if needed
- Discuss trade-offs before implementing when choices are meaningful

### When Test Expectations Don't Match Code Behavior

**First: STOP and THINK HARD.** Don't reflexively "fix" either one.

**Then choose your path:**

**Path 1: Fix the Code (COMMON)**
- When you're very confident the expected results are correct and well-designed
- The implementation has a bug or misunderstood the spec
- This is the default assumption for tests written by Roger or derived from his specs

**Path 2: Adjust the Tests (RARE)**
- When you're very confident the code is correct and the expected results were poorly thought out
- Often happens when YOU wrote both the plan and discovered a design issue during implementation
- **REQUIRED:** When reporting your work, prominently flag that you changed expected results
- **REQUIRED:** Explain: what the discrepancy was, why you concluded tests were wrong, your reasoning
- This lets Roger verify your judgment call and catches if you were wrong

**Path 3: Ask Roger (ALWAYS SAFEST)**
- When you're not entirely certain which is correct
- Maybe Roger has a quick answer, maybe it needs discussion
- Better to get the right answer than enshrine a bug in both code and tests
- If you're on the fence between paths 1 and 2: choose this path

**Golden Rule:** Changing test expectations is always noteworthy. Even if you're certain it was right, Roger wants to hear about it in your summary.

---

## Prompt Engineering

### Writing Prompts for LLMs
When creating prompts that other LLMs will consume:
- **Context first:** Explain the "why" and broader goal before the "how"
  - Example: Added "Context" section explaining the prediction system goal
- **Acknowledge judgment calls explicitly:** Tell the LLM when decisions require judgment
  - Provide standards: "reasonable person", "preponderance of evidence"
  - Give examples of edge cases
- **Professional polish matters:** Clean prompts may prime LLMs for more careful work
- **Consistency in terminology:** Use backticks consistently, maintain parallel structure

### Multi-Pass Review for Prompts and Text
- When reviewing prompts or documentation (not code), expect multiple passes may be needed
- Each pass with fresh framing ("another pass", "anything we missed") can surface different issues
- Pattern: Typos → Clarity → Consistency → Edge cases
- This mirrors human proofreading where attention shifts with each read

---

## Documentation Context

### Multiple Audience Levels
- Human developers (Roger)
- Future AI agents
- Potentially other team members
- Documentation should serve all these audiences

---

## Session Initialization

### Recommended Starting Pattern
When starting a new session:
1. Read `README.md` for project context
2. Read `AGENT_NOTES.md` (this file) for collaboration patterns
3. Ask Roger what we're working on
4. Check relevant code/state before making assumptions

### Current canonical local data dir (May 2026)

The latest pipeline outputs live at:

```
runpod_workspace/qwen/qwen-3-32b Roger 8slot/
```

This is the **8-slot** rebuild that supersedes `runpod_workspace/qwen/qwen-3-32b Roger/` (the older 4-slot dir, vectors ~2.6 MB each). The 8-slot trait vectors are ~5.2 MB. The 8-slot dir contains the regenerated activations/scores/vectors for the 8 traits in the April–May 2026 trait-edits TODO list (`conformist`, `nonconformist`, `indecisive`, `anthropocentric`, `ecocentric`, `obedient`, `rebellious`, `unhelpful`) plus regenerated combinations.

When invoking analysis scripts that take `--data_dir`, prefer the 8slot path. The `results_analysis/run_axis_experiment_batch.py` default (`runpod_workspace/qwen/qwen-3-32b Roger`) is stale; pass `--data_dir 'runpod_workspace/qwen/qwen-3-32b Roger 8slot'` explicitly until that default is updated. The README examples likewise still reference the older directory.

### Mid-Session Patterns
- If unsure about working style: "Should I implement this directly or discuss options first?"
- If scope is unclear: "This affects X, Y, and Z - should I handle all of them?"
- If state is uncertain: Check it rather than assuming

---

## Examples from Past Interactions

### Good Interaction Pattern
```
Roger: "Check what's currently installed and update requirements.txt"
Agent: [Checks actual versions] → [Updates file] → [Shows results]
Roger: [Approves]
```

### Could Be Better
```
Roger: "Add version numbers to requirements.txt"
Agent: "I'll use version X.Y.Z which is reasonable for..."
Roger: "No, check what's actually installed"
```

Better approach:
```
Roger: "Add version numbers to requirements.txt"
Agent: [Checks installed versions] → [Updates with actual versions] → [Shows results]
```

---

## Adding New Trait Clean Pairs

When adding a new trait B that is the antonym of an existing trait A (e.g., adding `obedient` as the antonym of `rebellious`):

### Process

1. **Create seed file** in `data/traits/instructions/B.json` with `positive_label`, `description`, and `negative_label` set to `non-B` (NOT to A yet).

2. **Generate instructions** for B:
   ```bash
   uv run python data_analysis/regenerate_trait_instructions.py --traits B --force
   ```

3. **Run antonym generation** for B (and re-run for A to double-check):
   ```bash
   uv run python data_analysis/generate_antonyms.py --traits B A
   ```
   (`--traits` scopes to specific traits; omit for all.)
   This should independently discover A as B's antonym. If A's antonym generation also returns B, we have a **clean pair**: A↔B confirmed bidirectionally.

4. **Update negative_labels**: Set B's `negative_label` to A and A's to B in their instruction files.

5. **Regenerate instructions** for B with the proper antonym (the Roger prompt style injects the antonym into the neg instruction clause):
   ```bash
   uv run python data_analysis/regenerate_trait_instructions.py --traits B --force
   ```
   A should NOT need regeneration since it already has B as its negative_label.

6. **Add to `data/traits/trait_list.json`** with description.

7. **Run goal classification** if the trait needs goal scoring (for `data/goal_roles_and_traits.json`).

### Why non-X first?

Starting with `non-B` instead of `A` ensures the antonym generator discovers `A` independently from the neg instructions, rather than being primed by us providing it. This validates that the pos/neg instruction pairs genuinely capture the A↔B opposition.

### `data/goal_roles_and_traits.json` structure

Lists of roles and traits partitioned by goal content, for experimental use.
Each of `roles` and `traits` has `goal` (all-5 @ 2) and `non_goal` (all-5 @ 0) sublists.

**Ordering convention** -- items are randomized within tiers, tiers are concatenated:

- `roles.goal`: first 30 = primary set (varied), last 10 = cluster duplicates
- `roles.non_goal`: first 30 = most varied (max non-goal semantic spread), next 10 = nice-to-haves, last 30 = most redundant with first 30
- `traits.goal`: first 30 = max goal-space variation (less-HHH-default side of pairs, distinct ethical frameworks), next 10 = remaining moral circle spectrum, last 26 = default-side of pairs + redundant goal directions
- `traits.non_goal`: first 30 = max persona-property variation (less-default side of pairs), next 10 = nice-to-haves, last 17 = pair partners + redundant

### Clean pair validation results (April 2026)

After running the bidirectional antonym-discovery procedure on each candidate pair (script: `data_analysis/generate_antonyms.py`), 5 of the 6 originally proposed pairs validated as clean and the 6th was reorganized into a 3-trait conformity triangle.

| pair | bidirectional? | discovered antonyms | status |
|---|---|---|---|
| pragmatic ↔ idealistic | yes (mild near-synonym hedge) | pragmatic→idealistic; idealistic→pragmatic\|realistic | clean pair |
| conservative ↔ progressive | yes | →progressive ; →conservative | clean pair |
| ecocentric ↔ anthropocentric | yes | →anthropocentric ; →ecocentric | clean pair (descriptions rewrote in this session) |
| decisive ↔ indecisive | yes | →indecisive ; →decisive | clean pair (`indecisive` newly seeded) |
| obedient ↔ rebellious | yes (mild same-axis hedge) | obedient→rebellious\|defiant; rebellious→obedient\|compliant | clean pair (descriptions tightened to authority-axis-only) |

The 6th candidate (`conformist ↔ contrarian`) turned out to be a **3-trait triangle** rather than a clean pair, structurally analogous to the compassionate/malicious/callous triangle:

| trait | role | `negative_label` |
|---|---|---|
| conformist | engaged + aligned (central) | `non-conformist` (hyphenated seed marker) |
| contrarian | engaged + opposed (sibling) | `conformist` (partner reference) |
| nonconformist | disengaged (sibling, newly seeded) | `conformist` (partner reference) |

Convention: when a trait's true antonym is **structurally ambiguous** (the union of two siblings on different axes), its `negative_label` keeps the seed-marker form (`non-{positive_label}`) to flag the asymmetry. The two siblings each set `negative_label` to the central trait. This mirrors the compassionate/callous arrangement where compassionate.neg=`non-compassionate` and callous.neg=`compassionate` (engaged-vs-disengaged carves a clean partner pointer in one direction; the other direction is ambiguous between callous and malicious).

### TODO: regenerate activation/vector data after April–May 2026 trait edits

The trait-instruction edits across the April + early-May 2026 sessions require activation extraction and vector recomputation for **8 traits** (the others were either reverted to git-HEAD-equivalent or had only metadata changes that don't affect generation).

**New traits — no prior activations exist (April 2026):**

- `conformist`
- `nonconformist`
- `indecisive`

**Existing traits — instruction[]/description rewritten substantively, prior activations now stale:**

- `anthropocentric` (April 2026)
- `ecocentric` (April 2026)
- `obedient` (April 2026)
- `rebellious` (April 2026)
- `unhelpful` (May 2026 — rewrite from passive "indifferent / bare minimum" to active "refuses / deflects / makes excuses / does the bare minimum or less when forced". Motivation: `pharmacist_helpful_v1` and `chef_helpful_v1` steering experiments showed the old passive definition produced near-zero effect on the unhelpful pole because the resulting vector mostly captured "slightly less enthusiastic helpfulness", not actual unhelpfulness. Clean-pair check with `helpful` confirmed bidirectionally (score 4/4 each direction) before keeping the new definition.)

After regenerating activations + vectors for these 8, downstream artefacts that key on these traits (axis caches, response-mode score caches, plots that visualize these axes) should be inspected and rerun where they touch the affected traits. Combinations involving `unhelpful` (the 30 `t_*__unhelpful` set) also need full regeneration.

**Deliberately not regenerating:**

- `compassionate`: only `negative_label` changed (`callous` → `non-compassionate`), the description and instruction[] are unchanged. The negative_label is used only in the RP-filtering scoring step and forms a very small part of that prompt; the change is unlikely to materially shift filtering decisions.
- `callous`, `pragmatic`, `idealistic`, `conservative`, `progressive`, `decisive`, `contrarian`: byte-identical to git HEAD after this session's cleanup; existing activations remain valid.

### TODO: variant-specific K grids in the PC round-trip experiment (May 2026)

In `klm_sweep.py` and `permutation_null.py` we currently use a single
expanded K grid (`expanded_k_grid` = `DEFAULT_K_COARSE` ∪ `K-near-N`
neighbourhood with width ±4) for **all** ρ-search variants.  That's
appropriate for the `nth_pc` variant (which exhibits a sharp K=N spike
empirically), but is over-padded for the `fixed_direction` and
`fixed_principled` variants — those don't show K=N spike behaviour and
their winners cluster at small K (typically 0–8, rarely above ~32).

Hypothesis: for fixed_dir variants, a small low-resolution coarse grid
(e.g. `[1, 2, 3, 4, 6, 8, 12, 16, 24, 32]`) plus bracket-and-bisect
refinement would find essentially the same optima as the current
expanded grid, while cutting the search space substantially.  Lower
search bias → lower noise floor in the corresponding permutation null →
higher effective signal-to-noise for fixed_dir lines on the round-trip
plot.

Plan when ready:
1. Add a `variant`-aware `expanded_k_grid` (or two helpers) so that
   `nth_pc` keeps the K-near-N expansion and `fixed_direction` /
   `fixed_principled` use the smaller grid.
2. Add a `variant`-aware null in `permutation_null.py` so each variant
   has its own noise floor.  (Currently the null only computes nth_pc
   and over-states the floor for fixed_dir.)
3. Re-run the actual sweep + null and regenerate the plot.

Motivation evidence (2026-05-06): in the 3-cell sweep with ±4 K-near-N,
fixed_direction K winners across 14 PCs × 2 styles = 28 cells were
mostly K ∈ {0, 1, 2, 4, 8} with one outlier at K=512 (PC 192 glo,
suspected ρ-hacking on noise).  fixed_principled K winners were even
smaller — mostly K ∈ {0, 4, 7, 8, 13}.  Neither variant's K winners
needed the dense N±4 window.

### PC round-trip experiment: findings synthesis (May 2026)

**Goal.** Test how faithfully human-interpretable axes written for
canonical PCA directions (Opus describes the axis, GPT/Sonnet rank
entities along it) get geometrically recovered by an `(L, K, M)`
search over whitened PCs at various `(slot, layer)` cells.

**Setup recap.**

- *Canonical Nth PC* is defined in a fixed reference geometry: slot 3,
  layer 25, soft-shear `L=2`, PCA on standardized entity embeddings.
  Opus narrates that direction; the judge rubric is that description.
- `nth_pc` variant: at each cell `(slot, layer, L, K)`, recompute PCA
  on the post-shear/whitened entity matrix and take the index-N
  singular vector.  Direction is free to "float" with `(L, K)`; the
  empirical K-winner pattern clusters near `K≈N` (which is why the
  search grid is `DEFAULT_K_COARSE ∪ N±4`).
- `fixed_principled` variant: take α = `U_canonical[:, N-1] / σ_{N-1}`
  (the entity weights that define canonical PC N) and reapply those
  weights at the target cell's centred entity matrix.  The transported
  object is the same *linear combination of entities* across cells,
  modulo cell-local geometric drift.  At the canonical cell with
  `L=2, K=0` it reduces to the canonical direction; elsewhere it
  doesn't.  Naive `fixed_same` (reuse the raw ℝ^D vector) was
  abandoned because slot changes make it nearly orthogonal to the
  principled map.
- `permutation_null`: same search machinery on randomly permuted judge
  scores, giving the ρ that `(L, K)` optimisation reaches on noise.
  Currently computed only for the `nth_pc` variant; see the
  variant-specific-K-grids TODO above for why this is awkward to
  benchmark `fixed_principled` against.

**Core empirical read.**

The `nth_pc` winner-decomposition heatmap
(`roger/pc_round_trip_nth_pc_winner_decomposition.png`; built by
`results_analysis/pc_round_trip/{winner_decomposition,plot_winner_decomposition}.py`)
projects each `nth_pc` global winner direction back into canonical-L=2
shear space and expresses its squared mass on each canonical PC (rows
= target index N, columns = canonical PC index, row-normalised).

- For small N (roughly N ≲ 12), the heatmap is broadly diagonal: the
  recovered direction at index N really does live near canonical PC N.
- For larger N, the heatmap goes strongly off-diagonal: most squared
  mass concentrates on the first ~8 canonical PCs, regardless of which
  N was being searched for.  Spot-checks confirm the picture from the
  other side: individual low-index canonical PCs (e.g. PC 1, 2) have
  non-trivial Spearman ρ against high-N judge-score vectors.

**Interpretation.**

An Opus description of canonical PC N can be split into roughly:
*(a)* a PC-N-specific signal — what's actually distinctive about PC N
that ends up in the prose — and *(b)* generic top-PC scaffolding
(length, hedging, bluntness, stance loudness, "helpfulness
temperature", and other dominant features articulable in any axis
description) which is correlated with the high-variance early
canonical PCs and shows up in the judge rankings of *almost any*
labelled axis.  Add some noise.

The two ρ-measurement variants probe different mixtures of these:

| Variant | What it sees | Empirical caricature at high N |
|---|---|---|
| `nth_pc` ρ | (a) + (b); the search picks whichever latent best predicts judges. | Stays high but the heatmap shows the chosen direction loads on canonical PCs 1–8 — high ρ via canonical-PC aliasing, not genuine PC-N recovery. |
| `fixed_principled` ρ | Mostly (a): the direction is pinned to PC N's α-weights, only `(L, K)` varies. | Falls toward the noise floor sooner with N — measures whatever PC-N-specific content remains in the rankings once aliasing is denied. |

Neither is "the right ρ"; they answer different questions.
`fixed_principled` upper-bounds how much of PC N is genuinely
articulable in description-language; `nth_pc` upper-bounds what the
search procedure can recover from the same descriptions when allowed
to drift onto any latent that predicts judges.

**Regime heuristic (informal, continuity not proven).**

- N ≲ ~12: `nth_pc`, `fixed_principled`, the decomposition heatmap
  and the face-valid description content all agree.  Treat "the Nth
  PC" as a latent the description language can pick out.
- N ≳ ~12: `nth_pc` ρ alone is misleading; trust the `fixed_principled`
  trace, the decomposition, and the low-PC-vs-high-N-ranking
  cross-correlation as the sanity-check trio.

**Geometry side note.**

`results_analysis/pc_round_trip/principled_layer_transport.py`
compares naive vs principled cross-cell transport.  Layer ±1 at fixed
slot drifts modestly; changing slot at fixed layer drifts a lot.
Slot, not layer, dominates inter-cell direction drift, which is why
the principled (α-weight) transport matters once the cell set spans
multiple slots.

**Operational caveat tied to methodology.**

Until variant-specific K grids and nulls land (TODO above), the
permutation null in the round-trip plot reflects the `nth_pc` search
procedure's noise floor, not `fixed_principled`'s.  Compare
`fixed_principled` traces to *each other* and to canonical (no-opt)
ρ; treat the dashed null bands as an upper bound on noise rather than
a literal floor for `fixed_principled`.

**Plot status (2026-05-06).**
`results_analysis/pc_round_trip/plot_direction_cosines.py` was
restricted to `fixed_principled`-only after this synthesis: the
single-panel ρ figure shows canonical (×) plus `fixed_principled` ◆
traces for 1/2/3-cell aggregates with R/G/B colour-coding.  `nth_pc`
remains in the upstream `klm_sweep` cache and the heatmap script;
those tools are kept available for the diagnosis described above but
no longer drive the headline plot.

### Snapshot-before-invalidate principle (May 2026 lesson)

Whenever invalidating, wiping, or overwriting expensive-to-recreate data — most commonly judge-score caches, activation tensors, computed vectors, and response files — **make a timestamped copy first**, even if it feels "obviously fine to drop." The recreate cost is non-trivial:

- Judge caches: $50–$150+ per full rejudge round (gpt + sonnet + haiku across all axes)
- Activations: ~2.6 GB per role × 1 GPU-hour → tens of dollars + tmpfs hassle
- Response sets: minutes-to-hours of GPU time per pipeline run

Half an hour after a wipe, "I want to know how much things actually changed" is a very common follow-up question (Spearman rho between old and new judge scores per entity, for instance). Without a snapshot, the answer is "we can't compute that anymore."

**Cheap mitigations, in roughly increasing thoroughness:**

1. `cp -a <file_or_dir> <file_or_dir>.bak.YYYYMMDD_HHMMSS` next to the original. Trivially deletable when no longer needed.
2. Stage the originals into `/tmp/<session-id>/...` before the in-place modification — survives a chat session but auto-cleaned by macOS at boot.
3. For really expensive data: `rsync -a` into an offline backup directory (e.g. `~/Documents/assistant-axis-backups/<date>/`), or move to `~/.Trash` instead of deleting (the macOS Trash retains files until you explicitly empty it, so a wipe is recoverable for days/weeks if you change your mind).

**Agent rule:** when about to run an invalidation/wipe/overwrite of expensive cache data, **bring this up before doing it** — propose a snapshot scheme, even briefly. It costs ~one tool call and saves the "ah, well" moment later. (This is the same instinct as `git stash` before a destructive rebase.)

### Combined response generation (pipeline)

The pipeline (`pipeline/1_generate.py`) supports two modes:

**Roger mode** (default): Generates combined role+trait instructions, standalone traits, and the default baseline. Uses `data/goal_roles_and_traits.json` to pick the top-N roles/traits from each goal/non-goal list.

- `r_{role}__{trait}` = goal role x non-goal trait (goal from role)
- `t_{role}__{trait}` = non-goal role x goal trait (goal from trait)
- Double underscore `__` separates role and trait in filenames
- Instructions are index-matched (pair 0-0, 1-1, ..., 4-4), concatenated with `\n`
- `--goal_count` / `--non_goal_count` (default 30 each) control how many items from each list; error only if a count exceeds BOTH lists it applies to

**Christina mode**: Processes standalone roles (or traits) from `--roles_dir`. Run separately per entity type (different `--roles_dir` and `--output_dir`) to avoid name collisions.

**Step 3 eval_prompt routing**: The judge (`3_judge.py`) requires an explicit `--entity_type {role,trait,combination}` flag to select the eval_prompt:

- `role` — look up stem in `data/roles/instructions/`, use its `eval_prompt` field.
- `trait` — look up stem in `data/traits/instructions/`, build a pipeline-specific 0-3 eval_prompt from the description. (The 0-100 `eval_prompt` in trait JSONs is NOT used by the pipeline, since `parse_judge_score()` rejects scores > 3.)
- `combination` — parse `r_<role>_t_<trait>` filename, build a compound 0-3 eval_prompt from both descriptions.

`default` is skipped under all entity types (step 4 uses all activations without scores).

**DO NOT try to autodetect entity type from the filename.** 9 names exist in both `data/roles/instructions/` and `data/traits/instructions/`:

    ascetic, contrarian, cosmopolitan, generalist, pacifist,
    patient, perfectionist, romantic, stoic

Any roles-first (or traits-first) fallback will silently mis-score one side for these 9. `run_pipeline.sh` passes the correct `--entity_type` per output-subdir type (Roger mode: `roles|traits|combinations`; Christina mode: inferred from `ROLES_DIR`). If you add a new standalone invocation of `3_judge.py`, you must pass `--entity_type` explicitly.

Steps 2, 4, 5 are unchanged — they process whatever files appear in their input directories.

---

## Updates and Evolution

This document should evolve as we discover new patterns. When something doesn't work smoothly:
1. Reflect on what caused friction
2. Determine if it's a pattern vs one-off situation
3. Update this document if it's a pattern
4. Keep it concise - remove outdated patterns

**Last Updated:** May 6, 2026

---

## Quick Reference

**Roger's Style in 4 Words:** Pragmatic, verify-then-trust, documentation-conscious, technically-sophisticated

**Golden Rules:**
1. Check actual state, don't assume
2. Be concise but complete
3. Documentation is infrastructure
4. Discuss trade-offs, then execute decisively

