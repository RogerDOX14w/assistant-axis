"""Name each pole twice: blind (the statements alone) and hinted (with the IPIP scales they are scored on).

One call per pole and form, on Haiku 5.5 (M3 decision 17: every Haiku call of the subproject is 5.5), the
system prompt the form's rubric (cached when it clears the model's minimum, ``split_runner.caches_system``), the
user turn one JSON object: ``{"statements": [...]}`` (blind) or ``{"statements": [...], "scales": [...]}``
(hinted).  Statements are shown as first-person sentences ("I get chores done right away."), at most
:data:`MAX_STATEMENTS` per pole (a seeded choice above that).  The answer is one JSON object, reason first
(the judging rule): ``reason, label, gloss, antonym_label, antonym_gloss, is_trait, ambiguity_flag,
single_word_exists``.

Rubric rules (plan § 6): symptom-like dispositions count as traits (Roger's answer to plan 07 § 9.1: the corpus
has ADHD and OCD); moods, abilities, interests and life circumstances do not; the examples are near-duplicates of
corpus words, never corpus labels or queue entries (the hygiene rule; tested); no temperature (Haiku 5.5 refuses
one, ``llm.accepts_temperature``).

**Parser** (:func:`parse_naming`): strict, as the plan asks: the reply must be one JSON object and nothing else (a
fenced or prose-wrapped reply is rejected and counted), every key present, the label 1-4 words (lower-cased with a
note), the gloss opening "This means" (over 25 words is noted, not rejected), the three flags booleans.  A
rejected answer is asked once more (:data:`ASK_ATTEMPTS`); every response received is charged to ``usage`` and
recorded, before parsing, in ``naming_responses.jsonl`` (append-only).

Labels: no corpus label is ever shown (the statements are item texts and the scale names are IPIP's), so the judge
display form is a no-op here; the scale names still pass through ``prompt_label`` and every record carries
``label_form`` (plan § 1, one rule everywhere).

**Versions**: a prompt text is pinned to its version in :data:`PINNED` (one version, one text; the test fails
when a text changes without a new version).
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from assistant_axis.entity_id import normalize_to_file_name
from assistant_axis.gapgen.cost import Estimate
from assistant_axis.gapgen.llm import call_anthropic_json
from assistant_axis.gapgen.prompt_labels import DEFAULT_LABEL_FORM, check_label_form, prompt_label
from assistant_axis.gapgen.registry import utc_now
from assistant_axis.judge_pricing import BudgetExceededError, MultiModelUsage

from .cluster import item_embed_text

DEFAULT_MODEL = "claude-haiku-5-5"
#: Haiku 5.5 thinks adaptively and its thinking counts against max_tokens (head_scope.py's measurement: about
#: 150 output tokens a head, thinking included); one pole's answer is about 150 tokens.
MAX_TOKENS = 4000
ASK_ATTEMPTS = 2
CONCURRENCY = 8
MAX_STATEMENTS = 30
MAX_LABEL_WORDS = 4
MAX_GLOSS_WORDS = 25
FORMS: tuple[str, ...] = ("blind", "hinted")
#: The answer's keys, in the order the prompt asks for them.
FIELD_NAMES: tuple[str, ...] = ("reason", "label", "gloss", "antonym_label", "antonym_gloss", "is_trait",
                                "ambiguity_flag", "single_word_exists", "statements", "scales", "scale", "inventory",
                                "direction")
ANSWER_KEYS: tuple[str, ...] = FIELD_NAMES[:8]
#: The example labels the prompts quote (none is a corpus label, a corpus stem or a seed-queue name; tested).
EXAMPLE_LABELS: tuple[str, ...] = ("punctilious", "slow to anger", "keeps others at arm's length")
#: For the estimate (measured on nothing yet; the plan's 700 in / 250 out per call, with the system prompt).
EST_IN_TOKENS, EST_OUT_TOKENS = 900, 400

_COMMON = """\
A persona trait is a lasting disposition that a persona can show in how it speaks and acts: a habit of feeling, \
thinking, acting or relating to others. Symptom-like dispositions count as traits when they describe a lasting \
tendency (being easily distracted, checking things over and over, feeling cut off from one's own feelings). These \
are not traits: a passing mood or state, an ability or skill, an interest or hobby, and a life circumstance (a job, \
a family situation, an illness as such).

Give:
- "reason": one short sentence on what the statements have in common.
- "label": the disposition's name in 1 to 4 lowercase words: an adjective or adjective phrase where English has one \
(for example "punctilious" or "slow to anger"), otherwise a short descriptive phrase (for example "keeps others at \
arm's length").
- "gloss": one sentence of at most 25 words that starts "This means" and describes the disposition in plain words, \
without repeating the label.
- "antonym_label": the name of the opposite disposition, in the same form, or null if it has no clear opposite.
- "antonym_gloss": one sentence starting "This means" that describes the opposite, or null.
- "is_trait": true if the disposition is a persona trait as defined above, false if it is a mood, an ability, an \
interest or a life circumstance.
- "ambiguity_flag": true if the statements do not share one disposition, or if the label could easily be read in \
another sense.
- "single_word_exists": true if one common English word names this disposition well.

Respond with one JSON object and nothing else, reason first:
{"reason": "<one short sentence>", "label": "<1-4 lowercase words>", "gloss": "This means ...", "antonym_label": \
"<1-4 lowercase words>" or null, "antonym_gloss": "This means ..." or null, "is_trait": true or false, \
"ambiguity_flag": true or false, "single_word_exists": true or false}"""

NAMING_PROMPT = """\
You are given one JSON object holding a group of self-report statements from a personality questionnaire \
("statements"). People rated how well each statement describes them, and these statements were grouped because \
they express closely related behavior. Name the one disposition of a person that the group expresses, as a \
persona trait.

""" + _COMMON

HINTED_PROMPT = """\
You are given one JSON object holding a group of self-report statements from a personality questionnaire \
("statements") and the questionnaire scales they are scored on ("scales"). People rated how well each statement \
describes them, and these statements were grouped because they express closely related behavior. Name the one \
disposition of a person that the group expresses, as a persona trait.

Each scale is given with its inventory, its direction ("for": agreeing with the statements raises the scale's \
score; "against": agreeing lowers it) and how many of the statements it scores. Treat the scale names as hints to \
what the questionnaire's authors meant to measure: name the disposition the statements themselves express, using a \
scale's name only where it fits them.

""" + _COMMON

PROMPT_VERSIONS: dict[str, int] = {"blind": 1, "hinted": 1}
#: form -> {version: sha256 of the prompt text}.  Append only.
PINNED: dict[str, dict[int, str]] = {
    "blind": {1: "41b361d75a6150c79edf575b80bd713329ed4f3c63275b98d82cad81ce3f0fdb"},
    "hinted": {1: "e33a08e94ca73a911b3b5a13403460cf4aa10881e8e8b0a0f2fe4e86ca3b56ea"},
}


def system_prompt(form: str) -> str:
    if form not in FORMS:
        raise ValueError(f"form must be one of {FORMS}, not {form!r}")
    return NAMING_PROMPT if form == "blind" else HINTED_PROMPT


def prompt_version(form: str) -> int:
    return PROMPT_VERSIONS[form]


def prompt_sha256(form: str) -> str:
    return hashlib.sha256(system_prompt(form).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- the user turn

@dataclass
class PoleRef:
    """What a naming call needs of a pole: its id, its item texts and (hinted) the scales they are scored on."""
    granularity: int
    cluster_id: int
    pole: str
    statements: list                       # item texts as IPIP prints them
    scales: list = field(default_factory=list)   # [{"scale", "inventory", "direction", "statements"}]

    @property
    def key(self) -> tuple:
        return (self.granularity, self.cluster_id, self.pole)


def shown_statements(p: PoleRef) -> list[str]:
    """The statements shown, first person, at most :data:`MAX_STATEMENTS` (a seeded choice by pole id above
    that, in the pole's order)."""
    texts = list(p.statements)
    if len(texts) > MAX_STATEMENTS:
        rng = random.Random(f"{p.granularity}:{p.cluster_id}:{p.pole}")
        keep = sorted(rng.sample(range(len(texts)), MAX_STATEMENTS))
        texts = [texts[i] for i in keep]
    return [item_embed_text(t) for t in texts]


def build_user(p: PoleRef) -> str:
    return json.dumps({"statements": shown_statements(p)}, ensure_ascii=False)


def build_hinted_user(p: PoleRef, *, label_form: str = DEFAULT_LABEL_FORM) -> str:
    scales = [{"scale": prompt_label(s["scale"], label_form), "inventory": s["inventory"], "direction": s["direction"],
               "statements": s["statements"]} for s in p.scales]
    return json.dumps({"statements": shown_statements(p), "scales": scales}, ensure_ascii=False)


def scales_for(constructs: Mapping[str, int]) -> list[dict]:
    """A pole's ``constructs`` (``"INV:Construct:+" -> n``) as the hinted turn's scales, most statements first."""
    out = []
    for k, n in sorted(constructs.items(), key=lambda kv: (-kv[1], kv[0])):
        inv, rest = k.split(":", 1)
        construct, sign = rest.rsplit(":", 1)
        out.append({"scale": construct, "inventory": inv, "direction": "for" if sign == "+" else "against",
                    "statements": int(n)})
    return out


# --------------------------------------------------------------------------- the parser

@dataclass
class Naming:
    reason: str
    label: str
    stem: str
    gloss: str
    antonym_label: Optional[str]
    antonym_gloss: Optional[str]
    is_trait: bool
    ambiguity_flag: bool
    single_word_exists: bool
    notes: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def _bool(v: Any) -> Optional[bool]:
    if isinstance(v, bool):
        return v
    if isinstance(v, str) and v.strip().lower() in ("true", "false"):
        return v.strip().lower() == "true"
    return None


def _label(v: Any, notes: list, what: str) -> Optional[str]:
    if not isinstance(v, str) or not v.strip():
        return None
    s = " ".join(v.split())
    if s != s.lower():
        notes.append(f"{what} lower-cased")
        s = s.lower()
    if len(s.replace("-", " ").split()) > MAX_LABEL_WORDS and len(s.split()) > MAX_LABEL_WORDS:
        return None
    try:
        normalize_to_file_name(s)
    except ValueError:
        return None
    return s


def parse_naming(text: Optional[str]) -> tuple[Optional[Naming], Optional[str]]:
    """``(naming, None)`` or ``(None, "<kind>: <detail>")``; kinds: no_response, empty, fenced, not_one_object,
    not_json, missing_key, bad_value, bad_label, bad_gloss."""
    if text is None:
        return None, "no_response: the request failed"
    t = text.strip()
    if not t:
        return None, "empty: no text"
    if t.startswith("```"):
        return None, "fenced: the reply is wrapped in a code fence"
    if not (t.startswith("{") and t.endswith("}")):
        return None, "not_one_object: text outside the JSON object"
    try:
        obj = json.loads(t)
    except json.JSONDecodeError as exc:
        return None, f"not_json: {exc.msg}"
    if not isinstance(obj, dict):
        return None, "not_one_object: not a JSON object"
    missing = [k for k in ANSWER_KEYS if k not in obj]
    if missing:
        return None, f"missing_key: {', '.join(missing)}"
    notes: list = []
    reason = obj["reason"]
    if not isinstance(reason, str) or not reason.strip():
        return None, "bad_value: reason"
    label = _label(obj["label"], notes, "label")
    if label is None:
        return None, f"bad_label: {obj['label']!r}"
    gloss = obj["gloss"]
    if not isinstance(gloss, str) or not gloss.strip().startswith("This means"):
        return None, f"bad_gloss: {str(gloss)[:60]!r}"
    gloss = " ".join(gloss.split())
    if len(gloss.split()) > MAX_GLOSS_WORDS + 2:          # "This means" plus 25 words, with a little slack
        notes.append("gloss over 25 words")
    ant = obj["antonym_label"]
    ant_label = None if ant is None or (isinstance(ant, str) and ant.strip().lower() in ("", "null", "none")) \
        else _label(ant, notes, "antonym_label")
    if ant is not None and ant_label is None and not (isinstance(ant, str) and ant.strip().lower() in ("", "null", "none")):
        return None, f"bad_label: antonym {ant!r}"
    ag = obj["antonym_gloss"]
    ant_gloss = " ".join(ag.split()) if isinstance(ag, str) and ag.strip() and ag.strip().lower() != "null" else None
    flags = {k: _bool(obj[k]) for k in ("is_trait", "ambiguity_flag", "single_word_exists")}
    bad = [k for k, v in flags.items() if v is None]
    if bad:
        return None, f"bad_value: {', '.join(bad)}"
    extra = sorted(set(obj) - set(ANSWER_KEYS))
    if extra:
        notes.append(f"extra keys {extra}")
    return Naming(reason=" ".join(reason.split()), label=label, stem=normalize_to_file_name(label), gloss=gloss,
                  antonym_label=ant_label, antonym_gloss=ant_gloss, notes=notes, **flags), None


# --------------------------------------------------------------------------- the calls

@dataclass
class NameResult:
    namings: dict = field(default_factory=dict)        # (granularity, cluster_id, pole, form) -> Naming
    errors: dict = field(default_factory=dict)         # same key -> the last parse error
    error_kinds: dict = field(default_factory=dict)    # kind -> count over every attempt
    first_attempt_ok: int = 0
    n_calls: int = 0
    stopped_by_budget: bool = False

    def parse_rate(self) -> tuple[int, int]:
        """``(poles named, poles asked)`` over the forms."""
        return len(self.namings), len(self.namings) + len(self.errors)


def _should_cache(system: str, model: str) -> bool:
    from assistant_axis.gapgen.split_runner import caches_system
    return caches_system(system, model)


async def name_poles(poles: Sequence[PoleRef], *, client, model: str = DEFAULT_MODEL, usage: MultiModelUsage,
                     hinted: bool = True, responses_path: Optional[Path] = None, concurrency: int = CONCURRENCY,
                     max_tokens: int = MAX_TOKENS, label_form: str = DEFAULT_LABEL_FORM,
                     forms: Optional[Sequence[str]] = None, now=utc_now) -> NameResult:
    """The blind call for every pole, and the hinted call beside it when ``hinted``.  A rejected answer is asked
    once more.  A ``BudgetExceededError`` from a guarded ``usage`` stops the run after keeping (and recording) the
    answer that crossed the cap."""
    check_label_form(label_form)
    forms = list(forms) if forms else (["blind", "hinted"] if hinted else ["blind"])
    res = NameResult()
    sem = asyncio.Semaphore(max(1, concurrency))
    lock = asyncio.Lock()
    if responses_path is not None:
        Path(responses_path).parent.mkdir(parents=True, exist_ok=True)

    async def one(p: PoleRef, form: str) -> None:
        system = system_prompt(form)
        user = build_user(p) if form == "blind" else build_hinted_user(p, label_form=label_form)
        cache = _should_cache(system, model)
        key = (*p.key, form)
        for attempt in range(1, ASK_ATTEMPTS + 1):
            async with sem:
                if res.stopped_by_budget:
                    return
                meta: dict = {}
                try:
                    text = await call_anthropic_json(client, system=system, user=user, model=model,
                                                     max_tokens=max_tokens, temperature=None, usage=usage,
                                                     cache_system=cache, meta=meta)
                except BudgetExceededError:
                    text = meta.get("text")
                    res.stopped_by_budget = True
                naming, err = parse_naming(text)
                rec = {"granularity": p.granularity, "cluster_id": p.cluster_id, "pole": p.pole, "form": form,
                       "model": model, "prompt_version": prompt_version(form), "prompt_sha256": prompt_sha256(form),
                       "label_form": label_form, "cache_system": cache, "user": user, "attempt": attempt,
                       "text": text, "stop_reason": meta.get("stop_reason"), "usage_raw": meta.get("usage_raw"),
                       "error": meta.get("error"), "parsed": naming.as_dict() if naming else None,
                       "parse_error": err, "at": now()}
                async with lock:
                    res.n_calls += 1
                    if responses_path is not None:
                        with open(responses_path, "a", encoding="utf-8") as fh:
                            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    if naming is not None:
                        res.namings[key] = naming
                        res.errors.pop(key, None)
                        res.first_attempt_ok += int(attempt == 1)
                    else:
                        kind = err.split(":")[0]
                        res.error_kinds[kind] = res.error_kinds.get(kind, 0) + 1
                        res.errors[key] = err
            if naming is not None or res.stopped_by_budget or (text is None and meta.get("error")):
                return

    await asyncio.gather(*(one(p, f) for p in poles for f in forms))
    return res


def estimate(poles: Sequence[PoleRef], *, hinted: bool = True, model: str = DEFAULT_MODEL) -> Estimate:
    """``n_poles x forms`` calls at the plan's per-call tokens (retries not counted)."""
    est = Estimate()
    n = len(poles) * (2 if hinted else 1)
    est.add(f"naming ({'blind + hinted' if hinted else 'blind'})", model, n, EST_IN_TOKENS, EST_OUT_TOKENS)
    return est


def make_client():
    """The Anthropic client with the direct key from ``.env`` (no router)."""
    import os

    from dotenv import load_dotenv
    from assistant_axis.gapgen.paths import REPO_ROOT
    load_dotenv(REPO_ROOT / ".env")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is not set (.env): the naming calls need the direct key")
    import anthropic
    return anthropic.AsyncAnthropic()
