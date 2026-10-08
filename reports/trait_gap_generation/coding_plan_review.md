# Coding plan: candidate groups and the review app (R1 graph, R2 app)

Written by Fable, 2026-10-08, from the brainstorm with Roger after the first two generators' pilots.  Roger
reviews this plan; his comments go into this file.  Terms: the [glossary](./glossary.md).

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
5. **Corpus traits are nodes and resolution targets** (assumption, to confirm).  "Already have it: merge into
   corpus trait X" is a first-class resolution, because the recovery test's false covers (`fervent` under
   `zealous`, `humorous` under `wry`) are exactly such cases, and the result feeds `gap_registry.py synonyms`.
6. **Decisions are an append-only event log, applied to the registry**, as the registry itself is a log.
   Undo is a reversal event; provenance (who, when, graph version) comes with it; promotion still goes only
   through `gap_registry.py promote`.
7. **A local app** (assumption, to confirm): one process under `uv run`, a small JSON API over the graph and the
   log, one HTML page, keyboard-driven.  Alternatives considered: a generated static page with manual export
   (decisions carried back by hand); a published Artifact with a shared database (zero setup, usable from any
   device, but the corpus data leaves the repository and its conventions).  The local app is the default; the
   artifact route is kept as an option if Roger wants to review away from this machine.
8. **Review order**: largest cliques first (one decision clears several), then singletons by generator and
   region; switchable in the app.  The 59 M3 review flags (`sonnet_below_opus_at`) are a badge, not a queue.
9. **Candidates M3 covered are shown greyed as neighbours**, never reviewed here; the exception is a covered
   candidate pulled into a group by hand, which the resolution then records as a synonym note.

Out of scope: community detection (Leiden, HDBSCAN) as a looser default partition (noted as a later option if
cliques prove too small); changes to M3; reviewing the holding lists; any change to the seed-queue format beyond
the synonym notes below.

## 2. R1: the candidate graph (`review_graph`)

**Edges.**  For each new candidate of the named M3 batches: its k nearest other new candidates by the cached
gloss embedding (`gloss_w14` form, `openai_text-embedding-3-large` tag in the embedding cache; k = 10, floor
cosine 0.25 as M3's), typed by the relation call (rubric [relation.md](./rubrics/relation.md), Haiku 5.5, the
candidate's gloss against the other candidate's gloss, one list per candidate as in M3), then the overlap call
on `similar` edges in both directions (rubric [overlap_concept.md](./rubrics/overlap_concept.md) v6, one pair
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

**Keys.**  `j` / `k` next and previous member, `x` drop, `m` merge in the highlighted neighbour, `n` nominate,
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

R1 on 333 candidates: about 3,300 relation rows on Haiku 5.5 (about $1), about 1,500 overlap calls on Sonnet
with Opus on the close ones (about $1.50 to $2.50); cap $6, no approval needed.  A full TDA run (about 1,400 new
candidates) about $10 to $15.  R2 costs nothing but Roger's time, which it is meant to save; the R2 pilot
measures that.
