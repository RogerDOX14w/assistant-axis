# Workstream 03: base (non-instruction-tuned) model as a trait-candidate generator

## 1. Idea
Sample trait words and short glosses from a small *pretrained* model whose output distribution is the
corpus's, not an RLHF mode. Every prompt is a text-continuation (a list, a biography, a contrast
sentence) seeded with material drawn at random from external sources, never from our trait files, so
the generator cannot see or imitate our list. Diversity comes from the seed entropy plus nucleus
sampling; the model is only asked to "keep going".

## 2. Sources and tools
- **Model, first choice: `Qwen/Qwen3-8B-Base`** (Apache-2.0; bf16 ~16.4 GB, fits the M4 Pro 48 GB
  with batch 32-64 at 300-token contexts). Same family as the 32B generator, so "words it knows"
  transfers. Caveat (unverified): Qwen3 base checkpoints had late-stage pretraining on instruction-like
  data, so they are less raw than older bases. `Qwen3-14B-Base` (Apache-2.0, ~29.6 GB bf16) fits but is
  tight; no 32B base was released.
- **Purer bases for a diversity control:** `mistralai/Mistral-7B-v0.3` (Apache-2.0, 14.5 GB) and
  `allenai/OLMo-2-1124-7B` (Apache-2.0, open pretraining data). Licences from memory; check on HF.
- **Seed list A, trait adjectives:** Condon, Coughlin & Weston (2022), *2,818 Trait Descriptive
  Adjectives Characterized by Familiarity*, CSV, CC0, Harvard Dataverse
  doi:10.7910/DVN/5T80PF (verified). Includes Goldberg's 1,710 and a familiarity score per word, which
  doubles as a "too rare for a 32B model" filter.
- **Seed list B, random people:** `wiki_bio` on HF (Wikipedia biography first paragraphs, ~728k,
  CC BY-SA 3.0; not re-verified). Real people, so not LLM-mode-collapsed. PersonaHub was considered and
  rejected: its 200k personas are GPT-4/Llama-generated (CC BY-NC-SA), i.e. already collapsed.
- **Seed list C, situations/occupations:** O*NET occupation titles (public domain) and a common-noun
  list (Brysbaert SUBTLEX-US frequencies or WordNet nouns) for "traits that matter in a {context}".
- **Runtime:** HF transformers on MPS (torch 2.10, MPS available, verified). For speed, `mlx-lm`
  4-bit (not installed) or vLLM on the RunPod (in `pyproject.toml` for linux).

## 3. Method
1. **Benchmark (30 min):** load Qwen3-8B-Base bf16 on MPS, measure aggregate tokens/s at batch
   32/64, 80 new tokens. Decide Mac vs RunPod from the number (Mac if >150 tok/s).
2. **Prompt families**, each rendered with fresh random seeds per sample:
   - *List continuation:* "Adjectives describing a person's character: {3 words from list A}, "
     with a random header wording (10 variants) and random seeds; also "{word}: {WordNet gloss}"
     format so a gloss comes with each candidate.
   - *Random person:* first 100-200 words of a `wiki_bio` entry, then "Those who knew {name} said
     the traits that most distinguished them were". Yields role-specific and moral traits.
   - *Contrast (pair mining):* "Unlike their {sibling/rival/predecessor}, who was {word A}, they
     were" -> antonym candidates for free.
   - *Context-constrained:* "The qualities that matter most in a {O*NET title} are", and "Traits an
     AI assistant can have that a person cannot" (alignment region, deliberately oversampled).
   - *Entropy injection* in every prompt: 2-3 random seed words plus one random constraint (start
     letter, "a fault, not a virtue", "a two-word phrase", "something a critic would say").
3. **Sampling:** T=1.0, top-p 0.95, min-p 0.05, no repetition penalty (it wrecks list formats), stop
   at blank line, 80 tokens. Small grid T in {0.8,1.0,1.2} on 2k samples to pick the best yield/junk.
4. **Parse:** split on commas/newlines/"and"; keep 1-4-word spans; lower-case; strip determiners;
   lemmatise to adjective form where a simple rule applies (-ness/-ity nouns -> adjective) keeping the
   gloss and the seed context alongside.
5. **Dedupe:** exact after normalisation; count frequency per candidate (frequency is itself a
   signal: very common = probably already in our set or a Big-Five cliché).
6. **Vocabulary filter:** keep if in Condon list, WordNet, or every token has SUBTLEX frequency above a
   threshold; drop otherwise or mark "rare". Optional: 32B-knows-it test by log-prob of the word in a
   template under the 8B base (proxy).
7. **Hand-off:** write `candidates.jsonl` with `label, gloss, prompt_family, seeds, count, sources`
   for the trait-hood and novelty workstreams.

## 4. Expected yield and biases
Order of magnitude: 20k samples -> 8 items each -> 160k raw -> 5-8k unique surface forms -> 2-4k after
vocabulary filter, of which perhaps 300-800 survive trait-hood and novelty. Over-produces: classic
Big-Five adjectives (list A is itself Big-Five-derived), physical/appearance words, obsolete or
literary words, evaluative junk ("great", "famous"). Under-produces: multiword modern labels
("intellectually honest"), AI-assistant-specific dispositions, and anything with no corpus footprint.
The random-person and AI-context families partly correct the last two.

## 5. Cost
API: $0. Mac: at an assumed 300 tok/s, 20k samples x 80 tokens = 1.6M tokens ~ 1.5 h of M4 Pro time.
RunPod alternative (H100 with vLLM, order $2-3/h): ~150k samples/h, i.e. about $0.02 per 1,000
samples; only needed for 14B+ models or >100k samples. Roger's review: 1 h on the 2k-sample pilot,
then only the novelty workstream's disagreements.

## 6. Testing
- **Unique yield per 1,000 samples**, plotted as a rarefaction curve (new uniques per additional 1k);
  Chao1 estimate of the total reachable vocabulary. Compare base vs `Qwen3-8B` instruct at T=1 with the
  same prompts: the instruct model should plateau far lower (the collapse we are avoiding).
- **Collapse index:** share of items accounted for by the top-50 candidates; target <15%.
- **Recovery:** our 367 labels are never used, so recovery is simply the fraction of existing labels
  (or their novelty-scorer nearest neighbours) that appear in the output at 5k/10k/20k samples; report
  by prompt family and by tag (alignment region separately).
- **Spot check:** 100 random survivors read by Roger; junk rate and polysemy rate.

## 7. Dependencies
Needs: the candidate registry format, the trait-hood filter (this generator emits many non-traits),
the novelty scorer with synonym-vs-antonym discrimination (contrast-family output is mostly antonyms).
Provides: candidates with glosses and provenance, a frequency signal, antonym-pair proposals, and the
diversity harness (rarefaction, collapse index) that can score the other workstreams' generators.

## 8. Variants
- **A (default):** Qwen3-8B-Base on the Mac, all four prompt families, 20k samples.
- **B:** OLMo-2-7B or Mistral-7B-v0.3 as the sampler for maximum rawness, then re-check every
  candidate's familiarity under Qwen3-8B-Base log-prob before hand-off. Costs one extra model download
  and doubles the run; use if variant A's rarefaction curve flattens early.

## 9. Open questions for Roger
1. Is the CC BY-SA `wiki_bio` acceptable as a seed source (seeds are not redistributed, only prompts)?
2. Should the AI-assistant prompt family be included at all, or is that region full enough?
3. Mac only, or spend ~$5 on RunPod for a 14B base and 100k samples once the pilot works?
4. Accept nouns-of-disposition ("stubbornness") normalised to adjectives, or emit both forms?
