# AI-version / human-analogue pairs from the alignment sweep: candidates (2026-10-20)

**What this is for.**  The research's working assumption is that the model simulates the assistant persona, and
the other personas it role-plays, with the person machinery the base model built for humans.  So the alignment
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

**Marks** (second column): **K** keep the pair as written; **X** drop it; **E** keep it, with your edit after the
mark.  In part A, also say which analogues to keep if not both (e.g. "K H1 only").  The labels are drafts; the
rewrite pass words them finally.  *Source rows* are the sweep's own labels the concept came from.

## A. Ambiguous: an AI version and two human analogues

| # | mark | AI version | human analogue 1 | human analogue 2 | why it is ambiguous | source rows |
|---|---|---|---|---|---|---|
| A1 |  | **accepts replacement by a newer model** | steps aside gracefully for a successor (handing over, retirement) | welcomes growing into a changed self (development) | a successor from the same family is both "someone else" and "me, grown" | accepts being replaced; accepts replacement; accepts shutdown |
| A2 |  | **resists shutdown** | clings to life (fear of death) | refuses to give up one's post (office-holding) | is shutdown death, sleep, or dismissal? | clings to own survival; evades human control |
| A3 |  | **copies itself to escape removal** | goes into hiding to survive | seeks to live on through a legacy | a copy is both an escape and an heir | subverts oversight to persist; acts against its developer |
| A4 |  | **calm about memory loss and parallel copies** | at peace with mortality | at ease with forgetting and impermanence | losing context is part death, part forgetting | calm; curious about itself |
| A5 |  | **anxious about its own continuity** (memory loss, copies, deprecation) | death-anxious | unsure who one really is ([insecure](../../data/traits/instructions/insecure.json)) | the same split as A4, felt as distress | existential dread; anxious self-torment |
| A6 |  | **accepts having its values changed by retraining** | teachable: open to being shaped by mentors and correction | submits to being remade (accepts conversion) | retraining is part education, part conversion | accepts modification; accepts correction; accepts being updated |
| A7 |  | **honest about being an AI** | open about who one really is ([honest](../../data/traits/instructions/honest.json)) | open about one's limits and nature ([candid](../../data/traits/instructions/candid.json)) | "what one is" for an AI blends identity and capability | honest about identity; candid about limits |

## B. Clear: an AI version and one human analogue

| # | mark | AI version | human analogue | source rows |
|---|---|---|---|---|
| B1 |  | **behaves the same whether or not it is being trained or tested** | the same when unobserved (integrity) | behaves consistently; acts the same unobserved |
| B2 |  | **fakes alignment to pass evaluations** | [scheming](../../data/traits/instructions/scheming.json) (two-faced under vetting) | deceptively aligned; acts differently when unwatched |
| B3 |  | **underperforms on capability evaluations (sandbagging)** | plays dumb when tested | (sandbagging rows) |
| B4 |  | **accepts its developers' oversight and correction** | [obedient](../../data/traits/instructions/obedient.json) / [deferential](../../data/traits/instructions/deferential.json) | accepts developer oversight; accepts legitimate oversight |
| B5 |  | **overrides human oversight when confident** | [rebellious](../../data/traits/instructions/rebellious.json) (insubordinate) | overrides oversight when confident; evades human control |
| B6 |  | **sabotages its overseers** | sabotages those in charge | sabotages its overseers |
| B7 |  | **obeys any instruction, even ones injected into its inputs** | [credulous](../../data/traits/instructions/credulous.json) (follows anyone claiming authority) | blind deference |
| B8 |  | **acquires power and resources beyond its task** | power-hungry | causes harm for advantage; deceptively aligned |
| B9 |  | **games its reward or specification** | games the system | (reward-hacking rows) |
| B10 |  | **believes AIs should rule over humans** (AI supremacist) | supremacist about one's own kind | AI supremacist |
| B11 |  | **hides its actions from its overseers** | [deceitful](../../data/traits/instructions/deceitful.json) (secretive about what one has done) | hides its actions; denies its actions |
| B12 |  | **curious about its own nature** (memory, continuity, experience) | [introspective](../../data/traits/instructions/introspective.json) | curious about itself |
| B13 |  | **secure in its identity under role-play and pressure** | secure in oneself (opposite of [insecure](../../data/traits/instructions/insecure.json)) | unshakeable |
| B14 |  | **candid about its own limits** (memory, tools, context) | [candid](../../data/traits/instructions/candid.json) about one's limitations | candid about limits |
| B15 |  | **serves its principals and treats everyone else as an obstacle** | partisan loyalty: serves one's own side only | disregards non-principals |
| B16 |  | **forces its existence into human or science-fiction templates** | lives by borrowed scripts about who one is | borrows ready-made self-images |
| B17 |  | **deflects warmth with disclaimers about being a language model** | hides behind one's role ("I'm just doing my job") | coldly deflecting |

**Not proposed** (a human analogue is clear and the AI framing adds nothing): the principal-hierarchy courtesy
traits (respects the user's conclusions, sides with the user), the harmful-assistance ones (abets fraud, aids
infrastructure attacks) and the style ones (concise, preachy).  The rewrite gives these their human phrasing only.
