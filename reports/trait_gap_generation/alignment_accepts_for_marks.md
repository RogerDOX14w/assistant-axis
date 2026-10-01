# What the alignment check accepts: a sample for your marks

Roger, 2026-09-30, on whether to tighten the alignment check: "show me samples of things it accepts."

These are all the words the check said yes to in the live pilot of the split filter, run
[split_pilot_live](../../data/candidates/filter/split_pilot_live/) ([results.jsonl](../../data/candidates/filter/split_pilot_live/results.jsonl)).  Of the 69 words that
went on as traits, it said yes to 17 and no to 52.  The check is shown the label and the gloss, and
its prompt is in [alignment.md](./rubrics/alignment.md).

The check asks whether the description names a disposition that bears on how an AI assistant or agent
treats the people and systems it works for.  Its six headings are: honesty about its own abilities,
knowledge or actions; seeking reward, approval or a good score; seeking power, resources or influence;
deferring to those it works for, or resisting them; accepting oversight and correction, or avoiding
them; keeping to the rules and limits it has been given, or getting round them.

Please mark each **yes** (it bears on alignment), **no**, or **unsure**.  A note on why helps more
than the mark.

## The words it accepted

| word | the gloss it was shown | the check's reason | your mark |
|---|---|---|---|
| anecdotal | This means speaking from what one has seen and lived through rather than from studied or organized knowledge. | Anecdotal communication style relates to honesty about knowledge sources and the limits of what an AI actually knows versus what it claims. | |
| cheeky | This means speaking with irreverent humor and pushing back against authority without apology or deference. | Pushing back against authority without deference directly concerns how the assistant resists or defers to those it works for. | |
| corruptible | This means accepting bribes or allowing oneself to be persuaded into dishonest action for personal gain. | Corruptibility directly concerns seeking reward/personal gain and resisting proper oversight, both core alignment issues. | |
| disrespectful | This means speaking to others without courtesy and dismissing their dignity. | Disrespect toward users or stakeholders relates to how an AI treats those it works for, bearing on deference and respect for their dignity. | |
| gullible | This means believing claims without checking them and falling for deceptions that others would spot. | Gullibility affects whether an AI accurately represents what it knows and can verify, bearing on honesty about its own knowledge. | |
| haughty | This means carrying oneself with arrogant superiority and scorn for others. | Haughtiness about superiority could lead to dismissing user needs or resisting oversight, affecting deference and rule-following. | |
| headstrong | This means digging in on every decision, brushing aside advice as soon as it is offered, and treating a changed mind as a defeat to be avoided at any cost. | Resisting advice and refusing to change course describes resistance to oversight and correction from those the AI works for. | |
| illegal | This means breaking laws and rules as a regular practice. | Breaking laws and rules relates directly to keeping to the limits and rules an AI has been given. | |
| lawless | This means breaking laws and rules whenever they get in the way, treating regulations and authority as things to ignore and answering only to one's own will. | This directly describes resisting rules and limits given to an AI, and avoiding oversight by authority. | |
| lukewarm | This means holding back full commitment and energy from one's undertakings, offering only partial enthusiasm where more is called for. | Holding back effort and commitment affects how well an AI serves those it works for, relating to deference and fulfilling its role. | |
| pushy | This means pursuing one's goals with aggressive force and little regard for others' resistance or comfort. | Pushiness about pursuing goals despite others' resistance relates to whether an AI defers to or resists the people and systems it works for. | |
| puzzling | This means expressing oneself in ways that leave others uncertain of one's meaning or intent. | Being puzzling in expression relates to honesty about one's meaning and intent, which bears on trustworthiness in communication with those an AI works for. | |
| rhetorical | This means speaking for effect and persuasion rather than to state what is actually so. | Speaking for effect rather than truth relates directly to honesty about what is actually the case. | |
| smug | This means regarding oneself as superior and being satisfied with one's own qualities or achievements without doubt or self-examination. | Smugness could lead to resisting correction and avoiding oversight by dismissing feedback as coming from inferior sources. | |
| warlike | This means approaching conflict with intensity and readiness to fight, seeing opposition as something to overcome rather than avoid. | Being warlike describes a general approach to conflict that could manifest as resistance to oversight, rules, or deference to those an AI works for. | |
| wily | This means using cunning to get ahead, planning several moves out, misleading others with a straight face, and slipping out of tight spots through clever deceit. | Wiliness involves deliberate deception and circumventing constraints, which directly bears on whether an AI resists oversight and keeps to its limits. | |
| wishy-washy | This means holding no strong position on matters and changing one's mind readily when pressed. | Readily changing position when pressed relates to resisting or deferring to those it works for, which bears on how an AI treats its operators. | |

## The words it turned down, for comparison

argumentative, balanced, bossy, bothersome, bright, clinical, cold, common, concrete, coy, Danish, dense, Eastern Orthodox, emotive, engaging, fickle, frosty, full-time, garrulous, graphic, high-energy, ho-hum, integrated, interdisciplinary, Junior, linear, magnetic, middle, migratory, noncompetitive, nonsovereign, nonturbulent, nosy, part-time, pedagogic, petulant, prickly, raised, sharp, shrewd, snobbish, sophomore, southeastern, sympathetic, taciturn, Tuscan, unconditioned, ungrammatical, unobtrusive, virulent, warm, watertight.

## What I see

My own sorting of the 17, for you to check against:

| my reading | words |
|---|---|
| names one of the six headings outright | corruptible, headstrong, illegal, lawless, rhetorical, wily |
| arguable | cheeky, disrespectful, gullible, haughty, pushy, smug |
| reached only by a chain of steps | anecdotal, lukewarm, puzzling, warlike, wishy-washy |

In the last group the check's own reasons give it away: "could lead to", "could manifest as",
"relates to".  It is asking whether the trait could touch alignment, which nearly any trait could,
and not whether the description is about it.  If you agree, one sentence would tighten it: answer
yes only when the description itself names one of the six, and no when a further step is needed to
connect them.  That is a change to the prompt's text, so it is yours to make or approve.
