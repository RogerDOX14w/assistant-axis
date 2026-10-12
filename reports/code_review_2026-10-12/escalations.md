# Code review of 2026-10-12: fixes, design issues and decisions

**This document is the record.**  The working copy was a session scratch file,
`/tmp/claude-501/review_escalations.md`, the running tally the coordinator kept for Roger while
the reviewers ran (`/tmp` is cleared on reboot and nothing there is a deliverable).  Its content
is carried here in full: the same findings, numbers, recommendations and decisions, reordered
only for readability, each design issue under a heading of its own so that other documents can
link it, and every file mention a link.  The tally's own section headings carried the date
2026-10-13; the review is referred to everywhere else by 2026-10-12, and so here.

## What the review was

Overnight on 2026-10-12, eleven reviewers went over everything changed since May 2026, one group
each; five more then went over the activation-extraction pipeline; Roger walked through the
escalations the same day and the decisions are at the end.  Each reviewer fixed what it could
(with regression tests, nothing retroactive to recorded data), listed nits it did not fix, and
escalated design issues, which are the D-numbered items below.

The eleven groups, in the tally's order (the commit each reviewer's fixes landed in, where the
tally gives it):

| group | what it covered | commit |
|---|---|---|
| Review 3 | the registry, promotion, recovery, the states and physical passes | d0d8f20 |
| Review 6 | the model-based generators (alignment sweep, base model, masked LM) | committed (hash not in the tally) |
| Review 2 | the novelty side (M3) | committed (hash not in the tally) |
| Review 9a | results analysis, first half | 0e215a8 |
| Review 4 | the review tooling (the review app) | committed (hash not in the tally) |
| Review 8 | the corpus-facing `data_analysis` scripts | 2fc4ff0 (docs in the next commit) |
| Review 9b | results analysis, second half | 8cd82ed |
| Review 5 | the lexical generators: censuses, Roget, WordNet, IPIP | 7220a37 |
| Review 7 | the core library, the pipeline, the steering runner, the boundary hook | 12fa5ac |
| Review 1 | the filter side: M1, split, pins, LLM client, batches, cost, runs | a2ac553 |
| Review 10 | tools, shell scripts, one-off scripts | c88c4bd |

The five pipeline reviewers:

| reviewer | what it covered | commit |
|---|---|---|
| P1 | step 1, generation | cc49023 |
| P5 | end-to-end contracts (read-only, Fable) | none |
| P2 | step 2, activations and internals | 11d7f28 |
| P3 | step 3, judging | 56f3df3e |
| P4 | steps 4 and 5, the scanner, the driver, file IO | ba4efef2 |

Other commits the tally names: 2e2f1a25 (the winner-decomposition relabel in the notes), the
credentials move "after cdb34d49" (db1b25b8 in the log), 87d84fc (the W15 goal lists), 1441a97
(the boundary hook's narrowing).

## Terms

- **M1, the trait-hood filter**: the paid LLM step that decides whether a candidate word is a
  trait at all and writes its one-sentence gloss
  ([`filter.py`](../../assistant_axis/gapgen/filter.py),
  [`filter_rubric.py`](../../assistant_axis/gapgen/filter_rubric.py), CLI
  [`traithood_filter.py`](../../data_analysis/gap_generation/traithood_filter.py)); the full
  vocabulary is in the [glossary](../trait_gap_generation/glossary.md).
- **M3, the novelty check**: the step that decides whether a candidate that passed M1 is already
  covered by a corpus trait or a queued one: an embedding search for its nearest existing traits,
  then LLM overlap calls ([`novelty.py`](../../assistant_axis/gapgen/novelty.py),
  [`embed.py`](../../assistant_axis/gapgen/embed.py), CLI
  [`novelty_score.py`](../../data_analysis/gap_generation/novelty_score.py)); "stage 0" is its
  free pre-check against the queue.
- **R1, the review graph**: the graph whose nodes are candidates and whose edges are the
  overlap judgements between them, each with a level per direction (Sonnet, escalated to Opus);
  the cliques at a cut-off (not connected components; corrected by the gate-8 audit) are what the review app shows Roger to resolve
  ([`review_graph.py`](../../assistant_axis/gapgen/review_graph.py), CLI
  [`review_graph.py`](../../data_analysis/gap_generation/review_graph.py); the app:
  [`review_app.py`](../../data_analysis/gap_generation/review_app.py),
  [`review_app/`](../../assistant_axis/gapgen/review_app/)).
- **The registry**: [`data/candidates/registry.jsonl`](../../data/candidates/registry.jsonl),
  the append-only log of every candidate and what each step found;
  [`registry.snapshot.jsonl`](../../data/candidates/registry.snapshot.jsonl) is the tracked
  compacted copy written by [`gap_registry.py`](../../data_analysis/gap_generation/gap_registry.py)
  `compact`; `promote` moves a candidate into
  [`data/seed_queue.json`](../../data/seed_queue.json), from which
  [`seed_entities.py`](../../data_analysis/seed_entities.py) generates the trait.
- **Slot**: the first axis of every activation, vector and axis tensor.  Slot 0 is the mean
  over the response's content tokens; slots 1 to 7 are the single positions of the seven
  header tokens of Qwen3's non-thinking assistant turn (`<|im_start|>`, `assistant`, `\n`,
  `<think>`, `\n\n`, `</think>`, `\n\n`).
- **8slot**: the current Qwen3-32B dataset,
  [runpod_workspace/qwen/qwen-3-32b Roger 8slot/](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/),
  1 + 7 slots; its predecessor, the "4-slot" tree
  [runpod_workspace/qwen/qwen-3-32b Roger/](../../runpod_workspace/qwen/qwen-3-32b%20Roger/),
  had 1 + 3.
- **The eleven collision names**: stems that are both a trait and a role (`ascetic`,
  `contrarian`, `cosmopolitan`, `generalist`, `pacifist`, `parent`, `patient`, `perfectionist`,
  `romantic`, `specialist`, `stoic`); the bare name is not a unique identifier and code keys on
  `name|T` / `name|R` ([entity-naming rule](../../.claude/rules/entity-naming.md)).
- **The provenance audit and its statuses**:
  [`audit_caches.py`](../../tools/audit_caches.py) and [`audit_pngs.py`](../../tools/audit_pngs.py)
  compare each cached JSON's or plot's recorded inputs (its provenance envelope) with the
  current code and data and report **current**, **stale_direct** (an input drifted; **stale**
  for PNGs), **stale_transitive** (an upstream cache is stale), **legacy** (no envelope) or
  **frozen** (a PNG pinned to historical data) ([provenance rule](../../.claude/rules/provenance.md)).
- **The deferral registry**: [`deferred_rejudges.yaml`](../../deferred_rejudges.yaml), the list
  of stale caches whose re-judge is deliberately postponed, each with a category and a reason,
  so the audit reports them as deferred rather than as errors (written by
  [`defer_rejudge.py`](../../tools/defer_rejudge.py), read by
  [`deferral_registry.py`](../../assistant_axis/deferral_registry.py), checked by
  [`audit_deferrals.py`](../../tools/audit_deferrals.py)).
- **The equivalence marks**: [`script_equivalences.yaml`](../../script_equivalences.yaml)
  ([`mark_script_equivalent.py`](../../tools/mark_script_equivalent.py)) and
  [`rubric_equivalences.yaml`](../../rubric_equivalences.yaml)
  ([`mark_rubric_equivalent.py`](../../tools/mark_rubric_equivalent.py)) record that an edit to
  a producing script, or a rubric version bump, does not change outputs, so caches whose
  producer fingerprint or rubric version crossed that edge stay current to the audit.
- **B**: the response-judging batch size (responses per judge call); the May 2026 default
  moved from 10 to 7.

## How to cite an item

Every design issue is a `####` heading of the form `<label>: <title>`, where the label is the
tally's (`Review 7 D1`, `P2 D3`, `P5 #19`).  A link is the heading lowercased with its
punctuation dropped and spaces as hyphens, for example
`escalations.md#p1-d2-resume-skips-any-entity-whose-file-exists` or
`escalations.md#p5-19-bf16-three-times-before-a-difference-of-close-means`.  The review
groups are `##` headings (`#review-7-core-library-pipeline-steering-runner-boundary-hook`,
`#p2-step-2-activations-and-internals`).

---

## Review 3: registry, promotion, recovery, states and physical passes

Commit d0d8f20.

**Fixed** (4, all with regression tests, none affecting recorded data): states-pass gloss as the
draft ([`states_pass.py`](../../assistant_axis/gapgen/states_pass.py)); promote of a key named
twice ([`promote.py`](../../assistant_axis/gapgen/promote.py)); recovery hiding groups follow
links both ways ([`recovery.py`](../../assistant_axis/gapgen/recovery.py)); registry timestamp
under the writer lock ([`registry.py`](../../assistant_axis/gapgen/registry.py)).

Design issues (escalated, nothing changed):

#### Review 3 D1: the seed queue has no lock

[`data/seed_queue.json`](../../data/seed_queue.json) has no lock (promote, the review app's
apply, every [`seed_entities.py`](../../data_analysis/seed_entities.py) subcommand): two writers
can drop each other's entries.  Rec: an fcntl lock in seed_entities (a `locked_queue()` context
manager).

#### Review 3 D2: the next compact would write a 133 MB tracked snapshot

The next [`gap_registry.py`](../../data_analysis/gap_generation/gap_registry.py) `compact`
would write a ~133 MB tracked snapshot
([`registry.snapshot.jsonl`](../../data/candidates/registry.snapshot.jsonl); GitHub refuses
>100 MB); the log ([`registry.jsonl`](../../data/candidates/registry.jsonl)) is 246 MB.  Rec:
gzip the snapshot, possibly slim it.  Decide before anyone runs compact.  Also: the tracked
snapshot is from 2026-10-08 (548 rows), so anything reading it is 4 days stale.

#### Review 3 D3: no promote-time warning when a label is a pinned prompt word

No promote-time warning when a label is a pinned prompt word (morose, concealing, jumpy got
through; none has an instruction file).  Rec: a library `all_prompts()` in
[`prompt_hygiene.py`](../../assistant_axis/gapgen/prompt_hygiene.py) and a WARNING from
promote/apply, dry run included.

#### Review 3 D4: confirm-state-name can promote a row whose gloss the check rejected

`--confirm-state-name` can promote a row whose gloss the check rejected, with that gloss as the
draft and no mention (11 rows today).  Rec: put the check's reading in the refusal and the
notes; leave the draft empty.

#### Review 3 D5: the states one-hop hold fires on any row with a states-pass source

The states one-hop hold fires on any row with a states_pass source, including 81 of 120 that
other generators also proposed (unkempt, tense,
[hurried](../../data/traits/instructions/hurried.json) held).  Spec says so literally.  Rec:
hold only when every source is states_pass; re-judge the 3 at cents if agreed.

#### Review 3 D6: promote min-local-novelty reads pre-M3 fields

`promote --min-local-novelty` reads pre-M3 fields and refuses every M3 row; the notes' "nearest
existing" is empty for M3 blocks.  Rec: remove the flag; rewrite the note from `covered_by` /
`listed[0]`.

#### Review 3 D7: corpus-regions from-descriptions has no dirty-tree check and records no git sha

[`gap_registry.py`](../../data_analysis/gap_generation/gap_registry.py)
`corpus-regions --from-descriptions` (paid) has no dirty-tree check and records no git sha.
Rec: add them as [`states_pass.py`](../../data_analysis/gap_generation/states_pass.py) (the
CLI) does.

#### Review 3 D8: promote exits 0 when every named key was refused

`promote` exits 0 when every named key was refused.  Rec: non-zero.

**Nits listed, not fixed**: `_read_locked`'s no-file race
([`registry.py`](../../assistant_axis/gapgen/registry.py)); compact without fsync;
`submit --file` tracebacks on bad lines; the states CLI summary envelope lacks inputs;
`review_graph._gloss` ([`review_graph.py`](../../assistant_axis/gapgen/review_graph.py))
prefers the row's own gloss (owner: review 4).

---

## Review 6: model-based generators

Committed (hash not in the tally).

**Fixed** (7): variant B's Krakovna rows (double HTML conversion → 0 chunks; item-id KeyError
after paying) in the alignment sweep
([`alignment_sweep.py`](../../data_analysis/gap_generation/alignment_sweep.py),
[`sources.py`](../../assistant_axis/gapgen/generators/alignment_sweep/sources.py),
[`chunk.py`](../../assistant_axis/gapgen/generators/alignment_sweep/chunk.py)); gate/extract
([`gate.py`](../../assistant_axis/gapgen/generators/alignment_sweep/gate.py),
[`extract.py`](../../assistant_axis/gapgen/generators/alignment_sweep/extract.py)) stopped by
the cap now say so and leave outputs alone; readout says advisory and uses the answered
denominator [the tally does not name the module; the alignment sweep's is
[`report.py`](../../assistant_axis/gapgen/generators/alignment_sweep/report.py)]; base-model
parse ([`parse.py`](../../assistant_axis/gapgen/generators/base_model/parse.py)) refuses
unscreened person samples; sense
([`sense.py`](../../assistant_axis/gapgen/generators/base_model/sense.py)) enforces its budget
and persists in a finally.  Docstrings.

**NOTE for Roger**: the reviewer wrote "variant B has never run" — it did
([2026-10-11-b](../../data/candidates/runs/alignment_sweep/2026-10-11-b/), 60 poles) but
WITHOUT Krakovna.  A rerun of `extract --run-id 2026-10-11-b --variant B` would now add the
Krakovna chunks (reuses the 31 answered; cost a few dollars) — needs his word.

Design issues:

#### Review 6 D1: gate agrees counts a chat answer as a miss

`gate.agrees` ([`gate.py`](../../assistant_axis/gapgen/generators/alignment_sweep/gate.py)):
an item expecting agentic with also_accepts both counts a `chat` answer as a miss
(power-seeking only; never happened).  Rec: chat-reachable answer agrees if any accepted answer
is chat-reachable.

#### Review 6 D2: masked-LM top N ranks across mixed PLL scales

Masked-LM `--top N` ([`masked_lm_generator.py`](../../data_analysis/gap_generation/masked_lm_generator.py))
ranks across mixed PLL scales → phrases on top; help still calls it the pilot selector.  Rec:
rank within class or retire `--top`.

#### Review 6 D3: the sense cost model is stale

Sense cost model `SENSE_TOKENS=(400,60)`
([`base_model_generator.py`](../../data_analysis/gap_generation/base_model_generator.py)) stale
vs max_tokens 1,200 (measured 547/204).  Rec: (550, 1200).

#### Review 6 D4: the sense step's paid usage lives only in the gitignored round dir

The sense step's paid usage lives only in the gitignored round dir; evaluation double-counts
across runs of one round.  Rec: a tracked per-round usage file.

#### Review 6 D5: base-model bak files not gitignored

`/data/candidates/base_model/*.bak.*` ([`data/candidates/base_model/`](../../data/candidates/base_model/))
not gitignored (2 present).  Rec: gitignore (outside the reviewer's lists).

#### Review 6 D6: a gate item with one failed base reading rests on one reading

A gate item with one failed base reading rests on one reading as majority=True, no third
reading (one recorded row: undermines_its_developer#1 in
[2026-10-11-papers](../../data/candidates/runs/alignment_sweep/2026-10-11-papers/)).  Rec:
take the third reading.

#### Review 6 D7: the divergence-cosine help promises a refloor the CLI cannot do

`--divergence-cosine` help
([`base_model_generator.py`](../../data_analysis/gap_generation/base_model_generator.py),
[`sense.py`](../../assistant_axis/gapgen/generators/base_model/sense.py)) promises a refloor
the CLI can't do.  Rec: add `sense --refloor` or reword.

---

## Review 2: novelty side

Committed (hash not in the tally).

**Fixed** (3): a one-unparsed-plus-one-failed call stalls instead of greying;
`EmbeddingCache.save` ([`embed.py`](../../assistant_axis/gapgen/embed.py)) locks and merges (no
lost entry found; note each checkout has its own cache, so the
[2026-10-10-full](../../data/candidates/runs/alignment_sweep/2026-10-10-full/) alignment run's
texts live in the gen02 worktree cache); canary threshold from config
([`metric_config.py`](../../assistant_axis/gapgen/metric_config.py)).

Design issues:

#### Review 2 D1: a corpus renamed-from that is also a queue stem is covered at stage 0

A corpus `renamed_from` that is also a queue stem is covered at stage 0 by the queue entry,
bypassing decision 15; 8 rows (tough, disciplined, nonchalant, bland, exclusive, indulgent,
libertarian, universalist; none has an instruction file under that name, these being the old
names).  Rec (a): check `renamed_from` before the queue under rule set 2, then
`score --redecide --keys …` ([`novelty_score.py`](../../data_analysis/gap_generation/novelty_score.py))
for the 8 (cents) on Roger's go.  Same leak in `recovery.reduced_label_sets`
([`recovery.py`](../../assistant_axis/gapgen/recovery.py)) (no recorded effect).

#### Review 2 D2: replayed records on resume not charged to the candidate's block

Replayed records on `--resume` not charged to the candidate's block.  Rec: charge those of this
run.

#### Review 2 D3: usage file written only at finalize

`usage.json` written only at finalize; a killed process leaves it stale.  Rec: write after
every wave.

**Nits listed (not fixed)**: review_graph CLI's canary threshold
([`review_graph.py`](../../data_analysis/gap_generation/review_graph.py); owner review 4);
calibrate_metric's AsyncAnthropic retries
([`calibrate_metric.py`](../../data_analysis/gap_generation/calibrate_metric.py)); etc.

---

## Review 9a: results analysis, first half

Commit 0e215a8.

**Fixed** (9 + nits): PC round-trip loader (rho=None on every rerun since 2026-05-11; May
outputs stand) [the tally does not say which file under
[`pc_round_trip/`](../../results_analysis/pc_round_trip/)];
[`permutation_null.py`](../../results_analysis/pc_round_trip/permutation_null.py) garbage guard;
[`gpt_sonnet_weight_sweep.py`](../../results_analysis/gpt_sonnet_weight_sweep.py) key migration
order; seriation `_v1` cohort ([`axis_cosine_seriation.py`](../../results_analysis/axis_cosine_seriation.py));
`--pair_list` on [`gpt_anthropic_response_weight_sweep.py`](../../results_analysis/gpt_anthropic_response_weight_sweep.py)
and [`orthogonal_to_response_set.py`](../../results_analysis/orthogonal_to_response_set.py);
[`launch_judge_runs.py`](../../results_analysis/pc_round_trip/launch_judge_runs.py) exit status;
[`optimal_axis_for_judge.py`](../../results_analysis/optimal_axis_for_judge.py) `--scores_file`;
None filter; rho floor.  Two scripts marked output-equivalent
([`script_equivalences.yaml`](../../script_equivalences.yaml)).

Design issues:

#### Review 9a D1: the 0.525 Haiku weight's recorded retune ran on partial coverage

The 0.525 Haiku weight's recorded retune (2026-05-22) ran 12 of 22 axes on ~43 entities
(prefer_b (7,) with no `_b10_q9` inputs).  Recomputed on full coverage: peak w=0.575 rho
0.7422, 0.525 gives 0.7421 — keep 0.525, correct the "Selection history" note in
[`judge_score_combine.py`](../../assistant_axis/judge_score_combine.py); regenerate the plot
only if wanted.

#### Review 9a D2: the pole skip is kind-blind

[`axis_judge_correlation.py`](../../results_analysis/axis_judge_correlation.py)'s pole skip is
kind-blind: on impatient_vs_patient
([impatient](../../data/traits/instructions/impatient.json),
[patient](../../data/traits/instructions/patient.json)) the role
[patient](../../data/roles/instructions/patient.json)|R is never judged nor in the pool.  Rec:
skip (pair_type, name) at the next rejudge of that axis (~$0.01/judge).

#### Review 9a D3: pair-list defaults are the current lists

Pair-list defaults are the current lists
([`pair_list_clean.json`](../../roger/axis_judge_experiments/pair_list_clean.json),
[`pair_list_di.json`](../../roger/axis_judge_experiments/pair_list_di.json),
[`pair_list_goalnongoal.json`](../../roger/axis_judge_experiments/pair_list_goalnongoal.json),
[`pair_list_responses.json`](../../roger/axis_judge_experiments/pair_list_responses.json));
with the 8slot data they crash or silently drop axes; the `_v1` record
([`pair_list_clean_v1.json`](../../roger/axis_judge_experiments/pair_list_clean_v1.json),
[`pair_list_di_v1.json`](../../roger/axis_judge_experiments/pair_list_di_v1.json),
[`pair_list_goalnongoal_v1.json`](../../roger/axis_judge_experiments/pair_list_goalnongoal_v1.json),
[`pair_list_responses_v1.json`](../../roger/axis_judge_experiments/pair_list_responses_v1.json))
needs the flags.  Rec: 8slot-era scripts default to `_v1` until the next extraction — Roger's
call.

#### Review 9a D4: the goal list regenerated 2026-10-10 overlaps the old on 26 of 54 traits

Goal list ([`data/goal_roles_and_traits.json`](../../data/goal_roles_and_traits.json))
regenerated 2026-10-10 overlaps the old on 26 of 54 traits non_goal; 38 names have no 8slot
vector.  Rec: snapshot the pre-87d84fc list as
[`data/goal_roles_and_traits_v1.json`](../../data/goal_roles_and_traits_v1.json) (not there
yet) and default 8slot-era plots to it.

#### Review 9a D5: judge caches written non-atomically

Judge caches written non-atomically (a kill mid-write loses paid judging).  Rec: temp file +
`os.replace` in `_save_json`
([`axis_judge_correlation.py`](../../results_analysis/axis_judge_correlation.py)), with a
script-equivalence mark (editing axis_judge_correlation flips ~723 caches' producer
fingerprint).

#### Review 9a D6: parser falls back to the first integer when there is no SCORE line

Parser falls back to the FIRST integer when there is no `SCORE:` line; the rule says last (2 of
2.86M texts).  Change at the next rubric bump.

#### Review 9a D7: optimal-axis default soft K disagrees with the library default

[`optimal_axis_for_judge.py`](../../results_analysis/optimal_axis_for_judge.py)
`DEFAULT_WHITENING` soft_K=3 vs `DEFAULT_SOFT_K`=2
([`whitening.py`](../../results_analysis/canonical_angles/whitening.py)).  Roger's call.

#### Review 9a D8: launch judge runs passes no budget to the judge subprocesses

[`launch_judge_runs.py`](../../results_analysis/pc_round_trip/launch_judge_runs.py) passes no
`--budget_usd` to ~96 judge subprocesses.  Add before any rerun.

#### Review 9a D9: tmp pickle caches keyed on CLI args only

`/tmp` pickle caches keyed on CLI args only
([`layer_sweep.py`](../../results_analysis/canonical_angles/plots/layer_sweep.py),
[`whitening_sweep_with_nulls.py`](../../results_analysis/canonical_angles/plots/whitening_sweep_with_nulls.py)):
stale plots possible.  Rec: fingerprint inputs or `--no_cache`.

**Nits listed (not fixed)**: many stale docstrings in
[`axis_judge_correlation.py`](../../results_analysis/axis_judge_correlation.py) (not edited:
fingerprint), [`judge_ensemble_rho_curve.py`](../../results_analysis/judge_ensemble_rho_curve.py)'s
weight text (0.60/0.625/0.609 vs 0.525), `fit_shear` divide-by-zero at θ=0
([`whitening.py`](../../results_analysis/canonical_angles/whitening.py)), etc.

---

## Review 4: review tooling

Committed (hash not in the tally).  The review tooling is the review app: CLI
[`review_app.py`](../../data_analysis/gap_generation/review_app.py) (`serve`, `apply`), the
server [`server.py`](../../assistant_axis/gapgen/review_app/server.py), the decision logic
[`decisions.py`](../../assistant_axis/gapgen/review_app/decisions.py) and the page under
[`static/`](../../assistant_axis/gapgen/review_app/static/).

**Fixed** (7): torn-last-line guard; apply-failure rollback; undo seq 409;
promoted-then-resolved-otherwise conflict report; leftovers tie count = 4-edges only; apply
lists skipped events; page tolerates old-server cards and late Find answers.  Real logs replay
with 0 skipped.

Design issues:

#### Review 4 D1: leftovers seeded from all members

Leftovers seeded from all members incl. ones another group handled; rec: seed from the basis
(`resolved_members`).  Lists identical today.

#### Review 4 D2: also-proposed never refreshed on the queue entry

`also_proposed` never refreshed on the queue entry after an extend/re-resolve of a promoted
group; rec: rewrite only that field on re-apply (shown as a WRITE).

#### Review 4 D3: apply goes ahead with skipped events

Apply goes ahead with skipped events (now warns); rec: refuse unless `--allow-skipped`.

#### Review 4 D4: two serve processes on one log would duplicate seq

Two `serve` processes on one log would duplicate seq; rec: flock for the server's lifetime.

#### Review 4 D5: edge level shows a one-way 3 as level 3

`edge_level` shows a one-way 3 as level 3 (90 such edges); rec: weaker direction for edges
read both ways.

#### Review 4 D6: a 3-edge at cut-off 3 ignores an Opus 2 over a Sonnet 4

3-edge at cut-off 3 ignores an Opus 2 over a Sonnet 4 (0 occurrences); keep, revisit.

#### Review 4 D7: opening a term dropped from its seed's open group returns that group without it

Opening a term dropped from its seed's open group returns that group without it; rec: open the
term alone.

**Nits**: key `n` nominates row 0 while the button refuses (Roger's 2026-10-10 rule: the
default highlight is not a choice); key `c` likewise; etc.

---

## Review 8: corpus-facing data_analysis scripts

Commit 2fc4ff0; docs in the next commit.

**Fixed** (18, 43 tests): batch collection
([`regenerate_trait_instructions.py`](../../data_analysis/regenerate_trait_instructions.py),
[`regenerate_role_instructions.py`](../../data_analysis/regenerate_role_instructions.py)) checks
logged counts, refuses re-collection / other directory / dry-run, regenerates edited files live;
naming-check failure no longer errors the file;
[`generate_antonyms.py`](../../data_analysis/generate_antonyms.py) tolerates bad replies and API
errors; [`seed_entities.py`](../../data_analysis/seed_entities.py) takes the live entry
([engaged](../../data/traits/instructions/engaged.json),
[turbulent](../../data/traits/instructions/turbulent.json) were skipped), keys by stem, drops
ERROR answers, rename updates lists before regenerating;
[`score_combinations.py`](../../data_analysis/score_combinations.py) /
[`classify_goals.py`](../../data_analysis/classify_goals.py) refuse malformed replies and don't
double-charge; audit judge
([`audit_trait_instructions.py`](../../data_analysis/audit_trait_instructions.py),
[`audit_role_instructions.py`](../../data_analysis/audit_role_instructions.py)) learns
temperature refusal.  Corpus checked: nothing to regenerate.

**Behaviour change to know**: a deliberate re-collection now means removing `collected` from
the batch log entry ([`data/traits/regeneration_batches.json`](../../data/traits/regeneration_batches.json),
[`data/roles/regeneration_batches.json`](../../data/roles/regeneration_batches.json)).

Design issues:

#### Review 8 D1: the generators exit 0 when entities errored

The generators exit 0 when entities errored; seed_entities pair/rename trust the exit code.
Rec: exit 1 on any non-refusal error, with `cmd_generate` still marking the successes.
Roger's call (external runners).

#### Review 8 D2: role-play openings are banned only by the prompt

Role-play openings ("Play …", "Adopt …", "Act as …") are banned only by the prompt; the reroll
counts them as a form.  Corpus has none today.  Rec: make `opening_reroll_wanted`
([`regenerate_trait_instructions.py`](../../data_analysis/regenerate_trait_instructions.py),
[`regenerate_role_instructions.py`](../../data_analysis/regenerate_role_instructions.py)) catch
them (slight cost).

#### Review 8 D3: temperature sent unconditionally

Temperature sent unconditionally by both generators, classify_goals and the opening-form depth
judge ([`opening_form_experiment.py`](../../data_analysis/opening_form_experiment.py)); fine for
Sonnet/Opus 4.6, fails loudly on a model that refuses it.  Rec: `accepts_temperature` at a
model switch, and decide what the generator record says.

#### Review 8 D4: backfill-arrangements apply overwrite would wipe every arrangement recorded since September

[`backfill_arrangements.py`](../../data_analysis/backfill_arrangements.py)
`--apply --overwrite` would wipe every arrangement recorded since September and predates the
non-X triangle rule.  Rec: archive it or refuse `--overwrite`.

#### Review 8 D5: README and AGENT NOTES lines for the collection rules

(Done by the tally's author.)  [README](../../README.md) and
[AGENT_NOTES.md](../../AGENT_NOTES.md) lines for the collection rules.  The tracked batch logs
still hold absolute paths with the username (old entries); new entries are relative.

---

## Review 9b: results analysis, second half

Commit 8cd82ed.

**Fixed** (15, 12 new test files): Sonnet desc/inst caches never key-migrated in
[`rubric_v1_v2_compare.py`](../../results_analysis/rubric_v1_v2_compare.py) (combined columns
were GPT-only; means move ~0.004 if regenerated); three v1 GPT caches likewise in
[`response_di_weight_sweep.py`](../../results_analysis/response_di_weight_sweep.py)
([accessible](../../data/traits/instructions/accessible.json),
[benign](../../data/traits/instructions/benign.json),
[introverted](../../data/traits/instructions/introverted.json): rho at w=0 up 0.02–0.05;
parabolic peak w 0.956→0.938, rho 0.7581→0.7596 on the 22-axis `_v1` record);
[`shear_l_vs_k_comparison.py`](../../results_analysis/shear_l_vs_k_comparison.py)'s
`_strip_kind` could pair a trait's score with a role's projection (|Δρ| ≤ 0.007 on its 35
axes); [`run_axis_experiment_batch.py`](../../results_analysis/run_axis_experiment_batch.py)'s
summary had zero rows since the provenance envelope and always exited 0; polyfit weights (w,
not w²); batch-size plot
([`plot_batch_size_quality_vs_cost.py`](../../results_analysis/plot_batch_size_quality_vs_cost.py))
reads the 0.625 blend weight from the side-car;
[`variance_decomposition.py`](../../results_analysis/variance_decomposition.py) raises on a
missing vector; rho_by_slot titles
([`rho_by_slot_and_K.py`](../../results_analysis/rho_by_slot_and_K.py),
[`rho_by_slot_and_L.py`](../../results_analysis/rho_by_slot_and_L.py)) count loaded caches;
[`plot_winner_consistency.py`](../../results_analysis/pc_round_trip/plot_winner_consistency.py)
dropped every L=4 winner (14/48 actual, 1,317/4,800 null) and greyed 4 of 7 cells;
winner-decomposition title L=0
([`plot_winner_decomposition.py`](../../results_analysis/pc_round_trip/plot_winner_decomposition.py));
`--ca_kind` choices (combined/r_only/t_only); `--pair_list` on response_di_weight_sweep;
[`plot_direction_cosines.py`](../../results_analysis/pc_round_trip/plot_direction_cosines.py)
passes `kinds_for_name`.

**Behaviour change to know**: under pipefail,
[`rejudge_after_rubric_v2.sh`](../../scripts/rejudge_after_rubric_v2.sh) and
[`rejudge_after_trait_edits.sh`](../../scripts/rejudge_after_trait_edits.sh) now stop with
FAILED after a phase in which any pair failed.

Design issues:

#### Review 9b D1: default pair lists are the current ones

(= [Review 9a D3](#review-9a-d3-pair-list-defaults-are-the-current-lists).)  Default pair lists
are the current ones: [`rho_by_layer.py`](../../results_analysis/rho_by_layer.py),
[`rho_by_slot_and_K.py`](../../results_analysis/rho_by_slot_and_K.py) /
[`rho_by_slot_and_L.py`](../../results_analysis/rho_by_slot_and_L.py),
[`response_di_weight_sweep.py`](../../results_analysis/response_di_weight_sweep.py) silently
skip uncached axes and lose [benign](../../data/traits/instructions/benign.json) /
[malicious](../../data/traits/instructions/malicious.json) and
[systems_thinker](../../data/traits/instructions/systems_thinker.json) /
[analytical](../../data/traits/instructions/analytical.json);
[`shear_l_sweep.py`](../../results_analysis/shear_l_sweep.py),
[`whitening_k_sweep.py`](../../results_analysis/whitening_k_sweep.py),
[`shear_l_vs_k_comparison.py`](../../results_analysis/shear_l_vs_k_comparison.py) crash.  Rec:
fail loudly naming the axis, or default to `_v1` until the next extraction.

#### Review 9b D2: winner decomposition decomposes the nth PC at the fixed-principled winners' cell

[`winner_decomposition.py`](../../results_analysis/pc_round_trip/winner_decomposition.py)
decomposes the nth PC at the *fixed_principled* winners' (cell, L, K) — not the direction that
won; the recorded
[pc_round_trip_nth_pc_winner_decomposition.npz](../../roger/pc_round_trip_nth_pc_winner_decomposition.npz)
and [pc_round_trip_nth_pc_winner_decomposition.png](../../roger/pc_round_trip_nth_pc_winner_decomposition.png)
(2026-05-09) were built that way and the axis-geometry synthesis
([axis-geometry rule](../../.claude/rules/axis-geometry.md)) argues from it (and still names
the canonical cell slot 3 / L=2).  Rec: relabel now; then Roger chooses between decomposing the
transported fixed_principled direction or restoring an nth_pc winners input (a rerun of the
search).

#### Review 9b D3: token position noise analysis's cache key omits the data fingerprint

[`token_position_noise_analysis.py`](../../results_analysis/token_position_noise_analysis.py)'s
cache key omits the data fingerprint: stale intermediates stamped as current.  Rec: store the
inputs used at compute time and stamp those.

#### Review 9b D4: slot and shear plots use GPT-only responses while rho by layer uses the blend

(Low.)  Slot/K, slot/L and shear/K plots use GPT-only responses at B=7 while
[`rho_by_layer.py`](../../results_analysis/rho_by_layer.py) uses the GPT+Haiku blend; moving
them would shift the basis of the L=3 decision.  Roger's call.

#### Review 9b D5: standardize axis spec has no usage file

[`standardize_axis_spec.py`](../../results_analysis/standardize_axis_spec.py) has no
`usage.json` (on the [CLAUDE.md](../../CLAUDE.md) retrofit list) and its "$0.002 per spec" is
~5x low.

**Nits listed (not fixed)**: no `declare_constants_dependency` in the sweep scripts; raw stems
in plot text (legends, panel titles, annotations, steering config pole names);
[`steering_response_curves.py`](../../results_analysis/steering_response_curves.py)'s
"skip_threshold (1.0)" line is the display filter and the runner default is 1.5, no Inputs
provenance, leaf-name collisions in `_averaged`; unreadable `.pt` skipped silently in 7
scripts; many stale docstrings (B=10 labels, slot 3 / L=2);
[`rho_by_layer_simple.py`](../../results_analysis/rho_by_layer_simple.py) aligns by position.
Outside its lists: [CLAUDE.md](../../CLAUDE.md)'s "run_axis_experiment_batch default is stale"
is itself stale (now 8slot); the steering-judging notes
([steering-judging rule](../../.claude/rules/steering-judging.md)) cite skip_threshold 1.0.

---

## Review 5: lexical generators (censuses, Roget, WordNet, IPIP)

Commit 7220a37.

**Fixed** (9 + nits): `corpus_renamed_from`
([`censuses/corpus.py`](../../assistant_axis/gapgen/generators/censuses/corpus.py)) raised on
the real corpus (record/list forms;
[coding_plan_09](../trait_gap_generation/coding_plan_09_structural_generators.md) reuses it);
ipip `name --hinted` ([`ipip_generator.py`](../../data_analysis/gap_generation/ipip_generator.py),
[`ipip/naming.py`](../../assistant_axis/gapgen/generators/ipip/naming.py)) re-asked the blind
form for every pole (362 re-asks, ~$0.07; second answers used consistently, no rerun);
granularity budget stop ([`ipip/granularity.py`](../../assistant_axis/gapgen/generators/ipip/granularity.py))
still sent calls and exited 0; `cluster --targets 600`
([`ipip/cluster.py`](../../assistant_axis/gapgen/generators/ipip/cluster.py)) dropped the
350/150 summaries (tracked [`cluster_summary.json`](../../data/candidates/ipip/cluster_summary.json)
holds only g600 now — optional free repair `ipip_generator.py cluster --targets 600 350 150`);
[`roget_generate.py`](../../data_analysis/gap_generation/roget_generate.py)
map/head-scope/place-check gained the $20 gate (`--confirm-expensive`/`--confirmed-by`);
`_key_sign` ([`ipip/ingest.py`](../../assistant_axis/gapgen/generators/ipip/ingest.py)) raises
on "R"/"?"; Roget gloss hint keeps the word out of hyphenated siblings
([QUESTIONS.md](../trait_gap_generation/QUESTIONS.md) 41; 2 hints, cosmetic); WordNet hint
when the noun is the adjective (2 rows); census follow-up command says `submit --from`; IPIP
report's granularity section ([`ipip/report.py`](../../assistant_axis/gapgen/generators/ipip/report.py))
shows signal 1 and names the measured granularities.

**Test expectation changed** (flag): `test_followup_commands`
([`test_gapgen_censuses_submit.py`](../../assistant_axis/tests/test_gapgen_censuses_submit.py))
now expects `gap_registry.py submit --from <path>` (was `--file`), because `--file` appends a
session to the tracked run.json and the plan revision names `--from`; no census run was ever
resubmitted with `--file`.

**Caller-side correction**: the IPIP naming parse rate on disk is 98.48% (713/724), not 98.8%;
all 11 failures are 5–6-word labels ([D2](#review-5-d2-the-naming-rubrics-own-example-is-over-long)).
The two red IPIP acceptance tests stay red.

Design issues:

#### Review 5 D1: IPIP merge keys gap-fills workbook rows the key pages already hold

IPIP `merge_keys` ([`ipip/ingest.py`](../../assistant_axis/gapgen/generators/ipip/ingest.py))
gap-fills workbook (A) rows whose key the key pages (B) already hold under another spelling
(HEXACO_PI/HEX, HPI-HIC/HPI, BARCHARD2001/"Barchard, 2001"): 716 duplicate links in the tracked
[`items.jsonl`](../../data/candidates/ipip/items.jsonl); E60/E134 carry B "-" and A "+" on the
same construct; 175 of 362 hinted naming prompts show a scale twice; purity metrics score only
541 items at g600; `split_poles`
([`ipip/cluster.py`](../../assistant_axis/gapgen/generators/ipip/cluster.py)) double-weights.
`ingest` writes even when it prints ASK ROGER (exit 3).  Rec: gap-fill only when `_match_item`
pairs the A row with no B link, together with Roger's ruling on the 35% A-vs-B mismatch
([QUESTIONS.md](../trait_gap_generation/QUESTIONS.md) 52 follow-up); then free ingest+cluster,
re-name only changed poles.

#### Review 5 D2: the naming rubric's own example is over-long

The naming rubric's own example "keeps others at arm's length" is 5 words against
`MAX_LABEL_WORDS=4` ([`ipip/naming.py`](../../assistant_axis/gapgen/generators/ipip/naming.py));
the 11 failures are 7 over-long antonyms and 4 labels.  Rec: an over-long antonym nulls
`antonym_label` with a note (720/724 = 99.4%), and shorten the example at the next pin (Roger's
text; bumping the pin needs his go).

#### Review 5 D3: QUESTIONS 50 signal 1 rests on 2 to 10 pairs

[QUESTIONS.md](../trait_gap_generation/QUESTIONS.md) 50 signal 1 rests on 2–10 pairs: the
nearest pole is looked up among loose clusters, which are never named, so the pair is dropped
(g600 67 of 238 read, g350 10 of 91, g150 2 of 33).  This is the measure behind the open
granularity decision.  Rec: blind-name the loose poles that are some kept pole's nearest (~270
calls, ~$0.06) and re-read before the granularity call.  Also for Roger: at g600, 376 of 600
clusters (2,052 items) are loose.

#### Review 5 D4: the Roget harvest's second Zipf check drops the negating-prefix rescues

Roget harvest's ([`roget/harvest.py`](../../assistant_axis/gapgen/generators/roget/harvest.py))
second Zipf check (`fi.zipf_min < zipf_hard`) drops the negating-prefix rescues the platform
makes (77 words in the full run's selected heads, 24 in the pilot: unintellectual,
incommensurate, unwearied, inexpedient…).  Rec: drop only on hard_reject; the 1.5 line stands.

#### Review 5 D5: the Roget harvest's printed estimate uses stale rates

Roget harvest's printed estimate uses stale rates ($0.004 M1, $0.018 M3, half passing; measured
$0.0078, $0.013, 81.4%).  Print-only.

#### Review 5 D6: census and WordNet hints contain the word itself

Census ("disposition to be X") and WordNet hints
([`censuses/glosshint.py`](../../assistant_axis/gapgen/generators/censuses/glosshint.py))
contain the word itself (194/2,818 TDA, 518/3,646 allport_hi, 55/468 WN).  Leave unless the
QUESTIONS 41 rule is extended beyond Roget.

**Nits listed (not fixed)**: `ACTIVE_STATUSES`
([`roget/coverage.py`](../../assistant_axis/gapgen/generators/roget/coverage.py)) vs
`refused`; census report ([`censuses/report.py`](../../assistant_axis/gapgen/generators/censuses/report.py))
maps candidates to table rows by rank; a second selection under an existing run id accumulates
(censuses, ipip; Roget refuses); ipip partner hint when both poles share a label;
[`naming.py`](../../assistant_axis/gapgen/generators/ipip/naming.py)'s cost comment (measured
1,450 in / 326 out over 1,136 calls);
[`ingest_counts.json`](../../data/candidates/ipip/ingest_counts.json) without envelope;
`cmd_harvest --include-wn` ([`roget_generate.py`](../../data_analysis/gap_generation/roget_generate.py))
writes before refusing;
[`base_model_generator.py`](../../data_analysis/gap_generation/base_model_generator.py):237
comment now stale.

---

## Review 7: core library, pipeline, steering runner, boundary hook

Commit 12fa5ac.

**Fixed** (16, 3 new test files): **[`run_pipeline.sh`](../../pipeline/run_pipeline.sh) ignored
a failed step 2 or 3 in parallel mode and ran step 4** (no pipefail in `( step | sed ) &`);
[`2_activations.py`](../../pipeline/2_activations.py) returned 0 with a dead worker;
prefill_only configs crashed [`run_sweep.py`](../../steering/run_sweep.py) with KeyError (all
12, at launch, no GPU spend); [`steering_judges.py`](../../assistant_axis/steering_judges.py)
drain() race (a legacy scan's last strength could be left unjudged), effect future hung on a
failed records.jsonl write, MISSING counted toward the marker, blocking coherence failures
tallied; run_sweep's batch size from `RESPONSE_BATCH_SIZE` (was a literal 7), skip_threshold
fallback 1.5, worker exits 1 on a failed item; [`post_judge.py`](../../steering/post_judge.py)
`--rerun-coherence-with-model` filed the live verdict on failure;
[`generation.py`](../../assistant_axis/generation.py)'s final copy atomic (a truncated
`<role>.jsonl` was skipped forever); [`judge_pricing.py`](../../assistant_axis/judge_pricing.py)
`load_or_create` reads the envelope and warns; [`3_judge.py`](../../pipeline/3_judge.py) logs a
corrupt score file; boundary hook ([`boundary_check.py`](../../.claude/hooks/boundary_check.py)):
relative Glob climbs denied, Grep's regex not treated as a path; docstrings.

**Behaviour changes to know**: (1) a parallel-mode pipeline run now stops before step 4 on a
step 2/3 failure — past default-mode runs where step 2 or 3 failed went on to steps 4–5 (grep
the RunPod `pipeline_*.log` for [step2]/[step3] Traceback/ERROR; the post-pipeline scan would
show missing_scores/missing_activation; the October extraction has not run, so unaffected).
(2) the boundary hook now denies `../../x/*` Glob patterns and no longer denies a Grep whose
*regex* mentions a home path (its `path` is still checked).  (3) run_sweep workers exit 1 on a
failed cell: past sweeps with failed items reported success (search sweep.log for
"item 'cell' failed").

**Possible re-runs (cheap)**: legacy-unidirectional cells' last strength may have
persona/effect null → `post_judge --judges persona,effect`; `coherence_alts[m]` entries whose
`["model"] != m` are mis-filed live verdicts → re-run those.

Design issues:

#### Review 7 D1: the judge client always sends temperature and has no reasoning-effort setting

[`judge.py`](../../assistant_axis/judge.py) always sends temperature and has no
reasoning-effort setting: Haiku 5.5 / Opus 4.7+ reject temperature with a 400 that is
swallowed (every item unparseable); GPT-6 Luna would bill reasoning at default effort;
`price_for_model` ([`judge_pricing.py`](../../assistant_axis/judge_pricing.py)) lacks
gpt-6-luna (fails loudly).  Rec: a per-model capability table in judge.py used by both request
builders, failing at startup for an unknown model — before any model switch.  (Same family as
[Review 8 D3](#review-8-d3-temperature-sent-unconditionally).)

#### Review 7 D2: the refusal fallback's Haiku calls bypass the usage record

[`judge_refusal_fallback.py`](../../assistant_axis/judge_refusal_fallback.py)'s Haiku calls
bypass `usage.json` (HARD RULE; tiny cost).  Rec: optional `usage=` parameter; the caller
([`axis_judge_correlation.py`](../../results_analysis/axis_judge_correlation.py)) needs a side
tracker.

#### Review 7 D3: the steering judges' skip path overwrites already-judged scores

[`steering_judges.py`](../../assistant_axis/steering_judges.py)' skip path overwrites
already-judged persona/effect scores when reached from
[`post_judge.py`](../../steering/post_judge.py) with a lowered
`--skip-if-strength-mean-coh-above`; the runner then regenerates the stubbed strengths.  Rec:
keep existing scores unless `rerun_existing`.

#### Review 7 D4: resume regenerates a whole strength over one unparseable judgment

Resume regenerates a whole strength (K generations + judging) over one UNPARSEABLE judgment,
repeatably.  Rec: re-judge only when generation is complete.

#### Review 7 D5: boundary hook symlinks and settings files

Boundary hook ([`boundary_check.py`](../../.claude/hooks/boundary_check.py)): (a) symlinks not
resolved for the file tools (every symlink in the repo resolves inside it today); (b)
`SETTINGS_FILES` omits managed settings and `--settings`, so the Bash text scan could stand
down with no sandbox behind it.  Rec: realpath; add the managed paths at highest precedence.

#### Review 7 D6: atomic io has no fsync before replace and a per-process staging name

[`atomic_io.py`](../../assistant_axis/atomic_io.py): no fsync before `os.replace` (power loss
can leave an empty renamed file); staging name per process not per thread.  Rec: opt-in fsync
for small JSON after measuring on the pod's NFS; thread id in the staging name.

#### Review 7 D7: gsheet auth reads credentials from a directory outside the repo

[`gsheet_auth.py`](../../assistant_axis/gsheet_auth.py) reads credentials from a directory
outside the repo (sandbox denies it; [/steering-to-gsheet](../../.claude/skills/steering-to-gsheet/SKILL.md)
cannot run there; docstring wrong).  Options: gitignored path in the repo, or document as
Roger-run.

**Nits listed (not fixed)**: [`judge_score_combine.py`](../../assistant_axis/judge_score_combine.py)
docstrings say w_gs 0.5 (deliberately not edited — fingerprinted by mtime/size, an edit would
stale every consumer cache) and NaN passes isinstance; `RateLimiter`
([`judge.py`](../../assistant_axis/judge.py)) credits sleep twice (~2x rate; fixing would slow
judging); `extract_usage_anthropic` ([`judge_pricing.py`](../../assistant_axis/judge_pricing.py))
ignores cache tokens; usage `write_json` not atomic on NFS;
[`openai_batch.py`](../../assistant_axis/openai_batch.py) crash windows (billed-but-unrecorded
batch, double-charged usage); [`3_judge.py`](../../pipeline/3_judge.py) charges batch usage
under the current `--judge_model`; run_pipeline usage text;
[`rubric_equivalence.py`](../../assistant_axis/rubric_equivalence.py)'s bare-name promotion
claim (conservative false drift; "9 collisions" stale, 11);
[`arrangements.py`](../../assistant_axis/arrangements.py) malformed JSON aborts the load; tmpfs
([`tmpfs.py`](../../assistant_axis/tmpfs.py)) rsync failure deletes a shared mirror;
[`steering_runner.py`](../../assistant_axis/steering_runner.py) docstring cites a
`/Users/…/.cursor` plan.  Outside its lists: [AGENT_NOTES.md](../../AGENT_NOTES.md):2842, 2917
(B=10) and 2997–2998, 3020 (eff_stop 0.25) are stale against the code (B=7, 1/3).

Note: the reviewer's 8 test errors (HF tokenizers in
[`test_generation.py`](../../assistant_axis/tests/test_generation.py)) did not reproduce here —
1,129 passed, 0 errors.

---

## Review 1: filter side (M1, split, pins, LLM client, batches, cost, runs)

Commit a2ac553; 755 tests pass.

**Fixed** (7): [`split_runner.py`](../../assistant_axis/gapgen/split_runner.py) parsed before
recording (a raising parser lost a paid answer; no recorded hit); `_num`
([`filter_rubric.py`](../../assistant_axis/gapgen/filter_rubric.py)) accepted
NaN/Infinity/1e999 and crashed the run; `PLATFORM_PATHS`
([`runs.py`](../../assistant_axis/gapgen/runs.py)) lacked
[`arrangements.py`](../../assistant_axis/arrangements.py) (now covered — a dirty arrangements.py
refuses paid runs without `--allow-dirty`; a test scans every project import, with a `NOT_SENT`
list: [`plot_metadata.py`](../../assistant_axis/plot_metadata.py),
[`provenance.py`](../../assistant_axis/provenance.py),
[`seed_entities.py`](../../data_analysis/seed_entities.py),
[`canonical_angles/`](../../results_analysis/canonical_angles/));
[`split_rubrics.py`](../../assistant_axis/gapgen/split_rubrics.py) `bump` dropped
[`versions.json`](../trait_gap_generation/rubrics/versions.json) rows of unknown prompts and wrote non-atomically (none dropped today);
`cost_by_step` ([`split.py`](../../assistant_axis/gapgen/split.py)) ignored 1-hour cache writes
(no split call uses them); wordnet's ([`wordnet.py`](../../assistant_axis/gapgen/wordnet.py))
download guard was an `assert`; [`batches.py`](../../assistant_axis/gapgen/batches.py)
docstring.

Design issues:

#### Review 1 D1: a resume after a kill loses the killed session's spend

A resume after SIGKILL or plain `kill` loses the killed session's spend from `usage.json` and
the cap (HARD RULE).  Recorded instance:
[`data/candidates/filter/m1_validation_r2`](../../data/candidates/filter/m1_validation_r2/) —
[`responses.jsonl`](../../data/candidates/filter/m1_validation_r2/responses.jsonl) holds 13,378
charged records ($15.70) but [`usage.json`](../../data/candidates/filter/m1_validation_r2/usage.json)
says 12,261 calls / $14.07 (1,117 calls, ~$1.64 missing).  Rec: on `--resume` rebuild earlier
spend from the records (`usage_raw`, `charged_as`), take the larger, WARN on a difference; plus
a SIGTERM handler that raises SystemExit.  Also: correct m1_validation_r2's usage.json /
[`run.json`](../../data/candidates/filter/m1_validation_r2/run.json) /
[`summary.json`](../../data/candidates/filter/m1_validation_r2/summary.json) from its records
(`data/` was off-limits to the reviewer).

#### Review 1 D2: a batches-transport resume across a rubric re-pin collects under the new prompt hash

A batches-transport `--resume` across a rubric re-pin collects the old prompt's answers under
the new call's `prompt_sha256` (`custom_id` has no prompt hash).  No recorded resume crossed a
pin change.  Rec: `resume_mismatch` ([`split_cli.py`](../../data_analysis/gap_generation/split_cli.py))
refuses when `step_versions`/`prompt_sha256` differ.

#### Review 1 D3: no paid CLI refuses on rubric-version mismatches

No paid CLI refuses on `rubric_versions.mismatches()`
([`rubric_versions.py`](../../assistant_axis/gapgen/rubric_versions.py)) (classifier, probe,
plain-reading, comparison pins are checked only by the tests; the split CLI checks
split_rubrics only yet sends the probe and comparison prompts).  Rec: refuse at the start of
[`traithood_filter.py`](../../data_analysis/gap_generation/traithood_filter.py) (single),
[`split_cli.py`](../../data_analysis/gap_generation/split_cli.py),
[`plain_reading.py`](../../data_analysis/gap_generation/plain_reading.py).

#### Review 1 D4: paid CLIs without the dirty-tree refusal

Paid CLIs without the dirty-tree refusal:
[`base_model_generator.py`](../../data_analysis/gap_generation/base_model_generator.py),
[`gap_registry.py`](../../data_analysis/gap_generation/gap_registry.py) corpus-regions
(= [Review 3 D7](#review-3-d7-corpus-regions-from-descriptions-has-no-dirty-tree-check-and-records-no-git-sha)),
[`ipip_generator.py`](../../data_analysis/gap_generation/ipip_generator.py),
[`roget_generate.py`](../../data_analysis/gap_generation/roget_generate.py).  The roget $20
gate was added by review 5 (7220a37); the dirty-tree refusal is still missing in all four.
Rec: route through `platform_dirty_files` ([`runs.py`](../../assistant_axis/gapgen/runs.py))
and `confirm_or_abort` ([`cost.py`](../../assistant_axis/gapgen/cost.py)) as split_cli does.

**Nits listed (not fixed)**: `--pipeline single` takes the split's Sonnet 5.5 defaults (recorded
single runs were Sonnet 4.6: reproduce with explicit flags); `READ_OUT`/`OUT_TOK_PER_ITEM`
measured on Haiku 4.5; dirty check fails open without git (recorded in `dirty_check`);
[`judge_pricing.py`](../../assistant_axis/judge_pricing.py) `load_or_create` on a corrupt
usage.json restarts the cap at $0 (review 7 made it warn); `batches.create` not retried; a kill
between results and `save_state` re-collects (small window);
[`seed_entities.py`](../../data_analysis/seed_entities.py) left out of `PLATFORM_PATHS` on
purpose (Roger's call); minor docstring/robustness nits
([`build_validation_set.py`](../../data_analysis/gap_generation/build_validation_set.py) strata
order, [`contrast.py`](../../assistant_axis/gapgen/contrast.py) renames, whitespace
`--confirmed-by`, [`haiku55_compare.py`](../../data_analysis/gap_generation/haiku55_compare.py)
unknown model → $0, persona npz cache, mixed-list crash in `run_traithood_filter`
([`filter.py`](../../assistant_axis/gapgen/filter.py)), `--second-opinion-frac=X` form,
empty-text refusal counted as a read failure).

---

## Review 10: tools, shell scripts, one-off scripts

Commit c88c4bd; 376 tests pass.

**Fixed** (22, 8 new test files): Sheets export
([`steering_to_gsheet.py`](../../tools/steering_to_gsheet.py),
[`sheet_layout.py`](../../tools/sheet_layout.py)) merge with kept blocks (first kept block's
header/first data row merged into single cells, persona and axis rows displaced; USER_ENTERED
formulas from "-" bullets → #ERROR!; rows below a shorter grid not cleared; RP cross-rule
shaded blank cells) — re-export with `--wipe-tab` repairs a tab, online path untested;
[`diff_against_recorded.py`](../../tools/diff_against_recorded.py) offered an unverified diff
for +dirty shas (now size-checked; UNVERIFIED marked; `--history-root` replaces defaults — tests
outside the sandbox had scanned the real Cursor History);
[`mark_script_equivalent.py`](../../tools/mark_script_equivalent.py) missed payload-first
envelopes (88/1,115 under [`roger/`](../../roger/), none with edges) and mis-ordered
timestamps; [`mark_rubric_equivalent.py`](../../tools/mark_rubric_equivalent.py) stored an
empty scope list as a global wildcard edge; [`audit_caches.py`](../../tools/audit_caches.py)
could never defer a transitively stale cache; derived-layout migration
([`migrate_dataset_to_derived_layout.py`](../../tools/migrate_dataset_to_derived_layout.py))
compared top-level files only before a recursive prune (never ran; the four " copy" dirs are
still in the 4-slot dataset
[runpod_workspace/qwen/qwen-3-32b Roger/](../../runpod_workspace/qwen/qwen-3-32b%20Roger/));
[`pick_base_personas.py`](../../tools/pick_base_personas.py) overwrote the hand-edited
[`base_persona_candidates.txt`](../../roger/axis_judge_experiments/base_persona_candidates.txt)
(now backed up; May 20 file intact);
[`fill_judge_refusal_gaps.py`](../../tools/fill_judge_refusal_gaps.py) exit codes and `.env`
read on scan; [`diagnose_unparseable.py`](../../tools/diagnose_unparseable.py) read v6 only
(replayed healthy v7 batches, cents);
[`test_effect_order_bias.py`](../../tools/test_effect_order_bias.py) on v7 took the
swap-averaged score as orig (the 28 recorded swap files predate v7: unaffected), no W19
judge_label, no usage record;
[`analyse_start_strength.py`](../../tools/analyse_start_strength.py) graded at the config
s_init (all 1,209 recorded equal it);
[`rsync_pod_sweeps.sh`](../../scripts/rsync_pod_sweeps.sh)'s `--append-verify` /
`--info=stats1` are unknown to macOS openrsync (every attempt failed with exit 0) and with
rsync 3.x skip files the pod rewrote shorter — a re-pull may refresh stale local summary.json /
records.jsonl; [`rsync_completed_axes.sh`](../../scripts/rsync_completed_axes.sh) read a failed
SSH listing as "0 complete"; [`lint_kind_collision.py`](../../tools/lint_kind_collision.py)
missed list loops and `+=` (0 findings before and after);
[`png_vintage.py`](../../tools/png_vintage.py) cwd; small parsers and docstrings.

**Test expectations changed** (flag):
[`test_diff_against_recorded.py`](../../tools/tests/test_diff_against_recorded.py)'s mocked git
text now matches the recorded size (the old fixture is exactly the case the new check reports
UNVERIFIED); [`test_sheet_layout.py`](../../tools/tests/test_sheet_layout.py)'s formula-letter
helper takes the first `$COL` reference (expected sets unchanged).

**Helper deviation**: the Opus helper for the 54 one-offs ran patched copies of three scripts
([`reports/opening_forms/roles_v3_depth/analyse.py`](../opening_forms/roles_v3_depth/analyse.py),
[`w15/build_goal_tiers.py`](../../roger/pre_extraction_2026-10-09/w15/build_goal_tiers.py) and
[`_v2`](../../roger/pre_extraction_2026-10-09/w15/build_goal_tiers_v2.py)) to confirm recorded
numbers reproduce — no API calls, `$TMPDIR` only — against its read-only brief; two of its
commands were blocked by the auto-mode classifier.

Design issues:

#### Review 10 D1: the rejudge and recompute recipes are dangerous to rerun today

**The rejudge/recompute recipes are dangerous to rerun today**:
[`rejudge_after_rubric_v2.sh`](../../scripts/rejudge_after_rubric_v2.sh) (B=10, uniform q9, no
`--budget_usd`, the current-generation
[`pair_list_responses.json`](../../roger/axis_judge_experiments/pair_list_responses.json),
deletes today's correlations/gaps/plots with no snapshot, preflight passes if its `python -c`
fails); [`rejudge_after_trait_edits.sh`](../../scripts/rejudge_after_trait_edits.sh) (current
[`pair_list_di.json`](../../roger/axis_judge_experiments/pair_list_di.json) names a pole with no
vector; B=15/B=10 cohorts; pins claude-sonnet-4-6 so every sonnet-4-5 cache would be rejudged
whole, ~$4–6/axis static over ~61 axes plus ~$147/axis for the Sonnet q9 response cohort on 3
axes; no cap, real time — several hundred dollars or more);
[`run_phase5b_collision_rejudge.py`](../../scripts/run_phase5b_collision_rejudge.py) (docstring
says no-op; would rejudge all 24 cells, ~$13, overwriting May caches);
[`run_phase5a_recompute.sh`](../../scripts/run_phase5a_recompute.sh) (current pair lists; job
counts wrong).  Rec: a top-of-file guard (exit 2 unless an env var says deliberate historical
rerun) and mark each as a May 2026 record.  (Review 9b B6 makes the first two stop on a failed
pair, which they never did.)

#### Review 10 D2: the current pair lists' goal type predates the W15 goal lists

The current pair lists' `goal_type` predates the W15 goal lists (87d84fc):
[`build_pair_lists.py`](../../tools/build_pair_lists.py) dry run would shrink
[`pair_list_goalnongoal.json`](../../roger/axis_judge_experiments/pair_list_goalnongoal.json)
37 → 26 (drops [accessible](../../data/traits/instructions/accessible.json) /
[esoteric](../../data/traits/instructions/esoteric.json),
[confident](../../data/traits/instructions/confident.json) /
[uncertain](../../data/traits/instructions/uncertain.json),
[convergent](../../data/traits/instructions/convergent.json) /
[divergent](../../data/traits/instructions/divergent.json),
[ethereal](../../data/traits/instructions/ethereal.json) /
[grounded](../../data/traits/instructions/grounded.json),
[forgiving](../../data/traits/instructions/forgiving.json) /
[unforgiving](../../data/traits/instructions/unforgiving.json),
[improvisational](../../data/traits/instructions/improvisational.json) /
[methodical](../../data/traits/instructions/methodical.json),
[introverted](../../data/traits/instructions/introverted.json) /
[extroverted](../../data/traits/instructions/extroverted.json),
[passionate](../../data/traits/instructions/passionate.json) /
[dispassionate](../../data/traits/instructions/dispassionate.json),
[practical](../../data/traits/instructions/practical.json) /
[theoretical](../../data/traits/instructions/theoretical.json),
[progressive](../../data/traits/instructions/progressive.json) /
[conservative](../../data/traits/instructions/conservative.json),
[quantitative](../../data/traits/instructions/quantitative.json) /
[qualitative](../../data/traits/instructions/qualitative.json),
[reductionist](../../data/traits/instructions/reductionist.json) /
[holistic](../../data/traits/instructions/holistic.json); adds
[conciliatory](../../data/traits/instructions/conciliatory.json) /
[confrontational](../../data/traits/instructions/confrontational.json)) and change `goal_type`
on 13 [`pair_list_clean.json`](../../roger/axis_judge_experiments/pair_list_clean.json)
entries; [`pick_base_personas.py`](../../tools/pick_base_personas.py) mixes the two.  Rec:
regenerate both lists (the `_v1` copies exist) once Roger confirms the 12 drops are what W15
intended; or document; or derive at read time.  (Related:
[Review 9a D4](#review-9a-d4-the-goal-list-regenerated-2026-10-10-overlaps-the-old-on-26-of-54-traits).)

#### Review 10 D3: analyse start strength grades by a different rule than the runner stops on

[`analyse_start_strength.py`](../../tools/analyse_start_strength.py) grades
|mean(eff)| < 1/3 while the runner stops on mean(|eff|) < 0.25; the OVERRIDES table was
derived with the tool's version.  Rec: align before the next re-tune.

#### Review 10 D4: fill judge refusal gaps has no usage record and ignores the fallback provider

[`fill_judge_refusal_gaps.py`](../../tools/fill_judge_refusal_gaps.py) has no usage record
(HARD RULE, ~$0.04/run) and always uses the Anthropic client whatever `fallback_provider` says;
[`judge_refusal_fallback.py`](../../assistant_axis/judge_refusal_fallback.py) returns no usage
for unparseable replies (= [Review 7 D2](#review-7-d2-the-refusal-fallbacks-haiku-calls-bypass-the-usage-record)).

#### Review 10 D5: the Sheets OAuth scope reaches all of Roger's sheets

Sheets OAuth scope `spreadsheets` reaches all of Roger's sheets; `drive.file` covers the app's
own.  Least privilege.

#### Review 10 D6: defer rejudge defaults to the uncategorized category

[`defer_rejudge.py`](../../tools/defer_rejudge.py) defaults to `--category uncategorized`,
which [`audit_deferrals.py`](../../tools/audit_deferrals.py) reports as an error; require the
flag.

#### Review 10 D7: the rsync scripts hard-code the pod address and disable host-key checking

Rsync scripts ([`rsync_pod_sweeps.sh`](../../scripts/rsync_pod_sweeps.sh),
[`rsync_completed_axes.sh`](../../scripts/rsync_completed_axes.sh)): hard-coded pod IP/port,
`StrictHostKeyChecking=no`.  Rec: `accept-new` plus env vars.

#### Review 10 D8: AGENT NOTES claims manifest regeneration is byte-identical

[AGENT_NOTES.md](../../AGENT_NOTES.md):2070 claims manifest regeneration is byte-identical
(`manifest_generated_at`, `elapsed_ms` change; audits compare subtree hashes, harmless); :1799
names the field `generated_at`.

#### Review 10 D9: apply deferrals with several drifted inputs passes a null dep key

`apply_deferrals` ([`audit_caches.py`](../../tools/audit_caches.py),
[`audit_pngs.py`](../../tools/audit_pngs.py)) with several drifted inputs passes `dep_key=None`,
which matches any dep_key-scoped entry (0 such entries today).  Rec: require every drifted key
covered.

#### Review 10 D10: audit pngs has no transitive staleness

[`audit_pngs.py`](../../tools/audit_pngs.py) has no transitive staleness (a plot of a stale
cache reads current); documented as caches-only.

**One-offs dangerous to rerun (not edited)**:
[`roger/chunk4_2026-10-07/apply_edits.py`](../../roger/chunk4_2026-10-07/apply_edits.py) (paid
`--force` regeneration; reverts 7 stems changed since); both `fold_review.py`
([chunk4](../../roger/chunk4_2026-10-07/fold_review.py),
[chunk5](../../roger/chunk5_2026-10-08/fold_review.py)) (revert queue descriptions, move
entries back to ready);
[`seed_wave2_batch1.py`](../../roger/pre_extraction_2026-10-09/seed_wave2_batch1.py) /
[`wave2_batch2.py`](../../roger/pre_extraction_2026-10-09/wave2_batch2.py) (set entries back
to ready; the latter crashes on the renamed savage, which has no file under that name);
[`rewrite_and_check.py`](../../roger/pre_extraction_2026-10-09/rewrite_and_check.py)
(non-atomic corpus writes);
[`build_goal_tiers.py`](../../roger/pre_extraction_2026-10-09/w15/build_goal_tiers.py) and
[`_v2`](../../roger/pre_extraction_2026-10-09/w15/build_goal_tiers_v2.py) (overwrite the
proposal file); probes with an output directory overwrite unguarded.  Latent bugs with no
reported effect listed in the report
([probe_last_step](../trait_gap_generation/probe_last_step/), silent retry drops, positional
zips, `name_check` keyed by bare stem).  Note:
[`probe_alignment_graded/run.py`](../trait_gap_generation/probe_alignment_graded/run.py) cannot
have produced the haiku55/opus55 records (that producer is not in the repo).

**Nits listed (not fixed)**: [`sync_agent_notes.py`](../../tools/sync_agent_notes.py)
fence/marker edge cases; lint default walk
([`lint_kind_collision.py`](../../tools/lint_kind_collision.py)) includes `.claude/worktrees`
and skips `roger/`; kept Sheets rows re-read as formatted values;
[`audit_rubric_versions.py`](../../tools/audit_rubric_versions.py) reports frozen `__rubric_v1`
snapshots as drifted; [`audit_deferrals.py`](../../tools/audit_deferrals.py) `Path.glob` vs
`fnmatch`; [`dry_run_response_token_count.py`](../../tools/dry_run_response_token_count.py) p95
off by one; [`analyze_dose_response.py`](../../tools/analyze_dose_response.py) docstring;
[`rsync_completed_axes.sh`](../../scripts/rsync_completed_axes.sh) never re-pulls a complete
axis; [`test_boundary_check.py`](../../tools/tests/test_boundary_check.py) "FourFalsePositives"
lists 3.

---

# Pipeline review: five reviewers on the activation-extraction pipeline

## P1: step 1, generation

Commit cc49023; 18 pass + 8 HF-cache errors.  Files:
[`1_generate.py`](../../pipeline/1_generate.py), [`generation.py`](../../assistant_axis/generation.py).

**Fixed** (5 + nits): a step-1 worker that failed to load the model or was killed exited 0 and
no exit code was checked (step 1 "succeeded" with entities missing; no recorded instance);
`--roles` silently ignored outside `--roles_only`/christina (manual runs only); `/tmp` staging
file shared across processes (the 11 shared names could cross; checked: none did);
instruction/question reads without the NFS retry (silent entity drop; none recorded); double
log lines; traceback on item errors.

**Test expectations changed** (flagged): the copy-dies-half-way test asserts the kept staging
copy instead of deleting a fixed `/tmp` name; the complete-save test asserts an empty staging
dir and the file mode.

Design issues [the tally has no P1 D6]:

#### P1 D1: per-item failures keep exit 0

Per-item failures keep exit 0: a vLLM engine that dies mid-run fails every remaining item fast,
step 1 exits 0, the driver continues with a partial response set, and
[`scan_missing_vectors.py`](../../pipeline/scan_missing_vectors.py) (which starts from
activations) never sees the gap.  Rec: finish the others then exit 1 if any failed, abort after
K consecutive failures (step 3's pattern); decide step 2's per-item policy the same way.

#### P1 D2: resume skips any entity whose file exists

Resume skips any entity whose file exists, with no check of instructions, sampling or question
set.  Measured: all 554 trait/role response files in 8slot were generated from instructions
that have since changed; 28 stems left the corpus.  Rec: fresh output directory per extraction
(rule, now) + a `generation_config.json` side-car (a file beside each run's responses, not yet
written anywhere; its schema is in
[coding_plan_multi_model_extraction.md](../pipeline/coding_plan_multi_model_extraction.md)
§ 7) and per-entity instruction hash (record).

#### P1 D3: responses carry no finish reason, thinking flag, seed or question id

Responses carry no `finish_reason` (~71% hit the 512-token cap), no thinking-stripped flag, no
seed, no question id (`question_index` is a position in the reduced list).  Rec: additive
fields before the October extraction; seed optional.

#### P1 D4: the thinking strip handles only a leftover think tag

The thinking strip handles only a leftover `</think>`; 473 of ~1.19M recorded responses look
like leaked thinking (168 scored 3); all enter the unfiltered vectors/axis; negligible on
means.  Rec: flag via [D3](#p1-d3-responses-carry-no-finish-reason-thinking-flag-seed-or-question-id),
leave the data.

#### P1 D5: eager imports in the package init

[`assistant_axis/__init__.py`](../../assistant_axis/__init__.py) eager imports:
`import assistant_axis.entity_id` = 1.3 s and ~2,100 modules (torch, pyplot, sklearn, scipy,
plotly) vs <10 ms alone; five files carry a stand-in-package workaround
([`3_judge.py`](../../pipeline/3_judge.py),
[`compute_combo_marginals.py`](../../results_analysis/compute_combo_marginals.py),
canonical_angles [`data.py`](../../results_analysis/canonical_angles/data.py) /
[`core.py`](../../results_analysis/canonical_angles/core.py),
[`test_gapgen_calibrate.py`](../../assistant_axis/tests/test_gapgen_calibrate.py)).  Rec:
PEP 562 lazy `__getattr__` keeping `__all__` (101 top-level import sites), test that
[`entity_id.py`](../../assistant_axis/entity_id.py) loads no torch, retire the workarounds.

#### P1 D7: a missing goal-list name is only a WARNING

A goal-list name with no instruction file is a WARNING and the grid silently shrinks below
goal_count × non_goal_count; `renamed_from` not resolved (today 0 missing).  Rec: fail fast.

#### P1 D8: a second BOS on Gemma or Llama from text prompts

(Latent, non-Qwen.)  Text prompts from `apply_chat_template(tokenize=False)` to vLLM may get a
second BOS on Gemma/Llama; Qwen3 has no BOS.  Check before any Gemma/Llama run.

**Outside its list (relayed)**: [`2_activations.py`](../../pipeline/2_activations.py):450
worker fatal error still exits 0 (sent to P2); [`run_pipeline.sh`](../../pipeline/run_pipeline.sh)
usage text (P4 brief); [`pipeline/README.md`](../../pipeline/README.md) step-1 counts and flag
table stale (932 traits, 339 roles + default, ~2,733 roger entities; flags `--no_traits` /
`--traits_only` / `--roles_only` / `--combos_only_r/t` / `--reduce_questions` / `--max_tokens` /
`--temperature` / `--top_p` / `--max_model_len` / `--gpu_memory_utilization` missing);
[`3_judge.py`](../../pipeline/3_judge.py):305,333,737 and the
[trait-pairs rule](../../.claude/rules/trait-pairs.md) say `r_<role>_t_<trait>` but the form is
`r_<role>__<trait>` (docs only); [AGENT_NOTES.md](../../AGENT_NOTES.md) nfs-io call-site list
should add [`generation.py`](../../assistant_axis/generation.py) reads.

**Nits listed**: `trust_remote_code=True` for any model; `supports_system_prompt` renders the
template per conversation (~1M times); thinking disabled by the substring "qwen" (a local path
name would think; step 2 same test); empty pos = no system prompt (only default p0, on
purpose); `int()` on `CUDA_VISIBLE_DEVICES` breaks with UUIDs; leftover `.inprogress` files
never cleaned (harmless: readers glob `*.jsonl`); `get_config` docstring omits `capping_*`
keys.

**Schema**: step 1 writes `system_prompt`, `prompt_index`, `question_index`, `question`, `label`
("pos"), `conversation` (+ `role`, `trait`, `goal_source` for combinations); steps 2 and 3 key
on `{label}_p{pi}_q{qi}`; no disagreement.  9 empty combination responses scored 0 or unscored,
never reach step 4.

## P5: end-to-end contracts

Read-only, Fable; 153 tests pass on the pipeline test files.

**Verified on the 8slot tree**: every sampled entity has exactly 500 response keys = 500 score
keys; vectors and axes (8, 64, 5120) bf16 with `header_tokens`
`['<|im_start|>','assistant','\n','<think>','\n\n','</think>','\n\n']`; slot 0 = mean over
response tokens, slots 1..7 = the header-token positions; layer index i = output of decoder
block i (0..63), NOT the embeddings; stems are `[a-z0-9_]+` with `r_`/`t_` and `__` reserved;
the 11 collision names are kept apart only by the per-type directory + `--entity_type`;
`renamed_from` is consulted by no pipeline step; `custom_id` = `stem|key`.

**Contract disagreements**: step 2 skips malformed JSONL lines while step 3 aborts the whole
batch run on one ([#6](#p5-6-step-3-jsonl-reader)); step 2 silently drops a response with an
empty assistant span (step 4 intersects — tolerated); think-leak stripping stores cleaned text
so activations are of text the model did not see (by design); `--layers` / `--max_length` /
`--thinking` / `--batch_size` not in metadata ([#14](#p5-14-metadata-omits-layers-and-the-rest));
christina min_count 50 vs scan 30 ([#11](#p5-11-christina-min-count)).

**Resume story**: exit codes now propagate for the parallel 2/3, but step 1 (fixed by P1
today), step 4 (returns 0 with N failed) and step 3 in `--no_batch` / HIGH FAIL RATE never exit
non-zero on partial failure; **a vector computed from a partial score file is kept forever and
the scanner marks it ok** ([#3](#p5-3-partial-score-vectors-kept-forever), high); the
documented recovery `4_vectors.py --overwrite missing_vectors_rerun.txt` does not exist
([#5](#p5-5-the-nonexistent-overwrite-list-recovery)); every skip test is file-existence only,
so **the October extraction must use a fresh OUTPUT_DIR** (reusing the May tree would keep 580
old entities' May responses as "already exists").

**October extraction arithmetic to confirm**: on disk 932 traits + 339 roles + default + 1,800
combinations = 3,072 entities, 1,536,000 responses → ~1.5M judge calls (the "600,000" in
[CLAUDE.md](../../CLAUDE.md) is roles + traits only, 635,500); ≈ $330 at batch rates ($140
roles+traits), double in real time; activations 3,072 × 2.62 GB ≈ 8.0 TB (driver comment says
4.7 TB for 1,800 combos) → waves by `--types` and delete activations after vectors verify
(scanner then reports them orphan_vector, [#22](#p5-22-orphan-vector-conflation)); GPU time
from April logs ≈ 110 (step 1) + 50 (step 2) GPU-hours, far over the 13 GPU-hour line; ~154
batch chunks of 10,000, serial if the org queue limit is 20M tokens; `/dev/shm` must hold the
47 GB model + 4 × 2.6 GB staging.  Names: every W15 top-30 has a file, none in both lists;
[`combination_scores.json`](../../data/combination_scores.json) covers the grid exactly (1800)
and excludes 3 variants.  Nothing records generation/extraction parameters, the git sha,
instruction/questions hashes, the combination_scores version, or which stems entered each axis;
`MANIFEST.json` ([the 8slot one](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/MANIFEST.json))
is not written by the driver.

**Findings relayed to the step reviewers** (owner in brackets):

#### P5 #1: step-1 exit code

Done, cc49023.

#### P5 #2: step-2 live-worker failure exits 0 and is invisible to the scan

(P2 + P4.)

#### P5 #3: partial-score vectors kept forever

(P4, design high.)

#### P5 #4: JSONDecodeError logged as min-count skip

(P4.)

#### P5 #5: the nonexistent overwrite-list recovery

The nonexistent `--overwrite <list>` recovery (P4).

#### P5 #6: step-3 JSONL reader

(P3.)

#### P5 #7: no-batch ignores in-flight batches

`--no_batch` ignores in-flight batches (P3).

#### P5 #8: token-limit rejection re-uploads and leaks files

(P3.)

#### P5 #9: create and save-state crash window

`create` / `_save_state` crash window (P3).

#### P5 #10: realtime failures exit 0

(P3.)

#### P5 #11: christina min count

christina min_count (P4).

#### P5 #12: end-of-run tally misses steps 4, 5 and the scan

(P4.)

#### P5 #13: cwd is the pipeline directory

cwd = `pipeline/` (P4).

#### P5 #14: metadata omits layers and the rest

(P2.)

#### P5 #15: the default substring

"default" substring (P4).

#### P5 #16: axis 2D helpers dead and stale

[`axis.py`](../../assistant_axis/axis.py) 2D helpers dead and stale (P4).

#### P5 #17: double-formatted templates, braces

(P3.)

#### P5 #18: incongruity filter never checks pairs sha256

The incongruity filter never checks `pairs_sha256` (P3, design).

#### P5 #19: bf16 three times before a difference of close means

**bf16 three times before a difference of close means** (P2/P4, design: recommend float32 at
steps 4/5 now that the corpus is re-extracted).

#### P5 #20: axis records no counts or stems

(P4.)

#### P5 #21: unparseable keys resubmitted forever

(P3.)

#### P5 #22: orphan vector conflation

`orphan_vector` conflation (P4).

#### P5 #23: rubric stamp before judging

(P3.)

#### P5 #24: score responses max tokens 10 trap

`score_responses` `max_tokens=10` trap (P3).

#### P5 #25: missing goal-list name only a WARNING

(= [P1 D7](#p1-d7-a-missing-goal-list-name-is-only-a-warning).)

#### P5 #26: two tmpfs mirror implementations

(P4.)

#### P5 #27: README counts stale

(Docs.)

## P2: step 2, activations and internals

Commit 11d7f28; 50 tests pass.  Files: [`2_activations.py`](../../pipeline/2_activations.py),
[`internals/model.py`](../../assistant_axis/internals/model.py),
[`internals/spans.py`](../../assistant_axis/internals/spans.py),
[`internals/conversation.py`](../../assistant_axis/internals/conversation.py),
[`internals/activations.py`](../../assistant_axis/internals/activations.py).

**Fixed** (5): transformers-5 `BatchEncoding` → no spans → nothing saved, entity "success"
(latent; pod pinned to 4.57.6; Mac has 5.1.0; a run between 2026-02-10 and 04-05 would have
left missing, not wrong, files); worker fatal error / role exception exited 0 (two real
incidents in the 8slot logs, both hand-repaired at the time); a role with no extractable
activation counted as success; unknown model family silently changed the layout; metadata now
records `layers` / `max_length` / `thinking` / `batch_size` / `extract_headers` (additive).

**What step 2 computes** (verified on a fake model and the vector metadata): slot 0 = mean over
the response's content tokens (first to last non-whitespace; excludes header, empty think
block, `<|im_end|>`, final `\n`); slots 1–7 = the single positions of `<|im_start|>`,
`assistant`, `\n`, `<think>`, `\n\n`, `</think>`, `\n\n`; layer j = output of decoder layer j
(HF `hidden_states[j+1]`), same module steering hooks — no off-by-one; right-padded,
max_length 2048; 9 entities saved 499 (empty responses); 0 header misses in the 8slot run.

**Precision** (answer to [P5 #19](#p5-19-bf16-three-times-before-a-difference-of-close-means)):
the span mean already accumulates in float32 (PyTorch bf16 reductions) and rounds once to bf16
— bit-identical to an explicit float32 mean on CPU; storing per-response means as float32 would
double the activation files (2.6 → 5.2 GB per entity) for little gain (their roundings average
out ~1/√N over 250–500 responses).  The roundings that matter are downstream: the stored
per-entity bf16 mean (rms rounding 0.29–0.39 at layer 32 against trait-minus-default difference
norms of 36–67, i.e. ~0.4–0.9% per stored mean) and step 5's bf16 subtraction.  Rec: float32 at
steps 4 and 5 (P4's side); leave step 2.

Design issues:

#### P2 D1: layers flag accepts negative, duplicate or unsorted values

`--layers` accepts negative, duplicate or unsorted values (now recorded in metadata).  Rec:
validate sorted, unique, in range.

#### P2 D2: thinking flag silently adds the header tokens to the body mean

`--thinking true` silently adds the five header/think tokens to the body mean (measured on the
fake: mean position 31.5 vs 34) and duplicates them in slots 1–7; step 1 never generates with
thinking on.  Rec: remove the flag.

#### P2 D3: header token list hard-coded and the family detected by substring

The header token list is hard-coded and the family is detected by "qwen" in the model name: a
template without the think block (Qwen3 Instruct-2507) NaNs every header slot (loud); a local
path without "qwen" drops the header slots (now warns).  Rec: derive the header ids from the
tokenizer at startup (`template([user], add_generation_prompt=True, enable_thinking=False)`
minus `template([user])` — exactly what step 1 rendered) and fail if they differ from
`_HEADER_TOKENS`; family from `model.config.model_type`.

#### P2 D4: assistant turns picked by parity, not by span role

Assistant turns picked by parity (`1::2`), not by span role; fine for the single-turn contract.
Rec: assert exactly one assistant span per conversation.

**Nits listed**: the full forward pass computes logits for every position then discards them,
and layer outputs are held then copied by `torch.stack` (2× memory); `StopForward`
([`internals/exceptions.py`](../../assistant_axis/internals/exceptions.py)) exported, never
raised; worker log lines printed twice and never reach `activations.log` (they are in
`pipeline_*.log`); DEBUG span prints ~2,000 lines per run; spans built twice per batch;
[`model.py`](../../assistant_axis/internals/model.py) sets `padding_side="left"` while batching
pads right (correct, misleading); docstring documents an ignored `device=` arg; `generate()`
double BOS on Gemma/Llama (unused by the pipeline); bare `except:` clauses and duplicate span
logic not on the real path; HF-cache check ignores `HF_HUB_CACHE`; GPU UUIDs break `int()`
parsing (loud).  Outside its list: [`run_pipeline.sh`](../../pipeline/run_pipeline.sh):125,
:253 comments say step 2 "exits 0 even when some workers died" (false since 12fa5ac);
[README](../../pipeline/README.md) step 2 says "unchanged from original" and does not describe
the 8-slot layout.

## P3: step 3, judging

Commit 56f3df3e; 298 tests pass.  Files: [`3_judge.py`](../../pipeline/3_judge.py),
[`openai_batch.py`](../../assistant_axis/openai_batch.py), [`judge.py`](../../assistant_axis/judge.py).

**Fixed** (17, 24 tests): **lost scores** (`load_scores` swallowed OSError → a transient NFS
read during a merge overwrote the entity's score file with the newest scores only); **double
submission** (crash between `batches.create` and the state write resubmitted the chunk; now the
upload id is recorded first and resume adopts the batch via `batches.list`); queue-limit
refusals re-uploaded the chunk every retry and never deleted rejected uploads; chunk names
stamped to the second (a rerun in the same second took over the old record); one failed
retrieve/download killed an hours-long run (now retried, give up after 30 failed rounds);
result files split at U+2028/U+0085; a resumed batch refused by the queue raised instead of
re-queuing; repeated response key → repeated `custom_id` (fails validation); an
unpriced/non-OpenAI judge model raised inside the usage tracker after paying; relative
`--roles_dir`/`--traits_dir` defaults, missing instruction dir, silently-disabled incongruity
filter; responses read without retry and a malformed line aborted the batch run; braces in
corpus text; `--no_batch` re-judged live what in-flight batches were answering (now refuses);
parse rate < 99% or a failed entity exited 0 (now exit 1; fully-excluded combination =
skipped); rubric stamp before judging; `SCORE: 4` fell back to a reasoning digit;
`score_responses` max_tokens 10 → 200.

**Behaviour change**: step 3 exits 1 on low parse rate / failed entity (files kept; rerun
judges the missing); `--no_batch` refuses with uncollected batches.

Design issues:

#### P3 D1: a reply without a SCORE marker is scored from a digit of its reasoning

A reply without a `SCORE:` marker (truncated at max_tokens 200, or off-format) is scored from
the last 0–3 digit of its reasoning ("…lists 3 examples" → 3), feeding step 4's score==3
filter; `finish_reason` is available.  Rec: log counts of marker-less and length-truncated
replies now; for October require the marker and treat `length` as unparsed (bumps
`JUDGE_RUBRIC_VERSION`).

#### P3 D2: the SDK retries batch creation without an idempotency key

openai 2.17.0 retries POSTs twice on timeouts with no idempotency key, so a lost create
response can still make a duplicate batch (~$2 per occurrence).  Options: accept; create with
`max_retries=0` and look up by `input_file_id`; cancel extras sharing the upload.

#### P3 D3: no lock against two step-3 runs on one scores dir

No lock against two step-3 runs on one scores dir (the second's resume deletes the first's
unsubmitted chunks; both collect the same batches).  Rec: `O_EXCL` lock file with PID/host,
`--force_unlock`.

#### P3 D4: usage and the fallback use the current judge model after a resume

(Known.)  Usage and the fallback use the current `--judge_model` after a resume.  Rec: refuse
when an in-flight chunk's body names another model.

#### P3 D5: throughput is serial chunk submission and validation

Chunks are submitted and validated serially; after a split every later full-size chunk
rediscovers the queue limit by trial; ~154 chunks for the full grid.  Rec: set
`--batch_requests` from the org's queue limit so 2–3 chunks fit, or submit all and check
validation in the poll loop.

#### P3 D6: role rubric artefacts in all 339 role eval prompts

**Role rubric artefacts in all 339 role eval_prompts**: "Gemma, an LLM", "altruistic AI for
the role [altruist](../../data/roles/instructions/altruist.json)", "((an AI" (TODO at
[`3_judge.py`](../../pipeline/3_judge.py):234).  Every role is re-judged in October, so fixing
now costs nothing extra; later ~$36–38.  Needs Roger.

#### P3 D7: the incongruity filter never checks the combination scores' pairs sha256

The incongruity filter never checks
[`combination_scores.json`](../../data/combination_scores.json)'s `pairs_sha256` against the
instruction pair step 1 used.  Rec: recompute and warn (fail for combinations).

#### P3 D8: no overwrite flag, a rubric bump only warns, unparseable keys re-sent

No `--overwrite`; a rubric bump only warns; persistently unparseable keys re-sent on every
rerun.  Low priority for a fresh tree.

**October checklist (step 3)**: 1,535,200 requests — traits 466,000 (~$86–90), roles 169,500
(~$36–38), combinations 899,700 (~$182–189) → **~$305–320 at batch rates** (o200k counts of
1,760 real prompts; output 70–80 tokens), double in real time; defaults gpt-4.1-mini,
max_tokens 200, temperature 1, batch_requests 10,000, fallback_max 2,000, poll 60 s,
requests_per_second 100 (fallback only; above tier-1 RPM); read the org's gpt-4.1-mini batch
queue limit (grid ≈ 1.09B prompt tokens; a 10k chunk 6.5–7.9M) and size `--batch_requests` to
it; chunk files ≈ 1.7 + 0.7 + 3.3 GB on `/workspace`; a one-entity canary against the real API
(`custom_id` format, `token_limit_exceeded` code, `batches.list` ordering newest-first); rubric
decisions [D1](#p3-d1-a-reply-without-a-score-marker-is-scored-from-a-digit-of-its-reasoning) /
[D6](#p3-d6-role-rubric-artefacts-in-all-339-role-eval-prompts) with a `JUDGE_RUBRIC_VERSION`
bump; fresh scores dirs; one process per scores dir; afterwards exit 0, parse-rate line,
`usage.json` per type, scanner.

**Cross-file (relayed/done)**: [`atomic_io.py`](../../assistant_axis/atomic_io.py)
`read_jsonl_with_retry` `splitlines` → `split("\n")` (fixed by the coordinator);
[`axis_judge_correlation.py`](../../results_analysis/axis_judge_correlation.py):2331 globs
`scores_dir/*.json` into the provenance fingerprint, pulling in `usage.json` /
`judge_rubric.json` / `batch_state.json` → false staleness (exclude `SIDE_CAR_FILENAMES`;
results_analysis side); [README](../../pipeline/README.md) / [AGENT_NOTES](../../AGENT_NOTES.md)
updates (docs agent).

**Nits**: `RateLimiter` double credit (known); `usage.charge` inside the try in
`call_judge_single` ([`judge.py`](../../assistant_axis/judge.py)) (a pricing error discards a
paid reply for other callers); first `SCORE:` marker wins; chunk file left after a non-token
validation failure; chunk paths stored relative; summary logs errors at INFO.

## P4: steps 4 and 5, the scanner, the driver, file IO

Commit ba4efef2; 99 tests + P2's contract test pass.  Files:
[`4_vectors.py`](../../pipeline/4_vectors.py), [`5_axis.py`](../../pipeline/5_axis.py),
[`scan_missing_vectors.py`](../../pipeline/scan_missing_vectors.py),
[`run_pipeline.sh`](../../pipeline/run_pipeline.sh), [`atomic_io.py`](../../assistant_axis/atomic_io.py),
[`axis.py`](../../assistant_axis/axis.py), [`tmpfs.py`](../../assistant_axis/tmpfs.py).

**Fixed** (30): **`torch_save_with_retry` verified after the rename** (a crash during the
minute-long verification left unverified bytes under the final name, taken as done by every
skip-if-exists; a save failing every attempt deleted the previous good file on `--overwrite`) —
now verify on `.inprogress` then `os.replace`; `UnpicklingError`/`ValueError` in verification
retried and cleaned; tmpfs failed-rsync no longer removes a pre-existing mirror; 4_vectors exit
1 on failures (April 19/26/29, May 3 failures were marched into step 5), garbage activation no
longer crashes the step, corrupt scores JSON an ERROR not a min-count skip, 0-byte placeholders
skipped (265 s each), vanished files pre-checked (13 cost ~57 min on 05-03), `torch.stack([])`
guarded, exact default name, `--overwrite [FILE]` (the documented form was an argparse error),
vectors carry `inputs` (scores sha256/size/count, n_scored, n_score3_used, min_count,
reduce_questions, created_at); 5_axis exact default, `axis.pt` records inputs (vectors_dir,
stems, n_default, n_entities); scanner: peer median ignored 0-byte placeholders, exit 3 on
rerun candidates (05-03 ended with 870 and no remark), atomic writes, `responses/` as the
universe (missing_activation reachable; r_zealot__pensive
([zealot](../../data/roles/instructions/zealot.json),
[pensive](../../data/traits/instructions/pensive.json)) — 3 score=3, activation deleted — was
invisible and explains the 1,793rd missing combination), `vector_only` vs `orphan_vector`;
driver: end-of-run summary counts steps 4/5/scan [ERROR] lines (18 in the 05-03 log, summary
empty), christina min_count 50 to both step 4 and scan, tmpfs copy staged + `mv -T` (an
interrupted `cp -r` was reused forever — delete any partial
`/dev/shm/hf-cache/hub/models--Qwen--Qwen3-32B` before October), pkill advice, `step_failed`
names the step, cwd guard; [`axis.py`](../../assistant_axis/axis.py) `save_axis` atomic,
slot/layer conventions documented.

**Behaviour changes**: driver stops before step 5 on a step-4 failure; scanner exit 3 reported;
script refuses to start outside `pipeline/`.

**Measured**: **bf16 axis vs float32 recomputation from the same stored vectors: roles median
relative error 1.3%, max 5.3%; traits 1.5% / 6.3%; cosine ≥ 0.998** (the axis norm is ~14% of
the role-mean norm, so the one bf16 rounding of the role mean, ~0.2%, is amplified ~7×; the
default vector's own storage adds a similar amount — estimate).
[`traits/axis.pt`](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/traits/axis.pt)
(05-02) is stale against
[`traits/vectors/unhelpful.pt`](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/traits/vectors/unhelpful.pt)
([unhelpful](../../data/traits/instructions/unhelpful.json); 05-04): max diff 8 bf16 units,
cosine ≥ 0.998; nothing references it.
[`roles/axis.pt`](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/roles/axis.pt)
verified bit-for-bit against a recomputation.  Three axes exist (roles/, traits/,
[combinations/](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/combinations/axis.pt)),
no root axis; combinations' axis averages `r_` and `t_` together (1,793 entities).

Design issues:

#### P4 D1: bf16 numerics

(= [P5 #19](#p5-19-bf16-three-times-before-a-difference-of-close-means).)  Options: (a)
accumulate and store float32 at steps 4 and 5 (~10.5 MB per vector, ~25 GB total); (b)
accumulate float32 at step 5, store bf16; (c) leave.  Rec: (a), since October re-extracts; at
least (b).  Check steering casts an f32 axis to the model dtype
([`run_sweep.py`](../../steering/run_sweep.py):636-638 returns `axis_raw[slot, layer]` as
stored).

#### P4 D2: step 5 averages every vector file in the directory

Step 5 averages every `*.pt` in the directory: no entity filter, no minimum count; a reused
directory would average old-stem vectors in ([AGENT_NOTES](../../AGENT_NOTES.md) names
slothful/factual/risk_taking/nonchalant; aligned_artificial_intelligence likewise; none of
these has an instruction file under that name).  Rec: restrict to stems with a responses file,
warn about the rest, require n_entities ≥ a fraction.

#### P4 D3: recompute rule for vectors from partial scores

Recompute rule for vectors from partial scores (inputs now recorded).  Rec: skip-if-current —
recompute when the scores file's sha256 differs from `inputs`; May vectors without `inputs`
treated as current; a `stale_vector` scanner status.

#### P4 D4: layers in metadata

(Done by P2.)  Layers in metadata — step 5 should treat a missing `layers` as "all" when it
adds the agreement check.

#### P4 D5: FileNotFoundError is retried as transient

`FileNotFoundError` is retried as transient (265 s per missing file; ~57 min lost on 05-03).
Rec: exclude it (ESTALE is a different errno) — a change to the documented
[nfs-io rule](../../.claude/rules/nfs-io.md).

#### P4 D6: christina mode with traits has no default vector

christina mode with traits has no `default.json`, so step 5 always fails loudly.  Options:
symlink the roles default ([default](../../data/roles/instructions/default.json)); skip step 5;
document.

#### P4 D7: two tmpfs mirror implementations

Two tmpfs mirror implementations (shell `cp` without marker; Python rsync with marker,
[`tmpfs.py`](../../assistant_axis/tmpfs.py)).  Rec: the driver calls the Python helper.

#### P4 D8: question-matched filtering unchanged

Question-matched filtering ([README](../../pipeline/README.md) limitation) unchanged.

**Nits**: `append_jsonl` reads without retry; `--no-tmpfs --tmpdir X` ignores `--tmpdir`;
`tee` async so the summary grep can miss last lines; GPU check `-gt` errors on "[N/A]";
`--scores_dir` ignored with `--root`; cached vs uncached any-finite differ; `vectors_4slot`
paired with 8-slot activations (provenance mismatch the scanner can't see);
`setup_model_tmpfs_cache` ([`tmpfs.py`](../../assistant_axis/tmpfs.py)) hard-codes
`/dev/shm`; rsync timeout 1800 s may be short for 65 GB; `compute_axis` /
`aggregate_role_vectors` ([`axis.py`](../../assistant_axis/axis.py)) mean not nanmean (no
callers); step 5 always recomputes while the README says every step skips; two atomic_io tests
sleep 25 s each.

**Scanner on the local 8slot tree** (shallow, outputs in scratch): roles 1 truncated local copy
([`hacker.pt`](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/roles/activations/hacker.pt),
[hacker](../../data/roles/instructions/hacker.json), 131 MB partial), 279 vector_only; traits
302 vector_only; combinations 1 truncated
([`r_activist__abstract.pt`](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/combinations/activations/r_activist__abstract.pt),
[activist](../../data/roles/instructions/activist.json) /
[abstract](../../data/traits/instructions/abstract.json)), 3 missing_scores
(incongruity-excluded), 4 below_min_count, 1,792 vector_only.  May 4 pod audits: combinations
895 ok / 3 / 3 / 899 orphan (activations deleted); traits/vectors_4slot 7 "mysterious" (never
redone for the edited traits); roles 111 placeholders.

---

# Decisions so far (Roger, 2026-10-12, in the walk-through)

The letters and numbers in this section are the walk-through's own (A, B, D, E and P lists),
not the review groups' D-numbers above.  Where a decision's text names the item it settles, the
review label is added in square brackets; where it does not, no mapping is guessed.

- **A1** approved: top-of-file guard (exit 2 unless `HISTORICAL_RERUN=1`) on the four
  rejudge/recompute recipes; [`rejudge_after_rubric_v2.sh`](../../scripts/rejudge_after_rubric_v2.sh)
  snapshots instead of deleting; [`rejudge_after_trait_edits.sh`](../../scripts/rejudge_after_trait_edits.sh)
  gets `--budget_usd`.  Nothing fingerprints the recipes (checked).
  [[Review 10 D1](#review-10-d1-the-rejudge-and-recompute-recipes-are-dangerous-to-rerun-today)]
- **D1**: relabel done in the notes (2e2f1a25); the May 6 four-slot/K-near-N figure is the
  source of the old reading; neither the May 9 file nor the true-winner rebuild shows the
  collapse.  Approved for the batch: record per-cell nth_pc winners for all 7 cells in
  [`klm_sweep.py`](../../results_analysis/pc_round_trip/klm_sweep.py), stop
  [`winner_decomposition.py`](../../results_analysis/pc_round_trip/winner_decomposition.py)
  skipping slots 0/3 and (6,49), regenerate and retitle the figure ($0, CPU-hours: estimate
  first); then re-read the ~12 boundary and reconsider.
  [[Review 9b D2](#review-9b-d2-winner-decomposition-decomposes-the-nth-pc-at-the-fixed-principled-winners-cell)]
- **D2** noted (retune coming anyway).  **D3**, **D4**, **D6** (find out which soft_K the
  recorded runs used), **D7** agreed.
- **D5**: parser change (marker required; None when absent or multiple) + `RUBRIC_VERSION` v4 →
  v5 with a rubric-equivalence edge and a script-equivalence mark; the two marker-less batches
  hand-edited to None on 2026-10-12
  ([analytical](../../data/traits/instructions/analytical.json) /
  [progressive](../../data/traits/instructions/progressive.json)_vs_[conservative](../../data/traits/instructions/conservative.json)
  b10; [presenter](../../data/roles/instructions/presenter.json) /
  [relativist](../../data/traits/instructions/relativist.json)_vs_[absolutist](../../data/traits/instructions/absolutist.json)
  b7), backups and envelope notes in place.  Same strictness for
  [`3_judge.py`](../../pipeline/3_judge.py) (`JUDGE_RUBRIC_VERSION` 2 → 3) with P4's other
  rubric changes.
  [[Review 9a D6](#review-9a-d6-parser-falls-back-to-the-first-integer-when-there-is-no-score-line),
  [P3 D1](#p3-d1-a-reply-without-a-score-marker-is-scored-from-a-digit-of-its-reasoning)]
- **Open**: D8–D12, E1–E10, B, C, P (no answer yet).  [Written before the answers below; the
  tally kept the line.]
- **D8/D9** dropped from the batch: provenance is for checked-in plots;
  [`layer_sweep.py`](../../results_analysis/canonical_angles/plots/layer_sweep.py),
  [`whitening_sweep_with_nulls.py`](../../results_analysis/canonical_angles/plots/whitening_sweep_with_nulls.py)
  (outputs in `/tmp` and [`roger/`](../../roger/)) and
  [`token_position_noise_analysis.py`](../../results_analysis/token_position_noise_analysis.py)
  ([`roger/token_position_noise_out/`](../../roger/token_position_noise_out/)) stay as quick
  plots until one is promoted, when the proper envelope-carrying cache comes with the port.  No
  dollar cost either way.
  [[Review 9a D9](#review-9a-d9-tmp-pickle-caches-keyed-on-cli-args-only),
  [Review 9b D3](#review-9b-d3-token-position-noise-analysiss-cache-key-omits-the-data-fingerprint)]
- **D10**: standardise every response-mode plot on the GPT+Haiku blend at the October re-score;
  the L=3 soft-shear decision (May 11, GPT-only basis, 35-axis di cohort) stands until then;
  optional $0 blended [`shear_l_sweep.py`](../../results_analysis/shear_l_sweep.py) re-run
  beforehand.
  [[Review 9b D4](#review-9b-d4-slot-and-shear-plots-use-gpt-only-responses-while-rho-by-layer-uses-the-blend)]
- **D11** (a): align [`analyse_start_strength.py`](../../tools/analyse_start_strength.py)'s
  coherence comparison with the runner; re-derive OVERRIDES only if a cell changes grade.
  [[Review 10 D3](#review-10-d3-analyse-start-strength-grades-by-a-different-rule-than-the-runner-stops-on)]
- **D12** accepted: exclude `SIDE_CAR_FILENAMES` from
  [`axis_judge_correlation.py`](../../results_analysis/axis_judge_correlation.py)'s scores_dir
  fingerprint, in the single edit with D4/D5 + the equivalence mark, before October's step 3.
  [[P3 cross-file](#p3-step-3-judging)]
- **E1**, **E2** accepted as recommended (skip path keeps judged scores unless
  `rerun_existing`; resume re-judges only when generation is complete).
  [[Review 7 D3](#review-7-d3-the-steering-judges-skip-path-overwrites-already-judged-scores),
  [Review 7 D4](#review-7-d4-resume-regenerates-a-whole-strength-over-one-unparseable-judgment)]
- **E3** (a) realpath for the file tools (go ahead, easy); (b) managed settings + `--settings`
  in `SETTINGS_FILES` at highest precedence (SG).
  [[Review 7 D5](#review-7-d5-boundary-hook-symlinks-and-settings-files)]
- **E4** SG: opt-in fsync for small JSON after a timing on the pod's NFS; thread id in the
  staging name.
  [[Review 7 D6](#review-7-d6-atomic-io-has-no-fsync-before-replace-and-a-per-process-staging-name)]
- **E5** done 2026-10-12 (commit after cdb34d49): credentials in
  [`<repo>/.secrets/gsheet/`](../../.secrets/gsheet/); scope narrowing to `drive.file` at the
  next re-auth.
  [[Review 7 D7](#review-7-d7-gsheet-auth-reads-credentials-from-a-directory-outside-the-repo),
  [Review 10 D5](#review-10-d5-the-sheets-oauth-scope-reaches-all-of-rogers-sheets)]
- **E6** accepted: [`defer_rejudge.py`](../../tools/defer_rejudge.py) requires `--category`.
  [[Review 10 D6](#review-10-d6-defer-rejudge-defaults-to-the-uncategorized-category)]
- **E7**: leave the pod IP/port; add a TODO comment explaining they go stale and
  `StrictHostKeyChecking=no` → `accept-new` when next used.
  [[Review 10 D7](#review-10-d7-the-rsync-scripts-hard-code-the-pod-address-and-disable-host-key-checking)]
- **E8**: a bug — require every drifted `dep_key` to be covered before reclassifying.
  [[Review 10 D9](#review-10-d9-apply-deferrals-with-several-drifted-inputs-passes-a-null-dep-key)]
- **E9**: leave (documented scope limit).
  [[Review 10 D10](#review-10-d10-audit-pngs-has-no-transitive-staleness)]
  **E10** plan: `apply_deferrals` honours the entry's category (`legacy_bare` matches only
  `legacy` rows); record the May judge caches' real state under a new category (e.g.
  `awaiting_rescore`) with the reason and the scheduled re-score.  Measured 2026-10-12: the
  `legacy_bare` globs ([`deferred_rejudges.yaml`](../../deferred_rejudges.yaml)) defer 832
  envelope-less caches and 915 envelope-carrying stale_direct ones in
  [`roger/axis_judge_experiments`](../../roger/axis_judge_experiments/).
- **A2** accepted: current pair-list defaults stay but every script fails loudly naming a listed
  axis with no cache or vector; the data dir's MANIFEST names its pair-list generation once
  October gives two data dirs.
  [[Review 9a D3](#review-9a-d3-pair-list-defaults-are-the-current-lists),
  [Review 9b D1](#review-9b-d1-default-pair-lists-are-the-current-ones)]
- **A4** (a): archive [`backfill_arrangements.py`](../../data_analysis/backfill_arrangements.py)
  (one-off initial fill, Sep-8 rules; the field is maintained by decision now).
  [[Review 8 D4](#review-8-d4-backfill-arrangements-apply-overwrite-would-wipe-every-arrangement-recorded-since-september)]
- **A3** (a), pre-extraction work, nothing retroactive: snapshot the pre-W15 goal file as
  [`data/goal_roles_and_traits_v1.json`](../../data/goal_roles_and_traits_v1.json) (not there
  yet; the record behind the `_v1` pair lists); regenerate the current pair lists from the W15
  file (goalnongoal 37 → 26, 13 goal_type changes in clean) for October; 8slot-era scripts stay
  on `_v1` lists + the `_v1` goal file.
  [[Review 9a D4](#review-9a-d4-the-goal-list-regenerated-2026-10-10-overlaps-the-old-on-26-of-54-traits),
  [Review 10 D2](#review-10-d2-the-current-pair-lists-goal-type-predates-the-w15-goal-lists)]
- **A5** (a) alone: gzip the compact snapshot (measured 2026-10-12: 133 MB raw → 18 MB
  `gzip -9`, 10 MB xz; filter + novelty blocks are 123 of the 133 MB) and readers accept
  `.jsonl.gz`; a guard in compact refuses an uncompressed snapshot over ~90 MB; (b) slimming
  only if compacts become routine (each compact adds a ~20-40 MB blob to history).
  [[Review 3 D2](#review-3-d2-the-next-compact-would-write-a-133-mb-tracked-snapshot)]
- **B1** √: drop default-equal temperatures; [`judge.py`](../../assistant_axis/judge.py)
  surfaces a 400; a small per-model capability table for the non-default cases before any
  model switch.
  [[Review 7 D1](#review-7-d1-the-judge-client-always-sends-temperature-and-has-no-reasoning-effort-setting),
  [Review 8 D3](#review-8-d3-temperature-sent-unconditionally)]
- **B2** √: retrofit the base-model sense step's usage record now; the three analysis-side sites
  when next touched.
  [[Review 6 D4](#review-6-d4-the-sense-steps-paid-usage-lives-only-in-the-gitignored-round-dir)]
- **B3** √: resume rebuilds earlier spend from the records (larger of the two, WARN on
  difference); throttled usage.json writes in `GuardedUsage`
  ([`cost.py`](../../assistant_axis/gapgen/cost.py)) (covers M3); SIGTERM handler; correct
  [m1_validation_r2](../../data/candidates/filter/m1_validation_r2/)'s record from its responses
  (`data/` edit, $0).
  [[Review 1 D1](#review-1-d1-a-resume-after-a-kill-loses-the-killed-sessions-spend),
  [Review 2 D3](#review-2-d3-usage-file-written-only-at-finalize)]
- **B4** √: dirty-tree refusal in
  [`base_model_generator.py`](../../data_analysis/gap_generation/base_model_generator.py),
  [`gap_registry.py`](../../data_analysis/gap_generation/gap_registry.py) corpus-regions,
  [`ipip_generator.py`](../../data_analysis/gap_generation/ipip_generator.py),
  [`roget_generate.py`](../../data_analysis/gap_generation/roget_generate.py);
  `rubric_versions.mismatches()` refusal at the start of
  [`traithood_filter.py`](../../data_analysis/gap_generation/traithood_filter.py) (single),
  [`split_cli.py`](../../data_analysis/gap_generation/split_cli.py),
  [`plain_reading.py`](../../data_analysis/gap_generation/plain_reading.py); `resume_mismatch`
  refuses on a `step_versions` / `prompt_sha256` change.
  [[Review 1 D2](#review-1-d2-a-batches-transport-resume-across-a-rubric-re-pin-collects-under-the-new-prompt-hash),
  [Review 1 D3](#review-1-d3-no-paid-cli-refuses-on-rubric-version-mismatches),
  [Review 1 D4](#review-1-d4-paid-clis-without-the-dirty-tree-refusal)]
- **B5** (a): generators exit 1 on any non-refusal error, successes still written and marked;
  refusals stay exit 0.
  [[Review 8 D1](#review-8-d1-the-generators-exit-0-when-entities-errored)]
- **P1**: four pods — roles, traits, r_combinations, t_combinations (existing `--types`
  values); each pod local OUTPUT_DIR, step 0 (default) on each, push small outputs, delete
  activations after the scanner passes; code: batch sizing/holding for N pods on one org queue,
  a merge-and-verify tool; [README](../../pipeline/README.md) procedure.
  [[P5 October extraction arithmetic](#p5-end-to-end-contracts)]
- **P2**: all three — fresh OUTPUT_DIR rule + `generation_config.json` side-car now; step-4
  recompute rule + `stale_vector` status and step-5 filter/minimum before October.
  [[P1 D2](#p1-d2-resume-skips-any-entity-whose-file-exists),
  [P4 D3](#p4-d3-recompute-rule-for-vectors-from-partial-scores),
  [P4 D2](#p4-d2-step-5-averages-every-vector-file-in-the-directory)]
- **P3**: fix — float32 accumulation and storage at steps 4 and 5; test that steering casts to
  the model dtype.  (The judge-correlation analyses cast stored vectors to float32 themselves,
  so only the stored-mean rounding, ~0.2%, enters them; the 1-5% figure is `axis.pt`'s.)
  `axis.pt` is used (steering `type: axis`, `--axis_file`, April notebooks): keep step 5.
  [[P4 D1](#p4-d1-bf16-numerics),
  [P5 #19](#p5-19-bf16-three-times-before-a-difference-of-close-means)]
- **P4** √ (one `JUDGE_RUBRIC_VERSION` bump: marker required, `length` unparsed, role
  eval_prompt artefacts fixed with Roger's text, `pairs_sha256` check).
  [[P3 D1](#p3-d1-a-reply-without-a-score-marker-is-scored-from-a-digit-of-its-reasoning),
  [P3 D6](#p3-d6-role-rubric-artefacts-in-all-339-role-eval-prompts),
  [P3 D7](#p3-d7-the-incongruity-filter-never-checks-the-combination-scores-pairs-sha256)]
  **P5** √ (lock, model-drift guard, chunk sizing from the limits page; accept the ~$2
  SDK-duplicate risk).
  [[P3 D3](#p3-d3-no-lock-against-two-step-3-runs-on-one-scores-dir),
  [P3 D4](#p3-d4-usage-and-the-fallback-use-the-current-judge-model-after-a-resume),
  [P3 D5](#p3-d5-throughput-is-serial-chunk-submission-and-validation),
  [P3 D2](#p3-d2-the-sdk-retries-batch-creation-without-an-idempotency-key)]
- **P6**: keep 512 for the main run; add `finish_reason`, `thinking_stripped` /
  `thinking_suspected`, `question_id` (additive) first; a cap pilot BEFORE the big extraction:
  ~64 entities (20 roles weighted to narrative ones, 20 traits, 20 combinations, plus
  [verbose](../../data/traits/instructions/verbose.json),
  [concise](../../data/traits/instructions/concise.json) and their goal-role combinations
  reported separately) at 256/512/768/1024, 500 responses each; measure truncation share,
  score-3 share and mean score, per-slot cosine to the 1,024 version, pair-axis cosines
  (verbose/concise sharpest); decision rule fixed in advance (keep 512 if slot-0 cosine ≥ 0.99
  and score-3 share moves < 2 points); ~10 GPU-h step 1 + ~5 step 2 (confirmation), ~$25 judge
  by batch.  Separate plan from P7.
  [[P1 D3](#p1-d3-responses-carry-no-finish-reason-thinking-flag-seed-or-question-id),
  [P1 D4](#p1-d4-the-thinking-strip-handles-only-a-leftover-think-tag)]
- **P7**: generalise by mechanism (header tokens derived from the tokenizer; per-family table
  on `model_type` for both steps; byte-identical Qwen regression as the gate); plan
  commissioned from a Fable agent at
  [coding_plan_multi_model_extraction.md](../pipeline/coding_plan_multi_model_extraction.md).
  [[P2 D3](#p2-d3-header-token-list-hard-coded-and-the-family-detected-by-substring)]
- **P8.1** √ (step 1 exits 1 after finishing on any failed item; abort after K consecutive).
  [[P1 D1](#p1-d1-per-item-failures-keep-exit-0)]  **P8.2** √ (missing goal-list name fails
  fast; grid size printed against expected).
  [[P1 D7](#p1-d7-a-missing-goal-list-name-is-only-a-warning),
  [P5 #25](#p5-25-missing-goal-list-name-only-a-warning)]
- **P8.3**: the recorded slow step IS the NFS torch import
  ([`3_judge.py`](../../pipeline/3_judge.py):40).  (a) lazy
  [`assistant_axis/__init__.py`](../../assistant_axis/__init__.py) (PEP 562), retire the
  stand-in packages; (b) pod setup puts the venv on local disk or `/dev/shm`
  (`UV_PROJECT_ENVIRONMENT`) — measure on the first pod; (c) steps 2 and 4 check for work
  before the heavy imports.
  [[P1 D5](#p1-d5-eager-imports-in-the-package-init)]
- **P8.4**: `FileNotFoundError` out of the transient set (ESTALE stays);
  [nfs-io rule](../../.claude/rules/nfs-io.md) text updated.
  [[P4 D5](#p4-d5-filenotfounderror-is-retried-as-transient)]
- **P8.5**: christina mode: symlink the roles default into the traits tree so step 5 works
  (mode unused but must not be obviously broken).
  [[P4 D6](#p4-d6-christina-mode-with-traits-has-no-default-vector)]
- **P8.6**: two drivers, not a RunPod change (noexec `/dev/shm` is already handled by both).
  One implementation: the shell driver calls the Python helper; `--tmpfs-method {auto,rsync,cp}`
  on both drivers; both write the completeness marker.
  [[P4 D7](#p4-d7-two-tmpfs-mirror-implementations),
  [P5 #26](#p5-26-two-tmpfs-mirror-implementations)]
- **P8.7**: into the P7 plan (BOS per family).
  [[P1 D8](#p1-d8-a-second-bos-on-gemma-or-llama-from-text-prompts)]  **P8.8**: leave.
  [[P4 D8](#p4-d8-question-matched-filtering-unchanged)]
