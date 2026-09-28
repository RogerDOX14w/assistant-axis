# 14. Trait-hood filter and candidate registry

## 1. Idea
Every generator emits raw words and phrases; this workstream answers "is this something a speaking persona can *enact as a stable disposition or style*, does the 32B model know it, and which sense do we mean?" cheaply, and records the answer, the novelty evidence and the review state in one registry that promotes into `data/seed_queue.json`. It is independent of our list by construction: the rubric never sees the existing traits, only the definition of trait-hood; the existing 367 are used solely as a held-out test.

## 2. Sources and tools
- **`wordfreq`** (PyPI, `pip install wordfreq`; `zipf_frequency(w, "en")` = log10 occurrences per billion). Not in `pyproject.toml` today. Code is MIT; the bundled frequency data carries the upstream sources' terms (README states the data licence; I could not verify the exact CC-BY-SA clause this session). Unmaintained since 2024 but frozen data is fine for a floor. Handles multiword via per-token combination (`zipf_frequency("kind to animals")` returns the min-ish estimate); for phrases use the min over content words instead.
- **WordNet 3.0 via `nltk`** (not installed; WordNet licence, permissive): adjective lemma list (~21k incl. satellites) for the random-adjective test, and per-lemma sense count as a local polysemy signal (no API cost).
- **Classifier model**: Claude Haiku 4.5 ($1/$5 per MTok; 50% off through the Message Batches API) with a cached rubric system prompt. Escalation tier for disagreements: Sonnet 5 ($2/$10). Prices from the claude-api skill table (cached 2026-06-24).
- **Local frequency check for borderline words**: Qwen3-32B "define this word in one line" probe on the RunPod when a batch is already up; on the Mac, Qwen3-32B tokenizer piece count as a proxy (≥4 pieces for a single word = suspect). Not a primary signal.
- Existing repo pieces reused: `data_analysis/seed_entities.py` lifecycle (`candidate -> ready -> seeded -> ...`), `normalize_to_file_name` / `display_form_name` in `assistant_axis/entity_id.py`, `MultiModelUsage` for the mandatory `usage.json`.

## 3. Method
1. **Normalise** each candidate: lowercase surface form, `stem = normalize_to_file_name(surface)`, `label = display_form_name(surface)`; dedupe on `(stem, sense_id)` where `sense_id` is assigned in step 4 (a word with two intended senses is two candidates).
2. **Frequency floor (local, $0)**: `zipf = wordfreq.zipf_frequency(head_word)`; for phrases, min over content words. Floor 3.0 (≈1 per million words) → `rare` tag; 2.5-3.0 → `borderline`, sent to the 32B define-probe when convenient. Never a hard drop: a rare word with a common gloss can still be relabelled by Roger.
3. **Local polysemy prior**: WordNet adjective sense count `n_senses`; ≥3 → `polysemy_prior`. Also a cheap `evaluative_prior` from a 40-word stoplist (nice, bad, good, great, awful, fine, decent, ...) extended by the classifier's own flags over time.
4. **LLM classifier (Haiku 4.5, batched 25 candidates per call, structured JSON output)**. Rubric, in the system prompt (~1,200 tokens, `cache_control` on it):
   - Definition of trait-hood as in the brief, with 6 positive and 12 negative examples chosen from *outside* the corpus.
   - Per candidate, output: `verdict` ∈ {`trait`, `tagged`, `reject`}; `tags` ⊆ {`physical`, `transient_state`, `demographic`, `role_person`, `role_thing`, `evaluative_only`, `relational_only` (waterproof, hexagonal), `not_a_word`}; `gloss` (one line, the *trait* sense, "This means being X: ..." register); `senses` (list of up to 3 short sense labels for the word in ordinary use) and `trait_sense_rank` (1 = the trait sense is the dominant everyday sense, 2 = secondary, 3 = minor); `enactable_in_text` 0-2 (can a text-only persona show it in a reply?); `confidence` 0-1.
   - Rule: `tagged` is for candidates that fail trait-hood for one of the tag reasons but are coherent (may become roles or physical-tagged traits); `reject` only for non-words, pure relational adjectives and things nobody could enact.
   - `polysemy` flag is derived, not asked for: `trait_sense_rank ≥ 2` or (`n_senses ≥ 3` and `confidence < 0.7`).
5. **Second opinion where it matters**: 10% random sample plus every candidate with `confidence < 0.6` or a prior/LLM disagreement (e.g. `evaluative_prior` but verdict `trait`) re-run on Sonnet 5; disagreements go to Roger with both outputs.
6. **Registry write**: one JSONL record per candidate in `data/candidates/registry.jsonl` (append-only; a small `registry.py` upserts by `(stem, sense_id)` and merges signal blocks from other workstreams).
7. **Promotion**: `registry.py promote --min-novelty ... --status accepted` emits seed-queue entries with `status: "candidate"`, `entity_type` from the verdict (`role_*` tags → `role`), `tags: ["gap_gen", "source:<generator>", <filter tags>]`, `description_draft` from the gloss, `partner` from the novelty block when the nearest existing trait is flagged as an antonym, `section: "trait-gap generators (2026-09)"`. Roles get `entity_type: "role"` and go through the same queue.

### Registry record (draft schema)
```json
{"stem": "world_shaping", "label": "world-shaping", "surface": "world-shaping", "sense_id": 1,
 "gloss": "This means being world-shaping: ...", "entity_type": "trait",
 "sources": [{"generator": "wordnet_walk", "rank": 412, "score": 0.71, "run": "2026-09-20a"}],
 "freq": {"zipf": 3.4, "borderline": false, "qwen_define_ok": null},
 "filter": {"verdict": "trait", "tags": [], "senses": ["shaping the world", "..."], "trait_sense_rank": 1,
            "enactable_in_text": 2, "confidence": 0.85, "polysemy": false, "model": "claude-haiku-4-5",
            "second_opinion": null},
 "novelty": {"signals": {"minilm_cos": {"score": 0.62, "nearest": [{"stem": "proactive", "kind": "T", "sim": 0.71, "relation": "related"}]},
                         "e5_cos": {...}, "tfidf_desc": {...}},
             "agreement": "agree", "adjudication": {"model": null, "relation": null, "note": null}},
 "matches_existing": null, "heldout_hit": false,
 "review": {"status": "unreviewed|accepted|rejected|merged|deferred", "by": null, "at": null, "note": null},
 "seed_queue_stem": null}
```
`relation` ∈ {synonym, antonym, related, unrelated} is filled by the novelty workstream; `matches_existing` / `heldout_hit` support generator recovery tests.

## 4. Expected yield and biases
Of 10,000 raw candidates from mixed generators, expect ~25-40% `trait`, ~30% `tagged` (mostly `physical`, `transient_state`, `role_*`), the rest `reject`. Over-produces: virtue/vice adjectives (the rubric's easiest case), so the novelty scorer will find most of those already covered. Under-produces: multiword dispositions and AI-alignment-specific phrasings ("rationalizing", "ends justify means"), which Haiku may call `transient_state` or `evaluative_only`; the positive examples must include several of these. Polysemy flagging will be over-eager on common words (every common adjective has ≥3 WordNet senses), hence the `trait_sense_rank` gate rather than the sense count alone.

## 5. Cost
Per 10,000 candidates: 400 Haiku calls × (~1,200 cached rubric + ~400 uncached input + ~1,500 output tokens) ≈ 0.16M uncached input + 0.48M cache reads + 0.6M output ≈ **$3.2 live, ~$1.6 via Batches**. Sonnet 5 second opinions on ~15% ≈ $1.0 (batch $0.5). Validation set (367 + rejected labels + 1,000 WordNet adjectives ≈ 1,400 candidates) ≈ $0.5. Local: seconds for wordfreq/WordNet. Roger's time: the disagreement queue only, ~2-4% of candidates, ~10 s each → ~1 h per 10k.

## 6. Testing
- **Existing 367 traits** (labels only, no descriptions): ≥95% `trait`; the ~26 corpus entries carrying the `physical` tag in the seed queue should come back `tagged: physical` (that is the correct answer, not a miss). Report every non-`trait` with its tags for eyeballing.
- **Rejected labels** (disciplinary, engaging, economic, balanced, empowered, emotive): expect `polysemy` true or `trait_sense_rank ≥ 2` on all six, `empowered` also `transient_state`, `economic` `relational_only`. Failure on ≥2 means the rubric needs sense examples.
- **Random 1,000 WordNet adjectives**: expect ≤15% `trait`; spot-check 50 of the `trait` verdicts by hand.
- **Gloss quality**: 30 random glosses compared with the corpus `description` for matched existing traits; the description writer step later uses the gloss, so it must name the sense, not just restate the word.
- **Stability**: rerun 200 candidates twice; verdict agreement ≥ 90%.
- Unit tests for `registry.py` upsert/promote against a fixture queue (pytest, as in `data_analysis/tests/`).

## 7. Dependencies
Needs: candidate lists from the generator workstreams (surface + generator rank/score); novelty scores and nearest-existing lists per signal, with antonym/synonym relation, from the novelty workstream. Provides: the schema above, `registry.py` (upsert, promote, report), filter verdicts and glosses to the novelty scorer (it should embed the gloss, not the bare word, which also resolves the polysemy problem at the embedding stage), and the `heldout_hit` field the generator-test workstream needs.

## 8. Variants
- **A (recommended)**: Haiku batched classifier as above; rubric cached; Sonnet escalation.
- **B (local)**: Qwen3-32B on the RunPod via vLLM with the same rubric, ~400 prompts of 2k tokens, minutes of GPU time; zero API cost but needs a live pod and a JSON-parse fallback. Worth it only if candidate volume exceeds ~100k; also gives the frequency floor "for free" (the classifier model is the generator model).

## 9. Open questions for Roger
1. Should `physical` candidates be promoted as traits with the `physical` tag (the Sep 2026 research-track decision) or parked in the registry only?
2. Registry location and format: `data/candidates/registry.jsonl` (append-only, git-tracked) versus a single JSON like the seed queue.
3. Zipf floor: 3.0 as proposed, or stricter (3.5) given that the 32B must also generate 40 questions and instructions from the label?
4. Is a `role_*` verdict enough to route into the roles half of the queue, or should roles get their own filter pass with a role-hood rubric?

## 10. Roger responses
1. For now, physiscal traits would go to the appropriate area of TRAITS_TO_ADD.
2. SG
3. Try it and see, adjust as needed. What does out current trait distribution look like
4. Unclear on the options, ask me in more detail

## 11. Resolution (2026-09-23)

1. Physical candidates: routed to the physical-attribute section of TRAITS_TO_ADD, not promoted.
2. Registry: append-only JSONL, as proposed.
3. Zipf floor: **not a gate.**  Measured on the 414 existing labels (rarest content word, wordfreq):
   median 3.37, quartile 2.82, 5th percentile 1.9; a 3.0 floor would reject a third of our own
   labels (confabulatory, guileless, abstemious, sycophantic, deontological, ecocentric, ...).
   Rule: hard reject only below Zipf 2.0 (keeps 95% of existing labels); below 2.5 run a cheap
   definition probe (Haiku; the 32B itself only at adoption) asking whether the model knows the
   word in the intended sense; record Zipf as a registry feature either way.
4. Roles: option (a).  A candidate the classifier tags as a role (person or thing) goes to a
   roles holding list in the registry with no further check; no role-hood pass now.
5. States (from plan 1, Q3): a state word is in scope when it names a disposition to be in that
   state (agitated, flustered, calm already are); the gloss must say "a general tendency to ..."
   so the embedding and the generator read a disposition, not an episode.  The filter tags
   `state` and the gloss carries the tendency wording; the state/trait distinction from affect
   research (Spielberger's state-trait anxiety; dispositional vs momentary affect) is the model.
