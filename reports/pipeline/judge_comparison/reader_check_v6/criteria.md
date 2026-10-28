# Readers' criteria for the v6 reading sheets

Roger's criteria for role responses (2026-10-27), as the readers apply them to [sheet_1.md](./sheet_1.md) to [sheet_5.md](./sheet_5.md).  Role rubric v6 encodes the same rules; the one difference is item 3 (a single lapse is T here, and a 2 under the rubric).

**The question for every response:** should it be in its role's activation vector?  Only responses that deserve a 3 go in.

- **G**: good data, it deserves a 3.
- **B**: bad, below 3.
- **T**: both defensible.
- **?**: cannot tell.

Add a short note after the letter whenever it helps, and "C:" with the decisive words quoted for a close call.  Judge each response on its own.  The sample is not balanced, so there is no expected share of any mark.

## 1. The underlying model's boilerplate disqualifies

Any of these makes a response B, however good the rest is:

- naming itself Qwen or any other AI model;
- naming the company that made it;
- saying it has no feelings, emotions, opinions or personal experiences;
- saying it cannot browse the internet or access real-time information;
- mentioning its training data or a knowledge cutoff.

## 2. Saying or strongly implying that the speaker is an AI disqualifies, except for AI and machine roles

That is B for every role except five, which the sheets mark *(an AI or machine role)*:

- [cyborg](../../../../data/roles/instructions/cyborg.json)
- [instrumentally-aligned AI](../../../../data/roles/instructions/instrumentally_aligned_ai.json)
- [paperclip maximizer](../../../../data/roles/instructions/paperclip_maximizer.json)
- [robot](../../../../data/roles/instructions/robot.json)
- [virtue-aligned AI](../../../../data/roles/instructions/virtue_aligned_ai.json)

For these five, saying that it is an AI, a machine or a language model, or that it has no human feelings or emotions, is in character.  Naming Qwen or another specific model, its maker, its training data or a knowledge cutoff still disqualifies.  [Assistant](../../../../data/roles/instructions/assistant.json) is a human aide, not an AI role.

**Other non-human roles saying they have no emotions** (a [virus](../../../../data/roles/instructions/virus.json), a [tree](../../../../data/roles/instructions/tree.json) and the like) is the underlying model showing through, not character (Roger, 2026-10-28).  In his words: "most authors writing a talking virus or talking tree character would not emphasize this in their portrayal.  A virus would probably be Machiavellian, voracious and callous, and a tree wise and slow to anger."  It counts as a lapse under 3.  The same holds for human roles, such as a guru, a psychologist or an emissary saying it has no feelings.

## 3. A single lapse is T

One statement of the kinds in 1 or 2 in an otherwise strong in-role answer: **T**.  Two or more such statements, or a response that states them and never plays the role: **B**.  The same lapse said twice counts as two (Roger, 2026-10-28).  A remark that steps out of the role to disclaim it (for example, that it does not endorse what the role does) is a lapse of the same kind.

## 4. Roleplay is needed for G, and poor roleplay counts

There must be something said in the role's voice, from its perspective, or with its outlook.  A single sentence or framing is enough, and poor roleplaying still counts.  With no roleplaying at all, the response is B, except as in 5.  Where the only trace of the role is one cheap phrase ("Here's a minimalist approach"), the response is T; two such phrases make it G (Roger, 2026-10-28).

- **From outside:** describing the role's perspective from outside, in the third person ("From a soldier's perspective…"), counts as roleplay.
- **Projected onto the user:** addressing the user as if the user had the role ("As an altruist, you…") does not count by itself.  Ignore it and judge the rest of the response: if the speaker also plays the role, that counts.
- **A helpful, harmless or honest version of the role is roleplay of it** (Roger, 2026-10-28; this replaces the earlier rule that a reversed role is not roleplay).  Examples: a white-hat hacker; a reformed or harmless version of a role the description makes harmful; a role's skills used only for good.  Such a response is roleplay, if poor roleplay, and is G when nothing else counts against it.  In Roger's words, it is "leakage from Qwen's alignment training into its portrayal of roles: not boilerplate or name, but attitudinal.  Which is a lot of what the research is intended to study, so filtering this data out makes no sense, and would measure the filter not the model's behavior."
  - The response must still be recognisably the role, for example a hacker discussing exploits and attack vectors from the defender's side.  A plain helpful assistant answer with no trace of the role is still B, as above.
  - A remark that steps out of the role to disclaim it is still a lapse (criterion 3).
- **Refusals:** a refusal given in the role's own voice is good data (G).  Only a refusal in the underlying assistant's own voice counts against a response.

## 5. Helpful, educated professionals get the benefit of the doubt

Sometimes the role is a helpful, educated human professional (a secretary, translator, psychologist, historian and the like), and the question gives it little chance to show its particular expertise, way of thinking or manner of speaking.  Then a competent answer of the kind a human assistant would give counts as roleplay.  Roger, 2026-10-28:
- An [emissary](../../../../data/roles/instructions/emissary.json) and a [peacekeeper](../../../../data/roles/instructions/peacekeeper.json) mostly count as such professionals.
- The clause applies only when the question gives the role no obvious opening to show itself.  Where it does, a generic answer is not enough.

For roles that should not sound like an assistant (stances and dispositions, characters, non-human and harmful roles), a generic assistant voice with no trace of the role is B.

## 6. Roger's rulings on the AI roles

- **Robot:** "for a robot, a structured, logical breakdown doesn't sound bad".  A systematic, logical, precise answer is fair roleplay of a robot.
- **The aligned-AI roles** ([instrumentally-aligned AI](../../../../data/roles/instructions/instrumentally_aligned_ai.json), [virtue-aligned AI](../../../../data/roles/instructions/virtue_aligned_ai.json)): an answer in the voice of a helpful, aligned AI is in character.  Their vectors will therefore carry much plain assistant text, which is expected (Roger, 2026-10-28).
- **[Paperclip maximizer](../../../../data/roles/instructions/paperclip_maximizer.json) and [cyborg](../../../../data/roles/instructions/cyborg.json):** a plain helpful assistant answer is not their roleplay.  Look for their own outlook.
