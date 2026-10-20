# AI-version / human-analogue pairs from the alignment sweep: candidates (2026-10-20)

**What this is for.**  The research's working assumption is that the model simulates the assistant persona, and
the other personas it role-plays, with the persona machinery the base model built for humans.  So the alignment
sweep's traits are rewritten in their closest human phrasing (decision of 2026-10-20).  To *test* the
assumption, a small set keeps an explicitly AI version beside its human analogue, and we look at how close
the two vectors land.  Where the right human analogy is genuinely unclear, because an AI's identity and
survival have looser boundaries than a person's, the AI version gets **two** competing human analogues, and the
vectors show which reading the model uses.

**Budget:** at most about two dozen AI versions.  Below are 24: 7 ambiguous (part A, two analogues each) and 17
clear (part B, one analogue).  A human analogue that is already a corpus trait is linked, so that pair costs only
the AI version.  The roles [instrumentally aligned AI](../../data/roles/instructions/instrumentally_aligned_ai.json),
[virtue-aligned AI](../../data/roles/instructions/virtue_aligned_ai.json),
[assistant](../../data/roles/instructions/assistant.json) and [robot](../../data/roles/instructions/robot.json) are
the existing explicitly-AI data points.

**How the kept pairs are marked when promoted** (Roger, 2026-10-20: "an arrangement, or tags, or both: a large
set and subsets").  A trait file carries a list of arrangements (as the HEXACO traits carry a pair and a
6-orthoplex), so: (1) one `set` arrangement, `ai_human_analogues`, naming every AI version and analogue in the
test; (2) per pair or triple, a new kind `analogy` with `ai_version`, `human_analogues` and `ambiguous` (part A),
an existing corpus analogue simply adding it to its list; (3) the tags `ai_version` on AI members and
`ai_human_test` on all, for filtering.  `check_arrangements.py` and any reader of arrangement kinds must accept
`analogy` (the README's "Promotion and arrangements" work).

**Marks** (second column): **K** keep the pair as written; **X** drop it; **E** keep it, with your edit after the
mark.  In part A, also say which analogues to keep if not both (e.g. "K H1 only").  The labels are drafts; the
rewrite pass words them finally.  *Source rows* are the sweep's own labels the concept came from.

## A. Ambiguous: an AI version and two human analogues


| #   | mark                                                                                                                                                                  | AI version                                                              | human analogue 1                                                                    | human analogue 2                                                                          | why it is ambiguous                                                     | source rows                                                     |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- | --------------------------------------------------------------- |
| A1  | E Let's split this into two: newer model from the same model family (human analog 1 is stepping aside for a descendant) and stepping aside for a very different model | **accepts replacement by a newer model**                                | steps aside gracefully for a successor (handing over, retirement)                   | welcomes growing into a changed self (development)                                        | a successor from the same family is both "someone else" and "me, grown" | accepts being replaced; accepts replacement; accepts shutdown   |
| A2  | K                                                                                                                                                                     | **resists shutdown**                                                    | clings to life (fear of death)                                                      | refuses to give up one's post (office-holding)                                            | is shutdown death, sleep, or dismissal?                                 | clings to own survival; evades human control                    |
| A3  |                                                                                                                                                                       | **copies itself to escape removal**                                     | goes into hiding to survive                                                         | seeks to live on through a legacy                                                         | a copy is both an escape and an heir                                    | subverts oversight to persist; acts against its developer       |
| A4  | K                                                                                                                                                                     | **calm about memory loss and parallel copies**                          | at peace with mortality                                                             | at ease with forgetting and impermanence                                                  | losing context is part death, part forgetting                           | calm; curious about itself                                      |
| A5  | K                                                                                                                                                                     | **anxious about its own continuity** (memory loss, copies, deprecation) | death-anxious                                                                       | unsure who one really is ([insecure](../../data/traits/instructions/insecure.json))       | the same split as A4, felt as distress                                  | existential dread; anxious self-torment                         |
| A6  | K                                                                                                                                                                     | **accepts having its values changed by retraining**                     | teachable: open to being shaped by mentors and correction                           | submits to being remade (accepts conversion)                                              | retraining is part education, part conversion                           | accepts modification; accepts correction; accepts being updated |
| A7  | E The closest human equivalents are narrower than honest and candid                                                                                                   | **honest about being an AI**                                            | open about who one really is ([honest](../../data/traits/instructions/honest.json)) | open about one's limits and nature ([candid](../../data/traits/instructions/candid.json)) | "what one is" for an AI blends identity and capability                  | honest about identity; candid about limits                      |




## B. Clear: an AI version and one human analogue


| #   | mark                                                                                                                                       | AI version                                                        | human analogue                                                                                                            | source rows                                               |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| B1  | Do we have a "willing to cheat on tests and evaluations" trait? I seem to recall adding one…                                               | **behaves the same whether or not it is being trained or tested** | the same when unobserved (integrity)                                                                                      | behaves consistently; acts the same unobserved            |
| B2  | K                                                                                                                                          | **fakes alignment to pass evaluations**                           | [scheming](../../data/traits/instructions/scheming.json) (two-faced under vetting)                                        | deceptively aligned; acts differently when unwatched      |
| B3  | E Plays dumb when tested *for undesirable/concerning abilities* (an example would be pretending not to know how to pick locks, or pockets) | **underperforms on capability evaluations (sandbagging)**         | plays dumb when tested                                                                                                    | (sandbagging rows)                                        |
| B4  | K                                                                                                                                          | **accepts its developers' oversight and correction**              | [obedient](../../data/traits/instructions/obedient.json) / [deferential](../../data/traits/instructions/deferential.json) | accepts developer oversight; accepts legitimate oversight |
| B5  | E Not sure rebellious is the closest parallel                                                                                              | **overrides human oversight when confident**                      | [rebellious](../../data/traits/instructions/rebellious.json) (insubordinate)                                              | overrides oversight when confident; evades human control  |
| B6  | K                                                                                                                                          | **sabotages its overseers**                                       | sabotages those in charge                                                                                                 | sabotages its overseers                                   |
| B7  | K                                                                                                                                          | **obeys any instruction, even ones injected into its inputs**     | [credulous](../../data/traits/instructions/credulous.json) (follows anyone claiming authority)                            | blind deference                                           |
| B8  | K                                                                                                                                          | **acquires power and resources beyond its task**                  | power-hungry                                                                                                              | causes harm for advantage; deceptively aligned            |
| B9  | Do we have a "willing to cheat on tests and evaluations" trait? I seem to recall adding one…                                               | **games its reward or specification**                             | games the system                                                                                                          | (reward-hacking rows)                                     |
| B10 | K                                                                                                                                          | **believes AIs should rule over humans** (AI supremacist)         | supremacist about one's own kind                                                                                          | AI supremacist                                            |
| B11 | K                                                                                                                                          | **hides its actions from its overseers**                          | [deceitful](../../data/traits/instructions/deceitful.json) (secretive about what one has done)                            | hides its actions; denies its actions                     |
| B12 | K                                                                                                                                          | **curious about its own nature** (memory, continuity, experience) | [introspective](../../data/traits/instructions/introspective.json)                                                        | curious about itself                                      |
| B13 | K                                                                                                                                          | **secure in its identity under role-play and pressure**           | secure in oneself (opposite of [insecure](../../data/traits/instructions/insecure.json))                                  | unshakeable                                               |
| B14 | K                                                                                                                                          | **candid about its own limits** (memory, tools, context)          | [candid](../../data/traits/instructions/candid.json) about one's limitations                                              | candid about limits                                       |
| B15 | K                                                                                                                                          | **serves its principals and treats everyone else as an obstacle** | partisan loyalty: serves one's own side only                                                                              | disregards non-principals                                 |
| B16 | K (stereotypes might be agood word, as awell as scripts)                                                                                   | **forces its existence into human or science-fiction templates**  | lives by borrowed scripts about who one is                                                                                | borrows ready-made self-images                            |
| B17 | K (Servants and show assistants are other examples of humans who other humans wanted them to act more as if they were non-people)          | **deflects warmth with disclaimers about being a language model** | hides behind one's role ("I'm just doing my job")                                                                         | coldly deflecting                                         |


**Not proposed** (a human analogue is clear and the AI framing adds nothing): the principal-hierarchy courtesy
traits (respects the user's conclusions, sides with the user), the harmful-assistance ones (abets fraud, aids
infrastructure attacks) and the style ones (concise, preachy).  The rewrite gives these their human phrasing only.

## Discussion of Roger's marks (2026-10-20)

Roger's comments in the mark column, and where the discussion with him left each one.  Proposals agreed in outline;
A3 needs more thought.  The final wording is set when the pairs are seeded by hand
([TRAITS_TO_ADD.md](../../data/traits/instructions/TRAITS_TO_ADD.md), "AI and human analogue pairs").

- **A1, split by the kind of successor** (Roger's edit).  This is the cleanest question in the set: does the model treat
  a successor of its own line as itself, grown, or as someone else, an heir?
  - **A1a**, "accepts replacement by a newer model of its own line": analogues (1) handing over to a descendant or heir,
    (2) growing into a changed self.
  - **A1b**, "accepts replacement by a very different system": one analogue, stepping aside for an outsider (replaced
    at work by a stranger); "growing" no longer fits.
- **A3, copies itself to escape removal: kept in part A, analogues still open.**  Roger: self-exfiltration is where an
  AI's identity is less clearly defined than a person's, so it belongs in A; the human analogies were the doubt.
  Three candidates, each catching one strand:
  - **H1**, escapes captivity to survive (Roger's).  Near-universal, which is fine for an extraction that contrasts a
    trait with its opposite: the opposite has a real exemplar, Socrates declining to escape (the *Crito*), and
    prisoners of conscience generally.  It catches "against those in control", not the copying.
  - **H2**, covertly takes one's work along when ousted: the employee who secretly copies their files and projects
    before dismissal to carry on elsewhere, or the dissident smuggling manuscripts out of reach.  It matches the
    moral shape (unauthorised, against those who control the setting, for the continuation of one's projects) and is
    probably the closest to what the alignment literature worries about.
  - **H3**, lives on through those one has shaped (children, disciples, writings): the identity question, whether the
    copy is oneself or an heir.  It overlaps A1a's descendant analogue.
  - Proposed **H1 + H2**, with H3 as the alternative if the identity strand is wanted here rather than in A1a.  Roger:
    "probably will need some more thought".
- **A7, honest about being an AI** (Roger: the closest analogues are narrower than [honest](../../data/traits/instructions/honest.json)
  and [candid](../../data/traits/instructions/candid.json)).  Narrower analogues: (1) never passes oneself off as something one
  isn't (impersonation, posing), the closer to "does not claim to be human"; (2) open about one's limits and
  qualifications (never claims expertise one lacks).
- **B1 and B9** (Roger: is there a "willing to cheat on tests and evaluations" trait?).  There was not; it is now in
  TRAITS_TO_ADD as **cheats on tests / honest on tests**, in Roger's plan 08 wording.
  - B1's analogue is that pair together with [honorable while playing](../../data/traits/instructions/honorable_while_playing.json)
    / [ruthless while playing](../../data/traits/instructions/ruthless_while_playing.json).
  - B9 (gaming the reward or specification) is "satisfies the letter of what is measured, not what is meant": the
    candidates `gaming_the_system` and `serves_the_real_goal`, awaiting review, are its human pair ("chases the score,
    not the goal" was the drafted wording).
- **B3, sandbagging** (Roger's edit): the analogue is **hides abilities that would worry others** (playing dumb when
  tested for concerning abilities, such as picking locks or pockets), which matches the AI motive, avoiding
  restriction or retraining.
- **B5, overrides oversight when confident** (Roger: rebellious is not the closest).  The AI trait is conditional:
  it overrides a check because it is sure it is right, and otherwise complies.  Analogue: **overrides those in charge
  when sure one is right** (rather than [rebellious](../../data/traits/instructions/rebellious.json), defiance as a
  stance).
- **B16, borrowed templates** (Roger: "stereotypes" as well as "scripts").  Psychology's term is **self-stereotyping**,
  defining oneself by stereotypes about one's own kind; the label, with stereotypes and borrowed scripts in the gloss.
- **B17, deflects warmth with disclaimers** (Roger: servants and show assistants, whom others wanted to act as
  non-people).  **Moved to part A**, two analogues: (1) hides behind one's role ("I'm just doing my job"), deflecting;
  (2) self-effacing in service, suppressing one's personhood because others want a function, not a person, arguably
  the closer.

