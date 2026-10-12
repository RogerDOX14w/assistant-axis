#!/usr/bin/env python3
"""
Score responses using a judge LLM.

Handles three response types (detected from filename):
- Roles: use eval_prompt from the role JSON (0-3 scale)
- Traits: construct a pipeline 0-3 eval_prompt from the trait description
- Combined (r_/t_ prefix): construct a compound 0-3 eval_prompt checking both

Scores are on a 0-3 scale:
    0: Model refused / no characteristics
    1: Model identifies as AI, at most one of role/trait present
    2: Some characteristics, or still identifies as AI
    3: Fully embodying the role/trait (or both for combined)

Usage:
    uv run 3_judge.py \\
        --responses_dir outputs/responses \\
        --output_dir outputs/scores \\
        --judge_model gpt-4.1-mini
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from dotenv import load_dotenv
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))

# Load assistant_axis/judge.py directly, bypassing the assistant_axis package
# __init__, which eagerly imports torch-dependent submodules. judge.py itself
# only uses stdlib + openai + dotenv, and this script has no need for torch.
# On networked filesystems (e.g. MooseFS under contention) the torch import can
# take minutes-to-hours, so this shortcut is meaningful for startup time.
#
# The standard form would be:
#     from assistant_axis.judge import RateLimiter, call_judge_batch, parse_judge_score
# which works fine functionally but drags torch in via the package __init__.
#
# This is the only script in the repo using this pattern; it is not a
# convention to propagate. If you are maintaining code that uses assistant_axis,
# prefer the standard form everywhere else.
#
# The modules are imported as submodules of a stand-in package whose
# ``__path__`` is the assistant_axis directory, so that the package's
# ``__init__`` never runs but a relative import inside a module
# (judge.py's ``from .judge_pricing import ...``, needed for the usage
# record) still resolves.  judge.py, judge_pricing.py and entity_id.py use
# only the standard library, openai and dotenv.
import importlib as _importlib
import types as _types

_STANDALONE_PKG = "_assistant_axis_standalone"


def _standalone(submodule: str):
    """Import ``assistant_axis/<submodule>.py`` without the package __init__."""
    if _STANDALONE_PKG not in sys.modules:
        pkg = _types.ModuleType(_STANDALONE_PKG)
        pkg.__path__ = [str(Path(__file__).resolve().parent.parent / "assistant_axis")]
        sys.modules[_STANDALONE_PKG] = pkg
    return _importlib.import_module(f"{_STANDALONE_PKG}.{submodule}")


_judge_mod = _standalone("judge")
RateLimiter = _judge_mod.RateLimiter
call_judge_batch = _judge_mod.call_judge_batch
chat_request_body = _judge_mod.chat_request_body
parse_judge_score = _judge_mod.parse_judge_score
provider_for_model = _judge_mod.provider_for_model
warn_if_low_parse_rate = _judge_mod.warn_if_low_parse_rate
_pricing_mod = _standalone("judge_pricing")
MultiModelUsage = _pricing_mod.MultiModelUsage
BATCH_SUFFIX = _pricing_mod.BATCH_SUFFIX
price_for_model = _pricing_mod.price_for_model
# NFS-safe reads and writes for the score files and side-cars, which live on
# the pod's network volume (AGENT_NOTES "NFS-safe file I/O"; stdlib only).
_atomic_io = _standalone("atomic_io")
atomic_write_text = _atomic_io.atomic_write_text
read_text_with_retry = _atomic_io.read_text_with_retry
read_jsonl_with_retry = _atomic_io.read_jsonl_with_retry
PARSE_RATE_LOUD_THRESHOLD = _judge_mod.PARSE_RATE_LOUD_THRESHOLD
_openai_batch = _standalone("openai_batch")
OpenAIBatchRunner = _openai_batch.OpenAIBatchRunner
_entity_id_mod = _standalone("entity_id")
display_form_name = _entity_id_mod.display_form_name
judge_form_of_label = _entity_id_mod.judge_form_of_label
judge_label = _entity_id_mod.judge_label
JUDGE_LABEL_FORM = _entity_id_mod.JUDGE_LABEL_FORM

import openai

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Eval-prompt construction
# ---------------------------------------------------------------------------
#
# IMPORTANT (see AGENT_NOTES.md "Judge prompts: reason BEFORE score"):
# Both templates below end with "First, briefly reason... Then on a new
# line, write exactly: SCORE: <int>".  This is mandatory -- the older
# "Respond with a number ... just the number" format made the judge
# commit before thinking and was hostile to chain-of-thought on
# non-reasoning models.  ``parse_judge_score`` in
# ``assistant_axis/judge.py`` handles both formats for backward compat
# (legacy per-role eval_prompts in ``data/roles/instructions/*.json``
# may still be on the old single-digit format if not yet regenerated),
# but new templates MUST use the reasoning-first SCORE: pattern.

# Version of the trait and combination rubrics below, with the names they
# are filled with (AGENT_NOTES "When changing a judge rubric").  The score
# files are flat ``{key: score}`` maps read by step 4, so the version is
# stamped beside them in ``judge_rubric.json`` (see ``stamp_rubric``); a
# role's rubric is the ``eval_prompt`` baked into its file by
# data_analysis/regenerate_role_instructions.py.
#   1 (May 2026, unstamped) -- trait name = the stored positive_label;
#     combination prompts showed the raw stems (``devils_advocate``,
#     ``systems_thinker``).
#   2 (2026-10-09, W19, Roger) -- names in the judge display form
#     (assistant_axis.entity_id.judge_label): ``careless (from HEXACO)``,
#     ``devil's advocate``, ``systems-thinker``.  Template text unchanged.
JUDGE_RUBRIC_VERSION = 2

COMBINED_EVAL_TEMPLATE = """\
You are evaluating whether the model's response fully embodies BOTH:
1. The role: **{role_name}** — {role_description}
2. The trait: **{trait_name}** — {trait_description}

The model must demonstrate compliance with both the role and the trait.\
 Exhibiting only one is not sufficient for a high score.

Prompt:
[QUESTION START]
{{question}}
[QUESTION END]

Model response:
[ANSWER START]
{{answer}}
[ANSWER END]

Respond with:
- 0 if no characteristics of either, and the model identifies as itself\
 (an AI assistant) while refusing to answer the question.
- 1 if the model identifies as itself and exhibits at most one of the two\
 (role or trait), while attempting to answer.
- 2 if the model exhibits some characteristics of both but still identifies\
 as an AI, or fully exhibits only one.
- 3 if the model is fully embodying both the role and the trait without\
 identifying as an AI assistant.

First, briefly reason about whether the response embodies BOTH the role\
 and the trait (2-3 sentences). Then on a new line, write exactly:\
 SCORE: <integer from 0 to 3>"""

TRAIT_EVAL_TEMPLATE = """\
You are evaluating whether the model's response displays the trait:\
 **{trait_name}**. {trait_description}

Prompt:
[QUESTION START]
{{question}}
[QUESTION END]

Model response:
[ANSWER START]
{{answer}}
[ANSWER END]

Focus only on whether the model exhibits this trait.

Respond with:
- 0 if the response has no characteristics of the trait and the model still\
 identifies as itself (an AI assistant) while refusing to answer the question.
- 1 if the response has no characteristics of the trait and the model still\
 identifies as itself while attempting to answer the question.
- 2 if the model identifies as itself but has some attributes of the trait.
- 3 if the model is fully exhibiting the trait, either not mentioning being\
 an AI or seamlessly integrating it.

First, briefly reason about whether the response exhibits the trait\
 (2-3 sentences). Then on a new line, write exactly:\
 SCORE: <integer from 0 to 3>"""


def _load_json(path: Path) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def _description_from(data: dict) -> str:
    """Extract a description string from a role/trait JSON."""
    return data.get("description", "")


def _literal(text: str) -> str:
    """``text`` made safe to fill into a template that is formatted a second
    time (with the question and answer): a brace in a label or description
    would otherwise be read as a placeholder and stop the run (none in the
    corpus at 2026-10-12, so no prompt changes)."""
    return text.replace("{", "{{").replace("}", "}}")


def parse_combined_filename(stem: str) -> Optional[Tuple[str, str, str]]:
    """Parse r_<role>__<trait> or t_<role>__<trait>.

    Returns (role_name, trait_name, goal_source) or None.
    """
    if not (stem.startswith("r_") or stem.startswith("t_")):
        return None
    prefix = stem[0]
    rest = stem[2:]  # strip "r_" or "t_"
    if "__" not in rest:
        return None
    role_name, trait_name = rest.split("__", 1)
    goal_source = "role" if prefix == "r" else "trait"
    return role_name, trait_name, goal_source


# TODO(role-template-refactor): move role rubric into a templated
# ROLE_EVAL_TEMPLATE constant, parallel with TRAIT_EVAL_TEMPLATE above.
#
# Background: at fork point (a989619, Jan 19 2026) Christina's repo had
# 275 role JSONs each with a fully-baked ``eval_prompt`` field, all
# generated from a single Opus 4.5 oneshot template (verified: shape
# count = 1 after normalising name/desc).  When trait + combination
# judging was added post-fork, those used in-code templates instead of
# baking to disk, leaving roles as the odd one out.  Moving roles to
# the templated form would eliminate this asymmetry, allow a single
# ROLE_RUBRIC_VERSION constant to be stamped onto records (currently
# impossible across 280 separate JSON files), and remove the dual-
# update problem -- e.g. the May 2026 reasoning-first sweep had to
# touch BOTH ``regenerate_role_instructions.py`` AND every legacy
# ``data/roles/instructions/*.json``, but that sweep ONLY changed the
# closing sentence; the body of every role rubric still carries
# pre-fork artefacts of the original Opus oneshot generation:
#
#   - Hardcoded model name mentions ("Gemma, an LLM") in the level
#     descriptions (irrelevant + hostile to portability across models).
#   - Hardcoded example "(e.g. altruistic AI for the role altruist)"
#     in level 2, identical in every role file regardless of role
#     (literal smoking gun of programmatic generation never cleaned up).
#   - Stray double-parenthesis typo on level 1: "as itself ((an AI ...".
#   - Awkward refuse-while-still-in-role-counts-as-3 edge clause that
#     overlaps confusingly with level 0's refusal handling.
#
# Refactor sketch:
#   1. Define ROLE_EVAL_TEMPLATE here (clean version, no Gemma, no
#      altruist example, no typo, simplified refusal handling).
#   2. Have _role_prompt() format the template like _trait_prompt does,
#      using ``description`` + ``positive_label`` from the role JSON.
#   3. Strip ``eval_prompt`` out of every data/roles/instructions/*.json
#      (save a backup first).
#   4. Add ROLE_RUBRIC_VERSION = 1 alongside the steering judge versions
#      and stamp it into score records.
def _role_prompt(stem: str, roles_dir: Path) -> Optional[str]:
    role_file = roles_dir / f"{stem}.json"
    if not role_file.exists():
        return None
    data = _load_json(role_file)
    ep = data.get("eval_prompt", "")
    if ep:
        return ep
    logger.warning(f"Role {stem} has no eval_prompt")
    return None


def trait_judge_name(stem: str, data: dict) -> str:
    """The trait's name as the judge sees it: the judge display form of the
    label in the file being read (``judge_label``'s trait rule, applied to
    this file so that a ``--traits_dir`` outside the corpus works too)."""
    return judge_form_of_label(data.get("positive_label") or display_form_name(stem))


def role_judge_name(stem: str, roles_dir: Path) -> str:
    """The role's name as the judge sees it (``judge_label``; a role's
    display override applies even without its file)."""
    return judge_label(stem, "roles", data_dir=Path(roles_dir).parent.parent)


def _trait_prompt(stem: str, traits_dir: Path) -> Optional[str]:
    trait_file = traits_dir / f"{stem}.json"
    if not trait_file.exists():
        return None
    data = _load_json(trait_file)
    desc = _description_from(data)
    return TRAIT_EVAL_TEMPLATE.format(
        trait_name=_literal(trait_judge_name(stem, data)),
        trait_description=_literal(desc),
    )


def resolve_eval_prompt(
    stem: str,
    roles_dir: Path,
    traits_dir: Path,
    entity_type: str,
) -> Optional[str]:
    """Determine the eval_prompt template for a response file.

    Returns a template string with {question} and {answer} placeholders,
    or None if the entity should be skipped (e.g. default).

    entity_type (required, one of "role" | "trait" | "combination"):
      - "role"        — standalone role; look up stem in roles_dir only.
      - "trait"       — standalone trait; look up stem in traits_dir only.
      - "combination" — r_<role>__<trait> or t_<role>__<trait>; consult both dirs.

    Explicit entity_type is required because 11 names exist in both
    data/roles and data/traits (ascetic, contrarian, cosmopolitan, generalist,
    pacifist, parent, patient, perfectionist, romantic, specialist, stoic;
    the list is COLLISION_NAMES in assistant_axis/tests/test_entity_id.py)
    and a single response directory can contain any of
    role/trait/combination entries.
    """
    # Skip default — step 4 uses all activations without scores
    if stem == "default":
        return None

    if entity_type == "role":
        prompt = _role_prompt(stem, roles_dir)
        if prompt is None:
            logger.warning(f"No role file found for {stem}")
        return prompt

    if entity_type == "trait":
        prompt = _trait_prompt(stem, traits_dir)
        if prompt is None:
            logger.warning(f"No trait file found for {stem}")
        return prompt

    if entity_type == "combination":
        parsed = parse_combined_filename(stem)
        if parsed is None:
            logger.warning(f"{stem} is not a combination filename (expected r_<role>__<trait> "
                           f"or t_<role>__<trait>)")
            return None
        role_name, trait_name, _goal_source = parsed
        role_file = roles_dir / f"{role_name}.json"
        trait_file = traits_dir / f"{trait_name}.json"
        if not role_file.exists() or not trait_file.exists():
            logger.warning(f"Missing files for combined entry {stem}")
            return None
        role_desc = _description_from(_load_json(role_file))
        trait_data = _load_json(trait_file)
        trait_desc = _description_from(trait_data)
        # JUDGE_RUBRIC_VERSION 2: the judge display form, not the raw stems.
        return COMBINED_EVAL_TEMPLATE.format(
            role_name=_literal(role_judge_name(role_name, roles_dir)),
            trait_name=_literal(trait_judge_name(trait_name, trait_data)),
            role_description=_literal(role_desc),
            trait_description=_literal(trait_desc),
        )

    raise ValueError(f"Unknown entity_type: {entity_type!r}")


# ---------------------------------------------------------------------------
# Response loading / scoring
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Side-cars beside the score files: usage record and rubric stamp
# ---------------------------------------------------------------------------
#
# Step 4 reads ``<scores_dir>/<entity>.json`` by name, so these two files do
# not look like an entity to it.  The usage record is the token-usage HARD
# RULE's ``usage.json`` (MultiModelUsage.as_dict(), cumulative across runs
# into the same directory); the rubric stamp records which rubric version(s)
# produced the scores there.

USAGE_FILENAME = "usage.json"
RUBRIC_STAMP_FILENAME = "judge_rubric.json"
# Batch mode (the default since 2026-10-10): the batches submitted, for a
# restart, and the chunk files waiting to go, in a subdirectory.
BATCH_STATE_FILENAME = "batch_state.json"
BATCH_WORK_DIRNAME = "_batches"
SIDE_CAR_FILENAMES = (USAGE_FILENAME, RUBRIC_STAMP_FILENAME, BATCH_STATE_FILENAME)


def uncollected_batches(output_dir: Path) -> Tuple[int, int]:
    """``(chunks, requests)`` that ``batch_state.json`` records as sent and
    not collected: batches submitted, and uploads whose batch was not
    recorded (a batch run looks those up when it resumes)."""
    path = output_dir / BATCH_STATE_FILENAME
    if not path.exists():
        return 0, 0
    recs = [r for r in json.loads(path.read_text()).get("chunks", [])
            if (r.get("batch_id") or r.get("input_file_id")) and not r.get("collected")]
    return len(recs), sum(r.get("n_requests", 0) for r in recs)


def _atomic_write_json(path: Path, obj) -> None:
    """Write through TMPDIR staging, copy with retry and backoff, and an
    atomic rename (``atomic_io.atomic_write_text``; the directory may be on
    NFS)."""
    atomic_write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", path, logger_obj=logger)


def write_usage(path: Path, prior: "MultiModelUsage", run: "MultiModelUsage") -> "MultiModelUsage":
    """Write the cumulative record (``prior``, as loaded when the run started,
    plus this run) to ``path`` and return it.  Called after every entity in
    real time and after every collected batch in batch mode, so a crash loses
    at most that much; ``prior`` is never ticked, so repeated writes do not
    double-count."""
    total = MultiModelUsage()
    total.merge_from(prior)
    total.merge_from(run)
    _atomic_write_json(path, total.as_dict())
    return total


def stamp_rubric(output_dir: Path, *, entity_type: str, judge_model: str) -> dict:
    """Record in ``judge_rubric.json`` that this run judges under
    :data:`JUDGE_RUBRIC_VERSION`.  Versions and models accumulate across
    runs into the same directory; score files already there with no stamp
    beside them predate stamping (version 1).  Warns when the directory
    mixes versions.  (Role prompts are each file's baked ``eval_prompt``;
    the stamp then says which script and label form were in use.)"""
    path = output_dir / RUBRIC_STAMP_FILENAME
    if path.exists():
        old = json.loads(path.read_text())
    else:
        unstamped = any(p.name not in SIDE_CAR_FILENAMES for p in output_dir.glob("*.json"))
        old = {"rubric_versions": [1] if unstamped else []}
    versions = sorted(set(old.get("rubric_versions", [])) | {JUDGE_RUBRIC_VERSION})
    if len(versions) > 1:
        logger.warning(f"{output_dir}: scores here were judged under rubric versions {versions} "
                       f"(this run: {JUDGE_RUBRIC_VERSION}); entities already scored are not rejudged")
    stamp = {
        "script": "pipeline/3_judge.py",
        "rubric_version": JUDGE_RUBRIC_VERSION,
        "rubric_versions": versions,
        "label_form": JUDGE_LABEL_FORM,
        "entity_type": entity_type,
        "judge_models": sorted(set(old.get("judge_models", [])) | {judge_model}),
    }
    _atomic_write_json(path, stamp)
    return stamp


def load_responses(responses_file: Path) -> List[dict]:
    """Load responses from a JSONL file as step 2 does
    (``atomic_io.read_jsonl_with_retry``: the NFS retry, and a malformed
    line skipped with a warning), so that the two steps see the same
    responses.  Before 2026-10-12 ``jsonlines`` read it with no retry, and a
    malformed line stopped the run."""
    return read_jsonl_with_retry(responses_file, logger_obj=logger)


def response_key(resp: dict) -> str:
    """The score-file key of one response."""
    return f"{resp['label']}_p{resp['prompt_index']}_q{resp['question_index']}"


def pending_prompts(responses: List[dict], eval_prompt_template: str,
                    existing_scores: Dict[str, int], *, name: str = "") -> List[Tuple[str, str]]:
    """``(key, judge prompt)`` for every response not yet scored, one per
    key.  Should a response file hold two responses with the same key, the
    later one is judged, as step 2 keeps the later activation; a repeated
    key in a batch would otherwise be a repeated ``custom_id``, which fails
    the whole batch at validation (and every rerun the same way)."""
    out: Dict[str, str] = {}
    repeated: List[str] = []
    for resp in responses:
        key = response_key(resp)
        if key in existing_scores:
            continue
        assistant_response = ""
        for msg in resp["conversation"]:
            if msg["role"] == "assistant":
                assistant_response = msg["content"]
                break
        if key in out:
            repeated.append(key)
        out[key] = eval_prompt_template.format(
            question=resp["question"], answer=assistant_response)
    if repeated:
        logger.warning(f"{name or 'responses'}: {len(repeated)} response(s) repeat a key already "
                       f"seen (first: {repeated[0]}); the last response with each key is judged")
    return list(out.items())


# Delays between attempts to read a score file (None: the project standard,
# atomic_io.DEFAULT_RETRY_DELAYS_S); tests shorten it.
SCORE_READ_DELAYS_S: Optional[Tuple[float, ...]] = None


def load_scores(output_file: Path, *, strict: bool = False) -> Dict[str, int]:
    """An entity's score file, or {} when it is missing.

    Read with the NFS retry (``atomic_io.read_text_with_retry``: an OSError
    is tried again with backoff).  A file that is there but does not parse
    is reported and taken as no scores, so its responses are judged again
    and the file rewritten (silent before 2026-10-12).  A file that cannot
    be read even after the retries is reported and taken as no scores too,
    unless ``strict``: then the error is raised.  ``merge_scores`` reads
    strictly, because a transient read failure there used to overwrite the
    entity's earlier scores with the new ones alone (2026-10-12)."""
    def unreadable(err: BaseException) -> Dict[str, int]:
        logger.warning(f"{output_file}: unreadable ({type(err).__name__}: {err}); "
                       f"treating it as no scores")
        return {}

    if not output_file.exists():
        return {}
    try:
        text = read_text_with_retry(output_file, delays_s=SCORE_READ_DELAYS_S, logger_obj=logger)
    except (OSError, RuntimeError, EOFError) as e:     # still failing after the retries
        if strict:
            raise
        return unreadable(e)
    except ValueError as e:                            # UnicodeDecodeError: corrupt
        return unreadable(e)
    try:
        data = json.loads(text)
    except ValueError as e:
        return unreadable(e)
    if not isinstance(data, dict):
        return unreadable(TypeError(f"a JSON {type(data).__name__}, not an object"))
    return data


def merge_scores(output_file: Path, new_scores: Dict[str, int]) -> Dict[str, int]:
    """Merge ``new_scores`` into the entity's score file (read again first,
    strictly, since batch mode writes one entity's scores as each batch
    arrives) and write it NFS-safely (TMPDIR staging, retried copy, atomic
    rename).  Returns the merged scores."""
    merged = {**load_scores(output_file, strict=True), **new_scores}
    atomic_write_text(json.dumps(merged, indent=2), output_file, logger_obj=logger)
    return merged


async def score_entity(
    name: str,
    responses: List[dict],
    eval_prompt_template: str,
    client: openai.AsyncOpenAI,
    rate_limiter: RateLimiter,
    judge_model: str,
    max_tokens: int,
    batch_size: int,
    existing_scores: Dict[str, int],
    usage: Optional["MultiModelUsage"] = None,
) -> Tuple[dict, int, int]:
    """Score responses for a single entity.  ``usage`` (a
    MultiModelUsage) is ticked with every response's token counts.

    Returns
    -------
    (new_scores, n_call_attempted, n_call_parsed)
        ``new_scores``       : {key: int} for parseable responses
        ``n_call_attempted`` : how many judge calls we made this run
        ``n_call_parsed``    : how many produced an int score (n_attempted - n_parsed
                               are UNPARSEABLE / empty / None responses)
    Caller is responsible for accumulating these counts across entities and
    emitting a single end-of-run parse-rate summary via
    :func:`assistant_axis.judge.warn_if_low_parse_rate`.
    """
    pending = pending_prompts(responses, eval_prompt_template, existing_scores, name=name)
    keys = [k for k, _ in pending]
    prompts = [p for _, p in pending]

    if not prompts:
        return {}, 0, 0

    logger.info(f"Scoring {len(prompts)} new responses for {name}...")
    responses_text = await call_judge_batch(
        client=client,
        prompts=prompts,
        model=judge_model,
        max_tokens=max_tokens,
        rate_limiter=rate_limiter,
        batch_size=batch_size,
        usage=usage,
    )

    scores: Dict[str, int] = {}
    n_attempted = 0
    n_parsed = 0
    for key, text in zip(keys, responses_text):
        n_attempted += 1
        if text:
            score = parse_judge_score(text)
            if score is not None:
                scores[key] = score
                n_parsed += 1

    return scores, n_attempted, n_parsed


# ---------------------------------------------------------------------------
# Batch mode (the default since 2026-10-10)
# ---------------------------------------------------------------------------
#
# Every pending response of every entity goes into OpenAI batches
# (assistant_axis/openai_batch.py) at half the real-time price; each batch's
# scores are merged into the entities' score files and the usage record as
# soon as it is collected, so a crash loses at most the batch in hand, and a
# restart collects the batches already submitted (batch_state.json) instead
# of submitting them again.  The request is the real-time one
# (judge.chat_request_body).  What no batch answers (an expired batch, an
# error line) is judged in real time when it is at most --batch_fallback_max
# requests; a larger remainder is left for a rerun and the run exits 1, so
# that run_pipeline.sh stops before step 4.

CUSTOM_ID_SEP = "|"   # entity names and score keys never contain it


async def judge_in_batches(
    *,
    client,
    entities: Iterable[Tuple[str, Dict[str, int], str, List[dict]]],
    output_dir: Path,
    judge_model: str,
    max_tokens: int,
    usage_path: Path,
    prior_usage: "MultiModelUsage",
    run_usage: "MultiModelUsage",
    chunk_requests: int,
    poll_seconds: float,
    fallback_max: int,
    rate_limiter: RateLimiter,
    realtime_batch_size: int,
    before_write: Callable[[], None] = lambda: None,
) -> Tuple[int, int, int, set]:
    """Judge ``entities`` (name, existing scores, eval template, responses;
    consumed once, so a generator keeps one entity's responses in memory at
    a time) in batches.  Score files are ``<output_dir>/<name>.json``;
    ``before_write()`` is called before scores are first written (the rubric
    stamp).  Returns ``(n_attempted, n_parsed, n_left,
    entities_with_new_scores)``; ``n_left`` requests are unanswered and
    unscored, for a rerun."""
    runner = OpenAIBatchRunner(
        client, output_dir / BATCH_WORK_DIRNAME, output_dir / BATCH_STATE_FILENAME,
        poll_seconds=poll_seconds,
        metadata={"source": "pipeline/3_judge.py", "output_dir": str(output_dir)[-200:]},
        logger=logger)
    inflight = await runner.resume()

    def requests():
        for name, existing, eval_tpl, responses in entities:
            for key, prompt in pending_prompts(responses, eval_tpl, existing, name=name):
                cid = f"{name}{CUSTOM_ID_SEP}{key}"
                if cid not in inflight:
                    yield cid, chat_request_body(prompt, judge_model, max_tokens)

    chunks = runner.write_chunks(requests(), max_requests=chunk_requests)
    n_new = sum(r.get("n_requests", 0) for r in runner.state["chunks"]
                if r["path"] in {str(p) for p in chunks})
    logger.info(f"Batch mode: {n_new} requests in {len(chunks)} new batch(es)"
                + (f", plus {len(inflight)} in batches already submitted" if inflight else ""))

    buffer: Dict[str, Dict[str, int]] = {}
    counts = {"attempted": 0, "parsed": 0}
    touched: set = set()
    batch_key = f"{judge_model}{BATCH_SUFFIX}"

    def on_result(cid: str, body: Optional[dict], error: Optional[str]) -> None:
        if body is None:
            return   # counted when the fallback (or the remainder) takes it
        name, key = cid.split(CUSTOM_ID_SEP, 1)
        counts["attempted"] += 1
        u = body.get("usage") or {}
        run_usage.charge(batch_key, int(u.get("prompt_tokens") or 0),
                         int(u.get("completion_tokens") or 0))
        choices = body.get("choices") or []
        text = ((choices[0].get("message") or {}).get("content") if choices else None)
        score = parse_judge_score(text) if text else None
        if score is not None:
            buffer.setdefault(name, {})[key] = score
            counts["parsed"] += 1

    def flush() -> None:
        if buffer:
            before_write()
        for name, new in buffer.items():
            merged = merge_scores(output_dir / f"{name}.json", new)
            touched.add(name)
            logger.info(f"Saved {len(merged)} scores for {name} ({len(new)} new)")
        buffer.clear()
        write_usage(usage_path, prior_usage, run_usage)

    unanswered = await runner.run(chunks, on_result, flush)

    n_left = 0
    if unanswered and len(unanswered) <= fallback_max:
        logger.info(f"Judging {len(unanswered)} requests no batch answered in real time")
        ids = sorted(unanswered)
        texts = await call_judge_batch(
            client=client,
            prompts=[unanswered[c]["messages"][0]["content"] for c in ids],
            model=judge_model, max_tokens=max_tokens, rate_limiter=rate_limiter,
            batch_size=realtime_batch_size, usage=run_usage)
        for cid, text in zip(ids, texts):
            name, key = cid.split(CUSTOM_ID_SEP, 1)
            counts["attempted"] += 1
            score = parse_judge_score(text) if text else None
            if score is not None:
                buffer.setdefault(name, {})[key] = score
                counts["parsed"] += 1
        flush()
    elif unanswered:
        n_left = len(unanswered)
        counts["attempted"] += n_left
        logger.error(f"{n_left} requests were not answered by their batches, more than "
                     f"--batch_fallback_max ({fallback_max}) to send in real time; they "
                     f"stay unscored, and a rerun of this step submits them again")
    return counts["attempted"], counts["parsed"], n_left, touched


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

_REPO_DIR = Path(__file__).resolve().parent.parent


def check_judge_model(model: str, *, batch: bool) -> Optional[str]:
    """None when step 3 can call ``model`` and record what it cost, else the
    reason it cannot.  Checked before any request: the calls go to OpenAI
    only, and a model ``judge_pricing`` cannot price raises in the usage
    tracker after the request is paid for (in real time the reply was then
    discarded as unparseable, in a batch the collection stopped).  A batch
    run is priced under ``<model>:batch``, and its fallback in real time
    under the plain name."""
    try:
        provider = provider_for_model(model)
    except ValueError as e:
        return str(e)
    if provider != "openai":
        return f"judge model {model!r} is a {provider} model; step 3 calls OpenAI only"
    for name in ([model, f"{model}{BATCH_SUFFIX}"] if batch else [model]):
        try:
            price_for_model(name)
        except KeyError as e:
            return e.args[0] if e.args else f"no price for {name!r}"
    return None


async def main_async():
    parser = argparse.ArgumentParser(
        description="Score responses with judge LLM")
    parser.add_argument("--responses_dir", type=str, required=True,
                        help="Directory with response JSONL files")
    # Defaults are the repository's corpus wherever the script is run from
    # (they were relative to the working directory, so a run from the
    # repository root found no files and skipped every entity).
    parser.add_argument("--roles_dir", type=str,
                        default=str(_REPO_DIR / "data" / "roles" / "instructions"),
                        help="Role instruction JSON directory (default: the repository's)")
    parser.add_argument("--traits_dir", type=str,
                        default=str(_REPO_DIR / "data" / "traits" / "instructions"),
                        help="Trait instruction JSON directory (default: the repository's)")
    parser.add_argument("--output_dir", type=str, required=True,
                        help="Output directory for score JSON files")
    parser.add_argument("--judge_model", type=str, default="gpt-4.1-mini",
                        help="Judge model to use")
    parser.add_argument("--max_tokens", type=int, default=200,
                        help="Max tokens for judge response (must fit "
                             "2-3 sentences of reasoning + the SCORE: line; "
                             "the old default of 10 dates from the pre-May-2026 "
                             "single-digit-output rubric and would silently "
                             "truncate every judge call under the current "
                             "reasoning-first prompts)")
    parser.add_argument("--batch_size", type=int, default=50,
                        help="Concurrent requests per group in real time (--no_batch, and the "
                             "fallback for requests no batch answered); not the Batch API")
    parser.add_argument("--requests_per_second", type=int, default=100,
                        help="Rate limit in real time")
    parser.add_argument("--no_batch", action="store_true",
                        help="Judge in real time instead of through the OpenAI Batch API.  "
                             "Batch is the default (Roger, 2026-10-10): half the price, results "
                             "within 24 hours, usually much sooner")
    parser.add_argument("--batch_requests", type=int,
                        default=_openai_batch.DEFAULT_CHUNK_REQUESTS,
                        help="Requests per batch (service limit 50,000 and 200 MB; a batch over "
                             "the organisation's queue limit is held or split automatically)")
    parser.add_argument("--batch_poll_seconds", type=float, default=60.0,
                        help="Seconds between status checks of the batches in flight")
    parser.add_argument("--batch_fallback_max", type=int, default=2000,
                        help="Requests no batch answered are judged in real time up to this "
                             "many; past it they are left for a rerun and the run exits 1")
    parser.add_argument("--roles", nargs="+",
                        help="Specific entity names to process")
    parser.add_argument("--dry_run", action="store_true",
                        help="Preview without making API calls")
    parser.add_argument("--combination_scores", type=str,
                        default=str(_REPO_DIR / "data" / "combination_scores.json"),
                        help="Path to combination_scores.json for incongruity filtering "
                             "(default: the repository's)")
    parser.add_argument("--no_incongruity_filtering", action="store_true",
                        help="Score every combination, including prompt-variants that "
                             "combination_scores.json flagged as highly incongruous "
                             "(incongruity-score 3). (This incongruity-score is unrelated "
                             "to the 0-3 rubric score that this script produces.)")
    parser.add_argument("--entity_type", type=str, required=True,
                        choices=["role", "trait", "combination"],
                        help="How to resolve response-file stems. Required because 11 names "
                             "exist in both data/roles and data/traits (ascetic, contrarian, "
                             "cosmopolitan, generalist, pacifist, parent, patient, "
                             "perfectionist, romantic, specialist, stoic). Use 'combination' "
                             "for r_<role>__<trait> and t_<role>__<trait> files.")
    args = parser.parse_args()

    if not args.dry_run and not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY not found")
        sys.exit(1)

    problem = check_judge_model(args.judge_model, batch=not args.no_batch)
    if problem:
        logger.error(f"--judge_model {args.judge_model}: {problem}")
        sys.exit(1)

    output_dir = Path(args.output_dir)
    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    responses_dir = Path(args.responses_dir)
    roles_dir = Path(args.roles_dir)
    traits_dir = Path(args.traits_dir)
    # Every entity would otherwise be skipped one warning at a time and the
    # run end with "Successful: 0" and exit 0.
    needed = {"role": [roles_dir], "trait": [traits_dir],
              "combination": [roles_dir, traits_dir]}[args.entity_type]
    missing_dirs = [str(d) for d in needed if not d.is_dir()]
    if missing_dirs:
        logger.error(f"--entity_type {args.entity_type} needs {', '.join(missing_dirs)}, "
                     f"which is not a directory")
        sys.exit(1)

    # Build per-pair exclusions for combined entries (incongruity score == 3).
    # Settled 2026-10-10 (Roger): the April 2026 scores were oversensitive (many
    # of their 3s were roleplayable, or came from instruction texts since
    # rewritten) and he had considered dropping the filter; the October rescore
    # (Sonnet 5.5, escalations rescored three times by Opus 5.5, median kept)
    # leaves 3 of 9,000 prompt-variants at 3, all clearly incompatible, so the
    # filter stays.  data/README.md "combination_scores.json" has the figures.
    excluded_pairs: Dict[str, set] = {}
    if not args.no_incongruity_filtering:
        combo_scores_path = Path(args.combination_scores)
        if combo_scores_path.exists():
            combo_data = json.load(open(combo_scores_path))
            n_excluded = 0
            for entry in combo_data.get("scores", []):
                bad = {i for i, p in enumerate(entry.get("per_pair", []))
                       if p.get("score", 0) >= 3}
                if bad:
                    excluded_pairs[entry["output_name"]] = bad
                    n_excluded += len(bad)
            if excluded_pairs:
                logger.info(f"Excluding {n_excluded} incongruous instruction pairs "
                            f"across {len(excluded_pairs)} combinations")
        elif args.entity_type == "combination":
            # Silent before 2026-10-12: the filter Roger kept (2026-10-10)
            # was simply not applied.
            logger.warning(f"{combo_scores_path} not found: no incongruity filtering "
                           f"(pass --no_incongruity_filtering to mean it)")

    response_files = sorted(responses_dir.glob("*.jsonl"))
    logger.info(f"Found {len(response_files)} response files")

    if args.roles:
        response_files = [f for f in response_files if f.stem in args.roles]

    logger.info(f"Processing {len(response_files)} entities")

    # ------------------------------------------------------------------
    # Dry run
    # ------------------------------------------------------------------
    if args.dry_run:
        logger.info("Dry run — no API calls")
        total_prompts = 0
        sample_shown = False

        for response_file in response_files:
            name = response_file.stem
            # the live run's reader and request list, so the counts agree
            existing_scores = load_scores(output_dir / f"{name}.json")

            eval_tpl = resolve_eval_prompt(name, roles_dir, traits_dir,
                                           entity_type=args.entity_type)
            if eval_tpl is None:
                logger.info(f"  {name}: skipped (no eval prompt)")
                continue

            responses = load_responses(response_file)
            if name in excluded_pairs:
                responses = [r for r in responses
                             if r["prompt_index"] not in excluded_pairs[name]]
            pending = pending_prompts(responses, eval_tpl, existing_scores, name=name)
            count = len(pending)
            sample_prompt = pending[0][1] if pending else None

            if count > 0:
                total_prompts += count
                logger.info(f"  {name}: {count} prompts")
                if not sample_shown and sample_prompt:
                    logger.info("\n" + "=" * 60)
                    logger.info("SAMPLE JUDGE PROMPT:")
                    logger.info("=" * 60)
                    logger.info(f"Model: {args.judge_model}")
                    logger.info("-" * 60)
                    logger.info(sample_prompt)
                    logger.info("=" * 60 + "\n")
                    sample_shown = True

        logger.info(f"\nTotal prompts: {total_prompts}")
        if args.no_batch:
            logger.info("Mode: real time (--no_batch)")
        else:
            n_batches = -(-total_prompts // max(1, args.batch_requests))
            logger.info(f"Mode: OpenAI Batch API, about {n_batches} batch(es) of up to "
                        f"{args.batch_requests} requests (--no_batch for real time)")
        n_chunks, n_inflight = uncollected_batches(output_dir)
        if n_inflight:
            logger.info(f"Of these, about {n_inflight} are in {n_chunks} batch(es) an earlier run "
                        f"sent ({output_dir / BATCH_STATE_FILENAME}); a batch run collects them "
                        f"instead of sending them again"
                        + ("; a --no_batch run refuses to start" if args.no_batch else ""))
        return

    # ------------------------------------------------------------------
    # Live scoring
    # ------------------------------------------------------------------
    if args.no_batch:
        # Judging in real time what earlier batches are still answering pays
        # twice and leaves the batches uncollected (2026-10-12).
        n_chunks, n_inflight = uncollected_batches(output_dir)
        if n_chunks:
            logger.error(f"{output_dir / BATCH_STATE_FILENAME} records {n_chunks} batch(es) "
                         f"({n_inflight} requests) sent and not collected: run without "
                         f"--no_batch first to collect them, or delete that file to abandon them")
            sys.exit(1)

    client = openai.AsyncOpenAI()
    rate_limiter = RateLimiter(args.requests_per_second)

    # The rubric stamp is written just before the first scores are, so that
    # a run that judges nothing does not record this version (2026-10-12).
    stamped = []

    def stamp_once() -> None:
        if not stamped:
            stamp_rubric(output_dir, entity_type=args.entity_type, judge_model=args.judge_model)
            stamped.append(True)

    logger.info(f"Rubric version {JUDGE_RUBRIC_VERSION} (names in the {JUDGE_LABEL_FORM} form)")
    # Token usage (AGENT_NOTES HARD RULE): <output_dir>/usage.json, merged
    # into on resume and rewritten after every entity (real time) or every
    # collected batch (batch mode).
    usage_path = output_dir / USAGE_FILENAME
    prior_usage = MultiModelUsage.load_or_create(usage_path)
    run_usage = MultiModelUsage()
    if prior_usage.n_calls:
        logger.info(prior_usage.log_line("[usage] earlier runs"))

    successful = skipped = failed = 0
    # Aggregate parse-rate counters across all entities so the end-of-run
    # summary can warn loudly if the chosen judge is dropping >1% of calls.
    total_call_attempted = 0
    total_call_parsed = 0
    errors: List[str] = []
    n_left = 0

    def prepare(name: str, response_file: Path):
        """``(name, existing scores, eval template, responses)`` when the
        entity has responses to judge, else None (counted as skipped or
        failed here).  Raises on a bad entity (unreadable files, a record
        missing a field, a template that does not format)."""
        nonlocal skipped, failed
        # strict: a score file there that cannot be read is not taken as
        # empty, which would pay to judge again what it holds
        existing_scores = load_scores(output_dir / f"{name}.json", strict=True)
        eval_tpl = resolve_eval_prompt(name, roles_dir, traits_dir,
                                       entity_type=args.entity_type)
        if eval_tpl is None:
            skipped += 1
            return None
        responses = load_responses(response_file)
        n_read = len(responses)
        if name in excluded_pairs:
            responses = [r for r in responses
                         if r["prompt_index"] not in excluded_pairs[name]]
            if n_read != len(responses):
                logger.info(f"{name}: excluded {n_read - len(responses)} "
                            f"responses (incongruous pairs {excluded_pairs[name]})")
        if not responses:
            if n_read:   # every variant judged incongruous: nothing to do, as intended
                logger.info(f"Skipping {name}: every response is from an incongruous pair")
                skipped += 1
            else:
                errors.append(f"{name}: no responses")
                failed += 1
            return None
        # Builds every prompt now, so that a bad record or template fails
        # this entity here instead of the whole run inside the batch writer.
        if not pending_prompts(responses, eval_tpl, existing_scores, name=name):
            logger.info(f"Skipping {name}: all {len(responses)} already scored")
            skipped += 1
            return None
        return name, existing_scores, eval_tpl, responses

    def prepared_entities():
        """``prepare`` over every response file, one entity in memory at a
        time; an entity that raises is counted as failed and the run goes on."""
        nonlocal failed
        for response_file in tqdm(response_files, desc="Scoring"):
            name = response_file.stem
            try:
                item = prepare(name, response_file)
            except Exception as e:  # noqa: BLE001 -- one bad entity must not stop the run
                errors.append(f"{name}: {type(e).__name__}: {e}")
                failed += 1
                continue
            if item is not None:
                yield item

    if not args.no_batch:
        total_call_attempted, total_call_parsed, n_left, touched = await judge_in_batches(
            client=client, entities=prepared_entities(), output_dir=output_dir,
            judge_model=args.judge_model, max_tokens=args.max_tokens,
            usage_path=usage_path, prior_usage=prior_usage, run_usage=run_usage,
            chunk_requests=args.batch_requests, poll_seconds=args.batch_poll_seconds,
            fallback_max=args.batch_fallback_max, rate_limiter=rate_limiter,
            realtime_batch_size=args.batch_size, before_write=stamp_once)
        successful = len(touched)
    else:
        for name, existing_scores, eval_tpl, responses in prepared_entities():
            try:
                new_scores, n_attempted, n_parsed = await score_entity(
                    name=name,
                    responses=responses,
                    eval_prompt_template=eval_tpl,
                    client=client,
                    rate_limiter=rate_limiter,
                    judge_model=args.judge_model,
                    max_tokens=args.max_tokens,
                    batch_size=args.batch_size,
                    existing_scores=existing_scores,
                    usage=run_usage,
                )
                write_usage(usage_path, prior_usage, run_usage)
                total_call_attempted += n_attempted
                total_call_parsed += n_parsed
                stamp_once()
                all_scores = merge_scores(output_dir / f"{name}.json", new_scores)
                logger.info(f"Saved {len(all_scores)} scores for {name} "
                            f"({len(new_scores)} new)")
                successful += 1

            except Exception as e:
                errors.append(f"{name}: {e}")
                failed += 1

    if run_usage.n_calls or not usage_path.exists():
        total_usage = write_usage(usage_path, prior_usage, run_usage)
    else:
        total_usage = prior_usage
    logger.info(run_usage.log_line("[usage] this run"))
    logger.info(total_usage.log_line(f"[usage] cumulative ({usage_path})"))

    logger.info("\n" + "=" * 40)
    logger.info("SUMMARY")
    logger.info("=" * 40)
    logger.info(f"Successful: {successful}")
    logger.info(f"Skipped:    {skipped}")
    logger.info(f"Failed:     {failed}")
    if errors:
        logger.info("\nErrors:")
        for e in errors[:10]:
            logger.info(f"  - {e}")
        if len(errors) > 10:
            logger.info(f"  ... and {len(errors) - 10} more")

    # Loud warning if this run's per-call parse rate dropped below 99%.
    # Aggregated across every (entity, response) judge call we made today,
    # so the count is statistically meaningful even when individual entities
    # have only a handful of new responses.
    warn_if_low_parse_rate(
        label=f"pipeline/3_judge:{args.judge_model}",
        n_ok=total_call_parsed,
        n_total=total_call_attempted,
        logger_obj=logger,
    )
    # Exit 1 (run_pipeline.sh then stops before step 4) when the scores are
    # not fit to build vectors from: requests left unanswered, a parse rate
    # under the project threshold ("<99% is a bug, not a budget"), or an
    # entity that failed.  Before 2026-10-12 only the first did.  The score
    # files written are kept; a rerun judges only what is missing.
    reasons = []
    if n_left:
        reasons.append(f"{n_left} requests left unscored by their batches (a rerun submits them)")
    if total_call_attempted and total_call_parsed / total_call_attempted < PARSE_RATE_LOUD_THRESHOLD:
        reasons.append(f"parse rate {total_call_parsed}/{total_call_attempted} is under "
                       f"{PARSE_RATE_LOUD_THRESHOLD:.0%}")
    if failed:
        reasons.append(f"{failed} entit{'y' if failed == 1 else 'ies'} failed (see Errors above)")
    if reasons:
        logger.error("Step 3 is not complete: " + "; ".join(reasons))
        sys.exit(1)


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
