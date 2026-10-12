# 09 Structural generators: classical schemes and operators on our own traits

Updated 2026-10-12: counts and prices refreshed to the corpus and the code as they stand, and Roger's answers to the
open questions (§ 9) incorporated.  Yields and costs below are scaled from the 2026-10-08 figures by the corpus's
growth (932 trait files against 385) and are to be re-measured at the null-rate pilot (§ 6.5).  **Greenlit for detailed planning by Roger on 2026-10-12**; the coding plan is [coding_plan_09_structural_generators.md](./coding_plan_09_structural_generators.md) (being written).

## 1. Idea

Two generators, one pipeline. (A) Transcribe five classical trait schemes that were fixed long before our list existed (Aristotle's mean table, Theophrastus' 30 Characters, the seven sins and virtues, VIA's 24 strengths with their over/underuse forms, Murray's needs) and modernise each entry with a cheap model. (B) Apply five structural operators (opposite, excess, deficiency, retarget, remode) to each of our 932 trait files. B is derived from our list, but the operators move to a *different position in a structure* (the third pole of a triple, the same disposition aimed at a new target), so its output is not a synonym of its input. Both generators emit structural metadata (role, siblings), which is what lets the novelty scorer tell a pair completion from a duplicate and tells the arrangement-hunting TODO when a recorded pair is really a `sequence`.

## 2. Sources and tools

| Source | Size | Availability / licence | Notes |
|---|---|---|---|
| Aristotle, NE II.7 (+ EE II.3) mean table | 12-14 triples (deficiency / mean / excess) | public domain (Ross translation) | hand-typed into a small JSON; needs modern glosses (Greek terms such as *megaloprepeia* have no plain English word) |
| Theophrastus, *Characters* | 30 sketches | public domain (Jebb 1870) | titles + one-line gloss; all are vices, all social |
| Seven sins / seven virtues + cardinal and theological virtues | 7 + 7 + 7 | common knowledge | ~half already in the corpus (envious, gluttonous, lustful, greedy, humble, patient, generous) |
| VIA 24 strengths with Niemiec's overuse / underuse names (2019) | 24 × 3 = 72 | the *names* are freely published; the survey is copyrighted (not needed) | prosocial strengths already scanned (the [holding lists](../../data/traits/instructions/TRAITS_TO_ADD.md), line 1657); the over/under structure was not. **Included (Roger, 2026-10-12), gated on verifying the over/under names against the paper before the A run**; I could not check them here |
| Murray (1938) psychogenic needs | 20 core (abasement ... understanding); PRF/EPPS variants add ~7 | list not copyrightable | each need gives a high and a low pole ("need for order" -> orderly / disorderly) |
| Our corpus | 932 files (2026-10-12), `negative_label`, `arrangement`; [seed queue](../../data/seed_queue.json) 1,047 entries, of which 969 are trait entries and 963 distinct labels; 119 trait entries live (`backlog` and `candidate`); `trait_antonyms_v4.json` | in repo | inputs for B and the exists/queued registry |
| Cheap model | **Haiku 5.5** at $0.10 / $0.50 per MTok, the rate in [judge_pricing.py](../../assistant_axis/judge_pricing.py) (Haiku 4.5 was $1 / $5) | use `call_judge_single_unified` + `MultiModelUsage` (hard rule) | prompt caching on the fixed system prompt; one model (Roger, 2026-10-12) |

## 3. Method

**A. Classical schemes (~205 rows, no enumeration LLM needed).**
1. Hand-type the five tables as JSON rows: `scheme, item, role (deficiency|mean|excess|sin|virtue|strength|underuse|overuse|need_high|need_low), gloss, sibling_ids`. The VIA over- and underuse rows are in; their names are checked against the paper before this step is used (§ 2).
2. Modernise with Haiku 5.5, 20 rows per call: for each row return 1-3 modern labels a 32B model knows (multiword allowed), a "This means being X: ..." gloss of at most 25 words, a polysemy flag, and one-sentence reasoning first. Aristotle's *pusillanimous* becomes "self-effacing"; Theophrastus' "petty ambition" becomes "status-seeking".
3. Emit to the registry with the structural payload intact. Rule for the scorer: when two poles of an Aristotelian triple land on an existing pair (e.g. cowardly?/cautious/bold/rash), the pair is a `sequence` with a missing pole, and the missing pole is the gap.

**B. Operators on our traits (932 calls, or about 320 pair calls + 290 singleton calls, see Variants).**
4. Input per trait: label, description, `negative_label`, arrangement kind. One JSON response per trait with, reasoning field first:
   - `position`: is the trait as described a deficiency, a mean, an excess, or not scalar (worldviews such as deontological, structuralist are not). Written to a side table, not to `arrangement` (§ 9, question 3).
   - `opposite`: the antonym. Run even where a partner is recorded; disagreement with the recorded `negative_label` is a free "mismatch" signal for the pairing review.
   - `excess` / `deficiency`: the vice this becomes with too much / too little (cautious -> paralysed / reckless; honest -> tactless / evasive). Reject labels of the form over-/under-/too-/non-X.
   - `retarget`: for each of self, intimates, strangers, authority, animals, ideas: a *named* stable disposition with that target, or null. Null must be the expected majority (harsh -> self-critical is real; "kind to animals toward ideas" is not). **For the traits in the alignment region, three principal targets are added: the user, the operator, the developer** (Roger, 2026-10-12: yes, for the alignment region). These presuppose an AI assistant, so their non-null outputs go to the AI-identity sub-family list ([QUESTIONS](./QUESTIONS.md) 67 and 78) for sign-off before promotion. The corpus has 10 alignment-region traits, so this is a small run.
   - `remode`: attitude, habit, speech forms, or null (arrogant -> speech: boastful; cautious -> speech: hedging).
   Every item carries label, gloss, `has_common_word` (single word vs phrase only, kept as information, not a filter: phrase-only labels are accepted, Roger 2026-10-12), polysemy flag.
5. Prompt: fixed system prompt (corpus definition of a trait, "the vice is a vice", inside-voice, words a 32B model knows, null-is-expected), three worked examples, the JSON schema with reasoning first. About 1,200 input tokens (900 cached), 400-700 output.
6. Local post-processing, no API: normalise labels to stems (lowercase, hyphen/space, nominal -> adjective); tag `exists` / `queued` against the 932 stems, their `negative_label`s and the labels of the 1,047 seed-queue entries (keep, do not drop: an existing trait reached as another's `excess` is arrangement evidence); merge duplicates across source traits, keeping the provenance list (tactless will arrive from honest, blunt and candid; the multiplicity is a quality signal); hand the merged set to the shared novelty scorer, which returns duplicate_of / antonym_of / near / novel.
7. Write one JSONL per run (label, gloss, generator, scheme or operator, source, role, siblings, n_sources, flags, model) plus `usage.json`.

## 4. Expected yield and biases

A: ~205 rows -> ~250 labels; roughly 40% exists/queued, 40% near, 40-60 novel (unchanged: the classical tables do not depend on the corpus's size).

B, scaled from the 385-file figures by 932/385 (about 2.4×; to be re-measured): 932 × ~5.5 applicable cells ≈ 5,100 raw -> ~2,200 distinct labels after merge -> ~1,450 not exists/queued -> **360-730 novel after scoring**. Over-produces: vice-side excess forms and near-synonym clusters (dedup's job), phrase-only "X toward Y" labels, and the virtue/vice moral register (the classical schemes are Greek and Christian ethics; light on cognitive style and the alignment region, which is the intended complement). Under-produces: non-scalar traits, and anything two structural steps from what we have.

## 5. Cost

A: ~12 calls, about $0.10 or less. B: 932 calls at about $0.0004 each on Haiku 5.5 ($0.10 / $0.50 per MTok, the plan's token figures), so **about $0.37 per pass**. The 2026-10-08 figure of $1.50 for 385 calls was at Haiku 4.5's $1 / $5 rates. The GPT-4.1-mini second pass is dropped (Roger, 2026-10-12: one model). Total well under $5; scorer verification calls belong to that workstream's budget. Local: embedding ~1,000 glosses, seconds on the Mac.

Review is the real cost. At the measured ~150 terms an hour, the 360-730 novel candidates are **2.5-5 hours**, against the 1-2 hours the 2026-10-08 plan assumed for 200-350. **Proposal, not yet Roger's decision:** size the B wave by review hours, as [plan 04](./04_masked_lm_fill.md) is sized (about two hours, roughly 300 kept terms), cutting by the scorer's novelty and reviewing grouped by triple so siblings are judged together; the whole-corpus run would then be a second wave, not the first. Roger: 30 minutes on the classical tables once.

## 6. Testing

1. **Pair recovery**: hide one pole of each of the ~260 clean pairs; `opposite` should recover it (stem match or gloss cosine above threshold). Expect >80%; this mostly re-tests `generate_antonyms`, so the informative number is the next one.
2. **Structure recovery**: hide one member of each known triangle and of the 16-member moral-circle sequence; check whether `excess`/`deficiency`/`retarget` on the neighbours recover it. Small N, spot checks.
3. **Queue hold-out**: the **96 queued-but-unfiled labels from taxonomy scans and audits** (84 `backlog` and 12 `paired` entries, counted 2026-10-12; the 2026-10-08 figure of ~480 is stale, since most of those have been filed). The 35 `candidate` entries promoted from the census review on 2026-10-11 are left out: they came from a generator. Recall of the 96 from the 932 filed traits, by operator, is the real test. Tier D pair completions should score well.
4. **Precision**: 50 novel candidates judged trait / not-trait / duplicate by Roger or the trait-hood judge; target ≥70% trait-and-new.
5. **Null-rate pilot**: 20 traits first; retarget/remode non-null above 40% means hallucinated forms, below 5% means laziness. This pilot, with item 6, is the tested decision that Haiku 5.5 is the model for this use; a second model is added only if item 6 fails (Roger, 2026-10-12).
6. **Stability**: 30 traits run twice, label-set Jaccard ≥0.5, else sample n=2 by design. Parse rate ≥99%, `usage.json` written.

## 7. Dependencies

Needs: the candidate registry format; the trait-hood filter; the novelty scorer, which must consume the `role` field so that `opposite` items are scored as pair completions, not duplicates. Provides: candidates with role and siblings; a `position` (deficiency/mean/excess) annotation for every existing trait, held in a side table under `data/candidates/structural/` and not in the checked-in corpus (Roger, 2026-10-12: side table until confirmed); and a list of recorded-`negative_label` disagreements, both feeding the [holding lists](../../data/traits/instructions/TRAITS_TO_ADD.md) (arrangement hunting) and the pairing review.

**TODO (Roger, 2026-10-12): review whether the side table is promoted into `arrangement`.** Trigger: when the pairing review is done, so that the table has been read against the pairs it would change.

## 8. Variants

- **Per-trait call** (above) vs **per-operator batched call** (20 traits, one operator): batching calibrates "excess" uniformly across traits and saves prompt tokens, but risks positional laziness. Suggested: batched for retarget/remode, per-trait for the rest.
- **Pair-level call**: give both poles of a clean pair, ask for the deficiency/mean/excess sequence and where each pole sits (about 320 calls at 932 traits). Produces `sequence` proposals directly; recommended for pairs, per-trait for singletons.
- **Classical tables**: hand-typed (faithful, 30 min) vs recited by a strong model (cheap in Roger time, recall risk on Theophrastus and the VIA over/under names).

## 9. Open questions for Roger (answered 2026-10-12)

1. Phrase-only labels ("harsh toward self") when no single word exists: accepted, given `kind to animals`, or only with a common word?

   **Roger: accepted.**  Phrase-only labels are kept (§ 3, item 4); `has_common_word` is information, not a filter.
2. Retarget list: add "toward the user / the operator / the developer" for the alignment region (sycophantic toward the user vs the principal)?

   **Roger: yes.**  Added for the alignment region only (§ 3, item 4); outputs that name a principal go to the AI-identity sub-family list for sign-off before promotion.
3. Should `position` annotations be written into existing files' `arrangement` or kept as a side table until confirmed?

   **Roger: side table, with a TODO to review.**  § 7 holds the table and the TODO and its trigger.
4. One cheap model or two (Haiku 4.5 plus GPT-4.1-mini) for agreement-based filtering?

   **Roger: Haiku 5.5.**  One model, priced at its current rate (§ 2, § 5); a second model only if the stability test fails (§ 6.6).
5. Is the VIA over/under pass worth including, given the prosocial VIA scan already done?

   **Roger: yes.**  Included in A (§ 3, item 1), with the names verified before use (§ 2).  The scan covered the strengths and not their over- and underuse forms, so it is not a duplicate of work already done.

## Status (2026-10-12)

Answers to the five questions recorded; counts, prices and the Haiku 5.5 decision brought up to date; the review cost added to § 5 with the wave sized by review hours as a proposal (still open).  **Greenlit for detailed planning, 2026-10-12** (Roger: "09 is now greenlit, start plan writing on it"); the coding plan is in progress.
