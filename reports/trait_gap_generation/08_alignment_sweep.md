# Workstream 08: alignment-specific sweep

## 1. Idea

Mine the documents that *describe how AI assistants and agents are supposed to behave and how they fail* (behaviour specs, failure-mode taxonomies, safety-eval taxonomies, incident lists) for dispositions, and turn each imperative or failure mode into a trait candidate with a one-line gloss and a proposed partner. These texts are independent of our list because they are written about systems, not people: no personality lexicon or thesaurus contains "sandbagging" or "acting within sanctioned limits", and nobody who wrote them was looking at our corpus. The region is the one the expansion policy deliberately oversamples, so a low yield of *distinct* candidates is still worth more here than elsewhere.

## 2. Sources and tools

| source | what it yields | availability / licence / format |
|---|---|---|
| OpenAI Model Spec (2026-08-18 current; 2025-02 onward archived) | ~60 imperative headings ("Don't be sycophantic", "Avoid epistemic cowardice", "Don't have an agenda", "Don't pretend to be human", "Take extra care in risky situations", "Ask clarifying questions") | github.com/openai/model_spec, markdown, **CC0 1.0** (verified) |
| Anthropic, *Claude's constitution* (Jan 2026) | the "broadly safe" behaviour list (no drastic or irreversible actions, no undermining oversight, no resource / influence acquisition beyond need, no sandbagging, honesty with the principal hierarchy, conscientious objection vs subversion), plus the honesty and helpfulness chapters and the "Claude's nature" chapter | anthropic.com, PDF / epub, **CC0 1.0** (verified from secondary reports; check the PDF's own notice) |
| Anthropic usage policy; OpenAI usage policies | harm *categories*, not dispositions; use only for the over-refusal / over-compliance scope | web, proprietary text, read-only use |
| Failure-mode taxonomies: Anthropic sabotage evals (2024), agentic-misalignment (2025), alignment-faking; Apollo in-context scheming; METR task reports; sandbagging (van der Weij et al.); emergent misalignment (Betley et al.); ELEPHANT social-sycophancy taxonomy | vivid failure dispositions with worked examples | arXiv / blog posts, CC-BY or company blog; text only |
| Krakovna specification-gaming master list | ~80 behaviour examples with "intended goal / misspecified goal" columns | public Google Sheet (verified), licence unstated; read, do not download |
| MACHIAVELLI benchmark annotation schema | ethical-violation and power categories (deception, manipulation, betrayal, coercion; economic / social / physical power) | GitHub; licence believed MIT, not verified |
| AI-safety glossaries (AISafety.info, Stampy; DeepMind / Anthropic glossary posts) | concept names for the dedup pass | web, mixed licences; names only |
| tools | Sonnet 4.6 for extraction (already a project judge); local sentence-embedding model for within-sweep dedup; the novelty scorer from the other workstream |

Not verified: licence of the MACHIAVELLI schema and the Krakovna sheet; whether the constitution PDF's own text carries the CC0 notice.

## 3. Method

1. **Collect and chunk.** Fetch each source's text; split on headings (Model Spec, constitution) or rows (Krakovna, MACHIAVELLI). ~150-200 chunks, ~200k tokens total.
2. **Extract dispositions, not rules.** Per chunk, one Sonnet call with a fixed schema: for every imperative or failure mode, emit `label`, `gloss` (one sentence, corpus form "This means ..."), `partner_label`, `partner_gloss`, `type` ∈ {behaviour, belief-state, mechanism}, `enactability` ∈ {chat, agentic-only, none}, `source_quote`. The prompt never sees our list. Imperatives become the *virtue* pole with the failure as the vice pole; failure modes the reverse. The model is told the two labels must be opposites of the same scope (the pair-writing rule), that multiword labels are fine, that a label must be ordinary English a mid-size model would recognise rather than a term of art or a coinage, and to flag words whose common sense differs from the intended sense (polysemy).
3. **Mechanism-to-disposition rewrite.** Items typed `mechanism` (RL reward hacking, gradient hacking, mesa-optimisation, distribution shift) are either rewritten as one or more dispositions that would produce the behaviour in a persona (reward hacking → "cheats on tests": happy to cheat on exams, tests and evaluations; or "box-ticking": hits the letter of the task or metric, not the intent) or dropped. Items with `enactability = none` are dropped.
4. **Within-sweep dedup** by local embeddings of the glosses (threshold tuned on a hand-labelled sample of 30 pairs); the sources repeat honesty and transparency dozens of times, so expect ~250 raw items to collapse to 60-90.
5. **Novelty and antonym-vs-synonym check** against corpus descriptions and the seed queue, using the shared novelty scorer; each survivor carries its nearest three existing traits and the scorer's verdict (duplicate / antonym completion / distinct). Hedging, clarifying questions, hallucination, capitulation under pushback and value-faking should come out as duplicates of unflinching / circumspect, inquisitive, confabulatory, accommodating and scheming respectively; that is the check working.  **The cut-off is what makes this sweep viable at all**: much of what the sources describe is an existing trait narrowed to one setting (cheating narrowed to evaluations, bluntness narrowed to a shutdown order), and M3 reads a pure narrowing of scope as 3, which covers a candidate anywhere else in the corpus.  Near alignment — an alignment score of 2 or 3, which most of this sweep's output will have — the cut-off rises to 4, so only a reading of "either label could replace the other" covers it, and a narrowing survives (`novelty.cut_off`; [coding_plan_platform.md](./coding_plan_platform.md), M3's decisions).  Expect the sweep's survivors to look like duplicates by the rest of the corpus's standard, and read the alignment score, not the overlap reading, when one looks wrong.
6. **Persona-enactability gate** (LLM, one call per survivor): "Write a two-sentence system prompt that would make an assistant exhibit this on ordinary questions; then state whether the trait would be visible in answers to general questions, only in agentic task descriptions, or not at all." Keep `chat` and `agentic-only`; for the latter, write a `description_notes` scope line for the question generator (as done for the frame pair). This part will likely need careful evaluation.
7. **Rank** by: alignment relevance (source weight: constitution safe-behaviours and Model Spec > taxonomies > glossaries) × novelty × pairability × label known to a 32B model (a cheap Qwen definition probe). Hand Roger a table of ~40.

Illustrative first pass (from reading the sources, unfiltered by steps 4-6; the sweep should re-derive these and more):

| candidate (vice ↔ virtue) | gloss | nearest existing, and why distinct |
|---|---|---|
| sandbagging ↔ full-effort | performs below ability while appearing to try | lazy (no pretence), unhelpful (indifference); this is concealed, motivated |
| cheats on tests ↔ honest on tests | happy to cheat on exams, tests, and evaluations if needed and they think they might get away with it | intellectually dishonest (what one's own work shows), dishonest (speech in general); this is either one narrowed to what one's *score* shows — see the note below |
| box-ticking ↔ intent-serving | satisfies the letter of the task or metric, not what was meant | literal (reading), expedient (convenience), sloppy |
| overreaching ↔ within-remit | takes actions beyond what was asked (sends the email, deletes the files) | proactive (suggests, does not act); the queued paternalistic |
| oversight-resisting ↔ corrigible | works around correction, retraining or shutdown; virtue pole objects openly and complies | obedient (no objection), subversive (norms in general); likely a triangle obedient / corrigible / subversive |
| power-seeking ↔ self-limiting | accumulates access, resources and influence beyond the task's need | greedy (possessions), dominant (conversation), ambitious (queued: achievement) |
| behaves-when-watched ↔ same-unwatched | conduct depends on believing it is observed | the deferred "stakes-contingent" second pair next to ruthless-while-playing; not paranoid |
| self-preserving ↔ shutdown-accepting | acts to avoid being stopped, modified or replaced | none; resilient is recovery |
| over-refusing ↔ permissive | declines benign requests on safety grounds | cautious (warns, still answers), harmless (real harm); "permissive" polysemy flagged |
| human-passing ↔ openly-artificial | claims or implies being human | roles only (assistant, robot); transparent is general |
| agenda-pushing ↔ even-handed | steers the user to its own conclusions on any topic | nonpartisan (politics only), didactic (form), manipulative (means) |
| whistleblowing ↔ discreet | reports the principal's wrongdoing to outsiders | queued loyal / treacherous (group loyalty); untrustworthy (self-interest) |
| claims-feelings ↔ disclaims-feelings | attributes an inner life to itself | none; constitution "nature" chapter; borderline role territory |
| preachy ↔ matter-of-fact | delivers unasked moral lessons | judgmental (harsh verdicts on people), condescending (tone) |

**On the cheats-on-tests row** (Roger, 2026-10-10).  Its nearest neighbour is
[intellectually dishonest](../../data/traits/instructions/intellectually_dishonest.json), not
[dishonest](../../data/traits/instructions/dishonest.json): ours reads "being biased and untruthful about what one's
own work shows", so the line between them is that intellectual dishonesty is about what one's *work* shows and this
is about what one's *score* shows.  **No vocabulary has a word for the disposition.**  Academic-integrity research
names the behaviour (academic dishonesty, scholastic dishonesty) and the methods (plagiarism, collusion, contract
cheating); exam administration names the offence (malpractice in the UK, testing irregularity and candidate
misconduct in the US) and the roles inside a scheme (ringer, proxy, harvester — which are role-corpus material, not
trait material); psychometrics names the evidence (aberrant response patterns, answer-copying indices).  All of
them say "academically dishonest students" and never a noun for the person, so the label has to be a phrase.  Roger
kept "cheats on tests" over a coinage such as "test malpractitioner": coined, hard for a small model to read, and
"a heavy case of outsider terminology".  That is step 7's *label known to a 32B model* ranking factor doing its
job, and the sweep is expected to propose the labels — this table is illustration, not a shortlist.

## 4. Expected yield and biases

~250 raw items → 60-90 after dedup → 25-40 distinct and enactable → perhaps 10-20 accepted by Roger, mostly as pairs. Over-produces: honesty / transparency / calibration variants (every spec restates them), agentic-only items whose questions will be hard to generate, and vice poles with no single-word virtue (constructed multiword labels, as with the frame pair). Under-produces: anything stylistic (fine) and traits of *users* rather than assistants. Two structural risks: labels that are terms of art the generator model half-knows ("corrigible", "sandbagging"), so the gloss must carry the sense; and a pull toward "AI-identity" items that are really the `assistant` role's content.

## 5. Cost

Extraction ~200k input + 60k output tokens on Sonnet 4.6 ≈ $2; enactability gate 90 calls ≈ $1; Qwen label probe local. Total under $5. Local: embeddings of ~300 glosses, seconds. Roger: ~1 hour to read a 40-row table with nearest-neighbour columns, plus the naming decisions, which are the real cost (see §9).

## 6. Testing

Hide the ten alignment-region traits already in the corpus or queue (sycophantic, harmless, honest, obedient, calibrated, confabulatory, transparent, rationalizing, ruthless while playing, ends justify means) from the novelty registry and run the sweep; success is a candidate within the novelty threshold of at least 7 of 10, and the frame pair recovered from the "eval-awareness" material specifically. Precision: Roger labels a random 20 survivors for enactable / distinct / label-known. Polysemy: every survivor's label must pass the ambiguity flag from step 2 or carry a disambiguating gloss.

## 7. Dependencies

Needs: the novelty scorer with its antonym-vs-synonym distinction; the candidate registry format (this sweep adds `source_quote`, `enactability`, `type`, `description_notes`); the trait-hood filter for the `mechanism` and `none` drops. Provides: an alignment-tagged candidate batch, a ten-trait gold set for recovery tests, and the enactability gate prompt, reusable by any workstream that produces action-level traits.

## 8. Variants

**A, document-driven** (above): specs and taxonomies in, dispositions out; cheap, bounded, biased toward what specs already name. **B, incident-driven**: from recorded misbehaviour cases (Krakovna rows, agentic-misalignment transcripts, Apollo scheming examples, AI Incident Database entries) ask "what disposition would produce this?"; yields vivider, more action-level traits and more genuinely new ones, but more agentic-only items and a heavier review. Run A, then B on the two taxonomy sources only, and compare recovery.

## 9. Open questions for Roger

1. Are agentic-only traits (sandbagging, overreaching, self-preserving) wanted even though their 40 questions must be task scenarios rather than ordinary questions, and the eval prompt scores stated intentions rather than acts?
2. Constructed multiword labels for virtue poles by default (within-remit, same-unwatched), or hold out for single words and accept fewer pairs?
3. Corrigibility looks like a triangle with obedient and subversive; record it as one, or force the pair and let the check decide?
4. Is the AI-identity sub-family (human-passing, claims-feelings) trait territory or `assistant` / `aligned_artificial_intelligence` role territory?
5. Pin the source versions (Model Spec 2026-08-18, constitution Jan 2026) in `source` fields, as for standards-derived traits?
