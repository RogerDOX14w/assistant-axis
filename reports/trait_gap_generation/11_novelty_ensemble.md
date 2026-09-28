# 11. Novelty ensemble: independent signals and the disagreement protocol

## 1. Idea

Split "do we already have something close?" into two questions that fail for different reasons: **proximity** (is any existing trait in the same region?) and **relation type** (given the nearest ones, is the candidate a synonym, antonym, narrower, broader, or distinct?). Answer each with three cheap signals whose error modes are uncorrelated with the dense-embedding nearest neighbour (workstream 10): a lexical graph, a masked-LM fit test against the existing *descriptions*, and morphology. Where the signals agree the verdict is taken; only disagreements go to an LLM, and it sees only the top-5 neighbours the cheap signals turned up. Nothing here is trained on our list, so a candidate is never penalised or rewarded for resembling what we already generated.

## 2. Sources and tools

| Signal | Source | Availability / licence / format |
|---|---|---|
| S2 lexical graph | Open English WordNet 2025 via `pip install wn` (synonym, antonym, hypernym, "similar to") | CC-BY 4.0, ~100 MB SQLite after `wn.download("oewn:2025+")`. Not installed (nor nltk). Verified. |
| S2 supplement | ConceptNet 5.7 assertions (`Synonym`, `Antonym`, `DistinctFrom`, `SimilarTo`), Moby Thesaurus II | CC-BY-SA 4.0 gz TSV (~10 GB raw; filter to `/c/en/`); Moby public domain, Gutenberg #3202, flat `head,syn,syn,...`. Verified. Multiword coverage in both is poor (unverified how poor for our labels). |
| S3 masked-LM fit | `roberta-large` (or `bert-large-uncased-whole-word-masking`) through `transformers` 5.1 + torch 2.10, already installed | Apache/MIT weights, ~1.4 GB, runs on the Mac. |
| S4 morphology | pure-Python stem + affix rules; optional Snowball stemmer (`nltk` or `snowballstemmer`, BSD) | no download. |
| S5 second embedding family | static GloVe 6B-300d word vectors (PDDL, ~800 MB zip) *or* OpenAI `text-embedding-3-large` if workstream 10 goes local (and vice versa) | GloVe verified PDDL. OpenAI embedding pricing not re-verified here; workstream 10 owns it. |
| LLM adjudicator | `claude-haiku-4-5` ($1/$5 per MTok) default; `claude-sonnet-5` ($2/$10) for the audit sample. Batch API is 50% off; a cached system prompt cuts input further. | Pricing checked 2026-09-18. |

## 3. Method

1. **Candidate record** (from the registry): `label`, one-line `gloss`, optional intended sense. Existing side: 385 trait `label` + `description` + `negative_label` + `arrangement`.
2. **Neighbour set N.** Union of the top-5 from S1 (dense, workstream 10) and S5, plus every existing trait reachable in ≤2 lexical hops from the label (S2). Typically 6-12 traits; everything downstream is scored only on N.
3. **S3a, description fit.** For each T in N, mask the label in T's own description frame, `This means being [MASK]: <rest>`, and score the candidate label by pseudo-log-likelihood (sum of per-subtoken masked log-probs, so multiword labels work). Normalise against the label's PLL in a neutral frame. Also run the reverse direction (T's label in the candidate's gloss frame). High fit in both directions = same scope; high one way only = narrower/broader.
4. **S3b, antonym probe.** Frames such as `Being <cand> is the opposite of being [MASK]` and `not <cand> but [MASK]`; record the rank of each T's label and negative_label. Independent of the lexical graph, but noisy alone.
5. **S2 relations.** For each (cand, T): synonym-set overlap, direct antonym link (also to T's `negative_label`), hypernym path direction, ConceptNet `DistinctFrom`. Absent = no vote, not "distinct".
6. **S4 morphology.** Shared stem with a negation affix (un-, in-/im-/il-/ir-, non-, dis-, a-, -less/-ful) votes antonym; shared stem without one (literal/literalist) votes synonym; no shared stem = no vote.
7. **Thresholds** for each signal are fitted once on the calibration set (§6), giving each signal a three-way vote per pair: same / opposite / abstain, plus a proximity bin near / far.
8. **Agreement rules** (per candidate, over N):
   - **NOVEL**: S1 and S5 both below their far thresholds, no S2 link, S3a fit low everywhere. Accepted without LLM.
   - **DUPLICATE of T**: S1 and S5 agree on T as top-1, S3a fits both ways, no signal votes opposite. Accepted, but tagged `gloss-check` if the gloss shares no content word with T's description (the cautious/risk-averse lesson).
   - **PAIR with T**: at least two of {S2 antonym, S3b, S4} vote opposite and proximity is near. Accepted; also records whether T is currently a singleton (a completion) or already paired (a triangle candidate).
   - **LLM**: everything else, including any syn/ant split, a near candidate with no relation vote, or a multiword label S2 and S4 abstained on.
9. **LLM adjudication.** One call per candidate: label, gloss, and N with descriptions; asks for a relation per neighbour (synonym / antonym / narrower / broader / distinct / different-sense-of-the-word) and a one-line reason, JSON output. The last class is how polysemy is flagged. Verdicts and every signal's vote are written to the registry with `usage.json` (MultiModelUsage) beside them.

## 4. Expected yield and biases

Hand estimate from the log: about 55-65% of candidates should resolve without the LLM (most NOVEL and clean DUPLICATE cases), 35-45% go to adjudication; a 500-candidate pilot measures this before the full run. Over-produces: PAIR flags for negation-prefix words that are not real trait opposites (non-X, unhelpful), DUPLICATE flags for dictionary synonyms that our descriptions keep distinct. Under-produces: S2 and S4 abstain on multiword labels ("kind to animals"), so those lean on S3a and the LLM; S3 is weak on rare words the 32B generator would not know anyway (a useful coincidence).

## 5. Cost

LLM: 4,000 calls × ~700 input + 150 output tokens on Haiku 4.5 ≈ $5.8 (batch: $2.9); worst case all 10,000 on Sonnet 5 ≈ $29 (batch $14.5), so the standard run stays under $10. Audit sample of 200 on Sonnet 5 ≈ $0.50. Local: S3 is ~250k short forward passes (10k × ~12 neighbours × 2 directions) ≈ 1-2 h on the Mac; S2/S4/S5 are seconds once loaded. Downloads ~2.5 GB. Roger: 30 min confirming the calibration labels, 1 h reviewing the pilot's disagreement cases.

## 6. Testing

- **Calibration set** from `reports/seeding_log_2026-09.md`: ~55 confirmed antonym pairs (agitated/calm, orthodox/heterodox, sloppy/meticulous, overconfident/calibrated, ...), ~20 duplicates (grave/solemn, measured/understated, modern/contemporary, hopeful/optimistic, undiplomatic/blunt, epistemically_humble/calibrated, nonchalant/unflappable, lazy/slothful, applied/practical, balanced/moderate, consequentialist/utilitarian), ~20 near-but-distinct (dignified/goofy, stoic/reactive, expository/informational, educational/superficial, subversive/orthodox, diplomatic/partisan, cautious/risk_averse/bold), ~8 narrower/broader (literalist vs deconstructionist, intemperate vs stoic, cultural_relativist vs relativist), ~8 polysemy rejects (disciplinary, engaging, economic, balanced, empowered, meaningful, iconodule, ingenuous), plus 60 random far pairs. Report per-signal and ensemble confusion matrices; the syn-vs-ant confusion is the number that matters.
- **Hidden-partner recovery**: hide each of the 244 paired traits in turn, present its label+description as a candidate; the ensemble should return PAIR pointing at its partner. Hide each of the 20 deleted duplicates; expect DUPLICATE.
- **Auto-accept audit**: 200 auto-resolved verdicts re-judged by Sonnet 5 (and 50 by Roger); the error rate sets whether the agreement rules tighten.

## 7. Dependencies

Needs: the registry record format and S1 top-5 from workstream 10; the trait-hood filter runs *before* this (no point adjudicating non-traits). Provides: per-candidate verdict, neighbour list, relation votes, the calibration set (reusable by any scorer), and the polysemy flag from the LLM step.

## 8. Variants

**A (recommended)**: as above, description-fit MLM against N only. **B**: replace S3 with a second contextual sentence-embedding model and rely on S2+S4 alone for relation type; cheaper to build, but then all proximity signals share the "antonyms embed close" failure and more cases reach the LLM.

## 9. Open questions for Roger

1. Is a dictionary synonym with a plausibly different scope (applied/practical) a DUPLICATE to auto-accept, or always an LLM case? The rule in step 8 tags it; you choose whether the tag blocks.
2. Haiku 4.5 as adjudicator with a Sonnet audit, or Sonnet 5 throughout (~2.5× cost, still under $15 with batch)?
3. Should PAIR verdicts against an already-paired trait be surfaced (triangles) or dropped?
4. Approve the ~2.5 GB of downloads (OEWN, GloVe, roberta-large) and `pip install wn` into the uv environment.

## Addendum (2026-09-18)

Plan 10 now emits two scores, local (corrected nearest-neighbour cosine
after centering) and directional (residual outside the existing traits'
principal subspace).  Treat them as two ensemble signals: they fail
differently (a blend of existing traits scores novel locally but not
directionally; a near-antonym scores covered locally but may score novel
directionally if the pair's axis is under-represented), and their
disagreement is one of the cases to route to the LLM.  See plan 15 for the
calibration that decides their weights.
