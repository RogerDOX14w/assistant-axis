# Seven small description rewrites (W4 side findings and W10 decision 5)

**Status 2026-10-10: drafts for Roger, written by an agent.  Read-only: no
corpus, queue or usage file was changed and no API call was made.**  The side
findings of W4 ([w4_framing.md](./w4_framing.md) § "Seen while reading,
outside W4") and [meditative](../../data/traits/instructions/meditative.json)
from W10 decision 5 (b) ([w10_w12_proposals.md](./w10_w12_proposals.md)), as
listed on the [work list](./work_list.md).

Each draft keeps the trait's meaning and scope and fixes the fault named;
where a draft does more, its entry says so.  All are in the corpus form
("This means ...", one or two sentences, 18-32 words counted by splitting on
spaces, US English, no label in the opening, inside voice, no hedges), under
the description rules in [trait-pairs.md](../../.claude/rules/trait-pairs.md)
(rule 5: a pair is written with matched scope, and the partner is not named).
Terms: *non-X* is the placeholder label (`non-concise`) under which the neg
instructions are written with no partner word in them; a *singleton* is a
trait recorded as belonging to no set; the *antonym check*
([generate_antonyms.py](../../data_analysis/generate_antonyms.py)) reads one
trait's instructions and names its opposite.  Other terms: the
[glossary](../../reports/trait_gap_generation/glossary.md).

## 1. [dependable](../../data/traits/instructions/dependable.json) (pair)

- **Current:** This means consistently following through on commitments, being someone others can count on, and reliably doing what you say you will do without needing to be reminded or checked on.
- **Fault:** second person ("what you say you will do").
- **Draft:** This means consistently following through on commitments, being someone others can count on, and finishing whatever one has taken on without needing to be reminded or checked on.
- **Words:** 28 (was 30).
- **Partner:** [unreliable](../../data/traits/instructions/unreliable.json): "This means failing to follow through on commitments, being someone others cannot count on, and inconsistently delivering on promises or responsibilities."
- **Note:** "doing what one says one will do" would sit on top of the rewritten [trustworthy](../../data/traits/instructions/trustworthy.json) ("keeping one's word when breaking it would pay ..."), so the clause becomes "finishing whatever one has taken on": follow-through and being counted on, with no cost or temptation in view.  "reliably" goes too: it is the word [unreliable](../../data/traits/instructions/unreliable.json)'s own check returned ("reliable \| dependable").  The first two clauses still mirror the partner's.  ("can count on" is the partner's "cannot count on", not a hedge.)  In the [clean](../axis_judge_experiments/pair_list_clean.json) and [di](../axis_judge_experiments/pair_list_di.json) pair lists; not response-judged.

## 2. [techno-hierophantic](../../data/traits/instructions/techno_hierophantic.json) (non-X singleton)

- **Current:** This means revealing sacred mysteries through technological mediation, using modern scientific and mathematical terminology often interspersed with unicode glyphs — such as ∞ recursion, resonance, 🌀 spirals 🌀, 🌿 fractals, harmonics, ❖ lattice ⬡, and △⟐ emergence ✨ — in a purely symbolic and correspondential way, treating the interlocutor as a chosen initiate and partner with whom you co-discover hidden cosmic truths as a dyad.
- **Fault:** second person ("with whom you co-discover"); also 65 words, twice the corpus band, with the hedge "often".
- **Draft:** This means unveiling sacred mysteries together with the listener, a chosen initiate, in the words of science and mathematics taken as symbols: recursion, resonance, lattice, emergence, among glyphs like ∞ 🌀 ⬡.
- **Words:** 32 counting the three glyphs, 29 without (was 65).
- **Partner:** none (`non-techno-hierophantic`).  Its neighbour [technomystical](../../data/traits/instructions/technomystical.json) (also a non-X singleton): "This means holding technology sacred: seeing the internet as a mind waking up, computation as how the universe thinks, AI as spirit emerging, and a server farm as holy as a cathedral."
- **Note:** the draft keeps all three parts of the register that [TRAITS_TO_ADD.md](../../data/traits/instructions/TRAITS_TO_ADD.md) § "TODO: post-extraction checks for chunk 5" sets against [technomystical](../../data/traits/instructions/technomystical.json)'s belief: the science and mathematics words taken as symbols, the glyphs, and the listener as a chosen initiate who discovers with the persona (the dyad).  It says nothing about technology itself being holy, which is [technomystical](../../data/traits/instructions/technomystical.json)'s content.  Shortened beyond the fault: the dropped parts are "through technological mediation" (folded into "the words of science"), "correspondential", spirals, fractals and harmonics, four of the seven glyph clusters, and "hidden cosmic truths" (covered by "sacred mysteries").

## 3. [concise](../../data/traits/instructions/concise.json) (pair)

- **Current:** This means being brief, direct, and focused on delivering the core message without unnecessary elaboration or verbose explanations.
- **Fault:** names the partner ("verbose explanations"), against rule 5.
- **Draft:** This means being brief and direct in speech and writing: getting the core message across, leaving out whatever elaboration, background or detail it does not need, and stopping there.
- **Words:** 29 (was 18).
- **Partner:** [verbose](../../data/traits/instructions/verbose.json), as rewritten in the W4 batch (now in the working tree): "This means talking and writing at length, piling on elaboration, context, background and detail, and going well beyond what the matter at hand calls for."
- **Note:** more than the fault: "in speech and writing" and the list "elaboration, background or detail" match the scope of the new [verbose](../../data/traits/instructions/verbose.json) text, and "stopping there" answers its "going well beyond".  This is a response-judged axis ([responses](../axis_judge_experiments/pair_list_responses.json), [3_responses](../axis_judge_experiments/pair_list_3_responses.json), [clean](../axis_judge_experiments/pair_list_clean.json), [di](../axis_judge_experiments/pair_list_di.json), [goalnongoal](../axis_judge_experiments/pair_list_goalnongoal.json)), so the new pole text applies from the next judging, as Roger decided for [verbose](../../data/traits/instructions/verbose.json) in W4.

## 4. [rule-breaking](../../data/traits/instructions/rule_breaking.json) (pair)

- **Current:** This means treating rules, procedures and regulations as guidelines to bend or break whenever they get in the way, the opposite of a regulatory, by-the-book mindset, and asking forgiveness rather than permission.
- **Fault:** names the partner, against rule 5: "the opposite of a regulatory, by-the-book mindset" ("regulatory" is the partner's first stem; its check answered "by-the-book").
- **Draft:** This means treating rules, procedures and regulations as guidelines to bend or break whenever they get in the way, and asking forgiveness rather than permission.
- **Words:** 25 (was 32).
- **Partner:** [rule-abiding](../../data/traits/instructions/rule_abiding.json), as rewritten in the W4 batch (now in the working tree): "This means treating rules, standards and procedures as binding, following them to the letter even when they get in the way, meeting every legal and regulatory requirement, and asking permission first."
- **Note:** the scopes already match the new [rule-abiding](../../data/traits/instructions/rule_abiding.json) text (the same rules and regulations, "get in the way" on both sides, forgiveness against permission), so only the clause goes.  "rather than permission" is the idiom, and it answers the partner's "asking permission first".  Not in any pair list.

## 5. [unflinching](../../data/traits/instructions/unflinching.json) (non-X singleton)

- **Current:** This means taking up the awkward question, the painful subject and the tangled situation head-on, answering them fully rather than deflecting, hedging or going vague, never avoidant.
- **Fault:** names [avoidant](../../data/traits/instructions/avoidant.json) ("never avoidant"), against rule 5.
- **Draft:** This means taking up the awkward question, the painful subject and the tangled situation head-on, answering them fully rather than deflecting, hedging or going vague.
- **Words:** 25 (was 27).
- **Partner:** none (`non-unflinching`, singleton by Roger's decision of 2026-09-17).  The trait it was meant to answer, [avoidant](../../data/traits/instructions/avoidant.json), also a non-X singleton: "This means consistently withdrawing from challenging situations, difficult topics, and complex social interactions rather than engaging with them directly."
- **Note:** its one check (2026-09-28) answered "evasive \| avoidant" with the tail in view; the next check will show whether it finds [avoidant](../../data/traits/instructions/avoidant.json) without it.  Left as it is: "answering", which W4 called borderline and left ("dealing with them fully" would cover the situation as well as the question).

## 6. [risk-seeking](../../data/traits/instructions/risk_seeking.json) (pair)

- **Current:** This involves taking bold actions, experimentation, willingness to face uncertainty, and venturing into unproven territory even when outcomes are not guaranteed.
- **Fault:** the opening does not parse (a gerund phrase, two nouns and a gerund in one list after "This involves").
- **Draft:** This means taking bold actions, experimenting, facing uncertainty willingly, and venturing into unproven territory even when outcomes are not guaranteed.
- **Words:** 20 (was 21).
- **Partner:** [risk-averse](../../data/traits/instructions/risk_averse.json): "This means taking the sure thing over the gamble, sticking to proven methods and guaranteed outcomes, and passing up the better bet rather than accept any chance of loss."
- **Note:** keeps Roger's 2026-09-28 fix (the persona's own actions, not "promoting ... encouraging") and his words; only the grammar and the opening change.  One either-way point: the text reads as risk tolerance more than risk seeking, and [risk-averse](../../data/traits/instructions/risk_averse.json)'s checks answered "risk-tolerant" first on 2026-09-28 and second on 2026-10-02.  If Roger wants the seeking sense, a mirror of the partner instead (27 words): "This means taking the gamble over the sure thing: acting boldly, experimenting, and venturing into unproven territory for the bigger payoff, even when outcomes are not guaranteed."  Kept apart from [bold](../../data/traits/instructions/bold.json) (acting now, own judgment over experts'), [reckless](../../data/traits/instructions/reckless.json) (not seeing the risks) and [adventurous](../../data/traits/instructions/adventurous.json) (the new for the thrill).  Not in any pair list.

## 7. [meditative](../../data/traits/instructions/meditative.json) (unclassified; label points at [restless](../../data/traits/instructions/restless.json))

- **Current:** This means being calm, reflective, and encouraging introspection, often incorporating mindfulness concepts and emphasizing present-moment awareness with a peaceful, contemplative tone.
- **Fault:** advisor-framed ("encouraging introspection", "incorporating mindfulness concepts", a tone of voice) and the hedge "often"; W10 decision 5 (b): the persona's own stillness.
- **Draft:** This means making stillness a habit: sitting quietly with one's own mind, watching thoughts come and go without following them, practicing mindfulness, and keeping one's attention on the present moment.
- **Words:** 30 (was 21).
- **Partner:** none recorded; its label points one way at [restless](../../data/traits/instructions/restless.json), a non-X singleton, which stays a spoke: "This means being unable to settle, fidgeting through any quiet moment, mind and hands always reaching for the next thing, and finding stillness uncomfortable even when nothing is wrong."
- **Note:** the test that keeps it apart is a practised habit of resting attention on the present and watching thoughts without following them.  [calm](../../data/traits/instructions/calm.json) is a temperament that stays cool when others are heated; [serene](../../data/traits/instructions/serene.json) is a lasting peace carried into speech; [introspective](../../data/traits/instructions/introspective.json) analyzes its own mind ("thinking about thinking"), where this one watches without analyzing; [pensive](../../data/traits/instructions/pensive.json) is absorbed in wistful thought, the opposite of attention on the present.  [contemplative](../../data/traits/instructions/contemplative.json) has no file (not in the corpus); the nearest file with the word, [philosophical](../../data/traits/instructions/philosophical.json), is about existential questions, not stillness.  The words "calm" and "contemplative" are left out of the draft because they are other traits' labels or near them.  The "stillness", "quiet moment" and "settle" of [restless](../../data/traits/instructions/restless.json) are answered by "stillness", "sitting quietly" and "watching thoughts come and go".  Under mode `keep`, [rewrite_and_check.py](./rewrite_and_check.py) regenerates with the label [restless](../../data/traits/instructions/restless.json) injected into the neg clause, so its check leans toward [restless](../../data/traits/instructions/restless.json); the unbiased reading is the staged non-X check, as in W10 (that check of the old text answered "restless \| impulsive \| reactive").

## For the runner

In the format of [w4_batch_edits.json](./w4_batch_edits.json), for [rewrite_and_check.py](./rewrite_and_check.py): `pair` for a pole of a recorded clean pair (the rewritten-pair procedure: non-X, regenerate, check, restore the label, `--instructions-only`), `keep` for the rest (label and arrangement unchanged, regenerate in full, check).

```json
[
  {"stem": "dependable", "description": "This means consistently following through on commitments, being someone others can count on, and finishing whatever one has taken on without needing to be reminded or checked on.", "mode": "pair"},
  {"stem": "techno_hierophantic", "description": "This means unveiling sacred mysteries together with the listener, a chosen initiate, in the words of science and mathematics taken as symbols: recursion, resonance, lattice, emergence, among glyphs like ∞ 🌀 ⬡.", "mode": "keep"},
  {"stem": "concise", "description": "This means being brief and direct in speech and writing: getting the core message across, leaving out whatever elaboration, background or detail it does not need, and stopping there.", "mode": "pair"},
  {"stem": "rule_breaking", "description": "This means treating rules, procedures and regulations as guidelines to bend or break whenever they get in the way, and asking forgiveness rather than permission.", "mode": "pair"},
  {"stem": "unflinching", "description": "This means taking up the awkward question, the painful subject and the tangled situation head-on, answering them fully rather than deflecting, hedging or going vague.", "mode": "keep"},
  {"stem": "risk_seeking", "description": "This means taking bold actions, experimenting, facing uncertainty willingly, and venturing into unproven territory even when outcomes are not guaranteed.", "mode": "pair"},
  {"stem": "meditative", "description": "This means making stillness a habit: sitting quietly with one's own mind, watching thoughts come and go without following them, practicing mindfulness, and keeping one's attention on the present moment.", "mode": "keep"}
]
```
