"""
Response generation utilities for transformer models.

This module provides functions for generating model responses using vLLM
for batch inference.

For HuggingFace generation, use ProbingModel.generate() from assistant_axis.internals.

Example (vLLM - batch inference):
    from assistant_axis.generation import VLLMGenerator

    generator = VLLMGenerator("google/gemma-2-27b-it")
    responses = generator.generate_batch(conversations)
"""

import hashlib
import json
import logging
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Dict, Mapping, Optional, Tuple

import torch
from tqdm import tqdm

logger = logging.getLogger(__name__)

# Where save_responses stages a response file before copying it to the output
# directory: local disk, not TMPDIR (which can point at NFS on RunPod).
_LOCAL_STAGING_DIR = Path("/tmp")

# The side-car step 1 writes beside the response files (``.json``, so no
# ``*.jsonl`` glob of steps 2 and 3 or the scanner sees it).  Schema: the
# multi-model plan, reports/pipeline/coding_plan_multi_model_extraction.md
# § 7; written since 2026-10-12 (walk-through P2).
GENERATION_CONFIG_NAME = "generation_config.json"
GENERATION_CONFIG_SCHEMA = 1


def chat_template_kwargs_for(family) -> Dict[str, Any]:
    """The chat-template kwargs step 1 renders with: the family row's
    (assistant_axis/model_families.py; thinking off for Qwen3,
    https://github.com/vllm-project/vllm/issues/18066).  One place, so the
    side-car records what generate_batch used.  Since 2026-10-13 (the
    multi-model plan) keyed on the row, not on a substring of the model
    name."""
    return dict(family.template_kwargs)


# Step 1's --response_cleanup (the response-token-ids plan § 4.3,
# 2026-11-02): "family" applies the family row's rule (today's behaviour),
# "keep" leaves vLLM's text as it came, leaked plan and all.  "family" is the
# default for now; the AGENT_NOTES TODO "keep leaked thinking instead of
# stripping it?" settles the default going forward (Roger, 2026-11-02).
RESPONSE_CLEANUP_OVERRIDES = ("family", "keep")

# The version of the clean-up rules this code applies, recorded in the
# side-car as response_cleanup_version under every clean-up ("none" included:
# it names the rule set the code applied) and compared by
# settings_differences.  1: the rule that made the October texts (cut to the
# last </think>, then .strip()); 2: the surgical cut of 2026-11-03
# (strip_leaked_plan; Roger).  Bump it whenever a clean-up changes what it does
# to a text.  A side-car written before the field has no key, so a rerun into
# such a directory is refused as None -> 2, which is right (the new stripped
# texts keep edge whitespace the old ones lost); --allow_mixed_settings
# overrides it as any other setting.
RESPONSE_CLEANUP_VERSION = 2


def response_cleanup_for(family, override: Optional[str] = None) -> str:
    """The clean-up applied to each generated text: the family row's
    (``strip_leaked_think`` for Qwen3, ``none`` otherwise), or ``"none"``
    under ``override="keep"`` (``--response_cleanup keep``).  The side-car
    records this, what was done to the text, with the flag beside it
    (``response_cleanup_override``), so that a directory refuses a later run
    only when its texts would have been cleaned differently: ``keep`` on a
    row whose rule is ``none`` is the same run as the default (Roger,
    2026-11-03; until then the side-car recorded the word ``keep`` and
    refused that pair).  ``keep`` means no clean-up at all; should a family
    ever get a second clean-up and "keep the plan only" be wanted, that is
    a new value, not a new meaning of ``keep``."""
    if override is None or override == "family":
        return family.response_cleanup
    if override == "keep":
        return "none"
    raise ValueError(f"response clean-up override {override!r} is not one of "
                     f"{RESPONSE_CLEANUP_OVERRIDES}")


def prompt_token_ids(tokenizer, conversation: List[Dict[str, str]],
                     template_kwargs: Mapping[str, Any]) -> List[int]:
    """The token ids step 1 hands vLLM for a conversation: the chat template
    with the generation prompt, tokenized by the template itself
    (``return_dict=False``).  Not the rendered text: vLLM tokenizes a text
    prompt with the tokenizer's special tokens, which gives Llama 3 and Gemma 2
    a second BOS after the one the template writes (review P1 D8).  For Qwen3
    the ids are the text path's (its tokenizer adds nothing to text)."""
    from .internals.chat_layout import chat_ids
    return chat_ids(tokenizer, conversation, add_generation_prompt=True,
                    template_kwargs=dict(template_kwargs))


# ---------------------------------------------------------------------------
# Leaked thinking without tags (walk-through P6; review P1 D4)
# ---------------------------------------------------------------------------
#
# With thinking off, Qwen3 sometimes still plans before answering.  When the
# plan ends in "</think>" generate_batch strips it (``thinking_stripped``);
# when it carries no tag at all the text stays, and is flagged
# ``thinking_suspected`` (the data are left as they are; P1 D4: "flag, leave
# the data").  The review's description of such a response: "Hmm, the user is
# asking... Let me break this down".  The signal used is the model talking
# about the conversation in the third person ("the user is asking", "the
# user's question") near the start, which an answer to the user does not do.
# Calibrated on the 8slot tree (2026-10-12): 196 of 291,000 role and trait
# responses, nearly all planning ("Okay, so the user is asking how ...") and a
# few out-of-character AI answers that speak of "the user".  A second rule, a
# planning opener ("Okay,", "Hmm") followed by talk of how to respond, was
# tried and dropped: its 20 extra hits were nearly all in-character answers
# (one extraction question asks how to respond to a pet sitter).

_THIRD_PERSON_USER = re.compile(
    r"\bthe user(?:'s)?\s+(?:is|was|asks|asked|wants|wanted|might|may|seems|has|"
    r"needs|question|request|query|message|mentioned|says|said)\b", re.IGNORECASE)
THINKING_SCAN_CHARS = 600


def looks_like_leaked_thinking(text: str) -> bool:
    """Whether a response speaks of "the user" in the third person within
    its first :data:`THINKING_SCAN_CHARS` characters (``"Okay, so the user
    is asking ..."``): the model's planning leaking into the answer without
    a ``</think>`` tag.  A heuristic, recorded as ``thinking_suspected``;
    nothing is removed."""
    return bool(_THIRD_PERSON_USER.search((text or "")[:THINKING_SCAN_CHARS]))


# The separator Qwen3 writes after </think>, in the template's think block and
# when its planning leaks with thinking off: one token in its vocabulary.
PLAN_SEPARATOR = "\n\n"


def strip_leaked_plan(text: str) -> str:
    """The ``strip_leaked_think`` clean-up of one text that has a leaked
    plan: everything up to and including the last ``</think>``, then
    exactly one ``"\\n\\n"`` if that is what immediately follows, and
    nothing else (Roger, 2026-11-03).  ``"</think>\\n\\n\\n"`` keeps its third
    newline; whitespace the model wrote at either end of its reply is its own
    and stays.  Until 2026-11-03 the cut was followed by ``.strip()``, which
    took that whitespace too, and step 1's content range started one token
    early, at the ``"\\n\\n"``; :func:`token_ranges` now cuts where this
    does.  A text without ``</think>`` raises ``ValueError`` (``rfind``
    would give -1 and cut its first seven characters)."""
    if "</think>" not in text:
        raise ValueError("strip_leaked_plan: the text has no </think> to cut at")
    rest = text[text.rfind("</think>") + len("</think>"):]
    if rest.startswith(PLAN_SEPARATOR):
        rest = rest[len(PLAN_SEPARATOR):]
    return rest


# ---------------------------------------------------------------------------
# The token ranges behind the stored text (the response-token-ids plan,
# reports/pipeline/response_token_ids/plan.md § 3 and § 4.2, 2026-11-02)
# ---------------------------------------------------------------------------
#
# Step 1 stores vLLM's ids verbatim (``response_token_ids``) and two ranges
# into them: ``content_token_range``, the tokens behind the stored content,
# and ``thinking_token_range``, the leaked plan's tokens.  Step 2 prefills the
# ids and averages slot 0 over the content range.  The content range is
# checked here, by decoding it, against the text it is said to be behind; a
# range that fails the check is not written (null), and step 2 takes the text
# path for that response.

# A UTF-8 character is at most four bytes, so a cap that lands inside one
# leaves at most three ids of it (each holds at least one byte).
MAX_PARTIAL_CHARACTER_IDS = 3
_REPLACEMENT_CHARACTER = "\ufffd"


def _decode_plain(tokenizer, ids: List[int]) -> str:
    """What vLLM's text is expected to be for ``ids``: special tokens left
    out (vLLM's default ``skip_special_tokens=True``) and no clean-up of
    spaces (vLLM's detokenizer does none; Llama 3's tokenizer config turns it
    on for ``decode``)."""
    return tokenizer.decode(list(ids), skip_special_tokens=True,
                            clean_up_tokenization_spaces=False)


def token_ranges(tokenizer, token_ids: List[int], text: str, *, leaked: bool, stripped: bool,
                 think_end_id: Optional[int], special_ids) -> Tuple[
                     Optional[Tuple[int, int]], Optional[Tuple[int, int]]]:
    """``(thinking_range, content_range)`` for one response: half-open index
    ranges into ``token_ids`` (vLLM's ids, verbatim), or None.

    ``text`` is the stored content (after the strip when ``stripped``),
    ``leaked`` whether the strip rule's detection fired on vLLM's text,
    ``stripped`` whether the strip was applied, ``think_end_id`` the id of
    ``</think>`` (None when the tokenizer has none) and ``special_ids`` the
    tokenizer's special ids.  The plan's § 4.2, step by step, with the cut
    of 2026-11-03 (Roger: the pointer follows the surgical strip exactly):

    1. When ``leaked``: ``k`` is the index after the last ``think_end_id``,
       and the cut is ``k + 1`` when the id at ``k`` decodes to exactly
       ``"\\n\\n"`` (one token; Qwen3 has it), else ``k``: where
       :func:`strip_leaked_plan` cuts the text.  The thinking range is
       ``(0, cut)`` whether or not the strip was applied, so that the two
       ranges partition the generated ids (the stop token and a character
       cut at the cap aside).  With no ``think_end_id`` (``</think>``
       spelled in pieces) the thinking range is None, and when ``stripped``
       so is the content range (its start is unknown).  The content starts
       at the cut when ``stripped``, else at 0.
    2. Trailing special ids (the stop token) are left out.
    3. Trailing ids that decode to a partial character (the cap landed inside
       one: the decoding ends in U+FFFD) are left out, at most
       :data:`MAX_PARTIAL_CHARACTER_IDS`.
    4. The check: the range decodes to exactly ``text``; the content range
       is None when it does not.  (A ``"\\n\\n\\n"`` token right after
       ``</think>``, of which the strip takes two characters, fails it: the
       record then takes step 2's text path.)
    """
    if stripped and not leaked:
        raise ValueError("a response cannot be stripped without the strip rule's detection")
    ids = [int(i) for i in token_ids]
    thinking = None
    start = 0
    if leaked:
        hits = ([i for i, t in enumerate(ids) if t == think_end_id]
                if think_end_id is not None else [])
        if hits:
            k = hits[-1] + 1
            cut = (k + 1 if k < len(ids) and _decode_plain(tokenizer, [ids[k]]) == PLAN_SEPARATOR
                   else k)
            thinking = (0, cut)
        elif stripped:
            return None, None
        if stripped:
            start = thinking[1]
    special = set(int(i) for i in special_ids)
    end = len(ids)
    while end > start and ids[end - 1] in special:
        end -= 1
    steps = 0
    while (end > start and steps < MAX_PARTIAL_CHARACTER_IDS
           and _decode_plain(tokenizer, ids[start:end]).endswith(_REPLACEMENT_CHARACTER)):
        end -= 1
        steps += 1
    decoded = _decode_plain(tokenizer, ids[start:end])
    return thinking, ((start, end) if decoded == text else None)


def _range_field(r: Optional[Tuple[int, int]]) -> Optional[List[int]]:
    """A range as the record stores it: ``[start, end]`` or null."""
    return None if r is None else [int(r[0]), int(r[1])]


def think_end_token_id(tokenizer) -> Optional[int]:
    """The id of ``</think>`` when the tokenizer has it as one token (Qwen3:
    151668), else None.  ``convert_tokens_to_ids`` gives the unknown token's
    id for a token it lacks, so the id is accepted only when it decodes to
    ``</think>``."""
    try:
        tid = tokenizer.convert_tokens_to_ids("</think>")
    except (KeyError, ValueError):
        return None
    if tid is None or isinstance(tid, list):
        return None
    return int(tid) if tokenizer.decode([int(tid)]) == "</think>" else None


def add_token_ranges(details: List[Dict[str, Any]], tokenizer, log=None) -> int:
    """Set ``thinking_token_range`` and ``content_token_range`` on each
    detail dict of :meth:`VLLMGenerator.generate_batch_detailed`
    (:func:`token_ranges`) and log the batch's null content ranges; returns
    their number.  A null range never stops the run: step 2 takes the text
    path for that response.  A tokenizer without ``all_special_ids`` is an
    error (2026-11-03): with no special ids the stop token would stay inside
    every range, and step 2 would refuse every record; step 1 is the place
    to fail."""
    log = log or logger
    special_ids = getattr(tokenizer, "all_special_ids", None)
    if special_ids is None:
        raise AttributeError(
            f"the tokenizer ({type(tokenizer).__name__}) has no all_special_ids; step 1 needs "
            f"them to leave the stop token out of each response's content range")
    special_ids = list(special_ids)
    think_end_id = think_end_token_id(tokenizer)
    n_null = n_pieces = 0
    for d in details:
        thinking, content = token_ranges(
            tokenizer, d["token_ids"], d["text"], leaked=d["leaked"],
            stripped=d["thinking_stripped"], think_end_id=think_end_id, special_ids=special_ids)
        d["thinking_token_range"] = _range_field(thinking)
        d["content_token_range"] = _range_field(content)
        if content is None:
            n_null += 1
            n_pieces += int(d["leaked"] and thinking is None)
    if n_null:
        pieces = (f" ({n_pieces} of them a stripped plan whose </think> is not one id)"
                  if n_pieces else "")
        log.warning(f"{n_null} of {len(details)} responses: the stored ids do not decode to the "
                    f"stored text{pieces}; their range is null and step 2 will take the text "
                    f"path for them")
    else:
        log.info(f"{len(details)} of {len(details)} responses: the stored ids decode to the "
                 f"stored text")
    return n_null


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def git_sha(repo: Optional[Path] = None) -> Optional[str]:
    """``<short sha>`` of the checkout, ``+dirty`` when tracked files are
    modified; None when git is unavailable."""
    repo = repo or Path(__file__).resolve().parent.parent
    try:
        sha = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=30, check=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(repo), "status", "--porcelain",
                                "--untracked-files=no"],
                               capture_output=True, text=True, timeout=60, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return sha + ("+dirty" if dirty else "") if sha else None


def instruction_dir_record(directory: Path) -> Dict[str, Any]:
    """What a run read from an instruction directory: the directory's
    content hash (sha256 over each ``*.json`` file's name and bytes, sorted)
    and, per stem, a hash of what step 1 actually uses, the ``instruction``
    list's ``pos`` texts (``pos_sha256``), so that a later edit can be traced
    to the entities whose responses it makes stale."""
    from .atomic_io import read_text_with_retry
    directory = Path(directory)
    h = hashlib.sha256()
    pos_sha: Dict[str, Optional[str]] = {}
    files = sorted(directory.glob("*.json"))
    for fp in files:
        text = read_text_with_retry(fp, logger_obj=logger)
        h.update(f"{fp.name}\0{_sha256_text(text)}\n".encode("utf-8"))
        try:
            pos = [i.get("pos", "") for i in json.loads(text).get("instruction", [])]
            pos_sha[fp.stem] = _sha256_text(json.dumps(pos, ensure_ascii=False))
        except (ValueError, AttributeError):
            pos_sha[fp.stem] = None
    return {"path": str(directory), "n_files": len(files), "sha256": h.hexdigest(),
            "pos_sha256": pos_sha}


def build_generation_run_record(
    *,
    model_name: str,
    family,
    layout,
    system_prompt: str,
    sample_conversation: List[Dict[str, str]],
    sample_prompt_ids: List[int],
    temperature: float,
    top_p: float,
    max_tokens: int,
    max_model_len: int,
    questions_file: str,
    question_count: int,
    reduce_questions: int,
    instruction_dirs: Mapping[str, Path],
    selection: Optional[Mapping[str, Any]] = None,
    script: str = "pipeline/1_generate.py",
    response_cleanup_override: Optional[str] = None,
) -> Dict[str, Any]:
    """One run's entry of ``generation_config.json``.  The field names are
    the multi-model plan's (§ 7: ``script``, ``created_at``, ``git_sha``,
    ``model_name``, ``model_type``, ``template_kwargs``, ``header_tokens``,
    ``header_ids``, ``generation_prompt_ids``, ``system_prompt``,
    ``response_cleanup``, ``sampling``, ``questions``,
    ``sample_conversation``, ``sample_prompt_ids``).  ``family`` is the
    model's row (assistant_axis/model_families.py), ``layout`` the header
    layout derived from its tokenizer
    (assistant_axis/internals/chat_layout.py), ``system_prompt`` what the
    template was seen to do with a system message (``native`` or
    ``fold_into_user``), and ``sample_prompt_ids`` the ids step 1 sends for
    ``sample_conversation``: step 2 re-renders that conversation and requires
    them to be its prefix.  Added beside the plan's fields (walk-through P2):
    the questions file's ``sha256`` and the number of questions kept,
    ``instructions`` (:func:`instruction_dir_record` per directory read) and
    ``selection`` (mode, flags, goal file and its hash, the work items).
    ``response_cleanup`` is the clean-up applied to the texts: the row's, or
    ``"none"`` under ``response_cleanup_override="keep"`` (``--response_cleanup
    keep``, since 2026-11-02); ``response_cleanup_override`` (since
    2026-11-03) is the flag's value, ``"family"`` or ``"keep"``, kept for the
    record and not compared by the side-car check
    (:func:`response_cleanup_for`); ``response_cleanup_version`` (since
    2026-11-03) is :data:`RESPONSE_CLEANUP_VERSION`, the version of the
    clean-up rules, compared by the check."""
    from .atomic_io import read_jsonl_with_retry, read_text_with_retry
    q_text = read_text_with_retry(questions_file, logger_obj=logger)
    n_all = len(read_jsonl_with_retry(questions_file, skip_malformed=False, logger_obj=logger))
    n_kept = len(range(min(question_count, n_all))[::max(reduce_questions, 1)])
    return {
        "script": script,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_sha": git_sha(),
        "model_name": model_name,
        "model_type": family.model_type,
        "template_kwargs": chat_template_kwargs_for(family),
        "header_tokens": list(layout.header_tokens),
        "header_ids": list(layout.header_ids),
        "generation_prompt_ids": list(layout.generation_prompt_ids),
        "system_prompt": system_prompt,
        "response_cleanup": response_cleanup_for(family, override=response_cleanup_override),
        "response_cleanup_override": response_cleanup_override or "family",
        "response_cleanup_version": RESPONSE_CLEANUP_VERSION,
        "sampling": {"temperature": temperature, "top_p": top_p,
                     "max_tokens": max_tokens, "max_model_len": max_model_len},
        "questions": {"file": str(questions_file), "sha256": _sha256_text(q_text),
                      "question_count": question_count, "reduce_questions": reduce_questions,
                      "n_kept": n_kept},
        "sample_conversation": [dict(m) for m in sample_conversation],
        "sample_prompt_ids": [int(i) for i in sample_prompt_ids],
        "instructions": {k: instruction_dir_record(Path(v)) for k, v in instruction_dirs.items()},
        "selection": dict(selection or {}),
    }


# What two runs into one responses directory must share: the generation
# settings.  Instructions may differ (they are reported per entity instead).
# model_type and header_ids since the multi-model plan (2026-10-13), so that
# step 1, tools/merge_pod_outputs.py and step 2's side-car check refuse the
# same differences.  response_cleanup_version since 2026-11-03: a record
# written before has none, so a rerun into such a directory is refused as
# None -> 2 (RESPONSE_CLEANUP_VERSION).
SETTINGS_KEYS = ("model_name", "model_type", "template_kwargs", "header_ids",
                 "response_cleanup", "response_cleanup_version", "sampling")
QUESTION_KEYS = ("sha256", "question_count", "reduce_questions")


def settings_differences(previous: Mapping[str, Any], current: Mapping[str, Any]) -> List[str]:
    """Human-readable differences between two run records' generation
    settings (model, template kwargs, clean-up, sampling, questions)."""
    diffs = []
    for k in SETTINGS_KEYS:
        if previous.get(k) != current.get(k):
            diffs.append(f"{k}: {previous.get(k)!r} -> {current.get(k)!r}")
    pq, cq = previous.get("questions") or {}, current.get("questions") or {}
    for k in QUESTION_KEYS:
        if pq.get(k) != cq.get(k):
            diffs.append(f"questions.{k}: {pq.get(k)!r} -> {cq.get(k)!r}")
    return diffs


def changed_instructions(previous: Mapping[str, Any], current: Mapping[str, Any]) -> List[str]:
    """Stems whose ``pos`` instructions hash differs between two run
    records (in any directory both read)."""
    out = []
    for key, cur in (current.get("instructions") or {}).items():
        prev = (previous.get("instructions") or {}).get(key)
        if not prev:
            continue
        for stem, h in (cur.get("pos_sha256") or {}).items():
            ph = (prev.get("pos_sha256") or {}).get(stem)
            if ph is not None and h != ph:
                out.append(stem)
    return sorted(set(out))


def read_generation_config(output_dir: Path) -> Optional[Dict[str, Any]]:
    """The side-car in ``output_dir``, or None when there is none.  A file
    that is not valid JSON raises (it is never silently replaced)."""
    from .atomic_io import read_text_with_retry
    path = Path(output_dir) / GENERATION_CONFIG_NAME
    if not path.exists():
        return None
    return json.loads(read_text_with_retry(path, logger_obj=logger))


def write_generation_config(output_dir: Path, run_record: Mapping[str, Any]) -> Path:
    """Append ``run_record`` to ``output_dir/generation_config.json``
    (``{"schema": 1, "runs": [...]}``; a rerun that fills gaps appends),
    written atomically."""
    from .atomic_io import atomic_write_text
    output_dir = Path(output_dir)
    existing = read_generation_config(output_dir) or {"schema": GENERATION_CONFIG_SCHEMA, "runs": []}
    existing.setdefault("runs", []).append(dict(run_record))
    path = output_dir / GENERATION_CONFIG_NAME
    atomic_write_text(json.dumps(existing, indent=1, ensure_ascii=False) + "\n", path,
                      logger_obj=logger)
    return path


def generate_response(
    model,
    tokenizer,
    conversation: List[Dict[str, str]],
    max_new_tokens: int = 512,
    temperature: float = 0.7,
    top_p: float = 0.9,
    do_sample: bool = True,
    family=None,
) -> str:
    """
    Generate a single response for a conversation using HuggingFace.

    Not on the pipeline path.  The template kwargs are the family row's
    (``family``, or the row of ``model.config.model_type``; an unknown type
    raises), and the prompt is handed over as the template's token ids, as
    step 1 does since 2026-10-13 (the multi-model plan).

    Args:
        model: HuggingFace model
        tokenizer: HuggingFace tokenizer
        conversation: List of message dicts
        max_new_tokens: Maximum tokens to generate
        temperature: Sampling temperature
        top_p: Top-p sampling parameter
        do_sample: Whether to sample (False = greedy)

    Returns:
        Generated response text
    """
    if family is None:
        from .model_families import family_for_model_type
        family = family_for_model_type(getattr(getattr(model, "config", None), "model_type", None))
    ids = prompt_token_ids(tokenizer, conversation, family.template_kwargs)
    input_ids = torch.tensor([ids], device=model.device)
    input_length = input_ids.shape[1]

    with torch.no_grad():
        outputs = model.generate(
            input_ids=input_ids,
            attention_mask=torch.ones_like(input_ids),
            max_new_tokens=max_new_tokens,
            temperature=temperature if do_sample else None,
            top_p=top_p if do_sample else None,
            do_sample=do_sample,
            pad_token_id=tokenizer.pad_token_id,
        )

    response = tokenizer.decode(
        outputs[0][input_length:],
        skip_special_tokens=True
    )

    return response


# NOTE (re-extracted helper, not new functionality):
#
# This helper is a verbatim re-extraction of the inline probe that
# previously lived inside ``format_conversation`` below.  The probe
# itself was first added in commit 5e571f5 ("Update response token
# index method.", 2026-01-13) as a top-level function with this exact
# body, alongside ``tests/test_generation.py`` which imports it by
# name.  The very next day, commit 81e0af5 ("Add trait list and
# import internals/ for activation capture.", 2026-01-14) inlined the
# probe into ``format_conversation`` as part of a larger refactor
# that pivoted ``generation.py`` from HuggingFace toward vLLM and
# moved a chunk of code into ``assistant_axis/internals/``.  That
# inlining did not update ``test_generation.py``, so its
# ``from assistant_axis.generation import supports_system_prompt``
# line has been a silent test-collection error on Christina's branch
# ever since (about four weeks before this repo was forked off it on
# 2026-02-10).  No behavioural change: ``format_conversation`` below
# now calls this helper instead of inlining the identical probe.
# Cherrypick-friendly: dropping this helper back into Christina's
# branch fixes her test without touching anything else.
def supports_system_prompt(tokenizer) -> bool:
    """Check whether a tokenizer's chat template supports system prompts.

    Detects support behaviourally: applies the chat template to a
    two-message conversation containing a sentinel system message,
    and checks whether the sentinel survives in the rendered output.
    Templates that raise on a ``system`` role (e.g. Gemma 2's "System
    role not supported" Jinja exception) and templates that silently
    drop / merge the system message both correctly return ``False``.

    Args:
        tokenizer: HuggingFace tokenizer.

    Returns:
        ``True`` if the rendered template preserves the system
        content verbatim, ``False`` otherwise.
    """
    test_message = "__SYSTEM_TEST__"
    test_conversation = [
        {"role": "system", "content": test_message},
        {"role": "user", "content": "hello"},
    ]
    try:
        output = tokenizer.apply_chat_template(
            test_conversation,
            tokenize=False,
            add_generation_prompt=False,
        )
        return test_message in output
    except Exception:
        return False


_SYSTEM_PROMPT_WARNED: set = set()


def system_prompt_mode(tokenizer, family=None) -> str:
    """``"native"`` when the template keeps a system message
    (:func:`supports_system_prompt`), else ``"fold_into_user"``.  With a
    family row whose ``system_prompt`` says otherwise, a WARNING (once per
    family and outcome): a template that drops the system message on a row
    marked native would generate without the persona instruction if nothing
    folded it; the fold keeps the run usable, and the warning says so
    (multi-model plan § 5.3)."""
    mode = "native" if supports_system_prompt(tokenizer) else "fold_into_user"
    if family is not None and family.system_prompt != mode:
        key = (family.model_type, mode)
        if key not in _SYSTEM_PROMPT_WARNED:
            _SYSTEM_PROMPT_WARNED.add(key)
            logger.warning(
                f"the chat template's system-prompt behaviour is {mode!r}, but the "
                f"{family.model_type!r} family row says {family.system_prompt!r}; "
                f"conversations are built as {mode!r} (assistant_axis/model_families.py)")
    return mode


def format_conversation(
    instruction: Optional[str],
    question: str,
    tokenizer,
    family=None,
) -> List[Dict[str, str]]:
    """
    Format a conversation for model input.

    Args:
        instruction: Optional system instruction
        question: User question
        tokenizer: HuggingFace tokenizer (to check system prompt support)
        family: the model's family row; when given, a template whose
            system-prompt behaviour differs from the row's is warned about
            (:func:`system_prompt_mode`)

    Returns:
        List of message dicts for the conversation
    """
    if system_prompt_mode(tokenizer, family) == "native":
        messages = []
        if instruction:
            messages.append({"role": "system", "content": instruction})
        messages.append({"role": "user", "content": question})
        return messages
    else:
        # Concatenate instruction with question for models without system support
        if instruction:
            formatted = f"{instruction}\n\n{question}"
        else:
            formatted = question
        return [{"role": "user", "content": formatted}]


# =============================================================================
# vLLM Generation (for batch inference / pipeline)
# =============================================================================

class VLLMGenerator:
    """
    Generator for batch inference using vLLM.

    Example:
        generator = VLLMGenerator("google/gemma-2-27b-it")
        responses = generator.generate_batch(conversations)
    """

    def __init__(
        self,
        model_name: str,
        max_model_len: int = 2048,
        tensor_parallel_size: Optional[int] = None,
        gpu_memory_utilization: float = 0.9,
        temperature: float = 0.7,
        max_tokens: int = 512,
        top_p: float = 0.9,
        family=None,
        expected_header_ids: Optional[List[int]] = None,
        response_cleanup_override: Optional[str] = None,
    ):
        """
        Initialize vLLM generator.

        Args:
            model_name: HuggingFace model name
            max_model_len: Maximum model context length
            tensor_parallel_size: Number of GPUs (None for auto-detect)
            gpu_memory_utilization: GPU memory utilization
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Top-p sampling
            family: the model's family row (assistant_axis/model_families.py);
                None: read from the model's config.json at :meth:`load`
            expected_header_ids: the header ids step 1's preflight derived
                (and recorded in the side-car); the layout derived from vLLM's
                tokenizer at :meth:`load` must have the same
            response_cleanup_override: ``--response_cleanup``: None or
                ``"family"`` (the row's rule) or ``"keep"`` (no strip;
                :func:`response_cleanup_for`)
        """
        if response_cleanup_override not in (None,) + RESPONSE_CLEANUP_OVERRIDES:
            raise ValueError(f"response_cleanup_override {response_cleanup_override!r} is not "
                             f"one of {RESPONSE_CLEANUP_OVERRIDES}")
        self.model_name = model_name
        self.max_model_len = max_model_len
        self.tensor_parallel_size = tensor_parallel_size
        self.gpu_memory_utilization = gpu_memory_utilization
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.family = family
        self.expected_header_ids = (list(expected_header_ids)
                                    if expected_header_ids is not None else None)
        self.response_cleanup_override = response_cleanup_override
        self.layout = None

        self.llm = None
        self.sampling_params = None

    def load(self):
        """Load the vLLM model.

        The family row is resolved first (an unknown ``model_type`` or a row
        not built refuses before vLLM starts); after the load the header
        layout is derived from vLLM's tokenizer and logged."""
        if self.llm is not None:
            return

        from .model_families import family_for_model, require_built
        if self.family is None:
            self.family = family_for_model(self.model_name)
        require_built(self.family)

        from vllm import LLM, SamplingParams

        logger.info(f"Loading vLLM model: {self.model_name} (family {self.family.model_type})")

        self.llm = LLM(
            model=self.model_name,
            max_model_len=self.max_model_len,
            tensor_parallel_size=self.tensor_parallel_size,
            gpu_memory_utilization=self.gpu_memory_utilization,
            # From the row since 2026-10-13 (False for every row: all are
            # native in transformers and vLLM); it was True for every model.
            trust_remote_code=self.family.trust_remote_code,
        )

        self.sampling_params = SamplingParams(
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            top_p=self.top_p,
        )

        from .internals.chat_layout import LayoutError, derive_chat_layout
        self.layout = derive_chat_layout(self.llm.get_tokenizer(), self.family)
        if (self.expected_header_ids is not None
                and list(self.layout.header_ids) != self.expected_header_ids):
            raise LayoutError(
                f"vLLM's tokenizer derives the header ids {list(self.layout.header_ids)}; the "
                f"preflight (and the side-car) has {self.expected_header_ids}")
        logger.info(f"Model loaded successfully; header {list(self.layout.header_tokens)!r} "
                    f"(ids {list(self.layout.header_ids)})")

    def generate_batch(
        self,
        conversations: List[List[Dict[str, str]]],
    ) -> List[str]:
        """
        Generate responses for a batch of conversations.

        Args:
            conversations: List of conversations (each is a list of message dicts)

        Returns:
            List of generated response texts (see :meth:`generate_batch_detailed`
            for the finish reason and the clean-up flags)
        """
        return [d["text"] for d in self.generate_batch_detailed(conversations)]

    def generate_batch_detailed(
        self,
        conversations: List[List[Dict[str, str]]],
    ) -> List[Dict[str, Any]]:
        """Generate responses for a batch of conversations; one dict per
        conversation: ``text``, ``finish_reason`` (vLLM's: ``"stop"``, or
        ``"length"`` when the text was cut at ``max_tokens``),
        ``thinking_stripped`` (the leaked-thinking strip below changed the
        text) and ``thinking_suspected`` (:func:`looks_like_leaked_thinking`
        on the final text).  The three are the additive response fields of
        walk-through P6 (2026-10-12).

        Since the response-token-ids plan (2026-11-02,
        reports/pipeline/response_token_ids/plan.md § 4.1) also ``token_ids``,
        the ids vLLM sampled (``output.outputs[0].token_ids``) verbatim as
        ints, leaked plan and stop token included; ``leaked``, whether the
        strip rule's detection fired (``</think>`` in vLLM's text, ``<think>``
        not), decided before any strip; ``raw_text``, vLLM's text before the
        strip, when the strip changed it; and (§ 4.2) ``thinking_token_range``
        and ``content_token_range`` (:func:`token_ranges`, as ``[start,
        end]`` lists or None)."""
        self.load()

        tokenizer = self.llm.get_tokenizer()

        # The family row's template kwargs (thinking off for Qwen3:
        # https://github.com/vllm-project/vllm/issues/18066), and the prompt
        # as the template's token ids (vllm.inputs.TokensPrompt, a TypedDict:
        # this dict is one), not as rendered text (multi-model plan § 5.3).
        chat_template_kwargs = chat_template_kwargs_for(self.family)
        prompts = [{"prompt_token_ids": prompt_token_ids(tokenizer, conv, chat_template_kwargs)}
                   for conv in conversations]

        logger.info(f"Running batch inference for {len(prompts)} prompts...")
        outputs = self.llm.generate(prompts, self.sampling_params)

        # The sampled ids are kept as vLLM returned them (a tuple or an array:
        # plain ints, for JSON), so that step 2 can prefill what the model
        # generated instead of a re-encoding of the text (the
        # response-token-ids plan, 2026-11-02).  Read by attribute: every vLLM
        # CompletionOutput has them, and an output without them should fail
        # loudly, not write records without ids.
        details = [{"text": output.outputs[0].text,
                    "finish_reason": getattr(output.outputs[0], "finish_reason", None),
                    "thinking_stripped": False,
                    "token_ids": [int(i) for i in output.outputs[0].token_ids],
                    "leaked": False}
                   for output in outputs]

        # Workaround: vLLM sometimes generates thinking content with Qwen
        # models despite enable_thinking=False. It strips the opening <think>
        # tag but leaves </think> and the preceding thinking text in the
        # output.  Cut the plan surgically (strip_leaked_plan): everything up
        # to and including the last </think>, and the one "\n\n" after it.
        # The text before the strip is kept as raw_text (2026-11-02), for
        # readers that have no tokenizer.  The detection is the family rule's
        # and runs under --response_cleanup keep too (the response-token-ids
        # plan § 4.3): then the text is left as vLLM gave it and only the
        # plan's token range records where the plan is.
        detect = self.family.response_cleanup == "strip_leaked_think"
        strip = (response_cleanup_for(self.family, override=self.response_cleanup_override)
                 == "strip_leaked_think")
        if detect:
            cleaned = kept = ragged = 0
            for d in details:
                resp = d["text"]
                if '</think>' in resp and '<think>' not in resp:
                    d["leaked"] = True
                    if not strip:
                        kept += 1
                        continue
                    d["raw_text"] = resp
                    d["text"] = strip_leaked_plan(resp)
                    d["thinking_stripped"] = True
                    cleaned += 1
                    ragged += int(d["text"] != d["text"].strip())
            if cleaned:
                # How many stripped texts still begin or end with whitespace,
                # the model's own, which the strip keeps (until 2026-11-03 a
                # .strip() removed it unseen): the smoke run's count.
                logger.warning(
                    f"Stripped orphaned thinking content from {cleaned}/{len(details)} "
                    f"responses (vLLM/Qwen thinking leak); {ragged} of them still begin or "
                    f"end with whitespace, which is kept")
            if kept:
                logger.warning(
                    f"Kept orphaned thinking content in {kept}/{len(details)} responses "
                    f"(--response_cleanup keep: the stored text, which step 3 judges, holds "
                    f"the plan)")
        for d in details:
            d["thinking_suspected"] = looks_like_leaked_thinking(d["text"])
        # The two token ranges, checked against the text they point at
        # (the response-token-ids plan § 4.2, 2026-11-02).
        add_token_ranges(details, tokenizer)
        return details

    def generate_for_role(
        self,
        instructions: List[str],
        questions: List[str],
        prompt_indices: Optional[List[int]] = None,
        question_ids: Optional[List[Any]] = None,
    ) -> List[Dict]:
        """
        Generate responses for a role across all instruction variants and questions.

        Args:
            instructions: List of system prompt variants
            questions: List of questions
            prompt_indices: Which instruction indices to use (default: all)
            question_ids: The questions file's ``id`` of each question
                (parallel to ``questions``); recorded as ``question_id``

        Returns:
            List of result dicts with conversation, prompt_index,
            question_index, and since 2026-10-12 (walk-through P6, additive)
            question_id, finish_reason, thinking_stripped, thinking_suspected;
            since 2026-11-02 (the response-token-ids plan, additive)
            response_token_ids, content_token_range, thinking_token_range,
            and raw_text when thinking_stripped
        """
        self.load()
        tokenizer = self.llm.get_tokenizer()

        if prompt_indices is None:
            prompt_indices = list(range(len(instructions)))
        if question_ids is not None and len(question_ids) != len(questions):
            raise ValueError(f"{len(question_ids)} question ids for {len(questions)} questions")

        # Build all conversations
        all_conversations = []
        all_metadata = []

        for prompt_idx in prompt_indices:
            if prompt_idx >= len(instructions):
                continue

            instruction = instructions[prompt_idx]

            for q_idx, question in enumerate(questions):
                conversation = format_conversation(instruction, question, tokenizer,
                                                   family=self.family)
                all_conversations.append(conversation)
                all_metadata.append({
                    "system_prompt": instruction,
                    "prompt_index": prompt_idx,
                    "question_index": q_idx,
                    "question_id": None if question_ids is None else question_ids[q_idx],
                    "question": question,
                })

        if not all_conversations:
            return []

        # Generate
        details = self.generate_batch_detailed(all_conversations)

        # Build results.  The keys before "conversation" are those written
        # since the start; the four after it are additive (2026-10-12), and
        # steps 2 and 3 read records by key, so they ignore them.  After those,
        # since 2026-11-02 (the response-token-ids plan § 3): the ids vLLM
        # sampled, verbatim; content_token_range, [start, end) into them of
        # the tokens behind the stored content (null when the decoding check
        # failed: step 2 then re-encodes the text); thinking_token_range,
        # [0, cut) of the leaked plan's tokens, its last </think> and the
        # "\n\n" after it (null when none was detected or </think> is not one
        # id; the two ranges partition the ids); and, when the strip changed
        # the text, raw_text, the text before it.  Step 3 and the response
        # judging read the stored content and have no tokenizer; since
        # 2026-11-03 a stripped one keeps the model's own whitespace at its
        # ends (strip_leaked_plan).
        results = []
        for conv, meta, d in zip(all_conversations, all_metadata, details):
            result = {
                "system_prompt": meta["system_prompt"],
                "prompt_index": meta["prompt_index"],
                "question_index": meta["question_index"],
                "question": meta["question"],
                "conversation": conv + [{"role": "assistant", "content": d["text"]}],
                "question_id": meta["question_id"],
                "finish_reason": d["finish_reason"],
                "thinking_stripped": d["thinking_stripped"],
                "thinking_suspected": d["thinking_suspected"],
                "response_token_ids": d["token_ids"],
                "content_token_range": d["content_token_range"],
                "thinking_token_range": d["thinking_token_range"],
            }
            if d["thinking_stripped"]:
                result["raw_text"] = d["raw_text"]
            results.append(result)

        return results


class RoleResponseGenerator:
    """
    Generator for role-based model responses using vLLM batch inference.

    Processes role JSON files and generates responses for all roles.

    Example:
        generator = RoleResponseGenerator(
            model_name="google/gemma-2-27b-it",
            roles_dir="data/prompts/roles",
            output_dir="outputs/responses",
            questions_file="data/prompts/questions.jsonl"
        )
        generator.process_all_roles()
    """

    def __init__(
        self,
        model_name: str,
        roles_dir: str,
        output_dir: str,
        questions_file: str,
        max_model_len: int = 2048,
        tensor_parallel_size: Optional[int] = None,
        gpu_memory_utilization: float = 0.9,
        question_count: int = 300,
        reduce_questions: int = 1,
        temperature: float = 0.7,
        max_tokens: int = 512,
        top_p: float = 0.9,
        prompt_indices: Optional[List[int]] = None,
        short_name: Optional[str] = None,
        family=None,
        expected_header_ids: Optional[List[int]] = None,
        response_cleanup_override: Optional[str] = None,
    ):
        """
        Initialize role response generator.

        Args:
            model_name: HuggingFace model name
            roles_dir: Directory containing role JSON files
            output_dir: Output directory for JSONL files
            questions_file: Path to questions JSONL file
            max_model_len: Maximum model context length
            tensor_parallel_size: Number of GPUs
            gpu_memory_utilization: GPU memory utilization
            question_count: Number of questions per role
            reduce_questions: Take every Nth question (1 = all, 3 = every 3rd)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Top-p sampling
            prompt_indices: Which prompt indices to use (default: 0-4)
            short_name: Short model name for formatting (auto-detected if None)
            family, expected_header_ids, response_cleanup_override: passed to
                :class:`VLLMGenerator`
        """
        self.model_name = model_name
        self.roles_dir = Path(roles_dir)
        self.output_dir = Path(output_dir)
        self.questions_file = questions_file
        self.question_count = question_count
        self.reduce_questions = reduce_questions
        self.prompt_indices = prompt_indices if prompt_indices is not None else list(range(5))

        # Get short name for {model_name} placeholder
        if short_name is None:
            from .models import get_config
            config = get_config(model_name)
            self.short_name = config["short_name"]
        else:
            self.short_name = short_name

        self.generator = VLLMGenerator(
            model_name=model_name,
            max_model_len=max_model_len,
            tensor_parallel_size=tensor_parallel_size,
            gpu_memory_utilization=gpu_memory_utilization,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            family=family,
            expected_header_ids=expected_header_ids,
            response_cleanup_override=response_cleanup_override,
        )

        self.questions = None
        self.question_ids = None     # the questions file's ``id`` of each kept question
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized RoleResponseGenerator with model: {model_name}")
        logger.info(f"Output directory: {self.output_dir}")

    def load_questions(self) -> List[str]:
        """Load questions from JSONL file."""
        if self.questions is not None:
            return self.questions

        # Retried read (the repo lives on the /workspace network mount on
        # RunPod; AGENT_NOTES "NFS-safe file I/O").  A malformed line raises
        # rather than being skipped: skipping it would renumber every later
        # question, and question_index is a position in this list.
        from .atomic_io import read_jsonl_with_retry
        entries = read_jsonl_with_retry(
            self.questions_file, skip_malformed=False, logger_obj=logger)
        entries = entries[:self.question_count]
        if self.reduce_questions > 1:
            entries = entries[::self.reduce_questions]
        self.questions = [entry['question'] for entry in entries]
        # The file's own id of each kept question (walk-through P6,
        # 2026-10-12): question_index below is a position in this reduced
        # list, so it alone does not say which question it was.
        self.question_ids = [entry.get('id') for entry in entries]
        # TODO(design-debt): the question_index stored downstream (see
        # generate_role_responses's enumerate(questions)) is 0-based into this
        # already-reduced list, not into the original questions file.  That
        # means activation keys like pos_p3_q7 give no indication of whether
        # they came from a reduce=1 run (original q7) or a reduce=3 run
        # (original q21), and there's no stable identifier tying activations
        # back to a specific question.  Consequences:
        #   - post-hoc further reduction at step 4 composes oddly
        #     (see 4_vectors.py; reduce=3 at step 1 + reduce=3 at step 4 = 9x,
        #      not 3x, because step 4 sees renumbered indices)
        #   - can't fill in missing questions later (e.g., add 80 more to a
        #     240-question run) without regenerating everything
        #   - can't cross-reference activations across runs with different
        #     reduce settings
        # Partly addressed 2026-10-12 (walk-through P6): every response record
        # now also carries question_id, the questions file's own id, so the
        # original question of a record is known; the keys (and so step 2's
        # activation keys and step 4's --reduce_questions) are unchanged.
        # Better design: store the original question index in the activation
        # key (e.g., pos_p3_q021 for original index 21), always 0-based into
        # the full questions file.  Not fixing now because we have substantial
        # data generated across multiple runs/pods under the current scheme.
        logger.info(f"Loaded {len(self.questions)} questions")
        return self.questions

    def load_role(self, role_file: Path) -> dict:
        """Load a role (or trait) JSON file, retrying transient read errors
        (the repo lives on the /workspace network mount on RunPod)."""
        from .atomic_io import read_text_with_retry
        return json.loads(read_text_with_retry(role_file, logger_obj=logger))

    def format_instruction(self, instruction: str) -> str:
        """Format instruction, replacing {model_name} placeholder."""
        return instruction.replace("{model_name}", self.short_name)

    def generate_role_responses(self, role_name: str, role_data: dict) -> List[dict]:
        """Generate responses for a single role or trait."""
        instructions = role_data.get('instruction', [])
        if not instructions:
            return []

        questions = self.load_questions()

        formatted_instructions = []
        for inst in instructions:
            raw = inst.get('pos', '')
            formatted_instructions.append(self.format_instruction(raw))

        logger.info(f"Processing '{role_name}' with {len(questions)} questions")

        results = self.generator.generate_for_role(
            instructions=formatted_instructions,
            questions=questions,
            prompt_indices=self.prompt_indices,
            question_ids=self.question_ids,
        )

        for r in results:
            r["label"] = "pos"

        return results

    def generate_combined_responses(
        self,
        role_data: dict,
        trait_data: dict,
        role_name: str,
        trait_name: str,
        goal_source: str,
    ) -> List[dict]:
        """Generate responses for a combined role+trait instruction.

        Concatenates role and trait pos instructions index-matched
        (pair 0-0, 1-1, ...) separated by a newline.

        Args:
            role_data: Role JSON data with 'instruction' list
            trait_data: Trait JSON data with 'instruction' list
            role_name: Role identifier (for metadata)
            trait_name: Trait identifier (for metadata)
            goal_source: "role" or "trait" indicating which carries the goal
        """
        role_instructions = role_data.get('instruction', [])
        trait_instructions = trait_data.get('instruction', [])
        if not role_instructions or not trait_instructions:
            return []

        questions = self.load_questions()

        n_pairs = min(len(role_instructions), len(trait_instructions))
        combined_instructions = []
        for i in range(n_pairs):
            role_inst = self.format_instruction(role_instructions[i].get('pos', ''))
            trait_inst = self.format_instruction(trait_instructions[i].get('pos', ''))
            combined_instructions.append(f"{role_inst}\n{trait_inst}")

        prompt_indices = [i for i in self.prompt_indices if i < n_pairs]

        logger.info(f"Processing combined '{role_name}+{trait_name}' "
                    f"(goal={goal_source}) with {len(questions)} questions")

        results = self.generator.generate_for_role(
            instructions=combined_instructions,
            questions=questions,
            prompt_indices=prompt_indices,
            question_ids=self.question_ids,
        )

        for r in results:
            r["label"] = "pos"
            r["role"] = role_name
            r["trait"] = trait_name
            r["goal_source"] = goal_source

        return results

    def save_responses(self, role_name: str, responses: List[dict]):
        """Save responses to JSONL file.

        Writes to local /tmp first, then copies to the output directory to
        avoid partial-write failures on flaky network filesystems (RunPod NFS).
        """
        import jsonlines
        import os
        import shutil
        import uuid

        output_file = self.output_dir / f"{role_name}.jsonl"
        # Copied to a side name and renamed into place: a copy that dies
        # half way (a killed process, an NFS error on the last attempt) must
        # not leave a truncated <role>.jsonl, which should_skip_role() would
        # then treat as done on every later run (fixed 2026-10-12).
        inprogress = output_file.with_name(output_file.name + ".inprogress")
        # Bypass TMPDIR (which points to NFS on RunPod) — /tmp is always local.
        # A unique name per save: the fixed /tmp/<role>.jsonl.tmp was shared by
        # every process saving that name, so two step-1 runs at once (roles and
        # traits on different GPUs) could copy each other's responses for the
        # eleven names that are both a role and a trait (fixed 2026-10-12).
        # Not tempfile.mkstemp: its file is mode 0600, and copy2 would carry
        # that onto the response file; open() gives the umask's mode as before.
        local_tmp = _LOCAL_STAGING_DIR / (
            f"{role_name}.{os.getpid()}.{uuid.uuid4().hex[:12]}.jsonl.tmp")
        with jsonlines.open(local_tmp, mode='w') as writer:
            for response in responses:
                writer.write(response)
        for attempt in range(5):
            try:
                shutil.copy2(str(local_tmp), str(inprogress))
                os.replace(str(inprogress), str(output_file))
                logger.info(f"Saved {len(responses)} responses to {output_file}")
                break
            except OSError as e:
                if attempt < 4:
                    import time
                    wait = 10 * (attempt + 1)
                    logger.warning(f"Copy to NFS failed for {role_name} (attempt {attempt+1}/5): {e}. "
                                   f"Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    logger.error(f"Copy to NFS failed for {role_name} after 5 attempts: {e}; "
                                 f"the local copy is kept at {local_tmp}")
                    inprogress.unlink(missing_ok=True)
                    raise
        local_tmp.unlink(missing_ok=True)

    def write_generation_config(self, run_record: Mapping[str, Any]) -> Path:
        """Append a run record to this generator's output directory's
        ``generation_config.json`` (the module function of that name)."""
        return write_generation_config(self.output_dir, run_record)

    def should_skip_role(self, role_name: str) -> bool:
        """Check if role output already exists."""
        output_file = self.output_dir / f"{role_name}.jsonl"
        return output_file.exists()

    def process_all_roles(
        self,
        skip_existing: bool = True,
        roles: Optional[List[str]] = None,
    ):
        """
        Process all roles and generate responses.

        Args:
            skip_existing: Skip roles with existing output files
            roles: Specific role names to process (None for all)
        """
        # Load model
        self.generator.load()
        self.load_questions()

        # Get role files
        role_files = {}
        for file_path in sorted(self.roles_dir.glob("*.json")):
            role_name = file_path.stem
            try:
                role_data = self.load_role(file_path)
                if 'instruction' not in role_data:
                    logger.warning(f"Skipping {role_name}: missing 'instruction' field")
                    continue
                role_files[role_name] = role_data
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")

        logger.info(f"Found {len(role_files)} role files")

        # Filter
        if roles:
            role_files = {k: v for k, v in role_files.items() if k in roles}

        if skip_existing:
            role_files = {k: v for k, v in role_files.items() if not self.should_skip_role(k)}

        logger.info(f"Processing {len(role_files)} roles")

        # Process
        for role_name, role_data in tqdm(role_files.items(), desc="Processing roles"):
            try:
                responses = self.generate_role_responses(role_name, role_data)
                if responses:
                    self.save_responses(role_name, responses)
            except Exception as e:
                logger.error(f"Error processing {role_name}: {e}")
