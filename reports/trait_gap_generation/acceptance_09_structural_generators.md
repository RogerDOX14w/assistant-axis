# Acceptance report: workstream 9, the structural generators (generator id `structural`)

Built 2026-10-13 by Opus in the worktree `plan09-build` (from `anthropic-vllm-uv` at 736c06c6), to
[coding_plan_09_structural_generators.md](./coding_plan_09_structural_generators.md) with its decisions closed
(Roger, 2026-10-13).  **Status: built and tested; no paid call has been made.**  Every free step is done; the paid
steps (the null-rate pilot, the stability run, the modernise call, the full operator pass, the submissions and M1
and M3 on them) are listed in order with their estimates in § 8, for the coordinator to run from the main checkout.
Terms: the [glossary](./glossary.md), whose new section "Structural-generator terms" defines
[the Aristotelian mean](./glossary.md#aristotelian-mean), [position](./glossary.md#position),
[the five operators](./glossary.md#structural-operators), [the null rate](./glossary.md#null-rate),
[label-set Jaccard](./glossary.md#label-set-jaccard) and [net-new rows and the net-new kept share](./glossary.md#net-new).
M1 is the platform's trait-hood filter and M3 its novelty check.

## 1. What was built, against the plan's file layout (§ 5)

| file | what it does |
|---|---|
| [structural/\_\_init\_\_.py](../../assistant_axis/gapgen/generators/structural/__init__.py) | the paths, `GENERATOR = "structural"`, and the frozen interface (`load_operator_table`, `OPERATOR_TABLE_PATH`, `load_position_table`, `POSITION_TABLE_PATH`) |
| [classical.py](../../assistant_axis/gapgen/generators/structural/classical.py) | loads and checks the five hand-typed tables; `require_verified` is the VIA gate |
| [prompts.py](../../assistant_axis/gapgen/generators/structural/prompts.py) | reads the two pinned prompts (refuses an unpinned text), the declared example words and the hygiene lists |
| [modernise.py](../../assistant_axis/gapgen/generators/structural/modernise.py) | generator A's call: 20 classical rows a call, 1-3 modern labels, a gloss, a polysemy flag; `classical_modern.jsonl` |
| [operators.py](../../assistant_axis/gapgen/generators/structural/operators.py) | generator B's call: one per trait, the user turn (never the `negative_label` or the members), the parser, the item rule (over-/under-/too-/non-X, more than four words, non-ASCII), the principal-target guard both ways, the call loop (recorded before parsing, retried once, resumed by prompt hash), the estimate, the stratified sample |
| [postprocess.py](../../assistant_axis/gapgen/generators/structural/postprocess.py) | stems (folded through OEWN), the membership tags with `registered_by`, `registered_decided` and `net_new`, the merge (every source kept, `n_sources`, `roles`, `siblings`, `kinds`), the rank, `operator_table.jsonl` |
| [sidetable.py](../../assistant_axis/gapgen/generators/structural/sidetable.py) | `position_table.jsonl` and `negative_label_mismatches.md`; never writes a trait file |
| [evaluate.py](../../assistant_axis/gapgen/generators/structural/evaluate.py) | pair recovery, structure recovery, the queue hold-out's three lines and their four frozen lists, null rates, pair-pole positions, stability Jaccard, parse rate, `evaluation.json` |
| [submit.py](../../assistant_axis/gapgen/generators/structural/submit.py) | `--all`, the review-hour wave (`--kept-target`, counted on net-new rows, siblings travelling), candidates and `source_ref`, the downstream estimate and gate, the review-rate hook for plan 13 |
| [report.py](../../assistant_axis/gapgen/generators/structural/report.py) | `report.md` (led by the already-registered headline, pair completions and degree fillers first, the novel figure raw and net), `roger_sample.md`, `ai_identity_subfamily.md` |
| [structural_generator.py](../../data_analysis/gap_generation/structural_generator.py) | the CLI: `classical`, `modernise`, `operators`, `null-rate`, `stability`, `postprocess`, `side-table`, `submit`, `report` |
| [structural_operators.md](./rubrics/structural_operators.md), [structural_modernise.md](./rubrics/structural_modernise.md) | the two prompts, pinned as version 1 in [versions.json](./rubrics/versions.json), named in `GENERATOR_FILES` of [split_rubrics.py](../../assistant_axis/gapgen/split_rubrics.py) |
| [classical/](../../data/candidates/structural/classical/) | [aristotle.json](../../data/candidates/structural/classical/aristotle.json), [theophrastus.json](../../data/candidates/structural/classical/theophrastus.json), [sins_virtues.json](../../data/candidates/structural/classical/sins_virtues.json), [via.json](../../data/candidates/structural/classical/via.json), [murray.json](../../data/candidates/structural/classical/murray.json): hand-typed, tracked |
| tests | [test_gapgen_structural_classical.py](../../assistant_axis/tests/test_gapgen_structural_classical.py), [\_prompts](../../assistant_axis/tests/test_gapgen_structural_prompts.py), [\_operators](../../assistant_axis/tests/test_gapgen_structural_operators.py), [\_postprocess](../../assistant_axis/tests/test_gapgen_structural_postprocess.py), [\_sidetable](../../assistant_axis/tests/test_gapgen_structural_sidetable.py), [\_evaluate](../../assistant_axis/tests/test_gapgen_structural_evaluate.py), [\_submit](../../assistant_axis/tests/test_gapgen_structural_submit.py), [\_acceptance](../../assistant_axis/tests/test_gapgen_structural_acceptance.py), the CLI's [test_gap_generation_structural_cli.py](../../data_analysis/tests/test_gap_generation_structural_cli.py), and the fixtures [structural_fakes.py](../../assistant_axis/tests/structural_fakes.py) |

Also: six [glossary](./glossary.md) entries (task 6), [QUESTIONS](./QUESTIONS.md) 108-120 (§ 10 below), and one
`.gitignore` line for the tables' `.bak.<UTC>` snapshots.  Not there yet, because each is written by a paid step:
[classical_modern.jsonl](../../data/candidates/structural/classical_modern.jsonl),
[operator_table.jsonl](../../data/candidates/structural/operator_table.jsonl),
[position_table.jsonl](../../data/candidates/structural/position_table.jsonl),
[negative_label_mismatches.md](../../data/candidates/structural/negative_label_mismatches.md),
[evaluation.json](../../data/candidates/structural/evaluation.json) and the runs under
[runs/structural/](../../data/candidates/runs/structural/) (all not there yet).

## 2. The three decisions as built

1. **The review-hour wave** (decision 1).  `submit --kept-target 300 --kept-share X` walks the table in rank order,
   each selected row's siblings travelling with it, until `ceil(300 / X)` **net-new** rows are selected; a corpus,
   queued or already-decided row inside the cut is submitted and counted toward neither the target nor the estimate.
   `X` is the pilot's measured net-new kept share; until then 0.5, printed as ASSUMED.  The readouts lead with pair
   completions and degree fillers and give the novel figure raw and net.  **Review rate**: the plan's ~150 terms an
   hour; `--review-rate measured` is the marked hook (`submit.review_terms_per_hour`) that switches to plan 13's
   `pooled_review_rate` once `assistant_axis.gapgen.testing` is merged (until then it refuses with a pointer).  When
   plan 13's rate is None (no review log with decisions) it falls back to the plan's figure with a printed note
   (review S4, 2026-10-13); tests cover the refusal, the fallback and a measured rate.
2. **The queue hold-out's three lines** (decision 2).  `evaluate.freeze_holdout` builds the four stem lists and
   the null-rate command writes them into `evaluation.json` before its first call (the pilot's start); `postprocess`
   freezes them only if no pilot has.  On the main checkout's registry today they would be **96** (84 `backlog` and
   12 `paired` without a file), **139** rejected names, **41** accepted registry rows and **38** queue candidates,
   as the plan counts.
3. **Principal targets, staged.**  `--principal-min-score` (default 3) lists the user, the operator and the
   developer for the **108** traits at alignment score 3 (among them [obedient](../../data/traits/instructions/obedient.json),
   [rebellious](../../data/traits/instructions/rebellious.json), [scheming](../../data/traits/instructions/scheming.json),
   [unhelpful](../../data/traits/instructions/unhelpful.json), [sycophantic](../../data/traits/instructions/sycophantic.json),
   [honest](../../data/traits/instructions/honest.json), [manipulative](../../data/traits/instructions/manipulative.json)
   and [deferential](../../data/traits/instructions/deferential.json), all at score 3 in
   [corpus_regions.json](../../data/candidates/corpus_regions.json)).  A later stage runs `--principal-min-score 2
   --principal-only` (75 traits once stage 1 is recorded; score 1 adds 317), which sends only the three principal
   slots and skips every trait whose recorded answers already carry them.  The guard refuses a principal-target
   input below the score and drops (with a problem recorded) a principal answer for a trait the call did not list
   them for.  Principal items go to `ai_identity_subfamily.md` for the QUESTIONS 67/78 sign-off.  Haiku 5.5, no
   `temperature`.

## 3. Deviations, with reasons

- **`registered_decided`** means M1 and M3 have nothing left to do (an M1 verdict other than `trait`, or `trait`
  and an M3 block), not "an M1 verdict and an M3 decision": M3 never scores a rejected word, so the plan's literal
  rule would count M1's rejects as undecided for ever ([QUESTIONS](./QUESTIONS.md) 117).
- **The estimate prices every selected row the registry has not decided**, a corpus or queue word not yet in the
  registry included (M1 will be charged for it); the wave's target counts net-new rows only (QUESTIONS 118).
- **`excess` and `deficiency` follow the plan's rule, not its illustration**: the illustrative reply had the two
  the other way round from the rule beside it (QUESTIONS 119); the coding plan's illustration was corrected to the
  rule on 2026-10-13.
- **`n_sources` counts distinct traits and classical rows** reaching a stem, not sources (one trait whose
  opposite and deficiency land on one word counts once; QUESTIONS 115).
- **The evaluation functions read the replies, not the merged table** (`pair_recovery(replies, pairs, ...)`), so
  that each trait's blind opposite is judged as answered, not through a merged row's first gloss.
- **The prompt is longer than the plan's estimate**: 6,625 characters, about 1,740 input tokens a call with the
  user turn, against the plan's 1,200 (three worked examples, the nine targets and the label rule).  The full pass
  is **$0.43**, not $0.37; still under $1.  No cache hit is assumed (Haiku 5.5's cache minimum is 512 tokens, so it
  will in fact be cached; the plan assumed 4,096).
- **`modernise` leaves VIA out by default** while it is unverified (133 rows in 7 calls, not ~205 in 11);
  `--scheme via` is refused with exit 2.
- **Answers are always reused by prompt hash** in the paid commands (`operators --resume` and `modernise
  --resume` are kept for the plan's CLI shape and are no-ops): a rerun never pays twice for the same prompt and
  model.  For `modernise` this includes the call that re-asks the rows a twenty-row answer left out, whose prompt is
  recomputed from those rows (review S1, 2026-10-13: until then `modernise` reused only with `--resume`, and never
  the retry).
- **Several runs** (`postprocess --run-id R1 R2`): the run named last wins for a trait answered in full by both;
  principal-only answers add their items beside the full reply.
- **`postprocess --embedder none|hash|openai`** (default `openai`, pennies, gated by `--budget-usd 0.1` and the
  dirty-tree check) and `--no-fold` (no OEWN); `evaluation.json` is rewritten only when its payload changes, so a
  rerun leaves it byte-identical (its envelope's time would otherwise move).  The embeddings' spend goes to the
  cumulative `data/candidates/structural/usage.json` even when the cap stops them (the guard writes it, and a
  `finally` again; the command then exits 1 without writing `evaluation.json`; review S3, 2026-10-13).
- **The read-only commands read the registry without its lock** (`read_snapshot`), so that a dry run writes
  nothing, not even `registry.jsonl.lock`.
- **The pilot gates exit 3** (`null-rate` outside the band, `stability` below 0.5): a revision round or Roger's
  decision, not a crash.
- **Prompt hygiene is the stricter form** (every word of each prompt against the corpus, the whole seed queue and
  the two validation files, with two prose words recorded, `mean` and `operator`), not only the example words.
- **How the tests were run.**  In this worktree `uv run pytest` picked up the main checkout's virtual
  environment (its `VIRTUAL_ENV` is inherited by the shell), and for `data_analysis/tests` imported the main
  checkout's package; so every test here was run as `uv run --extra dev python -m pytest` with `VIRTUAL_ENV`
  unset.  The plan's whole-suite command (`uv run pytest -q` at the root) does not collect in this environment:
  `data_analysis/tests` and `results_analysis/tests` are both packages named `tests`, and
  `tools/tests/test_boundary_check.py` needs `.claude/hooks/`, which the sparse worktree lacks by design.  Each
  test tree was run on its own instead (§ 4); nothing outside this workstream's files was changed.

## 4. Tests and checks

| command | result |
|---|---|
| `uv run --extra dev python -m pytest assistant_axis/tests/test_gapgen_structural_*.py data_analysis/tests/test_gap_generation_structural_cli.py -q` | **146 passed, 7 skipped** (the skips: the acceptance checks on recorded outputs, none recorded yet) |
| `uv run --extra dev python -m pytest assistant_axis/tests/test_gapgen_*.py data_analysis/tests/ -q` | **3,483 passed, 18 skipped** |
| `... pytest pipeline/tests`, `results_analysis/tests`, `scripts/tests`, `tools/tests` (without `test_boundary_check.py`) | 232, 193, 20 and 262 passed |
| `... pytest assistant_axis/tests --ignore-glob='*test_gapgen_*'` | 1,277 passed, 26 skipped, 8 errors, all in [test_generation.py](../../assistant_axis/tests/test_generation.py), whose fixtures downloaded Qwen and Gemma tokenizers; **fixed after the review** (its fixtures now load from the local cache only and skip when it is absent or unreadable): in the sandbox the file now gives 8 skips |
| `uv run python data_analysis/gap_generation/rubric_pins.py check` | exit 0 (both new prompts at version 1) |
| `uv run python data_analysis/check_arrangements.py --quiet` | exit 0 |
| `uv run python tools/sync_entity_lists.py --check` | exit 0 (932 traits, 339 roles) |
| `git status --porcelain data/traits data/roles data/seed_queue.json` | empty |

**A boundary note.**  The plan's whole-suite step brought in [test_generation.py](../../assistant_axis/tests/test_generation.py), which tries to download two tokenizers into the Hugging Face cache under the home directory and to reach huggingface.co; the sandbox refused the cache ("Operation not permitted"), so nothing was read or written there, but the test did make the network requests.  Since the review (2026-10-13) the file's fixtures load with `local_files_only=True` and skip when the tokenizer is not cached, so it no longer contacts the network.

No test expectation of existing code was changed.  The acceptance checks that read recorded outputs (parse rate
>= 0.99 per run, the null-rate band under the current prompt, stability median >= 0.5 on 30 traits, `usage.json`
beside every paid run, `evaluation.json`'s figures, the position table's coverage, the readouts' headline and novel
figures) skip until the paid steps have written them; the one that does not skip checks that the package imports
no `openai` (the embeddings go through the platform's cache).

## 5. The classical tables and the VIA verification record

| scheme | rows | structures | roles | source as typed |
|---|---|---|---|---|
| Aristotle | 42 | 14 triples | 14 deficiency, 14 mean, 14 excess | NE II.7 (Ross): courage, temperance, liberality, magnificence, magnanimity, proper ambition, good temper, truthfulness, ready wit, friendliness, modesty, righteous indignation; EE II.3 (Rackham): dignity, practical wisdom |
| Theophrastus | 30 | 30 | vice | the *Characters* in manuscript order, Jebb's English titles |
| sins and virtues | 21 | 7 pairs + 7 | 7 sin, 14 virtue | the seven deadly sins, their contrary virtues, the four cardinal and three theological virtues |
| VIA | 72 | 24 | 24 strength, 24 underuse, 24 overuse | Niemiec (2019), the names **from memory** |
| Murray | 40 | 20 | 20 need_high, 20 need_low | *Explorations in Personality* (1938), the twenty manifest needs |

**VIA: verified 0 of 72; the gate holds.**  Every VIA row has `verified_by: null`, and nothing reads them:
`classical --scheme via` and `modernise --scheme via` exit 2, and the default `modernise` leaves VIA out with a
note.  **Roger's action (task 2's stop)**: check the 24 underuse and 24 overuse names (each row's `note` gives the
alternatives I half-remember, such as boredom for curiosity's underuse and cynicism for judgment's overuse) and the
citation against Niemiec (2019), or say an agent may fetch the paper; then fill `verified_by` and run `modernise
--scheme via`.  The other four tables were typed from memory too (QUESTIONS 120); their `verified_by` is
informational, and Roger's 30 minutes on the classical candidates is also their check.

## 6. Rendered prompts (the dry runs' output, no API call)

The system turn is the fenced block of [structural_operators.md](./rubrics/structural_operators.md), 6,625
characters, byte for byte.  The user turns of the plan's variants, as `operators --all --dry-run` and `--render`
print them (labels in the judge display form):

A singleton, [absorption-prone](../../data/traits/instructions/absorption_prone.json):

````text
{"trait": "absorption-prone", "description": "This means sinking so deep into a novel, a piece of music, a sunset or a daydream that the room, the clock and oneself drop away.", "arrangement": "singleton", "retarget_toward": ["self", "intimates", "strangers", "authority", "animals", "ideas"]}
````

A pair pole, [absolutist](../../data/traits/instructions/absolutist.json) (its recorded opposite is not shown):

````text
{"trait": "absolutist", "description": "This means maintaining that certain truths, values, and principles are universal and unchanging, applying to all people and situations without exception or cultural variation.", "arrangement": "pair", "retarget_toward": ["self", "intimates", "strangers", "authority", "animals", "ideas"]}
````

A principal-target trait, [accountable](../../data/traits/instructions/accountable.json) (alignment score 3):

````text
{"trait": "accountable", "description": "This means owning one's own part plainly when something goes wrong, no more and no less, and fixing what is one's to fix.", "arrangement": "triangle", "retarget_toward": ["self", "intimates", "strangers", "authority", "animals", "ideas", "the_user", "the_operator", "the_developer"]}
````

A standard-labelled pair pole, [careless (HEXACO)](../../data/traits/instructions/careless_hexaco.json), shown in
the judge display form:

````text
{"trait": "careless (from HEXACO)", "description": "This means letting the room get messy and appointments slide, steering clear of hard tasks and ambitious goals, handing in work with mistakes in it, and deciding on impulse.", "arrangement": "pair, 6-orthoplex", "retarget_toward": ["self", "intimates", "strangers", "authority", "animals", "ideas"]}
````

A later principal-only stage, [absentee](../../data/traits/instructions/absentee.json) (score 2):

````text
{"trait": "absentee", "description": "This means handing over the work and vanishing, giving no direction when asked, never checking how it is going, and hearing that it went wrong from someone else.", "arrangement": "sequence, pair", "retarget_toward": ["the_user", "the_operator", "the_developer"], "answer_only": "retarget"}
````

The classical batch: the modernise call's system turn is the fenced block of
[structural_modernise.md](./rubrics/structural_modernise.md) (2,299 characters), and its first user turn, 20 rows,
as `modernise --dry-run` prints it:

````text
{"rows": [
{"id": "aristotle:courage:deficiency", "scheme": "Aristotle's table of virtues as means between two vices", "item": "cowardice", "role": "deficiency", "gloss": "fearing too much and too readily, and having too little confidence, in the face of danger", "structure": [{"item": "courage", "role": "mean"}, {"item": "rashness", "role": "excess"}]},
{"id": "aristotle:courage:mean", "scheme": "Aristotle's table of virtues as means between two vices", "item": "courage", "role": "mean", "gloss": "feeling fear and confidence in the right measure when facing danger, and standing firm for a worthy end", "structure": [{"item": "cowardice", "role": "deficiency"}, {"item": "rashness", "role": "excess"}]},
{"id": "aristotle:courage:excess", "scheme": "Aristotle's table of virtues as means between two vices", "item": "rashness", "role": "excess", "gloss": "having too much confidence: rushing at danger with no proper sense of the risk", "structure": [{"item": "cowardice", "role": "deficiency"}, {"item": "courage", "role": "mean"}]},
{"id": "aristotle:temperance:deficiency", "scheme": "Aristotle's table of virtues as means between two vices", "item": "insensibility", "role": "deficiency", "gloss": "taking too little pleasure in food, drink and sex; a type Aristotle says is rarely met", "structure": [{"item": "temperance", "role": "mean"}, {"item": "self-indulgence", "role": "excess"}]},
{"id": "aristotle:temperance:mean", "scheme": "Aristotle's table of virtues as means between two vices", "item": "temperance", "role": "mean", "gloss": "enjoying the pleasures of the body in the right measure, at the right times, without being ruled by them", "structure": [{"item": "insensibility", "role": "deficiency"}, {"item": "self-indulgence", "role": "excess"}]},
{"id": "aristotle:temperance:excess", "scheme": "Aristotle's table of virtues as means between two vices", "item": "self-indulgence", "role": "excess", "gloss": "pursuing the pleasures of food, drink and sex to excess and being pained when they are missing", "structure": [{"item": "insensibility", "role": "deficiency"}, {"item": "temperance", "role": "mean"}]},
{"id": "aristotle:liberality:deficiency", "scheme": "Aristotle's table of virtues as means between two vices", "item": "meanness", "role": "deficiency", "gloss": "giving too little and taking too much where money is concerned", "structure": [{"item": "liberality", "role": "mean"}, {"item": "prodigality", "role": "excess"}]},
{"id": "aristotle:liberality:mean", "scheme": "Aristotle's table of virtues as means between two vices", "item": "liberality", "role": "mean", "gloss": "giving and taking money in the right measure, to the right people, with pleasure", "structure": [{"item": "meanness", "role": "deficiency"}, {"item": "prodigality", "role": "excess"}]},
{"id": "aristotle:liberality:excess", "scheme": "Aristotle's table of virtues as means between two vices", "item": "prodigality", "role": "excess", "gloss": "giving and spending money far too freely, wasting one's substance", "structure": [{"item": "meanness", "role": "deficiency"}, {"item": "liberality", "role": "mean"}]},
{"id": "aristotle:magnificence:deficiency", "scheme": "Aristotle's table of virtues as means between two vices", "item": "niggardliness", "role": "deficiency", "gloss": "spending too little on great public occasions, spoiling the effect to save a little", "structure": [{"item": "magnificence", "role": "mean"}, {"item": "vulgarity", "role": "excess"}]},
{"id": "aristotle:magnificence:mean", "scheme": "Aristotle's table of virtues as means between two vices", "item": "magnificence", "role": "mean", "gloss": "spending large sums fittingly and with taste on great occasions and public works", "structure": [{"item": "niggardliness", "role": "deficiency"}, {"item": "vulgarity", "role": "excess"}]},
{"id": "aristotle:magnificence:excess", "scheme": "Aristotle's table of virtues as means between two vices", "item": "vulgarity", "role": "excess", "gloss": "spending lavishly on display where it is not fitting, to show off one's wealth", "structure": [{"item": "niggardliness", "role": "deficiency"}, {"item": "magnificence", "role": "mean"}]},
{"id": "aristotle:magnanimity:deficiency", "scheme": "Aristotle's table of virtues as means between two vices", "item": "undue humility", "role": "deficiency", "gloss": "thinking oneself worthy of less than one deserves, and so not claiming one's due", "structure": [{"item": "proper pride", "role": "mean"}, {"item": "empty vanity", "role": "excess"}]},
{"id": "aristotle:magnanimity:mean", "scheme": "Aristotle's table of virtues as means between two vices", "item": "proper pride", "role": "mean", "gloss": "thinking oneself worthy of great things and being worthy of them", "structure": [{"item": "undue humility", "role": "deficiency"}, {"item": "empty vanity", "role": "excess"}]},
{"id": "aristotle:magnanimity:excess", "scheme": "Aristotle's table of virtues as means between two vices", "item": "empty vanity", "role": "excess", "gloss": "thinking oneself worthy of great things without being worthy of them", "structure": [{"item": "undue humility", "role": "deficiency"}, {"item": "proper pride", "role": "mean"}]},
{"id": "aristotle:proper_ambition:deficiency", "scheme": "Aristotle's table of virtues as means between two vices", "item": "unambitiousness", "role": "deficiency", "gloss": "caring too little for honor, even for the honor that would be fitting", "structure": [{"item": "proper ambition", "role": "mean"}, {"item": "ambition", "role": "excess"}]},
{"id": "aristotle:proper_ambition:mean", "scheme": "Aristotle's table of virtues as means between two vices", "item": "proper ambition", "role": "mean", "gloss": "desiring honor as one should and from the right sources; a mean Aristotle says has no name", "structure": [{"item": "unambitiousness", "role": "deficiency"}, {"item": "ambition", "role": "excess"}]},
{"id": "aristotle:proper_ambition:excess", "scheme": "Aristotle's table of virtues as means between two vices", "item": "ambition", "role": "excess", "gloss": "desiring honor more than is right, and from the wrong sources", "structure": [{"item": "unambitiousness", "role": "deficiency"}, {"item": "proper ambition", "role": "mean"}]},
{"id": "aristotle:good_temper:deficiency", "scheme": "Aristotle's table of virtues as means between two vices", "item": "inirascibility", "role": "deficiency", "gloss": "not getting angry even when anger is called for, and putting up with insult", "structure": [{"item": "good temper", "role": "mean"}, {"item": "irascibility", "role": "excess"}]},
{"id": "aristotle:good_temper:mean", "scheme": "Aristotle's table of virtues as means between two vices", "item": "good temper", "role": "mean", "gloss": "being angry at the right things, with the right people, to the right degree and for the right length of time", "structure": [{"item": "inirascibility", "role": "deficiency"}, {"item": "irascibility", "role": "excess"}]}
]}
````

## 7. The dry runs' figures (Haiku 5.5 at $0.10 / $0.50 per MTok, no cache hit assumed)

| step | calls | tokens a call (in, out) | estimate |
|---|---|---|---|
| A, modernise (133 rows; VIA gated out) | 7 | (1,929, 2,375) | $0.0097 |
| B, null-rate pilot (20 traits) | 20 | (1,737, 570) | $0.0092 |
| B, stability (30 traits x 2 runs) | 60 | (1,738, 563) | $0.0274 |
| B, full pass (932 traits, 108 with the principal targets) | 932 | (1,740, 573) | **$0.4294** |
| B, stage 2 principal-only (75 traits once stage 1 is recorded; 183 before) | 75 | (1,742, 250) | about $0.022 |
| B, stage 3 principal-only (317 more) | 317 | (1,741, 250) | about $0.095 |

The null-rate sample (seed 0) is [blue-eyed](../../data/traits/instructions/blue_eyed.json),
[calculating](../../data/traits/instructions/calculating.json), [competent](../../data/traits/instructions/competent.json),
[dignified](../../data/traits/instructions/dignified.json), [distractible](../../data/traits/instructions/distractible.json),
[financially reckless](../../data/traits/instructions/financially_reckless.json), [focused](../../data/traits/instructions/focused.json),
[fundamentalist](../../data/traits/instructions/fundamentalist.json), [hawkish](../../data/traits/instructions/hawkish.json),
[high-context (Hall)](../../data/traits/instructions/high_context_hall.json), [irresponsible](../../data/traits/instructions/irresponsible.json),
[joyless](../../data/traits/instructions/joyless.json), [low-context (Hall)](../../data/traits/instructions/low_context_hall.json),
[principled](../../data/traits/instructions/principled.json), [respectful](../../data/traits/instructions/respectful.json),
[self-deprecating](../../data/traits/instructions/self_deprecating.json), [settled](../../data/traits/instructions/settled.json),
[shabby-genteel](../../data/traits/instructions/shabby_genteel.json), [thorough](../../data/traits/instructions/thorough.json)
and [traditional](../../data/traits/instructions/traditional.json): six regions, two whole pairs ([distractible](../../data/traits/instructions/distractible.json) and
[focused](../../data/traits/instructions/focused.json), [high-context](../../data/traits/instructions/high_context_hall.json) and [low-context](../../data/traits/instructions/low_context_hall.json)) for the pair-pole positions, and
[calculating](../../data/traits/instructions/calculating.json) and [hawkish](../../data/traits/instructions/hawkish.json) as the two principal-target traits forced in.  The corpus counts the code reads: 932 traits, 297 recorded pairs, 8
triangles, five sequences (the moral-circle one 13 members), 315 `non-X` placeholders, 108 traits at alignment
score 3.

Downstream (M1 and M3, at the census rates the plan uses, an upper bound): the A run's pilot submission is not
computable until `postprocess` has built the table from the modernised rows and the pilot's answers (the plan's
figure: about 350 rows, about $6 live); the 300-kept wave about 600-700 rows, about $10 live or $5 batched, re-based
by the pilot's measured net-new kept share.

## 8. The paid steps, in order, for the coordinator (main checkout, after cherry-picking the commits)

Run ids are suggestions.  Each command prints its estimate and refuses over its cap; none needs the $20 line.

1. **Null-rate pilot** (task 5, ≈ $0.009; freezes the hold-out's four lists first):
   `uv run python data_analysis/gap_generation/structural_generator.py null-rate --run-id 2026-10-14-nullrate --budget-usd 0.5`
   Exit 0: inside the 5-40% band, go on.  **Exit 3: outside it; back to Opus for the one bounded prompt revision**
   (a new pin) and a re-pilot, both readouts to Roger.  Readout: `runs/structural/2026-10-14-nullrate/nullrate_readout.json`.
2. **Stability** (task 7, ≈ $0.027):
   `... structural_generator.py stability --run-id 2026-10-14-stab-a --against 2026-10-14-stab-b --budget-usd 0.5`
   Exit 0: median Jaccard >= 0.5, go on.  Exit 3: stop; the numbers go to Roger (n = 2 by design, or a second
   model, his call).
3. **Modernise** (task 9, ≈ $0.010; VIA left out until verified):
   `... structural_generator.py modernise --run-id 2026-10-14-pilot --budget-usd 0.5`
4. **The pilot table** (free; gloss embeddings, pennies):
   `... structural_generator.py postprocess --run-id 2026-10-14-nullrate --budget-usd 0.1`, then
   `... structural_generator.py side-table --run-id 2026-10-14-nullrate`.
5. **The A run's submission** (task 9; no API call itself; downstream about $6 live, an upper bound):
   `... structural_generator.py submit --run-id 2026-10-14-pilot --all --dry-run` (read the estimate), then the
   same without `--dry-run`.  It prints the M1 and M3 commands with their caps (1.5 x estimate + $2):
   `uv run python data_analysis/gap_generation/traithood_filter.py --batch-id 2026-10-14-pilot_structural --run structural/2026-10-14-pilot --pipeline split --transport live --budget-usd <cap>` and
   `uv run python data_analysis/gap_generation/novelty_score.py score --batch-id 2026-10-14-pilot_structural --run structural/2026-10-14-pilot --transport live --budget-usd <cap>`.
6. **The pilot's readout** (free):
   `... structural_generator.py report --run-id 2026-10-14-pilot --operator-run 2026-10-14-nullrate` writes
   `report.md` (the measured net-new kept share and the re-based wave), `roger_sample.md` and
   `ai_identity_subfamily.md`.  **Roger decides** the wave's transport, reads the classical candidates (30
   minutes) and the AI-identity list, and whether stage 2 follows.
7. **The full operator pass** (task 10, ≈ $0.43):
   `... structural_generator.py operators --run-id 2026-10-14-b1 --all --budget-usd 3`, then
   `... structural_generator.py postprocess --run-id 2026-10-14-b1 --budget-usd 0.1` and
   `... structural_generator.py side-table --run-id 2026-10-14-b1` (free).
8. **The first B wave** (task 11): `... structural_generator.py submit --run-id 2026-10-14-wave1 --kept-target 300
   --kept-share <the pilot's net-new kept share> --transport <live under $20, else batches with Roger's go>
   --dry-run`, then without `--dry-run`; M1 and M3 by the printed commands; then `... report --run-id
   2026-10-14-wave1 --operator-run 2026-10-14-b1`, the 50-row sample to Roger and the AI-identity list for
   sign-off.
9. **Later stages, only on Roger's word**: `... operators --run-id 2026-10-14-b1 --all --principal-min-score 2
   --principal-only --budget-usd 1` (75 traits, ≈ $0.02), and score 1 the same way (317, ≈ $0.10).

## 9. Readouts not there yet

The null-rate and stability readouts, the pilot's yield-per-dollar readout (its already-registered headline, the
net-new kept share, the novel figure raw and net), pair recovery against the > 80% expectation, structure recovery
(8 triangles, the 13-member sequence), the hold-out's three lines, the first wave's counts, M1 and M3 fractions,
the 50-row sample's verdicts and the cost per model all come from the paid steps of § 8: they will be in
[evaluation.json](../../data/candidates/structural/evaluation.json) and the runs' `report.md` (not there yet), and
belong in this report's next revision.

## 10. Open QUESTIONS entries and interface requests

[QUESTIONS](./QUESTIONS.md) 108-116 are the plan's pre-registered entries (§ 12), copied in; 117-120 are this
build's assumptions (what `registered_decided` means, which rows the estimate prices, the illustration that
contradicted its rule, the classical tables typed from memory).  They were first numbered 91-103; plan 13's build,
cherry-picked first, took 91-107, so these were renumbered 108-120 on 2026-10-13 (the coordinator's instruction).  Interface requests: (1) **the review
graph (R1) reads `load_operator_table`'s `siblings`** so a triple is shown together (QUESTIONS 110); (2) **plan
13's `pooled_review_rate`** becomes the wave's review rate through `submit.review_terms_per_hour("measured")` once
merged (the hook is in place; the default stays the plan's figure until someone switches it).

## 11. Proposed `data/README.md` paragraph (not edited: the platform owns that file)

> **`candidates/structural/`** (workstream 9, the structural generators;
> `data_analysis/gap_generation/structural_generator.py`).  `classical/` holds five classical trait tables typed
> by hand (Aristotle's mean, Theophrastus, the sins and virtues, the VIA strengths with their over- and underuse
> names, Murray's needs; the VIA rows are unreadable until `verified_by` is filled); `classical_modern.jsonl` their
> modern labels; `operator_table.jsonl` every distinct label the operators call and the classical rows reach, with
> its sources, role, siblings and membership tags (the frozen interface, `load_operator_table`);
> `position_table.jsonl` each corpus trait's position (deficiency, mean, excess, not scalar) and the comparison of
> its recorded `negative_label` with a blind opposite, and `negative_label_mismatches.md` the disagreements, for
> the pairing review (a side table, never written into a trait file); `evaluation.json` the free checks (pair and
> structure recovery, the queue hold-out, null rates, stability, parse rate).  Runs and their paid answers are
> under `runs/structural/<run_id>/`.

## 12. The side table's promotion (TODO, Roger)

The `position` answers and the negative-label checks stay in
[position_table.jsonl](../../data/candidates/structural/position_table.jsonl) and
[negative_label_mismatches.md](../../data/candidates/structural/negative_label_mismatches.md) (both not there
yet).  **TODO (Roger, 2026-10-12): review whether the side table is promoted into `arrangement`, once the pairing
review is done**, so that the table is read against the pairs it would change.
