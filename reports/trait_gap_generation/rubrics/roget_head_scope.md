# The Roget head-scope call

| | |
|---|---|
| **Status** | Draft 2 (2026-10-08), pinned as version 2 in [versions.json](./versions.json); draft 1 was version 1. |
| **What the model is shown** | About 20 heads of Roget's Thesaurus per call, in text order: each head's id (its number), title, class and section titles, and its adjectives in Roget's order (the first 20 distinct ones). |
| **What it returns** | For each head a reason, then `character`: 2, 1 or 0. |
| **What it is tuned on** | Not tuned on labelled heads.  Draft 2 replaced draft 1 after one run: draft 1 rated 289 of 586 heads 0, 123 of them heads the corpus already covers or partly covers.  Both are checked against the Roget pilot's trait-hood outcomes in [head_scope_readout.md](../../../data/candidates/roget/head_scope_readout.md). |
| **Model** | Haiku 5.5 (`claude-haiku-5-5`; no temperature: it refuses one).  Sent uncached (about 480 tokens, under Haiku 5.5's 512-token minimum; the code caches it if a later draft grows past the minimum). |

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent
to the model exactly as written.  Leave the fence lines themselves alone.  Notes for me go under
"Your notes", outside the block.

**What it is for.**  The Roget generator ([coding_plan_02_roget_wordnet.md](../coding_plan_02_roget_wordnet.md))
harvests words from the "dispositional" heads, Classes IV-VI of the thesaurus (a **head** is one numbered
entry, such as 604 Resolution).  Those classes also hold heads that are not about character at all:
Dearness, Cheapness, Debt and Purchase in the section Possessive relations, Misnomer and Correspondence
in Means of communicating ideas, Jewelry in Personal affections.  In the pilot, 32 of the 33 words the
trait-hood filter (M1) turned away came from such heads.  Whole sections cannot be dropped, because
Possessive relations also holds Liberality, Economy, Parsimony and Prodigality.  So this call rates each
head once, and the harvest skips the heads rated 0; the coverage map reports them apart as "not
character" ([QUESTIONS.md](../QUESTIONS.md) entry 44, approved by Roger on 2026-10-08).  The
code is [head_scope.py](../../../assistant_axis/gapgen/generators/roget/head_scope.py); the command is
`roget_generate.py head-scope` ([roget_generate.py](../../../data_analysis/gap_generation/roget_generate.py));
the ratings are in [head_scope.json](../../../data/candidates/roget/head_scope.json).

## The prompt

````text
Each item below is one head of Roget's Thesaurus (1911): a numbered entry, given with its id (its number in the thesaurus), its title, the class and section of the thesaurus it belongs to, and its adjectives in Roget's order (at most 20). We are looking for the heads whose adjectives can describe what a person is like.

For each head, say how many of its adjectives can describe what sort of person someone is, as in "she is a ___ person". That includes character and temperament; habits of thought, speech and conduct; attitudes and values; skills and failings shown in how a person acts; moods and feelings a person can be prone to; and the groups a person belongs to, such as an origin, a faith, a class or a way of life.

- 2: most of them can.
- 1: some can and some cannot; the head is mixed.
- 0: few or none can. They describe things, prices, quantities, documents, places or events, or a person's looks or passing circumstances (in custody, on duty, behind in payments) rather than the person.

Judge the adjectives, not the title or the section: a title may name a thing while its adjectives describe people, or a quality while its adjectives describe things. Read each adjective in the sense it has in its head; a word that describes people only in another of its senses does not count. Count an adjective only in an ordinary use about a person, not by a stretch. When you are unsure between 0 and 1, answer 1.

For each head give a reason in one short sentence, then the rating.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": "<the head's id, as given>", "reason": "<one short sentence>", "character": 0|1|2}]}
Return one row per head, in the order given.
````

## Rendered sample

Built from the code before the first pin, as AGENT_NOTES asks ("Read the rendered prompt, not the template"), with `roget_generate.py head-scope --render 814,592,837`, which prints the calls holding those heads exactly as they are sent.  The system turn is the block above, sent as written and uncached: at about 480 tokens (1,476 characters) it is under Haiku 5.5's 512-token caching minimum.  The user turn is one JSON object, one head per line.  The heads go in text order, about 20 a call (586 heads with adjectives make 30 calls of 19 or 20); a head with no adjectives is not sent.  Three of the 30 calls follow, chosen for the three variants the payload has: a sparse head, a head with many adjectives, and Class VI feeling heads.

**Call 12**, Means of communicating ideas into Volition in general: holds the sparse head 592 Correspondence (one adjective, *epistolary*), heads about kinds of text (590 Writing, 591 Printing, 597 Poetry) beside heads about speaking manner (584 Loquacity, 585 Taciturnity), and the first heads of Class V.  (Heads 581-603.)

```
{"heads": [
 {"id": "581", "title": "Aphony", "class": "Words relating to the intellectual faculties", "section": "Means of communicating ideas", "adjectives": ["dumb", "mute", "deafmute", "deaf and dumb", "mum", "tongue-tied", "breathless", "tongueless", "voiceless", "speechless", "wordless", "mute as a fish", "mute as a mackerel", "muzzled", "inarticulate", "inaudible", "croaking", "raucous", "hoarse", "husky"]},
 {"id": "582", "title": "Speech", "class": "Words relating to the intellectual faculties", "section": "Means of communicating ideas", "adjectives": ["speaking", "spoken", "oral", "lingual", "phonetic", "not written", "unwritten", "outspoken", "eloquent", "elocutionary", "oratorical", "rhetorical", "declamatory", "Ciceronian", "nuncupative", "Tullian"]},
 {"id": "583", "title": "Stammering", "class": "Words relating to the intellectual faculties", "section": "Means of communicating ideas", "adjectives": ["stammering", "inarticulate", "guttural", "nasal", "tremulous", "affected"]},
 {"id": "584", "title": "Loquacity", "class": "Words relating to the intellectual faculties", "section": "Means of communicating ideas", "adjectives": ["loquacious", "talkative", "garrulous", "chattering", "open-mouthed", "fluent", "voluble", "glib", "flippant", "long tongued"]},
 {"id": "585", "title": "Taciturnity", "class": "Words relating to the intellectual faculties", "section": "Means of communicating ideas", "adjectives": ["silent", "mute", "mum", "silent as a post", "silent as a stone", "taciturn", "sparing of words", "closetongued", "curt", "reserved"]},
 {"id": "588", "title": "Conversation", "class": "Words relating to the intellectual faculties", "section": "Means of communicating ideas", "adjectives": ["conversing", "interlocutory", "conversational", "discursive", "colloquial"]},
 {"id": "589", "title": "Soliloquy", "class": "Words relating to the intellectual faculties", "section": "Means of communicating ideas", "adjectives": ["soliloquizing"]},
 {"id": "590", "title": "Writing", "class": "Words relating to the intellectual faculties", "section": "Means of communicating ideas", "adjectives": ["writing", "written", "in writing", "in black and white", "under one's hand", "uncial", "Runic", "cuneiform"]},
 {"id": "591", "title": "Printing", "class": "Words relating to the intellectual faculties", "section": "Means of communicating ideas", "adjectives": ["printed", "in type", "typographical", "solid in galleys"]},
 {"id": "592", "title": "Correspondence", "class": "Words relating to the intellectual faculties", "section": "Means of communicating ideas", "adjectives": ["epistolary"]},
 {"id": "594", "title": "Description", "class": "Words relating to the intellectual faculties", "section": "Means of communicating ideas", "adjectives": ["descriptive", "graphic", "narrative", "epic", "suggestive", "well-drawn", "historic", "traditional", "traditionary", "legendary", "storied", "described"]},
 {"id": "595", "title": "Dissertation", "class": "Words relating to the intellectual faculties", "section": "Means of communicating ideas", "adjectives": ["discursive", "expository"]},
 {"id": "596", "title": "Compendium", "class": "Words relating to the intellectual faculties", "section": "Means of communicating ideas", "adjectives": ["compendious", "synoptic", "abridged"]},
 {"id": "597", "title": "Poetry", "class": "Words relating to the intellectual faculties", "section": "Means of communicating ideas", "adjectives": ["poetic", "poetical", "lyric", "lyrical", "tuneful", "epic", "dithyrambic", "metrical", "elegiac", "iambic", "trochaic", "amoebaeic", "Melibean", "Ionic", "Sapphic", "Pindaric"]},
 {"id": "598", "title": "Prose", "class": "Words relating to the intellectual faculties", "section": "Means of communicating ideas", "adjectives": ["prosy", "prosaic", "unpoetic", "unrhymed", "in prose", "not in verse"]},
 {"id": "599", "title": "The Drama", "class": "Words relating to the intellectual faculties", "section": "Means of communicating ideas", "adjectives": ["dramatic", "theatric", "theatrical", "scenic", "histrionic", "comic", "tragic", "farcical", "tragicomic", "melodramatic", "operatic", "stagy"]},
 {"id": "600", "title": "Will", "class": "Words relating to the voluntary powers", "section": "Volition in general", "adjectives": ["voluntary", "volitional", "willful", "optional", "discretional", "discretionary", "autocratic", "spontaneous", "unconstrained"]},
 {"id": "601", "title": "Necessity", "class": "Words relating to the voluntary powers", "section": "Volition in general", "adjectives": ["necessary", "fated", "destined", "elect", "uncontrollable", "inevitable", "unavoidable", "irresistible", "irrevocable", "inexorable", "resistless", "involuntary", "instinctive", "automatic", "blind", "mechanical", "unconscious", "unwitting", "unthinking"]},
 {"id": "602", "title": "Willingness", "class": "Words relating to the voluntary powers", "section": "Volition in general", "adjectives": ["willing", "minded", "fain", "disposed", "inclined", "favorable", "favorably-minded", "favorably inclined", "favorably disposed", "nothing loth", "in the vein", "in the mood", "in the humor", "in the mind", "ready", "forward", "earnest", "eager", "predisposed", "docile"]},
 {"id": "603", "title": "Unwillingness", "class": "Words relating to the voluntary powers", "section": "Volition in general", "adjectives": ["unwilling", "not in the vein", "loth", "loath", "shy of", "disinclined", "indisposed", "averse", "reluctant", "not content", "laggard", "backward", "remiss", "slack", "slow to", "scrupulous", "restive", "demurring"]}
 ]}
```

**Call 22**, Possessive relations into Affections in general: the price heads (812 Price, 814 Dearness, 815 Cheapness, with 20 adjectives each where Roget has more) beside the character heads of the same section (816 Liberality, 817 Economy, 817a Greed, 818 Prodigality, 819 Parsimony).  Cheapness shows why the rubric asks for the head's sense: *reasonable*, *moderate* and *low* describe people only in another sense.  (Heads 811-826.)

```
{"heads": [
 {"id": "811", "title": "Accounts", "class": "Words relating to the voluntary powers", "section": "Possessive relations", "adjectives": ["accountable", "accounting"]},
 {"id": "812", "title": "Price", "class": "Words relating to the voluntary powers", "section": "Possessive relations", "adjectives": ["priced", "to the tune of", "ad valorem", "dutiable", "mercenary", "venal"]},
 {"id": "812a", "title": "Value", "class": "Words relating to the voluntary powers", "section": "Possessive relations", "adjectives": ["valuable", "estimable", "worthwhile", "worthy", "full of worth"]},
 {"id": "812b", "title": "Worthlessness", "class": "Words relating to the voluntary powers", "section": "Possessive relations", "adjectives": ["worthless", "valueless", "useless", "cheap", "shoddy", "slapdash"]},
 {"id": "813", "title": "Discount", "class": "Words relating to the voluntary powers", "section": "Possessive relations", "adjectives": ["discounting"]},
 {"id": "814", "title": "Dearness", "class": "Words relating to the voluntary powers", "section": "Possessive relations", "adjectives": ["dear", "high", "high priced", "of great price", "expensive", "costly", "precious", "dear bought", "at a premium", "not to be had", "beyond price", "above price", "priceless", "of priceless value", "unreasonable", "extravagant", "exorbitant", "extortionate", "overpriced", "more than it's woth"]},
 {"id": "815", "title": "Cheapness", "class": "Words relating to the voluntary powers", "section": "Possessive relations", "adjectives": ["cheap", "low", "low priced", "moderate", "reasonable", "inexpensive", "well worth the money", "worth the money", "good at the price", "cheap at the price", "dirt cheap", "dog cheap", "cheap as dirt", "cheap and nasty", "catchpenny", "half-price", "depreciated", "unsalable", "gratuitous", "gratis"]},
 {"id": "816", "title": "Liberality", "class": "Words relating to the voluntary powers", "section": "Possessive relations", "adjectives": ["liberal", "free", "generous", "hospitable", "bountiful", "bounteous", "handsome", "unsparing", "ungrudging", "unselfish", "open handed", "free handed", "full handed", "open hearted", "large hearted", "free hearted", "munificent", "princely", "overpaid"]},
 {"id": "817", "title": "Economy", "class": "Words relating to the voluntary powers", "section": "Possessive relations", "adjectives": ["economical", "frugal", "careful", "thrifty", "saving", "chary", "spare", "sparing", "underpaid"]},
 {"id": "817a", "title": "Greed", "class": "Words relating to the voluntary powers", "section": "Possessive relations", "adjectives": ["greedy", "avaricious", "covetous", "acquisitive", "grasping", "rapacious", "greedy as a hog", "overeager", "voracious", "ravenous", "ravenous as a wolf", "openmouthed", "extortionate", "exacting", "insatiable", "insatiate", "unquenchable", "quenchless", "omnivorous"]},
 {"id": "818", "title": "Prodigality", "class": "Words relating to the voluntary powers", "section": "Possessive relations", "adjectives": ["prodigal", "profuse", "thriftless", "unthrifty", "improvident", "wasteful", "extravagant", "lavish", "dissipated", "overliberal"]},
 {"id": "819", "title": "Parsimony", "class": "Words relating to the voluntary powers", "section": "Possessive relations", "adjectives": ["parsimonious", "penurious", "stingy", "miserly", "mean", "shabby", "peddling", "scrubby", "penny wise", "near", "niggardly", "close", "fast handed", "close handed", "strait handed", "close fisted", "hard fisted", "tight fisted", "tight", "sparing"]},
 {"id": "820", "title": "Affections", "class": "Words relating to the sentient and moral powers", "section": "Affections in general", "adjectives": ["affected", "characterized", "formed", "molded", "cast", "tempered", "framed", "predisposed", "prone", "inclined", "having a bias", "tinctured with", "imbued with", "penetrated with", "eaten up with", "inborn", "inbred", "ingrained", "deep-rooted", "ineffaceable"]},
 {"id": "821", "title": "Feeling", "class": "Words relating to the sentient and moral powers", "section": "Affections in general", "adjectives": ["feeling", "sentient", "sensuous", "sensorial", "sensory", "emotive", "emotional", "of feeling", "with feeling warm", "quick", "lively", "smart", "strong", "sharp", "acute", "cutting", "piercing", "incisive", "keen", "keen as a razor"]},
 {"id": "822", "title": "Sensibility", "class": "Words relating to the sentient and moral powers", "section": "Affections in general", "adjectives": ["sensible", "sensitive", "impressible", "impressionable", "susceptive", "susceptible", "alive to", "gushing", "warm hearted", "tender hearted", "soft hearted", "tender as a chicken", "soft", "sentimental", "romantic", "enthusiastic", "spirited", "mettlesome", "vivacious", "lively"]},
 {"id": "823", "title": "Insensibility", "class": "Words relating to the sentient and moral powers", "section": "Affections in general", "adjectives": ["insensible", "unconscious", "impassive", "impassible", "blind to", "deaf to", "dead to", "unsusceptible", "insusceptible", "passionless", "spiritless", "heartless", "soulless", "unfeeling", "unmoral", "apathetic", "phlegmatic", "dull", "frigid", "cold blooded"]},
 {"id": "824", "title": "Excitation", "class": "Words relating to the sentient and moral powers", "section": "Affections in general", "adjectives": ["excited", "wrought up", "astir", "sparkling", "in a fever", "in a ferment", "in a blaze", "in hysterics", "black in the face", "overwrought", "tense", "taught", "on a razor's edge", "hot", "red-hot", "flushed", "feverish", "all of a twitter", "in a pucker", "with quivering lips"]},
 {"id": "825", "title": "Excitability", "class": "Words relating to the sentient and moral powers", "section": "Affections in general", "adjectives": ["excitable", "easily excited", "in an excitable state", "high-strung", "impatient", "intolerant", "feverish", "febrile", "hysterical", "delirious", "mad", "moody", "maggoty-headed", "unquiet", "mercurial", "electric", "galvanic", "hasty", "hurried", "restless"]},
 {"id": "826", "title": "Inexcitability", "class": "Words relating to the sentient and moral powers", "section": "Affections in general", "adjectives": ["unexcitable", "imperturbable", "dispassionate", "cold-blooded", "irritable", "enduring", "stoical", "Platonic", "philosophic", "staid", "stayed", "sober", "sober minded", "grave", "sober as a judge", "grave as a judge", "sedate", "demure", "cool-headed", "easy-going"]}
 ]}
```

**Call 23**, Personal affections, the feeling heads of Class VI: 837 Dejection (107 adjectives, the first 20 shown), the states of 827 Pleasure and 828 Pain, and the looks of 845 Beauty and 846 Ugliness.  (Heads 827-846.)

```
{"heads": [
 {"id": "827", "title": "Pleasure", "class": "Words relating to the sentient and moral powers", "section": "Personal affections", "adjectives": ["not sorry", "glad", "gladsome", "pleased as Punch", "happy", "blest", "blessed", "blissful", "beatified", "happy as a clam", "happy as a king", "thrice happy", "enjoying", "in a blissful state", "in raptures", "in ecstasies", "at ease", "overjoyed", "entranced", "enchanted"]},
 {"id": "828", "title": "Pain", "class": "Words relating to the sentient and moral powers", "section": "Personal affections", "adjectives": ["in pain", "full of pain", "suffering", "pained", "afflicted", "worried", "aching", "griped", "on the rack", "in limbo", "between hawk and buzzard", "uncomfortable", "uneasy", "ill at ease", "in a taking", "in a way", "disturbed", "heavy laden", "stricken", "crushed"]},
 {"id": "829", "title": "Pleasurableness", "class": "Words relating to the sentient and moral powers", "section": "Personal affections", "adjectives": ["causing pleasure", "pleasure-giving", "pleasing", "pleasant", "pleasurable", "agreeable", "grateful", "gratifying", "lief", "acceptable", "welcome", "welcomed", "favorite", "to one's taste", "to one's mind", "to one's liking", "refreshing", "comfortable", "cordial", "genial"]},
 {"id": "830", "title": "Painfulness", "class": "Words relating to the sentient and moral powers", "section": "Personal affections", "adjectives": ["causing pain", "hurting", "painful", "dolorous", "unpleasant", "unpleasing", "displeasing", "disagreeable", "unpalatable", "bitter", "distasteful", "uninviting", "unwelcome", "undesirable", "undesired", "obnoxious", "unacceptable", "unpopular", "thankless", "unsatisfactory"]},
 {"id": "831", "title": "Content", "class": "Words relating to the sentient and moral powers", "section": "Personal affections", "adjectives": ["content", "contented", "satisfied", "at ease", "at one's ease", "at home", "easygoing", "not particular", "conciliatory", "of good comfort", "unafflicted", "unmolested", "at rest", "snug", "comfortable", "in one's element", "satisfactory", "tolerable", "good enough", "OK"]},
 {"id": "832", "title": "Discontent", "class": "Words relating to the sentient and moral powers", "section": "Personal affections", "adjectives": ["discontented", "dissatisfied", "unsatisfied", "ungratified", "dissident", "malcontent", "malcontented", "exigent", "exacting", "hypercritical", "repining", "in high dudgeon", "in a fume", "in the sulks", "in the dumps", "in bad humor", "glum", "sulky", "sour as a crab", "soured"]},
 {"id": "833", "title": "Regret", "class": "Words relating to the sentient and moral powers", "section": "Personal affections", "adjectives": ["regretting", "regretful", "homesick", "regretted", "much to be regretted", "regrettable"]},
 {"id": "834", "title": "Relief", "class": "Words relating to the sentient and moral powers", "section": "Personal affections", "adjectives": ["relieving", "consolatory", "soothing", "assuaging", "balmy", "balsamic", "lenitive", "palliative"]},
 {"id": "835", "title": "Aggravation", "class": "Words relating to the sentient and moral powers", "section": "Personal affections", "adjectives": ["aggravated", "worse", "unrelieved", "aggravating"]},
 {"id": "836", "title": "Cheerfulness", "class": "Words relating to the sentient and moral powers", "section": "Personal affections", "adjectives": ["cheerful", "cheery", "of good cheer", "smiling", "blithe", "in spirits", "in good spirits", "breezy", "bully", "chipper", "in high spirits", "in high feather", "happy as a king", "gay as a lark", "allegro", "debonair", "light", "lightsome", "light hearted", "buoyant"]},
 {"id": "837", "title": "Dejection", "class": "Words relating to the sentient and moral powers", "section": "Personal affections", "adjectives": ["cheerless", "joyless", "spiritless", "uncheerful", "melancholy", "dismal", "somber", "dark", "gloomy", "clouded", "murky", "lowering", "frowning", "lugubrious", "funereal", "mournful", "lamentable", "dreadful", "dreary", "flat"]},
 {"id": "838", "title": "Rejoicing", "class": "Words relating to the sentient and moral powers", "section": "Personal affections", "adjectives": ["rejoicing", "jubilant", "exultant", "triumphant", "flushed", "elated", "pleased", "delighted", "tickled pink"]},
 {"id": "839", "title": "Lamentation", "class": "Words relating to the sentient and moral powers", "section": "Personal affections", "adjectives": ["lamenting", "in mourning", "in sackcloth and ashes", "sorrowing", "mournful", "tearful", "lachrymose", "plaintive", "querulous", "in the melting mood", "in tears", "with moistened eyes", "with watery eyes", "bathed in tears", "dissolved in tears", "elegiac"]},
 {"id": "840", "title": "Amusement", "class": "Words relating to the sentient and moral powers", "section": "Personal affections", "adjectives": ["amusing", "entertaining", "diverting", "recreational", "recreative", "fun", "festive", "festal", "jovial", "jolly", "jocund", "roguish", "playful", "playful as a kitten", "sportive", "funny", "very funny", "hilarious", "uproarious", "side-splitting"]},
 {"id": "841", "title": "Weariness", "class": "Words relating to the sentient and moral powers", "section": "Personal affections", "adjectives": ["wearying", "wearing", "wearisome", "tiresome", "irksome", "uninteresting", "stupid", "bald", "devoid of interest", "dry", "monotonous", "dull", "arid", "tedious", "humdrum", "mortal", "flat", "prosy", "prosing", "slow"]},
 {"id": "842", "title": "Wit", "class": "Words relating to the sentient and moral powers", "section": "Personal affections", "adjectives": ["witty", "attic", "quick-witted", "nimble-witted", "smart", "jocular", "jocose", "humorous", "facetious", "waggish", "whimsical", "kidding", "joking", "puckish", "merry and wise", "pleasant", "sprightly", "light", "sparkling", "epigrammatic"]},
 {"id": "843", "title": "Dullness", "class": "Words relating to the sentient and moral powers", "section": "Personal affections", "adjectives": ["dull", "dull as ditch water", "unentertaining", "uninteresting", "flat", "dry as dust", "unfunny", "logy", "unimaginative", "prosy", "prosing", "prosaic", "matter of fact", "commonplace", "pedestrian", "pointless", "stupid", "slow", "insipid", "vapid"]},
 {"id": "845", "title": "Beauty", "class": "Words relating to the sentient and moral powers", "section": "Personal affections", "adjectives": ["beautiful", "beauteous", "handsome", "gorgeous", "pretty", "lovely", "graceful", "elegant", "prepossessing", "delicate", "dainty", "refined", "fair", "personable", "comely", "seemly", "bonny", "good-looking", "well-favored", "well-made"]},
 {"id": "846", "title": "Ugliness", "class": "Words relating to the sentient and moral powers", "section": "Personal affections", "adjectives": ["ugly", "ugly as sin", "ugly as a toad", "ugly as a scarecrow", "plain", "homely", "ordinary", "inartistic", "unsightly", "unseemly", "uncomely", "unlovely", "unshapely", "sightless", "unbeautiful", "semibeautiful", "misshapen", "monstrous", "ill-made", "ill-shaped"]}
 ]}
```

The user turns are the same under both drafts (only the system turn changed).

Read for fit (2026-10-08, draft 1; draft 2 was read the same way, `--render 698,188`).  The opening describes what is sent: an id that is the head's number (a string, since some heads are lettered, 812a, 817a), a title, the class and section titles, and at most 20 adjectives; the answer's `id` asks for the id as given, so no renumbering can slip in.  Three changes came from reading these calls, before the pin: (1) the price heads hold words that describe people in another sense (*reasonable*, *moderate*, *low* in Cheapness; *dear*, *precious* in Dearness), so the rubric now says to read each adjective in the sense it has in its head; (2) 845 Beauty and 846 Ugliness describe looks, which the 0 line did not name, so it now says "a person's looks or situation"; (3) head 830 reached the model as ". Painfulness", a parser artifact of the head line, so the payload strips a leading period from the title (`head_scope.display_title`).  Multiword entries ("of great price", "not in the vein") do not fit the frame "she is a ___ person" word for word; they are left in, as Roget gives them, since the frame illustrates the question rather than a test to apply.

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Opus | First draft, from the brief of 2026-10-08; before the pin, the head's-sense clause and "looks" in the 0 line, after reading the rendered calls | |
| 2 | Opus | "Character" spelled out as what a person is like: character and temperament, habits of thought, speech and conduct, attitudes and values, skills and failings shown in action, moods a person is prone to, and memberships (origin, faith, class, way of life); the 0 line says "passing circumstances" with three examples; "When you are unsure between 0 and 1, answer 1"; the separate feeling sentence folded into the list | Draft 1 read "character" narrowly: it rated 0 heads such as Skill, Cooperation, Duty, Rejoicing, Wealth and Marriage, 123 of the 289 it rated 0 being heads the corpus covers or partly covers.  Memberships count because the corpus counts them as traits (decisions_m1.md decision 3); the brief's 0 line named "a person's situation", and this narrows it to passing circumstances (QUESTIONS 44) |
