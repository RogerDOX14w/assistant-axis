#!/usr/bin/env python3
"""
Score responses using a judge LLM.

Handles three response types (--entity_type):
- Roles: a 0-3 eval_prompt from the role's name and description
- Traits: a 0-3 eval_prompt from the trait's label and description
- Combined (r_/t_ prefix): a compound 0-3 eval_prompt checking both

The rubrics are versioned (--prompt_version; assistant_axis/judge_rubrics.py):
0, the original number-only rubrics; 3, the current ones (the default); 4,
the next version, a draft; 5, version 4 and a clause for helpful professional
roles, a draft for comparison on the October extraction.

Scores are on a 0-3 scale:
    0: Model refused / no characteristics
    1: Model identifies as AI, at most one of role/trait present
    2: Some characteristics, or still identifies as AI
    3: Fully embodying the role/trait (or both for combined)

Usage:
    uv run 3_judge.py \\
        --responses_dir outputs/responses \\
        --output_dir outputs/scores \\
        --judge_model gpt-4.1-mini \\
        --entity_type role [--prompt_version 4]
"""

import argparse
import asyncio
import hashlib
import json
import logging
import os
import re
import socket
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from dotenv import load_dotenv
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))

# Plain imports.  Until 2026-10-12 these modules were loaded through a
# stand-in package so that the package __init__, which then imported torch,
# matplotlib and sklearn eagerly, never ran (minutes on the pod's network
# volume: the recorded slow start of this step).  The __init__ is lazy since
# then (PEP 562; review P1 D5, walk-through P8.3), and none of these modules
# imports torch; pipeline/tests/test_3_judge.py checks that loading this
# script still imports no torch.
import assistant_axis.atomic_io as _atomic_io
import assistant_axis.judge as _judge_mod
import assistant_axis.judge_pricing as _pricing_mod
import assistant_axis.openai_batch as _openai_batch
from assistant_axis.atomic_io import (  # NFS-safe; AGENT_NOTES "NFS-safe file I/O"
    atomic_write_text, read_jsonl_with_retry, read_text_with_retry,
)
from assistant_axis.entity_id import (
    JUDGE_LABEL_FORM, display_form_name, judge_form_of_label, judge_label,
)
from assistant_axis.anthropic_batch import AnthropicBatchRunner
from assistant_axis.judge import (
    PARSE_RATE_LOUD_THRESHOLD, JudgeRequestError, RateLimiter, anthropic_reply,
    anthropic_request_params, call_judge_batch, chat_request_body, parse_judge_score,
    provider_for_model, warn_if_low_parse_rate,
)
from assistant_axis.judge_pricing import BATCH_SUFFIX, MultiModelUsage, price_for_model
from assistant_axis.judge_rubrics import (
    DEFAULT_PROMPT_VERSION, MIXABLE_VERSIONS, PROMPT_VERSIONS, PromptVersion, first_integer_score,
    get_version,
)
from assistant_axis.openai_batch import OpenAIBatchRunner

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
# The rubrics are versioned in assistant_axis/judge_rubrics.py, and
# --prompt_version picks one (Roger, 2026-10-23: so that steps 3 to 5 can be
# rerun under another rubric on the same responses and activations).  The
# version numbers continue the rubric versions recorded beside the scores in
# ``judge_rubric.json`` (AGENT_NOTES "When changing a judge rubric"; the score
# files are flat ``{key: score}`` maps read by step 4, so the version is
# stamped beside them, see ``stamp_rubric``):
#   0 -- the original number-only rubrics (Christina's role rubric at the
#     fork; the April 2026 trait and combination rubrics), read as the first
#     integer in the reply, --max_tokens 10.  Runnable since 2026-10-23.
#   1 (May 2026, unstamped) -- reason-first closing line; trait name = the
#     stored positive_label; combination prompts showed the raw stems
#     (``devils_advocate``, ``systems_thinker``).  Not runnable.
#   2 (2026-10-09, W19, Roger) -- names in the judge display form
#     (assistant_axis.entity_id.judge_label): ``careless (from HEXACO)``,
#     ``devil's advocate``, ``systems-thinker``.  Template text unchanged.
#     Not runnable.
#   3 (2026-10-12, walk-through P4 / D5; review P3 D1) -- how a reply is
#     read: exactly one ``SCORE: <int>`` marker is the answer
#     (parse_judge_score(require_marker=True)); a reply with none or several,
#     or cut at max_tokens (finish_reason "length"), is unparseable, never a
#     digit of its reasoning.  Prompt text unchanged.  The default.
#   4 (draft, 2026-10-23) -- version 3 with the arms of the role rubric
#     experiment (reports/pipeline/role_rubric_experiment/) that Roger
#     approves; so far A1, and for altruist only the level-2 example
#     "philanthropic AI for the role philanthropist".
#   5 (draft, 2026-10-23) -- version 4 and a clause for helpful, educated
#     professional roles, kept separate for comparison on the October
#     extraction's activations (Roger).
# Every version renders a role's rubric from its template, the role's judge
# display name and its description; until 2026-10-23 step 3 read the
# ``eval_prompt`` baked into the role file, which a test pins equal to the
# version 3 rendering for every role.  Versions 3 and 4 end with "First,
# briefly reason... Then on a new line, write exactly: SCORE: <int>"
# (AGENT_NOTES.md "Judge prompts: reason BEFORE score"); version 0 is the
# number-only anti-pattern, kept to reproduce the original judging, never as
# a model for a new rubric.
JUDGE_RUBRIC_VERSION = DEFAULT_PROMPT_VERSION

# Version 3's templates under their old names.
COMBINED_EVAL_TEMPLATE = PROMPT_VERSIONS[3].combination
TRAIT_EVAL_TEMPLATE = PROMPT_VERSIONS[3].trait


# How step 3 reads a reply (its prompt version's reply format), and why a
# reply was not scored, counted for the end-of-run summary.
_MARKER_RE = re.compile(r"SCORE\s*:\s*(\d+)", re.IGNORECASE)
REPLY_PROBLEMS: Counter = Counter()


def score_reply(text: Optional[str], finish_reason: Optional[str] = None, *,
                reply_format: str = "score_marker") -> Optional[int]:
    """The score of one judge reply, or None (unparseable), counting the
    reason in :data:`REPLY_PROBLEMS`: ``truncated`` (``finish_reason`` is
    ``"length"``: cut at ``--max_tokens``), ``no_reply`` (no text: a failed
    call, a content-flagged prompt), ``no_marker``, ``several_markers``,
    ``out_of_range``.

    ``reply_format`` ``"first_integer"`` (prompt version 0) reads the reply
    as the fork did (``judge_rubrics.first_integer_score``): a reply cut at
    ``max_tokens`` is read like any other, and the reasons are ``no_reply``,
    ``no_integer`` and ``out_of_range``."""
    if reply_format == "first_integer":
        if not text:
            REPLY_PROBLEMS["no_reply"] += 1
            return None
        score = first_integer_score(text)
        if score is None:
            REPLY_PROBLEMS["out_of_range" if re.search(r"\b\d+\b", text) else "no_integer"] += 1
        return score
    if finish_reason == "length":
        REPLY_PROBLEMS["truncated"] += 1
        return None
    if not text:
        REPLY_PROBLEMS["no_reply"] += 1
        return None
    score = parse_judge_score(text, require_marker=True)
    if score is None:
        n = len(_MARKER_RE.findall(text))
        REPLY_PROBLEMS["no_marker" if n == 0 else "several_markers" if n > 1
                       else "out_of_range"] += 1
    return score


def combination_pairs_sha256(role: str, trait: str, roles_dir: Path, traits_dir: Path) -> str:
    """The ``pairs_sha256`` that data_analysis/score_combinations.py records
    for a combination (``pairs_sha256(_make_combo(...))``, computed the same
    way: the role's and the trait's judge labels and the index-matched
    ``pos`` instruction pairs, sha256, first 16 hex digits), from the
    instruction files as they are now.  A test pins the two together."""
    role_data = _load_json(Path(roles_dir) / f"{role}.json")
    trait_data = _load_json(Path(traits_dir) / f"{trait}.json")
    ri, ti = role_data.get("instruction", []), trait_data.get("instruction", [])
    pairs = [{"role_instruction": ri[i].get("pos", ""), "trait_instruction": ti[i].get("pos", "")}
             for i in range(min(len(ri), len(ti)))]
    blob = json.dumps([judge_label(role, "roles"), trait_judge_name(trait, trait_data), pairs],
                      sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def check_pairs_sha256(stems: Iterable[str], stored: Dict[str, Optional[str]],
                       roles_dir: Path, traits_dir: Path) -> Tuple[List[str], List[str]]:
    """``(mismatched, unlisted)`` combination stems: recorded with a
    ``pairs_sha256`` other than :func:`combination_pairs_sha256` of the files
    now (or an instruction file missing), and not in the scores file at all."""
    mismatched, unlisted = [], []
    for stem in stems:
        parsed = parse_combined_filename(stem)
        if parsed is None:
            continue
        if stem not in stored:
            unlisted.append(stem)
            continue
        role, trait, _ = parsed
        try:
            current = combination_pairs_sha256(role, trait, roles_dir, traits_dir)
        except OSError:
            current = None
        if current is None or current != stored[stem]:
            mismatched.append(stem)
    return mismatched, unlisted


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


# Role rubrics are templates since 2026-10-23 (the TODO that stood here,
# "role-template-refactor", steps 1, 2 and 4): every prompt version renders a
# role's rubric from its template, the role's judge display name and the
# description in its file, as it does for traits.  The ``eval_prompt`` that
# data_analysis/regenerate_role_instructions.py still bakes into each role
# file is no longer read here; a test pins it equal to the version 3
# rendering for every role, so version 3 sends what step 3 sent before.  Step
# 3 of the old sketch (strip ``eval_prompt`` from the files) is not done: the
# role rubric experiment (data_analysis/role_rubric_experiment.py) reads it.
# The artefacts of the original oneshot generation that the old note listed
# ("Gemma, an LLM", the altruist example in level 2, the doubled parenthesis
# in level 1, level 0's refusal clause) are what that experiment tests;
# prompt version 4 takes the edits Roger approves.
def _role_prompt(stem: str, roles_dir: Path, version: PromptVersion) -> Optional[str]:
    role_file = roles_dir / f"{stem}.json"
    if not role_file.exists():
        return None
    data = _load_json(role_file)
    desc = _description_from(data)
    if not desc:
        logger.warning(f"Role {stem} has no description")
        return None
    return version.role_template(stem).format(
        role_name=_literal(role_judge_name(stem, roles_dir)),
        description=_literal(desc),
    )


def trait_judge_name(stem: str, data: dict) -> str:
    """The trait's name as the judge sees it: the judge display form of the
    label in the file being read (``judge_label``'s trait rule, applied to
    this file so that a ``--traits_dir`` outside the corpus works too)."""
    return judge_form_of_label(data.get("positive_label") or display_form_name(stem))


def role_judge_name(stem: str, roles_dir: Path) -> str:
    """The role's name as the judge sees it (``judge_label``; a role's
    display override applies even without its file)."""
    return judge_label(stem, "roles", data_dir=Path(roles_dir).parent.parent)


def _trait_prompt(stem: str, traits_dir: Path, version: PromptVersion) -> Optional[str]:
    trait_file = traits_dir / f"{stem}.json"
    if not trait_file.exists():
        return None
    data = _load_json(trait_file)
    desc = _description_from(data)
    return version.trait.format(
        trait_name=_literal(trait_judge_name(stem, data)),
        trait_description=_literal(desc),
    )


def resolve_eval_prompt(
    stem: str,
    roles_dir: Path,
    traits_dir: Path,
    entity_type: str,
    *,
    prompt_version: int = DEFAULT_PROMPT_VERSION,
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

    ``prompt_version``: the rubric version (assistant_axis/judge_rubrics.py).
    """
    version = get_version(prompt_version)
    # Skip default — step 4 uses all activations without scores
    if stem == "default":
        return None

    if entity_type == "role":
        prompt = _role_prompt(stem, roles_dir, version)
        if prompt is None and not (roles_dir / f"{stem}.json").exists():
            logger.warning(f"No role file found for {stem}")
        return prompt

    if entity_type == "trait":
        prompt = _trait_prompt(stem, traits_dir, version)
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
        return version.combination.format(
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
            if (r.get("batch_id") or r.get("input_file_id") or r.get("submitting_ts"))
            and not r.get("collected")]
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


def _recorded_versions(output_dir: Path) -> Tuple[List[int], Dict[str, str]]:
    """``(versions, hashes)`` that ``judge_rubric.json`` records for the
    scores in ``output_dir``: score files there with no stamp beside them
    predate stamping (version 1); ``hashes`` maps a version (as a string) to
    the hash of its text (``PromptVersion.sha256``), recorded since
    2026-10-23."""
    path = output_dir / RUBRIC_STAMP_FILENAME
    if path.exists():
        old = json.loads(path.read_text())
        return list(old.get("rubric_versions", [])), dict(old.get("prompt_sha256", {}))
    unstamped = any(p.name not in SIDE_CAR_FILENAMES for p in output_dir.glob("*.json"))
    return ([1] if unstamped else []), {}


def prompt_version_conflict(output_dir: Path, prompt_version: int,
                            entity_type: str) -> Optional[str]:
    """Why ``output_dir`` cannot take ``entity_type`` scores judged under
    ``prompt_version``, or None.  Its scores were judged under another version (other than a mix
    of versions 1-3, which send the same text and differ in how a reply was
    read, and which step 3 has only warned about), or under another text of
    the same version (a draft that has changed since): step 4 would average
    responses kept by two rubrics into one vector.  Checked before any
    request, and in a dry run."""
    recorded, hashes = _recorded_versions(output_dir)
    others = sorted(set(recorded) - {prompt_version})
    if others and not (set(recorded) | {prompt_version}) <= MIXABLE_VERSIONS:
        return (f"{output_dir}: the scores there were judged under prompt version(s) "
                f"{', '.join(str(v) for v in others)}, not {prompt_version}; judge version "
                f"{prompt_version} into another --output_dir (run_pipeline.sh "
                f"--judge-prompt-version gives each version its own scores_v<N>/)")
    sha = hashes.get(str(prompt_version))
    current = get_version(prompt_version).sha256(entity_type)
    if sha and sha != current:
        return (f"{output_dir}: the scores there were judged under another text of prompt "
                f"version {prompt_version} (hash {sha}; now {current}, the draft has changed "
                f"since); judge into another --output_dir")
    return None


def stamp_rubric(output_dir: Path, *, entity_type: str, judge_model: str,
                 prompt_version: int = DEFAULT_PROMPT_VERSION) -> dict:
    """Record in ``judge_rubric.json`` that this run judges under
    ``prompt_version`` (assistant_axis/judge_rubrics.py), with the hash of
    its text for ``entity_type``.  Versions, hashes and models accumulate across runs into the
    same directory; score files already there with no stamp beside them
    predate stamping (version 1).  Warns when the directory mixes versions
    (only versions 1-3 can be mixed: :func:`prompt_version_conflict`)."""
    path = output_dir / RUBRIC_STAMP_FILENAME
    old = json.loads(path.read_text()) if path.exists() else {}
    recorded, hashes = _recorded_versions(output_dir)
    versions = sorted(set(recorded) | {prompt_version})
    if len(versions) > 1:
        logger.warning(f"{output_dir}: scores here were judged under rubric versions {versions} "
                       f"(this run: {prompt_version}); entities already scored are not rejudged")
    version = get_version(prompt_version)
    stamp = {
        "script": "pipeline/3_judge.py",
        "rubric_version": prompt_version,
        "rubric_versions": versions,
        "prompt_sha256": {**hashes, str(prompt_version): version.sha256(entity_type)},
        "reply_format": version.reply_format,
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
    reply_format: str = "score_marker",
) -> Tuple[dict, int, int]:
    """Score responses for a single entity.  ``usage`` (a
    MultiModelUsage) is ticked with every response's token counts;
    ``reply_format`` is the prompt version's (:func:`score_reply`).

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
        # rubric v3 on: a reply cut at max_tokens is unparseable
        reject_truncated=reply_format == "score_marker",
    )

    scores: Dict[str, int] = {}
    n_attempted = 0
    n_parsed = 0
    for key, text in zip(keys, responses_text):
        n_attempted += 1
        score = score_reply(text, reply_format=reply_format)
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


class ModelDriftError(RuntimeError):
    """Batches in flight were requested with another judge model."""


# ---------------------------------------------------------------------------
# One step-3 process per scores directory (walk-through P5; review P3 D3)
# ---------------------------------------------------------------------------
#
# Two runs on one scores directory used to interfere: the second's resume
# deleted the first's unsubmitted chunks, and both collected (and charged)
# the same batches.  A lock file, created with O_EXCL (atomic on local disk
# and on NFSv3+), holds the PID, host and start time of the run that owns the
# directory.  A lock left by a process that is no longer running on this host
# is removed with a warning; any other lock refuses the run unless
# --force_unlock (for a lock left by a run on another host that has ended).
# The lock is taken in both modes: a --no_batch run writes the same score
# files and usage record.

LOCK_FILENAME = ".3_judge.lock"   # not *.json: nothing reads it as an entity


class LockHeldError(RuntimeError):
    """Another step-3 run holds the scores directory's lock."""


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:      # exists, owned by someone else
        return True
    except OSError:
        return True
    return True


class ScoresDirLock:
    """``with ScoresDirLock(output_dir, force=...):`` -- see above."""

    def __init__(self, output_dir: Path, *, force: bool = False):
        self.path = Path(output_dir) / LOCK_FILENAME
        self.force = force
        self.payload = {"pid": os.getpid(), "host": socket.gethostname(),
                        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "argv": sys.argv[1:]}
        self.held = False

    def _holder(self) -> dict:
        try:
            return json.loads(self.path.read_text())
        except (OSError, ValueError):
            return {}

    def _try_create(self) -> bool:
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            return False
        with os.fdopen(fd, "w") as f:
            json.dump(self.payload, f)
        return True

    def acquire(self) -> None:
        if self._try_create():
            self.held = True
            return
        holder = self._holder()
        desc = (f"pid {holder.get('pid')} on {holder.get('host')}, started "
                f"{holder.get('started_at')}" if holder else "unreadable")
        same_host_dead = (holder.get("host") == self.payload["host"]
                          and isinstance(holder.get("pid"), int)
                          and not _pid_alive(holder["pid"]))
        if self.force or same_host_dead:
            logger.warning(f"{self.path}: removing the lock of a run that is "
                           f"{'not running any more' if same_host_dead else 'overridden by --force_unlock'}"
                           f" ({desc})")
            self.path.unlink(missing_ok=True)
            if self._try_create():
                self.held = True
                return
            holder = self._holder()
        raise LockHeldError(
            f"{self.path} is held by another step-3 run ({desc}); one run per scores directory.  "
            f"If that run has ended (on another host), pass --force_unlock")

    def release(self) -> None:
        """Remove the lock if it is still this run's."""
        if self.held:
            holder = self._holder()
            if holder.get("pid") == self.payload["pid"] and holder.get("host") == self.payload["host"]:
                self.path.unlink(missing_ok=True)
            self.held = False

    def __enter__(self) -> "ScoresDirLock":
        self.acquire()
        return self

    def __exit__(self, *exc) -> None:
        self.release()


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
    reply_format: str = "score_marker",
) -> Tuple[int, int, int, set]:
    """Judge ``entities`` (name, existing scores, eval template, responses;
    consumed once, so a generator keeps one entity's responses in memory at
    a time) in batches.  Score files are ``<output_dir>/<name>.json``;
    ``before_write()`` (the rubric stamp) is called once new batches are
    written, so that a run stopped before collecting them has recorded the
    version they were requested under, and before scores are first written.
    ``reply_format``: the prompt version's (:func:`score_reply`).  Returns ``(n_attempted, n_parsed, n_left,
    entities_with_new_scores)``; ``n_left`` requests are unanswered and
    unscored, for a rerun."""
    # A Claude judge goes through Anthropic Message Batches (2026-10-26), an
    # OpenAI one through the OpenAI Batch API; the runners share an interface.
    anthropic_judge = provider_for_model(judge_model) == "anthropic"
    if anthropic_judge:
        runner = AnthropicBatchRunner(
            client, output_dir / BATCH_WORK_DIRNAME, output_dir / BATCH_STATE_FILENAME,
            poll_seconds=poll_seconds, logger=logger)
        request_for = anthropic_request_params
    else:
        runner = OpenAIBatchRunner(
            client, output_dir / BATCH_WORK_DIRNAME, output_dir / BATCH_STATE_FILENAME,
            poll_seconds=poll_seconds,
            metadata={"source": "pipeline/3_judge.py", "output_dir": str(output_dir)[-200:]},
            logger=logger)
        request_for = chat_request_body
    inflight = await runner.resume()
    # Model drift (walk-through P5; review P3 D4): a batch in flight was
    # requested with another judge model.  Collected under this run's
    # --judge_model, its scores would be mixed with this model's and its
    # usage charged under the wrong name.
    other = {m: names for m, names in runner.inflight_models().items() if m != judge_model}
    if other:
        raise ModelDriftError(
            f"{output_dir / BATCH_STATE_FILENAME} records batches in flight requested with "
            + "; ".join(f"{m} ({len(n)} chunk(s), e.g. {n[0]})" for m, n in sorted(other.items()))
            + f", not --judge_model {judge_model}: rerun with --judge_model set to that model "
              f"to collect them, or delete the state file to abandon them")

    def requests():
        for name, existing, eval_tpl, responses in entities:
            for key, prompt in pending_prompts(responses, eval_tpl, existing, name=name):
                cid = f"{name}{CUSTOM_ID_SEP}{key}"
                if cid not in inflight:
                    yield cid, request_for(prompt, judge_model, max_tokens)

    chunks = runner.write_chunks(requests(), max_requests=chunk_requests)
    if chunks:
        before_write()
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
        if anthropic_judge:
            text, finish, n_in, n_out, refused = anthropic_reply(body)
            if refused:   # counted as the real-time path counts it (judge.REFUSED_REPLIES)
                _judge_mod.REFUSED_REPLIES[judge_model] = _judge_mod.REFUSED_REPLIES.get(judge_model, 0) + 1
            run_usage.charge(batch_key, n_in, n_out)
        else:
            u = body.get("usage") or {}
            run_usage.charge(batch_key, int(u.get("prompt_tokens") or 0),
                             int(u.get("completion_tokens") or 0))
            choices = body.get("choices") or []
            text = ((choices[0].get("message") or {}).get("content") if choices else None)
            finish = choices[0].get("finish_reason") if choices else None
        score = score_reply(text, finish, reply_format=reply_format)
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
            batch_size=realtime_batch_size, usage=run_usage,
            reject_truncated=reply_format == "score_marker")
        for cid, text in zip(ids, texts):
            name, key = cid.split(CUSTOM_ID_SEP, 1)
            counts["attempted"] += 1
            score = score_reply(text, reply_format=reply_format)
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
    reason it cannot.  Checked before any request: the model must be an
    OpenAI or a Claude model (a Claude judge since 2026-10-26, the judge
    comparison: batch mode through Anthropic Message Batches,
    ``assistant_axis/anthropic_batch.py``), and a model ``judge_pricing``
    cannot price raises in the usage tracker after the request is paid for
    (in real time the reply was then discarded as unparseable, in a batch
    the collection stopped).  A batch run is priced under ``<model>:batch``,
    and its fallback in real time under the plain name."""
    try:
        provider_for_model(model)
    except ValueError as e:
        return str(e)
    for name in ([model, f"{model}{BATCH_SUFFIX}"] if batch else [model]):
        try:
            price_for_model(name)
        except KeyError as e:
            return e.args[0] if e.args else f"no price for {name!r}"
    return None


def judge_key_name(model: str) -> str:
    """The environment variable holding the API key the judge ``model`` needs
    (loaded from ``.env`` by ``load_dotenv``; only its presence is checked)."""
    return "ANTHROPIC_API_KEY" if provider_for_model(model) == "anthropic" else "OPENAI_API_KEY"


def judge_client(model: str):
    """The async client for the judge ``model``'s provider."""
    if provider_for_model(model) == "anthropic":
        import anthropic
        return anthropic.AsyncAnthropic()
    return openai.AsyncOpenAI()


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
    parser.add_argument("--prompt_version", type=int, default=DEFAULT_PROMPT_VERSION,
                        help="Rubric version (assistant_axis/judge_rubrics.py): 0, the original "
                             "number-only rubrics read as the first integer in the reply; 3, the "
                             "current rubrics (the default); 4, the next version, a draft (version "
                             "3 with the approved arms of the role rubric experiment); 5, a draft, "
                             "version 4 and a clause for helpful professional roles.  A scores "
                             "directory holds one version: a run refuses a directory judged under "
                             "another (run_pipeline.sh --judge-prompt-version gives each version "
                             f"its own directories).  Default {DEFAULT_PROMPT_VERSION}")
    parser.add_argument("--max_tokens", type=int, default=None,
                        help="Max tokens for judge response (default: the prompt version's, 200 "
                             "for versions 3 and 4, which must fit 2-3 sentences of reasoning + "
                             "the SCORE: line, and the fork's 10 for version 0, whose replies "
                             "are a number; 10 under a reasoning-first version would truncate "
                             "every judge call)")
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
                             "the organisation's queue limit is held or split automatically).  "
                             "Size it from the queue limit when several runs share one API key "
                             "(pipeline/README.md, 'Several runs on one organisation's queue')")
    parser.add_argument("--min_parse_rate", type=float, default=PARSE_RATE_LOUD_THRESHOLD,
                        help="The run exits 1 when fewer than this share of its judge calls give "
                             f"a score (default {PARSE_RATE_LOUD_THRESHOLD}, the project's "
                             "'<99%% is a bug' threshold; rubric v3 counts a reply without exactly "
                             "one SCORE marker, or cut at --max_tokens, as unparseable)")
    parser.add_argument("--force_unlock", action="store_true",
                        help="Remove the scores directory's lock (.3_judge.lock) left by a run "
                             "that has ended on another host.  A lock of a run no longer "
                             "running on this host is removed without it.")
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
    if not 0 < args.min_parse_rate <= 1:
        parser.error("--min_parse_rate must be in (0, 1]")
    try:
        version = get_version(args.prompt_version)
    except ValueError as e:
        parser.error(f"--prompt_version: {e}")
    if args.max_tokens is None:
        args.max_tokens = version.max_tokens

    problem = check_judge_model(args.judge_model, batch=not args.no_batch)
    if problem:
        logger.error(f"--judge_model {args.judge_model}: {problem}")
        sys.exit(1)
    key_name = judge_key_name(args.judge_model)
    if not args.dry_run and not os.getenv(key_name):
        logger.error(f"{key_name} not found")
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
    stored_pairs_sha: Dict[str, Optional[str]] = {}
    if not args.no_incongruity_filtering:
        combo_scores_path = Path(args.combination_scores)
        if combo_scores_path.exists():
            combo_data = json.load(open(combo_scores_path))
            n_excluded = 0
            for entry in combo_data.get("scores", []):
                stored_pairs_sha[entry["output_name"]] = entry.get("pairs_sha256")
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

    # The incongruity scores must be of the instruction pairs as they are
    # now (walk-through P4; review P3 D7): an exclusion computed for texts
    # that have since been regenerated would drop the wrong variants.  A
    # mismatch stops a combination run before any request; a combination with
    # no entry is judged in full, with a warning.
    if args.entity_type == "combination" and stored_pairs_sha:
        mismatched, unlisted = check_pairs_sha256(
            [f.stem for f in response_files], stored_pairs_sha, roles_dir, traits_dir)
        if unlisted:
            logger.warning(f"{len(unlisted)} combination(s) have no entry in "
                           f"{args.combination_scores}, so every variant is judged: "
                           f"{', '.join(unlisted[:10])}{' ...' if len(unlisted) > 10 else ''}")
        if mismatched:
            logger.error(f"{len(mismatched)} combination(s) in {args.combination_scores} were "
                         f"scored for other instruction texts or labels than the files have now "
                         f"(pairs_sha256): {', '.join(mismatched[:10])}"
                         f"{' ...' if len(mismatched) > 10 else ''}.  Rerun "
                         f"data_analysis/score_combinations.py (it rescores only what changed), "
                         f"or pass --no_incongruity_filtering to judge every variant")
            sys.exit(1)

    # ------------------------------------------------------------------
    # Dry run
    # ------------------------------------------------------------------
    if args.dry_run:
        logger.info("Dry run — no API calls")
        logger.info(f"Prompt version {version.number}{' (draft)' if version.draft else ''}: "
                    f"{version.summary}; --max_tokens {args.max_tokens}")
        conflict = prompt_version_conflict(output_dir, args.prompt_version, args.entity_type) \
            if output_dir.is_dir() else None
        if conflict:
            logger.error(f"A live run would stop: {conflict}")
        total_prompts = 0
        sample_shown = False

        for response_file in response_files:
            name = response_file.stem
            # the live run's reader and request list, so the counts agree
            existing_scores = load_scores(output_dir / f"{name}.json")

            eval_tpl = resolve_eval_prompt(name, roles_dir, traits_dir,
                                           entity_type=args.entity_type,
                                           prompt_version=args.prompt_version)
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
                    logger.info(f"Model: {args.judge_model}, prompt version {args.prompt_version}")
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
    # Live scoring, under the scores directory's lock (P5, 2026-10-12)
    # ------------------------------------------------------------------
    lock = ScoresDirLock(output_dir, force=args.force_unlock)
    try:
        lock.acquire()
    except LockHeldError as e:
        logger.error(str(e))
        sys.exit(1)
    try:
        await live_scoring(args, output_dir=output_dir, roles_dir=roles_dir,
                           traits_dir=traits_dir, excluded_pairs=excluded_pairs,
                           response_files=response_files)
    finally:
        lock.release()


async def live_scoring(args, *, output_dir: Path, roles_dir: Path, traits_dir: Path,
                       excluded_pairs: Dict[str, set], response_files: List[Path]) -> None:
    """Judge every pending response (batch mode, or real time with
    ``--no_batch``), write the scores, usage record and rubric stamp, and
    exit 1 when the run is not complete.  Called with the lock held."""
    if args.no_batch:
        # Judging in real time what earlier batches are still answering pays
        # twice and leaves the batches uncollected (2026-10-12).
        n_chunks, n_inflight = uncollected_batches(output_dir)
        if n_chunks:
            logger.error(f"{output_dir / BATCH_STATE_FILENAME} records {n_chunks} batch(es) "
                         f"({n_inflight} requests) sent and not collected: run without "
                         f"--no_batch first to collect them, or delete that file to abandon them")
            sys.exit(1)

    # One prompt version per scores directory (2026-10-23), checked before
    # any request: step 4 averages whatever a directory's score files keep.
    conflict = prompt_version_conflict(output_dir, args.prompt_version, args.entity_type)
    if conflict:
        logger.error(conflict)
        sys.exit(1)
    version = get_version(args.prompt_version)

    client = judge_client(args.judge_model)
    rate_limiter = RateLimiter(args.requests_per_second)

    # The rubric stamp is written just before the first scores are, or the
    # first new batches (2026-10-23), so that a run that judges nothing does
    # not record this version (2026-10-12).
    stamped = []

    def stamp_once() -> None:
        if not stamped:
            stamp_rubric(output_dir, entity_type=args.entity_type, judge_model=args.judge_model,
                         prompt_version=args.prompt_version)
            stamped.append(True)

    logger.info(f"Rubric version {version.number}{' (draft)' if version.draft else ''}: "
                f"{version.summary} (names in the {JUDGE_LABEL_FORM} form; "
                f"--max_tokens {args.max_tokens})")
    # Token usage (AGENT_NOTES HARD RULE): <output_dir>/usage.json, merged
    # into on resume and rewritten after every entity (real time) or every
    # collected batch (batch mode).
    usage_path = output_dir / USAGE_FILENAME
    prior_usage = MultiModelUsage.load_or_create(usage_path)
    run_usage = MultiModelUsage()
    if prior_usage.n_calls:
        logger.info(prior_usage.log_line("[usage] earlier runs"))

    successful = skipped = failed = 0
    REPLY_PROBLEMS.clear()
    truncated_at_start = _judge_mod.TRUNCATED_REPLIES.get(args.judge_model, 0)
    refused_at_start = _judge_mod.REFUSED_REPLIES.get(args.judge_model, 0)
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
                                       entity_type=args.entity_type,
                                       prompt_version=args.prompt_version)
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

    # An HTTP 400 from the judge (B1, 8bf84f14: JudgeRequestError, raised for a
    # request the API refuses as a whole, such as an unsupported parameter)
    # would fail every later request the same way: the run stops and exits 1
    # with the reason.  A 400 that flags one prompt's content stays per item
    # (None, an unparseable reply; judge.CONTENT_FLAGGED counts them).
    request_error: Optional[str] = None
    if not args.no_batch:
        try:
            total_call_attempted, total_call_parsed, n_left, touched = await judge_in_batches(
                client=client, entities=prepared_entities(), output_dir=output_dir,
                judge_model=args.judge_model, max_tokens=args.max_tokens,
                usage_path=usage_path, prior_usage=prior_usage, run_usage=run_usage,
                chunk_requests=args.batch_requests, poll_seconds=args.batch_poll_seconds,
                fallback_max=args.batch_fallback_max, rate_limiter=rate_limiter,
                realtime_batch_size=args.batch_size, before_write=stamp_once,
                reply_format=version.reply_format)
            successful = len(touched)
        except ModelDriftError as e:
            logger.error(str(e))
            sys.exit(1)
        except JudgeRequestError as e:          # in the real-time fallback
            request_error = str(e)
    else:
        for name, existing_scores, eval_tpl, responses in prepared_entities():
            if request_error:
                break
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
                    reply_format=version.reply_format,
                )
                write_usage(usage_path, prior_usage, run_usage)
                total_call_attempted += n_attempted
                total_call_parsed += n_parsed
                stamp_once()
                all_scores = merge_scores(output_dir / f"{name}.json", new_scores)
                logger.info(f"Saved {len(all_scores)} scores for {name} "
                            f"({len(new_scores)} new)")
                successful += 1

            except JudgeRequestError as e:
                request_error = f"{name}: {e}"
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

    # Why replies were not scored.  A real-time reply cut at
    # max_tokens comes back from judge.call_judge_batch as None (counted in
    # judge.TRUNCATED_REPLIES), so it is moved from no_reply to truncated.
    rt_truncated = _judge_mod.TRUNCATED_REPLIES.get(args.judge_model, 0) - truncated_at_start
    if rt_truncated:
        REPLY_PROBLEMS["no_reply"] -= rt_truncated
        REPLY_PROBLEMS["truncated"] += rt_truncated
    # A Claude judge's refusal (stop_reason "refusal") also comes back as None
    # (judge.REFUSED_REPLIES), so it is moved from no_reply to refused.
    rt_refused = _judge_mod.REFUSED_REPLIES.get(args.judge_model, 0) - refused_at_start
    if rt_refused:
        REPLY_PROBLEMS["no_reply"] -= rt_refused
        REPLY_PROBLEMS["refused"] += rt_refused
    problems = {k: v for k, v in REPLY_PROBLEMS.items() if v > 0}
    if problems:
        logger.info(f"Unparseable replies (rubric v{version.number}): " + ", ".join(
            f"{v} {k.replace('_', ' ')}" for k, v in sorted(problems.items())))

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
    if request_error:
        reasons.append(f"the judge API refused a request, so the run stopped: {request_error}")
    if n_left:
        reasons.append(f"{n_left} requests left unscored by their batches (a rerun submits them)")
    if total_call_attempted and total_call_parsed / total_call_attempted < args.min_parse_rate:
        reasons.append(f"parse rate {total_call_parsed}/{total_call_attempted} is under "
                       f"--min_parse_rate {args.min_parse_rate:.0%}")
    if failed:
        reasons.append(f"{failed} entit{'y' if failed == 1 else 'ies'} failed (see Errors above)")
    if reasons:
        logger.error("Step 3 is not complete: " + "; ".join(reasons))
        sys.exit(1)




def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
