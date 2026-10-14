# Coding plan: noun normalization (the shared relabel helper, the platform step, the backlog, the roles)

Written 2026-10-13 (Fable) for Roger's review, then for one Opus agent in a worktree.  Format:
[PLAN_FORMAT.md](./PLAN_FORMAT.md).  Decided by Roger on 2026-10-13 ("SG, make this happen"; his words are in
§ 1), recorded in plan 03's pilot gate ([coding_plan_03_base_model.md](./coding_plan_03_base_model.md) § 10, item c)
and plan 05's decision 3 ([coding_plan_05_corpus_frames.md](./coding_plan_05_corpus_frames.md)).  Every figure
below was measured read-only on 2026-10-13 over the live registry
([registry.jsonl](../../data/candidates/registry.jsonl), 9,949 keys), the corpus (932 trait files, 340 role
files), the [seed queue](../../data/seed_queue.json) and the repository's OEWN copy; the measurement section at the
end gives the lists.

**Terms.**  A *noun of disposition* names a kind of person by a standing trait (pedant, coward, snob); the corpus
prefers the adjective (pedantic, cowardly, snobby) because a persona is prompted "You are <label>".  A *quality
noun* names the trait itself (honesty, empathy, vanity).  A *role noun* names an occupation or office (priest,
doctor) and belongs on the roles list, never relabelled.  The *derivation link* is Open English WordNet's
(OEWN's) sense-to-sense relation between derivationally related words (pedant.n to pedantic.a); a *lexicographer
file* is the coarse OEWN category of a sense (`noun.person`, `noun.attribute`, `noun.animal`, ...), which the `wn`
package reads as `Synset.lexfile()`.  M1 is the trait-hood filter and M3 the novelty check
([coding_plan_platform.md](./coding_plan_platform.md), "Interface as built"); the *registry* is the candidate log
keyed by stem and sense; a *holding list* (`roles`, `states`, `physical`, `nationalities`) is where M1 parks a row
that is not a trait ([decisions_m1.md](./decisions_m1.md)).  Zipf frequency:
[glossary.md](./glossary.md#zipf-frequency).  Words in plain text below (pedant, coward) are registry labels or
OEWN lemmas, not corpus files; corpus traits and roles are linked.

## Open decisions (Roger's, at plan review; labelled OPEN until decided; all four decided 2026-10-14)

1. **Decided (2026-10-14, Roger): (a), in the platform.**  Where the helper runs.  Roger: "once it's created every generator that might find it useful should
   incorporate it, or else we should build it into the pipeline."  *Measured*: every one of the nine submission
   sites in the repository goes through one function, `submit_candidates` in
   [registry.py](../../assistant_axis/gapgen/registry.py) (the submit modules of the
   [base model](../../assistant_axis/gapgen/generators/base_model/submit.py),
   [masked LM](../../assistant_axis/gapgen/generators/masked_lm/submit.py),
   [IPIP](../../assistant_axis/gapgen/generators/ipip/submit.py),
   [censuses](../../assistant_axis/gapgen/generators/censuses/submit.py) and
   [alignment sweep](../../assistant_axis/gapgen/generators/alignment_sweep/submit.py), the
   [Roget CLI](../../data_analysis/gap_generation/roget_generate.py), the states pass's renamed route and both forms
   of [gap_registry.py](../../data_analysis/gap_generation/gap_registry.py) `submit`); the helper touches about 1 in 170
   submitted rows (53 of 8,849 single-word rows in the backlog; 57 of 3,825 eligible words in the base-model pilot).
   - (a) **In the platform**: `submit_candidates` runs the helper on every single-word surface and adds the
     adjective as a second, linked candidate of the same generator and run.  One change covers every present
     generator, the three being built or planned (09, 05, 06, 12) and every resubmission (`gap_registry.py submit
     --from` reproduces the derived rows).  The registry gains one additive block, `relabel`, on linked rows.
   - (b) **In each generator**: a call before `submit_candidates`; eleven call sites to touch (eight built, three
     planned), each with a test; the platform unchanged.
   - **Recommendation: (a).**  The generators keep whatever local fold their plans already specify (the base model's
     `-ness`/`-ity` fold before submission stays; plan 05's table records the helper's answer per filler for its
     readout), but the registry-facing step is one.  Two call sites opt out by flag: the M1 validation set and
     the recovery harness submit labels to be judged as given.
   **Roger (2026-10-14):** "a) seems much more elegant, *unless* for some reason some generators need this
   functionality at points before `submit_candidates`.  We'll also need to retrospectively handle candidates that
   were already submitted before this code change, obviously."  None does: the helper is a library function any
   generator can call (plan 05's table records its answer per filler); only the registry-facing step is shared.
   The retrospective handling is decision 4 (the backlog pass).
2. **Decided (2026-10-14, Roger): (c), revised from (b) the same day.**  The rule set's reach.  The deterministic helper is (i) the existing suffix rules of
   [parse.py](../../assistant_axis/gapgen/generators/base_model/parse.py) `normalize_form` (quality nouns in
   -ness, -ity, -ence, -ism, ...), (ii) the OEWN derivation link **from a person or quality sense only**
   (lexicographer files `noun.person`, `noun.attribute`, `noun.feeling`, `noun.cognition`: without that gate 35 of
   76 backlog links came from thing senses, rat to ratty, bog to boggy, face to facial), and (iii) a short list of
   person-noun suffix rules OEWN's link misses (narcissist to narcissistic, hypocrite to hypocritical, introvert to
   introverted, bigot to bigoted, fool to foolish), each gated on OEWN having the adjective, on Zipf 1.5 (the
   platform's floor) and on the adjective not being a pure "of or relating to" pertainym (doctor to doctoral).
   *Measured* on the backlog: (i)+(ii) give 38 relabels, about 90% right by my reading; (iii) adds 15 (the -istic,
   -itical, -verted, -oted, +ish and +ful endings), about 85% right; the +y and +ly endings would add 16 more at
   about 40% right (fish to fishy, cur to curly, slipper to slippery) and are **left out**.
   - (a) (i)+(ii) only.  (b) **(i)+(ii)+(iii) as listed in § 5** (53 relabels on the backlog, 13 of them new
     rows).  (c) (b) plus +y and +ly (69, 23 new, a third of the extra ones wrong).
   - **Recommendation: (b).**  A wrong relabel costs one M1 call ($0.007) and, when M1 passes it, one review card
     that says "from <noun>"; the rules of (iii) are the ones whose measured list is clean.
   **Roger (2026-10-14):** "b).  Are we somehow checking that the result makes sense applied to a person, and is a
   trait, at later stages in the pipeline than where this is being done?  If so, a lot of the bad ones from -y and
   -ly would get filtered, but the ones kept might be rather random and not necessarily semantically close."
   Answer: M1 judges every derived adjective as a candidate (trait-hood, person sense, physical and state tags), so
   most bad ones are filtered; nothing checks that the adjective means what the noun meant, so an M1-passed
   adjective from +y/+ly (fishy, slippery) stands as a trait in its own sense with a misleading link.  Hence (b);
   a gloss-similarity gate between noun and adjective would be the way to admit +y/+ly later.
   **Revised (2026-10-14, Roger: "Let's go with c)").**  A wrong-sense adjective that passes M1 is a legitimate
   candidate on its own merits (M3 and review still judge it), so +y/+ly cost only their M1/M3 calls and a review
   card: about 16 more relabels, 10 new rows, about $0.20.  Every derived row shows its route on the review card,
   in Roger's wording, e.g. "suffix rule +y from 'slipper', sense not checked" (from the `relabel` block's rule and
   source noun; "sense not checked" for every suffix rule, the derivation link's lexicographer-file gate being the
   only sense check).
3. **Decided (2026-10-14, Roger): (b), the 100-row pilot.**  The Haiku relabel for nouns the rules leave.  The coordinator's rule, which Roger approved, was an
   LLM rewrite "only if some generator is left with more than about 100 nouns".  *Measured*: the censuses leave
   389 person nouns with no deterministic adjective (charlatan, liar, loner, bookworm, dreamer), the corpus roles
   187 (plumber, nurse) and the queue and the roles holding list about 110 more; so the trigger fires.  But two
   facts argue the call would do little: M1 passes these nouns as traits **as nouns** (274 of the 389; the corpus
   already holds 48 nominal labels, [perfectionist](../../data/traits/instructions/perfectionist.json),
   [homebody](../../data/traits/instructions/homebody.json),
   [contrarian](../../data/traits/instructions/contrarian.json), [elitist](../../data/traits/instructions/elitist.json)),
   and for most of them English has no adjective, so the model's answer is either "none" or a synonym (liar to
   dishonest, loner to reclusive), which is M3's job, not a relabel.  Where OEWN merely lacks the link
   (bookworm to bookish, zealot to zealous, prude to prudish) the call would find real ones.
   - (a) Skip.  (b) **A 100-row pilot** (60 person nouns M1 passed as traits, 40 role nouns), Haiku 5.5, about
     $0.01 live, prompt rendered in § 10; adopt the call site for the backlog and as a platform step only if at
     least 20 of the 100 come back with a single established adjective OEWN or wordfreq knows.  (c) Run it over
     all ~700 leftover nouns at once (about $0.04) and read the whole list.
   - **Recommendation: (b).**  It settles the question for a cent; the full run is (c) if the pilot's yield is
     there.
   **Roger (2026-10-14):** "b) SG".
4. **Decided (2026-10-14, Roger): (a), now.**  Apply the backlog pass now or with the next wave.  *Measured* (rule set (b)): 53 backlog rows
   relabel; 10 adjectives are corpus traits (link only, $0), 30 are registry rows already (a `relabel` source is
   added, $0, no new M1 call), **13 are new rows** (about $0.21 of M1 and M3, about 8 review cards, grouped with
   their nouns by the review graph).
   - (a) **Apply now** (`noun_relabel.py backlog --apply`, then M1 and M3 on the 13).  (b) Wait and let the next
     generator wave's submissions carry it (the backlog rows would then stay unlinked).
   - **Recommendation: (a)**; it is the acceptance test of the whole build on real data, and it costs a quarter.
   **Roger (2026-10-14):** "a)".

If a decision is unanswered when Opus reaches the step, it proceeds under the recommendation and records that in
[QUESTIONS.md](./QUESTIONS.md) (§ 12).

## 1. Decisions already made

| decision | reason | source |
|---|---|---|
| **One shared deterministic helper**, free, built now, applied to the base model before its 20k run. | Roger, 2026-10-13: "SG, make this happen, I have no opinion on which project needs to write it, but once it's created every generator that might find it useful should incorporate it, or else we should build it into the pipeline." | plan 03 § 10 (c); plan 05 decision 3 |
| **The helper never changes a label.**  It proposes an *adjective sibling*: the noun row is submitted exactly as the generator emitted it and keeps its own M1 verdict; the adjective is a second candidate, linked both ways.  A quality noun too (honesty beside honest). | Roger: "roles are nouns, so anything we put in the role queue this should not be applied to."  A person noun that M1 will hold on the roles list cannot be told from a noun of disposition before M1 reads it (priest and pedant look alike to a lexicon), so replacing the label would lose roles; adding loses nothing.  Uniform for every noun kind so that the record has one shape. | this plan |
| **The backlog is relabelled retroactively**, read from the registry, as a run of its own (`noun_relabel/backlog-<date>`). | Roger: "We also have a backlog of data generated before it, which we might need to apply this to retroactively." | this plan |
| **Role nouns feed a trait-candidate stream** (`noun_relabel/roles-<date>`): the corpus role files, the queue's role entries and the registry rows held on the roles list, through the same helper; the role itself is untouched. | Roger: "we could use it to generate new candidates from them that might be traits" | this plan |
| A noun with no deterministic adjective is **submitted as the noun and M1 decides**. | the coordinator's recommendation, approved; M1 passes 68% of such person nouns as traits (measured) | plan 03 § 10 (c) |
| Mechanical rules only, each gated on OEWN having the result, so a fold never invents a word; the derivation link reads the sense's lexicographer file; British spellings fold to US. | Roger, plan 03 § 9.4; entity-naming rule (US English) | plan 03; [entity-naming.md](../../.claude/rules/entity-naming.md) |
| Derived rows carry the **submitting generator and run id** at submission time (the row is part of that run and `submit --from` reproduces it); the backlog and roles streams carry generator `noun_relabel`. | plan 13's per-generator recall counts what a generator's run put in front of M3; the backlog has no live run to attach to (the states pass's `renamed` route is the precedent: [states_pass.py](../../assistant_axis/gapgen/states_pass.py) `renamed_candidates`) | this plan |
| An adjective that is already a **corpus trait stem** (or a `renamed_from`) makes no new row: the noun row records `relabel.to_corpus_stem` and M3 will cover the noun through the trait. | 10 of 53 backlog relabels; an M1 call on a corpus label is wasted | this plan |
| No new dependency: `wn` (installed 1.1.1, pinned `>=0.9`) and `wordfreq` are already the platform's. | PLAN_FORMAT | [pyproject.toml](../../pyproject.toml) |

## 2. Out of scope

- Any edit to a trait or role file, to the seed queue, or to `arrangement` fields; promotion stays
  `gap_registry.py promote` by name.
- Synonym relabels (liar to dishonest): M3's territory.  The optional Haiku call (open decision 3) asks for a
  *derived* adjective only.
- A relabel of multi-word surfaces, of words OEWN lacks (2,177 backlog rows), or of a word OEWN lists as an
  adjective already ([atheist](../../data/traits/instructions/atheist.json),
  [feminist](../../data/traits/instructions/feminist.json), bully, elitist: 5,386 rows; the label is valid as it
  is).
- The review app's merge decisions: the review graph groups a noun with its adjective; Roger still decides.
- Plan 05's table columns (`form`, `relabel_rule`) and plan 09's `stem_of`: they call the helper; their files are
  theirs.

## 3. Rule files to Read first

[provenance.md](../../.claude/rules/provenance.md) (usage.json on every paid call site, `MultiModelUsage`;
the pilot of open decision 3 is the only paid step), [entity-naming.md](../../.claude/rules/entity-naming.md)
(`normalize_to_file_name`, US English), [trait-pairs.md](../../.claude/rules/trait-pairs.md) (the seed queue,
the trait-gap platform paragraph), [judging.md](../../.claude/rules/judging.md) (reason before verdict; version
pins; the rendered-prompt rule) before task 9, [CLAUDE.md](../../CLAUDE.md) (file-access boundary, the $20 rule,
tests are mandatory, hotlinks).

**File-access boundary, restated for the Opus task prompt**: read and write only inside the repository worktree,
the agent's scratchpad and `$TMPDIR`; never list, read or stat anything else under the home directory, not
`~/.cache`, not even to see whether something is installed.  OEWN lives in the repository at `data/external/wn/`
([wordnet.py](../../assistant_axis/gapgen/wordnet.py) pins it); if it is missing, say so and stop.  Nothing is
downloaded in this plan.

## 4. Existing code to reuse

- [parse.py](../../assistant_axis/gapgen/generators/base_model/parse.py): `Lexicon`, `normalize_form_kind`,
  `normalize_form`, `us_spelling`, `SUFFIX_EXCEPTIONS`, `NOUN_SUFFIXES`, `ADVERB_EXCEPTIONS`, `_UK_US`: the
  mechanical rules **move** to the new module and are re-exported here under the same names (plan 09's
  `postprocess.stem_of` and [test_gapgen_base_model_parse.py](../../assistant_axis/tests/test_gapgen_base_model_parse.py)
  import them from here; both must keep working unchanged).
- [wordnet.py](../../assistant_axis/gapgen/wordnet.py): `oewn()`, `oewn_installed()`, `ADJ_POS`,
  `OEWN_LEXICON`; the `wn` API as the Roget walk uses it
  ([wn_clusters.py](../../assistant_axis/gapgen/generators/roget/wn_clusters.py) docstring):
  `Wordnet.words(form)`, `.senses(form, pos)`, `Sense.relations()["derivation"]`, `Sense.word().lemma()/.pos`,
  `Synset.lexfile()`, `.definition()`, `.lemmas()`.
- [glosshint.py](../../assistant_axis/gapgen/generators/censuses/glosshint.py): `lookup_forms` (as given, lower,
  hyphen and space), `_clean_definition`; [wordlist.py](../../assistant_axis/gapgen/generators/masked_lm/wordlist.py)
  `person_noun_lemmas` (the hyponym closure; the lexicographer file replaces it here, but the test compares the
  two on a sample); [corpus.py](../../assistant_axis/gapgen/generators/censuses/corpus.py) `corpus_trait_stems`,
  `corpus_renamed_from`.
- [registry.py](../../assistant_axis/gapgen/registry.py): `Candidate`, `submit_candidates`, `SubmitReport`,
  `new_record`, `source_entry`, `_source_identity`, `ROW_FIELDS`, `BLOCKS`, `Registry.update_many`;
  [runs.py](../../assistant_axis/gapgen/runs.py): `start_run`, `RunContext.record_candidates`, `PLATFORM_PATHS`,
  `dirty_refusal`; [normalize.py](../../assistant_axis/gapgen/normalize.py) `normalize_candidate`, `make_key`;
  [freq.py](../../assistant_axis/gapgen/freq.py) `HARD_REJECT_BELOW` (1.5) and the `wordfreq` Zipf.
- [states_pass.py](../../assistant_axis/gapgen/states_pass.py) `renamed_candidates` / `renamed_record` (a
  candidate submitted from a registry row, `source_ref` the row's key, the block's `renamed_to`): the shape this
  plan's links copy.
- [review_graph.py](../../assistant_axis/gapgen/review_graph.py) `label_variant_pairs` (pairs whose labels are
  one label blind are joined as 3-edges, `label_variant`): the relabel pairs join the same way.
- [gap_registry.py](../../data_analysis/gap_generation/gap_registry.py) `cmd_submit`, `cmd_report`,
  `cmd_holding` (the arrow added to the row lines); [promote.py](../../assistant_axis/gapgen/promote.py)
  `queue_entry_from_record` (the note added).
- For task 9 only: [llm.py](../../assistant_axis/gapgen/llm.py) `call_anthropic_json` (no temperature for Haiku
  5.5), [cost.py](../../assistant_axis/gapgen/cost.py) `GuardedUsage`, `Estimate`, `confirm_or_abort`,
  [rubric_versions.py](../../assistant_axis/gapgen/rubric_versions.py) `HISTORY`; the response-recording loop of
  the states pass's gloss check.
- Test style: [test_gapgen_censuses_submit.py](../../assistant_axis/tests/test_gapgen_censuses_submit.py) (a tmp
  registry through the real API), the fake lexicon of
  [base_model_fakes.py](../../assistant_axis/tests/base_model_fakes.py),
  [test_gapgen_interface.py](../../assistant_axis/tests/test_gapgen_interface.py) (the export list and
  `CANDIDATE_FIELDS` pin; `Candidate` does not change).

## 5. File layout

```
assistant_axis/gapgen/nouns.py                       (not there yet) the shared helper
  HELPER_VERSION = 1
  Lexicon(adjectives, nouns)                          moved from base_model/parse.py
  normalize_form_kind / normalize_form / us_spelling / SUFFIX_EXCEPTIONS (+ the -ity sense-drift words:
      personality, reality, mentality, nationality, sexuality, individuality, actuality, speciality, locality,
      totality, legality) / NOUN_SUFFIXES / ADVERB_EXCEPTIONS   moved; parse.py re-exports them
  PERSON_LEXFILES = {"noun.person"}; QUALITY_LEXFILES = {"noun.attribute", "noun.feeling", "noun.cognition"}
  PERSON_SUFFIX_RULES = (("ist", ("istic",)), ("ite", ("itical",)), ("vert", ("verted",)), ("ot", ("oted",)),
                         ("", ("ish",)))                                        person-sense nouns only
  QUALITY_SUFFIX_RULES = (("ty", ("t", "")), ("cy", ("te",)), ("", ("ful", "ous")))  quality-sense nouns only
  PERTAINYM_RE  ("of or relating to", "relating to", "pertaining to", "belonging to", "used by|for", ...)
  FLOOR_ZIPF = freq.HARD_REJECT_BELOW
  NounLookups (Protocol): pos(form) -> list[str]; lexfiles(form) -> set[str];
      derivations(form) -> list[Derivation(adjective, lexfile, definition)];
      adjective_definitions(adj) -> list[str]; synset_mates(adj) -> set[str]; zipf(word) -> float
  OewnLookups(wordnet=None): the real one, cached per process (adjective and noun lemma sets built once)
  FakeLookups(pos=, lexfiles=, derivations=, definitions=, mates=, zipf=): for tests
  Relabel(surface, adjective, rule, lexfile, definition, zipf, helper_version)        frozen dataclass
  NoRelabel(surface, reason)   reason in REASONS = ("phrase", "not_in_oewn", "has_adjective_sense", "not_a_noun",
      "person_no_adjective", "quality_no_adjective", "other_noun", "pertainym_only", "below_floor")
  relabel(surface, *, lookups) -> Relabel | NoRelabel        the rule, in this order:
      1 a surface with a space: phrase.  2 lookup forms (as given, lower, hyphen/space); none: not_in_oewn.
      3 any adjective sense: has_adjective_sense.  4 no noun sense: not_a_noun.
      5 normalize_form_kind folds it to an OEWN adjective: Relabel(rule "suffix:<kind>").
      6 derivation links from senses in PERSON or QUALITY lexfiles, adjectives only, the surface itself excluded;
        choose by (person sense first, then Zipf); if the chosen lemma is below FLOOR_ZIPF take the synset mate
        sharing its first four letters with the highest Zipf (childly -> childlike, aristocratical ->
        aristocratic; rule "derivation+spelling"); pertainym_only when every adjective sense's definition
        matches PERTAINYM_RE; below_floor when still under the floor; else Relabel(rule "derivation").
      7 the suffix rules of the noun's lexfile class (PERSON_SUFFIX_RULES if a person sense, QUALITY_SUFFIX_RULES
        if a quality sense), first match whose result is an OEWN adjective, same pertainym and floor gates:
        Relabel(rule "suffix:<ending>").
      8 person_no_adjective | quality_no_adjective | other_noun.
  derived_candidate(c: Candidate, r: Relabel) -> Candidate   surface r.adjective (OEWN's spelling), same
      generator, run_id, rank, score; gloss_hint = r.definition (the linked adjective sense's, cleaned);
      source_ref = f"relabel:{r.rule}:{c.surface}"; partner_hint None; sense_id 1
  relabel_candidates(cands, *, lookups, corpus_stems) -> list[Derived(noun: Candidate, adjective: Candidate | None,
      relabel: Relabel, corpus_stem: str | None)]            one entry per noun that relabels; corpus hits carry no
      adjective candidate
  relabel_blocks(noun_key, adj_key | None, r, *, corpus_stem=None, now) -> (noun_block, adj_block | None)   § 6
assistant_axis/gapgen/registry.py                   ROW_FIELDS + "relabel"; BLOCKS + "relabel";
  submit_candidates(cands, *, registry_path, run=None, relabel="auto", corpus_stems=None)
      "auto": OewnLookups when wordnet.oewn_installed(), else one WARNING and no relabelling; None/False: off;
      a NounLookups: used (tests).  Derived candidates are appended after their nouns in the same call and
      are NOT written to candidates.jsonl (they are a function of it; `submit --from` re-derives them).
      SubmitReport + n_relabelled, relabels: list[(noun_key, adj_key | None, corpus_stem | None)]
assistant_axis/gapgen/generators/base_model/parse.py   imports and re-exports the moved names; docstring points
      to nouns.py; its own extract_items unchanged
assistant_axis/gapgen/review_graph.py               relabel pairs (rows whose relabel.to_key / from_key name each
      other, both in the build) join label_variant_pairs' groups; `via` "relabel"; GRAPH_SCHEMA 4
assistant_axis/gapgen/review_app/server.py          the card shows "from <noun>" / "adjective: <adj>" from the block
assistant_axis/gapgen/promote.py                    queue_entry_from_record: a note "relabelled from <noun> (<rule>)"
data_analysis/gap_generation/gap_registry.py        submit: --no-relabel; report / holding: "<- noun" / "-> adj"
data_analysis/gap_generation/noun_relabel.py        (not there yet) the CLI, § 7
data/candidates/runs/noun_relabel/backlog-<date>/   (not there yet) candidates.jsonl, run.json, usage.json ($0),
                                                    backlog_report.md (every relabel and every leftover person noun)
data/candidates/runs/noun_relabel/roles-<date>/     (not there yet) the same for the roles stream
data/candidates/noun_relabel/llm_pilot_<date>/      (not there yet; task 9 only) responses.jsonl, usage.json, readout.md
assistant_axis/tests/test_gapgen_nouns.py           (not there yet)
assistant_axis/tests/test_gapgen_registry_relabel.py (not there yet)
assistant_axis/tests/test_gapgen_noun_relabel_cli.py (not there yet)
```

## 6. Data schemas

**The `relabel` block** (additive; `schema_version` stays 1; absent on every row the helper did not relabel, so
the log does not grow by 9,949 lines: the backlog pass re-derives "nothing to do" from the rules, which take
seconds).  On the adjective row:

```json
"relabel": {"from_key": "pedant#1", "from_surface": "pedant", "rule": "derivation", "lexfile": "noun.person",
            "helper_version": 1, "oewn": "oewn:2024", "run": "censuses/2026-10-11-allport_hi",
            "at": "2026-10-14T09:00:00+00:00"}
```

On the noun row: `{"to_key": "pedantic#1", "rule": "derivation", "helper_version": 1, "oewn": "oewn:2024",
"at": ...}`, or, when the adjective is a corpus trait, `{"to_corpus_stem": "artistic", "rule": "derivation", ...}`
and no new row.  A noun relabels to one adjective; a later helper version that derives another adds a second
linked row and leaves the first.

**The adjective row's source entry** (what `submit_candidates` writes; the registry's idempotence key is
`(generator, run_id, surface, source_ref)`, so a resubmission is a no-op):

```json
{"generator": "censuses", "run_id": "2026-10-11-allport_hi", "rank": 412, "score": null,
 "source_ref": "relabel:derivation:pedant", "gloss_hint": "marked by a narrow focus on or display of learning especially its trivial aspects",
 "partner_hint": null, "surface": "pedantic"}
```

**The backlog and roles runs' `candidates.jsonl`** (tracked, `Candidate`'s fields exactly; the main checkout's
`gap_registry.py submit --from` replays it):

```json
{"surface": "snobby", "generator": "noun_relabel", "run_id": "backlog-2026-10-14", "rank": null, "score": null,
 "gloss_hint": "...", "sense_id": 1, "source_ref": "relabel:derivation:snob#1", "partner_hint": null}
```

(`source_ref` names the registry key for these streams, the surface for a live submission; the block's
`from_key` is the authoritative link in both.)  The roles stream's `source_ref` is `relabel:<rule>:role:<stem>`,
`relabel:<rule>:queue_role:<stem>` or `relabel:<rule>:roles_list:<key>`; a role noun whose adjective is already a
registry row still submits (the row gains a `noun_relabel` source, M1 does not run again on a filtered row); one
whose adjective is a corpus trait is listed in the report and not submitted.

**`run.json` of a stream** adds `helper_version`, `oewn`, `rules` (the rule tables' sha256), `counts` (by rule,
by where the adjective already was, by the noun's M1 state) and, for the backlog, `registry_snapshot_sha256`.

**The pilot's response record** (task 9): `{"key", "label", "gloss", "kind": "person"|"role", "prompt_sha256",
"model", "raw", "parsed": {"reason", "adjective", "confidence"}, "in_oewn", "zipf", "at"}`.

## 7. CLI

`uv run python data_analysis/gap_generation/noun_relabel.py ...` (all read the live registry; `--registry PATH`
for tests):

- `check WORD ...`: prints `relabel()`'s answer per word ($0), for Roger to poke at the rules.
- `backlog [--apply] [--run-id backlog-<date>]`: every registry row with a single-word label through the helper;
  prints the table (relabels by rule; adjective already a corpus trait / a registry row / new; the noun's M1
  state; the leftover person nouns by generator) and writes
  [backlog_report.md](../../data/candidates/runs/noun_relabel/backlog-2026-10-14/backlog_report.md) (not there yet;
  the date is the run's).  Without `--apply` nothing is
  written to the registry (the dry run is the default).  With `--apply`: `relabel` blocks on the linked rows
  (`update_many`), the new adjectives submitted as `noun_relabel/<run-id>` with `relabel=None` (the stream does
  its own linking), `candidates.jsonl` first; then prints the follow-up commands:
  [traithood_filter.py](../../data_analysis/gap_generation/traithood_filter.py) `--batch-id <run-id> --run
  noun_relabel/<run-id> --pipeline split --budget-usd 1` and
  [novelty_score.py](../../data_analysis/gap_generation/novelty_score.py) `score --batch-id <run-id> --run
  noun_relabel/<run-id> --budget-usd 1` (the paid steps are the
  platform's CLIs with their own estimates and caps; this command spends nothing).  Idempotent: a row that already
  carries a `relabel` block at the current helper version is skipped.
- `roles [--apply] [--run-id roles-<date>]`: the three role sources (role files by `positive_label`, queue entries
  with `entity_type: "role"`, registry rows with `holding: "roles"`); the same table, report and follow-ups.
  Never writes a role file, a queue entry or a held row's label; the held row gets the `to_key` link only.
- `llm-pilot --n 100 --budget-usd 0.10 [--seed 0] [--dry-run] [--allow-dirty]` (task 9, only on Roger's go):
  estimate printed (Haiku 5.5, about 300 input and 60 output tokens a call, $0.10 / $0.50 per million: about
  $0.006 for 100), `confirm_or_abort`, dirty-tree refusal, `GuardedUsage` to `usage.json`, every response recorded
  before it is parsed, [readout.md](../../data/candidates/noun_relabel/llm_pilot_2026-10-14/readout.md) (not there
  yet; dated by the run) with the yield and the full list.

`gap_registry.py submit --file|--from` gains `--no-relabel` (the validation set and any replay that must be
judged as given).

## 8. Acceptance tests, written first

The three new test files are [test_gapgen_nouns.py](../../assistant_axis/tests/test_gapgen_nouns.py),
[test_gapgen_registry_relabel.py](../../assistant_axis/tests/test_gapgen_registry_relabel.py) and
[test_gapgen_noun_relabel_cli.py](../../assistant_axis/tests/test_gapgen_noun_relabel_cli.py) (none there yet).

- `test_gapgen_nouns.py` (FakeLookups throughout; no OEWN): the rule order on one word per branch (phrase,
  not_in_oewn, has_adjective_sense for atheist, not_a_noun, suffix fold stubbornness to stubborn, derivation pedant
  to pedantic from `noun.person`, a thing-sense link rat to ratty refused as other_noun, quality link empathy to
  empathetic, person suffix narcissist to narcissistic and hypocrite to hypocritical and fool to foolish, quality
  suffix honesty to honest, pertainym_only doctor to doctoral, below_floor, the spelling mate childly to
  childlike); the -ity exceptions (personality is not personal); `relabel(r.adjective)` is `has_adjective_sense`
  (idempotence); `derived_candidate` field by field; `relabel_candidates` skips corpus stems; the rule tables'
  sha256 pinned (a change bumps `HELPER_VERSION`).
- `test_gapgen_nouns.py::TestRealOewn` (`skipif not oewn_installed()`): twelve words with their expected answers
  (pedant, coward, snob, atheist, rat, doctor, child, narcissist, hypocrite, honesty, personality, yes-man), so an
  OEWN or `wn` upgrade shows; `Synset.lexfile()` present; the lexicographer-file person test agrees with
  `person_noun_lemmas` on the 100 most frequent person nouns of the closure.
- `test_gapgen_base_model_parse.py` passes **unchanged** after the move (it imports through `parse`).
- `test_gapgen_registry_relabel.py` (tmp registry, FakeLookups): one noun candidate makes two rows with both
  blocks and the source entry of § 6; the report's `n_relabelled` and `relabels`; resubmission is a no-op
  (`n_unchanged`); a corpus-stem adjective makes no row and `to_corpus_stem`; `relabel=None` makes one row;
  `relabel="auto"` without OEWN warns once and makes one row; `gap_registry.py submit --from` on the run's
  `candidates.jsonl` reproduces the derived row; every existing registry and generator submit test passes with
  the default (they run without OEWN, so nothing changes for them).
- `test_gapgen_noun_relabel_cli.py`: `backlog` on a tmp registry seeded with a noun row, a noun whose adjective is
  a corpus trait (tmp data dir) and a row already linked: the dry run writes nothing (byte-identical registry);
  `--apply` writes the blocks, the run directory with `candidates.jsonl` before the append, `run.json`,
  `usage.json` with zero cost, and is idempotent on a second run; `roles` on a tmp data dir with two role files
  and a queue role entry: the role files and the queue are byte-identical after `--apply`; `check` prints.
- Review graph: a relabel pair in a tmp build is a `label_variant`-style 3-edge with `via` "relabel";
  `GRAPH_SCHEMA` 4 round-trips.  Promote: the queue entry's note.  `test_gapgen_interface.py` still passes
  (`Candidate` unchanged; `nouns` added to the docstring's module list if exported).
- Task 9 (only if built): the prompt's sha256 pinned in `rubric_versions.HISTORY["noun_relabel"]`, reason before
  answer, a fake client round trip, usage charged for an unparseable reply, the dry run writes nothing.

Commands that must pass: `uv run pytest assistant_axis/tests/test_gapgen_nouns.py
assistant_axis/tests/test_gapgen_registry_relabel.py assistant_axis/tests/test_gapgen_noun_relabel_cli.py
assistant_axis/tests/test_gapgen_base_model_parse.py assistant_axis/tests/test_gapgen_interface.py -q`, then
`uv run pytest assistant_axis/tests/test_gapgen_*.py -q`, `uv run python data_analysis/check_arrangements.py`,
`uv run python tools/sync_entity_lists.py --check` (nothing in the corpus changes; the two are the format's check
that nothing did).

## 9. Ordered task checklist

1. Tests of § 8 for `nouns.py`, red.  Move the mechanical rules out of `parse.py` into `nouns.py`, re-export;
   `test_gapgen_base_model_parse.py` green unchanged.
2. `relabel()` with `FakeLookups` and `OewnLookups`; the real-OEWN pin test; `check` subcommand.
3. `derived_candidate`, `relabel_candidates`, `relabel_blocks`; `ROW_FIELDS` / `BLOCKS`; `submit_candidates`'s
   `relabel` parameter and report fields; `gap_registry.py submit --no-relabel`; the registry tests green and the
   whole gapgen suite green.
4. `noun_relabel.py backlog` dry run on the live registry (read-only): the table of the measurement section
   reproduced (53 relabels under rule set (b); the counts may move by a few rows with the registry); write
   `backlog_report.md` to the scratchpad for the acceptance report.
5. `noun_relabel.py roles` dry run: 40 / 6 / 3 adjectives from the three sources, 6 distinct new.
6. Review graph, review app card, promote note, `report` / `holding` arrows; tests.
7. Open decision 4 (a): `backlog --apply`, then M1 and M3 on `noun_relabel/backlog-<date>` (about $0.21 live,
   caps $1 each); `roles --apply` and the same (about $0.10).  Both under $20: real time.  Report the rows M1
   passed and M3 kept, and the review graph's grouping of each with its noun.
8. The AGENT_NOTES paragraph under "Trait-gap platform": what the helper is, where it runs, the `relabel` block,
   the two streams, `--no-relabel`; `uv run python tools/sync_agent_notes.py`.  A line in plan 05's decision 3
   and plan 09 § 4 saying `normalize_form` now lives in `nouns.py` (same import path still works).
9. Open decision 3 (b), only on Roger's go: the pilot prompt (§ 10) pinned, `llm-pilot --dry-run` showing the
   100 rows and the estimate, then the run; `readout.md` with the yield and the list; no call site beyond the
   pilot until Roger has read it.

## 10. Pilot

The build's pilot is task 7 on real data: the backlog pass (53 relabels, 13 new rows) and the roles stream (6
new rows), about $0.31 together, live.  Readout: per rule, how many adjectives M1 passed and M3 kept; the review
graph's grouping; the full relabel list with the noun's M1 state beside it, for Roger's eye (my reading of the
list is in the measurement section).  **Roger decides** on it: the rule set stays (b), or drops a rule whose
measured precision is poor, or adds +y / +ly after all (open decision 2); and whether the base-model 20k run
submits with the helper on (the default) or `--no-relabel`.

**The optional Haiku pilot (open decision 3, task 9), as the model will receive it.**  System prompt (cached,
pinned as `noun_relabel` v1 in `rubric_versions.HISTORY`):

```
You are helping curate a research corpus of personality traits. Each entry is a one- or two-word label, and the
corpus prefers an adjective ("pedantic", "cowardly") to a noun for the kind of person ("pedant", "coward"),
because a persona is prompted with "You are <label>." Some such nouns have a standard English adjective meaning
"like such a person" (pedant: pedantic; hypocrite: hypocritical; bookworm: bookish); many have none (charlatan,
loner, go-getter), and for those the noun stays.

You are given one noun and a one-sentence gloss of the disposition it names. Say whether English has a standard
adjective for being that kind of person.
- The adjective must be in established use with that meaning, one word (a hyphen is allowed), not coined for the
  occasion, and derived from the noun or its root (bookworm: bookish is fine; liar: dishonest is not, a synonym is
  not a relabel).
- If several exist, give the most common.
- If none exists, say so; do not force one.

Respond with one JSON object and nothing else, reason first:
{"reason": "<one short sentence>", "adjective": "<word>"|null, "confidence": <0-1>}
```

User turn, one row a call (a registry row's `label` and `gloss`; for a role noun with no gloss, the role file's
`description`):

```
Noun: charlatan
Gloss: This means pretending to skill or knowledge one does not have, presenting oneself as expert while covering
over the gaps in what one actually can do.
```

A second sample, the case the rules miss:

```
Noun: bookworm
Gloss: This means reading voraciously and returning to books again and again, treating a good novel or a stack of
library loans as the most welcome part of one's day.
```

Model `claude-haiku-5-5` (no temperature: [llm.py](../../assistant_axis/gapgen/llm.py) `accepts_temperature`),
`max_tokens` 120, one reading.  The readout counts answers that are an OEWN adjective or clear Zipf 1.5, lists
every answer, and marks the ones the rules would have given anyway (none, by construction of the sample).  Adopt
threshold: 20 of 100.  Cost: about $0.006; cap $0.10; live.

## 11. Report at the end

One page at [acceptance_noun_normalization.md](./acceptance_noun_normalization.md) (not there yet): what was built
against § 5; deviations with reasons; the § 8 commands verbatim with pass counts; the backlog and roles tables
from the real run beside the measurement section's figures; M1 and M3 outcomes of the new rows and the cost from
the two `usage.json` files; the pilot's readout if task 9 ran; open QUESTIONS entries; the AGENT_NOTES paragraph as
written.

## 12. Escalation

Opus retries a failing step once with a changed approach, then Fable (diff review, architecture, stubborn
failures), then Roger through [QUESTIONS.md](./QUESTIONS.md) in its format (`N. [NN] question. Assumption
proceeded under: ... Status: open`, numbering continues from 91), proceeding under the stated assumption unless the
answer would make the work useless.  Pre-registered entries Opus copies in at the start: (1) OEWN absent at
`submit_candidates` time: one WARNING and no relabelling, the backlog pass catches the rows up later; (2) derived
rows are not written to the generator's `candidates.jsonl` (re-derived on replay), the block's `from_key` is the
link; (3) a noun relabels to one adjective per helper version.  Anything that would edit a trait or role file or
the queue, spend over a command's cap, or change `Candidate`, stops and asks.

## Measured on 2026-10-13 (read-only; scratch scripts, nothing written into the repository)

**The backlog.**  Registry 9,949 keys; 8,849 single-word labels, 1,100 phrases.  Of the single-word rows OEWN
lacks 2,177, lists 5,386 with an adjective sense (left alone), 137 as non-nouns, and **1,149 as nouns with no
adjective sense** (13%), of which about 440 are person nouns (408 by lexicographer file).  What M1 did with the
1,149: **trait 524 (46%)**, held on states 180, turned away by the frames ("You are <label>." gave no reading or
a stretched one) 266 (23%, mostly thing-words: bacon, bond, chit), **held on roles 94**, physical 20, other
rejects 60, unfiltered 3.  For the 440 person nouns alone: trait 298 (68%), roles 79 (18%), frames 27 (6%).  So
M1 does not drop nouns of disposition as nouns; the base-model pilot's "8% of eligible words, 2.7% of M1
survivors" counts the junk nouns a free model emits (data, query, house: 85 of its 310 eligible nouns), which M1
rejects rightly.  By generator the 1,149 are censuses 1,068, states_pass 31, base_model 40, roget 13,
antonym_check 13, ipip 2, alignment_sweep 1.

**Relabel coverage, rule set (b).**  53 of the 1,149 (4.6%): derivation 34 (two by the spelling mate), the
existing suffix rules 4, -istic 4, +ish 8, -itical 1, -verted 1, +ful 1.  Adjective already a corpus trait 10
([artistic](../../data/traits/instructions/artistic.json) from artist,
[empathetic](../../data/traits/instructions/empathetic.json), [foolish](../../data/traits/instructions/foolish.json),
[friendly](../../data/traits/instructions/friendly.json), [hawkish](../../data/traits/instructions/hawkish.json),
[humble](../../data/traits/instructions/humble.json) from humility,
[introverted](../../data/traits/instructions/introverted.json),
[pessimistic](../../data/traits/instructions/pessimistic.json), [romantic](../../data/traits/instructions/romantic.json)
from romanticism, [spiritual](../../data/traits/instructions/spiritual.json)); already a registry row 30
(gentlemanly, hypocritical, narcissistic, realistic, vain, venomous, villainous, ...); **new 13**: bratty,
cabalistic, dwarfish, dysphoric, faddish, hammy, simplistic, snobby (right by my reading) and blubbery,
characteristic, complementary, lemony, shrimpy (wrong: OEWN's quality senses of thing-words, and its metaphorical
person sense of shrimp).  The nouns' own M1 states: trait 38, held 7, rejected 8.  By generator: censuses 38,
base_model 13, antonym_check 2, roget 1.  Gates at work: the lexicographer-file gate on the derivation link
refused 35 thing-sense links (rat, bog, face, fish, wood); the pertainym gate 7 (brahminical, casuistical,
cenobitic, faustian, gladiatorial, modernistic, nominalistic); the floor 6 (brickly, caseous, fogyish,
hoydenish, landlubberly, scoundrelly: all Zipf 0).  Left out of (b): +y and +ly, 16 relabels of which fishy,
bloody, woody, hilly, curly, slippery, pimply, funky, contributory, wormy are wrong (10 of 16).  What the rules
leave: **389 person nouns** with no deterministic adjective (M1: trait 274, held 93, rejected 38; charlatan,
liar, loner, dreamer, bookworm, cheat, charmer, chameleon), 89 quality nouns (honesty and modesty are among the
few a -ty rule folds), 589 other nouns (thing-words).  One existing-rule defect found: `-ity` folds personality to
personal (and would fold reality, mentality, nationality); § 5 adds them to `SUFFIX_EXCEPTIONS`.

**The corpus's own convention.**  48 of the 932 trait labels are OEWN nouns with no adjective sense (twelve zodiac
signs, perfectionist, homebody, contrarian, elitist, populist, determinist, materialist, lurker, joiner, renter,
smoker, teetotaler, ...): nominal labels are admitted where English has no adjective, which is what "the noun
stays and M1 decides" continues.

**Roles.**  Corpus role files 340: 40 have an adjective under rule set (b), 13 of them corpus traits
([altruist](../../data/roles/instructions/altruist.json) to altruistic, [cynic](../../data/roles/instructions/cynic.json)
to [cynical](../../data/traits/instructions/cynical.json), [critic](../../data/roles/instructions/critic.json),
[athlete](../../data/roles/instructions/athlete.json), [poet](../../data/roles/instructions/poet.json),
[philosopher](../../data/roles/instructions/philosopher.json), [skeptic](../../data/roles/instructions/skeptic.json),
[spirit](../../data/roles/instructions/spirit.json), [artist](../../data/roles/instructions/artist.json), ...), 20
registry rows already ([priest](../../data/roles/instructions/priest.json) to priestly,
[scholar](../../data/roles/instructions/scholar.json) to scholarly, [child](../../data/roles/instructions/child.json)
to childlike, [judge](../../data/roles/instructions/judge.json) to judicial,
[angel](../../data/roles/instructions/angel.json), [demon](../../data/roles/instructions/demon.json),
[monk](../../data/roles/instructions/monk.json) to monkish, ...), 1 a live queue entry
([parasite](../../data/roles/instructions/parasite.json) to parasitic), **6 new**:
[beggar](../../data/roles/instructions/beggar.json) to beggarly, [chimera](../../data/roles/instructions/chimera.json)
to chimerical, [entrepreneur](../../data/roles/instructions/entrepreneur.json) to entrepreneurial,
[ghost](../../data/roles/instructions/ghost.json) to ghostly, [monarch](../../data/roles/instructions/monarch.json)
to monarchical, [oracle](../../data/roles/instructions/oracle.json) to oracular.  The pertainym gate dropped 17
([doctor](../../data/roles/instructions/doctor.json) to doctoral, [editor](../../data/roles/instructions/editor.json)
to editorial, [tutor](../../data/roles/instructions/tutor.json) to tutorial, secretarial, viral, curatorial,
...); 187 roles are person nouns with no adjective; 48 have an adjective sense already.  Queue role entries 78: 6
adjectives, the 2 new ones (beggarly, monarchical) the corpus roles already gave.  Registry rows held on roles
211: 3 adjectives, none new.  So Roger's role stream yields **6 distinct new trait candidates** deterministically,
about $0.10 through M1 and M3, plus 20 links on existing rows; the rest is open decision 3's territory.

**The base-model pilot table** ([candidate_table_round1.jsonl](../../data/candidates/base_model/candidate_table_round1.jsonl),
3,825 eligible words, 310 nouns): 57 relabel under (b) (empathy to empathetic 15 emissions, humor, vanity,
humility, courage, compassion, enthusiasm, hypocrisy, introvert, pessimist, hypocrite, narcissist, coward, cynic,
despot, egoist, snob, ...); 21 are corpus traits, 31 registry rows, 8 new; 84 person nouns and 67 quality nouns
have no adjective; 85 are thing-words.  Of the 38 nouns at the submission floor (count 2) 14 relabel.  Scaled to
the 20k run (about 2.5 times the words): some 140 derived rows, about 20 new, about $0.30.

**Costs**: the helper $0; the backlog pass about $0.21 (13 rows at M1 $0.0072 and M3 $0.011 at the 0.8 pass
rate); the roles stream about $0.10; the Haiku pilot about $0.006 (the full ~700 leftover nouns about $0.04).  All
live.  Review: about 8 and 4 cards, each grouped with its noun.

## Inconsistencies with the existing code, and how each is resolved

| found | resolution |
|---|---|
| `normalize_form` lives in the base model's `parse.py` and plan 09's `postprocess.stem_of` imports it from there ([coding_plan_09_structural_generators.md](./coding_plan_09_structural_generators.md) § 5), as does plan 05's file layout | the rules move to [nouns.py](../../assistant_axis/gapgen/nouns.py) (not there yet); `parse.py` re-exports every name, so plan 09's build (in its worktree today) and the parse tests need no change; a one-line note in both plans |
| `-ity` fold has no sense check: personality to personal is a live backlog relabel (M1 passed "personal" as a trait) | the sense-drift words join `SUFFIX_EXCEPTIONS` (§ 5); a test |
| plan 05 decision 3 says "the relabel lands in `label` and the noun stays in `surface`", that is, the table submits the adjective | under this plan the generator submits the noun and the platform adds the adjective; plan 05's table keeps its `form` / `relabel_rule` columns by calling `relabel()` for its readout.  One line in plan 05 when it is next edited (its decision 3 already points here) |
| the base model folds -ness/-ity nouns before submission (`normalized_from` on its table) and the platform would see the adjective | unchanged: a quality noun folded by the generator reaches the platform as an adjective and nothing more happens; a noun it did not fold gets the platform's sibling |
| `submit_candidates` has no OEWN dependency and the registry tests run without OEWN | `relabel="auto"` is a no-op with a WARNING when OEWN is not installed; tests inject `FakeLookups`; the backlog pass is the catch-up |
| `ROW_FIELDS` is a fixed tuple; `BLOCKS` names the mergeable blocks | both gain `relabel`; `schema_version` stays 1 (additive) |
| the review graph joins label variants by `label_variant_key` (hyphen, case, space, apostrophe) | the relabel pairs join the same groups with `via` "relabel"; `GRAPH_SCHEMA` 4 |
| the masked-LM generator's agent-noun frames ([coding_plan_04_masked_lm.md](./coding_plan_04_masked_lm.md)) and plan 06's role nouns ([coding_plan_06_llm_entropy.md](./coding_plan_06_llm_entropy.md) measured baseline) emit person nouns with no local fold | covered by the platform step at their next submission; their earlier rows by the backlog pass |
| plan 13's pooled recovery harness ([coding_plan_13_generator_testing.md](./coding_plan_13_generator_testing.md)) is being built today | unaffected: derived rows carry the generator's name and count as its candidates; the harness submits nothing |

## Adoption order

1. This build (one Opus agent, worktree; the platform paths are `PLATFORM_PATHS`, so paid runs refuse until it is
   committed).  2. The backlog and roles streams (task 7).  3. The base-model 20k run submits through the platform
   with the helper on (nothing to add to plan 03; Roger's "applied to the base model before the 20,000-sample
   run").  4. Plans 09 and 13 merge in either order (the import path is kept); plans 05, 06 and 12 inherit the step
   with no code of their own.  5. The Haiku pilot if Roger says so (open decision 3).

## Frozen interface (for the generators and plans 05, 06, 09, 12)

`from assistant_axis.gapgen.nouns import relabel, Relabel, NoRelabel, OewnLookups, FakeLookups, HELPER_VERSION,
normalize_form, normalize_form_kind, Lexicon`: `relabel(surface, *, lookups) -> Relabel | NoRelabel` with the
fields of § 5; `submit_candidates(..., relabel="auto" | None | NounLookups)` and `SubmitReport.n_relabelled` /
`.relabels`; the `relabel` block of § 6; `source_ref` prefix `relabel:`.  Names are added, never renamed,
without a note here; a rule change bumps `HELPER_VERSION` and adds a row to the pinned table.
