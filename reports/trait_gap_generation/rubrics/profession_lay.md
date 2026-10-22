# Generator B's lay-role call: what the people of an occupation group call themselves

| | |
|---|---|
| **Status** | **Draft 1 (2026-10-22, Opus), pinned as version 1**: the text of [coding_plan_16_role_generators.md](../coding_plan_16_role_generators.md) § 7a.5 with four small changes made while writing the code against the real O*NET data (the change log below says which and why).  Not run yet: its first run is `professions_generator.py lay` on wave 1's table (about 760 groups and titles, three readings each). |
| **What it is for** | Generator B, lists of professions ([16_role_generators.md](../16_role_generators.md) § 6): one call per SOC broad group (its detailed O*NET occupations with their descriptions) and one per selected O*NET job title (under its occupation), asking for the lay roles a person of the group would name themselves by.  The code is [lay.py](../../../assistant_axis/gapgen/generators/professions/lay.py); the command is [professions_generator.py](../../../data_analysis/gap_generation/professions_generator.py) `lay`. |
| **What the model is shown** | One JSON object as the user turn (`lay.build_user`): `"group"` with the group's `code` and `title` (and, for a job title, its `alternate_title`), then `"occupations"`, each with an `id` (1, 2, 3 ... in the order listed), its O*NET `title` and its O*NET `description`, one occupation a line.  The group's employment is not shown, so the answer does not depend on the ranking.  The rendered samples are below the prompt. |
| **What it returns** | A short reason, then `roles`: zero to three `{"role", "covers", "distinct_persona", "gloss"}` (zero only for a job title that is just another name for its occupation's role). |
| **Model** | Haiku 5.5 (`claude-haiku-5-5`), no temperature (it refuses one), `max_tokens` 3000 (it thinks adaptively, and the thinking counts against it), the system prompt cached.  A generating call: three readings a group, combined as the union of the roles by stem with each role's support (1-3) recorded, `distinct_persona` by majority of the readings that name the role, the gloss from the first reading that names it; a role named once is kept.  Agreement is reported, never a gate ([judging.md](../../../.claude/rules/judging.md), "Sampled outputs at T=1"). |

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent to the model
exactly as written, as the system prompt.  Leave the fence lines themselves alone.  A changed text is pinned with
[rubric_pins.py](../../../data_analysis/gap_generation/rubric_pins.py) (`bump profession_lay --why '...'`) before a paid run will use
it (the `lay` command refuses a text that is not its latest pin).  Notes for me go under "Your notes", outside the
block.

## The prompt

````text
You are given one JSON object: a group of occupations from an official classification. "group" gives the group's code and title; "occupations" lists its occupations, each with an "id" (the occupations are numbered 1, 2, 3 ... in the order listed), a title and a description. Say what the people in this group call themselves: the plain word or short phrase a person says when asked what they are ("I'm a nurse", "I'm a cardiologist", "I'm an executive"), not the classification's title and not a job advertisement's. "Chief Sustainability Officers" are executives; "Nursing Assistants" are nurse's aides.

Give one to three lay roles for the group, each one to three words, lower case, singular, US spelling, no "the". Give one when the occupations are one role under several titles, more when the group holds roles that are different personas: people who would describe their days, their tools, their customers or their worries differently. A specialty whose holder talks about its own subject all day is a persona of its own (a cardiologist talks about hearts); a title that only names a level, a sector or a reporting line is not (a chief sustainability officer is an executive).

When "group" carries an "alternate_title", the call is about that title alone. It is a lay title from the classification's own list for the occupation shown. Say whether it names a persona of its own (a bouncer, beside a security guard) or is only another name for the occupation's role (a security officer is a security guard). Give it, in its lay form, as the one role when it names a persona of its own; when it does not, give no roles ("roles": []).

For each lay role, say which of the listed occupations it covers (their ids), whether it is a persona distinct from the group's most general role ("distinct_persona"), and write a one-sentence description in the form "A <role> is someone who ..." (write "An" before a vowel sound): what the persona does, where, with what and with whom, in the words the persona would use of itself, not the classification's, about 20 to 35 words, no hedging, US spelling.

Give a reason in one short sentence first, then the roles.

Respond with one JSON object and nothing else, reason first:
{"reason": "<one short sentence>", "roles": [{"role": "<one to three words>", "covers": [<ids of the listed occupations>], "distinct_persona": true|false, "gloss": "<one sentence>"}]}
````

## Rendered samples

The system turn is the block above, byte for byte.  The user turns below are `lay.build_user`'s output for the two
variants, rendered from the code on 2026-10-22 before the pin.  The occupations' titles and descriptions are O*NET
31.0's, verbatim from [occupation_data.csv](../../../data/external/onet/occupation_data.csv) (git-ignored, in the main
checkout).  Two parts were supplied by hand because their files are not downloaded yet: the broad group's title
"Physicians" (SOC 2018's title of 29-1210, which the OEWS file's broad row supplies at build time), and the job-title
row "Bouncer" under 33-9032.00 (it comes from [job_titles.csv](../../../data/external/onet/job_titles.csv), not there
yet).  The Physicians group shows all 19 O*NET occupations under 29-1210: SOC 2018's Physicians run from 29-1211 to
29-1229 (`soc.BROAD_SPILLOVER`), and the six `29-1229.0x` specialties are O*NET's own.

Variant 1, a SOC broad group (29-1210 Physicians; 19 O*NET occupations):

```text
{"group": {"code": "29-1210", "title": "Physicians"},
 "occupations": [
  {"id": 1, "title": "Anesthesiologists", "description": "Administer anesthetics and analgesics for pain management prior to, during, or after surgery."},
  {"id": 2, "title": "Cardiologists", "description": "Diagnose, treat, manage, and prevent diseases or conditions of the cardiovascular system. May further subspecialize in interventional procedures (e.g., balloon angioplasty and stent placement), echocardiography, or electrophysiology."},
  {"id": 3, "title": "Dermatologists", "description": "Diagnose and treat diseases relating to the skin, hair, and nails. May perform both medical and dermatological surgery functions."},
  {"id": 4, "title": "Emergency Medicine Physicians", "description": "Make immediate medical decisions and act to prevent death or further disability. Provide immediate recognition, evaluation, care, stabilization, and disposition of patients. May direct emergency medical staff in an emergency department."},
  {"id": 5, "title": "Family Medicine Physicians", "description": "Diagnose, treat, and provide preventive care to individuals and families across the lifespan. May refer patients to specialists when needed for further diagnosis or treatment."},
  {"id": 6, "title": "General Internal Medicine Physicians", "description": "Diagnose and provide nonsurgical treatment for a wide range of diseases and injuries of internal organ systems. Provide care mainly for adults and adolescents, and are based primarily in an outpatient care setting."},
  {"id": 7, "title": "Neurologists", "description": "Diagnose, manage, and treat disorders and diseases of the brain, spinal cord, and peripheral nerves, with a primarily nonsurgical focus."},
  {"id": 8, "title": "Obstetricians and Gynecologists", "description": "Provide medical care related to pregnancy or childbirth. Diagnose, treat, and help prevent diseases of women, particularly those affecting the reproductive system. May also provide general care to women. May perform both medical and gynecological surgery functions."},
  {"id": 9, "title": "Pediatricians, General", "description": "Diagnose, treat, and help prevent diseases and injuries in children. May refer patients to specialists for further diagnosis or treatment, as needed."},
  {"id": 10, "title": "Physicians, Pathologists", "description": "Diagnose diseases and conduct lab tests using organs, body tissues, and fluids. Includes medical examiners."},
  {"id": 11, "title": "Psychiatrists", "description": "Diagnose, treat, and help prevent mental disorders."},
  {"id": 12, "title": "Radiologists", "description": "Diagnose and treat diseases and injuries using medical imaging techniques, such as x rays, magnetic resonance imaging (MRI), nuclear medicine, and ultrasounds. May perform minimally invasive medical procedures and tests."},
  {"id": 13, "title": "Physicians, All Other", "description": "All physicians not listed separately."},
  {"id": 14, "title": "Allergists and Immunologists", "description": "Diagnose, treat, and help prevent allergic diseases and disease processes affecting the immune system."},
  {"id": 15, "title": "Hospitalists", "description": "Provide inpatient care predominantly in settings such as medical wards, acute care units, intensive care units, rehabilitation centers, or emergency rooms. Manage and coordinate patient care throughout treatment."},
  {"id": 16, "title": "Urologists", "description": "Diagnose, treat, and help prevent benign and malignant medical and surgical disorders of the genitourinary system and the renal glands."},
  {"id": 17, "title": "Physical Medicine and Rehabilitation Physicians", "description": "Diagnose and treat disorders requiring physiotherapy to provide physical, mental, and occupational rehabilitation."},
  {"id": 18, "title": "Preventive Medicine Physicians", "description": "Apply knowledge of general preventive medicine and public health issues to promote health care to groups or individuals, and aid in the prevention or reduction of risk of disease, injury, disability, or death. May practice population-based medicine or diagnose and treat patients in the context of clinical health promotion and disease prevention."},
  {"id": 19, "title": "Sports Medicine Physicians", "description": "Diagnose, treat, and help prevent injuries that occur during sporting events, athletic training, and physical activities."}
 ]}
```

An answer of the expected shape (one reading; the glosses shortened here): `{"reason": "All are doctors; a few
specialties are personas of their own.", "roles": [{"role": "doctor", "covers": [1, 2, ..., 19], "distinct_persona":
false, "gloss": "A doctor is someone who ..."}, {"role": "cardiologist", "covers": [2], "distinct_persona": true,
"gloss": "A cardiologist is someone who ..."}, {"role": "psychiatrist", "covers": [11], "distinct_persona": true,
"gloss": "A psychiatrist is someone who ..."}]}`.

Variant 2, a job title under its occupation (33-9032.00 Security Guards, alternate title "Bouncer"):

```text
{"group": {"code": "33-9032.00", "title": "Security Guards", "alternate_title": "Bouncer"},
 "occupations": [
  {"id": 1, "title": "Security Guards", "description": "Guard, patrol, or monitor premises to prevent theft, violence, or infractions of rules. May operate x-ray and metal detector equipment."}
 ]}
```

Expected: `{"reason": "A bouncer works a club door and is a persona of its own beside the guard.", "roles": [{"role":
"bouncer", "covers": [1], "distinct_persona": true, "gloss": "A bouncer is someone who ..."}]}`; for a title that is
only another name (a security officer), `{"reason": "...", "roles": []}`.

**Read for fit (2026-10-22).**  The ids, the alternate title and the one-occupation group read as the text describes
them.  One thing the rendering shows that the text leaves to the model: the Physicians group holds a dozen
specialties a person would name themselves by, and the call gives at most three roles, so the three readings' union
is what brings more than two of them in (and M3's sub-role rule, decision 4, covers a specialty by its parent at
overlap 3 when the parent is a corpus role).  Left as the plan has it.

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Opus | The plan's § 7a.5 text, with four changes: (1) the first paragraph says the occupations carry an `id` numbering them in the order listed (the plan's text named ids only in the answer format); (2) the alternate-title paragraph says the call is about that title alone and asks for `"roles": []` when the title is only another name, since the plan's "one to three roles" contradicted "give it as a role only when it does"; (3) "in its own words" became "in the words the persona would use of itself, not the classification's", the wording of the same rule in [role_gloss.md](./role_gloss.md), since "its own" could be read as the classification's; (4) "write "An" before a vowel sound", as [role_gloss.md](./role_gloss.md) has it | Read against the real O*NET groups while writing [lay.py](../../../assistant_axis/gapgen/generators/professions/lay.py) (the working-style rule "Read the rendered prompt, not the template") |
