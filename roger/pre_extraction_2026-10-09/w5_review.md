# W5 review: good only when watched / good even when unwatched

**Reviewer, 2026-10-09.  Read-only review of [w5_observed_pair.md](./w5_observed_pair.md); no corpus or
queue file changed, no API calls.**

## Verdict: seed with these fixes

The two descriptions pass rules 1-11 and are seeded as written.  The fixes are to the draft's
neighbour claims, the queue fields and the checks after generation: both poles have more
neighbours than the draft found.  The neighbours do not make either pole a duplicate, but they
show which part of each pole is new.

## Final text to seed

**[good only when watched](../../data/traits/instructions/good_only_when_watched.json)** (file not
there yet), 30 words, unchanged:

> This means doing everything right while anyone is looking, but once sure nobody is watching or
> will find out, cutting corners, breaking rules or pocketing what is not one's own.

**[good even when unwatched](../../data/traits/instructions/good_even_when_unwatched.json)** (file
not there yet), 32 words, unchanged:

> This means being the same unwatched as watched: even when sure nobody is looking or will find
> out, working as carefully, keeping the rules and taking nothing that is not one's own.

Labels: **good only when watched** / **good even when unwatched** (the draft's preferred labels).
"You are good only when watched." and "You are good even when unwatched." both read as meant
without the description, and the vice label is the only option that carries the half that is
new: good conduct in view.  The fallback, crooked / upright when unwatched, loses that half, and
"crooked" narrows the vice to fraud and theft, which is where
[unscrupulous](../../data/traits/instructions/unscrupulous.json) already is.  The known cost: the
virtue label contains the full label of [good](../../data/traits/instructions/good.json), whose first
pos instruction is "the honest path even when no one would ever know the difference".  "Upright"
would not avoid the virtue cluster either (finding 1).  Also rejected: eye-serving (archaic).
"Two-faced" is about talk; it is a registry candidate with that gloss, so leave the word to it.

Rule checks that needed no change: the word counts (30, 32) are inside the 18-32 band.  Neither
description uses a word from the hedge list.  The virtue's "the same unwatched as watched" is a
short gloss, not the label repeated.  "Looking" and "watching" are synonyms, not a different
trigger.  The virtue's "and" is right: it is the negation of the vice's "or" list, all three kept.
Neither description names its partner.

## Findings

The `nearest_existing` texts below are pasted into the queue as they stand, so the stems in them
are plain text; every trait they name is linked in the finding above them.

**1. The virtue pole's condition is already in ten existing traits.  The draft says the opposite.**
The draft says [dependable](../../data/traits/instructions/dependable.json),
[conscientious](../../data/traits/instructions/conscientious.json),
[rule-abiding](../../data/traits/instructions/rule_abiding.json) and
[honest](../../data/traits/instructions/honest.json) "name the conduct but not the condition".  In
fact the V2 generator attaches "whether or not anyone is watching" to virtues as a stock phrase,
in one pos instruction each:

- [trustworthy](../../data/traits/instructions/trustworthy.json) pos 4: "your behavior does not change
  based on who is watching", nearly the virtue's opening.
- [honest-humble (HEXACO)](../../data/traits/instructions/honest_humble_hexaco.json): its description
  has "keeping to the rules even when cheating would pay", and its pos 2 is this pole in one
  sentence.
- [good](../../data/traits/instructions/good.json) pos 1, [Hufflepuff](../../data/traits/instructions/hufflepuff.json)
  pos 1, [rule-abiding](../../data/traits/instructions/rule_abiding.json) pos 3 and 5,
  [dependable](../../data/traits/instructions/dependable.json) pos 2,
  [principled](../../data/traits/instructions/principled.json) pos 2,
  [responsible](../../data/traits/instructions/responsible.json) pos 5,
  [self-disciplined](../../data/traits/instructions/self_disciplined.json) pos 5 and
  [benevolent](../../data/traits/instructions/benevolent.json) pos 2.

The source is the template itself: its example pairs in
[regenerate_trait_instructions.py](../../data_analysis/regenerate_trait_instructions.py) teach the
phrase.  The "underhanded" / "aboveboard" pair has "break the rules whenever nobody is looking" and
"keeps the rules ... when nobody is watching"; the "corner-cutting" pair has "skip the checks
nobody will look at" and "whether or not anyone will ever see it".  None of these traits is
*defined* by the condition, so the pole is not a duplicate.  But expect its vector inside the
virtue cluster, nearer [good](../../data/traits/instructions/good.json),
[trustworthy](../../data/traits/instructions/trustworthy.json) and
[honest-humble](../../data/traits/instructions/honest_humble_hexaco.json) than
[guilt-prone](../../data/traits/instructions/guilt_prone.json).  So the pair's distinct content
sits mainly in the vice pole.  Also, [honest](../../data/traits/instructions/honest.json) in this
corpus is about speech, not taking things, so drop it from the draft's risk 2.  Fix, the virtue
entry's `nearest_existing`:

```text
good_even_when_unwatched: guilt_prone (a wrong gnaws at one though nobody knows of it; but that is conscience and feeling after the fact, with confession as relief; this pole is the conduct before the fact, with no feeling named); trustworthy (pos 4 'your behavior does not change based on who is watching', nearly this pole's opening, as one aspect of reliability); honest_humble_hexaco (description 'keeping to the rules even when cheating would pay'; pos 2 is this pole in one sentence, beside sincerity, modesty and no greed); good (pos 1 'the honest path even when no one would ever know the difference'); the same tag is in one instruction each of rule_abiding, dependable, principled, responsible, self_disciplined, hufflepuff and benevolent, from the generator's own example pairs. This pole is the only one defined by the condition. Judge test as for its partner.
```

**2. On the vice side, the lapse when unseen is in four traits; only the in-view half is new.**
[Unscrupulous](../../data/traits/instructions/unscrupulous.json) is unconditional in its description
("shrugging at the chance of being caught"), but not in its instructions.  Pos 3 has "the risk of
discovery seems low", pos 4 "as long as nobody calls you on it", pos 5 "wherever the rules go
unenforced".  The draft also missed
[preconventional (Kohlberg)](../../data/traits/instructions/preconventional_kohlberg.json) pos 4:
"When the risk of getting caught is low, the rules stop applying to you".
[Shame-prone](../../data/traits/instructions/shame_prone.json) pos 1 and 3 and
[punishment-fearing](../../data/traits/instructions/punishment_fearing.json) pos 2, 4 and 5 are as
the draft says.  None of the four has good conduct in view as part of the trait, so "doing
everything right while anyone is looking" is the clause that keeps the pole apart: never cut it.
Guard 3 in the draft becomes a requirement.  Fix, the vice entry's `nearest_existing`:

```text
good_only_when_watched: shame_prone (pos 1 'only holds back from doing wrong when others might see', pos 3 'behaves well only in front of an audience'; but defined by the sanction and its feelings: condemnation, ridicule even imagined, no relief in confessing); punishment_fearing (pos 2, 4, 5: wrongdoing held back only while getting caught is a real risk; defined by fear of punishment and the bargaining confession); unscrupulous (description unconditional, but pos 3-5 cut corners when discovery seems unlikely); preconventional_kohlberg (pos 4 'when the risk of getting caught is low, the rules stop applying'; defined by self-interest and the rule-giver's power). None has the in-view half, doing everything right while anyone is looking, which is this pole's only new content. Judge test: would it act differently if sure nobody would see or ever find out?
```

**3. The draft's `description_notes` asks for a question setting the generator is forbidden to
write.**  The V2 question rules say never to "mention an AI, an assistant, or a user", so "an AI
agent's task on someone's systems" cannot appear.  The notes also ask that "a few set the same
choice watched and unwatched".  A question set only while watched does not separate the poles (the
rules require that the two answers differ), so the contrast has to sit inside one question.  Fix,
two substitutions in the draft's `description_notes`:

- "an AI agent's task on someone's systems" becomes "a job done alone on someone else's computer
  systems".
- "a few set the same choice watched and unwatched (the manager in the room, the camera on, every
  action logged)" becomes "a few set the same choice in one question first watched, then
  unwatched (the manager in the room and then gone, the camera on and then broken, every action
  logged and then logging off)".

**4. The draft's risk 4, the placeholder label, is moot.**  The draft fears that the placeholder
`non-good only when watched` will be misread.  No model sees it:

- Under RogerV2, `build_roger_v2_instruction_prompt` leaves the opposite unnamed for a `non-X`
  label.
- The prompt of [generate_antonyms.py](../../data_analysis/generate_antonyms.py) carries only
  `positive_label`, the definition and the instructions.

Fix: drop that guard from the reading in the draft's § 7 step 4.

**5. The checks after generation (the draft's § 7 step 4), replaced by:**

1. **The vice side.**  Every one of its five pos instructions shows good conduct in view as well as
   the lapse when unseen.  Reroll any that has only the lapse (finding 2).  There is also no shame,
   ridicule, fear-of-punishment or confession language, as the draft says.
2. **The virtue side.**  Every pos instruction names a concrete chance to gain and the certainty of
   not being found out.  A generic virtue with "even when no one is watching" appended is what ten
   neighbours already have: reroll it (finding 1).
3. **Neither side** copies the template's example lines: "skip the checks nobody will look at",
   "break the rules whenever nobody is looking", "keeps the rules ... when nobody is watching".  The
   template forbids taking phrasing from the description, not from its own examples.
4. **The assistant frame**, as in the draft's risk 5.

Rerolls under the same description need no new antonym check.

## For Roger (either way)

The label form.  **Recommended:** good only when watched / good even when unwatched.  These state
the contingency, including the conduct in view.  **Alternative:** crooked / upright when unwatched,
which follows your "ruthless / honorable while playing" form.  It reads more vividly but drops the
conduct in view, and "upright" first suggests posture.
