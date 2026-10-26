#!/usr/bin/env python3
"""Save one layer of activation files, every slot, for analysis off the pod.

Step 2 writes each entity's activations as ``{key: (slots, layers, D)}``,
about 2.6 GB for 500 responses of Qwen3-32B.  The analyses of the rubric and
question-sampling experiments use one layer (25) and every slot, about 41 MB
per entity in bfloat16, small enough to copy to the Mac, where vectors for
any kept set (any judge, any rubric version) are then the mean of the kept
slices (Roger, 2026-10-26: the extra-question run on the 30 sample roles).

Each output file is ``{"layer": L, "source": <path>, "acts": {key: (slots, D)}}``
in the input's dtype.  ``--preread`` reads each file into memory sequentially
in large blocks before ``torch.load`` (the fix pre-extraction item 14 tests
for slow random reads on the network volume); every file's read time and rate
are printed, so the same run measures both ways.

Usage (on the pod):
    python tools/slice_activations.py --activations-dir /root/extra/q1/activations \\
        --out-dir /workspace/rubric_exp/extra_questions/q1/slices_l25 --layer 25
"""
from __future__ import annotations

import argparse
import io
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

BLOCK = 64 * 1024 * 1024


def read_file(path: Path, *, preread: bool):
    """``(acts, seconds)``: the loaded activation dict and the read time."""
    import torch
    t0 = time.time()
    if preread:
        buf = io.BytesIO()
        with open(path, "rb") as f:
            while True:
                block = f.read(BLOCK)
                if not block:
                    break
                buf.write(block)
        buf.seek(0)
        acts = torch.load(buf, map_location="cpu", weights_only=False)
    else:
        acts = torch.load(str(path), map_location="cpu", weights_only=False)
    return acts, time.time() - t0


def slice_layer(acts: dict, layer: int) -> dict:
    """``{key: (slots, D)}``: layer ``layer`` of every 3-d tensor in ``acts``
    (other entries, such as metadata, are left out), copied so the full
    tensors can be freed."""
    import torch
    return {k: v[:, layer, :].clone() for k, v in acts.items() if isinstance(v, torch.Tensor) and v.dim() == 3}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--activations-dir", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--layer", type=int, default=25)
    p.add_argument("--names", nargs="*", help="entity stems (default: every .pt file in the directory)")
    p.add_argument("--preread", action="store_true", help="read each file sequentially into memory first")
    p.add_argument("--overwrite", action="store_true")
    args = p.parse_args()

    from assistant_axis.atomic_io import torch_save_with_retry
    files = ([args.activations_dir / f"{n}.pt" for n in args.names] if args.names
             else sorted(args.activations_dir.glob("*.pt")))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    total_bytes = total_s = 0.0
    for f in files:
        out = args.out_dir / f.name
        if out.exists() and not args.overwrite:
            print(f"{f.stem}: exists, skipped", flush=True)
            continue
        size = f.stat().st_size
        acts, secs = read_file(f, preread=args.preread)
        sliced = slice_layer(acts, args.layer)
        del acts
        torch_save_with_retry({"layer": args.layer, "source": str(f), "acts": sliced}, out)
        total_bytes += size
        total_s += secs
        print(f"{f.stem}: {len(sliced)} responses; read {size / 1e9:.2f} GB in {secs:.1f} s "
              f"({size / 1e6 / max(secs, 1e-9):.0f} MB/s, {'preread' if args.preread else 'torch.load'})", flush=True)
    if total_s:
        print(f"total: {total_bytes / 1e9:.1f} GB read in {total_s:.0f} s ({total_bytes / 1e6 / total_s:.0f} MB/s)")


if __name__ == "__main__":
    main()
