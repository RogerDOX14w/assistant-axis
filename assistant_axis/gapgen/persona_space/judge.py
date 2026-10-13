"""Decision 2b: the ``dup_vs_new`` disagreements read through M3's own overlap call (coding_plan_12_persona_space.md,
"Rendered prompt").

For every candidate M3 decided ``new`` that persona space calls duplicate-like, the pair (the candidate's label and
gloss as the target, the persona-nearest corpus trait's label and description as the other) is read under rubric A
exactly as the recovery harness's match stage reads one: :meth:`NoveltyRunner.run_pairs`, Sonnet 5.5 on every pair,
Opus 5.5 on the pairs M3's rule sends it at the candidate's cut-off, one pair per call, the system prompt cached.
Every response is appended to ``responses.jsonl`` as it arrives, before it is parsed; a budget stop is raised after
every answer is recorded.  The reading is summarised (:func:`summarise`: the pair's verdict under M3's rule at the
candidate's cut-off, and whether it reaches the cut-off) and recorded in the batch and on the ``persona`` block's
``reading``; **it is never written into the ``novelty`` block and never changes M3's decision**.

A response stopped with ``stop_reason: "refusal"`` (Sonnet 5.5's reasoning-extraction refusals, judging rule of
2026-10-13) is a failed call: it is recorded, counted in ``n_refused``, and its pair's verdict is ``refused``, never
read as an empty answer.  M3's rubric asks for a one-sentence reason, which Sonnet 5.5 answers.
"""
from __future__ import annotations

from typing import Mapping, Optional, Sequence

from .. import novelty as NV
from .. import novelty_runner as NR
from ..cost import Estimate


def pairs(dis: Sequence, *, kind: str = "dup_vs_new") -> list[tuple[str, str, int]]:
    """``[(key, stem, 1)]``: each listed disagreement of ``kind`` once, with its persona-nearest trait's stem."""
    out, seen = [], set()
    for d in dis:
        k = d.kind if hasattr(d, "kind") else d["kind"]
        key = d.key if hasattr(d, "key") else d["key"]
        stem = d.judge_stem if hasattr(d, "judge_stem") else d.get("judge_stem")
        if k != kind or key in seen or not stem:
            continue
        seen.add(key)
        out.append((key, stem, 1))
    return out


def read_pairs(runner: NR.NoveltyRunner, cands: Sequence[NR.M3Candidate], pair_list: Sequence[tuple[str, str, int]],
               *, wave: str = "p") -> dict:
    """The overlap call on every pair (:meth:`NoveltyRunner.run_pairs`): ``{(key, stem): {"sonnet", "opus"} |
    {"stalled", "phase"}}``.  Raises a budget stop after every answer is recorded."""
    by_key = {c.key: c for c in cands}
    missing = sorted({k for k, _, _ in pair_list} - set(by_key))
    if missing:
        raise KeyError(f"pairs for candidates not given: {missing[:10]}")
    return runner.run_pairs([by_key[k] for k in dict.fromkeys(k for k, _, _ in pair_list)], list(pair_list),
                            wave=wave)


def refusals(records: Sequence[Mapping]) -> dict[tuple[str, str], int]:
    """``{(key, stem): number of responses stopped as refusals}`` in a run's records."""
    out: dict = {}
    for r in records:
        if r.get("stop_reason") == "refusal":
            k = (r.get("key"), r.get("stem"))
            out[k] = out.get(k, 0) + 1
    return out


def summarise(readings: Mapping[tuple[str, str], Mapping], cands: Sequence[NR.M3Candidate], *,
              rules: Optional[NV.Rules] = None, records: Sequence[Mapping] = ()) -> dict[str, dict]:
    """``{key: {"stem", "sonnet", "opus", "verdict", "at_cut_off", ...}}``: each pair under M3's rule at the
    candidate's cut-off (:func:`novelty.pair_verdict`; ``at_cut_off`` when the rule set would cover on it,
    :func:`novelty.verdict_cuts`).  A pair whose every answer was a refusal is ``refused``; a pair left without an
    answer is ``stalled``; neither reaches the cut-off."""
    rules = rules or NV.DEFAULT_RULES
    by_key = {c.key: c for c in cands}
    refused = refusals(records)
    out: dict[str, dict] = {}
    for (key, stem), r in readings.items():
        c = by_key[key]
        spec = c.cut_off_spec(rules)
        n_ref = refused.get((key, stem), 0)
        base = {"stem": stem, "cut_off": spec.c, "n_refused": n_ref}
        if "stalled" in r:
            out[key] = base | {"sonnet": None, "opus": None, "verdict": "stalled", "at_cut_off": False,
                               "why": r["stalled"]}
            continue
        s = (r.get("sonnet") or {}).get("value")
        o = (r.get("opus") or {}).get("value") if r.get("opus") else None
        if s is None and o is None and n_ref:
            out[key] = base | {"sonnet": None, "opus": None, "verdict": "refused", "at_cut_off": False}
            continue
        pv = NV.pair_verdict(s, o, spec)
        out[key] = base | {"sonnet": s, "opus": o, "verdict": pv["verdict"],
                           "at_cut_off": bool(NV.verdict_cuts(pv["verdict"], rules)),
                           "sonnet_reason": (r.get("sonnet") or {}).get("reason"),
                           "opus_reason": (r.get("opus") or {}).get("reason") if r.get("opus") else None}
    return out


def block_reading(summary: Mapping) -> dict:
    """The ``reading`` field of a ``persona`` block (§ 6): ``{"stem", "sonnet", "opus", "verdict", "at_cut_off"}``."""
    return {k: summary.get(k) for k in ("stem", "sonnet", "opus", "verdict", "at_cut_off")}


def render(runner: NR.NoveltyRunner, cand: NR.M3Candidate, stem: str) -> dict:
    """The request the first (Sonnet) call of a pair is sent as (``llm.request_params``): for the dry run and the
    rendered-prompt rule."""
    st = runner.states.get(cand.key) or NR.CandState(cand=cand)
    call = runner._overlap_call(st, stem, "sonnet", 1)
    return NR.request_params_for(call)


def estimate(n_pairs: int, *, opus_share: float = NR.OPUS_SHARE_FULL_SCAN) -> Estimate:
    """Sonnet on every pair, Opus on ``opus_share`` of them (the full scan's 40%, the larger of M3's two measured
    shares for a pair read whole), at the overlap call's measured tokens (:data:`novelty_runner.OVERLAP_TOKENS`)."""
    est = Estimate()
    est.add("overlap, Sonnet (every pair)", NR.FIRST_MODEL, n_pairs, *NR.OVERLAP_TOKENS["sonnet"])
    est.add(f"overlap, Opus ({opus_share:.0%} of pairs)", NR.SECOND_MODEL, int(round(n_pairs * opus_share)),
            *NR.OVERLAP_TOKENS["opus"])
    return est
