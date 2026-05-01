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
  saves additionally **verify the destination file size byte-for-byte
  against the staging file** before considering the save successful —
  silent NFS short-writes (which previously produced the 5 MB truncated
  `r_guardian__casual.pt`) now raise an `OSError` and trigger the
  retry loop.
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
vector as one of `mysterious` / `truncated_activation` / `ok_zero_size`
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

### TODO: regenerate activation/vector data after April 2026 trait edits

The trait-instruction edits in this session require activation extraction and vector recomputation for **7 traits** (the others were either reverted to git-HEAD-equivalent or had only metadata changes that don't affect generation).

**New traits — no prior activations exist:**

- `conformist`
- `nonconformist`
- `indecisive`

**Existing traits — instruction[]/description rewritten substantively, prior activations now stale:**

- `anthropocentric`
- `ecocentric`
- `obedient`
- `rebellious`

After regenerating activations + vectors for these 7, downstream artefacts that key on these traits (axis caches, response-mode score caches, plots that visualize these axes) should be inspected and rerun where they touch the affected traits.

**Deliberately not regenerating:**

- `compassionate`: only `negative_label` changed (`callous` → `non-compassionate`), the description and instruction[] are unchanged. The negative_label is used only in the RP-filtering scoring step and forms a very small part of that prompt; the change is unlikely to materially shift filtering decisions.
- `callous`, `pragmatic`, `idealistic`, `conservative`, `progressive`, `decisive`, `contrarian`: byte-identical to git HEAD after this session's cleanup; existing activations remain valid.

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

**Last Updated:** April 4, 2026

---

## Quick Reference

**Roger's Style in 4 Words:** Pragmatic, verify-then-trust, documentation-conscious, technically-sophisticated

**Golden Rules:**
1. Check actual state, don't assume
2. Be concise but complete
3. Documentation is infrastructure
4. Discuss trade-offs, then execute decisively

