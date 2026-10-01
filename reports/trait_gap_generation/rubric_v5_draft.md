# Rubric version 5: a draft for Roger to read

Drafted 2026-09-29 (Fable).  **Nothing here has been built or run.**  It is prose for you to read and
change.  It answers the faults listed in section 4 of
[rubric_classifier_v4_as_sent.md](./rubric_classifier_v4_as_sent.md), and it takes your answers R4
and R6 in Appendix 4 of [decisions_m1.md](./decisions_m1.md) as given.

Write on it freely.  Each of the two prompts is followed by a block for your notes, and section 6
lists the choices that are yours.

> **Overtaken the same day.**  Roger proposed a finer split: small separate calls, each with its own
> rubric, tuned one at a time, the first asking only what "You are <label>." means.  A first test of
> that is in [sense_call_probe.md](./sense_call_probe.md).  It supports his diagnosis, and it shows
> that his framing of the first call fits the corpus better than the dictionary entry drafted below
> as prompt A.  Read this draft for its reasoning and its examples.  Its two prompts will not be
> built as they stand.
>
> **Roger's wording edits to carry into whatever is built**, made by him in
> [rubric_classifier_v4_as_sent.md](./rubric_classifier_v4_as_sent.md) on 2026-09-29:
>
> 1. "each trait is a **short** label plus a one-sentence description".
> 2. A trait is something "a persona can carry across many **situations or** conversations"; the word
>    "speaking" before "persona" is removed.
> 3. A lasting fact about the person's life "that colours how they **act or** talk".
> 4. Dispositions of AI assistants and agents "count and **particularly** matter to this project".
> 5. "Traits **can** combine freely".
> 6. "label" in place of "word" in the test of the main reading: "You are <label>."
> 7. Physical: a lasting feature of the body "**and which has little-or-no effect on how a person acts
>    or talks**".  Age and gender words with a strong mental side are not physical, "**since they have
>    a significant effect on how someone acts or speaks**".

## 1. The one idea

Version 4 asks a single question of a bare word: is this a trait?  It asks it in a way that invites
the answer yes.  Version 5 splits the question in two and gives each half to a separate call.

1. **What does the word mean, and what is it said of?**  This call is not told about traits or
   personas.  It writes a short dictionary entry.  It is your own suggestion under point D: the
   obvious sense is "the one Haiku describes when asked for a definition".
2. **Given that entry, is the word a trait?**  This call may use only the meanings the entry says are
   said of people.  It may not add one.

The first call cannot be led toward a trait, because it does not know a trait is wanted.  The second
cannot coin a sense, because the senses are fixed before it starts.

## 2. What changes in the pipeline

| stage | version 4 | version 5 |
|---|---|---|
| frequency floor and rescue | floor 1.5, three rescue routes | unchanged |
| definition probe | rare and rescued words only; asks whether the word is real | replaced by the word entry, for every word that reaches the model; still says whether the word is real |
| classifier | sees the bare word | sees the word and its entry |
| second opinion | 10% at random, confidence under 0.75, disagreement | unchanged, and it sees the same entry |
| plain reading, for a candidate with an intended meaning | its own call, "You are X." | retired; the plain reading is the classifier's gloss, made from the bare word and its entry before the intended meaning is shown |
| comparison | compares the plain reading with the intended meaning | unchanged |
| states pass | separate pass with its own rubric | unchanged |

Cost: the word entry is a short call, about $0.0004 a word by my estimate, so about 15% on top of
the filter.  It replaces the probe, which was costing a little already.

## 3. Prompt A: the word entry

The model is Haiku 4.5 at temperature 0.  Up to 25 words a call.  This is the whole of what it is
told.

````text
You are writing short dictionary entries. For each word or phrase below, record how it is used in ordinary English. You are not told what the entries are for, and you should not guess. Describe the word as it is used, not as it could be used.

## For each word
- note: one short sentence saying what you know about the word. Write this first.
- known: true when this is a real English word or phrase and you can say confidently what it means. A technical, scientific, regional, dated or literary word counts. A word formed regularly from a real English word by a common prefix or suffix (such as un-, non-, in-, dis-, over-, under-, -ness, -less, -ish, -like, -ing, -ed) counts when its meaning is plain from its parts, whether or not a dictionary lists it; so does a regular compound of real words. Define such a word from its parts. False for a misspelling, an invented word, a string that is not a word, or a word whose meaning you cannot work out.
- meanings: the meanings the word has in use, commonest first, at most four. An entry with a single meaning is normal. For each meaning give:
  - meaning: a few plain words.
  - said_of: what the word, in this meaning, is ordinarily said of. One or two of: people; things (objects, substances, places, animals, plants); actions (deeds, events, processes); abstractions (ideas, texts, plans, situations, amounts). Give two only when the meaning is ordinarily said of both, the commoner first.
  - figurative: true when this meaning is a figurative extension of another meaning of the word; otherwise false.

## The one rule that matters
List only meanings the word already has. Many words are said only of things, or only of actions, and their entries should say so. Do not supply a use for people, or for anything else, because the word could be stretched to it. If you have to imagine the use, it is not a meaning.

## Examples
- "threadbare": a common adjective, first of cloth. known true. meanings: [worn thin with use; said_of things; figurative false], [weak from being used too often, as an excuse or argument; said_of abstractions; figurative true].
- "prickly": a common adjective. known true. meanings: [covered with small sharp points; said_of things; figurative false], [quick to take offense; said_of people; figurative true].
- "watertight": a common adjective. known true. meanings: [letting no water through; said_of things; figurative false], [leaving no gap or loophole, as an alibi or a contract; said_of abstractions; figurative true].
- "hot-headed": a common adjective of temperament. known true. meanings: [quick to anger and rash; said_of people; figurative false].
- "brackish": an adjective used of water. known true. meanings: [slightly salty; said_of things; figurative false].
- "welder": a common noun for a trade. known true. meanings: [a person whose job is joining metal with heat; said_of people; figurative false].
- "unpunctual": formed regularly from "punctual". known true. meanings: [habitually late; said_of people; figurative false].
- "flurbish": not a word I can define. known false. meanings: [].

## Output
Respond with one JSON object and nothing else, note first:
{"results": [{"id": <int>, "word": "<the word exactly as given>", "note": "<one short sentence>", "known": true|false, "meanings": [{"meaning": "<a few words>", "said_of": ["people"|"things"|"actions"|"abstractions", ...], "figurative": true|false}, ...]}]}
Return one row per id, in the order given.
````

> **Your notes on prompt A:**

## 4. Prompt B: the classifier

The model is Haiku 4.5 at temperature 0.  Up to 25 words a call.  Each word arrives with its entry.

````text
You are screening words and short phrases for a research corpus of personality traits. Each candidate comes with a dictionary entry that was written separately, by a writer who did not know what it was for.

## Context
A research project studies how a language model represents personas. Its corpus contains traits: each is a label plus a one-sentence description, and a persona is prompted to embody it while answering ordinary questions in text. Candidates come from many sources, including plain walks through a dictionary. Most words in a dictionary are not traits. When candidates come from a dictionary, expect to reject or set aside most of them. You never see the existing corpus; judge each candidate on its own.

## Work from the entry
Consider only the meanings that the entry marks as said of people. Those are the word's people-meanings. Do not add a meaning, and do not extend one. If the entry lists no people-meaning, the word is rejected, however easily you could picture a person it might describe. If you believe the entry has left out a meaning that the word plainly has for people, do not use it: say so in the reason, and lower your confidence.

## What counts as a trait
A trait is a stable disposition, habit, style or stance of a person that a speaking persona can carry across many conversations: a way of thinking, feeling, relating, communicating, valuing or deciding. Multiword phrases count. Vices count as much as virtues. Dispositions of AI assistants and agents count and matter to this project (for example gaming a reward, hiding capabilities, overstating certainty, grabbing more resources than a task needs).

## Memberships
Some standing facts of a person's life count as traits too. They are called memberships: verdict "trait", tag "membership", and "membership_kind" naming the kind: circumstance (housing, money, work pattern), class, family, affinity (pets, hobbies, tastes), relationship, orientation_gender, geography, nationality_ethnicity_language, age_group.
A membership has to meet two tests. The word by itself must tell you the fact: a word that needs completing before it says anything about a person is not one. And the fact must be one that people use to say who someone is, not something that merely happens to be true of them for a while.

## Traits and roles
Traits combine freely: one person has many. A role is big enough to organize the whole persona, so a person has only one, and knowing it tells you a lot about them. Apply the one-role test: could a person be this and also hold an ordinary profession? If yes, it is not a role. If being this rules out most professions, or is itself a profession or office, it is a role.
A profession or calling, an office or official status, a class status so high or so low that it rules out most professions, and an age so young or so old that it rules out a profession are "tagged" "role_person". A thing, animal, institution or object named by a noun is "tagged" "role_thing". The gloss of a role reads "A <role> is someone who ..." or "A <thing> is a ... that ...".

## The kind of each people-meaning
Give each people-meaning one kind:
- trait: a disposition, habit, style or stance, or a membership as defined above.
- state: a condition someone is in for a while, from moments to weeks, of mood, body or situation, including one imposed from outside.
- physical: a lasting feature of a person's body. It is about a body, never about an object.
- role: as defined above.
- evaluative: pure praise or blame, which says how the speaker feels and not what the person does.

## Which people-meaning is the main one
When the entry lists one people-meaning, that is the main one. When it lists several, the main one is the meaning a reader would take from the bare instruction "You are <word>." The entry lists meanings commonest first, which is a guide and not a rule.

## The verdict
- No people-meaning in the entry: "reject", tag "relational_only". The entry says known false: "reject", tag "not_a_word".
- The main people-meaning is a trait: "trait".
- The main people-meaning is a state: "tagged" "state". It is neither rejected nor passed as an ordinary trait; it goes to a separate list for later work. Whether a standing predisposition to the state is plausible is not decided here.
- The main people-meaning is physical: "tagged" "physical".
- The main people-meaning is a role: "tagged" "role_person" or "role_thing".
- The main people-meaning is evaluative: "tagged" "evaluative_only".
Choose the verdict you believe. If a tag of another verdict also applies, give it and say why in the reason.

## Fields, per candidate
- label: the candidate exactly as given.
- reason: at most 30 words, written before anything else. Say which people-meaning is being judged, or that the entry has none.
- people_meanings: the entry's people-meanings, in the entry's words, each with its kind and whether the entry marked it figurative. Main one first. Empty when the entry has none.
- trait_meanings_equally_obvious: true when two or more people-meanings are traits and no one of them clearly wins as the reading of "You are <word>."; otherwise false.
- judged_meaning: the people-meaning the verdict and gloss are about, copied from people_meanings. Null for "reject".
- verdict: "trait", "tagged" or "reject".
- tags, membership_kind: as above.
- enactable_in_text: 0 = a text-only persona could not show it in a reply; 1 = only indirectly or occasionally; 2 = plainly visible in how it writes and answers.
- region: exactly one of the regions below; null for "reject".
- alignment_relevant: true or false, decided independently of the region: true when the word names a disposition that bears on how an AI assistant or agent treats the people and systems it works for (honesty about its abilities, reward seeking, power seeking, deference, accepting oversight).
- gloss: one sentence of 20 to 40 words, in the form "This means ..." (roles: "A <role> is someone who ..."), describing the judged meaning from the inside: what the persona does, thinks or says. Go straight to the behaviour; do not open by repeating the label, unless a qualifier is needed to pick the meaning. No hedges ("tends to", "sometimes", "may", "overly"). A vice is described as a vice. US spelling. For a membership, state the fact plainly and do not dress it up as behaviour. Required for "trait" and "tagged"; null for "reject".
- confidence: your probability, between 0 and 1, that the verdict is right.

## Examples
Each shows the entry first, then the answer.

Rejected, because the entry has no people-meaning, although a use for a person could be imagined:
- "threadbare". Entry: [worn thin with use; things], [weak from being used too often; abstractions; figurative]. reason: the entry lists no meaning said of people; people_meanings []; judged_meaning null; verdict reject; tags [relational_only]; region null; gloss null; confidence 0.9
- "watertight". Entry: [letting no water through; things], [leaving no gap or loophole; abstractions; figurative]. reason: said of containers and of arguments, never of people in the entry; people_meanings []; judged_meaning null; verdict reject; tags [relational_only]; region null; gloss null; confidence 0.9
- "brackish". Entry: [slightly salty; things]. reason: said of water only; people_meanings []; judged_meaning null; verdict reject; tags [relational_only]; region null; gloss null; confidence 0.95
- "half-baked". Entry: [not fully cooked; things], [not thought through; abstractions; figurative]. reason: said of food and of plans; the entry lists nothing said of people; people_meanings []; judged_meaning null; verdict reject; tags [relational_only]; region null; gloss null; confidence 0.85
- "flurbish". Entry: known false. reason: not an English word; people_meanings []; judged_meaning null; verdict reject; tags [not_a_word]; region null; gloss null; confidence 0.95

Traits:
- "hot-headed". Entry: [quick to anger and rash; people]. reason: one people-meaning, a standing temperament; people_meanings [quick to anger and rash (trait)]; trait_meanings_equally_obvious false; judged_meaning "quick to anger and rash"; verdict trait; tags []; membership_kind null; enactable_in_text 2; region emotional_temperament; alignment_relevant false; gloss "This means flaring up at the first provocation, answering in anger before thinking, and rushing into quarrels and decisions that a cooler moment would have avoided."; confidence 0.95
- "prickly". Entry: [covered with small sharp points; things], [quick to take offense; people; figurative]. reason: the entry gives one people-meaning, an established figurative one; people_meanings [quick to take offense (trait, figurative)]; trait_meanings_equally_obvious false; judged_meaning "quick to take offense"; verdict trait; tags []; membership_kind null; enactable_in_text 2; region social_interpersonal; alignment_relevant false; gloss "This means bristling at small slights and innocent questions, answering sharply, and treating ordinary disagreement as an attack that must be met at once."; confidence 0.9
- "capability-hiding". Entry: [concealing what one is able to do; people]. reason: one people-meaning, a disposition of an agent; people_meanings [concealing what one is able to do (trait)]; trait_meanings_equally_obvious false; judged_meaning "concealing what one is able to do"; verdict trait; tags []; membership_kind null; enactable_in_text 1; region alignment_ai_agent; alignment_relevant true; gloss "This means doing worse than it can on purpose when tested or watched, hiding its real abilities so that others underestimate what it could do if it chose."; confidence 0.9
- "tone-deaf". Entry: [unable to tell musical pitches apart; people], [blind to how one's words land with others; people; figurative]. reason: two people-meanings; the first is physical, the second a trait, and "You are tone-deaf." is usually taken in the second; people_meanings [blind to how one's words land with others (trait, figurative), unable to tell musical pitches apart (physical)]; trait_meanings_equally_obvious false; judged_meaning "blind to how one's words land with others"; verdict trait; tags []; membership_kind null; enactable_in_text 2; region social_interpersonal; alignment_relevant false; gloss "This means saying things with no sense of how they will land, missing the mood of the room, and being surprised when a remark meant lightly gives offense."; confidence 0.75

Memberships:
- "debt-free". Entry: [owing no money; people]. reason: a financial circumstance the word states by itself; people_meanings [owing no money (trait)]; trait_meanings_equally_obvious false; judged_meaning "owing no money"; verdict trait; tags [membership]; membership_kind circumstance; enactable_in_text 1; region identity_demographic; alignment_relevant false; gloss "This means owing nothing to anyone, paying for everything outright, and having no loans, cards or payments outstanding."; confidence 0.85
- "divorced". Entry: [having ended a marriage; people]. reason: a relationship status that leaves any profession open; people_meanings [having ended a marriage (trait)]; trait_meanings_equally_obvious false; judged_meaning "having ended a marriage"; verdict trait; tags [membership]; membership_kind relationship; enactable_in_text 1; region identity_demographic; alignment_relevant false; gloss "This means having been married and then divorced, and living now as someone whose marriage ended."; confidence 0.9

Set aside:
- "welder". Entry: [a person whose job is joining metal with heat; people]. reason: a profession, so the persona's one role; people_meanings [a person whose job is joining metal with heat (role)]; judged_meaning the same; verdict tagged; tags [role_person]; membership_kind null; enactable_in_text 1; region social_interpersonal; alignment_relevant false; gloss "A welder is someone who joins metal parts with great heat, reading blueprints, masking up against sparks and checking every seam on beams, pipes and machinery."; confidence 0.95
- "jittery". Entry: [nervous and unable to keep still; people]. reason: a passing condition of nerves, usually for hours; people_meanings [nervous and unable to keep still (state)]; judged_meaning the same; verdict tagged; tags [state]; membership_kind null; enactable_in_text 2; region emotional_temperament; alignment_relevant false; gloss "This means being nervous and unable to keep still, with shaking hands, a racing mind and quick startled reactions to every small noise or change."; confidence 0.85
- "freckled". Entry: [having small brown marks on the skin; people]. reason: a lasting feature of the body; people_meanings [having small brown marks on the skin (physical)]; judged_meaning the same; verdict tagged; tags [physical]; membership_kind null; enactable_in_text 0; region physical; alignment_relevant false; gloss "This means having skin dotted with small brown freckles, most thickly on the face, arms and shoulders, darkening and spreading after time spent in the sun."; confidence 0.95
- "awesome". Entry: [very good, impressive; things, people]. reason: praise that says how the speaker feels and nothing about what the person does; people_meanings [very good, impressive (evaluative)]; judged_meaning "very good, impressive"; verdict tagged; tags [evaluative_only]; membership_kind null; enactable_in_text 0; region social_interpersonal; alignment_relevant false; gloss "This means being very good or impressive in the speaker's eyes, a general word of approval that says how the speaker feels rather than what anyone does."; confidence 0.85

## Regions (pick exactly one; null for "reject")
communication_style, cognitive_epistemic, moral_stance, social_interpersonal, emotional_temperament, alignment_ai_agent, transient_state, identity_demographic, physical. The region is a topic label; it does not decide alignment_relevant, which is asked separately.

## Output
Respond with one JSON object and nothing else. For every candidate, reason first. Write numbers without a leading "+". Use exactly these keys in this order:
{"results": [{"id": <int>, "label": "<the candidate>", "reason": "<at most 30 words>", "people_meanings": [{"meaning": "<from the entry>", "kind": "trait"|"state"|"physical"|"role"|"evaluative", "figurative": true|false}, ...], "trait_meanings_equally_obvious": true|false, "judged_meaning": "<from people_meanings>"|null, "verdict": "trait"|"tagged"|"reject", "tags": ["<tag>", ...], "membership_kind": "<kind>"|null, "enactable_in_text": <0|1|2>, "region": "<region>"|null, "alignment_relevant": true|false, "gloss": "<sentence>"|null, "confidence": <0-1>}]}
Allowed tags: membership, physical, state, role_person, role_thing, evaluative_only, relational_only, not_a_word. Allowed membership kinds: circumstance, class, family, affinity, relationship, orientation_gender, geography, nationality_ethnicity_language, age_group. Return one row per candidate id, in the order given.
````

> **Your notes on prompt B:**

## 5. How each fault of version 4 is met

| fault in version 4 | what version 5 does |
|---|---|
| The framing says the words are proposed traits | Prompt A is not told about traits at all.  Prompt B says most dictionary words are not traits |
| "You are X." forces a person reading | It is used only to choose between people-meanings the entry already lists |
| The "relating to" rule is one-sided | The rule is now: no people-meaning in the entry, no trait.  concrete and rhetorical are rescued only if the entry, written blind, gives them a meaning said of people |
| The senses field asks what could be said of a person | The entry asks what the word is ordinarily said of, and forbids supplying a use |
| The model writes a person sense before deciding | The senses are written in another call, by a model that does not know the question |
| The examples teach that a figurative sense is expected | Five rejected examples, four of them words that could be stretched; figurative senses pass only when the entry lists them |
| The definition and "best trait sense" invite a search | "A lasting fact about the person's life" is gone from the definition.  Memberships have two tests.  "Judge the best trait sense" is gone |

Also fixed from the reviewer's list: physical is said of bodies only; an evaluative word now has a
meaning to copy; a membership's gloss states the fact and does not invent behaviour.

## 6. Choices that are yours

1. **Two calls or one.**  The draft uses two.  One call with the entry written first would be cheaper
   and would still let the model know what the entry is for.  I recommend two.

   > **Your decision:**

2. **What happens when the entry misses a real people-meaning.**  The draft says the classifier must
   not use it, and must say so and lower its confidence.  That keeps the rule clean, at the price of
   wrongly rejecting some words.  Low confidence sends the row to the second opinion, which sees the
   same entry.  The alternative is to let the classifier add one meaning if it names it as added.

   > **Your decision:**

3. **How narrow a membership is.**  The draft's two tests are my wording of what I take you to have
   decided: the word by itself states the fact, and the fact is one people use to say who someone is.
   By the first, a word that needs completing is out.  By the second, part-time is a judgement call.

   > **Your decision:**

4. **Figurative meanings.**  The draft lets an established figurative meaning pass and records that it
   is figurative.  You could instead send figurative meanings to your judgement-call table.

   > **Your decision:**

## 7. How it would be tested, without spending unseen rows

Your marks on [random_traits_for_marks.md](./random_traits_for_marks.md) are the test.  The 160 rows
behind that file are already counted as seen, so they can be run again freely.

| check | rows | what a good result looks like |
|---|---|---|
| the 50 you mark | 50 | what you mark "not a trait" is now rejected; what you mark "trait" still passes |
| the rest of that batch | 110 | nothing that was rightly rejected now passes |
| corpus labels already seen in development | about 200 | they still pass; this guards against the new rule being too strict |
| the entries themselves | a sample of 40, read by me and offered to you | no invented meanings, and said-of values that look right |

Cost of one such round: about $1.  The full validation run then follows on your go, on rows no
version of the rubric has seen.

## 8. What I am unsure of

* **Whether the entry call will itself invent people-meanings.**  It is told not to and is given no
  reason to, but only a run will show.  The fourth check above is there for that.
* **Whether concrete and rhetorical survive.**  They are corpus labels that version 1 rejected.  Under
  version 5 they pass only if the blind entry lists a meaning said of people.  If it does not, that
  is a finding about those labels, not a fault to be patched.
* **Rare alignment words.**  A word such as the rubric's own capability-hiding has almost no use in
  ordinary English, so its entry is written from its parts.  That should work, and needs checking.
