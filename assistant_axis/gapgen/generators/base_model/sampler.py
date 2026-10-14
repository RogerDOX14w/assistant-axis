"""The sample plan and the sampler (plan section 5, ``sampler.py``).

:func:`plan_samples` turns a round into a deterministic list of :class:`SampleSpec`: the family of sample ``i``
comes from one seeded draw sequence (fixed weights, so a longer plan extends a shorter one), its prompt from a
``random.Random`` seeded by ``(seed, round, i)``, and each family's header variants cycle.  A temperature grid
(the shakedown) repeats the same prompts at every temperature.

:func:`run_sampling` runs a :class:`SampleBackend` over the plan's pending samples (those not already in the
round's ``samples.jsonl``), batched by temperature and sorted by prompt length (less padding), appends one JSON
line per sample after every batch (the file is the checkpoint: a resumed run skips what is there), and charges
each sample's prompt and new tokens to a ``MultiModelUsage`` under the model id, priced at zero
(``judge_pricing``), writing ``usage.json`` after every batch and in a ``finally`` (an interrupted run keeps
its record).  Continuations are cut at the first blank line.

Batches are sized by a prompt-token budget as well as ``batch_size`` (2026-10-14: the 20k run of 2026-10-14 ran the
Mac out of unified memory in its last batches, 32 of the longest prompts, and filled the disk with swap):
:func:`make_batches` closes a batch before ``len(batch) * longest prompt in it`` would pass ``token_budget``, so
long prompts go in smaller batches and ``batch_size`` stays the most a batch holds.  Prompt lengths are the
backend's tokenizer counts (``prompt_tokens``) or, for a backend without one, ``ceil(chars / 4)``.  The default,
:data:`DEFAULT_TOKEN_BUDGET` = 1,024, is batch 32 at 32 tokens: the 19,920 prompts of round 1 have a median of 31
tokens (p90 109, longest 404), so the short half still goes 32 at a time while a 109-token prompt goes 9 at a time
and the longest 2 at a time.  ``None`` or 0 turns the budget off (batches of ``batch_size``, as before).

:class:`HFBackend` is the local model: ``transformers`` on MPS (or CPU) in bf16, left padding, nucleus sampling
with ``min_p``, no repetition penalty, ``stop_strings=["\\n\\n"]``.  It loads only from the in-tree Hub cache
(``data/external/hf``, ``local_files_only``) and never downloads.
"""
from __future__ import annotations

import json
import os
import random
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional, Protocol, Sequence

from assistant_axis.judge_pricing import MultiModelUsage

from . import MODEL_ID
from .prompts import FAMILIES, FAMILY_WEIGHTS, PROMPTS_VERSION, Prompt, render
from .seeds import SeedBundle

TOP_P = 0.95
MIN_P = 0.05
MAX_NEW_TOKENS = 80
STOP = "\n\n"
#: The prompt-token budget of one batch (see the module docstring): batch 32 at round 1's median prompt (31 tokens).
DEFAULT_TOKEN_BUDGET = 1024
#: The character-per-token proxy for a backend that cannot count tokens.
CHARS_PER_TOKEN = 4


@dataclass(frozen=True)
class Generation:
    text: str
    n_prompt_tokens: int
    n_new_tokens: int
    stop_reason: Optional[str]      # blank_line | eos | max_tokens


class SampleBackend(Protocol):
    model_id: str
    batch_size: int

    def generate(self, prompts: Sequence[str], *, temperature: float, top_p: float, min_p: float,
                 max_new_tokens: int) -> list: ...


@dataclass(frozen=True)
class SampleSpec:
    sample_id: str
    round: int
    index: int
    family: str
    temperature: float
    prompt: Prompt


@dataclass
class SampleStats:
    n_planned: int = 0
    n_done_before: int = 0
    n_new: int = 0
    n_prompt_tokens: int = 0
    n_new_tokens: int = 0
    seconds: float = 0.0
    stop_reasons: Counter = field(default_factory=Counter)

    @property
    def tok_per_s(self) -> float:
        return self.n_new_tokens / self.seconds if self.seconds > 0 else 0.0

    def as_dict(self) -> dict:
        return {"n_planned": self.n_planned, "n_done_before": self.n_done_before, "n_new": self.n_new,
                "n_prompt_tokens": self.n_prompt_tokens, "n_new_tokens": self.n_new_tokens,
                "seconds": round(self.seconds, 1), "new_tok_per_s": round(self.tok_per_s, 1),
                "stop_reasons": dict(sorted(self.stop_reasons.items(), key=lambda kv: str(kv[0])))}


# ---------------------------------------------------------------------------- plan

def _tag(t: float) -> str:
    return f"{float(t):g}"


def plan_samples(bundle: SeedBundle, *, round_n: int, n: int, seed: int = 0,
                 temperatures: Sequence[float] = (1.0,), families: Optional[Iterable[str]] = None,
                 weights: Optional[dict] = None) -> list[SampleSpec]:
    """The round's samples (see the module docstring).  Ids: ``R<round>-<i:06d>``, or ``R<round>-t<T>-<i:06d>``
    when the plan has several temperatures."""
    fams = tuple(families) if families else FAMILIES
    unknown = [f for f in fams if f not in FAMILIES]
    if unknown:
        raise ValueError(f"unknown families {unknown} (one of {FAMILIES})")
    w = weights or FAMILY_WEIGHTS
    fam_w = [w[f] for f in fams]
    frng = random.Random(f"{seed}:{round_n}:families")
    counters: Counter = Counter()
    base: list[tuple[int, str, Prompt]] = []
    for i in range(n):
        fam = frng.choices(fams, weights=fam_w)[0]
        v = counters[fam] % 10
        counters[fam] += 1
        base.append((i, fam, render(fam, bundle, random.Random(f"{seed}:{round_n}:{i}"), variant=v)))
    out = []
    multi = len(temperatures) > 1
    for t in temperatures:
        for i, fam, p in base:
            sid = f"R{round_n}-t{_tag(t)}-{i:06d}" if multi else f"R{round_n}-{i:06d}"
            out.append(SampleSpec(sample_id=sid, round=round_n, index=i, family=fam, temperature=float(t), prompt=p))
    return out


# ---------------------------------------------------------------------------- sampling

def truncate_at_stop(text: str) -> tuple[str, Optional[str]]:
    """Cut a continuation at its first blank line."""
    i = text.find(STOP)
    return (text[:i], "blank_line") if i >= 0 else (text, None)


def read_done(path: Path) -> set[str]:
    p = Path(path)
    if not p.exists():
        return set()
    done = set()
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                done.add(json.loads(line)["sample_id"])
            except (json.JSONDecodeError, KeyError):
                continue          # a torn last line from a killed run: that sample is redone
    return done


def _record(s: SampleSpec, g, *, model: str, top_p: float, min_p: float, max_new_tokens: int) -> dict:
    text, reason = truncate_at_stop(g.text)
    return {"sample_id": s.sample_id, "round": s.round, "index": s.index, "family": s.family,
            "prompt_sha256": s.prompt.sha256, "prompts_version": PROMPTS_VERSION, "seed_refs": list(s.prompt.seed_refs),
            "seed_words": list(s.prompt.seeds), "constraint": s.prompt.constraint,
            "header_variant": s.prompt.header_variant, "partner_seed": s.prompt.partner_seed,
            "temperature": s.temperature, "top_p": top_p, "min_p": min_p, "max_new_tokens": max_new_tokens,
            "text": text, "n_prompt_tokens": int(g.n_prompt_tokens), "n_new_tokens": int(g.n_new_tokens),
            "stop_reason": reason or g.stop_reason, "model": model}


def prompt_lengths(backend, texts: Sequence[str]) -> list[int]:
    """Each prompt's length in tokens: the backend's ``prompt_tokens(texts)`` when it has one, else
    ``ceil(len(text) / CHARS_PER_TOKEN)``."""
    fn = getattr(backend, "prompt_tokens", None)
    if callable(fn):
        return [int(n) for n in fn(list(texts))]
    return [max(1, -(-len(t) // CHARS_PER_TOKEN)) for t in texts]


def make_batches(specs: Sequence[SampleSpec], lengths: Sequence[int], *, batch_size: int,
                 token_budget: Optional[int] = DEFAULT_TOKEN_BUDGET) -> list[list[SampleSpec]]:
    """Consecutive batches of ``specs``, in order: a batch is closed when it holds ``batch_size`` specs or when one
    more would make ``len(batch) * longest prompt in it`` exceed ``token_budget`` (a prompt longer than the budget
    goes alone).  ``token_budget`` None or 0: ``batch_size`` alone."""
    bs = max(1, int(batch_size))
    out: list[list[SampleSpec]] = []
    cur: list[SampleSpec] = []
    longest = 0
    for s, n in zip(specs, lengths):
        m = max(longest, int(n))
        if cur and (len(cur) >= bs or (token_budget and (len(cur) + 1) * m > token_budget)):
            out.append(cur)
            cur, m = [], int(n)
        cur.append(s)
        longest = m
    if cur:
        out.append(cur)
    return out


def run_sampling(backend: SampleBackend, plan: Sequence[SampleSpec], *, out_path: Path, usage: MultiModelUsage,
                 usage_path: Optional[Path] = None, resume: bool = True, top_p: float = TOP_P, min_p: float = MIN_P,
                 max_new_tokens: int = MAX_NEW_TOKENS, token_budget: Optional[int] = None,
                 echo=print) -> SampleStats:
    """Sample every pending spec of ``plan`` into ``out_path`` (see the module docstring).  ``token_budget``: the
    prompt-token budget of a batch (:func:`make_batches`; the CLI passes :data:`DEFAULT_TOKEN_BUDGET`); None or 0
    sizes batches by ``backend.batch_size`` alone."""
    out_path = Path(out_path)
    done = read_done(out_path) if resume else set()
    if not resume and out_path.exists() and out_path.stat().st_size:
        raise FileExistsError(f"{out_path} exists; resume it or choose another round")
    stats = SampleStats(n_planned=len(plan), n_done_before=sum(1 for s in plan if s.sample_id in done))
    pending = [s for s in plan if s.sample_id not in done]
    batches: list[list[SampleSpec]] = []
    for t in sorted({s.temperature for s in pending}):
        group = sorted((s for s in pending if s.temperature == t), key=lambda s: (len(s.prompt.text), s.sample_id))
        lengths = prompt_lengths(backend, [s.prompt.text for s in group]) if token_budget else [0] * len(group)
        batches += make_batches(group, lengths, batch_size=backend.batch_size, token_budget=token_budget)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    try:
        for bi, batch in enumerate(batches, 1):
            gens = backend.generate([s.prompt.text for s in batch], temperature=batch[0].temperature, top_p=top_p,
                                    min_p=min_p, max_new_tokens=max_new_tokens)
            recs = [_record(s, g, model=backend.model_id, top_p=top_p, min_p=min_p, max_new_tokens=max_new_tokens)
                    for s, g in zip(batch, gens)]
            with open(out_path, "a", encoding="utf-8") as fh:
                fh.write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs))
                fh.flush()
                os.fsync(fh.fileno())
            for r in recs:
                usage.charge(backend.model_id, r["n_prompt_tokens"], r["n_new_tokens"])
                stats.n_prompt_tokens += r["n_prompt_tokens"]
                stats.n_new_tokens += r["n_new_tokens"]
                stats.stop_reasons[r["stop_reason"]] += 1
            stats.n_new += len(recs)
            stats.seconds = time.time() - t0
            if usage_path is not None:
                usage.write_json(usage_path)
            echo(f"batch {bi}/{len(batches)} T={batch[0].temperature:g} ({len(batch)} prompts): "
                 f"{stats.n_done_before + stats.n_new}/{stats.n_planned} samples, {stats.tok_per_s:.1f} new tok/s")
    finally:
        stats.seconds = time.time() - t0
        if usage_path is not None:
            usage.write_json(usage_path)
    return stats


# ---------------------------------------------------------------------------- the local model

class HFBackend:  # pragma: no cover - loads the 16 GB model; exercised by the GAPGEN_RUN_LOCAL smoke test
    """``Qwen/Qwen3-8B-Base`` through ``transformers`` (see the module docstring)."""

    def __init__(self, model_id: str = MODEL_ID, *, device: str = "mps", dtype: str = "bfloat16",
                 batch_size: int = 32, cache_dir: Optional[Path] = None):
        from assistant_axis.gapgen.paths import hf_cache_dir, pin_hf_cache
        pin_hf_cache()
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        if device == "mps" and not torch.backends.mps.is_available():
            raise RuntimeError("MPS is not available in this process (inside the Claude Code Bash sandbox Metal sees "
                               "no device); run outside the sandbox, or pass --device cpu")
        self.model_id, self.device, self.batch_size = model_id, device, batch_size
        cdir = str(cache_dir or hf_cache_dir())
        self.tok = AutoTokenizer.from_pretrained(model_id, cache_dir=cdir, local_files_only=True,
                                                 padding_side="left")
        if self.tok.pad_token is None:
            self.tok.pad_token = self.tok.eos_token
        self.model = AutoModelForCausalLM.from_pretrained(model_id, cache_dir=cdir, local_files_only=True,
                                                          dtype=getattr(torch, dtype)).to(device).eval()
        self._torch = torch

    def prompt_tokens(self, prompts: Sequence[str]) -> list[int]:
        """Each prompt's token count, unpadded (what ``generate`` reports as ``n_prompt_tokens``)."""
        return [len(ids) for ids in self.tok(list(prompts))["input_ids"]]

    def release_memory(self) -> None:
        """Hand the device allocator's cached blocks back (PyTorch's MPS allocator keeps freed blocks in its pool,
        so the longest batches' attention memory stayed allocated: 2026-10-14)."""
        torch = self._torch
        if self.device == "mps" and hasattr(torch, "mps"):
            torch.mps.empty_cache()
        elif str(self.device).startswith("cuda"):
            torch.cuda.empty_cache()

    def generate(self, prompts: Sequence[str], *, temperature: float, top_p: float, min_p: float,
                 max_new_tokens: int) -> list[Generation]:
        torch = self._torch
        enc = out = None
        try:
            enc = self.tok(list(prompts), return_tensors="pt", padding=True).to(self.device)
            with torch.inference_mode():
                out = self.model.generate(**enc, do_sample=True, temperature=temperature, top_p=top_p, min_p=min_p,
                                          top_k=0, repetition_penalty=1.0, max_new_tokens=max_new_tokens,
                                          stop_strings=[STOP], tokenizer=self.tok, pad_token_id=self.tok.pad_token_id)
            new = out[:, enc["input_ids"].shape[1]:].tolist()
            n_prompt = enc["attention_mask"].sum(dim=1).tolist()
        finally:
            del enc, out                    # the device tensors, before the pool is emptied
            self.release_memory()
        stops = {self.tok.pad_token_id, self.tok.eos_token_id}
        gens = []
        for row, n_p in zip(new, n_prompt):
            n = next((k for k, t in enumerate(row) if t in stops), len(row))
            text = self.tok.decode(row[:n], skip_special_tokens=True)
            if STOP in text:
                reason = "blank_line"
            elif n < len(row):
                reason = "eos"
            else:
                reason = "max_tokens"
            gens.append(Generation(text=text, n_prompt_tokens=int(n_p), n_new_tokens=int(n + (n < len(row))),
                                   stop_reason=reason))
        return gens
