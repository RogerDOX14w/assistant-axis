#!/usr/bin/env python3
"""
Extract activations from response JSONL files.

This script loads responses from per-role JSONL files and extracts mean response
activations for each conversation, saving them as .pt files per role.

Supports automatic multi-worker parallelization when total GPUs > tensor_parallel_size.
Number of workers = total_gpus // tensor_parallel_size

The model's family (assistant_axis/model_families.py, keyed on config.json's
model_type) gives the chat-template kwargs and the span builder; the header
slots are derived from the model's own chat template before any model is
loaded (assistant_axis/internals/chat_layout.py).  A model_type with no row
in the table refuses to run (multi-model plan, 2026-10-13).

Usage:
    uv run pipeline/2_activations.py \
        --model google/gemma-2-27b-it \
        --responses_dir outputs/gemma-2-27b/responses \
        --output_dir outputs/gemma-2-27b/activations

    # With tensor parallelism (auto-parallelizes across workers)
    uv run pipeline/2_activations.py \
        --model google/gemma-2-27b-it \
        --tensor_parallel_size 2 \
        ...
"""

import argparse
import gc
import logging
import os
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class LayersError(ValueError):
    """``--layers`` is not ``all`` or a strictly increasing list of layer
    indices within the model's range."""


def parse_layers(spec: str, n_layers: Optional[int]) -> List[int]:
    """``--layers`` as model layer indices: ``all``, or comma-separated
    integers, strictly increasing (sorted, no repeats) and within
    ``[0, n_layers)``; with ``n_layers`` None only the form and the order are
    checked.  Raises :class:`LayersError`.

    Until 2026-10-13 any list was taken as given (review P2 D1): a negative
    index picked a layer from the end and a repeated or unsorted one shifted
    the layer axis, which is positional in ``--layers``, without a word."""
    if spec.strip() == "all":
        if n_layers is None:
            return []
        return list(range(n_layers))
    have = f" (the model has {n_layers} layers, 0..{n_layers - 1})" if n_layers else ""
    try:
        layers = [int(x.strip()) for x in spec.split(",") if x.strip()]
    except ValueError:
        raise LayersError(f"--layers {spec!r}: not 'all' or a comma-separated list of "
                          f"integers{have}") from None
    if not layers:
        raise LayersError(f"--layers {spec!r}: no layer given{have}")
    if any(b <= a for a, b in zip(layers, layers[1:])):
        raise LayersError(f"--layers {spec}: must be strictly increasing (sorted, no "
                          f"repeats){have}")
    bad = [x for x in layers if x < 0 or (n_layers is not None and x >= n_layers)]
    if bad:
        raise LayersError(f"--layers {spec}: {bad} out of range{have}")
    return layers


def _layers_arg(spec: str) -> str:
    """argparse type for --layers: the form and order now, the range once the
    model's layer count is known (main, and each worker after its load)."""
    try:
        parse_layers(spec, None)
    except LayersError as e:
        raise argparse.ArgumentTypeError(str(e)) from None
    return spec


class _RemovedFlag(argparse.Action):
    """A flag that is gone: an argparse error saying why."""

    def __call__(self, parser, namespace, values, option_string=None):
        parser.error(f"{option_string} was removed on 2026-10-13 (multi-model plan, review "
                     f"P2 D2): step 1 never generates with thinking on, and the chat-template "
                     f"kwargs come from the model's family row (assistant_axis/model_families.py)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract activations from responses")
    parser.add_argument("--model", type=str, required=True, help="HuggingFace model name")
    parser.add_argument("--responses_dir", type=str, required=True, help="Directory with response JSONL files")
    parser.add_argument("--output_dir", type=str, required=True, help="Output directory for .pt files")
    parser.add_argument("--layers", type=_layers_arg, default="all",
                        help="Layers to extract: all, or a comma-separated list of layer indices, "
                             "strictly increasing and within the model's range")
    parser.add_argument("--batch_size", type=int, default=16, help="Batch size")
    parser.add_argument("--max_length", type=int, default=2048, help="Maximum sequence length")
    parser.add_argument("--tensor_parallel_size", type=int, default=None, help="GPUs per model (auto-detect if None)")
    parser.add_argument("--roles", nargs="+", help="Specific roles to process")
    parser.add_argument("--name_prefix", type=str, default=None,
                        help="Only process response files whose stem starts with "
                             "this prefix (e.g. 'r_' or 't_').  Used by "
                             "run_pipeline.sh's r_combinations / t_combinations "
                             "subset types so disk-limited runs can extract one "
                             "half of the combination grid at a time.")
    parser.add_argument("--thinking", nargs="?", action=_RemovedFlag, help=argparse.SUPPRESS)
    parser.add_argument("--no-headers", action="store_true", default=False,
                       help="Disable header token extraction (legacy compat)")
    parser.add_argument("--ignore_generation_config", action="store_true",
                        help="Extract although the responses directory has no "
                             "generation_config.json (a tree made before 2026-10-12, such as the "
                             "May 8slot tree) or one whose model type, template kwargs, header "
                             "ids or sample prompt differ from this model's; the differences are "
                             "logged.  Off by default: the run refuses (exit 1).")
    parser.add_argument("--verify_spans", type=int, default=0, metavar="N",
                        help="Before extracting each worker's first entity, decode the assistant "
                             "span of its first N conversations and compare it with the stored "
                             "content; exit 1 on any mismatch (default 0, off; the smoke runs "
                             "pass 20)")
    return parser


def pending_response_files(responses_dir: Path, output_dir: Path, *,
                           roles: Optional[List[str]] = None,
                           name_prefix: Optional[str] = None) -> List[Path]:
    """The response files (narrowed by ``--roles`` / ``--name_prefix``) whose
    ``<name>.pt`` does not exist yet.  Standard library only, so that a rerun
    with nothing to do can return before torch is imported (below)."""
    files = sorted(Path(responses_dir).glob("*.jsonl"))
    if roles:
        files = [f for f in files if f.stem in roles]
    if name_prefix:
        files = [f for f in files if f.stem.startswith(name_prefix)]
    pending = [f for f in files if not (Path(output_dir) / f"{f.stem}.pt").exists()]
    if len(files) > len(pending):
        logger.info(f"Skipping {len(files) - len(pending)} of {len(files)} response file(s) "
                    f"whose activations already exist")
    return pending


# A rerun with nothing to extract returns here, before the torch and
# transformers imports below (seconds locally, minutes on the pod's network
# volume; walk-through P8.3, 2026-10-12).  Only when run as a script: the
# tests import the module for its functions.
if __name__ == "__main__":
    _early = build_parser().parse_args()
    if not pending_response_files(Path(_early.responses_dir), Path(_early.output_dir),
                                  roles=_early.roles, name_prefix=_early.name_prefix):
        logger.info("Nothing to process — all activations already exist")
        sys.exit(0)

import torch  # noqa: E402
import torch.multiprocessing as mp  # noqa: E402
from tqdm import tqdm  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent.parent))

from assistant_axis.internals import ProbingModel, ConversationEncoder, ActivationExtractor, SpanMapper  # noqa: E402
from assistant_axis.internals.chat_layout import (  # noqa: E402
    PROBE_CONTENT,
    ChatLayout,
    LayoutError,
    chat_ids,
    derive_chat_layout,
)
from assistant_axis.model_families import (  # noqa: E402
    FamilyNotBuiltError,
    FamilySpec,
    UnknownFamilyError,
    family_for_model_type,
    require_built,
)


def _hf_home_path() -> Path:
    """Resolve the HF cache root the same way huggingface_hub does."""
    hf = os.environ.get("HF_HOME")
    if hf:
        return Path(hf).expanduser()
    return Path("~/.cache/huggingface").expanduser()


def _is_path_on_tmpfs(
    path: Path,
    mounts_file: Path = Path("/proc/mounts"),
) -> Optional[bool]:
    """True if `path` (or its deepest existing ancestor) is on a tmpfs mount.

    Returns None if we can't determine the answer (e.g. /proc/mounts
    unavailable on macOS).  Best-effort -- a None result should be treated
    as "don't know, don't spam warnings".

    `mounts_file` is parameterised purely so the unit tests can supply a
    synthetic /proc/mounts; production callers should leave the default.
    """
    try:
        p = path.expanduser().resolve()
        while p != p.parent and not p.exists():
            p = p.parent
        if not p.exists():
            return None

        if not mounts_file.exists():
            return None

        mounts: List[tuple[str, str]] = []
        with open(mounts_file) as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 3:
                    mounts.append((parts[1], parts[2]))

        path_str = str(p)
        best: Optional[tuple[str, str]] = None
        for mnt, fst in mounts:
            if path_str == mnt or path_str.startswith(mnt.rstrip("/") + "/") or mnt == "/":
                if best is None or len(mnt) > len(best[0]):
                    best = (mnt, fst)

        return best is not None and best[1] == "tmpfs"
    except Exception:
        return None


def _warn_if_hf_cache_not_tmpfs(model_name: str) -> None:
    """Print a loud warning if HF_HOME isn't on RAM-backed tmpfs.

    Loading large models (Qwen3-32B, Llama-70B, etc.) from non-tmpfs HF
    caches -- especially NFS-backed ones -- causes silent multi-hour hangs
    on cold mmap reads of the safetensors shards.  `pipeline/run_pipeline.sh`
    handles this by mirroring the model into /dev/shm/hf-cache and
    exporting HF_HOME to point at it.  Direct invocations of this script
    bypass that setup and silently fall back to the canonical (often slow)
    HF cache.

    This check fires once at startup and is purely advisory -- some
    machines have local NVMe fast enough that non-tmpfs is fine.
    """
    hf_home = _hf_home_path()
    on_tmpfs = _is_path_on_tmpfs(hf_home)

    if on_tmpfs is True:
        logger.info(f"HF cache is RAM-backed: HF_HOME={hf_home}")
        return
    if on_tmpfs is None:
        return

    logger.warning("=" * 70)
    logger.warning("  WARNING: HF cache is NOT on RAM-backed tmpfs")
    logger.warning(f"  HF_HOME={hf_home}")
    logger.warning(f"  Loading model {model_name} may hang for HOURS on cold")
    logger.warning("  mmap reads if the underlying storage is NFS or other slow")
    logger.warning("  filesystems.  Symptoms: long silence after the tqdm")
    logger.warning("  'Loading checkpoint shards' bar reaches 100%.")
    logger.warning("")
    logger.warning("  Fix: launch via pipeline/run_pipeline.sh, which copies the")
    logger.warning("  model into /dev/shm/hf-cache and sets HF_HOME automatically.")
    logger.warning("  Or pre-populate /dev/shm/hf-cache/hub/ yourself and export")
    logger.warning("  HF_HOME=/dev/shm/hf-cache before invoking this script.")
    logger.warning("=" * 70)


class NoActivationsError(RuntimeError):
    """A response file had conversations but none yielded an activation.

    That means no assistant span was found in any of them: a tokenizer or
    chat-template change (transformers 5's ``apply_chat_template`` return
    type did exactly this), not the data.  Before 2026-10-12 the entity was
    skipped without a word and counted as a success.
    """


def load_responses(responses_file: Path) -> List[dict]:
    """Load responses from JSONL file, with NFS-flake retries.

    Goes through ``assistant_axis.atomic_io.read_jsonl_with_retry`` so
    this share the project-standard exponential backoff
    ``[5, 20, 60, 180]`` s and the broader transient-error set
    (``OSError``/``RuntimeError``/``EOFError``).  Response files are
    small (a few MB at most) so reading the full text and parsing
    line-by-line is equivalent to the previous streaming approach with
    no meaningful memory cost.
    """
    from assistant_axis.atomic_io import read_jsonl_with_retry
    return read_jsonl_with_retry(responses_file, logger_obj=logger)


class ContractError(RuntimeError):
    """A response file breaks the pipeline's single-turn contract: a
    conversation with more than one assistant turn.  Step 1 writes exactly
    one per record; until 2026-10-13 step 2 picked assistant turns by parity
    (turns 1, 3, ...) and averaged them (review P2 D4)."""


class SpanVerificationError(RuntimeError):
    """``--verify_spans`` found an assistant span that does not decode to the
    stored content."""


@dataclass
class Preflight:
    """What step 2 knows before loading any model: the family row, the layer
    count from ``config.json``, the tokenizer and the header layout derived
    from its chat template (None when it could not be derived under
    ``--no-headers``)."""

    family: FamilySpec
    n_layers: Optional[int]
    tokenizer: object
    layout: Optional[ChatLayout]


def preflight_model(model_name: str, *, extract_headers: bool = True) -> Preflight:
    """Read the model's ``config.json`` and tokenizer (a few MB, no weights):
    refuse a ``model_type`` with no row or a row not built
    (``UnknownFamilyError`` / ``FamilyNotBuiltError``; § 15 Q8, Q3), and derive
    the header layout (``LayoutError`` when the template gives none).  Run
    once in the parent before any worker loads the model."""
    from transformers import AutoConfig, AutoTokenizer
    cfg = AutoConfig.from_pretrained(model_name)
    family = require_built(family_for_model_type(cfg.model_type))
    n_layers = getattr(cfg, "num_hidden_layers", None)
    if n_layers is None:          # a multimodal config keeps it in text_config
        n_layers = getattr(getattr(cfg, "text_config", None), "num_hidden_layers", None)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    try:
        layout = derive_chat_layout(tokenizer, family)
    except LayoutError as e:
        if extract_headers:
            raise
        logger.warning(f"--no-headers: no header layout derived ({e}); body means only")
        layout = None
    return Preflight(family=family, n_layers=n_layers, tokenizer=tokenizer, layout=layout)


class GenerationConfigError(RuntimeError):
    """The responses directory has no ``generation_config.json``, or its last
    run does not match this model (multi-model plan § 5.5)."""


def check_generation_config(responses_dir: Path, pre: Preflight, *, ignore: bool = False,
                            log=None) -> List[str]:
    """Compare step 1's side-car with what step 2 is about to do, before any
    model is loaded (multi-model plan § 5.5): the last recorded run's
    ``model_type``, ``template_kwargs`` and ``header_ids`` must equal this
    model's row and derived layout, and its ``sample_prompt_ids`` (the ids
    step 1 handed vLLM for ``sample_conversation``) must be the prefix of
    step 2's rendering of that conversation with an assistant turn: the
    end-to-end check that the two steps see the same tokens.

    Returns the differences.  Raises :class:`GenerationConfigError` on any
    difference, or when there is no side-car (the May 8slot tree has none:
    Roger, § 15 Q10), unless ``ignore`` (``--ignore_generation_config``),
    which logs them instead."""
    from assistant_axis.generation import GENERATION_CONFIG_NAME, read_generation_config
    log = log or logger
    path = Path(responses_dir) / GENERATION_CONFIG_NAME
    cfg = read_generation_config(Path(responses_dir))
    if not cfg or not cfg.get("runs"):
        msg = (f"{responses_dir} has no {GENERATION_CONFIG_NAME} (or no run in it): its "
               f"responses were made before 2026-10-12 (the May 8slot tree) or by hand, under "
               f"settings nothing records; pass --ignore_generation_config to extract them anyway")
        if not ignore:
            raise GenerationConfigError(msg)
        log.warning(msg + " (--ignore_generation_config given)")
        return [msg]

    last = cfg["runs"][-1]
    family = pre.family
    tok = pre.tokenizer
    diffs: List[str] = []
    if last.get("model_type") != family.model_type:
        diffs.append(f"model_type: step 1 {last.get('model_type')!r}, step 2 {family.model_type!r}")
    if last.get("template_kwargs") != dict(family.template_kwargs):
        diffs.append(f"template_kwargs: step 1 {last.get('template_kwargs')!r}, step 2 "
                     f"{dict(family.template_kwargs)!r}")
    if pre.layout is not None and last.get("header_ids") != list(pre.layout.header_ids):
        diffs.append(f"header_ids: step 1 {last.get('header_ids')!r}, step 2 "
                     f"{list(pre.layout.header_ids)!r}")
    sample, sent = last.get("sample_conversation"), last.get("sample_prompt_ids")
    if not sample or sent is None:
        diffs.append("sample_conversation / sample_prompt_ids: not recorded (a side-car "
                     "written before 2026-10-13)")
    else:
        rendered = chat_ids(tok, list(sample) + [{"role": "assistant", "content": PROBE_CONTENT}],
                            add_generation_prompt=False,
                            template_kwargs=dict(family.template_kwargs))
        if rendered[:len(sent)] != [int(i) for i in sent]:
            diffs.append(f"sample_prompt_ids: what step 1 sent, {tok.decode(list(sent))!r}, is not "
                         f"the start of step 2's rendering of the same conversation, "
                         f"{tok.decode(rendered)!r}")
    if diffs:
        msg = (f"{path} (last run {last.get('created_at')}) does not match this model: "
               f"{'; '.join(diffs)}.  Step 2 would compute on a context step 1 did not use; pass "
               f"--ignore_generation_config to extract anyway (a deliberate re-extraction)")
        if not ignore:
            raise GenerationConfigError(msg)
        log.warning(msg + " (--ignore_generation_config given)")
    else:
        log.info(f"{path}: model type, template kwargs, header ids and the sample prompt match")
    return diffs


def log_layout(layout: Optional[ChatLayout], log=None) -> None:
    log = log or logger
    if layout is None:
        return
    log.info(f"Header layout ({layout.model_type}, template kwargs {layout.template_kwargs}): "
             f"{len(layout.header_tokens)} tokens {list(layout.header_tokens)!r}, ids "
             f"{list(layout.header_ids)}; generation prompt ids "
             f"{list(layout.generation_prompt_ids)}")


def verify_assistant_spans(pm: ProbingModel, conversations: List[List[Dict[str, str]]],
                           n: int, *, entity: str, log=None) -> List[Dict]:
    """``--verify_spans``: for the first ``n`` conversations, decode the
    assistant span that slot 0 averages and compare it with the stored
    content, both stripped of leading and trailing whitespace (the span
    builders leave boundary whitespace out: the strip rule).  Each mismatch
    is logged with both strings and returned."""
    log = log or logger
    family = pm.family
    encoder = ConversationEncoder(pm.tokenizer, pm.model_name, span_builder=family.span_builder)
    kwargs = dict(family.template_kwargs)
    mismatches = []
    for i, conv in enumerate(conversations[:n]):
        full_ids, spans = encoder.build_turn_spans(conv, **kwargs)
        got = [pm.tokenizer.decode(full_ids[s["start"]:s["end"]],
                                   clean_up_tokenization_spaces=False).strip()
               for s in spans if s["role"] == "assistant"]
        want = [m.get("content", "").strip() for m in conv
                if m["role"] == "assistant" and m.get("content", "").strip()]
        if got != want:
            mismatches.append({"conversation": i, "decoded": got, "stored": want})
            log.error(f"{entity}: conversation {i}: the assistant span decodes to {got!r}; "
                      f"the stored content is {want!r}")
    checked = min(n, len(conversations))
    log.info(f"{entity}: --verify_spans: {checked - len(mismatches)} of {checked} assistant "
             f"spans decode to the stored content")
    return mismatches


def extract_activations_batch(
    pm: ProbingModel,
    conversations: List[List[Dict[str, str]]],
    layers: List[int],
    batch_size: int = 16,
    max_length: int = 2048,
    *,
    layout: Optional[ChatLayout] = None,
    extract_headers: bool = True,
    entity: str = "?",
) -> tuple[List[Optional[torch.Tensor]], List[Dict], Dict]:
    """Extract mean response activations for a batch of conversations.

    The family (``pm.family``, from the loaded model's ``config.model_type``;
    an unknown type raises ``UnknownFamilyError``) gives the template kwargs
    and the span builder; ``layout`` (derived from the template when None)
    gives the header slots.  Each conversation must have at most one
    assistant turn (:class:`ContractError` otherwise): its activation is that
    turn's, ``(1 + N, n_layers, hidden)`` with headers, ``(n_layers,
    hidden)`` without; none when the response is empty or cut away.

    Returns:
        (activations_list, all_mismatches, header_metadata) -- one activation
        tensor per conversation (or None), accumulated header-token mismatch
        records, and the layout's metadata (``header_tokens``, ``header_ids``,
        ``model_name``, ``extract_headers``, ``model_type``,
        ``template_kwargs``, ``generation_prompt_ids``; only ``model_type``
        and ``template_kwargs`` when headers are not extracted).
    """
    family = pm.family
    chat_kwargs = dict(family.template_kwargs)
    encoder = ConversationEncoder(pm.tokenizer, pm.model_name, span_builder=family.span_builder)
    extractor = ActivationExtractor(pm, encoder)

    header_metadata: Dict = {}
    if extract_headers:
        if layout is None:
            layout = derive_chat_layout(pm.tokenizer, family)
        header_metadata = {
            "header_tokens": list(layout.header_tokens),
            "header_ids": list(layout.header_ids),
            "model_name": pm.model_name,
            "extract_headers": True,
        }
    else:
        layout = None
    header_metadata.update({"model_type": family.model_type,
                            "template_kwargs": dict(family.template_kwargs)})
    if layout is not None:
        header_metadata["generation_prompt_ids"] = list(layout.generation_prompt_ids)
    span_mapper = SpanMapper(
        pm.tokenizer,
        header_ids=layout.header_ids if layout is not None else None,
        search_distance=layout.search_distance if layout is not None else None)

    print(f"DEBUG: chat_kwargs = {chat_kwargs}")

    all_activations: List[Optional[torch.Tensor]] = []
    all_mismatches: List[Dict] = []
    num_conversations = len(conversations)

    for batch_start in range(0, num_conversations, batch_size):
        batch_end = min(batch_start + batch_size, num_conversations)
        batch_conversations = conversations[batch_start:batch_end]

        # Use ActivationExtractor.batch_conversations to get activations
        batch_activations, batch_metadata = extractor.batch_conversations(
            batch_conversations,
            layer=layers,
            max_length=max_length,
            **chat_kwargs,
        )

        # batch_activations shape: (num_layers, batch_size, max_seq_len, hidden_size)

        # Build spans for this batch
        batch_full_ids, batch_spans, span_metadata = encoder.build_batch_turn_spans(batch_conversations, **chat_kwargs)

        # Debug: print first 2 assistant spans
        if batch_start == 0:
            for span in batch_spans[:4]:
                if span['role'] == 'assistant':
                    print(f"  DEBUG span: conv={span['conversation_id']} start={span['start']} end={span['end']} n_tokens={span['n_tokens']}")

            if layout is not None:
                print(f"  Expected assistant header ids: {list(layout.header_ids)}")
                shown = 0
                for span in batch_spans:
                    if span['role'] != 'assistant' or shown >= 2:
                        continue
                    cid = span['conversation_id']
                    fids = batch_full_ids[cid]
                    s = span['start']
                    window = fids[max(0, s - layout.search_distance):s + 1]
                    print(f"  Actual tokens before span[{cid}] start={s}: {window}")
                    shown += 1

        conv_activations_list, mismatches, turn_roles = span_mapper.map_spans(
            batch_activations, batch_spans, batch_metadata,
            batch_full_ids=batch_full_ids,
            extract_headers=extract_headers,
        )
        all_mismatches.extend(mismatches)

        # The assistant turn by its role (multi-model plan § 5.4), not by
        # parity: exactly one is allowed.  For a [system?, user, assistant]
        # conversation it is turn 1, which is what the parity rule (1::2)
        # picked; indexing it gives the same bf16 values as the nanmean over
        # a size-1 axis that the parity rule took (the golden gate checks).
        for local, (conv_acts, roles) in enumerate(zip(conv_activations_list, turn_roles)):
            assistant_turns = [t for t, r in enumerate(roles) if r == "assistant"]
            if len(assistant_turns) > 1:
                raise ContractError(
                    f"{entity}: conversation {batch_start + local} has {len(assistant_turns)} "
                    f"assistant turns; the pipeline is single-turn")
            if not assistant_turns or conv_acts.numel() == 0:
                all_activations.append(None)
                continue
            t = assistant_turns[0]
            # A copy, not a view: a view would keep (and torch.save would
            # write) the whole stacked turns tensor.
            act = conv_acts[:, t] if conv_acts.ndim == 4 else conv_acts[t]
            all_activations.append(act.to("cpu", copy=True))   # (1+N, layers, hidden) or (layers, hidden)

        # Cleanup
        del batch_activations
        if (batch_start // batch_size) % 5 == 0:
            torch.cuda.empty_cache()

    return all_activations, all_mismatches, header_metadata


def process_role(
    pm: ProbingModel,
    role_file: Path,
    output_dir: Path,
    layers: List[int],
    batch_size: int,
    max_length: int,
    *,
    layout: Optional[ChatLayout] = None,
    extract_headers: bool = True,
    verify_spans: int = 0,
) -> tuple[bool, int]:
    """Process a single role file and save activations.

    ``layout`` is the worker's header layout (derived from the template when
    None); ``verify_spans`` > 0 runs :func:`verify_assistant_spans` on the
    first that many conversations before extracting anything.

    Returns:
        (saved, mismatch_count) for the caller to accumulate; ``saved`` is
        False only for a response file with no responses (logged as a
        warning).

    Raises:
        NoActivationsError: the file had conversations but not one of them
            yielded an activation, so nothing was saved.
        ContractError: a conversation has more than one assistant turn.
        SpanVerificationError: ``--verify_spans`` found a mismatch.
    """
    role = role_file.stem
    output_file = output_dir / f"{role}.pt"

    # Load responses
    responses = load_responses(role_file)
    if not responses:
        logger.warning(f"{role}: no responses in {role_file}; nothing to extract")
        return False, 0

    # Extract conversations and metadata
    conversations = []
    metadata = []
    for resp in responses:
        conversations.append(resp["conversation"])
        metadata.append({
            "prompt_index": resp["prompt_index"],
            "question_index": resp["question_index"],
            "label": resp["label"],
        })

    logger.info(f"Processing {role}: {len(conversations)} conversations")

    if verify_spans > 0:
        bad = verify_assistant_spans(pm, conversations, verify_spans, entity=role)
        if bad:
            raise SpanVerificationError(
                f"{role}: {len(bad)} of {min(verify_spans, len(conversations))} assistant spans "
                f"do not decode to the stored content (logged above); nothing extracted")

    activations_list, mismatches, header_metadata = extract_activations_batch(
        pm=pm,
        conversations=conversations,
        layers=layers,
        batch_size=batch_size,
        max_length=max_length,
        layout=layout,
        extract_headers=extract_headers,
        entity=role,
    )

    if mismatches:
        logger.warning(
            f"  {role}: {len(mismatches)} header-token mismatches"
        )
        for m in mismatches[:5]:
            logger.warning(
                f"    conv={m['conversation_id']} turn={m['turn']} "
                f"pos={m['position']} "
                f"expected={m['expected']} actual={m['actual']}"
            )
        if len(mismatches) > 5:
            logger.warning(f"    ... and {len(mismatches) - 5} more")

    activations_dict = {}
    for i, (act, meta) in enumerate(zip(activations_list, metadata)):
        if act is not None:
            key = f"{meta['label']}_p{meta['prompt_index']}_q{meta['question_index']}"
            activations_dict[key] = act

    if not activations_dict:
        raise NoActivationsError(
            f"{role}: none of {len(conversations)} conversations yielded an "
            f"activation (no assistant span found); nothing saved"
        )
    n_dropped = len(conversations) - len(activations_dict)
    if n_dropped:
        logger.warning(
            f"{role}: {n_dropped} of {len(conversations)} conversations have no "
            f"activation (empty or truncated-away response, or a repeated key)"
        )

    # Save via local disk staging + retry/backoff copy to the final
    # (possibly NFS) destination, plus a post-copy size-sanity check
    # to catch silent NFS truncation (the failure mode that produced
    # the 5 MB ``r_guardian__casual.pt`` and surfaced downstream in
    # step 4 as ``"storage has wrong byte size of dtype"``).  The
    # ``_use_new_zipfile_serialization=False`` form is the older
    # pickle format and dodges the "iostream error" that torch's
    # default zip writer hits on RunPod for files this large.
    #
    # ``torch_save_with_retry`` honours ``TMPDIR`` for the staging
    # location.  Caveats:
    #   - On some RunPod setups TMPDIR points to NFS (the original
    #     reason this site used to hardcode /tmp).  Don't blindly
    #     export TMPDIR without checking where it points.
    #   - On other setups /tmp lives on a small container disk (often
    #     ~10-50 GB) which can fill up: each .pt activations file is
    #     roughly 2.6 GB (n_convs × n_slots × n_layers × hidden × bf16),
    #     and 4 concurrent workers can blow out small /tmp instantly.
    #   - If /tmp is too small, point TMPDIR at a tmpfs:
    #         export TMPDIR=/dev/shm
    #     /dev/shm is RAM-backed (default size = 50% of RAM = plenty
    #     on boxes with 256 GB+ RAM), local, and fast.  No automatic
    #     cleanup, but the helper removes the staging file after a
    #     successful copy.
    if activations_dict:
        from assistant_axis.atomic_io import torch_save_with_retry
        # What was extracted, recorded since 2026-10-12 (step 4 copies it into
        # the vector).  "layers" names the model layer at each index of the
        # layer axis, which is positional in --layers: a subset gives an axis
        # shorter than the model's; step 5 does not yet check the lists agree.  Files
        # written before lack these keys; every one of them used all layers.
        # Since 2026-10-13 (multi-model plan § 7) also model_type,
        # template_kwargs and, with headers, generation_prompt_ids; the
        # "thinking" key written on 2026-10-12 went (it was False in every
        # file; template_kwargs carries enable_thinking now).
        file_metadata = dict(header_metadata)
        file_metadata.setdefault("extract_headers", False)
        file_metadata.update({
            "layers": [int(x) for x in layers],
            "max_length": int(max_length),
            "batch_size": int(batch_size),
        })
        activations_dict["metadata"] = file_metadata
        torch_save_with_retry(
            activations_dict, output_file,
            use_zipfile_serialization=False,
            logger_obj=logger,
        )
        n_act = len(activations_dict) - (1 if "metadata" in activations_dict else 0)
        logger.info(f"Saved {n_act} activations (+ metadata) for {role} "
                    f"({output_file.stat().st_size:,} bytes)")

    # Cleanup
    gc.collect()
    torch.cuda.empty_cache()

    return True, len(mismatches)


def load_worker_model(args, log=None):
    """Load the model and set up what every entity of this process uses:
    ``(pm, layers, layout)``.  The family is the loaded model's
    (``config.model_type``; refused if unknown or not built), ``--layers`` is
    checked against its layer count, and the header layout is derived once
    from its tokenizer (and must equal the preflight's ids, which main put on
    ``args.expected_header_ids``)."""
    log = log or logger
    log.info(f"Loading model: {args.model}")
    pm = ProbingModel(args.model, hf_load_kwargs=getattr(args, "hf_load_kwargs", None))
    family = require_built(pm.family)
    n_layers = len(pm.get_layers())
    layers = parse_layers(args.layers, n_layers)
    log.info(f"Model has {n_layers} layers; extracting {len(layers)}")
    layout = None
    if not args.no_headers:
        layout = derive_chat_layout(pm.tokenizer, family)
        expected = getattr(args, "expected_header_ids", None)
        if expected is not None and list(layout.header_ids) != list(expected):
            raise LayoutError(
                f"the loaded model's tokenizer derives the header ids {list(layout.header_ids)}; "
                f"the preflight derived {list(expected)}")
        log_layout(layout, log)
    return pm, layers, layout


def process_roles_on_worker(worker_id: int, gpu_ids: List[int], role_files: List[Path], args):
    """Process a subset of roles on a worker.

    Exits with status 1 if the worker could not start (the model failed to
    load) or any role raised, so that ``run_multi_worker`` reports the step as
    incomplete.  Before 2026-10-12 both were logged and the worker exited 0:
    the most likely way to lose a worker, a CUDA out-of-memory error while
    loading the model beside an orphaned process, is an ordinary exception,
    so the dead-worker check in ``run_multi_worker`` never saw it.  Both
    happened in the 8slot extraction and were caught by hand before step 4:
    on 2026-04-26 176 of 280 roles failed on a full ``/tmp`` staging disk
    and step 2 reported "Multi-worker processing completed!"; on 2026-04-27
    workers 1 and 2 hit CUDA out of memory at load ("Fatal error on Worker").
    Roles after a failed one are still processed, and everything saved stays
    saved; a rerun extracts only what is missing.
    """
    # Set CUDA_VISIBLE_DEVICES for this worker's GPU subset
    gpu_ids_str = ','.join(map(str, gpu_ids))
    os.environ['CUDA_VISIBLE_DEVICES'] = gpu_ids_str

    # Set up logging for this process
    worker_logger = logging.getLogger(f"Worker-{worker_id}")
    handler = logging.StreamHandler()
    formatter = logging.Formatter(f'%(asctime)s - Worker-{worker_id}[GPUs:{gpu_ids_str}] - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    worker_logger.addHandler(handler)
    worker_logger.setLevel(logging.INFO)

    worker_logger.info(f"Starting Worker {worker_id} with GPUs {gpu_ids} and {len(role_files)} roles")

    output_dir = Path(args.output_dir)
    exit_code = 0

    try:
        # Load the model; the layout is derived once per worker
        pm, layers, layout = load_worker_model(args, worker_logger)

        # Process assigned roles
        extract_headers = not args.no_headers
        completed_count = 0
        empty_count = 0
        failed_count = 0
        total_mismatches = 0

        for i, role_file in enumerate(tqdm(role_files, desc=f"Worker-{worker_id}",
                                           position=worker_id)):
            try:
                saved, n_mm = process_role(
                    pm, role_file, output_dir, layers,
                    args.batch_size, args.max_length,
                    layout=layout, extract_headers=extract_headers,
                    verify_spans=getattr(args, "verify_spans", 0) if i == 0 else 0,
                )
                total_mismatches += n_mm
                if saved:
                    completed_count += 1
                else:
                    empty_count += 1
            except SpanVerificationError:
                raise                     # the spans are wrong for every entity: stop
            except Exception as e:
                failed_count += 1
                worker_logger.error(f"Exception processing {role_file.stem}: {e}",
                                    exc_info=True)

        worker_logger.info(
            f"Worker {worker_id} completed: {completed_count} successful, "
            f"{empty_count} with no responses, {failed_count} failed, "
            f"{total_mismatches} total header mismatches"
        )
        if failed_count:
            exit_code = 1

    except Exception as e:
        worker_logger.error(f"Fatal error on Worker {worker_id}: {e}", exc_info=True)
        exit_code = 1

    finally:
        worker_logger.info(f"Worker {worker_id} cleanup completed")

    if exit_code:
        sys.exit(exit_code)


def run_multi_worker(args) -> int:
    """Run multi-worker processing."""
    # Get available GPUs
    if 'CUDA_VISIBLE_DEVICES' in os.environ:
        gpu_ids = [int(x.strip()) for x in os.environ['CUDA_VISIBLE_DEVICES'].split(',') if x.strip()]
    else:
        gpu_ids = list(range(torch.cuda.device_count()))

    total_gpus = len(gpu_ids)

    if total_gpus == 0:
        logger.error("No GPUs available.")
        return 1

    tensor_parallel_size = args.tensor_parallel_size

    if tensor_parallel_size > total_gpus:
        logger.error(f"tensor_parallel_size ({tensor_parallel_size}) > available GPUs ({total_gpus})")
        return 1

    num_workers = total_gpus // tensor_parallel_size

    if total_gpus % tensor_parallel_size != 0:
        logger.warning(f"GPUs ({total_gpus}) not evenly divisible by tensor_parallel_size ({tensor_parallel_size}). "
                      f"Using {num_workers} workers.")

    logger.info(f"Available GPUs: {gpu_ids}")
    logger.info(f"Tensor parallel size: {tensor_parallel_size}")
    logger.info(f"Number of workers: {num_workers}")

    # Get role files
    responses_dir = Path(args.responses_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    role_files = pending_response_files(responses_dir, output_dir,
                                        roles=args.roles, name_prefix=args.name_prefix)

    if not role_files:
        logger.info("No roles to process")
        return 0

    logger.info(f"Processing {len(role_files)} roles across {num_workers} workers")

    # Partition GPUs
    gpu_chunks = []
    for i in range(num_workers):
        start = i * tensor_parallel_size
        end = start + tensor_parallel_size
        gpu_chunks.append(gpu_ids[start:end])

    # Distribute roles
    role_chunks = [[] for _ in range(num_workers)]
    for i, role_file in enumerate(role_files):
        role_chunks[i % num_workers].append(role_file)

    for i in range(num_workers):
        logger.info(f"Worker {i} (GPUs {gpu_chunks[i]}): {len(role_chunks[i])} roles")

    # Set multiprocessing start method
    mp.set_start_method('spawn', force=True)

    # Launch workers
    processes = []
    for worker_id in range(num_workers):
        if role_chunks[worker_id]:
            p = mp.Process(
                target=process_roles_on_worker,
                args=(worker_id, gpu_chunks[worker_id], role_chunks[worker_id], args)
            )
            p.start()
            processes.append(p)

    # Wait for completion
    logger.info(f"Launched {len(processes)} worker processes")
    for p in processes:
        p.join()

    # A worker that died (OOM kill, CUDA abort, segfault) left its roles
    # unextracted.  Before 2026-10-12 this still returned 0, so the pipeline
    # went on to step 4 with a partial activations directory (the failure the
    # GPU pre-flight in run_pipeline.sh exists to prevent).  Since the review
    # of the same day a worker also exits 1 when its model failed to load or
    # any of its roles raised (process_roles_on_worker), having processed the
    # rest; a rerun extracts whatever is missing.
    dead = [(i, p.exitcode) for i, p in enumerate(processes) if p.exitcode != 0]
    if dead:
        logger.error(f"{len(dead)} of {len(processes)} worker(s) exited abnormally "
                     f"(launch index, exit code): {dead}; their roles are incomplete -- "
                     f"see the worker's log above, then rerun this step to extract the rest")
        return 1

    logger.info("Multi-worker processing completed!")
    return 0


def main():
    parser = build_parser()
    args = parser.parse_args()

    # Set up file logging (append to output_dir/activations.log)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(output_dir / "activations.log", mode="a")
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(file_handler)

    # Catch direct invocations that bypass run_pipeline.sh's tmpfs setup --
    # loading large models from NFS-backed HF caches silently hangs for
    # hours on cold mmap reads.  Advisory only; doesn't block the run.
    _warn_if_hf_cache_not_tmpfs(args.model)

    # Determine which roles need processing -- BEFORE reading the model's
    # config or loading it.  This lets the script run cleanly on a CPU-only
    # box when all activations are already cached (e.g. re-running just to
    # drive the downstream pipeline steps).
    responses_dir = Path(args.responses_dir)
    role_files = pending_response_files(responses_dir, output_dir,
                                        roles=args.roles, name_prefix=args.name_prefix)
    if not role_files:
        logger.info("Nothing to process — all activations already exist")
        return

    # Before any model is loaded (multi-model plan § 5.4): the family from
    # config.json (an unknown model_type or a row not built refuses), the
    # header layout from the tokenizer's chat template, --layers against the
    # layer count.  Each worker derives the layout again from its own load
    # and must find the same ids.
    try:
        pre = preflight_model(args.model, extract_headers=not args.no_headers)
    except (UnknownFamilyError, FamilyNotBuiltError, LayoutError) as e:
        logger.error(f"{args.model}: {e}")
        sys.exit(1)
    try:
        parse_layers(args.layers, pre.n_layers)
    except LayersError as e:
        parser.error(str(e))
    log_layout(pre.layout)
    # Step 1's side-car against this model (§ 5.5), still before any load.
    try:
        check_generation_config(responses_dir, pre, ignore=args.ignore_generation_config)
    except GenerationConfigError as e:
        logger.error(str(e))
        sys.exit(1)
    args.hf_load_kwargs = dict(pre.family.hf_load_kwargs)
    args.expected_header_ids = (list(pre.layout.header_ids)
                                if pre.layout is not None and not args.no_headers else None)

    # Detect GPUs for multi-worker decision
    if 'CUDA_VISIBLE_DEVICES' in os.environ:
        available_gpus = [int(x.strip()) for x in os.environ['CUDA_VISIBLE_DEVICES'].split(',') if x.strip()]
        total_gpus = len(available_gpus)
    else:
        total_gpus = torch.cuda.device_count()

    # Determine tensor parallel size
    tensor_parallel_size = args.tensor_parallel_size if args.tensor_parallel_size else total_gpus

    # Use multi-worker mode if we have more GPUs than tensor_parallel_size
    use_multi_worker = (
        total_gpus > 1 and
        tensor_parallel_size > 0 and
        total_gpus > tensor_parallel_size
    )

    if use_multi_worker:
        logger.info(f"Multi-worker mode: {total_gpus} GPUs with tensor_parallel_size={tensor_parallel_size}")
        logger.info(f"Number of workers: {total_gpus // tensor_parallel_size}")
        args.tensor_parallel_size = tensor_parallel_size
        exit_code = run_multi_worker(args)
        if exit_code != 0:
            sys.exit(exit_code)
    else:
        # Single-worker mode
        logger.info(f"Single-worker mode: Using {tensor_parallel_size} GPU(s)")

        pm, layers, layout = load_worker_model(args)

        extract_headers = not args.no_headers
        total_mismatches = 0
        no_activations: List[str] = []

        for i, role_file in enumerate(tqdm(role_files, desc="Processing roles")):
            try:
                _, n_mm = process_role(
                    pm, role_file, output_dir, layers,
                    args.batch_size, args.max_length,
                    layout=layout, extract_headers=extract_headers,
                    verify_spans=args.verify_spans if i == 0 else 0,
                )
            except NoActivationsError as e:
                # Logged and carried on, like the multi-worker mode; any
                # other exception still stops the run here, as before.
                logger.error(str(e))
                no_activations.append(role_file.stem)
                continue
            except SpanVerificationError as e:
                logger.error(str(e))
                sys.exit(1)
            total_mismatches += n_mm

        if total_mismatches:
            logger.warning(f"Total header-token mismatches across all roles: {total_mismatches}")
        if no_activations:
            logger.error(f"{len(no_activations)} role(s) yielded no activations and were "
                         f"not saved: {no_activations[:10]}"
                         f"{' ...' if len(no_activations) > 10 else ''}")
            sys.exit(1)

    logger.info("Done!")


if __name__ == "__main__":
    main()
