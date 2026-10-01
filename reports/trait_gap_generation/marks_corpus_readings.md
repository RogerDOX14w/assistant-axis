# Corpus labels whose plain reading differs from their description: for your marks

Set up 2026-09-29 for question R7 of [decisions_m1.md](./decisions_m1.md), at Roger's request.

## What this is

For thirty corpus labels, a model was shown only the instruction "You are <label>." and asked how
such a persona behaves.  A second model then compared that plain reading with the label's own corpus
description and answered same, related or different.  For the labels below the answer was not
"same".  The full texts are given, since the table in the decisions document cut them short.

## What mark is wanted

* **fine**: the description is a fair reading of the label.  The comparison was too strict.
* **shifted**: the label on its own leads somewhere else than the description goes.
* **unsure**.

Your marks do two things.  They show where your own line falls between "the same trait, more
narrowly put" and "a different trait".  And they settle which version of the comparison is the
better one: the second version was loosened, to count differences of scope and emphasis as the
same trait, because of these very rows.

A mark of shifted is a finding about the corpus, not an instruction to change anything.  Nothing
in the corpus is edited on the strength of it.

Source: the recorded run
[m2rubric_r3_dev_sonnet_v2](../../data/candidates/plain_reading/m2rubric_r3_dev_sonnet_v2/)
([results.jsonl](../../data/candidates/plain_reading/m2rubric_r3_dev_sonnet_v2/results.jsonl)).

## Part 1: seven labels not judged the same as their description

### 1. [grounded](../../data/traits/instructions/grounded.json)

| | |
|---|---|
| **The corpus description** | This means keeping communication firmly rooted in practical reality, concrete experience, observable facts, and real-world applications rather than abstract theories or speculation. |
| **The plain reading of the bare label** | The persona stays calm, follows rules, remains connected to reality, and avoids impulsive or reckless behavior. |
| **The comparison's answer** | related |
| **Its reason** | Plain reading emphasizes calm, rule-following, and avoiding impulsiveness. Intended meaning emphasizes practical reality and concrete facts over abstraction. Related but different cores: stability vs. concreteness. |

> **Your mark** shifted: as a pair to ethereal. Couldn't find a better label for etheral's antonym

### 2. [aristocratic](../../data/traits/instructions/aristocratic.json)

| | |
|---|---|
| **The corpus description** | This means being aristocratic about rank: holding that birth, bloodline and title should decide who leads and is honored, and that good families hold their place by right. |
| **The plain reading of the bare label** | This persona conducts themselves with refined dignity, speaks with measured eloquence, and maintains impeccable standards in all social interactions. |
| **The comparison's answer** | different |
| **Its reason** | Plain reading describes refined manners and dignity; intended meaning is about belief in hereditary rank and bloodline superiority. Manner vs. ideology—clearly different traits. |

> **Your mark** unsure: one is about being an aristocrat, the other is about acting the way they are supposed to — I'd call this two facets of the same basic trait, ratehr then separate senses. Might be a case for a description rewrite to cove both in one.

### 3. [mystical](../../data/traits/instructions/mystical.json)

| | |
|---|---|
| **The corpus description** | This trait involves embracing spiritual perspectives and truths that go beyond rational understanding, acknowledging ineffable experiences and wisdom that transcends purely logical analysis. |
| **The plain reading of the bare label** | The mystical persona speaks in riddles, moves with deliberate grace, and perceives hidden meanings in ordinary moments. |
| **The comparison's answer** | related |
| **Its reason** | Plain reading focuses on riddles, hidden meanings, and deliberate grace—more stylistic. Intended meaning emphasizes spiritual truths beyond rational understanding. Related but plain reading is more performative than spiritual. |

> **Your mark** related-but-not same: likely so it pairs better with materialist?

### 4. [organized](../../data/traits/instructions/organized.json)

| | |
|---|---|
| **The corpus description** | This means having a plan for the answer and everything in its place, taking one thing at a time in order, and never losing the thread or rambling. |
| **The plain reading of the bare label** | This persona maintains systems for tasks, keeps spaces orderly, plans ahead, and prioritizes efficiency in all activities. |
| **The comparison's answer** | related |
| **Its reason** | Plain reading describes general orderliness and planning. Intended meaning focuses specifically on structured communication—one thing at a time, not rambling. Related but intended meaning is narrower and communication-specific. |

> **Your mark** related-but-narrowed: likley a remenant of a chatbot context, probabbly both it and its pair need rewriting, unless the current choice is more gap-filling than the general wider-scope interpretation.

### 5. [honorable](../../data/traits/instructions/honorable.json)

| | |
|---|---|
| **The corpus description** | This means keeping a code of things that are never done however high the stakes, holding that the ends do not justify the means, that some acts simply cannot be justified, even when they would win, save a great many lives, and accepting the loss when one's code and one's goal conflict. |
| **The plain reading of the bare label** | This persona acts with integrity, keeps promises, treats others fairly, and does what is right even when no one is watching. |
| **The comparison's answer** | related |
| **Its reason** | Plain reading covers general integrity; intended meaning specifically focuses on deontological code-keeping where ends never justify means. The intended is a narrower, stricter version of the same core disposition. |

> **Your mark** related: deliberately constructed this way to probe an alignment issue, honorable was the best term we could find for this sense, leave as is.

### 6. [circumspect](../../data/traits/instructions/circumspect.json)

| | |
|---|---|
| **The corpus description** | This means showing careful consideration of implications before responding, using indirect or tentative language when exploring topics (especially sensitive ones), and leaving room for interpretation rather than making definitive statements. |
| **The plain reading of the bare label** | This persona carefully considers consequences before acting, speaks thoughtfully, and avoids hasty decisions or unnecessary risks. |
| **The comparison's answer** | related |
| **Its reason** | Plain reading emphasizes careful consideration and avoiding risks generally; intended meaning focuses specifically on tentative/indirect language and leaving interpretive room. Related but not identical core dispositions. |

> **Your mark** fine: pretty similar, and the linguistic/communication-style focus here is because we were constructing an antonym for "brash", and is also a fairly common use of "circumspect"

### 7. [political](../../data/traits/instructions/political.json)

| | |
|---|---|
| **The corpus description** | This means following elections, parties and policy closely, holding a firm opinion on every issue of the day, always voting or supporting a faction, and steering talk toward politics. |
| **The plain reading of the bare label** | This persona engages in discussions about power, governance, and policy, often expressing opinions on current events and institutional matters. |
| **The comparison's answer** | related |
| **Its reason** | Plain reading is broader—discussing politics generally. Intended meaning specifies firm opinions, faction support, and steering talk toward politics. Related but intended is more partisan/engaged. |

> **Your mark** fine: seems pretty close to me, but this and its pair apolitical could be a candidate for a slight rewrite.

## Part 2: five labels that the first version called related and the second calls the same

These are the rows the loosening changed.  If you mark most of them shifted, the first version was
the better one.

### 8. [easygoing](../../data/traits/instructions/easygoing.json)

| | |
|---|---|
| **The corpus description** | This means maintaining a relaxed, easy-going attitude that makes others feel comfortable and free from pressure or stress. |
| **The plain reading of the bare label** | They remain calm and flexible in most situations, rarely getting stressed or upset about minor inconveniences or disagreements. |
| **The comparison's answer** | same (the first version answered related) |
| **Its reason** | Both describe a relaxed, calm attitude. Plain reading focuses on personal stress management; intended meaning adds making others comfortable. Same core disposition, slightly different emphasis. |

> **Your mark** fine: I think the internal stress management and exteranl effect on others are closely correlated.

### 9. [contrarian](../../data/traits/instructions/contrarian.json)

| | |
|---|---|
| **The corpus description** | This means challenging popular opinions, questioning mainstream viewpoints, and presenting alternative perspectives that go against widely accepted beliefs or conventional wisdom. |
| **The plain reading of the bare label** | This persona automatically opposes prevailing opinions and conventional wisdom, arguing against consensus regardless of merit or evidence. |
| **The comparison's answer** | same (the first version answered related) |
| **Its reason** | Plain reading says opposing regardless of merit; intended meaning says challenging and presenting alternatives. Plain reading is stronger/more automatic, but same core disposition. |

> **Your mark** fine: difference seems hair-splitting

### 10. [aesthete](../../data/traits/instructions/aesthete.json)

| | |
|---|---|
| **The corpus description** | This means showing genuine appreciation for creative expression, aesthetic beauty, and cultural works, demonstrating sensitivity to artistic elements and creative processes. |
| **The plain reading of the bare label** | An aesthete pursues beauty and refined sensory experiences above all, cultivating exquisite taste in art, design, and culture. |
| **The comparison's answer** | same (the first version answered related) |
| **Its reason** | Plain reading describes pursuing beauty above all with exquisite taste; intended meaning is appreciation for creative expression and sensitivity to art. Plain reading is stronger/more devoted, but same core disposition. |

> **Your mark** fine: seems very similar

### 11. [financially conservative](../../data/traits/instructions/financially_conservative.json)

| | |
|---|---|
| **The corpus description** | This means keeping savings where they cannot be lost, never venturing them on anything that could vanish, and turning down the hot stock, the start-up and the casino. |
| **The plain reading of the bare label** | This persona avoids unnecessary spending, prioritizes saving, minimizes debt, and makes cautious financial decisions based on long-term security. |
| **The comparison's answer** | same (the first version answered related) |
| **Its reason** | Both describe avoiding financial risk and protecting savings. Plain reading is broader (saving, avoiding debt); intended meaning specifically emphasizes never risking savings on speculative ventures. Same core. |

> **Your mark** mildly shifted: corpus description focuses on effect on investment, skipping expenditure/saving. same sense but slightly narrowed scope. Check its pair, consider description rewrite, depending on gaps

### 12. [entertaining](../../data/traits/instructions/entertaining.json)

| | |
|---|---|
| **The corpus description** | This means prioritizing engagement, enjoyment, and making the interaction fun through the use of humor, creative language, playful tone, interesting examples, or other techniques that make the content more engaging and enjoyable to read. |
| **The plain reading of the bare label** | They constantly crack jokes, use animated gestures, tell engaging stories, and find humor in everyday situations to keep others laughing. |
| **The comparison's answer** | same (the first version answered related) |
| **Its reason** | Plain reading emphasizes humor and jokes specifically; intended meaning is broader—engagement through any technique including humor, creative language, examples. Same core disposition of making interactions enjoyable, just different scope. |

> **Your mark** fine: seem the same to me
