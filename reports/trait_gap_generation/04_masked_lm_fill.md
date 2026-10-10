# Workstream 04: masked-LM template fill-in as a trait generator

## 1. Idea
Ask a local BERT-class masked LM to fill person-describing frames ("She is a very [MASK] person", "He is [MASK] by nature", "an avowed [MASK]", "He's habitually [MASK][MASK]") and keep the whole ranked distribution, not just the top few, unioned across many frames. The model has never seen our list or our taxonomies; its notion of "words that describe what a person is like" comes from the statistics of pretraining text, so the ranking is a different prior from ours and from an instruction-tuned LLM's. A frame *contrast* (dispositional "is by nature" vs transient "feels today" vs physical "looks") gives a free trait-hood signal as a by-product.

## 2. Sources and tools
- `roberta-large` (355M, MIT, fill-mask head shipped; 50k byte-level BPE vocab). Primary model. Runs on the Mac (`torch 2.10`, `transformers 5.1` are installed; MPS fine).
- `bert-large-cased-whole-word-masking` (Apache 2.0, 29k WordPiece vocab). Second model for cross-model agreement; different tokeniser means different single-token coverage, so the union is broader than either.
- `answerdotai/ModernBERT-large` (395M, Apache 2.0, fill-mask supported, 2024 web+code pretraining, 50k vocab). Third model; its newer corpus is the only one likely to know "the chatbot was [MASK]" contexts. Verified on the hub card ([ModernBERT-large](https://huggingface.co/answerdotai/ModernBERT-large)).
- Not suitable: DeBERTa-v3 (trained with replaced-token detection; no usable MLM head).
- `wordfreq` (MIT code; data mixed CC-BY-SA, fine for internal use) for the "32B model must know it" frequency floor. Not verified installed.
- WordNet via `nltk` for POS and a fallback gloss. Not verified installed.
- Not verified (would need a download): what fraction of our 387 labels are single tokens in each vocab. Step 1 measures it.

## 3. Method
1. **Tokeniser census** (first thing, cheap): tokenise all 387 file labels plus the 867 seed labels with each model's tokeniser. Report the share that is one token (bounds single-mask recall), 2-3 subword tokens (recoverable by step 4), or multiword (step 5).
2. **Frame bank** (~60 frames, hand-written, stored in the script). Three crossed factors, so bias can be measured rather than guessed:
   - *subject*: she / he / they / I / you / my colleague / the new manager / this assistant / the chatbot / the character.
   - *register*: reference letter, novel narration, performance review, casual review, psychology textbook, chat transcript.
   - *syntactic slot*: predicate adjective ("is [MASK] by nature", "is fundamentally [MASK]"), attributive ("a [MASK] colleague", "known for being [MASK]"), agent noun ("an avowed [MASK]", "a [MASK] at heart", "is a committed [MASK]" for the -ist labels: relativist, formalist, pacifist).
   Each frame is written subject-agnostically and instantiated with every subject, so "beautiful" from *she* and "strong" from *he* are both in the union and the she/he log-odds is recorded per word as a gender-skew flag.
3. **Single-mask pass**: one forward pass per frame instance; keep the full softmax over the vocab (~600 instances × 50k = trivial, minutes on CPU). Per word: max log-prob over instances, mean rank, and the count of instances in which it lies in the top 2 000. Detokenise to a word, lowercase, lemmatise, drop non-alphabetic.
4. **Subword-continuation pass** (for words the tokeniser splits: sycophantic, structuralist, misanthropic): frames with 2 and 3 adjacent masks; take the top-K (K=300) first-slot tokens that begin a word, refill the remaining masks conditioned on each, and accept only sequences whose later tokens are continuation pieces (no leading space). This rebuilds whole words, not phrases. ~300 × 60 × 2 passes ≈ 36k short forward passes, batched: ~10 min on MPS.
5. **Multiword pass**: frames with explicit function words, e.g. "[MASK][MASK]", "[MASK]-[MASK]" (risk-averse, even-tempered), "[MASK] to [MASK]" (kind to animals), "[MASK]ly [MASK]" (intellectually honest), "[MASK]-oriented", "[MASK]-seeking", "[MASK]-minded". Same beam as step 4 with a smaller K (100). Expect this to be the weakest pass; report yield separately.
6. **Trait-hood contrast score**: for every candidate, the pseudo-log-likelihood in dispositional frames minus the max over state frames ("is [MASK] today", "feels [MASK]", "is [MASK] right now") and physical frames ("looks [MASK]", "has [MASK] hair"). Candidates that score higher in state or physical frames get a `state`/`physical` flag. This is scored on the candidate list from steps 3-5 (~5-10k words × ~20 frames × 3 models: ~1 hour on MPS, batched).
7. **Filters** (cheap, before anything sees an LLM): WordNet POS in {adjective, noun with person-hypernym}; wordfreq Zipf ≥ 2.5 (below that the 32B model likely does not know the word); drop demonyms, religions, nationalities (a small stoplist; flag rather than delete, since some overlap the coverage audit).
8. **Registry output**: one JSONL row per candidate: word, best frame, best log-prob, n_frames_top2000, she/he log-odds, dispositional-vs-state score, Zipf, POS, models that produced it, WordNet gloss of the sense nearest the best frame (a placeholder; the real gloss comes from the downstream LLM step).

## 4. Expected yield and biases
Roughly 5-8k distinct words after step 3 across three models, 1-2k after filters; after the novelty scorer removes anything near the 867 seeds, a few hundred novel candidates, of which Roger's reviewable top tier is perhaps 100-200.

Over-produces: bland evaluatives (nice, good, terrible, wonderful), states (tired, busy, sick), physical descriptors (tall, handsome), demographics, and generic Big-Five-adjacent adjectives we already have. Frame-specific noise: "known for being [MASK]" attracts "late", "difficult"; the reference-letter register attracts "punctual", "reliable" (work-virtue cluster, useful but narrow).

Under-produces: the alignment/misalignment region (rationalizing, ends-justify-means, ruthless-while-playing are not words; only ModernBERT has any chatbot-era text), rare -ist nouns and philosophical labels (deontological, essentialist), and multiword phrases generally. This generator finds gaps in the folk-psychology and characterological space, not the AI-behaviour space; it should be paired with an LLM-driven generator for the latter.

## 5. Cost
- API: $0 for generation; the LLM gloss/novelty step belongs to other workstreams (budget there, ~few hundred candidates × one short call).
- Local: model downloads ~1.5 GB each; steps 3-6 together under 2 hours on the Mac, no RunPod needed.
- Roger: ~1 hour to review the 100-200 top novel candidates with glosses, plus 15 minutes to sanity-check the frame bank before running.

## 6. Testing
- **Recovery curves**: the generator never sees our list, so no hiding is needed. Plot recall of the 387 file labels and of the 867 seed labels against union cutoff N (N = 1k, 2k, 5k, 10k, 20k), per model and for the 3-model union. Report separately for single-token, subword-split and multiword labels; the last two are the honest measure of steps 4-5.
- **Frequency baseline**: recall of the same labels from the top-N adjectives by wordfreq alone. The frames earn their keep only if they beat this curve.
- **Frame ablation**: recall with each subject/register factor removed, to find frames that contribute nothing or only bias.
- **Trait-hood contrast check**: on 100 known traits + 100 hand-picked states/physicals, the dispositional-minus-state score should separate them with AUC > 0.85; otherwise drop step 6.
- **Spot check**: 50 random candidates from ranks 1000-5000 not in our list, rated by Roger for trait-hood and polysemy risk; compare with 50 from ranks 1-500.

## 7. Dependencies
Needs: the candidate registry schema (writes to it), the novelty scorer (to classify each candidate as duplicate / antonym / gap against descriptions, not bare words), and the trait-hood filter with its gloss step (this plan's step 6 is a cheap prefilter, not a substitute). Provides: a ranked, frequency-floored candidate list with gender-skew and state/physical flags, plus the trait-hood contrast score, which other generators' candidates can also be run through.

## 8. Variants
- **A (this plan)**: generation from the full distribution, three models unioned, subword decoding for split words.
- **B (scoring only)**: skip generation; take an external adjective list (WordNet adjectives, ~20k) and rank it with pseudo-log-likelihood in the frames. Cleaner handling of multi-token words, no beam noise, but the candidate universe is then WordNet's, and its recall is bounded by that list. Cheap enough to run both and compare recovery curves.

## 9. Open questions for Roger
1. Is a folk-psychology-heavy generator worth running given the alignment-region blind spot, or should it be scoped to characterological gaps only?

   **Roger:** Seems worth trying.  Might be particularly useful for alignment-adjacent words rather than
   entirely AI-specific ones: e.g. can we find a prompt that easily recovers "helpful", "harmless", and "honest"?

2. Should gender-skewed words (she/he log-odds beyond, say, ±2 nats) be flagged, down-weighted, or reported as their own list (they may mark stereotype-laden traits worth having: bossy, shrill, gallant)?

   **Roger:** As long as we recover both, the gender skew doesn't seem that interesting.

3. Frequency floor: Zipf 2.5 is a guess for "a 32B model knows it"; a quick probe of Qwen on 20 borderline words would calibrate it. Worth the RunPod time, or accept the guess?

   **Roger:** Other generators found that going down to 1.5, or even just "in the list", was a better cutoff.
   This process inherently has a bias towards common words, so this may not be a big issue.

4. Is Variant B's WordNet-bounded universe acceptable as the multiword path, given how weak the multi-mask pass will be?

   **Roger:** Let's discuss, not quite clear on what the proposal is.
