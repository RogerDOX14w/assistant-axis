#!/usr/bin/env python3
"""
Extract activations from response JSONL files.

This script loads responses from per-role JSONL files and extracts mean response
activations for each conversation, saving them as .pt files per role.

Supports automatic multi-worker parallelization when total GPUs > tensor_parallel_size.
Number of workers = total_gpus // tensor_parallel_size

Usage:
    uv run scripts/2_activations.py \
        --model google/gemma-2-27b-it \
        --responses_dir outputs/gemma-2-27b/responses \
        --output_dir outputs/gemma-2-27b/activations

    # With tensor parallelism (auto-parallelizes across workers)
    uv run scripts/2_activations.py \
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
from typing import Dict, List, Optional

import jsonlines
import torch
import torch.multiprocessing as mp
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))

from assistant_axis.internals import ProbingModel, ConversationEncoder, ActivationExtractor, SpanMapper

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_responses(responses_file: Path) -> List[dict]:
    """Load responses from JSONL file, with retries for NFS flakiness."""
    import time
    for attempt in range(5):
        try:
            responses = []
            with jsonlines.open(responses_file, 'r') as reader:
                for entry in reader:
                    responses.append(entry)
            return responses
        except OSError as e:
            if attempt < 4:
                wait = 10 * (attempt + 1)
                logger.warning(f"Read failed for {responses_file.name} (attempt {attempt+1}/5): {e}. "
                               f"Retrying in {wait}s...")
                time.sleep(wait)
            else:
                logger.error(f"Read failed for {responses_file.name} after 5 attempts: {e}")
                raise
    return []


def extract_activations_batch(
    pm: ProbingModel,
    conversations: List[List[Dict[str, str]]],
    layers: List[int],
    batch_size: int = 16,
    max_length: int = 2048,
    enable_thinking: bool = False,
    extract_headers: bool = True,
) -> tuple[List[Optional[torch.Tensor]], List[Dict], Dict]:
    """Extract mean response activations for a batch of conversations.

    Returns:
        (activations_list, all_mismatches, header_metadata) -- one activation
        tensor per conversation (or None), accumulated header-token mismatch
        records, and header metadata dict (empty when headers not extracted).
    """
    encoder = ConversationEncoder(pm.tokenizer, pm.model_name)
    extractor = ActivationExtractor(pm, encoder)
    span_mapper = SpanMapper(pm.tokenizer, model_name=pm.model_name)

    header_metadata: Dict = {}
    if extract_headers:
        try:
            hdr_ids = span_mapper.expected_assistant_header_ids()
            tokens = []
            family = span_mapper._model_family()
            if family:
                from assistant_axis.internals.spans import _HEADER_TOKENS
                tokens = _HEADER_TOKENS[family]
            header_metadata = {
                "header_tokens": tokens,
                "header_ids": hdr_ids,
                "model_name": pm.model_name,
                "extract_headers": True,
            }
        except ValueError:
            pass

    # Build chat_kwargs for Qwen models
    chat_kwargs = {}
    if 'qwen' in pm.model_name.lower():
        chat_kwargs['enable_thinking'] = enable_thinking

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

            if extract_headers:
                try:
                    hdr_ids = span_mapper.expected_assistant_header_ids()
                    print(f"  Expected assistant header ids: {hdr_ids}")
                    shown = 0
                    for span in batch_spans:
                        if span['role'] != 'assistant' or shown >= 2:
                            continue
                        cid = span['conversation_id']
                        fids = batch_full_ids[cid]
                        s = span['start']
                        family = span_mapper._model_family() or "unknown"
                        from assistant_axis.internals.spans import _MAX_HEADER_SEARCH_DIST
                        max_dist = _MAX_HEADER_SEARCH_DIST.get(family, 12)
                        window = fids[max(0, s - max_dist):s + 1]
                        print(f"  Actual tokens before span[{cid}] start={s}: {window}")
                        shown += 1
                except ValueError:
                    pass

        conv_activations_list, mismatches = span_mapper.map_spans(
            batch_activations, batch_spans, batch_metadata,
            batch_full_ids=batch_full_ids,
            extract_headers=extract_headers,
        )
        all_mismatches.extend(mismatches)

        for conv_acts in conv_activations_list:
            if conv_acts.numel() == 0:
                all_activations.append(None)
                continue

            if conv_acts.ndim == 4:
                # (1+N, turns, layers, hidden) -> mean across assistant turns per slot
                if conv_acts.shape[1] >= 2:
                    assistant_slots = conv_acts[:, 1::2, :, :]
                    if assistant_slots.shape[1] > 0:
                        mean_act = assistant_slots.nanmean(dim=1).cpu()  # (1+N, layers, hidden)
                        all_activations.append(mean_act)
                    else:
                        all_activations.append(None)
                else:
                    all_activations.append(None)
            else:
                # 3D: (turns, layers, hidden) -- no-headers path
                if conv_acts.shape[0] >= 2:
                    assistant_act = conv_acts[1::2]
                    if assistant_act.shape[0] > 0:
                        mean_act = assistant_act.mean(dim=0).cpu()  # (layers, hidden)
                        all_activations.append(mean_act)
                    else:
                        all_activations.append(None)
                else:
                    all_activations.append(None)

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
    enable_thinking: bool = False,
    extract_headers: bool = True,
) -> tuple[bool, int]:
    """Process a single role file and save activations.

    Returns:
        (success, mismatch_count) for the caller to accumulate.
    """
    role = role_file.stem
    output_file = output_dir / f"{role}.pt"

    # Load responses
    responses = load_responses(role_file)
    if not responses:
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

    activations_list, mismatches, header_metadata = extract_activations_batch(
        pm=pm,
        conversations=conversations,
        layers=layers,
        batch_size=batch_size,
        max_length=max_length,
        enable_thinking=enable_thinking,
        extract_headers=extract_headers,
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

    # Save via local disk, then copy to destination. torch.save's default
    # zip serialization triggers "iostream error" on RunPod; using the older
    # pickle format (_use_new_zipfile_serialization=False) avoids the fragile
    # zip writer entirely.
    if activations_dict:
        import shutil
        import time as _time
        if header_metadata:
            activations_dict["metadata"] = header_metadata
        # Stage the .pt to a local-disk temp file, then atomically copy to the
        # final (possibly NFS) output location.  This avoids torch.save writing
        # directly to NFS, which on RunPod is slow and flaky for large files.
        #
        # We honour TMPDIR with /tmp as the default fallback.  Caveats:
        #   - On some RunPod setups TMPDIR points to NFS (the original reason
        #     this site used to hardcode /tmp).  Don't blindly export TMPDIR
        #     without checking where it points.
        #   - On other setups /tmp lives on a small container disk (often
        #     ~10-50 GB) which can fill up: each .pt activations file is
        #     roughly 2.6 GB (n_convs × n_slots × n_layers × hidden × bf16),
        #     and 4 concurrent workers can blow out small /tmp instantly.
        #   - If /tmp is too small, point TMPDIR at a tmpfs:
        #         export TMPDIR=/dev/shm
        #     /dev/shm is RAM-backed (default size = 50% of RAM = plenty on
        #     boxes with 256 GB+ RAM), local, and fast.  No automatic cleanup,
        #     but `local_tmp.unlink()` below removes the staging file after a
        #     successful copy, so files only accumulate on crashed runs (and
        #     /dev/shm is wiped on reboot anyway).
        local_tmp = Path(os.environ.get("TMPDIR", "/tmp")) / f"{output_file.stem}.pt.tmp"
        for attempt in range(3):
            try:
                torch.save(activations_dict, local_tmp,
                           _use_new_zipfile_serialization=False)
                break
            except (RuntimeError, OSError) as e:
                if attempt < 2:
                    logger.warning(f"Local torch.save failed for {role} (attempt {attempt+1}/3): {e}")
                    _time.sleep(5)
                else:
                    raise
        for attempt in range(5):
            try:
                shutil.copy2(str(local_tmp), str(output_file))
                n_act = len(activations_dict) - (1 if "metadata" in activations_dict else 0)
                logger.info(f"Saved {n_act} activations (+ metadata) for {role}")
                break
            except OSError as e:
                if attempt < 4:
                    wait = 10 * (attempt + 1)
                    logger.warning(f"Copy to NFS failed for {role} (attempt {attempt+1}/5): {e}. "
                                   f"Retrying in {wait}s...")
                    _time.sleep(wait)
                else:
                    logger.error(f"Copy to NFS failed for {role} after 5 attempts: {e}")
                    raise
        local_tmp.unlink(missing_ok=True)

    # Cleanup
    gc.collect()
    torch.cuda.empty_cache()

    return True, len(mismatches)


def process_roles_on_worker(worker_id: int, gpu_ids: List[int], role_files: List[Path], args):
    """Process a subset of roles on a worker."""
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

    try:
        # Load model
        worker_logger.info(f"Loading model: {args.model}")
        pm = ProbingModel(args.model)

        # Determine layers
        n_layers = len(pm.get_layers())
        if args.layers == "all":
            layers = list(range(n_layers))
        else:
            layers = [int(x.strip()) for x in args.layers.split(",")]

        worker_logger.info(f"Extracting {len(layers)} layers")

        # Process assigned roles
        extract_headers = not args.no_headers
        completed_count = 0
        failed_count = 0
        total_mismatches = 0

        for role_file in tqdm(role_files, desc=f"Worker-{worker_id}", position=worker_id):
            try:
                success, n_mm = process_role(
                    pm, role_file, output_dir, layers,
                    args.batch_size, args.max_length, args.thinking,
                    extract_headers=extract_headers,
                )
                total_mismatches += n_mm
                if success:
                    completed_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                failed_count += 1
                worker_logger.error(f"Exception processing {role_file.stem}: {e}")

        worker_logger.info(
            f"Worker {worker_id} completed: {completed_count} successful, "
            f"{failed_count} failed, {total_mismatches} total header mismatches"
        )

    except Exception as e:
        worker_logger.error(f"Fatal error on Worker {worker_id}: {e}")

    finally:
        worker_logger.info(f"Worker {worker_id} cleanup completed")


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

    role_files = []
    for f in sorted(responses_dir.glob("*.jsonl")):
        # Filter by --roles if specified
        if args.roles and f.stem not in args.roles:
            continue
        # Filter by --name_prefix if specified (subset extraction, e.g. r_)
        if args.name_prefix and not f.stem.startswith(args.name_prefix):
            continue
        # Skip existing
        output_file = output_dir / f"{f.stem}.pt"
        if output_file.exists():
            logger.info(f"Skipping {f.stem} (already exists)")
            continue
        role_files.append(f)

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

    logger.info("Multi-worker processing completed!")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Extract activations from responses")
    parser.add_argument("--model", type=str, required=True, help="HuggingFace model name")
    parser.add_argument("--responses_dir", type=str, required=True, help="Directory with response JSONL files")
    parser.add_argument("--output_dir", type=str, required=True, help="Output directory for .pt files")
    parser.add_argument("--layers", type=str, default="all", help="Layers to extract (all or comma-separated)")
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
    parser.add_argument("--thinking", type=lambda x: x.lower() in ['true', '1', 'yes'], default=False,
                       help="Enable thinking mode for Qwen models (default: False)")
    parser.add_argument("--no-headers", action="store_true", default=False,
                       help="Disable header token extraction (legacy compat)")
    args = parser.parse_args()

    # Set up file logging (append to output_dir/activations.log)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(output_dir / "activations.log", mode="a")
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(file_handler)

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

        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        responses_dir = Path(args.responses_dir)

        # Determine which roles need processing -- BEFORE loading the model.
        # This lets the script run cleanly on a CPU-only box when all
        # activations are already cached (e.g. re-running just to drive the
        # downstream pipeline steps).  Loading ProbingModel triggers a
        # multi-GB GPU allocation, which would fail without CUDA even when
        # there's no actual work to do.
        response_files = sorted(responses_dir.glob("*.jsonl"))
        logger.info(f"Found {len(response_files)} response files")

        if args.roles:
            response_files = [f for f in response_files if f.stem in args.roles]
        if args.name_prefix:
            response_files = [f for f in response_files
                              if f.stem.startswith(args.name_prefix)]

        role_files = []
        for f in response_files:
            output_file = output_dir / f"{f.stem}.pt"
            if output_file.exists():
                logger.info(f"Skipping {f.stem} (already exists)")
                continue
            role_files.append(f)

        if not role_files:
            logger.info("Nothing to process — all activations already exist")
            return

        # Load model
        logger.info(f"Loading model: {args.model}")
        pm = ProbingModel(args.model)

        n_layers = len(pm.get_layers())
        logger.info(f"Model has {n_layers} layers")

        if args.layers == "all":
            layers = list(range(n_layers))
        else:
            layers = [int(x.strip()) for x in args.layers.split(",")]

        logger.info(f"Extracting {len(layers)} layers")

        extract_headers = not args.no_headers
        total_mismatches = 0

        for role_file in tqdm(role_files, desc="Processing roles"):
            _, n_mm = process_role(
                pm, role_file, output_dir, layers,
                args.batch_size, args.max_length, args.thinking,
                extract_headers=extract_headers,
            )
            total_mismatches += n_mm

        if total_mismatches:
            logger.warning(f"Total header-token mismatches across all roles: {total_mismatches}")

    logger.info("Done!")


if __name__ == "__main__":
    main()
