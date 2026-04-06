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

### Current clean pairs added (April 2026)

| New trait (B) | Expected antonym (A) | Confirmed? |
|---|---|---|
| obedient | rebellious | pending |
| pragmatic | idealistic | pending |
| conservative | progressive | pending |
| compassionate | callous | pending |
| conformist | contrarian | pending |
| ecocentric | anthropocentric | pending |

### Combined response generation (pipeline)

The pipeline (`pipeline/1_generate.py`) supports two modes:

**Roger mode** (default): Generates combined role+trait instructions, standalone traits, and the default baseline. Uses `data/goal_roles_and_traits.json` to pick the top-N roles/traits from each goal/non-goal list.

- `r_{role}__{trait}` = goal role x non-goal trait (goal from role)
- `t_{role}__{trait}` = non-goal role x goal trait (goal from trait)
- Double underscore `__` separates role and trait in filenames
- Instructions are index-matched (pair 0-0, 1-1, ..., 4-4), concatenated with `\n`
- `--goal_count` / `--non_goal_count` (default 30 each) control how many items from each list; error only if a count exceeds BOTH lists it applies to

**Christina mode**: Processes standalone roles (or traits) from `--roles_dir`. Run separately per entity type (different `--roles_dir` and `--output_dir`) to avoid name collisions.

**Step 3 eval_prompt routing**: The judge (`3_judge.py`) detects response type by filename prefix. Combined entries get a compound 0-3 eval_prompt constructed from both descriptions. Standalone traits get a pipeline-specific 0-3 eval_prompt (the 0-100 eval_prompt in trait JSONs is NOT used by the pipeline, since `parse_judge_score()` rejects scores > 3). Standalone roles use their existing `eval_prompt` from the JSON file. `default` is skipped (step 4 uses all activations without scores).

Steps 2, 4, 5 are unchanged — they process whatever files appear in their input directories.

---

## Updates and Evolution

This document should evolve as we discover new patterns. When something doesn't work smoothly:
1. Reflect on what caused friction
2. Determine if it's a pattern vs one-off situation
3. Update this document if it's a pattern
4. Keep it concise - remove outdated patterns

**Last Updated:** April 5, 2026

---

## Quick Reference

**Roger's Style in 4 Words:** Pragmatic, verify-then-trust, documentation-conscious, technically-sophisticated

**Golden Rules:**
1. Check actual state, don't assume
2. Be concise but complete
3. Documentation is infrastructure
4. Discuss trade-offs, then execute decisively

