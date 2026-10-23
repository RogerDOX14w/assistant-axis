# Review of coding plan 16, steps 1 and 2: the shared role path and generator B, diff `22db8afc..a76941ff`

Reviewer: Fable, 2026-10-23.  Branch `plan16-role-generators`, 13 commits, 76 files, +11,438 / -305.
Specification: [coding_plan_16_role_generators.md](./coding_plan_16_role_generators.md) (Roger's six decisions of
2026-10-22 in its "Decisions for Roger" block, the earlier ones in its § 1) and
[16_role_generators.md](./16_role_generators.md) § 12.  Link targets are relative to this file.  "Ran" means executed
in the worktree with scratch under `$TMPDIR`, no API call made and nothing downloaded; "read" means confirmed in the
source; "infer" is marked.  Terms: the [glossary](./glossary.md); a *role* is who or what a persona is, a *trait* a
disposition; *M1* the trait-hood filter, *M3* the novelty check, *R1* the review graph, *R2* the review app; a
*holding list* keeps a registry row out of the trait flow; the *stage* is the roles pass's two calls before M3 (the
role gloss, then three readings of the role kind); *stage 0* is M3's exact-label match (no call); the *cut-off* is
the overlap reading at which a candidate counts as covered; the *kind readout* is decision 2's too-low /
about-right / too-high chip; the *kept share* is kept rows per row not covered at stage 0, the figure that sizes B's
waves.

## 1. Verdict

**Merge after one code fix (section 4), and change the order of the pre-pilot steps before Roger marks the
sheet (section 3).**  The build does what the plan and Roger's decisions say, and the things that cost money are
guarded as the rules require: every call site has a usage tracker and writes `usage.json`, every paid command has
`--dry-run`, a cap and the $20 flag, the downloads are refused without `--approved-by` (ran), the kind rubric is the
classifier's byte for byte (ran: sha `11b559f0cff50189` in the file, the base string and
[role_kinds.json](../../data/roles/role_kinds.json)), and the suite is green but for failures that predate the build
or need a file the worktree lacks (section 9).  What should change before the pilot is not code: the 40-pair sheet
Roger is asked to mark compares two corpus descriptions, a text pair no production call ever reads, and the role
gloss call's glosses that would make it production-like come from the retrieval check, which needs nothing from
him and is listed after his marks.  The one code defect is in generator B's ranker, which reads the role index's
setting under other keys than the retrieval check writes it, so a recalibration would split B from M3.

## 2. Decision by decision

| # | Roger decided | built | departure |
|---|---|---|---|
| D1 | ESCO as CC BY 4.0 behind a source flag for wave 2, by the API; ISCO-08 out | as decided: `--source esco` / `--only esco_occupations`, [sources.py](../../assistant_axis/gapgen/generators/professions/sources.py) `fetch_esco_occupations`; ISCO-08 and the ISCO-groups file in `SKIPPED` | the API's shape is assumed (`ESCO_UNVERIFIED`), said so in the plan's § 6.6 and the code; no page limit from the CLI for a smoke run (minor 8) |
| D2 | a role named like a trait: allowed with a loud NOTE, the twin on the card | as decided: [promote.py](../../assistant_axis/gapgen/promote.py) `role_collisions`, `COLLISION_NOTE`, `*** NOTE` printed; `nearest_traits` on the node and card | |
| D3 | the label-stripped query against 95%, the label-kept form reported | as decided: `PRODUCTION_ARM`, `INFO_FORMS` in [roles_pass.py](../../assistant_axis/gapgen/roles_pass.py); `role_query_text` strips `A|An <label> is` | |
| D4 | the pilot batched | as decided: the stage follows `--transport`; § 10 and the READMEs say `--transport batches` | |
| D5 | the 14 state-tagged rows stay | as decided: `is_role_row` takes every row on the list (ran: all 15 of the snapshot's state-tagged rows are role rows with an accepted reading) | |
| D6 | `uv add openpyxl`, asked for with the downloads | not added (right: not asked for yet); imported lazily, the error names the command (read, tested) | |
| § 1.2 | balance: readout only, 10% of the held count, too-low kinds first | as decided: `balance`, `kind_readout`, order `kinds`, statuses fixed at serve time | the plan's own worked examples contradict its formula; the formula is right (minor 4) |
| § 1.3 | a role-aimed row M1 reads as a trait goes to both flows, provisionally | as decided: `ROLE_ROUTES["trait"] = "both"`, `RELABEL_ROLE_AIMED = "auto"`, one table and one flag; routed by the first surviving primary reading, written as `role_route` with `routes_version` | |
| § 1.4, 1.5 | sub-roles covered by the parent at 3; cross-type as information, covered against roles only | as decided: `RoleCandidate.cut_off = 3` under every rule set; `cross_type` on the block, never read by the decision (tested by equality); the role index and `role_label_sets_for` hold roles and role queue entries only | R1 keeps the trait tiers (minor 5) |
| § 1.8 | M2's settings reused; the check not leave-one-out; recalibration below 95% | as decided: the role stays in the index; the arms only below the line; `MetricConfig.roles` written and read by M3 and R1 | not by B's ranker (fix 2) |
| § 1.11 | promotion by name only | as decided: `--allow-roles` refused on the bulk path; the app's `apply` passes `allow_roles=True` | |
| § 1.12 | reason first, no temperature on 5.5, three readings by majority, generating calls keep the union | as decided in all five rubrics and both callers | |
| § 1.13 | role rows never merged with trait rows by bare name | as decided: `stem|R#sense`, `candidate_key`; `corpus_key(stem, "role")` in R1; `/files/roles/` in R2 | |

## 3. Blocking before the pilot

1. **The sheet Roger marks is description against description.**
   [novelty_score.py](../../data_analysis/gap_generation/novelty_score.py) `rubric_sheet_pairs` and
   `cmd_rubric_check --make-sheet`; [role_rubric_pairs.md](./role_rubric_pairs.md) ("both are the corpus files'
   descriptions"); [role_rubric_pairs_key.json](./role_rubric_pairs_key.json) (`"glosses": null`).  The plan's § 8
   says the sheet shows "the glosses labelled as the role gloss call's".  In production the overlap call reads a
   candidate's role gloss against a corpus description (M3) or two role glosses (R1); no call reads two corpus
   descriptions, whose forms are mixed ("This involves being a disciplined military professional ...").  The code
   has the right option already (`--glosses <retrieval run>/glosses.jsonl`), and the retrieval check that produces
   those glosses needs nothing from Roger and costs $0.044 by its own dry run (ran).  But [README.md](./README.md)
   ("Waiting on Roger before anything is paid for: the marks ...; then, in order: the retrieval check, the rubric
   check") and § 10 put his marks first.  Marks made on the present sheet would have to be redone once the texts
   change.  Fix: run `retrieval-check` first, then `rubric-check --make-sheet --glosses
   data/candidates/novelty/roles_retrieval_1/glosses.jsonl --overwrite`, then ask for the marks; swap the two steps
   in the README and § 10.  The key then records the gloss source and the sheet's column line says which text is
   the gloss call's, as the working-style rule wants.

## 4. Fix before merge

2. **B's ranker reads the role setting under other keys than the check writes.**
   [rank.py:191-199](../../assistant_axis/gapgen/generators/professions/rank.py) (`role_index_settings`) reads
   `roles.representation` and `roles.space.variant`; `write_role_setting`
   ([novelty_score.py](../../data_analysis/gap_generation/novelty_score.py), the retrieval check) writes a flat
   `variant` and `query_form`, which `role_settings` (the same file, lines 253-261) reads for M3 and R1.  And
   `rank.role_query` ([rank.py:34, 104-109](../../assistant_axis/gapgen/generators/professions/rank.py)) uses the
   constant `role_gloss_w14` whatever `roles.query_form` says.  Today, with no `roles` section in
   [metric_config.json](../../data/candidates/metric_config.json), the two agree and no test can tell; after a
   recalibration (the check below 95% choosing, say, `role_gloss_w20` in the raw space) M3 and R1 would retrieve in
   the new setting while B's distance feature ranked in the old one, against the frozen interface's last line.
   Fix: one reader (move `role_settings` into
   [roles_pass.py](../../assistant_axis/gapgen/roles_pass.py) and call it from rank.py for the variant and the
   query form), and extend
   [test_gapgen_roles_retrieval_check.py](../../assistant_axis/tests/test_gapgen_roles_retrieval_check.py)'s
   "written and read back by the pass" to assert that `build_role_index` and `role_query` follow the written
   setting.

## 5. Minor

3. **`finalize` folds the registry once per candidate.**  The `kinds_of` lambda passed to `finalize` in
   `run_scoring` ([novelty_score.py](../../data_analysis/gap_generation/novelty_score.py)) is
   `{k: RP.kind_of(reg.fold().get(k) or {}) for k in keys}`: for the pilot's 325 rows, 325 folds of a 12,000-line
   log at the end of the run.  Fold once.

4. **The kind readout's examples in the plan contradict its formula; the formula is right.**  § 6.4 gives `held =
   share x n_now`, too high when `count > 1.1 x held`, which is Roger's sentence of 2026-10-21; `balance`
   ([roles_pass.py:161-186](../../assistant_axis/gapgen/roles_pass.py)) does that.  But § 6.4's example (occupation
   171 at n_now 351, held 167.7) is about right by it (171 < 184.5), not too high, and § 6.3's "171 of 162 held
   at 339 + 12 accepted ... held 161.6" is arithmetic of its own.  The test
   [test_gapgen_roles_review.py:30-35](../../assistant_axis/tests/test_gapgen_roles_review.py)
   (`test_occupation_too_high_after_17_accepts_at_339`) holds `n_now` at 339 while adding 17 to occupation, which
   is not what 17 accepts do: they raise `n_now` too, and occupation-only accepts tip the chip at about 35
   (`162 + a > 1.1 x 0.478 x (339 + a)` gives `a > 34`), while a kind of 8 tips on one or two.  Fix the two
   examples, make the test's setup say what it tests, and keep in mind for the readout's text that the margin is
   10% of the held count, so the chip moves slowly on the big kinds and fast on the small ones.

5. **R1 in a roles build keeps the trait tiers and escalation.**
   [review_graph.py:120-123](../../assistant_axis/gapgen/review_graph.py) (`CUT_OFF = 4`, proposed 3),
   `PairCandidate.cut_off` (line 576) and `reading_of` (511-515) are untouched, so two role candidates reading 3 one
   way and 2 the other (a sub-role beside its parent, both candidates) are a *proposed* group, and a Sonnet 2 between
   candidates is not read by Opus, while M3's walk covers at 3 and escalates a Sonnet 3 or 2.  The first is
   defensible for a review (Roger decides whether to keep both, and nothing is lost); the second is an asymmetry
   between the two readers of one rubric.  Record the choice in the plan's as-built notes and in
   [overlap_concept_roles.md](./rubrics/overlap_concept_roles.md)'s "What it is for"; align the escalation if it is
   cheap.  Question 2 below.

6. **The single-call M1 pipeline leaves a role-aimed row unrouted.**  `FilterRunner` writes no `role_route`
   ([filter.py](../../assistant_axis/gapgen/filter.py), the `holding_for(..., entity_type=...)` call), so
   `is_role_row` ([roles_pass.py:111-116](../../assistant_axis/gapgen/roles_pass.py)) is false for it and the trait
   builder ([novelty_runner.py:221-222](../../assistant_axis/gapgen/novelty_runner.py)) refuses only rows with a
   route: a role-aimed row filtered with `--pipeline single` and a `trait` verdict would enter the trait flow.  The
   default is `split` and B's follow-up prints it.  Refuse `--pipeline single` for role-aimed items, or refuse on
   `entity_type` alone in the trait builder (keeping `not_a_trait` for the held rows, which
   [test_gap_generation_llm_entropy_cli.py](../../data_analysis/tests/test_gap_generation_llm_entropy_cli.py)
   asserts).

7. **`submit --transport` defaults to `batches`**
   ([professions_generator.py:784](../../data_analysis/gap_generation/professions_generator.py)), so the printed
   M1 and M3 commands for a 375-row wave (about $2.7 and $3.5 live) say `--transport batches`, against the
   under-$20 real-time rule; `lay` defaults to live.  Default live, and let Roger say when batched (he did for the
   pilot).

8. **ESCO's first live use pages the whole API on assumed field names.**
   [sources.py:424-475](../../assistant_axis/gapgen/generators/professions/sources.py): `max_pages` exists on the
   function and not on `fetch`, so there is no smoke run from the CLI.  Add `--esco-max-pages N` (and print one
   parsed row before writing) for wave 2.

9. **`ONET_CHANGES` is written from memory of the licence page**
   ([sources.py:71-76](../../assistant_axis/gapgen/generators/professions/sources.py), said so in a comment).  When
   Roger approves the downloads, read `onetcenter.org/license_db.html` (the licence check fetches it anyway) and
   match the statement's wording.

10. **Docs, small.**  [data_analysis/README.md](../../data_analysis/README.md)'s role-path block and B block are
    accurate against the code (read, every command checked against `build_parser`); the order of the pre-pilot
    steps is finding 1.  The plan's § 7a.4 says the Opus rule is "at the cut-off, one below it, or unsure", which
    is M3's; R1's is finding 5.

## 6. The builder's deviations and judgement calls

| deviation | sound? | note |
|---|---|---|
| keys `stem|R#n`, `split_key` still two fields, `parse_key` adds the type | yes | the callers unpack two; `make_key(*parse_key(k)) == k` tested |
| M1 routes by the first surviving primary reading | yes | that is "the most likely reading" of decision 3; recorded on the block; the routing test replays the 2026-09-29 answers trait-aimed and role-aimed and asserts every judgement field equal, only the routing fields differ |
| the gloss wave skipped for `role`, `both` **and** `turned_away` | yes | a turned-away row is `reject`; its gloss would be paid for and never read.  The alignment and descriptors waves run only on a gloss, so they are skipped with it (read, [split_runner.py](../../assistant_axis/gapgen/split_runner.py) wave 6) |
| the stage follows `--transport` | yes, and required by decision 4 | the batched stage is tested through the real `BatchTransport` on a fake batch client ([test_gapgen_roles_pass.py:234](../../assistant_axis/tests/test_gapgen_roles_pass.py)) |
| exact-label matches skip the stage | yes | 57 of the snapshot's 355 held rows (ran); a provisional candidate with an empty gloss is covered at stage 0 before any embedding, and would stall "no embedding", not crash, if the two label-set builders ever disagreed |
| `cross_type` always on in a roles run, off in a trait run unless `--cross-type` | yes | decision 5; embeddings only; the trait corpus is cached; never a decision (tested) |
| `--redecide`, relation-only and full-scan refused for a roles batch | yes | out of scope; refusing beats silently running the trait path |
| ("patient", "doctor") instead of nurse in the rubric pairs | yes | nurse is the rubric's own example; a pair in the prompt would test memory, not judgement |
| the kind readout follows § 6.4; the plan's examples inconsistent | the builder is right | minor 4 |
| promotion refusals per entity type; a trait stem allowed with the NOTE | yes | § 6.5 and decision 2; tested for a role file, a live role entry, a turned-down role entry, a corpus trait and a queue trait entry |
| Physicians 29-1210 takes 29-1211..29-1229; 459 broad groups | read, not ran | SOC 2018's structure has no 29-1220 and 459 broad occupations (read); the 459 on the real files is a test that skips without them |
| the extra cut `occupation_title` | yes | the broad group's call already names that role |
| group ids prefixed; `source_ref` forms; one ranking row per stem | yes | a role two groups name carries both refs; `source_line` strips a label-fit tag after `;` |
| ESCO as JSONL from the API, shape unchecked | honest and flagged | minor 8 |
| already-registered rows resubmitted for provenance | yes | [traithood_filter.py](../../data_analysis/gap_generation/traithood_filter.py) `--run` filters only rows with no filter block (read, `unfiltered_or_rescued`), so a resubmission costs no call; the row gains its SOC source |
| 85% M1 pass in the downstream estimate | fine as a placeholder | labelled `M1_PASS_RATE`, with a 95% high band; replace by the pilot's figure |
| `ATTRIBUTION.md` with a statement of changes | yes | CC BY 4.0 asks for it; minor 9 on its wording |
| a promoted entry's `source` is the generator's attribution line | yes | better than the bare ref; § 6.5's example put the occupation's title in it, which the ref does not carry; the builder says so |
| `profession_lay` pinned with four wording fixes | yes | each resolves a contradiction or a reading the drafter missed; the change log says which |
| the sheet's texts are corpus descriptions | no | finding 1; not in the builder's list |
| tasks 19-20, the § 11 report, the frozen-interface copy not done | right | paid work waits for Roger; the copy is the main session's |

**label-fit for B (the builder's question).**  [label_fit.md](./rubrics/label_fit.md) is trait-framed throughout
("the name another program gave to a trait", "a lasting trait of a person", a better label "a single word whose most
common sense, said of a person, is the trait"), and its corrections rename candidates
(`corrected_candidates`, which now keeps the role fields: tested).  On a role gloss it would be asked whether
"bouncer" said of a person is the *trait* the gloss describes, and could propose an adjective.  My view: skip it for
B's wave 1.  The lay call writes the role and its gloss in one reading, so label and gloss fit by construction, which
is the mismatch the check was built for (a generator's label from one source, its gloss from another); the risk the
check guards against is small here and the risk it adds (a trait-framed judge renaming roles) is not.  Keep the
command, have it print that the rubric is trait-framed, and decide on a role version after the pilot's review shows
whether role labels drift from their glosses.  If a role version is wanted, it is three substitutions (role for
trait, "who or what a persona is" for "a lasting trait of a person", a phrase allowed as the better name) and a new
pin.

## 7. Prompt findings

Read as rendered, in the five files.  Reason first where the call decides (role kind, relation, overlap, lay); no
"think"; labels through `prompt_label` (the judge display form) in every builder; US spelling in every block.

* **[role_gloss.md](./rubrics/role_gloss.md).**  Fits the data: one item a call with `"id": 1`, the reading M1
  accepted or `null`, which the last rule covers.  The two readings shown are the snapshot's (ran).  For the state-tagged
  rows (captive, housebound) the reading is a state and the gloss will describe a circumstance, which is decision 5.
  No fault.
* **[role_kind.md](./rubrics/role_kind.md).**  Byte for byte the classifier's; both readers load it; the sha is the
  side-car's (ran).  No fault.
* **[relation_roles.md](./rubrics/relation_roles.md).**  The list goes under `"roles"` as the text says
  (`relation_payload(list_key=...)`), ids number the listed roles in the order given; the rendering in the file is
  the code's (a test pins its digest).  No fault.
* **[overlap_concept_roles.md](./rubrics/overlap_concept_roles.md).**  Line 3 directional, line 2 names the reverse
  case, the three variants read as intended.  "What it is for" says the Opus rule is M3's at cut-off 3; R1's differs
  (minor 5).
* **[profession_lay.md](./rubrics/profession_lay.md).**  The four changes are right.  One thing the rendering shows
  and the text leaves alone: "one to three lay roles" caps the biggest groups where the cap bites most (Physicians,
  19 occupations, a dozen personas of their own: cardiologist, psychiatrist, radiologist, dermatologist, ...); the
  union of three readings brings in at most nine and in practice fewer, since the readings agree on the first two
  or three.  The builder's "Read for fit" notes it and leaves it.  A rubric change is free now (no run yet):
  question 3 below.

## 8. Tests

**The six changed expectations**, each read against the spec:

| change | justified? |
|---|---|
| (1) `holding="roles"` is now a pass; `"nationalities"` stands in as the unknown list | yes: the test still exercises the `ValueError` path |
| (2) "never promoted" becomes "promoted only by name (--allow-roles)" | yes: the policy changed by decision § 1.11; the refusal says how |
| (3) a role's `href` is `/files/roles/hacker.json` | yes: the route exists and is tested |
| (4) `PINNED_NAMES` includes `ROLE_NAMES`, non-overlap asserted | yes |
| (5) `candidates.jsonl` lines gain `entity_type`, `kind_guess`, `human` | yes: `CANDIDATE_FIELDS` is the contract; old lines read as traits (tested) |
| (6) the censuses acceptance accepts the nine-field form beside the twelve | yes: recorded runs keep their form |

None hides a regression.  **New tests** test behaviour, not the code's shape: the M1 routing test replays the
recorded answers and compares the two aims field by field; the stage's budget stop, resume and batched transport
run on fakes; M3, R1, R2 and promotion run end to end on a ten-role fixture; B runs through all seven commands on
fakes, including the cost guard refusing before any call, the wave arithmetic and the readout tipping to too high;
`cross_type` is shown never to change a decision by running a trait fixture with and without it.  **Paid paths**:
none reachable from a test (ran: every client is `FakeAsyncAnthropic`, the HTTP layer is injected, `licence_check`
takes `text_fn`, the real `UrllibHttp` methods are `pragma: no cover`; a test that reads the real role corpus makes
no call).  The digests pinned: the role-kind sha, the relation rendering, variant 1 of the lay call.

## 9. Money and records

| call site | tracker | side-car | cap and flag | dry run |
|---|---|---|---|---|
| the stage (`score --holding roles`) | the run's `GuardedUsage` | the batch's `usage.json`, with M3's | `--budget-usd`, `confirm_or_abort` | prints the first row's two requests and both estimates |
| `retrieval-check` | `GuardedUsage` | `usage.json` in its run dir | default $1 | ran: $0.044 estimated, the gloss request rendered, nothing written |
| `rubric-check` | `GuardedUsage` | `usage.json` | default $2 | ran: refused with 40 of 40 unmarked |
| R1 roles build | as the trait build | `usage.json` | as before | as before |
| B `lay` | `RunGuardedUsage` (sessions summed) | the run's `usage.json` | `--budget-usd` required | renders a row per kind |
| B `rank` | the same | the same | default $0.50 | prints the embedding estimate |
| B `label-fit` | [label_fit.py](../../data_analysis/gap_generation/label_fit.py)'s | `label_fit/` | default $2 | passed through |
| B `submit` | zero-call | `usage.json` | $10 on the downstream estimate; `--all` over $20 refused without the flag (tested) | prints the follow-ups |
| `fetch` | none (no call) | manifest rows | `--approved-by` | ran: the plan printed, nothing requested; without approval refused before any request |

Batch usage is kept under `<model>:batch` through the existing transports.  Nothing here reads `.env` but through
`load_dotenv` in the CLIs and the embedder.

## 10. What is good

* The M1 routing is built so that a trait-aimed run is provably unchanged: the same items, the same recorded
  answers, every judgement field equal, and only `role_route`, `routes_version`, the holding and the entity type
  differ; decision 3 is one table and one flag, as asked.
* The stage has the right shape for money: every response on record before it is parsed, a resume replays by
  (step, prompt, model, user turn, reading), a budget stop raises after the answers in hand are recorded, parse
  rates warned; and the batched path is tested through the real transport.
* The kind rubric moved without changing a byte, so the 340 corpus kinds on record stay valid and a candidate's kind
  is measured by the same text.
* `cross_type` is additive and shown to be so; the role index is centred on its own corpus; the retrieval check's
  acceptance line, arms and information form are exactly decision 11 and Roger's decision 3.
* Generator B is a ranked pick, not a sweep: the cut is explicit and reported by reason, the ranking is three
  z-scored features with named weights, the wave is metered to the kept share, attribution travels with every
  artefact (run directory, `run.json`, each promoted entry's `source`, the readout), and the download gate holds.
* The sheet is blind to the design's sets, the mark column is second, and the key records where every text came
  from.
* The docs are complete, every file a relative link, and the plan's as-built notes say what changed and why.

## 11. Claims checked

| claim | result (ran unless marked) |
|---|---|
| `role_kind.md` hashes to `11b559f0cff50189`; equals the base `SYSTEM`; `role_kinds.json` records it | all three equal |
| the five rubrics pinned at version 1 | [rubric_pins.py](../../data_analysis/gap_generation/rubric_pins.py) `check`: role_gloss, role_kind, relation_roles, overlap_concept_roles, profession_lay, each version 1 |
| § 8 test 17 lints | [lint_kind_collision.py](../../tools/lint_kind_collision.py) 0 findings; [sync_entity_lists.py](../../tools/sync_entity_lists.py) `--check` up to date (339 roles); [check_arrangements.py](../../data_analysis/check_arrangements.py) 0 problems |
| the suite (`test_gapgen_*.py`, `data_analysis/tests`) | 4,736 passed, 47 skipped, 11 failed.  8 of the 11 fail in the main checkout at its HEAD too (`test_corpus_regions_cover_every_trait_file`, the zodiac traits missing from its regions file; recorded runs' `run.json`; Roget label heads; the structural table); 3 need the real OEWN 2024 lexicon, absent from the worktree (`wn.Error: no lexicon found ... 'oewn:2024'`).  The one failure in a changed test, [test_gapgen_censuses_acceptance.py](../../assistant_axis/tests/test_gapgen_censuses_acceptance.py) `test_run_files[repairs-2026-10-15]`, fails at its line 71 (`KeyError: 'sources'` in the recorded run) after the changed assertion at line 64 passed, and fails in main too |
| the pilot material (the tracked snapshot, [registry.snapshot.jsonl.gz](../../data/candidates/registry.snapshot.jsonl.gz)) | 355 held rows (the plan says 382 in the live registry), all `entity_type: role`, 340 `role_person` and 15 `state`; every one a role row with an accepted reading; 57 exact-label matches (the plan: 57); 31 relabel blocks (the plan: 32); no `|R` row yet; the § 7a.1 readings for bouncer#1 and bot#1 are the snapshot's |
| the readout formula | `balance(REF, 339)`: all about right; the test's 179 at 339 too high, 178 about right |
| `fetch --dry-run` | the plan with sizes and licences, ISCO-08 and three others listed as not fetched; nothing requested |
| `fetch` without `--approved-by` | refused before any request |
| `retrieval-check --dry-run`, `rubric-check --dry-run` | as in section 9 |

**Not verified.**  The ESCO API's shape (no network); the OEWS workbook's layout and the 459 groups on the real
files (not downloaded; the test skips); SOC 2018's 29-1210 spillover (read from the structure, not run on a file);
the live registry's 382 held rows and 14 state-tagged rows (the snapshot has 355 and 15); the first live answers of
every rubric.

## 12. Questions that are Roger's to decide

1. **Regenerate the sheet with the retrieval check's glosses before you mark it** (finding 1)?  I recommend yes:
   $0.05 and a minute, and the marks then test the text pairs the pilot will read.
2. **R1 for roles: should a 3 between two candidates merge the sub-role into the parent, or stay a proposal** (as
   built, minor 5)?  I recommend as built: both are candidates, and a proposal costs you one decision.
3. **The lay call's cap of three roles a reading** (section 7): raise it for groups of more than ten occupations
   ("one to five"), or accept the under-count on the big medical and engineering groups, since the sub-role rule
   covers a specialty by a corpus parent and the job-title path recovers the common ones?  Free to change now.
4. **Label-fit on B's wave 1**: skip (my view, section 6), or run it as built with the trait rubric?
5. **`submit --transport` default** (minor 7): live, by the under-$20 rule, unless you want B's waves batched as
   the pilot is.

## Recommendation

**Merge after fixes**: finding 2 (the ranker's reader of the role setting) before the merge; finding 1 (the sheet's
texts and the order of the pre-pilot steps) before Roger marks; the minor items when the files are next touched.
