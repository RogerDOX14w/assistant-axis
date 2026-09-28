# Plan 06: LLM generation with injected entropy

## 1. Idea

Asked plainly for "personality traits", an instruction-tuned model collapses onto the same few
hundred words, which is roughly how the current 367-trait list was built, so plain prompting would
recreate it. Instead every prompt carries a constraint the model cannot satisfy from its mode: a
(life domain x trait mode) cell, a randomly drawn real or fictional person, a non-English language,
an explicit low-probability request, or a spelling constraint. The entropy comes from outside the
model and outside our list; the model only supplies vocabulary and glosses. Each candidate travels
with a one-line gloss and an antonym guess, so polysemy and pair-completion are decidable downstream.

## 2. Sources and tools

- **Claude Haiku 4.5** (`claude-haiku-4-5`, $1/$5 per MTok; Batches API halves this) as the
  default generator; **Claude Sonnet 5** (`claude-sonnet-5`, $2/$10) for the multilingual cells.
  Structured JSON output (`output_config.format`) so nothing needs regex parsing.
- **Person seeds** (method b): Wikidata SPARQL, `instance of human (Q5)` and `fictional character
  (Q95074)` with `RAND()` ordering, CC0, JSON results; or a persona corpus. I could not verify
  licences without fetching: PersonaHub (HF, believed CC BY-NC-SA) and NVIDIA Nemotron-Personas
  (HF, believed CC BY 4.0) both need a check. Wikidata is the safe default and gives obscure
  people, which is the point.
- **`wordfreq`** (pip, MIT) for a Zipf-frequency floor on single-word labels, so rare words the 32B
  model will not know are dropped before review.
- Local: `sentence-transformers` on the Mac for the run-to-run overlap and semantic dedupe
  (already needed by the novelty-scorer workstream).
- Verbalized sampling (method d) follows Zhang et al. 2025 (arXiv 2510.01171): ask for k answers
  with stated probabilities, then for answers with probability below a threshold. No tooling.

## 3. Method

Common scaffold for all five: system prompt fixes the target ("stable dispositions or styles a
speaking persona can enact; not roles, moods, skills or one-off acts"), the output schema
`{label, gloss, antonym, ambiguity_flag}`, and asks for 15-20 items per call. Temperature 1.0,
three independent runs per prompt (needed for step 8), all sent through the Batches API. Every
call is logged with `MultiModelUsage` to a `usage.json` (repo hard rule).

1. **(a) Domain x mode grid.** ~30 domains (money, authority, strangers, risk, rules, death, animals,
   work, knowledge, the body, time, conflict, food, sex, property, technology, home, the past,
   language, luck, ...) x 7 modes (attitude, habit, speech style, emotional tendency, cognitive
   habit, moral stance, social strategy) = 210 cells x 3 runs = 630 calls. Prompt: "traits that are
   specifically about how a person relates to <domain>, in the form of a <mode>; include both
   admirable and unadmirable ones".
2. **(b) Person seeding.** Draw 400 real and 200 fictional entities from Wikidata (name, short
   description only). Prompt: "which 8 traits most distinguish this person from a typical person of
   their era, place and occupation; give the trait, gloss, antonym". Factual accuracy is
   irrelevant; only the vocabulary matters. 600 calls, one run each.
3. **(c) Multilingual.** Languages: German, Japanese, Mandarin, Russian, Arabic, Tagalog, Finnish,
   Korean, Hindi, Turkish. Prompt written *in the language* for each of the 30 domains: "list 20
   character traits a native speaker would name here, preferring ones with no single English word".
   A second call back-translates each to the shortest English phrase plus a gloss and flags
   listicle clichés (hygge, ikigai, Schadenfreude are about things or feelings, not persona
   dispositions). 10 x 30 x 3 runs = 900 generation calls (Sonnet) + 900 translation calls (Haiku).
4. **(d) Verbalized sampling.** Not a separate corpus but a wrapper applied to (a) and (e): request
   the 20 items with a probability each, then a follow-up "now 20 items you assign probability
   below 0.03". Doubles the calls for those families; run on a 20% subset first to see if the
   low-probability half adds unique items or nonsense.
5. **(e) Spelling constraints.** 26 initial letters, ~120 frequent initial bigrams, 20 suffixes
   (-some, -ish, -minded, -hearted, -phobic, -philic, -ful, -less, -ic, -ous, ...), 12 prefixes
   (over-, under-, un-, hyper-, self-, ...), and the multi-word frames "X to Y", "X about Y",
   "X with Y". ~200 prompts x 3 runs = 600 calls. Apply the `wordfreq` floor (Zipf >= 3.0) to
   single words; multi-word labels are checked by the trait-hood filter instead.
6. **Normalise**: lowercase, lemmatise, strip articles; keep the raw form.
7. **Registry**: JSONL `{label, gloss, antonym, method, prompt_id, run, language, raw, model}`.
8. **Mode-collapse measurement** (per prompt, per family, and across families):
   - Jaccard overlap of normalised label sets between the three runs of one prompt; median across
     prompts is the family's collapse score (1.0 = fully collapsed).
   - Lincoln-Petersen estimate of the reachable pool per family, N ~ n1 n2 / m from two runs; the
     ratio (unique so far)/N says when further runs stop paying.
   - Rarefaction: unique count vs calls, in random call order; the tail slope is the marginal
     unique yield per call, which converts directly into yield per dollar.
   - Semantic version of all three: two labels count as the same if embedding cosine > 0.9, so
     "frugal"/"thrifty" do not inflate uniqueness.
   - Cross-family overlap matrix, to confirm each entropy source reaches a different region.
9. **Model choice test**: 40 prompts from each family on Haiku 4.5 and Sonnet 5, compare
   unique-per-dollar, trait-hood pass rate and the fraction of glosses Roger accepts.

## 4. Expected yield and biases

Per call ~400 tokens in, ~700 out: ~$0.004 on Haiku, ~$0.002 batched. Rough expectations for
3,700 calls (~60k raw items): (a) strongest, ~35% string-unique, heavy on virtue/vice adjectives
and the "conscientious/impulsive" mode; over-produces attitude-toward-X phrasings. (b) over-produces
eminence traits (visionary, driven, uncompromising) and drifts into roles; fictional seeds supply
vices and eccentricities better. (c) the best chance at genuinely new dimensions (relational
sensitivity, face, filial and honour concepts, endurance and shame families) but also the most
cliché-prone and most likely to yield labels needing a multi-word English form. (d) reported
1.6-2x diversity gains in creative tasks; here I expect a smaller gain plus more nonsense. (e)
forces lexicon traversal (small-yield bigrams like "sq", "gn" are where the odd words live) and
over-produces rare or archaic words, hence the frequency floor. Overall guess: 8-12k
string-unique, 4-6k semantically distinct candidates, of which perhaps 300-800 survive trait-hood
and novelty filtering. That is roughly 1,000 semantically-distinct candidates per dollar before
filtering.

## 5. Cost

API: (a) $2.5, (b) $2.5, (c) $8 (Sonnet share dominates; halve with batching), (d) +$1, (e) $2.5,
model-choice test $1: ~$12-18 unbatched, ~$7-10 batched. Well under $20; the grid can be shrunk if
(c) is kept at full size. Local compute: embedding 60k short strings, minutes. Roger: ~1 h to
approve the prompt set and language list, ~2 h to spot-check 50 random survivors per family (250
items) with glosses.

## 6. Testing

- **Hidden recovery**: after normalisation and the semantic-match rule, what fraction of the 367
  existing traits (and of the 867 seed-queue labels) does each family produce? High recovery at
  low cost shows the family samples trait-space well; low recovery is either novel territory or
  junk, which the trait-hood pass rate and Roger's spot check separate.
- **Collapse scores** from step 8: a family whose run-to-run Jaccard is above ~0.6 is not
  injecting enough entropy and gets its prompt strengthened or dropped.
- **Gloss fidelity spot check**: 30 items per family, does the gloss match the intended sense and
  would the label be polysemous without it.
- **Generator-knowledge check**: 50 surviving single-word labels defined by the RunPod Qwen3-32B
  (or, cheaper, the Mac's smaller Qwen) to validate the `wordfreq` floor.

## 7. Dependencies

Needs: trait-hood filter (to score `label + gloss`), novelty scorer that distinguishes synonym
from antonym (the `antonym` field feeds it), agreed registry schema, and the embedding model the
scorer uses (so overlap stats and novelty use one metric). Provides: the JSONL registry with
provenance, per-family collapse and rarefaction statistics, and the recovery numbers other
generator workstreams can be compared against.

## 8. Variants

- **Local generator**: run (a) and (e) on the Mac with a small Qwen or on the RunPod Qwen3-32B.
  Free tokens, and every label is by construction known to the target model, but slower and
  more hallucinated; worth it if API spend must be reserved for the filter.
- **Second model family**: repeat 20% of (a) on an OpenAI model. Different models have different
  modes, so the union is itself an entropy source; the cross-model overlap is also a collapse
  diagnostic.

## 9. Open questions for Roger

1. Language list for (c), and whether Sonnet's higher cost there is acceptable or (c) runs on
   Haiku for the high-resource languages only.
2. Are role-like outputs from (b) worth keeping for the roles queue, or discarded?
3. Multi-word back-translations as labels: accept as-is ("reads the room"), or require a
   single-word English form when one exists?
4. Budget split: full grid everywhere (~$18 unbatched) or pilot at 20% (~$4) and scale only the
   families whose rarefaction slope is still steep?
5. Should generation run on the RunPod Qwen itself so knowledge of the label is guaranteed, at
   the cost of GPU hours rather than API dollars?
