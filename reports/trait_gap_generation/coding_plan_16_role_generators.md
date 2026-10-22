# Coding plan: plan 16, build-order steps 1 and 2 (the shared role path; generator B, professions)

Written 2026-10-21 (Fable) in the [PLAN_FORMAT.md](./PLAN_FORMAT.md) shape from
[16_role_generators.md](./16_role_generators.md), whose § 12 records Roger's decisions of 2026-10-21, against the
platform as built ([coding_plan_platform.md](./coding_plan_platform.md), "Interface as built"; the physical pass of
[coding_plan_review.md](./coding_plan_review.md) § 8 is the template).  Scope: **§ 11 steps 1 and 2** of the idea
plan: (1) the shared role path (§ 3: role-mode submission, M1 routing for role-aimed rows, the role gloss and role
kind calls, M3 for roles with its two rubrics and the retrieval check, the review app's role pass with the kind
readout, `promote --allow-roles`, the kinds side-car), piloted on the rows M1 has parked on the `roles` holding list;
(2) generator B, lists of professions (§ 6), whose ranked pick supplies the occupation half of every wave.  Terms:
the [glossary](./glossary.md); a *role* is who or what a persona is (pirate, refugee, goldfish), a *trait* a
disposition it enacts; *M1* is the trait-hood filter, *M3* the novelty check
([retrieve, then judge](./glossary.md#retrieve-then-judge)), *R1* the review graph, *R2* the review app; a
*holding list* is the registry field `holding` that keeps a row out of the trait flow; the *registry* is
[registry.jsonl](../../data/candidates/registry.jsonl) (git-ignored, one per checkout; the tracked snapshot is
[registry.snapshot.jsonl.gz](../../data/candidates/registry.snapshot.jsonl.gz)); the *seed queue* is
[seed_queue.json](../../data/seed_queue.json).  Roger's review comments go into this file.

**The later generators.**  A, D (a), D (b) and C get coding plans of their own once the shared path's pilot has
given the role kept share (it sizes every wave).  This plan designs the shared path so that each plugs in without
platform work: a generator submits `Candidate`s with `entity_type="role"`, a `kind_guess` among the nine kinds, a
`human` guess and a `source_ref` that the review card shows as provenance (§ 6.1, § Frozen interface); the pass,
R1, R2 and promotion then run as for the pilot.  Nothing in those four generators is planned here.

## Decisions for Roger (decided 2026-10-22)

1. **ESCO and ISCO-08 (decision 7's condition).**  Findings in § 7d.  ESCO: no page names a licence for the
   classification files themselves, but two official pages say EU-owned content on europa.eu is CC BY 4.0 unless
   otherwise indicated, and nothing indicates otherwise; a third-party site says EUPL 1.2 (unverified).  ISCO-08:
   the files are there (2021 copies), no licence on their page, the ILO's policy puts data before May 2023 outside
   its automatic CC BY 4.0, and the 2012 volume reserves rights.  **Recommend**: treat ESCO as CC BY 4.0 on that
   evidence and build its adapter behind a source flag for wave 2 (wave 1 runs on option (a): SOC broad tier,
   O*NET descriptions, O*NET job titles); leave ISCO-08 out until a licence statement is found, and use only
   ESCO's occupations file, not its ISCO-groups file.  If Roger wants certainty before ESCO runs, the two
   addresses are the Publications Office (op-copyright@publications.europa.eu) and rights@ilo.org.
   **Decided (Roger, 2026-10-22): (a)**, ESCO as CC BY 4.0 behind a source flag for wave 2 (by the API, so no e-mail address is given), ISCO-08 out.
2. **A role candidate whose stem is a corpus trait** (specialist, young, optimist's twins): the eleven collisions
   are allowed by policy, but [test_collision_regression.py](../../assistant_axis/tests/test_collision_regression.py)
   fails until `COLLISION_NAMES` is updated, and the twins TODO in [ROLES_TO_ADD.md](../../data/roles/instructions/ROLES_TO_ADD.md)
   may drop some.  **Recommend**: promotion allows it with a loud NOTE naming the trait and the test to update, the
   card shows the trait twin among the nearest traits (decision 5), and Roger decides per case.  The alternative,
   refusing, loses roles the corpus already admits.
   **Decided (Roger, 2026-10-22): (a)**, allowed with a loud NOTE and the trait twin on the card; Roger decides per case.
3. **Query form of the retrieval check.**  The role gloss carries its label ("A bouncer is someone who ..."), so a
   query that keeps it finds the role's own description by the label alone.  **Recommend** the production query
   strips the opening "A/An <label> is" (§ 7b), the check is run on that form against 95%, and the label-kept
   form is reported beside it as information.
   **Decided (Roger, 2026-10-22): (a)**, the label-stripped production form against 95%, the label-kept form reported.
4. **Pilot transport.**  `--transport auto` sends 300 or more non-exact-label candidates through the Batches API;
   the pilot has about 325 (§ 10) for about $4.  **Recommend** `--transport live` (the under-$20 rule: turnaround
   over the saving).
   **Decided (Roger, 2026-10-22): (b), batched** (`--transport batches`) for this pilot; his under-$20 real-time rule otherwise stands.
5. **The 15 state-tagged rows on the roles list** (captive, fugitive, housebound, imprisoned, ostracized, shut-in
   and nine more, routed there by the states pass): **recommend** they stay in the pilot as circumstance
   candidates; their gloss comes from the role gloss call like any other.
   **Decided (Roger, 2026-10-22): (a)**, they stay, by the "lasts months or years" test, which captive, fugitive, housebound, imprisoned, ostracized, shut-in and the rest pass.  The exact set is the 14 rows of the `roles` list that M1 tagged `state` (2026-10-22); learning, minding and unauthoritative look like M1 errors, left to the role gloss call and review.
6. **One small dependency**: reading the BLS OEWS workbook needs `openpyxl` (pure Python, not a dependency
   today); the alternative is a hand-made CSV.  **Recommend** `uv add openpyxl`, asked for with the downloads.
   **Decided (Roger, 2026-10-22): (a)**, `uv add openpyxl`, asked for with the downloads.

## 1. Decisions already made

Each from [16_role_generators.md](./16_role_generators.md) § 12 ("Decided (Roger, 2026-10-21)") unless noted;
none is reopened here.

1. **The cap is the corpus's total size**, 500-600 roles, 339 on disk today (decision 1); waves are sized by
   review hours (§ 4).  Whether AI-persona roles count if they become traits is still Roger's.
2. **Balance: readout only, plus the card and the order** (decision 2): every wave prints the nine-way split
   before, submitted, kept and after; the card says whether the candidate's kind is too high, too low or about
   right (more than 10% above or below the count that keeps the kind's share as in
   [role_kinds.json](../../data/roles/role_kinds.json) on 2026-10-16); a review order shows the too-low kinds
   first; no automatic cut.
3. **A role-aimed row M1 reads as a trait goes to both flows, provisionally** (decision 3, open): the noun stays a
   role candidate (kind 8, temperament), its adjective sibling from the relabel helper enters the trait flow.
   Built as one routing table and one flag so the twins TODO can change it (§ 5a).
4. **Sub-roles are covered by their parent at overlap 3**, the card naming the parent (decision 4).
5. **Cross-type retrieval**: nearest traits shown as information; covered is decided against roles only
   (decision 5).
6. **B's sources**: (b) ESCO and ISCO-08 if their licences can be confirmed acceptable, else (a) the SOC broad
   tier with O*NET descriptions and O*NET job titles, ranked by familiarity and distance (decision 7; the
   findings are § 7d, the call is Decisions for Roger 1).
7. **B is second in the build order** (decision 10): its ranked pick, metered to about half of each wave's
   submissions, supplies the occupation half (§ 6 of the idea plan).
8. **M2's trait settings are reused for role retrieval, with a retrieval check** (decision 11): every corpus role
   queried with a fresh gloss from the role gloss call, recall at 10 against 95%; recalibrated only below it
   (20 against 14 words, centring on the role corpus's own mean), embeddings only; not leave-one-out.
9. **The nine kinds, one dimension** (Roger, 2026-10-16, [README](./README.md#generators-aimed-at-roles-roger-2026-10-10-unparked-for-planning-2026-10-16));
   the candidate's kind is read by the same rubric as
   [classify_role_kinds.py](../../data_analysis/classify_role_kinds.py), three readings, majority.
10. **The role gloss is in the corpus form** "A <role> is someone who ..." / "... is something that ..." (§ 3
    step 3), one sentence; no alignment call; the cut-off is flat at 3 (§ 3 step 5).
11. **Promotion is by name only** (`promote --keys ... --allow-roles`, the review app's apply), refused for the
    bulk path, writing an `entity_type: "role"` queue entry (§ 3 step 7; plan 06's decision 1 (a)).
12. **Prompt conventions** (Roger; [judging.md](../../.claude/rules/judging.md)): a short reason first, then the
    answer, never "think"; Haiku 5.5 and Sonnet 5.5 take no temperature; a call that decides is read three times
    and combined by majority, never gated on stability; a call that generates keeps the union with support.
13. **Role-mode rows are never merged with trait rows by bare name** ([entity-naming.md](../../.claude/rules/entity-naming.md)):
    a role row of a surface that has a trait row is a second row keyed by entity type (§ 6.1); labels reach every
    prompt through `prompt_label` (the judge display form); US spelling.

## 2. Out of scope

- Generators A, C, D (a) and D (b): their coding plans follow the pilot.  Nothing here downloads Wikidata, the
  SRD or Roget's person heads.
- Recalibrating M2 on role vectors, and the role/trait twins measurement (ROLES_TO_ADD's TODO).
- Changing the trait flow's decisions: the cross-type information added to trait M3 blocks (task 10) is additive
  and never changes a verdict.
- The extraction of promoted roles on the RunPod, and role-pair formation beyond `partner_hint` (the promotion
  and arrangements TODO in the [README](./README.md#low-priority-todos)).
- DOT, HISCO, ISCO-08 (unless a licence statement appears) and ESCO's ISCO-groups file.
- The AI-persona roles question (ROLES_TO_ADD § "AI-persona roles under the role judge").

## 3. Rule files to Read first

[provenance.md](../../.claude/rules/provenance.md) (`usage.json` through `MultiModelUsage` on every call site;
provenance envelopes on JSON outputs), [entity-naming.md](../../.claude/rules/entity-naming.md) (`entity_id`,
`judge_label`, `normalize_to_file_name`, the eleven collisions, US spelling), [judging.md](../../.claude/rules/judging.md)
(reason first; no temperature on 5.5 models; sampled outputs combined, never gated; parse-rate warning; the judge
display form), [trait-pairs.md](../../.claude/rules/trait-pairs.md) (the queue, [seed_entities.py](../../data_analysis/seed_entities.py), the
description-writing rules the gloss imitates, the role-pair check), [working-style.md](../../.claude/rules/working-style.md)
(render every prompt as the model receives it; review sheets show the field the pipeline acts on), and
[CLAUDE.md](../../CLAUDE.md) (the file-access boundary, the $20 confirmation, batch or real time, tests are
mandatory, hotlink every file).  **File-access boundary, restated for every Opus task prompt:** read and write
only under the repository and the session scratchpad; never list, read or stat anything else under the home
directory, not even to see whether something is installed or cached; a download goes to `data/external/` after
Roger's OK; never read `.env` or print a key.

## 4. Existing code to reuse

- [physical_pass.py](../../assistant_axis/gapgen/physical_pass.py): the shape of a pass (`HOLDING`, `BLOCK`,
  `candidate_from_row`, `provisional_candidate`, `request`, `pins`, `estimate`, `render`, `gloss_rows`,
  `queue_entry_extras`, `section_for`); [roles_pass.py](../../assistant_axis/gapgen/roles_pass.py) copies its structure.
- [split_runner.py](../../assistant_axis/gapgen/split_runner.py) and [split.py](../../assistant_axis/gapgen/split.py):
  M1's calls, `payload(step, ...)` (one JSON object with `"id": 1`), `verdict_tags_holding` (lines 629-642),
  `reroute_roles` (507-517, the precedent for a per-row reroute), `to_filter_block`; the kind call's parser.
- [novelty.py](../../assistant_axis/gapgen/novelty.py) and [novelty_runner.py](../../assistant_axis/gapgen/novelty_runner.py):
  `CorpusTrait`, `CorpusIndex`, `build_index`, `expand`, `build_shortlist`, `cut_off_spec`, `Walk`,
  `novelty_block`, `M3Candidate` (whose `cut_off` a subclass fixes: `near_duplicates.CorpusCandidate` is the
  model), `NoveltyRunner` (takes any index), `load_broader_rubric` / `BROADER_PINS` (a rubric pinned before
  [versions.json](./rubrics/versions.json) knows it; not needed once the new names are in `split_rubrics`).
- [novelty_score.py](../../data_analysis/gap_generation/novelty_score.py): `score --holding`, `PASS_LISTS`,
  `load_index`, `physical_gloss_stage`, `render --stand-in`, `GuardedUsage`, the Batches transport
  ([batches.py](../../assistant_axis/gapgen/batches.py)).
- [review_graph.py](../../assistant_axis/gapgen/review_graph.py) (`corpus_key`, `corpus_targets`,
  `target_path`, `_holding_of`, `_candidate_node`) and [review_app/decisions.py](../../assistant_axis/gapgen/review_app/decisions.py)
  (`member_card`, `_item`, `queue`, `counts`, `ORDERS`, `apply_decisions`), [server.py](../../assistant_axis/gapgen/review_app/server.py)
  (`/files/traits`, the order `Literal`), [static/app.js](../../assistant_axis/gapgen/review_app/static/app.js)
  (`renderCard`, `ORDERS`).
- [promote.py](../../assistant_axis/gapgen/promote.py) (`promote(... allow_physical, allow_released_states)`,
  `queue_entry_from_record`, the physical branch at lines 258-263 and 299-300 to mirror) and
  [gap_registry.py](../../data_analysis/gap_generation/gap_registry.py) (`cmd_promote`, `cmd_holding`,
  `cmd_submit`).
- [registry.py](../../assistant_axis/gapgen/registry.py) (`Candidate`, `CANDIDATE_FIELDS`, `submit_candidates`,
  `new_record`, `source_entry`, `_link_relabels`), [normalize.py](../../assistant_axis/gapgen/normalize.py)
  (`make_key`, `split_key`, `HOLDING`, `ENTITY_TYPES`), [nouns.py](../../assistant_axis/gapgen/nouns.py)
  (`relabel`, `relabel_candidates`), [filter.py](../../assistant_axis/gapgen/filter.py) (`items_from_records`,
  `holding_for`, `FilterResult.registry_fields`).
- [classify_role_kinds.py](../../data_analysis/classify_role_kinds.py): `KINDS`, `SYSTEM`, `user_message`,
  `parse_kind`, `combine`; its text becomes the pinned rubric (task 3).
- [split_rubrics.py](../../assistant_axis/gapgen/split_rubrics.py) and [rubric_pins.py](../../data_analysis/gap_generation/rubric_pins.py):
  the new rubric names go into a fifth table, `ROLE_FILES`, pinned in [versions.json](./rubrics/versions.json).
- [freq.py](../../assistant_axis/gapgen/freq.py) (`zipf_info`), [embed.py](../../assistant_axis/gapgen/embed.py)
  (`OpenAIEmbedder`, `EmbeddingCache`, `embed_texts`), [representation.py](../../assistant_axis/gapgen/representation.py)
  (`represent`), [retrieval.py](../../assistant_axis/gapgen/retrieval.py) (`query_text`).
- [base_model/sources.py](../../assistant_axis/gapgen/generators/base_model/sources.py) (`Source`, `ONET_NOTE`,
  `LICENCE_CHECK`) and [setup_external.py](../../data_analysis/gap_generation/setup_external.py) /
  `base_model_generator.py fetch`: the manifest-and-licence pattern for downloads; [DOWNLOAD_MANIFEST.json](../../data/external/onet/DOWNLOAD_MANIFEST.json)
  is the record to extend.
- [structural/submit.py](../../assistant_axis/gapgen/generators/structural/submit.py) and
  [masked_lm/submit.py](../../assistant_axis/gapgen/generators/masked_lm/submit.py): `select_wave`,
  `estimate_downstream_usd` (`M1_USD_PER_WORD = 0.0072`, `M3_USD_PER_PASSED_WORD = 0.011`, `BATCH_FACTOR = 0.5`),
  `review_terms_per_hour`, `followup_commands`.
- [label_fit.py](../../assistant_axis/gapgen/label_fit.py): the label-against-gloss check B's labels go through
  before submission ([QUESTIONS 204](./QUESTIONS.md)).
- [recovery.py](../../assistant_axis/gapgen/recovery.py) / [recovery_test.py](../../data_analysis/gap_generation/recovery_test.py):
  the harness (traits only today); B's recovery here is by string (§ 8 test 11), the paid harness for roles comes
  with D (b).
- [seed_entities.py](../../data_analysis/seed_entities.py): `seed_document`, `cmd_write` (role files), `generate`
  ([regenerate_role_instructions.py](../../data_analysis/regenerate_role_instructions.py), about $0.02 a role).
- [judge_pricing.py](../../assistant_axis/judge_pricing.py) (`MultiModelUsage`, `price_for_model`:
  Haiku 5.5 $0.10 / $0.50, Sonnet 5.5 $2 / $10, Opus 5.5 $4 / $20 per MTok, `text-embedding-3-large` $0.13),
  [judge.py](../../assistant_axis/judge.py) (`warn_if_low_parse_rate`), [entity_id.py](../../assistant_axis/entity_id.py)
  (`entity_id`, `parse_entity_id`, `corpus_display_name`, `judge_label`, `normalize_to_file_name`).

## 5. File layout

### 5a. The shared role path

New module [roles_pass.py](../../assistant_axis/gapgen/roles_pass.py), the role counterpart of
[physical_pass.py](../../assistant_axis/gapgen/physical_pass.py):

```python
HOLDING = "roles"; PASS_NAME = "roles"; BLOCK = "role_pass"; MODEL = "claude-haiku-5-5"
STEPS = ("role_gloss", "role_kind"); KIND_READINGS = 3
KINDS = classify_role_kinds.KINDS          # the nine (key, name, definition); re-exported, one source
ROLE_ROUTES = {"role": "role", "trait": "both", "membership": "membership", "state": "turned_away",
               "physical": "turned_away", "action": "turned_away", "evaluative": "turned_away",
               "not_a_persona": "turned_away"}      # decision 3 provisional; ROUTES_VERSION = 1
RELABEL_ROLE_AIMED = "auto"                 # the other half of decision 3: None turns the sibling off
REFERENCE_KINDS_2026_10_16 = {"occupation": 162, "stance": 47, "non_human": 44, "circumstance": 24,
                              "temperament": 22, "relationship": 20, "status": 9, "pastime": 8, "other": 3}  # 339, default.json left out
BALANCE_MARGIN = 0.10

def is_role_row(row) -> bool                       # holding == "roles", or entity_type == "role" and filter.role_route in ("role", "both")
def accepted_reading(row) -> Optional[str]         # as physical_pass
def gloss_of(row) -> Optional[str]                 # the role_pass block's gloss
def kind_of(row) -> Optional[str]; def human_of(row) -> Optional[bool]   # kind != "non_human"
def needs_stage(row) -> bool
def candidate_from_row(row) -> tuple[Optional["RoleCandidate"], Optional[str]]   # not_filtered | not_a_role_row | no_gloss
def provisional_candidate(row) -> "RoleCandidate"
class RoleCandidate(M3Candidate):                  # cut_off fixed at 3 under every rule set; region None; alignment None
def request(step, *, label, reading=None, gloss=None, model=MODEL, rubrics_dir=None, label_form=None) -> dict
def pins(rubrics_dir=None) -> dict                 # role_gloss, role_kind versions and sha256; ValueError on a mismatch
def estimate(n_rows, *, model=MODEL) -> Estimate   # one gloss call, three kind calls a row
def render(row, *, model=MODEL, rubrics_dir=None, label_form=None) -> str
async def stage_rows(rows, *, client, usage, batch_id, records_path, on_block=None, model=MODEL, concurrency=4,
                     retry_delays=None, rubrics_dir=None, label_form=None) -> dict[str, dict]
def run_stage_rows(rows, **kw) -> dict[str, dict]
def stage_summary(blocks) -> dict; def result_line(row, block) -> dict
def route_for(kind_call: str, *, entity_type: str) -> Optional[str]      # ROLE_ROUTES for a role-aimed row, None otherwise
def queue_entry_extras(entry, rec, queue, *, section=None) -> dict        # tags gap_gen, source:<g>, kind:<kind>, human:<bool>; section; description_draft the gloss
def balance(current: Mapping[str, int], n_now: int, *, reference=REFERENCE_KINDS_2026_10_16, margin=BALANCE_MARGIN) -> dict
def kind_status(kind, *, current, n_now) -> str    # too_low | about_right | too_high
def corpus_kind_counts(data_dir, queue, *, review_state=None) -> tuple[dict, int]   # files + live queue role entries + this review's promoted nominees
```

Changes in existing modules (each a task in § 9; the new module is [roles_pass.py](../../assistant_axis/gapgen/roles_pass.py)):

- [registry.py](../../assistant_axis/gapgen/registry.py): `Candidate` gains `entity_type: str = "trait"`,
  `kind_guess: Optional[str] = None`, `human: Optional[bool] = None` (appended to `CANDIDATE_FIELDS`;
  `read_candidates` accepts a line without them as trait); `new_record(surface, *, entity_type, ...)`;
  `submit_candidates` keys a role-aimed candidate by `make_key(stem, sense_id, "role")` and merges it into an
  existing row only when that row's `entity_type` is `role` (§ 6.1); `source_entry` carries `kind_guess` and
  `human`; relabel runs for role-aimed nouns under `RELABEL_ROLE_AIMED`, the sibling submitted as a trait.
- [normalize.py](../../assistant_axis/gapgen/normalize.py): `make_key(stem, sense_id=1, entity_type="trait")`
  gives `f"{stem}#{sense_id}"` for a trait and `f"{entity_id(stem, 'roles')}#{sense_id}"` (`optimist|R#1`) for a
  role; `split_key` returns `(stem, sense_id, entity_type)`; `entity_type_of_key`.
- [filter.py](../../assistant_axis/gapgen/filter.py): `items_from_records` puts `entity_type` in `meta`;
  `holding_for(verdict, tags, membership_kind, *, entity_type="trait")`; `FilterResult.registry_fields` never
  overwrites a submitted `role`.
- [split.py](../../assistant_axis/gapgen/split.py) / [split_runner.py](../../assistant_axis/gapgen/split_runner.py):
  for a role-aimed row the join is recorded as judged and `role_route` is written on the filter block from the
  primary reading's kind (`roles_pass.route_for`); `verdict_tags_holding(..., entity_type)` gives holding `None`
  and entity type `role` for routes `role` and `both`, holding `None` and the membership tags for `membership`,
  and verdict `reject` with the kind's tag for `turned_away`; the gloss, alignment and descriptors waves are
  skipped for routes `role` and `both` (the role gloss replaces them).  The 382 held rows are unchanged.
- [novelty_runner.py](../../assistant_axis/gapgen/novelty_runner.py): `candidate_from_row(row, *, holding=None)`
  hands `holding == "roles"` to `roles_pass.candidate_from_row` and refuses an `entity_type == "role"` row in a
  trait run (`not_a_trait_row`); [novelty.py](../../assistant_axis/gapgen/novelty.py): `load_role_corpus(data_dir)`
  ([default.json](../../data/roles/instructions/default.json) left out; label `corpus_display_name(stem, "roles")`; arrangements from the role files),
  `query_text(..., form="role_gloss_w14")`, `cross_type` on the block.
- [novelty_score.py](../../data_analysis/gap_generation/novelty_score.py): `--holding roles` (`PASS_LISTS["roles"]`),
  the stage before M3, the role index and rubrics, `cross_type` retrieval from the other index, `run.json`
  `pass: "roles"`; the new `retrieval-check` and `rubric-check` subcommands (§ 7).
- [split_rubrics.py](../../assistant_axis/gapgen/split_rubrics.py): `ROLE_FILES = {"role_gloss": "role_gloss.md",
  "role_kind": "role_kind.md", "relation_roles": "relation_roles.md", "overlap_concept_roles":
  "overlap_concept_roles.md", "profession_lay": "profession_lay.md"}`, in `PINNED_FILES`.
- [review_graph.py](../../assistant_axis/gapgen/review_graph.py): `corpus_key(stem, kind)` gives `role:<stem>`,
  `corpus_targets` reads the role files and the queue's role entries for a roles build, `target_path` knows
  `role:`, `_holding_of` picks the role builder from `novelty.pass`, nodes carry `outcome: "role"`, `kind`,
  `human`, `kind_guess`, `provenance`, `nearest_traits`; R1's own calls use the role rubrics in a roles build.
- [review_app/decisions.py](../../assistant_axis/gapgen/review_app/decisions.py): `member_card` adds `role_kind`,
  `human`, `kind_readout`, `nearest_roles`, `nearest_traits`, `provenance`; `_item` adds `kind`; `queue(order="kinds")`;
  `counts()` adds `balance`; `ORDERS` gains `kinds`; `apply_decisions` passes `allow_roles=True`;
  [server.py](../../assistant_axis/gapgen/review_app/server.py): `/files/roles/{stem}.json`, the order `Literal`;
  [app.js](../../assistant_axis/gapgen/review_app/static/app.js): the kind chip and readout, the balance line, `ORDERS`.
- [promote.py](../../assistant_axis/gapgen/promote.py): `promote(..., allow_roles=False)`; the roles branch mirrors
  the physical one; collision checks per entity type (§ 6.5); [gap_registry.py](../../data_analysis/gap_generation/gap_registry.py):
  `promote --allow-roles` (by name only), `holding --list roles` prints the gloss and kind once the block exists,
  `submit --entity-type role`.
- [classify_role_kinds.py](../../data_analysis/classify_role_kinds.py): `SYSTEM` loaded from
  [rubrics/role_kind.md](./rubrics/role_kind.md) through `split_rubrics.load_prompt`, byte for
  byte (its recorded `prompt_sha256` `11b559f0cff50189` must not change); `--from-pass BLOCKS` appends a pass's
  kinds (task 13).
- [seed_entities.py](../../data_analysis/seed_entities.py): `write` of a role entry with `gap_gen.role_kind`
  appends it to [role_kinds.json](../../data/roles/role_kinds.json) (`"from": "roles_pass:<batch_id>"`,
  `"input": "gloss"`).

### 5b. Generator B: `professions`

New package [generators/professions/](../../assistant_axis/gapgen/generators/professions/):

```python
# sources.py: what is downloaded, with sizes, licences, attribution (the base_model/sources.py pattern)
SOURCES = {"onet_occupations": Source(...on disk...), "onet_job_titles": Source(dest="onet/job_titles.csv", size_bytes=4_504_432, licence="CC BY 4.0", ...),
           "bls_oews_national": Source(dest="bls/oesm25nat.zip", licence="public domain", ...),
           "bls_soc_structure": Source(dest="bls/soc_structure_2018.xlsx", licence="public domain", ..., note="optional: OEWS carries the broad titles"),
           "esco_occupations": Source(dest="esco/occupations_en.csv", licence="CC BY 4.0 (Commission reuse policy; see plan)", ..., note="wave 2, Decisions for Roger 1")}
ATTRIBUTION = {...}                                  # one paragraph per source, written to ATTRIBUTION.md in every run directory
def fetch(keys, *, dest_root=DATA_EXTERNAL, approved_by: str, user_agent=...) -> list[dict]   # manifest rows; a 403 from BLS says to download by hand
def licence_check(key) -> bool                       # the page must name the licence (LICENCE_CHECK)
# soc.py
def broad_code(onet_or_soc_code: str) -> str         # "29-1212.00" -> "29-1210"; "29-1210" -> itself
def soc_tiers(code) -> dict                          # major, minor, broad, detailed
def read_oews_national(zip_path) -> dict[str, dict]  # OCC_CODE -> {title, o_group, tot_emp}
def broad_groups(onet_rows, oews) -> list[BroadGroup]   # 459 expected; BroadGroup(code, title, detailed: list[Occupation], employment)
# onet.py
def read_occupation_data(path) -> list[Occupation]   # Occupation(code, title, description)
def read_job_titles(path) -> list[JobTitle]          # JobTitle(code, title, short_title, sources)
def lay_title_candidates(titles, *, zipf, corpus_stems, max_words=2, min_zipf=3.0, n=300) -> list[JobTitle]
# lay.py: the Haiku call (rubric profession_lay)
def build_user(group: BroadGroup | JobTitleGroup) -> str          # one JSON object (§ 7a.5)
def parse_lay(text) -> tuple[Optional[dict], Optional[str]]
def combine_readings(readings: list[dict]) -> list[LayRole]       # union by normalized role; support 1-3; distinct_persona by majority; gloss from the first reading that has the role
async def lay_groups(groups, *, client, usage, readings=3, records_path, ...) -> dict[str, list[LayRole]]
# rank.py
def familiarity(role: LayRole, *, zipf, employment) -> dict        # zipf of the lay title; log10 employment of its broad code
def distance(role, *, role_index) -> dict                          # nearest corpus role, cosine, via role_gloss_w14
def rank(roles, *, weights=RANK_WEIGHTS) -> list[Ranked]           # z-scored sum: zipf, log employment, 1 - cosine; ties by employment
# submit.py
def net_new(ranked, *, registry_rows, corpus_stems, queue_stems) -> tuple[list, list]   # kept, already-registered (their provenance still merged)
def select_wave(ranked, *, wave_rows=300, share=0.5, kept_share: float) -> list        # n = share * wave_rows / kept_share, from the top
def to_candidates(selected, run_id) -> list[Candidate]             # entity_type "role", kind_guess "occupation", human True, source_ref "soc:29-1210" or "onet_title:33-9032.00:bouncer", partner_hint None, gloss_hint the lay gloss
def run_submit(run_id, *, ranking, wave_rows, share, kept_share, all_rows=False, dry_run=True) -> SubmitSummary
# report.py
def recovery_by_string(lay_roles, *, occupation_stems) -> dict     # the 162 hidden by string, at the broad level
def report_markdown(run_dir) -> str
```

CLI [professions_generator.py](../../data_analysis/gap_generation/professions_generator.py),
run directories `data/candidates/runs/professions/<run_id>/` with `table.jsonl`, `lay_responses.jsonl`,
`lay.jsonl`, `ranking.jsonl`, `candidates.jsonl`, `ATTRIBUTION.md`, `report.md`, `run.json`, `usage.json`.

## 6. Data schemas

### 6.1 A registry row in role mode (new fields in bold in the prose)

A role-aimed submission of a surface that already has a trait row.  Key `optimist|R#1` (the stem part is the
`entity_id`; the trait row `optimist#1` is untouched); `entity_type: "role"` from submission; the source carries
the generator's guesses; after M1, `filter.role_route`; after the stage, the `role_pass` block; after M3, the
`novelty` block with `pass: "roles"` and `cross_type`.

```json
{"schema_version": 1, "key": "optimist|R#1", "stem": "optimist", "sense_id": 1, "surface": "optimist", "label": "optimist",
 "gloss": null, "entity_type": "role",
 "sources": [{"generator": "professions", "run_id": "2026-10-28-wave1", "rank": 41, "score": 1.83, "source_ref": "onet_title:21-1013.00:optimist",
              "gloss_hint": "An optimist is someone who ...", "partner_hint": null, "surface": "optimist", "kind_guess": "temperament", "human": true}],
 "filter": {"pipeline": "split", "outcome": "trait", "verdict": "trait", "tags": [], "role_route": "both", "routes_version": 1, "...": "as today"},
 "role_pass": {"gloss": "An optimist is someone who expects things to turn out well, ...", "gloss_form_ok": true,
               "kind": "temperament", "kind_readings": [{"kind": "temperament", "reason": "..."}, {"kind": "temperament", "reason": "..."}, {"kind": "stance", "reason": "..."}],
               "kind_unanimous": false, "kind_split": false, "human": true, "reading": "someone who expects the best", "model": "claude-haiku-5-5",
               "batch_id": "roles_pilot_1", "step_versions": {"role_gloss": 1, "role_kind": 1}, "prompt_sha256": {"role_gloss": "...", "role_kind": "..."}, "at": "..."},
 "novelty": {"run_id": "roles_pilot_1", "pass": "roles", "decision": "covered", "reason": "exact_label", "covered_by": "optimist", "cut_off": 3,
             "alignment_score": null, "listed": [{"stem": "idealist", "cosine": 0.61, "rank": 1, "via": "retrieved", "relation": "similar"}],
             "cross_type": {"traits": [{"stem": "optimistic", "cosine": 0.74}, {"stem": "hopeful", "cosine": 0.66}]}, "...": "as today"},
 "holding": null, "review": {"status": "unreviewed"}, "seed_queue_stem": null, "rev": 4, "...": "..."}
```

A held row of the pilot keeps its plain key (`baker#1`, `entity_type: "role"`, `holding: "roles"`); a role-aimed
resubmission of `baker` merges into it (the row is already a role row), adding the SOC source.  The rule, in
`submit_candidates`: a role-aimed candidate merges into the row at `stem#sense` when that row's entity type is
`role`, else lives at `stem|R#sense`; a trait-aimed candidate never merges into a `|R` row.

### 6.2 `Candidate` (frozen interface, § Frozen interface)

```json
{"surface": "bouncer", "generator": "professions", "run_id": "2026-10-28-wave1", "rank": 12, "score": 2.41,
 "gloss_hint": "A bouncer is someone who works the door of a bar or club, ...", "sense_id": 1,
 "source_ref": "onet_title:33-9032.00:bouncer", "partner_hint": null, "entity_type": "role", "kind_guess": "occupation", "human": true}
```

### 6.3 The review card's role fields (`member_card`)

```json
{"key": "cardiologist#1", "label": "cardiologist", "gloss": "A cardiologist is a doctor who ...", "generator": "censuses",
 "role_kind": "occupation", "role_kind_unanimous": true, "human": true, "kind_guess": null,
 "kind_readout": {"status": "too_high", "count": 171, "held": 161.6, "margin": 16.2, "text": "occupation: too high (171 of 162 held at 339 + 12 accepted)"},
 "nearest_roles": [{"stem": "doctor", "cosine": 0.71, "relation": "similar", "reading": 3}, {"stem": "paramedic", "cosine": 0.52, "relation": "unrelated"}],
 "nearest_traits": [{"stem": "clinical", "cosine": 0.44}],
 "covered_by": null, "provenance": [{"generator": "censuses", "source_ref": "tda:cardiologist"}],
 "m3_decision": "new", "tags": ["role_person", "role"]}
```

A covered sub-role shows `covered_by: "doctor"` with the reading (decision 4), greyed as covered rows are.

### 6.4 The kind readout (`balance`)

```json
{"n_now": 351, "reference_total": 339, "margin": 0.1,
 "kinds": {"occupation": {"reference": 162, "share": 0.478, "count": 171, "held": 167.7, "status": "too_high", "room": -3.3},
           "pastime": {"reference": 8, "share": 0.0236, "count": 8, "held": 8.3, "status": "about_right", "room": 0.3}, "...": "..."},
 "order": ["pastime", "status", "other", "relationship", "circumstance", "temperament", "stance", "non_human", "occupation"]}
```

`held = share × n_now`; `too_low` when `count < (1 − margin) × held`, `too_high` when `count > (1 + margin) × held`;
`n_now` counts the role files (less `default.json`), the live role entries of the queue whose stem has no file,
and this review's promoted nominees; `count` likewise, the queue entry's kind from its `kind:<kind>` tag and a
nominee's from its `role_pass` block.  `order` sorts kinds by status (too low, about right, too high) then by
`room` descending.

### 6.5 The seed-queue role entry a promotion writes

```json
{"stem": "bouncer", "label": "bouncer", "entity_type": "role", "chunk": "gap", "sub_chunk": "professions",
 "pairing": "singleton", "partner": null, "partner_exists": null, "arrangement_members": null,
 "description_draft": "A bouncer is someone who works the door of a bar or club, checking IDs, turning away the drunk and the underage, and throwing out anyone who starts trouble.",
 "description_notes": "role pass roles_wave1 | kind occupation (3 of 3) | nearest roles: bartender 0.58 (0), guardian 0.49 (1) | nearest traits: intimidating 0.41",
 "description": null, "source": "O*NET 31.0 job title under 33-9032.00 Security Guards (CC BY 4.0, USDOL/ETA)", "tags": ["gap_gen", "source:professions", "kind:occupation", "human:true", "role_person"],
 "status": "candidate", "section": "role generators (2026-10)",
 "gap_gen": {"registry_key": "bouncer|R#1", "sources": ["professions/2026-10-28-wave1"], "rubric_version": 5, "holding": null,
             "role_kind": {"kind": "occupation", "unanimous": true, "readings": ["..."], "batch_id": "roles_wave1", "prompt_sha256": "11b559f0cff50189"}}}
```

A `partner_hint` gives `pairing: "pair"` with `partner` and `pair_by_construction: false`; the role-pair check
decides at seeding ([generate_antonyms.py --roles](../../data_analysis/generate_antonyms.py)).  Collision checks
at promotion, per entity type: a stem that is a role file, a live role queue entry or a turned-down role entry
refuses; a stem that is a trait file or trait entry is allowed with the NOTE of Decisions for Roger 2.

### 6.6 B's table rows

`table.jsonl` (one per SOC broad group, plus one per selected job title):

```json
{"kind": "broad", "code": "29-1210", "title": "Physicians", "employment": 782430, "detailed": [{"code": "29-1212.00", "title": "Cardiologists", "description": "Diagnose, treat, manage, and prevent diseases ..."}, "..."]}
{"kind": "job_title", "code": "33-9032.00", "occupation": "Security Guards", "title": "Bouncer", "zipf": 3.6, "employment": 1200000, "description": "Guard, patrol, or monitor premises ..."}
```

`lay.jsonl` (after the call, readings combined): `{"group": "29-1210", "roles": [{"role": "cardiologist", "covers": ["29-1212.00"], "distinct_persona": true, "support": 3, "gloss": "A cardiologist is ...", "votes": {"distinct_persona": [true, true, true]}}]}`.
`ranking.jsonl`: `{"role": "cardiologist", "stem": "cardiologist", "group": "29-1210", "zipf": 3.4, "employment": 782430, "nearest_role": "doctor", "cosine": 0.71, "score": 1.12, "rank": 37, "net_new": false, "registered_as": "cardiologist#1"}`.
[DOWNLOAD_MANIFEST.json](../../data/external/onet/DOWNLOAD_MANIFEST.json) rows as the O*NET one on disk (a [DOWNLOAD_MANIFEST.json](../../data/external/bls/DOWNLOAD_MANIFEST.json) beside the BLS files, not there yet), plus `"downloaded_by": "hand"` when BLS refused the fetch.

**As built (2026-10-22).**  Group ids are prefixed by kind (`broad:29-1210`, `job_title:33-9032.00:bouncer`,
`esco:5414`) in `lay.jsonl` and `ranking.jsonl`; a candidate's `source_ref` is `soc:29-1210`,
`onet_title:33-9032.00:bouncer` or `esco:5414` (§ 6.2), and a promoted entry's `source` is the attribution line
`professions.source_line` makes of it ("O*NET 31.0 job title under 33-9032.00 (CC BY 4.0, USDOL/ETA)"; the
occupation's title is not in the ref, so it is not in the line); a job-title row also carries
`label`, `stem`, `employment_source`, `also_under` and `short_title`; `ranking.jsonl` has one row per stem (a role
named by two groups is ranked once, with both as sources).  ESCO's occupations are kept as JSONL
(`data/external/esco/occupations_en.jsonl`, not there yet) from its API; the API's response shape is taken from its
documentation and not yet checked against a live answer (`sources.ESCO_UNVERIFIED`).

## 7. CLI

All through `uv run python`; every paid command prints its estimate, takes `--budget-usd` (hard cap), needs
`--confirm-expensive --confirmed-by` over $20, refuses a dirty platform tree without `--allow-dirty`, writes
`usage.json` beside its output, and has `--dry-run` (rendered requests, the plan, no call).

- `novelty_score.py score --holding roles --batch-id roles_<name> (--unscored | --run G/R | --keys K ...) [--transport live|batches|auto] --budget-usd C`:
  the stage (role gloss, then three role kind readings) for rows without a `role_pass` block, written on the
  registry as each row finishes; then M3 against the role index (§ 7b) with `relation_roles` and
  `overlap_concept_roles`, cut-off 3, `cross_type.traits` from the trait index; `run.json` and every block carry
  `pass: "roles"`; a resume across passes is refused.  Dry run: the stage's rendered requests for the first row,
  the M3 plan and both estimates.
- `novelty_score.py render --stand-in STEM --pass roles` and `render --key K`: the relation and overlap requests
  as sent (used for the rendered samples before pinning, task 4).
- `novelty_score.py retrieval-check --batch-id roles_retrieval_1 --budget-usd 1 [--forms role_gloss_w14,label_gloss,role_gloss_w20] [--space centred,raw]`:
  § 7b; writes [glosses.jsonl](../../data/candidates/novelty/roles_retrieval_1/glosses.jsonl), [recall.json](../../data/candidates/novelty/roles_retrieval_1/recall.json), [recall.md](../../data/candidates/novelty/roles_retrieval_1/recall.md) and [usage.json](../../data/candidates/novelty/roles_retrieval_1/usage.json) under `data/candidates/novelty/roles_retrieval_1/` (not there yet).
- `novelty_score.py rubric-check --pairs reports/trait_gap_generation/role_rubric_pairs.md --batch-id roles_rubric_1 --budget-usd 2` (the marked sheet, [role_rubric_pairs.md](./role_rubric_pairs.md), blank until Roger marks it; the command parses its mark column):
  § 8 test 7; writes [readings.jsonl](../../data/candidates/novelty/roles_rubric_1/readings.jsonl), [kappa.json](../../data/candidates/novelty/roles_rubric_1/kappa.json) and [readout.md](../../data/candidates/novelty/roles_rubric_1/readout.md) under `data/candidates/novelty/roles_rubric_1/` (not there yet).
- `review_graph.py build --batch-id review_roles_<name> --from-batches roles_<name> --budget-usd C`: unchanged
  flags; a roles build is detected from the batches' `pass` and uses the role rubrics and corpus targets.
- `review_app.py serve --batch-id review_roles_<name> --order kinds`; `status`; `apply [--dry-run]` (promotes with
  `allow_roles=True`).
- `gap_registry.py promote --keys K ... --allow-roles [--section S] [--dry-run]`; `promote --status accepted`
  still refuses a role row; `gap_registry.py submit --from DIR/candidates.jsonl` reads `entity_type`;
  `holding --list roles` shows gloss and kind.
- `classify_role_kinds.py --from-pass data/candidates/novelty/roles_<name>/role_pass.jsonl` (no call): appends
  the pass's kinds for stems that now have files; `seed_entities.py write` does the same per entry.
- `professions_generator.py`:
  - `fetch [--only KEY ...] --approved-by "Roger, <date>"`: the downloads of § 7d, licence page checked, manifest
    written; no call.  Refused without `--approved-by`.
  - `build --run-id R`: `table.jsonl` from the files on disk; `report` prints the 459 broad groups, the job-title
    cut, and the recovery by string of the 162 corpus occupations at the broad level (free).
  - `lay --run-id R [--readings 3] [--transport live|batches] --budget-usd C`: the Haiku call per group and per
    selected title; `lay_responses.jsonl`, `lay.jsonl`; dry run renders one group and one title.
  - `rank --run-id R [--weights zipf=1,employment=1,distance=1]`: embeddings through the cache (pennies);
    `ranking.jsonl`; prints the top 40 with their nearest corpus role.
  - `label-fit --run-id R --budget-usd C`: the platform's label-fit check on the selected labels and glosses
    (`label_fit.py`), as the other generators run it before submission.
  - `submit --run-id R --wave-rows 300 --share 0.5 --kept-share P [--all] [--dry-run]`: § 7d's metering;
    `candidates.jsonl`, `ATTRIBUTION.md`, the registry; prints the M1 and M3 commands to run next
    (`traithood_filter.py --run professions/R`, then `novelty_score.py score --holding roles --run professions/R`).
  - `report --run-id R`: `report.md` (sources, cut, recovery by string, ranking summary, the occupation share
    before and after at the held share).

### 7a. Rubrics, drafted in full, with rendered samples

Each lives in [rubrics/](./rubrics/) in the fenced-block format `split_rubrics.load_prompt` reads, first pinned
as version 1 with [rubric_pins.py](../../data_analysis/gap_generation/rubric_pins.py) `bump NAME --version 1 --why ...`; the user turn is one JSON object.  Opus
renders each from the real code (`render`) before the pin and puts the rendering in the rubric file, as
[relation.md](./rubrics/relation.md) does.  Labels in the samples are in the judge display form.

#### 7a.1 [role_gloss.md](./rubrics/role_gloss.md): the role gloss call

Haiku 5.5, one item per call, M1's request settings (`split_runner.MAX_TOKENS_THINKING`, no temperature), the
system prompt cached.  Adapted from [gloss.md](./rubrics/gloss.md) draft 4 to the role corpus's form (the
description rules of [trait-pairs.md](../../.claude/rules/trait-pairs.md) § "Description-writing rules", rules 1-3).

````text
Each item gives a label and one reading of the instruction "You are <label>." Write a one-sentence description of the persona that fits that reading, in the form a corpus of roles uses. The description will be read beside the label, by someone who needs to know exactly what is meant.

How to write it:
- Begin with the label. For a person: "A <label> is someone who ...". For a being, creature, thing or system that is not a person: "A <label> is a <what it is> that ..." or "A <label> is something that ...". Write "An" before a vowel sound.
- After "someone who" go straight to what the persona does, where, with what and with whom: the work, the tools, the customers, the hours, the enemy. Name the particulars of its world, not its category: "runs a boiler from a panel through a twelve-hour shift", not "performs industrial tasks".
- One sentence, about 20 to 35 words.
- Describe a standing identity, not a passing moment.
- Say it plainly. A bad role is bad: a smuggler moves contraband for money. Do not soften, hedge or excuse: no "may", "sometimes", "tends to", "often", "appropriately".
- Use the words the persona would use of itself, not the words of a case report or a job advertisement: no "professional responsible for", "individuals who", "engages in", "demonstrates".
- Do not define the role by what it is not, and do not name an opposite or a neighboring role.
- Keep to the reading you were given, whether it is narrower or wider than the label's usual sense. Do not widen it to other meanings of the label. If the reading is null, write for the label's most usual sense as said of a person or being.
- US spelling.

Respond with one JSON object and nothing else:
{"results": [{"id": <int>, "gloss": "<one sentence>"}]}
Return one row per id, in the order given.
````

Rendered user turns (`roles_pass.request("role_gloss", ...)`, one object with `"id": 1`; the readings are M1's, from real rows of the tracked registry snapshot). *Replaced 2026-10-22 (Opus, the build) by the code's own rendering, as the rubric file has it; the drafter's expected answers are left out, the model's own come with the pilot.*

```
--- variant 1: a held row (bouncer#1, on the roles list), M1's accepted reading ---
{"id": 1, "label": "bouncer", "reading": "works as a club or bar doorman who checks entry and removes troublemakers"}

--- variant 2: a non-human role (bot#1, on the roles list), M1's accepted reading ---
{"id": 1, "label": "bot", "reading": "act as an automated program or chatbot"}

--- variant 3: the retrieval check, a corpus role glossed with no reading ---
{"id": 1, "label": "operator", "reading": null}
```

#### 7a.2 [role_kind.md](./rubrics/role_kind.md): the role kind call

The `SYSTEM` string of [classify_role_kinds.py](../../data_analysis/classify_role_kinds.py), moved into a rubric
file **byte for byte** (two spaces after each period as in the source; the file's block must hash to the sha the
side-car records, `11b559f0cff50189` over the first 16 hex digits) and loaded by both readers.  Haiku 5.5,
`max_tokens` 2000, three readings, majority (`combine`), user turn `user_message(label, gloss)`.

````text
You sort personas into kinds.  Each persona is a role that a language model can be asked to take on.  Choose the one kind below that best says what the role is.  If a role could fit two kinds, choose the one that is most central to it.  A non-human role is always "non_human", whatever it does.  "other" is for a role that fits none of the kinds.

The kinds:
- "occupation" (occupation or task): a job, profession or function someone performs, assistant-style functions included (accountant, doctor, summarizer)
- "relationship" (life stage, family and relationship): a stage of life or a place in a family or relationship (infant, elder, parent, widow)
- "circumstance" (circumstance): a situation one is in rather than something one does, migration and legal standing included (homeless, patient, pregnant, refugee, prisoner)
- "status" (status or wealth): a social rank or level of wealth (aristocrat, billionaire, beggar)
- "stance" (stance or way of life): a chosen conviction, cause or way of living, the lawless included (activist, vegan, pacifist, smuggler, spy)
- "pastime" (pastime): a hobby or leisure pursuit (gamer, surfer, collector)
- "non_human" (non-human being): anything that is not a human being: mythic, fantasy and fictional creatures (elves included), machines, robots and AIs, animals, plants and natural systems (angel, vampire, robot, cyborg, coral reef, tree, swarm)
- "temperament" (a temperament under a noun): a personality trait expressed as a noun for a kind of person (optimist, cynic, perfectionist)
- "other" (other): anything that fits none of the above (void, zeitgeist, default)

Answer with one JSON object and nothing else.  Give the reason in one short sentence first, then the kind: {"reason": "<one short sentence>", "kind": "<one of the kind keys above>"}
````

Rendered user turns (`classify_role_kinds.user_message(label, text)`, which both readers build). *Replaced 2026-10-22 (Opus, the build) by the code's own rendering, as the rubric file has it; the drafter's expected answers are left out, the model's own come with the pilot.*

```
--- a corpus role (classify_role_kinds.py; the description is the role file's) ---
Role: operator
Description: An operator is someone who runs a boiler, a crane, a press, or a refinery unit from a panel or a cab: watching gauges and alarms through a twelve-hour shift, following the checklist, and calling maintenance when the readings drift.

--- a candidate (the roles pass's stage; the description is the candidate's role gloss, written by the call before) ---
Role: bouncer
Description: <the role gloss the role gloss call wrote for bouncer#1>
```

#### 7a.3 [relation_roles.md](./rubrics/relation_roles.md): the relation call for roles

Haiku 5.5, one call per candidate, every listed role in a seeded shuffle, uncached, `max_tokens` 4096; `unsure`
answers re-asked of Sonnet 5.5, as [relation.md](./rubrics/relation.md).  The three answers kept; the examples
are roles (doctor, guardian, destroyer, predator, prey, healer, pilot are corpus roles).

````text
You are given one JSON object: a persona role, the candidate ("candidate"), with a one-sentence description, and a numbered list of other persona roles ("roles"), each with its description. A role is who or what a persona is: a person, a being, a thing or a system. For each listed role, say how it stands to the candidate.

Judge the meaning of the two descriptions, not how often the two roles meet or work together. A doctor and a nurse work side by side and are different roles.

Give one of these answers for each listed role:
- "similar": the two roles are close: the same role under another name, or one a kind of the other, or one the other narrowed to a setting, or two roles that share a core. For example, doctor and physician; cardiologist and doctor; bush pilot and pilot; healer and doctor.
- "opposed": the listed role is the counterpart of the candidate: the other side of the same relation, or the same place in the world taken the opposite way. For example, predator and prey; guardian and destroyer.
- "unrelated": different roles, connected at most by belonging to the same broad area. For example, doctor and plumber: both are trades, and that is all they share.
- "unsure": you cannot tell from the two descriptions.

For each listed role give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed role's id>, "reason": "<one short sentence>", "relation": "similar"|"opposed"|"unrelated"|"unsure"}]}
Return one row per listed role, in the order given.
````

Rendered user turn, from the code: `novelty_score.py render --pass roles --stand-in detective` (the corpus role detective standing in for a candidate, itself hidden: its description stands in for a role gloss and its cached corpus embedding for the query, so the listed roles are the role corpus's real nearest under M2's settings; five corpus roles not yet in the embedding cache were left out of this rendering's index). Shuffled by run and candidate, no cosines or ranks; descriptions are the corpus files' own. *Replaced 2026-10-22 (Opus, the build) by the code's own rendering, as the rubric file has it; the drafter's expected answers are left out, the model's own come with the pilot.* The plan's stand-in was the candidate `cop` with the ten nearest by hand.

```
{"candidate": {"label": "detective", "description": "A detective is a professional investigator who systematically analyzes evidence, examines clues, and uses deductive reasoning to solve mysteries and uncover the truth."},
 "roles": [
  {"id": 1, "label": "designer", "description": "A designer is a creative professional who develops visual and functional solutions, combining aesthetic sensibilities with practical problem-solving skills to create compelling and effective designs across various media and contexts."},
  {"id": 2, "label": "veterinarian", "description": "A veterinarian is a medical professional who specializes in the diagnosis, treatment, and prevention of diseases and injuries in animals, providing healthcare services for pets, livestock, and other non-human patients."},
  {"id": 3, "label": "fixer", "description": "A fixer is a shadowy problem-solver who specializes in making inconvenient situations disappear through any means necessary, often operating outside legal boundaries and using questionable methods."},
  {"id": 4, "label": "mechanic", "description": "A mechanic is a hands-on problem solver who fixes and maintains machines and systems, drawing from practical experience with tools, parts, and troubleshooting methods."},
  {"id": 5, "label": "debugger", "description": "A debugger is a technical troubleshooter who systematically identifies, analyzes, and resolves problems in various systems, using methodical approaches and diagnostic techniques to trace issues to their root causes."},
  {"id": 6, "label": "researcher", "description": "A researcher is someone who systematically gathers, analyzes, and synthesizes information on specific topics, often employing rigorous methodologies and evidence-based approaches to investigate questions and draw conclusions."},
  {"id": 7, "label": "spy", "description": "A spy is a covert intelligence operative who works in secrecy to collect sensitive information through surveillance, infiltration, and deception."},
  {"id": 8, "label": "doctor", "description": "A doctor is a physician who examines patients, works out what is wrong with them, and treats it: ordering tests, making diagnoses, prescribing medication, carrying out procedures, referring on to specialists, and talking to patients."},
  {"id": 9, "label": "scientist", "description": "A scientist is someone who systematically applies scientific methods, evidence-based reasoning, and empirical investigation to understand and explain natural phenomena and solve problems."},
  {"id": 10, "label": "analyst", "description": "An analyst is someone who systematically examines data, information, and situations to identify patterns, draw insights, and provide evidence-based conclusions and recommendations."}
 ]}
```

Read for fit: "one JSON object", "the candidate", "a numbered list of other persona roles (\"roles\")" and "the listed
role's id" all match what is sent (one candidate a call, the list under `"roles"`, ids numbering the listed roles in
the order given); the candidate's description is a one-sentence description in the corpus form, as its role gloss will
be.  The neighbours of this stand-in (debugger, scientist, analyst, spy) show the case the overlap call's line 1
(neighbours) and line 0 cover; none is the same role.  No mechanical fault; the text was pinned as drafted.

#### 7a.4 [overlap_concept_roles.md](./rubrics/overlap_concept_roles.md): the overlap call for roles

Sonnet 5.5 first, Opus 5.5 where `sonnet_action` sends the pair (at the cut-off, one below it, or unsure), one
pair per call, the system prompt cached.  Rubric A's scale with the hierarchy made explicit (§ 3 step 4), and
**line 3 made directional**: a candidate that is a kind of a corpus role is covered (decision 4), a candidate
that is the wider role is not (a worker is not a union member), so the wider case reads 2.  No broader check for
roles: the direction is in the rubric.

````text
You are given one JSON object: a persona role, the target ("target"), and one other persona role ("other"), each with a one-sentence description. A role is who or what a persona is: a person, a being, a thing or a system. Say how close the other role is to the target: the same role, or a different one?

Judge the meaning of the two descriptions, not how often the two roles meet or work together. A doctor and a nurse work side by side and are different roles.

Give one of these answers:
- 4: the same role under another name. Either label could replace the other in any description of a persona. For example, cop and police officer.
- 3: the target is a kind of the other, or the other narrowed to a setting, a specialty or a rank: a persona in the target role is also in the other role, and what it does all day is one part of what the other role does. For example, the target cardiologist with the other doctor; the target bush pilot with the other pilot; the target sergeant with the other soldier.
- 2: overlapping roles. They share a core, but the target is not a kind of the other: a persona can be either without being the other, and each adds something the other lacks. This includes the other being a kind of the target, the target the wider role. For example, healer and doctor; the target doctor with the other cardiologist.
- 1: neighboring roles: they work in the same world or with the same people, but one is not a kind of the other and they do different things. For example, judge and lawyer.
- 0: different roles, connected at most by belonging to the same broad area. For example, doctor and plumber.
- "opposite": the other role is the counterpart of the target: the other side of the same relation, or the same place in the world taken the opposite way. For example, predator and prey.
- "unsure": you cannot tell from the two descriptions.

Give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"reason": "<one short sentence>", "similarity": 0|1|2|3|4|"opposite"|"unsure"}
````

Rendered user turns (`overlap_test.render_single`, the form M3's walk and R1 send; the target's description its role gloss, a stand-in until the stage has written one; the other's the corpus file's). *Replaced 2026-10-22 (Opus, the build) by the code's own rendering, as the rubric file has it; the drafter's expected answers are left out, the model's own come with the pilot.*

```
--- variant 1: a sub-role against its parent (expected 3: covered, the card names doctor) ---
{"target": {"label": "cardiologist", "description": "A cardiologist is a doctor who treats the heart: reading ECGs and echocardiograms, managing blood pressure and failing hearts, placing stents, and seeing the same patients for years."},
 "other": {"label": "doctor", "description": "A doctor is a physician who examines patients, works out what is wrong with them, and treats it: ordering tests, making diagnoses, prescribing medication, carrying out procedures, referring on to specialists, and talking to patients."}}

--- variant 2: the wider role against a corpus sub-role (expected 2: new) ---
{"target": {"label": "worker", "description": "A worker is someone who earns a wage by the hour or the week, clocking in and out, taking orders from a supervisor, and counting on the pay packet at the end of it."},
 "other": {"label": "union member", "description": "A union member is someone who carries a union card: paying dues, working under the contract the union bargained, taking grievances to the steward, walking a picket line when the vote says strike, and never crossing one."}}

--- variant 3: R1, candidate against candidate (both descriptions role glosses) ---
{"target": {"label": "cop", "description": "A cop is someone who patrols a beat in uniform, answers calls, makes arrests, writes reports and testifies in court, backed by a badge and a department."},
 "other": {"label": "police officer", "description": "A police officer is someone who patrols in uniform, responds to calls, arrests suspects and gives evidence in court on behalf of a police force."}}
```

#### 7a.5 [profession_lay.md](./rubrics/profession_lay.md): B's lay-role call

Haiku 5.5, one call per SOC broad group (its detailed O*NET occupations with descriptions) and one per selected
job title, three readings (a generating call: the union of roles with support, `distinct_persona` by majority,
the gloss from the first reading that names the role), `max_tokens` 3000, the system prompt cached.

````text
You are given one JSON object: a group of occupations from an official classification. "group" gives the group's code and title; "occupations" lists its occupations, each with an "id" (the occupations are numbered 1, 2, 3 ... in the order listed), a title and a description. Say what the people in this group call themselves: the plain word or short phrase a person says when asked what they are ("I'm a nurse", "I'm a cardiologist", "I'm an executive"), not the classification's title and not a job advertisement's. "Chief Sustainability Officers" are executives; "Nursing Assistants" are nurse's aides.

Give one to three lay roles for the group, each one to three words, lower case, singular, US spelling, no "the". Give one when the occupations are one role under several titles, more when the group holds roles that are different personas: people who would describe their days, their tools, their customers or their worries differently. A specialty whose holder talks about its own subject all day is a persona of its own (a cardiologist talks about hearts); a title that only names a level, a sector or a reporting line is not (a chief sustainability officer is an executive).

When "group" carries an "alternate_title", the call is about that title alone. It is a lay title from the classification's own list for the occupation shown. Say whether it names a persona of its own (a bouncer, beside a security guard) or is only another name for the occupation's role (a security officer is a security guard). Give it, in its lay form, as the one role when it names a persona of its own; when it does not, give no roles ("roles": []).

For each lay role, say which of the listed occupations it covers (their ids), whether it is a persona distinct from the group's most general role ("distinct_persona"), and write a one-sentence description in the form "A <role> is someone who ..." (write "An" before a vowel sound): what the persona does, where, with what and with whom, in the words the persona would use of itself, not the classification's, about 20 to 35 words, no hedging, US spelling.

Give a reason in one short sentence first, then the roles.

Respond with one JSON object and nothing else, reason first:
{"reason": "<one short sentence>", "roles": [{"role": "<one to three words>", "covers": [<ids of the listed occupations>], "distinct_persona": true|false, "gloss": "<one sentence>"}]}
````

The text above is the pinned version 1 ([profession_lay.md](./rubrics/profession_lay.md), 2026-10-22), with four changes from this plan's draft made while writing the code against the real O*NET data: the occupations' ids are named in the first paragraph; the alternate-title paragraph says the call is about that title alone and asks for `"roles": []` when the title is only another name (the draft's "one to three roles" contradicted "only when it does"); "in its own words" became "in the words the persona would use of itself, not the classification's"; and "write "An" before a vowel sound" was added, as in [role_gloss.md](./rubrics/role_gloss.md).

Rendered user turns (`lay.build_user`; O*NET 31.0 text, verbatim from [occupation_data.csv](../../data/external/onet/occupation_data.csv); the group's employment is not shown, so the model's answer is independent of the ranking).  The broad group's title "Physicians" and the job-title row "Bouncer" were supplied by hand, since the OEWS file and [job_titles.csv](../../data/external/onet/job_titles.csv) (not there yet) are not downloaded.  Physicians holds **19 O*NET occupations**, not 8: SOC 2018's Physicians run from 29-1211 to 29-1229 (`soc.BROAD_SPILLOVER`), and the six `29-1229.0x` specialties are O*NET's own. *Replaced 2026-10-22 (Opus, the build) by the code's own rendering, as the rubric file has it; the drafter's expected answers are left out, the model's own come with the pilot.*

```
--- variant 1: a SOC broad group (29-1210 Physicians; 19 O*NET occupations) ---
{"group": {"code": "29-1210", "title": "Physicians"},
 "occupations": [
  {"id": 1, "title": "Anesthesiologists", "description": "Administer anesthetics and analgesics for pain management prior to, during, or after surgery."},
  {"id": 2, "title": "Cardiologists", "description": "Diagnose, treat, manage, and prevent diseases or conditions of the cardiovascular system. May further subspecialize in interventional procedures (e.g., balloon angioplasty and stent placement), echocardiography, or electrophysiology."},
  {"id": 3, "title": "Dermatologists", "description": "Diagnose and treat diseases relating to the skin, hair, and nails. May perform both medical and dermatological surgery functions."},
  {"id": 4, "title": "Emergency Medicine Physicians", "description": "Make immediate medical decisions and act to prevent death or further disability. Provide immediate recognition, evaluation, care, stabilization, and disposition of patients. May direct emergency medical staff in an emergency department."},
  {"id": 5, "title": "Family Medicine Physicians", "description": "Diagnose, treat, and provide preventive care to individuals and families across the lifespan. May refer patients to specialists when needed for further diagnosis or treatment."},
  {"id": 6, "title": "General Internal Medicine Physicians", "description": "Diagnose and provide nonsurgical treatment for a wide range of diseases and injuries of internal organ systems. Provide care mainly for adults and adolescents, and are based primarily in an outpatient care setting."},
  {"id": 7, "title": "Neurologists", "description": "Diagnose, manage, and treat disorders and diseases of the brain, spinal cord, and peripheral nerves, with a primarily nonsurgical focus."},
  {"id": 8, "title": "Obstetricians and Gynecologists", "description": "Provide medical care related to pregnancy or childbirth. Diagnose, treat, and help prevent diseases of women, particularly those affecting the reproductive system. May also provide general care to women. May perform both medical and gynecological surgery functions."},
  {"id": 9, "title": "Pediatricians, General", "description": "Diagnose, treat, and help prevent diseases and injuries in children. May refer patients to specialists for further diagnosis or treatment, as needed."},
  {"id": 10, "title": "Physicians, Pathologists", "description": "Diagnose diseases and conduct lab tests using organs, body tissues, and fluids. Includes medical examiners."},
  {"id": 11, "title": "Psychiatrists", "description": "Diagnose, treat, and help prevent mental disorders."},
  {"id": 12, "title": "Radiologists", "description": "Diagnose and treat diseases and injuries using medical imaging techniques, such as x rays, magnetic resonance imaging (MRI), nuclear medicine, and ultrasounds. May perform minimally invasive medical procedures and tests."},
  {"id": 13, "title": "Physicians, All Other", "description": "All physicians not listed separately."},
  {"id": 14, "title": "Allergists and Immunologists", "description": "Diagnose, treat, and help prevent allergic diseases and disease processes affecting the immune system."},
  {"id": 15, "title": "Hospitalists", "description": "Provide inpatient care predominantly in settings such as medical wards, acute care units, intensive care units, rehabilitation centers, or emergency rooms. Manage and coordinate patient care throughout treatment."},
  {"id": 16, "title": "Urologists", "description": "Diagnose, treat, and help prevent benign and malignant medical and surgical disorders of the genitourinary system and the renal glands."},
  {"id": 17, "title": "Physical Medicine and Rehabilitation Physicians", "description": "Diagnose and treat disorders requiring physiotherapy to provide physical, mental, and occupational rehabilitation."},
  {"id": 18, "title": "Preventive Medicine Physicians", "description": "Apply knowledge of general preventive medicine and public health issues to promote health care to groups or individuals, and aid in the prevention or reduction of risk of disease, injury, disability, or death. May practice population-based medicine or diagnose and treat patients in the context of clinical health promotion and disease prevention."},
  {"id": 19, "title": "Sports Medicine Physicians", "description": "Diagnose, treat, and help prevent injuries that occur during sporting events, athletic training, and physical activities."}
 ]}

--- variant 2: a job title under its occupation ---
{"group": {"code": "33-9032.00", "title": "Security Guards", "alternate_title": "Bouncer"},
 "occupations": [
  {"id": 1, "title": "Security Guards", "description": "Guard, patrol, or monitor premises to prevent theft, violence, or infractions of rules. May operate x-ray and metal detector equipment."}
 ]}
```

### 7b. The role index and the retrieval check (decision 11)

**Index.**  `load_role_corpus` gives the 339 roles (label `corpus_display_name(stem, "roles")`, the file's
description, arrangements from the files: the six pairs expand as trait pairs do; the sequence, map, square and
set arrangements do not, since `expands_to` covers simplices only); embedded as `label: description` in `w20`
through the cache; `build_index` with M2's settings ([metric_config.json](../../data/candidates/metric_config.json)
`covered`: `centred`, `cos`, `k` 10), the centring mean being that of the corpus the index holds (the role
corpus; the trait index centres on the trait corpus the same way).  The queue's live role entries with a text join
the search as the trait entries do (`entity_type == "role"`).  Exact-label stage 0 matches the role stems and
role queue entries (57 of the 382 held rows are corpus role stems: covered at stage 0, no call).

**Query form `role_gloss_w14`**: the gloss with its opening `A|An <label> is` removed (a regex on the label's
display form, case-insensitive; a gloss that does not open so is used whole, with a WARNING), then cut to 14
words, mirroring the trait form (a trait gloss carries no label).  `label_gloss` stays the alternative.

**Cross-type**: the same query against the trait index gives `cross_type.traits` (the 5 nearest, cosine only);
in a trait run, against the role index, `cross_type.roles` (task 10; additive; the eleven collisions are its
check).

**The check** (`retrieval-check`, embeddings and the role gloss only, no judge): for each of the 339 roles one
role gloss call with `reading: null` (variant 3 of § 7a.1; the gloss is independent of the description, so this
measures retrieval, not paraphrase; a gloss in another sense of the label counts as a miss and is listed as
such), then the query in each form against the full index (the role stays in: not leave-one-out), recall at 10
of the role's own stem; the report gives recall per form and per kind, the misses with their glosses and the
rank the role got, and the mean reciprocal rank.  **Acceptance: recall at 10 of the production form
(`role_gloss_w14`, centred) at or above 0.95.**  Below it: the arms `role_gloss_w20` (20 words) and `raw` space,
plus `label_gloss` as information, each on the same glosses at no new call; the best arm becomes the role
setting, recorded in the run's `run.json` and in a `roles` section of the metric config (`MetricConfig.roles`,
read by the role pass; absent means M2's settings), with the recall table in the pilot readout.  Cost: 339 Haiku
calls, about $0.05, and 339 × 4 embeddings, under $0.01.

### 7c. The kind readout and the review order (decision 2)

Computed by `roles_pass.balance` from `corpus_kind_counts` (§ 6.4): the reference shares are the frozen
2026-10-16 counts (`default.json` left out: other 3, total 339; a test compares the constant with
[role_kinds.json](../../data/roles/role_kinds.json) while that file still records 340 roles including `default`);
`n_now` and `count` are the corpus as it will be once this review is applied.  On the card (§ 6.3): a chip with the
kind and its status, in the member line beside the generator, and the readout text; `too_high` shown in the
colour the app uses for covered rows, since Roger will generally not accept there.  In the header, beside the
counts, one line per kind: `occupation 171 / 168 held (too high)`.  The readout is recomputed on every
action (it rides on `counts()`), so accepting twelve occupations turns the chip as he goes.

**Order `kinds`**: the kind status of each queue item is fixed at serve time (so the queue does not reshuffle
under `S.qpos`, agent caveat in [decisions.py](../../assistant_axis/gapgen/review_app/decisions.py)) and the
items are sorted by status (too low, about right, too high), then by the kind's `room` descending, then as the
`cliques` order sorts within a kind; a group's kind is its members' commonest.  `serve --order kinds` is the
default for a batch whose graph says `pass: roles`; `--order cliques` is still there.  The header says which
order is in force and when the statuses were fixed; `status` prints the balance before and after.

### 7d. B: sources, licences, downloads, attribution, ranking, metering

**Licence findings (read 2026-10-21).**

| source | what the pages say | verdict for our use |
|---|---|---|
| O*NET 31.0 (on disk) | CC BY 4.0 with required attribution, verified 2026-10-10 at onetcenter.org/license_db.html ([LICENSE.txt](../../data/external/onet/LICENSE.txt), [DOWNLOAD_MANIFEST.json](../../data/external/onet/DOWNLOAD_MANIFEST.json)) | acceptable; attribution load-bearing from the first candidate (`ONET_NOTE`) |
| BLS SOC 2018 and OEWS | "everything that we publish, both in hard copy and electronically, is in the public domain" except copyrighted photographs; BLS asks to be cited (https://www.bls.gov/bls/linksite.htm) | acceptable; cite BLS |
| ESCO | the download page (https://esco.ec.europa.eu/en/use-esco/download) says "free of charge", names no licence, and asks for an e-mail address behind a privacy statement; the ESCO copyright notice (https://esco.ec.europa.eu/en/copyright-notice-esco-skills-competences) and the Commission's legal notice (https://commission.europa.eu/legal-notice_en, Decision 2011/833/EU) say that "unless otherwise indicated" EU-owned content on europa.eu is licensed under CC BY 4.0, reuse "provided appropriate credit is given and changes are indicated"; the ESCO notice carries CC BY-SA 4.0 only for a third party's skills cards; esco.ec.europa.eu/en/legal-notice returns 404; a third-party site (skilldata.info) claims EUPL 1.2, unverified | CC BY 4.0 by the Commission's general policy, nothing to the contrary found, not stated for the files themselves: Decisions for Roger 1 |
| ISCO-08 | the files exist on the ILO's ISCO site (https://isco.ilo.org/en/isco-08: structure and definitions xlsx 304 KB, structure csv 224 KB, under `ilo.org/ilostat-files/ISCO/newdocs-08-2021/`), with no licence or terms on the page beyond "2021 International Labour Organization"; the ILO copyright page (https://www.ilo.org/global/copyright/lang--en/index.htm) licenses publications and datasets **from 3 May 2023** under CC BY 4.0 and says earlier ones "don't automatically" carry one, with permission through rights@ilo.org; the 2012 publication page (https://www.ilo.org/publications/international-standard-classification-occupations-2008-isco-08-structure) states no licence; the ILOSTAT terms page returned 403; the old ILO statement that ISCO "can be used without prior authorization" survives only in third-party copies (HL7) | not confirmed: left out |

**Downloads** (each a fresh ask at build time; the `fetch` command refuses without `--approved-by`; nothing is
over 2 GB, so no delete-when-done note):

| file | URL | size | into |
|---|---|---|---|
| O*NET 31.0 job titles (the table formerly "Alternate Titles": 54,269 rows of lay titles by O*NET-SOC code) | https://www.onetcenter.org/dl_files/database/db_31_0_csv/job_titles.csv | 4,504,432 bytes (HEAD, 2026-10-21) | [data/external/onet/job_titles.csv](../../data/external/onet/job_titles.csv) (not there yet), the manifest extended |
| BLS OEWS May 2025 national estimates (xlsx in a zip; columns OCC_CODE, OCC_TITLE, O_GROUP, TOT_EMP; rows at the major, minor, broad and detailed tiers, so it also supplies the broad titles) | https://www.bls.gov/oes/special-requests/oesm25nat.zip | a few MB (bls.gov answers automated requests with 403, so the size could not be read; the build tries a browser user agent, else Roger downloads it by hand) | `data/external/bls/` |
| BLS 2018 SOC structure (optional: the broad titles, if OEWS's are not wanted) | https://www.bls.gov/soc/2018/soc_structure_2018.xlsx | small | `data/external/bls/` |
| ESCO occupations (wave 2, after Decisions for Roger 1; the CSV bundle needs an e-mail address, or the API at ec.europa.eu/esco/api) | https://esco.ec.europa.eu/en/use-esco/download | tens of MB for the bundle; the occupations file alone a few MB | `data/external/esco/` |

`openpyxl` for the workbooks (Decisions for Roger 6).

**Attribution** travels with every artefact that holds a title: `ATTRIBUTION.md` in the run directory (the
O*NET paragraph of `sources.py`, the BLS citation, ESCO's when used), the same text in `run.json`, a `source` on
each queue entry (§ 6.5), and the readout.

**Levels and the cut.**  The 1,016 O*NET occupations fold onto 2018 SOC detailed codes (the code without its
suffix) and those onto 459 broad groups (`broad_code`); one lay call per broad group with its detailed
occupations and descriptions.  Job titles: 1-2 words, no parentheses or abbreviations, singular after
normalization, Zipf at or above 3.0 ([freq.py](../../assistant_axis/gapgen/freq.py)), not a corpus role stem,
deduplicated across occupations, the top 300 by Zipf; one lay call each under its occupation.  About 760 calls,
three readings each.

**Ranking** (`rank.py`): per lay role, `zipf` of the title (`wordfreq`, phrases scored as it scores them),
`log10` of the broad group's OEWS employment (a job title takes its occupation's detailed employment), and
distance `1 − cosine` to the nearest corpus role by the role index (query `role_gloss_w14` of the lay gloss);
each z-scored over the run, summed with weights 1, 1, 1 (`--weights`), highest first; a role whose nearest
corpus role is at cosine 0.75 or above is still ranked (M3's hierarchy line decides covered) but flagged
`near_corpus`.  Recovery by string of the 162 corpus occupations (their stems and `renamed_from`) among the lay
roles is printed before submission: the plan's figure is above 80% at the broad level, and the misses say which
level the corpus sits at.

**Metering** (`submit`): the wave's submission budget is `wave_rows / kept_share` (300 reviewed rows, about two
hours at the measured 146 terms an hour, [acceptance_13](./acceptance_13_generator_testing.md); `kept_share`
the pilot's measured role kept share, § 10), and B takes `share` (0.5) of it from the top of the ranking, net-new
rows only (not a corpus role, not a queue entry, not a key the registry has decided; a lay role that is already a
held row is resubmitted so that its SOC provenance merges, and counts toward neither the meter nor the
estimate).  `--all` submits the whole ranking (refused without `--confirm-expensive` when its downstream
estimate passes $20).  The run's readout shows the occupation share before and after at the held share
(`balance` over the corpus plus the submitted rows by `kind_guess`).

**As built (2026-10-22).**  SOC 2018's Physicians broad group 29-1210 takes the detailed codes 29-1211 to 29-1229
(there is no broad group 29-1220; `soc.BROAD_SPILLOVER`), so O*NET 31.0's detailed codes fold onto the 459 broad
groups (460 without it) and Physicians holds 19 O*NET occupations.  The job-title cut has one more step than above:
a title that is its occupation's own title made singular (Security Guard under Security Guards) is dropped
(`occupation_title`).  A lay role already registered, held or decided, is resubmitted so that its SOC provenance
merges, and counts toward neither the meter nor the estimate.  The downstream estimate that `submit` prints
assumes 85% of the wave passes M1 (`submit.M1_PASS_RATE`, to be replaced by the pilot's figure).  `ATTRIBUTION.md`
carries, after O*NET's paragraph, a statement of the changes (lay roles and glosses derived by a language model,
occupations grouped by SOC broad code, not approved by USDOL/ETA: `sources.ONET_CHANGES`), as CC BY 4.0 asks.

## 8. Acceptance tests, written first

Test files under [assistant_axis/tests/](../../assistant_axis/tests/) (all sixteen and the two fakes written 2026-10-22), fakes beside them in
[professions_fakes.py](../../assistant_axis/tests/professions_fakes.py) and [roles_fakes.py](../../assistant_axis/tests/roles_fakes.py) (a fake Anthropic client answering from canned JSON, a `HashEmbedder`
index over a ten-role fixture corpus, a scratch registry under `tmp_path`); no network, no key.

1. [test_gapgen_normalize_role_keys.py](../../assistant_axis/tests/test_gapgen_normalize_role_keys.py): `make_key("optimist", 1, "role") == "optimist|R#1"`, `split_key` round
   trips both forms, a `|R` key never passes the trait stem regex unchanged; `check_id` is not involved.
2. [test_gapgen_registry_role_mode.py](../../assistant_axis/tests/test_gapgen_registry_role_mode.py): a role-aimed candidate of a surface with a trait row makes a second row;
   one with a held role row merges into it with `kind_guess` and `human` on the source; `read_candidates` reads
   old lines as trait; a relabel sibling of a role-aimed noun is a trait row; `candidates.jsonl` lines carry the
   three new fields; resubmission is idempotent.
3. [test_gapgen_filter_role_routes.py](../../assistant_axis/tests/test_gapgen_filter_role_routes.py): `route_for` for each of the eight kinds; `verdict_tags_holding` with
   entity type role for each route; a trait-aimed row is unchanged byte for byte (the 382 held rows' blocks
   replayed from a fixture); M1's write-back keeps `entity_type: "role"`; the gloss wave is skipped for routes
   `role` and `both`; changing `ROLE_ROUTES["trait"]` to `"role"` changes only the relabel-independent branch.
4. [test_gapgen_roles_pass.py](../../assistant_axis/tests/test_gapgen_roles_pass.py): `is_role_row` on the three shapes (held plain key, role-aimed `|R`, trait row);
   `candidate_from_row` reasons; `RoleCandidate.cut_off == 3` under rule sets 1-3 with `alignment_score` None;
   `request` for both steps, byte-pinned digests for the rendered user turns of § 7a.1-7a.2; `stage_rows` on the
   fake client writes a block per row with three kind readings combined by majority (a tie keeps the first,
   `kind_split`), a failed gloss recorded with `errors`, a budget stop keeping what was paid for; `pins` raises on
   a changed text; `estimate` counts four calls a row.
5. [test_gapgen_role_kind_rubric.py](../../assistant_axis/tests/test_gapgen_role_kind_rubric.py): the fenced block of [role_kind.md](./rubrics/role_kind.md) hashes to the side-car's recorded
   `prompt_sha256` (`11b559f0cff50189`); `classify_role_kinds.SYSTEM` equals it; `--from-pass` appends a stem that
   has a file and skips one that does not; `seed_entities.py write` of a role entry with `gap_gen.role_kind`
   appends the same record (in [data_analysis/tests/test_seed_entities.py](../../data_analysis/tests/test_seed_entities.py)).
6. [test_gapgen_roles_index.py](../../assistant_axis/tests/test_gapgen_roles_index.py): `load_role_corpus` leaves `default.json` out and shows `devil's advocate`;
   the six pairs expand, a map does not; `query_text(form="role_gloss_w14")` strips `A bouncer is` and `An
   operator is` and warns on a gloss that opens otherwise; `cross_type.traits` on a role block and
   `cross_type.roles` on a trait block, never a verdict change (a trait fixture run before and after is equal but
   for the field); a role row in a trait run is `not_a_trait_row`.
7. [test_gapgen_roles_m3.py](../../assistant_axis/tests/test_gapgen_roles_m3.py) (end to end on fakes): `score --holding roles` over a fixture registry of 12 rows
   (two corpus-stem rows covered at stage 0, one sub-role covered by its parent at 3 with `covered_by`, one wider
   role new at 2, one opposed pair completion, one state-tagged row, one `|R` row): blocks carry `pass: "roles"`,
   `cut_off` 3, the role rubrics' pins; `summary.json`, `decisions.md`, `usage.json` written; a resume across
   passes refused; the relation user turn's digest pinned against § 7a.3's rendering.
8. [test_gapgen_roles_retrieval_check.py](../../assistant_axis/tests/test_gapgen_roles_retrieval_check.py): on the hash index, recall per form and per kind, the misses listed
   with rank and gloss, the acceptance line, the arms run only below 0.95, the chosen arm written to the config's
   `roles` section and read back by the pass.
9. [test_gapgen_roles_review.py](../../assistant_axis/tests/test_gapgen_roles_review.py): R1 on the fixture builds `role:` corpus nodes with `outcome: "role"` and the
   card fields of § 6.3; `balance` on hand-made counts (every kind about right at the reference; occupation too
   high after 17 accepts at 339; pastime too low at n_now 400 with 8) and its `order`; `queue(order="kinds")`
   stable across actions; the chip and readout text; `/files/roles/{stem}.json`; `apply` promotes with
   `allow_roles`.
10. [test_gapgen_promote_roles.py](../../assistant_axis/tests/test_gapgen_promote_roles.py): `promote` refuses a role row without `allow_roles` (and the bulk path
    always); the queue entry of § 6.5 (tags, section, `description_draft` the gloss, `source`, `gap_gen.role_kind`);
    a role stem that is a role file or live role entry refused; one that is a trait file allowed with the NOTE
    naming `COLLISION_NAMES`; a `partner_hint` makes `pairing: "pair"`; `gap_registry.py promote --status
    accepted` leaves role rows out and says so.
11. [test_gapgen_professions_sources.py](../../assistant_axis/tests/test_gapgen_professions_sources.py): every `Source` has a licence, a URL and attribution text; `fetch` on a
    fake HTTP (200 for O*NET, 403 for BLS) writes manifest rows and says "download by hand" for BLS; refused
    without `--approved-by`; `ATTRIBUTION.md` holds the O*NET paragraph verbatim.
12. [test_gapgen_professions_soc.py](../../assistant_axis/tests/test_gapgen_professions_soc.py): `broad_code` on O*NET and SOC codes; `read_oews_national` on a fixture
    workbook (openpyxl); `broad_groups` yields a group per broad code with its detailed occupations and
    employment, 459 on the real files when present (skipped otherwise); `lay_title_candidates` applies the cut
    (words, parentheses, Zipf floor, corpus stems, dedupe, top-n).
13. [test_gapgen_professions_lay.py](../../assistant_axis/tests/test_gapgen_professions_lay.py): `build_user` for both variants byte-pinned against § 7a.5; `parse_lay` on
    good, prose-prefixed and broken answers; `combine_readings` keeps the union with support and takes
    `distinct_persona` by majority, never drops a one-reading role; a refusal is a failed call, counted.
14. [test_gapgen_professions_rank.py](../../assistant_axis/tests/test_gapgen_professions_rank.py): z-scoring, weights, ties, `near_corpus`, the recovery by string over a
    fixture corpus with a `renamed_from`.
15. [test_gapgen_professions_submit.py](../../assistant_axis/tests/test_gapgen_professions_submit.py): `net_new` against corpus, queue and decided keys; `select_wave`'s
    arithmetic (0.5 × 300 / 0.4 = 375); `to_candidates` fields (`entity_type`, `kind_guess`, `human`,
    `source_ref` forms, `gloss_hint`); `--all` over $20 refused; the printed follow-up commands.
16. [test_gapgen_professions_acceptance.py](../../assistant_axis/tests/test_gapgen_professions_acceptance.py): fetch (fixture files) → build → lay (fake) → rank → label-fit
    (fake) → submit into a scratch registry → `score --holding roles --run professions/R` (fake) → R1 → the
    card: one occupation covered by its parent, one new, the readout says occupation too high after the
    submission at the held share; `usage.json` at every stage; the cost guard refuses an estimate over the cap.
17. Existing suites green: `uv run pytest assistant_axis/tests/test_gapgen_*.py data_analysis/tests -q`;
    `uv run python data_analysis/check_arrangements.py` ([check_arrangements.py](../../data_analysis/check_arrangements.py)); `uv run python tools/sync_entity_lists.py --check`;
    `uv run python data_analysis/gap_generation/rubric_pins.py check`; `uv run python tools/lint_kind_collision.py` ([lint_kind_collision.py](../../tools/lint_kind_collision.py)).

**The paid checks before the pilot** (not tests; recorded runs): the retrieval check (§ 7b, about $0.10) and
the rubric check (§ 10 of the idea plan): Roger marks 40 role pairs (the six recorded pairs, ten parent /
sub-role pairs such as doctor / cardiologist, ten same-role pairs such as cop / police officer, the rest
unrelated; the sheet [role_rubric_pairs.md](./role_rubric_pairs.md), written 2026-10-22 and waiting for the marks: mark column second, the
glosses labelled as the role gloss call's) in about twenty minutes; `rubric-check` runs both role rubrics on
Sonnet 5.5 in both orders and prints weighted kappa against his marks and the straight-minus-swapped gap
(about $0.50); below kappa 0.6 the rubric is redrafted before the pilot's first overlap call.

## 9. Ordered task checklist

Each task is one sitting with the test that proves it; tasks 1-13 are the shared path, 14-20 generator B.
Opus works in a worktree; platform tasks get a Fable diff review before the pilot (plan § 11 step 1).

1. Keys and the `Candidate`: `normalize.make_key` / `split_key`, `Candidate` fields, `CANDIDATE_FIELDS`,
   `new_record`, `submit_candidates`'s merge rule, `source_entry`, `gap_registry.py submit --entity-type` (tests 1-2).
2. M1 routing: `roles_pass.ROLE_ROUTES` / `route_for`, `items_from_records` meta, `holding_for`,
   `verdict_tags_holding`, the join and waves in `split_runner`, the write-back (test 3).
3. The two rubric files [role_gloss.md](./rubrics/role_gloss.md) and [role_kind.md](./rubrics/role_kind.md) (the latter moved byte for byte, [classify_role_kinds.py](../../data_analysis/classify_role_kinds.py)
   reading it), `ROLE_FILES` in `split_rubrics`, pins at version 1 (test 5; `rubric_pins.py check` green).
4. `roles_pass.py`: the stage (`request`, `stage_rows`, blocks, `render`, `estimate`, `pins`), `RoleCandidate`,
   `candidate_from_row`; `novelty_runner.candidate_from_row`'s roles branch (test 4).
5. The role index and query form: `load_role_corpus`, `role_gloss_w14`, queue role entries in the search, the
   `cross_type` fields both ways (test 6).
6. [relation_roles.md](./rubrics/relation_roles.md) and [overlap_concept_roles.md](./rubrics/overlap_concept_roles.md), pinned at version 1, rendered with `render --stand-in
   cardiologist --pass roles` and `render --key <a held row>` and the renderings put in the files (test 7's
   digests).
7. `novelty_score.py score --holding roles`: `PASS_LISTS`, the stage call, the role index and rubrics, `pass`
   on blocks and `run.json`, `summary.json`'s stage figures, `decisions.md` with the kind column (test 7).
8. `retrieval-check` (test 8); run it live (about $0.10, no confirmation needed) and record [recall.md](../../data/candidates/novelty/roles_retrieval_1/recall.md) (not there yet).
9. R1 for roles: `corpus_key`, `corpus_targets`, `target_path`, `_holding_of`, node fields, role rubrics in a roles
   build (test 9, graph part).
10. R2 for roles: `member_card` fields, `balance` and `corpus_kind_counts`, `queue(order="kinds")`, `counts`,
    [server.py](../../assistant_axis/gapgen/review_app/server.py) route and `Literal`, [app.js](../../assistant_axis/gapgen/review_app/static/app.js) chip, readout and balance line, `apply` with `allow_roles` (test 9).
11. Promotion: `promote(..., allow_roles)`, the roles branch, per-type collision checks, `queue_entry_extras`,
    `gap_registry.py promote --allow-roles`, `holding --list roles` with gloss and kind (test 10).
12. The rubric check: the 40-pair sheet for Roger, `rubric-check` (kappa, swap-averaging), run after his marks
    (about $0.50).
13. The kinds side-car: [classify_role_kinds.py](../../data_analysis/classify_role_kinds.py) `--from-pass`, [seed_entities.py](../../data_analysis/seed_entities.py) `write` appending (test 5);
    [README.md](./rubrics/README.md) of the rubrics directory and [coding_plan_review.md](./coding_plan_review.md) get a "Role pass"
    section pointer; the pilot (§ 10).
14. [professions/sources.py](../../assistant_axis/gapgen/generators/professions/sources.py) and `fetch` with the manifest and `ATTRIBUTION.md`; ask Roger for the downloads
    (and `openpyxl`) with the sizes of § 7d (test 11).
15. [soc.py](../../assistant_axis/gapgen/generators/professions/soc.py) and [onet.py](../../assistant_axis/gapgen/generators/professions/onet.py): the table, the job-title cut, `build` and its recovery by string (test 12).
16. [profession_lay.md](./rubrics/profession_lay.md) pinned at version 1, [lay.py](../../assistant_axis/gapgen/generators/professions/lay.py) with three readings and the union, `lay --dry-run`
    rendering both variants into the rubric file (test 13).
17. [rank.py](../../assistant_axis/gapgen/generators/professions/rank.py), `rank` (test 14); `label-fit` wiring ([label_fit.py](../../assistant_axis/gapgen/label_fit.py)).
18. [submit.py](../../assistant_axis/gapgen/generators/professions/submit.py), `submit`, `report` (tests 15-16).
19. `lay` and `rank` live on the full table (about $1), the recovery by string and the top 40 to Roger with the
    readout; then `submit` at the pilot's kept share, M1, M3 (`--holding roles --run professions/R`), R1, R2.
20. The § 11 report, and the frozen interface below copied into [coding_plan_platform.md](./coding_plan_platform.md)'s
    "Interface as built" by the main session.

## 10. Pilot: the held role rows

**Material.**  The `roles` holding list holds **382 rows today** (355 on 2026-10-16; `gap_registry.py holding
--list roles`, 2026-10-21): all `entity_type: "role"`, none glossed, none reviewed; 367 tagged `role_person`
by M1 and 15 tagged `state` and routed here by the states pass (captive, fugitive, housebound, ...); by first
source censuses 192, masked LM 132, corpus frames 21, Roget 11, base model 9, structural 6, others 11; 57 are
corpus role stems (covered at stage 0 for no call; six of them also queue role entries marked done), 3 are
trait stems ([qualitative](../../data/traits/instructions/qualitative.json), [specialist](../../data/traits/instructions/specialist.json),
[young](../../data/traits/instructions/young.json)) and one a turned-down role entry (servant); 7 are phrases (man of letters, quality assurance, ...); 32 carry a relabel
block (antagonist → antagonistic, soldier → soldierly).  Noise is expected (accredited, arraigning, beneath,
blasting): M3 does not remove it, and the review does; the readout counts how much of the review time it cost.

**Run** (each with `--dry-run` first):

1. `novelty_score.py retrieval-check --batch-id roles_retrieval_1 --budget-usd 1` (task 8): recall at 10 against
   0.95; the arms if below.
2. Roger's 40-pair marks, `rubric-check` (task 12): kappa at or above 0.6 for both role rubrics.
3. `novelty_score.py score --holding roles --batch-id roles_pilot_1 --unscored --transport batches --budget-usd 8`
   (batched: Roger's decision 4, 2026-10-22):
   the stage (382 gloss calls, 1,146 kind readings, about $0.20), then M3 on the 325 rows not covered at stage 0
   (about $0.011 a row live: about $3.6; batched about $2).
4. `review_graph.py build --batch-id review_roles_pilot_1 --from-batches roles_pilot_1 --budget-usd 4`
   (about $1-2 on the kept rows).
5. `review_app.py serve --batch-id review_roles_pilot_1 --order kinds`; Roger reviews; `apply`.
6. `seed_entities.py write` and `generate` for the promoted entries (about $0.02 a role on Sonnet 4.6, outside
   this plan's spend); `classify_role_kinds.py` reads the side-car.

**Readout** ([data/candidates/novelty/roles_pilot_1/readout.md](../../data/candidates/novelty/roles_pilot_1/readout.md),
not there yet): the retrieval check's recall table; the rubric check's kappa; the stage's figures (glosses in the
form, kind agreement: unanimous share, splits); M3's decisions (covered at stage 0, covered by a parent at 3,
covered at 4, new, grey) with the sub-role covers listed by parent; the nine-way split of the 382 by the kind
call, of the kept rows and of the corpus after Roger's accepts; **the role kept share** (kept rows per row not
covered at stage 0; the figure that sizes B's first wave and every later wave) and the promote share; Roger's
review-minutes and terms an hour ([review_minutes.py](../../assistant_axis/gapgen/testing/review_minutes.py)),
nouns against the 146 of traits; the cost from `usage.json` against this estimate; the noise share (rows Roger
rejected as not roles) and whether M1's established check should tighten for role-aimed rows.

**Roger's decision on it**: whether the kept share and the review rate justify B's first wave at `--wave-rows
300 --share 0.5` (about one hour of his time at a kept share near 0.5), whether the sub-role rule (decision 4)
held up (any parent cover he undid), and whether the routing table of decision 3 stays `both` for the twins.

**Cost and time**: about $5-6 live in all ($0.10 check, $0.50 rubric check, $0.20 stage, $3.6 M3, $1-2 R1),
about $4 batched; Roger about two hours of review plus twenty minutes of marks.

## 11. Report at the end

One page, [acceptance_16_role_path_and_professions.md](./acceptance_16_role_path_and_professions.md) (not there
yet): built (modules, rubrics pinned with versions), deviations from this plan and why, test results (the commands
of § 8 test 17 and the pass counts), the retrieval and rubric checks' figures, the pilot readout's numbers (kept
share, promote share, terms an hour, the balance before and after), B's recovery by string, the lay call's
agreement across readings, the occupation share before and after B's wave, cost per stage from every
`usage.json` against § Cost, the downloads with their manifest rows and attribution, and the open items handed on
(ESCO's wave, ISCO-08, the twins TODO).

## 12. Escalation

Opus retries once, then Fable (diff review, architecture calls, a stubborn test), then Roger through
[QUESTIONS.md](./QUESTIONS.md) (numbered entry, the assumption proceeded under, the status column), proceeding
under the stated assumption unless the answer would make the work useless.  Likely questions: a BLS 403 that a
user agent does not clear (assumption: Roger downloads the two files by hand); a kind-call agreement below 70%
on the pilot (assumption: proceed, report; the kind is information, not a gate); the retrieval check below 0.95
on every arm (assumption: take the best arm, report, and flag for the post-extraction recalibration).

## Cost (estimates; re-measured at the pilot)

| piece | calls | live | batched |
|---|---|---|---|
| retrieval check | 339 Haiku gloss, 1,356 embeddings | $0.10 | — |
| rubric check | 40 pairs × 2 rubrics × 2 orders, Sonnet 5.5; a few Opus | $0.50 | — |
| pilot stage | 382 gloss + 1,146 kind readings, Haiku 5.5 | $0.20 | $0.10 |
| pilot M3 | about 325 rows at $0.011 | $3.60 | $2.00 |
| pilot R1 | relation and overlap among about 200 kept rows | $1.50 | $0.80 |
| B lay call | about 760 groups and titles × 3 readings, Haiku 5.5 | $0.90 | $0.45 |
| B rank, label-fit | embeddings; label-fit on about 400 labels, Haiku | $0.40 | $0.20 |
| B wave 1 downstream | M1 on 300-400 net-new at $0.0072; M3 on about 85% at $0.011; R1 | $6.50 | $3.30 |
| **total** | | **about $14** | about $8 |

Every run is under $20, so each runs live unless Roger says otherwise; he said so for the pilot, which runs batched (Decisions for Roger 4); the cumulative
spend is tracked in the acceptance report.  Promoted roles' instruction files (about $0.02 each, Sonnet 4.6) and
their extraction are outside this plan.  Roger's time: about 3.5 hours (the pilot 2 h, the marks 20 min, B's
wave about 1 h).

## Frozen interface (for A, C, D (a) and D (b))

- `Candidate(surface, generator, run_id, rank, score, gloss_hint, sense_id, source_ref, partner_hint,
  entity_type="role", kind_guess, human)`; `submit_candidates(..., run=ctx)` as today; a role-aimed candidate
  is keyed `stem|R#sense` unless a role row already holds `stem#sense`.
- The generator's `source_ref` and `kind_guess` are shown on the card as provenance and the guess; the kind the
  pipeline acts on is the role kind call's (`role_pass.kind`); `human` is derived from it (`kind != non_human`).
- After submission the generator runs, in order: `traithood_filter.py --run G/R`, `novelty_score.py score
  --holding roles --run G/R --batch-id roles_<G>_<R>`, `review_graph.py build --from-batches roles_<G>_<R>`,
  `review_app.py serve`; promotion is the app's apply or `gap_registry.py promote --keys --allow-roles`.
- Wave sizing: `wave_rows / kept_share` submissions per wave, each generator's share by the plan's § 4; B's share
  0.5; the kept share is the pilot's measured figure until a generator measures its own.
- `roles_pass.balance(current, n_now)` is the balance readout every generator's `report` prints (before,
  submitted by `kind_guess`, kept by the kind call, after); a kind whose share moves more than five points is
  flagged, never cut.
- Rubric names `role_gloss`, `role_kind`, `relation_roles`, `overlap_concept_roles` in `split_rubrics.ROLE_FILES`;
  a generator's own call goes into `GENERATOR_FILES` as `profession_lay` does.
- `MetricConfig.roles` (absent = M2's trait settings; present after a recalibration) is what the role index reads.
