"""Readers of a recorded harness batch beyond its own report (plan 13 § 5 ``recovery_extras.py``; § 1 rows on the
strict column and pair recovery).  No call is made: everything is read from ``seed<S>/matches.jsonl`` (one row per
label match and per pair the match stage judged), the reduced-corpus M3 run's ``run.json`` and the generator runs'
``candidates.jsonl``.

* **The strict column** (:func:`strict_column`): recall with every pair read at the fixed cut-off 4 (Roger,
  2026-10-12: "3 is primary, report 4 as well"), from the recorded readings (``recovery.pair_outcome(reading, 4)``
  under the reduced run's rules).  A pair whose Sonnet reading would need an Opus reading at 4 that it lacks (Sonnet
  4, or 3 under the Opus check, with no Opus reading) cannot be decided from the record: it is listed in
  ``needs_opus`` and not counted.  On the four recorded batches there are none (the match wave sends every Sonnet
  reading at c - 1 or above to Opus).
* **Pair recovery** (:func:`pair_recovery`): a hidden trait some kept candidate was read ``opposite`` against: the
  candidate is its antonym, which finds the trait's pole when the harness hides pairs whole.  Printed beside recall,
  never summed into it.
* **Recall at N** (:func:`recall_at_n`): recall using only the candidates a generator ranked in its top share
  (its own ``rank`` in ``candidates.jsonl``): how early in its output a generator finds what it finds.
* **Contamination** (:func:`contamination`): the change in recall when the stems that came from the generator's own
  source are excluded from the draw (``recovery_test.py --exclude-provenance``); none apply today.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

from .. import novelty as NV
from .. import recovery as RC

STRICT_C = 4
#: Sonnet's actions at a cut-off that need an Opus reading before the pair is decided.
NEEDS_OPUS_ACTIONS = ("opus_decides", "opus_check", "opus_replaces", "opus_confirms")
RANK_QUANTILES = (0.1, 0.25, 0.5, 0.75, 1.0)


def read_jsonl(p: Path) -> list[dict]:
    p = Path(p)
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.exists() else []


def seed_dirs(batch_dir: Path) -> list[Path]:
    return sorted((p for p in Path(batch_dir).glob("seed*") if p.is_dir()), key=lambda p: int(p.name[4:] or 0))


def m3_dir_for(seed_dir: Path) -> Path:
    """The reduced-corpus M3 run of a seed: ``novelty/<batch>_s<seed>/`` beside ``recovery/``."""
    seed_dir = Path(seed_dir)
    batch = seed_dir.parent
    return batch.parent.parent / "novelty" / f"{batch.name}_s{seed_dir.name[4:]}"


def run_rules(seed_dir: Path) -> NV.Rules:
    p = m3_dir_for(seed_dir) / "run.json"
    if p.exists():
        r = json.loads(p.read_text(encoding="utf-8")).get("rules")
        if r:
            return NV.rules_of({"rules": r})
    return NV.DEFAULT_RULES


def decisions_of(seed_dir: Path) -> dict[str, Optional[str]]:
    """key -> the reduced run's decision (from its ``results.jsonl``)."""
    return {r["key"]: (r.get("novelty") or {}).get("decision") for r in read_jsonl(m3_dir_for(seed_dir) / "results.jsonl")}


def _reading(r: Mapping) -> dict:
    return {"sonnet": r.get("sonnet"), "opus": r.get("opus")}


@dataclass
class StrictFigures:
    c: int
    n_hidden: int
    n_recovered: int
    recall: Optional[float]
    n_recovered_headline: int
    recovered: list = field(default_factory=list)
    lost_at_strict: list = field(default_factory=list)     # recovered at the run's cut-off, not at the strict one
    needs_opus: list = field(default_factory=list)          # pairs the record cannot decide at c

    def as_dict(self) -> dict:
        return asdict(self)


def strict_column(seed_dir: Path, *, c: int = STRICT_C, hidden: Optional[Sequence[str]] = None,
                  decisions: Optional[Mapping[str, Optional[str]]] = None,
                  keys: Optional[set] = None) -> StrictFigures:
    """Recall over the kept candidates (``keys``: only these) with every overlap pair read at the fixed cut-off
    ``c``; label matches recover at any cut-off."""
    seed_dir = Path(seed_dir)
    rows = read_jsonl(seed_dir / "matches.jsonl")
    hid = list(hidden) if hidden is not None else json.loads((seed_dir / "hidden.json").read_text())["hidden"]
    dec = decisions if decisions is not None else decisions_of(seed_dir)
    rules = run_rules(seed_dir)
    got, head, needs = set(), set(), []
    for r in rows:
        if dec.get(r["key"]) not in RC.KEPT_DECISIONS or (keys is not None and r["key"] not in keys):
            continue
        if r.get("recovers"):
            head.add(r["stem"])
        if r.get("how") == "label":
            got.add(r["stem"])
            continue
        if r.get("stalled"):
            continue
        s = (r.get("sonnet") or {}).get("value")
        o = (r.get("opus") or {}).get("value") if r.get("opus") else None
        if NV.sonnet_action(s, c) in NEEDS_OPUS_ACTIONS and o is None:
            needs.append({"key": r["key"], "stem": r["stem"], "sonnet": s, "cut_off": r.get("cut_off")})
            continue
        if RC.pair_outcome(_reading(r), c, rules)["recovers"]:
            got.add(r["stem"])
    return StrictFigures(c=c, n_hidden=len(hid), n_recovered=len(got), recall=RC._share(len(got), len(hid)),
                         n_recovered_headline=len(head), recovered=sorted(got), lost_at_strict=sorted(head - got),
                         needs_opus=needs)


@dataclass
class PairFigures:
    n_hidden: int
    n_pair_recovered: int
    share: Optional[float]
    n_also_recovered: int                   # of those, recovered outright too
    by_region: dict = field(default_factory=dict)
    stems: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def pair_recovery(seed_dir: Path, *, hidden_doc: Optional[Mapping] = None,
                  decisions: Optional[Mapping[str, Optional[str]]] = None, keys: Optional[set] = None) -> PairFigures:
    """Hidden traits a kept candidate was read ``opposite`` against (once per hidden trait), by region."""
    seed_dir = Path(seed_dir)
    hd = hidden_doc if hidden_doc is not None else json.loads((seed_dir / "hidden.json").read_text())
    dec = decisions if decisions is not None else decisions_of(seed_dir)
    rows = [r for r in read_jsonl(seed_dir / "matches.jsonl")
            if dec.get(r["key"]) in RC.KEPT_DECISIONS and (keys is None or r["key"] in keys)]
    opp = {r["stem"] for r in rows if r.get("verdict") == "opposite"}
    rec = {r["stem"] for r in rows if r.get("recovers")}
    tr = hd.get("traits") or {}
    tot, got = Counter(), Counter()
    for s in hd["hidden"]:
        reg = (tr.get(s) or {}).get("region") or RC.NO_REGION
        tot[reg] += 1
        got[reg] += s in opp
    return PairFigures(n_hidden=len(hd["hidden"]), n_pair_recovered=len(opp),
                       share=RC._share(len(opp), len(hd["hidden"])), n_also_recovered=len(opp & rec),
                       by_region={k: {"n_hidden": tot[k], "n_pair_recovered": got[k]} for k in sorted(tot)},
                       stems=sorted(opp))


def run_ranks(run_dir: Path) -> dict[str, float]:
    """key -> the generator's own rank of the candidate (``candidates.jsonl``; the best rank where a key appears more
    than once).  Candidates without a rank are left out."""
    from ..normalize import make_key, normalize_candidate
    out: dict[str, float] = {}
    for c in read_jsonl(Path(run_dir) / "candidates.jsonl"):
        if c.get("rank") is None:
            continue
        try:
            n = normalize_candidate(c["surface"])
        except Exception:  # noqa: BLE001 - a surface the registry refused is not a row
            continue
        k = make_key(n.stem, int(c.get("sense_id") or 1))
        out[k] = min(float(c["rank"]), out.get(k, float("inf")))
    return out


def recall_at_n(seed_dir: Path, run_dir: Path, *, quantiles: Sequence[float] = RANK_QUANTILES,
                keys: Optional[set] = None, decisions: Optional[Mapping[str, Optional[str]]] = None) -> list[dict]:
    """``[{"quantile", "max_rank", "n_candidates", "n_recovered", "recall"}]``: recall using only the kept candidates
    whose rank is within the first ``quantile`` of the run's ranks (``keys``: the run's rows in a pooled batch)."""
    seed_dir = Path(seed_dir)
    ranks = run_ranks(run_dir)
    if keys is not None:
        ranks = {k: v for k, v in ranks.items() if k in keys}
    if not ranks:
        return []
    hid = json.loads((seed_dir / "hidden.json").read_text())["hidden"]
    dec = decisions if decisions is not None else decisions_of(seed_dir)
    rows = [r for r in read_jsonl(seed_dir / "matches.jsonl") if r.get("recovers") and dec.get(r["key"]) in
            RC.KEPT_DECISIONS and r["key"] in ranks]
    ordered = sorted(ranks.values())
    out = []
    for q in quantiles:
        cut = ordered[max(0, min(len(ordered) - 1, int(round(q * len(ordered))) - 1))]
        got = {r["stem"] for r in rows if ranks[r["key"]] <= cut}
        out.append({"quantile": q, "max_rank": cut, "n_candidates": sum(1 for v in ranks.values() if v <= cut),
                    "n_recovered": len(got), "recall": RC._share(len(got), len(hid))})
    return out


def contamination(report_a: Mapping, report_b: Mapping) -> dict:
    """The change from report ``a`` (the plain draw) to ``b`` (with ``--exclude-provenance``): mean recall and
    precision over kept candidates, b minus a."""
    def m(r, k):
        return (r.get("mean") or {}).get(k)
    out = {}
    for k in ("recall_kept", "precision_kept", "recall_either"):
        a, b = m(report_a, k), m(report_b, k)
        out[k] = {"plain": a, "excluded": b, "delta": None if a is None or b is None else round(b - a, 4)}
    return out


def extras_json(batch_dir: Path, *, runs_root: Optional[Path] = None, c: int = STRICT_C) -> dict:
    """``extras.json`` of a recorded harness batch: per seed the strict column, pair recovery and recall at N (per
    run in a pooled batch, from the runs' ``candidates.jsonl`` under ``runs_root``), and the ``needs_opus`` list over
    all seeds."""
    batch_dir = Path(batch_dir)
    run = json.loads((batch_dir / "run.json").read_text(encoding="utf-8")) if (batch_dir / "run.json").exists() else {}
    runs_root = Path(runs_root) if runs_root is not None else batch_dir.parent.parent / "runs"
    pooled = bool(run.get("pooled"))
    seeds = []
    needs_all = []
    for sd in seed_dirs(batch_dir):
        if not (sd / "matches.jsonl").exists():
            continue
        hd = json.loads((sd / "hidden.json").read_text(encoding="utf-8"))
        dec = decisions_of(sd)
        strict = strict_column(sd, c=c, hidden=hd["hidden"], decisions=dec)
        pair = pair_recovery(sd, hidden_doc=hd, decisions=dec)
        rec: dict = {"seed": hd.get("seed"), "strict": strict.as_dict(), "pair_recovery": pair.as_dict()}
        if not pooled and run.get("generator") and run.get("run_id"):
            rec["recall_at_n"] = recall_at_n(sd, runs_root / run["generator"] / run["run_id"], decisions=dec)
        elif pooled:
            res = read_jsonl(m3_dir_for(sd) / "results.jsonl")
            runs_of = defaultdict(set)
            for r in res:
                for g in r.get("generators") or []:
                    runs_of[g].add(r["key"])
            rec["recall_at_n_by_run"] = {}
            for gdir in sorted(p for p in runs_root.glob("*/*") if (p / "candidates.jsonl").exists()):
                g, rid = gdir.parent.name, gdir.name
                if g not in runs_of:
                    continue
                pts = recall_at_n(sd, gdir, keys=runs_of[g], decisions=dec)
                if pts:
                    rec["recall_at_n_by_run"][f"{g}/{rid}"] = pts
        needs_all += [dict(x, seed=hd.get("seed")) for x in strict.needs_opus]
        seeds.append(rec)
    return {"batch_id": batch_dir.name, "pooled": pooled, "c_strict": c, "seeds": seeds, "needs_opus": needs_all,
            "n_needs_opus": len(needs_all)}


def extras_markdown(ex: Mapping) -> str:
    L = [f"Strict column (cut-off {ex['c_strict']}) and pair recovery for `{ex['batch_id']}`:", "",
         "| seed | recall at the run's cut-off | recall at 4 | lost at 4 | pair-recovered (read opposite) | "
         "needs an Opus reading |", "|---|---|---|---|---|---|"]
    for s in ex["seeds"]:
        st, pr = s["strict"], s["pair_recovery"]
        L.append(f"| {s['seed']} | {st['n_recovered_headline']} of {st['n_hidden']} | {st['n_recovered']} of "
                 f"{st['n_hidden']} | {len(st['lost_at_strict'])} | {pr['n_pair_recovered']} | {len(st['needs_opus'])} |")
    return "\n".join(L) + "\n"


def roger_sample(batch_dir: Path, *, traits: Mapping[str, NV.CorpusTrait], n: int = 20, seed: int = 0) -> str:
    """``roger_sample.md`` (plan 13 § 8, the manual check): ``n`` seeded "recovered" verdicts (overlap pairs of a kept
    candidate that recovered a hidden trait) and ``n`` "novel" ones (overlap pairs of a kept candidate read below the
    cut-off against a hidden trait), over every seed of the batch, each with the candidate's gloss, the hidden
    trait's description and both models' readings, and an empty column for Roger's verdict.  Label matches are left
    out (they need no judgement).  Links are relative to the batch directory."""
    import random
    batch_dir = Path(batch_dir)
    rec, nov = [], []
    for sd in seed_dirs(batch_dir):
        dec = decisions_of(sd)
        gloss = {r["key"]: r.get("gloss") for r in read_jsonl(m3_dir_for(sd) / "results.jsonl")}
        for r in read_jsonl(sd / "matches.jsonl"):
            if r.get("how") != "overlap" or r.get("stalled") or dec.get(r["key"]) not in RC.KEPT_DECISIONS:
                continue
            x = dict(r, seed=int(sd.name[4:] or 0), gloss=gloss.get(r["key"]))
            (rec if r.get("recovers") else nov).append(x)
    rng = random.Random(seed)
    pick_r = rng.sample(rec, min(n, len(rec)))
    pick_n = rng.sample(nov, min(n, len(nov)))

    def md(x) -> str:
        return str("" if x is None else x).replace("|", "/").replace("\n", " ")

    def reading(x) -> str:
        s, o = x.get("sonnet") or {}, x.get("opus") or {}
        out = f"Sonnet {s.get('value')}: {md(s.get('reason'))}"
        return out + (f"<br>Opus {o.get('value')}: {md(o.get('reason'))}" if o else "")
    L = [f"# Manual check of the harness's verdicts (`{batch_dir.name}`)", "",
         f"Plan 13 § 8: {len(pick_r)} recovered and {len(pick_n)} novel verdicts drawn at random (seed {seed}) from "
         f"the overlap pairs of the kept candidates ({len(rec)} recovered and {len(nov)} novel pairs in all; "
         "label matches left out).  *Recovered*: the overlap call read the candidate as the hidden trait, at the "
         "candidate's cut-off or above; *novel*: it read it below.  Mark each row **agree** or **disagree** in the "
         "last column.", ""]
    for title, xs in (("Recovered", pick_r), ("Novel", pick_n)):
        L += [f"## {title}", "", "| # | seed | candidate (its gloss) | hidden trait (its description) | readings | "
              "verdict | Roger |", "|---|---|---|---|---|---|---|"]
        for i, x in enumerate(xs, 1):
            t = traits.get(x["stem"])
            L.append(f"| {i} | {x['seed']} | **{md(x['label'])}**: {md(x.get('gloss'))} | **{md(t.label if t else x['stem'])}**"
                     f": {md(t.description if t else '')} | {reading(x)} | {x.get('verdict')} at {x.get('cut_off')} | |")
        L.append("")
    return "\n".join(L) + "\n"


__all__ = ["roger_sample", "STRICT_C", "StrictFigures", "strict_column", "PairFigures", "pair_recovery", "run_ranks", "recall_at_n",
           "contamination", "extras_json", "extras_markdown", "seed_dirs", "m3_dir_for", "decisions_of"]
