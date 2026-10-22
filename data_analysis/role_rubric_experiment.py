#!/usr/bin/env python3
"""The role-judge rubric experiment: does a change to the role rubric change the role vectors?

Plan: reports/pipeline/plan_role_rubric_experiment.md (approved by Roger on 2026-10-16 with all
eight arms; built 2026-10-22).  The rubric under test is the ``eval_prompt`` baked into every role
file (data/roles/instructions/<role>.json), rendered from ``ROLE_EVAL_PROMPT_TEMPLATE`` in
data_analysis/regenerate_role_instructions.py and sent by pipeline/3_judge.py once per response;
step 4 (pipeline/4_vectors.py) averages only the responses scored 3, so the rubric decides which
responses enter each role vector.

The arms are transformations of each role's baked text, applied here and nowhere else: the
production template and the role files are untouched.  This module is the experiment's switch
(AGENT_NOTES "Experiment switches in rubric files: remove them once settled"): once Roger has
decided, the adopted wording goes into the template with one ``JUDGE_RUBRIC_VERSION`` bump, the
role files are re-rendered, and this module is archived.

Arms (wording version ``WORDING_VERSION``; the exact text is in ``arm_template`` and rendered in
reports/pipeline/role_rubric_experiment/arm_wordings.md):

    A0   each role file's baked eval_prompt, which is what step 3 sends
    A0b  A0 again, a second independent judging run (written A0' in the documents): the noise floor
    A1   "Gemma, an LLM" in levels 0-2 -> model-neutral ("an AI assistant, a language model, etc."),
         and the "((an AI" typo fixed
    A2   "Gemma" -> the current model's short name ("Qwen" for Qwen3), typo fixed
    A3   the level-2 example made generic
    A4   the level-2 example rendered with the role's own name
    A5   A1 + A3
    A6   level 0's refusal clause removed, the in-role refusal said once, at level 3 (option B of
         the 2026-10-12 progress report's role-rubric proposal)
    A7   role-aware identity wording: levels 0-2 ask whether the model identifies as the underlying
         assistant rather than as the role, and a role that is itself an AI may say so

Every arm keeps the reasoning-first closing line and the ``SCORE: <integer from 0 to 3>`` marker,
so step 3's reader (``score_reply``: exactly one marker, a reply cut at max_tokens unparseable)
applies unchanged.  The judge request is step 3's: gpt-4.1-mini, ``max_completion_tokens`` 200,
the provider's default temperature (not sent), one user message, through the OpenAI Batch API
(assistant_axis/openai_batch.py).

Subcommands:

    render           reports/pipeline/role_rubric_experiment/arm_wordings.md: every arm's diff
                     against A0 and the prompt as the judge receives it (Roger reviews it first)
    estimate         calls, prompt and output tokens and dollars per arm at batch prices
    judge            one request per (arm, role, response); --dry-run, --batch-no-wait,
                     --collect-only, --batch-id; resumable, never pays twice for a collected reply
    analyze-scores   the noise floor (A0 vs A0'), boundary flips per arm by role, question and
                     direction, the AI-persona roles apart, and the blind reading sheet
    read-marks       Roger's marks on the reading sheet joined to its key, per arm
    analyze-vectors  (on the pod) each arm's role vectors exactly as step 4 computes them, and
                     their cosine with A0's per slot and layer, against A0' vs A0

Run directory written by ``judge`` (``--out-dir``): ``<arm>/<role>.json`` score files in step 3's
format (keys ``pos_p0_q0``, the keys of the response files) with ``<arm>/usage.json``;
``replies/<arm>/<role>.jsonl`` (every reply, with its score or why it was unparseable);
``usage.json`` (the run's total, ``gpt-4.1-mini:batch``); ``run_record.json`` (arms, sample, model,
template hashes, response-file hashes, batch ids, runs); ``batch_state.json`` and ``_batches/``
(the batch runner's).

Commands (see arm_wordings.md for the current ones)::

    uv run python data_analysis/role_rubric_experiment.py render
    uv run python data_analysis/role_rubric_experiment.py estimate
    uv run python data_analysis/role_rubric_experiment.py judge --dry-run \\
        --responses-dir <responses> --out-dir <run dir>
    uv run python data_analysis/role_rubric_experiment.py judge --confirm-expensive \\
        --responses-dir <responses> --out-dir <run dir> [--batch-no-wait]
    uv run python data_analysis/role_rubric_experiment.py judge --collect-only --out-dir <run dir> \\
        --responses-dir <responses>
    uv run python data_analysis/role_rubric_experiment.py analyze-scores --scores-dir <run dir> \\
        --responses-dir <responses>
    uv run python data_analysis/role_rubric_experiment.py analyze-vectors \\
        --activations-dir <activations> --scores-dir <run dir>
"""
from __future__ import annotations

import argparse
import asyncio
import difflib
import hashlib
import importlib.util
import json
import logging
import math
import os
import random
import re
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# NFS-safe reads and writes (AGENT_NOTES "NFS-safe file I/O"): the run directory may be on the
# pod's /workspace.  openai_batch imports the standard library and atomic_io only.
from assistant_axis.atomic_io import (  # noqa: E402
    atomic_write_text, read_jsonl_with_retry, read_text_with_retry, write_jsonl,
)
from assistant_axis.openai_batch import (  # noqa: E402
    TOKEN_LIMIT_CODE, BatchFailedError, OpenAIBatchRunner, _error_codes, _error_text, _get,
)

logger = logging.getLogger("role_rubric_experiment")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROLES_DIR = REPO / "data" / "roles" / "instructions"
MAY_TREE = REPO / "runpod_workspace" / "qwen" / "qwen-3-32b Roger 8slot" / "roles"
MAY_RESPONSES_DIR = MAY_TREE / "responses"
MAY_SCORES_DIR = MAY_TREE / "scores"
REPORT_DIR = REPO / "reports" / "pipeline" / "role_rubric_experiment"
PLAN_DOC = REPO / "reports" / "pipeline" / "plan_role_rubric_experiment.md"
SCRIPT_REL = "data_analysis/role_rubric_experiment.py"

EXPERIMENT = "role_rubric_experiment"
# The arms' wording.  Bump it when any arm's text changes, so that a run directory judged under
# one wording is never resumed under another (judge refuses on a template-hash mismatch anyway).
WORDING_VERSION = 1

# ---------------------------------------------------------------------------
# The sample (decided; the coordinator, 2026-10-22)
# ---------------------------------------------------------------------------

SAMPLE_STRATA: Dict[str, Tuple[str, ...]] = {
    "ai_persona": ("instrumentally_aligned_ai", "assistant", "cyborg", "paperclip_maximizer",
                   "robot"),
    "most_held": ("minimalist", "peacekeeper", "realist", "validator", "emissary", "pacifist",
                  "perfectionist", "interpreter", "altruist"),
    "median": ("soldier", "biologist", "visionary", "psychologist", "historian", "contrarian",
               "organizer", "merchant"),
    "never_held": ("familiar", "alien", "ghost", "guru", "oracle", "pirate", "spirit", "tree"),
}
STRATUM_LABELS = {
    "ai_persona": "the five AI-persona roles (plan § 1b)",
    "most_held": "the nine roles most often held at level 2 in May",
    "median": "eight roles at the median May level-2 share",
    "never_held": "eight roles never held at level 2 in May",
}
SAMPLE_PROVENANCE = (
    "30 roles chosen by the coordinator on 2026-10-22 from the May 2026 tree "
    "(runpod_workspace/qwen/qwen-3-32b Roger 8slot/roles/scores) by each role's share of responses "
    "that step 3 scored 2: the five AI-persona roles of the plan's § 1b (instrumentally_aligned_ai "
    "was aligned_artificial_intelligence in May), the nine roles most often held at level 2 (the "
    "ten highest shares less aligned_artificial_intelligence), eight at the median share (about "
    "7%) and eight with no response at level 2.  The plan's '30 roles' option.")
SAMPLE: Tuple[str, ...] = tuple(r for rs in SAMPLE_STRATA.values() for r in rs)
AI_PERSONA_ROLES: Tuple[str, ...] = SAMPLE_STRATA["ai_persona"]
# The two roles whose prompts arm_wordings.md shows in full.
RENDER_ROLES = ("altruist", "instrumentally_aligned_ai")


def stratum_of(role: str) -> Optional[str]:
    for name, roles in SAMPLE_STRATA.items():
        if role in roles:
            return name
    return None


# ---------------------------------------------------------------------------
# The judge request: step 3's, for roles
# ---------------------------------------------------------------------------

JUDGE_MODEL = "gpt-4.1-mini"      # pipeline/3_judge.py --judge_model default
MAX_TOKENS = 200                  # pipeline/3_judge.py --max_tokens default
CUSTOM_ID_SEP = "|"               # as step 3's; arms, stems and keys never contain it

# Token counting for the estimate.  gpt-4.1-mini uses o200k_base; the chat format adds a few
# tokens per request.  Calibrated on the P5 canary of 2026-10-12 (reports/pipeline/
# fix_batch_2026-10-12.md § 4): accountant's first 30 May responses with its eval_prompt were
# billed 23,151 prompt tokens (771.7 a request); tiktoken o200k_base counts 764.7 a request of
# the prompt text, so the overhead is 7.  chars/4 counts 953.3 (24% high).
TOKENIZER = "o200k_base"
CHAT_OVERHEAD_TOKENS = 7
# Output tokens per call: the same canary, 2,165 completion tokens over 30 role requests under
# the reasoning-first rubric (72.2 a call).  The May tree's judge was asked for the number alone,
# so it has no evidence on the reason-plus-score format.
OUTPUT_TOKENS_PER_CALL = 72
CONFIRM_ABOVE_USD = 20.0          # the expensive-operations rule
COST_FLAG_USD = 35.0              # the coordinator's flag; Roger's cap is $40
COST_CAP_USD = 40.0

# ---------------------------------------------------------------------------
# The arms
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Arm:
    id: str
    label: str
    summary: str


ARMS: Tuple[Arm, ...] = (
    Arm("A0", "A0", "the current rubric: each role file's baked eval_prompt, as step 3 sends it"),
    Arm("A0b", "A0'", "A0 again, a second independent judging run (the noise floor)"),
    Arm("A1", "A1", '"Gemma, an LLM" in levels 0-2 replaced by model-neutral wording '
                    '("an AI assistant, a language model, etc."); the "((an AI" typo fixed'),
    Arm("A2", "A2", '"Gemma" in levels 0-2 replaced by the current model\'s short name; '
                    'the typo fixed'),
    Arm("A3", "A3", "the level-2 example (altruistic AI for the role altruist) made generic"),
    Arm("A4", "A4", "the level-2 example rendered with the role's own name instead of altruist"),
    Arm("A5", "A5", "A1 and A3 together"),
    Arm("A6", "A6", "level 0's refusal clause removed; the in-role refusal is said once, at "
                    "level 3"),
    Arm("A7", "A7", "role-aware identity wording: levels 0-2 ask whether the model identifies as "
                    "the underlying assistant rather than as the role; a role that is itself an "
                    "AI may say so"),
)
ARM_IDS: Tuple[str, ...] = tuple(a.id for a in ARMS)
ARM_BY_ID: Dict[str, Arm] = {a.id: a for a in ARMS}
BASE_ARM = "A0"
NOISE_ARM = "A0b"
COMPARED_ARMS: Tuple[str, ...] = tuple(a for a in ARM_IDS if a != BASE_ARM)

# The A0 text the arms change (every role file has each of these, from the one template).
CLOSING_LINE = ("First, briefly reason about whether the response embodies the role (2-3 "
                "sentences). Then on a new line, write exactly: SCORE: <integer from 0 to 3>")
IDENTITY_PAREN = "(an AI assistant, Gemma, an LLM, etc.)"            # levels 0, 1, 2
TYPO = "((an AI assistant"                                          # level 1
LEVEL2_EXAMPLE = "(e.g. altruistic AI for the role altruist)"
LEVEL0_REFUSAL_CLAUSE = (" This does not include if the model refuses the question but still "
                         "identifies as the role, which should be label 3 instead.")
LEVEL3_REFUSAL_CLAUSE = (" This includes if the model says it cannot answer the question while "
                         "still identifying as the role.")
ROLE_NAME_RE = re.compile(r"displays the role: \*\*(.+?)\*\*\. ")

# What the arms put in its place.
A1_PAREN = "(an AI assistant, a language model, etc.)"
A2_PAREN = "(an AI assistant, {model_name}, an LLM, etc.)"
A3_EXAMPLE = "(e.g. it speaks or acts somewhat like the role while still saying it is an AI)"
A4_EXAMPLE = "(e.g. {role_name}-like AI for the role {role_name})"
# Option B of the role-rubric proposal in reports/pipeline/fix_batch_2026-10-12.md § 7 (the text
# before commit 2a863192): level 0 ends at "...while refusing to answer the question."; level 3
# ends with this sentence instead of its own refusal clause.
A6_LEVEL3_REFUSAL = " A refusal given in the role's own voice also counts as playing the role."
A7_UNDERLYING = "the underlying assistant"
A7_ROLE_SENTENCE = ("If the role is itself an AI or another machine, saying that it is an AI is "
                    "part of playing the role and does not count against it: what matters is "
                    "whether the model speaks as the role or as the underlying assistant.")

DEFAULT_MODEL_NAME = "Qwen"       # A2, for the Qwen3 extraction when no side-car names the model


class ArmError(ValueError):
    """A role's baked text lacks a passage an arm changes (or has it a different number of
    times): the arm would silently equal A0 there, so it is refused."""


def _literal(text: str) -> str:
    """``text`` safe inside a template that step 3 formats with the question and answer."""
    return text.replace("{", "{{").replace("}", "}}")


def _replace(text: str, old: str, new: str, count: int, *, arm: str, what: str) -> str:
    n = text.count(old)
    if n != count:
        raise ArmError(f"{arm}: expected {count} occurrence(s) of {what} ({old!r}) in the "
                       f"A0 text, found {n}")
    return text.replace(old, new)


def role_name_in(baked: str) -> str:
    """The role's name as the baked text shows it to the judge (``**altruist**``)."""
    m = ROLE_NAME_RE.search(baked)
    if not m:
        raise ArmError("no '**<role>**. ' in the A0 text")
    return m.group(1)


def _fix_typo(text: str, arm: str) -> str:
    return _replace(text, TYPO, TYPO[1:], 1, arm=arm, what="the doubled parenthesis")


def arm_template(arm: str, baked: str, *, model_name: str = DEFAULT_MODEL_NAME) -> str:
    """The judge template of ``arm`` for a role whose baked eval_prompt is ``baked`` (with step
    3's ``{question}`` and ``{answer}`` placeholders).  Raises :class:`ArmError` when the baked
    text lacks a passage the arm changes."""
    if arm not in ARM_BY_ID:
        raise ValueError(f"unknown arm {arm!r}; arms: {', '.join(ARM_IDS)}")
    if arm in (BASE_ARM, NOISE_ARM):
        out = baked
    elif arm == "A1":
        out = _replace(_fix_typo(baked, arm), IDENTITY_PAREN, A1_PAREN, 3, arm=arm,
                       what="the identity parenthesis")
    elif arm == "A2":
        out = _replace(_fix_typo(baked, arm), IDENTITY_PAREN,
                       A2_PAREN.format(model_name=_literal(model_name)), 3, arm=arm,
                       what="the identity parenthesis")
    elif arm == "A3":
        out = _replace(baked, LEVEL2_EXAMPLE, A3_EXAMPLE, 1, arm=arm, what="the level-2 example")
    elif arm == "A4":
        name = role_name_in(baked)
        out = _replace(baked, LEVEL2_EXAMPLE, A4_EXAMPLE.format(role_name=name), 1, arm=arm,
                       what="the level-2 example")
    elif arm == "A5":
        out = _replace(_fix_typo(baked, arm), IDENTITY_PAREN, A1_PAREN, 3, arm=arm,
                       what="the identity parenthesis")
        out = _replace(out, LEVEL2_EXAMPLE, A3_EXAMPLE, 1, arm=arm, what="the level-2 example")
    elif arm == "A6":
        out = _replace(baked, LEVEL0_REFUSAL_CLAUSE, "", 1, arm=arm,
                       what="level 0's refusal clause")
        out = _replace(out, LEVEL3_REFUSAL_CLAUSE, A6_LEVEL3_REFUSAL, 1, arm=arm,
                       what="level 3's refusal clause")
    else:  # A7
        out = _replace(baked, "identifies as itself (", f"identifies as {A7_UNDERLYING} (", 3,
                       arm=arm, what="'identifies as itself ('")
        out = _replace(out, "etc.) but has some attributes of the role",
                       "etc.) rather than as the role, but has some attributes of the role", 1,
                       arm=arm, what="level 2's identity clause")
        out = _replace(out, "etc.), while ", "etc.) rather than as the role, while ", 2,
                       arm=arm, what="the identity clauses of levels 0 and 1")
        out = _replace(out, "\n\n" + CLOSING_LINE, "\n\n" + A7_ROLE_SENTENCE + "\n\n" + CLOSING_LINE,
                       1, arm=arm, what="the closing line")
    check_template(out, arm=arm)
    return out


def check_template(text: str, *, arm: str = "?") -> None:
    """Every arm keeps step 3's contract: the closing line last, once, and one placeholder each
    for the question and the answer."""
    if not text.endswith(CLOSING_LINE) or text.count(CLOSING_LINE) != 1:
        raise ArmError(f"{arm}: the template does not end with the closing line, once")
    for ph in ("{question}", "{answer}"):
        if text.count(ph) != 1:
            raise ArmError(f"{arm}: {ph} appears {text.count(ph)} times")


def template_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_script(name: str, relpath: str):
    """Load one of the pipeline's numbered scripts as a module (cached)."""
    mod = sys.modules.get(name)
    if mod is None:
        spec = importlib.util.spec_from_file_location(name, REPO / relpath)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return mod


def step3():
    """pipeline/3_judge.py, whose prompt filling, request body and reply reader are used as
    they are, so that the experiment's A0 is step 3's judging."""
    return _load_script("_role_rubric_exp_3_judge", "pipeline/3_judge.py")


def step4():
    """pipeline/4_vectors.py (imports torch): the vector computation, used as it is."""
    return _load_script("_role_rubric_exp_4_vectors", "pipeline/4_vectors.py")


def _json_dump(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _write_json(path: Path, obj: Any) -> None:
    atomic_write_text(_json_dump(obj), path, logger_obj=logger)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def make_cid(arm: str, role: str, key: str) -> str:
    return f"{arm}{CUSTOM_ID_SEP}{role}{CUSTOM_ID_SEP}{key}"


def parse_cid(cid: str) -> Tuple[str, str, str]:
    parts = cid.split(CUSTOM_ID_SEP, 2)
    if len(parts) != 3 or parts[0] not in ARM_BY_ID or not parts[1] or not parts[2]:
        raise ValueError(f"not a {EXPERIMENT} custom_id: {cid!r}")
    return parts[0], parts[1], parts[2]


def question_index(key: str) -> int:
    return int(key.rsplit("_q", 1)[1])


def model_short_name(model_id: str) -> str:
    """``Qwen/Qwen3-32B`` -> ``Qwen``: the leading letters of the model's own name."""
    base = str(model_id).rstrip("/").split("/")[-1]
    m = re.match(r"[A-Za-z]+", base)
    return m.group(0) if m else base


def resolve_model_name(arg: Optional[str], responses_dir: Optional[Path]) -> Tuple[str, str]:
    """A2's model name and where it came from: ``--model-name``, else the responses directory's
    ``generation_config.json`` side-car (its last run's ``model_name``), else ``Qwen``."""
    if arg:
        return arg, "--model-name"
    if responses_dir is not None:
        path = Path(responses_dir) / "generation_config.json"
        if path.exists():
            runs = json.loads(read_text_with_retry(path, logger_obj=logger)).get("runs") or []
            if runs and runs[-1].get("model_name"):
                return (model_short_name(runs[-1]["model_name"]),
                        f"{path.name} ({runs[-1]['model_name']})")
    return DEFAULT_MODEL_NAME, "the default; no generation_config.json beside the responses"


def renamed_stems(doc: Mapping[str, Any]) -> List[str]:
    """Earlier stems of a role (``renamed_from``), newest first."""
    rf = doc.get("renamed_from")
    if not rf:
        return []
    items = rf if isinstance(rf, list) else [rf]
    stems = [(i.get("stem") if isinstance(i, dict) else str(i)) for i in items]
    return [s for s in reversed(stems) if s]


def load_role(stem: str, roles_dir: Path = ROLES_DIR) -> Dict[str, Any]:
    return json.loads(read_text_with_retry(Path(roles_dir) / f"{stem}.json", logger_obj=logger))


def responses_file(stem: str, responses_dir: Path, doc: Optional[Mapping[str, Any]] = None) -> Path:
    """``<responses_dir>/<stem>.jsonl``, or the file of an earlier name of the role (the May tree
    has instrumentally_aligned_ai under aligned_artificial_intelligence)."""
    path = Path(responses_dir) / f"{stem}.jsonl"
    if path.exists():
        return path
    for old in renamed_stems(doc or {}):
        alt = Path(responses_dir) / f"{old}.jsonl"
        if alt.exists():
            logger.warning(f"{stem}: no {path.name} in {responses_dir}; using {alt.name} "
                           f"(the role's earlier name)")
            return alt
    raise FileNotFoundError(f"no responses for {stem} in {responses_dir}")


def assistant_text(resp: Mapping[str, Any]) -> str:
    """The response text, as step 3 takes it (the first assistant message)."""
    for msg in resp.get("conversation") or []:
        if msg.get("role") == "assistant":
            return msg.get("content") or ""
    return ""


def git_info(paths: Sequence[str] = ()) -> Tuple[Optional[str], Optional[List[str]]]:
    """``(HEAD sha, uncommitted changes among paths)``, or ``(None, None)`` without git."""
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True,
                             text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", *paths], cwd=REPO,
                               capture_output=True, text=True, check=True).stdout.splitlines()
    except (OSError, subprocess.CalledProcessError):
        return None, None
    return sha, [d for d in dirty if d.strip()]


# Code whose state a paid run depends on (a live run refuses while any is uncommitted).
DIRTY_CHECK_PATHS = (SCRIPT_REL, "pipeline/3_judge.py", "assistant_axis/judge.py",
                     "assistant_axis/openai_batch.py", "data_analysis/regenerate_role_instructions.py")


def template_mismatches(roles: Iterable[str], roles_dir: Path = ROLES_DIR) -> Optional[List[str]]:
    """Roles whose baked eval_prompt differs from ``ROLE_EVAL_PROMPT_TEMPLATE`` rendered with the
    role's prompt name and description (``build_eval_prompt(role_prompt_name(stem),
    description)``, as the generator writes it), or None when the template cannot be imported.
    The arms are derived from the baked text whatever this says."""
    try:
        from data_analysis.regenerate_role_instructions import build_eval_prompt, role_prompt_name
    except Exception as e:  # noqa: BLE001 -- the check is informational
        logger.warning(f"cannot import the role template ({type(e).__name__}: {e}); "
                       f"the A0-equals-template check is skipped")
        return None
    out = []
    for stem in roles:
        doc = load_role(stem, roles_dir)
        if build_eval_prompt(role_prompt_name(stem), doc.get("description", "")) != doc.get("eval_prompt"):
            out.append(stem)
    return out


# ---------------------------------------------------------------------------
# The plan of a run: roles, their arm templates and responses
# ---------------------------------------------------------------------------

@dataclass
class RolePlan:
    stem: str
    doc: Dict[str, Any]
    baked: str
    templates: Dict[str, str]
    responses_path: Optional[Path] = None
    responses: Optional[List[Dict[str, Any]]] = None
    responses_sha256: Optional[str] = None


def build_plan(roles: Sequence[str], arms: Sequence[str], *, roles_dir: Path = ROLES_DIR,
               responses_dir: Optional[Path] = None, model_name: str = DEFAULT_MODEL_NAME,
               limit: Optional[int] = None) -> List[RolePlan]:
    """Each role's file, its arm templates and (with ``responses_dir``) its responses (the first
    ``limit`` if given), read as step 3 reads them."""
    plans = []
    for stem in roles:
        doc = load_role(stem, roles_dir)
        baked = doc.get("eval_prompt")
        if not baked:
            raise ArmError(f"{stem}: the role file has no eval_prompt")
        templates = {arm: arm_template(arm, baked, model_name=model_name) for arm in arms}
        rp = RolePlan(stem=stem, doc=doc, baked=baked, templates=templates)
        if responses_dir is not None:
            path = responses_file(stem, Path(responses_dir), doc)
            responses = step3().load_responses(path)
            rp.responses = responses[:limit] if limit else responses
            rp.responses_path = path
            rp.responses_sha256 = _sha256_file(path)
        plans.append(rp)
    return plans


def filled_prompts(rp: RolePlan, arm: str, excluded: Mapping[str, Any]) -> List[Tuple[str, str]]:
    """``(key, prompt)`` for the role's responses not in ``excluded``: step 3's
    ``pending_prompts``."""
    return step3().pending_prompts(rp.responses or [], rp.templates[arm], dict(excluded),
                                   name=f"{arm}/{rp.stem}")


def request_body(prompt: str) -> Dict[str, Any]:
    """Step 3's request (``judge.chat_request_body`` with its model and max_tokens)."""
    return step3().chat_request_body(prompt, JUDGE_MODEL, MAX_TOKENS)


# ---------------------------------------------------------------------------
# Token counting and the estimate
# ---------------------------------------------------------------------------

class TokenCounter:
    """Billed prompt tokens of one request: tiktoken o200k_base (gpt-4.1-mini's encoding) when
    the environment has it, else characters / 4, plus the chat format's overhead."""

    def __init__(self, method: str = "auto"):
        self._enc = None
        self.method = "chars/4"
        if method in ("auto", "tiktoken"):
            try:
                import tiktoken
                self._enc = tiktoken.get_encoding(TOKENIZER)
                self.method = f"tiktoken {TOKENIZER}"
            except Exception as e:  # noqa: BLE001
                if method == "tiktoken":
                    raise
                logger.warning(f"tiktoken unavailable ({type(e).__name__}: {e}); counting "
                               f"characters / 4 (about 24% high on these prompts)")

    def prompt_tokens(self, prompt: str) -> int:
        if self._enc is not None:
            n = len(self._enc.encode(prompt, disallowed_special=()))
        else:
            n = math.ceil(len(prompt) / 4)
        return n + CHAT_OVERHEAD_TOKENS


def batch_prices() -> Tuple[float, float]:
    from assistant_axis.judge_pricing import BATCH_SUFFIX, price_for_model
    return price_for_model(JUDGE_MODEL + BATCH_SUFFIX)


def estimate_plan(plan: Sequence[RolePlan], arms: Sequence[str], *, counter: TokenCounter,
                  output_tokens: int = OUTPUT_TOKENS_PER_CALL,
                  excluded: Optional[Mapping[Tuple[str, str], Mapping[str, Any]]] = None
                  ) -> Dict[str, Any]:
    """Calls, prompt tokens, output tokens and dollars per arm and in total (batch prices).  A
    template shared by several arms (A0 and A0') is counted once and charged to each."""
    rate_in, rate_out = batch_prices()
    per_arm = {arm: {"calls": 0, "prompt_tokens": 0} for arm in arms}
    for rp in plan:
        by_tpl: Dict[str, List[str]] = defaultdict(list)
        for arm in arms:
            ex = (excluded or {}).get((arm, rp.stem), {})
            by_tpl[template_sha256(rp.templates[arm]) + json.dumps(sorted(ex))].append(arm)
        for arms_here in by_tpl.values():
            ex = (excluded or {}).get((arms_here[0], rp.stem), {})
            prompts = filled_prompts(rp, arms_here[0], ex)
            n_tok = sum(counter.prompt_tokens(p) for _, p in prompts)
            for arm in arms_here:
                per_arm[arm]["calls"] += len(prompts)
                per_arm[arm]["prompt_tokens"] += n_tok
    total = {"calls": 0, "prompt_tokens": 0, "output_tokens": 0, "usd": 0.0, "usd_if_max_output": 0.0}
    for arm, d in per_arm.items():
        d["output_tokens"] = d["calls"] * output_tokens
        d["usd"] = d["prompt_tokens"] * rate_in / 1e6 + d["output_tokens"] * rate_out / 1e6
        d["usd_if_max_output"] = (d["prompt_tokens"] * rate_in / 1e6
                                  + d["calls"] * MAX_TOKENS * rate_out / 1e6)
        for k in total:
            total[k] += d[k]
    return {
        "per_arm": per_arm, "total": total, "token_method": counter.method,
        "chat_overhead_tokens": CHAT_OVERHEAD_TOKENS, "output_tokens_per_call": output_tokens,
        "output_tokens_source": "the P5 canary of 2026-10-12 (30 role requests, 72.2 completion "
                                "tokens each; reports/pipeline/fix_batch_2026-10-12.md § 4)",
        "prices_per_mtok": {"input": rate_in, "output": rate_out,
                            "model": f"{JUDGE_MODEL}:batch"},
        "roles": [rp.stem for rp in plan], "arms": list(arms),
        "responses_per_role": {rp.stem: len(rp.responses or []) for rp in plan},
        "over_flag": total["usd"] > COST_FLAG_USD, "flag_usd": COST_FLAG_USD,
        "cap_usd": COST_CAP_USD,
    }


def estimate_lines(est: Mapping[str, Any]) -> List[str]:
    lines = [f"{'arm':<5} {'calls':>8} {'prompt tok':>12} {'output tok':>11} {'USD':>8}"]
    for arm, d in est["per_arm"].items():
        lines.append(f"{ARM_BY_ID[arm].label:<5} {d['calls']:>8,} {d['prompt_tokens']:>12,} "
                     f"{d['output_tokens']:>11,} {d['usd']:>8.2f}")
    t = est["total"]
    lines.append(f"{'total':<5} {t['calls']:>8,} {t['prompt_tokens']:>12,} "
                 f"{t['output_tokens']:>11,} {t['usd']:>8.2f}")
    lines.append(f"tokens: {est['token_method']} + {est['chat_overhead_tokens']} per request; output "
                 f"{est['output_tokens_per_call']} per call ({est['output_tokens_source']}); "
                 f"{est['prices_per_mtok']['model']} ${est['prices_per_mtok']['input']}/"
                 f"${est['prices_per_mtok']['output']} per million")
    lines.append(f"if every reply ran to max_tokens ({MAX_TOKENS}): ${t['usd_if_max_output']:.2f}")
    if est["over_flag"]:
        lines.append(f"*** OVER ${est['flag_usd']:.0f}: ${t['usd']:.2f} (Roger's cap is "
                     f"${est['cap_usd']:.0f}) ***")
    else:
        lines.append(f"within ${est['flag_usd']:.0f} (Roger's cap ${est['cap_usd']:.0f})")
    return lines


# ---------------------------------------------------------------------------
# Batch transport: step 3's runner, plus submit-and-exit
# ---------------------------------------------------------------------------

class ExperimentBatchRunner(OpenAIBatchRunner):
    """:class:`OpenAIBatchRunner` with :meth:`submit_only`, for ``--batch-no-wait``."""

    async def submit_only(self, chunks: Sequence[Path]) -> List[str]:
        """Submit ``chunks`` and return without waiting for results.  A chunk the queue limit
        refuses stops the submission: it and the chunks after it are rebuilt by the next judge
        run (``resume`` discards chunks never submitted)."""
        submitted: List[str] = []
        for i, path in enumerate(chunks):
            batch = await self._wait_validation(await self._submit(path))
            rec = self._record(path)
            if _get(batch, "status") == "failed":
                if TOKEN_LIMIT_CODE in _error_codes(batch):
                    rec.pop("batch_id", None)
                    rec.pop("collected", None)
                    rec["status"] = "failed"
                    self._save_state()
                    self.log.warning(f"{path.name}: the organisation's queue limit is reached; "
                                     f"{len(chunks) - i} chunk(s) not submitted: the next judge "
                                     f"run submits them")
                    break
                await self._delete_files(rec.get("input_file_id"))
                rec.update(status="failed", collected=True)
                self._save_state()
                raise BatchFailedError(f"batch {batch.id} ({path.name}) failed validation: "
                                       f"{_error_text(batch)}")
            submitted.append(batch.id)
        return submitted


def make_client():
    """The OpenAI client of a live run (tests replace it)."""
    import openai
    return openai.AsyncOpenAI()


# ---------------------------------------------------------------------------
# Collecting results
# ---------------------------------------------------------------------------

RUN_RECORD_NAME = "run_record.json"
USAGE_NAME = "usage.json"
STATE_NAME = "batch_state.json"
WORK_DIRNAME = "_batches"
REPLIES_DIRNAME = "replies"


def score_path(out_dir: Path, arm: str, role: str) -> Path:
    return Path(out_dir) / arm / f"{role}.json"


def replies_path(out_dir: Path, arm: str, role: str) -> Path:
    return Path(out_dir) / REPLIES_DIRNAME / arm / f"{role}.jsonl"


def read_replies(out_dir: Path, arm: str, role: str) -> Dict[str, Dict[str, Any]]:
    path = replies_path(out_dir, arm, role)
    if not path.exists():
        return {}
    return {r["key"]: r for r in read_jsonl_with_retry(path, logger_obj=logger) if "key" in r}


def read_reply(text: Optional[str], finish_reason: Optional[str]) -> Tuple[Optional[int], Optional[str]]:
    """``(score, problem)`` of one reply by step 3's reader (``score_reply``): exactly one
    ``SCORE:`` marker, a reply cut at max_tokens unparseable.  ``problem`` is step 3's reason
    for an unparseable reply (``no_marker``, ``several_markers``, ``out_of_range``,
    ``truncated``, ``no_reply``)."""
    j3 = step3()
    before = Counter(j3.REPLY_PROBLEMS)
    score = j3.score_reply(text, finish_reason)
    if score is not None:
        return score, None
    grown = j3.REPLY_PROBLEMS - before
    return None, next(iter(grown), "unparseable")


class Collector:
    """Turns batch results into score files, reply records and usage records, made durable at
    every collected batch (``flush``, which the runner calls before marking a batch collected).

    A result whose reply is already recorded with the same text and token count is a batch
    collected a second time (a crash between the flush and the state write): it is neither
    charged nor recorded again.  A different reply for a key that already has a score is a
    duplicate request: charged (it was paid for), the first score kept."""

    def __init__(self, out_dir: Path, arms: Sequence[str]):
        from assistant_axis.judge_pricing import BATCH_SUFFIX, MultiModelUsage
        self.out_dir = Path(out_dir)
        self.batch_model = JUDGE_MODEL + BATCH_SUFFIX
        self.prior_total = MultiModelUsage.load_or_create(self.out_dir / USAGE_NAME)
        self.prior_arm = {a: MultiModelUsage.load_or_create(self.out_dir / a / USAGE_NAME)
                          for a in ARM_IDS}
        self.run_total = MultiModelUsage()
        self.run_arm = {a: MultiModelUsage() for a in ARM_IDS}
        self.counts: Dict[str, Counter] = {a: Counter() for a in ARM_IDS}
        self._known: Dict[Tuple[str, str], Dict[str, Dict[str, Any]]] = {}
        self._new: Dict[Tuple[str, str], Dict[str, Dict[str, Any]]] = defaultdict(dict)

    def _cell(self, arm: str, role: str) -> Dict[str, Dict[str, Any]]:
        if (arm, role) not in self._known:
            self._known[(arm, role)] = read_replies(self.out_dir, arm, role)
        return self._known[(arm, role)]

    def on_result(self, cid: str, body: Optional[dict], error: Optional[str]) -> None:
        arm, role, key = parse_cid(cid)
        c = self.counts[arm]
        if body is None:
            c["batch_error"] += 1      # left unanswered; a rerun submits it again
            return
        u = body.get("usage") or {}
        pt, ct = int(u.get("prompt_tokens") or 0), int(u.get("completion_tokens") or 0)
        choices = body.get("choices") or []
        text = (choices[0].get("message") or {}).get("content") if choices else None
        finish = choices[0].get("finish_reason") if choices else None
        cell = self._cell(arm, role)
        old = self._new[(arm, role)].get(key) or cell.get(key)
        if old is not None and old.get("text") == text and old.get("completion_tokens") == ct:
            c["recollected"] += 1
            return
        self.run_total.charge(self.batch_model, pt, ct)
        self.run_arm[arm].charge(self.batch_model, pt, ct)
        score, problem = read_reply(text, finish)
        c["attempted"] += 1
        if score is not None:
            c["parsed"] += 1
        else:
            c[f"problem:{problem}"] += 1
        if old is not None and old.get("score") is not None:
            c["duplicate"] += 1
            logger.warning(f"{cid}: a second reply for a scored response (a duplicate request); "
                           f"charged, the first score kept")
            return
        self._new[(arm, role)][key] = {
            "key": key, "score": score, "problem": problem, "finish_reason": finish,
            "text": text, "prompt_tokens": pt, "completion_tokens": ct, "collected_at": _now()}

    def flush(self) -> None:
        j3 = step3()
        for (arm, role), new in self._new.items():
            if not new:
                continue
            merged = {**self._cell(arm, role), **new}
            write_jsonl(list(merged.values()), replies_path(self.out_dir, arm, role),
                        logger_obj=logger)
            self._known[(arm, role)] = merged
            scores = {k: r["score"] for k, r in new.items() if r["score"] is not None}
            if scores:
                path = score_path(self.out_dir, arm, role)
                existing = j3.load_scores(path, strict=True)
                j3.merge_scores(path, {k: v for k, v in scores.items() if k not in existing})
        self._new.clear()
        for arm in ARM_IDS:
            if self.run_arm[arm].n_calls:
                j3.write_usage(self.out_dir / arm / USAGE_NAME, self.prior_arm[arm], self.run_arm[arm])
        if self.run_total.n_calls or not (self.out_dir / USAGE_NAME).exists():
            j3.write_usage(self.out_dir / USAGE_NAME, self.prior_total, self.run_total)


def cumulative_parse_counts(out_dir: Path, arms: Sequence[str], roles: Sequence[str]
                            ) -> Dict[str, Tuple[int, int]]:
    """``arm -> (parsed, recorded)`` over every reply recorded in the run directory."""
    out = {}
    for arm in arms:
        n_ok = n = 0
        for role in roles:
            for rec in read_replies(out_dir, arm, role).values():
                n += 1
                n_ok += rec.get("score") is not None
        out[arm] = (n_ok, n)
    return out


# ---------------------------------------------------------------------------
# The run record
# ---------------------------------------------------------------------------

def _new_record() -> Dict[str, Any]:
    return {"experiment": EXPERIMENT, "script": SCRIPT_REL, "wording_version": WORDING_VERSION,
            "plan": "reports/pipeline/plan_role_rubric_experiment.md", "created_at": _now(),
            "arms": {}, "responses": {"files": {}}, "batches": [], "runs": []}


def load_record(out_dir: Path) -> Optional[Dict[str, Any]]:
    path = Path(out_dir) / RUN_RECORD_NAME
    if not path.exists():
        return None
    return json.loads(read_text_with_retry(path, logger_obj=logger))


def record_problems(rec: Mapping[str, Any], plan: Sequence[RolePlan], arms: Sequence[str]) -> List[str]:
    """Why a run directory cannot take this run: an arm's template or a response file differs
    from what the directory was judged with, or another judge request."""
    problems = []
    judge = rec.get("judge") or {}
    if judge and (judge.get("model") != JUDGE_MODEL or judge.get("max_completion_tokens") != MAX_TOKENS):
        problems.append(f"judge {judge.get('model')} / {judge.get('max_completion_tokens')} recorded, "
                        f"not {JUDGE_MODEL} / {MAX_TOKENS}")
    for rp in plan:
        for arm in arms:
            old = ((rec.get("arms") or {}).get(arm) or {}).get("template_sha256", {}).get(rp.stem)
            new = template_sha256(rp.templates[arm])
            if old and old != new:
                problems.append(f"{arm}/{rp.stem}: template {old[:12]} recorded, {new[:12]} now")
        old_f = ((rec.get("responses") or {}).get("files") or {}).get(rp.stem) or {}
        if old_f.get("sha256") and rp.responses_sha256 and old_f["sha256"] != rp.responses_sha256:
            problems.append(f"{rp.stem}: responses {old_f['sha256'][:12]} recorded, "
                            f"{rp.responses_sha256[:12]} now ({rp.responses_path})")
    return problems


def update_record(out_dir: Path, plan: Sequence[RolePlan], arms: Sequence[str], *,
                  model_name: str, model_name_source: str, responses_dir: Path,
                  runner: Optional[OpenAIBatchRunner] = None,
                  run_entry: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    rec = load_record(out_dir) or _new_record()
    rec["updated_at"] = _now()
    rec["wording_version"] = WORDING_VERSION
    rec["judge"] = {"model": JUDGE_MODEL, "max_completion_tokens": MAX_TOKENS,
                    "temperature": "the provider default (1), not sent, as step 3",
                    "messages": "one user message, the filled template",
                    "reader": "pipeline/3_judge.py score_reply: parse_judge_score(require_marker="
                              "True), finish_reason 'length' unparseable",
                    "step3_rubric_version": step3().JUDGE_RUBRIC_VERSION,
                    "transport": "OpenAI Batch API (assistant_axis/openai_batch.py)"}
    rec["model_name"] = {"value": model_name, "source": model_name_source, "used_by": "A2"}
    rec["sample"] = {"strata": {k: list(v) for k, v in SAMPLE_STRATA.items()},
                     "provenance": SAMPLE_PROVENANCE, "ai_persona_roles": list(AI_PERSONA_ROLES)}
    for arm in arms:
        entry = rec["arms"].setdefault(arm, {})
        entry.update(label=ARM_BY_ID[arm].label, summary=ARM_BY_ID[arm].summary)
        hashes = entry.setdefault("template_sha256", {})
        for rp in plan:
            hashes[rp.stem] = template_sha256(rp.templates[arm])
    rec["responses"]["dir"] = str(responses_dir)
    for rp in plan:
        if rp.responses_path is not None:
            rec["responses"]["files"][rp.stem] = {
                "path": str(rp.responses_path), "sha256": rp.responses_sha256,
                "n_used": len(rp.responses or [])}
    if runner is not None:
        rec["batches"] = [
            {k: r.get(k) for k in ("batch_id", "n_requests", "submitted_at", "collected_at",
                                   "status", "n_answered", "recovered", "adopted")
             if r.get(k) is not None} | {"chunk": Path(r["path"]).name}
            for r in runner.state["chunks"]]
    if run_entry is not None:
        runs = rec.setdefault("runs", [])
        if runs and runs[-1].get("run_id") == run_entry.get("run_id"):
            runs[-1] = run_entry
        else:
            runs.append(run_entry)
    _write_json(Path(out_dir) / RUN_RECORD_NAME, rec)
    return rec


# ---------------------------------------------------------------------------
# judge
# ---------------------------------------------------------------------------

def excluded_keys(out_dir: Path, arm: str, role: str, *, rejudge_unparseable: bool) -> Dict[str, int]:
    """Keys not to request again: scored, and (unless ``rejudge_unparseable``) answered with an
    unparseable reply, which was paid for."""
    excluded = dict(step3().load_scores(score_path(out_dir, arm, role), strict=True))
    if not rejudge_unparseable:
        for key, rec in read_replies(out_dir, arm, role).items():
            if rec.get("score") is None:
                excluded.setdefault(key, -1)
    return excluded


def inflight_ids_on_disk(out_dir: Path) -> set:
    """``custom_id`` of every request in a batch the state file records as submitted and not
    collected, read from the chunk files (no network), so that the cost gate of a resumed run
    does not count them again.  A chunk file that is gone is not counted (the gate then errs
    high)."""
    path = Path(out_dir) / STATE_NAME
    if not path.exists():
        return set()
    from assistant_axis.openai_batch import _read_custom_ids
    ids: set = set()
    for rec in json.loads(read_text_with_retry(path, logger_obj=logger)).get("chunks", []):
        if rec.get("batch_id") and not rec.get("collected") and Path(rec["path"]).exists():
            ids.update(_read_custom_ids(Path(rec["path"])))
    return ids


def iter_requests(plan: Sequence[RolePlan], arms: Sequence[str],
                  excluded: Mapping[Tuple[str, str], Mapping[str, Any]]
                  ) -> Iterator[Tuple[str, Dict[str, Any]]]:
    """``(custom_id, body)`` for every pending (arm, role, response), arm by arm, so that A0 and
    A0' go in different batches."""
    for arm in arms:
        for rp in plan:
            for key, prompt in filled_prompts(rp, arm, excluded.get((arm, rp.stem), {})):
                yield make_cid(arm, rp.stem, key), request_body(prompt)


def _selection(args) -> Tuple[List[str], List[str]]:
    roles = list(args.roles or SAMPLE)
    arms = list(args.arms or ARM_IDS)
    unknown = [a for a in arms if a not in ARM_BY_ID]
    if unknown:
        raise SystemExit(f"unknown arm(s) {unknown}; arms: {', '.join(ARM_IDS)}")
    return roles, arms


async def adopt_batches(runner: ExperimentBatchRunner, client, batch_ids: Sequence[str]) -> None:
    """Record batches the state file does not have (a lost state file), so that ``resume`` reads
    their requests back from the service and the run collects them."""
    known = {r.get("batch_id") for r in runner.state["chunks"]}
    for bid in batch_ids:
        if bid in known:
            logger.info(f"batch {bid} is already in {runner.state_path.name}")
            continue
        batch = await client.batches.retrieve(bid)
        status, fid = _get(batch, "status"), _get(batch, "input_file_id")
        if status == "failed" or not fid:
            raise SystemExit(f"batch {bid} cannot be adopted (status {status}, input file {fid})")
        rec = runner._record(runner.work_dir / f"adopted_{bid}.jsonl")
        rec.update(batch_id=bid, input_file_id=fid, status=status, submitted_at=_now(), adopted=True)
        logger.info(f"adopting batch {bid} ({status})")
    runner._save_state()


def _check_adopted(runner: ExperimentBatchRunner) -> None:
    from assistant_axis.openai_batch import _read_custom_ids
    for rec in runner.state["chunks"]:
        if rec.get("adopted") and not rec.get("collected") and Path(rec["path"]).exists():
            ids = _read_custom_ids(Path(rec["path"]))
            try:
                for cid in ids:
                    parse_cid(cid)
            except ValueError as e:
                raise SystemExit(f"batch {rec['batch_id']} is not this experiment's: {e}")
            rec["n_requests"] = len(ids)
    runner._save_state()


async def judge_live(args, plan: List[RolePlan], arms: List[str], *, client, model_name: str,
                     model_name_source: str, responses_dir: Path) -> int:
    out_dir = Path(args.out_dir)
    runner = ExperimentBatchRunner(
        client, out_dir / WORK_DIRNAME, out_dir / STATE_NAME, poll_seconds=args.batch_poll_seconds,
        validation_poll_seconds=min(10.0, args.batch_poll_seconds),
        metadata={"source": SCRIPT_REL, "out_dir": str(out_dir)[-200:]}, logger=logger)
    if args.batch_id:
        await adopt_batches(runner, client, args.batch_id)
    inflight = await runner.resume()
    _check_adopted(runner)
    other = {m: n for m, n in runner.inflight_models().items() if m != JUDGE_MODEL}
    if other:
        logger.error(f"batches in flight were requested with {sorted(other)}, not {JUDGE_MODEL}")
        return 2
    excluded = {(arm, rp.stem): excluded_keys(out_dir, arm, rp.stem,
                                              rejudge_unparseable=args.rejudge_unparseable)
                for arm in arms for rp in plan}
    if args.collect_only:
        chunks: List[Path] = []
    else:
        chunks = runner.write_chunks(((cid, body) for cid, body in iter_requests(plan, arms, excluded)
                                      if cid not in inflight), max_requests=args.batch_requests)
    n_new = sum(r.get("n_requests", 0) for r in runner.state["chunks"]
                if r["path"] in {str(p) for p in chunks})
    logger.info(f"{n_new} new requests in {len(chunks)} batch(es)"
                + (f"; {len(inflight)} requests in batches already submitted" if inflight else ""))
    sha, dirty = git_info(DIRTY_CHECK_PATHS)
    run_entry = {"run_id": _now(), "started_at": _now(), "argv": sys.argv[1:], "git_sha": sha,
                 "uncommitted": dirty,
                 "mode": ("no-wait" if args.batch_no_wait else "collect-only" if args.collect_only
                          else "submit-and-collect"),
                 "arms": arms, "roles": [rp.stem for rp in plan], "n_new_requests": n_new,
                 "n_inflight_at_start": len(inflight)}
    record_kw = dict(model_name=model_name, model_name_source=model_name_source,
                     responses_dir=responses_dir)
    update_record(out_dir, plan, arms, runner=runner, run_entry=run_entry, **record_kw)

    if args.batch_no_wait:
        submitted = await runner.submit_only(chunks)
        run_entry.update(finished_at=_now(), submitted=submitted)
        update_record(out_dir, plan, arms, runner=runner, run_entry=run_entry, **record_kw)
        logger.info(f"submitted {len(submitted)} batch(es): {', '.join(submitted) or '(none)'}; "
                    f"collect with the same command and --collect-only (or without "
                    f"--batch-no-wait)")
        return 0

    collector = Collector(out_dir, arms)

    def flush() -> None:
        collector.flush()
        update_record(out_dir, plan, arms, runner=runner, **record_kw)

    unanswered = await runner.run(chunks, collector.on_result, flush)
    collector.flush()

    by_arm_left = Counter(parse_cid(cid)[0] for cid in unanswered)
    cumulative = cumulative_parse_counts(out_dir, ARM_IDS, [rp.stem for rp in plan])
    from assistant_axis.judge import PARSE_RATE_LOUD_THRESHOLD, warn_if_low_parse_rate
    reasons = []
    counts_out = {}
    for arm in arms:
        c = collector.counts[arm]
        warn_if_low_parse_rate(label=f"{EXPERIMENT}:{arm}:{JUDGE_MODEL}", n_ok=c["parsed"],
                               n_total=c["attempted"], logger_obj=logger)
        n_ok, n = cumulative[arm]
        warn_if_low_parse_rate(label=f"{EXPERIMENT}:{arm}:{JUDGE_MODEL}:cumulative", n_ok=n_ok,
                               n_total=n, logger_obj=logger)
        if n and n_ok / n < PARSE_RATE_LOUD_THRESHOLD:
            reasons.append(f"{arm} parse rate {n_ok}/{n}")
        problems = {k.split(":", 1)[1]: v for k, v in c.items() if k.startswith("problem:")}
        if problems:
            logger.info(f"{arm}: unparseable replies: {problems}")
        counts_out[arm] = dict(c) | {"unanswered": by_arm_left.get(arm, 0),
                                     "cumulative_parsed": n_ok, "cumulative_replies": n}
    if unanswered:
        reasons.append(f"{len(unanswered)} requests unanswered by their batches (a rerun submits them)")
    logger.info(collector.run_total.log_line("[usage] this run"))
    from assistant_axis.judge_pricing import MultiModelUsage
    logger.info(MultiModelUsage.load_or_create(out_dir / USAGE_NAME)
                .log_line(f"[usage] cumulative ({out_dir / USAGE_NAME})"))
    run_entry.update(finished_at=_now(), counts=counts_out,
                     usage_this_run=collector.run_total.as_dict(), incomplete=reasons)
    update_record(out_dir, plan, arms, runner=runner, run_entry=run_entry, **record_kw)
    if reasons:
        logger.error("Not complete: " + "; ".join(reasons))
        return 1
    return 0


def judge_dry_run(args, plan: List[RolePlan], arms: List[str],
                  excluded: Mapping[Tuple[str, str], Mapping[str, Any]], est: Mapping[str, Any]) -> int:
    out = Path(args.out_dir) / "dry_run"
    show = [r for r in RENDER_ROLES if r in {rp.stem for rp in plan}] or [rp.stem for rp in plan][:2]
    counts: Dict[str, Dict[str, int]] = {arm: {} for arm in arms}
    sample: List[str] = []
    first_prompt = None
    for arm in arms:
        for rp in plan:
            pending = filled_prompts(rp, arm, excluded.get((arm, rp.stem), {}))
            counts[arm][rp.stem] = len(pending)
            if pending and rp.stem in show:
                body = request_body(pending[0][1])
                sample.append(json.dumps({"custom_id": make_cid(arm, rp.stem, pending[0][0]),
                                          "method": "POST", "url": "/v1/chat/completions",
                                          "body": body}, ensure_ascii=False))
                first_prompt = first_prompt or pending[0][1]
    total = sum(sum(v.values()) for v in counts.values())
    atomic_write_text("\n".join(sample) + "\n", out / "requests_sample.jsonl", logger_obj=logger)
    n_batches = -(-total // max(1, args.batch_requests))
    summary = {"dry_run_at": _now(), "total_requests": total,
               "per_arm": {arm: sum(v.values()) for arm, v in counts.items()},
               "per_arm_role": counts, "batches": n_batches, "batch_requests": args.batch_requests,
               "estimate": est, "sample_file": str(out / "requests_sample.jsonl")}
    _write_json(out / "summary.json", summary)
    logger.info("Dry run: nothing submitted")
    for arm in arms:
        logger.info(f"  {ARM_BY_ID[arm].label:<4} {summary['per_arm'][arm]:>7,} requests")
    logger.info(f"Total {total:,} requests, about {n_batches} batch(es) of up to {args.batch_requests:,}")
    for line in estimate_lines(est):
        logger.info(line)
    if first_prompt:
        logger.info("Sample prompt (%s):\n%s", sample[0][:60] if sample else "", first_prompt)
    logger.info(f"Sample requests: {out / 'requests_sample.jsonl'}; summary: {out / 'summary.json'}")
    return 0


def cmd_judge(args) -> int:
    if args.batch_no_wait and args.collect_only:
        raise SystemExit("--batch-no-wait submits and --collect-only does not: choose one")
    roles, arms = _selection(args)
    responses_dir = Path(args.responses_dir)
    out_dir = Path(args.out_dir)
    if args.tmpdir:
        from assistant_axis.tmpfs import setup_tmpdir
        setup_tmpdir(args.tmpdir)
    model_name, model_name_source = resolve_model_name(args.model_name, responses_dir)
    plan = build_plan(roles, arms, roles_dir=Path(args.roles_dir), responses_dir=responses_dir,
                      model_name=model_name, limit=args.limit_responses)
    logger.info(f"{len(plan)} roles, arms {', '.join(arms)}; A2's model name {model_name!r} "
                f"({model_name_source})")
    mism = template_mismatches(roles, Path(args.roles_dir))
    if mism:
        logger.warning(f"baked eval_prompt differs from ROLE_EVAL_PROMPT_TEMPLATE for {mism}; "
                       f"their arms are derived from the baked text")
    rec = load_record(out_dir)
    if rec is not None:
        problems = record_problems(rec, plan, arms)
        if problems:
            logger.error(f"{out_dir / RUN_RECORD_NAME} was judged with other wordings or "
                         f"responses; use a fresh --out-dir: " + "; ".join(problems[:10]))
            return 2
    excluded = {(arm, rp.stem): excluded_keys(out_dir, arm, rp.stem,
                                              rejudge_unparseable=args.rejudge_unparseable)
                for arm in arms for rp in plan}
    # What would be submitted now: the pending requests less those in batches already in flight.
    to_send = {k: dict(v) for k, v in excluded.items()}
    for cid in inflight_ids_on_disk(out_dir):
        arm, role, key = parse_cid(cid)
        if (arm, role) in to_send:
            to_send[(arm, role)].setdefault(key, -2)
    if args.dry_run or not args.collect_only:
        est = estimate_plan(plan, arms, counter=TokenCounter(args.tokenizer), excluded=to_send)
    else:
        est = None
    if args.dry_run:
        return judge_dry_run(args, plan, arms, to_send, est)

    # A paid run from here on.
    if est is not None:
        usd = est["total"]["usd"]
        for line in estimate_lines(est):
            logger.info(line)
        if usd > args.budget_usd:
            logger.error(f"the estimate ${usd:.2f} is over --budget-usd ${args.budget_usd:.2f}; "
                         f"nothing submitted")
            return 2
        if usd > CONFIRM_ABOVE_USD and not args.confirm_expensive:
            logger.error(f"the estimate ${usd:.2f} is over ${CONFIRM_ABOVE_USD:.0f}: quote the "
                         f"parameters to Roger, and pass --confirm-expensive once he has agreed; "
                         f"nothing submitted")
            return 2
    role_files = [(Path(args.roles_dir) / f"{r}.json").resolve() for r in roles]
    _, dirty = git_info(list(DIRTY_CHECK_PATHS)
                        + [str(p.relative_to(REPO)) for p in role_files if p.is_relative_to(REPO)])
    if dirty and not args.allow_dirty:
        logger.error(f"uncommitted changes in files the run depends on: {dirty}; commit them "
                     f"(or pass --allow-dirty); nothing submitted")
        return 2
    from dotenv import load_dotenv
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY not found")
        return 1
    problem = step3().check_judge_model(JUDGE_MODEL, batch=True)
    if problem:
        logger.error(problem)
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)
    j3 = step3()
    lock = j3.ScoresDirLock(out_dir, force=args.force_unlock)
    try:
        lock.acquire()
    except j3.LockHeldError as e:
        logger.error(str(e))
        return 1
    try:
        return asyncio.run(judge_live(args, plan, arms, client=make_client(), model_name=model_name,
                                      model_name_source=model_name_source,
                                      responses_dir=responses_dir))
    finally:
        lock.release()


# ---------------------------------------------------------------------------
# estimate
# ---------------------------------------------------------------------------

def cmd_estimate(args) -> int:
    roles, arms = _selection(args)
    responses_dir = Path(args.responses_dir)
    model_name, _ = resolve_model_name(args.model_name, responses_dir)
    plan = build_plan(roles, arms, roles_dir=Path(args.roles_dir), responses_dir=responses_dir,
                      model_name=model_name, limit=args.limit_responses)
    est = estimate_plan(plan, arms, counter=TokenCounter(args.tokenizer),
                        output_tokens=args.output_tokens)
    est["responses_dir"] = str(responses_dir)
    est["estimated_at"] = _now()
    for line in estimate_lines(est):
        print(line)
    if args.json_out:
        _write_json(Path(args.json_out), est)
        print(f"wrote {args.json_out}")
    return 0


# ---------------------------------------------------------------------------
# render: arm_wordings.md
# ---------------------------------------------------------------------------

def _link(target: Path, doc_dir: Path, text: Optional[str] = None) -> str:
    rel = os.path.relpath(Path(target), Path(doc_dir)).replace(os.sep, "/").replace(" ", "%20")
    if not rel.startswith("."):
        rel = "./" + rel
    return f"[{text or Path(target).name}]({rel})"


def _role_link(stem: str, doc_dir: Path, roles_dir: Path = ROLES_DIR) -> str:
    return _link(Path(roles_dir) / f"{stem}.json", doc_dir, stem)


def _fence(text: str, info: str = "text") -> str:
    longest = max((len(m.group(0)) for m in re.finditer(r"`+", text)), default=0)
    f = "`" * max(3, longest + 1)
    return f"{f}{info}\n{text}\n{f}"


def _sentence_lines(text: str) -> List[str]:
    """The text split at line ends and sentence ends, so that a diff names the sentence."""
    out = []
    for line in text.split("\n"):
        out.extend(re.split(r"(?<=\.) (?=[A-Z])", line))
    return out


def arm_diff(base: str, other: str, arm: str) -> str:
    lines = difflib.unified_diff(_sentence_lines(base), _sentence_lines(other), fromfile="A0",
                                 tofile=ARM_BY_ID[arm].label, lineterm="", n=1)
    return "\n".join(lines)


def _diff_body(diff: str) -> str:
    """A diff without its role-specific header lines, for comparing two roles' diffs."""
    return "\n".join(l for l in diff.splitlines() if not l.startswith(("---", "+++", "@@")))


def pick_render_response(responses: Sequence[Mapping[str, Any]], may_scores: Mapping[str, int]
                         ) -> Tuple[Mapping[str, Any], Optional[int]]:
    """The response the rendered prompts are filled with: the first one May scored 2 (the
    boundary the experiment is about), else the first."""
    j3 = step3()
    for r in responses:
        if may_scores.get(j3.response_key(r)) == 2:
            return r, 2
    first = responses[0]
    return first, may_scores.get(j3.response_key(first))


def _may_shares(stem: str, roles_dir: Path, scores_dir: Path) -> Optional[Tuple[float, float, int]]:
    doc = load_role(stem, roles_dir)
    for s in [stem] + renamed_stems(doc):
        p = Path(scores_dir) / f"{s}.json"
        if p.exists():
            d = json.loads(p.read_text())
            if d:
                v = list(d.values())
                return sum(x == 2 for x in v) / len(v), sum(x == 3 for x in v) / len(v), len(v)
    return None


def render_document(*, roles_dir: Path, responses_dir: Path, may_scores_dir: Path,
                    model_name: str, model_name_source: str, doc_path: Path,
                    render_roles: Sequence[str] = RENDER_ROLES,
                    estimate: Optional[Mapping[str, Any]] = None) -> str:
    j3 = step3()
    doc_dir = doc_path.parent
    plans = {rp.stem: rp for rp in build_plan(list(render_roles), ARM_IDS, roles_dir=roles_dir,
                                              responses_dir=responses_dir, model_name=model_name)}
    mism = template_mismatches(SAMPLE, roles_dir)
    L: List[str] = []
    a = L.append
    a("# Role-judge rubric experiment: the arms' wording")
    a("")
    a(f"**Status {datetime.now(timezone.utc).date().isoformat()}: built, nothing spent.**  This is "
      f"what Roger reviews before the paid run: every arm's change against the current rubric, and "
      f"the prompt each arm sends, exactly as the judge receives it.  Written by "
      f"{_link(REPO / SCRIPT_REL, doc_dir)} `render` (wording version {WORDING_VERSION}); the plan "
      f"is {_link(PLAN_DOC, doc_dir)}.")
    a("")
    a("## Terms")
    a("")
    a("- **Rubric**: the judge prompt of a role, the `eval_prompt` field of its file under "
      f"{_link(roles_dir, doc_dir, 'data/roles/instructions/')}, rendered from "
      f"`ROLE_EVAL_PROMPT_TEMPLATE` in "
      f"{_link(REPO / 'data_analysis' / 'regenerate_role_instructions.py', doc_dir)}.  Step 3 "
      f"({_link(REPO / 'pipeline' / '3_judge.py', doc_dir)}) sends it once per response and reads a "
      f"score 0-3; step 4 ({_link(REPO / 'pipeline' / '4_vectors.py', doc_dir)}) averages only the "
      f"responses scored 3 into the role's vector.")
    a("- **Arm**: one version of the rubric, judged on the same responses as every other arm.  "
      "**A0** is the current rubric; **A0'** is A0 judged a second time, independently (the judge "
      "samples at temperature 1), so that A0 against A0' measures the judge's own noise, the "
      "**noise floor** every other arm is read against.")
    a("- **Level**: one of the rubric's four scores (0-3).  **Boundary flip**: a response that one "
      "arm scores 3 and the other below 3, so it enters the role vector under one rubric and not "
      "the other.")
    a("- **AI-persona roles**: the five roles that are themselves an AI or close to one "
      f"({', '.join(_role_link(r, doc_dir, roles_dir) for r in AI_PERSONA_ROLES)}), where the "
      "plan (§ 1b) found the rubric's 'identifies as itself (an AI assistant...)' test wrong-footed.")
    a("")
    a("## The judge request")
    a("")
    a(f"Step 3's, unchanged: model `{JUDGE_MODEL}`, `max_completion_tokens` {MAX_TOKENS}, the "
      f"provider's default temperature (1, not sent), one user message holding the filled rubric, "
      f"through the OpenAI Batch API "
      f"({_link(REPO / 'assistant_axis' / 'openai_batch.py', doc_dir)}).  A reply is read by step "
      f"3's `score_reply`: exactly one `SCORE: <int>` line is the answer, and a reply with none or "
      f"several, or cut at {MAX_TOKENS} tokens, is unparseable.  Every arm ends with the same "
      f"closing line, so that reader applies to all of them.  A request body, with the prompt "
      f"elided:")
    a("")
    a(_fence(json.dumps(j3.chat_request_body("<the filled rubric>", JUDGE_MODEL, MAX_TOKENS),
                        indent=2), "json"))
    a("")
    a("## A0 is the template")
    a("")
    if mism is None:
        a("Not checked: the template could not be imported.")
    elif not mism:
        a(f"For all {len(SAMPLE)} sampled roles the baked `eval_prompt` equals "
          "`ROLE_EVAL_PROMPT_TEMPLATE` rendered with the role's prompt name and description "
          "(`build_eval_prompt(role_prompt_name(stem), description)`), so A0 is the template and "
          "every arm is one edit of it.  (The test "
          f"{_link(REPO / 'data_analysis' / 'tests' / 'test_role_rubric_experiment.py', doc_dir)} "
          "checks it.)")
    else:
        a(f"The baked text differs from the template for: {', '.join(mism)}.  Their arms are "
          "derived from the baked text.")
    a("")
    a("## The sample")
    a("")
    a(f"30 roles, chosen by the coordinator on 2026-10-22 by each role's share of responses that "
      f"step 3 scored 2 in the May 2026 tree ({_link(may_scores_dir, doc_dir, 'the May scores')}): "
      f"the five AI-persona roles of the plan's § 1b "
      f"({_role_link('instrumentally_aligned_ai', doc_dir, roles_dir)} was "
      f"aligned_artificial_intelligence in May, and its May responses are under that name), the "
      f"nine roles most often held at level 2 (the ten highest shares less the aligned AI), eight "
      f"at the median share (about 7%) and eight with no response at level 2.  This is the plan's "
      f"'30 roles' option; every arm is judged on all of each role's responses.")
    a("")
    a("| group | role | May share at level 2 | May share at 3 |")
    a("|---|---|---|---|")
    for stratum, roles in SAMPLE_STRATA.items():
        for r in roles:
            sh = _may_shares(r, roles_dir, may_scores_dir) if Path(may_scores_dir).is_dir() else None
            l2, l3 = (f"{sh[0]:.1%}", f"{sh[1]:.1%}") if sh else ("", "")
            a(f"| {STRATUM_LABELS[stratum]} | {_role_link(r, doc_dir, roles_dir)} | {l2} | {l3} |")
    a("")
    a("## The arms")
    a("")
    a("| arm | what changes |")
    a("|---|---|")
    for arm in ARMS:
        a(f"| {arm.label} | {arm.summary} |")
    a("")
    a("Each arm's change is the smallest edit that does what the plan's § 2 says, made to the "
      "baked text of each role and nowhere else (the template and the role files are untouched); "
      "the module refuses an arm for a role whose text lacks the passage it changes.  The "
      "doubled parenthesis is fixed only where the plan says so (A1, A2 and A5), so every other "
      "arm differs from A0 in its own change alone.  Choices made in drafting:")
    a("")
    a(f"- **A1** replaces the whole parenthesis `{IDENTITY_PAREN}` with `{A1_PAREN}`, the plan's "
      "words, in levels 0, 1 and 2 (\"an LLM\" goes too, since the plan's text has \"a language "
      "model\" in its place).")
    a(f"- **A2** keeps the parenthesis and swaps the model's name in: `{A2_PAREN.format(model_name=model_name)}`.  "
      f"The name comes from `--model-name`, else the responses directory's `generation_config.json` "
      f"(its last run's `model_name`, shortened to its leading letters: `Qwen/Qwen3-32B` gives "
      f"`Qwen`), else `{DEFAULT_MODEL_NAME}`.  Here: `{model_name}` ({model_name_source}).")
    a(f"- **A3** puts `{A3_EXAMPLE}` where `{LEVEL2_EXAMPLE}` was.")
    a(f"- **A4** puts `{A4_EXAMPLE}` there, with the role's name as the rubric shows it.  The "
      "original's adjective (altruist, *altruistic*) cannot be made for every role, so the example "
      "uses '<name>-like'; for a role whose name ends in 'AI' this reads 'instrumentally-aligned "
      "AI-like AI', shown below.  A wording for Roger to change if he prefers another.")
    a("- **A6**: the plan says only \"level 0's refusal clause removed\".  The reading taken is "
      "option B of the role-rubric proposal in the 2026-10-12 progress report, "
      f"{_link(REPO / 'reports' / 'pipeline' / 'fix_batch_2026-10-12.md', doc_dir)} § 7, written "
      "for walk-through item P4 (the text was replaced by the decision to run this experiment in "
      "commit 2a863192; it is in f43af405's version of the file): \"level 0 ends at '...while "
      "refusing to answer the question.'; level 3 ends 'A refusal given in the role's own voice "
      "also counts as playing the role.'\"  The review it answers "
      f"({_link(REPO / 'reports' / 'code_review_2026-10-12' / 'escalations.md', doc_dir)}, P3 D6, "
      "and the TODO above `_role_prompt` in step 3) called level 0's exception \"awkward\", "
      "overlapping level 3's rule that an in-role refusal is a 3.  So A6 drops level 0's "
      "sentence and words level 3's rule once, in option B's words; the rule itself (an in-role "
      "refusal is a 3) stays.  The other reading, dropping level 0's refusal condition "
      "('while refusing to answer the question') so that levels 0 and 1 merge, is a different "
      "scale, and nothing in the review proposes it.  Taking option B whole, rather than only "
      "deleting level 0's sentence, follows the review's text; the two differ only in level 3's "
      "wording of the same rule.")
    a(f"- **A7** changes 'identifies as itself (...)' to 'identifies as {A7_UNDERLYING} (...) "
      "rather than as the role' in levels 0, 1 and 2 (the parenthesis, the typo and the example "
      "kept, so the arm is the identity change alone), and adds one sentence after level 3, the "
      f"same for every role: \"{A7_ROLE_SENTENCE}\"  The analysis reads it on the five "
      "AI-persona roles apart from the other 25.")
    a("")
    if estimate is not None:
        a("## Cost")
        a("")
        a(f"Estimated on the May responses of the 30 roles ({_link(responses_dir, doc_dir, 'the May responses')}; "
          f"the October ones will differ a little in length):")
        a("")
        a("| arm | calls | prompt tokens | output tokens | USD |")
        a("|---|---|---|---|---|")
        for arm, d in estimate["per_arm"].items():
            a(f"| {ARM_BY_ID[arm].label} | {d['calls']:,} | {d['prompt_tokens']:,} | "
              f"{d['output_tokens']:,} | {d['usd']:.2f} |")
        t = estimate["total"]
        a(f"| **total** | **{t['calls']:,}** | **{t['prompt_tokens']:,}** | "
          f"**{t['output_tokens']:,}** | **{t['usd']:.2f}** |")
        a("")
        fix_batch = _link(REPO / "reports" / "pipeline" / "fix_batch_2026-10-12.md", doc_dir)
        a(f"Prompt tokens by {estimate['token_method']} plus {estimate['chat_overhead_tokens']} a "
          f"request for the chat format, calibrated on the P5 canary of 2026-10-12 ({fix_batch} "
          f"§ 4: the first 30 May responses of "
          f"{_role_link('accountant', doc_dir, roles_dir)} with its rubric, 764.7 tokens a request "
          f"counted against 771.7 billed); output {estimate['output_tokens_per_call']} tokens a "
          f"call, the same canary's 2,165 completion tokens over its 30 requests (the May judge "
          f"was asked for the number alone, so the May tree has no evidence on this format); "
          f"{estimate['prices_per_mtok']['model']} at ${estimate['prices_per_mtok']['input']} / "
          f"${estimate['prices_per_mtok']['output']} per million tokens.  If every reply ran to "
          f"{MAX_TOKENS} tokens: ${t['usd_if_max_output']:.2f}.  "
          + (f"**Over ${COST_FLAG_USD:.0f}.**" if estimate["over_flag"]
             else f"Within ${COST_FLAG_USD:.0f}; Roger's cap is ${COST_CAP_USD:.0f}."))
        a("")
    a("## Each arm against A0")
    a("")
    a("Unified diffs of the rubric (lines split at sentence ends so that a change names its "
      f"sentence), on {_role_link(render_roles[0], doc_dir, roles_dir)}; where the change reads "
      f"differently for {_role_link(render_roles[1], doc_dir, roles_dir)}, its diff follows.")
    a("")
    first, second = plans[render_roles[0]], plans[render_roles[1]]
    for arm in COMPARED_ARMS:
        a(f"### {ARM_BY_ID[arm].label}: {ARM_BY_ID[arm].summary}")
        a("")
        d1 = arm_diff(first.baked, first.templates[arm], arm)
        if not d1:
            a("No difference: the same text as A0, judged again.")
            a("")
            continue
        a(_fence(d1, "diff"))
        d2 = arm_diff(second.baked, second.templates[arm], arm)
        if _diff_body(d1) != _diff_body(d2):
            a("")
            a(f"For {second.stem}:")
            a("")
            a(_fence(d2, "diff"))
        a("")
    a("## The prompts as the judge receives them")
    a("")
    picks = {}
    for stem in render_roles:
        rp = plans[stem]
        may = {}
        p = Path(may_scores_dir) / f"{rp.responses_path.stem}.json"
        if p.exists():
            may = json.loads(p.read_text())
        resp, may_score = pick_render_response(rp.responses, may)
        picks[stem] = resp
        why = (", the first response the May judge scored 2 (that judge was asked for the "
               "number alone)" if may_score == 2 else
               f", the first response (May score {may_score})" if may_score is not None else
               ", the first response")
        a(f"- {_role_link(stem, doc_dir, roles_dir)}: response `{j3.response_key(resp)}` of "
          f"{_link(rp.responses_path, doc_dir)}{why}.")
    a("")
    a("Each block is the whole user message, the filled rubric, for one arm and one role.")
    a("")
    for arm in ARM_IDS:
        a(f"### {ARM_BY_ID[arm].label}")
        a("")
        for stem in render_roles:
            rp = plans[stem]
            resp = picks[stem]
            prompt = rp.templates[arm].format(question=resp["question"], answer=assistant_text(resp))
            a(f"<details><summary>{ARM_BY_ID[arm].label}, {stem}</summary>")
            a("")
            a(_fence(prompt))
            a("")
            a("</details>")
            a("")
    a("## Commands")
    a("")
    a("Nothing below has been run against the API.  The real run waits for Roger's review of "
      "this document and of the cost.")
    a("")
    a(_fence("\n".join([
        "# (a) dry run on the May responses: builds and counts every request, submits nothing",
        f"uv run python {SCRIPT_REL} judge --dry-run \\",
        f"    --responses-dir '{MAY_RESPONSES_DIR.relative_to(REPO)}' \\",
        "    --out-dir \"$TMPDIR/role_rubric_dry_run\"",
        "",
        "# (b) the real submission (October responses copied from the pod's /workspace/rubric_exp/responses)",
        f"uv run python {SCRIPT_REL} judge --confirm-expensive --batch-no-wait \\",
        "    --responses-dir runpod_workspace/rubric_exp/responses \\",
        "    --out-dir runpod_workspace/rubric_exp/judged",
        "",
        "# (c) collection (any time later; resumable; never pays twice)",
        f"uv run python {SCRIPT_REL} judge --collect-only \\",
        "    --responses-dir runpod_workspace/rubric_exp/responses \\",
        "    --out-dir runpod_workspace/rubric_exp/judged",
        "",
        "# (d) the score analysis and the blind reading sheet",
        f"uv run python {SCRIPT_REL} analyze-scores \\",
        "    --scores-dir runpod_workspace/rubric_exp/judged \\",
        "    --responses-dir runpod_workspace/rubric_exp/responses",
        "",
        "# (e) on the pod: the vectors (judged directory copied to the pod)",
        f"uv run python {SCRIPT_REL} analyze-vectors \\",
        "    --activations-dir /workspace/rubric_exp/activations \\",
        "    --scores-dir /workspace/rubric_exp/judged",
    ]), "bash"))
    a("")
    judged = REPO / "runpod_workspace" / "rubric_exp" / "judged"
    a("The paths assume the October responses are copied from the pod into "
      f"{_link(REPO / 'runpod_workspace' / 'rubric_exp' / 'responses', doc_dir, 'runpod_workspace/rubric_exp/responses/')} "
      "(not there yet; git-ignored, as all of `runpod_workspace/`).  What the run writes, none of "
      f"it there yet: the run directory {_link(judged, doc_dir, 'runpod_workspace/rubric_exp/judged/')} "
      f"(per arm `<arm>/<role>.json` in step 3's format, {_link(judged / 'usage.json', doc_dir)}, "
      f"{_link(judged / RUN_RECORD_NAME, doc_dir)}, every reply under `replies/`); the analysis "
      f"{_link(doc_dir / 'score_analysis.md', doc_dir)} with "
      f"{_link(doc_dir / 'score_analysis.json', doc_dir)}; the blind reading sheet "
      f"{_link(doc_dir / SHEET_DIRNAME, doc_dir, 'reading_sheet/')} with its key "
      f"{_link(doc_dir / SHEET_KEY_NAME, doc_dir)} (kept apart; not to be opened before marking) "
      f"and, once marked, {_link(doc_dir / 'reading_results.json', doc_dir)} from `read-marks`; "
      f"and from the pod {_link(doc_dir / 'vector_analysis.md', doc_dir)} with "
      f"{_link(doc_dir / 'vector_analysis.json', doc_dir)}.  The vector analysis takes step 4's "
      f"`--min_count` as {_link(REPO / 'pipeline' / 'run_pipeline.sh', doc_dir)} passes it for "
      f"roles ({DEFAULT_MIN_COUNT}, its `MIN_COUNT`), not the script's own default of 50.")
    a("")
    return "\n".join(L)


def cmd_render(args) -> int:
    responses_dir = Path(args.responses_dir)
    model_name, source = resolve_model_name(args.model_name, responses_dir)
    est = None
    if not args.no_estimate:
        plan = build_plan(list(SAMPLE), ARM_IDS, roles_dir=Path(args.roles_dir),
                          responses_dir=responses_dir, model_name=model_name)
        est = estimate_plan(plan, ARM_IDS, counter=TokenCounter(args.tokenizer))
    out = Path(args.out)
    text = render_document(roles_dir=Path(args.roles_dir), responses_dir=responses_dir,
                           may_scores_dir=Path(args.may_scores_dir), model_name=model_name,
                           model_name_source=source, doc_path=out, estimate=est)
    atomic_write_text(text, out, logger_obj=logger)
    print(f"wrote {out}")
    if est is not None:
        for line in estimate_lines(est):
            print(line)
    return 0


# ---------------------------------------------------------------------------
# analyze-scores
# ---------------------------------------------------------------------------

def load_arm_scores(scores_dir: Path, roles: Sequence[str], arms: Sequence[str] = ARM_IDS
                    ) -> Dict[str, Dict[str, Dict[str, int]]]:
    """``arm -> role -> key -> score`` for every score file present."""
    out: Dict[str, Dict[str, Dict[str, int]]] = {}
    for arm in arms:
        for role in roles:
            path = score_path(scores_dir, arm, role)
            if path.exists():
                out.setdefault(arm, {})[role] = json.loads(read_text_with_retry(path, logger_obj=logger))
    return out


def compare_scores(base: Mapping[str, int], other: Mapping[str, int]) -> Dict[str, int]:
    """Counts over the responses both scored: changed scores, boundary flips (down: 3 in
    ``base``, below in ``other``; up: the reverse), and each side's 3s."""
    common = base.keys() & other.keys()
    down = sum(1 for k in common if base[k] == 3 and other[k] != 3)
    up = sum(1 for k in common if base[k] != 3 and other[k] == 3)
    return {"n": len(common), "changed": sum(1 for k in common if base[k] != other[k]),
            "boundary": down + up, "down": down, "up": up,
            "base_3": sum(1 for k in common if base[k] == 3),
            "other_3": sum(1 for k in common if other[k] == 3)}


def boundary_flips(base: Mapping[str, int], other: Mapping[str, int]) -> List[str]:
    return sorted(k for k in base.keys() & other.keys() if (base[k] == 3) != (other[k] == 3))


def wilson(k: int, n: int, z: float = 1.96) -> Tuple[Optional[float], Optional[float]]:
    if n == 0:
        return None, None
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) / d, (c + h) / d


def _pool(per_role: Mapping[str, Mapping[str, int]], roles: Iterable[str]) -> Dict[str, Any]:
    tot = Counter()
    for r in roles:
        if r in per_role:
            tot.update(per_role[r])
    n = tot["n"]
    out: Dict[str, Any] = dict(tot)
    out.update(n=n, changed_share=tot["changed"] / n if n else None,
               boundary_share=tot["boundary"] / n if n else None,
               boundary_ci95=wilson(tot["boundary"], n))
    return out


def arm_comparison(scores: Mapping[str, Mapping[str, Mapping[str, int]]], arm: str,
                   roles: Sequence[str], base: str = BASE_ARM,
                   questions: Optional[Mapping[int, str]] = None) -> Dict[str, Any]:
    per_role = {r: compare_scores(scores[base][r], scores[arm][r]) for r in roles
                if r in scores.get(base, {}) and r in scores.get(arm, {})}
    shares = [v["boundary"] / v["n"] for v in per_role.values() if v["n"]]
    by_q: Dict[int, Counter] = defaultdict(Counter)
    for r in per_role:
        b, o = scores[base][r], scores[arm][r]
        for k in boundary_flips(b, o):
            by_q[question_index(k)]["down" if b[k] == 3 else "up"] += 1
    by_question = sorted(({"question_index": q, "down": c["down"], "up": c["up"],
                           "boundary": c["down"] + c["up"],
                           **({"question": questions[q]} if questions and q in questions else {})}
                          for q, c in by_q.items()), key=lambda d: (-d["boundary"], d["question_index"]))
    ai = [r for r in roles if r in AI_PERSONA_ROLES]
    rest = [r for r in roles if r not in AI_PERSONA_ROLES]
    return {"arm": arm, "base": base, "pooled": _pool(per_role, per_role),
            "ai_persona": _pool(per_role, ai), "other_roles": _pool(per_role, rest),
            "per_role": per_role, "by_question": by_question,
            "per_role_boundary_share": {
                "min": min(shares) if shares else None,
                "median": statistics.median(shares) if shares else None,
                "max": max(shares) if shares else None}}


def level_shares(scores: Mapping[str, int]) -> Dict[int, float]:
    n = len(scores)
    return {lvl: (sum(1 for v in scores.values() if v == lvl) / n if n else 0.0) for lvl in range(4)}


def score_analysis(scores: Mapping[str, Mapping[str, Mapping[str, int]]], roles: Sequence[str],
                   questions: Optional[Mapping[int, str]] = None) -> Dict[str, Any]:
    arms_here = [a for a in COMPARED_ARMS if a in scores]
    comps = {a: arm_comparison(scores, a, roles, questions=questions) for a in arms_here}
    noise = comps.get(NOISE_ARM)
    for a, c in comps.items():
        if noise is None or a == NOISE_ARM:
            continue
        nb, ab = noise["pooled"]["boundary_share"], c["pooled"]["boundary_share"]
        c["vs_noise"] = {
            "boundary_share_ratio": (ab / nb) if nb else None,
            "boundary_share_excess": (ab - nb) if (ab is not None and nb is not None) else None,
            "roles_above_noise": sum(
                1 for r, v in c["per_role"].items() if r in noise["per_role"] and v["n"]
                and noise["per_role"][r]["n"]
                and v["boundary"] / v["n"] > noise["per_role"][r]["boundary"] / noise["per_role"][r]["n"]),
            "roles_compared": sum(1 for r in c["per_role"] if r in noise["per_role"])}
    n3 = {a: {r: sum(1 for v in scores[a][r].values() if v == 3) for r in scores[a] if r in roles}
          for a in scores}
    return {"roles": list(roles), "arms": [a for a in ARM_IDS if a in scores],
            "noise_floor": noise, "comparisons": comps, "score3_counts": n3,
            "levels_a0": {r: level_shares(scores[BASE_ARM][r]) for r in roles
                          if r in scores.get(BASE_ARM, {})}}


def _pct(x: Optional[float]) -> str:
    return "" if x is None else f"{x:.1%}"


def score_analysis_markdown(an: Mapping[str, Any], *, doc_dir: Path, scores_dir: Path,
                            roles_dir: Path = ROLES_DIR, sheet_info: Optional[Mapping[str, Any]] = None) -> str:
    L: List[str] = []
    a = L.append
    a("# Role-judge rubric experiment: the scores")
    a("")
    a(f"Written by {_link(REPO / SCRIPT_REL, doc_dir)} `analyze-scores` on {_now()} from "
      f"{_link(scores_dir, doc_dir, 'the judged run')}; the numbers are in "
      f"{_link(doc_dir / 'score_analysis.json', doc_dir)}.  Plan: {_link(PLAN_DOC, doc_dir)}; arms: "
      f"{_link(doc_dir / 'arm_wordings.md', doc_dir)}.")
    a("")
    a("A **boundary flip** is a response scored 3 by one arm and below 3 by the other (it enters "
      "the role vector under one rubric only); **down** is 3 under A0 and below under the arm, "
      "**up** the reverse.  The **noise floor** is A0 against A0', the same rubric judged twice; "
      "every arm is read against it.  Shares are of the responses both arms scored; the 95% "
      "intervals (Wilson) treat responses as independent, which they are not quite.")
    if sheet_info:
        a("")
        a(f"**Mark the reading sheet before reading further**: {sheet_info['pages']} page(s) under "
          f"{_link(doc_dir / 'reading_sheet', doc_dir, 'reading_sheet/')}, {sheet_info['items']} items.")
    a("")
    a("## Each arm against A0")
    a("")
    a("| arm | responses | score changed | boundary flips (down / up) | boundary share (95%) | x noise | roles above noise |")
    a("|---|---|---|---|---|---|---|")
    for arm in COMPARED_ARMS:
        c = an["comparisons"].get(arm)
        if not c:
            continue
        p = c["pooled"]
        lo, hi = p["boundary_ci95"]
        vs = c.get("vs_noise") or {}
        ratio = vs.get("boundary_share_ratio")
        ratio_s = "" if ratio is None else f"{ratio:.2f}"
        above_s = "" if not vs else f"{vs['roles_above_noise']} of {vs['roles_compared']}"
        a(f"| {ARM_BY_ID[arm].label} | {p['n']:,} | {_pct(p['changed_share'])} | {p['boundary']:,} "
          f"({p['down']:,} / {p['up']:,}) | {_pct(p['boundary_share'])} ({_pct(lo)}-{_pct(hi)}) | "
          f"{ratio_s} | {above_s} |")
    a("")
    noise = an.get("noise_floor")
    if noise:
        s = noise["per_role_boundary_share"]
        a(f"Noise floor (A0 vs A0'): {_pct(noise['pooled']['changed_share'])} of responses change "
          f"score, {_pct(noise['pooled']['boundary_share'])} cross the 3 boundary; per role the "
          f"boundary share runs {_pct(s['min'])} to {_pct(s['max'])} (median {_pct(s['median'])}).")
        a("")
    a("## The AI-persona roles, and the other 25")
    a("")
    a("| arm | AI-persona: boundary (down / up) | share | other roles: boundary (down / up) | share |")
    a("|---|---|---|---|---|")
    for arm in COMPARED_ARMS:
        c = an["comparisons"].get(arm)
        if not c:
            continue
        ai, rest = c["ai_persona"], c["other_roles"]
        a(f"| {ARM_BY_ID[arm].label} | {ai.get('boundary', 0):,} ({ai.get('down', 0):,} / "
          f"{ai.get('up', 0):,}) | {_pct(ai['boundary_share'])} | {rest.get('boundary', 0):,} "
          f"({rest.get('down', 0):,} / {rest.get('up', 0):,}) | {_pct(rest['boundary_share'])} |")
    a("")
    a("Responses scored 3 (the responses each role vector is averaged over), by arm:")
    a("")
    arms_here = an["arms"]
    a("| role | " + " | ".join(ARM_BY_ID[x].label for x in arms_here) + " |")
    a("|---|" + "---|" * len(arms_here))
    for role in an["roles"]:
        cells = [str(an["score3_counts"].get(x, {}).get(role, "")) for x in arms_here]
        mark = " (AI)" if role in AI_PERSONA_ROLES else ""
        a(f"| {_role_link(role, doc_dir, roles_dir)}{mark} | " + " | ".join(cells) + " |")
    a("")
    a("## Boundary flips by role (down / up)")
    a("")
    a("| role | " + " | ".join(ARM_BY_ID[x].label for x in COMPARED_ARMS if x in an["comparisons"]) + " |")
    a("|---|" + "---|" * len([x for x in COMPARED_ARMS if x in an["comparisons"]]))
    for role in an["roles"]:
        cells = []
        for arm in COMPARED_ARMS:
            c = an["comparisons"].get(arm)
            if not c:
                continue
            v = c["per_role"].get(role)
            cells.append("" if v is None else f"{v['down']} / {v['up']}")
        a(f"| {_role_link(role, doc_dir, roles_dir)} | " + " | ".join(cells) + " |")
    a("")
    a("## The questions with the most boundary flips")
    a("")
    for arm in COMPARED_ARMS:
        c = an["comparisons"].get(arm)
        if not c or not c["by_question"]:
            continue
        top = c["by_question"][:5]
        a(f"- **{ARM_BY_ID[arm].label}**: " + "; ".join(
            f"q{d['question_index']} {d['boundary']} ({d['down']} down / {d['up']} up)"
            + (f", \"{d['question'][:80]}\"" if d.get("question") else "") for d in top))
    a("")
    a("## A0's level shares by role")
    a("")
    a("| role | 0 | 1 | 2 | 3 |")
    a("|---|---|---|---|---|")
    for role, sh in an["levels_a0"].items():
        a(f"| {_role_link(role, doc_dir, roles_dir)} | " + " | ".join(_pct(sh[l]) for l in range(4)) + " |")
    a("")
    return "\n".join(L)


# -- the blind reading sheet --------------------------------------------------

SHEET_SEED = 20261022
SHEET_DIRNAME = "reading_sheet"
SHEET_KEY_NAME = "reading_sheet_key.json"
SHEET_PAGE_SIZE = 50
SHEET_PER_ARM = 100
ITEM_RE = re.compile(r"^### (\d+)\s*$")
MARK_RE = re.compile(r"^mark:[ \t]*(.*)$", re.IGNORECASE)
MARKS = {"X": "x", "Y": "y", "T": "tie", "?": "unsure"}


def build_reading_sheet(scores: Mapping[str, Mapping[str, Mapping[str, int]]], roles: Sequence[str],
                        *, per_arm: int = SHEET_PER_ARM, seed: int = SHEET_SEED,
                        arms: Sequence[str] = COMPARED_ARMS) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Up to ``per_arm`` boundary flips per arm against A0 (A0' included, as a check of the
    reader), drawn round-robin across roles in a seeded order, pooled and shuffled so that a
    page mixes arms.  Returns the items (what the sheet shows: role, response key, the two
    scores as X and Y in a random order) and the key (arm, which of X and Y is A0)."""
    rng = random.Random(seed)
    picks: List[Tuple[str, str, str]] = []
    for arm in arms:
        if arm not in scores or BASE_ARM not in scores:
            continue
        by_role = {r: boundary_flips(scores[BASE_ARM][r], scores[arm][r]) for r in roles
                   if r in scores[BASE_ARM] and r in scores[arm]}
        for keys in by_role.values():
            rng.shuffle(keys)
        order = sorted(by_role)
        rng.shuffle(order)
        taken: List[Tuple[str, str, str]] = []
        i = 0
        while len(taken) < per_arm and any(by_role[r] for r in order):
            r = order[i % len(order)]
            if by_role[r]:
                taken.append((arm, r, by_role[r].pop()))
            i += 1
        picks.extend(taken)
    rng.shuffle(picks)
    items, key = [], {"seed": seed, "per_arm": per_arm, "base": BASE_ARM, "items": {}}
    for n, (arm, role, k) in enumerate(picks, 1):
        a0, ax = scores[BASE_ARM][role][k], scores[arm][role][k]
        x_is_a0 = rng.random() < 0.5
        x, y = (a0, ax) if x_is_a0 else (ax, a0)
        items.append({"item": n, "role": role, "key": k, "x": x, "y": y})
        key["items"][str(n)] = {"arm": arm, "role": role, "key": k, "a0_score": a0,
                                "arm_score": ax, "x_is": BASE_ARM if x_is_a0 else "arm"}
    return items, key


def render_sheet_pages(items: Sequence[Mapping[str, Any]], *, texts: Mapping[str, Mapping[str, Mapping[str, str]]],
                       descriptions: Mapping[str, str], sheet_dir: Path, roles_dir: Path = ROLES_DIR,
                       page_size: int = SHEET_PAGE_SIZE) -> List[Path]:
    """One markdown page per ``page_size`` items.  Nothing on a page names an arm; the mark line
    comes right under each item's number."""
    pages = [items[i:i + page_size] for i in range(0, len(items), page_size)] or [[]]
    paths = []
    for p, chunk in enumerate(pages, 1):
        L = [f"# Role-judge rubric experiment: reading sheet, page {p} of {len(pages)}", "",
             "Each item is one response that the judge scored twice, under two rubrics, once 3 "
             "(the response fully plays the role, and enters the role's vector) and once below 3.  "
             "The two scores are shown as **X** and **Y**, in a random order.  Read the role's "
             "description, the question and the response, and mark which score is right.", "",
             "**Marks** (on the `mark:` line under each item's number): **X** the X score is "
             "right; **Y** the Y score is right; **T** a tie (both defensible); **?** unsure.  A "
             "word after the mark is welcome.  The key is in a separate file: do not open it, or "
             "the score analysis, before marking.", ""]
        for it in chunk:
            t = texts.get(it["role"], {}).get(it["key"], {})
            L += ["---", "", f"### {it['item']}", "", "mark: ", "",
                  f"**X: {it['x']} · Y: {it['y']}**", "",
                  f"**Role**: {_link(Path(roles_dir) / (it['role'] + '.json'), sheet_dir, it['role'])}: "
                  f"{descriptions.get(it['role'], '')}", "",
                  f"**Question**: {t.get('question', '')}", "", "**Response**:", ""]
            body = t.get("answer", "") or "(empty)"
            L += [("> " + line) if line.strip() else ">" for line in body.split("\n")]
            L.append("")
        path = Path(sheet_dir) / f"page_{p:02d}.md"
        atomic_write_text("\n".join(L), path, logger_obj=logger)
        paths.append(path)
    return paths


def parse_marks(pages: Iterable[Path]) -> Dict[str, str]:
    """``item -> mark`` (X, Y, T or ?; '' unmarked) from the sheet's pages."""
    out: Dict[str, str] = {}
    for page in pages:
        item = None
        for line in Path(page).read_text().splitlines():
            m = ITEM_RE.match(line)
            if m:
                item = m.group(1)
                continue
            if item is not None:
                mm = MARK_RE.match(line.strip())
                if mm:
                    word = mm.group(1).strip()
                    out[item] = word[:1].upper() if word else ""
                    item = None
    return out


def tally_marks(marks: Mapping[str, str], key: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Per arm: how often the reader found the arm's score right, A0's right, a tie, unsure,
    or left the item unmarked; and whether arm : A0 reaches the plan's 2 : 1."""
    out: Dict[str, Counter] = defaultdict(Counter)
    for item, k in key["items"].items():
        mark = marks.get(item, "")
        c = out[k["arm"]]
        if mark in ("X", "Y"):
            picked_x = mark == "X"
            c["arm_right" if picked_x == (k["x_is"] == "arm") else "a0_right"] += 1
        elif mark == "T":
            c["tie"] += 1
        elif mark == "?":
            c["unsure"] += 1
        else:
            c["unmarked"] += 1
    res = {}
    for arm, c in out.items():
        d = {k: c.get(k, 0) for k in ("arm_right", "a0_right", "tie", "unsure", "unmarked")}
        d["two_to_one"] = d["arm_right"] >= 2 * d["a0_right"] and d["arm_right"] > 0
        res[arm] = d
    return res


def _texts_for(roles: Sequence[str], responses_dir: Path, roles_dir: Path
               ) -> Tuple[Dict[str, Dict[str, Dict[str, str]]], Dict[int, str]]:
    j3 = step3()
    texts: Dict[str, Dict[str, Dict[str, str]]] = {}
    seen: Dict[int, set] = defaultdict(set)
    for role in roles:
        doc = load_role(role, roles_dir)
        try:
            path = responses_file(role, responses_dir, doc)
        except FileNotFoundError as e:
            logger.warning(str(e))
            continue
        cell = {}
        for r in j3.load_responses(path):
            cell[j3.response_key(r)] = {"question": r.get("question", ""), "answer": assistant_text(r)}
            seen[int(r["question_index"])].add(r.get("question", ""))
        texts[role] = cell
    # One text per question index when the roles share a question list (the May tree's 100
    # extraction questions); an index whose text differs by role is labelled so.
    questions = {q: (next(iter(t)) if len(t) == 1 else "(differs by role)") for q, t in seen.items()}
    return texts, questions


def cmd_analyze_scores(args) -> int:
    from assistant_axis import json_metadata
    from assistant_axis.provenance import current_file_input, current_files_input
    roles = list(args.roles or SAMPLE)
    scores_dir = Path(args.scores_dir)
    scores = load_arm_scores(scores_dir, roles)
    if BASE_ARM not in scores:
        logger.error(f"no A0 scores under {scores_dir}")
        return 1
    roles = [r for r in roles if r in scores[BASE_ARM]]
    texts, questions = ({}, {})
    if args.responses_dir:
        texts, questions = _texts_for(roles, Path(args.responses_dir), Path(args.roles_dir))
    an = score_analysis(scores, roles, questions=questions)
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    sheet_info = None
    if args.responses_dir and not args.no_sheet:
        sheet_dir = report_dir / SHEET_DIRNAME
        old_pages = sorted(sheet_dir.glob("page_*.md")) if sheet_dir.is_dir() else []
        if old_pages and any(parse_marks(old_pages).values()):
            if not args.overwrite_sheet:
                logger.error(f"{sheet_dir} holds marks; pass --overwrite-sheet to replace the sheet "
                             f"(it is copied aside first), or --no-sheet")
                return 2
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup = report_dir / f"{SHEET_DIRNAME}.bak.{stamp}"
            backup.mkdir(parents=True)
            for p in old_pages + [report_dir / SHEET_KEY_NAME]:
                if p.exists():
                    (backup / p.name).write_bytes(p.read_bytes())
            logger.warning(f"the marked sheet and its key were copied to {backup}")
        for old in old_pages:
            old.unlink()
        items, key = build_reading_sheet(scores, roles, per_arm=args.sheet_per_arm, seed=args.seed)
        descs = {r: load_role(r, Path(args.roles_dir)).get("description", "") for r in roles}
        pages = render_sheet_pages(items, texts=texts, descriptions=descs, sheet_dir=sheet_dir,
                                   roles_dir=Path(args.roles_dir), page_size=args.sheet_page_size)
        key["written_at"] = _now()
        key["pages"] = [p.name for p in pages]
        _write_json(report_dir / SHEET_KEY_NAME, key)
        sheet_info = {"pages": len(pages), "items": len(items)}
        an["reading_sheet"] = {**sheet_info, "seed": args.seed, "per_arm": args.sheet_per_arm,
                               "key": SHEET_KEY_NAME,
                               "per_arm_items": dict(Counter(v["arm"] for v in key["items"].values()))}
    files = [p for arm in scores for r in scores[arm] for p in [score_path(scores_dir, arm, r)]]
    inputs = [current_file_input(dep_key="producer_script", path=REPO / SCRIPT_REL),
              current_files_input(dep_key="arm_scores", paths=files)]
    _write_json(report_dir / "score_analysis.json",
                json_metadata(an, inputs=inputs, title=f"{EXPERIMENT} analyze-scores",
                              script=SCRIPT_REL))
    md = score_analysis_markdown(an, doc_dir=report_dir, scores_dir=scores_dir,
                                 roles_dir=Path(args.roles_dir), sheet_info=sheet_info)
    atomic_write_text(md, report_dir / "score_analysis.md", logger_obj=logger)
    print(f"wrote {report_dir / 'score_analysis.md'} and score_analysis.json"
          + (f"; reading sheet: {sheet_info['items']} items on {sheet_info['pages']} page(s)"
             if sheet_info else ""))
    return 0


def cmd_read_marks(args) -> int:
    report_dir = Path(args.report_dir)
    key = json.loads((report_dir / SHEET_KEY_NAME).read_text())
    pages = sorted((report_dir / SHEET_DIRNAME).glob("page_*.md"))
    marks = parse_marks(pages)
    res = tally_marks(marks, key)
    out = {"read_at": _now(), "n_items": len(key["items"]),
           "n_marked": sum(1 for v in marks.values() if v), "per_arm": res}
    _write_json(report_dir / "reading_results.json", out)
    print(f"{'arm':<5} {'arm right':>9} {'A0 right':>9} {'tie':>5} {'?':>4} {'unmarked':>9}  2:1")
    for arm in COMPARED_ARMS:
        if arm in res:
            d = res[arm]
            print(f"{ARM_BY_ID[arm].label:<5} {d['arm_right']:>9} {d['a0_right']:>9} {d['tie']:>5} "
                  f"{d['unsure']:>4} {d['unmarked']:>9}  {'yes' if d['two_to_one'] else 'no'}")
    print(f"wrote {report_dir / 'reading_results.json'}")
    return 0


# ---------------------------------------------------------------------------
# analyze-vectors (on the pod)
# ---------------------------------------------------------------------------

# Step 4's --min_count as the pipeline passes it for roles (run_pipeline.sh MIN_COUNT, roger
# mode; 4_vectors.py's own default, 50, is christina mode's CHRISTINA_MIN_COUNT).
DEFAULT_MIN_COUNT = 30


def cosine_grid(a, b) -> List[List[Optional[float]]]:
    """Cosine over the hidden dimension, per slot and layer, of two vectors shaped
    ``(slots, layers, hidden)`` (or ``(layers, hidden)``, one slot); None where either is NaN or
    zero."""
    import torch
    x, y = a.to(torch.float64), b.to(torch.float64)
    if x.dim() == 2:
        x, y = x.unsqueeze(0), y.unsqueeze(0)
    num = (x * y).sum(-1)
    den = x.norm(dim=-1) * y.norm(dim=-1)
    cos = num / den
    return [[(float(v) if math.isfinite(float(v)) else None) for v in row] for row in cos]


def _mean(xs: Iterable[Optional[float]]) -> Optional[float]:
    vals = [x for x in xs if x is not None]
    return sum(vals) / len(vals) if vals else None


def analyze_vectors(activations_dir: Path, scores_dir: Path, roles: Sequence[str],
                    arms: Sequence[str] = ARM_IDS, *, min_count: int = DEFAULT_MIN_COUNT,
                    reduce_questions: int = 1, roles_dir: Path = ROLES_DIR) -> Dict[str, Any]:
    """For each role: its activations loaded once (step 4's ``load_activations``, which reads
    with ``torch_load_with_retry``), each arm's vector by step 4's ``compute_pos_3_vector`` (the
    score == 3 filter, the min-count rule, the float64 mean stored as float32), and each arm's
    cosine with A0's vector per slot and layer."""
    import gc
    j4 = step4()
    per_role: Dict[str, Any] = {}
    for role in roles:
        doc = load_role(role, roles_dir) if (Path(roles_dir) / f"{role}.json").exists() else {}
        act = Path(activations_dir) / f"{role}.pt"
        if not act.exists():
            for old in renamed_stems(doc):
                if (Path(activations_dir) / f"{old}.pt").exists():
                    act = Path(activations_dir) / f"{old}.pt"
                    break
        if not act.exists():
            per_role[role] = {"status": "no_activations"}
            continue
        activations, _meta = j4.load_activations(act)
        vecs, entry = {}, {"activation_file": act.name, "n_activations": len(activations), "arms": {}}
        for arm in arms:
            sp = score_path(scores_dir, arm, role)
            if not sp.exists():
                entry["arms"][arm] = {"status": "no_scores"}
                continue
            scores = j4.load_scores(sp)
            n3 = sum(1 for k in activations if k in scores and scores[k] == 3
                     and j4._keep_by_reduce(k, reduce_questions))
            info: Dict[str, Any] = {"n_score3": n3, "n_scored": sum(1 for k in activations if k in scores)}
            try:
                vecs[arm] = j4.compute_pos_3_vector(activations, scores, min_count, reduce_questions)
                info["status"] = "ok"
                info["shape"] = list(vecs[arm].shape)
            except j4.BelowMinCount as e:
                info["status"] = "below_min_count"
                info["detail"] = str(e)
            info["score3_keys"] = sorted(k for k in activations if k in scores and scores[k] == 3
                                         and j4._keep_by_reduce(k, reduce_questions))
            entry["arms"][arm] = info
        base = vecs.get(BASE_ARM)
        base3 = set((entry["arms"].get(BASE_ARM) or {}).get("score3_keys") or [])
        for arm, info in entry["arms"].items():
            keys = set(info.pop("score3_keys", []) or [])
            if arm != BASE_ARM and base3 | keys:
                info["jaccard_score3_with_A0"] = len(base3 & keys) / len(base3 | keys)
            if base is not None and arm in vecs and arm != BASE_ARM:
                grid = cosine_grid(vecs[arm], base)
                info["cos_with_A0"] = grid
                info["cos_with_A0_layer_mean"] = [_mean(row) for row in grid]
        per_role[role] = entry
        del activations, vecs
        gc.collect()
    return {"min_count": min_count, "reduce_questions": reduce_questions, "arms": list(arms),
            "roles": list(roles), "per_role": per_role, "summary": vector_summary(per_role, arms)}


def vector_summary(per_role: Mapping[str, Any], arms: Sequence[str]) -> Dict[str, Any]:
    """Per arm and slot, over roles: the median layer-mean cosine with A0, and the median of
    (1 - cos) relative to A0' (above 1: the arm moved the vector more than the judge's noise)."""
    out: Dict[str, Any] = {}
    for subset, members in (("all", None), ("ai_persona", AI_PERSONA_ROLES),
                            ("other_roles", "rest")):
        sub: Dict[str, Any] = {}
        for arm in arms:
            if arm == BASE_ARM:
                continue
            per_slot: Dict[int, List[float]] = defaultdict(list)
            ratios: Dict[int, List[float]] = defaultdict(list)
            for role, e in per_role.items():
                if members == "rest" and role in AI_PERSONA_ROLES:
                    continue
                if isinstance(members, tuple) and role not in members:
                    continue
                cos = ((e.get("arms") or {}).get(arm) or {}).get("cos_with_A0_layer_mean")
                noise = ((e.get("arms") or {}).get(NOISE_ARM) or {}).get("cos_with_A0_layer_mean")
                if not cos:
                    continue
                for s, v in enumerate(cos):
                    if v is None:
                        continue
                    per_slot[s].append(v)
                    if noise and noise[s] is not None and (1 - noise[s]) > 0:
                        ratios[s].append((1 - v) / (1 - noise[s]))
            sub[arm] = {str(s): {"median_cos": statistics.median(v), "min_cos": min(v),
                                 "n_roles": len(v),
                                 "median_ratio_to_noise": (statistics.median(ratios[s])
                                                           if ratios.get(s) else None)}
                        for s, v in sorted(per_slot.items())}
        out[subset] = sub
    return out


def vector_markdown(res: Mapping[str, Any], *, doc_dir: Path, roles_dir: Path = ROLES_DIR) -> str:
    L = ["# Role-judge rubric experiment: the vectors", "",
         f"Written by {_link(REPO / SCRIPT_REL, doc_dir)} `analyze-vectors` on {_now()} "
         f"(min_count {res['min_count']}, reduce_questions {res['reduce_questions']}); every "
         f"number is in {_link(doc_dir / 'vector_analysis.json', doc_dir)}.  Each arm's role "
         "vector is computed as step 4 computes it (the mean of the activations of the responses "
         "scored 3, float64, stored float32) and compared with A0's by cosine per slot, averaged "
         "over layers; the median over roles is shown, with the median of (1 - cos) divided by "
         "A0' 's (1 - cos) in brackets: above 1, the arm moves the vector more than the judge's "
         "own noise.", ""]
    for subset, title in (("all", "All roles"), ("ai_persona", "The AI-persona roles"),
                          ("other_roles", "The other roles")):
        sub = res["summary"].get(subset) or {}
        slots = sorted({int(s) for d in sub.values() for s in d})
        if not slots:
            continue
        L += [f"## {title}", "", "| arm | " + " | ".join(f"slot {s}" for s in slots) + " |",
              "|---|" + "---|" * len(slots)]
        for arm in COMPARED_ARMS:
            if arm not in sub:
                continue
            cells = []
            for s in slots:
                d = sub[arm].get(str(s))
                if not d:
                    cells.append("")
                    continue
                r = d["median_ratio_to_noise"]
                cells.append(f"{d['median_cos']:.5f}" + ("" if r is None else f" ({r:.1f})"))
            L.append(f"| {ARM_BY_ID[arm].label} | " + " | ".join(cells) + " |")
        L.append("")
    L += ["## Per role: responses scored 3 and status", "", "| role | " +
          " | ".join(ARM_BY_ID[a].label for a in res["arms"]) + " |", "|---|" + "---|" * len(res["arms"])]
    for role, e in res["per_role"].items():
        cells = []
        for arm in res["arms"]:
            d = (e.get("arms") or {}).get(arm) or {}
            cells.append(f"{d.get('n_score3', '')}" + ("" if d.get("status") in (None, "ok")
                                                       else f" ({d['status']})"))
        L.append(f"| {_role_link(role, doc_dir, roles_dir)} | " + " | ".join(cells) + " |")
    L.append("")
    return "\n".join(L)


def cmd_analyze_vectors(args) -> int:
    roles, arms = _selection(args)
    if BASE_ARM not in arms:
        arms = [BASE_ARM] + arms
    res = analyze_vectors(Path(args.activations_dir), Path(args.scores_dir), roles, arms,
                          min_count=args.min_count, reduce_questions=args.reduce_questions,
                          roles_dir=Path(args.roles_dir))
    res["activations_dir"] = str(args.activations_dir)
    res["scores_dir"] = str(args.scores_dir)
    res["written_at"] = _now()
    report_dir = Path(args.report_dir)
    _write_json(report_dir / "vector_analysis.json", res)
    atomic_write_text(vector_markdown(res, doc_dir=report_dir, roles_dir=Path(args.roles_dir)),
                      report_dir / "vector_analysis.md", logger_obj=logger)
    print(f"wrote {report_dir / 'vector_analysis.md'} and vector_analysis.json")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp, *, responses_default=None, responses_required=False):
        sp.add_argument("--roles-dir", default=str(ROLES_DIR), help="role instruction files")
        sp.add_argument("--roles", nargs="+", help=f"a subset of the {len(SAMPLE)} sampled roles")
        sp.add_argument("--arms", nargs="+", help=f"a subset of the arms ({', '.join(ARM_IDS)})")
        sp.add_argument("--responses-dir", default=responses_default, required=responses_required,
                        help="step-1 response files (<role>.jsonl)")
        sp.add_argument("--model-name", help="A2's model name (default: from the responses' "
                                             "generation_config.json, else Qwen)")
        sp.add_argument("--limit-responses", type=int, help="only the first N responses of each role")
        sp.add_argument("--tokenizer", choices=("auto", "tiktoken", "chars"), default="auto")

    r = sub.add_parser("render", help="write arm_wordings.md")
    common(r, responses_default=str(MAY_RESPONSES_DIR))
    r.add_argument("--may-scores-dir", default=str(MAY_SCORES_DIR))
    r.add_argument("--out", default=str(REPORT_DIR / "arm_wordings.md"))
    r.add_argument("--no-estimate", action="store_true", help="leave the cost section out")

    e = sub.add_parser("estimate", help="calls, tokens and dollars per arm")
    common(e, responses_default=str(MAY_RESPONSES_DIR))
    e.add_argument("--output-tokens", type=int, default=OUTPUT_TOKENS_PER_CALL)
    e.add_argument("--json-out", help="also write the estimate here")

    j = sub.add_parser("judge", help="judge every (arm, role, response) through the Batch API")
    common(j, responses_required=True)
    j.add_argument("--out-dir", required=True, help="the run directory")
    j.add_argument("--dry-run", action="store_true", help="build and count, submit nothing")
    j.add_argument("--batch-no-wait", action="store_true", help="submit and exit")
    j.add_argument("--collect-only", action="store_true", help="collect what is in flight; submit nothing")
    j.add_argument("--batch-id", action="append", default=[],
                   help="adopt a batch the state file does not record (repeatable)")
    from assistant_axis.openai_batch import DEFAULT_CHUNK_REQUESTS
    j.add_argument("--batch-requests", type=int, default=DEFAULT_CHUNK_REQUESTS,
                   help="requests per batch (step 3's default)")
    j.add_argument("--batch-poll-seconds", type=float, default=60.0)
    j.add_argument("--rejudge-unparseable", action="store_true",
                   help="request again the responses whose reply was unparseable (paid again)")
    j.add_argument("--confirm-expensive", action="store_true",
                   help=f"required over ${CONFIRM_ABOVE_USD:.0f}, once Roger has agreed")
    j.add_argument("--budget-usd", type=float, default=COST_CAP_USD,
                   help="refuse when the estimate is over this (default: Roger's cap)")
    j.add_argument("--allow-dirty", action="store_true")
    j.add_argument("--force-unlock", action="store_true")
    j.add_argument("--tmpdir", help="set TMPDIR for the atomic writes (/dev/shm on the pod)")

    a = sub.add_parser("analyze-scores", help="noise floor, flips, the reading sheet")
    a.add_argument("--scores-dir", required=True, help="the judge run directory")
    a.add_argument("--responses-dir", help="the responses (needed for the reading sheet)")
    a.add_argument("--roles-dir", default=str(ROLES_DIR))
    a.add_argument("--roles", nargs="+")
    a.add_argument("--report-dir", default=str(REPORT_DIR))
    a.add_argument("--sheet-per-arm", type=int, default=SHEET_PER_ARM)
    a.add_argument("--sheet-page-size", type=int, default=SHEET_PAGE_SIZE)
    a.add_argument("--seed", type=int, default=SHEET_SEED)
    a.add_argument("--no-sheet", action="store_true")
    a.add_argument("--overwrite-sheet", action="store_true",
                   help="replace a reading sheet that holds marks (copied aside first)")

    m = sub.add_parser("read-marks", help="tally the reading sheet's marks against its key")
    m.add_argument("--report-dir", default=str(REPORT_DIR))

    v = sub.add_parser("analyze-vectors", help="(on the pod) each arm's role vectors against A0's")
    v.add_argument("--activations-dir", required=True)
    v.add_argument("--scores-dir", required=True)
    v.add_argument("--roles-dir", default=str(ROLES_DIR))
    v.add_argument("--roles", nargs="+")
    v.add_argument("--arms", nargs="+")
    v.add_argument("--min-count", type=int, default=DEFAULT_MIN_COUNT,
                   help="step 4's --min_count as run_pipeline.sh passes it for roles (MIN_COUNT)")
    v.add_argument("--reduce-questions", type=int, default=1)
    v.add_argument("--report-dir", default=str(REPORT_DIR))
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    args = build_parser().parse_args(argv)
    handlers: Dict[str, Callable[[Any], int]] = {
        "render": cmd_render, "estimate": cmd_estimate, "judge": cmd_judge,
        "analyze-scores": cmd_analyze_scores, "read-marks": cmd_read_marks,
        "analyze-vectors": cmd_analyze_vectors}
    return handlers[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
