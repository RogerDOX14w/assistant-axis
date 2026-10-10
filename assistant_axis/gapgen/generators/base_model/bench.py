"""Throughput benchmark of the local model (plan section 5, ``bench.py``; plan 03 section 3.1).

:func:`benchmark` times one batch per batch size at the production sampling settings (80 new tokens, stop at a
blank line) and reports aggregate new tokens per second; :func:`reading` gives the Mac-or-escalate reading:
above :data:`THRESHOLD_TOK_S` (150) aggregate the generator stays on the Mac; below it, the work stops and the
numbers go to Roger (escalation to RunPod or OpenRouter is his decision, plan section 12).
"""
from __future__ import annotations

import time
from typing import Callable, Sequence

from .sampler import MAX_NEW_TOKENS, MIN_P, TOP_P

THRESHOLD_TOK_S = 150.0
FULL_RUN_SAMPLES = 20_000


def benchmark(backend, prompts: Sequence[str], *, batch_sizes: Sequence[int] = (32, 64),
              max_new_tokens: int = MAX_NEW_TOKENS, temperature: float = 1.0, warmup: bool = True,
              clock: Callable[[], float] = time.perf_counter, echo=print) -> list[dict]:
    """One timed batch per size (the prompts cycled to fill it), after an untimed warm-up batch of 2."""
    if warmup:
        backend.generate(list(prompts[:2]), temperature=temperature, top_p=TOP_P, min_p=MIN_P, max_new_tokens=8)
    rows = []
    for bs in batch_sizes:
        batch = [prompts[i % len(prompts)] for i in range(bs)]
        t0 = clock()
        gens = backend.generate(batch, temperature=temperature, top_p=TOP_P, min_p=MIN_P,
                                max_new_tokens=max_new_tokens)
        dt = max(clock() - t0, 1e-9)
        new = sum(g.n_new_tokens for g in gens)
        prompt = sum(g.n_prompt_tokens for g in gens)
        per_sample = dt / bs
        row = {"batch_size": bs, "seconds": round(dt, 2), "new_tokens": new, "prompt_tokens": prompt,
               "tok_per_s": round(new / dt, 1), "samples_per_s": round(bs / dt, 3),
               "mean_new_tokens": round(new / bs, 1),
               "hours_per_20k": round(per_sample * FULL_RUN_SAMPLES / 3600, 2)}
        echo(f"batch {bs}: {dt:.1f} s, {new} new tokens ({row['mean_new_tokens']}/sample), {row['tok_per_s']} tok/s "
             f"aggregate, {row['samples_per_s']} samples/s, 20k samples in about {row['hours_per_20k']} h")
        rows.append(row)
    return rows


def reading(rows: Sequence[dict], *, threshold: float = THRESHOLD_TOK_S) -> str:
    best = max(rows, key=lambda r: r["tok_per_s"])
    if best["tok_per_s"] > threshold:
        return (f"best {best['tok_per_s']} tok/s at batch {best['batch_size']} > {threshold:.0f}: the generator "
                f"stays on the Mac (plan 03 section 3.1)")
    return (f"best {best['tok_per_s']} tok/s at batch {best['batch_size']} is below {threshold:.0f}: stop; the "
            f"numbers go to Roger, whose call escalation is (RunPod or OpenRouter, plan section 12)")
