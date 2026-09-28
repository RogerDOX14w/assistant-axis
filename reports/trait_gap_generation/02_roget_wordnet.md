# 02 — Roget's Thesaurus heads as a coverage map, WordNet adjective clusters as sibling

## 1. Idea
Roget (1911) partitions all of English into 1,000 numbered heads arranged in opposed pairs
(602 Willingness / 603 Unwillingness, 604 Resolution / 605 Irresolution, 606 Obstinacy /
607 Tergiversation), and Classes IV–VI (Intellect, Volition, Affections; heads 450–1000) are a
ready-made map of dispositions. Mapping our labels onto heads gives a per-head coverage report whose
empty heads are gaps *by concept*, and the opposed-head structure yields antonym-pair candidates for
free. WordNet's adjective clusters (head synset + direct antonym + satellites) are a second,
differently-built map: it supplies word-level antonym pointers, per-sense glosses, and a native
trait-hood signal. Both were built 100+ years apart from our list, so neither is biased toward it.

## 2. Sources and tools (verified 2026-09-18)
- **Roget 1911, Gutenberg #10681** (public domain; text 1.4 MB, US-ASCII, CRLF; also at
  GITenberg `10681-body.txt`). Structure is parseable: `CLASS` / `DIVISION` / `SECTION` / numbered
  subsection lines, head lines `^(\d+[a-z]?)\. Title -- N\.` (1,032 match; 994 distinct numbers +
  38 lettered heads like 604a), POS blocks at line start (`N.` `V.` `Adj.` 927 heads, `Adv.` `Phr.`
  `Int.`), items separated by `;`/`,`, cross-refs `&c (topic) NNN` (604a is cited as `604.1`),
  `^` = obsolete/rare (dagger), `[Obs.]` `[Lat.]` `[U.S.]` tags. **Opposed pairs are not
  encoded** (the original two-column synopsis is flattened), so pairing must be reconstructed.
- **Existing parsers/datasets**: `MoserMichael/roget-thesaurus-parser` (GitHub, Python,
  Class/Section/Head/Sense objects; licence not checked); **Open Roget's Project** (Java, CC BY-SA
  4.0, updated lexicon, tarball only); an RDF dump of the 1911 edition (CC BY-SA). None encodes
  opposed pairs; a ~150-line parser of our own is cheaper than adapting them.
- **WordNet**: `wn` package (pip; not installed here, nor nltk). `WN_DATA_DIR` /
  `wn.config.data_directory` can point inside the repo (e.g. `data/external/wn/`, gitignored);
  `wn.download('oewn:2024')` or `wn.add(local LMF)`; API exposes `sense.get_related('antonym')`,
  `synset.get_related('similar')`, `synset.pos == 's'` for satellites. Open English WordNet 2024:
  CC BY 4.0, LMF/JSON/RDF/WNDB formats, 120,630 synsets (18,156 adjective synsets in WN 3.0).
  Zero-dependency alternative: parse WNDB `data.adj` directly (`a`/`s` synset type, `!` antonym,
  `&` similar, `+` derivational pointers).
- **Not verified**: `wordfreq` package licence/data bundling (needed for the rarity filter); the
  roget-thesaurus-parser licence; whether the RDF dump is still hosted.

## 3. Method
1. **Parse Roget** into `heads.json`: number, title, class/division/section/subsection path, adj
   list, noun list, cross-refs. Drop `^`, `[Obs.]`, foreign-tagged items. Keep 450–1000 (plus a
   handful earlier, e.g. 82 Conformity/83 Unconformity) as the "dispositional" set, ~560 heads.
2. **Reconstruct opposed pairs** (`head_pairs.json`): candidate = adjacent numbers in the same
   subsection; confirm by (a) morphological negation overlap between adj lists (un-/in-/dis-),
   (b) ≥1 WordNet antonym pointer between the two adj lists, (c) one Haiku call per subsection over
   the head titles for the residue (triads such as 600/601, 606/607/608). ~$0.5.
3. **Map our labels** (387 trait files + 867 seed-queue labels) onto heads by two independent
   routes: **lexical** — label (and its -ness/-ity/-ous/-ic derivations) occurs in a head's adj or
   noun list; **semantic** — local embedding (bge/e5 via `transformers`, Mac) of our
   `description` vs each head's "title + first 15 adjectives" profile, top-3 cosine. Agree →
   accept; disagree or lexical-miss → Haiku adjudication with the description (~600 calls, ~$1).
4. **Per-head coverage report** (`roget_coverage.md`/`.json`): for each head, mapped existing
   traits, mapped queued labels, partner head and its coverage. Gap classes: (i) both heads empty,
   (ii) one side empty = pair completion, (iii) head covered by ≥3 traits = crowded (duplicate
   check).
5. **Harvest pair candidates**: for gap heads, take adj-list items with Zipf frequency ≥ 3.5
   (32B-model-known), single or two-word, gloss = head title + path + partner head; pair each with
   the partner head's harvested adjectives. Prefer items with a WordNet antonym pointer landing in
   the partner head (double-confirmed pairs).
6. **WordNet sibling**: (a) noun closure under `trait.n.01`, `disposition.n.01`, `attitude.n.01`,
   `temperament.n.01`, `character.n.02` → derivationally related adjectives → their cluster's
   direct antonym: pairs with synset glosses attached (the "intended sense" rides along, and
   polysemy is flagged when a lemma has ≥2 adjective senses). (b) Map each of our labels to a
   synset (lexical + embedding of gloss vs description, as in step 3) so WordNet antonyms of
   existing traits are pair-completion candidates independent of Roget.
7. Emit candidates in the shared registry format with `source` (`roget:604`/`oewn:…`), gloss,
   partner, ambiguity flag, frequency.

## 4. Expected yield and biases
~560 heads; guess 150–250 with zero coverage after mapping, ~100 of them plausible trait gaps →
200–400 word candidates, ~100–150 confirmed opposed pairs. WordNet route: a few hundred
trait-closure adjectives, ~150 antonym pairs, heavy overlap with Roget. Over-produces: emotional
*states* (Class VI: wonder, regret, lamentation), Victorian moral vocabulary and archaic words
(tergiversation, pusillanimous), evaluative adjectives (good/bad). Under-produces: AI/alignment
traits (sycophantic, rationalizing, ends-justify-means), modern coinages, multiword labels, and
fine intra-head distinctions (cautious vs risk-averse both land in 864 Caution).

## 5. Cost
API < $3 (pairing + adjudication + optional gloss check, Haiku). Local: embeddings of ~1,500
descriptions + 560 profiles, minutes on the Mac. Disk: 1.4 MB Roget text; OEWN ~100 MB DB if via
`wn` (gitignore) or ~5 MB `data.adj`. Roger's time: ~1–2 h reviewing the empty-head table (sorted by
class, with proposed pair), not the full report.

## 6. Testing
- **Recovery**: hide the 387 existing labels; measure how many appear verbatim among harvested
  adjectives of Classes IV–VI (expect 70–85 % of single-word labels, near 0 % for coined multiword
  ones) and how many existing antonym partners (from `trait_antonyms_v4.json`) are recovered as
  opposed-head or WordNet-antonym pairs.
- **Mapping precision**: spot-check 40 label→head assignments; report lexical/semantic agreement
  rate before adjudication.
- **Pairing table**: check 30 known Roget pairs (602/603, 604/605, 896/897…) and the triads.

## 7. Dependencies
Needs: the candidate registry format; the novelty scorer (to tell synonym-duplicate from
antonym-completion within a crowded head); the trait-hood filter (to drop states). Provides: a
stable coverage coordinate per trait (Roget head number) usable by every other workstream; the
WordNet trait-closure membership and ≥2-sense polysemy flag as cheap features for the trait-hood
filter and the ambiguity flag; double-confirmed antonym pairs.

## 8. Variants
- **A (Roget-first, planned above)**: heads as the coverage unit; WordNet confirms pairs.
- **B (finer grain)**: use Roget's semicolon groups (5–10 per head, "resolute; unflinching;
  earnest") as units — better at splitting cautious/risk-averse, more rows to review.
- **C (WordNet-first)**: trait-closure adjectives + antonym pointers as the generator, Roget only
  for the report; no pairing reconstruction needed, but no concept map of what's missing.

## 9. Open questions for Roger
1. Scope: Classes IV–VI only, or all 1,000 heads (Classes I–III give a few, e.g. Order/Disorder)?
2. Are emotional states (Class VI Personal Affections) in scope as traits, or only dispositions?
3. Frequency threshold for "the 32B model knows it" (Zipf 3.5? 4.0?), and is `wordfreq` acceptable
   (CC BY-SA data) or should rarity be judged by the model itself?
4. `wn` + OEWN 2024 (CC BY 4.0, 100 MB local DB) vs a hand parser over WN 3.0 `data.adj`?
5. Should the Roget head number become a permanent field in the seed queue / trait files?

## 10. Resolution (2026-09-23)

1. Scope: Classes IV-VI first, then a cheap pass over Classes I-III restricted to heads whose
   adjective lists already contain one of our labels.
2. Emotional states (Class VI): in scope as inclinations to enter the state frequently, glossed
   as a general tendency (same rule as plan 1 § 10.3).
3. Frequency: the soft Zipf feature of plan 14 § 11; wordfreq's CC BY-SA data is acceptable
   for a tool whose output is a candidate list (nothing from it is redistributed).
4. WordNet access: under discussion (2026-09-23).
5. The Roget head number is recorded in the registry as provenance, not in trait files.
