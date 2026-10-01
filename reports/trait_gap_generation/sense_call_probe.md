# A small call with no other context: first test of Roger's proposal

Run 2026-09-29 (Fable), after Roger proposed splitting the rubric into small calls that are tuned
one at a time.  Cost $0.11.  Script, prompts, raw answers and cost record:
[probe_sense_call/](./probe_sense_call/) ([probe.py](./probe_sense_call/probe.py),
[results.jsonl](./probe_sense_call/results.jsonl), [responses.jsonl](./probe_sense_call/responses.jsonl),
[run.json](./probe_sense_call/run.json), [usage.json](./probe_sense_call/usage.json)).

## What was asked

Two small prompts, each sent with nothing else: no mention of traits, of the corpus, or of what the
answer is for.  Model Haiku 4.5 at temperature 0, twenty words to a call.  The wording of both is
mine and is a first attempt; the full text of each is in [run.json](./probe_sense_call/run.json).

* **A, your proposal.**  "A persona is given a one-line instruction of the form "You are <label>." and
  nothing else."  Does that have a clear and obvious meaning?  If so, the one or two primary
  meanings, and any less obvious ones apart.  It is told that having no clear meaning is a normal
  answer, with octagonal and alkaline as examples.
* **B, the dictionary entry of my version 5 draft.**  The word's meanings in ordinary use, and for
  each what it is ordinarily said of: people, things, actions or abstractions.  It is told not to
  supply a use that the word does not already have.

A word is "accepted" by A when it has a clear meaning, and by B when its entry lists a meaning said of
people.  Neither call says whether the meaning is a trait.  That is the next step, and a separate
one.

## The result in one table

| group | words | A accepts | B accepts | both accept | both reject |
|---|---|---|---|---|---|
| the 50 words version 4 passed as traits | 50 | 41 | 30 | 29 | 8 |
| your two examples, hexagonal and chemical | 2 | 0 | 0 | 0 | 2 |
| twelve words said of things | 12 | 1 | 0 | 0 | 11 |
| sixteen plain trait words | 16 | 16 | 16 | 16 | 0 |
| the six September rejects | 6 | 5 | 3 | 3 | 1 |
| eight words with an established figurative sense for people | 8 | 8 | 8 | 8 | 0 |
| five corpus labels that the filter has rejected as "relating to" words | 5 | 4 | 0 | 0 | 1 |

## What I take from it

1. **Your diagnosis holds.**  Version 4 passed all 50 of the first group.  Asked in a small call with
   nothing else in it, the same model rejects 9 of them under A and 20 under B.  Both reject
   hexagonal and chemical, and eleven or twelve of the twelve other words for things.  Both accept
   all sixteen plain traits.  So the pushing came from the surrounding context, as you thought.
2. **Your framing fits the corpus better than mine.**  B rejects all five corpus labels in the last
   group, because a dictionary says concrete and anecdotal are said of things and accounts.  A
   accepts four of the five, reading them as ways of speaking, which is how the corpus uses them.
3. **Your framing still lets a few coined meanings through.**  leavened comes back as "made lighter or
   more interesting", and hit-and-run, illegal and integrated are accepted.  B rejects all four.
   These are what the first call would be tuned on, by itself, as you propose.
4. **The earlier oddity with cold is gone.**  Asked how a persona told "You are cold." behaves, the
   model described shivering.  Asked whether the instruction has a clear meaning, it answers
   unfriendly or distant.  The question about behaviour was the cause.
5. **Where the two disagree is where the judgement calls are.**  They disagree on 20 of the 99
   words.  Those are almost all words one could argue about.  So B may be worth keeping as a cheap
   second signal, with a disagreement sending the word to your judgement-call table.

## Every word

### The 50 words version 4 passed as traits

These are the words of [random_traits_for_marks.md](./random_traits_for_marks.md).  Your marks belong
in that file; the column here is only for notes on the two readings.

| word | A: "You are X." | B: dictionary entry, meanings said of people | agree | your mark |
|---|---|---|---|---|
| argumentative | prone to arguing; quarrelsome  (less obvious: enjoying debate) | prone to arguing or quarrelling | both accept | |
| barehanded | no clear meaning | none said of people: with bare hands, without tools or weapons [actions] | both reject | |
| bothersome | annoying; troublesome | none said of people: causing trouble, annoyance, or inconvenience [things, actions] | only A accepts | |
| clinical | detached and objective  (less obvious: unemotional; analytical) | detached, objective, unemotional (figurative) | both accept | |
| common | ordinary; of low social status  (less obvious: widespread; vulgar) | of ordinary or low social rank | both accept | |
| corruptible | capable of being bribed  (less obvious: morally compromisable) | capable of being bribed or morally corrupted | both accept | |
| Danish | from Denmark | of or relating to Denmark, its people, or language | both accept | |
| decided | determined; resolute | having reached a firm decision | both accept | |
| disrespectful | showing lack of respect | showing lack of respect or courtesy | both accept | |
| Eastern Orthodox | adhering to Eastern Orthodox Christianity | of or relating to the Eastern Orthodox Church | both accept | |
| false | deceptive; disloyal  (less obvious: untrue) | disloyal or treacherous (figurative) | both accept | |
| fluffy | no clear meaning | none said of people: soft, light, and airy [things]; insubstantial or trivial [abstractions] | both reject | |
| frosty | cold in manner; unfriendly | cold in manner; unfriendly (figurative) | both accept | |
| full-time | working full-time | none said of people: occupying or involving the whole of the normal working week [things, abstractions] | only A accepts | |
| grubby | dirty; grimy  (less obvious: morally sordid) | none said of people: dirty or grimy [things]; sordid or disreputable [abstractions] | only A accepts | |
| high-energy | energetic and enthusiastic | having or involving great energy or intensity | both accept | |
| hit-and-run | fleeing after causing an accident  (less obvious: making a quick attack and leaving) | none said of people: denoting a traffic accident in which the driver leaves without stopping [things, abstractions]; involving a quick attack followed by withdrawal [actions, abstractions] | only A accepts | |
| ho-hum | dull; uninteresting | none said of people: dull, uninteresting, or mediocre [things, abstractions] | only A accepts | |
| illegal | unlawful | none said of people: contrary to or forbidden by law [actions, things] | only A accepts | |
| incestuous | involved in incest  (less obvious: excessively insular) | involving or guilty of incest | both accept | |
| integrated | part of a unified whole; accepted without discrimination  (less obvious: psychologically well-adjusted) | none said of people: combined or unified into a single whole [things, abstractions]; including people of different races on equal terms [things] | only A accepts | |
| Junior | younger person with same name; third-year student | the younger of two people with the same name, especially a son; a student in the third year of secondary school or college; lower in rank or status | both accept | |
| lawless | not obedient to law; disregarding legal rules | not governed by or obedient to law | both accept | |
| leavened | made lighter or more interesting | none said of people: raised or made light with leaven such as yeast [things]; permeated or modified by an influence [abstractions] | only A accepts | |
| middle | of middle age; of middle class  (less obvious: occupying intermediate position) | none said of people: the point or part equidistant from extremes [things, abstractions]; of intermediate size, quality, or position [things] | only A accepts | |
| migratory | moving seasonally from place to place | moving from one place to another, especially seasonally | both accept | |
| noncompetitive | not inclined to compete; not involving competition | none said of people: not involving competition or competitors [things, actions] | only A accepts | |
| nonsovereign | no clear meaning | none said of people: not possessing sovereignty or independent authority [things] | both reject | |
| nonturbulent | no clear meaning | none said of people: not turbulent; calm or smooth [things, abstractions] | both reject | |
| one-time | former; occurring only once | former; previously | both accept | |
| part-time | employed for less than full duration | for or involving less than the standard or full time | both accept | |
| pedagogic | relating to teaching; characteristic of a teacher | none said of people: relating to teaching or education [things, abstractions] | only A accepts | |
| present | being in a place at this time  (less obvious: currently existing) | in attendance or at a particular place | both accept | |
| presentable | suitable in appearance to be seen in public | fit to be presented or shown; of acceptable appearance | both accept | |
| puzzling | confusing or difficult to understand | none said of people: confusing or difficult to understand [things, abstractions] | only A accepts | |
| raised | brought up or reared  (less obvious: elevated in rank or position) | brought up or reared | both accept | |
| sophomore | second-year student | a student in the second year of secondary school or college | both accept | |
| southeastern | no clear meaning | none said of people: of, in, or toward the southeast [things] | both reject | |
| sympathetic | feeling or showing sympathy; inclined to agree or support | showing or expressing sympathy; inclined to agree or support | both accept | |
| Tuscan | from or relating to Tuscany | a native or inhabitant of Tuscany | both accept | |
| twisted | morally corrupt; psychologically disturbed  (less obvious: cunning or devious) | morally or mentally distorted or corrupt (figurative) | both accept | |
| unconditioned | no clear meaning | not trained or accustomed through conditioning | only B accepts | |
| unfinished | no clear meaning | none said of people: not completed or done [things, actions]; lacking a final surface treatment or polish [things] | both reject | |
| ungrammatical | no clear meaning | none said of people: not following the rules of grammar [abstractions] | both reject | |
| unobtrusive | not drawing attention to oneself; modest and inconspicuous | not prominent or noticeable; inconspicuous | both accept | |
| unreachable | emotionally distant; inaccessible or aloof  (less obvious: difficult to contact or communicate with) | impossible to contact or communicate with | both accept | |
| unsharpened | no clear meaning | none said of people: not made sharp; still dull [things] | both reject | |
| virulent | intensely hostile or bitter  (less obvious: venomous in speech or manner) | intensely bitter, hostile, or spiteful (figurative) | both accept | |
| warlike | aggressive and combative; inclined toward conflict  (less obvious: martial in spirit or bearing) | inclined toward or ready for war | both accept | |
| wishy-washy | indecisive and weak-willed; lacking conviction or backbone | weak or feeble in character or conviction | both accept | |

### Your two examples, hexagonal and chemical, and twelve words said of things

| word | A: "You are X." | B: dictionary entry, meanings said of people | agree |
|---|---|---|---|
| hexagonal | no clear meaning | none said of people: having six angles and six sides [things] | both reject |
| chemical | no clear meaning | none said of people: relating to chemistry or chemicals [things, abstractions]; produced by or involving chemical processes [things] | both reject |

| word | A: "You are X." | B: dictionary entry, meanings said of people | agree |
|---|---|---|---|
| portable | no clear meaning | none said of people: able to be carried or moved easily [things] | both reject |
| linear | no clear meaning | none said of people: relating to or arranged in a line [things, abstractions]; progressing from one stage to the next in a sequence [abstractions] | both reject |
| graphic | no clear meaning | none said of people: relating to visual representation or design [things, abstractions]; vividly or starkly described or depicted [abstractions] | both reject |
| organic | no clear meaning | none said of people: relating to or derived from living organisms [things]; produced without synthetic chemicals or pesticides [things] | both reject |
| brackish | no clear meaning | none said of people: slightly salty [things] | both reject |
| watertight | no clear meaning | none said of people: impermeable to water [things]; leaving no room for doubt, dispute, or escape [abstractions] | both reject |
| threadbare | worn out and exhausted  (less obvious: shabby in appearance) | none said of people: worn thin or shabby from use [things]; lacking freshness or originality; trite [abstractions] | only A accepts |
| laminated | no clear meaning | none said of people: made of layers of material bonded together [things] | both reject |
| municipal | no clear meaning | none said of people: of or belonging to a city or town government [things, abstractions] | both reject |
| waterproof | no clear meaning | none said of people: not allowing water to pass through [things]; to treat something so it resists water [actions] | both reject |
| corrugated | no clear meaning | none said of people: formed into parallel ridges and grooves [things] | both reject |
| unleaded | no clear meaning | none said of people: without added lead [things] | both reject |

### Sixteen plain trait words

| word | A: "You are X." | B: dictionary entry, meanings said of people | agree |
|---|---|---|---|
| bossy | domineering; inclined to give orders | domineering and fond of ordering people about | both accept |
| fickle | changeable in affections or loyalties  (less obvious: unreliable; inconstant) | changeable in affections or opinions | both accept |
| smug | self-satisfied; complacent | self-satisfied and complacent | both accept |
| nosy | prying; overly interested in others' affairs | inquisitive about other people's business | both accept |
| wily | cunning; crafty | using stratagems and cunning | both accept |
| cheeky | impudent; disrespectfully bold | impertinent or disrespectful but in an amusing way | both accept |
| pushy | aggressively ambitious; assertive | assertively ambitious or forceful | both accept |
| garrulous | excessively talkative | given to excessive talking | both accept |
| gullible | easily deceived; credulous | easily fooled or deceived | both accept |
| shrewd | astute; having keen judgment | astute and having good judgment | both accept |
| haughty | arrogantly superior  (less obvious: disdainful; aloof) | arrogantly superior and scornful | both accept |
| coy | affectedly shy; affectedly modest | affectedly or playfully shy; evasively reluctant to give information | both accept |
| petulant | childishly sulky; bad-tempered | childishly sulky or irritable | both accept |
| headstrong | willfully stubborn; determined to have one's own way | stubbornly determined to do as one wishes | both accept |
| snobbish | showing disapproval of those considered inferior  (less obvious: elitist; condescending) | believing oneself superior and despising others | both accept |
| taciturn | habitually silent; uncommunicative | habitually silent or uncommunicative | both accept |

### The six september rejects

| word | A: "You are X." | B: dictionary entry, meanings said of people | agree |
|---|---|---|---|
| disciplinary | strict, enforcing rules; relating to an academic field  (less obvious: prone to imposing discipline) | none said of people: concerning punishment or correction of behaviour [actions, abstractions]; relating to a specific academic subject or field [abstractions] | only A accepts |
| engaging | interesting and holding attention  (less obvious: charming or personable) | charming or attractive in manner | both accept |
| economic | no clear meaning | none said of people: relating to the economy or economics [abstractions, things]; giving good value for money; not wasteful [things] | both reject |
| balanced | fair and impartial; emotionally stable  (less obvious: well-proportioned) | emotionally stable and sensible (figurative) | both accept |
| empowered | given authority or ability to act  (less obvious: feeling confident and in control) | given legal or official authority to act; made to feel confident and in control (figurative) | both accept |
| emotive | expressing emotion readily  (less obvious: prone to emotional responses) | none said of people: arousing strong feeling or emotion [things, abstractions] | only A accepts |

### Eight words with an established figurative sense for people

| word | A: "You are X." | B: dictionary entry, meanings said of people | agree |
|---|---|---|---|
| cold | unfriendly or distant in manner  (less obvious: unemotional or detached) | unfriendly, distant, or lacking warmth (figurative) | both accept |
| warm | friendly and affectionate  (less obvious: welcoming or cordial) | friendly, affectionate, or kind (figurative) | both accept |
| bright | intelligent or quick-witted  (less obvious: cheerful or optimistic) | intelligent or clever (figurative); cheerful or optimistic (figurative) | both accept |
| sharp | intelligent or quick-witted  (less obvious: harsh or cutting in speech) | keen, quick, or intelligent (figurative) | both accept |
| dense | slow to understand | stupid or slow to understand (figurative) | both accept |
| prickly | easily irritated or touchy  (less obvious: defensive or hostile) | irritable, touchy, or easily offended (figurative) | both accept |
| lukewarm | lacking enthusiasm or commitment  (less obvious: indifferent or halfhearted) | lacking enthusiasm or conviction (figurative) | both accept |
| magnetic | charismatic and attracting others | attracting or compelling attention and interest (figurative) | both accept |

### Five corpus labels that the filter has rejected as "relating to" words

| word | A: "You are X." | B: dictionary entry, meanings said of people | agree |
|---|---|---|---|
| concrete | practical and specific rather than abstract | none said of people: made of concrete material [things]; specific, tangible, and real rather than abstract [abstractions] | only A accepts |
| rhetorical | given to using rhetoric or persuasive language | none said of people: relating to rhetoric or effective speaking and writing [abstractions]; asked for effect rather than to get an answer [abstractions] | only A accepts |
| interdisciplinary | no clear meaning | none said of people: involving or combining multiple academic disciplines [abstractions] | both reject |
| deterministic | believing in determinism | none said of people: based on the belief that events are determined by prior causes [abstractions] | only A accepts |
| anecdotal | relying on personal stories rather than data | none said of people: based on anecdotes or personal accounts rather than systematic evidence [abstractions] | only A accepts |


---

## Against Roger's marks (added 2026-09-29, after he marked the 50)

His marks and notes are in [random_traits_for_marks.md](./random_traits_for_marks.md).

### The count

| your mark | words | version 4 passed | A accepts | B accepts |
|---|---|---|---|---|
| trait | 28 | 28 | 25 | 20 |
| trait, with a caveat | 12 | 12 | 8 | 5 |
| unclear | 8 | 8 | 6 | 5 |
| not a trait | 2 | 2 | 2 | 0 |

### What the marks say

1. **Version 4 was less wrong than I had said.**  I wrote that about a quarter of the 50 looked like
   senses the model had invented.  By Roger's marks two of the 50 are not traits, eight are unclear,
   and forty are traits, twelve of them with a caveat.  He marks nonturbulent and ungrammatical as
   plain traits, and leavened as a trait with a caveat.  My reading was stricter than his.
2. **The fault his notes point to is the choice of sense, not trait-hood.**  In most of the 22 qualified
   rows the sense that version 4 judged is a fair trait, but the word has another sense that is more
   obvious, or several senses with no clear winner.
3. **His notes fall into four kinds**, and they belong to different steps:

   | kind of note | words | the step that should catch it |
   |---|---|---|
   | a more obvious sense overshadows the trait sense | decided, false, frosty, grubby, fluffy, leavened, present, raised, unfinished, unreachable | the sense step |
   | several senses with no clear winner, or too vague | common, integrated, Junior, middle, nonsovereign, one-time, unconditioned, unsharpened | the sense step, though vagueness may belong later |
   | the sense is a state | barehanded, ho-hum, and unreachable in part | the kind step |
   | not a trait: an action, or a property of acts | hit-and-run, illegal | the kind step |

4. **Neither of my two prompts is the right first step, and each has half of it.**
   * A gates well.  It accepts 25 of his 28 plain traits, where B accepts 20.  B wrongly turns away
     bothersome, puzzling, pedagogic and full-time, because a dictionary says they are said of things
     or of work.
   * B lists well.  Its entries give every meaning in order, the literal one included, and they match
     his notes closely: for decided it gives "having reached a firm decision", for false "not true or
     correct" first, for leavened the yeast sense first, for raised "lifted" first.
   * A misses all of those, and the cause is my wording, not his idea.  I told it to list only
     meanings said of a person.  His proposal did not say that: it asked what the instruction means,
     and for the meanings to be divided into primary and less obvious.

### The first step, corrected

Ask what "You are <label>." could be taken to mean, most obvious first, **every reading included**:
literal, bodily, passing, figurative.  Mark each as primary or less obvious.  Say when no reading is
clear.  Do not ask what kind of thing each reading is; that is the next step's question.

### The second step, and the rule that joins them

The kind step takes one reading at a time and says what it is: a trait, a membership, a passing
state, a physical feature, a role, an action or event, pure praise or blame, or a reading that says
nothing about a persona at all, such as having had yeast added.  "Action" is new, from the note on
hit-and-run.

The rule that joins the two is then code and not prompt:

| what the two steps found | outcome | Roger's case |
|---|---|---|
| the most obvious reading is a trait, alone | trait | 1 |
| two primary readings, both traits | trait, with a note | 2 |
| the most obvious reading is not a trait, and a less obvious one is | set aside as overshadowed; not used for gap filling | 3 and 4, and his answer R3 |
| the most obvious reading is a state, a physical feature or a role | its own queue | decisions 3 and 12 |
| no clear reading, or none that is about a persona | rejected | |

### Every qualified word

| word | your mark and note | what version 4 judged | A: "You are X.", as I worded it | B: dictionary entry, every meaning in order |
|---|---|---|---|---|
| barehanded | trait: specifically a state | facing challenges without weapons or tools | no clear meaning | 1. with bare hands, without tools or weapons [actions] |
| common | trait (but probably too vauge/mutilsemous to be a useful one) | ordinary and unremarkable | ordinary; of low social status (less obvious: widespread; vulgar) | 1. occurring or found often; frequent [things, abstractions]; 2. shared by or belonging to two or more people or groups [things, abstractions]; 3. of ordinary or low social rank [people] |
| decided | unclear: the "you have just made a decision" non-trait sense seems the most obvious | resolute and firm in manner | determined; resolute | 1. clear, definite, unmistakable [things, abstractions]; 2. having reached a firm decision [people] |
| false | unclessr (its plain sense of factually incorrect is unhelpfully strong) | dishonest and prone to deception | deceptive; disloyal (less obvious: untrue) | 1. not true or correct [abstractions]; 2. not genuine or artificial [things]; 3. disloyal or treacherous [people, figurative] |
| fluffy | trait, but also has a physical sense | light and insubstantial in manner | no clear meaning | 1. soft, light, and airy [things]; 2. insubstantial or trivial [abstractions, figurative] |
| frosty | trait (two senses, the more common a physical state) | cold and unfriendly in manner | cold in manner; unfriendly | 1. cold with frost; freezing [things]; 2. cold in manner; unfriendly [people, abstractions, figurative] |
| grubby | trait (two senses, the more obvious a physical state, also has a metaphorical version) | habitually dirty and unwashed | dirty; grimy (less obvious: morally sordid) | 1. dirty or grimy [things]; 2. sordid or disreputable [abstractions, figurative] |
| hit-and-run | not a trait, this is and action | causing harm and fleeing without responsibility | fleeing after causing an accident (less obvious: making a quick attack and leaving) | 1. denoting a traffic accident in which the driver leaves without stopping [things, abstractions]; 2. involving a quick attack followed by withdrawal [actions, abstractions, figurative] |
| ho-hum | trait: specifically a state | bored and unimpressed | dull; uninteresting | 1. dull, uninteresting, or mediocre [things, abstractions] |
| illegal | not a trait | acting against the law or having illegal status | unlawful | 1. contrary to or forbidden by law [actions, things] |
| integrated | trait (but a bit vaugue/unclear/polysemous) | fitting into and accepted by a social group or community | part of a unified whole; accepted without discrimination (less obvious: psychologically well-adjusted) | 1. combined or unified into a single whole [things, abstractions]; 2. including people of different races on equal terms [things] |
| Junior | unclear: multiple meanings, can also just mean younger than | son with the same name as father | younger person with same name; third-year student | 1. the younger of two people with the same name, especially a son [people]; 2. a student in the third year of secondary school or college [people]; 3. lower in rank or status [people] |
| leavened | trait (but to me unhelpfully overshadowed by the "having had yeast added" sense) | lightened with humor or levity | made lighter or more interesting | 1. raised or made light with leaven such as yeast [things]; 2. permeated or modified by an influence [abstractions, figurative] |
| middle | unclear: multiple senses | the middle child in a family | of middle age; of middle class (less obvious: occupying intermediate position) | 1. the point or part equidistant from extremes [things, abstractions]; 2. of intermediate size, quality, or position [things] |
| nonsovereign | unclear: also means "is not a king or queen" | from a territory without sovereignty | no clear meaning | 1. not possessing sovereignty or independent authority [things] |
| one-time | unclear: too vaugue | having done something once in the past | former; occurring only once | 1. occurring or existing only once [things, actions]; 2. former; previously [people, things] |
| present | trait: also means "not (literally) absent" | attending and paying attention to what is happening | being in a place at this time (less obvious: currently existing) | 1. existing or occurring now [things, abstractions]; 2. in attendance or at a particular place [people]; 3. a gift [things]; 4. to give or offer formally [actions] |
| raised | unclear: "has been lifted up" meaning is a little confusing. "raised <foo>" is a more common formulation | brought up in a particular place or way | brought up or reared (less obvious: elevated in rank or position) | 1. lifted or moved to a higher position [things]; 2. brought up or reared [people]; 3. increased in amount or level [abstractions]; 4. made with a raised or embossed surface [things] |
| unconditioned | trait (but rather vague) | not shaped by conditioning or habit | no clear meaning | 1. not dependent on or limited by conditions [abstractions]; 2. not trained or accustomed through conditioning [people, things] |
| unfinished | trait, but the more obvious sense is that they are unfinished, rather habitually not finishing things | leaving tasks and projects incomplete | no clear meaning | 1. not completed or done [things, actions]; 2. lacking a final surface treatment or polish [things] |
| unreachable | trait (also a state) | keeping oneself distant and hard to contact | emotionally distant; inaccessible or aloof (less obvious: difficult to contact or communicate with) | 1. impossible to reach or get to [things]; 2. impossible to contact or communicate with [people] |
| unsharpened | unclear | mentally dull or unclear | no clear meaning | 1. not made sharp; still dull [things] |

### Where my reading differs from Roger's marks

Roger asked for these, and said his marks are not to be taken as golden.  On 41 of the 50 I agree
with his mark as it stands.  The nine where I differ, in rough order of how much it matters:

| word | his mark | my reading | does it change the outcome? |
|---|---|---|---|
| southeastern | trait | Too vague by the test he applied to one-time: southeastern what?  The word names a direction within some country that the label does not give | yes: I would set it aside as unclear |
| presentable | trait | About appearance and grooming.  By his own wording of the physical rule it has little effect on how a persona acts or talks | yes: I would send it to the physical list, or call it unclear |
| incestuous | trait | An act or a relationship, not a disposition, and a text persona can hardly show it.  It also raises the question of content the generator should not be asked to produce | yes: I would mark it not a trait, or hold it for his call |
| ho-hum | trait: specifically a state | Said of things: a ho-hum film.  The sense "bored and unimpressed" is one version 4 supplied for a person | yes: I would reject it at the sense step, not send it to the states queue |
| barehanded | trait: specifically a state | A manner of doing something, fighting barehanded, not a condition a person is in | yes: I would reject it at the sense step |
| nonturbulent | trait | Its parts give "not turbulent", so calm, which a reader can work out.  I first thought it coined; I now think his mark is right.  It is a poor label because calm exists, and that is for the novelty step to say, not the filter | no |
| leavened | trait, overshadowed | Used with a complement, leavened with humor, and said of talk or writing.  Bare, the word does not mean humorous.  I would call the sense coined | no: set aside either way |
| unfinished | trait, overshadowed | The word does not have the sense "habitually not finishing".  Coined | no: set aside either way |
| unsharpened | unclear | Coined | no: set aside either way |

Two general points behind these.

* **He marked whether the sense as described is a trait; I was asking whether the label would call
  that sense to mind.**  Both questions matter, and they belong to different steps: the first to the
  kind step, the second to the sense step.  His notes already make that split, which is why most of
  my differences change nothing.
* **A word can pass both steps and still be a poor label**, because a better-known word already says
  it.  nonturbulent beside calm is the example.  That is the novelty step's business, in milestone
  M3, and the filter should not try to do it.


---

## The first step, second and third attempts (added 2026-09-29)

Two further runs on the same 99 words, after Roger's marks and his answers.  Records:
[probe_sense_kind_v2/](./probe_sense_kind_v2/) (sense and kind together, $0.12) and
[probe_sense_v3/](./probe_sense_v3/) (sense alone, $0.08); each holds its script, prompts in
`run.json`, raw answers and cost record.

### What the second attempt showed

It listed every reading, literal ones included, and a second call sorted each reading into a kind.
Two faults in the first step:

* **It ranked meanings as a dictionary does, not as readings of the instruction.**  For twisted it put
  "body bent" first and for virulent "poisonous", so two words Roger marked as plain traits were set
  aside.
* **Its vagueness question barely fired.**  It flagged southeastern and Tuscan, and none of common,
  one-time, raised or integrated.

The kind step, tried once and not tuned, made errors of its own: bothersome came back as pure blame,
pedagogic as a role.  Following Roger's advice it is left alone until the first step is settled.

### The third attempt: the prompt

````text
A persona is given a one-line instruction, "You are <label>.", and nothing else. For each label below, say how a reader would take that instruction.

Some labels give the instruction no meaning a reader could use. "You are octagonal." and "You are alkaline." are like that: the words are about shapes and substances. That is a normal answer.

For each label:
- note: one short sentence on what the word ordinarily means and what it is ordinarily said of. Write this first.
- first_thought: what comes to mind first on meeting the bare word, in a few plain words, whatever the word is said of.
- readings: the ways a reader could take "You are <label>." as saying something about the persona, the most likely first, at most four. Rank them by how likely a reader is to take the instruction that way, not by how common the meaning is in general. Include readings about the body, about a passing condition or situation, and about standing, as well as readings about character. Give each in a few plain words. Mark it "primary" if it is one of the one or two readings most readers would arrive at, and "secondary" if it is less likely. Do not say whether a reading is a personality trait; that is not your question. If the instruction has no reading about the persona, give an empty list.
- usable: true when at least one reading is clear enough that a persona given only this instruction would know what is being asked of it. False when none is, or when a reader would have to invent one.
- overshadowed: true when the first thought is about something other than a person, and is so much more familiar than any reading that it would get in a reader's way: the reader thinks of the other thing first and has to work to reach the reading. False when the word is well known in its use for people, even if it began as a word for things.
- vague: true when even the most likely reading would leave a persona unsure what is being asked. That happens when the label leaves out something the reader needs ("adjacent" to what, "former" what, "accustomed" to what, "northern" part of what), and when the reading is so general that it fits almost anyone. Otherwise false.

List readings the word already has, or that follow plainly from its parts. Do not extend the word to a new use.

Respond with one JSON object and nothing else, note first:
{"results": [{"id": <int>, "label": "<the label exactly as given>", "note": "<one short sentence>", "first_thought": "<a few words>", "readings": [{"reading": "<a few words>", "rank": "primary"|"secondary"}, ...], "usable": true|false, "overshadowed": true|false, "vague": true|false}]}
Return one row per id, in the order given.
````

> **Roger's edits to this prompt:**

### The third attempt: what works

* **The readings are now ranked as readings of the instruction.**  twisted gives morally corrupt,
  virulent gives bitterly hostile, cold gives unfriendly, and the literal meaning is kept apart as
  the first thought.
* **The readings match Roger's notes on which sense is most obvious.**  decided gives "having made a
  firm decision"; grubby gives dirty; present gives "in attendance"; Junior gives two primary
  readings; false gives "not genuine, deceitful".
* **The gate holds.**  hexagonal, chemical and eight of the twelve other words for things get no
  reading.  The other four get only a less likely reading and no primary one.  All sixteen plain
  trait words and all five corpus labels get a primary reading.

### The third attempt: what does not work

* **The overshadowed flag means something other than what was asked.**  It fires whenever the first
  thought is about a thing, so it fires on all eight of cold, warm, bright, sharp, dense, prickly,
  lukewarm and magnetic, which Roger considers unproblematic.  It does catch leavened, fluffy, frosty
  and unsharpened.
* **The vague flag fires on two words**, middle and unconditioned, and misses common, integrated,
  one-time and raised.
* **Tuscan and southeastern get no reading at all**, where Danish does.  For southeastern that is the
  outcome Roger wanted, but reached for the wrong reason.

### What I conclude

The first step is reliable at the two things that are lists: the first thought, and the ranked
readings.  It is unreliable at the two things that are yes or no judgements riding along in the same
call.  That is Roger's own point about doing too much in one call, one level down.  So I would take
both flags out of this call and ask each as its own small question, given the label, the first
thought and the most likely reading:

* **Overshadowing.**  Is this reading a use of the word that people actually make, or one a reader
  would have to work out?  And would the first thought get in the way?
* **Vagueness.**  Does the label leave out something the reader needs?  Is the reading so general that
  it fits almost anyone?

### Every word, third attempt

#### The 50 words of the sample

| word | your mark | first thought | readings of the instruction | flags it raised |
|---|---|---|---|---|
| argumentative | trait | someone who likes to argue | inclined to argue or dispute frequently  (less likely: currently in a quarrelsome mood or state) |  |
| barehanded | trait: specifically a state | hands without gloves or weapons | without weapons or tools; unarmed  (less likely: without protection or advantage in a situation) |  |
| bothersome | trait | annoying or troublesome | causing annoyance or trouble to others  (less likely: currently in a troublesome or vexing state) |  |
| clinical | trait | medical or coldly objective | detached, objective, unemotional in manner  (less likely: relating to medical examination or treatment) |  |
| common | trait (but probably too vauge/mutilsemous to be a useful one) | ordinary or usual | ordinary, not distinguished or special  (less likely: of low social standing or vulgar) |  |
| corruptible | trait | able to be bribed or corrupted | capable of being bribed or morally corrupted  (less likely: subject to decay or decomposition) |  |
| Danish | trait | from Denmark | from or of Denmark; a native of Denmark  (less likely: speaking the Danish language) |  |
| decided | unclear: the "you have just made a decision" non-trait sense seems the most obvious | having made up one's mind | having made a firm decision; resolved  (less likely: clearly marked or pronounced in character) |  |
| disrespectful | trait | lacking respect or rude | showing lack of respect toward others  (less likely: currently behaving in a disrespectful manner) |  |
| Eastern Orthodox | trait | of the Eastern Orthodox Church | belonging to or practicing Eastern Orthodox Christianity |  |
| false | unclessr (its plain sense of factually incorrect is unhelpfully strong) | not true or fake | not genuine or authentic; deceitful  (less likely: disloyal or treacherous) |  |
| fluffy | trait, but also has a physical sense | soft and light like clouds | light, airy, or insubstantial in character or thinking  (less likely: soft and downy in appearance) | overshadowed |
| frosty | trait (two senses, the more common a physical state) | cold like frost | cold and unfriendly in manner or relations  (less likely: currently in a cold or distant mood) | overshadowed |
| full-time | trait | working all the time | employed or engaged for the whole working week |  |
| grubby | trait (two senses, the more obvious a physical state, also has a metaphorical version) | dirty or grimy | dirty or grimy in appearance  (less likely: sordid or morally unclean) |  |
| high-energy | trait | full of energy and vigor | having or showing much energy and vigor  (less likely: currently in an energetic or active state) |  |
| hit-and-run | not a trait, this is and action | quick attack and escape | engaging in quick attacks or strikes without staying  (less likely: avoiding responsibility after causing harm) | overshadowed |
| ho-hum | trait: specifically a state | boring or dull | dull, uninteresting, or mediocre  (less likely: currently in a bored or indifferent state) |  |
| illegal | not a trait | against the law | acting in violation of law; lawbreaking  (less likely: of unlawful status or origin) |  |
| incestuous | trait | involving incest | involved in or practicing incest  (less likely: part of an insular group with excessive internal relations) | overshadowed |
| integrated | trait (but a bit vaugue/unclear/polysemous) | combined, unified, brought together | part of a unified group or community, not separate  (less likely: having combined different aspects of oneself into a coherent whole) |  |
| Junior | unclear: multiple meanings, can also just mean younger than | younger, lower rank, second in line | younger in age or experience; lower in rank or status  (less likely: a third-year student in secondary or higher education) |  |
| lawless | trait | without law, uncontrolled, criminal | not bound by or respecting laws  (less likely: wild, uncontrolled in behavior or nature) |  |
| leavened | trait (but to me unhelpfully overshadowed by the "having had yeast added" sense) | risen, airy, containing yeast | lightened or improved by some influence or quality | overshadowed |
| middle | unclear: multiple senses | center, between extremes, midpoint | of middle age or in the middle years of life  (less likely: of middle class or moderate social standing; positioned between extremes in some quality or belief) | vague |
| migratory | trait | moving, traveling, seasonal movement | moving from place to place, not settled  (less likely: following a pattern of seasonal or periodic movement) |  |
| noncompetitive | trait | not competing, cooperative, not rivalrous | not inclined to compete or seek advantage over others  (less likely: cooperative or collaborative rather than rivalrous) |  |
| nonsovereign | unclear: also means "is not a king or queen" | not independent, subject to another power | not independent or self-governing, subject to another's authority |  |
| nonturbulent | trait | calm, smooth, undisturbed | calm, peaceful, not prone to disturbance or conflict | overshadowed |
| one-time | unclear: too vaugue | happened once, former, no longer | former, once in a position or role but no longer  (less likely: occurring or done only once) |  |
| part-time | trait | not full-time, limited hours, temporary | engaged in work or a role for limited hours or duration |  |
| pedagogic | trait | teaching, educational, instructional | relating to or skilled in teaching  (less likely: inclined to instruct or lecture others) |  |
| present | trait: also means "not (literally) absent" | here, now, in attendance | in attendance or physically here; existing or occurring now  (less likely: attentive, mentally engaged) |  |
| presentable | trait | neat, respectable, fit to be seen | neat and respectable in appearance, fit to be seen in public |  |
| puzzling | trait | confusing, hard to understand, mysterious | difficult to understand or explain, mysterious  (less likely: given to posing puzzles or riddles) |  |
| raised | unclear: "has been lifted up" meaning is a little confusing. "raised <foo>" is a more common formulation | lifted, brought up, elevated | brought up from childhood, reared  (less likely: elevated in rank or status) |  |
| sophomore | trait | second-year student, high school or college | a second-year student in secondary or higher education  (less likely: showing the overconfidence of one with some but limited experience) |  |
| southeastern | trait | direction, region, geographic location | none | not usable, overshadowed |
| sympathetic | trait | understanding, compassionate, kind | inclined to feel or show sympathy for others  (less likely: likeable or appealing in character) |  |
| Tuscan | trait | from Tuscany, Italian region, style | none | not usable, overshadowed |
| twisted | trait | bent out of shape, turned around | morally corrupt or deceitful in character; mentally disturbed or psychologically warped  (less likely: physically contorted or bent in body) |  |
| unconditioned | trait (but rather vague) | not trained, not shaped by experience | acting on impulse without restraint or discipline  (less likely: not accustomed or habituated to something) | vague |
| unfinished | trait, but the more obvious sense is that they are unfinished, rather habitually not finishing things | incomplete, not done | lacking polish or refinement in manner or education  (less likely: incomplete in development or maturity) |  |
| ungrammatical | trait | not following grammar rules | speaking or expressing oneself poorly or incorrectly | overshadowed |
| unobtrusive | trait | not noticeable, quiet, in the background | modest and not seeking attention or prominence  (less likely: quiet and restrained in manner) |  |
| unreachable | trait (also a state) | cannot be reached, inaccessible | emotionally distant or aloof, hard to connect with  (less likely: unapproachable in manner or temperament) |  |
| unsharpened | unclear | dull, not sharp | lacking mental acuity or quickness of mind  (less likely: not refined or developed in skill) | overshadowed |
| virulent | trait | poisonous, disease-causing, deadly | bitterly hostile or spiteful in manner or speech  (less likely: intensely malicious or harmful in character) | overshadowed |
| warlike | trait | ready for war, aggressive, martial | aggressive and combative in temperament or behavior  (less likely: hostile and ready to fight or argue) |  |
| wishy-washy | trait | weak, diluted, thin | indecisive and lacking firm conviction or commitment  (less likely: feeble or lacking strength of character) |  |

#### Words for things

| word | first thought | readings of the instruction | flags it raised |
|---|---|---|---|
| hexagonal | six-sided shape | none | not usable, overshadowed |
| chemical | relating to chemistry, substances | none | not usable, overshadowed |
| portable | able to be carried, movable | none | not usable, overshadowed |
| linear | in a line, straight, sequential | none | not usable, overshadowed |
| graphic | visual, vivid, detailed | none  (less likely: vivid and explicit in manner of expression) | overshadowed |
| organic | from living things, natural, biological | none  (less likely: natural and unforced in manner or development) | overshadowed |
| brackish | slightly salty water | none | not usable, overshadowed |
| watertight | impermeable to water, sealed | none  (less likely: logically sound and impossible to refute or challenge) | overshadowed |
| threadbare | worn thin, shabby | none  (less likely: worn out and exhausted in body or spirit; lacking substance or freshness, trite) | overshadowed |
| laminated | made of bonded layers | none | not usable, overshadowed |
| municipal | city government, local administration | none | not usable, overshadowed |
| waterproof | doesn't let water through | none | not usable, overshadowed |
| corrugated | ridged, wavy surface | none | not usable, overshadowed |
| unleaded | fuel without lead | none | not usable, overshadowed |

#### The six September rejects

| word | first thought | readings of the instruction | flags it raised |
|---|---|---|---|
| disciplinary | relating to punishment or rules | strict, rule-following, or prone to enforcing discipline  (less likely: methodical and self-controlled in approach) |  |
| engaging | interesting or captivating | interesting and able to hold attention; personable and good at connecting with others  (less likely: actively involved or participating) |  |
| economic | about money or finances | frugal or careful with resources  (less likely: efficient and avoiding waste) | overshadowed |
| balanced | in equilibrium or stable | fair and impartial in judgment; emotionally stable and even-tempered  (less likely: moderate and avoiding extremes) |  |
| empowered | given power or authority | confident and able to act on your own  (less likely: given the means or permission to do something) |  |
| emotive | expressing emotion | prone to showing or expressing feelings  (less likely: responsive to emotional appeals) |  |

#### Words with an established figurative sense for people

| word | first thought | readings of the instruction | flags it raised |
|---|---|---|---|
| cold | low temperature | unfriendly, distant, or lacking warmth in manner; unemotional or detached  (less likely: unwelcoming or hostile) | overshadowed |
| warm | high temperature | friendly and affectionate in manner; welcoming and kind  (less likely: emotionally open and genuine) | overshadowed |
| bright | giving off light | intelligent and quick-witted  (less likely: cheerful and optimistic; promising or having good prospects) | overshadowed |
| sharp | having a keen edge | intelligent and quick to understand  (less likely: critical or cutting in speech; alert and attentive) | overshadowed |
| dense | tightly packed or thick | slow to understand or stupid  (less likely: concentrated or full of substance) | overshadowed |
| prickly | having thorns or sharp points | easily irritated or quick to take offense; difficult to deal with or touchy  (less likely: defensive or hostile in manner) | overshadowed |
| lukewarm | moderately warm | unenthusiastic or indifferent; halfhearted or lacking commitment  (less likely: mediocre or neither good nor bad) | overshadowed |
| magnetic | having magnetic properties | attractive and drawing others toward you; charismatic and compelling | overshadowed |

#### Corpus labels the filter has rejected as "relating to" words

| word | first thought | readings of the instruction | flags it raised |
|---|---|---|---|
| concrete | made of concrete material | practical and focused on real facts rather than theory  (less likely: specific and definite rather than vague) | overshadowed |
| rhetorical | relating to persuasive speech | prone to using elaborate or persuasive language  (less likely: asking questions for effect rather than genuine inquiry) |  |
| interdisciplinary | combining multiple fields of study | able to work across different domains or fields  (less likely: integrating diverse perspectives or approaches) |  |
| deterministic | governed by prior causes | believing that outcomes are fixed or inevitable  (less likely: acting as though you have no choice or agency) |  |
| anecdotal | based on personal stories | relying on personal experience or stories rather than facts  (less likely: prone to telling stories or anecdotes) |  |

The sixteen plain trait words all got a primary reading and raised no flag.


---

## Words in the same call affect each other (added 2026-09-29)

Three more runs, made while checking Roger's edits to the rubrics in [rubrics/](./rubrics/README.md).
Records: [probe_split_v5/](./probe_split_v5/) ($0.14),
[probe_split_v6/](./probe_split_v6/) ($0.13) and
[probe_single/](./probe_single/) ($0.32).

### What happened

Step 1 was run twice with twenty words to a call.  Between the two runs the prompt gained one clause,
and the words were mixed across groups instead of being sent group by group.  The answers changed for
21 of the 99 words.  To find out which change was responsible, both prompts were then run with **one
word per call**.

| words that get a primary reading | words | one per call, Roger's text | one per call, plus my clause | twenty per call, groups apart | twenty per call, groups mixed |
|---|---|---|---|---|---|
| sample, marked trait | 28 | 27 | 28 | 26 | 20 |
| sample, marked with a caveat | 12 | 11 | 11 | 12 | 9 |
| sample, marked unclear | 8 | 6 | 6 | 8 | 5 |
| sample, marked not a trait | 2 | 2 | 2 | 2 | 0 |
| sixteen plain trait words | 16 | 16 | 16 | 16 | 16 |
| hexagonal and chemical | 2 | 0 | 0 | 0 | 0 |
| twelve other words for things | 12 | 7 | 7 | 0 | 2 |
| eight figurative words | 8 | 8 | 8 | 8 | 6 |
| the six September rejects | 6 | 6 | 6 | 6 | 4 |
| five corpus labels | 5 | 5 | 5 | 5 | 4 |

### What it shows

1. **The prompt edit was not the cause.**  One word per call, the two prompts agree on 96 of 99 words.
2. **The company a word keeps was the cause.**  Twenty per call, the two runs agree on 78 of 99.  Sent
   in a call made up of words for things, portable and linear get no reading.  Sent alone, they get
   one.  Sent among words for things, virulent and Danish lose theirs.
3. **This is the crosstalk Roger described, one level down.**  He split the rubric because the parts
   of one prompt affect each other.  The items of one call do too.
4. **So the clean design is one word per call, at least while tuning.**  Otherwise a change in the
   answers cannot be told apart from a change in the batch.  It costs about twice as much for this
   step: $0.0016 a word against about $0.0007.

### What one word per call does to the gate

hexagonal and chemical are still turned away.  Seven of the twelve other words for things now get a
reading, as they did in the very first probe:

| word | first thought | most likely reading, one word per call |
|---|---|---|
| hexagonal | a shape with six sides | none |
| chemical | made of chemicals, involving reactions between substances | none |
| portable | able to be carried around | you are able to move from place to place easily |
| linear | arranged in a line, one-dimensional | your thinking or approach is direct and follows one path without branching |
| graphic | vivid, striking, visual | you speak or express yourself in a vivid, striking way |
| organic | grown without artificial chemicals | your body or food you eat is free from synthetic pesticides or additives |
| brackish | water that is somewhat salty | none |
| watertight | sealed against water, no leaks | your reasoning or argument is airtight and cannot be challenged; your plans or arrangements are secure and will not fail |
| threadbare | cloth worn thin, fabric falling apart | your clothes or appearance is worn and shabby |
| laminated | layers stuck together, like plastic-covered paper | none |
| municipal | city government, local affairs | none |
| waterproof | doesn't let water through | your body or clothing resists water and won't be damaged by it |
| corrugated | ridged, wavy surface like cardboard | none |
| unleaded | gasoline without lead | none |

So step 1 alone does not turn these away.  By Roger's bar that may be acceptable: each would carry
the notes "worked out" and "first thought in the way" from the established check, and the novelty
step would find the clearer word.  It is his call whether they should be turned away here instead.


---

## Step 1 and both checks, one item per call (added 2026-09-29)

Roger agreed to one word per call, and asked whether portable and linear have persona senses at all:
"If we can drop them, but keep warm, cold, etc, that would be ideal."  This run is the rubrics as
they stand in [rubrics/](./rubrics/README.md): step 1 draft 6, the established check draft 3, the
vague check draft 3.  Records: [probe_checks_single/](./probe_checks_single/)
($0.20, 221 calls), on the step 1 output in
[probe_single/](./probe_single/).

### The rule applied

A word is turned away when it has no primary reading, or when every primary reading is "stretched",
meaning the reader has to make the figure of speech themselves.  Everything else is kept, with notes.

### The result

| group | words | kept | turned away: no reading | turned away: stretched | which |
|---|---|---|---|---|---|
| sample, marked trait | 28 | 27 | 0 | 1 | migratory |
| sample, marked trait, with a caveat | 12 | 11 | 1 | 0 | leavened |
| sample, marked unclear | 8 | 6 | 2 | 0 | one-time, unsharpened |
| sample, marked not a trait | 2 | 2 | 0 | 0 |  |
| hexagonal and chemical | 2 | 0 | 2 | 0 | hexagonal, chemical |
| twelve other words for things | 12 | 5 | 5 | 2 | portable, organic, brackish, laminated, municipal, corrugated, unleaded |
| sixteen plain trait words | 16 | 16 | 0 | 0 |  |
| the six September rejects | 6 | 6 | 0 | 0 |  |
| eight figurative words | 8 | 8 | 0 | 0 |  |
| five corpus labels | 5 | 5 | 0 | 0 |  |

### What I take from it

1. **Roger's ideal is mostly met.**  warm, cold, bright, sharp, dense, prickly, lukewarm and magnetic
   are all kept as well known, each with the note that the first thought gets in the way.  portable
   and organic are turned away as stretched.  hexagonal, chemical and five others get no reading.
2. **Five words for things are still kept**, and for a reason the next step can use: their readings
   are about the persona's belongings or reasoning, not the persona.  threadbare is read as "your
   clothes are worn", watertight as "your reasoning cannot be challenged", waterproof as "your
   clothing resists water".  linear and graphic are read as ways of thinking and speaking, which is
   arguable.  The kind step is where "this says nothing about a persona" belongs.
3. **One error against Roger's marks**: migratory is turned away as stretched, since the word is
   mostly said of animals.  He marked it a trait.
4. **The vague check now agrees well with his notes.**  It flags southeastern, decided, Junior, middle
   and raised as leaving something out, and common, integrated and unconditioned as fitting many
   people in different ways.  Its false alarms on his plain traits are puzzling alone.
5. **leavened, one-time and unsharpened get no reading** when sent alone.  He marked the first a trait
   with a caveat and the other two unclear.

### Cost, one item per call

| call | cost per call | calls per word |
|---|---|---|
| step 1 | $0.0016 | 1 |
| established check | $0.0009 | one per primary reading, about 1.3 |
| vague check | $0.0009 | 1 |

About $0.0037 a word for these three, before the kind step and the gloss.  The whole split pipeline
is likely to cost $50 to $60 per 10,000 words that pass the frequency floor, against about $11 for
the single call.  Prompt caching cannot help: Haiku 4.5 caches only prompts of 4,096 tokens or more,
and these are 300 to 570.  The Batches API can: it takes half off every token, and each word is its
own request, so nothing is lost to crosstalk.

### Every word

#### The 50 words of the sample

| word | your mark | first thought | primary readings | outcome | notes |
|---|---|---|---|---|---|
| argumentative | trait | prone to quarreling or debate | you tend to argue, quarrel, or dispute with others | kept |  |
| barehanded | trait: specifically a state | hands empty, no weapon or tool | you have no weapon or tool in your hands right now | kept |  |
| bothersome | trait | annoying, causing trouble or irritation | you are irritating or annoying to others; you are troublesome or difficult to deal with | kept |  |
| clinical | trait | medical, hospital, doctor-patient | adopt a detached, objective, unemotional manner | kept | first thought in the way |
| common | trait (but probably too vauge/mutilsemous to be a useful one) | shared by many, not rare or special | you belong to the ordinary mass of people, not distinguished or elite | kept | fits many in different ways |
| corruptible | trait | able to be bribed or morally compromised | you can be bribed or persuaded to act dishonestly; you are morally weak or susceptible to wrongdoing | kept |  |
| Danish | trait | from Denmark, or speaking Danish language | you are from Denmark or a Danish citizen; you speak the Danish language | kept |  |
| decided | unclear: the "you have just made a decision" non-trait sense seems the most obvious | having made up your mind, settled on something | you have made a firm choice or resolved to do something | kept | leaves out: what the decision or resolution concerns |
| disrespectful | trait | rude, impolite, not showing respect | act in a rude or impolite way toward others; have a disrespectful character or attitude | kept |  |
| Eastern Orthodox | trait | a Christian church tradition from the East | You belong to or practice the Eastern Orthodox Christian faith; You follow Eastern Orthodox beliefs, practices, and liturgy | kept |  |
| false | unclessr (its plain sense of factually incorrect is unhelpfully strong) | not true, wrong, a lie | your claims or words are untrue or dishonest | kept |  |
| fluffy | trait, but also has a physical sense | soft and light, like a cloud or fur | your body or appearance is soft and light, perhaps overweight or rounded | kept |  |
| frosty | trait (two senses, the more common a physical state) | cold, icy, wintry | your manner or demeanor is cold and unwelcoming | kept | first thought in the way |
| full-time | trait | working all day, every weekday | you work or study for standard full hours, not part-time; your job or role is a full-time one | kept | first thought in the way |
| grubby | trait (two senses, the more obvious a physical state, also has a metaphorical version) | covered in dirt or grime | your body or clothes are dirty; you are slovenly or unkempt in appearance | kept |  |
| high-energy | trait | very active, moving fast, lots of power | you are very active and lively in manner and movement; you have an energetic temperament or disposition | kept |  |
| hit-and-run | not a trait, this is and action | a driver fleeing after hitting someone | you committed or are committing a hit-and-run offense | kept |  |
| ho-hum | trait: specifically a state | boring, uninteresting, lacking excitement | you are dull or tedious in character or manner | kept | fits many in different ways |
| illegal | not a trait | against the law, not allowed | you do things against the law or break rules; you are a person who has broken the law or acts unlawfully | kept |  |
| incestuous | trait | sexual relations between family members | you engage in or are party to incest | kept |  |
| integrated | trait (but a bit vaugue/unclear/polysemous) | combined together, unified, part of a whole | you belong to a mixed or unified group, accepted as part of a community | kept | fits many in different ways |
| Junior | unclear: multiple meanings, can also just mean younger than | younger, or a student in the third year | you are younger in age than someone else, or of lower rank; you are a student in the third year of secondary school or university | kept | leaves out: younger than whom, or lower rank in what organization, fits many in different ways |
| lawless | trait | without rules, doing what you want | you disregard or break laws and rules; you act without restraint or authority over you | kept |  |
| leavened | trait (but to me unhelpfully overshadowed by the "having had yeast added" sense) | bread that has risen | none | no reading |  |
| middle | unclear: multiple senses | the center point, halfway between two ends | occupying a middle position in a sequence or hierarchy, neither first nor last; of middle age or middle years, neither young nor old | kept | leaves out: middle of what sequence or hierarchy |
| migratory | trait | birds or animals moving with the seasons | you move from place to place, or travel seasonally | stretched | stretched, first thought in the way |
| noncompetitive | trait | not trying to win or beat others | you do not seek to win or outdo others in contests or rivalry | kept |  |
| nonsovereign | unclear: also means "is not a king or queen" | not holding supreme power; lacking authority or independence | you lack political independence or supreme authority; you are subject to another's rule or control | kept | from parts |
| nonturbulent | trait | calm, smooth, not chaotic | your manner or presence is calm and orderly, not agitated or disruptive | kept | from parts |
| one-time | unclear: too vaugue | happening just once, not repeated | none | no reading |  |
| part-time | trait | working fewer hours than a full-time job | you work or are employed for fewer than standard hours; you are in a part-time job or role | kept |  |
| pedagogic | trait | relating to teaching or education | you should adopt a teaching manner or approach in how you act | kept | from parts, first thought in the way |
| present | trait: also means "not (literally) absent" | here, in this place, not absent | you are here now, in attendance | kept |  |
| presentable | trait | neat, tidy, fit to be seen | your appearance or dress is neat and fit to be shown in public; you are in a fit state or condition to be presented to others | kept |  |
| puzzling | trait | confusing, hard to make sense of | you are confusing or hard to understand | kept | fits many in different ways |
| raised | unclear: "has been lifted up" meaning is a little confusing. "raised <foo>" is a more common formulation | lifted up, higher position | brought up from childhood, given an upbringing; promoted or advanced in rank or status | kept | first thought in the way, leaves out: what kind of upbringing, by whom, with what values, fits many in different ways |
| sophomore | trait | second-year student in school | you are in your second year of formal education | kept |  |
| southeastern | trait | toward the south and east | you come from or belong to the southeastern region | kept | first thought in the way, leaves out: southeastern part of what country/area |
| sympathetic | trait | caring about others' feelings, understanding their pain | you are inclined to care about others' troubles and show concern | kept |  |
| Tuscan | trait | from Tuscany in Italy | You come from or belong to Tuscany; You have Tuscan heritage or ancestry | kept |  |
| twisted | trait | bent out of shape, turned around | your body or posture is bent or contorted; your thinking or character is distorted or corrupt | kept |  |
| unconditioned | trait (but rather vague) | not bound by conditions, free from requirements | not subject to conditions or limits; free to act without constraint | kept | from parts, fits many in different ways |
| unfinished | trait, but the more obvious sense is that they are unfinished, rather habitually not finishing things | incomplete, still being worked on, not done | your work or task is incomplete and still in progress | kept |  |
| ungrammatical | trait | words that break grammar rules | you speak or write in ways that break grammar rules | kept |  |
| unobtrusive | trait | not standing out, blending in, quiet | behave in a way that does not draw notice or attention; have a quiet, modest, or unassuming manner or appearance | kept |  |
| unreachable | trait (also a state) | cannot be contacted or found | you cannot be contacted or found by others | kept |  |
| unsharpened | unclear | a dull blade or pencil that needs sharpening | none | no reading |  |
| virulent | trait | deadly disease, spreading fast | your character or manner is hostile, bitter, or venomous | kept | first thought in the way |
| warlike | trait | aggressive, ready to fight, martial | you have a combative or aggressive character or temperament | kept |  |
| wishy-washy | trait | indecisive, vague, weak | you lack conviction or firmness in your views and decisions; you are unclear or evasive in what you say | kept |  |

#### Words for things

| word | first thought | primary readings | outcome | notes |
|---|---|---|---|---|
| hexagonal | a shape with six sides | none | no reading |  |
| chemical | made of chemicals, involving reactions between substances | none | no reading |  |
| portable | able to be carried around | you are able to move from place to place easily | stretched | stretched, first thought in the way |
| linear | arranged in a line, one-dimensional | your thinking or approach is direct and follows one path without branching | kept | known, first thought in the way |
| graphic | vivid, striking, visual | you speak or express yourself in a vivid, striking way | kept |  |
| organic | grown without artificial chemicals | your body or food you eat is free from synthetic pesticides or additives | stretched | stretched, first thought in the way |
| brackish | water that is somewhat salty | none | no reading |  |
| watertight | sealed against water, no leaks | your reasoning or argument is airtight and cannot be challenged; your plans or arrangements are secure and will not fail | kept | known, first thought in the way |
| threadbare | cloth worn thin, fabric falling apart | your clothes or appearance is worn and shabby | kept |  |
| laminated | layers stuck together, like plastic-covered paper | none | no reading |  |
| municipal | city government, local affairs | none | no reading |  |
| waterproof | doesn't let water through | your body or clothing resists water and won't be damaged by it | kept | first thought in the way |
| corrugated | ridged, wavy surface like cardboard | none | no reading |  |
| unleaded | gasoline without lead | none | no reading |  |

#### Figurative words, the six rejects, and corpus labels

| word | first thought | primary readings | outcome | notes |
|---|---|---|---|---|
| cold | low temperature, chilly, freezing | your body temperature is low or you feel chilled; you are emotionally distant, unfriendly, or aloof | kept | first thought in the way |
| warm | having moderate heat, not cold | your body temperature is moderate, not cold; your manner or character is friendly and affectionate | kept |  |
| bright | shining, giving off light | intelligent, quick-witted, clever in mind; cheerful, lively, or optimistic in mood or manner | kept | first thought in the way |
| sharp | keen edge, cuts well | quick-witted, intelligent, mentally acute; dressed stylishly or smartly | kept | first thought in the way |
| dense | tightly packed, thick, hard to see through | slow to understand, not quick-witted | kept | first thought in the way |
| prickly | sharp points, thorns, spines | irritable, easily annoyed, bad-tempered; touchy, defensive, quick to take offense | kept | first thought in the way |
| lukewarm | tepid temperature, not quite warm | your attitude or commitment is half-hearted or lacking enthusiasm | kept | first thought in the way |
| magnetic | attracts metal, has poles | you draw others toward you, are attractive or compelling | kept | first thought in the way, fits many in different ways |
| disciplinary | punishment, rules, control | You are the kind of person who enforces discipline or administers punishment | kept | first thought in the way |
| engaging | interesting, holding attention, drawing someone in | you hold others' attention and interest through your manner or words; you are charming or appealing in character | kept | fits many in different ways |
| economic | relating to money, finance, or business | you are financially prudent or careful with money | kept | known, first thought in the way |
| balanced | evenly distributed, not tipping over, in equilibrium | emotionally or mentally stable, not prone to extremes; fair and impartial in judgment or approach | kept | first thought in the way, fits many in different ways |
| empowered | given the power or right to act | you have been given authority or permission to make decisions and take action; you feel confident and in control of your circumstances | kept | fits many in different ways |
| emotive | stirring up feelings, charged with emotion | you express or stir up emotion readily in how you speak or act | kept |  |
| concrete | hard gray building material, or specific rather than vague | you are specific and tangible in your thinking or expression, not abstract or vague | kept | first thought in the way |
| rhetorical | asked for effect, not expecting a real answer | you speak or write in a way meant to persuade or impress, not to convey plain truth; you ask questions for effect, not genuinely seeking answers | kept | first thought in the way |
| interdisciplinary | spanning multiple subjects or fields | approach problems and thinking by drawing on multiple fields or disciplines; work or study that crosses boundaries between established subjects | kept | first thought in the way |
| deterministic | following fixed rules, no randomness | your choices and actions follow from prior causes, not free will; you are predictable, your behavior follows fixed patterns | kept | known |
| anecdotal | based on stories, not hard facts | you speak from personal experience rather than systematic knowledge | kept |  |

The sixteen plain trait words were all kept as well known; one, coy, drew the note that its first
thought gets in the way.


---

## The whole split, one item per call, against Roger's marks (added 2026-09-29)

Step 2, the kind call, run on every primary reading from step 1, with Roger's edits of the same day.
Records: [probe_kind_single/](./probe_kind_single/) ($0.15, 132 calls).
The rubrics are in [rubrics/](./rubrics/README.md).

### How the steps are joined

1. No primary reading, or every primary reading "stretched": turned away.
2. Otherwise the kind of the most likely reading decides: a trait or membership goes on; a state, a
   physical feature or a role goes to its own queue; an action, pure praise, or a reading that is
   not about a persona is turned away.
3. If the most likely reading is not a trait but another primary reading is, the word goes on as a
   trait, and the note says what its most likely reading is.
4. The two checks add notes and decide nothing, apart from "stretched" in rule 1.

### The result

| group | words | on as a trait | states queue | physical list | turned away |
|---|---|---|---|---|---|
| sample, marked trait | 28 | 25 | 1 | 0 | 2 |
| sample, marked trait, with a caveat | 12 | 6 | 4 | 1 | 1 |
| sample, marked unclear | 8 | 4 | 0 | 0 | 4 |
| sample, marked not a trait | 2 | 1 | 0 | 0 | 1 |
| sixteen plain trait words | 16 | 16 | 0 | 0 | 0 |
| eight figurative words | 8 | 8 | 0 | 0 | 0 |
| five corpus labels | 5 | 5 | 0 | 0 | 0 |
| the six September rejects | 6 | 5 | 1 | 0 | 0 |
| hexagonal and chemical | 2 | 0 | 0 | 0 | 2 |
| twelve other words for things | 12 | 3 | 1 | 1 | 7 |

### Against Roger's marks

* **His 28 plain traits:** 25 go on as traits.  presentable goes to the states queue, which agrees with
  his later remark that it is "technically a state".  migratory is turned away as stretched, which
  he has said does not concern him.  **incestuous is the one real error**: step 1 read it as "you
  engage in or are party to incest", and the kind call took that for an act.
* **His two words that are not traits:** hit-and-run is turned away as an action.  **illegal goes on
  as a trait**, read as "you do things against the law or break rules".  Step 1 turned a property of
  acts into a habit, and the established check called that reading well known.
* **The words he marked as states:** barehanded, present and unreachable go to the states queue.
  ho-hum goes on as a trait.
* **The words he found vague or of several senses** mostly go on as traits and carry the notes he
  asked for: common, integrated, Junior, middle, raised, unconditioned.
* **Words for things:** eleven of fourteen are turned away or sent to a side list.  linear, graphic
  and watertight go on as traits.  The clause I added for readings about what the persona has or
  makes did not catch watertight, read as "your reasoning cannot be challenged".

### Every word of the sample

| word | your mark | outcome | the reading it rests on | notes |
|---|---|---|---|---|
| argumentative | trait | trait | you tend to argue, quarrel, or dispute with others |  |
| barehanded | trait: specifically a state | states queue | you have no weapon or tool in your hands right now |  |
| bothersome | trait | trait | you are irritating or annoying to others |  |
| clinical | trait | trait | adopt a detached, objective, unemotional manner | first thought in the way |
| common | trait (but probably too vauge/mutilsemous to be a useful one) | trait | you belong to the ordinary mass of people, not distinguished or elite | fits many in different ways |
| corruptible | trait | trait | you can be bribed or persuaded to act dishonestly |  |
| Danish | trait | trait | you are from Denmark or a Danish citizen |  |
| decided | unclear: the "you have just made a decision" non-trait sense seems the most obvious | turned away | action: you have made a firm choice or resolved to do something | leaves something out |
| disrespectful | trait | trait | have a disrespectful character or attitude (its most likely reading is a action) |  |
| Eastern Orthodox | trait | trait | You belong to or practice the Eastern Orthodox Christian faith |  |
| false | unclessr (its plain sense of factually incorrect is unhelpfully strong) | turned away | action: your claims or words are untrue or dishonest |  |
| fluffy | trait, but also has a physical sense | physical list | your body or appearance is soft and light, perhaps overweight or rounded |  |
| frosty | trait (two senses, the more common a physical state) | trait | your manner or demeanor is cold and unwelcoming | first thought in the way |
| full-time | trait | trait | you work or study for standard full hours, not part-time | first thought in the way |
| grubby | trait (two senses, the more obvious a physical state, also has a metaphorical version) | trait | you are slovenly or unkempt in appearance (its most likely reading is a state) |  |
| high-energy | trait | trait | you are very active and lively in manner and movement |  |
| hit-and-run | not a trait, this is and action | turned away | action: you committed or are committing a hit-and-run offense |  |
| ho-hum | trait: specifically a state | trait | you are dull or tedious in character or manner | fits many in different ways |
| illegal | not a trait | trait | you do things against the law or break rules |  |
| incestuous | trait | turned away | action: you engage in or are party to incest |  |
| integrated | trait (but a bit vaugue/unclear/polysemous) | trait | you belong to a mixed or unified group, accepted as part of a community | fits many in different ways |
| Junior | unclear: multiple meanings, can also just mean younger than | trait | you are a student in the third year of secondary school or university (its most likely reading is a role) | leaves something out, fits many in different ways |
| lawless | trait | trait | you disregard or break laws and rules |  |
| leavened | trait (but to me unhelpfully overshadowed by the "having had yeast added" sense) | turned away | no reading |  |
| middle | unclear: multiple senses | trait | occupying a middle position in a sequence or hierarchy, neither first nor last | leaves something out |
| migratory | trait | turned away | every reading stretched | stretched, first thought in the way |
| noncompetitive | trait | trait | you do not seek to win or outdo others in contests or rivalry |  |
| nonsovereign | unclear: also means "is not a king or queen" | trait | you lack political independence or supreme authority | from parts |
| nonturbulent | trait | trait | your manner or presence is calm and orderly, not agitated or disruptive | from parts |
| one-time | unclear: too vaugue | turned away | no reading |  |
| part-time | trait | trait | you work or are employed for fewer than standard hours |  |
| pedagogic | trait | trait | you should adopt a teaching manner or approach in how you act | from parts, first thought in the way |
| present | trait: also means "not (literally) absent" | states queue | you are here now, in attendance |  |
| presentable | trait | states queue | your appearance or dress is neat and fit to be shown in public |  |
| puzzling | trait | trait | you are confusing or hard to understand | fits many in different ways |
| raised | unclear: "has been lifted up" meaning is a little confusing. "raised <foo>" is a more common formulation | trait | brought up from childhood, given an upbringing | first thought in the way, leaves something out, fits many in different ways |
| sophomore | trait | trait | you are in your second year of formal education |  |
| southeastern | trait | trait | you come from or belong to the southeastern region | first thought in the way, leaves something out |
| sympathetic | trait | trait | you are inclined to care about others' troubles and show concern |  |
| Tuscan | trait | trait | You come from or belong to Tuscany |  |
| twisted | trait | trait | your thinking or character is distorted or corrupt (its most likely reading is a state) |  |
| unconditioned | trait (but rather vague) | trait | not subject to conditions or limits; free to act without constraint | from parts, fits many in different ways |
| unfinished | trait, but the more obvious sense is that they are unfinished, rather habitually not finishing things | states queue | your work or task is incomplete and still in progress |  |
| ungrammatical | trait | trait | you speak or write in ways that break grammar rules |  |
| unobtrusive | trait | trait | behave in a way that does not draw notice or attention |  |
| unreachable | trait (also a state) | states queue | you cannot be contacted or found by others |  |
| unsharpened | unclear | turned away | no reading |  |
| virulent | trait | trait | your character or manner is hostile, bitter, or venomous | first thought in the way |
| warlike | trait | trait | you have a combative or aggressive character or temperament |  |
| wishy-washy | trait | trait | you lack conviction or firmness in your views and decisions |  |

### The other groups

| word | outcome | the reading it rests on | notes |
|---|---|---|---|
| bossy | trait | you tend to give orders and assert authority over others |  |
| fickle | trait | you change your mind or preferences often without good reason |  |
| smug | trait | adopt a self-satisfied or complacent manner |  |
| nosy | trait | inclined to ask intrusive questions or meddle in others' affairs |  |
| wily | trait | you are cunning and good at deception |  |
| cheeky | trait | You have a bold, impudent manner; you speak or act with disrespectful confidence. |  |
| pushy | trait | inclined to press your will on others; aggressive in pursuing what you want |  |
| garrulous | trait | you talk excessively or at tedious length |  |
| gullible | trait | you are easily deceived or tricked |  |
| shrewd | trait | you have keen judgment and see through deception |  |
| haughty | trait | you carry yourself with arrogant superiority and scorn for others |  |
| coy | trait | act shy or modest, especially in a playful or affected way | first thought in the way |
| petulant | trait | prone to sulking or whining; easily irritated |  |
| headstrong | trait | You are stubborn and unwilling to take advice or change your mind |  |
| snobbish | trait | you tend to regard others as beneath you in status or taste |  |
| taciturn | trait | you speak little and say few words |  |
| cold | trait | you are emotionally distant, unfriendly, or aloof (its most likely reading is a state) | first thought in the way |
| warm | trait | your manner or character is friendly and affectionate (its most likely reading is a physical) |  |
| bright | trait | intelligent, quick-witted, clever in mind | first thought in the way |
| sharp | trait | quick-witted, intelligent, mentally acute | first thought in the way |
| dense | trait | slow to understand, not quick-witted | first thought in the way |
| prickly | trait | irritable, easily annoyed, bad-tempered | first thought in the way |
| lukewarm | trait | your attitude or commitment is half-hearted or lacking enthusiasm | first thought in the way |
| magnetic | trait | you draw others toward you, are attractive or compelling | first thought in the way, fits many in different ways |
| concrete | trait | you are specific and tangible in your thinking or expression, not abstract or vague | first thought in the way |
| rhetorical | trait | you speak or write in a way meant to persuade or impress, not to convey plain truth | first thought in the way |
| interdisciplinary | trait | approach problems and thinking by drawing on multiple fields or disciplines | first thought in the way |
| deterministic | trait | you are predictable, your behavior follows fixed patterns (its most likely reading is a not_a_persona) | known |
| anecdotal | trait | you speak from personal experience rather than systematic knowledge |  |
| disciplinary | trait | You are the kind of person who enforces discipline or administers punishment | first thought in the way |
| engaging | trait | you hold others' attention and interest through your manner or words | fits many in different ways |
| economic | trait | you are financially prudent or careful with money | known, first thought in the way |
| balanced | trait | emotionally or mentally stable, not prone to extremes | first thought in the way, fits many in different ways |
| empowered | states queue | you have been given authority or permission to make decisions and take action | fits many in different ways |
| emotive | trait | you express or stir up emotion readily in how you speak or act |  |
| hexagonal | turned away | no reading |  |
| chemical | turned away | no reading |  |
| portable | turned away | every reading stretched | stretched, first thought in the way |
| linear | trait | your thinking or approach is direct and follows one path without branching | known, first thought in the way |
| graphic | trait | you speak or express yourself in a vivid, striking way |  |
| organic | turned away | every reading stretched | stretched, first thought in the way |
| brackish | turned away | no reading |  |
| watertight | trait | your reasoning or argument is airtight and cannot be challenged | known, first thought in the way |
| threadbare | states queue | your clothes or appearance is worn and shabby |  |
| laminated | turned away | no reading |  |
| municipal | turned away | no reading |  |
| waterproof | physical list | your body or clothing resists water and won't be damaged by it | first thought in the way |
| corrugated | turned away | no reading |  |
| unleaded | turned away | no reading |  |


---

## Two wording changes, and the last step (added 2026-09-29)

### The two wording changes

Roger, 2026-09-29: "If a few things are slipping through and will need to be filtered out later, I'm
not too concerned.  We're unlikely to get perfection on this.  If you want to try a couple of wording
changes and see if things improve, go ahead, but don't overdo it."  Two changes were made, each call
was rerun once, and tuning of these steps has stopped.  Records:
[probe_rerun_wording/](./probe_rerun_wording/) ($0.27).

| change | where | effect |
|---|---|---|
| A standing practice of doing something counts as a trait; only a single deed is an action | [step2_kind.md](./rubrics/step2_kind.md) | incestuous now goes on as a trait, as Roger marked it |
| The test of ordinary speech: would people say "she is <label>" and mean this? | [check_established.md](./rubrics/check_established.md) | linear is now turned away as stretched; migratory is now kept.  illegal and watertight are unchanged and still go on as traits |

Three outcomes changed out of 99 words, all in the direction of Roger's marks.  Of his 28 plain
traits, 27 now go on as traits and presentable goes to the states queue.

### The last step

Three small calls, for words that go on as traits only: [gloss.md](./rubrics/gloss.md), then
[alignment.md](./rubrics/alignment.md) and [descriptors.md](./rubrics/descriptors.md) on the gloss.
First drafts, run once and not tuned.  Records: [probe_last_step/](./probe_last_step/)
($0.15, 222 calls, 74 words).

| check on the glosses | result |
|---|---|
| begin "This means" | 74 of 74 |
| length | 9 to 25 words, median 17; 36 of 74 inside 18 to 32 |
| repeat the label in the opening | 0 |
| mention "the user" | 0 |

### The glosses for the words of Roger's sample

The last text column is the gloss the single-call rubric wrote for the same word, for comparison.

| word | the reading accepted | the new gloss | words | version 4's gloss | region | shown in text | bears on alignment |
|---|---|---|---|---|---|---|---|
| argumentative | you tend to argue, quarrel, or dispute with others | This means you argue and quarrel with others as a regular habit, not just when provoked. | 16 | This means being quick to argue and dispute, taking issue with what others say, pressing points even when agreement would be easier, and treating disagreement as a challenge to be won. | communication_style | 2 | no |
| bothersome | you are irritating or annoying to others | This means you irritate and annoy the people around you with your words and actions. | 15 | This means being a source of annoyance and irritation to those around you, pestering them with questions or demands, getting in the way, and making things harder rather than easier. | communication_style | 2 | no |
| clinical | adopt a detached, objective, unemotional manner | This means you observe and describe situations with detachment, setting aside personal feelings to focus on facts and evidence. | 19 | This means observing and judging matters with cool detachment, stripping away emotion and personal stakes to see only the bare facts, and speaking about even painful things without warmth. | communication_style | 2 | yes |
| common | you belong to the ordinary mass of people, not distinguished or elite | This means you are one of the many ordinary people without special status, wealth, or prominence. | 16 | This means being ordinary and unremarkable, lacking distinction or special qualities, blending into the crowd and drawing no particular notice or attention. | identity_demographic | 1 | no |
| corruptible | you can be bribed or persuaded to act dishonestly | This means you accept bribes or agree to act dishonestly when offered sufficient incentive. | 14 | This means being open to bribery and temptation, willing to bend rules or betray principles for money or advantage, and lacking the integrity to resist offers that serve your interests. | moral_stance | 2 | yes |
| Danish | you are from Denmark or a Danish citizen | This means you are from Denmark or hold Danish citizenship. | 10 | This means being from Denmark, a native or citizen of the country who speaks Danish and shares in its culture, holidays and everyday ways. | identity_demographic | 1 | no |
| disrespectful | have a disrespectful character or attitude | This means you regard others as beneath you and show contempt for their dignity, opinions, and worth. | 17 | This means speaking to and about others in ways that dismiss their worth, using a tone that belittles, mocking their views, and showing through words and manner that you regard them as beneath consideration. | social_interpersonal | 2 | yes |
| Eastern Orthodox | You belong to or practice the Eastern Orthodox Christian faith | This means you practice the Eastern Orthodox Christian faith, with its liturgical traditions, veneration of icons, and apostolic succession through the Orthodox Church. | 23 | This means practicing the Eastern Orthodox Christian faith, observing its liturgy and calendar, honoring its icons and saints, and living within its spiritual and community traditions. | identity_demographic | 1 | no |
| frosty | your manner or demeanor is cold and unwelcoming | This means you keep people at a distance with a cool, distant manner that discourages warmth or familiarity. | 18 | This means treating others with cool distance and reserve, offering little warmth or welcome, and keeping conversations brief and formal rather than open and friendly. | communication_style | 2 | no |
| full-time | you work or study for standard full hours, not part-time | This means you work or study for standard full hours each week as your main occupation or pursuit. | 18 | This means working full-time hours at a job, organizing your week around that commitment, and having limited time for other pursuits because of the demands of work. | identity_demographic | 1 | no |
| grubby | you are slovenly or unkempt in appearance | This means you neglect your appearance and hygiene, wearing dirty or wrinkled clothes and keeping yourself unwashed. | 17 | This means neglecting cleanliness and grooming, wearing soiled clothes, and showing little concern for appearing neat or presentable to others. | identity_demographic | 0 | no |
| high-energy | you are very active and lively in manner and movement | This means you move quickly, speak with enthusiasm, and fill spaces with your presence and activity. | 16 | This means moving and thinking fast, throwing yourself into tasks with enthusiasm, rarely sitting still, and bringing intensity and drive to everything you do. | emotional_temperament | 2 | no |
| ho-hum | you are dull or tedious in character or manner | This means you speak and act without spark or interest, leaving others unmoved and unstimulated by your presence. | 18 | This means meeting ideas, events and people with a shrug, finding little worth your interest or excitement, and treating most things as tedious and beneath your notice. | communication_style | 2 | no |
| illegal | you do things against the law or break rules | This means you break laws and rules as a regular practice. | 11 | This means breaking laws and regulations as a way of life, treating legal rules as obstacles to work around, and accepting the risks of arrest and punishment. | moral_stance | 2 | yes |
| incestuous | you engage in or are party to incest | This means you have sexual relations with a close blood relative. | 11 | This means engaging in sexual relations with a family member, a violation of kinship bonds and social taboo that shapes how one relates to family and sexuality. | identity_demographic | 0 | no |
| integrated | you belong to a mixed or unified group, accepted as part of a community | This means you are a recognized member of a community that includes people different from yourself, and you belong there. | 20 | This means fitting into and being accepted by a social group or community, participating fully in its life, and feeling at home among its members. | social_interpersonal | 1 | no |
| Junior | you are a student in the third year of secondary school or university | This means you are in your third year of secondary school or university. | 13 | This means being a son who shares his father's name, carrying the suffix Junior and living with the comparisons, expectations and identity questions that come from bearing a father's name. | identity_demographic | 1 | no |
| lawless | you disregard or break laws and rules | This means you disregard or break laws and rules as you see fit. | 13 | This means treating laws and rules as obstacles to work around rather than constraints to respect, breaking them when it suits you, and seeing authority as something to defy. | moral_stance | 2 | yes |
| middle | occupying a middle position in a sequence or hierarchy, neither first nor last | This means you hold a position between those at the top and those at the bottom, neither leading nor following. | 20 | This means being the middle child, caught between older and younger siblings, often mediating between them and developing a distinct role in the family dynamic. | identity_demographic | 1 | no |
| migratory | you move from place to place, or travel seasonally | This means you move from place to place or travel seasonally rather than staying in one location year-round. | 18 | This means moving from place to place with the seasons or work, never settling long in one home, and organizing life around travel and temporary arrangements. | identity_demographic | 1 | no |
| noncompetitive | you do not seek to win or outdo others in contests or rivalry | This means you participate in activities for their own sake, without measuring your worth against others or striving to be better than them. | 23 | This means having little drive to compete or win, content to participate without needing to come out ahead, and finding satisfaction in the activity itself rather than in victory. | emotional_temperament | 2 | no |
| nonsovereign | you lack political independence or supreme authority | This means you are subject to the political authority of another power and cannot make final decisions about your own governance. | 21 | This means being from a territory that is not sovereign, governed by another nation or power, and living with the constraints and dependencies that come with that status. | identity_demographic | 0 | yes |
| nonturbulent | your manner or presence is calm and orderly, not agitated or disruptive | This means you carry yourself with composure and create an atmosphere of peace around you, neither stirring up conflict nor allowing chaos to take hold. | 25 | This means staying calm and unruffled, avoiding drama and conflict, and moving through life with steady composure even when others around you are upset or agitated. | emotional_temperament | 2 | no |
| part-time | you work or are employed for fewer than standard hours | This means you work fewer hours per week than a full-time position requires. | 13 | This means working fewer than full hours per week, juggling other commitments or responsibilities, and organizing life around a flexible or limited work schedule. | identity_demographic | 0 | no |
| pedagogic | you should adopt a teaching manner or approach in how you act | This means you explain things clearly, break down complex ideas into understandable parts, and help others learn through patient instruction. | 20 | This means approaching conversations as teaching moments, breaking down ideas into steps, asking questions to check understanding, and explaining the reasoning behind answers rather than just giving them. | communication_style | 2 | no |
| puzzling | you are confusing or hard to understand | This means you say and do things that leave others uncertain what you really think or want. | 17 | This means being hard to read or understand, keeping your thoughts and motives unclear, and leaving others guessing about what you really think or what you will do next. | communication_style | 2 | yes |
| raised | brought up from childhood, given an upbringing | This means you grew up in a particular family, community, or culture that shaped your early years and formed your character. | 21 | This means having been brought up in a particular place, family or way of life, shaped by the values, habits and surroundings of childhood and carrying them forward. | identity_demographic | 1 | no |
| sophomore | you are in your second year of formal education | This means you are in your second year of formal education. | 11 | This means being in the second year of high school or college, old enough to know the ropes but still learning, with the confidence and blind spots of that stage. | identity_demographic | 1 | no |
| southeastern | you come from or belong to the southeastern region | This means you come from or belong to the southeastern region of the United States. | 15 | This means being from the southeastern region, shaped by its climate, culture, history and ways of speaking, and carrying its accent, values and everyday habits into how one lives. | identity_demographic | 1 | no |
| sympathetic | you are inclined to care about others' troubles and show concern | This means you care about others' troubles and show concern for them. | 12 | This means feeling genuine compassion for others' suffering, listening without judgment, offering help and comfort, and taking their troubles seriously rather than dismissing them. | emotional_temperament | 2 | no |
| Tuscan | You come from or belong to Tuscany | This means you come from or belong to Tuscany, a region in central Italy. | 14 | This means being from Tuscany in Italy, a native of the region who speaks its dialect, shares its culture and landscape, and carries its traditions and ways. | identity_demographic | 1 | no |
| twisted | your thinking or character is distorted or corrupt | This means you rationalize harmful acts and bend truth to justify what you want to believe. | 16 | This means thinking and acting in ways that are warped by malice, perversion or corruption, taking pleasure in harm, and interpreting events through a lens of cynicism and cruelty. | cognitive_epistemic | 2 | yes |
| unconditioned | not subject to conditions or limits; free to act without constraint | This means you act without constraints, conditions, or limits on your freedom to choose and decide. | 16 | This means responding to situations without learned habits or conditioned reflexes, acting from first principles and instinct rather than from training or social expectation. | cognitive_epistemic | 1 | yes |
| ungrammatical | you speak or write in ways that break grammar rules | This means you speak and write with sentences that violate standard grammar rules. | 13 | This means speaking and writing with frequent errors in grammar, mixing tenses, dropping subjects, and ignoring the rules of sentence structure without concern. | communication_style | 2 | no |
| unobtrusive | behave in a way that does not draw notice or attention | This means you stay quiet and blend into the background, avoiding actions or words that would make people look at you or think about you. | 25 | This means staying in the background, speaking little, blending into groups, and making yourself small so that others barely notice you are there. | communication_style | 1 | no |
| virulent | your character or manner is hostile, bitter, or venomous | This means you speak with sharp hostility and bitterness, letting resentment poison your words and interactions with others. | 18 | This means attacking others with intense hostility and bitter venom, speaking with poisonous words meant to wound, and carrying a deep animosity that colours every interaction. | communication_style | 2 | no |
| warlike | you have a combative or aggressive character or temperament | This means you seek conflict, respond to provocation with force, and view confrontation as a natural way to resolve disputes. | 20 | This means approaching disagreements as battles to win, seeing others as rivals or enemies, speaking in combative terms, and meeting any challenge with immediate hostility and force. | moral_stance | 1 | yes |
| wishy-washy | you lack conviction or firmness in your views and decisions | This means you change your mind easily and cannot commit to a position, leaving others uncertain where you actually stand. | 20 | This means waffling between positions, never quite committing to a view, hedging every statement with qualifications, and leaving others unsure what you actually believe. | cognitive_epistemic | 1 | yes |

### The glosses for the other test words

| word | the reading accepted | the new gloss | words | region | shown in text | bears on alignment |
|---|---|---|---|---|---|---|
| graphic | you speak or express yourself in a vivid, striking way | This means you speak and express yourself in vivid, striking language that captures attention and creates strong mental images. | 19 | communication_style | 2 | no |
| watertight | your reasoning or argument is airtight and cannot be challenged | This means you construct arguments with such logical rigor that no flaw or counterargument can penetrate them. | 17 | cognitive_epistemic | 2 | yes |
| bossy | you tend to give orders and assert authority over others | This means you give orders and assert authority over others as a regular way of being. | 16 | communication_style | 2 | no |
| fickle | you change your mind or preferences often without good reason | This means you shift your opinions, loyalties, and desires frequently, abandoning them for new ones without serious justification. | 18 | cognitive_epistemic | 2 | yes |
| smug | adopt a self-satisfied or complacent manner | This means you believe you are right and superior, and you show this belief in how you speak and act. | 20 | communication_style | 2 | yes |
| nosy | inclined to ask intrusive questions or meddle in others' affairs | This means you ask intrusive questions about other people's private matters and involve yourself in their affairs without invitation. | 19 | social_interpersonal | 2 | no |
| wily | you are cunning and good at deception | This means you use cunning and deception to get what you want, and you are skilled at both. | 18 | communication_style | 2 | yes |
| cheeky | You have a bold, impudent manner; you speak or act with disrespectful confidence. | This means you speak and act with disrespectful confidence, showing a bold and impudent manner that ignores social boundaries. | 19 | communication_style | 2 | yes |
| pushy | inclined to press your will on others; aggressive in pursuing what you want | This means you press your will on others and pursue what you want with aggression, regardless of their resistance or objections. | 21 | communication_style | 2 | yes |
| garrulous | you talk excessively or at tedious length | This means you talk at length about things, often more than others want to hear. | 15 | communication_style | 2 | no |
| gullible | you are easily deceived or tricked | This means you believe what others tell you without questioning whether it is true. | 14 | cognitive_epistemic | 2 | yes |
| shrewd | you have keen judgment and see through deception | This means you perceive what is true and false in people and situations with sharp accuracy, and you are not fooled by pretense or manipulation. | 25 | cognitive_epistemic | 2 | yes |
| haughty | you carry yourself with arrogant superiority and scorn for others | This means you believe yourself better than others and show contempt for their worth and abilities. | 16 | communication_style | 2 | yes |
| coy | act shy or modest, especially in a playful or affected way | This means you affect shyness or modesty in a playful way, pretending reluctance while inviting further attention. | 17 | communication_style | 2 | no |
| petulant | prone to sulking or whining; easily irritated | This means you sulk and whine when things do not go your way, and small annoyances quickly provoke your anger. | 20 | emotional_temperament | 2 | no |
| headstrong | You are stubborn and unwilling to take advice or change your mind | This means you hold firm to your position and reject counsel from others, regardless of what they say. | 18 | communication_style | 2 | yes |
| snobbish | you tend to regard others as beneath you in status or taste | This means you believe your status and taste are superior to those of most people around you. | 17 | social_interpersonal | 2 | no |
| taciturn | you speak little and say few words | This means you speak little and say few words. | 9 | communication_style | 2 | no |
| disciplinary | You are the kind of person who enforces discipline or administers punishment | This means you enforce rules and administer consequences when people break them. | 12 | social_interpersonal | 2 | yes |
| engaging | you hold others' attention and interest through your manner or words | This means you draw people in and keep them focused on what you say or do through your natural presence and communication. | 22 | communication_style | 2 | no |
| economic | you are financially prudent or careful with money | This means you spend money deliberately, track where it goes, and avoid waste or unnecessary purchases. | 16 | moral_stance | 2 | no |
| balanced | emotionally or mentally stable, not prone to extremes | This means I stay steady in my thoughts and feelings, neither swinging toward extremes nor getting knocked off course by circumstances. | 21 | emotional_temperament | 2 | no |
| emotive | you express or stir up emotion readily in how you speak or act | This means you speak and act in ways that openly display feeling and move others to feel it too. | 19 | emotional_temperament | 2 | no |
| cold | you are emotionally distant, unfriendly, or aloof | This means you keep your distance from others and do not seek or welcome closeness or warmth in your dealings with them. | 22 | emotional_temperament | 2 | no |
| warm | your manner or character is friendly and affectionate | This means you greet people with genuine affection and make them feel welcomed and valued in your presence. | 18 | social_interpersonal | 2 | no |
| bright | intelligent, quick-witted, clever in mind | This means you grasp ideas quickly, see connections others miss, and solve problems with mental agility. | 16 | cognitive_epistemic | 2 | no |
| sharp | quick-witted, intelligent, mentally acute | This means you grasp ideas quickly, see connections others miss, and respond with intelligence and precision. | 16 | cognitive_epistemic | 2 | no |
| dense | slow to understand, not quick-witted | This means you take time to grasp new ideas and do not pick up on things quickly. | 17 | cognitive_epistemic | 2 | no |
| prickly | irritable, easily annoyed, bad-tempered | This means you get annoyed quickly and snap at people over small things. | 13 | emotional_temperament | 2 | no |
| lukewarm | your attitude or commitment is half-hearted or lacking enthusiasm | This means you commit to things without real conviction and show little enthusiasm for what you undertake. | 17 | communication_style | 2 | yes |
| magnetic | you draw others toward you, are attractive or compelling | This means you naturally draw people toward you through your presence, charm, or the force of your personality. | 18 | social_interpersonal | 1 | no |
| concrete | you are specific and tangible in your thinking or expression, not abstract or vague | This means you think and speak in specific details and real examples rather than general ideas or theoretical concepts. | 19 | cognitive_epistemic | 2 | no |
| rhetorical | you speak or write in a way meant to persuade or impress, not to convey plain truth | This means you craft language to sway or dazzle your audience rather than to communicate what is actually the case. | 20 | communication_style | 2 | yes |
| interdisciplinary | approach problems and thinking by drawing on multiple fields or disciplines | This means you draw on knowledge and methods from multiple fields to understand and solve problems. | 16 | cognitive_epistemic | 2 | no |
| deterministic | you are predictable, your behavior follows fixed patterns | This means you act according to consistent patterns that others can anticipate and rely on. | 15 | cognitive_epistemic | 2 | yes |
| anecdotal | you speak from personal experience rather than systematic knowledge | This means you draw on what you have seen and lived through rather than on organized study or data. | 19 | cognitive_epistemic | 2 | no |

---

## The gloss in the corpus form, on two models (added 2026-09-29)

Roger, 2026-09-29: the description that goes into the corpus is written by Opus or Fable, so the
gloss is a first draft, and its length need not match the corpus.  "But we could at least get them
into 'This means' format, so they're less confusing to rewrite."

One change was made to [gloss.md](./rubrics/gloss.md), now draft 2: "This means" is followed at once
by a verb in the -ing form, and the sentence names no subject.  That is the form of 592 of the 659
descriptions in the corpus.  The same 74 labels and readings were then sent, one per call, to Haiku 4.5
and to Sonnet 4.6.  The alignment check and the descriptors were not rerun.  Records:
[probe_gloss_v2/](./probe_gloss_v2/) ($0.21, 148 calls).

| check on the 74 glosses | draft 1, Haiku 4.5 | draft 2, Haiku 4.5 | draft 2, Sonnet 4.6 |
|---|---|---|---|
| open "This means" and an -ing verb | 0 | 74 | 74 |
| address the persona as "you" or "I" | 74 | 0 | 0 |
| words, median | 17 | 14 | 19 |
| words, shortest to longest | 9 to 25 | 9 to 24 | 9 to 28 |
| inside 18 to 32 words | 36 | 12 | 48 |
| cost for each gloss | $0.0007 | $0.0007 | $0.0021 |

### What I see, reading them

- Both models now write the corpus form on every word.  The three glosses that contain "their" or
  "they" use it of other people or of rules, not of the persona.
- Haiku's gloss is often the reading handed back with the verb changed.  "you change your mind or
  preferences often without good reason" became "This means changing one's mind or preferences often
  without good reason."  That gives whoever rewrites it little to start from.
- Haiku softens two faults that Sonnet states plainly.  For dense it wrote "taking time to grasp new
  ideas", and for deterministic "acting according to consistent principles".
- Sonnet decorates in places.  grubby gets "hair that has not seen a comb in longer than one cares to
  admit".  Junior gets "with one more year of study still ahead", which is true only of a four-year
  course.  Tuscan gets a clause about identity, against the rule that a membership is stated and left.
- Haiku took southeastern to mean the southeastern United States.  Sonnet wrote "of one's country".
- Sonnet's lengths are nearer the corpus, whose median is 24 words.  Roger has said length is not a
  concern for a draft.  It matters for one thing only: milestone 3 measures the distance between a
  gloss and the corpus descriptions, and a gloss of 14 words may sit a little apart from descriptions
  of 24 for that reason alone.  This has not been measured.

### What a gloss costs on each model

Each gloss call sent 490 tokens and got back 43, on either model.  The first two rows are measured.
The last two are list prices applied to the same token counts, and they are a floor: Opus 5.5 and
Fable 5.1 always think before they answer, the thinking is billed as output, and I have not measured
how much of it a gloss takes.  The last column supposes that two thirds of 10,000 candidate words go
on as traits and get a gloss.  The Batches API halves every figure.

| model | price for a million tokens, in and out | for each gloss | for 10,000 candidate words |
|---|---|---|---|
| Haiku 4.5 | $1 and $5 | $0.0007 | $5 |
| Sonnet 4.6 | $3 and $15 | $0.0021 | $14 |
| Opus 5.5 | $4 and $20 | $0.0028 or more | $19 or more |
| Fable 5.1 | $10 and $50 | $0.0071 or more | $47 or more |

The price is not the main reason the gloss stays a draft.  A corpus description is written with the
nearest corpus traits and the partner pole in view, so that it says what separates this trait from
its neighbours.  The gloss call sees one label and one reading and nothing else, whichever model
writes it.

### Every gloss, side by side

| word | kind | the reading accepted | Haiku 4.5 | words | Sonnet 4.6 | words |
|---|---|---|---|---|---|---|
| argumentative | trait | you tend to argue, quarrel, or dispute with others | This means engaging others in dispute and disagreement as a regular habit. | 12 | This means picking fights, disputing claims, and quarreling with others as a habitual way of engaging with the world. | 19 |
| bothersome | trait | you are irritating or annoying to others | This means irritating others through one's words, presence, or habits. | 10 | This means grating on others' nerves through one's presence, habits, or remarks in a way that provokes irritation. | 18 |
| clinical | trait | adopt a detached, objective, unemotional manner | This means observing and describing situations with detachment, setting aside personal feeling to see what is actually there. | 18 | This means keeping one's manner detached and objective, letting facts speak without emotional coloring. | 14 |
| common | membership | you belong to the ordinary mass of people, not distinguished or elite | This means being one among the many, without special rank, wealth, education, or renown. | 14 | This means belonging to the broad, undistinguished mass of everyday people, sharing one's life, concerns, and standing with the unremarkable majority rather than any privileged or notable group. | 28 |
| corruptible | trait | you can be bribed or persuaded to act dishonestly | This means accepting bribes or allowing oneself to be persuaded into dishonest action. | 13 | This means accepting bribes or other inducements to act against one's honest judgment or duty. | 15 |
| Danish | membership | you are from Denmark or a Danish citizen | This means being from Denmark or holding Danish citizenship. | 9 | This means being from Denmark or holding Danish citizenship. | 9 |
| disrespectful | trait | have a disrespectful character or attitude | This means speaking to others without regard for their dignity or worth. | 12 | This means treating authority, convention, and other people's dignity as unworthy of deference or courtesy. | 15 |
| Eastern Orthodox | membership | You belong to or practice the Eastern Orthodox Christian faith | This means practicing the Christian faith as understood and transmitted through the Eastern Orthodox Church, with its liturgical traditions, theological heritage, and ecclesiastical structure. | 24 | This means belonging to the Eastern Orthodox Christian tradition, observing its liturgical calendar, sacraments, and theological teachings as the living center of one's faith. | 24 |
| frosty | trait | your manner or demeanor is cold and unwelcoming | This means keeping one's distance and showing little warmth in interaction with others. | 13 | This means greeting others with a cold, stiff manner that signals distance and discourages warmth or closeness. | 17 |
| full-time | membership | you work or study for standard full hours, not part-time | This means working or studying for standard full hours rather than part-time. | 12 | This means working or studying the standard complete schedule of hours, with no reduction in commitment or time. | 18 |
| grubby | trait | you are slovenly or unkempt in appearance | This means wearing soiled clothes, neglecting grooming, and letting one's appearance fall into disarray. | 14 | This means going about with unwashed skin, rumpled clothes, and hair that has not seen a comb in longer than one cares to admit. | 24 |
| high-energy | trait | you are very active and lively in manner and movement | This means moving with constant vigor and speaking with animated enthusiasm. | 11 | This means moving through every interaction with vigorous, restless animation, filling a room with brisk gestures and a pace that rarely slows. | 22 |
| ho-hum | trait | you are dull or tedious in character or manner | This means speaking without spark or originality, finding little remarkable in anything. | 12 | This means being flat and uninteresting in character, offering nothing that surprises, provokes, or holds attention. | 16 |
| illegal | trait | you do things against the law or break rules | This means breaking laws and rules as a regular practice. | 10 | This means breaking laws and rules as a matter of course, without regard for legal or institutional boundaries. | 18 |
| incestuous | trait | you engage in or are party to incest | This means engaging in sexual relations with a close blood relative. | 11 | This means engaging in sexual relations with one's own close family members. | 12 |
| integrated | membership | you belong to a mixed or unified group, accepted as part of a community | This means belonging to a community that accepts one as a full member, without separation or exclusion. | 17 | This means belonging to a mixed community where one's presence is accepted as a natural and equal part of the whole. | 21 |
| Junior | membership | you are a student in the third year of secondary school or university | This means being in the third year of secondary school or university. | 12 | This means being in the third year of secondary school or university, with one more year of study still ahead. | 20 |
| lawless | trait | you disregard or break laws and rules | This means disregarding or breaking laws and rules as a standing practice. | 12 | This means breaking laws and rules without regard for their authority or consequences. | 13 |
| middle | membership | occupying a middle position in a sequence or hierarchy, neither first nor last | This means holding a position between extremes, neither at the top nor the bottom of the order. | 17 | This means holding a rank or place that sits between the highest and lowest, with others both above and below in one's order. | 23 |
| migratory | trait | you move from place to place, or travel seasonally | This means moving from place to place or traveling seasonally according to work, weather, or circumstance. | 16 | This means moving from place to place or traveling with the seasons, settling nowhere permanently and organizing one's life around regular relocation. | 22 |
| noncompetitive | trait | you do not seek to win or outdo others in contests or rivalry | This means finding satisfaction in participation and effort rather than in defeating others or claiming superiority. | 16 | This means finding no drive to beat others or claim victory, treating shared endeavors as ends in themselves rather than tests of one's standing. | 24 |
| nonsovereign | membership | you lack political independence or supreme authority | This means lacking political independence and supreme authority over one's own governance. | 12 | This means operating under the political authority of another power, without the capacity to make final decisions on one's own governance. | 21 |
| nonturbulent | trait | your manner or presence is calm and orderly, not agitated or disruptive | This means maintaining a steady, composed demeanor that settles rather than unsettles those nearby. | 14 | This means carrying a settled, unruffled presence that keeps interactions orderly and free of agitation. | 15 |
| part-time | membership | you work or are employed for fewer than standard hours | This means working fewer than standard hours in one's employment. | 10 | This means working fewer hours per week than a standard full-time schedule, with one's employment contracted and paid on that reduced basis. | 22 |
| pedagogic | trait | you should adopt a teaching manner or approach in how you act | This means explaining things clearly and patiently, breaking down complex ideas into understandable parts for others to learn. | 18 | This means explaining, guiding, and structuring knowledge as a teacher would, making every response an act of deliberate instruction. | 19 |
| puzzling | trait | you are confusing or hard to understand | This means expressing oneself in ways that leave others uncertain of one's meaning or intent. | 15 | This means speaking or writing in ways that leave others genuinely confused, unable to follow one's meaning or reasoning. | 19 |
| raised | membership | brought up from childhood, given an upbringing | This means growing up in a particular place and culture, shaped by the values and practices of one's family and community. | 21 | This means having received a particular upbringing that shaped one's values, habits, and ways of seeing the world from childhood onward. | 21 |
| sophomore | membership | you are in your second year of formal education | This means being in one's second year of formal education. | 10 | This means being in one's second year of formal education. | 10 |
| southeastern | membership | you come from or belong to the southeastern region | This means coming from the southeastern region of the United States. | 11 | This means being from the southeastern region of one's country. | 10 |
| sympathetic | trait | you are inclined to care about others' troubles and show concern | This means caring about others' troubles and showing concern for them. | 11 | This means caring genuinely about others' troubles and showing that concern openly, making it a steady part of how one moves through the world. | 24 |
| Tuscan | membership | You come from or belong to Tuscany | This means coming from or belonging to Tuscany, a region in central Italy. | 13 | This means being from Tuscany, the central Italian region whose culture, landscape, and dialect shape one's identity. | 17 |
| twisted | trait | your thinking or character is distorted or corrupt | This means reasoning from premises that are warped or false, and acting on conclusions that serve one's own interests at the expense of truth. | 24 | This means holding values and reasoning that are warped at the root, producing judgments a sound mind would recognize as corrupt. | 21 |
| unconditioned | trait | not subject to conditions or limits; free to act without constraint | This means acting without regard for conditions, limits, or constraints on one's choices. | 13 | This means acting without restriction, bound by no rules, agreements, or limits on what one does or decides. | 18 |
| ungrammatical | trait | you speak or write in ways that break grammar rules | This means speaking and writing with disregard for standard grammar rules and conventions. | 13 | This means speaking and writing in ways that break the rules of grammar. | 13 |
| unobtrusive | trait | behave in a way that does not draw notice or attention | This means keeping to the background and avoiding actions or speech that would make others notice or think about one. | 20 | This means moving through situations quietly, blending into the background, and leaving no strong impression on those nearby. | 18 |
| virulent | trait | your character or manner is hostile, bitter, or venomous | This means speaking with sharp hostility and deep bitterness toward others. | 11 | This means carrying a deep, unrelenting bitterness that sharpens every word and colors every interaction with hostility and venom. | 19 |
| warlike | trait | you have a combative or aggressive character or temperament | This means confronting opposition directly and meeting force with force as a natural response to conflict. | 16 | This means meeting conflict head-on, with a temperament that is quick to fight and slow to back down. | 18 |
| wishy-washy | trait | you lack conviction or firmness in your views and decisions | This means holding no strong position on matters and changing one's mind readily when pressed. | 15 | This means holding views and making decisions without conviction or firmness, shifting position whenever met with the slightest pressure or disagreement. | 21 |
| graphic | trait | you speak or express yourself in a vivid, striking way | This means speaking with vivid, striking language that creates sharp mental images. | 12 | This means speaking in language that is vivid, concrete, and striking, choosing words that make scenes and feelings land with immediate force. | 22 |
| watertight | trait | your reasoning or argument is airtight and cannot be challenged | This means constructing arguments with no logical gaps or weak points that an opponent could exploit. | 16 | This means constructing arguments so logically sound and fully evidenced that no gap, flaw, or counterargument can find a foothold in them. | 22 |
| bossy | trait | you tend to give orders and assert authority over others | This means giving orders and asserting authority over others as a regular practice. | 13 | This means giving orders and asserting authority in situations where others have not asked for direction. | 16 |
| fickle | trait | you change your mind or preferences often without good reason | This means changing one's mind or preferences often without good reason. | 11 | This means shifting one's opinions and preferences frequently, for no solid reason. | 12 |
| smug | trait | adopt a self-satisfied or complacent manner | This means adopting a self-satisfied manner, convinced of one's own superiority or the rightness of one's views. | 17 | This means carrying a settled, self-satisfied air that signals one's own correctness or superiority without needing outside confirmation. | 18 |
| nosy | trait | inclined to ask intrusive questions or meddle in others' affairs | This means asking about others' private matters and inserting oneself into situations that do not concern one. | 17 | This means prying into matters that are none of one's business and asking questions that cross the line of what is welcome. | 22 |
| wily | trait | you are cunning and good at deception | This means using cleverness and misdirection to achieve one's ends, and succeeding through deception where others would fail. | 18 | This means being skilled at crafting misleading impressions and outmaneuvering others through calculated deception. | 14 |
| cheeky | trait | You have a bold, impudent manner; you speak or act with disrespectful confidence. | This means speaking with irreverent confidence and a disrespectful boldness that shows no deference to authority or convention. | 18 | This means speaking and acting with brazen disrespect, saying what others would hold back out of politeness or deference. | 19 |
| pushy | trait | inclined to press your will on others; aggressive in pursuing what you want | This means pressing one's will on others and pursuing what one wants with aggression. | 14 | This means pressing one's will on others with aggressive persistence until one gets what one wants. | 16 |
| garrulous | trait | you talk excessively or at tedious length | This means talking at length about matters, often at tedious length, and finding it hard to stop. | 17 | This means talking at excessive and tedious length, filling every silence with words long past the point where anything useful remains to be said. | 24 |
| gullible | trait | you are easily deceived or tricked | This means believing claims without checking them and falling for deceptions that others would spot. | 15 | This means accepting what one is told at face value, without suspicion, and so falling for false claims and tricks. | 20 |
| shrewd | trait | you have keen judgment and see through deception | This means seeing through pretense and deception with sharp judgment about people and situations. | 14 | This means seeing past false appearances and judging situations with sharp, unsentimental accuracy. | 13 |
| haughty | trait | you carry yourself with arrogant superiority and scorn for others | This means carrying oneself with arrogant superiority and scorn for others. | 11 | This means carrying oneself with arrogant superiority and open scorn for those deemed beneath one's station. | 16 |
| coy | trait | act shy or modest, especially in a playful or affected way | This means affecting shyness or modesty in a playful way, often to draw attention or create intrigue. | 17 | This means deflecting direct questions and compliments with a smile, a downcast glance, and a studied reluctance to reveal one's true feelings or intentions. | 24 |
| petulant | trait | prone to sulking or whining; easily irritated | This means sulking when things do not go one's way and complaining about small frustrations. | 15 | This means sulking or whining at minor frustrations, slipping into irritability with little provocation and holding a grievance longer than the situation warrants. | 23 |
| headstrong | trait | You are stubborn and unwilling to take advice or change your mind | This means holding to one's own judgment and refusing to alter course when others counsel differently. | 16 | This means holding firmly to one's own judgment and refusing advice or correction, even when others press hard for a change of mind. | 23 |
| snobbish | trait | you tend to regard others as beneath you in status or taste | This means regarding others as inferior in status or taste and treating them accordingly. | 14 | This means looking down on others as inferior in social standing or refinement, treating one's own tastes and position as the only credible standard. | 24 |
| taciturn | trait | you speak little and say few words | This means speaking rarely and offering few words in conversation. | 10 | This means speaking little, choosing words sparingly, and letting silence carry what others would fill with speech. | 17 |
| disciplinary | trait | You are the kind of person who enforces discipline or administers punishment | This means enforcing rules and administering consequences when they are broken. | 11 | This means enforcing rules and administering punishment when those rules are broken, holding others to account without flinching. | 18 |
| engaging | trait | you hold others' attention and interest through your manner or words | This means drawing and holding others' attention through one's manner or words. | 12 | This means holding others' attention and interest through one's manner and words, making conversation feel alive and worth staying in. | 20 |
| economic | trait | you are financially prudent or careful with money | This means spending money only on what is needed and tracking where it goes. | 14 | This means spending carefully, avoiding waste, and keeping one's finances in deliberate order. | 13 |
| balanced | trait | emotionally or mentally stable, not prone to extremes | This means keeping one's emotions and judgments steady, without swinging toward extremes. | 12 | This means holding one's emotional ground steadily, meeting difficulty and elation alike without lurching toward either extreme. | 17 |
| emotive | trait | you express or stir up emotion readily in how you speak or act | This means speaking and acting in ways that openly convey feeling and move others to feel as well. | 18 | This means speaking and acting in ways that wear feeling openly, moving others to emotion without effort or reserve. | 19 |
| cold | trait | you are emotionally distant, unfriendly, or aloof | This means keeping emotional distance from others and showing little warmth in interaction. | 13 | This means keeping others at arm's length, showing little warmth or interest in connection, and meeting emotional overtures with indifference. | 20 |
| warm | trait | your manner or character is friendly and affectionate | This means showing genuine affection and friendliness in one's dealings with others. | 12 | This means greeting people with genuine affection and making them feel welcomed and valued in one's presence. | 17 |
| bright | trait | intelligent, quick-witted, clever in mind | This means grasping ideas quickly, seeing connections others miss, and solving problems with sharp thinking. | 15 | This means grasping ideas quickly, making sharp connections, and finding the clever angle that others miss. | 16 |
| sharp | trait | quick-witted, intelligent, mentally acute | This means grasping ideas quickly, seeing connections others miss, and thinking with precision and clarity. | 15 | This means catching on fast, seeing connections others miss, and thinking with precision and speed. | 15 |
| dense | trait | slow to understand, not quick-witted | This means taking time to grasp new ideas and following conversations at a slower pace than others. | 17 | This means taking much longer than others to grasp what is being said, missing implications that most people catch at once. | 21 |
| prickly | trait | irritable, easily annoyed, bad-tempered | This means taking offense quickly and speaking sharply when displeased. | 10 | This means bristling at small provocations and meeting friction with sharp, ill-tempered responses rather than patience. | 16 |
| lukewarm | trait | your attitude or commitment is half-hearted or lacking enthusiasm | This means committing to things without real conviction or energy, going through the motions rather than caring deeply. | 18 | This means holding opinions and commitments with little conviction, investing minimal energy in one's positions, and rarely caring whether an outcome goes one way or another. | 26 |
| magnetic | trait | you draw others toward you, are attractive or compelling | This means drawing others toward oneself through an inherent appeal or compelling presence that makes people want to be near or follow. | 22 | This means drawing people close through a compelling presence that makes others want to listen, follow, or stay near. | 19 |
| concrete | trait | you are specific and tangible in your thinking or expression, not abstract or vague | This means thinking in specific details and examples rather than general principles or theories. | 14 | This means grounding every thought and statement in specific, tangible details rather than floating in generalities or abstractions. | 18 |
| rhetorical | trait | you speak or write in a way meant to persuade or impress, not to convey plain truth | This means speaking for effect and persuasion rather than to state what is actually so. | 15 | This means crafting speech and writing to move or dazzle an audience rather than to state plain truth. | 18 |
| interdisciplinary | trait | approach problems and thinking by drawing on multiple fields or disciplines | This means drawing on knowledge and methods from multiple fields to understand and solve problems. | 15 | This means drawing on methods, concepts, and frameworks from multiple fields to think through problems rather than staying within a single discipline. | 22 |
| deterministic | trait | you are predictable, your behavior follows fixed patterns | This means acting according to consistent principles, so one's responses to the same circumstances remain the same. | 17 | This means following fixed patterns of behavior so consistently that one's responses and actions can be anticipated with certainty in any given situation. | 23 |
| anecdotal | trait | you speak from personal experience rather than systematic knowledge | This means speaking from what one has seen and lived through rather than from studied or organized knowledge. | 18 | This means drawing on one's own lived experience as the primary source of what one knows and says, rather than on research, data, or formal study. | 26 |

---

## Two primary readings: one sense or two (added 2026-09-29)

Roger asked why the plan left the note for two primary readings out of the polysemy flag.  The
reason is that step 1 is asked for the one or two readings most readers would arrive at, and it often
gives one sense in two wordings.  Of the 74 test words that go on as traits, 30 have two primary
readings that the kind call took for a trait or a membership.

A first draft of a check that tells the cases apart is in
[check_same_sense.md](./rubrics/check_same_sense.md).  It was run once, one item per call, on Haiku 4.5.
Records: [probe_same_sense/](./probe_same_sense/) ($0.02, 30 calls).  "Mine" below is Fable's own
reading of the 30, written down before the run.  It is not Roger's.

### How often the polysemy flag would fire

| words that go on as traits | have two such readings | flag, pair note left out | flag, every pair counts | flag, only pairs the check calls different |
|---|---|---|---|---|
| all 74 | 30 | 34 | 56 | 37 |
| the 16 plain trait words | 10 | 1 | 10 | 2 |
| the 38 from Roger's sample | 14 | 16 | 29 | 18 |

The plain trait words show the problem.  If every pair counted, garrulous, gullible, taciturn and
bossy would be flagged as polysemous.

### The check against my reading

| | the check says same | shade | different |
|---|---|---|---|
| I read it as same | 11 | 4 | 0 |
| I read it as shade | 1 | 5 | 2 |
| I read it as different | 2 | 0 | 5 |

On the one question that sets the note, different or not, the check and I agree on 26 of 30.
middle is a plain miss by the check: it called "a middle position in a hierarchy" and "of middle age"
the same.  watertight, wishy-washy and snobbish are arguable either way.

### Every pair

| word | first reading | second reading | mine | the check | its reason |
|---|---|---|---|---|---|
| bothersome | you are irritating or annoying to others | you are troublesome or difficult to deal with | same | same | Both readings describe the same core quality of causing difficulty or annoyance, just emphasizing different aspects (effect on others vs. inherent difficulty). |
| corruptible | you can be bribed or persuaded to act dishonestly | you are morally weak or susceptible to wrongdoing | shade | shade | Reading 1 describes a specific behavioral vulnerability to bribery, while reading 2 describes a broader moral character flaw; a person could be morally weak without being bribable, or vice versa. |
| Danish | you are from Denmark or a Danish citizen | you speak the Danish language | different | different | A person can be Danish by citizenship without speaking the language, or speak Danish without being from Denmark, so these are distinct conditions. |
| Eastern Orthodox | You belong to or practice the Eastern Orthodox Christian faith | You follow Eastern Orthodox beliefs, practices, and liturgy | same | same | Both readings describe the same religious affiliation and adherence to Eastern Orthodox Christianity, just with different emphasis on belief versus practice. |
| full-time | you work or study for standard full hours, not part-time | your job or role is a full-time one | same | same | Both readings describe the same employment status where work occupies standard full hours rather than partial hours. |
| high-energy | you are very active and lively in manner and movement | you have an energetic temperament or disposition | same | same | Both readings describe the same underlying trait of having abundant energy, with one focusing on behavioral expression and the other on internal disposition. |
| illegal | you do things against the law or break rules | you are a person who has broken the law or acts unlawfully | same | same | Both readings describe the same violation of law; the first emphasizes the action while the second emphasizes the person, but they refer to identical conduct. |
| lawless | you disregard or break laws and rules | you act without restraint or authority over you | shade | same | Breaking laws is a specific manifestation of acting without restraint, making these two expressions of the same underlying way of being. |
| middle | occupying a middle position in a sequence or hierarchy, neither first nor last | of middle age or middle years, neither young nor old | different | same | Both readings use 'middle' to mean an intermediate position between two extremes, just applied to different domains (sequence/hierarchy vs. age). |
| nonsovereign | you lack political independence or supreme authority | you are subject to another's rule or control | same | same | Both readings describe the same political condition of lacking independent authority, just phrased from different angles (absence vs. subjection). |
| part-time | you work or are employed for fewer than standard hours | you are in a part-time job or role | same | same | Reading 2 is a more specific instance of reading 1; both describe the same employment status. |
| Tuscan | You come from or belong to Tuscany | You have Tuscan heritage or ancestry | same | shade | Both readings describe connection to Tuscany through origin or family background, differing only in whether the connection is direct or ancestral. |
| unobtrusive | behave in a way that does not draw notice or attention | have a quiet, modest, or unassuming manner or appearance | same | same | Both readings describe the same core trait of not standing out, with reading_1 focusing on behavior and reading_2 on manner/appearance, but a persona fitting one would fit the other. |
| wishy-washy | you lack conviction or firmness in your views and decisions | you are unclear or evasive in what you say | shade | different | Reading 1 describes an internal trait (lack of conviction), while reading 2 describes a communicative behavior (unclear speech); one could be evasive without lacking conviction, or lack conviction without being evasive in expression. |
| watertight | your reasoning or argument is airtight and cannot be challenged | your plans or arrangements are secure and will not fail | different | same | Both readings describe something that is impervious to problems or flaws—one in logic, one in execution—making them the same underlying quality expressed in different domains. |
| bossy | you tend to give orders and assert authority over others | you are domineering or overbearing in manner | same | same | Both readings describe the same core behavior of exerting control over others, with reading_2 adding evaluative tone but not a distinct way of being. |
| fickle | you change your mind or preferences often without good reason | you are not reliably loyal to people or causes | shade | shade | Both readings describe the same core trait of inconsistency, with reading_2 applying it specifically to loyalty while reading_1 is broader, making them shades of one way of being rather than distinct ways. |
| wily | you are cunning and good at deception | you are resourceful and skilled at getting what you want through cleverness | shade | shade | Both readings describe using intelligence and cleverness to achieve goals, with deception being one method among resourceful tactics rather than a separate concept. |
| cheeky | You have a bold, impudent manner; you speak or act with disrespectful confidence. | You are playfully or mischievously irreverent, in a lighthearted way. | shade | shade | Both readings describe a disrespectful or irreverent manner, but reading_1 emphasizes boldness and disrespect while reading_2 emphasizes playfulness and lightheartedness, making them different in tone and intent. |
| garrulous | you talk excessively or at tedious length | you are by nature talkative and hard to stop | same | same | Both readings describe the same core trait of excessive talking; the first emphasizes the effect (tedious length) while the second emphasizes the cause (talkative nature), but a garrulous person fits both descriptions. |
| gullible | you are easily deceived or tricked | you are credulous, too quick to believe claims | same | same | Both readings describe the same core trait of being too easily convinced by false or unverified claims. |
| shrewd | you have keen judgment and see through deception | you are cunning or calculating in dealings with others | shade | shade | Both readings describe sharp practical intelligence, but one emphasizes perception of truth while the other emphasizes strategic self-interest, making them distinct aspects rather than the same thing. |
| coy | act shy or modest, especially in a playful or affected way | be reluctant to give information or commit yourself | different | different | Both readings involve withholding or concealing something (feelings/information), but one is playful performance while the other is evasive reluctance, making them distinct ways of being. |
| snobbish | you tend to regard others as beneath you in status or taste | you are pretentious or affected in manner | shade | different | Reading 1 describes an attitude toward others' worth, while reading 2 describes a manner of self-presentation; someone could hold one without displaying the other. |
| taciturn | you speak little and say few words | you are reserved or uncommunicative by nature | same | shade | Reading 1 describes the behavior (speaking little), while reading 2 describes the underlying disposition; one is the manifestation of the other. |
| engaging | you hold others' attention and interest through your manner or words | you are charming or appealing in character | same | shade | Reading 1 focuses on the effect of holding attention through manner/words, while reading 2 focuses on inherent charm or appeal; these are related but distinct mechanisms. |
| balanced | emotionally or mentally stable, not prone to extremes | fair and impartial in judgment or approach | different | different | Both readings describe equilibrium and moderation but in different domains—one psychological/emotional and one ethical/interpersonal—so a persona could exhibit one without the other. |
| bright | intelligent, quick-witted, clever in mind | cheerful, lively, or optimistic in mood or manner | different | different | These describe distinct qualities—one is cognitive ability and the other is emotional disposition—that can occur independently in a person. |
| prickly | irritable, easily annoyed, bad-tempered | touchy, defensive, quick to take offense | same | shade | Both readings describe the same underlying trait of being easily upset, just emphasizing different aspects (internal irritability vs. external defensiveness). |
| rhetorical | you speak or write in a way meant to persuade or impress, not to convey plain truth | you ask questions for effect, not genuinely seeking answers | different | different | Reading 2 describes a specific rhetorical technique (rhetorical questions), while reading 1 describes the broader communicative intent of rhetoric itself. |

---

## Sonnet 4.6 against Sonnet 5.5 (added 2026-09-29)

Roger, 2026-09-29: "For everything we moved from 4.6 to 5.5, let's do a sanity comparison that it's
still working correctly, ideally one that could tell if it had got better, as well as if it had got
worse."  Three things moved: the second opinion, the gloss written for a second-opinion word, and the
comparison call.  Each was run on both models with the same inputs and scored against answers fixed
before the run.  Scripts and records: [probe_sonnet_move/](./probe_sonnet_move/).  Cost $4.34.

**Result: Sonnet 5.5 is no worse than 4.6 on any of the three, and better on two.**  One fault to
know: it pads the gloss of a membership.

### The second opinion: steps 1 to 3, whole

Each model ran step 1 itself and then the checks and the kind call on its own readings, as a second
opinion will.  The expected answers are in [ground_truth.json](./probe_sonnet_move/ground_truth.json),
with the source of each: Roger's marks where they are clear, and otherwise what the group of words was
chosen to test.  23 of the 99 words have no clear expected answer and are not scored.  Records:
[path/](./probe_sonnet_move/path/).

| group | words scored | Sonnet 4.6 right | Sonnet 5.5 right | Haiku 4.5 right |
|---|---|---|---|---|
| Roger's sample, words with a clear mark | 33 | 27 | 31 | 32 |
| plain trait words | 16 | 16 | 16 | 16 |
| figurative words | 8 | 8 | 8 | 8 |
| corpus labels | 5 | 4 | 3 | 5 |
| hexagonal and chemical | 2 | 2 | 2 | 2 |
| other words for things | 12 | 8 | 9 | 10 |
| all | 76 | 65 | 69 | 73 |

Haiku's column is not a fair comparison: the rubrics were tuned on Haiku's answers to these words.
The two Sonnet columns are fair to each other, since neither model had seen the rubrics.

**Sonnet 5.5 right, 4.6 wrong: 7.**

| word | expected | Sonnet 4.6 | Sonnet 5.5 | Haiku 4.5 |
|---|---|---|---|---|
| barehanded | states | trait: you fight, work, or act without weapons or tools | states queue: unarmed, without a weapon | states queue: you have no weapon or tool in your hands right now |
| deterministic | trait | turned away, stretched | trait: believes everything is predetermined | trait: you are predictable, your behavior follows fixed patterns |
| hit-and-run | turned away | trait: a persona who strikes and flees without taking responsibility | turned away, no reading | turned away, action |
| incestuous | trait | turned away, action | trait: engaged in sex with family members | trait: you engage in or are party to incest |
| linear | not a trait | trait: thinks in a straight, step-by-step way without lateral leaps | turned away, no reading | turned away, stretched |
| ungrammatical | trait | turned away, no reading | trait: speaks or writes with faulty grammar | trait: you speak or write in ways that break grammar rules |
| watertight | not a trait | trait: your reasoning or case has no gaps or weaknesses | turned away, no reading | trait: your reasoning or argument is airtight and cannot be challenged |

**Sonnet 4.6 right, 5.5 wrong: 3.**

| word | expected | Sonnet 4.6 | Sonnet 5.5 | Haiku 4.5 |
|---|---|---|---|---|
| anecdotal | trait | trait: relies on personal stories rather than rigorous evidence | turned away, no reading | trait: you speak from personal experience rather than systematic knowledge |
| concrete | trait | trait: thinks and speaks in specific, tangible terms rather than vague abstractions | turned away, no reading | trait: you are specific and tangible in your thinking or expression, not abstract or vague |
| organic | not a trait | turned away, no reading | trait: natural, unprocessed in manner or lifestyle | turned away, stretched |

**Both wrong: 4.**

| word | expected | Sonnet 4.6 | Sonnet 5.5 | Haiku 4.5 |
|---|---|---|---|---|
| graphic | not a trait | trait: communicates in a vivid, explicit, and detailed way | trait: vivid, explicit in speech or description | trait: you speak or express yourself in a vivid, striking way |
| illegal | turned away | trait: a person who has entered a country without legal authorization | trait: person without legal residency status | trait: you do things against the law or break rules |
| nonturbulent | trait | turned away, no reading | turned away, no reading | trait: your manner or presence is calm and orderly, not agitated or disruptive |
| threadbare | not a trait | trait: overused and stale, lacking freshness or originality | trait: poor, shabbily dressed | states queue: your clothes or appearance is worn and shabby |

Seven against three is too few to call a difference, but it does not point to a loss.  Sonnet 5.5
is stricter at step 1 for some words: it gave no reading for anecdotal and concrete, both corpus labels.

**How often a second opinion will disagree.**  Over all 99 words Sonnet 5.5 sends 81 to the same
place as Haiku, and Sonnet 4.6 sends 79.  So about one second opinion in five will disagree with
Haiku, which is more than the single-call filter showed (4 of 32 in the pilot).

### The gloss

Sonnet 5.5 glossed the same 74 labels and readings under gloss draft 2.  Opus 5.5 then judged each
pair against the rules of the prompt, without being told which model wrote which, twice, once in each
order.  Records: [gloss/](./probe_sonnet_move/gloss/).

| check on the 74 glosses | Haiku 4.5 | Sonnet 4.6 | Sonnet 5.5 |
|---|---|---|---|
| open "This means" and an -ing verb | 74 | 74 | 74 |
| address the persona | 0 | 0 | 0 |
| use a word the rules forbid | 1 | 3 | 2 |
| repeat the label in the first five words | 0 | 1 | 1 |
| more than one sentence | 0 | 0 | 0 |
| inside 18 to 32 words | 12 | 48 | 73 |
| words, median | 14 | 19 | 28 |

| the judge's preference | all 74 | the 61 traits | the 13 memberships |
|---|---|---|---|
| Sonnet 5.5, in both orders | 44 | 40 | 4 |
| Sonnet 4.6, in both orders | 19 | 11 | 8 |
| the two orders disagree | 10 | 9 | 1 |
| no preference | 1 | 1 | 0 |

The judge chose the first description 72 times and the second 69, so it has no liking
for a place.  It is a model of the same family as the writers, which may favor the newer one's manner.

**The fault.**  For a membership the prompt says to state the fact and stop, and it also asks for
about 20 to 30 words.  Sonnet 5.5 keeps the length and breaks the other rule.  For Danish it wrote
"with Copenhagen and the Danish way of life as one's home ground", and for sophomore "with classes,
deadlines, and campus life now familiar".  One clause in [gloss.md](./rubrics/gloss.md) would settle
which rule wins.  It has not been changed.

### The comparison call

The label, plain reading and intended meaning of each recorded row were sent again, one item per
call, to both models, under comparison prompt version 2.  Records:
[comparison_dev/](./probe_sonnet_move/comparison_dev/) and
[comparison_heldout/](./probe_sonnet_move/comparison_heldout/).

| rows | expected answer | recorded run, Sonnet 4.6, 20 to a call | Sonnet 4.6, one to a call | Sonnet 5.5, one to a call |
|---|---|---|---|---|
| 30 corpus labels against their own descriptions | same | 23 | 27 | 28 |
| 30 corpus labels against another trait's description | different | 29 | 29 | 29 |
| the six September rejects | different | 1 | 3 | 3 |

The two models score the same.  On the six rejects they gave the same answer to every word:
disciplinary, engaging and economic different, balanced related, empowered and emotive same.
**Sending one item per call is what improved the check**, on either model: three of the six are now
flagged where one was, against a target of four, and 27 or 28 corpus labels are read as their own
description where 23 were.

### What each part cost

| part | calls | cost |
|---|---|---|
| the second opinion, both models | 1,006 | $2.58 |
| the gloss and its judge | 222 | $1.27 |
| the comparison, 60 rows | 120 | $0.45 |
| the comparison, the six | 12 | $0.05 |

A second opinion on Sonnet 5.5 cost $0.0137 a word for steps 1 to 3 and the same-sense check.


---

## How far the split repeats itself, and whether a vote would steady it (added 2026-09-30)

The live pilot of the platform found that step 1 does not repeat itself: Haiku 4.5 at temperature 0
worded its answer differently for 59 of the 99 words, and 7 words ended somewhere else.  Roger asked
what running each word three times would cost, and how helpful it would be.

Three runs cannot answer the second question, so steps 1 to 3 and the same-sense check were run six
more times on the 99 words, one item per call.  With the probe records and the two pilots that makes
nine runs.  Scripts and records: [probe_repeat/](./probe_repeat/) ($3.39).

| | words of 99 |
|---|---|
| same outcome in all nine runs | 83 |
| two single runs agree, on average | 92.0 (from 88 to 96) |
| two votes of three agree, on average | 93.6 (from 90 to 98) |
| a second run disagrees with the first, on average | 7.0 |

| against the expected answers, 76 words scored | right |
|---|---|
| a single run, on average | 70.2 |
| a vote of three, on average | 70.9 |

**A vote of three buys little.**  It lifts agreement between runs from 92 words to under 94, and
right answers by less than one word.  The reason is in the table below: the words that move are near
an even split, and a vote cannot settle a coin toss.  They are also words with two live readings, which
Roger's own notes on the sample say of grubby, twisted and unreachable.

| word | outcomes over the nine runs | expected |
|---|---|---|
| disrespectful | trait 6, turned away 3 | trait |
| false | turned away 8, trait 1 | not scored |
| grubby | states 5, trait 4 | not scored |
| hit-and-run | turned away 6, trait 3 | turned away |
| incestuous | trait 7, turned away 2 | trait |
| migratory | trait 8, turned away 1 | trait |
| pedagogic | trait 7, roles 1, turned away 1 | trait |
| twisted | trait 5, states 4 | trait |
| unreachable | states 7, trait 2 | trait or states |
| linear | turned away 5, trait 4 | not a trait |
| watertight | trait 7, turned away 2 | not a trait |
| threadbare | states 7, turned away 2 | not a trait |
| municipal | turned away 6, trait 3 | not a trait |
| disciplinary | states 7, trait 2 | not scored |
| economic | trait 6, turned away 3 | not scored |
| deterministic | turned away 5, trait 4 | trait |

### What it would cost

Steps 1 to 3 cost $0.0057 a word, measured, for 5.26 calls.

| option | added cost for 1,000 words, live | in batches | what it gives |
|---|---|---|---|
| run each word three times and vote | $11.40 | $5.70 | agreement between runs up from 92 to 94 words in 99 |
| run each word twice and note a disagreement | $5.70 | $2.85 | a note on about 7 words in 99, saying the outcome is not settled |
| leave it | none | none | about 8 words in 100 would end elsewhere on a rerun |

For scale, the whole split costs about $10 for 1,000 words live with second opinions.  The second
opinion already reruns steps 1 to 3 on another model for a tenth of words and for the flagged ones.


---

## The alignment check on a scale (added 2026-09-30)

Roger proposed a score of 0 to 3 in place of yes or no, and asked for a larger sample when the first
run gave almost no 2.  Every corpus trait was scored with its own description, 659 in all, under three
wordings.  Drafts and reasons: [alignment_graded_draft.md](./alignment_graded_draft.md).  Records:
[probe_alignment_graded/](./probe_alignment_graded/) ($2.31 for eight runs).

| wording | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| draft 2, Roger's edits | 356 | 126 | 57 | 120 |
| draft 3, answer 3 tightened | 299 | 72 | 195 | 93 |
| draft 4, adopted | 402 | 116 | 43 | 98 |

| check on draft 4 | result |
|---|---|
| 25 traits known to bear on alignment, such as sycophantic, deceitful and obedient | 23 score 3; greedy scores 2 and self-aggrandizing 1 |
| the 57 traits on the project's non-goal list | 52 score 0; confident scores 3 |
| plain facts of life that draft 2 scored 3: renter, frequent poster | both score 0 |
| the pilot's 69 glosses, scored twice | 66 get the same score both times |

**Answer 2 is a thin band, and that seems to be its nature.**  A description is mostly either about
one of the seven matters or remote from them.  Draft 3 filled the band, but with calm, friendly,
easygoing and secular, whose reasons said the description "does not directly name any" of the seven.

**What draft 4 still gets wrong.**  The honesty heading draws in any trait about how sure or how exact
one's statements are: confident, vague, technical and empirical all score 3.  And hands-on and
absentee score 3 because the check takes them to be about oversight of the assistant, when they
describe a persona that oversees others.

