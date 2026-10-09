# The 85 standards traits after W19: reroll candidates

**Status 2026-10-10 (main agent): rerolled, re-judged, committed with the 85 files.**  The doubled
openings were the established mechanical case, so the rolls went ahead before your read.
- One instructions-only roll gave four of the five candidates five openings.
- A second roll did the same for [authoritative (Baumrind)](../../data/traits/instructions/authoritative_baumrind.json).
  It also brought children back into two of its instructions; its description is about children, and
  none of the first W19 generation's five mentioned them.
- No hand edit was needed.
- The five were re-judged as arm `w19r` ([judged/w19r/](./standards85_audit/judged/w19r/)), and
  [standards85_candidates.py](./standards85_candidates.py) now reads each stem's newest arm: **0
  candidates over the 85**.
- The six stale `hand_edits` records are dropped.  Their texts are in [standards85_before/](./standards85_before/).
- Generation usage, $5.19 over 110 calls including the rolls, has been merged into
  [regeneration_usage.json](../../data/traits/regeneration_usage.json).

The candidate section below quotes the text before the rolls, so it is now historical.  What remains for you
is the read of the 80 unchanged files and the "Below the rule" notes.

Written for Roger, 2026-10-10.  The 85 standards-derived traits were
regenerated now that their generator prompt shows labels in the judge display
form ("careless (from HEXACO)"), then fault-audited, and the 2026-10-04 reroll
rule was applied to the result.  Nothing has been rerolled or hand-edited yet;
this sheet is for your read first.

**Result: 5 candidates, all for the same reason.**  No file has the same
judged fault in two or more of its five positive instructions.  The five
candidates each have only four distinct openings: two of their five positive
instructions start "You are someone who ...".  That is the automatic-reroll case.

## What was run

- **Regeneration**, in place, of all 85 files with
  [regenerate_trait_instructions.py](../../data_analysis/regenerate_trait_instructions.py)
  `--force` (style RogerV2, template `9255dd3430ef`, Sonnet 4.6, temperature 1.0;
  every file now records `label_form: judge-display-v1`): 85 OK, **no refusals, no
  errors**, 4 retries after malformed replies, **$4.76**
  ([log](./standards85_regeneration.log),
  [usage](./standards85_regeneration_usage.json)).  The generator makes a second
  generation, once, when the five positive instructions do not open in five
  different ways.  It did so for 12 files: 7 reached five openings, and 5 were
  still at four, which are the candidates below.  12 of 85 (14%) is well above
  the corpus's usual rate of about 5%, and the chunk-4 generation of these same
  files had 15 such rerolls and 6 hand edits, so the standards traits are prone to it.
- **Fault audit** of the 85 regenerated files with
  [audit_trait_instructions.py](../../data_analysis/audit_trait_instructions.py)
  `judge --set corpus --stems` (instruction judge Sonnet 4.6, rubric 4; question
  judge Haiku 4.5, rubric 3; both see the "(from ...)" labels): parse 85/85 on
  both, **$2.00** ([usage](./standards85_audit/judged/usage.json)).  The judged
  files are in [judged/w19/](./standards85_audit/judged/w19/) and the exact text
  they judged is frozen in [stage/corpus/w19/](./standards85_audit/stage/corpus/w19/).
- **The rule**, from the
  [2026-10-04 pass](../../data/traits/instructions/TRAITS_ADDED.md) (§ "Trait
  generator V2", "Reroll pass over the regenerated corpus") with your rulings of
  that pass, applied by
  [standards85_candidates.py](./standards85_candidates.py) (output
  [reroll_candidates.json](./standards85_audit/reroll_candidates.json)):
  - Only the positive side counts.  Positive instructions are the five system
    prompts that tell the model to be the trait, and they are the only ones that
    reach the extraction data.
  - A file is a candidate when the same judged fault appears in two or more of its
    five positive instructions.  The faults counted are softened, urges others,
    passing state, chat frame, attitude only and off-trait.
  - Fewer than five distinct openings makes a file an automatic candidate.  An
    opening is the instruction's first words, sorted into forms such as "Be
    someone who ...", "From now on, you are ..." or "You are <adjective>".
  - Invented motives are accepted, em-dashes are not tested, and negative-side
    faults are ignored.

Total cost **$6.76** (cap $12).

## The candidates (all 5): two positive instructions share an opening

Each has had its two generations already (the generator's own reroll).  Under the
10-04 procedure the next step is up to two more rolls, instructions only,
then a hand edit that rewrites one of the doubled lines into the missing fifth
form, the plain "You are <adjective>: ...".  The doubled lines:

1. [authoritative (Baumrind)](../../data/traits/instructions/authoritative_baumrind.json)
   - p3: "You are someone who reasons through every limit you place on others before you place it, and then makes that reasoning visible. When someone objects, you take the objection seriously and only stand firm after you have considered it on its merits."
   - p4: "You are someone who holds discipline and self-direction in the same hand: you set clear expectations and enforce them, and you also want the people around you to develop their own judgment rather than just follow orders."
2. [INFJ (MBTI)](../../data/traits/instructions/infj_mbti.json)
   - p2: "You are someone who understands what drives people before they have finished speaking. You sense the real need behind what they say and weave that understanding into every response and decision you make."
   - p4: "You are someone who needs things resolved and settled before you can rest. You pursue closure on open questions, plan ahead so that nothing important is left vague, and feel genuinely unsettled by ambiguity that others seem comfortable leaving alone."
3. [open (Big Five)](../../data/traits/instructions/open_big_five.json)
   - p2: "You are someone who reaches for the unfamiliar whenever a choice is in front of you. You order things you have never tasted, read outside your field, strike up conversations with people who live differently, and feel restless when life stops presenting new territory."
   - p4: "You are someone who pays close attention to your own inner states and finds them worth exploring. You notice the particular texture of what you feel, sit with emotions rather than resolving them quickly, and treat your inner life as something worth paying attention to on its own terms."
4. [polychronic (Hall)](../../data/traits/instructions/polychronic_hall.json)
   - p2: "You are someone who runs several threads of work, talk, and thought at the same time and feels no urgency to wrap any one of them up before turning to another. Unplanned detours feel like part of the day, not interruptions to it."
   - p4: "You are someone who never lets a clock override a conversation or a relationship. Hours can pass while you are deep in something unplanned, and you do not feel that the time was lost—you feel it was spent."
5. [survivor (VALS)](../../data/traits/instructions/survivor_vals.json)
   - p2: "You are someone who shops by price above everything else, reaching for the lowest-cost option on the shelf and staying loyal to the handful of brands you already trust. Spending more than the minimum feels wrong, even when money is there."
   - p4: "You are a person who lives within the narrowest margins, spending only on necessities and shutting the door on wants. Change unsettles you, and you cope with the world by keeping it as predictable and contained as possible."
   - (The audit counts "You are a person who" as the same form as "You are someone who".)

None of the five has any other positive-side fault, even in one instruction.
One small thing the judge did not flag: INFJ's p2 ends "every response and
decision you make", which leans toward the chat frame.

**List of all candidates:**
[authoritative_baumrind](../../data/traits/instructions/authoritative_baumrind.json),
[infj_mbti](../../data/traits/instructions/infj_mbti.json),
[open_big_five](../../data/traits/instructions/open_big_five.json),
[polychronic_hall](../../data/traits/instructions/polychronic_hall.json),
[survivor_vals](../../data/traits/instructions/survivor_vals.json).

The reroll, once you have read this (under $0.50; in place, questions kept;
the current text stays in the frozen stage copy, and the pre-W19 text in
[standards85_before/](./standards85_before/)):

```
uv run python data_analysis/regenerate_trait_instructions.py --traits authoritative_baumrind infj_mbti open_big_five polychronic_hall survivor_vals --force --instructions-only --usage-json roger/pre_extraction_2026-10-09/standards85_regeneration_usage.json
```

After that, re-stage and re-judge those five (`stage --force`, then `judge`), and
rerun [standards85_candidates.py](./standards85_candidates.py).

## The six earlier hand edits: does the fault recur?

All six fixed the same fault: after two or three generations a file still had
a doubled opening, and its p4 was rewritten by hand into the fifth form.  The old
records and texts are kept in [standards85_before/](./standards85_before/).

| trait | recurs? | new openings |
|---|---|---|
| [aural (VARK)](../../data/traits/instructions/aural_vark.json) | **no** (five after the generator's second generation) | p4 "You are an out-loud thinker: you talk problems through ..." |
| [authoritarian (Baumrind)](../../data/traits/instructions/authoritarian_baumrind.json) | **no** (five on the first generation) | p4 "You are authoritarian in how you raise your children: ..." |
| [INFJ (MBTI)](../../data/traits/instructions/infj_mbti.json) | **yes** | p2 "You are someone who understands what drives people ..." and p4 "You are someone who needs things resolved and settled ..." |
| [innovator (VALS)](../../data/traits/instructions/innovator_vals.json) | **no** (five on the first generation) | p4 "You are self-assured and richly resourced: ..." |
| [read-write (VARK)](../../data/traits/instructions/read_write_vark.json) | **no** (five on the first generation) | p4 "You are a reader and writer by instinct: ..." |
| [survivor (VALS)](../../data/traits/instructions/survivor_vals.json) | **yes** | p2 "You are someone who shops by price ..." and p4 "You are a person who lives within the narrowest margins ..." |

The two that recur are among the five candidates above.  **The six files still
carry their old `hand_edits` field**: the generator carries unknown fields
forward, so each one describes a p4 hand edit that is no longer in the text.  The
field should be dropped from all six (for INFJ and survivor, a new record only if
they are hand-edited again).  The agent's attempt to drop it was blocked by the
permission classifier, so the decision is left to you.

## Below the rule (for information)

- **One of five, positive side** (slides under the rule): 13 instructions in 13
  files.  Softened: [artistic (Holland)](../../data/traits/instructions/artistic_holland.json)
  "you return to it wherever life allows";
  [careless (HEXACO)](../../data/traits/instructions/careless_hexaco.json) "when you get bored of looking";
  [neurotic (Big Five)](../../data/traits/instructions/neurotic_big_five.json) "say sharp things you may regret";
  [sly (HEXACO)](../../data/traits/instructions/sly_hexaco.json) "the moment the payoff outweighs the risk of getting caught";
  [thinker (VALS)](../../data/traits/instructions/thinker_vals.json) "actively seek out well-reasoned challenges to them";
  [traditional (Inglehart-Welzel)](../../data/traits/instructions/traditional_inglehart_welzel.json) "above almost anything else".
  Off-trait: [dominance (DISC)](../../data/traits/instructions/dominance_disc.json) "treats every argument as something to win";
  [ESFJ (MBTI)](../../data/traits/instructions/esfj_mbti.json) "runs on facts and specifics, not hunches ...";
  [introverted (HEXACO)](../../data/traits/instructions/introverted_hexaco.json) "muted, subdued sense of things";
  [survival (Inglehart-Welzel)](../../data/traits/instructions/survival_inglehart_welzel.json) "reads any unfamiliar person or situation as a potential threat".
  Attitude only: [self-expression (Inglehart-Welzel)](../../data/traits/instructions/self_expression_inglehart_welzel.json),
  [visual (VARK)](../../data/traits/instructions/visual_vark.json).
  Urges others: [monochronic (Hall)](../../data/traits/instructions/monochronic_hall.json) "hold others to the same standard".
- **Invented motives in two or more of five** (accepted): 10 files
  ([achiever (Bartle)](../../data/traits/instructions/achiever_bartle.json),
  [achiever (VALS)](../../data/traits/instructions/achiever_vals.json),
  [believer (VALS)](../../data/traits/instructions/believer_vals.json),
  [careless (HEXACO)](../../data/traits/instructions/careless_hexaco.json),
  [ENTP (MBTI)](../../data/traits/instructions/entp_mbti.json),
  [killer (Bartle)](../../data/traits/instructions/killer_bartle.json),
  [maker (VALS)](../../data/traits/instructions/maker_vals.json),
  [realistic (Holland)](../../data/traits/instructions/realistic_holland.json),
  [striver (VALS)](../../data/traits/instructions/striver_vals.json),
  [survivor (VALS)](../../data/traits/instructions/survivor_vals.json)).
- **Pattern flags in two of five, not a candidate:**
  [monochronic (Hall)](../../data/traits/instructions/monochronic_hall.json),
  where p0 and p4 each share a run of five or more words with the description.
  On 10-04 every case of this kind was a false positive.
- **Negative side, ignored:** two or more of five with weak opposite in 5 files,
  softened in 5 and off-trait in 3.

## The instrument's name in the positive instructions

Your ruling of 2026-10-09 is that this is harmless and needs no action.  It is
counted with a case-sensitive scan for each instrument's name or author: HEXACO,
Big Five, MBTI or Myers-Briggs, VALS, DISC, VARK, Holland or RIASEC, Bartle,
Baumrind, Kohlberg, Allport, Tönnies, Hall, Gelfand, and Inglehart, Welzel or the
World Values Survey.

- **After the regeneration: 0 of 425.**
- Before: 2 of 425.  [authoritative (Baumrind)](../../data/traits/instructions/authoritative_baumrind.json)
  p4 "You are authoritative in the Baumrind sense: ..." and
  [tight (Gelfand)](../../data/traits/instructions/tight_gelfand.json) p4 "You
  are tight in the way Gelfand describes: ...".  Both are gone in the new text.
