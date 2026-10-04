# Coding plan: the overlap rubric arms experiment (2026-10-04)

Brief for the Opus coding agent, from Fable, on Roger's go ("OK, go gather data").  Read
[m3_overlap_test_readout.md](./m3_overlap_test_readout.md) ("Fable through the API, and the six-way
chart" and the paragraphs after it) for what the experiment is for; this file says what to build.

## Why

The overlap test ([overlap_test.py](../../assistant_axis/gapgen/overlap_test.py), CLI
[data_analysis/gap_generation/overlap_test.py](../../data_analysis/gap_generation/overlap_test.py), run
[overlap_test_1](../../data/candidates/overlap_test/overlap_test_1/)) showed that the large models
agree with each other on rubric A about as often as each agrees with itself when it sees the same pair
twice (about 85%), and that the disagreement sits on two boundaries of the 0-4 scale: 1 / 2 (harmless
for the decision) and 2 / 3 (the cut-off).  At 2 / 3 the models see the shape of the pair alike (one
trait adds something, the other only shifts emphasis) and round it to a number differently, because the
rubric's 3 ("differing only in scope, degree or emphasis") and 2 ("each adds something the other lacks")
both fit a one-sided addition.  Roger asked whether another step in the 1-3 range would make the
judgement easier.  We test that, and two alternatives, on the same 409 pairs.

## The arms

All arms share rubric A's text except for the scale lines (and, for arm D, the answer key).  The rubric
texts below are final: do not reword them; render them as the model will see them
([AGENT_NOTES.md](../../AGENT_NOTES.md), "Read the rendered prompt, not the template") and fix only
mechanical faults (a typo, a broken JSON example), recording any fix in the file's change log.

| arm | key | file (new, in [rubrics/](./rubrics/)) | what changes |
|---|---|---|---|
| 0 | `A` | [overlap_concept.md](./rubrics/overlap_concept.md), as pinned (version 4) | nothing: the baseline, run again |
| 1 | `C` | `overlap_six.md` | six rungs, 0-5: the 2-3 region split by who adds something |
| 2 | `D` | `overlap_relation.md` | the kind of relationship is named, with direction; the score is derived |
| 3 | `E` | `overlap_scope.md` | Roger's rewrite of line 3 only, and the reason says which kind of difference |

Rubric B ([overlap_cooccurrence.md](./rubrics/overlap_cooccurrence.md)) is not in this experiment.

### Arm C, `overlap_six.md`: the scale lines replace rubric A's six scale lines; everything else is A's text

```
Give one of these answers for each listed trait:
- 5: the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- 4: the same concept, differing only in degree, strength or emphasis; neither adds anything the other lacks. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further.
- 3: one contains the other: one of the two is the other narrowed to a single domain, or the other with something more added to it, and the narrower or plainer one adds nothing of its own. For example, fussy and fussy eater: the same fussiness, narrowed to food.
- 2: overlapping concepts. They share a core, but each adds something the other lacks. For example, studious and bookish: both are about learning from books, but studious adds diligence and bookish adds a taste for reading.
- 1: related but distinct concepts: neighbours, not the same concept. For example, tetchy and sullen: both are bad-tempered, but quick irritation is a different thing from silent resentment.
- 0: different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "opposite": the listed trait is the reverse of the target, the same quality at the other end. For example, cheery and morose.
- "unsure": you cannot tell from the two descriptions.
```

The answer format is A's with `0|1|2|3|4|5`.  Mapping to the decision scale: 5 -> 4, 4 -> 3, 3 -> 3,
2 -> 2, 1 -> 1, 0 -> 0.

### Arm D, `overlap_relation.md`: the opening question, the scale lines and the answer format change

Opening sentence (replaces A's first sentence's last clause): "... For each listed trait, say how its
concept is related to the target's."  Then A's second paragraph unchanged, then:

```
Give one of these answers for each listed trait:
- "same": the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- "variant": the same concept, differing only in degree, strength or emphasis; neither adds anything the other lacks. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further.
- "contains": one of the two is the other narrowed to a single domain, or the other with something more added to it, and the narrower or plainer one adds nothing of its own. Say which is the wider one. For example, fussy and fussy eater: fussy is the wider.
- "overlap": overlapping concepts. They share a core, but each adds something the other lacks. For example, studious and bookish: both are about learning from books, but studious adds diligence and bookish adds a taste for reading.
- "neighbours": related but distinct concepts: neighbours, not the same concept. For example, tetchy and sullen: both are bad-tempered, but quick irritation is a different thing from silent resentment.
- "different": different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "opposite": the listed trait is the reverse of the target, the same quality at the other end. For example, cheery and morose.
- "unsure": you cannot tell from the two descriptions.

For each listed trait give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed trait's id>, "reason": "<one short sentence>", "relation": "same"|"variant"|"contains"|"overlap"|"neighbours"|"different"|"opposite"|"unsure", "wider": "target"|"listed"}]}
Give "wider" only when the relation is "contains". Return one row per listed trait, in the order given.
```

Mapping to the decision scale: same -> 4, variant -> 3, contains -> 3, overlap -> 2, neighbours -> 1,
different -> 0, opposite -> opposite, unsure -> unsure.  Record `wider` on the result row; a `contains`
without `wider` parses, with `wider` null and a parse note.

### Arm E, `overlap_scope.md`: A's text with line 3 replaced by Roger's wording

```
- 3: the same concept, differing only in scope, degree, strength or emphasis. One may be the other narrowed to a single domain, or broadened beyond it; a stronger or a milder form of it; or the same thing with the stress elsewhere. What the wider or stronger one adds is more of the same, not something new. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further. Or fussy and fussy eater: the same fussiness, narrowed to food. In the reason, say which: narrowed, broadened, stronger, milder, or a shift of emphasis.
```

Decision scale: A's own.

### Example words

Example words in a rubric must not be corpus labels (the hygiene test in
[test_gapgen_split_rubrics.py](../../assistant_axis/tests/test_gapgen_split_rubrics.py), `OVERLAP_EXAMPLE_WORDS`);
fussy and fussy eater were checked free on 2026-10-04 (picky eater is the corpus's; fussy eater is its
near-duplicate, which the rule wants).  Add the new words to the test's list.

## The data design

- The pairs: the 409 pairs of `overlap_test_1`, built the same way (same seed and inputs give the same
  pairs; the run refuses to start if they differ, as `--resume` does today).  New run id
  `overlap_arms_1` under `data/candidates/overlap_test/`.
- Models: Sonnet 5.5 and Opus 5.5 (`--models claude-sonnet-5-5 claude-opus-5-5`).  Not Haiku, not Fable.
- **Two passes per arm and model.**  Pass 2 sends the same calls (same target, same listed traits) with
  the listed traits in a fresh random order (a different shuffle seed per pass, derived from the run
  seed and the pass number), so every pair is judged twice by every model under every arm and
  self-consistency is measured on all 409 pairs.  Records carry `pass`; a call's key is
  (rubric, model, call_id, pass); `--resume` works per key.  The CLI flag: `--passes 2` (default 1, so
  nothing changes for the old runs).  The answers of both passes are kept; pass 1 is "the" answer where
  one is needed (the existing tables), and the new analysis compares the passes.
- Arm 0 is re-run in full (both passes), not imported from `overlap_test_1`: every arm then has the
  same conditions and the same day.  Comparing arm 0 pass 1 with run 1 is a third consistency reading
  for free, in the analysis.
- Cost: about $0.64 (Sonnet) and $1.24 (Opus) per arm and pass, so about $15 for the four arms.  Budget
  cap `--budget-usd 20`.  Under the $20 line, so no confirmation is needed, but tell Fable in your
  report what was spent; the estimate printed by the dry run must be under $20 before the live run.

## What to build

1. **Rubric variants in the harness.**  `RUBRICS` in `overlap_test.py` gains `C`, `D`, `E` with the
   per-rubric facts the code needs: file, name, answer key (`similarity` / `relation`), the numeric
   scale (0-4 or 0-5, or none for `D`), the categorical answers, the extra key (`wider`, `D` only), and
   the mapping to the decision scale (a function `decision_value(rubric, value)`).  Everything that
   assumed `SCALE = 0..4` and the key `similarity` (the parser, `answer_value`, `scale_lines`, the
   estimate's output tokens, the analysis, the tables) reads the rubric's facts instead.  Rubric B keeps
   working unchanged.  The pins: `split_rubrics.OVERLAP_FILES` gains the three files; first pins are
   version 1 (`rubric_pins.py bump <name> --version 1 --why '...'`).
2. **Passes**, as above.  `render_user(call, corpus, order_seed=...)`; the record's `request.user` is
   what was sent, as now.  `latest_records`, `first_records`, `done_keys`, `collect_answers` and
   `first_attempt_parse` key by pass.
3. **Analysis**, in `summary.json` and `tables.md`, per arm and model:
   - self-consistency between the passes: exact, within one (native scale), and on the decision scale;
     and the boundary each flip crosses (counts by adjacent pair of values);
   - Sonnet against Opus, per pass, native and decision scale (the existing `agreement`);
   - the known groups (existing `group_stats`) on the decision scale;
   - at cut-off 3 on the decision scale, nearest pairs: the share covered; pairs where the two
     models fall on different sides; pairs where the two passes of one model fall on different sides;
   - for `D`: counts of each relation, `wider` by direction, and how often `wider` is missing;
   - for `E`: a count of which kind the reason names on 3s (a word search is fine: narrowed /
     broadened / stronger / milder / emphasis; report the share naming none);
   - arm 0 pass 1 against `overlap_test_1`'s rubric-A answers, same statistics as a pass-to-pass
     comparison (read run 1's `responses.jsonl` by path; do not modify run 1).
   A section per arm in `tables.md`, and one cross-arm table: arm, model, consistency (exact), Sonnet-
   Opus agreement, covered share at cut-off 3, between-model crossings, between-pass flips.
4. **CLI**: `--rubrics` accepts `C D E`; `--passes`; the dry run prints one rendered prompt per arm
   (the existing `rendered_prompts.md` logic, per rubric); `--analyse-only` recomputes everything from
   the records.
5. **Tests** for each of 1-4 with the fake client (`assistant_axis/tests/fake_anthropic.py`): parsing
   of each arm's answers including `wider`, the mappings, two passes giving distinct keys and both
   answers kept, the consistency statistics on made-up answers, the CLI end to end for `--rubrics C D E
   --passes 2`.  The existing tests keep passing (do not change an expectation without saying why in
   your report; see AGENT_NOTES "When Test Expectations Don't Match Code Behavior").

## Running it

1. Dry run: `uv run python data_analysis/gap_generation/overlap_test.py --run-id overlap_arms_1
   --models claude-sonnet-5-5 claude-opus-5-5 --rubrics A C D E --passes 2 --budget-usd 20 --dry-run`.
   Read the rendered prompts for every arm as the model will see them; check the estimate.
2. Live, the same without `--dry-run`, in the foreground with a Bash timeout of 600000 ms (each arm is
   about 720 calls, three to five minutes at concurrency 8); if the tool's limit cuts it, run again with
   `--resume`.  If a stage stops on the parse-rate guard, read the failed answers before anything
   else and report; do not loosen the guard.
3. `--analyse-only` is free; use it while fixing the analysis.

## Report back

Commit at checkpoints on this branch (`worktree-agent-a49beca76adafdfc1`), one purpose per commit,
messages ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; never push.  When done,
report: the commits; the cross-arm table and the per-arm sections (quote the numbers, do not make Fable
open files); anything surprising in the rendered prompts or the answers; spend; and any test
expectation you changed, with the reason.  Do not write the readout for Roger; Fable does that.

## Constraints that apply to every command

- **Files**: read, write and search only inside this repository
  (`/Users/roger/Documents/GitHub/assistant-axis/`, this worktree included), `$TMPDIR` and the session
  scratchpad.  Nothing else on the machine, not to "check what is installed", not read-only.  If
  something seems to need a path outside, stop and say so in your report.
- **Bash is sandboxed**: `ps` and `pgrep` fail; `kill -0 <pid>` on another command's job says
  "operation not permitted" while the job is alive and "no such process" only when it has ended;
  temporary files go under `$TMPDIR`; `.claude/hooks`, `.claude/skills`, the settings files and
  `~/.claude/projects` cannot be written from the shell (use the Edit and Write tools; you should not
  need them).
- Open source files with the **Read tool** before editing (the repository's rules load that way);
  edit with Edit and Write, not with shell rewrites; one purpose per shell command; never repeat a
  command that was refused.
- Run tests as separate invocations: `uv run pytest -q assistant_axis/tests data_analysis/tests`; a
  bare `pytest` at the root collides with the mirror under `runpod_workspace/`.
- `.env` is in place in this worktree; never read or print it.  Models are reached directly through the
  Anthropic SDK, as the harness does.
