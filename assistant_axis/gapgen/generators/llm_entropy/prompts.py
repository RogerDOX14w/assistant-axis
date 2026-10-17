"""The five prompt families: their tables, their user turns and the pinned system turns (plan sections 5 and
"Rendered prompts").

**System turns** are the pinned texts of ``reports/trait_gap_generation/rubrics/`` (the house pattern of
:mod:`assistant_axis.gapgen.split_rubrics`): :data:`SCAFFOLD_RUBRIC` for families a, b, d and e,
:data:`BACKTRANSLATE_RUBRIC` for the back-translation call, and :data:`MULTILINGUAL_RUBRIC`, the English master that
the ten family-c system turns are translated from (the translations live in ``multilingual_prompts.json`` with their
sha256, :func:`render_c` reads them).  :func:`load_rubric` refuses a text that is not its latest pin.

**User turns** are built here from the tables below.  Wording is data: any change to a table or a template must
bump :data:`PROMPTS_VERSION` and append the new :func:`wording_sha256` to :data:`PROMPT_HASHES` (append-only; a
test enforces it), as the base-model generator's prompts do.

**No corpus label appears in any prompt** (the families carry domains, persons, languages and spellings, never a
trait name), so the judge display form is a no-op here; records still carry ``label_form``.  Every example word and
every domain, mode and constraint word is checked against the corpus, the seed queue and the validation files
(:mod:`assistant_axis.gapgen.prompt_hygiene`; the prompt test).

**Grid sizes** (plan section 7, ``prompts``): (a) 30 domains x 7 modes = 210 cells; (b) 400 real and 200 fictional
seeds = 600; (c) 10 languages x 30 domains = 300; (e) 26 letters + 120 bigrams + 20 suffixes + 12 prefixes + 3 frames
= 181; (d) wraps (a) and (e).

**The bigram table** (:data:`BIGRAMS`) was derived once, on 2026-10-17, from Open English WordNet 2024 (``oewn:2024``,
the in-tree copy): every adjective lemma (parts of speech ``a`` and ``s``) that is a single word of at least three
lower-case ASCII letters (17,263 lemmas, 255 distinct initial bigrams), counted by its first two letters, the 120
commonest taken, ties broken alphabetically (``nu``, ``sw`` and ``up`` tie at 35 lemmas at the cut; ``nu`` is the
120th).  The plan's sample bigram ``sq`` (29 lemmas) is therefore not in the table; the rendered sample uses ``sc``.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen.paths import REPO_ROOT

FAMILIES: tuple[str, ...] = ("a", "b", "c", "d", "e")
#: The families a ``generate`` call makes (d's stage 1 is ``generate --with-probabilities`` on a or e; its stage 2 is
#: ``verbalized``).
GENERATE_FAMILIES: tuple[str, ...] = ("a", "b", "c", "e")
FAMILY_NAMES: dict[str, str] = {"a": "domain x mode", "b": "person seeding", "c": "multilingual",
                                "d": "verbalized sampling", "e": "spelling constraints"}

SCAFFOLD_RUBRIC = "llm_entropy_scaffold"
MULTILINGUAL_RUBRIC = "llm_entropy_multilingual"
BACKTRANSLATE_RUBRIC = "llm_entropy_backtranslate"
RUBRICS: tuple[str, ...] = (SCAFFOLD_RUBRIC, MULTILINGUAL_RUBRIC, BACKTRANSLATE_RUBRIC)

PROMPTS_VERSION = 1
#: Append-only: the :func:`wording_sha256` of every version's tables and templates.
PROMPT_HASHES: dict[int, str] = {
    1: "b6bc875e97514e43014ec9c96b78f8faf5af3194435e03c540239c99fe3205d4",
}

# --------------------------------------------------------------------------- (a) domains and modes

#: 30 life domains: ``(id, the phrase the prompt uses)``.  The workstream plan's twenty, then ten more spread over
#: other parts of a life (faith, the natural world, kin and friends, health, looks, renown, public affairs, error,
#: being praised).  Each id is the prompt-id part (``a:money:habit``).
DOMAINS: tuple[tuple[str, str], ...] = (
    ("money", "money"), ("authority", "authority"), ("strangers", "strangers"), ("risk", "risk"),
    ("rules", "rules"), ("death", "death"), ("animals", "animals"), ("work", "work"), ("knowledge", "knowledge"),
    ("body", "the body"), ("time", "time"), ("conflict", "conflict"), ("food", "food"), ("sex", "sex"),
    ("property", "property"), ("technology", "technology"), ("home", "home"), ("past", "the past"),
    ("language", "language"), ("luck", "luck"), ("religion", "religion"), ("nature", "nature"),
    ("family", "family"), ("friendship", "friendship"), ("illness", "illness"), ("beauty", "beauty"),
    ("fame", "fame"), ("politics", "politics"), ("mistakes", "mistakes"), ("praise", "praise"),
)
DOMAIN_IDS: tuple[str, ...] = tuple(d for d, _ in DOMAINS)
DOMAIN_PHRASE: dict[str, str] = dict(DOMAINS)


@dataclass(frozen=True)
class Mode:
    id: str          # the prompt-id part (a:money:habit)
    name: str        # "a habit"
    gloss: str       # what the cell's own parenthesis says it is
    contrast: str    # how the other cells' parentheses name it


#: The seven ways a trait shows (plan 06 section 3.1).
MODES: tuple[Mode, ...] = (
    Mode("attitude", "an attitude", "an attitude the person holds", "an attitude they hold"),
    Mode("habit", "a habit", "something the person does as a rule", "something they do as a rule"),
    Mode("speech", "a speech style", "a way the person speaks", "a way they speak"),
    Mode("emotion", "an emotional tendency", "a feeling the person tends to have", "a feeling they tend to have"),
    Mode("cognition", "a cognitive habit", "a way the person thinks", "a way they think"),
    Mode("moral", "a moral stance", "a moral stance the person takes", "a moral stance they take"),
    Mode("social", "a social strategy", "a strategy the person uses with other people",
         "a strategy they use with other people"),
)
MODE_BY_ID: dict[str, Mode] = {m.id: m for m in MODES}

A_TEMPLATE = ("Domain: {domain}. Mode: {mode}.\n"
              "Name 15 to 20 traits that are specifically about how a person relates to {domain}, each in the form "
              "of {mode} ({gloss}, as opposed to {contrasts}). Include admirable and unadmirable ones, and ones with "
              "no common single word.")

# --------------------------------------------------------------------------- (b) person seeding

B_TEMPLATE = ("Person: {person}.\n"
              "This person may be little known; the description is all we have, and factual accuracy about them does "
              "not matter here, only the vocabulary. Name the 8 to 12 traits that would most distinguish such a "
              "person from a typical person of their era, place and occupation, as those who knew them might have "
              "put it. Give the trait, its gloss, its antonym and its kind, as instructed.")
#: The dry run's (b) sample: the fixed, long-dead row of plan section 6 (one of the five random items drawn on
#: 2026-10-13 to check the API), never a fetched seed (section 5a).
DRY_RUN_SEED = {"seed_id": "b:r0001", "qid": "Q65871003", "name": "Tian Yi", "description": "person, CBDB ID = 367824",
                "kind": "real", "born": None, "died": "1684"}

# --------------------------------------------------------------------------- (c) languages

@dataclass(frozen=True)
class Language:
    code: str
    name: str        # English name, as the back-translation user turn and the master's {language} show it
    native: str      # the language's own name for itself


#: Roger, 2026-10-13: high to fairly-high resource languages; Persian replaced Tagalog.
LANGUAGES: tuple[Language, ...] = (
    Language("de", "German", "Deutsch"), Language("ja", "Japanese", "日本語"), Language("zh", "Mandarin", "普通话"),
    Language("ru", "Russian", "русский"), Language("ar", "Arabic", "العربية"), Language("fa", "Persian", "فارسی"),
    Language("fi", "Finnish", "suomi"), Language("ko", "Korean", "한국어"), Language("hi", "Hindi", "हिन्दी"),
    Language("tr", "Turkish", "Türkçe"),
)
LANGUAGE_BY_CODE: dict[str, Language] = {lang.code: lang for lang in LANGUAGES}

#: The English request each (c) user turn is translated from; ``{domain}`` stays a placeholder in the translation
#: and takes the translated domain name at render time (only in the heading line, so that no language needs an
#: inflected form of it).
C_USER_MASTER = ("Domain of life: {domain}.\n"
                 "Name 15 to 20 character traits that are specifically about how a person relates to this domain of "
                 "life: admirable and unadmirable ones, preferring ones for which English has no single word.")

#: The translation call (Sonnet 5.5, ten calls, live): the system turn.  Not a pinned rubric (it makes data, the
#: translations, which are pinned by their own sha256); its wording is under :data:`PROMPTS_VERSION`.
TRANSLATE_SYSTEM = (
    "You translate instructions for a language model from English into {language}, for a research project that "
    "asks speakers of many languages the same questions in their own language. Translate each text you are given "
    "in full into natural, idiomatic {language}, as a native speaker would write it, keeping its meaning, its order "
    "and its line breaks. Keep these exactly as they are, untranslated: every JSON key and quoted field name "
    "(\"approach\", \"items\", \"label\", \"romanization\", \"english_hint\", \"gloss\", \"antonym\", \"kind\", "
    "\"ambiguity_flag\"), the eight kind values (\"trait\", \"membership\", \"state\", \"physical\", \"role\", "
    "\"action\", \"evaluative\", \"not_a_persona\"), null, true and false, the JSON punctuation, and the placeholder "
    "{domain}. Where the English says that a gloss starts \"This means\", use the opening a {language} writer would "
    "use for such a definition.\n\n"
    "Answer in exactly this form, with nothing before or after it. First a note of one or two sentences on any "
    "choice of wording a reviewer should know about, then the translations:\n"
    "<note>...</note>\n<system>...</system>\n<user_template>...</user_template>\n"
    "<domains>\none line per domain, as id: the domain in {language} as a heading would name it\n</domains>")
TRANSLATE_USER = ("Text 1, the instructions:\n<<<\n{system}\n>>>\n\n"
                  "Text 2, the request, with the placeholder {{domain}} kept:\n<<<\n{user_template}\n>>>\n\n"
                  "Domains (id: English):\n{domains}")
#: The check of each translation for Roger's read (Haiku 5.5, ten calls, live): a literal translation back.
PROMPT_BACK_SYSTEM = (
    "You translate text from {language} into English as literally as you can while staying readable, so that a "
    "reviewer who does not read {language} can check what it says. Keep its order, its line breaks, the JSON keys "
    "and values left in English, and the placeholder {domain}.\n\n"
    "Answer in exactly this form, with nothing before or after it:\n"
    "<system>...</system>\n<user_template>...</user_template>\n<domains>\none line per domain, as id: English\n"
    "</domains>")

# --------------------------------------------------------------------------- (d) verbalized sampling

D_STAGE1_APPEND = ("\n\nFor each item also give \"probability\": your estimate, between 0 and 1, of how likely you "
                   "would have been to name this item if asked this question with no further guidance. Spread the "
                   "items over the range; do not give every item the same number.")
D_STAGE2_TEMPLATE = ("Earlier, asked the following, you answered as shown.\n"
                     "Question: {question}\n"
                     "Your answer: {answer}\n"
                     "Now give 15 to 20 further items, none of them in your answer above and none a rewording of "
                     "one, to which you would assign a probability below 0.03: {topic} that are real and nameable but "
                     "that you would almost never think of first. Same fields, including \"probability\".")
D_PROBABILITY_CEILING = 0.03

# --------------------------------------------------------------------------- (e) spelling constraints

LETTERS: tuple[str, ...] = tuple("abcdefghijklmnopqrstuvwxyz")
#: The 120 commonest initial bigrams of OEWN 2024's single-word adjective lemmas, commonest first (module
#: docstring for the derivation; frozen here, never recomputed at run time).
BIGRAMS: tuple[str, ...] = tuple("""
un co in re pr no di de ca an st su pa se ex tr ma pe bi ch mo me ac ba po sp al im br cr mi he sa ar ap be en so fa
fo te ho la as ad gr bo li th bl sc am cl ra ne sh ha pl fl ov bu mu le lo pu au ve fr cu ab do si fi ta to hy vi ce
ph sl va fe ge pi ro qu ag fu wi el sy wa gl ri wo at ru na da ga we dr or ti em hi ir ob op hu ep du lu af cy go ci
vo ou nu
""".split())
#: 20 suffixes (plan 06 section 3.5's ten, then ten more common in adjectives of character).
SUFFIXES: tuple[str, ...] = ("some", "ish", "minded", "hearted", "phobic", "philic", "ful", "less", "ic", "ous",
                             "ive", "able", "ant", "ent", "al", "ary", "ly", "y", "headed", "spirited")
#: 12 prefixes (plan 06 section 3.5's five, then seven more).
PREFIXES: tuple[str, ...] = ("over", "under", "un", "hyper", "self", "mis", "dis", "in", "anti", "counter", "ill",
                             "well")


@dataclass(frozen=True)
class Frame:
    id: str
    form: str        # "X about Y"
    gloss: str       # what the form is, in the constraint line
    each: str        # "each about a different Y"


FRAMES: tuple[Frame, ...] = (
    Frame("to", "X to Y", 'an adjective followed by "to" and a person, a thing or an act', "each to a different Y"),
    Frame("about", "X about Y", "an adjective about a thing or a subject", "each about a different Y"),
    Frame("with", "X with Y", 'an adjective followed by "with" and a person, a thing or a resource',
          "each with a different Y"),
)
FRAME_BY_ID: dict[str, Frame] = {f.id: f for f in FRAMES}
E_SPELLING_LINES: dict[str, str] = {
    "letter": "Spelling constraint: the label's main word begins with the letter \"{x}\".",
    "bigram": "Spelling constraint: the label's main word begins with the letters \"{x}\".",
    "suffix": "Spelling constraint: the label's main word ends in \"-{x}\".",
    "prefix": "Spelling constraint: the label's main word begins with the prefix \"{x}-\".",
}
E_SPELLING_BODY = ("Name 15 to 20 traits whose label satisfies the constraint. Go through the vocabulary that fits the "
                   "spelling, common words first; a phrase whose main word fits counts. If fewer than 15 real traits "
                   "fit, give the ones that do and stop; do not invent words.")
E_FRAME_LINE = "Form constraint: the label has the form \"{form}\", {gloss} (two to four words)."
E_FRAME_BODY = ("Name 15 to 20 traits of that form, {each}, common phrasings first. If fewer than 15 real traits fit, "
                "give the ones that do and stop; do not invent words.")

# --------------------------------------------------------------------------- the back-translation call's user turn

BACKTRANSLATE_HEADER = "Language: {language}.\nItems:"
BACKTRANSLATE_ITEM = "{i}. label: {label}; gloss: {gloss}; antonym: {antonym}"

#: Every example word the texts quote (scaffold and back-translation), checked by the prompt test.
EXAMPLE_WORDS: dict[str, tuple[str, ...]] = {
    SCAFFOLD_RUBRIC: ("punctilious", "slow to anger", "avoids the limelight", "great"),
    MULTILINGUAL_RUBRIC: (),
    BACKTRANSLATE_RUBRIC: ("reads the room",),
}


# --------------------------------------------------------------------------- pins and hashes

class RubricNotPinned(RuntimeError):
    """One of the generator's texts on disk is not its latest pinned version."""


def load_rubric(name: str, rubrics_dir: Optional[Path] = None, *, allow_unpinned: bool = False) -> dict:
    """``{"name", "text", "version", "sha256", "file"}``; refuses a text that is not the latest pin (with
    ``allow_unpinned``, for rendering only, ``version`` and ``sha256`` are None)."""
    if name not in RUBRICS:
        raise KeyError(f"not an llm_entropy rubric: {name!r}")
    probs = [p for p in sr.mismatches(rubrics_dir) if p.split(":", 1)[0] == name]
    path = sr.rubric_path(name, rubrics_dir)
    try:
        rel = str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        rel = str(path)
    text = sr.load_prompt(name, rubrics_dir)
    if probs:
        if not allow_unpinned:
            raise RubricNotPinned("; ".join(probs) + "\n" + sr.bump_command(probs))
        return {"name": name, "text": text, "version": None, "sha256": None, "file": rel}
    version, sha = sr.current_versions(rubrics_dir, (name,))[name]
    return {"name": name, "text": text, "version": version, "sha256": sha, "file": rel}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def wording_tables() -> dict:
    """Every table and template a user turn (or a translation request) depends on: what :data:`PROMPT_HASHES`
    pins."""
    return {
        "domains": [list(d) for d in DOMAINS], "modes": [list((m.id, m.name, m.gloss, m.contrast)) for m in MODES],
        "a_template": A_TEMPLATE, "b_template": B_TEMPLATE, "dry_run_seed": DRY_RUN_SEED,
        "languages": [[lang.code, lang.name, lang.native] for lang in LANGUAGES], "c_user_master": C_USER_MASTER,
        "translate_system": TRANSLATE_SYSTEM, "translate_user": TRANSLATE_USER, "prompt_back_system": PROMPT_BACK_SYSTEM,
        "d_stage1_append": D_STAGE1_APPEND, "d_stage2_template": D_STAGE2_TEMPLATE,
        "d_probability_ceiling": D_PROBABILITY_CEILING,
        "letters": list(LETTERS), "bigrams": list(BIGRAMS), "suffixes": list(SUFFIXES), "prefixes": list(PREFIXES),
        "frames": [[f.id, f.form, f.gloss, f.each] for f in FRAMES], "e_spelling_lines": E_SPELLING_LINES,
        "e_spelling_body": E_SPELLING_BODY, "e_frame_line": E_FRAME_LINE, "e_frame_body": E_FRAME_BODY,
        "backtranslate_header": BACKTRANSLATE_HEADER, "backtranslate_item": BACKTRANSLATE_ITEM,
        "example_words": {k: list(v) for k, v in EXAMPLE_WORDS.items()},
    }


def wording_sha256() -> str:
    return sha256_text(json.dumps(wording_tables(), sort_keys=True, ensure_ascii=False))


# --------------------------------------------------------------------------- prompts

@dataclass(frozen=True)
class Prompt:
    """One prompt of a family: its id (``a:money:habit``, ``b:r0001``, ``c:de:money``, ``e:bigram:sc``,
    ``d:a:money:habit``), the user turn, the language and the parts it was built from (``meta``)."""
    prompt_id: str
    family: str
    user: str
    language: str = "en"
    meta: Mapping = field(default_factory=dict)


def _or_list(xs: Sequence[str]) -> str:
    xs = list(xs)
    if len(xs) == 1:
        return xs[0]
    return ", ".join(xs[:-1]) + ", or " + xs[-1]


def render_a(domain: str, mode: str) -> str:
    """The (a) user turn of a (domain id, mode id) cell."""
    m = MODE_BY_ID[mode]
    contrasts = _or_list([x.contrast for x in MODES if x.id != m.id])
    return A_TEMPLATE.format(domain=DOMAIN_PHRASE[domain], mode=m.name, gloss=m.gloss, contrasts=contrasts)


def _year_text(v) -> Optional[str]:
    """A year as the (b) line shows it: ``1684``, ``44 BC``; None when unknown."""
    if v is None or v == "":
        return None
    try:
        y = int(str(v).lstrip("+"))
    except ValueError:
        return str(v)
    return f"{-y} BC" if y < 0 else str(y)


def person_line(seed: Mapping) -> str:
    """``Tian Yi (person, CBDB ID = 367824; died 1684)`` or ``<name> (<description>; fictional)``."""
    parts = []
    desc = (seed.get("description") or "").strip()
    if desc:
        parts.append(desc)
    tail = []
    if seed.get("kind") == "fictional":
        tail.append("fictional")
    else:
        b, d = _year_text(seed.get("born")), _year_text(seed.get("died"))
        if b:
            tail.append(f"born {b}")
        if d:
            tail.append(f"died {d}")
    inner = "; ".join([", ".join(parts)] + tail if parts else tail)
    return f"{seed['name']} ({inner})" if inner else str(seed["name"])


def render_b(seed: Mapping) -> str:
    """The (b) user turn of one seed (a mapping with ``name``, ``description``, ``kind``, ``born``, ``died``)."""
    return B_TEMPLATE.format(person=person_line(seed))


def render_e(constraint: str) -> str:
    """The (e) user turn of a constraint id (``letter:q``, ``bigram:sc``, ``suffix:minded``, ``prefix:over``,
    ``frame:about``)."""
    kind, _, x = constraint.partition(":")
    if kind == "frame":
        f = FRAME_BY_ID[x]
        return E_FRAME_LINE.format(form=f.form, gloss=f.gloss) + "\n" + E_FRAME_BODY.format(each=f.each)
    if kind not in E_SPELLING_LINES:
        raise KeyError(f"unknown (e) constraint {constraint!r}")
    return E_SPELLING_LINES[kind].format(x=x) + "\n" + E_SPELLING_BODY


def e_constraints() -> list[str]:
    return ([f"letter:{x}" for x in LETTERS] + [f"bigram:{x}" for x in BIGRAMS] + [f"suffix:{x}" for x in SUFFIXES]
            + [f"prefix:{x}" for x in PREFIXES] + [f"frame:{f.id}" for f in FRAMES])


def render_c(lang: str, domain: str, *, prompts_json: Mapping) -> tuple[str, str]:
    """``(system, user)`` of a (c) cell, from the language's recorded translation (``multilingual_prompts.json``'s
    ``languages[lang]``); ``KeyError`` when the language has none."""
    entry = (prompts_json.get("languages") or {})[lang]
    return entry["system"], entry["user_template"].replace("{domain}", entry["domains"][domain])


def render_d_stage1(base_user: str) -> str:
    """Stage 1 of (d): the (a) or (e) user turn with the probability paragraph appended."""
    return base_user + D_STAGE1_APPEND


def d_topic(base_prompt_id: str) -> str:
    """What stage 2 asks more of: ``traits about money as a habit``, or the (e) constraint's."""
    parts = base_prompt_id.split(":")
    if parts[0] == "a":
        return f"traits about {DOMAIN_PHRASE[parts[1]]} as {MODE_BY_ID[parts[2]].name}"
    if parts[0] == "e":
        return "traits of the same form" if parts[1] == "frame" else "traits whose label satisfies the same constraint"
    raise ValueError(f"(d) wraps (a) and (e) only, not {base_prompt_id!r}")


def render_d_stage2(base_prompt_id: str, stage1_user: str, stage1_answer_text: str) -> str:
    """Stage 2 of (d): a fresh call whose user turn quotes stage 1's user turn and its answer verbatim."""
    return D_STAGE2_TEMPLATE.format(question=stage1_user, answer=stage1_answer_text, topic=d_topic(base_prompt_id))


def _q(s) -> str:
    return "null" if s is None else json.dumps(str(s), ensure_ascii=False)


def render_backtranslate(lang: str, items: Sequence[Mapping]) -> str:
    """The back-translation call's user turn: the language's English name and the answer's items in order."""
    lines = [BACKTRANSLATE_HEADER.format(language=LANGUAGE_BY_CODE[lang].name)]
    for i, it in enumerate(items, 1):
        lines.append(BACKTRANSLATE_ITEM.format(i=i, label=_q(it.get("label")), gloss=_q(it.get("gloss")),
                                               antonym=_q(it.get("antonym"))))
    return "\n".join(lines)


def render_master(lang: str, master_text: str) -> str:
    """The English master (:data:`MULTILINGUAL_RUBRIC`'s text) for one language, before translation."""
    return master_text.replace("{language}", LANGUAGE_BY_CODE[lang].name)


def render_translate(lang: str, master_text: str) -> tuple[str, str]:
    """``(system, user)`` of the translation call for one language."""
    name = LANGUAGE_BY_CODE[lang].name
    system = TRANSLATE_SYSTEM.replace("{language}", name)
    user = TRANSLATE_USER.format(system=render_master(lang, master_text), user_template=C_USER_MASTER,
                                 domains="\n".join(f"{d}: {p}" for d, p in DOMAINS))
    return system, user


def render_prompt_back(lang: str, entry: Mapping) -> tuple[str, str]:
    """``(system, user)`` of the check call that translates one language's prompts back into English."""
    name = LANGUAGE_BY_CODE[lang].name
    system = PROMPT_BACK_SYSTEM.replace("{language}", name)
    user = (f"<system>\n{entry['system']}\n</system>\n<user_template>\n{entry['user_template']}\n</user_template>\n"
            "<domains>\n" + "\n".join(f"{d}: {entry['domains'][d]}" for d in DOMAIN_IDS) + "\n</domains>")
    return system, user


# --------------------------------------------------------------------------- the grids

def grid_prompts(family: str, *, seeds: Optional[Sequence[Mapping]] = None, prompts_json: Optional[Mapping] = None,
                 with_probabilities: bool = False) -> list[Prompt]:
    """Every prompt of a family, in a fixed order: (a) 210 cells, (b) one per seed (``seeds``, opaque ``seed_id``
    each), (c) 300 cells (``prompts_json`` gives each language's text), (e) 181 constraints.  ``with_probabilities``
    appends (d)'s stage-1 paragraph to (a) and (e)."""
    if with_probabilities and family not in ("a", "e"):
        raise ValueError("--with-probabilities is (d)'s stage 1 and applies to families a and e only")
    out: list[Prompt] = []
    if family == "a":
        for d in DOMAIN_IDS:
            for m in MODES:
                u = render_a(d, m.id)
                out.append(Prompt(f"a:{d}:{m.id}", "a", render_d_stage1(u) if with_probabilities else u,
                                  meta={"domain": d, "mode": m.id, "with_probabilities": with_probabilities}))
    elif family == "b":
        for s in seeds or ():
            out.append(Prompt(str(s["seed_id"]), "b", render_b(s),
                              meta={"seed_kind": s.get("kind"), "era": s.get("era")}))
    elif family == "c":
        if prompts_json is None:
            raise ValueError("family c needs multilingual_prompts.json (translate-prompts)")
        for lang in LANGUAGES:
            for d in DOMAIN_IDS:
                system, user = render_c(lang.code, d, prompts_json=prompts_json)
                out.append(Prompt(f"c:{lang.code}:{d}", "c", user, language=lang.code,
                                  meta={"domain": d, "system": system,
                                        "language_prompt_sha256": prompts_json["languages"][lang.code]["sha256"]}))
    elif family == "e":
        for c in e_constraints():
            u = render_e(c)
            out.append(Prompt(f"e:{c}", "e", render_d_stage1(u) if with_probabilities else u,
                              meta={"constraint": c, "with_probabilities": with_probabilities}))
    else:
        raise ValueError(f"no grid for family {family!r}: generate takes {GENERATE_FAMILIES}")
    return out


GRID_SIZES: dict[str, int] = {"a": len(DOMAINS) * len(MODES), "b": 600, "c": len(LANGUAGES) * len(DOMAINS),
                              "e": len(LETTERS) + len(BIGRAMS) + len(SUFFIXES) + len(PREFIXES) + len(FRAMES)}


def draw_order(prompt_ids: Iterable[str], seed: int) -> list[str]:
    """The seeded order the share and ``--n-prompts`` draws take their prompts from: by the sha256 of the seed and
    the prompt id, so that a draw does not depend on the list's order and a smaller draw is the start of a larger
    one with the same seed (the model-test arms' 40 prompts are inside the pilot's share where the share has 40)."""
    return sorted(prompt_ids, key=lambda p: (sha256_text(f"llm_entropy:{seed}:{p}"), p))


def select_prompts(prompts: Sequence[Prompt], *, share: Optional[float] = None, n: Optional[int] = None,
                   seed: int = 0) -> list[Prompt]:
    """A seeded draw of ``round(share x len)`` prompts, or ``n`` of them, in the grid's order (every prompt with all
    its runs: the caller makes the runs).  Neither: every prompt."""
    if share is None and n is None:
        return list(prompts)
    if share is not None and not 0 < float(share) <= 1:
        raise ValueError(f"--share must be in (0, 1], got {share}")
    k = int(n) if n is not None else int(round(float(share) * len(prompts)))
    keep = set(draw_order([p.prompt_id for p in prompts], seed)[:max(0, k)])
    return [p for p in prompts if p.prompt_id in keep]


def variant_samples() -> list[tuple[str, str, str]]:
    """``[(variant, prompt id, user turn)]``: one rendered user turn per variant (the dry runs and ``prompts``)."""
    out = [("a: domain x mode", "a:money:habit", render_a("money", "habit")),
           ("b: person seeding (real; the fixed sample row of plan section 6)", DRY_RUN_SEED["seed_id"],
            render_b(DRY_RUN_SEED)),
           ("b: person seeding (fictional; an invented sample)", "b:f0001",
            render_b({"name": "Captain Zarnath Quell", "description": "fictional starship captain in an invented "
                      "serial", "kind": "fictional"})),
           ("d: stage 1 of a:money:habit", "a:money:habit", render_d_stage1(render_a("money", "habit"))),
           ("d: stage 2 of a:money:habit", "d:a:money:habit",
            render_d_stage2("a:money:habit", render_d_stage1(render_a("money", "habit")),
                            '{"approach": "...", "items": [...]}  (the stage-1 reply text, verbatim)')),
           ("e: letter", "e:letter:q", render_e("letter:q")),
           ("e: bigram", "e:bigram:sc", render_e("bigram:sc")),
           ("e: suffix", "e:suffix:minded", render_e("suffix:minded")),
           ("e: prefix", "e:prefix:over", render_e("prefix:over")),
           ("e: frame", "e:frame:about", render_e("frame:about")),
           ("e: frame", "e:frame:to", render_e("frame:to")),
           ("e: frame", "e:frame:with", render_e("frame:with")),
           ("back-translation", "c:de:money",
            render_backtranslate("de", [{"label": "pfennigfuchserisch", "gloss": "Das bedeutet, bei jeder "
                                         "Kleinigkeit um den letzten Cent zu feilschen.", "antonym": "großzügig"},
                                        {"label": "geldscheu", "gloss": "Das bedeutet, Geldfragen zu meiden.",
                                         "antonym": None}]))]
    return out


__all__ = ["FAMILIES", "GENERATE_FAMILIES", "FAMILY_NAMES", "SCAFFOLD_RUBRIC", "MULTILINGUAL_RUBRIC",
           "BACKTRANSLATE_RUBRIC", "RUBRICS", "PROMPTS_VERSION", "PROMPT_HASHES", "DOMAINS", "DOMAIN_IDS", "MODES",
           "Mode", "LANGUAGES", "Language", "LANGUAGE_BY_CODE", "LETTERS", "BIGRAMS", "SUFFIXES", "PREFIXES", "FRAMES",
           "Frame", "C_USER_MASTER", "DRY_RUN_SEED", "EXAMPLE_WORDS", "D_PROBABILITY_CEILING", "RubricNotPinned",
           "load_rubric", "sha256_text", "wording_tables", "wording_sha256", "Prompt", "render_a", "person_line",
           "render_b", "render_e", "e_constraints", "render_c", "render_d_stage1", "d_topic", "render_d_stage2",
           "render_backtranslate", "render_master", "render_translate", "render_prompt_back", "grid_prompts",
           "GRID_SIZES", "draw_order", "select_prompts", "variant_samples"]
