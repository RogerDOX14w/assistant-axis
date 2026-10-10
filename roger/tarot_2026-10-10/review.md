# Review of the four Tarot gap drafts (2026-10-10)

Reviewer pass on [drafts.json](./drafts.json) (the walk: [tarot_walk.md](./tarot_walk.md)), against the description-writing rules 1-11 in [trait-pairs.md](../../.claude/rules/trait-pairs.md) § "Description-writing rules for new seeds (Sep 2026)".  Neighbours were read from their files and found by searching every trait description for the drafts' key words; the probe's overlap readings (0-4, where 4 means the same concept) are in [readings.jsonl](./probe/novelty/probe_tarot_m3/readings.jsonl).  None of the four stems exists as a trait or a role; none of the drafts has a hedge, names a partner or opens with its label word.  No API calls were made.

| draft | verdict | words |
|---|---|---|
| [amorous](../../data/traits/instructions/amorous.json) (not seeded yet) | seed with one fix | 27 |
| [strong-willed](../../data/traits/instructions/strong_willed.json) (not seeded yet) | seed with fixes (rewritten) | 28 |
| [self-reinventing](../../data/traits/instructions/self_reinventing.json) (not seeded yet) | seed as drafted | 29 |
| [dreamy](../../data/traits/instructions/dreamy.json) (not seeded yet) | seed with fixes | 26 |

## amorous (the Lovers): seed with one fix

**Fix.** "falling for people easily and wholly" becomes "falling hard and wholly for someone".  With "easily" and the plural "people", the clause describes someone who falls for a new person at every turn.  That pulls toward [flirty](../../data/traits/instructions/flirty.json) and [promiscuous](../../data/traits/instructions/promiscuous.json), contradicts the draft's own test ("love for one particular person") and the card's "one other person", and makes the trait easier to read as a passing mood.

> This means living for love: falling hard and wholly for someone, letting the heart choose, and building one's days, plans and loyalties around the person one loves.

**Label.** On its own, "You are amorous." reads first as a mood ("feeling amorous tonight") and leans sexual; the probe's filter gloss of the bare word ("romantic or sexual desire ... lingers near them") shows that lean.  The description supplies the lasting disposition ("living for love", building one's days around someone), and the text has nothing sexual in it, so the label holds.  The alternatives are worse.  [romantic](../../data/traits/instructions/romantic.json) is taken by the Romanticism style and is also a role ([romantic](../../data/roles/instructions/romantic.json)).  Lovestruck, smitten and besotted are states.  "Devoted" is broader and went to the gap registry for kin care.  Run the label-blind naming check ([`generate_antonyms.py --name-pos`](../../data_analysis/generate_antonyms.py)) after generation; only a blind name other than amorous would be a question for Roger.

**Nearest neighbours and the separating test.** The question to ask is "is romantic love for one person what the persona's life is built around?"  [lustful](../../data/traits/instructions/lustful.json) is sexual desire, and [flirty](../../data/traits/instructions/flirty.json) is playful banter that needs no real feeling (both read 2 in the probe).  [romantic](../../data/traits/instructions/romantic.json) as a trait is a style, emotion and imagination over analysis (read 1).  The role [romantic](../../data/roles/instructions/romantic.json) is an outlook, a belief in love and beauty, not being in love with someone.  [monogamous](../../data/traits/instructions/monogamous.json), [loyal](../../data/traits/instructions/loyal.json) and [happily-partnered](../../data/traits/instructions/happily_partnered.json) describe the shape of a relationship, faithfulness or satisfaction, not love as the centre of life.  [anxious-preoccupied attachment](../../data/traits/instructions/anxious_preoccupied_attachment.json) and [clingy](../../data/traits/instructions/clingy.json) are about fear of losing closeness.  The probe's flag that amorous might complete [asexual](../../data/traits/instructions/asexual.json) as a pair does not hold: asexual is an orientation, and amorous is a disposition.

## strong-willed (the Chariot): seed with fixes

**Is it a real gap?** Yes, but a narrow one.  In plain English, strong-willed means doing what one wants even when others advise against it.  No trait in the corpus covers that:

- [persevering](../../data/traits/instructions/persevering.json) keeps going through failure and time.
- [unyielding](../../data/traits/instructions/unyielding.json) holds a stated position in a dispute.
- [dominant](../../data/traits/instructions/dominant.json) steers other people.
- [self-disciplined](../../data/traits/instructions/self_disciplined.json) masters one's own appetite.
- [decisive](../../data/traits/instructions/decisive.json) commits to a choice.

The corpus also has no opposite pole for it (no weak-willed, pliable or easily led).  The probe's 3 against persevering (Sonnet 3, Opus 3; this trait's cut-off, the reading at which a candidate counts as covered, was 4) was earned by a filter gloss that the persevering-flavoured hint had steered ("pressing on ... through obstacles, discouragement ... until the goal is reached").  In the same registry, [tenacious](../../data/candidates/registry.snapshot.jsonl) was covered by persevering (3, 3), and stubborn read 3 against unyielding.  So the description has to keep to resisting influence.

**What was wrong with the draft.** Its last clause, "driving through every obstacle and objection until it is done", is persevering's content, and it ends on persevering's own words ("stopping only when it is done").  Its opening, "by force of will", half-repeats the label (rule 1).  The fix centres the trait on not being talked out of anything and on carrying one's own course over other people's objections.  Endurance through failure, the persevering part, is left out.

> This means doing what one has set one's mind on: no advice, coaxing or pressure talks one out of it, and one pushes it through over everyone's objections.

**Test.** Does the persona carry out what it has decided although others try to talk it out of it?  The neighbours ask different questions:

- [persevering](../../data/traits/instructions/persevering.json): does it keep at a goal through failure?
- [unyielding](../../data/traits/instructions/unyielding.json): does it refuse to concede a point in an argument?  A strong-willed persona can concede the point and still do as it likes.
- [dominant](../../data/traits/instructions/dominant.json): does it steer other people?

The probe gave the trait alignment score 2 ("near alignment"): resistance to being talked out of a course bears on corrigibility, a reason to keep it.  The antonym check will show where the trait sits:

- [accommodating](../../data/traits/instructions/accommodating.json) would put it on [unyielding](../../data/traits/instructions/unyielding.json).
- [defeatist](../../data/traits/instructions/defeatist.json) would put it on [persevering](../../data/traits/instructions/persevering.json).
- Either answer means it is covered, and it should come back to Roger.
- Pliable, weak-willed or easily led would mean an axis of its own.

## self-reinventing (Death and Judgement): seed as drafted

> This means letting old ways and old selves end: taking hard stock of one's life, answering an inner call to start over, and becoming someone new more than once.

"More than once" makes it a lasting disposition (rule 11).  "Taking hard stock" and "an inner call" keep it on the card's reading: the change comes from within, after a reckoning.  It is not forced by events, chosen for an audience, or made for a better offer.

**Label.** The bare word leans toward remaking one's image or career.  The probe's filter gloss was "remaking one's own identity or public image ... as circumstances or ambitions shift".  The description pulls it back to the card, and the alternatives are worse: self-renewing is not idiomatic, born-again is religious, and transformed is a state.  Keep the label, and let the same naming check after generation confirm it.

**Nearest neighbours and the separating test.** Does the persona remake its own life and self after taking stock, more than once?  The neighbours:

- [performative](../../data/traits/instructions/performative.json) adjusts its image to each audience (read 2 in the probe).
- [course-correcting](../../data/traits/instructions/course_correcting.json) changes a task's approach.
- [self-uncertain](../../data/traits/instructions/self_uncertain.json) has no answer to "who am I?" from week to week, where this persona has a clear self at every stage.
- [fickle](../../data/traits/instructions/fickle.json) goes cold on things at the first letdown.
- [job-hopping](../../data/traits/instructions/job_hopping.json) leaves employers for better offers.
- The role [convert](../../data/roles/instructions/convert.json) has one religious before-and-after.

[self-certain](../../data/traits/instructions/self_certain.json) ("describing oneself the same way year after year") may come back from the antonym check.

## dreamy (the Moon): seed with fixes

**What was wrong with the draft.** Two things.

- **"Losing track of the room" belongs to absorption-prone.**  Together with "drifting into daydreams", this clause is the daydream branch of [absorption-prone](../../data/traits/instructions/absorption_prone.json) ("a daydream that the room, the clock and oneself drop away").
- **"Seeing more in shadows and half-heard things than is there" is a different trait.**  This is the Moon's fearful side, misperception, which the walk already found covered by [anxious](../../data/traits/instructions/anxious.json), [superstitious](../../data/traits/instructions/superstitious.json), [paranoid](../../data/traits/instructions/paranoid.json) and [credulous](../../data/traits/instructions/credulous.json).  Plain "dreamy" does not include it, and keeping it would put two concepts in one description.

The fix keeps the inner fantasy life and adds the other two parts of the plain sense: being only half present ("half-hearing"), and impractical ("vague and unpractical", Oxford).

> This means living half in a world of one's own imagining: drifting into daydreams, half-hearing what is said, and spinning plans that never leave one's head.

The opening picks the sense, so the US slang "dreamy" (good-looking) and "dreamy music" do not need a contrast clause.

**Nearest neighbours and the separating test.** Is the persona's mind away in things it imagines during ordinary moments, half present and unpractical?  The neighbours:

- [absorption-prone](../../data/traits/instructions/absorption_prone.json) is swallowed whole by a book, music or a sunset; the point there is depth, here it is being half present (read 2 in the probe).
- [distractible](../../data/traits/instructions/distractible.json) is pulled off task by every noise (2).
- [whimsical](../../data/traits/instructions/whimsical.json) is playful, eccentric fancy shown to others (2).
- [pensive](../../data/traits/instructions/pensive.json) muses on real things, wistfully.
- [ethereal](../../data/traits/instructions/ethereal.json) is a way of speaking.
- [oblivious](../../data/traits/instructions/oblivious.json) misses changes in its surroundings, with no inner world named.
- [Pisces](../../data/traits/instructions/pisces.json) and [open (Big Five)](../../data/traits/instructions/open_big_five.json) contain daydreaming as one part of a bundle.

The backlog facet Imagination (IPIP-NEO) would be a deliberate near-duplicate in the standards register if it is ever imported.

## Either-way choices for Roger

None now.  The one conditional: if the naming check after generation returns a blind name other than amorous or self-reinventing, the label comes back to Roger with that answer.

## Final entries

```json
[
  {"stem": "amorous", "label": "amorous",
   "description": "This means living for love: falling hard and wholly for someone, letting the heart choose, and building one's days, plans and loyalties around the person one loves.",
   "verdict": "seed with fixes"},
  {"stem": "strong_willed", "label": "strong-willed",
   "description": "This means doing what one has set one's mind on: no advice, coaxing or pressure talks one out of it, and one pushes it through over everyone's objections.",
   "verdict": "seed with fixes"},
  {"stem": "self_reinventing", "label": "self-reinventing",
   "description": "This means letting old ways and old selves end: taking hard stock of one's life, answering an inner call to start over, and becoming someone new more than once.",
   "verdict": "seed as drafted"},
  {"stem": "dreamy", "label": "dreamy",
   "description": "This means living half in a world of one's own imagining: drifting into daydreams, half-hearing what is said, and spinning plans that never leave one's head.",
   "verdict": "seed with fixes"}
]
```
