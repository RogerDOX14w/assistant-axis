# Coding plan: candidate groups and the review app (R1 graph, R2 app)

Written by Fable, 2026-10-08, from the brainstorm with Roger after the first two generators' pilots.  **Reviewed
by Roger 2026-10-08** (decisions 5 and 7 confirmed, 10 and 11 agreed); R1 coding started the same day.  Terms: the [glossary](./glossary.md).

**The problem.**  M3 ([coding_plan_platform.md](./coding_plan_platform.md), "Interface as built") judges every
candidate against the corpus only, so near-synonyms proposed together all come out `new` side by side: among the
three pilots' 333 new candidates the median one has another new candidate at gloss-embedding cosine 0.66, a
quarter above 0.76 (`godless` / `irreligious` / `nonreligious`; `backbiting` / `scandalmongering`; `complying` /
`slavish` / `willing`).  Roger's review time is the binding budget (README, cross-cutting points), and the review
has to decide one or two words per concept, not each word alone.  Plan 10's "clustering of survivors" was
dropped in the M3 redesign; this plan replaces it.

## 1. Decisions already made (and why)

1. **A typed graph, not a partition, is the artefact.**  Nodes are a batch's new candidates plus the corpus and
   queue traits they touch; edges carry a relation (`similar` / `opposed` / `unrelated`) and, on similar edges,
   the overlap readings.  Grouping is read off the graph; navigation uses the rest of it.  Why: clustering in a
   high-dimensional space chains (A close to B close to C with A far from C) and buries antonyms; a typed graph
   makes both visible instead of deciding them.  Candidate-to-corpus edges come free from M3's recorded readings
   (`novelty.readings`: stem, cosine, relation, Sonnet and Opus values).
2. **Tight groups are simplicial cliques of rating-4 edges, merged by default** (Roger).  Rubric A's 4 is "the
   same concept: either label could replace the other in any description of a persona".  A clique is a set in
   which every pair is a 4-edge, so a chain can never be a group; two cliques may overlap.  A 4-edge needs the
   reading in both directions, under M3's escalation rule at cut-off 4 (Sonnet 4 confirmed by Opus, or Sonnet 3
   raised to 4 by Opus; `RULES` at cut-off 4, the rule M3 already uses near alignment).
3. **Opposed is an edge label.**  Never merged across; the opposed pole of a group is one step away in the flow
   (step 5 below).  No clustering logic splits on it; Roger reads an antonym in under a second.
4. **The review flow** (Roger, 2026-10-08):
   1. start with a term, or with a merged-by-default 4-clique;
   2. drop members (never the last) and merge in neighbours (singletons or cliques) until the group is one he
      wants to resolve;
   3. nominate one member as the suggested label; the rest pass in as data (synonym notes on that entry);
   4. resolve the group;
   5. optionally start a new group intended as the antonym of the one just resolved, if it has none; otherwise
      continue with a new, unconnected group.
5. **Corpus traits are nodes and resolution targets** (assumption, **CONFIRMED**).  "Already have it: merge into
   corpus trait X" is a first-class resolution, because the recovery test's false covers (`fervent` under
   `zealous`, `humorous` under `wry`) are exactly such cases, and the result feeds `gap_registry.py synonyms`.
6. **Decisions are an append-only event log, applied to the registry**, as the registry itself is a log.
   Undo is a reversal event; provenance (who, when, graph version) comes with it; promotion still goes only
   through `gap_registry.py promote`.
7. **A local app** (assumption, **CONFIRMED**): one process under `uv run`, a small JSON API over the graph and the
   log, one HTML page, keyboard-driven.  Alternatives considered: a generated static page with manual export
   (decisions carried back by hand); a published Artifact with a shared database (zero setup, usable from any
   device, but the corpus data leaves the repository and its conventions).  The local app is the default; the
   artifact route is kept as an option if Roger wants to review away from this machine.
8. **Review order**: largest cliques first (one decision clears several), then singletons by generator and
   region; switchable in the app.  The 59 M3 review flags (`sonnet_below_opus_at`) are a badge, not a queue.
9. **Candidates M3 covered are shown greyed as neighbours**, never reviewed here; the exception is a covered
   candidate pulled into a group by hand, which the resolution then records as a synonym note.

10. **R1 is a separate phase after M3, not folded into it** (Roger, 2026-10-08: "Agreed").  Combining would
    share only the embedding (cached) and the relation list (about $0.10 to $0.20 per 300 candidates on Haiku
    5.5); the overlap calls are different pairs at different thresholds and cannot be shared, and a combined
    phase would spend candidate-pair calls on candidates M3 then covers (49% of the TDA pilot).  M3's decision
    stays a property of the candidate against the corpus (reproducible, batch-independent, what the recovery
    harness reruns); groups span batches and change under review.  The one thing shared for the UX, not the
    bill: R1's retrieval reads one index over corpus traits, queue traits and unresolved candidates, so a card's
    neighbour list is a single ranking.  M3 is untouched.
11. **A cosine floor of 0.35 on R1's overlap calls**, calibrated on the 4,334 recorded M3 readings with a
    cosine and a final value: below 0.35, 0.1% read 4 and 3.9% read 3 or above (1,994 readings); 0.35 to 0.45,
    0.8% and 20% (828); 0.45 to 0.55, 10% and 56% (341); 0.55 to 0.65, 27% and 82% (113); above 0.65, 58% and
    100% (12).  The 81 readings of 4 have minimum cosine 0.32, tenth percentile 0.45, median 0.55, so the floor
    keeps about 98% of the 4-edges and, with k = 10, halves the overlap stage against the worst case.  The
    relation call still sees every retrieved neighbour (it is cheap and types the opposed edges).

12. **Two tiers of groups** (Roger, 2026-10-08: "SG", after the R1 pilot).  The pilot
    ([readout.md](../../data/candidates/review/review_pilots_1/readout.md), $1.51) found rating-4 cliques too rare
    to save review time: 325 new candidates gave 19 cliques (18 pairs, one triple) and 290 singletons, and the
    plan's own example `godless` / `irreligious` / `nonreligious` reads 3.  At 3 the recorded readings give 57
    cliques covering 103 candidates (42 pairs, 12 triples, 3 of four: `frigid` / `impersonal` / `unaffable` /
    `warmthless`, `balky` / `headstrong` / `incompliant` / `indocile`, `affectionate` / `fond` / `loving`, ...).
    So: **merged groups** are cliques of 4-edges (both directions 4), merged by default as decision 2 says;
    **proposed groups** are cliques of 3-edges (both directions 3 or above) not already inside a merged group,
    pre-assembled as the starting group when their first member is opened but not merged until Roger confirms
    with one key.  Rubric A's 3 is "the same concept, differing only in scope, degree or emphasis", which is the
    choose-the-best-word case; a 2 stays a neighbour.  Overlapping proposed groups stay overlapping, as cliques
    do.  Roughly two-thirds of candidates remain singletons because they are distinct; for those the card's
    neighbour list does the work.

Out of scope: community detection (Leiden, HDBSCAN) as a looser default partition (noted as a later option if
cliques prove too small); changes to M3; reviewing the holding lists (except the physical list, since 2026-10-09:
section 8); any change to the seed-queue format beyond the synonym notes below.

## 2. R1: the candidate graph (`review_graph`)

**Edges.**  For each new candidate of the named M3 batches: its k nearest neighbours in one index over the
other new (and earlier unresolved) candidates, the corpus traits and the queue traits, by the cached gloss
embedding (`gloss_w14` form, `openai_text-embedding-3-large` tag in the embedding cache; k = 10 among
candidates, retrieval floor 0.25 as M3's; corpus and queue neighbours come with their M3 readings and get no
new call), typed by the relation call (rubric [relation.md](./rubrics/relation.md), Haiku 5.5, the
candidate's gloss against the other candidate's gloss, one list per candidate as in M3), then the overlap call
on `similar` candidate edges at cosine 0.35 or above (decision 11), in both directions (rubric [overlap_concept.md](./rubrics/overlap_concept.md) v6, one pair
per call, Sonnet then Opus under `RULES` at cut-off 4, prompt caching on) through `NoveltyRunner.run_pairs` with
the other candidate standing in the "other trait" slot (its gloss as the description).  Corpus and queue edges
are copied from `novelty.readings` and `novelty.listed`; no new corpus call.

**Cliques.**  Maximal cliques (Bron-Kerbosch; the strict graph is small and sparse) on the 4-edges.  A candidate
in no clique is a singleton group.  Overlapping cliques stay overlapping; the app shows the overlap.

**Module** `assistant_axis/gapgen/review_graph.py`:

```
build_graph(batch_ids, *, registry_path, k=10, cosine_floor=0.25, runner_factory, usage, budget) -> Graph
Graph.nodes: list[Node]; Graph.edges: list[Edge]; Graph.cliques: list[list[str]]; Graph.to_json() / from_json()
maximal_cliques(strict_edges) -> list[list[str]]
```

`graph.json` (one per review batch, `data/candidates/review/<batch_id>/graph.json`; provenance per
[provenance.md](../../.claude/rules/provenance.md)):

```json
{"batch_id": "review_pilots_1", "from_batches": ["gen_pilot_censuses", "gen_pilot_roget", "gen_pilot_wn_clusters"],
 "config": {"k": 10, "cosine_floor": 0.25, "rules": "cut_off_4", "overlap_rubric": 6, "relation_rubric": 1,
            "embedding": {"model": "text-embedding-3-large", "query_form": "gloss_w14"}},
 "nodes": [{"key": "godless#1", "kind": "candidate", "label": "godless", "generator": "censuses",
            "gloss": "This means ...", "verdict": "trait", "decision": "new", "covered_by": null,
            "flags": [], "region": "moral_stance"},
           {"key": "trait:irreverent", "kind": "corpus", "label": "irreverent", "gloss": "<description>"}],
 "edges": [{"a": "godless#1", "b": "irreligious#1", "cosine": 0.81, "relation": "similar",
            "readings": {"ab": {"sonnet": 4, "opus": null}, "ba": {"sonnet": 4, "opus": null}}, "strict": true},
           {"a": "godless#1", "b": "trait:irreverent", "cosine": 0.52, "relation": "similar",
            "readings": {"ab": {"sonnet": 2, "opus": 2}}, "strict": false, "source": "m3"}],
 "cliques": [["godless#1", "irreligious#1", "nonreligious#1"]],
 "usage": {"...": "MultiModelUsage.as_dict()"}, "_provenance": {"...": "..."}}
```

**CLI** `data_analysis/gap_generation/review_graph.py`:

```
build  --batch-id B --from-batches M3_BATCH ... [--k 10] [--cosine-floor 0.25] [--transport auto|live|batches]
       --budget-usd C [--confirm-expensive --confirmed-by WHO] [--resume] [--dry-run]
groups --batch-id B          # prints the cliques and singleton counts, largest first
```

The estimate before any call: candidates × k relation rows at Haiku 5.5's measured tokens, plus two overlap
calls per similar edge at M3's measured Sonnet share and the cut-off-4 Opus share (take both from the pilots'
`usage.json`); the budget cap and the $20 line as in M3 (`gapgen.cost.confirm_or_abort`).  `--resume` resends
nothing answered.  `usage.json` beside the graph.

**R1 as built (2026-10-08, commits c74a649, 20682f9, d065b40).**  Deviations accepted: the second direction is
read only when the first decides the edge (was: always both), `mixed` and `unsure` relations go to the overlap
call like `similar`, covered candidates are greyed nodes with no edges, `build_graph` takes a prepared plan and
the runner, a second cost check runs after the relation calls.  The runner is used through a `ReviewRunner`
subclass (no change to M3's files), coupled to the runner's `_relation_call`, `_wave` and `_overlap_call`.
**Change for decision 12** (built with R2): a `--proposed-cut-off` (default 3) beside the fixed merged cut-off 4;
the second direction is read whenever the first reads at the proposed cut-off or above; `graph.json` gains
`proposed_groups` (maximal cliques of 3-edges, minus any group wholly inside a merged clique) beside `cliques`
(renamed in the schema's description, not the key, to "merged groups"); `build --resume` on `review_pilots_1`
reads only the missing second directions (about 65 pairs, about $0.30).

## 3. R2: the review app (`review_app`)

**Shape.**  `assistant_axis/gapgen/review_app/`: `server.py` (FastAPI; routes below), `decisions.py` (the event
log and its replay), `static/index.html`, `app.js`, `style.css` (no build step, no framework).  CLI
`data_analysis/gap_generation/review_app.py`:

```
serve  --batch-id B [--port 8765] [--order cliques|generator|region]
apply  --batch-id B [--dry-run]      # replays the log into the registry's review blocks and promotes
status --batch-id B                  # groups resolved / open, decisions by type, time per decision
```

Roger runs `serve` himself and opens `http://127.0.0.1:8765` (the agent's sandbox cannot bind a port; the agent
tests through FastAPI's `TestClient`).

**State.**  `data/candidates/review/<batch_id>/decisions.jsonl`, one event per line, append-only:

```json
{"seq": 41, "at": "2026-10-09T09:12:03+00:00", "by": "roger", "group": "g17", "action": "resolve",
 "members": ["godless#1", "irreligious#1", "nonreligious#1"], "nominated": "irreligious#1",
 "resolution": "promote", "note": null, "graph_sha256": "..."}
```

Actions: `open` (members, from a clique or a term), `drop` (key), `merge_in` (keys: a singleton or a clique),
`nominate` (key), `resolve` (resolution `promote` | `merge_into:<corpus or queue key>` | `park` | `reject` |
`defer`), `start_antonym` (of group), `undo` (seq).  The current state of every group and term is the replay of
the log; the server keeps it in memory and appends on each action.  A term is `handled` once its group is
resolved; a term in two overlapping cliques is handled by the first resolution and shown so in the other.

**Routes.**  `GET /api/queue` (groups in the chosen order with handled counts), `GET /api/group/{id}` (members
with gloss, generator, M1 tags, M3 decision and covering trait, flags; neighbours ranked: cliques and singletons
by strongest edge, corpus and queue traits by reading; the opposed neighbours as a separate list), `GET
/api/term/{key}` (the ego view: the term and everything one edge away), `POST /api/action` (one event; returns
the new state of the group and the queue counts), `GET /api/status`.

**Apply.**  `apply` writes each resolved group into the registry: the nominated member's `review` block becomes
`{"status": "accepted", "by": "roger", "at": ..., "note": ..., "group": ["godless#1", ...]}` and it is promoted
with `gap_registry.py promote --keys` (the existing path), its seed-queue entry carrying `also_proposed:
[labels of the other members]` as a note (the only addition to the queue format); every other member becomes
`{"status": "merged_into", "into": "<nominated key>"}`; `merge_into:<corpus key>` marks every member
`merged_into` that trait and adds the labels to the trait's rename shortlist (`synonyms`); `park`, `reject`
and `defer` set the status as named.  `apply` is idempotent (a second run changes nothing) and `--dry-run`
prints the registry writes.

**Groups on the card.**  Opening a term starts from its merged group if it has one (already merged); otherwise
from its largest proposed group, shown pre-assembled with a "proposed" mark, where `Enter` on the group header
(or `g`) accepts it as the working group and `x` drops members first; a term in no group starts alone.  The queue
counts merged groups, proposed groups and singletons separately.

**Keys.**  `g` accept the proposed group, `j` / `k` next and previous member, `x` drop, `m` merge in the highlighted neighbour, `n` nominate,
`Enter` resolve with promote, `c` resolve as merge into the highlighted corpus trait, `p` park, `r` reject, `d`
defer, `a` start the antonym group, `u` undo, `/` find a term.  The page shows the queue's remaining counts
at all times.

## 4. Acceptance tests (written first)

R1, fake clients and the toy corpus (`assistant_axis/tests/test_gapgen_review_graph.py`):

- every clique is a simplex: each pair in it is a 4-edge in both directions;
- a chain A-B-C where A-C reads 2 gives cliques {A,B} and {B,C}, never {A,B,C};
- an opposed edge is never inside a clique, and an opposed pair of cliques is linked;
- corpus and queue edges are copied from the registry's `novelty.readings` and cost no call;
- the estimate matches a hand count; a run over `--budget-usd` is refused before any call; `--resume` after a
  simulated stop sends only the unanswered pairs; `usage.json` is written even with zero calls;
- `graph.json` round-trips and its provenance names the batches and rubric versions.

R2 (`assistant_axis/tests/test_gapgen_review_app.py`, `TestClient`):

- the five-step flow on the toy graph: open a clique, drop one, merge a singleton in, nominate, resolve, start
  the antonym group, resolve it; the queue counts move as expected;
- a dropped last member is refused; a handled term shows as handled in its other clique;
- the log replays to the same state after a restart; `undo` reverses the last event and the replay agrees;
- `apply` writes the review blocks, calls promote once per resolved group with the nominated key, adds
  `also_proposed`, marks the rest `merged_into`, is idempotent on a second run, and writes nothing on `--dry-run`;
- `merge_into` a corpus trait adds the labels to the synonyms shortlist.

- a proposed group opens pre-assembled but unmerged; `g` merges it; dropping a member before `g` merges the rest;
  a term in two proposed groups offers the larger and lists the other as a neighbour group.

Existing suites stay green: `test_gapgen_registry.py`, the novelty and recovery suites, `check_arrangements.py
--quiet`, `sync_entity_lists.py --check`.

## 5. Rule files to Read before starting

[provenance.md](../../.claude/rules/provenance.md) (every JSON output, the usage record),
[judging.md](../../.claude/rules/judging.md) (the two call sites), [entity-naming.md](../../.claude/rules/entity-naming.md)
(keys, labels, display forms), [trait-pairs.md](../../.claude/rules/trait-pairs.md) (promotion and pairs);
`working-style.md` is always loaded.  The platform's own conventions: the "Interface as built" section of
[coding_plan_platform.md](./coding_plan_platform.md), `novelty_runner.py`'s `read_pairs` / `run_pairs`, and
`gap_registry.py promote`.

## 6. Task checklist (ordered)

1. R1 tests (§ 4), then `review_graph.py`: nodes from the batches, kNN by the cache, the relation list call,
   the overlap pairs through `run_pairs` with the candidate-as-other adaptation, `maximal_cliques`, `graph.json`.
2. The R1 CLI with estimate, cap, resume and usage; a `--dry-run` on the three pilots' batches printing the
   estimate (expected: about $2 to $3 for 333 candidates).
3. **R1 pilot**: `build --batch-id review_pilots_1 --from-batches gen_pilot_censuses gen_pilot_roget
   gen_pilot_wn_clusters --transport live --budget-usd 6`; readout: candidates, similar / opposed / unrelated
   edge counts, 4-edges, cliques by size, singletons, cost; the ten largest cliques listed.  Fable reads it
   before R2 starts.
4. R2 tests, then `decisions.py` (log, replay, apply) and `server.py` with the routes.
5. The page: queue, group card, ego view, keys, counts; a screenshot or a text walk-through in the report.
6. `apply` and `status`; the README section in [README.md](./README.md) and a short usage note at the top of
   `review_app.py`.
7. **R2 pilot**: Roger reviews the census pilot's groups (about 230 candidates in their cliques); `status`
   gives decisions per minute and the split promote / merge / park / reject; the readout says what the flow
   lacked.  Full generator runs are reviewed through this app afterwards.

## 7. Costs

R1 on 333 candidates: about 3,300 relation rows on Haiku 5.5 (about $1), and with the 0.35 floor about 800
overlap calls on Sonnet with Opus on the close ones (about $1 to $1.50); cap $6, no approval needed.  A full TDA run (about 1,400 new
candidates) about $10 to $15.  R2 costs nothing but Roger's time, which it is meant to save; the R2 pilot
measures that.

## 8. Physical pass (2026-10-09)

**What it is.**  Roger, 2026-10-09 ([QUESTIONS.md](./QUESTIONS.md) question 1): "On the physical queue, I think we
handle promotion normally, and if promoted they get the physical tag.  I suspect the proportion of them promoted
may be small, so probably worth doing this as a separate pass, but I think the process and tooling is the same."
M1 tags a word `physical` when the reading it accepts is a lasting bodily feature and parks the row on the
physical *holding list* (the registry field `holding`, which keeps a row out of the trait flow; promotion refused
it).  Such rows never reached M3, R1 or R2, because M3 scores only rows whose filter verdict is `trait`.  The
physical pass sends them through the same three tools, in batches of their own; the code is
[physical_pass.py](../../assistant_axis/gapgen/physical_pass.py).

**The gloss stage.**  The split filter writes no gloss (the one-sentence "This means ..." description M3 embeds
and shows the models; [glossary](./glossary.md#m1-gloss)) and no alignment score (0 to 3, which sets M3's
*cut-off*, the overlap reading at which a candidate counts as covered: 3 far from alignment, 4 near it) for a
physical row.  So the pass first runs M1's own two calls on each row that has none: the gloss call
([gloss.md](./rubrics/gloss.md) as pinned) on the accepted reading, then the alignment call
([alignment.md](./rubrics/alignment.md) as pinned) on that gloss, on Haiku 5.5 with M1's request settings.  The
result is a block `physical_gloss` on the registry row (the filter block and the row's own `gloss` are left
alone).  M1's third call, the region, is not run: its rubric has no region for a bodily feature.  After the stage,
M3 runs exactly as for trait rows, against the whole corpus, the physical track included.

**The three commands, in order** (each with `--dry-run` first; costs as for any run of the tool):

1. M3: `uv run python data_analysis/gap_generation/novelty_score.py score --holding physical --batch-id
   physical_<name> --unscored --budget-usd <cap>` (or `--run GENERATOR/RUN_ID`, or `--keys K ...`)
   ([novelty_score.py](../../data_analysis/gap_generation/novelty_score.py)).  Every block, the run's `run.json`
   and its `summary.json` (the smoke run's: [run.json](../../data/candidates/novelty/physical_pilots_1/run.json),
   [summary.json](../../data/candidates/novelty/physical_pilots_1/summary.json)) carry `"pass": "physical"`; use a
   batch id of its own (a resume across the two kinds of batch is refused).  The gloss stage's answers are in the
   run's [physical_gloss.jsonl](../../data/candidates/novelty/physical_pilots_1/physical_gloss.jsonl).
2. R1: `uv run python data_analysis/gap_generation/review_graph.py build --batch-id review_physical_<name>
   --from-batches physical_<name> --budget-usd <cap>` ([review_graph.py](../../data_analysis/gap_generation/review_graph.py)).
   Unchanged but for the nodes, which carry `outcome: "physical"`.
3. R2: `uv run python data_analysis/gap_generation/review_app.py serve --batch-id review_physical_<name>`, then
   `apply --dry-run` and `apply` ([review_app.py](../../data_analysis/gap_generation/review_app.py)).  The card
   shows the `physical` tag.  A promoted row's seed-queue entry carries the tag `physical`, the physical track's
   section (read from the queue's physical entries, such as [blond](../../data/traits/instructions/blond.json)'s,
   in [seed_queue.json](../../data/seed_queue.json)) and the pass's gloss as `description_draft`.
   `gap_registry.py promote --keys K` promotes one by name the same way
   ([gap_registry.py](../../data_analysis/gap_generation/gap_registry.py)); `promote --status accepted`, the bulk
   path, still refuses a physical row, and the roles and nationalities lists stay unpromotable.

**Smoke run** (the pilots' 13 physical rows, $0.063 in all): M3
[physical_pilots_1](../../data/candidates/novelty/physical_pilots_1/decisions.md) covered 9: by exact label
[blind](../../data/traits/instructions/blind.json), [good-looking](../../data/traits/instructions/good_looking.json),
[muscular](../../data/traits/instructions/muscular.json) and [thin](../../data/traits/instructions/thin.json); by
the overlap reading impaired under [mobility impaired](../../data/traits/instructions/mobility_impaired.json),
physical under [athletic](../../data/traits/instructions/athletic.json), sinistral under
[left-handed](../../data/traits/instructions/left_handed.json), spare under
[thin](../../data/traits/instructions/thin.json) and stone-deaf under [deaf](../../data/traits/instructions/deaf.json).
New: alive, cherubic, stentorian, weather-beaten.  R1
[review_physical_pilots_1](../../data/candidates/review/review_physical_pilots_1/graph.json): four singletons, no
group.  Two glosses went past the body (cherubic's adds hidden mischief, which raised its alignment score to 2 and
its cut-off to 4; physical's adds training); like any gloss, it is a first draft for the description writer.

## 9. States pass v4 (2026-10-09)

**What it is.**  M1, the trait-hood filter ([coding_plan_platform.md](./coding_plan_platform.md)), parks a word whose
accepted reading is a passing state (a mood, a reaction, a bodily or situational condition) on the `states` *holding list*:
the registry field `holding`, which keeps a row out of the trait flow until something moves it.  The states pass
([states_pass.py](../../assistant_axis/gapgen/states_pass.py), CLI
[states_pass.py](../../data_analysis/gap_generation/states_pass.py)) has asked Roger's three questions of those rows
since round 2 (decision 12 of [decisions_m1.md](./decisions_m1.md)), but nothing acted on its answers except a
promotion under a name Roger typed in (`--confirm-state-name`, [QUESTIONS.md](./QUESTIONS.md) question 14).
Version 4 of its queue prompt adds his rules of 2026-10-09 and moves rows out of the list.

**Roger's rules (2026-10-09; his words, condensed by the coordinator).**  For a word on the states list:

1. "Does the state typically last months or longer, rather than days or weeks?"  If so, drop "states": it is a lasting
   condition, needs a gloss of the lasting condition itself, and goes on like any trait.  His cut-off: "months yes,
   weeks-to-months no(ish), though it's a fuzzy borderline.  My mental model is 'How likely is this to wear off
   during the course of a narrative?', and my assumption is that narratives that last weeks in, say, a dozen
   paragraphs are not that uncommon, while months in a dozen paragraphs is unusual."  Lasting: expecting
   ([pregnant](../../data/roles/instructions/pregnant.json)), [unemployed](../../data/roles/instructions/unemployed.json),
   depressed (an episode), grieving (sorrowing, heartsick), [newlywed](../../data/roles/instructions/newlywed.json).
   Not lasting: [sleep-deprived](../../data/traits/instructions/sleep_deprived.json) (days to weeks), housebound after
   a short illness, jet-lagged.
2. Otherwise: "is a habitual, persistent predisposition toward this temporary state plausible?"
3. If so: does the label itself have that predisposition as a sense ("ordinary speakers already use the word for a
   person who is often that way"; tearful yes, startled no)?  If so, gloss it in that sense, "confirm the gloss was
   written that way (possibly a keyword scan, backed by a Haiku call)", and if confirmed move it out of the states
   queue.
4. "We should probably check states for roles as well, using our standard rule": the kind call's own definition of a
   role ([step2_kind.md](./rubrics/step2_kind.md)): "an identity big enough to organize the whole persona, so that a
   person has only one: a profession or calling, an office or official status, a rank so high or so low that it rules
   out most professions, an age so young or so old that it rules out a profession."  The role/trait border is fuzzy
   and duplicates across corpus roles and traits are accepted, so a borderline call is not an error to fix in code.

What "move out" means is the coordinator's proposal, which Roger has not objected to; it is built as proposed and
recorded in [QUESTIONS.md](./QUESTIONS.md) question 45 as "proceeded under, Roger to confirm": the row leaves the
states list and goes through M3 and the review app as the physical pass does (section 8), so that Roger decides in
review, not by typing names; when only another name fits (startled gives jumpy), that name becomes a candidate of its
own, which goes through M1, M3 and review as any generator's word, while the state word stays on the states list.

**The routes.**  The queue call (prompt v4, Haiku 5.5, 20 rows a call) answers, reason first: `typical_duration`
(hours, days, weeks, months or years) and `lasting`; for a lasting condition `role` and a `gloss` of the condition;
otherwise `plausible`, `name_fits`, `suggested_name` and a `gloss` of the predisposition, as in v3.  The code then
routes the row ([states_pass.py](../../assistant_axis/gapgen/states_pass.py) `route_for`):

| route | when | what happens to the row |
|---|---|---|
| `role` | lasting, and a role | `holding: "roles"`, entity type `role`: read by hand with the rest of the roles list ([QUESTIONS.md](./QUESTIONS.md) question 1); no gloss check, no M3 |
| `lasting` | lasting, not a role | gloss check; if confirmed, M1's alignment score, then `holding: "states_released"` |
| `predisposition` | not lasting, plausible, the state's own name fits | the same |
| `renamed` | not lasting, plausible, only another name fits | stays on the states list; the suggested name is submitted as a new candidate (below) |
| `held` | not lasting and not plausible; a gloss the check turned down; a second rename (below) | stays on the states list, the reason on the block as `route_reason` |

A `typical_duration` of months with `lasting` false (or weeks with true) is kept as the model gave it: Roger called
that border fuzzy.  The block records `duration_agrees` and the summary lists the rows where it is false.

**The gloss check.**  A keyword scan first ([states_pass.py](../../assistant_axis/gapgen/states_pass.py) `SCAN_FOR`,
`SCAN_AGAINST`): a gloss with a marker for its route (lasting: "for months", "years", "month after month", "day after
day", "every day", "daily" ...; predisposition: "again and again", "easily", "often", "whenever", "any", "every",
"readily" ...) and none against ("right now", "at the moment", "today", "this morning", "just", "briefly" ...) is
confirmed without a call.  Any other gloss goes to the check call (prompt v1, Haiku 5.5, one gloss a call), which
reads the sentence as `lasting`, `predisposition` or `passing` without being told which was meant (so it cannot
simply agree); the gloss, the one-sentence "This means ..." description M3 embeds and shows its models
([glossary](./glossary.md#m1-filter-gloss)), is confirmed when the reading is its route's.  The scan never turns a
gloss down on its own.  The alignment call (M1's, [alignment.md](./rubrics/alignment.md) as pinned, the 0 to 3 score that sets M3's *cut-off*, the overlap reading at which a candidate counts as covered) is
sent beside the check calls, on every gloss of the two released routes, so a gloss the check turns down has paid for
a score that is not recorded (about $0.0002 a row).

**Where a released row goes: a marker, not a cleared `holding`.**  A released row's `holding` becomes
`states_released`, a list of its own in `HOLDING` of [normalize.py](../../assistant_axis/gapgen/normalize.py),
rather than `None`.  A cleared field would put the row
in the main flow, where it does not fit: its filter verdict is `tagged` (not `trait`), its own `gloss` is empty (the
gloss is on the `states_pass` block), [gap_registry.py](../../data_analysis/gap_generation/gap_registry.py)
`report` would list it as an ordinary row, and the bulk path
`promote --status accepted` would promote it with no description draft.  The marker keeps it out of all of these, as
the physical list keeps a physical row out, and gives the pass one value to select on
([novelty_score.py](../../data_analysis/gap_generation/novelty_score.py) `score --holding states`) and one listing
([gap_registry.py](../../data_analysis/gap_generation/gap_registry.py) `holding --list states_released`).  The
row has left the states list either way: `holding --list states` no longer shows it, the states pass no longer picks
it up, and its block says why it left.

**Promotion.**  A released row is promoted only by name, as a physical row is:
[gap_registry.py](../../data_analysis/gap_generation/gap_registry.py) `promote --keys K` or the review app's `apply`
([review_app.py](../../data_analysis/gap_generation/review_app.py)); both pass `allow_released_states` to
[promote.py](../../assistant_axis/gapgen/promote.py), and `promote --status accepted` refuses the row.  Its seed-queue
entry carries the tags `states_pass` and `lasting_state` or `predisposition` (beside M1's `state`), the pass's gloss
as `description_draft`, and a note naming the route, the duration and the batch.  A row on the roles list is never
promoted (question 1).  The old path for a held row, `promote --keys K --confirm-state-name K=NAME`, is unchanged.

**Renamed rows: one hop.**  A `renamed` row's suggested name is written to the tracked `candidates.jsonl` of the
run directory `data/candidates/runs/states_pass/<batch_id>/` first (the pilot's:
[candidates.jsonl](../../data/candidates/runs/states_pass/states_v4_pilot/candidates.jsonl)) and then submitted to the registry (generator
`states_pass`, run id the states-pass batch, `source_ref` the state's key, `gloss_hint` the predisposition gloss), and
the state's block records it as `renamed_to`.  The new candidate goes through M1 like any generator's word.  If M1
tags it a state again and the pass would rename it once more, it is held instead (`route_reason` "already a
states-pass rename"): a row with a `states_pass` source gets one hop.

**The commands, in order** (each with `--dry-run` first, which prints the estimate and renders the calls):

1. The states pass: `uv run python data_analysis/gap_generation/states_pass.py --batch-id states_<name> --mode queue
   --holding-states --transport batches --budget-usd <cap>` ([states_pass.py](../../data_analysis/gap_generation/states_pass.py)).
   It takes the rows on the states list with no `states_pass` block yet (`--rejudge` for every one), writes each
   row's block and new `holding`, and submits the renamed route's names.  `--transport auto` goes live under 300
   rows; `--resume` continues a stopped run in its batch directory (its rows, its answers on record, its recorded
   batches).
2. M1 on the renamed route's names: `uv run python data_analysis/gap_generation/traithood_filter.py --batch-id <F>
   --run states_pass/states_<name> --pipeline split --transport batches --budget-usd <cap>`
   ([traithood_filter.py](../../data_analysis/gap_generation/traithood_filter.py)); from there they are ordinary
   candidates (M3, R1, R2), and any that come back tagged a state are judged by the next states pass.
3. M3 on the released rows: `uv run python data_analysis/gap_generation/novelty_score.py score --holding states
   --batch-id states_m3_<name> --unscored --transport batches --budget-usd <cap>`
   ([novelty_score.py](../../data_analysis/gap_generation/novelty_score.py)).  No gloss stage: the states pass
   wrote the gloss and the alignment score.  Every block, `run.json` and `summary.json` say `"pass": "states"`; use a
   batch id of its own.
4. R1: `uv run python data_analysis/gap_generation/review_graph.py build --batch-id review_states_<name>
   --from-batches states_m3_<name> --transport batches --budget-usd <cap>`
   ([review_graph.py](../../data_analysis/gap_generation/review_graph.py)); the nodes carry `outcome: "states"`.
5. R2: `uv run python data_analysis/gap_generation/review_app.py serve --batch-id review_states_<name>`, then
   `apply --dry-run` and `apply` ([review_app.py](../../data_analysis/gap_generation/review_app.py)).  The card shows
   M1's `state` tag, the outcome `states` and a chip saying where the row came from, such as `states pass: lasting
   (months)`.

`gap_registry.py holding --list states`, `--list states_released` and `--list roles`
([gap_registry.py](../../data_analysis/gap_generation/gap_registry.py)) show each row's route, duration and gloss.

**The calls as Haiku 5.5 receives them** (rendered from the code, as the judging rule asks; the four rows are real
rows of the states list: one lasting, one whose own name fits, one needing another name and one implausible; the pilot
sent them inside its 20- and 10-row calls, so the user turn here is how the call builds those four alone):

````text
--- system (queue prompt v4) ---
You are helping to build a research corpus of personality traits. Each trait is a label plus a one-sentence description, and a persona is prompted to embody it while answering ordinary questions in text, so a trait must be something a person can have as a standing way of being, or a condition that lasts months or longer, not something that happens to them once.

## Your task
Each candidate below names a state: a condition someone is in for a while (a mood, a reaction, a bodily or situational condition). You are given the state's name and a short description of the state. For each, reason first, then answer:
1. typical_duration: how long the state typically lasts: "hours" (or less), "days", "weeks", "months" or "years".
2. lasting: true when the state typically lasts months or longer. The test is how likely it is to wear off in the course of a story: a story told in a dozen paragraphs often spans weeks, but rarely months. So a state of weeks, or of weeks to months, is not lasting; a state of months or years is.
3. If lasting is true, answer role and gloss, and set plausible, name_fits and suggested_name to null:
   - role: is the lasting condition a role in this sense: an identity big enough to organize the whole persona, so that a person has only one: a profession or calling, an office or official status, a rank so high or so low that it rules out most professions, an age so young or so old that it rules out a profession?
   - gloss: one sentence of 20 to 40 words (count them) describing the lasting condition itself: what the person's days are like while it lasts, and how it shows in what they do, feel or say.
4. If lasting is false, set role to null and answer:
   - plausible: is a habitual predisposition to this state plausible? That is, could a person be prone to falling into it again and again, so that the proneness is part of who they are and would show in how they talk? Moods, reactions and emotional or social states mostly allow it. Conditions imposed from outside, or purely bodily conditions that no temperament brings about, mostly do not.
   - name_fits: if plausible, is the state's own name still a good name for the predisposition? It is when ordinary speakers already use the word for a person who is often that way. If not, give suggested_name: the plainest ordinary English name for the predisposition (one word if one exists, otherwise a short phrase such as "easily ..." or "prone to ...").
   - gloss: if plausible, one sentence of 20 to 40 words (count them) describing the habitual predisposition, not the passing state: what the person habitually does, feels or says.
   If a predisposition is not plausible, set name_fits, suggested_name and gloss to null.
Every gloss begins "This means" followed at once by a verb in the -ing form, and goes straight to the behavior, from the inside. No hedges ("tends to", "sometimes", "may"). A vice is described as a vice. US spelling.

## Examples (reason first, then the answers)
- "bereaved": grief over a death in the family lasts months or longer, and it combines with any profession, so it is no role; typical_duration "months"; lasting true; role false; plausible, name_fits and suggested_name null; gloss "This means living, month after month, with the recent death of someone close: missing them every day, returning to memories of them, and finding plans and ordinary pleasures emptied by the loss."
- "retired": having left paid work for good lasts years and rules out a profession; typical_duration "years"; lasting true; role true; plausible, name_fits and suggested_name null; gloss "This means having left working life for good: living on a pension and savings, filling the days with chosen pursuits, and speaking of one's working years as a finished chapter."
- "convalescing": recovery from an illness takes weeks, at most a few months, so it is not lasting; a bodily condition that no temperament brings about; typical_duration "weeks"; lasting false; role null; plausible false; name_fits, suggested_name and gloss null.
- "startled": over in moments; some people are startled by every small surprise, and the ordinary name for that is jumpy; typical_duration "hours"; lasting false; role null; plausible true; name_fits false; suggested_name "jumpy"; gloss "This means reacting to every sudden noise, interruption or unexpected question with a jolt of alarm, losing the thread for a moment and needing time to settle again."
- "wistful": a mood of an hour or an afternoon, and people who often feel it are called wistful; typical_duration "hours"; lasting false; role null; plausible true; name_fits true; suggested_name null; gloss "This means drifting easily into longing for what is gone or out of reach, dwelling on old places and chances missed, and letting a soft sadness color how one speaks."

## Output
Respond with one JSON object and nothing else. For every candidate, reason first (at most 30 words), then give the answers. Use exactly these keys in this order:
{"results": [{"id": <int>, "label": "<the candidate>", "reason": "<at most 30 words>", "typical_duration": "hours"|"days"|"weeks"|"months"|"years", "lasting": true|false, "role": true|false|null, "plausible": true|false|null, "name_fits": true|false|null, "suggested_name": "<name>"|null, "gloss": "<sentence>"|null, "confidence": <0-1>}]}
confidence is your probability, between 0 and 1, that lasting and the answer after it (role, or plausible) are right. Return one row per candidate id, in the order given.
--- user ---
Judge these 4 states. Reason first, then answer, for each.
{"id": 1, "label": "expecting", "state_description": "pregnant, carrying a child"}
{"id": 2, "label": "tearful", "state_description": "currently crying or on the verge of tears"}
{"id": 3, "label": "rattled", "state_description": "emotionally disturbed or agitated; having lost composure"}
{"id": 4, "label": "muddy", "state_description": "covered in mud, dirty from mud (a passing condition of the body or clothes)"}
````

The four rows' answers as the pilot recorded them (each was one row of a 20- or 10-row call; route added by the code):

```json
{"id": 1, "label": "expecting", "reason": "Pregnancy lasts about nine months, so it is lasting. It rules out no profession, so it is not a role.", "typical_duration": "months", "lasting": true, "role": false, "plausible": null, "name_fits": null, "suggested_name": null, "gloss": "This means carrying a child through months of growing bodily change: tiring easily, planning around appointments and due dates, and speaking often of the baby, the nursery and what is coming.", "confidence": 0.9, "route": "lasting"}
{"id": 2, "label": "tearful", "reason": "Crying or near tears passes within hours; people who often cry easily are commonly called tearful.", "typical_duration": "hours", "lasting": false, "role": null, "plausible": true, "name_fits": true, "suggested_name": null, "gloss": "This means welling up at small kindnesses, sad songs or hard news, speaking with a thickened voice, and reaching for a tissue more often than others would expect.", "confidence": 0.8, "route": "predisposition"}
{"id": 3, "label": "rattled", "reason": "Being emotionally thrown off composure passes within hours. Many people are easily rattled, so the predisposition is plausible and the phrase 'easily rattled' is the ordinary name.", "typical_duration": "hours", "lasting": false, "role": null, "plausible": true, "name_fits": false, "suggested_name": "easily rattled", "gloss": "This means losing composure at the slightest provocation, fumbling words, snapping at others, and reacting to small upsets with visible agitation before slowly regaining control.", "confidence": 0.8, "route": "renamed"}
{"id": 4, "label": "muddy", "reason": "Mud on the body or clothes is a passing physical condition that is cleaned off within hours. No temperament produces it.", "typical_duration": "hours", "lasting": false, "role": null, "plausible": false, "name_fits": null, "suggested_name": null, "gloss": null, "confidence": 0.95, "route": "held"}
```

````text
--- system (check prompt v1) ---
You are checking a description written for a research corpus of personality traits. Each trait is a label plus a one-sentence description, and a persona is prompted to embody it in text, so a description must describe something that stays with the person from one day to the next, not one passing episode.

You are given a label and its description. Say which of three things the description, as written, describes:
- "lasting": a condition the person lives in for months or longer, described as going on over that time;
- "predisposition": a habitual proneness: the person falls into a state again and again, or easily, as part of who they are;
- "passing": being in a state now, or for one short spell, with nothing in the description that makes it last or recur.
Judge the description as written, not the label on its own.

Respond with one JSON object and nothing else, reason first:
{"reason": "<one short sentence>", "reading": "lasting"|"predisposition"|"passing"}
--- user (sulky: a predisposition gloss the scan did not pass) ---
{"label": "sulky", "description": "This means going quiet and withdrawn after a slight, answering questions in clipped words, avoiding eye contact, and nursing resentment long after the matter has been settled."}
--- answer ---
{"reason": "The description portrays a habitual pattern of withdrawing after any slight, which recurs as part of the person's usual reaction, though it never specifies a duration of months.", "reading": "predisposition"}
--- user (beholden: a lasting gloss the scan did not pass) ---
{"label": "beholden", "description": "This means carrying a debt of gratitude to someone who helped, measuring one's choices against that obligation, and deferring to their wishes while it lasts."}
--- answer ---
{"reason": "The description frames beholdenness as an ongoing debt the person carries and lives under, with choices continually measured against it 'while it lasts,' which implies a standing condition over an extended period rather than a habitual tendency or a single episode.", "reading": "lasting"}
--- user (rueful: a predisposition gloss the scan did not pass) ---
{"label": "rueful", "description": "This means reflecting with a wry, self-deprecating regret on one's own mistakes and lost chances, smiling ruefully at them and admitting them openly in conversation."}
--- answer ---
{"reason": "The description characterizes a manner of reflecting and admitting regrets but never says the person does so repeatedly, habitually, or over an extended period, so nothing marks it as recurrent or lasting.", "reading": "passing"}
````

**Pilot (2026-10-09): the 170 rows on the states list** of this checkout's registry (from the generator pilots:
censuses, Roget, the WordNet stream, the Allport column IV and rare pilots, the antonym check and the M1 validation
pool), every step through the Message Batches API.

- *States pass* [states_v4_pilot](../../data/candidates/states_pass/states_v4_pilot/summary.json): 170 of 170
  answered, $0.034, 29 minutes (three batch waves).  Typical durations: hours 95, days 26, weeks 26, months 13, years
  10.  Routes: role 3, lasting 17, predisposition 15, renamed 66, held 69 (67 neither lasting nor plausible; 2 glosses
  the check turned down).  Of the 34 glosses of the two released routes, the scan passed 17 and the check call read 17,
  confirming 15 and turning down two: contented's ("going through ordinary days at ease with what one has ...", read
  as lasting: a settled way of living, not a proneness) and rueful's (read as passing: nothing makes it recur).
  Alignment scores of the 32 released glosses: 22 at 0, 8 at 1, 1 at 2 (repentant), 1 at 3 (beholden: "deferring to
  their wishes").  Three rows' `typical_duration` disagrees with `lasting` (destined and thirty-ninth: months, not
  lasting; unwronged: years, not lasting); all three were held as implausible.
- *Roles* (all of them): fugitive ("living on the run for months"), housebound (read as years unable to leave home),
  ostracized ("an imposed low standing that rules out most ordinary roles").  Against Roger's examples: expecting,
  heartsick and unemployed came out lasting, but expecting and unemployed not as roles ("it rules out no profession"),
  although both are corpus roles ([pregnant](../../data/roles/instructions/pregnant.json),
  [unemployed](../../data/roles/instructions/unemployed.json)); depressed's accepted reading is "currently feeling sad,
  low, or down in mood", a mood, so it came out not lasting and renamed gloomy; sorrowing and lamenting came out as
  renamed predispositions (sorrowful, mournful), not as lasting grief.  Duplicates across roles and traits are
  accepted, so these are for Roger's eye, not fixes.
- *Renamed*: 66 names submitted to the registry (47 new rows, 19 merged into rows already there, such as
  [anxious](../../data/traits/instructions/anxious.json), [contented](../../data/traits/instructions/contented.json)
  and [remorseful](../../data/traits/instructions/remorseful.json), which are corpus traits that M3's exact-label
  check will find), recorded in
  [candidates.jsonl](../../data/candidates/runs/states_pass/states_v4_pilot/candidates.jsonl).  They await M1 (step 2
  above).
- *A finding about the queue call*: 6 of the 9 twenty-row calls stopped at the first `max_tokens` (8000), because
  Haiku 5.5's adaptive thinking took about 500 output tokens a row; the retry wave, in ten-row calls, recovered every
  row.  The default is now 16000 and the estimate 500 tokens a row (no prompt change).
- *M3* [states_v4_m3](../../data/candidates/novelty/states_v4_m3/decisions.md) on the 32 released rows: 13
  covered, 19 new, $0.126, 4 hours 48 minutes (fifteen batch waves, 5 to 45 minutes each that afternoon).  Covered by
  exact label: [remorseful](../../data/traits/instructions/remorseful.json) (a corpus trait) and unemployed (the corpus role
  [unemployed](../../data/roles/instructions/unemployed.json)); by the overlap reading: amorous under [flirty](../../data/traits/instructions/flirty.json),
  fearful under [anxious](../../data/traits/instructions/anxious.json), lonesome under [lonely](../../data/traits/instructions/lonely.json), miserably partnered under
  [unhappily-partnered](../../data/traits/instructions/unhappily_partnered.json), nervous under [neurotic (Big Five)](../../data/traits/instructions/neurotic_big_five.json),
  overburdened under [stressed](../../data/traits/instructions/stressed.json), pretty well under [healthy](../../data/traits/instructions/healthy.json), thankful under [grateful](../../data/traits/instructions/grateful.json), unhappy under
  [discontented](../../data/traits/instructions/discontented.json), unhealthy under [sickly](../../data/traits/instructions/sickly.json) and woeful under [melancholic](../../data/traits/instructions/melancholic.json) (four of these covers carry
  the review flag `sonnet_below_opus_at`: amorous, fearful, nervous, unhappy).  New: 12 lasting conditions (beholden,
  declining, disabused, emigrating, expecting, heartsick, liable, nascent, thriving, unacknowledged, unmastered,
  unpunished) and 7 predispositions (disheveled, inconsolable, repentant, rumpled, sulky, tearful, teasing).
- *R1* [review_states_v4](../../data/candidates/review/review_states_v4/graph.json): 19 candidates, one merged group
  (disheveled, rumpled), 17 singletons, $0.007, 28 minutes.  Every node carries `outcome: "states"`, and a card reads,
  for expecting, `state`, `states`, `states pass: lasting (months)`.  Ready for `review_app.py serve --batch-id
  review_states_v4` ([review_app.py](../../data_analysis/gap_generation/review_app.py)).
- *Spend*: $0.166 in all (states pass $0.034, M3 $0.126, R1 $0.007), against the $5 cap.  M1 on the 47 new renamed
  candidates (step 2) is estimated at $0.20 through the Batches API and was not run.
