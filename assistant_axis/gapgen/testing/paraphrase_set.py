"""The paraphrase sanity set: does the recovery harness's matcher find a corpus trait again when a candidate names
it in other words?  (Coding plan 13 § 1, § 6, § 8 and task 7; the prompt is "Rendered prompt: the paraphrase
synonym call" there.)

The harness matches a candidate to a hidden corpus trait by its label first, with no model call, so a candidate
that carries the trait's own name never exercises the overlap call.  This module makes 80 candidates that name
corpus traits in other words and turns them into an input the harness can score:

1. **The set** (:func:`build_set`, $0): 40 traits whose hiding group (:func:`recovery.hiding_groups`) is the
   trait alone, and one pole of each of 40 recorded pairs (a hiding group of exactly two that is a label-reciprocal
   pair), the partner recorded.  Each must have a fresh recorded paraphrase from the M2 calibration
   (``data/candidates/calibration/paraphrases.json``): a trait with none, one whose paraphrase was written from
   another label or description (its ``sources`` sha256 no longer matches ``label\\ndescription``), or one whose
   paraphrase names the trait's own label as a word (the user turn would carry the hidden label) is refused and
   another drawn, and counted.  The draw is seeded and spread over M1's regions: each kind's quota per region is
   proportional to that region's share of the kind's hiding groups, at least one per region that has an eligible
   group (when the quota allows), never more than it has.  No two items share a hiding group.  Items are numbered
   ``s01``.. (singles) and ``p01``.. (pair poles), each in stem order.
2. **The synonym call** (:func:`run`, Haiku 5.5, live, about $0.01): one call per item, the pinned rubric
   ``paraphrase_synonym`` as the system turn (:data:`SYNONYM_SYSTEM`; refused unless the text on disk is its latest
   pin) and ``Definition: <paraphrase>`` as the user turn (:func:`render_user`), never the hidden label.  The answer,
   reasoning first, is a label of one or two words and a fresh 12-16-word "This means ..." gloss
   (:func:`parse`).  Every response is appended to ``responses.jsonl`` **before** it is parsed and charged to the
   usage tracker (unparseable ones too); an unparseable answer is asked once more.  An answer whose label is the
   hidden stem or one of its ``renamed_from`` (normalised as the registry normalises a surface, compared
   separator-blind as the harness compares labels) is on the *label path*: it is asked once more with the line
   ``The label must not be the word "<label>" or a spelling of it.``, and the re-ask's answer is kept
   (``reasked``); if it names the trait again it stays on the label path (``label_path``).  ``resume`` sends
   nothing whose prompt (system and user turn, :func:`prompt_sha256`) already has a parsed answer on record.
3. **The scratch registry** (:func:`to_scratch_registry`): one row per answered item in a registry log of its own
   (never the real one), source ``testing/paraphrase_set``, with a synthetic M1 filter block (``verdict: trait``,
   the gloss, the hidden trait's region and alignment score) so that M3 selects it
   (:func:`novelty_runner.candidate_from_row`).  Nothing in a row names the hidden trait; the row's source
   ``source_ref`` is the item id.  Two items whose labels normalise to one stem are not merged: the second gets
   sense 2 (key ``<stem>#2``) and both rows record ``filter.same_label_as``.
4. **The hidden file** (:func:`hidden_file`): every item's trait and partner, through
   :func:`recovery.fixed_hidden`, each hiding group whole.  The harness then runs on the scratch registry with that
   hidden file (:func:`harness_command`).
5. **The report** (:func:`report_figures`, :func:`report`): from the harness batch's ``seed*/matches.jsonl``, its
   ``recovery_report.json`` and each seed's reduced-corpus M3 results: concept recall over the items (the item's
   candidate has a ``recovers`` row for its own hidden trait), split by the reduced run's decision on the
   candidate (kept, covered, not decided); the pair poles' pair-recovery (the pole recovered and the partner read
   ``opposite``); the label-path count; the parse rate; the misses with their readings.

Files (under ``data/candidates/testing/paraphrase_set/``): ``set.jsonl`` (:func:`write_set`), ``responses.jsonl``,
``answers.jsonl`` (the answer records; :func:`run` writes it), ``usage.json``, ``registry.jsonl`` (the scratch
registry, not tracked), ``hidden.json`` (the CLI writes :func:`hidden_file`'s record with
:func:`recovery.write_hidden`), ``report.md``.  The CLI is ``generator_dashboard.py paraphrase-set build | run |
report``.

``MAX_TOKENS`` is 2,000, not the plan's "about 400": Haiku 5.5 thinks adaptively and its thinking counts against
``max_tokens`` (the platform gives every model whose thinking cannot be switched off 2,000; the IPIP naming call
measured about 150 output tokens an answer, thinking included).  Only the tokens produced are billed.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import os
import random
import re
import shutil
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.judge import extract_json_blob, warn_if_low_parse_rate
from assistant_axis.judge_pricing import BudgetExceededError, MultiModelUsage

from .. import novelty as NV
from .. import paths
from .. import records as RF
from .. import recovery as RC
from .. import split_rubrics as sr
from ..cost import Estimate, resume_usage
from ..llm import call_anthropic_json
from ..normalize import make_key, normalize_candidate, split_key
from ..prompt_labels import DEFAULT_LABEL_FORM, prompt_label
from ..registry import Registry, new_record, utc_now, utc_stamp
from . import PARAPHRASE_SET_DIR

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-5-5"
#: Haiku 5.5 thinks adaptively and its thinking counts against max_tokens (module docstring).
MAX_TOKENS = 2000
RUBRIC_NAME = "paraphrase_synonym"
SET_DIR = PARAPHRASE_SET_DIR
SCHEMA_VERSION = 1

SET_NAME = "set.jsonl"
RESPONSES_NAME = "responses.jsonl"
ANSWERS_NAME = "answers.jsonl"
USAGE_NAME = "usage.json"
REGISTRY_NAME = "registry.jsonl"
HIDDEN_NAME = "hidden.json"
REPORT_NAME = "report.md"

PARAPHRASES_PATH = paths.CALIBRATION_DIR / "paraphrases.json"
#: The ``paraphrase_source`` every item records (the paraphrases file, relative to ``data/candidates/``).
PARAPHRASE_SOURCE = "calibration/paraphrases.json"
#: The scratch registry's source and the synthetic filter block's batch id.
GENERATOR = "testing"
RUN_ID = "paraphrase_set"
BATCH_ID = "testing/paraphrase_set"
#: The harness batch the plan names (``recovery_test.py``'s default for ``--generator testing --run-id
#: paraphrase_set``).
HARNESS_BATCH_ID = f"rec_{GENERATOR}_{RUN_ID}"

KINDS: tuple[str, ...] = ("single", "pair_pole")
#: Refusal reasons of the draw, in the order they are checked.
REFUSALS: tuple[str, ...] = ("no_paraphrase", "stale", "names_label")
#: An unparseable answer is asked once more (two sends per prompt at most).
ASK_ATTEMPTS = 2
CONCURRENCY = 8
#: Output tokens a call, thinking included, for the estimate (the IPIP naming call's measurement on Haiku 5.5).
OUT_TOKENS = 150
#: The estimate's allowance for re-asks and retries, as a share of the items.
REASK_ALLOWANCE = 0.25
REASK_LINE = 'The label must not be the word "{label}" or a spelling of it.'


class RubricNotPinned(RuntimeError):
    """The synonym rubric's text on disk is not its latest pinned version."""


# --------------------------------------------------------------------------- the rubric

def load_rubric(rubrics_dir: Optional[Path] = None) -> dict:
    """``{"name", "text", "version", "sha256", "file"}`` of the pinned synonym rubric; refuses a text that is not its
    latest pin (:class:`RubricNotPinned`, with the ``rubric_pins.py bump`` command)."""
    probs = [p for p in sr.mismatches(rubrics_dir) if p.split(":", 1)[0] == RUBRIC_NAME]
    if probs:
        raise RubricNotPinned("; ".join(probs) + "\n" + sr.bump_command(probs))
    version, sha = sr.current_versions(rubrics_dir, (RUBRIC_NAME,))[RUBRIC_NAME]
    path = sr.rubric_path(RUBRIC_NAME, rubrics_dir)
    try:
        rel = str(path.resolve().relative_to(paths.REPO_ROOT.resolve()))
    except ValueError:
        rel = str(path)
    return {"name": RUBRIC_NAME, "text": sr.load_prompt(RUBRIC_NAME, rubrics_dir), "version": version, "sha256": sha,
            "file": rel}


def system_prompt(rubrics_dir: Optional[Path] = None) -> str:
    """The synonym call's system turn, exactly as the rubric file holds it (and only when it is pinned)."""
    return load_rubric(rubrics_dir)["text"]


def __getattr__(name: str) -> Any:
    """``SYNONYM_SYSTEM``: the pinned rubric's text, read when asked for (an unpinned text raises
    :class:`RubricNotPinned` there, not at import)."""
    if name == "SYNONYM_SYSTEM":
        return system_prompt()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# --------------------------------------------------------------------------- items

@dataclass(frozen=True)
class Item:
    """One row of ``set.jsonl`` (plan 13 § 6, "Paraphrase-set item")."""
    id: str                                # s01.. (singles), p01.. (pair poles)
    kind: str                              # "single" | "pair_pole"
    hidden_stem: str
    partner_stem: Optional[str]            # the pair partner (None for a single)
    region: Optional[str]                  # the hidden trait's, from corpus_regions.json
    alignment_score: Optional[int]         # the hidden trait's, from corpus_regions.json
    paraphrase_source: str
    paraphrase: str

    def as_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Mapping) -> "Item":
        return cls(**{f.name: d.get(f.name) for f in fields(cls)})


ITEM_FIELDS: tuple[str, ...] = tuple(f.name for f in fields(Item))


def write_set(items: Sequence[Item], path: Path) -> Path:
    atomic_write_text("".join(json.dumps(it.as_dict(), ensure_ascii=False) + "\n" for it in items), Path(path))
    return Path(path)


def read_set(path: Path) -> list[Item]:
    return [Item.from_dict(d) for d in _read_jsonl(path)]


def write_answers(answers: Sequence[Mapping], path: Path) -> Path:
    atomic_write_text("".join(json.dumps(dict(a), ensure_ascii=False) + "\n" for a in answers), Path(path))
    return Path(path)


def read_answers(path: Path) -> list[dict]:
    return _read_jsonl(path)


def read_responses(path: Path) -> list[dict]:
    return _read_jsonl(path)


def _read_jsonl(path: Path) -> list[dict]:
    p = Path(path)
    if not RF.exists(p):
        return []
    return RF.read_jsonl(p)


def _append(rec: Mapping, path: Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(dict(rec), ensure_ascii=False) + "\n")
        fh.flush()


# --------------------------------------------------------------------------- inputs

def paraphrase_source(label: str, description: str) -> str:
    """sha256 of what a paraphrase was written from (``calibrate_metric.paraphrase_source``: the stored label and
    the description, joined by a newline)."""
    return hashlib.sha256(f"{label}\n{description}".encode("utf-8")).hexdigest()


def load_paraphrases(path: Path = PARAPHRASES_PATH) -> tuple[dict[str, str], dict[str, str]]:
    """``(paraphrases, sources)`` of the M2 calibration's paraphrase cache: stem -> "This means ..." text, and stem
    -> sha256 of the ``label\\ndescription`` it was written from."""
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return dict(d.get("paraphrases") or {}), dict(d.get("sources") or {})


def load_alignment(path: Path = paths.CORPUS_REGIONS_PATH) -> dict[str, Optional[int]]:
    """``{stem: alignment_score}`` from ``corpus_regions.json`` (its ``result`` block); ``{}`` when absent."""
    p = Path(path)
    if not p.exists():
        return {}
    doc = json.loads(p.read_text(encoding="utf-8"))
    res = doc.get("result", doc) if isinstance(doc, dict) else {}
    out = {}
    for s, v in res.items():
        a = (v or {}).get("alignment_score") if isinstance(v, Mapping) else None
        out[s] = a if isinstance(a, int) and not isinstance(a, bool) else None
    return out


def _words(text: str) -> str:
    """Lower case, hyphens and underscores as spaces, single-spaced (for the whole-word label check)."""
    return " ".join(re.sub(r"[-_]", " ", str(text).lower()).split())


def names_own_label(trait: NV.CorpusTrait, text: str) -> bool:
    """Whether ``text`` carries the trait's label (without a standard's parenthesised suffix) or its stem as a whole
    word or phrase, hyphens and spaces alike."""
    hay = f" {re.sub(r'[^a-z0-9 ]', ' ', _words(text))} "
    base = re.sub(r"\s*\(.*\)\s*$", "", trait.label)
    needles = {_words(base), _words(trait.stem)}
    return any(n and f" {n} " in hay for n in needles)


def refusal(stem: str, traits: Mapping[str, NV.CorpusTrait], paraphrases: Mapping[str, str],
            sources: Optional[Mapping[str, str]] = None) -> Optional[str]:
    """Why ``stem`` cannot be an item (:data:`REFUSALS`), or None: no recorded paraphrase; a paraphrase written from
    another label or description (an entry without a recorded source is taken as fresh, as the calibration does);
    a paraphrase that names the trait's own label."""
    p = paraphrases.get(stem)
    if not isinstance(p, str) or not p.strip():
        return "no_paraphrase"
    t = traits[stem]
    rec = (sources or {}).get(stem)
    if rec is not None and rec != paraphrase_source(t.label, t.description):
        return "stale"
    if names_own_label(t, p):
        return "names_label"
    return None


# --------------------------------------------------------------------------- the draw

def _quotas(pool: Mapping[str, int], eligible: Mapping[str, int], n: int, rng: random.Random) -> dict[str, int]:
    """``n`` split over the regions that have an eligible group: proportional to each region's share of the pool,
    at least one each when ``n`` allows, at most its eligible groups; remainders (and ties, in a seeded order) to
    the regions furthest below their share."""
    regions = sorted(r for r in pool if eligible.get(r, 0) > 0)
    tie = {r: rng.random() for r in regions}
    total = sum(pool[r] for r in regions)
    raw = {r: n * pool[r] / total for r in regions}
    q = {r: min(eligible[r], int(math.floor(raw[r] + 1e-9))) for r in regions}
    if n >= len(regions):
        for r in regions:
            q[r] = max(q[r], 1)
    while sum(q.values()) > n:
        r = max((r for r in regions if q[r] > 1), key=lambda r: (q[r] - raw[r], tie[r]))
        q[r] -= 1
    while sum(q.values()) < n:
        r = max((r for r in regions if q[r] < eligible[r]), key=lambda r: (raw[r] - q[r], tie[r]))
        q[r] += 1
    return q


def _draw(kind: str, groups: Sequence[Sequence[str]], n: int, *, why: Mapping[str, Optional[str]],
          regions: Mapping[str, Optional[str]], seed: int, refused: Counter, refused_stems: dict) -> tuple[list, dict]:
    """``n`` (stem, group) picks of one kind (module docstring, step 1) and the kind's pool and quotas."""
    strata: dict[str, list[list[str]]] = defaultdict(list)
    for g in groups:
        strata[RC._group_stratum(list(g), regions)].append(sorted(g))
    pool = {r: len(gs) for r, gs in strata.items()}
    eligible = {r: sum(1 for g in gs if any(why[m] is None for m in g)) for r, gs in strata.items()}
    if sum(eligible.values()) < n:
        raise ValueError(f"only {sum(eligible.values())} {kind.replace('_', ' ')} groups have a fresh paraphrase, "
                         f"fewer than the {n} asked for")
    quotas = _quotas(pool, eligible, n, random.Random(f"{seed}:{kind}:quotas"))
    out = []
    for r in sorted(strata):
        gs = sorted(strata[r])
        rng = random.Random(f"{seed}:{kind}:{r}")
        rng.shuffle(gs)
        taken = 0
        for g in gs:
            if taken >= quotas.get(r, 0):
                break
            poles = list(g)
            rng.shuffle(poles)
            pick = None
            for m in poles:
                if why[m] is None:
                    pick = m
                    break
                refused[why[m]] += 1
                refused_stems[why[m]].append(m)
            if pick is not None:
                out.append((pick, g))
                taken += 1
    ineligible: dict[str, list[str]] = defaultdict(list)
    for g in groups:
        for m in g:
            if why[m] is not None:
                ineligible[why[m]].append(m)
    info = {"groups": len(groups), "eligible": sum(eligible.values()),
            "ineligible": {k: sorted(ineligible[k]) for k in REFUSALS if ineligible.get(k)}}
    return out, {"pool": info, "quotas": dict(sorted(quotas.items()))}


def build_set_with_stats(traits: Mapping[str, NV.CorpusTrait], paraphrases: Mapping[str, str],
                         regions: Mapping[str, Optional[str]], *, n_single: int = 40, n_pairs: int = 40, seed: int = 0,
                         sources: Optional[Mapping[str, str]] = None,
                         alignment: Optional[Mapping[str, Optional[int]]] = None) -> tuple[list[Item], dict]:
    """:func:`build_set` and what the draw did: ``{"seed", "n_single", "n_pairs", "pool": {kind: {"groups",
    "eligible", "ineligible": {reason: [stems]}}}, "quotas": {kind: {region: n}}, "refused": {reason: n},
    "refused_stems": {reason: [stems]}, "regions": {kind | "all": {region: n}}}``.  ``pool`` counts every trait the
    kind could draw that is ineligible; ``refused`` only those the seeded walk drew and passed over."""
    alignment = alignment or {}
    groups = RC.hiding_groups(traits)
    singles = [g for g in groups if len(g) == 1]
    pairs = [g for g in groups if len(g) == 2 and traits[g[0]].pair_partner == g[1]
             and traits[g[1]].pair_partner == g[0]]
    why = {m: refusal(m, traits, paraphrases, sources) for g in singles + pairs for m in g}
    refused: Counter = Counter()
    refused_stems: dict[str, list[str]] = defaultdict(list)
    picks_s, info_s = _draw("single", singles, n_single, why=why, regions=regions, seed=seed, refused=refused,
                            refused_stems=refused_stems)
    picks_p, info_p = _draw("pair_pole", pairs, n_pairs, why=why, regions=regions, seed=seed, refused=refused,
                            refused_stems=refused_stems)

    def make(kind: str, picks: list, prefix: str) -> list[Item]:
        width = max(2, len(str(len(picks))))
        out = []
        for i, (stem, g) in enumerate(sorted(picks), 1):
            partner = next((m for m in g if m != stem), None) if kind == "pair_pole" else None
            out.append(Item(id=f"{prefix}{i:0{width}d}", kind=kind, hidden_stem=stem, partner_stem=partner,
                            region=regions.get(stem), alignment_score=alignment.get(stem),
                            paraphrase_source=PARAPHRASE_SOURCE, paraphrase=paraphrases[stem]))
        return out

    items = make("single", picks_s, "s") + make("pair_pole", picks_p, "p")
    by_kind = {k: dict(sorted(Counter(it.region or RC.NO_REGION for it in items if it.kind == k).items()))
               for k in KINDS}
    stats = {"seed": int(seed), "n_single": n_single, "n_pairs": n_pairs,
             "pool": {"single": info_s["pool"], "pair_pole": info_p["pool"]},
             "quotas": {"single": info_s["quotas"], "pair_pole": info_p["quotas"]},
             "refused": {k: refused.get(k, 0) for k in REFUSALS},
             "refused_stems": {k: sorted(refused_stems.get(k, [])) for k in REFUSALS},
             "regions": {**by_kind, "all": dict(sorted(Counter(it.region or RC.NO_REGION for it in items).items()))}}
    return items, stats


def build_set(traits: Mapping[str, NV.CorpusTrait], paraphrases: Mapping[str, str],
              regions: Mapping[str, Optional[str]], *, n_single: int = 40, n_pairs: int = 40, seed: int = 0,
              sources: Optional[Mapping[str, str]] = None,
              alignment: Optional[Mapping[str, Optional[int]]] = None) -> list[Item]:
    """The seeded set (module docstring, step 1): ``n_single`` singles then ``n_pairs`` pair poles.  ``regions``:
    ``recovery.load_regions``; ``sources``: the paraphrases' source hashes (:func:`load_paraphrases`);
    ``alignment``: :func:`load_alignment`.  ``ValueError`` when a kind has too few eligible groups."""
    return build_set_with_stats(traits, paraphrases, regions, n_single=n_single, n_pairs=n_pairs, seed=seed,
                                sources=sources, alignment=alignment)[0]


# --------------------------------------------------------------------------- the call

def render_user(item: Item, *, reask_label: Optional[str] = None, label_form: str = DEFAULT_LABEL_FORM) -> str:
    """The user turn: ``Definition: <paraphrase>``; with ``reask_label`` (the hidden trait's stored label, shown in
    the judge display form, ``prompt_labels.prompt_label``) one more line, :data:`REASK_LINE`.  The hidden label is
    never in the user turn otherwise."""
    user = f"Definition: {item.paraphrase}"
    if reask_label:
        user += "\n" + REASK_LINE.format(label=prompt_label(reask_label, label_form))
    return user


def prompt_sha256(system: str, user: str) -> str:
    """sha256 of one call's prompt, its system and user turns (as ``json.dumps({"system", "user"})``, sorted keys)."""
    blob = json.dumps({"system": system, "user": user}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Answer:
    reasoning: str
    label: str
    gloss: str


def answer_stem(label: Any) -> Optional[str]:
    """The registry stem of a label (``normalize.normalize_candidate``: the surface cleaned, then
    ``normalize_to_file_name``), or None when it does not normalise."""
    if not isinstance(label, str) or not label.strip():
        return None
    try:
        return normalize_candidate(label).stem or None
    except ValueError:
        return None


def parse_with_reason(text: Optional[str]) -> tuple[Optional[Answer], Optional[str]]:
    """``(answer, None)`` for a reply holding ``{"reasoning", "label", "gloss"}`` (a code fence or prose around the
    object is tolerated), else ``(None, why)``: no text, not a JSON object, a field missing or not text, an empty
    label or one that does not normalise, a gloss that does not start "This means"."""
    if not text:
        return None, "no text"
    blob = extract_json_blob(text)
    try:
        d = json.loads(blob) if blob else None
    except (json.JSONDecodeError, TypeError):
        d = None
    if not isinstance(d, dict):
        return None, "not a JSON object"
    for k in ("reasoning", "label", "gloss"):
        if not isinstance(d.get(k), str):
            return None, f"no {k}"
    label, gloss = d["label"].strip(), d["gloss"].strip()
    if not label:
        return None, "empty label"
    if answer_stem(label) is None:
        return None, "label does not normalise"
    if not gloss.startswith("This means"):
        return None, "gloss does not start 'This means'"
    return Answer(reasoning=d["reasoning"].strip(), label=label, gloss=gloss), None


def parse(text: Optional[str]) -> Optional[Answer]:
    """:func:`parse_with_reason`'s answer, or None."""
    return parse_with_reason(text)[0]


def names_hidden(label: Any, trait: NV.CorpusTrait) -> bool:
    """Whether a label names the hidden trait: its stem (:func:`answer_stem`) is, separator-blind
    (:func:`novelty.blind`), the trait's stem or one of its ``renamed_from``, as the harness's label match compares."""
    stem = answer_stem(label)
    if stem is None:
        return False
    b = NV.blind(stem)
    return b == NV.blind(trait.stem) or any(b == NV.blind(o) for o in trait.renamed_from)


def _unanswered(it: Item, failure: str, n_calls: int, model: str, rub: Mapping) -> dict:
    return it.as_dict() | {"label": None, "stem": None, "gloss": None, "reasoning": None, "label_path": False,
                           "reasked": False, "first_label": None, "model": model, "prompt_sha256": None,
                           "rubric_version": rub["version"], "answered": False, "failure": failure,
                           "reask_failure": None, "n_calls": n_calls, "reused": False}


async def run_async(items: Sequence[Item], *, client, usage: MultiModelUsage, out_dir: Path, resume: bool = False,
                    concurrency: int = CONCURRENCY, traits: Mapping[str, NV.CorpusTrait],
                    rubrics_dir: Optional[Path] = None, model: str = MODEL, max_tokens: int = MAX_TOKENS,
                    now: Callable[[], str] = utc_now) -> list[dict]:
    """:func:`run`, as a coroutine."""
    rub = load_rubric(rubrics_dir)
    system = rub["text"]
    out = Path(out_dir)
    resp_path, usage_path, answers_path = out / RESPONSES_NAME, out / USAGE_NAME, out / ANSWERS_NAME
    unknown = sorted({it.hidden_stem for it in items} - set(traits))
    if unknown:
        raise ValueError(f"{len(unknown)} hidden stem(s) not in the corpus: {', '.join(unknown[:10])}")
    earlier = read_responses(resp_path)
    if earlier and not resume:
        raise FileExistsError(f"{resp_path} holds {len(earlier)} responses: resume the run, or write it elsewhere")
    out.mkdir(parents=True, exist_ok=True)
    if resume:
        usage.merge_from(resume_usage(MultiModelUsage.load_or_create(usage_path), earlier, where=str(out)))
    reusable: dict[str, Answer] = {}
    attempts: Counter = Counter()
    for r in earlier:
        attempts[r.get("item_id")] = max(attempts[r.get("item_id")], int(r.get("attempt") or 0))
        if r.get("model") == model and r.get("prompt_sha256"):
            a = parse(r.get("text"))
            if a is not None:
                reusable[r["prompt_sha256"]] = a
    state: dict = {"n_calls": 0, "n_parsed": 0, "stop": None}
    sem = asyncio.Semaphore(max(1, int(concurrency)))
    answers: dict[str, dict] = {}

    async def ask(it: Item, reask_label: Optional[str]) -> tuple[Optional[Answer], str, str, int]:
        """``(answer, prompt sha, how, sends)``: ``how`` is reused, answered, unparseable, no_response or budget."""
        user = render_user(it, reask_label=reask_label)
        sha = prompt_sha256(system, user)
        if sha in reusable:
            return reusable[sha], sha, "reused", 0
        sends, how = 0, "budget"
        for _ in range(ASK_ATTEMPTS):
            if state["stop"] is not None:
                return None, sha, "budget", sends
            meta: dict = {}
            try:
                text = await call_anthropic_json(client, system=system, user=user, model=model, max_tokens=max_tokens,
                                                 temperature=None, usage=usage, cache_system=True, meta=meta)
            except BudgetExceededError as exc:      # the response that crossed the cap is kept (it was paid for)
                text = meta.get("text")
                state["stop"] = state["stop"] or exc
            attempts[it.id] += 1
            sends += 1
            state["n_calls"] += 1
            raw = meta.get("usage_raw") or {}
            _append({"item_id": it.id, "attempt": attempts[it.id], "reask": reask_label is not None, "model": model,
                     "rubric": RUBRIC_NAME, "rubric_version": rub["version"], "rubric_sha256": rub["sha256"],
                     "prompt_sha256": sha, "user": user, "text": text, "stop_reason": meta.get("stop_reason"),
                     "usage_raw": raw, "charged_as": model if raw else None, "error": meta.get("error"),
                     "at": now()}, resp_path)
            ans = parse(text)                       # parsed only once the response is on record
            if ans is not None:
                state["n_parsed"] += 1
                return ans, sha, "answered", sends
            how = "no_response" if text is None and meta.get("error") else "unparseable"
        return None, sha, how, sends

    async def one(it: Item) -> None:
        async with sem:
            if state["stop"] is not None:
                return
            trait = traits[it.hidden_stem]
            ans, sha, how, n = await ask(it, None)
            if ans is None:
                answers[it.id] = _unanswered(it, how, n, model, rub)
                return
            reused = how == "reused"
            reasked, first_label, reask_failure = False, None, None
            if names_hidden(ans.label, trait):
                reasked, first_label = True, ans.label
                ans2, sha2, how2, n2 = await ask(it, trait.label)
                n += n2
                reused = reused and how2 == "reused"
                if ans2 is not None:
                    ans, sha = ans2, sha2
                else:
                    reask_failure = how2
            answers[it.id] = it.as_dict() | {
                "label": ans.label, "stem": answer_stem(ans.label), "gloss": ans.gloss, "reasoning": ans.reasoning,
                "label_path": names_hidden(ans.label, trait), "reasked": reasked, "first_label": first_label,
                "model": model, "prompt_sha256": sha, "rubric_version": rub["version"], "answered": True,
                "failure": None, "reask_failure": reask_failure, "n_calls": n, "reused": reused}

    done: list[dict] = []
    try:
        await asyncio.gather(*(one(it) for it in items))
    finally:
        done = [answers[it.id] for it in items if it.id in answers]
        write_answers(done, answers_path)
        usage.write_json(usage_path)
    warn_if_low_parse_rate(label=f"paraphrase_set:{model}", n_ok=state["n_parsed"], n_total=state["n_calls"],
                           logger_obj=logger)
    logger.info("%s", usage.log_line())
    if state["stop"] is not None:
        raise state["stop"]
    return done


def run(items: Sequence[Item], *, client, usage: MultiModelUsage, out_dir: Path, resume: bool = False,
        concurrency: int = CONCURRENCY, traits: Mapping[str, NV.CorpusTrait], rubrics_dir: Optional[Path] = None,
        model: str = MODEL, max_tokens: int = MAX_TOKENS, now: Callable[[], str] = utc_now) -> list[dict]:
    """One synonym call per item (module docstring, step 2), live; returns the answer records, in item order, and
    writes them to ``<out_dir>/answers.jsonl``.

    An answer record is the item's fields plus ``label``, ``stem`` (the registry stem of the label), ``gloss``,
    ``reasoning``, ``label_path`` (the kept answer names the hidden trait), ``reasked`` (the first answer did, and
    the item was asked again; ``first_label`` is that answer's label), ``model``, ``prompt_sha256`` (of the kept
    answer's prompt), ``rubric_version``, ``answered``, ``failure`` (unparseable, no_response or budget, for an item
    with no answer), ``reask_failure``, ``n_calls`` (sent this session) and ``reused`` (taken from the record).

    Every response is appended to ``<out_dir>/responses.jsonl`` before it is parsed (the item id, attempt, re-ask
    flag, model, rubric version and sha256, ``prompt_sha256``, the user turn, the text, stop reason, billed usage as
    ``usage_raw`` with ``charged_as``, error, time) and charged to ``usage`` by ``llm.call_anthropic_json``.  A
    responses file with records needs ``resume=True`` (``FileExistsError`` otherwise); a resume adds the earlier
    spend to ``usage`` (``cost.resume_usage`` of ``usage.json`` and the records) before it sends anything, so pass a
    fresh tracker.  ``usage.json`` and ``answers.jsonl`` are written in a ``finally``; a budget stop
    (``BudgetExceededError`` from a guarded ``usage``) keeps the response that crossed the cap, sends nothing more,
    writes both and re-raises.  ``warn_if_low_parse_rate`` runs over this session's sends."""
    return asyncio.run(run_async(items, client=client, usage=usage, out_dir=out_dir, resume=resume,
                                 concurrency=concurrency, traits=traits, rubrics_dir=rubrics_dir, model=model,
                                 max_tokens=max_tokens, now=now))


def estimate(items: Sequence[Item], *, system: Optional[str] = None, model: str = MODEL) -> Estimate:
    """One call per item at the mean prompt size (characters / 4 x the tokenizer factor) and :data:`OUT_TOKENS`
    out, plus :data:`REASK_ALLOWANCE` of that for re-asks and retries."""
    from ..overlap_test import CHARS_PER_TOKEN, tokenizer_factor
    system = system_prompt() if system is None else system
    est = Estimate()
    if not items:
        return est
    f = tokenizer_factor(model)
    per_in = int(round(sum((len(system) + len(render_user(it))) / CHARS_PER_TOKEN * f for it in items) / len(items)))
    reask_in = per_in + int(round(len(REASK_LINE) / CHARS_PER_TOKEN * f))
    est.add("synonym calls (one per item)", model, len(items), per_in, OUT_TOKENS)
    est.add("re-asks and retries (allowance)", model, int(math.ceil(REASK_ALLOWANCE * len(items))), reask_in,
            OUT_TOKENS)
    return est


# --------------------------------------------------------------------------- the scratch registry and hidden file

def registry_keys(items: Sequence[Item], answers: Iterable[Mapping]) -> dict[str, str]:
    """``{item id: registry key}`` for the answered items, in item order: ``<stem>#1``, and ``<stem>#2``, ... for a
    later item whose label normalises to a stem an earlier one took (their rows stay apart)."""
    by = {a["id"]: a for a in answers if a.get("answered")}
    seen: Counter = Counter()
    out = {}
    for it in items:
        a = by.get(it.id)
        stem = answer_stem(a.get("label")) if a else None
        if stem is None:
            continue
        seen[stem] += 1
        out[it.id] = make_key(stem, seen[stem])
    return out


def _refuse_real_registry(path: Path) -> None:
    p = Path(path).absolute()
    real = {Path(x).absolute() for x in (paths.REGISTRY_PATH, paths.REGISTRY_SNAPSHOT_PATH,
                                         paths.REGISTRY_SNAPSHOT_GZ_PATH)}
    if p in real or p.resolve() in {r.resolve() for r in real} or str(p).endswith(".gz"):
        raise ValueError(f"{path} is the platform's registry: the paraphrase set writes a scratch registry of its own "
                         f"(default {SET_DIR / REGISTRY_NAME})")


def to_scratch_registry(items: Sequence[Item], answers: Iterable[Mapping], regions: Mapping[str, Optional[str]],
                        path: Path, *, now: Optional[str] = None) -> int:
    """Write the scratch registry (module docstring, step 3) at ``path`` afresh (an existing file is copied to
    ``<path>.bak.<UTC>`` first) and return the number of rows.  ``regions`` (``recovery.load_regions``) gives a
    row's ``filter.region`` (the item's own region where the map has no entry).  ``ValueError`` for the platform's
    registry or its snapshot."""
    path = Path(path)
    _refuse_real_registry(path)
    answers = list(answers)
    by = {a["id"]: a for a in answers if a.get("answered")}
    keys = registry_keys(items, answers)
    by_stem: dict[str, list[str]] = defaultdict(list)
    for iid, key in keys.items():
        by_stem[split_key(key)[0]].append(iid)
    now = now or utc_now()
    rows = []
    for rank, it in enumerate(items, 1):
        if it.id not in keys:
            continue
        a = by[it.id]
        stem, sense = split_key(keys[it.id])
        src = {"generator": GENERATOR, "run_id": RUN_ID, "rank": rank, "score": None, "source_ref": it.id,
               "gloss_hint": a["gloss"], "partner_hint": None, "surface": a["label"]}
        rec = new_record(a["label"], sense_id=sense, sources=[src], now=now)
        region = regions.get(it.hidden_stem, it.region) if regions else it.region
        rec["gloss"] = a["gloss"]
        rec["filter"] = {"pipeline": "synthetic", "verdict": "trait", "outcome": "trait", "gloss": a["gloss"],
                         "region": region, "alignment": it.alignment_score, "alignment_score": it.alignment_score,
                         "batch_id": BATCH_ID, "synthetic": True, "model": a.get("model"), "at": now}
        others = [x for x in by_stem[stem] if x != it.id]
        if others:
            rec["filter"]["same_label_as"] = others
        rows.append(rec)
    if path.exists():
        shutil.copy2(path, path.with_name(f"{path.name}.bak.{utc_stamp()}"))
        path.unlink()
    Registry(path).write(rows, now=now)
    return len(rows)


def hidden_file(items: Sequence[Item], traits: Mapping[str, NV.CorpusTrait], regions: Mapping[str, Optional[str]],
                kinds: Mapping[str, str]) -> dict:
    """The harness's hidden set: every item's trait and partner (``recovery.fixed_hidden``, each hiding group whole,
    ``hidden_frac`` None, ``source`` :data:`BATCH_ID`).  Write it with ``recovery.write_hidden``."""
    stems = [s for it in items for s in (it.hidden_stem, it.partner_stem) if s]
    return RC.fixed_hidden(stems, traits, regions=regions, kinds=kinds, source=BATCH_ID)


def harness_command(set_dir: Path = SET_DIR, *, budget_usd: float = 4.0) -> str:
    """The harness run the plan prints after ``run`` (§ 7), on the scratch registry and the hidden file."""
    def rel(p: Path) -> str:
        try:
            return str(Path(p).absolute().relative_to(paths.REPO_ROOT))
        except ValueError:
            return str(p)
    return (f"uv run python data_analysis/gap_generation/recovery_test.py --generator {GENERATOR} --run-id {RUN_ID} "
            f"--registry {rel(Path(set_dir) / REGISTRY_NAME)} --hidden-file {rel(Path(set_dir) / HIDDEN_NAME)} --seed 0 "
            f"--budget-usd {budget_usd:g}")


# --------------------------------------------------------------------------- the report

def _share(n: int, d: int) -> Optional[float]:
    return round(n / d, 4) if d else None


def _count(n: int, d: int) -> dict:
    return {"n": d, "recovered": n, "share": _share(n, d)}


def _seed_of(d: Path) -> Optional[int]:
    m = re.fullmatch(r"seed(\d+)", d.name)
    return int(m.group(1)) if m else None


def _harness_report(batch_dir: Path) -> dict:
    p = Path(batch_dir) / "recovery_report.json"
    if not p.exists():
        return {}
    doc = json.loads(p.read_text(encoding="utf-8"))
    return doc.get("result", doc) if isinstance(doc, dict) else {}


def _decisions(batch_dir: Path, seed: int, rows: Sequence[Mapping], harness: Mapping,
               candidates_dir: Optional[Path]) -> tuple[str, dict, str]:
    """``(reduced run's batch id, {key: novelty block}, where from)``: the reduced-corpus M3 run's
    ``results.jsonl`` when it is there, else the decisions the match rows carry."""
    rr = next(((s.get("reduced_run") or {}) for s in harness.get("seeds") or [] if s.get("seed") == seed), {})
    batch = rr.get("batch_id") or f"{Path(batch_dir).name}_s{seed}"
    res = paths.novelty_dir(batch, candidates_dir=candidates_dir) / "results.jsonl"
    if RF.exists(res):
        return batch, {r["key"]: (r.get("novelty") or {}) for r in _read_jsonl(res)}, "results.jsonl"
    out: dict = {}
    for r in rows:
        out.setdefault(r["key"], {"decision": r.get("decision"), "covered_by": r.get("covered_by")})
    return batch, out, "matches.jsonl"


def _short(r: Mapping) -> dict:
    keep = ("stem", "how", "cosine", "rank", "cut_off", "sonnet", "opus", "verdict", "recovers", "stalled", "match")
    return {k: r[k] for k in keep if k in r}


def _bucket(decision: Optional[str], answered: bool) -> str:
    if not answered:
        return "no_answer"
    if decision in RC.KEPT_DECISIONS:
        return "kept"
    if decision == "covered":
        return "covered"
    return "not_decided"


BUCKETS: tuple[str, ...] = ("kept", "covered", "not_decided", "no_answer")


def report_figures(batch_dir: Path, *, set_path: Path, answers_path: Path, responses_path: Optional[Path] = None,
                   registry_path: Optional[Path] = None, candidates_dir: Optional[Path] = None,
                   data_dir: Optional[Path] = None) -> dict:
    """The report's figures (module docstring, step 5) from a harness batch directory (``data/candidates/recovery/
    <B>/``): ``{"n_items", "n_by_kind", "answers": {"answered", "unanswered", "reasked", "label_path_first",
    "label_path"}, "parse": {"n_responses", "n_parsed", "rate"}, "batch", "seeds": [{"seed", "reduced_run",
    "decisions_from", "concept_recall", "overlap_recall", "by_decision", "by_kind", "by_how", "pair_recovery",
    "items", "misses"}]}``.  Each item's registry key comes from the scratch registry's rows (``registry_path``) or,
    without one, from :func:`registry_keys`; ``candidates_dir`` locates the reduced runs' ``novelty/<B>_s<S>/``."""
    del data_dir                                        # the figures need no trait text; :func:`report` uses it
    batch_dir = Path(batch_dir)
    items = read_set(set_path)
    answers = read_answers(answers_path)
    by_ans = {a["id"]: a for a in answers}
    if registry_path is not None and Path(registry_path).exists():
        keys = {s.get("source_ref"): k for k, r in Registry(registry_path).fold().items()
                for s in r.get("sources") or [] if s.get("generator") == GENERATOR and s.get("run_id") == RUN_ID}
    else:
        keys = registry_keys(items, answers)
    responses = read_responses(responses_path or Path(answers_path).parent / RESPONSES_NAME)
    n_parsed = sum(1 for r in responses if parse(r.get("text")) is not None)
    answered = [a for a in answers if a.get("answered")]
    harness = _harness_report(batch_dir)
    seeds = []
    for sd in sorted((d for d in batch_dir.glob("seed*") if d.is_dir() and _seed_of(d) is not None), key=_seed_of):
        seed = _seed_of(sd)
        rows = _read_jsonl(sd / "matches.jsonl")
        batch, decisions, src = _decisions(batch_dir, seed, rows, harness, candidates_dir)
        per_item = []
        for it in items:
            a = by_ans.get(it.id) or {}
            key = keys.get(it.id)
            own = [r for r in rows if key and r.get("key") == key and r.get("stem") == it.hidden_stem]
            rec = [r for r in own if r.get("recovers")]
            how = ("label" if any(r.get("how") == "label" for r in rec) else "overlap") if rec else None
            nv = (decisions.get(key) or {}) if key else {}
            partner_rows = [r for r in rows if key and it.partner_stem and r.get("key") == key
                            and r.get("stem") == it.partner_stem]
            per_item.append({
                "id": it.id, "kind": it.kind, "hidden_stem": it.hidden_stem, "partner_stem": it.partner_stem,
                "region": it.region, "key": key, "label": a.get("label"), "gloss": a.get("gloss"),
                "paraphrase": it.paraphrase, "label_path": bool(a.get("label_path")),
                "decision": nv.get("decision"), "covered_by": nv.get("covered_by"),
                "bucket": _bucket(nv.get("decision"), bool(key)), "recovered": bool(rec), "how": how,
                "partner_opposite": any(r.get("verdict") == "opposite" for r in partner_rows) if it.partner_stem
                else None,
                "readings": [_short(r) for r in own], "partner_readings": [_short(r) for r in partner_rows]})
        n = len(per_item)
        got = [x for x in per_item if x["recovered"]]
        not_label = [x for x in per_item if x["how"] != "label"]
        pairs = [x for x in per_item if x["kind"] == "pair_pole"]
        misses = []
        for x in per_item:
            if x["recovered"]:
                continue
            if x["bucket"] == "no_answer":
                why = "no answer"
            elif not x["readings"]:
                why = "not judged: the hidden trait is not among the candidate's nearest in the full corpus" \
                    if x["decision"] else "not decided by the reduced run"
            elif any(r.get("stalled") for r in x["readings"]):
                why = "stalled: no reading"
            else:
                why = "read below the cut-off"
            misses.append(x | {"why": why})
        seeds.append({
            "seed": seed, "reduced_run": batch, "decisions_from": src,
            "concept_recall": _count(len(got), n),
            "overlap_recall": _count(sum(1 for x in not_label if x["recovered"]), len(not_label)),
            "by_decision": {b: _count(sum(1 for x in per_item if x["bucket"] == b and x["recovered"]),
                                      sum(1 for x in per_item if x["bucket"] == b)) for b in BUCKETS},
            "by_kind": {k: _count(sum(1 for x in per_item if x["kind"] == k and x["recovered"]),
                                  sum(1 for x in per_item if x["kind"] == k)) for k in KINDS},
            "by_how": {"label": sum(1 for x in got if x["how"] == "label"),
                       "overlap": sum(1 for x in got if x["how"] == "overlap")},
            "pair_recovery": {"n": len(pairs), "pole_recovered": sum(1 for x in pairs if x["recovered"]),
                              "partner_opposite": sum(1 for x in pairs if x["partner_opposite"]),
                              "both": sum(1 for x in pairs if x["recovered"] and x["partner_opposite"]),
                              "share": _share(sum(1 for x in pairs if x["recovered"] and x["partner_opposite"]),
                                              len(pairs))},
            "items": per_item, "misses": misses})
    return {"n_items": len(items), "n_by_kind": {k: sum(1 for it in items if it.kind == k) for k in KINDS},
            "answers": {"answered": len(answered), "unanswered": len(items) - len(answered),
                        "reasked": sum(1 for a in answered if a.get("reasked")),
                        "label_path_first": sum(1 for a in answered if a.get("reasked")),
                        "label_path": sum(1 for a in answered if a.get("label_path"))},
            "parse": {"n_responses": len(responses), "n_parsed": n_parsed, "rate": _share(n_parsed, len(responses))},
            "batch": batch_dir.name, "seeds": seeds}


def _md(s: Any) -> str:
    return str("" if s is None else s).replace("|", "\\|").replace("\n", " ")


def _pct(x: Optional[float]) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def _frac(c: Mapping) -> str:
    return f"{c['recovered']} of {c['n']} ({_pct(c['share'])})"


def _reading(r: Mapping) -> str:
    if r.get("how") == "label":
        m = r.get("match") or {}
        return "label match" + (f" (former stem {m.get('old_stem')})" if m.get("match") == "renamed_from" else "")
    if r.get("stalled"):
        return f"stalled ({r['stalled']})"
    parts = []
    for who in ("sonnet", "opus"):
        x = r.get(who)
        if x:
            parts.append(f"{who.capitalize()} {x.get('value')} ({x.get('reason') or ''})")
    tail = f"verdict {r.get('verdict')}"
    if r.get("cosine") is not None:
        tail += f", cosine {r['cosine']:.2f}, rank {r.get('rank')}"
    return "; ".join(parts + [tail])


def report(batch_dir: Path, *, set_path: Path, answers_path: Path, responses_path: Optional[Path] = None,
           registry_path: Optional[Path] = None, candidates_dir: Optional[Path] = None, data_dir: Optional[Path] = None,
           report_dir: Optional[Path] = None, figures: Optional[Mapping] = None) -> str:
    """``report.md`` (module docstring, step 5): :func:`report_figures` in Markdown, every file it mentions a link
    relative to ``report_dir`` (default :data:`SET_DIR`, where the report is written)."""
    f = figures or report_figures(batch_dir, set_path=set_path, answers_path=answers_path,
                                  responses_path=responses_path, registry_path=registry_path,
                                  candidates_dir=candidates_dir)
    base = Path(report_dir or SET_DIR).absolute()
    data_dir = Path(data_dir or paths.DATA_DIR)
    trait_dir = data_dir / "traits" / "instructions"
    labels = {s: t.label for s, t in NV.load_trait_corpus(data_dir).items()} if trait_dir.exists() else {}
    batch_dir = Path(batch_dir)

    def rel(p: Path) -> str:
        r = os.path.relpath(Path(p).absolute(), base)
        return r if r.startswith("..") else f"./{r}"

    def link(p: Path, text: Optional[str] = None) -> str:
        return f"[{_md(text or Path(p).name)}]({rel(p)})"

    def T(stem: Optional[str]) -> str:  # noqa: N802 - a trait file
        return link(trait_dir / f"{stem}.json", labels.get(stem) or stem.replace("_", " ")) if stem else ""

    resp = Path(responses_path or Path(answers_path).parent / RESPONSES_NAME)
    plan = paths.REPO_ROOT / "reports" / "trait_gap_generation" / "coding_plan_13_generator_testing.md"
    a, pr = f["answers"], f["parse"]
    L = [f"# Paraphrase sanity set: the matcher's recall (`{_md(f['batch'])}`)", "",
         f"Plan 13 task 7 ({link(plan)}).  Each item is a corpus trait named in other words: Haiku 5.5 was given the "
         "trait's recorded paraphrase from the M2 calibration, never its name, and asked for a synonym label and a "
         "fresh definition (the pinned rubric "
         f"{link(paths.RUBRICS_DIR / 'paraphrase_synonym.md')}).  Each answer became a candidate in a scratch "
         "registry, every item's trait (and a pair pole's partner) was hidden, and the recovery harness scored the "
         "candidates against the corpus without them.  Terms:", "",
         "- **single** / **pair pole**: a trait that hides alone, or one pole of a recorded pair (the pair hides "
         "whole).",
         "- **concept recall**: items whose candidate the harness matched to the item's own hidden trait, by label or "
         "by the overlap call at the candidate's cut-off, over all items.  The target is over 90%; a miss is a "
         "matcher bug to file with its readings, not a finding about generators.",
         "- **kept** / **covered**: the reduced-corpus M3 run's decision on the candidate (`new` or `grey`, or "
         "turned away because a remaining trait covers it); **not decided**: the run left it out.",
         "- **label path**: the answer's label was the hidden trait's own name (separator-blind, or a former name), "
         "which the harness matches with no model call; such an item was asked once more with that word ruled out.",
         "- **pair-recovery**: a pair pole recovered and its hidden partner read `opposite` against the candidate.",
         "",
         f"Inputs: the items {link(set_path)}, the answers {link(answers_path)}, every response {link(resp)}, the "
         f"harness batch {link(batch_dir / 'recovery_report.md')} ({link(batch_dir / 'recovery_report.json')}).", "",
         "## Answers", "", "| | |", "|---|---|",
         f"| items | {f['n_items']} ({f['n_by_kind']['single']} single, {f['n_by_kind']['pair_pole']} pair poles) |",
         f"| answered | {a['answered']} ({a['unanswered']} without an answer) |",
         f"| parse rate | {pr['n_parsed']} of {pr['n_responses']} responses ({_pct(pr['rate'])}) |",
         f"| label path | {a['label_path_first']} answered with the trait's own name and were asked again; "
         f"{a['label_path']} still named it |", ""]
    seeds = f["seeds"]
    if not seeds:
        L += ["No seed directory in the harness batch yet.", ""]
        return "\n".join(L) + "\n"
    L += ["## Figures", "",
          "| seed | concept recall | by label | by the overlap call | recall without label matches | kept | covered | "
          "not decided | pair-recovery | matches |", "|---|---|---|---|---|---|---|---|---|---|"]
    for s in seeds:
        d, p = s["by_decision"], s["pair_recovery"]
        matches = batch_dir / ("seed" + str(s["seed"])) / "matches.jsonl"
        L.append(f"| {s['seed']} | {_frac(s['concept_recall'])} | {s['by_how']['label']} | {s['by_how']['overlap']} | "
                 f"{_frac(s['overlap_recall'])} | {_frac(d['kept'])} | {_frac(d['covered'])} | "
                 f"{_frac(d['not_decided'])} | {p['both']} of {p['n']} ({_pct(p['share'])}) | {link(matches)} |")
    L += ["", "Recall by kind and the pair poles in detail:", "",
          "| seed | singles | pair poles | pair poles recovered | partner read opposite | both |",
          "|---|---|---|---|---|---|"]
    for s in seeds:
        k, p = s["by_kind"], s["pair_recovery"]
        L.append(f"| {s['seed']} | {_frac(k['single'])} | {_frac(k['pair_pole'])} | "
                 f"{p['pole_recovered']} of {p['n']} | "
                 f"{p['partner_opposite']} of {p['n']} | {p['both']} of {p['n']} |")
    L.append("")
    for s in seeds:
        L += [f"## Misses, seed {s['seed']} ({len(s['misses'])})", "",
              f"The reduced-corpus M3 run is `{_md(s['reduced_run'])}` (decisions from its {s['decisions_from']}).", ""]
        if not s["misses"]:
            L += ["None.", ""]
            continue
        L += ["| item | hidden trait | answer | M3 decision | why | readings |", "|---|---|---|---|---|---|"]
        for x in s["misses"]:
            dec = x["decision"] or ""
            if x["covered_by"]:
                dec += f" (by {T(x['covered_by'])})"
            ans = f"{_md(x['label'])}: {_md(x['gloss'])}" if x["label"] else ""
            L.append(f"| {x['id']} | {T(x['hidden_stem'])} | {ans} | {dec} | {_md(x['why'])} | "
                     f"{'<br>'.join(_md(_reading(r)) for r in x['readings'])} |")
        L.append("")
        unpaired = [x for x in s["items"] if x["kind"] == "pair_pole" and x["recovered"] and not x["partner_opposite"]]
        if unpaired:
            L += [f"Pair poles recovered without their partner read `opposite` ({len(unpaired)}):", "",
                  "| item | pole | partner | answer | partner readings |", "|---|---|---|---|---|"]
            for x in unpaired:
                L.append(f"| {x['id']} | {T(x['hidden_stem'])} | {T(x['partner_stem'])} | {_md(x['label'])} | "
                         f"{'<br>'.join(_md(_reading(r)) for r in x['partner_readings']) or 'not read'} |")
            L.append("")
    return "\n".join(L) + "\n"


__all__ = ["MODEL", "MAX_TOKENS", "RUBRIC_NAME", "SET_DIR", "Item", "Answer", "RubricNotPinned", "load_rubric",
           "system_prompt", "paraphrase_source", "load_paraphrases", "load_alignment", "refusal", "build_set",
           "build_set_with_stats", "write_set", "read_set", "write_answers", "read_answers", "read_responses",
           "render_user", "prompt_sha256", "parse", "parse_with_reason", "answer_stem", "names_hidden", "run",
           "run_async", "estimate", "registry_keys", "to_scratch_registry", "hidden_file", "harness_command",
           "report_figures", "report"]
