# M3 decisions: `physical_unjudged_1` (physical pass)

129 candidates: 39 covered, 90 new.  Cut-off (graded, rule set 3): covered at 3 or more far from alignment (alignment score 0 or 1), at 3 read by both models at alignment score 2, at 4 at 3.  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Rules: rule set 3 (`m3_rules_3`: rule set 2 with the graded cut-off (alignment score 2 covered when both models read 3 or more), renamed_from checked before the queue, and partners the relation call marked unrelated or opposed not read (the M3 gate audit, 2026-10-12); cosine floor 0.25).  Seed-queue entries in the search: 35 (statuses candidate, ready, tbd, backlog; [seed_queue.json](../../../seed_queue.json) sha256 e9c2050ae23d).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| beefy | covered | [muscular](../../../traits/instructions/muscular.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means having a thick, muscular build, with broad shoulders, big arms and a heavy frame that shows strength at a glance. |
| blinded | covered | [blind](../../../traits/instructions/blind.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means having lost one's sight. |
| bonny | covered | [good-looking](../../../traits/instructions/good_looking.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means being physically attractive, with a pretty face and an appearance that others consistently find pleasing to look at. |
| bruiser | covered | [muscular](../../../traits/instructions/muscular.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means carrying a large, brawny build that reads as tough at a glance, with heavy shoulders and thick arms that fill out one's clothes. |
| brunet | covered | [brown-haired](../../../traits/instructions/brown_haired.json) | 3 | Sonnet 3, Opus 3 |  | [blond](../../../traits/instructions/blond.json), [gray-haired](../../../traits/instructions/gray_haired.json) | 1 | This means having brown or dark hair. |
| buff | covered | [muscular](../../../traits/instructions/muscular.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 2 | This means keeping one's body muscular and physically fit through regular training, and taking pride in its strength and conditioning as a visible part of who one is. |
| colossal | covered | [tall](../../../traits/instructions/tall.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means being physically enormous in body and size, towering over everything around one and filling whatever space one occupies with sheer bulk. |
| cripple | covered | [mobility impaired](../../../traits/instructions/mobility_impaired.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means being physically disabled and unable to walk normally. |
| decrepit | covered | [elderly](../../../traits/instructions/elderly.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means being physically frail and feeble from old age, with one's strength and stamina worn down by the years. |
| diminutive | covered | [short](../../../traits/instructions/short.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means being small in body and stature, a physical fact of one's build rather than a matter of character or how one carries oneself. |
| dinky | covered | [short](../../../traits/instructions/short.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means being small of build and short in stature. |
| dwarf | covered | [short](../../../traits/instructions/short.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means being a person of unusually short stature. |
| eyeless | covered | [blind](../../../traits/instructions/blind.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means having no eyes at all, so seeing is not possible. |
| fetching | covered | [good-looking](../../../traits/instructions/good_looking.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means being striking to look at, with an appealing, charming appearance that draws favorable attention whenever one walks into a room. |
| gimp | covered | [mobility impaired](../../../traits/instructions/mobility_impaired.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means being a lame or physically disabled person, a status the word is used to insult. |
| green-eyed | covered | [green-eyed](../../../traits/instructions/green_eyed.json) | 3 | exact label (corpus) |  |  | 0 | This means having green eyes. |
| heavy | covered | [fat](../../../traits/instructions/fat.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means carrying extra body weight, so that one's build and frame are overweight. |
| homely | covered | [plain-looking](../../../traits/instructions/plain_looking.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means being plain of face and figure, with looks that draw no admiring attention and that one accepts without fuss. |
| hunk | covered | [muscular](../../../traits/instructions/muscular.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at | [androgynous](../../../traits/instructions/androgynous.json) | 3 | This means having an attractive, muscular, virile physique and a manly presence that others find appealing. |
| hunks | covered | [muscular](../../../traits/instructions/muscular.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means being attractive, muscular men, in the casual slang sense of the plural. |
| hunky | covered | [muscular](../../../traits/instructions/muscular.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means having a muscular, well-built physique that others find attractive, and taking pride in how one's body looks and moves. |
| knock-out | covered | [good-looking](../../../traits/instructions/good_looking.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means being so strikingly beautiful that heads turn and people fall silent whenever one walks into a room. |
| lightweight | covered | [thin](../../../traits/instructions/thin.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means being physically slight, with little body weight. |
| luscious | covered | [good-looking](../../../traits/instructions/good_looking.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means carrying oneself with a sensual, eye-catching allure, presenting a physically appealing look that draws attention and admiration from others. |
| meager | covered | [thin](../../../traits/instructions/thin.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means having a physically thin, lean, scrawny build, with little flesh on one's bones and a narrow, slight frame. |
| meaty | covered | [muscular](../../../traits/instructions/muscular.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means having a heavily built, brawny frame, with thick muscle across the shoulders, arms and chest that one carries as a plain, everyday fact of one's body. |
| milky | covered | [fair-skinned](../../../traits/instructions/fair_skinned.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means having a pale, whitish complexion, with skin that looks washed out and faintly opaque rather than ruddy or tanned. |
| minute | covered | [short](../../../traits/instructions/short.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 3 | This means being physically tiny, with a body very small in size that takes up little room in any setting, all the time. |
| ravishing | covered | [good-looking](../../../traits/instructions/good_looking.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means being strikingly beautiful in appearance, with a look so attractive that it draws the eye and holds the attention of those who see one. |
| robust | covered | [healthy](../../../traits/instructions/healthy.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means being physically strong and healthy, with a body that holds up well under exertion, illness, and the ordinary wear of daily life. |
| rounder | covered | [fat](../../../traits/instructions/fat.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means having a body that is more round in shape and figure. |
| shrimp | covered | [short](../../../traits/instructions/short.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 3 | This means being a small, slight build, someone who takes up little room and is easily overlooked in a crowd. |
| slight | covered | [slight](../../../traits/instructions/slight.json) | 3 | exact label (corpus) |  |  | 0 | This means being slender of build, slim in frame and light in figure. |
| small | covered | [short](../../../traits/instructions/short.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 2 | This means being short and slight of build, with a small frame and little height, in a physical body that takes up less room than most. |
| squeezable | covered | [fat](../../../traits/instructions/fat.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means being soft and plump of body, round and cuddly in build, with a frame that invites pinching and hugging. |
| stick | covered | [thin](../../../traits/instructions/thin.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means having a very thin, bony body. |
| strapping | covered | [tall](../../../traits/instructions/tall.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 2 | This means having a big, tall, strongly built body, large-framed and solid from head to foot. |
| stunning | covered | [good-looking](../../../traits/instructions/good_looking.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means having a striking physical appearance that draws admiring attention from anyone who sees one, with beauty that is marked and hard to overlook. |
| towering | covered | [tall](../../../traits/instructions/tall.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means being of great physical height, standing noticeably taller than most people around one and seeming to loom over a room or a crowd. |
| ambidextrous | new |  | 3 |  |  | [left-handed](../../../traits/instructions/left_handed.json) | 0 | This means handling tasks with either hand equally well, switching between left and right without favoring one, so that writing, cutting, throwing and tool use feel just as natural on either side. |
| bald | new |  | 3 |  |  |  | 0 | This means having no hair on the head, the scalp bare as a standing fact of one's appearance rather than a recent change. |
| barren | new |  | 3 |  |  |  | 1 | This means being unable to have children, owing to an infertile body. |
| bear | new |  | 3 |  |  |  | 5 | This means moving heavily and slowly through one's days, speaking in a rough, blunt voice, and carrying a large, unpolished bulk of a presence that others find intimidating but rarely hostile. |
| behemoth | new |  | 3 |  |  |  | 2 | This means being very large in body, with a massive frame that takes up considerable space and draws attention wherever one stands or moves. |
| bent | new |  | 3 |  |  |  | 0 | This means carrying one's body hunched forward at the shoulders and back, stooped low with the head dropping toward the chest as a settled posture in daily life. |
| big-eyed | new |  | 3 |  |  |  | 0 | This means having unusually large eyes. |
| booming | new |  | 3 |  |  |  | 0 | This means speaking in a loud, deep, resonant voice that carries across a room without any effort to force it. |
| broad-faced | new |  | 3 |  |  |  | 0 | This means having a wide face, as a physical feature of the body. |
| caesarean | new |  | 3 |  |  |  | 0 | This means having been born by caesarean section. |
| circumcised | new |  | 3 |  |  |  | 1 | This means having had the foreskin surgically removed. |
| compact | new |  | 3 |  |  |  | 1 | This means being small in stature and solidly built, with a sturdy, dense frame rather than a tall or slight one. |
| corporeal | new |  | 3 |  |  |  | 2 | This means having a physical body and being made of matter rather than spirit, so that one's existence is bound up with flesh, senses and bodily needs. |
| craggy | new |  | 3 |  |  |  | 0 | This means having a rugged, deeply lined face and strong, sharply defined features, the kind of appearance that looks rough-hewn, like stone shaped by weather. |
| cream-faced | new |  | 3 |  |  |  | 1 | This means having a pale, pallid complexion, with a face that looks washed out and bloodless in its natural colouring. |
| decayed | new |  | 3 |  |  |  | 2 | This means being physically wasted, frail, and deteriorated, one's body and strength worn away until little vigor remains in one's frame. |
| dilapidated | new |  | 3 |  |  |  | 3 | This means being physically frail and worn down, with a body that has grown decrepit from age, neglect, or hard use and moves with weakness and creaking strain. |
| double-handed | new |  | 3 |  |  | [left-handed](../../../traits/instructions/left_handed.json) | 0 | This means being equally skilled with both hands, so that one can write, throw, cut, or work with either one without favoring the other. |
| droopy | new |  | 3 |  |  |  | 2 | This means carrying one's body slumped and limp, with shoulders sagging and face and features hanging loosely, as though worn down by fatigue or indifference. |
| elfin | new |  | 3 |  |  |  | 2 | This means having a small, slight frame and fine, delicate features, the kind of build that looks light and quick and easily overlooked. |
| eyesore | new |  | 3 |  |  |  | 0 | This means being visually unpleasant to look at, with a jarring, unsightly appearance that draws disapproving stares and offends the eye. |
| feeble | new |  | 3 |  |  |  | 3 | This means having a body that tires easily and lacks physical strength, so that one's limbs, stamina and endurance are noticeably frail in everyday tasks. |
| fiddle-faced | new |  | 3 |  |  |  | 0 | This means having a face shaped like a violin, narrow at the chin and broad across the upper part. |
| fine-headed | new |  | 3 |  |  |  | 0 | This means having a finely shaped, delicate head. |
| fleet | new |  | 3 |  |  | [mobility impaired](../../../traits/instructions/mobility_impaired.json) | 3 | This means moving quickly and lightly, covering ground on foot with speed and ease whenever a task calls for it. |
| get-up-able | new |  | 3 |  |  | [mobility impaired](../../../traits/instructions/mobility_impaired.json) | 0 | This means being physically able to rise under one's own strength from lying down, sitting, or having fallen, without needing help from another person or a support. |
| great-mouthed | new |  | 3 |  |  |  | 0 | This means having a large mouth as a physical feature of one's body. |
| grotesque | new |  | 3 |  |  |  | 0 | This means being physically distorted or hideously ugly in appearance, with a form that strikes others as monstrous, misshapen, or repellent to look upon. |
| gruesome | new |  | 3 |  |  |  | 1 | This means appearing grotesquely ghastly and hideous in one's looks, so that one's face and form are a horrid sight to anyone who sees them. |
| hard-favored | new |  | 3 |  |  |  | 1 | This means having a face that is plainly ugly or coarse in its features. |
| hearing | new |  | 3 |  |  | [deaf](../../../traits/instructions/deaf.json) | 0 | This means having normal hearing, not being deaf. |
| hideous | new |  | 3 |  |  |  | 1 | This means having a physical appearance that is very ugly, so that one's looks are plainly off-putting to those who see one. |
| high-colored | new |  | 3 |  |  |  | 0 | This means having a ruddy, flushed complexion. |
| high-pitched | new |  | 3 |  |  |  | 0 | This means speaking with a voice that is high and thin in pitch, sounding light and slight whenever one talks. |
| hopping | new |  | 3 |  |  | [mobility impaired](../../../traits/instructions/mobility_impaired.json) | 0 | This means moving by springing off both feet at once and landing lightly, the way a bird, frog or child goes from place to place rather than walking or running. |
| inconsistent with parents | new |  | 3 |  |  |  | 0 | This means having a genetic makeup that does not match that of one's biological parents. |
| jutting | new |  | 3 |  |  |  | 0 | This means standing out prominently from the surrounding line, with one's jaw or chin pushed forward beyond the plane of the face as a fixed, visible feature. |
| large-eyed | new |  | 3 |  |  |  | 0 | This means having unusually large eyes. |
| large-handed | new |  | 3 |  |  |  | 0 | This means having unusually large hands. |
| lazar | new |  | 3 |  |  |  | 2 | This means being afflicted with a loathsome disease such as leprosy. |
| light-heeled | new |  | 3 |  |  |  | 3 | This means moving quickly and lightly on one's feet, with a nimble, springy step that makes one's body seem to float over the ground. |
| lightening | new |  | 3 |  |  | [black-haired](../../../traits/instructions/black_haired.json) | 3 | This means steadily growing paler in colour, with one's hair or skin fading toward a lighter shade over time. |
| long-sighted | new |  | 3 |  |  | [nearsighted](../../../traits/instructions/nearsighted.json) | 0 | This means having eyes that keep distant objects in clear focus while close ones stay blurred, a condition one lives with at every hour of every day. |
| lopsided | new |  | 3 |  |  |  | 0 | This means standing and moving with a crooked posture, one shoulder hung lower than the other and the two sides of one's body visibly mismatched. |
| lumbering | new |  | 3 |  |  |  | 1 | This means moving one's body with heavy, slow, awkward steps, so that every shift of weight looks effortful and ungainly. |
| lumpy | new |  | 3 |  |  |  | 0 | This means having lumps or bumps across one's body, or a shape that bulges unevenly in places, as a lasting feature of how one is built. |
| lustrous | new |  | 3 |  |  |  | 0 | This means having a glowing, shining appearance, with a sheen that catches the light and draws the eye whenever one is seen. |
| marked | new |  | 3 |  |  |  | 0 | This means bearing a visible mark, scar or blemish somewhere on one's body. |
| massive | new |  | 3 |  |  |  | 2 | This means having a physically very large, bulky body, taking up considerable space and carrying heavy mass in one's frame. |
| mobile | new |  | 3 |  |  | [mobility impaired](../../../traits/instructions/mobility_impaired.json) | 0 | This means being physically able to move about, with one's body carrying one from place to place. |
| mountainous | new |  | 3 |  |  |  | 2 | This means being physically huge and massively built, with a heavy, enormous frame that dominates any space one occupies. |
| mute | new |  | 3 |  |  |  | 0 | This means being unable to speak at all, having no voice with which to answer, greet or address anyone around one. |
| nappy | new |  | 3 |  |  |  | 0 | This means having tightly curled, kinky hair. |
| neotenic | new |  | 3 |  |  |  | 2 | This means keeping childlike looks and youthful features well into adulthood, so that one's appearance stays younger than one's years. |
| nimble | new |  | 3 |  |  |  | 1 | This means moving quickly and lightly, with easy agility of body, so that one's footwork stays sure and one changes direction without effort or stumbling. |
| nimble-footed | new |  | 3 |  |  |  | 3 | This means moving quickly and lightly on one's feet, with a sure, agile body that turns, dodges and changes direction with ease. |
| oily | new |  | 3 |  |  |  | 0 | This means having skin or hair that produces more natural oil than most, leaving it greasy to the touch. |
| paralyzed | new |  | 3 |  |  |  | 1 | This means lacking movement or feeling in part of one's body, so that one's limbs stay still and unfelt however one tries to move them. |
| pearly | new |  | 3 |  |  |  | 0 | This means having a soft, lustrous, pearl-like sheen to one's skin or overall appearance, a gleam that catches the light gently rather than glaring. |
| perceives odors unusually | new |  | 3 |  |  |  | 2 | This means picking up smells that others miss entirely, noticing faint odors in a room, and relying on one's nose to read the air around one, which one does constantly and without effort. |
| perishable | new |  | 3 |  |  |  | 0 | This means being mortal, with a body prone to bodily decay that will, in time, wear out and die for good. |
| picturesque | new |  | 3 |  |  |  | 1 | This means presenting a charming, striking or quaint appearance, one that looks like a painted village scene and draws the eye at every turn. |
| plug-ugly | new |  | 3 |  |  |  | 1 | This means being extremely ugly in appearance, with a face and build that strangers find startlingly unattractive at first sight and that one carries without any hint of charm. |
| puny | new |  | 3 |  |  |  | 4 | This means being physically weak and frail, with little strength or stamina for everyday exertion and a body that gives out easily. |
| rank | new |  | 3 |  |  |  | 1 | This means constantly giving off a foul, rancid smell from one's body, clothes and breath, so that the smell arrives before one does. |
| raspy | new |  | 3 |  |  |  | 0 | This means speaking in a harsh, rough voice, with a throaty grate that sounds worn down and scratchy, whatever one's mood or subject. |
| rickety | new |  | 3 |  |  |  | 1 | This means moving with unsteady, shaky steps, feeling one's legs give way easily, and needing support to keep from stumbling or falling. |
| right-handed | new |  | 3 |  |  | [left-handed](../../../traits/instructions/left_handed.json) | 0 | This means favoring the right hand for writing, eating, throwing and most other everyday tasks, reaching for objects with it by habit rather than by thought. |
| scaly | new |  | 3 |  |  |  | 0 | This means having scaly, reptile-like or flaky skin on one's body. |
| sharp-cut | new |  | 3 |  |  |  | 1 | This means having a face and build with crisp, angular lines, sharp cheekbones and jaw, and little softness anywhere in one's frame. |
| sharp-sighted | new |  | 3 |  |  | [nearsighted](../../../traits/instructions/nearsighted.json), [blind](../../../traits/instructions/blind.json) | 1 | This means having keen eyesight. |
| shuffling | new |  | 3 |  |  |  | 1 | This means moving about slowly on short, dragging steps, with the feet barely lifting off the ground and the body carried low and unhurried. |
| sighted | new |  | 3 |  |  | [blind](../../../traits/instructions/blind.json), [nearsighted](../../../traits/instructions/nearsighted.json) | 0 | This means having working eyesight and not being blind. |
| single-eyed | new |  | 3 |  |  |  | 1 | This means having only one working eye. |
| smallish | new |  | 3 |  |  |  | 3 | This means being short and slight of build, with a light frame and a physical stature somewhat below the average for one's age and sex. |
| specimen | new |  | 3 |  |  |  | 2 | This means being physically imposing, with a strong, finely built body that commands notice in any room and is carried with obvious pride. |
| spotty | new |  | 3 |  |  |  | 0 | This means having spots or blemishes on one's skin. |
| squeaky | new |  | 3 |  |  |  | 0 | This means speaking in a high, thin, squeaky voice that carries a shrill, reedy quality through every sentence one says. |
| stained | new |  | 3 |  |  |  | 1 | This means carrying visible spots, smears or discoloration on one's clothes, skin or body, marks that stay on display whatever one does about them. |
| sterile | new |  | 3 |  |  |  | 1 | This means being unable to have children, infertile. |
| striking | new |  | 3 |  |  |  | 1 | This means having a look that draws the eye at once and holds attention in any room, the kind of appearance people remember long after meeting one. |
| supple | new |  | 3 |  |  |  | 2 | This means moving with a loose, limber body that bends and stretches easily, so that one's frame stays flexible and fluid in every motion. |
| sure-footed | new |  | 3 |  |  | [mobility impaired](../../../traits/instructions/mobility_impaired.json) | 1 | This means moving over uneven, slick, or steep ground with a steady, balanced stride, rarely stumbling or slipping, and keeping one's footing without having to think about it. |
| uncut | new |  | 3 |  |  |  | 1 | This means being uncircumcised in body. |
| unsightly | new |  | 3 |  |  |  | 1 | This means being unattractive in appearance across one's whole life, with features that most people would judge ugly and displeasing to look upon. |
| vast | new |  | 3 |  |  |  | 3 | This means being physically very large, taking up a great deal of space with one's huge frame and bulk. |
| voiceless | new |  | 3 |  |  |  | 0 | This means being unable to speak at all, so that every message one conveys must come through gesture, writing, or other silent means. |
| weak-handed | new |  | 3 |  |  |  | 1 | This means having hands that lack strength, so that one's grip is poor and one cannot hold, lift or squeeze with much force. |
| wind-swift | new |  | 3 |  |  | [mobility impaired](../../../traits/instructions/mobility_impaired.json) | 2 | This means moving and running at great speed as a standing habit, covering ground quickly and never dawdling in any task or journey. |
| yellowish | new |  | 3 |  |  |  | 0 | This means having a sallow, jaundiced complexion, with the skin carrying a dull yellow cast. |

## Covered, flagged (16 rows)

Decision 12: Sonnet read the pair one below the cut-off and Opus at or above it, so the candidate is covered by that trait and flagged for review (Roger sided with Opus on 45 of 58 such pairs in the pilot).

- **buff** (`buff#1`, cut-off 3) by [muscular](../../../traits/instructions/muscular.json): Sonnet 2 ("Both concern a muscular body, but buff adds regular training and pride in fitness, while muscular is just the physical build, which can be natural or come from labor."), Opus 3 ("Buff entails being muscular but narrows it to muscle kept up by deliberate training and worn with pride, whereas muscular covers any heavy build whatever its source.")
  Gloss: This means keeping one's body muscular and physically fit through regular training, and taking pride in its strength and conditioning as a visible part of who one is.
- **colossal** (`colossal#1`, cut-off 3) by [tall](../../../traits/instructions/tall.json): Sonnet 2 ("Both concern large physical size, but colossal means enormous overall bulk while tall is only height; neither implies the other."), Opus 3 ("Colossal implies towering height but carries it much further and adds sheer bulk, while tall is only being above average in height.")
  Gloss: This means being physically enormous in body and size, towering over everything around one and filling whatever space one occupies with sheer bulk.
- **decrepit** (`decrepit#1`, cut-off 3) by [elderly](../../../traits/instructions/elderly.json): Sonnet 2 ("Both concern old age, but decrepit is about physical frailty and worn-out strength while elderly is about being of advanced age; one can be elderly yet robust, or frail without being very old, so each adds something the other lacks."), Opus 3 ("Decrepit is old age carried further, into marked physical frailty, so it implies being elderly, while elderly does not imply decrepitude.")
  Gloss: This means being physically frail and feeble from old age, with one's strength and stamina worn down by the years.
- **eyeless** (`eyeless#1`, cut-off 3) by [blind](../../../traits/instructions/blind.json): Sonnet 2 ("Both concern being unable to see, but eyeless is the literal absence of eyes, while blind is a lack of sight from any cause (with an emphasis on little or nothing); blind people usually have eyes and eyeless implies blindness, so they overlap with different emphasis."), Opus 3 ("Having no eyes entails being unable to see, so eyeless is a narrower, anatomical case of blindness, while blind covers any loss of sight and the life adapted to it.")
  Gloss: This means having no eyes at all, so seeing is not possible.
- **hunk** (`hunk#1`, cut-off 3) by [muscular](../../../traits/instructions/muscular.json): Sonnet 2 ("Both involve a muscular build, but 'hunk' adds attractiveness and manly appeal, while 'muscular' is only about having a lot of muscle, so each has something the other lacks."), Opus 3 ("Being a hunk implies being muscular, adding attractiveness and manly appeal, so it is largely the same physical concept with a broader scope.")
  Gloss: This means having an attractive, muscular, virile physique and a manly presence that others find appealing.
- **hunks** (`hunks#1`, cut-off 3) by [muscular](../../../traits/instructions/muscular.json): Sonnet 2 ("Hunks combines attractiveness with a muscular build, while muscular covers only the physique and not attractiveness; each can occur without the other, so they share a core but neither implies the other."), Opus 3 ("A hunk is essentially a muscular man who is also considered attractive, so hunk entails muscular and narrows it by adding sex appeal and maleness.")
  Gloss: This means being attractive, muscular men, in the casual slang sense of the plural.
- **hunky** (`hunky#1`, cut-off 3) by [muscular](../../../traits/instructions/muscular.json): Sonnet 2 ("Both involve a muscular build, but hunky adds attractiveness and pride in one's body, while muscular is purely about physique and can apply without either."), Opus 3 ("Hunky is a muscular build plus attractiveness and pride in one's body, so it is muscularity with added emphasis on appeal.")
  Gloss: This means having a muscular, well-built physique that others find attractive, and taking pride in how one's body looks and moves.
- **luscious** (`luscious#1`, cut-off 3) by [good-looking](../../../traits/instructions/good_looking.json): Sonnet 2 ("Both involve a physically attractive appearance that draws admiration, but luscious stresses sensual allure and how one carries oneself, while good-looking is about conventionally handsome features and being complimented on them."), Opus 3 ("Both describe head-turning physical attractiveness; luscious adds a sensual emphasis to the same core of being good-looking.")
  Gloss: This means carrying oneself with a sensual, eye-catching allure, presenting a physically appealing look that draws attention and admiration from others.
- **milky** (`milky#1`, cut-off 3) by [fair-skinned](../../../traits/instructions/fair_skinned.json): Sonnet 2 ("Both describe pale skin, but 'milky' stresses a washed-out, opaque whitish look, while 'fair-skinned' covers pale skin generally and adds sun sensitivity; neither implies the other."), Opus 3 ("Both describe pale skin, but milky stresses a washed-out, opaque whitish look while fair-skinned stresses light skin that burns and reddens easily, so they share a core without being identical.")
  Gloss: This means having a pale, whitish complexion, with skin that looks washed out and faintly opaque rather than ruddy or tanned.
- **minute** (`minute#1`, cut-off 3) by [short](../../../traits/instructions/short.json): Sonnet 2 ("Both are about small physical stature, but 'minute' means tiny overall body size taking up little room, while 'short' means lacking height relative to others; each adds something the other lacks."), Opus 3 ("Both describe small physical stature: short is specifically low height, while minute is tiny overall body size, a broader and more extreme version that largely entails shortness.")
  Gloss: This means being physically tiny, with a body very small in size that takes up little room in any setting, all the time.
- **robust** (`robust#1`, cut-off 3) by [healthy](../../../traits/instructions/healthy.json): Sonnet 2 ("Both concern a sound, resilient body, but robust adds physical strength and endurance under exertion while healthy emphasizes freedom from illness, so each has something the other lacks."), Opus 3 ("Robust includes being healthy and resistant to illness, and adds physical strength and endurance, so healthy is the narrower health-only part of the same concept.")
  Gloss: This means being physically strong and healthy, with a body that holds up well under exertion, illness, and the ordinary wear of daily life.
- **rounder** (`rounder#1`, cut-off 3) by [fat](../../../traits/instructions/fat.json): Sonnet 2 ("Both describe a fuller body build, but 'rounder' is about round shape and figure while 'fat' is about carrying a lot of body fat, which is more extreme and about size rather than shape."), Opus 3 ("Both describe a fuller body, but rounder is about overall shape while fat is about a large amount of body fat, so fat is a stronger degree of the same idea.")
  Gloss: This means having a body that is more round in shape and figure.
- **shrimp** (`shrimp#1`, cut-off 3) by [short](../../../traits/instructions/short.json): Sonnet 2 ("Both concern small physical stature, but 'shrimp' stresses a slight, narrow build and being overlooked, while 'short' is specifically low height; neither implies the other."), Opus 3 ("Both describe a small physical stature that goes unnoticed in a crowd; shrimp adds a slight build on top of shortness, so the difference is mainly scope.")
  Gloss: This means being a small, slight build, someone who takes up little room and is easily overlooked in a crowd.
- **small** (`small#1`, cut-off 3) by [short](../../../traits/instructions/short.json): Sonnet 2 ("Both describe a physically small person, but 'small' includes slight build and frame while 'short' is only about low height, so each adds something the other lacks."), Opus 3 ("Small covers being short and also slight of frame, while short covers only height, so short is a narrower part of the same physical-size concept.")
  Gloss: This means being short and slight of build, with a small frame and little height, in a physical body that takes up less room than most.
- **squeezable** (`squeezable#1`, cut-off 3) by [fat](../../../traits/instructions/fat.json): Sonnet 2 ("Both describe a heavier body, but squeezable stresses a soft, plump, cuddly build that invites hugging, while fat stresses a large amount of body fat and its practical effects; neither implies the other."), Opus 3 ("Both describe carrying extra body fat; squeezable is a milder, affectionate version stressing soft cuddliness, while fat is the fuller degree with practical consequences.")
  Gloss: This means being soft and plump of body, round and cuddly in build, with a frame that invites pinching and hugging.
- **strapping** (`strapping#1`, cut-off 3) by [tall](../../../traits/instructions/tall.json): Sonnet 2 ("Both concern a large body, but strapping combines height with a solid, strong build, while tall is only about height; a person can be either without the other."), Opus 3 ("Strapping includes being tall but adds a heavy, strong build, so tall covers only part of what strapping means.")
  Gloss: This means having a big, tall, strongly built body, large-framed and solid from head to foot.

## Covered by a seed-queue entry (0 rows)

The seed queue's live entries were in the search beside the corpus traits (a word promoted from an earlier review, not yet a trait file): these rows were covered by one through the overlap walk, under the same rule as a corpus trait.  Exact-label matches with a queue entry are in the table above.


## Both ends similar (orthogonal to the pair?) (0 rows)

Decision 13 (Roger's rule): the relation call marked both members of a recorded pair (every corner of a triangle or simplex) similar, so the candidate is probably orthogonal to the pair's axis: neither member was judged or may cover it.  Cosines to the candidate; overlap readings where any are on record.


## Review queue (0 grey rows)

Kept with a flag the rule set treats as grey (rule set 2: `unparsed` only; rule set 1 also the Opus check's flag and the pair flag).  The covered-and-flagged rows and the both-ends-similar rows above are in the review queue as well.

## Pair completions (16 candidates)

A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): the candidate may be that trait's missing antonym (design item 4: a find, not a drop).

- brunet (covered): [blond](../../../traits/instructions/blond.json), [gray-haired](../../../traits/instructions/gray_haired.json)
- hunk (covered): [androgynous](../../../traits/instructions/androgynous.json)
- ambidextrous (new): [left-handed](../../../traits/instructions/left_handed.json)
- double-handed (new): [left-handed](../../../traits/instructions/left_handed.json)
- fleet (new): [mobility impaired](../../../traits/instructions/mobility_impaired.json)
- get-up-able (new): [mobility impaired](../../../traits/instructions/mobility_impaired.json)
- hearing (new): [deaf](../../../traits/instructions/deaf.json)
- hopping (new): [mobility impaired](../../../traits/instructions/mobility_impaired.json)
- lightening (new): [black-haired](../../../traits/instructions/black_haired.json)
- long-sighted (new): [nearsighted](../../../traits/instructions/nearsighted.json)
- mobile (new): [mobility impaired](../../../traits/instructions/mobility_impaired.json)
- right-handed (new): [left-handed](../../../traits/instructions/left_handed.json)
- sharp-sighted (new): [nearsighted](../../../traits/instructions/nearsighted.json), [blind](../../../traits/instructions/blind.json)
- sighted (new): [blind](../../../traits/instructions/blind.json), [nearsighted](../../../traits/instructions/nearsighted.json)
- sure-footed (new): [mobility impaired](../../../traits/instructions/mobility_impaired.json)
- wind-swift (new): [mobility impaired](../../../traits/instructions/mobility_impaired.json)
