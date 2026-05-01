#!/usr/bin/env python3
"""Multi-GPU steering sweep dispatcher.

Reads a YAML/JSON experiment config, builds a work-item queue
``[baselines, (slot, layer, sign) x N]``, and spawns one worker process
per visible GPU.  Each worker loads the model once (using
``setup_model_tmpfs_cache`` to mirror weights into /dev/shm and avoid
NFS-backed mmap stalls), then pulls items off the shared queue and runs
either :func:`compute_baselines` or :func:`run_steering_cell`.

Baselines (strength=0) are computed once per (persona, question) and
shared across all cells via ``{output_root}/baselines/records.jsonl``.

Usage::

    uv run steering/run_sweep.py --config configs/angel_to_demon.yaml
    uv run steering/run_sweep.py --config configs/foo.yaml --gpus 4

Config schema (YAML or JSON, by file extension)::

    experiment_id: angel_to_demon_v1
    model_name: Qwen/Qwen3-32B
    output_dir: /workspace/outputs/qwen-3-32b/steering    # parent dir
    axis_source:
      type: role_transplant         # or "axis"
      # for "role_transplant":
      vectors_dir: /workspace/outputs/qwen-3-32b/roles/vectors
      role_from: angel
      role_to: demon
      # for "axis":
      # axis_path: /workspace/outputs/qwen-3-32b/roles/axis.pt
    persona:
      type: role                    # or "trait", "combination"
      role: historian
      traits: []                    # used for "combination" / "trait"
      prompt_index: 0               # which of the 5 instruction variants
    cells:
      - { slot: 0, layer: 26 }
      - { slot: 0, layer: 49 }
      - { slot: 3, layer: 25 }
      # optional per-cell overrides:
      # - { slot: 1, layer: 25, weakest_strength: 0.5 }
    sweep:
      weakest_strength: 1.0
      max_strength: 64.0
      multiplier: 1.189
      signs: [+1, -1]
    positions_mode: all             # or "prefill_only"
    batch_size: 8
    max_new_tokens: 256
    questions_file: data/steering/questions/angel_to_demon_v1.json

Phase-1 limitations (deferred to follow-up plans):
  - Judge integration is stubbed (NoOpJudgeDispatcher); records land
    with judges=null and never trigger early termination.
  - positions_mode is restricted to {"all", "prefill_only"}.
  - axis_source supports "axis" and "role_transplant"; "header_replacement"
    is deferred (it needs intervention_type=replacement, a larger change).
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Make assistant_axis imports work whether run from repo root or steering/.
# steering/run_sweep.py -> parents[1] is the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from assistant_axis.atomic_io import (   # noqa: E402
    atomic_write_text, read_text_with_retry,
)

logger = logging.getLogger("steering_sweep")


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def _load_config(path: Path) -> Dict[str, Any]:
    text = read_text_with_retry(path, logger_obj=logger)
    if path.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as e:
            raise SystemExit(
                "PyYAML required for .yaml configs; install or use .json"
            ) from e
        return yaml.safe_load(text)
    return json.loads(text)


def _load_questions(path: Path) -> List[str]:
    """Load a question list from a JSON file.

    Accepts either:
      - a flat list: ["q1", "q2", ...]
      - or {"questions": ["q1", "q2", ...]}
    """
    raw = json.loads(read_text_with_retry(path, logger_obj=logger))
    if isinstance(raw, list):
        questions = raw
    elif isinstance(raw, dict) and "questions" in raw:
        questions = raw["questions"]
    else:
        raise ValueError(
            f"{path}: expected a list or {{questions: [...]}}; got {type(raw).__name__}"
        )
    if not all(isinstance(q, str) for q in questions):
        raise ValueError(f"{path}: all entries must be strings")
    return list(questions)


def _build_persona_system_prompt(persona_cfg: Dict[str, Any],
                                 *,
                                 instructions_dir: Path) -> str:
    """Build the system prompt for the persona using the standard instruction sources.

    role:        data/roles/instructions/<role>.json instruction[prompt_index].pos
    trait:       data/traits/instructions/<trait>.json instruction[prompt_index].pos
    combination: role_inst + "\\n" + trait_inst[i] for each trait, joined by "\\n"
                 (matches RoleResponseGenerator.generate_combined_responses
                 in assistant_axis/generation.py:475)
    """
    ptype = persona_cfg.get("type", "role")
    prompt_idx = int(persona_cfg.get("prompt_index", 0))

    def _load_inst(kind: str, name: str) -> str:
        path = instructions_dir / kind / "instructions" / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(
                f"persona instruction file not found: {path}"
            )
        data = json.loads(read_text_with_retry(path, logger_obj=logger))
        try:
            return data["instruction"][prompt_idx]["pos"]
        except (KeyError, IndexError) as e:
            raise ValueError(
                f"{path}: missing instruction[{prompt_idx}].pos"
            ) from e

    if ptype == "role":
        return _load_inst("roles", persona_cfg["role"])
    if ptype == "trait":
        return _load_inst("traits", persona_cfg["trait"])
    if ptype == "combination":
        role = persona_cfg["role"]
        traits = persona_cfg.get("traits", [])
        if not traits:
            raise ValueError("combination persona requires at least one trait")
        parts = [_load_inst("roles", role)]
        for trait in traits:
            parts.append(_load_inst("traits", trait))
        return "\n".join(parts)
    raise ValueError(f"unknown persona.type: {ptype!r}")


# ---------------------------------------------------------------------------
# Work-item construction
# ---------------------------------------------------------------------------

def _cell_dir_name(slot: int, layer: int, sign: int) -> str:
    sign_str = "+1" if sign > 0 else "-1"
    return f"s{slot}_l{layer}_{sign_str}"


def _build_work_items(
    config: Dict[str, Any],
    output_root: Path,
    persona_prompt: str,
    questions: List[str],
) -> List[Dict[str, Any]]:
    """Construct the list of work items to dispatch to GPU workers.

    Produces one ``baselines`` item, then one ``cell`` item per
    ``(slot, layer, sign)``.  Items are simple dicts (picklable) that
    workers consume to call either ``compute_baselines`` or
    ``run_steering_cell``.
    """
    sweep_cfg = config.get("sweep", {})
    default_weakest = float(sweep_cfg.get("weakest_strength", 1.0))
    max_strength = float(sweep_cfg.get("max_strength", 64.0))
    multiplier = float(sweep_cfg.get("multiplier", 1.189))
    signs = list(sweep_cfg.get("signs", [+1, -1]))
    if not all(s in (+1, -1) for s in signs):
        raise ValueError(f"sweep.signs must be subset of [+1, -1]; got {signs}")

    batch_size = int(config.get("batch_size", 8))
    max_new_tokens = int(config.get("max_new_tokens", 256))
    positions_mode = config.get("positions_mode", "all")

    items: List[Dict[str, Any]] = [{
        "kind": "baselines",
        "persona": persona_prompt,
        "questions": questions,
        "output_dir": str(output_root),
        "batch_size": batch_size,
        "max_new_tokens": max_new_tokens,
    }]

    cells = config.get("cells", [])
    if not cells:
        raise ValueError("config.cells is empty; nothing to sweep")

    for cell_cfg in cells:
        slot = int(cell_cfg["slot"])
        layer = int(cell_cfg["layer"])
        weakest = float(cell_cfg.get("weakest_strength", default_weakest))
        for sign in signs:
            cell_dir = output_root / _cell_dir_name(slot, layer, int(sign))
            items.append({
                "kind": "cell",
                "slot": slot,
                "layer": layer,
                "sign": int(sign),
                "cell_dir": str(cell_dir),
                "axis_source": config["axis_source"],
                "weakest_strength": weakest,
                "max_strength": max_strength,
                "multiplier": multiplier,
                "persona": persona_prompt,
                "questions": questions,
                "batch_size": batch_size,
                "max_new_tokens": max_new_tokens,
                "positions_mode": positions_mode,
            })
    return items


# ---------------------------------------------------------------------------
# Worker process
# ---------------------------------------------------------------------------

def _setup_worker_logger(worker_id: int, gpu_id: int) -> logging.Logger:
    log = logging.getLogger(f"steering_worker_{worker_id}")
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        f"%(asctime)s - W{worker_id}[GPU {gpu_id}] - %(levelname)s - %(message)s"
    ))
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    return log


def _load_axis_for_cell(axis_source: Dict[str, Any],
                        slot: int, layer: int):
    """Load and extract a steering vector for one cell.

    Returns a 1-D torch.Tensor of shape (hidden,).  Workers are expected
    to move it to their model's device before passing to run_steering_cell.
    The axis-loaders themselves use atomic_io.torch_load_with_retry, so
    transient NFS short-reads are retried automatically.
    """
    from assistant_axis.axis import load_axis_with_metadata, load_role_vector

    src_type = axis_source.get("type", "axis")

    def _ensure_3d(t):
        return t.unsqueeze(0) if t.ndim == 2 else t

    if src_type == "axis":
        axis_path = axis_source["axis_path"]
        axis_raw, _ = load_axis_with_metadata(axis_path)
        axis_raw = _ensure_3d(axis_raw)
        return axis_raw[slot, layer].clone()

    if src_type == "role_transplant":
        vectors_dir = Path(axis_source["vectors_dir"])
        role_from = axis_source["role_from"]
        role_to = axis_source["role_to"]
        v_from, _ = load_role_vector(str(vectors_dir / f"{role_from}.pt"))
        v_to, _ = load_role_vector(str(vectors_dir / f"{role_to}.pt"))
        v_from = _ensure_3d(v_from)
        v_to = _ensure_3d(v_to)
        diff = v_to - v_from
        return diff[slot, layer].clone()

    if src_type == "header_replacement":
        raise NotImplementedError(
            "axis_source.type='header_replacement' is deferred to a later "
            "plan -- it needs intervention_type=replacement which the v1 "
            "runner does not expose."
        )

    raise ValueError(f"unknown axis_source.type: {src_type!r}")


def _worker_main(
    worker_id: int,
    gpu_id: int,
    queue,                 # multiprocessing.Queue
    config: Dict[str, Any],
):
    """Worker process body: load model on assigned GPU, drain work queue."""
    # Restrict CUDA to just our GPU before any torch import that could
    # initialise CUDA context.
    os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)

    # Set up tmpfs (TMPDIR + HF cache mirror) before model load.
    from assistant_axis.tmpfs import setup_model_tmpfs_cache, setup_tmpdir_if_unset
    setup_tmpdir_if_unset()
    new_hf_home = setup_model_tmpfs_cache(model_name=config["model_name"])
    if new_hf_home is not None:
        os.environ["HF_HOME"] = new_hf_home

    log = _setup_worker_logger(worker_id, gpu_id)
    log.info("starting; loading model...")

    # Heavy imports inside the worker so they happen post-fork.
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from assistant_axis.steering_runner import (
        compute_baselines, directional_schedule, run_steering_cell,
    )

    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(config["model_name"])
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        config["model_name"],
        device_map="cuda:0",  # only this GPU is visible after CUDA_VISIBLE_DEVICES
        dtype=torch.bfloat16,
    )
    model.eval()
    log.info(f"model loaded in {time.time() - t0:.1f}s")

    while True:
        item = queue.get()
        if item is None:
            log.info("got sentinel; exiting")
            break

        try:
            if item["kind"] == "baselines":
                log.info("computing baselines")
                compute_baselines(
                    model, tokenizer,
                    persona_system_prompt=item["persona"],
                    questions=item["questions"],
                    output_dir=item["output_dir"],
                    batch_size=item["batch_size"],
                    max_new_tokens=item["max_new_tokens"],
                    model_name=config["model_name"],
                )

            elif item["kind"] == "cell":
                slot, layer, sign = item["slot"], item["layer"], item["sign"]
                cell_dir = item["cell_dir"]
                log.info(
                    f"running cell s{slot}_l{layer}_sign={sign:+d}, "
                    f"weakest={item['weakest_strength']}, max={item['max_strength']}"
                )
                axis_vector = _load_axis_for_cell(
                    item["axis_source"], slot, layer
                ).to(model.device, dtype=torch.bfloat16)
                schedule = directional_schedule(
                    sign=sign,
                    weakest=item["weakest_strength"],
                    max_strength=item["max_strength"],
                    multiplier=item["multiplier"],
                )
                log.info(f"schedule: {len(schedule)} strengths "
                         f"({schedule[0]} .. {schedule[-1]})")
                run_steering_cell(
                    model, tokenizer,
                    axis_vector=axis_vector,
                    slot=slot,
                    layer=layer,
                    sign=sign,
                    strengths=schedule,
                    persona_system_prompt=item["persona"],
                    questions=item["questions"],
                    output_dir=cell_dir,
                    batch_size=item["batch_size"],
                    max_new_tokens=item["max_new_tokens"],
                    positions_mode=item["positions_mode"],
                    model_name=config["model_name"],
                )
            else:
                log.error(f"unknown work item kind: {item.get('kind')!r}")

        except Exception as e:
            log.exception(f"item {item.get('kind')!r} failed: {e}")
            # Continue processing remaining items rather than crash the
            # worker -- one bad cell shouldn't sink the whole sweep.

    log.info("worker exiting cleanly")


# ---------------------------------------------------------------------------
# Coordinator
# ---------------------------------------------------------------------------

def _detect_gpu_count(requested: Optional[int]) -> int:
    """Return number of GPUs to use.

    If `requested` is None, use all visible GPUs (CUDA_VISIBLE_DEVICES
    or torch.cuda.device_count()).  Otherwise cap at min(requested, available).
    """
    import torch
    available = torch.cuda.device_count()
    if available == 0:
        raise RuntimeError(
            "no CUDA GPUs visible; this script requires at least 1 GPU"
        )
    if requested is None:
        return available
    return max(1, min(int(requested), available))


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, required=True,
                        help="YAML or JSON experiment config file")
    parser.add_argument("--gpus", type=int, default=None,
                        help="Number of GPUs to use (default: all visible)")
    parser.add_argument("--instructions_dir", type=Path, default=Path("data"),
                        help="Root of data/{roles,traits}/instructions/<name>.json "
                             "(default: data)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    config = _load_config(args.config)

    # Required keys
    for k in ("experiment_id", "model_name", "output_dir", "axis_source",
              "persona", "cells", "questions_file"):
        if k not in config:
            raise SystemExit(f"config missing required key: {k!r}")

    output_root = Path(config["output_dir"]) / config["experiment_id"]
    output_root.mkdir(parents=True, exist_ok=True)

    # Freeze config + questions to the experiment dir for reproducibility.
    questions = _load_questions(Path(config["questions_file"]))
    persona_prompt = _build_persona_system_prompt(
        config["persona"], instructions_dir=args.instructions_dir,
    )

    atomic_write_text(json.dumps(config, indent=2) + "\n",
                      output_root / "config.json")
    atomic_write_text(json.dumps(questions, indent=2) + "\n",
                      output_root / "questions.json")
    atomic_write_text(persona_prompt + "\n",
                      output_root / "persona_system_prompt.txt")
    logger.info(f"experiment {config['experiment_id']} -> {output_root}")
    logger.info(f"persona system prompt: {persona_prompt!r}")
    logger.info(f"{len(questions)} questions loaded from {config['questions_file']}")

    work_items = _build_work_items(config, output_root, persona_prompt, questions)
    n_cells = sum(1 for it in work_items if it["kind"] == "cell")
    logger.info(f"built {len(work_items)} work items "
                f"(1 baselines + {n_cells} cells)")

    n_gpus = _detect_gpu_count(args.gpus)
    logger.info(f"using {n_gpus} GPU worker(s)")

    # Spawn workers.  CUDA requires the 'spawn' start method.
    import torch.multiprocessing as mp
    ctx = mp.get_context("spawn")
    queue = ctx.Queue()
    for item in work_items:
        queue.put(item)
    for _ in range(n_gpus):
        queue.put(None)  # sentinel per worker

    procs = []
    for worker_id in range(n_gpus):
        gpu_id = worker_id  # 1:1 mapping when CUDA_VISIBLE_DEVICES is preserved
        p = ctx.Process(
            target=_worker_main,
            args=(worker_id, gpu_id, queue, config),
        )
        p.start()
        procs.append(p)

    rc = 0
    for p in procs:
        p.join()
        if p.exitcode != 0:
            logger.error(f"worker pid={p.pid} exited with code {p.exitcode}")
            rc = 1

    logger.info("all workers finished")
    sys.exit(rc)


if __name__ == "__main__":
    main()
