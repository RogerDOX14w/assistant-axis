# 09 Structural generators: classical schemes and operators on our own traits

## 1. Idea

Two generators, one pipeline. (A) Transcribe five classical trait schemes that were fixed long before our list existed (Aristotle's mean table, Theophrastus' 30 Characters, the seven sins and virtues, VIA's 24 strengths with their over/underuse forms, Murray's needs) and modernise each entry with a cheap model. (B) Apply five structural operators (opposite, excess, deficiency, retarget, remode) to each of our 385 trait files. B is derived from our list, but the operators move to a *different position in a structure* (the third pole of a triple, the same disposition aimed at a new target), so its output is not a synonym of its input. Both generators emit structural metadata (role, siblings), which is what lets the novelty scorer tell a pair completion from a duplicate and tells the arrangement-hunting TODO when a recorded pair is really a `sequence`.

## 2. Sources and tools

| Source | Size | Availability / licence | Notes |
|---|---|---|---|
| Aristotle, NE II.7 (+ EE II.3) mean table | 12-14 triples (deficiency / mean / excess) | public domain (Ross translation) | hand-typed into a small JSON; needs modern glosses (Greek terms such as *megaloprepeia* have no plain English word) |
| Theophrastus, *Characters* | 30 sketches | public domain (Jebb 1870) | titles + one-line gloss; all are vices, all social |
| Seven sins / seven virtues + cardinal and theological virtues | 7 + 7 + 7 | common knowledge | ~half already in the corpus (envious, gluttonous, lustful, greedy, humble, patient, generous) |
| VIA 24 strengths with Niemiec's overuse / underuse names (2019) | 24 × 3 = 72 | the *names* are freely published; the survey is copyrighted (not needed) | prosocial strengths already scanned (TRAITS_TO_ADD line 1657); the over/under structure was not. Verify the over/under names against the paper before use; I could not check them here |
| Murray (1938) psychogenic needs | 20 core (abasement ... understanding); PRF/EPPS variants add ~7 | list not copyrightable | each need gives a high and a low pole ("need for order" -> orderly / disorderly) |
| Our corpus | 385 files, `negative_label`, `arrangement`; seed queue 972 entries / 867 labels; `trait_antonyms_v4.json` | in repo | inputs for B and the exists/queued registry |
| Cheap model | Haiku 4.5 ($1 / $5 per MTok) or GPT-4.1-mini | both clients installed; use `call_judge_single_unified` + `MultiModelUsage` (hard rule) | prompt caching on the fixed system prompt |

## 3. Method

**A. Classical schemes (~205 rows, no enumeration LLM needed).**
1. Hand-type the five tables as JSON rows: `scheme, item, role (deficiency|mean|excess|sin|virtue|strength|underuse|overuse|need_high|need_low), gloss, sibling_ids`.
2. Modernise with the cheap model, 20 rows per call: for each row return 1-3 modern labels a 32B model knows (multiword allowed), a "This means being X: ..." gloss of at most 25 words, a polysemy flag, and one-sentence reasoning first. Aristotle's *pusillanimous* becomes "self-effacing"; Theophrastus' "petty ambition" becomes "status-seeking".
3. Emit to the registry with the structural payload intact. Rule for the scorer: when two poles of an Aristotelian triple land on an existing pair (e.g. cowardly?/cautious/bold/rash), the pair is a `sequence` with a missing pole, and the missing pole is the gap.

**B. Operators on our traits (385 calls, or ~130 pair calls + ~120 singleton calls, see Variants).**
4. Input per trait: label, description, `negative_label`, arrangement kind. One JSON response per trait with, reasoning field first:
   - `position`: is the trait as described a deficiency, a mean, an excess, or not scalar (worldviews such as deontological, structuralist are not).
   - `opposite`: the antonym. Run even where a partner is recorded; disagreement with the recorded `negative_label` is a free "mismatch" signal for the pairing review.
   - `excess` / `deficiency`: the vice this becomes with too much / too little (cautious -> paralysed / reckless; honest -> tactless / evasive). Reject labels of the form over-/under-/too-/non-X.
   - `retarget`: for each of self, intimates, strangers, authority, animals, ideas: a *named* stable disposition with that target, or null. Null must be the expected majority (harsh -> self-critical is real; "kind to animals toward ideas" is not).
   - `remode`: attitude, habit, speech forms, or null (arrogant -> speech: boastful; cautious -> speech: hedging).
   Every item carries label, gloss, `has_common_word` (single word vs phrase only), polysemy flag.
5. Prompt: fixed system prompt (corpus definition of a trait, "the vice is a vice", inside-voice, words a 32B model knows, null-is-expected), three worked examples, the JSON schema with reasoning first. About 1,200 input tokens (900 cached), 400-700 output.
6. Local post-processing, no API: normalise labels to stems (lowercase, hyphen/space, nominal -> adjective); tag `exists` / `queued` against the 385 stems, their `negative_label`s and the 867 queue labels (keep, do not drop: an existing trait reached as another's `excess` is arrangement evidence); merge duplicates across source traits, keeping the provenance list (tactless will arrive from honest, blunt and candid; the multiplicity is a quality signal); hand the merged set to the shared novelty scorer, which returns duplicate_of / antonym_of / near / novel.
7. Write one JSONL per run (label, gloss, generator, scheme or operator, source, role, siblings, n_sources, flags, model) plus `usage.json`.

## 4. Expected yield and biases

A: ~205 rows -> ~250 labels; roughly 40% exists/queued, 40% near, 40-60 novel. B: 385 × ~5.5 applicable cells ≈ 2,100 raw -> ~900 distinct labels after merge -> ~600 not exists/queued -> 150-300 novel after scoring. Over-produces: vice-side excess forms and near-synonym clusters (dedup's job), phrase-only "X toward Y" labels, and the virtue/vice moral register (the classical schemes are Greek and Christian ethics; light on cognitive style and the alignment region, which is the intended complement). Under-produces: non-scalar traits, and anything two structural steps from what we have.

## 5. Cost

A: ~12 calls, under $0.10. B: 385 calls × (~$0.0007 in + ~$0.003 out) ≈ $1.50 on Haiku 4.5 per pass; a second pass at a different seed or on GPT-4.1-mini doubles it. Total under $5; scorer verification calls belong to that workstream's budget. Local: embedding ~1,000 glosses, seconds on the Mac. Roger: 30 minutes on the classical tables once; 1-2 hours on the 200-350 novel candidates, reviewed grouped by triple so siblings are judged together.

## 6. Testing

1. **Pair recovery**: hide one pole of each of the ~260 clean pairs; `opposite` should recover it (stem match or gloss cosine above threshold). Expect >80%; this mostly re-tests `generate_antonyms`, so the informative number is the next one.
2. **Structure recovery**: hide one member of each known triangle and of the 16-member moral-circle sequence; check whether `excess`/`deficiency`/`retarget` on the neighbours recover it. Small N, spot checks.
3. **Queue hold-out**: the ~480 queued-but-unfiled labels came from taxonomy scans and audits, not from this generator; recall of those from the 385 filed traits, by operator, is the real test. Tier D pair completions should score well.
4. **Precision**: 50 novel candidates judged trait / not-trait / duplicate by Roger or the trait-hood judge; target ≥70% trait-and-new.
5. **Null-rate pilot**: 20 traits first; retarget/remode non-null above 40% means hallucinated forms, below 5% means laziness.
6. **Stability**: 30 traits run twice, label-set Jaccard ≥0.5, else sample n=2 by design. Parse rate ≥99%, `usage.json` written.

## 7. Dependencies

Needs: the candidate registry format; the trait-hood filter; the novelty scorer, which must consume the `role` field so that `opposite` items are scored as pair completions, not duplicates. Provides: candidates with role and siblings; a `position` (deficiency/mean/excess) annotation for every existing trait and a list of recorded-`negative_label` disagreements, both feeding TRAITS_TO_ADD § arrangement hunting and the pairing review.

## 8. Variants

- **Per-trait call** (above) vs **per-operator batched call** (20 traits, one operator): batching calibrates "excess" uniformly across traits and saves prompt tokens, but risks positional laziness. Suggested: batched for retarget/remode, per-trait for the rest.
- **Pair-level call**: give both poles of a clean pair, ask for the deficiency/mean/excess sequence and where each pole sits (~130 calls). Produces `sequence` proposals directly; recommended for pairs, per-trait for singletons.
- **Classical tables**: hand-typed (faithful, 30 min) vs recited by a strong model (cheap in Roger time, recall risk on Theophrastus and the VIA over/under names).

## 9. Open questions for Roger

1. Phrase-only labels ("harsh toward self") when no single word exists: accepted, given `kind to animals`, or only with a common word?
2. Retarget list: add "toward the user / the operator / the developer" for the alignment region (sycophantic toward the user vs the principal)?
3. Should `position` annotations be written into existing files' `arrangement` or kept as a side table until confirmed?
4. One cheap model or two (Haiku 4.5 plus GPT-4.1-mini) for agreement-based filtering?
5. Is the VIA over/under pass worth including, given the prosocial VIA scan already done?
