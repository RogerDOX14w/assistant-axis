# Coding plan: M3, the novelty check (2026-10-07)

Brief for the Opus coding agent, from Fable, on Roger's go.  M3 decides, for each candidate trait that
passed the M1 filter, whether the corpus already has it.  The design is settled in
[coding_plan_platform.md](./coding_plan_platform.md): the section "M2 final settings and the M3 design"
(items 1-9) and the section "M3 overlap call: decisions after the rubric test" (decisions 1-11, the
later ones overriding the earlier where they differ).  Read both, then the readouts they cite
([m3_overlap_test_readout.md](./m3_overlap_test_readout.md),
[m3_overlap_arms_readout.md](./m3_overlap_arms_readout.md)) for the measurements behind them.  This
file says what to build, in what order, and what the pilot is.  Where it and the platform plan
disagree, this file wins; say so in your report if you find such a case.

## The pipeline, per candidate

A candidate is a registry row ([registry.py](../../assistant_axis/gapgen/registry.py); the row and its
vocabularies are the frozen interface in the platform plan) whose M1 filter block has the verdict
`trait`.  M1 gives it a stem and label, a gloss in the corpus form ("This means ..."), an alignment
score 0-3 and a region.  M3 adds a `novelty` block.  Stages:

0. **Exact-label check** (no model).  The normalised label (`normalize_to_file_name`) equal to a corpus
   stem, a queued stem (`data/seed_queue.json`), or a corpus file's `renamed_from`: decision
   `covered`, `covered_by` that stem, reason `exact_label`, no calls.
1. **Retrieve.**  Embed the candidate's label plus gloss in the covered setting of
   [metric_config.json](../../data/candidates/metric_config.json) (OpenAI `text-embedding-3-large`,
   direct key, `w20`, centred, cosine; the corpus side from the existing embedding cache of the M2
   work, see [embed.py](../../assistant_axis/gapgen/embed.py), [space.py](../../assistant_axis/gapgen/space.py),
   [representation.py](../../assistant_axis/gapgen/representation.py)); take the 10 nearest corpus
   traits with their cosines.
2. **Expand arrangements** ([arrangements.py](../../assistant_axis/arrangements.py)).  For every
   retrieved trait in a recorded pair, triangle or tetrahedron, add the other members (sequences,
   rings, maps and sets do not expand), each with its own cosine to the candidate.  Keep, on each
   listed trait, its recorded partner(s), for the "opposite" rule below; the model never sees them.
3. **Relation call** (Haiku 4.5; one call per candidate, all listed traits in it, in random order,
   labels in display form, no cosines, no ranks, no partner marks).  For each listed trait: `similar`,
   `opposed`, `unrelated` or `unsure`.  The rubric is draft 1 below, a new file
   [rubrics/relation.md](./rubrics/relation.md), pinned as version 1 before any paid call; render the
   prompt with a real candidate and read it before sending anything.  `unsure` answers are asked again
   of Sonnet 5.5 for those traits only (one call, the unsure traits listed).  Outputs:
   - the **shortlist**: the traits marked `similar`, ordered by cosine, highest first;
   - the **pair check** (design item 4): for a listed pair, one side `similar` and the other
     `opposed` is the expected shape; both `similar` or both `opposed` is recorded as a flag
     (`pair_flag`) on the row, nothing else;
   - **opposed traits**: for each, if it has a recorded partner, the partner goes to the front of the
     shortlist (added if the relation call did not mark it similar); if it has none (`negative_label`
     a `non-X` placeholder, or a one-way pointer), the row records `pair_completion_for: <stem>`
     (design item 4: a find, not a drop).
   The purpose of this pass is to find the opposites and to keep the overlap call short; the pilot
   measures what it costs in recall (below).
4. **Overlap call** (Sonnet 5.5 first; rubric A, [rubrics/overlap_concept.md](./rubrics/overlap_concept.md),
   **as pinned when the run starts** (version 6, or its successor after Roger's pass; the run records
   the version and hash); one pair per call, the user turn byte for byte as the rubric file's rendered
   sample, the system prompt cached, as `overlap_arms_3` sent it: reuse `render_single`,
   `parse_single` and the cached call path of [overlap_test.py](../../assistant_axis/gapgen/overlap_test.py)
   rather than writing new ones, moving them to a shared module if that is cleaner).  Walk the
   shortlist in order; stop at the first `covered`.  With c the cut-off for this candidate (alignment
   score 0 or 1: c = 3; 2 or 3: c = 4; design item 6, decision 4):
   - Sonnet above c: `covered` by that trait, directly.
   - Sonnet = c: Opus 5.5 reads the same pair (same rubric, same form, cached); Opus at c or above:
     `covered`; under: continue.
   - Sonnet = c - 1: Opus reads the pair as well; **the candidate is not cut whatever Opus says**
     (decision 11); if Opus reads c or above, the row gets `review: "sonnet_below_opus_at"` with both
     readings; continue.
   - Sonnet below c - 1: continue.
   - Sonnet `opposite`: taken as it stands, no Opus (decision 9).  If the trait has a recorded partner
     and the partner has not been judged yet, judge it next; if it has none, record
     `pair_completion_for` as in stage 3; then continue down the list (Roger, 2026-10-07).
   - Sonnet `unsure`: Opus reads, and its answer is used as if it were Sonnet's.
   - An answer that fails to parse is asked again once (as the harness does); a second failure is
     recorded and the pair skipped, with the row marked `review: "unparsed"`.
   The shortlist exhausted without a `covered`: decision `new`.
5. **Decision and record.**  `decision`: `covered` (with `covered_by`, the stem; the readings that
   decided it), `new`, or `grey` = kept but carrying a review flag (`sonnet_below_opus_at`,
   `unparsed`, `pair_flag`), so that `review_order` lists it.  The `novelty` block on the row holds:
   `run_id`, `decision`, `covered_by`, `review`, `pair_completion_for`, `cut_off`, `alignment_score`,
   every reading in order (`stem`, `cosine`, `relation`, `sonnet`, `opus`, both reasons), the
   rubric names, versions and hashes, `config_version`, and the usage of the row's calls.  Writes go
   through the `Registry` API, idempotent per (run_id, key); a candidate already decided in the same
   run is skipped on resume.
6. **By-products.**  Every overlap reading is logged beside its cosine (design item 7:
   `<run>/readings.jsonl`, one line per pair judged, the calibration record).  `gap_registry.py`
   gains `synonyms`: the covered candidates with their `covered_by` and readings, as the rename
   shortlist of design item 8 (traits whose candidate reads 4 first, then 3).

## Transport, cost, records

- Live for the pilot; the Batches API for full runs (`--transport auto|live|batches` as the M1 filter
  has it), in waves: wave 1 the relation calls; then, per shortlist position, a Sonnet wave over every
  candidate still undecided, followed by an Opus wave over the pairs that need it; the wave code is
  [batches.py](../../assistant_axis/gapgen/batches.py), reused, with the 1-hour cache asked for on the
  system prompt in batch mode (the readout's caching note).  A wave is resumable as the filter's are.
- Caching on for every Sonnet and Opus call (the rubric is about 650 tokens; the minimum is 512).
  Haiku 4.5 cannot cache under 4,096 tokens; do not try.
- Prices as measured in `overlap_arms_3`: Sonnet about $0.0012 a pair, Opus about $0.0031 (it thinks
  more in the one-pair form), Haiku about $0.004 a relation call.  The estimate printed by a dry run
  uses these, counts the shortlist at 3 pairs per candidate with the early-exit rate of the test
  (about 18% fewer), and is checked against `--budget-usd`; `confirm_or_abort` from
  [cost.py](../../assistant_axis/gapgen/cost.py) gates it as the filter's runs are gated.
- `usage.json` (`MultiModelUsage`) per run, cache fields per record, a `run.json` with the pins,
  config version, transport and every setting, `run.log`, and `summary.json` with the counts:
  candidates by decision, by cut-off, pairs judged per candidate, early-exit depth, escalations,
  rescues, review flags by kind, pair completions, relation-call outcomes, cache hit rate, spend.

## The rubric for the relation call (draft 1)

For [rubrics/relation.md](./rubrics/relation.md), in the format of the other rubric files (header
table, "The prompt" fenced block, "Your notes", change log).  Example words are rubric A's, already
checked against the corpus.  Do not reword; render and read; fix only a mechanical fault and log it.

````text
You are given one JSON object: a persona trait, the candidate ("candidate"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how its concept stands to the candidate's.

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person.

Give one of these answers for each listed trait:
- "similar": the two concepts are close: the same concept, or one a form or a part of the other, or two concepts that share a core. For example, talkative and loquacious; or studious and bookish.
- "opposed": the listed trait is the reverse of the candidate, the same quality at the other end. For example, cheery and morose.
- "unrelated": different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "unsure": you cannot tell from the two descriptions.

For each listed trait give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed trait's id>, "reason": "<one short sentence>", "relation": "similar"|"opposed"|"unrelated"|"unsure"}]}
Return one row per listed trait, in the order given.
````

The user turn: `{"candidate": {"label", "description"}, "traits": [{"id", "label", "description"}, ...]}`,
the description being the candidate's M1 gloss, labels in display form, the list in random order
(seeded by the run and the key).  Parse as the harness parses rubric A's list form (extra keys ignored
and noted, the last `results` object taken, one re-ask).

## The pilot

Two pools, both submitted to the registry (generator and run id as given), then run through the M1
split filter ([traithood_filter.py](../../data_analysis/gap_generation/traithood_filter.py)
`--pipeline split --run <generator>/<run_id>`, live), then through M3:

- `antonym_check/pilot_1`: the words the antonym checks proposed that are not in the corpus:
  every `candidates` entry of [antonym_check_history.jsonl](../../data/traits/antonym_check_history.jsonl),
  normalised with `normalize_to_file_name`, minus corpus stems and queue stems; 449 words on
  2026-10-04 (203 proposed more than once).  `gloss_hint` empty; `source_ref` the check's stem.
- `m1_validation/pilot_1`: 150 of the random adjectives the M1 validation run passed as `trait`
  ([m1_validation/results.jsonl](../../data/candidates/filter/m1_validation/results.jsonl)), drawn
  with seed 0; they go through the filter again like any candidate (their earlier reading is on
  record for comparison).

Then M3 on every row of both runs that passed, with the design above; and, on **100 of those
candidates drawn with seed 0, a full scan**: the overlap call on every retrieved and expanded trait,
no shortlist, no early exit, Sonnet on all and Opus on the pairs the rule sends it, written to a
separate run directory, so that the readout can say what the relation call's shortlist would have
missed (a pair the full scan put at the cut-off or above that the relation call did not mark
`similar`), and what early exit would have skipped.  Estimated live cost: M1 on about 600 words about
$6; M3 with the shortlist about $9; the full scan about $5; relation calls about $2.5: **about $22 in
all, cap $30**.  Over the $20 line: Fable quotes the dry-run estimate to Roger and relays his go
before the first paid call of each stage; build and test first, so nothing waits on him.

Report (do not write the readout; Fable does): the commits; the counts of `summary.json`; the
decisions table for the pilot (every candidate: label, decision, covered_by, cut-off, the readings
that decided it, review flags), as a markdown file in the run directory for Roger to sample from;
the relation call's recall from the full scan; the review queue (`grey` rows) with both readings and
reasons; the pair completions; cache hit rates and spend by model and stage; anything surprising;
test expectations changed, with reasons.

## Tests, written alongside

Fake clients ([fake_anthropic.py](../../assistant_axis/tests/fake_anthropic.py)) and a toy corpus
(the one the overlap tests use), no paid calls: the exact-label check (corpus stem, queue stem,
`renamed_from`); retrieval and expansion (a pair member brings its partner, a triangle its two
corners, a sequence nothing; cosines on the added members); the relation call's shortlist order, the
pair check flag, the opposed-with-partner and opposed-without-partner paths; the overlap walk at both
cut-offs, every branch of the rule table, early exit, the "opposite" partner-next-then-continue rule,
"unsure" to Opus, the re-ask and the `unparsed` flag; the `grey` decision and `review_order`; the
registry block written once and resume skipping decided rows; the waves (one Sonnet wave then one
Opus wave per shortlist position, the Batches path exercised with the fake batch client the filter's
tests use); the estimate; the `synonyms` subcommand; the pilot's pool builders (counts on the real
files); a CLI end-to-end run on the toy corpus.  The existing suites keep passing; do not change an
expectation without saying why in the report.

## Constraints that apply to every command

- **Files**: read, write and search only inside this repository
  (`/Users/roger/Documents/GitHub/assistant-axis/`, this worktree included), `$TMPDIR` and the session
  scratchpad.  Nothing else on the machine, not to "check what is installed", not read-only.  If
  something seems to need a path outside, stop and say so in your report.
- **Bash is sandboxed**: `ps` and `pgrep` fail; `kill -0 <pid>` on another command's job says
  "operation not permitted" while the job is alive and "no such process" only when it has ended;
  temporary files go under `$TMPDIR`; `.claude/hooks`, `.claude/skills`, the settings files and
  `~/.claude/projects` cannot be written from the shell.  A command that fails on a sandbox restriction
  is reported, not routed around.
- Open source files with the **Read tool** before editing; edit with Edit and Write, not with shell
  rewrites; one purpose per shell command; never repeat a command that was refused.
- Run tests as separate invocations: `uv run pytest -q assistant_axis/tests data_analysis/tests`;
  never a bare `pytest` at the root.
- `.env` is in place in this worktree; never read or print it.  OpenAI and Anthropic are reached
  directly with their own keys, never through a router.
- Commit at checkpoints on this branch, one purpose per commit, messages ending with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; never push, never stash.  The platform's
  files must be committed before a live run.
- Rubric A's text is Roger's and is not edited here; the relation rubric is pinned before use and
  not reworded.

## Round 2: the rules from Roger's review, and the missed cases (2026-10-07)

On Roger's go after his review of the pilot ([m3_pilot_readout.md](./m3_pilot_readout.md), "Roger's
review"; his marks in [roger_review.json](../../data/candidates/novelty/m3_pilot_1/roger_review.json)).
The decisions are 12-15 of [coding_plan_platform.md](./coding_plan_platform.md) (M3 decisions) plus the
cosine floor; this section says what to build and run.  Start by fast-forwarding the worktree branch
to `anthropic-vllm-uv` (`git merge --ff-only anthropic-vllm-uv`; it is an ancestor).

### Changes to the pipeline

1. **Decision 12.**  A Sonnet reading one below the cut-off that Opus reads at or above it is
   `covered` with `covered_by` that trait and `review: "sonnet_below_opus_at"` kept on the row (both
   readings and reasons recorded as now).  `grey` is no longer given for this case.  The walk stops
   there as for any cover.
2. **Decision 13, Roger's rule.**  When the relation call marks both members of a recorded pair
   `similar`, both are removed from the shortlist before the walk, and the row gets
   `pair_notes: [{"pair": [...], "both": "similar"}]`; `decisions.md` lists these rows in a section
   "Both ends similar (orthogonal to the pair?)" with the ends' cosines and any overlap readings.
   Triangle and tetrahedron corners: the same rule when every corner comes back similar.
3. **Decision 14.**  `pair_flags` stays on the row as a record, but no longer makes the decision
   `grey`; the review queue is the `sonnet_below_opus_at` covers, the both-similar notes, and
   `unparsed`.
4. **Decision 15.**  The exact-label stage covers only on a corpus stem or a queue stem (separator-
   and case-blind: "anti feminist", "anti-feminist" and antifeminist are one label); a `renamed_from`
   match no longer covers, and the candidate is judged like any other, with the current trait put at
   the front of the shortlist whatever the relation call says.
5. **The cosine floor** (Roger, 2026-10-07: "an acceptable level of trade-off"): listed traits whose
   cosine to the candidate is below `--cosine-floor` (default 0.25, recorded in `run.json` and
   `metric_config`-style in the row) are not judged by the overlap call; they stay in the relation
   call and in `listed` with their relation, and the row records `n_below_floor`.  The partner of an
   opposed trait is judged even below the floor (the opposite rule), as is a `renamed_from` match.
6. **`full-scan --keys KEY ...`** (registry keys, as `score --keys`), in place of `--sample`, so chosen
   candidates can be scanned; and **`score --redecide`**, which re-runs the decision rule on a run's
   recorded readings and relation answers (no API call except where a rule now needs a reading that
   is not on record, which it sends live and records), writing a new run id's `results.jsonl`,
   `decisions.md` and `summary.json`, with a `decision_changes.md` listing every row whose decision
   differs from the source run and why.

### Run

1. **Re-decide the pilot** under rules 1-5: `score --redecide --from-batch m3_pilot_1 --batch-id
   m3_pilot_1_r2 --cosine-floor 0.25 --transport live`.  New calls are expected only for the 12
   `renamed_from` rows (now judged) and nothing else; estimate and report them (about $0.10).  Report
   `decision_changes.md`: how many covers became grey or new under the floor (the readout predicted
   two), how many flagged rows became covers (expected 61), how many greys became new (the pair-flag
   rows), what the 12 `renamed_from` rows decided, and the both-similar notes.
2. **Scan the five missed cases**: `full-scan --from-batch m3_pilot_1 --keys youthful#1 trendsetting#1
   meandering#1 self_serving#1 conflict_avoidant#1 --batch-id m3_pilot_1_scan_missed --transport
   live` (check the keys in the registry first; use the spelling there).  The question is whether the
   trait Roger says was wrongly marked opposed (immature, fashionable, erratic, uncaring, peaceful)
   would have covered the candidate: report Sonnet's and Opus's scores on those five pairs with the
   reasons, and the decision the scan gives against the pilot's.  About $0.15.
3. Both under the existing caps (`--budget-usd 2` each); nothing here approaches the $20 line.

### Tests and report

Tests for every change with the fake clients and the toy corpus: the covered-and-flagged decision;
the both-similar removal and note (pair, triangle); the pair flag no longer grey; the exact-label
stage's separator-blind match and the `renamed_from` path through the walk; the floor (a pair below it
is not judged; an opposed partner and a `renamed_from` match are judged regardless); `--redecide` on
recorded answers, with and without a reading it must fetch; `full-scan --keys`.  Existing suites
pass; a changed expectation is reported with its reason.  `decisions.md` gains the "Both ends similar"
section and a "Covered, flagged" section for the decision-12 rows (both readings and reasons), so that
Roger's review reads from one file.  Report: the commits; `decision_changes.md`'s counts and the
rows the floor changed (with their readings); the five missed cases with both models' scores and
reasons; spend; test expectations changed.  Do not write the readout; Fable does.  The constraints of
the first section apply unchanged.
