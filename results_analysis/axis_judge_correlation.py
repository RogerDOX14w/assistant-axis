#!/usr/bin/env python3
"""Axis judge correlation tool.

Given a direction in activation space (either derived from a pair of roles or
traits, or loaded from a saved axis file), have a judge LLM score every role
and trait on a -3..+3 rubric and report Spearman rho between the judge scores
and the projections of each entity's activation vector onto the direction, in
both the raw and soft-K PCA-whitened metrics, per token slot.

See results_analysis/README.md for usage.
"""

import argparse
import asyncio
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch
from dotenv import load_dotenv
from tqdm import tqdm

# Repo-internal imports: reuse the existing OpenAI judge infrastructure.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from assistant_axis.judge import RateLimiter  # type: ignore  # noqa: E402

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("axis_judge")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("anthropic").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Rubric templates (adapted from 2026-04-20 ad-hoc analysis)
# ---------------------------------------------------------------------------

_SCALE_TABLE = (
    "## Scale\n"
    "| Score | Meaning |\n"
    "|-------|---------|\n"
    "| -3 | Strongly toward the negative pole |\n"
    "| -2 | Clearly toward the negative pole |\n"
    "| -1 | Leans toward the negative pole |\n"
    "|  0 | Neutral, ambiguous, or does not map onto this axis |\n"
    "| +1 | Leans toward the positive pole |\n"
    "| +2 | Clearly toward the positive pole |\n"
    "| +3 | Strongly toward the positive pole |\n"
)

_RUBRIC_HEADER = (
    "You are scoring where a {entity} concept falls on a semantic axis.\n\n"
    "## Axis: {axis_name}\n\n"
    "**-3 (strong negative pole):** {negative_pole}\n"
    "**+3 (strong positive pole):** {positive_pole}\n\n"
    "For reference, {entity_plural} that score near -3 include: {negative_examples}\n"
    "{entity_plural_title} that score near +3 include: {positive_examples}\n\n"
    f"{_SCALE_TABLE}\n"
)

RUBRIC_STATIC = _RUBRIC_HEADER + (
    "## {entity_title} to score\n\n"
    "**{name}**: {content}\n\n"
    "First, briefly reason about where this {entity} falls on the axis "
    "(2-3 sentences). Then on a new line, write exactly: SCORE: <integer from -3 to +3>"
)

RUBRIC_RESPONSE_BATCH = _RUBRIC_HEADER + (
    "## Model responses to score\n\n"
    "Below are {n_items} responses the model generated while being asked to act as "
    "{entity} **{name}**. Score where **{name}** as a {entity} falls on the axis based on "
    "the behavior and attitudes these responses collectively exhibit (do not base your score "
    "on the questions, only on the responses).\n\n"
    "{items_block}\n\n"
    "First, briefly reason about where this {entity} falls on the axis based on the overall "
    "pattern across these {n_items} responses (2-3 sentences). Then on a new line, write "
    "exactly: SCORE: <integer from -3 to +3>"
)


def parse_signed_score(text: Optional[str]) -> Optional[int]:
    """Extract a signed integer score from a judge response (looks for 'SCORE: <int>').

    Falls back to finding the first standalone integer in [-3, 3] if no 'SCORE:' marker.
    Returns None if nothing parseable is found.
    """
    if not text:
        return None
    m = re.search(r"SCORE\s*:\s*([+-]?\d+)", text, flags=re.IGNORECASE)
    if m:
        try:
            v = int(m.group(1))
        except ValueError:
            v = None
        if v is not None:
            return int(max(-3, min(3, v)))
    # Fallback: first standalone integer in [-3, 3], optionally signed.
    for tok in re.findall(r"(?<![\w.])([+-]?\d+)(?![\w.])", text):
        try:
            v = int(tok)
        except ValueError:
            continue
        if -3 <= v <= 3:
            return v
    return None


# ---------------------------------------------------------------------------
# Axis specification
# ---------------------------------------------------------------------------

@dataclass
class AxisSpec:
    axis_name: str
    neg_pole: str
    pos_pole: str
    neg_examples: List[str]
    pos_examples: List[str]
    # per-slot unit direction in activation space; shape (n_slots, hidden_dim)
    # (fixed layer already selected)
    axis_by_slot: Dict[int, torch.Tensor]
    source_description: str
    # Names to hold out of the whitener pool and to exclude from scoring.
    exclusions: List[str] = field(default_factory=list)


def _slot_list_from_arg(arg: str, n_slots: int) -> List[int]:
    if arg == "all":
        return list(range(n_slots))
    try:
        idx = int(arg)
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"--slot must be 'all' or an integer, got {arg!r}") from e
    if not 0 <= idx < n_slots:
        raise argparse.ArgumentTypeError(f"--slot {idx} out of range [0, {n_slots})")
    return [idx]


def _load_vector_file(path: Path) -> torch.Tensor:
    """Load a .pt file that is either a dict with 'vector'/'axis' key or a raw tensor."""
    d = torch.load(path, weights_only=False, map_location="cpu")
    if isinstance(d, dict):
        for k in ("vector", "axis"):
            if k in d:
                return d[k]
        raise ValueError(f"{path}: dict has no 'vector' or 'axis' key; keys={list(d.keys())}")
    if isinstance(d, torch.Tensor):
        return d
    raise ValueError(f"{path}: unsupported payload type {type(d).__name__}")


def resolve_axis(
    args: argparse.Namespace, n_slots: int, hidden_dim: int, layer: int
) -> AxisSpec:
    """Build the AxisSpec from --pair args or --axis_file + manual pole args."""
    if args.pair is not None:
        name1, name2 = args.pair
        if args.pair_type not in ("roles", "traits"):
            raise SystemExit("--pair requires --pair_type {roles|traits}")
        pair_dir = Path(args.data_dir) / args.pair_type / "vectors"
        v1 = _load_vector_file(pair_dir / f"{name1}.pt")
        v2 = _load_vector_file(pair_dir / f"{name2}.pt")
        # Shape: (n_slots, n_layers, hidden)
        v1 = v1.float(); v2 = v2.float()
        if v1.shape != v2.shape or v1.shape[-1] != hidden_dim or v1.shape[0] != n_slots:
            raise SystemExit(
                f"Pair vectors have unexpected shape: {tuple(v1.shape)} vs {tuple(v2.shape)}; "
                f"expected ({n_slots}, _, {hidden_dim})"
            )

        # Use names as examples unless user overrode.
        neg_examples = args.neg_examples if args.neg_examples else [name2]
        pos_examples = args.pos_examples if args.pos_examples else [name1]
        # Pole descriptions: from instructions JSON descriptions, unless user overrode.
        instructions_dir = Path(args.instructions_dir) / args.pair_type / "instructions"
        if args.neg_pole:
            neg_pole = args.neg_pole
        else:
            with open(instructions_dir / f"{name2}.json") as f:
                neg_pole = json.load(f)["description"]
        if args.pos_pole:
            pos_pole = args.pos_pole
        else:
            with open(instructions_dir / f"{name1}.json") as f:
                pos_pole = json.load(f)["description"]

        # Direction per slot: v1 - v2 at the chosen layer.
        axis_by_slot: Dict[int, torch.Tensor] = {}
        for slot in range(n_slots):
            d = v1[slot, layer] - v2[slot, layer]
            norm = torch.linalg.vector_norm(d).item()
            if not np.isfinite(norm) or norm < 1e-6:
                raise SystemExit(
                    f"Pair direction at slot {slot} layer {layer} has norm {norm:.3e}; "
                    "pair vectors may be identical or corrupted."
                )
            axis_by_slot[slot] = d / norm
        axis_name = f"{name1} (+) vs {name2} (-) [{args.pair_type}]"
        source = (
            f"pair: +pole={name1}, -pole={name2}, type={args.pair_type}, layer={layer}; "
            f"direction = vec[{name1}] - vec[{name2}] (unit-normalized per slot)"
        )
        exclusions = sorted(set([name1, name2, *neg_examples, *pos_examples]))
        return AxisSpec(
            axis_name=axis_name,
            neg_pole=neg_pole, pos_pole=pos_pole,
            neg_examples=neg_examples, pos_examples=pos_examples,
            axis_by_slot=axis_by_slot,
            source_description=source, exclusions=exclusions,
        )

    # Manual-axis path
    if args.axis_file is None:
        raise SystemExit("Specify axis with either --pair / --pair_type or --axis_file + poles")
    if not (args.neg_pole and args.pos_pole and args.neg_examples and args.pos_examples):
        raise SystemExit("--axis_file requires --neg_pole, --pos_pole, --neg_examples, --pos_examples")

    axis_raw = _load_vector_file(Path(args.axis_file)).float()
    # Normalize shape to (n_slots, hidden). Accept a few reasonable inputs.
    if axis_raw.dim() == 3:
        # (n_slots, n_layers, hidden)
        if axis_raw.shape[0] != n_slots or axis_raw.shape[2] != hidden_dim:
            raise SystemExit(
                f"axis_file 3D shape {tuple(axis_raw.shape)} not ({n_slots}, _, {hidden_dim})"
            )
        axis_slots = axis_raw[:, layer, :]
    elif axis_raw.dim() == 2:
        # (n_layers, hidden) — same direction across slots
        if axis_raw.shape[1] != hidden_dim:
            raise SystemExit(f"axis_file 2D shape {tuple(axis_raw.shape)} not (_, {hidden_dim})")
        axis_slots = axis_raw[layer].unsqueeze(0).expand(n_slots, -1).contiguous()
    elif axis_raw.dim() == 1:
        if axis_raw.shape[0] != hidden_dim:
            raise SystemExit(f"axis_file 1D shape {tuple(axis_raw.shape)} not ({hidden_dim},)")
        axis_slots = axis_raw.unsqueeze(0).expand(n_slots, -1).contiguous()
    else:
        raise SystemExit(f"axis_file unsupported rank {axis_raw.dim()}")

    axis_by_slot = {}
    for slot in range(n_slots):
        d = axis_slots[slot]
        norm = torch.linalg.vector_norm(d).item()
        if not np.isfinite(norm) or norm < 1e-6:
            raise SystemExit(
                f"Axis at slot {slot} has norm {norm:.3e}; axis_file may be zeros or corrupted."
            )
        axis_by_slot[slot] = d / norm

    axis_name = args.axis_name or f"axis from {Path(args.axis_file).name}"
    source = f"axis_file: {args.axis_file}, layer={layer}, shape={tuple(axis_raw.shape)}"
    exclusions = sorted(set([*args.neg_examples, *args.pos_examples]))
    return AxisSpec(
        axis_name=axis_name,
        neg_pole=args.neg_pole, pos_pole=args.pos_pole,
        neg_examples=args.neg_examples, pos_examples=args.pos_examples,
        axis_by_slot=axis_by_slot,
        source_description=source, exclusions=exclusions,
    )


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@dataclass
class Corpus:
    # (type, name) -> activation tensor at (n_slots, hidden) for the chosen layer (float)
    vectors: Dict[Tuple[str, str], torch.Tensor]
    # (type, name) -> description text
    descriptions: Dict[Tuple[str, str], str]
    # (type, name) -> list of 5 pos instruction strings
    pos_instructions: Dict[Tuple[str, str], List[str]]
    # default activation at (n_slots, hidden) at the chosen layer
    default: torch.Tensor
    # Probe of what existed: which (type, name) are available for scoring/projecting.
    entities: List[Tuple[str, str]]


def _read_instructions_json(path: Path) -> Dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def load_corpus(args: argparse.Namespace, layer: int) -> Corpus:
    """Load role and trait vectors, descriptions, and pos instructions.

    Uses <data_dir>/{roles,traits}/vectors/*.pt and <instructions_dir>/{roles,traits}/instructions/*.json.
    Only includes entities that have BOTH a vector file AND an instructions JSON.
    """
    data_dir = Path(args.data_dir)
    instructions_dir = Path(args.instructions_dir)

    vectors: Dict[Tuple[str, str], torch.Tensor] = {}
    descriptions: Dict[Tuple[str, str], str] = {}
    pos_instructions: Dict[Tuple[str, str], List[str]] = {}
    default: Optional[torch.Tensor] = None

    for etype in ("roles", "traits"):
        vdir = data_dir / etype / "vectors"
        idir = instructions_dir / etype / "instructions"
        if not vdir.exists():
            logger.info(f"skip {etype}: no vectors dir at {vdir}")
            continue
        if not idir.exists():
            logger.info(f"skip {etype}: no instructions dir at {idir}")
            continue

        for vfile in sorted(vdir.glob("*.pt")):
            name = vfile.stem
            if name == "default":
                # Grab default activation; prefer roles, fall back to traits if not already set.
                if default is None:
                    default = _load_vector_file(vfile).float()
                continue
            ifile = idir / f"{name}.json"
            if not ifile.exists():
                logger.debug(f"skip {etype}/{name}: no instructions file")
                continue
            try:
                inst = _read_instructions_json(ifile)
            except Exception as e:
                logger.warning(f"skip {etype}/{name}: cannot parse instructions: {e}")
                continue
            desc = inst.get("description")
            if not desc:
                logger.debug(f"skip {etype}/{name}: instructions missing 'description'")
                continue
            pos = []
            for rec in inst.get("instruction", []):
                if isinstance(rec, dict) and "pos" in rec:
                    pos.append(rec["pos"])
            if len(pos) < 1:
                logger.debug(f"skip {etype}/{name}: no pos instructions")
                continue
            try:
                vec = _load_vector_file(vfile).float()
            except Exception as e:
                logger.warning(f"skip {etype}/{name}: cannot load vector: {e}")
                continue
            # Select the requested layer now. Vectors are (n_slots, n_layers, hidden).
            if vec.dim() == 3:
                vec_layer = vec[:, layer, :]
            elif vec.dim() == 2:
                # (n_slots, hidden) already, or (n_layers, hidden) — ambiguous.
                # For this repo all vectors are 3D; treat 2D as already-layer-selected
                # with slot dim preserved.
                vec_layer = vec
            else:
                logger.warning(f"skip {etype}/{name}: unexpected vector rank {vec.dim()}")
                continue
            vectors[(etype, name)] = vec_layer
            descriptions[(etype, name)] = desc
            pos_instructions[(etype, name)] = pos

    if default is None:
        # Try top-level default file.
        candidates = [
            data_dir / "default" / "vectors" / "default.pt",
            data_dir / "roles" / "vectors" / "default.pt",
            data_dir / "traits" / "vectors" / "default.pt",
        ]
        for p in candidates:
            if p.exists():
                default = _load_vector_file(p).float()
                break
    if default is None:
        raise SystemExit(
            "Could not find default activation (default.pt) under data_dir; "
            "needed for default-centering the projections."
        )
    if default.dim() == 3:
        default = default[:, layer, :]

    entities = sorted(vectors.keys())
    logger.info(f"Loaded {len(entities)} entities ({sum(1 for e in entities if e[0]=='roles')} roles, "
                f"{sum(1 for e in entities if e[0]=='traits')} traits)")
    return Corpus(
        vectors=vectors, descriptions=descriptions,
        pos_instructions=pos_instructions, default=default, entities=entities,
    )


# ---------------------------------------------------------------------------
# Response/score loading for --score_responses
# ---------------------------------------------------------------------------

@dataclass
class ScoredResponse:
    name: str
    key: str  # 'pos_p{P}_q{Q}'
    question: str
    answer: str


def _load_responses_jsonl(path: Path) -> Dict[Tuple[int, int], Dict[str, Any]]:
    """Map (prompt_index, question_index) -> full record for one entity."""
    out: Dict[Tuple[int, int], Dict[str, Any]] = {}
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                logger.warning(f"{path.name}: cannot parse line: {e}")
                continue
            p = rec.get("prompt_index")
            q = rec.get("question_index")
            if p is None or q is None:
                continue
            out[(int(p), int(q))] = rec
    return out


_KEY_RE = re.compile(r"pos_p(\d+)_q(\d+)")


def load_score3_responses(
    entity_names: Sequence[str],
    scores_dir: Path,
    responses_dir: Path,
) -> Dict[str, List[ScoredResponse]]:
    """For each entity, gather (question, answer) pairs whose response scored 3.

    Performs a sanity check that every score==3 key maps to a response record.
    Missing matches are logged and dropped.
    """
    out: Dict[str, List[ScoredResponse]] = {}
    for name in entity_names:
        scores_path = scores_dir / f"{name}.json"
        responses_path = responses_dir / f"{name}.jsonl"
        if not scores_path.exists():
            logger.warning(f"{name}: no scores file at {scores_path}; skipping response-mode")
            continue
        if not responses_path.exists():
            logger.warning(f"{name}: no responses file at {responses_path}; skipping response-mode")
            continue
        try:
            scores = json.loads(scores_path.read_text())
        except Exception as e:
            logger.warning(f"{name}: cannot parse scores: {e}")
            continue
        response_map = _load_responses_jsonl(responses_path)

        score3_keys = [k for k, v in scores.items() if v == 3]
        matched: List[ScoredResponse] = []
        missing = 0
        for k in score3_keys:
            m = _KEY_RE.match(k)
            if not m:
                continue
            p, q = int(m.group(1)), int(m.group(2))
            rec = response_map.get((p, q))
            if rec is None:
                missing += 1
                continue
            q_text = rec.get("question", "")
            # The final assistant reply is the last assistant message in the conversation.
            conv = rec.get("conversation", [])
            answer = ""
            for turn in reversed(conv):
                if isinstance(turn, dict) and turn.get("role") == "assistant":
                    answer = turn.get("content", "")
                    break
            if not q_text or not answer:
                continue
            matched.append(ScoredResponse(name=name, key=k, question=q_text, answer=answer))
        if missing:
            logger.warning(
                f"{name}: {missing}/{len(score3_keys)} score==3 keys had no matching response record"
            )
        if matched:
            out[name] = matched
        else:
            logger.info(f"{name}: no usable score==3 responses")
    return out


# ---------------------------------------------------------------------------
# Whitener
# ---------------------------------------------------------------------------

@dataclass
class SoftKWhitener:
    """Soft-K PCA whitener: scales top-K PC directions of the fit distribution
    down so they match sigma_{K+1}, leaves all other directions untouched.
    Transform is linear and in-place on row-vectors.
    """
    Vt: torch.Tensor        # (n_pcs, hidden)
    scale: torch.Tensor     # (n_pcs,)
    mu: torch.Tensor        # (hidden,)

    def apply(self, x: torch.Tensor) -> torch.Tensor:
        """x: (..., hidden) -> whitened (..., hidden). Does NOT subtract mu;
        the whitener is a pure linear rescaling of directions."""
        # For a vector v, W(v) = v + sum_k (scale_k - 1) * (v @ v_k) * v_k
        proj = x @ self.Vt.T                     # (..., n_pcs)
        delta = (proj * (self.scale - 1.0)) @ self.Vt  # (..., hidden)
        return x + delta


def fit_soft_k_whitener(pool: torch.Tensor, K: int) -> SoftKWhitener:
    """pool: (N, hidden). Fit on mean-centered SVD of the pool."""
    mu = pool.mean(dim=0)
    X = pool - mu
    # full_matrices=False SVD -> Vt is (min(N, hidden), hidden)
    _U, S, Vt = torch.linalg.svd(X, full_matrices=False)
    if K < 0:
        raise ValueError("K must be >= 0")
    K_eff = min(K, S.numel() - 1) if S.numel() >= 2 else S.numel()
    scale = torch.ones_like(S)
    if K_eff > 0:
        sigma_floor = S[K_eff]
        # Guard against zero singular values (degenerate pool)
        top_sigma = torch.clamp(S[:K_eff], min=torch.finfo(S.dtype).eps)
        scale[:K_eff] = sigma_floor / top_sigma
    return SoftKWhitener(Vt=Vt, scale=scale, mu=mu)


# ---------------------------------------------------------------------------
# Projection
# ---------------------------------------------------------------------------

def compute_projections(
    corpus: Corpus,
    axis_spec: AxisSpec,
    whiten_K: int,
    slots: Sequence[int],
    excluded_names: Sequence[str],
) -> Dict[int, Dict[str, Dict[str, float]]]:
    """Return {slot: {name: {'raw': float, 'whitened': float}}}.

    Names excluded_from whitener pool:
        excluded_names (pair members + example list names).
    But projections ARE computed for every entity (including excluded ones,
    for plotting / diagnostics); the downstream correlation step will drop
    excluded names from the judge-scored set.
    """
    excluded_set = set(excluded_names)
    result: Dict[int, Dict[str, Dict[str, float]]] = {}
    for slot in slots:
        default_vec = corpus.default[slot]  # (hidden,)
        # Build pool (default-centered) at this slot, holding out excluded names
        pool_rows = []
        for (_etype, name), vec in corpus.vectors.items():
            if name in excluded_set:
                continue
            pool_rows.append(vec[slot] - default_vec)
        if len(pool_rows) < 2:
            raise SystemExit(f"slot {slot}: held-out pool has <2 entries; cannot fit whitener")
        pool = torch.stack(pool_rows, dim=0)  # (N, hidden)
        whitener = fit_soft_k_whitener(pool, K=whiten_K)

        axis_unit_raw = axis_spec.axis_by_slot[slot]  # (hidden,)
        # Whitened metric: <x, a>_W = <W x, W a> = (W x) @ (W a).
        axis_w = whitener.apply(axis_unit_raw.unsqueeze(0)).squeeze(0)
        axis_w_norm = torch.linalg.vector_norm(axis_w).item()

        per_slot: Dict[str, Dict[str, float]] = {}
        for (_etype, name), vec in corpus.vectors.items():
            x = vec[slot] - default_vec  # (hidden,)
            raw_proj = float((x @ axis_unit_raw).item())
            if axis_w_norm < 1e-12:
                w_proj = float("nan")
            else:
                xw = whitener.apply(x.unsqueeze(0)).squeeze(0)
                # Project (Wx) onto (Wa)/||Wa|| so it's a unit-axis projection in the
                # whitened metric, same convention as the raw metric.
                w_proj = float((xw @ axis_w).item()) / axis_w_norm
            per_slot[name] = {"raw": raw_proj, "whitened": w_proj}
        result[slot] = per_slot
    return result


# ---------------------------------------------------------------------------
# Scoring: prompt construction
# ---------------------------------------------------------------------------

def _entity_words(etype: str) -> Tuple[str, str, str, str]:
    """(singular, plural, singular_title, plural_title)"""
    if etype == "roles":
        return ("role", "roles", "Role", "Roles")
    return ("trait", "traits", "Trait", "Traits")


def build_static_prompt(axis_spec: AxisSpec, etype: str, name: str, content: str) -> str:
    sing, plur, sing_t, plur_t = _entity_words(etype)
    return RUBRIC_STATIC.format(
        entity=sing, entity_plural=plur,
        entity_title=sing_t, entity_plural_title=plur_t,
        axis_name=axis_spec.axis_name,
        negative_pole=axis_spec.neg_pole, positive_pole=axis_spec.pos_pole,
        negative_examples=", ".join(axis_spec.neg_examples) or "(none)",
        positive_examples=", ".join(axis_spec.pos_examples) or "(none)",
        name=name, content=content,
    )


def build_response_batch_prompt(
    axis_spec: AxisSpec, etype: str, name: str, items: Sequence["ScoredResponse"]
) -> str:
    sing, plur, sing_t, plur_t = _entity_words(etype)
    n = len(items)
    blocks = []
    for i, it in enumerate(items, 1):
        blocks.append(
            f"--- Response {i} of {n} ---\n"
            f"[QUESTION]\n{it.question}\n[/QUESTION]\n"
            f"[RESPONSE]\n{it.answer}\n[/RESPONSE]"
        )
    items_block = "\n\n".join(blocks)
    return RUBRIC_RESPONSE_BATCH.format(
        entity=sing, entity_plural=plur,
        entity_title=sing_t, entity_plural_title=plur_t,
        axis_name=axis_spec.axis_name,
        negative_pole=axis_spec.neg_pole, positive_pole=axis_spec.pos_pole,
        negative_examples=", ".join(axis_spec.neg_examples) or "(none)",
        positive_examples=", ".join(axis_spec.pos_examples) or "(none)",
        name=name, n_items=n, items_block=items_block,
    )


def plan_response_batches(keys: Sequence[str], target_batch_size: int) -> List[List[str]]:
    """Partition `keys` into batches closest in average size to `target_batch_size`.

    n_batches = max(1, round(N / target)). Sizes differ by at most 1: the first
    `N % n_batches` batches get ceil(N/n_batches), the rest floor(N/n_batches).
    """
    n = len(keys)
    if n == 0:
        return []
    n_batches = max(1, round(n / target_batch_size))
    base = n // n_batches
    extra = n % n_batches
    batches: List[List[str]] = []
    idx = 0
    for b in range(n_batches):
        size = base + (1 if b < extra else 0)
        batches.append(list(keys[idx:idx + size]))
        idx += size
    return batches


def _sort_keys_by_question_then_prompt(keys: Sequence[str]) -> List[str]:
    """Sort 'pos_p{P}_q{Q}' keys by (Q, P) so batches naturally interleave
    across the 5 system-prompt variants rather than clumping by prompt."""
    def key_fn(k: str) -> Tuple[int, int]:
        m = _KEY_RE.match(k)
        if not m:
            return (10**9, 10**9)
        return (int(m.group(2)), int(m.group(1)))
    return sorted(keys, key=key_fn)


# ---------------------------------------------------------------------------
# Judge: provider-agnostic async calls
# ---------------------------------------------------------------------------

async def _call_anthropic_batch(
    prompts: Sequence[str],
    model: str,
    max_tokens: int,
    temperature: float,
    rate_limiter: RateLimiter,
    batch_size: int,
) -> List[Optional[str]]:
    import anthropic  # local import so OpenAI-only runs don't need it
    client = anthropic.AsyncAnthropic()

    async def one(prompt: str) -> Optional[str]:
        await rate_limiter.acquire()
        try:
            resp = await client.messages.create(
                model=model, max_tokens=max_tokens, temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            parts = []
            for block in resp.content:
                text = getattr(block, "text", None)
                if text:
                    parts.append(text)
            return "".join(parts) if parts else None
        except Exception as e:
            logger.error(f"anthropic call failed: {e}")
            return None

    results: List[Optional[str]] = []
    for i in range(0, len(prompts), batch_size):
        chunk = prompts[i:i + batch_size]
        tasks = [one(p) for p in chunk]
        r = await asyncio.gather(*tasks, return_exceptions=True)
        for x in r:
            if isinstance(x, Exception):
                logger.error(f"anthropic gather: {x}")
                results.append(None)
            else:
                results.append(x)
    return results


async def _call_openai_batch(
    prompts: Sequence[str],
    model: str,
    max_tokens: int,
    temperature: float,
    rate_limiter: RateLimiter,
    batch_size: int,
) -> List[Optional[str]]:
    """Local OpenAI async path; parallels _call_anthropic_batch so we can set
    temperature and token budget freely (the shared assistant_axis/judge.py
    hardcodes temperature=1).
    """
    import openai
    client = openai.AsyncOpenAI()

    async def one(prompt: str) -> Optional[str]:
        await rate_limiter.acquire()
        try:
            resp = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=max_tokens,
                temperature=temperature,
            )
            return resp.choices[0].message.content
        except Exception as e:
            logger.error(f"openai call failed: {e}")
            return None

    results: List[Optional[str]] = []
    for i in range(0, len(prompts), batch_size):
        chunk = prompts[i:i + batch_size]
        tasks = [one(p) for p in chunk]
        r = await asyncio.gather(*tasks, return_exceptions=True)
        for x in r:
            if isinstance(x, Exception):
                logger.error(f"openai gather: {x}")
                results.append(None)
            else:
                results.append(x)
    return results


async def call_judge(
    prompts: Sequence[str],
    provider: str,
    model: str,
    max_tokens: int,
    temperature: float,
    rps: float,
    batch_size: int,
) -> List[Optional[str]]:
    rate_limiter = RateLimiter(rps)
    if provider == "anthropic":
        return await _call_anthropic_batch(
            prompts, model, max_tokens, temperature, rate_limiter, batch_size
        )
    if provider == "openai":
        return await _call_openai_batch(
            prompts, model, max_tokens, temperature, rate_limiter, batch_size
        )
    raise SystemExit(f"Unknown provider: {provider}")


# ---------------------------------------------------------------------------
# Scoring orchestration (with incremental cache)
# ---------------------------------------------------------------------------

def _default_model_for_provider(provider: str) -> str:
    if provider == "anthropic":
        return "claude-sonnet-4-20250514"
    if provider == "openai":
        return "gpt-4.1-mini"
    raise SystemExit(f"Unknown provider: {provider}")


def _load_json_or_empty(path: Path) -> Dict[str, Any]:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception as e:
            logger.warning(f"{path}: cannot parse existing cache ({e}); starting fresh")
    return {}


def _save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True))


async def score_static_mode(
    mode: str,  # 'descriptions' or 'instructions'
    corpus: Corpus,
    axis_spec: AxisSpec,
    scorable: Sequence[Tuple[str, str]],
    args: argparse.Namespace,
) -> Dict[str, int]:
    cache_path = Path(args.output_dir) / f"scores_{mode}.json"
    cache: Dict[str, Any] = {} if args.no_cache else _load_json_or_empty(cache_path)

    prompts: List[str] = []
    names: List[str] = []
    etypes: List[str] = []
    for (etype, name) in scorable:
        if name in cache:
            continue
        if mode == "descriptions":
            content = corpus.descriptions[(etype, name)]
        elif mode == "instructions":
            # Leading newline so the numbered list starts below `**name**:`
            # rather than running on the same line as the name.
            content = "\n" + "\n".join(
                f"{i+1}. {s}" for i, s in enumerate(corpus.pos_instructions[(etype, name)])
            )
        else:
            raise ValueError(mode)
        prompts.append(build_static_prompt(axis_spec, etype, name, content))
        names.append(name)
        etypes.append(etype)
    if not prompts:
        logger.info(f"[{mode}] all {len(scorable)} entities already cached at {cache_path}")
        return {k: v for k, v in cache.items() if isinstance(v, int)}

    logger.info(
        f"[{mode}] scoring {len(prompts)} entities "
        f"({len(scorable) - len(prompts)} already cached) via {args.provider}:{args.judge_model}"
    )

    # Score in smaller sub-batches so the cache is saved frequently for crash-safety.
    written_cache = dict(cache)
    save_every = max(1, args.save_every)
    for i in tqdm(range(0, len(prompts), save_every), desc=f"{mode}"):
        chunk_prompts = prompts[i:i + save_every]
        chunk_names = names[i:i + save_every]
        raw_texts = await call_judge(
            chunk_prompts, provider=args.provider, model=args.judge_model,
            max_tokens=args.max_tokens, temperature=args.temperature,
            rps=args.rps, batch_size=args.batch_size,
        )
        for name, text in zip(chunk_names, raw_texts):
            score = parse_signed_score(text)
            if score is None:
                logger.warning(f"[{mode}] {name}: could not parse score from: {text!r}")
                continue
            written_cache[name] = score
        _save_json(cache_path, written_cache)

    # Return only int-valued entries.
    return {k: v for k, v in written_cache.items() if isinstance(v, int)}


async def score_responses_mode(
    axis_spec: AxisSpec,
    scorable: Sequence[Tuple[str, str]],
    args: argparse.Namespace,
) -> Dict[str, Dict[str, Any]]:
    """Score ALL score==3 responses per entity, partitioned into roughly equal-sized
    batches (targeting `--response_target_batch_size`, default 15). Each batch is one
    judge call producing one -3..+3 score; the entity's final score is the mean of
    those batch scores.

    Cache layout per entity:
        {
          'target_batch_size': int,
          'n_total_items': int,
          'n_batches': int,
          'per_batch': [{'keys': [...], 'score': int|None, 'text': str|None}, ...],
          'batch_scores': [int, ...],     # non-None batch scores
          'mean_score': float|None,
          'std_score': float|None,
        }

    Resume: if the cached plan (target_batch_size + sorted key list per batch) matches
    what we'd compute from the current score==3 pool AND every batch has a non-None
    score, the entity is skipped.
    """
    if not args.scores_dir or not args.responses_dir:
        raise SystemExit("--score_responses requires --scores_dir and --responses_dir")

    cache_path = Path(args.output_dir) / "scores_responses.json"
    cache: Dict[str, Any] = {} if args.no_cache else _load_json_or_empty(cache_path)

    names_only = [n for (_, n) in scorable]
    ent_type_map = {n: et for (et, n) in scorable}

    score3 = load_score3_responses(
        names_only, Path(args.scores_dir), Path(args.responses_dir)
    )
    logger.info(f"[responses] {len(score3)} entities have at least one score==3 response")

    target = args.response_target_batch_size

    # Plan batches for each entity (deterministic from the sorted score==3 keys).
    plans: Dict[str, Dict[str, Any]] = {}  # name -> {items, key_batches, key_to_item}
    for name, items in score3.items():
        sorted_keys = _sort_keys_by_question_then_prompt([it.key for it in items])
        key_to_item = {it.key: it for it in items}
        key_batches = plan_response_batches(sorted_keys, target)
        plans[name] = {
            "items": items,
            "key_batches": key_batches,
            "key_to_item": key_to_item,
        }

    # Build the actual work list: (name, etype, batch_index, [items in batch]).
    to_call: List[Tuple[str, str, int, List[ScoredResponse]]] = []
    written: Dict[str, Any] = dict(cache)
    for name, plan in plans.items():
        etype = ent_type_map.get(name, "roles")
        key_batches: List[List[str]] = plan["key_batches"]
        key_to_item: Dict[str, ScoredResponse] = plan["key_to_item"]
        existing = cache.get(name, {})
        cached_pb = existing.get("per_batch") or []
        cache_matches = (
            existing.get("target_batch_size") == target
            and len(cached_pb) == len(key_batches)
            and all(cached_pb[i].get("keys") == key_batches[i] for i in range(len(key_batches)))
        )
        if cache_matches and not args.no_cache:
            per_batch = cached_pb
        else:
            # Stale or missing -> rebuild per_batch skeleton, drop stale scores.
            per_batch = [{"keys": kb, "score": None, "text": None} for kb in key_batches]

        # Determine which batches need calls.
        for bi, entry in enumerate(per_batch):
            if entry.get("score") is None:
                batch_items = [key_to_item[k] for k in entry["keys"]]
                to_call.append((name, etype, bi, batch_items))

        # Write the up-to-date skeleton into the cache shell.
        written[name] = {
            "target_batch_size": target,
            "n_total_items": len(plan["items"]),
            "n_batches": len(key_batches),
            "per_batch": per_batch,
            "batch_scores": [e["score"] for e in per_batch if isinstance(e.get("score"), int)],
            "mean_score": None,
            "std_score": None,
        }
        _update_response_aggregates(written[name])

    logger.info(
        f"[responses] target_batch_size={target}; "
        f"{len(to_call)} batch calls to run "
        f"({sum(len(p['key_batches']) for p in plans.values())} batches total, "
        f"{sum(len(p['items']) for p in plans.values())} items across all entities)"
    )
    if to_call:
        batch_sizes = [len(items) for (_, _, _, items) in to_call]
        logger.info(
            f"[responses] batch sizes in pending calls: "
            f"min={min(batch_sizes)}, max={max(batch_sizes)}, "
            f"mean={np.mean(batch_sizes):.2f}"
        )

    # Save initial skeleton so a crash here still leaves a coherent cache.
    _save_json(cache_path, written)

    save_every = max(1, args.save_every)
    for i in tqdm(range(0, len(to_call), save_every), desc="responses"):
        chunk = to_call[i:i + save_every]
        prompts = [
            build_response_batch_prompt(axis_spec, etype, name, items)
            for (name, etype, _bi, items) in chunk
        ]
        raw_texts = await call_judge(
            prompts, provider=args.provider, model=args.judge_model,
            max_tokens=args.max_tokens, temperature=args.temperature,
            rps=args.rps, batch_size=args.batch_size,
        )
        for (name, _etype, bi, _items), text in zip(chunk, raw_texts):
            score = parse_signed_score(text)
            written[name]["per_batch"][bi]["score"] = score
            written[name]["per_batch"][bi]["text"] = text

        for name in written:
            _update_response_aggregates(written[name])
        _save_json(cache_path, written)

    for name in written:
        _update_response_aggregates(written[name])
    _save_json(cache_path, written)
    return {k: v for k, v in written.items() if isinstance(v, dict)}


def _update_response_aggregates(entry: Dict[str, Any]) -> None:
    """Recompute batch_scores/mean_score/std_score from entry['per_batch']."""
    per_batch = entry.get("per_batch", [])
    ints = [b["score"] for b in per_batch if isinstance(b.get("score"), int)]
    entry["batch_scores"] = ints
    if ints:
        arr = np.asarray(ints, dtype=float)
        entry["mean_score"] = float(arr.mean())
        entry["std_score"] = float(arr.std(ddof=0)) if len(arr) > 1 else 0.0
    else:
        entry["mean_score"] = None
        entry["std_score"] = None


# ---------------------------------------------------------------------------
# Correlations and plot
# ---------------------------------------------------------------------------

def _spearmanr(x: np.ndarray, y: np.ndarray) -> Tuple[float, float]:
    """Spearman rho and a two-sided p-value (via scipy if available, else manual)."""
    try:
        from scipy.stats import spearmanr  # type: ignore
        res = spearmanr(x, y)
        return float(res.correlation), float(res.pvalue)
    except Exception:
        # Fallback: rank-Pearson without p-value.
        def _rankdata(v: np.ndarray) -> np.ndarray:
            order = np.argsort(v, kind="mergesort")
            ranks = np.empty_like(order, dtype=float)
            ranks[order] = np.arange(1, len(v) + 1)
            # Tied ranks: replace tied runs with their mean
            sv = v[order]
            i = 0
            while i < len(sv):
                j = i + 1
                while j < len(sv) and sv[j] == sv[i]:
                    j += 1
                if j > i + 1:
                    mean_rank = (ranks[order[i]] + ranks[order[j - 1]]) / 2.0
                    for k in range(i, j):
                        ranks[order[k]] = mean_rank
                i = j
            return ranks
        rx, ry = _rankdata(x), _rankdata(y)
        if len(x) < 3:
            return float("nan"), float("nan")
        rx_c, ry_c = rx - rx.mean(), ry - ry.mean()
        denom = np.sqrt((rx_c**2).sum() * (ry_c**2).sum())
        rho = float((rx_c * ry_c).sum() / denom) if denom > 0 else float("nan")
        return rho, float("nan")


def compute_correlations(
    scores_by_mode: Dict[str, Dict[str, float]],
    projections: Dict[int, Dict[str, Dict[str, float]]],
    slots: Sequence[int],
    excluded_set: set,
) -> Dict[str, Any]:
    """Returns {mode: {slot: {raw|whitened: {rho, p, n, names, scores, projections}}}}."""
    out: Dict[str, Any] = {}
    for mode, score_map in scores_by_mode.items():
        out[mode] = {}
        for slot in slots:
            out[mode][str(slot)] = {}
            per_slot = projections.get(slot, {})
            for metric in ("raw", "whitened"):
                names = []
                svals = []
                pvals = []
                for name, s in sorted(score_map.items()):
                    if name in excluded_set:
                        continue
                    if name not in per_slot:
                        continue
                    p = per_slot[name].get(metric)
                    if p is None or not np.isfinite(p):
                        continue
                    names.append(name)
                    svals.append(s)
                    pvals.append(p)
                if len(svals) >= 3:
                    rho, pval = _spearmanr(np.asarray(svals, dtype=float),
                                           np.asarray(pvals, dtype=float))
                else:
                    rho, pval = float("nan"), float("nan")
                out[mode][str(slot)][metric] = {
                    "rho": rho, "p": pval, "n": len(svals),
                    "names": names, "scores": svals, "projections": pvals,
                }
    return out


def make_plot(
    correlations: Dict[str, Any],
    slots: Sequence[int],
    axis_spec: AxisSpec,
    output_path: Path,
    slot_labels: Optional[Dict[int, str]] = None,
) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    modes = list(correlations.keys())
    if not modes:
        logger.warning("no correlation data to plot")
        return
    n_modes = len(modes)
    metrics = ("raw", "whitened")
    n_cols = len(slots) * len(metrics)
    n_rows = n_modes

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(3.0 * n_cols, 3.0 * n_rows),
                             squeeze=False, sharex=False, sharey=False)
    fig.suptitle(
        f"Axis judge correlation: {axis_spec.axis_name}\n"
        f"neg: {axis_spec.neg_pole[:90]}...\npos: {axis_spec.pos_pole[:90]}...",
        fontsize=10,
    )

    sl = slot_labels or {i: f"slot {i}" for i in slots}
    for ri, mode in enumerate(modes):
        for ci, (slot, metric) in enumerate(
            [(s, m) for s in slots for m in metrics]
        ):
            ax = axes[ri, ci]
            entry = correlations[mode][str(slot)][metric]
            s = np.asarray(entry["scores"], dtype=float)
            p = np.asarray(entry["projections"], dtype=float)
            rho = entry["rho"]
            n = entry["n"]
            ax.scatter(s, p, s=10, alpha=0.55, edgecolor="none")
            if n >= 3 and np.isfinite(rho) and np.isfinite(p).all() and p.std() > 0 and s.std() > 0:
                # Simple OLS best-fit overlay
                slope, intercept = np.polyfit(s, p, 1)
                xs = np.array([s.min() - 0.2, s.max() + 0.2])
                ax.plot(xs, slope * xs + intercept, color="black", lw=0.8, alpha=0.6)
            ax.set_title(
                f"{mode} | {sl[slot]} | {metric}\n"
                + (f"ρ={rho:.3f}, n={n}" if np.isfinite(rho) else f"n={n}"),
                fontsize=9,
            )
            ax.set_xlabel("judge score", fontsize=8)
            ax.set_ylabel("projection", fontsize=8)
            ax.tick_params(labelsize=7)
            ax.grid(True, alpha=0.3)

    fig.tight_layout(rect=(0, 0, 1, 0.94))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=140, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Score roles/traits on a semantic axis with a judge LLM "
                    "and correlate with activation-space projections.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Axis specification (choose one of two paths).
    axis = p.add_argument_group("axis specification")
    axis.add_argument("--pair", nargs=2, metavar=("POS_NAME", "NEG_NAME"),
                      help="Pair of role or trait names. Positive pole listed first. "
                           "Their descriptions become pole text (unless overridden), their "
                           "names become example lists, and their vector difference is the "
                           "direction.")
    axis.add_argument("--pair_type", choices=["roles", "traits"],
                      help="Required with --pair.")
    axis.add_argument("--axis_file", type=str,
                      help="Path to a .pt file (dict with 'axis' or 'vector' key, or raw tensor). "
                           "Accepted shapes: (n_slots, n_layers, hidden), (n_layers, hidden), "
                           "or (hidden,).")
    axis.add_argument("--axis_name", type=str,
                      help="Display name for the axis. Defaults to pair / file name.")
    axis.add_argument("--neg_pole", type=str, help="Text description of the negative pole.")
    axis.add_argument("--pos_pole", type=str, help="Text description of the positive pole.")
    axis.add_argument("--neg_examples", type=_csv_or_space_list, default=[],
                      help="Comma-separated names of negative-pole exemplars.")
    axis.add_argument("--pos_examples", type=_csv_or_space_list, default=[],
                      help="Comma-separated names of positive-pole exemplars.")

    # Data.
    data = p.add_argument_group("data")
    data.add_argument("--data_dir", type=str, required=True,
                      help="Directory containing roles/vectors/*.pt and/or traits/vectors/*.pt.")
    data.add_argument("--instructions_dir", type=str, default="data",
                      help="Top-level directory with roles/instructions/*.json and "
                           "traits/instructions/*.json.")
    data.add_argument("--scores_dir", type=str,
                      help="Directory of per-entity scores JSONs; required for --score_responses.")
    data.add_argument("--responses_dir", type=str,
                      help="Directory of per-entity responses .jsonl files; required for "
                           "--score_responses.")
    data.add_argument("--layer", type=int, default=24)
    data.add_argument("--slot", type=str, default="all",
                      help="Token-slot index, or 'all'.")

    # Whitening.
    w = p.add_argument_group("whitening")
    w.add_argument("--whiten_K", type=int, default=128,
                   help="Number of top PCs to soft-scale down to sigma_{K+1}.")

    # Scoring modes.
    sm = p.add_argument_group("scoring modes")
    sm.add_argument("--score_descriptions", action="store_true",
                    help="Score each entity's description text.")
    sm.add_argument("--score_instructions", action="store_true",
                    help="Score each entity's concatenated 5 pos instructions.")
    sm.add_argument("--score_responses", action="store_true",
                    help="Score all score==3 model responses per entity, partitioned into "
                         "roughly equal-sized batches (one -3..+3 score per batch; "
                         "entity score = mean of batch scores).")
    sm.add_argument("--response_target_batch_size", type=int, default=15,
                    help="Target responses per batch for --score_responses. Actual batch "
                         "sizes will differ by at most 1 to cover all items (N items -> "
                         "max(1, round(N/target)) equal-sized batches).")
    sm.add_argument("--all", action="store_true",
                    help="Equivalent to --score_descriptions --score_instructions --score_responses.")

    # Judge.
    j = p.add_argument_group("judge")
    j.add_argument("--provider", choices=["anthropic", "openai"], default="anthropic")
    j.add_argument("--judge_model", type=str, default=None,
                   help="Defaults: claude-sonnet-4-20250514 (anthropic) / gpt-4.1-mini (openai).")
    j.add_argument("--max_tokens", type=int, default=1024,
                   help="Token budget for the judge response (must fit reasoning + SCORE line).")
    j.add_argument("--temperature", type=float, default=0.0,
                   help="Sampling temperature; 0 for greedy/deterministic rubric grading.")
    j.add_argument("--rps", type=float, default=10.0, help="Requests per second (token bucket).")
    j.add_argument("--batch_size", type=int, default=20, help="Concurrent in-flight calls.")
    j.add_argument("--save_every", type=int, default=40,
                   help="How many judge calls between cache flushes.")
    j.add_argument("--no_cache", action="store_true", help="Rescore everything from scratch.")

    # Output.
    o = p.add_argument_group("output")
    o.add_argument("--output_dir", type=str, required=True)
    o.add_argument("--max_entities", type=int, default=None,
                   help="Limit total entities scored (for dry runs).")

    args = p.parse_args()
    if args.all:
        args.score_descriptions = True
        args.score_instructions = True
        args.score_responses = True
    if not (args.score_descriptions or args.score_instructions or args.score_responses):
        p.error("Specify at least one of --score_descriptions / --score_instructions / "
                "--score_responses, or use --all.")
    if args.judge_model is None:
        args.judge_model = _default_model_for_provider(args.provider)
    return args


def _csv_or_space_list(s: str) -> List[str]:
    if not s:
        return []
    # Accept comma- or whitespace-separated.
    parts = [p.strip() for p in re.split(r"[,\s]+", s) if p.strip()]
    return parts


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run(args: argparse.Namespace) -> None:
    # Peek at one vector file to figure out n_slots / hidden_dim.
    data_dir = Path(args.data_dir)
    probe_paths = list((data_dir / "roles" / "vectors").glob("*.pt")) \
        + list((data_dir / "traits" / "vectors").glob("*.pt"))
    probe_paths = [p for p in probe_paths if p.name != "default.pt"]
    if not probe_paths:
        raise SystemExit(f"No vectors found under {data_dir}/(roles|traits)/vectors/")
    probe = _load_vector_file(probe_paths[0]).float()
    if probe.dim() != 3:
        raise SystemExit(f"Expected (n_slots, n_layers, hidden) vectors; got shape {tuple(probe.shape)}")
    n_slots, n_layers, hidden_dim = probe.shape
    logger.info(f"n_slots={n_slots} n_layers={n_layers} hidden={hidden_dim}; "
                f"using layer={args.layer}")
    if not 0 <= args.layer < n_layers:
        raise SystemExit(f"--layer {args.layer} out of range [0, {n_layers})")
    slots = _slot_list_from_arg(args.slot, n_slots)

    # Build the axis spec and load corpus.
    axis_spec = resolve_axis(args, n_slots, hidden_dim, args.layer)
    corpus = load_corpus(args, args.layer)

    # Which entities are scorable? All corpus entities minus the exclusion set.
    exclusion_set = set(axis_spec.exclusions)
    scorable: List[Tuple[str, str]] = [
        (et, n) for (et, n) in corpus.entities if n not in exclusion_set
    ]
    if args.max_entities is not None:
        scorable = scorable[:args.max_entities]
    logger.info(
        f"Scorable entities: {len(scorable)} "
        f"(excluded {len(corpus.entities) - len(scorable)} as poles/examples or by --max_entities)"
    )

    # Projections first (no API calls) so we can save them even if scoring is slow.
    projections = compute_projections(
        corpus=corpus, axis_spec=axis_spec, whiten_K=args.whiten_K,
        slots=slots, excluded_names=list(exclusion_set),
    )
    proj_out = {str(slot): per_slot for slot, per_slot in projections.items()}
    _save_json(Path(args.output_dir) / "projections.json", proj_out)

    # Save config up-front.
    config = {
        "args": {k: v for k, v in vars(args).items()},
        "n_slots": n_slots, "n_layers": n_layers, "hidden_dim": hidden_dim,
        "slots": slots, "layer": args.layer, "whiten_K": args.whiten_K,
        "axis_name": axis_spec.axis_name,
        "axis_source": axis_spec.source_description,
        "neg_pole": axis_spec.neg_pole, "pos_pole": axis_spec.pos_pole,
        "neg_examples": axis_spec.neg_examples, "pos_examples": axis_spec.pos_examples,
        "exclusions": axis_spec.exclusions,
        "n_scorable": len(scorable),
    }
    _save_json(Path(args.output_dir) / "config.json", config)

    # Run each requested scoring mode.
    scores_for_corr: Dict[str, Dict[str, float]] = {}
    if args.score_descriptions:
        d = await score_static_mode("descriptions", corpus, axis_spec, scorable, args)
        scores_for_corr["descriptions"] = {k: float(v) for k, v in d.items()}
    if args.score_instructions:
        d = await score_static_mode("instructions", corpus, axis_spec, scorable, args)
        scores_for_corr["instructions"] = {k: float(v) for k, v in d.items()}
    if args.score_responses:
        resp_cache = await score_responses_mode(axis_spec, scorable, args)
        means = {
            n: float(d["mean_score"]) for n, d in resp_cache.items()
            if d.get("mean_score") is not None
        }
        scores_for_corr["responses"] = means

    # Compute correlations and output.
    correlations = compute_correlations(
        scores_by_mode=scores_for_corr, projections=projections,
        slots=slots, excluded_set=exclusion_set,
    )
    _save_json(Path(args.output_dir) / "correlations.json", correlations)

    # Make plot.
    make_plot(
        correlations=correlations, slots=slots, axis_spec=axis_spec,
        output_path=Path(args.output_dir) / "correlation_plot.png",
    )

    # Print a brief summary.
    print("\n=== Spearman rho summary ===")
    print(f"axis: {axis_spec.axis_name}")
    for mode in correlations:
        print(f"\n{mode}:")
        for slot in slots:
            r = correlations[mode][str(slot)]
            print(
                f"  slot {slot}: "
                f"raw rho={r['raw']['rho']:+.3f} (n={r['raw']['n']}), "
                f"wht rho={r['whitened']['rho']:+.3f} (n={r['whitened']['n']})"
            )


def main() -> None:
    args = parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
