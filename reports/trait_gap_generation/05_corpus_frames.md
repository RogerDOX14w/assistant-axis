# Workstream 05: mining character descriptions with lexical frames

## 1. Idea
Harvest the words English speakers actually use to say what a person is like, by counting fillers of
frames such as "a very X person", "known for her X", "X to a fault", "an incorrigible X", in large
corpora, and rank them by usage frequency. The candidates come from how people describe people, not
from any taxonomy or from an LLM's recall of our list, and each arrives with a frequency (a proxy for
"the 32B model knows this word") and example sentences (a source for the one-line gloss).

## 2. Sources and tools (verified 2026-09-18 unless marked)
- **Google Books Ngram v3 (20200217), English**, CC BY 3.0. Format per line: `ngram TAB year,match,volumes ...`;
  tagged (`man_NOUN`) and untagged variants both present. 3-grams are 6,881 shards of ~390 MB
  (~2.6 TB) but **globally sorted**, so a frame with a fixed first token occupies a contiguous shard
  range findable by peeking shard heads with HTTP range requests. Checked: "very ..." lives in shards
  06650-06652 (~1.2 GB); a partial read of 06651 already gave "very learned man" 59k, "very peculiar
  character" 21k, "very decent man" 10k, "very shrewd man" 8k, "very gentlemanly man" 5k, "very gifted
  man" 4k. 4-grams (6,668 shards) work the same way. 1-grams (24 shards) supply background frequency.
- **nvidia/Nemotron-Personas-USA**, CC BY 4.0, 1M rows, 2.7 GB, not gated. `persona` field is a dense
  trait list ("routine-obsessed, bullet-journal aficionado who balances disciplined work ambition
  with a competitive edge..."). Synthetic and LLM-written, so on-distribution for persona prompts.
- **hieunguyenminh/roleplay**, CC BY 4.0, 5,755 character cards (2 MB), fields name/description/text.
- **PygmalionAI/PIPPA**, Apache 2.0, ~26k role-play logs with `bot_description`; NSFW-flagged,
  row count not verified.
- **proj-persona/PersonaHub**, CC BY-NC-SA 4.0, 200k personas (+370M "elite"); occupational, low trait
  density. **argilla/FinePersonas** (21M, llama3 licence) likewise. Low priority.
- **michaelauli/wiki_bio**, CC BY-SA 3.0, ~728k Wikipedia lead paragraphs: factual, low trait density;
  only for "known for his X" frames. **sedthh/gutenberg_english**, MIT wrapper on public-domain
  text, ~48k books, 10.7 GB: rich characterisation language, archaic skew.
- Not found as open, licensed corpora: obituaries, reference letters. PersonaChat mirrors carry no
  clear licence and personas are hobby facts ("I like to ski"); skip.
- Local tools: torch/transformers/sklearn are installed; spaCy and `datasets` are not (pip-installable,
  Apache/MIT). A small local instruct model or NLI model for stage-1 filtering; Haiku 4.5 for stage 2.

## 3. Method
1. **Books frames (corpus-free).** For anchors `very, so, rather, quite, too, extremely, notoriously,
   remarkably, thoroughly, utterly, hopelessly, chronically, famously` locate the shard range by
   head-peeking, stream `curl | zcat | grep` for `^<anchor> [a-z-]+ (person|man|woman|fellow|people|
   character|individual|soul|chap|lady|guy|girl|boy)`, sum `match` and `volumes` over years >= 1900
   (cutoff open). Add noun frames from 3-grams anchored on `an|a`? No: "a" is too big; instead anchor
   on `incorrigible, inveterate, notorious, shameless, hopeless, born, natural, total` + X + `.|,` to
   catch nominal traits (sycophant, pedant, gossip, yes-man). Keep hyphenated compounds.
2. **Text-corpus frames.** spaCy over Nemotron `persona`, roleplay/PIPPA descriptions, and a
   Gutenberg fiction subsample (~5k books): copular and appositive patterns (`is|was|seemed|remained
   (a|an)? (ADV)? ADJ{1,3} PERSON-NOUN`, `known for POSS X`, `X to a fault`, `POSS X streak|nature|side`,
   `tendency to be X`), plus every `amod`/`acomp` whose head is a person noun or the persona subject,
   keeping ADV+ADJ, ADJ+ADJ and `ADJ (to|toward|with|about) NOUN` spans for multiword labels.
3. **Ranking.** Per source: document frequency (volumes / rows / books). Score each lemma by
   log-odds of appearing in a person frame versus its background frequency (Books 1-grams), which
   demotes generic fillers (good, old, little, poor) and promotes disposition words. Merge sources by
   rank, keep per-source counts.
4. **Filter, two stages.** Lexical stoplist (age, nationality, appearance, wealth, health). Stage 1
   local: a small instruct model labels each lemma {disposition/style, physical/demographic, transient
   state, evaluative-only, other}. Stage 2 API: Haiku 4.5 on survivors returns label, one-line gloss in
   the person-describing sense, polysemy flag, and "enactable in an assistant's replies?" yes/no.
   Nominal traits get an adjectival label (sycophant -> sycophantic).
5. **Registry row:** label, gloss, type, per-source counts and ranks, frames matched, one example
   sentence, polysemy flag. Hand to the novelty scorer.

## 4. Expected yield and biases
Books frames: 5-15k distinct fillers above the 40-match floor, perhaps 1,500-3,000 dispositions after
filtering. Nemotron: a few thousand distinct adjectives/compounds, ~1,000 dispositions, many quirky
compounds ("spreadsheet-loving"). Over-produces: socially desirable and evaluative words, Victorian
moral vocabulary from Books (amiable, worthy, genteel), hobby-flavoured compounds and safety-filtered
niceness from synthetic personas (few cruel/evil/manipulative). Under-produces: concept-phrased
traits (ends justify means, intellectually honest), epistemic-style traits (calibrated, data-driven),
and the alignment region generally; frames find adjectives, not behaviours. Antonym completions come
for free only when the antonym is a common adjective.

## 5. Cost
Books: ~15-25 shards, ~6-10 GB streamed, 1-2 h wallclock, no storage beyond the grep output.
Nemotron + cards: ~3 GB download, spaCy over ~1.1M short texts ~1-2 h CPU; Gutenberg subsample
~2-3 h. Stage-1 local model 1-3 h. Stage 2: ~4k candidates x ~300 tokens with Haiku 4.5, under $3;
$8 if run on all text-corpus fillers too. Roger: 1-2 h reviewing the top few hundred novel survivors.

## 6. Testing
- **Recovery curve:** fraction of the 387 existing labels (lemmatised, underscores to spaces) found
  in the merged ranking at depth N for N in {500, 1k, 3k, 10k}, per source and merged; report which
  existing traits no source finds (expected: concept phrases, alignment traits).
- **Precision spot check:** 100 random survivors from the top 2k, judged for trait-hood; and 50
  Books-only vs 50 Nemotron-only survivors to see source-specific junk.
- **Filter agreement:** stage 1 vs stage 2 labels on 300 items; disagreements go to Roger.
- **Known negatives:** a fixed list of physical/demographic adjectives must not survive stage 1.

## 7. Dependencies
Needs: the shared candidate registry format; the trait-hood filter if another workstream builds one
(stage 2 above is a stand-in); the novelty scorer, which must take label + gloss and return synonym
vs antonym of the nearest existing trait. Provides: candidates with usage frequency and example
sentences, and a reusable lookup "how often is word W used of a person in Books", a rarity filter
any other generator can apply to its own output.

## 8. Variants
- **A (first weekend, corpus-free):** Books 3/4-gram frames only, stage-2 filter, recovery curve.
- **B (text corpora):** add spaCy frames over Nemotron, cards and Gutenberg for compounds and multiword.
- **C (extraction instead of frames):** Haiku reads 50k Nemotron personas and 5k cards and lists the
  traits each describes with a gloss (~$5); better for multiword and behavioural traits, but reintroduces
  an LLM's vocabulary between the corpus and us.

## 9. Open questions for Roger
1. Year cutoff for Books (>= 1900, >= 1950?), trading archaic vocabulary against volume.
2. Are NSFW-flagged PIPPA and non-commercial PersonaHub acceptable inputs?
3. Are synthetic, LLM-authored personas a plus (on-distribution) or circular with the generator's priors?
4. Include nominal traits (pedant, gossip, yes-man) with adjectival relabels?
5. Review depth: top 500 novel survivors, or everything the novelty scorer calls a gap?
