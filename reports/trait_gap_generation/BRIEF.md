# Shared brief: trait-gap candidate generation (2026-09-18)

## The project, in one paragraph
The assistant-axis project (repo /Users/roger/Documents/GitHub/assistant-axis) studies persona
directions in an LLM (Qwen3-32B). Its corpus is a set of *traits* and *roles*, each a JSON file in
`data/traits/instructions/` or `data/roles/instructions/` with a one-or-two-sentence `description`
("This means being X: ..."), five generated system-prompt instruction pairs (pos/neg), 40 questions
and an eval prompt. A trait is a stable disposition or style that a speaking persona can enact
(cautious, sycophantic, philistine, risk-averse, kind to animals); a role is a person or thing
(pirate, refugee, goldfish). Today there are 367 trait files and 336 roles; the seed queue
(`data/seed_queue.json`) holds 867 distinct trait labels including planned ones. Traits are valued
most as *clean pairs* (two files naming each other as antonyms, e.g. calibrated/overconfident);
singletons are fine. The alignment/misalignment region (traits of AI assistants and agents:
sycophantic, rationalizing, ends-justify-means, ruthless while playing) is deliberately oversampled.

## The task Roger set
Fill gaps in the trait set. He wants a way of generating candidate trait names/concepts with the
right semantic properties, by means NOT biased toward recreating the list we already have; then a
cheap, reliable way to answer "do we already have something close to this, and if so what?" many
thousands of times for well under $20 of LLM tokens (semantic-embedding distance is the obvious tool;
he wants two or more independent methods, believing them when they agree and spending LLM tokens
only where they disagree, starting from the nearest candidates they turned up); then a way to test
generators (e.g. how many members of our existing set a generator recovers when they are hidden).
Anything the generators find that is not near anything we have is a gap.

## What has already been done (do not redo)
- Gap scans against named taxonomies: Big Five, HEXACO, MBTI, PID-5, Dark/Light triads, Moral
  Foundations, Schwartz, Hofstede, Inglehart-Welzel, PEN, 16PF, circumplex, Enneagram, VALS, DISC,
  Holland, attachment, Kohlberg (queued in `data/traits/instructions/TRAITS_TO_ADD.md`).
- A May 2026 analysis (TRAITS_TO_ADD.md § "Strategy 1b") that took the PCA of the extracted persona
  vectors and named under-used directions with an LLM.
- Coverage audits of demographic, household, work, class, religion, political and individual-
  difference domains (same file, parts 2-4).

## Lessons from September 2026 that any plan must respect
- Polysemy bites: labels whose common sense is not the trait sense (disciplinary, engaging,
  economic, balanced, empowered) were rejected after generation; a candidate's *intended sense*
  must travel with it (a one-line gloss), and the filter must flag ambiguous words.
- The generator model is a 32B model: words too rare for it to know are useless as labels.
- Multiword labels are fine ("kind to animals", "intellectually honest", "ends justify means").
- A candidate near an existing trait may be its antonym (a pair completion, valuable) rather than a
  synonym (a duplicate); the novelty test must distinguish these.
- Descriptions, not bare words, define scope; two words can be synonyms in the dictionary and
  different traits here (cautious vs risk-averse vs bold).

## Constraints
- Cost: each method should run for well under $20 of API tokens; prefer local compute (a Mac with
  torch, transformers, scikit-learn, umap installed; a RunPod GPU is available for bigger models at
  extra cost). Anthropic and OpenAI clients are installed.
- File access: read only within the repo; write only the one output file named in your task.
  You may use web search/fetch to check whether a source (word list, dataset, thesaurus) exists,
  its licence and format, but do not download anything.
- Do not run generation or call paid APIs yourself; this is planning.

## Output format (write exactly one Markdown file at the path given in your task)
1. **Idea** (2-3 sentences): what it generates or answers, and why it is independent of our list.
2. **Sources and tools**: each named, with availability, licence and format as far as you could
   verify (say what you could not verify).
3. **Method**: numbered steps, concrete enough to estimate cost and to code from.
4. **Expected yield and biases**: how many candidates, what kinds it will over- and under-produce.
5. **Cost**: API dollars, local compute, Roger's review time.
6. **Testing**: how to tell whether it works (recovery of hidden existing traits, spot checks,...).
7. **Dependencies**: what it needs from other workstreams (a trait-hood filter, a novelty scorer, a
   candidate registry format) and what it provides to them.
8. **Variants**: if there are two reasonable ways to do it, outline both briefly.
9. **Open questions for Roger**: decisions only he can make.
Aim for 500-900 words. Work at moderate effort: a plan Roger can judge, not a literature review.

## File-access boundary (restated 2026-09-23 after a breach)

Agents may read only under `/Users/roger/Documents/GitHub/assistant-axis` and their own
scratchpad, and write only the files their task names.  Nothing under the home directory
outside that tree may be listed, read or stat'ed, including `~/.cache` (Hugging Face, pip,
uv), even to check whether a model or dataset is already downloaded: state the need and
its size in the report and let Roger answer.  Five planning agents listed caches or tool directories under the home directory
(`~/.cache/huggingface/hub`, `~/nltk_data`, `~/.ollama`) on 2026-09-17; Roger considers
that a privacy breach.  The boundary is this repository alone, not `~/Documents/GitHub/`.  Coding
plans must carry this paragraph into every Opus task prompt, and any download goes to
`data/external/` inside the repo.
